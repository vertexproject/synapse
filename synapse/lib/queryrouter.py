'''
Storm query classifier for read/write routing.

The regex-based classification approach is used because Storm's grammar makes
static analysis expensive. Rather than parsing the full AST for every query,
we use targeted regexes that match the known write patterns:

1. Edit bracket syntax ``[ form=valu ]`` — the primary node-creation syntax.
   The negative lookbehind avoids false positives from variable indexing ($x[0]).
2. Pipe-to-command syntax ``| delnode``, ``| merge``, etc. — all known mutating
   Storm commands are enumerated in _write_commands.
3. Method call patterns — ``$node.data.set()``, edge-add syntax ``->>`` etc.

This is intentionally conservative: unknown patterns default to 'read', and
the worker will fall back to write-forwarding if an IsReadOnly error surfaces.
'''
import re

_write_commands = frozenset((
    'auth.user.add', 'auth.user.del', 'auth.role.add', 'auth.role.del',
    'auth.user.grant', 'auth.user.revoke', 'auth.user.addrule', 'auth.user.delrule',
    'auth.role.addrule', 'auth.role.delrule',
    'cron.add', 'cron.del', 'cron.mod', 'cron.move', 'cron.enable', 'cron.disable',
    'cron.cleanup',
    'delnode',
    'dmon.add', 'dmon.del',
    'feed.ingest',
    'graph.add', 'graph.del',
    'layer.add', 'layer.del', 'layer.set', 'layer.pull.add', 'layer.push.add',
    'macro.set', 'macro.del',
    'merge',
    'model.edge.set', 'model.edge.del',
    'model.depr.lock', 'model.depr.unlock',
    'movetag',
    'pkg.load', 'pkg.del',
    'queue.add', 'queue.del',
    'service.add', 'service.del',
    'trigger.add', 'trigger.del', 'trigger.mod', 'trigger.enable', 'trigger.disable',
    'view.add', 'view.del', 'view.set', 'view.merge',
))

# Must not match variable indexing like $x[0] or $lib.list()[0]
_re_edit_bracket = re.compile(r'(?<![a-zA-Z0-9_\)\]])\[')

_re_write_cmd = re.compile(
    r'\|\s*(' + '|'.join(re.escape(c) for c in sorted(_write_commands, key=len, reverse=True)) + r')\b'
)

_re_write_patterns = re.compile(
    r'\$node\.data\.set\b'
    r'|\$node\.data\.pop\b'
    r'|\$lib\.queue\.\w+\.put\b'
    r'|->>\s*\w+'
)


def classify(text):
    '''
    Classify a Storm query as 'read' or 'write'.

    Returns:
        str: 'read' or 'write'
    '''
    stripped = _strip_comments(text)

    if _re_edit_bracket.search(stripped):
        return 'write'

    if _re_write_cmd.search(stripped):
        return 'write'

    if _re_write_patterns.search(stripped):
        return 'write'

    return 'read'


def _strip_comments(text):
    '''Remove // line comments from Storm text.'''
    return re.sub(r'//[^\n]*', '', text)
