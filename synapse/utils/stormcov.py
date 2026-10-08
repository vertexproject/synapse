'''
Storm coverage for pytest and coverage.py.

Storm files (`.storm`) are measured directly. Storm embedded in other file types is measured
as well, for the extensions in `--storm-embed-exts` (an empty value disables it):

* `.yaml` / `.yml`: string values stored under any key in `--storm-yaml-keys`.
* `.py`: string literals assigned to a name in `--storm-py-keys`, or stored under such a key in a dict literal.

Embedded Storm is attributed to the real host file and line numbers. Only literals whose
text maps one-to-one onto host lines are measured: Python string literals which use
escaped newlines or implicit concatenation, and YAML folded or multi-line flow scalars, are skipped.

A query which ran is matched back to its source by its parse tree, since the Cortex only sees the
text. Identical text in more than one place is credited to every one of those places when any of
them runs.

Python files already carry Python line coverage, and coverage.py allows only one file tracer
per file, so `coverage combine` refuses to merge that data with the Storm line coverage of the same
file ("Conflicting file tracer name"). Storm hits inside embedded files are therefore written to their own
data file (`--stormcov-data`) and are reported from it:

    python -m coverage report --data-file=.stormcov-embed

The keys used when reporting come from the `[synapse.utils.stormcov]` coverage plugin options
`py_keys` and `yaml_keys` and must match the pytest options used when collecting.
'''
import os
import ast
import sys
import glob
import logging
import pathlib
import itertools
import collections

import lark
import yaml
import regex
import pytest
import coverage

from coverage.data import combine_parallel_data
from coverage.exceptions import NoSource

import synapse.data as s_data
import synapse.common as s_common

logger = logging.getLogger(__name__)

PACKAGE_DIR = pathlib.Path('packages').absolute()

PLUGIN_NAME = 'synapse.utils.stormcov.StormReporterPlugin'

# Host file extensions which may embed Storm, and the kind of host each one is.
EMBED_KINDS = {'py': 'py', 'yaml': 'yaml', 'yml': 'yaml'}

DEFAULT_EMBED_EXTS = ('py', 'yaml', 'yml')
DEFAULT_PY_KEYS = ('_storm_query', 'storm')
DEFAULT_YAML_KEYS = ('storm', 'query', 'onload')
DEFAULT_DATA = '.stormcov-embed'

def pytest_addoption(parser): # pragma: no cover
    # NB: no coverage since this is a pytest hook
    """Add options to control storm coverage."""

    group = parser.getgroup('stormcov', 'storm coverage reporting')

    group.addoption(
        '--stormcov',
        action='store_true',
        default=False,
        dest='stormcov',
        help='Enable stormcov. Default: False',
    )

    group.addoption(
        '--storm-dirs',
        action='store',
        dest='stormdirs',
        help='Comma separated list of paths to search for Storm files. Default: autodiscover stormdirs based on executed tests.',
    )

    group.addoption(
        '--storm-exts',
        action='store',
        default='storm',
        dest='stormexts',
        help='Comma separated list of file extensions containing Storm. Default: storm',
    )

    group.addoption(
        '--storm-embed-exts',
        action='store',
        default=','.join(DEFAULT_EMBED_EXTS),
        dest='stormembedexts',
        help=f'Comma separated list of host file extensions (py, yaml, yml) to search for embedded Storm. Empty disables it. Default: {",".join(DEFAULT_EMBED_EXTS)}',
    )

    group.addoption(
        '--storm-py-keys',
        action='store',
        default=','.join(DEFAULT_PY_KEYS),
        dest='stormpykeys',
        help=f'Comma separated list of Python names and dict keys whose string values are Storm. Default: {",".join(DEFAULT_PY_KEYS)}',
    )

    group.addoption(
        '--storm-yaml-keys',
        action='store',
        default=','.join(DEFAULT_YAML_KEYS),
        dest='stormyamlkeys',
        help=f'Comma separated list of YAML keys whose string values are Storm. Default: {",".join(DEFAULT_YAML_KEYS)}',
    )

    group.addoption(
        '--stormcov-data',
        action='store',
        default=DEFAULT_DATA,
        dest='stormcov_data',
        help=f'Coverage data file for Storm embedded in other files. Default: {DEFAULT_DATA}',
    )

    group.addoption(
        '--stormcov-append',
        action='store_true',
        default=False,
        dest='stormcov_append',
        help='Append to existing coverage reports instead of erasing.',
    )

    group.addoption(
        '--stormcov-basedir',
        default=PACKAGE_DIR,
        type=pathlib.Path,
        help='The base package directory. Useful for monorepo environments.',
    )

    group.addoption(
        '--stormcov-branch',
        default=False,
        action='store_true',
        dest='stormcov_branch',
        help='Enable branch coverage for storm files. Enabled automatically if pytest-cov branch tracking is enabled.',
    )

DISABLE = sys.monitoring.DISABLE

def pytest_configure(config): # pragma: no cover
    # NB: no coverage since this is a pytest hook
    if not config.option.stormcov and not (config.option.stormdirs or config.option.stormcov_append):
        return

    config.pluginmanager.register(StormcovPlugin(config), 'stormcov')

