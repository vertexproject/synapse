import io
import os
import sys
import inspect
import logging
import collections

import lark
import regex
import pytest
import coverage

from coverage.exceptions import NoSource

import synapse.data as s_data
import synapse.common as s_common

logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    """Add options to control storm coverage."""

    group = parser.getgroup('stormcov', 'storm coverage reporting')
    group.addoption(
        '--storm-exts',
        action='store',
        default='storm',
        dest='stormexts',
        help='Comma separated list of file extensions containing Storm. Default: storm',
    )

    # This option allows us to have coverage but not storm coverage (i.e. only
    # Python coverage)
    group.addoption(
        '--no-stormcov',
        action='store_true',
        default=False,
        dest='no_stormcov',
        help='Disable stormcov. Default: False',
    )

DISABLE = sys.monitoring.DISABLE

def pytest_configure(config):
    if config.option.no_stormcov or not config.pluginmanager.has_plugin('_cov') or config.option.no_cov:
        return

    isworker = config.option.numprocesses is None or os.environ.get("PYTEST_XDIST_WORKER") is not None
    config.pluginmanager.register(StormcovPlugin(config, isworker), 'stormcov')

class StormcovPlugin:

    PARSE_METHODS = {'compute', 'once', 'lift', 'getPivsOut', 'getPivsIn'}

    def __init__(self, config, isworker):
        self.toolid = 2
        self.isworker = isworker
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
        self.lines_hit = collections.defaultdict(set)

        grammar = s_data.getLark('storm')

        self.parser = lark.Lark(grammar, start='query', regex=True, parser='lalr', keep_all_tokens=True,
                                maybe_placeholders=False, propagate_positions=True)

        opts = config.option

        self.extensions = [e.strip() for e in opts.stormexts.split(',')]

        # --cov: Load all storm files in current directory. Only show coverage
        # information for storm files that have greater than 0% coverage (had at
        # least one line executed)

        # --cov=path/to/dir: Load all storm files in specified directory. Show
        # coverage for all discovered storm files even if they have 0% coverage.

        self.covpaths = False
        if (cov_source := self.config.option.cov_source) == [True]:
            self.find_storm_files('.')

        else:
            self.covpaths = True
            for dirn in cov_source:
                self.find_storm_files(dirn)

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

                subg = s_common.guid(str(subq))
                line = (node.meta.line - 1)

                if subg in self.subq_map:
                    (pname, pline) = self.subq_map[subg]
                    logger.warning(f'Duplicate {rule} in {path} at line {line + 1}, coverage will '
                                   f'be reported on first instance in {pname} at line {pline + 1}')
                    continue

                self.subq_map[subg] = (path, line)

    @pytest.hookimpl(hookwrapper=True, tryfirst=True)
    def pytest_runtestloop(self, session):
        sys.monitoring.use_tool_id(self.toolid, 'pytest-stormcov')
        sys.monitoring.set_events(self.toolid, sys.monitoring.events.PY_START)
        sys.monitoring.register_callback(self.toolid, sys.monitoring.events.PY_START, self.sysmon_py_start)

        yield

        sys.monitoring.free_tool_id(self.toolid)

        # Get a reference to the pytest-cov plugin
        covplug = session.config.pluginmanager.getplugin('_cov')
        cov = covplug.cov_controller.cov

        # Load the existing data
        cov.load()
        data = cov.get_data()

        # Add our stormcov data
        lines_hit = dict(self.lines_hit)
        data.add_lines(lines_hit)

        if self.covpaths:
            # Paths were specified so show all files that were discovered in the
            # path even if they have 0% coverage
            data.touch_files(self.guid_map.values(), 'synapse.utils.stormcov.StormReporterPlugin')
        else:
            # Paths were not specified so only show files that were hit
            data.touch_files(lines_hit.keys(), 'synapse.utils.stormcov.StormReporterPlugin')

        # Save the coverage data
        data.write()

        # Reset the pytest-cov internal cov report and then re-run it's
        # pytest_runtestloop to get it to re-generate the test report. This
        # should work with any test report format specified by it's command line
        # options.
        covplug.cov_report = io.StringIO()
        for _ in covplug.pytest_runtestloop(session):
            pass

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
        if hasattr(realnode, '_coverage_hit'):
            return

        realnode._coverage_hit = True

        node = realnode
        while hasattr(node, 'parent'):
            node = node.parent

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

        tree = self.parser.parse(node.text)
        guid = s_common.guid(str(tree))

        subq = self.subq_map.get(guid)
        if subq is not None:
            (filename, offs) = subq
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
        astn = frame.f_locals.get('self')
        fname, offs = info
        strt = astn.astinfo.sline
        if astn.astinfo.isterm:
            fini = astn.astinfo.eline
        else:
            fini = strt

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
        grammar = s_data.getLark('storm')
        self.parser = lark.Lark(grammar, start='query', regex=True, parser='lalr', keep_all_tokens=True,
                                maybe_placeholders=False, propagate_positions=True)

    def file_reporter(self, filename):
        return StormReporter(filename, self.parser)

def coverage_init(reg, options):
    plugin = StormReporterPlugin()
    reg.add_file_tracer(plugin)
