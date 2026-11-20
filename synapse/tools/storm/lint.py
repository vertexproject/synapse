import os
import sys
import fnmatch
import tomllib

import regex

import synapse.exc as s_exc

import synapse.lib.cmd as s_cmd
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.schemas as s_schemas
import synapse.lib.stormlint as s_stormlint
import synapse.lib.stormmanifest as s_stormmanifest

desc = '''
Lint Storm code.

Each path is a file, a directory which is searched recursively for *.storm files, or - to read stdin.

Each --manifest is a stormcov manifest of Storm queries embedded in other source files, in the form
{"queries": [{"path": ..., "line": ..., "text": ..., "site": ...}]}, or when its path ends in .jsonl,
one {"path": ..., "line": ..., "text": ..., "site": ...} object per line. The path of each query's
host file is relative to the manifest's directory, line is the host line where the query text begins,
and each later line of text is on the next host line. The optional site is a label; when it ends with
:<line>:<col>, col is the 0-based column of the character before the query text, otherwise the text
starts at column 1. Findings are reported at their location in the host file.

Without --config, settings are read from the [tool.stormlint] table of the nearest pyproject.toml
which has one, searching upward from the current directory.

With --format json, each finding or file error is printed as one JSON object per line.

Exit codes: 0 when clean, 1 when there are findings, 2 on a usage, config or file error.
'''

def _loadToml(path):

    try:
        with open(path, 'rb') as fd:
            return tomllib.load(fd)

    except (OSError, tomllib.TOMLDecodeError) as e:
        raise s_exc.BadConfValu(mesg=f'{path}: {e}') from None

def _loadConf(path):
    '''
    Return (conf, confdir) from a pyproject.toml, or the nearest one with a [tool.stormlint] table.
    '''
    if path is not None:
        info = _loadToml(path)
        conf = info.get('tool', {}).get('stormlint', {})
        return _checkConf(path, conf), os.path.dirname(os.path.abspath(path))

    dirn = os.getcwd()
    while True:

        fpath = os.path.join(dirn, 'pyproject.toml')
        if os.path.isfile(fpath):

            conf = _loadToml(fpath).get('tool', {}).get('stormlint')
            if conf is not None:
                return _checkConf(fpath, conf), dirn

        parent = os.path.dirname(dirn)
        if parent == dirn:
            return {}, None

        dirn = parent

def _checkConf(path, conf):

    try:
        return s_schemas.reqValidStormLintConf(conf)
    except s_exc.SchemaViolation as e:
        raise s_exc.BadConfValu(mesg=f'{path}: [tool.stormlint] {e.get("mesg")}') from None

def _isExcluded(path, confdir, globs):

    if not globs:
        return False

    relp = os.path.relpath(os.path.abspath(path), confdir)
    while relp and relp != os.curdir:

        if any(fnmatch.fnmatchcase(relp, g) for g in globs):
            return True

        relp = os.path.dirname(relp)

    return False

def _getPaths(paths, confdir, globs):
    '''
    Yield each file to lint, skipping excluded files.
    '''
    for path in paths:

        if path == '-':
            yield path
            continue

        if _isExcluded(path, confdir, globs):
            continue

        if not os.path.isdir(path):
            yield path
            continue

        for root, dirs, files in os.walk(path):

            dirs[:] = sorted(d for d in dirs if not _isExcluded(os.path.join(root, d), confdir, globs))

            for name in sorted(files):

                if not name.endswith('.storm'):
                    continue

                fpath = os.path.join(root, name)
                if not _isExcluded(fpath, confdir, globs):
                    yield fpath

def _readText(path):

    if path == '-':
        return sys.stdin.read()

    with open(path, 'r', encoding='utf8') as fd:
        return fd.read()

# A file:line:col site gives the 0-based column of the character before the query text
SITE_COLUMN_RX = regex.compile(r':[0-9]+:([0-9]+)$')

def _loadManifest(path):
    '''
    Yield a (path, line, column, text) tuple for each query in a Storm query manifest.
    '''
    dirn = os.path.dirname(path)

    for query in s_stormmanifest.iterManifest(path):
        hostpath = os.path.normpath(os.path.join(dirn, query['path']))

        column = 0
        match = SITE_COLUMN_RX.search(query.get('site', ''))
        if match is not None:
            column = int(match.group(1)) + 1

        yield hostpath, query['line'], column, query['text']