def getParser():
    '''
    Build the Storm grammar parser.

    Notes:
        Building the LALR tables costs about two seconds per process, but do NOT try to
        cache it through lark.Lark.save()/load(): a built parser yields trees whose
        data is a Token('RULE', ...) while a deserialized one yields a str, so
        str(tree) -- which is what findStormFiles() and handleAst() hash to identify
        a query -- differs between a built parser and a loaded one. Coverage would
        then attribute nothing at all, silently, since no runtime query would hash to
        a guid in guid_map.
    '''
    grammar = s_data.getLark('storm')
    return lark.Lark(grammar, start='query', regex=True, parser='lalr', keep_all_tokens=True,
                            maybe_placeholders=False, propagate_positions=True)

def splitKeys(text):
    return frozenset(k.strip() for k in text.split(',') if k.strip())

def _pyKeyName(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

def _getPyStorm(path, keys):
    with open(path, 'r') as fd:
        text = fd.read()

    # A file which is not valid python cannot be located by line, so it is skipped
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        logger.warning('Skipping unparsable python file: %s', path)
        return

    # Collect the value node of every assignment or dict entry which is named by a key
    pairs = []
    for node in ast.walk(tree):

        # `name = ...` and `self.name = ...`
        if isinstance(node, ast.Assign):
            if any(_pyKeyName(t) in keys for t in node.targets):
                pairs.append(node.value)

        # `name: type = ...`, where a bare annotation has no value
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None and _pyKeyName(node.target) in keys:
                pairs.append(node.value)

        # `{'name': ...}`. A `**spread` entry has a None key.
        elif isinstance(node, ast.Dict):
            for knode, vnode in zip(node.keys, node.values):
                if isinstance(knode, ast.Constant) and knode.value in keys:
                    pairs.append(vnode)

    # ast.walk is breadth first, so restore source order
    for vnode in sorted(pairs, key=lambda n: n.lineno):

        # Only a plain string literal can be mapped back onto the host file
        if not isinstance(vnode, ast.Constant) or not isinstance(vnode.value, str):
            continue

        # The literal only maps onto host lines if every newline in its value is a physical newline.
        if vnode.end_lineno - vnode.lineno != vnode.value.count('\n'):
            continue

        yield vnode.value, vnode.lineno - 1

def _getYamlStorm(path, keys):
    with open(path, 'r') as fd:
        text = fd.read()

    # compose_all keeps the node positions which safe_load would throw away. A file
    # which is not valid yaml cannot be located by line, so it is skipped.
    try:
        roots = list(yaml.compose_all(text, Loader=yaml.CSafeLoader))
    except yaml.YAMLError:
        logger.warning('Skipping unparsable yaml file: %s', path)
        return

    found = []
    seen = set()
    todo = list(roots)
    while todo:
        node = todo.pop()

        # Aliases share one node, so track what has been visited to avoid cycles and repeats
        if node in seen:
            continue

        seen.add(node)

        # Descend through sequences to reach the mappings inside them
        if isinstance(node, yaml.SequenceNode):
            todo.extend(node.value)
            continue

        if not isinstance(node, yaml.MappingNode):
            continue

        for knode, vnode in node.value:

            # Every value is searched, whether or not its key matched
            todo.append(vnode)

            if not isinstance(knode, yaml.ScalarNode) or knode.value not in keys:
                continue

            # Only a string scalar can hold Storm. Bare `true`, `null` or an empty value
            # (`query:`) are resolved by yaml to a bool or null, but would parse as Storm.
            if not isinstance(vnode, yaml.ScalarNode) or vnode.tag != 'tag:yaml.org,2002:str':
                continue

            if vnode.style == '|':
                # Block scalar content starts on the line after the indicator
                found.append((vnode.start_mark.line + 1, vnode.value))
                continue

            # NB: the C loader reports a plain scalar style as an empty string
            if vnode.style in (None, '', "'", '"'):
                # Only single line scalars map onto a host line
                if vnode.start_mark.line == vnode.end_mark.line and '\n' not in vnode.value:
                    found.append((vnode.start_mark.line, vnode.value))

    for offs, text in sorted(found):
        yield text, offs

def getEmbeddedStorm(path, pykeys, yamlkeys):
    '''
    Yield (text, offs) for each Storm string embedded in a py or yaml host file.

    The line of the host file which holds line N of the text is N + offs.
    '''
    kind = EMBED_KINDS.get(os.path.splitext(path)[1][1:].lower())

    if kind == 'py':
        genr = _getPyStorm(path, pykeys)
    elif kind == 'yaml':
        genr = _getYamlStorm(path, yamlkeys)
    else:
        return

    for text, offs in genr:
        if text.strip():
            yield text, offs

class StormcovPlugin:

    PARSE_METHODS = {'compute', 'once', 'lift', 'getPivsOut', 'getPivsIn'}

    def __init__(self, config):
        # toolid=4 is not defined in sys.monitoring so there's less of a chance
        # that we interfere with another tool, namely coveragepy.
        self.toolid = 4
        self._prevcb = None
        self._freetool = False

        self.isworker = os.environ.get("PYTEST_XDIST_WORKER") is not None

        # xdist detection logic from here:
        # https://github.com/pytest-dev/pytest-cov/blob/be3366838e41a9cbefa714636a39c5c2f6d5f588/src/pytest_cov/plugin.py#L235C19-L235C139
        self.iscontroller = (
            getattr(config.option, 'numprocesses', False) or
            getattr(config.option, 'distload', False) or
            getattr(config.option, 'dist', 'no') != 'no'
        ) and not self.isworker

        self.config = config
        self.handlers = {
            'ast.py': self.handleAst,
            'view.py': self.handleView,
            'stormctrl.py': self.handleStormctrl,
        }

        self.text_map = {}
        self.nodeids = itertools.count()
        self.guid_map = {}
        self.embed_map = {}
        self.embed_hosts = set()
        self.subq_map = {}
        self._handler_cache = {}
        self.lines_hit = collections.defaultdict(set)
        self.arcs_hit = collections.defaultdict(set)
        self.prev_line = {}
        self.prev_nodeid = {}

        self.freg = regex.compile(r'.*synapse/lib/(ast.py|view.py|stormctrl.py)$')

        self.parser = getParser()

        opts = config.option

        self.append = config.option.stormcov_append
        self.stormdirs = config.option.stormdirs
        self.basedir = config.option.stormcov_basedir
        self.stormbranch = config.option.stormcov_branch
        self.extensions = [e.strip() for e in opts.stormexts.split(',')]

        self.embedexts = [e.lower() for e in splitKeys(opts.stormembedexts) if e.lower() in EMBED_KINDS]
        self.pykeys = splitKeys(opts.stormpykeys)
        self.yamlkeys = splitKeys(opts.stormyamlkeys)
        self.datafile = opts.stormcov_data

        self.pycov = hasattr(config.option, 'no_cov') and not config.option.no_cov

    def reset(self):
        self.lines_hit = collections.defaultdict(set)
        self.arcs_hit = collections.defaultdict(set)
        self.prev_line = {}
        self.prev_nodeid = {}

    def findStormFiles(self, dirn):
        for path in self.findExecutableFiles(dirn):

            if os.path.splitext(path)[1][1:].lower() in self.embedexts:
                self.findEmbeddedStorm(path)
                continue

            with open(path, 'r') as f:
                apth = os.path.abspath(path)

                try:
                    tree = self.parser.parse(f.read())
                except lark.exceptions.UnexpectedToken:
                    logger.warning('Skipping invalid storm file: %s', apth)
                    continue

                self.findSubqueries(tree, apth)

                # Identical text in more than one file is credited to every one of them
                guid = s_common.guid(str(tree))
                paths = self.guid_map.setdefault(guid, [])
                if apth not in paths:
                    paths.append(apth)

    def findEmbeddedStorm(self, path):
        apth = os.path.abspath(path)

        for text, offs in getEmbeddedStorm(apth, self.pykeys, self.yamlkeys):
            try:
                tree = self.parser.parse(text)
            except lark.exceptions.LarkError:
                logger.debug('Skipping invalid embedded storm in %s at line %d', apth, offs + 1)
                continue

            self.embed_hosts.add(apth)
            self.findSubqueries(tree, apth, offs)

            # A YAML alias repeats a literal at the same location, so only distinct locations are kept
            locs = self.embed_map.setdefault(s_common.guid(str(tree)), [])
            if (apth, offs) not in locs:
                locs.append((apth, offs))

    def findExecutableFiles(self, src_dir):
        rx = r"^[^#~!$@%^&*()+=,]+\.(" + "|".join(self.extensions) + r")$"
        # Test files and the HTTP cassettes recorded by tests (whose `query` keys are request data) are not product code
        embedrx = r"^(?!test_|conftest\.)(?!.*\.vcr\.)[^#~!$@%^&*()+=,]+\.(" + "|".join(self.embedexts) + r")$"
        for (dirpath, dirnames, filenames) in os.walk(src_dir):
            for filename in filenames:
                if regex.search(rx, filename) or (self.embedexts and regex.search(embedrx, filename)):
                    path = os.path.join(dirpath, filename)
                    yield path

    def findSubqueries(self, tree, path, hostoffs=0):
        for rule in ('argvquery', 'embedquery'):
            for node in tree.find_data(rule):

                subq = node.children[1]
                if subq.meta.empty:
                    continue

                subg = s_common.guid(str(subq))

                line = node.meta.line - 1
                if rule == 'argvquery':
                    line = subq.meta.line - 1

                # (path, offset added to the runtime line, subquery line within its own text)
                entry = (path, line + hostoffs, line)
                entries = self.subq_map.setdefault(subg, [])
                if entry not in entries:
                    entries.append(entry)

    def _startSysmon(self):
        if sys.monitoring.get_tool(self.toolid) is None:
            sys.monitoring.use_tool_id(self.toolid, 'pytest-stormcov')
            self._freetool = True

        sys.monitoring.set_events(self.toolid, sys.monitoring.events.PY_START)
        self._prevcb = sys.monitoring.register_callback(self.toolid, sys.monitoring.events.PY_START, self.sysmonPyStart)

    def _stopSysmon(self):
        if self._prevcb: # pragma: no cover
            sys.monitoring.register_callback(self.toolid, sys.monitoring.events.PY_START, self._prevcb)
            return

        if self._freetool:
            sys.monitoring.free_tool_id(self.toolid)
            self._freetool = False

    @pytest.hookimpl(wrapper=True)
    def pytest_runtestloop(self, session): # pragma: no cover
        # NB: no coverage since this is a pytest hook

        self.cov = coverage.Coverage()

        if not self.append:
            self.cov.erase()

        self._startSysmon()
        yield
        self._stopSysmon()
        self.finalizeArcs()

        self.cov.load()

        data = self.cov.get_data()

        # Bail if there's no coverage. This could be because of a xdist worker
        # that didn't have any work
        if not self.lines_hit and not self.arcs_hit:
            return

        # Add our stormcov data based on coverage mode
        usearcs = (self.pycov and self.cov.config.branch) or (not self.pycov and self.stormbranch)
        hits = self.arcs_hit if usearcs else self.lines_hit

        self.saveHits(data, hits, usearcs)

    def saveHits(self, data, hits, usearcs):
        mainhits = {fn: valu for fn, valu in hits.items() if not self.isEmbedHost(fn)}
        embedhits = {fn: valu for fn, valu in hits.items() if self.isEmbedHost(fn)}

        # The discovered files are registered even when the hits are all in the other
        # kind, so the ones which never ran report at 0% rather than dropping out.
        self.addHits(data, mainhits, usearcs, [path for paths in self.guid_map.values() for path in paths])
        data.write()

        if embedhits or self.embed_hosts:
            # Python files already carry Python coverage, so the hits in embedded files get their own data file.
            embeddata = coverage.CoverageData(basename=self.datafile, suffix=True)
            self.addHits(embeddata, embedhits, usearcs, self.embed_hosts)
            embeddata.write()
            embeddata.close()

    def isEmbedHost(self, path):
        return os.path.splitext(path)[1][1:].lower() in EMBED_KINDS

    def addHits(self, data, hits, usearcs, files):
        if usearcs:
            data.add_arcs({fn: set(valu) for fn, valu in hits.items()})
        else:
            data.add_lines({fn: set(valu) for fn, valu in hits.items()})

        data.touch_files(files, PLUGIN_NAME)

    def pytest_sessionstart(self, session): # pragma: no cover
        # NB: no coverage since this is a pytest hook
        if not self.embedexts or self.isworker or self.append:
            return

        coverage.CoverageData(basename=self.datafile).erase(parallel=True)

    def pytest_sessionfinish(self, session, exitstatus): # pragma: no cover
        # NB: no coverage since this is a pytest hook
        if self.isworker:
            return

        self.combineEmbedData()

    def combineEmbedData(self):
        '''
        Combine the per process embedded Storm data files into one.
        '''
        if not glob.glob(f'{self.datafile}.*'):
            return

        combine_parallel_data(coverage.CoverageData(basename=self.datafile))

    def discoverStormdirs(self, testpaths: list[pathlib.Path]):
        # If a specific set of directories were specified, use that
        if self.stormdirs:
            for dirn in self.stormdirs.split(','):
                self.findStormFiles(dirn)
            return

        stormdirs = set()

        # Iterate through the tests, get their path, and add the containing storm package directory
        for testpath in testpaths:
            if testpath.is_relative_to(self.basedir):
                stormdir = str(self.basedir / testpath.relative_to(self.basedir).parts[0])
                stormdirs.add(stormdir)

        for dirn in stormdirs:
            self.findStormFiles(dirn)

    @pytest.hookimpl(wrapper=True)
    def pytest_collection_modifyitems(self, config, items): # pragma: no cover
        # NB: no coverage since this is a pytest hook
        # Note: If using xdist, this function executes on each worker node
        testpaths = [item.path for item in items]
        self.discoverStormdirs(testpaths)
        yield

    @pytest.hookimpl(wrapper=True)
    def pytest_xdist_node_collection_finished(self, node, ids): # pragma: no cover
        # NB: no coverage since this is a pytest hook
        # Note: This hook allows the xdist controller to get a list of test ids so we can build a list of storm dirs to present stormterm coverage
        testpaths = [pathlib.Path(testid.split('::')[0]).absolute() for testid in ids]
        self.discoverStormdirs(testpaths)
        yield

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config): # pragma: no cover
        # NB: no coverage since this is a pytest hook
        if self.isworker:
            return

        if not self.iscontroller and not self.lines_hit and not self.arcs_hit:
            return

        try:
            self.cov.report(skip_covered=False, skip_empty=False, include=[f'*.{ext}' for ext in self.extensions])
        except coverage.exceptions.NoDataError:
            logger.warning('No storm coverage data was found.')

        if self.embedexts and os.path.exists(self.datafile):
            embedcov = coverage.Coverage(data_file=self.datafile)
            embedcov.load()

            try:
                embedcov.report(skip_covered=False, skip_empty=False, include=sorted(self.embed_hosts))
            except coverage.exceptions.NoDataError:
                logger.warning('No embedded storm coverage data was found.')

    def sysmonPyStart(self, code, instruction_offset): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback

        # Cache the code -> handler dispatch so the filename regex only runs the first
        # time we see a given code object.  Non-matching locations return DISABLE and
        # never recur, so they are not worth caching.
        handler = self._handler_cache.get(code)
        if handler is None:
            match = self.freg.match(code.co_filename)
            if match is None:
                return DISABLE

            handler = self.handlers[match.group(1)]
            self._handler_cache[code] = handler

        return handler(code)

    def handleAst(self, code, frame=None): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback

        # Resolve the frame containing the AST node ('self') and optional 'runt' local.
        # handleView/handleStormctrl pass frame directly; otherwise derive it from the
        # call stack based on which Storm method is executing.
        if frame is None:
            if code.co_name == 'pullgenr':
                # pullgenr is a generator trampoline; walk up two frames to reach the
                # caller, then verify it was called from execStormCmd before walking up
                # two more frames to reach the actual command runtime frame.
                frame = sys._getframe(2)

                if frame.f_back.f_code.co_name != 'execStormCmd':
                    return

                frame = frame.f_back.f_back

            elif code.co_name not in self.PARSE_METHODS:
                return DISABLE

            else:
                frame = sys._getframe(2)

        novalu = s_common.novalu

        flocals = frame.f_locals
        realnode = flocals.get('self')

        # Read storm_origin off the executing sub-runtime so that identical subquery
        # text at different lexical positions can be attributed to different file
        # offsets without modifying the shared cached Query object.  storm_origin is
        # None for top-level queries and for any node not executing inside a tee/subq.
        # When it is set we must skip the _coverage_root/_coverage_info cache because the
        # same node object may be re-used at multiple call sites.
        runt_from_frame = flocals.get('runt')
        runt_origin = getattr(runt_from_frame, 'storm_origin', None)

        if runt_origin is None and (cached := getattr(realnode, '_coverage_info', novalu)) is not novalu:
            # Fast path: re-use the attribution cached on the node from a prior call.
            if cached is not None:
                info, nodeid = cached
                self.markLines(realnode, info, nodeid=nodeid)
            return

        # Walk up to the root Query node so all AST nodes in a query share one nodeid.
        node = realnode
        while (parent := getattr(node, 'parent', None)) is not None:
            node = parent

        # Cache state lives on the root node rather than keyed by id(), which is reused once
        # a query is garbage collected and would hand a stale attribution to an unrelated query.
        nodeid = getattr(node, '_coverage_nodeid', None)
        if nodeid is None:
            nodeid = node._coverage_nodeid = next(self.nodeids)

        # A None entry means a previous call already determined this root has no
        # matching storm source; a real entry is a direct cache hit.
        if runt_origin is None:
            info = getattr(node, '_coverage_root', novalu)
            if info is not novalu:
                if info is None:
                    self._cacheMiss(realnode, node, nodeid, runt_origin)
                else:
                    self._cacheHit(realnode, node, nodeid, info, runt_origin)
                return

        # Only Query nodes carry the storm source text we need to look up.
        if node.__class__.__name__ != 'Query':
            self._cacheMiss(realnode, node, nodeid, runt_origin)
            return

        # When runt_origin is set, use its source line as a hint to disambiguate
        # duplicate subquery text that appears at different positions in the file.
        offs_hint = runt_origin.sline - 1 if runt_origin is not None else None

        # text_map is keyed by (query_text, offs_hint) and avoids re-parsing the same
        # text/position pair on every AST node in a query.
        text_key = (node.text, offs_hint)
        info = self.text_map.get(text_key, novalu)
        if info is not novalu:
            self._cacheHit(realnode, node, nodeid, info, runt_origin)
            return

        # First time seeing this query text: parse it, hash the tree, and look up
        # the matching storm source file via subq_map (position-aware) or guid_map.
        tree = self.parser.parse(node.text)
        guid = s_common.guid(str(tree))

        # Identical text can not be told apart at runtime, so every place it appears is
        # credited. A subquery with a known source line is only credited at that line.
        locs = []

        subqs = self.subq_map.get(guid)
        if subqs is not None:
            matched = [(p, o) for p, o, r in subqs if r == offs_hint]
            locs.extend(matched or [(p, o) for p, o, r in subqs])

        locs.extend((path, 0) for path in self.guid_map.get(guid, ()))
        locs.extend(self.embed_map.get(guid, ()))

        if not locs:
            # No storm source file found for this query; record a dead-end.
            self._cacheMiss(realnode, node, nodeid, runt_origin)
            return

        info = tuple(dict.fromkeys(locs))
        self.text_map[text_key] = info
        self._cacheHit(realnode, node, nodeid, info, runt_origin)

    def _cacheMiss(self, realnode, rootnode, nodeid, runt_origin): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        # Record a dead-end (node maps to no storm source). Only cache when there is
        # no runt_origin, since origin-based attribution is position specific.
        if runt_origin is None:
            rootnode._coverage_root = None
            realnode._coverage_info = None

    def _cacheHit(self, realnode, rootnode, nodeid, info, runt_origin): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        if runt_origin is None:
            rootnode._coverage_root = info
            realnode._coverage_info = (info, nodeid)

        self.markLines(realnode, info, nodeid=nodeid)

    def finalizeArcs(self):
        for (fname, offs), prev in self.prev_line.items():
            self.arcs_hit[fname].add((prev, -1))

    def markLines(self, astn, info, nodeid=None): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        astinfo = astn.astinfo
        strt = astinfo.sline
        if astinfo.isterm:
            fini = astinfo.eline
        else:
            fini = strt

        # info holds every location the query text appears at
        for fname, offs in info:

            # Arc state is per location, so identical copies in one file do not link to each other
            key = (fname, offs)

            arcs = self.arcs_hit[fname]
            self.lines_hit[fname].update(range(strt + offs, fini + offs + 1))

            # Arc tracking
            if nodeid is not None and self.prev_nodeid.get(key) != nodeid:
                prev = self.prev_line.get(key)
                if prev is not None:
                    arcs.add((prev, -1))
                self.prev_line.pop(key, None)
                self.prev_nodeid[key] = nodeid

            current_line = strt + offs
            prev = self.prev_line.get(key)
            if prev is not None:
                arcs.add((prev, current_line))
            else:
                arcs.add((-1, current_line))

            last_line = fini + offs
            for line in range(current_line, last_line):
                arcs.add((line, line + 1))

            self.prev_line[key] = last_line

    PIVOT_METHODS = {'nodesByPropValu', 'nodesByPropArray', 'nodesByTag', 'getNodeByNdef'}
    def handleView(self, code): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        if code.co_name not in self.PIVOT_METHODS:
            return DISABLE

        frame = sys._getframe(2)
        if frame.f_code.co_name != 'run':
            return
        return self.handleAst(code, frame=frame)

    def handleStormctrl(self, code): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        if code.co_name != '__init__':
            return DISABLE
        return self.handleAst(code, frame=sys._getframe(3))

