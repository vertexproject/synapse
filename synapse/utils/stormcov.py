import os
import sys
import inspect
import logging
import pathlib
import collections

import lark
import regex
import pytest
import coverage

from coverage.exceptions import NoSource

import synapse.data as s_data
import synapse.common as s_common

logger = logging.getLogger(__name__)

PACKAGE_DIR = pathlib.Path('packages').absolute()

def pytest_addoption(parser): # pragma: no cover
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

DISABLE = sys.monitoring.DISABLE

def pytest_configure(config): # pragma: no cover
    if not config.option.stormcov and not (config.option.stormdirs or config.option.stormcov_append):
        return

    config.pluginmanager.register(StormcovPlugin(config), 'stormcov')

def get_parser():
    grammar = s_data.getLark('storm')

    return lark.Lark(grammar, start='query', regex=True, parser='lalr', keep_all_tokens=True,
                            maybe_placeholders=False, propagate_positions=True)

class StormcovPlugin:

    PARSE_METHODS = {'compute', 'once', 'lift', 'getPivsOut', 'getPivsIn'}

    def __init__(self, config):
        self.toolid = sys.monitoring.COVERAGE_ID
        self._freetool = False

        self.config = config
        self.handlers = {
            'ast.py': self.handle_ast,
            'view.py': self.handle_view,
            'stormctrl.py': self.handle_stormctrl,
        }

        self.node_map = {}
        self.text_map = {}
        self.guid_map = {}
        self.subq_map = {}

        self.freg = regex.compile(r'.*synapse/lib/(ast.py|view.py|stormctrl.py)$')
        self.reset()

        self.parser = get_parser()

        opts = config.option

        self.append = config.option.stormcov_append
        self.stormdirs = config.option.stormdirs
        self.basedir = config.option.stormcov_basedir
        self.extensions = [e.strip() for e in opts.stormexts.split(',')]

        self.debug = []

    def reset(self):
        self.lines_hit = collections.defaultdict(set)

    def find_storm_files(self, dirn):
        for path in self.find_executable_files(dirn):
            with open(path, 'r') as f:
                apth = os.path.abspath(path)

                try:
                    tree = self.parser.parse(f.read())
                except lark.exceptions.UnexpectedToken:
                    logger.warning('Skipping invalid storm file: %s', apth)
                    continue

                self.find_subqueries(tree, apth)

                guid = s_common.guid(str(tree))
                self.guid_map[guid] = apth

    def find_executable_files(self, src_dir):
        rx = r"^[^#~!$@%^&*()+=,]+\.(" + "|".join(self.extensions) + r")$"
        for (dirpath, dirnames, filenames) in os.walk(src_dir):
            for filename in filenames:
                if regex.search(rx, filename):
                    path = os.path.join(dirpath, filename)
                    yield path

    def find_subqueries(self, tree, path):
        for rule in ('argvquery', 'embedquery'):
            for node in tree.find_data(rule):

                subq = node.children[1]
                if subq.meta.empty:
                    continue

                soff = subq.meta.start_pos
                eoff = subq.meta.end_pos

                if rule == 'embedquery':
                    soff = node.meta.start_pos + 2
                    eoff = node.meta.end_pos - 1

                subg = (s_common.guid(str(tree)), soff, eoff)
                line = (node.meta.line - 1)

                logger.info(f'guid={subg[0]} {path=} {subq=} {soff=} {eoff=} {line=}')

                if subg in self.subq_map:
                    (pname, pline) = self.subq_map[subg]
                    logger.warning(f'Duplicate {rule} in {path} at line {line + 1}, coverage will '
                                   f'be reported on first instance in {pname} at line {pline + 1}')
                    continue

                self.subq_map[subg] = (path, line)

    def _start_sysmon(self):
        if sys.monitoring.get_tool(self.toolid) is None:
            sys.monitoring.use_tool_id(self.toolid, 'pytest-stormcov')
            self._freetool = True

        sys.monitoring.set_events(self.toolid, sys.monitoring.events.PY_START)
        sys.monitoring.register_callback(self.toolid, sys.monitoring.events.PY_START, self.sysmon_py_start)

    def _stop_sysmon(self):
        if self._freetool:
            sys.monitoring.free_tool_id(self.toolid)
            self._freetool = False

    @pytest.hookimpl(wrapper=True)
    def pytest_runtestloop(self, session): # pragma: no cover

        self.cov = coverage.Coverage.current()

        if self.cov is None:
            self.cov = coverage.Coverage()

        if not self.append:
            self.cov.erase()

        self._start_sysmon()
        yield
        self._stop_sysmon()

        self.cov.load()

        data = self.cov.get_data()

        # Add our stormcov data
        data.add_lines(dict(self.lines_hit))
        data.touch_files(self.guid_map.values(), 'synapse.utils.stormcov.StormReporterPlugin')

        # Save the coverage data
        data.write()

    def discover_stormdirs(self, testpaths: list[pathlib.Path]):
        # If a specific set of directories were specified, use that
        if self.stormdirs:
            for dirn in self.stormdirs.split(','):
                self.find_storm_files(dirn)
            return

        stormdirs = set()

        # Iterate through the tests, get their path, and add the containing storm package directory
        for testpath in testpaths:
            if testpath.is_relative_to(self.basedir):
                stormdir = str(self.basedir / testpath.relative_to(self.basedir).parts[0])
                stormdirs.add(stormdir)

        for dirn in stormdirs:
            self.find_storm_files(dirn)

    @pytest.hookimpl(wrapper=True)
    def pytest_collection_modifyitems(self, config, items): # pragma: no cover
        # Note: If using xdist, this function executes on each worker node
        testpaths = [item.path for item in items]
        self.discover_stormdirs(testpaths)
        yield

    @pytest.hookimpl(wrapper=True)
    def pytest_xdist_node_collection_finished(self, node, ids): # pragma: no cover
        # Note: This hook allows the xdist controller to get a list of test ids so we can build a list of storm dirs to present stormterm coverage
        testpaths = [pathlib.Path(testid.split('::')[0]).absolute() for testid in ids]
        self.discover_stormdirs(testpaths)
        yield

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config): # pragma: no cover
        self.cov.report(skip_covered=False, skip_empty=False)

    def sysmon_py_start(self, code, instruction_offset):
        if (fname := self.freg.match(code.co_filename)):
            return self.handlers[fname.group(1)](code)
        return DISABLE

    def handle_ast(self, code, frame=None):
        if frame is None:
            if code.co_name == 'pullgenr':
                frame = inspect.currentframe().f_back.f_back

                if frame.f_back.f_code.co_name != 'execStormCmd':
                    return

                frame = frame.f_back.f_back

            elif code.co_name not in self.PARSE_METHODS:
                return DISABLE

            else:
                frame = inspect.currentframe().f_back.f_back

        realnode = frame.f_locals.get('self')
        realcls = realnode.__class__.__name__
        if hasattr(realnode, '_coverage_hit'):
            return

        realnode._coverage_hit = True

        node = realnode
        while hasattr(node, 'parent'):
            node = node.parent

        topnode = node

        if realcls in ('ArgvQuery', 'EmbedQuery'):
            node = realnode.kids[0]

        nodeid = id(node)

        info = self.node_map.get(nodeid, s_common.novalu)
        if info is None:
            return

        if info is not s_common.novalu:
            self.mark_lines(frame, info)
            return

        if not node.__class__.__name__ == 'Query':
            self.node_map[nodeid] = None
            return

        info = self.text_map.get(node.text, s_common.novalu)
        if info is not s_common.novalu:
            self.mark_lines(frame, info)
            return

        tree = self.parser.parse(topnode.text)
        guid = s_common.guid(str(tree))

        if realcls in ('ArgvQuery', 'EmbedQuery'):
            posinfo = node.getPosInfo()
            if realcls == 'EmbedQuery':
                posinfo = realnode.getPosInfo()
            soff, eoff = posinfo['offsets']
            filename, offs = self.subq_map.get((guid, soff, eoff), (None, 0))
        else:
            filename = self.guid_map.get(guid)
            offs = 0

        if filename is None:
            self.node_map[nodeid] = None
            return

        self.node_map[nodeid] = (filename, offs)
        self.text_map[node.text] = (filename, offs)
        self.mark_lines(frame, (filename, offs))

    def mark_lines(self, frame, info):
        self.debug.append((frame, info))
        astn = frame.f_locals.get('self')
        fname, offs = info
        strt = astn.astinfo.sline
        if astn.astinfo.isterm:
            fini = astn.astinfo.eline
        else:
            fini = strt

        logger.info(f'{fname} {offs} {strt + offs=} {fini + offs + 1=}')
        self.lines_hit[fname].update(range(strt + offs, fini + offs + 1))

    PIVOT_METHODS = {'nodesByPropValu', 'nodesByPropArray', 'nodesByTag', 'getNodeByNdef'}
    def handle_view(self, code):
        if code.co_name not in self.PIVOT_METHODS:
            return DISABLE

        frame = inspect.currentframe().f_back.f_back
        if frame.f_code.co_name != 'run':
            return
        return self.handle_ast(code, frame=frame)

    def handle_stormctrl(self, code):
        if code.co_name != '__init__':
            return DISABLE
        return self.handle_ast(code, frame=inspect.currentframe().f_back.f_back.f_back)

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

    def lines(self):
        source_lines = set()

        tree = self._parser.parse(self.source())

        for token in tree.scan_values(lambda v: isinstance(v, lark.lexer.Token)):
            if token.type in TOKENS:
                source_lines.add(token.line)

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

# StormReporterPlugin and coverage_init below are both to support the command
# line coverage tools being able to interpret coverage results generated by
# stormcov
class StormReporterPlugin(coverage.CoveragePlugin):
    def __init__(self):
        self.parser = get_parser()

    def file_reporter(self, filename):
        return StormReporter(filename, self.parser)

def coverage_init(reg, options):
    plugin = StormReporterPlugin()
    reg.add_file_tracer(plugin)
