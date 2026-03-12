import re
import sys

import synapse.lib.cmd as s_cmd
import synapse.lib.json as s_json
import synapse.lib.output as s_output

def _parsesrc(srcspec):
    '''
    Parse a source file/line spec like "synapse/common.py:130,139-140" into
    (path, frozenset_of_lines).  If no line spec is given, lines is None
    (meaning all lines in the file).
    '''
    parts = srcspec.split(':', 1)
    path = parts[0]

    if len(parts) == 1 or not parts[1]:
        return (path, None)

    lines = set()
    for part in parts[1].split(','):
        part = part.strip()
        if '-' in part:
            lo, hi = part.split('-', 1)
            lines.update(range(int(lo), int(hi) + 1))
        else:
            lines.add(int(part))

    return (path, frozenset(lines))

def _parsediff(text):
    '''
    Parse unified diff text (e.g. from "git diff") and return a dict mapping
    each modified file path to the frozenset of new-side line numbers that were
    added or changed.
    '''
    result = {}
    curfile = None
    newline = 0

    for line in text.splitlines():
        if line.startswith('+++ '):
            rest = line[4:]
            if rest.startswith('b/'):
                curfile = rest[2:]
                result.setdefault(curfile, set())
            else:
                curfile = None

        elif line.startswith('@@ ') and curfile is not None:
            m = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            if m is not None:
                newline = int(m.group(1)) - 1

        elif curfile is not None:
            if line.startswith('++') or line.startswith('--'):
                # Skip the "--- a/...\" / \"+++ b/...\" header lines already handled above,
                # and any \"+++\" lines that are part of diff output but not content.
                pass
            elif line.startswith('+'):
                newline += 1
                result[curfile].add(newline)
            elif line.startswith('-'):
                pass  # removed line, no new-side line number
            elif line.startswith('\\'):
                pass  # "No newline at end of file" marker
            else:
                newline += 1  # context line

    return {k: frozenset(v) for k, v in result.items() if v}

def _buildrevmap(covmap):
    '''
    Build a reverse lookup map {path: {line: [nodeid, ...]}} from the
    forward coverage map {nodeid: {path: [lines]}}.
    '''
    revmap = {}
    for nodeid, filemap in covmap.items():
        for path, lines in filemap.items():
            pathmap = revmap.setdefault(path, {})
            for ln in lines:
                pathmap.setdefault(ln, []).append(nodeid)

    return revmap

def _querytests(revmap, queries):
    '''
    Given a list of (path, lines_or_None) queries, return a sorted list of
    unique test node IDs that cover any of the queried file/line positions.
    '''
    seen = set()
    testids = []

    for path, lines in queries:
        pathmap = revmap.get(path, {})

        if lines is None:
            linekeys = sorted(pathmap)
        else:
            linekeys = sorted(lines)

        for ln in linekeys:
            for nodeid in pathmap.get(ln, []):
                if nodeid not in seen:
                    seen.add(nodeid)
                    testids.append(nodeid)

    return sorted(testids)

async def main(argv, outp=s_output.stdout):
    pars = s_cmd.Parser(prog='python -m synapse.utils.testcov.show', outp=outp,
                        description='Show per-test source coverage from a testcov JSON file.')

    pars.add_argument('covfile', help='Path to testcov JSON output file.')
    pars.add_argument('srcs', nargs='*', metavar='FILE[:LINES]',
                      help='Source file and optional line spec (e.g. synapse/common.py:130,139-140). '
                           'If omitted and stdin is not a TTY, reads "git diff" output from stdin.')

    opts = pars.parse_args(argv)

    with open(opts.covfile, 'rb') as fp:
        covmap = s_json.load(fp)

    queries = []

    if opts.srcs:
        for srcspec in opts.srcs:
            queries.append(_parsesrc(srcspec))
    else:
        if sys.stdin.isatty():
            outp.printf(pars.format_help())
            return 0
        difftext = sys.stdin.read()
        for path, lines in sorted(_parsediff(difftext).items()):
            queries.append((path, lines))

    revmap = _buildrevmap(covmap)
    for nodeid in _querytests(revmap, queries):
        outp.printf(nodeid)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