def _printError(outp, asjson, path, mesg):
    '''
    Print an error for a file which could not be read or parsed, as text or a JSON line.
    '''
    if asjson:
        outp.printf(s_json.dumps({'path': path, 'error': mesg}).decode())
    else:
        outp.printf(f'{path}: error: {mesg}')

def _printFinding(outp, asjson, path, line, column, f):
    '''
    Print a lint finding at its location, as text or a JSON line.
    '''
    if asjson:
        info = {'path': path, 'line': line, 'column': column, 'rule': f.rule, 'severity': f.severity,
                'mesg': f.mesg}
        outp.printf(s_json.dumps(info).decode())
    else:
        outp.printf(f'{path}:{line}:{column}: {f.rule} {f.mesg}')

def _showRules(outp):

    for line in s_stormlint.getRuleTable():
        outp.printf(line)

    return 0

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.lint', outp=outp, description=desc)
    pars.add_argument('paths', nargs='*', help='Files or directories to lint (use - for stdin).')
    pars.add_argument('--select', type=s_stormlint.splitRules,
                      help='Comma-separated rule IDs or prefixes to run in place of the default rules.')
    pars.add_argument('--ignore', type=s_stormlint.splitRules, help='Comma-separated rule IDs or prefixes to disable.')
    pars.add_argument('--enable', type=s_stormlint.splitRules,
                      help='Comma-separated rule IDs or prefixes to add to the selected rules, '
                           'such as rules which are off by default.')
    pars.add_argument('--manifest', default=[], action='append',
                      help='A JSON or JSONL manifest of embedded Storm queries to lint (may be specified multiple times).')
    pars.add_argument('--config', help='Path to a pyproject.toml with a [tool.stormlint] table.')
    pars.add_argument('--format', default='text', choices=('text', 'json'),
                      help='Print findings as text, or as one JSON object per line.')
    pars.add_argument('--show-rules', action='store_true', help='Print the lint rules and exit.')

    opts = pars.parse_args(argv)

    if opts.show_rules:
        return _showRules(outp)

    if not opts.paths and not opts.manifest:
        pars.error('at least one path or --manifest is required.')

    try:
        conf, confdir = _loadConf(opts.config)
    except s_exc.BadConfValu as e:
        outp.printf(f'error: {e.get("mesg")}')
        return 2

    select = opts.select
    if select is None:
        select = conf.get('select')

    ignore = opts.ignore
    if ignore is None:
        ignore = conf.get('ignore', ())

    enable = opts.enable
    if enable is None:
        enable = conf.get('enable', ())

    try:
        linter = s_stormlint.StormLinter(select=select, ignore=ignore, enable=enable)
    except s_exc.BadArg as e:
        outp.printf(f'error: {e.get("mesg")}')
        return 2

    globs = [os.path.normpath(g) for g in conf.get('exclude', ())]
    asjson = opts.format == 'json'

    count = 0
    failed = False
    seen = set()

    for path in _getPaths(opts.paths, confdir, globs):

        if path in seen:
            continue

        seen.add(path)

        try:
            text = _readText(path)
        except (OSError, UnicodeDecodeError) as e:
            failed = True
            _printError(outp, asjson, path, str(e))
            continue

        for f in linter.lint(text):
            count += 1
            _printFinding(outp, asjson, path, f.line, f.column, f)

    for mpath in opts.manifest:

        try:
            for path, line, column, text in _loadManifest(mpath):

                if _isExcluded(path, confdir, globs):
                    continue

                for f in linter.lint(text):
                    count += 1
                    fcol = f.column + column if f.line == 1 else f.column
                    _printFinding(outp, asjson, path, line + f.line - 1, fcol, f)

        except s_exc.BadArg as e:
            failed = True
            _printError(outp, asjson, mpath, e.get('mesg'))

    if not asjson and (count or not failed):
        outp.printf(s_stormlint.getSummary(count))

    if failed:
        return 2

    if count:
        return 1

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