TOKENS = [
    'ABSPROP',
    'ABSPROPNOUNIV',
    'PROPS',
    'UNIVNAME',
    'EXPRUNIVNAME',
    'RELNAME',
    'EXPRRELNAME',
    'ALLTAGS',
    'BREAK',
    'CONTINUE',
    'CMDNAME',
    'TAGMATCH',
    'NONQUOTEWORD',
    'VARTOKN',
    'EXPRVARTOKN',
    'NUMBER',
    'HEXNUMBER',
    'OCTNUMBER',
    'BOOL',
    'EXPRTIMES',
    '_EMIT',
    '_STOP',
    '_RETURN',
]

class StormReporter(coverage.FileReporter):
    def __init__(self, filename, parser):
        super().__init__(filename)

        self._parser = parser
        self._source = None

    def source(self):
        if self._source is None:
            try:
                with open(self.filename, 'r') as f:
                    self._source = f.read()

            except (OSError, UnicodeError) as exc:
                raise NoSource(f"Couldn't read {self.filename}: {exc}")
        return self._source

    def _trees(self):
        '''
        Yield (tree, offs) for each Storm tree in the file. The line of the file which holds
        line N of a tree is N + offs.
        '''
        yield self._parser.parse(self.source()), 0

    def lines(self):
        source_lines = set()

        for tree, offs in self._trees():
            for token in tree.scan_values(lambda v: isinstance(v, lark.lexer.Token)):
                if token.type in TOKENS:
                    source_lines.add(token.line + offs)

        return source_lines - self.excluded_lines()

    def excluded_lines(self):
        excluded_lines = set()

        pragma = 'pragma: no cover'
        start = 'pragma: no cover start'
        stop = 'pragma: no cover stop'

        lines = self.source().splitlines()
        nocov = [(lineno + 1, text) for (lineno, text) in enumerate(lines) if pragma in text]

        block = None
        for (lineno, text) in nocov:
            if stop in text:
                if block is not None:
                    # End a multi-line block
                    excluded_lines |= set(range(block, lineno + 1))
                    block = None
                continue

            if start in text:
                if block is None:
                    # Start a multi-line block
                    block = lineno
                continue

            if pragma in text:
                excluded_lines.add(lineno)

        return excluded_lines

    def arcs(self):
        arcs = set()
        for tree, offs in self._trees():
            treearcs = set()
            entries, exits, _, _ = self._analyzeQuery(tree, treearcs)
            for entry in entries:
                treearcs.add((-1, entry))
            for ex in exits:
                treearcs.add((ex, -1))

            for src, dst in treearcs:
                arcs.add((src if src == -1 else src + offs, dst if dst == -1 else dst + offs))

        excluded = self.excluded_lines()
        return {(s, d) for (s, d) in arcs if s not in excluded and d not in excluded}

    def _analyzeQuery(self, query_tree, arcs):
        '''Analyze a query tree. Returns (entries, exits, break_lines, continue_lines).'''
        ops = self._getQueryOps(query_tree)
        if not ops:
            return (set(), set(), set(), set())

        all_breaks = set()
        all_continues = set()
        op_infos = []
        for op in ops:
            entries, exits, breaks, conts = self._analyzeOp(op, arcs)
            all_breaks |= breaks
            all_continues |= conts
            op_infos.append((entries, exits))

            if not exits:
                break

        for i in range(len(op_infos) - 1):
            prev_exits = op_infos[i][1]
            next_entries = op_infos[i + 1][0]
            for src in prev_exits:
                for dst in next_entries:
                    arcs.add((src, dst))

        entries = op_infos[0][0] if op_infos else set()
        exits = op_infos[-1][1] if op_infos else set()
        return (entries, exits, all_breaks, all_continues)

    def _getQueryOps(self, query_tree):
        '''Get meaningful operation nodes from a query tree.'''
        ops = []
        for child in query_tree.children:
            if isinstance(child, lark.Tree):
                ops.append(child)
            elif isinstance(child, lark.lexer.Token) and child.type in ('BREAK', 'CONTINUE'):
                ops.append(child)
        return ops

    def _analyzeOp(self, op, arcs):
        '''Analyze a single op. Returns (entries, exits, break_lines, continue_lines).'''
        if isinstance(op, lark.lexer.Token):
            line = op.line
            if op.type == 'BREAK':
                return ({line}, set(), {line}, set())

            return ({line}, set(), set(), {line})

        if op.data == 'ifstmt':
            return self._analyzeIfstmt(op, arcs)
        if op.data == 'switchcase':
            return self._analyzeSwitchcase(op, arcs)
        if op.data == 'forloop':
            return self._analyzeForloop(op, arcs)
        if op.data == 'whileloop':
            return self._analyzeWhileloop(op, arcs)
        if op.data == 'trycatch':
            return self._analyzeTrycatch(op, arcs)
        if op.data in ('stop', 'return', 'emit'):
            line = op.meta.line
            arcs.add((line, -1))
            return ({line}, set(), set(), set())

        return ({op.meta.line}, {op.meta.line}, set(), set())

    def _analyzeBaresubquery(self, bsq, arcs):
        '''Analyze a baresubquery and return (entries, exits, break_lines, continue_lines).'''
        query = [c for c in bsq.children if isinstance(c, lark.Tree) and c.data == 'query'][0]
        return self._analyzeQuery(query, arcs)

    def _analyzeIfstmt(self, tree, arcs):
        '''Analyze an if/elif/else statement.'''
        clauses = []
        else_body = None

        for child in tree.children:
            if isinstance(child, lark.Tree):
                if child.data == 'ifclause':
                    clauses.append(child)
                elif child.data == 'baresubquery':
                    else_body = child

        cond_lines = []
        bodies = []
        for clause in clauses:
            cond_lines.append(clause.meta.line)
            for child in clause.children:
                if isinstance(child, lark.Tree) and child.data == 'baresubquery':
                    bodies.append(child)
                    break

        first_cond = cond_lines[0]
        all_exits = set()
        all_breaks = set()
        all_continues = set()

        # Arcs between conditions (false case chains to next condition)
        for i in range(len(cond_lines) - 1):
            arcs.add((cond_lines[i], cond_lines[i + 1]))

        # Arcs from each condition to its body (true case)
        for cond_line, body in zip(cond_lines, bodies):
            body_entries, body_exits, breaks, conts = self._analyzeBaresubquery(body, arcs)
            if not body_entries:
                all_exits.add(cond_line)
            else:
                for entry in body_entries:
                    arcs.add((cond_line, entry))
                all_exits |= body_exits
            all_breaks |= breaks
            all_continues |= conts

        # Handle else clause
        last_cond = cond_lines[-1]
        if else_body is not None:
            body_entries, body_exits, breaks, conts = self._analyzeBaresubquery(else_body, arcs)
            for entry in body_entries:
                arcs.add((last_cond, entry))
            all_exits |= body_exits
            all_breaks |= breaks
            all_continues |= conts
        else:
            all_exits.add(last_cond)

        return ({first_cond}, all_exits, all_breaks, all_continues)

    def _analyzeSwitchcase(self, tree, arcs):
        '''Analyze a switch/case statement.'''
        switch_line = tree.meta.line
        case_bodies = []
        has_default = False

        for child in tree.children:
            if isinstance(child, lark.Tree) and child.data == 'caseentry':
                body = None
                is_default = False
                for sub in child.children:
                    if isinstance(sub, lark.Tree) and sub.data == 'baresubquery':
                        body = sub
                    elif isinstance(sub, lark.lexer.Token) and sub.type == 'DEFAULTCASE':
                        is_default = True
                if is_default:
                    has_default = True
                if body is not None:
                    case_bodies.append(body)

        all_exits = set()
        all_breaks = set()
        all_continues = set()
        for body in case_bodies:
            body_entries, body_exits, breaks, conts = self._analyzeBaresubquery(body, arcs)
            for entry in body_entries:
                arcs.add((switch_line, entry))
            all_exits |= body_exits
            all_breaks |= breaks
            all_continues |= conts

        if not has_default:
            all_exits.add(switch_line)

        return ({switch_line}, all_exits, all_breaks, all_continues)

    def _analyzeForloop(self, tree, arcs):
        '''Analyze a for loop.'''
        loop_line = tree.meta.line
        body = None
        for child in tree.children:
            if isinstance(child, lark.Tree) and child.data == 'baresubquery':
                body = child
                break

        body_entries, body_exits, break_lines, continue_lines = self._analyzeBaresubquery(body, arcs)

        # Enter body arc
        for entry in body_entries:
            arcs.add((loop_line, entry))

        # Back-edge: body exit loops back to body entry
        for ex in body_exits:
            for entry in body_entries:
                arcs.add((ex, entry))

        # Continue loops back to body entry
        for cl in continue_lines:
            for entry in body_entries:
                arcs.add((cl, entry))

        # Loop can be skipped (empty iterable) or exited after last iteration
        all_exits = set()
        all_exits.add(loop_line)
        all_exits |= body_exits
        all_exits |= break_lines

        return ({loop_line}, all_exits, set(), set())

    def _analyzeWhileloop(self, tree, arcs):
        '''Analyze a while loop.'''
        loop_line = tree.meta.line
        body = None
        for child in tree.children:
            if isinstance(child, lark.Tree) and child.data == 'baresubquery':
                body = child
                break

        body_entries, body_exits, break_lines, continue_lines = self._analyzeBaresubquery(body, arcs)

        # Enter body arc
        for entry in body_entries:
            arcs.add((loop_line, entry))

        # Back-edge: body exit goes back to condition check
        for ex in body_exits:
            arcs.add((ex, loop_line))

        # Continue goes back to condition check
        for cl in continue_lines:
            arcs.add((cl, loop_line))

        # While can exit when condition is false or break
        all_exits = set()
        all_exits.add(loop_line)
        all_exits |= break_lines

        return ({loop_line}, all_exits, set(), set())

    def _analyzeTrycatch(self, tree, arcs):
        '''Analyze a try/catch statement.'''
        try_body = None
        catch_blocks = []

        for child in tree.children:
            if isinstance(child, lark.Tree):
                if child.data == 'query' and try_body is None:
                    try_body = child
                elif child.data == 'catchblock':
                    catch_blocks.append(child)

        all_exits = set()
        all_breaks = set()
        all_continues = set()
        try_entries = set()

        if try_body is not None:
            try_entries, try_exits, breaks, conts = self._analyzeQuery(try_body, arcs)
            all_exits |= try_exits
            all_breaks |= breaks
            all_continues |= conts

        for catch in catch_blocks:
            catch_line = catch.meta.line
            catch_body = None
            for child in catch.children:
                if isinstance(child, lark.Tree) and child.data == 'query':
                    catch_body = child
                    break

            # Arc from try entry to catch condition (exception path)
            for te in try_entries:
                arcs.add((te, catch_line))

            if catch_body is not None:
                catch_entries, catch_exits, breaks, conts = self._analyzeQuery(catch_body, arcs)
                # Arc from catch condition to catch body
                for ce in catch_entries:
                    arcs.add((catch_line, ce))
                all_exits |= catch_exits
                all_breaks |= breaks
                all_continues |= conts

        return (try_entries, all_exits, all_breaks, all_continues)

    def exit_counts(self):
        '''Return dict mapping src line to count of distinct destinations.'''
        counts = collections.defaultdict(int)
        for src, _ in self.arcs():
            if src != -1:
                counts[src] += 1
        return dict(counts)

    def no_branch_lines(self):
        return self.excluded_lines()

    def missing_arc_description(self, start, end, executed_arcs=None):
        '''Return a human-readable description of a missing arc.'''
        if end == -1:
            return 'the exit was not reached'

        if start == -1:
            return f'the entry to line {end} was not reached'

        for tree, offs in self._trees():
            branching = self._findBranchingConstruct(tree, start - offs)
            if branching is not None:
                ctype = branching
                if end > start:
                    return f'the {ctype} on line {start} did not jump to line {end}'
                return f'the {ctype} on line {start} did not loop back to line {end}'

        return f'line {start} did not jump to line {end}'

    def _findBranchingConstruct(self, tree, line):
        '''Find what branching construct a line belongs to.'''
        for child in tree.iter_subtrees():
            if hasattr(child, 'meta') and not child.meta.empty:
                if child.meta.line == line:
                    if child.data in ('ifstmt', 'ifclause'):
                        return 'if/elif condition'
                    if child.data == 'switchcase':
                        return 'switch'
                    if child.data == 'forloop':
                        return 'for loop'
                    if child.data == 'whileloop':
                        return 'while loop'
                    if child.data == 'trycatch':
                        return 'try/catch'
        return None

