import os
import sys
import fnmatch
import tomllib
import argparse

import synapse.exc as s_exc

import synapse.lib.cmd as s_cmd
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.schemas as s_schemas
import synapse.lib.stormlint as s_stormlint

desc = '''
Lint Storm code.

Each path is a file, a directory which is searched recursively for *.storm files, or - to read stdin.

Without --config, settings are read from the [tool.stormlint] table of the nearest pyproject.toml
which has one, searching upward from the current directory.

With --format json, each finding or file error is printed as one JSON object per line.

With --v3-ready, the rules which report Storm that must change for Synapse 3.x are added to the
selected rules. Data model renames and removals are reported as info findings.

Exit codes: 0 when clean or when there are only info findings, 1 when there are other findings,
2 on a usage, config or file error.
'''

def _loadToml(path):

    try:
        with open(path, 'rb') as fd:
            return tomllib.load(fd)

    except (OSError, tomllib.TOMLDecodeError) as e:
        raise s_exc.BadConfValu(mesg=f'{path}: {e}') from None

def _getToolConf(info):

    if (tool := info.get('tool')) is None:
        return None

    return tool.get('stormlint')

def _loadConf(path):
    '''
    Return (conf, confdir) from a pyproject.toml, or the nearest one with a [tool.stormlint] table.
    '''
    if path is not None:
        conf = _getToolConf(_loadToml(path))
        if conf is None:
            conf = {}

        return _checkConf(path, conf), os.path.dirname(os.path.abspath(path))

    dirn = os.getcwd()
    while True:

        fpath = os.path.join(dirn, 'pyproject.toml')
        if os.path.isfile(fpath):

            conf = _getToolConf(_loadToml(fpath))
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

def _splitRulesString(valu):
    return [v.strip() for v in valu.split(',') if v.strip()]

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

def _showRules(outp):

    rows = [('ID', 'SEVERITY', 'DEFAULT', 'NAME', 'DESCRIPTION')]
    for r in s_stormlint.rules.values():
        doc = r.doc.split('\n', 1)[0]
        if r.v3:
            default = 'v3'
        else:
            default = 'yes' if r.default else 'no'

        rows.append((r.iden, r.severity, default, r.name, doc))

    sizes = [max(len(row[i]) for row in rows) for i in range(4)]
    for row in rows:
        cols = [valu.ljust(size) for valu, size in zip(row, sizes)]
        outp.printf('  '.join(cols + [row[4]]).rstrip())

    return 0

async def main(argv, outp=s_output.stdout):

    pars = s_cmd.Parser(prog='synapse.tools.storm.lint', outp=outp, description=desc)
    pars.add_argument('paths', nargs='*', help='Files or directories to lint (use - for stdin).')
    pars.add_argument('--select', type=_splitRulesString,
                      help='Comma-separated rule IDs or prefixes to run in place of the default rules.')
    pars.add_argument('--ignore', type=_splitRulesString, help='Comma-separated rule IDs or prefixes to disable.')
    pars.add_argument('--enable', type=_splitRulesString,
                      help='Comma-separated rule IDs or prefixes to add to the selected rules, '
                           'such as rules which are off by default.')
    pars.add_argument('--v3-ready', action=argparse.BooleanOptionalAction, default=None,
                      help='Add the rules which report Storm that must change for Synapse 3.x.')
    pars.add_argument('--config', help='Path to a pyproject.toml with a [tool.stormlint] table.')
    pars.add_argument('--format', default='text', choices=('text', 'json'),
                      help='Print findings as text, or as one JSON object per line.')
    pars.add_argument('--show-rules', action='store_true', help='Print the lint rules and exit.')

    try:
        opts = pars.parse_args(argv)

        if opts.show_rules:
            return _showRules(outp)

        if not opts.paths:
            pars.error('at least one path is required.')

    except s_exc.ParserExit as e:
        return e.get('status')

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

    v3ready = opts.v3_ready
    if v3ready is None:
        v3ready = conf.get('v3_ready', False)

    try:
        linter = s_stormlint.StormLinter(select=select, ignore=ignore, enable=enable, v3ready=v3ready)
    except s_exc.BadArg as e:
        outp.printf(f'error: {e.get("mesg")}')
        return 2

    globs = [os.path.normpath(g) for g in conf.get('exclude', ())]
    asjson = opts.format == 'json'

    count = 0
    infos = 0
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
            if asjson:
                outp.printf(s_json.dumps({'path': path, 'error': str(e)}).decode())
            else:
                outp.printf(f'{path}: error: {e}')

            continue

        for f in linter.lint(text):

            isinfo = f.severity == 'info'
            if isinfo:
                infos += 1
            else:
                count += 1

            if asjson:
                info = {'path': path, 'line': f.line, 'column': f.column, 'rule': f.rule,
                        'severity': f.severity, 'mesg': f.mesg}
                outp.printf(s_json.dumps(info).decode())
            elif isinfo:
                outp.printf(f'{path}:{f.line}:{f.column}: {f.rule} (info) {f.mesg}')
            else:
                outp.printf(f'{path}:{f.line}:{f.column}: {f.rule} {f.mesg}')

    if not asjson:

        noun = 'error' if count == 1 else 'errors'
        if infos:
            infonoun = 'info finding' if infos == 1 else 'info findings'
            outp.printf(f'Found {count} {noun} and {infos} {infonoun}.')

        elif count:
            outp.printf(f'Found {count} {noun}.')

        elif not failed:
            outp.printf('All checks passed!')

    if failed:
        return 2

    if count:
        return 1

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