class EmbeddedStormReporter(StormReporter):
    '''
    Reporter for a py or yaml file which embeds Storm.
    '''
    def __init__(self, filename, parser, pykeys, yamlkeys):
        super().__init__(filename, parser)
        self._pykeys = pykeys
        self._yamlkeys = yamlkeys
        self._treecache = None

    def _trees(self):
        if self._treecache is None:
            self._treecache = []

            for text, offs in getEmbeddedStorm(self.filename, self._pykeys, self._yamlkeys):
                try:
                    tree = self._parser.parse(text)
                except lark.exceptions.LarkError:
                    continue

                self._treecache.append((tree, offs))

        yield from self._treecache

# StormReporterPlugin and coverage_init below are both to support the command
# line coverage tools being able to interpret coverage results generated by
# stormcov
class StormReporterPlugin(coverage.CoveragePlugin):
    def __init__(self, pykeys=DEFAULT_PY_KEYS, yamlkeys=DEFAULT_YAML_KEYS):
        self.parser = getParser()
        self.pykeys = frozenset(pykeys)
        self.yamlkeys = frozenset(yamlkeys)

    def file_reporter(self, filename):
        if os.path.splitext(filename)[1][1:].lower() in EMBED_KINDS:
            return EmbeddedStormReporter(filename, self.parser, self.pykeys, self.yamlkeys)

        return StormReporter(filename, self.parser)

def coverage_init(reg, options): # pragma: no cover
    # NB: no coverage since this is the coverage plugin entrypoint
    # Coverage plugin options are comma separated strings
    plugin = StormReporterPlugin(
        pykeys=splitKeys(options['py_keys']) if 'py_keys' in options else DEFAULT_PY_KEYS,
        yamlkeys=splitKeys(options['yaml_keys']) if 'yaml_keys' in options else DEFAULT_YAML_KEYS,
    )
    reg.add_file_tracer(plugin)
