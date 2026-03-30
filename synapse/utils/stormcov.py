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
    # NB: no coverage since this is a pytest hook
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
            'ast.py': self.handle_ast,
            'view.py': self.handle_view,
            'stormctrl.py': self.handle_stormctrl,
        }

        self.node_map = {}
        self.text_map = {}
        self.guid_map = {}
        self.subq_map = {}
        self.lines_hit = collections.defaultdict(set)
        self.arcs_hit = collections.defaultdict(set)
        self.prev_line = {}
        self.prev_nodeid = {}

        self.freg = regex.compile(r'.*synapse/lib/(ast.py|view.py|stormctrl.py)$')

        self.parser = get_parser()

        opts = config.option

        self.append = config.option.stormcov_append
        self.stormdirs = config.option.stormdirs
        self.basedir = config.option.stormcov_basedir
        self.extensions = [e.strip() for e in opts.stormexts.split(',')]

    def reset(self):
        self.lines_hit = collections.defaultdict(set)
        self.arcs_hit = collections.defaultdict(set)
        self.prev_line = {}
        self.prev_nodeid = {}

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

                line = node.meta.line - 1
                rline = node.meta.line
                if rule == 'argvquery':
                    line = subq.meta.line - 1

                if subg in self.subq_map:
                    (pname, _, pline) = self.subq_map[subg]
                    logger.warning(f'Duplicate {rule} in {path} at line {rline}, coverage will '
                                   f'be reported on first instance in {pname} at line {pline}')
                    continue

                self.subq_map[subg] = (path, line, rline)

    def _start_sysmon(self):
        if sys.monitoring.get_tool(self.toolid) is None:
            sys.monitoring.use_tool_id(self.toolid, 'pytest-stormcov')
            self._freetool = True

        sys.monitoring.set_events(self.toolid, sys.monitoring.events.PY_START)
        self._prevcb = sys.monitoring.register_callback(self.toolid, sys.monitoring.events.PY_START, self.sysmon_py_start)

    def _stop_sysmon(self):
        if self._prevcb: # pragma: no cover
            sys.monitoring.register_callback(self.toolid, sys.monitoring.events.PY_START, self._prevcb)
            return

        if self._freetool:
            sys.monitoring.free_tool_id(self.toolid)
            self._freetool = False

    @pytest.hookimpl(wrapper=True)
    def pytest_runtestloop(self, session): # pragma: no cover
        # NB: no coverage since this is a pytest hook

        # self.cov = coverage.Coverage().current()
        # if self.cov is None:
        self.cov = coverage.Coverage()

        if not self.append:
            self.cov.erase()

        self._start_sysmon()
        yield
        self._stop_sysmon()
        self.finalize_arcs()

        self.cov.load()

        data = self.cov.get_data()

        # Bail if there's no coverage. This could be because of a xdist worker
        # that didn't have any work
        if not self.lines_hit and not self.arcs_hit:
            return

        # Add our stormcov data based on coverage mode
        if self.cov.config.branch:
            data.add_arcs(dict(self.arcs_hit))
        else:
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
        # NB: no coverage since this is a pytest hook
        # Note: If using xdist, this function executes on each worker node
        testpaths = [item.path for item in items]
        self.discover_stormdirs(testpaths)
        yield

    @pytest.hookimpl(wrapper=True)
    def pytest_xdist_node_collection_finished(self, node, ids): # pragma: no cover
        # NB: no coverage since this is a pytest hook
        # Note: This hook allows the xdist controller to get a list of test ids so we can build a list of storm dirs to present stormterm coverage
        testpaths = [pathlib.Path(testid.split('::')[0]).absolute() for testid in ids]
        self.discover_stormdirs(testpaths)
        yield

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config): # pragma: no cover
        # NB: no coverage since this is a pytest hook
        if self.isworker:
            return

        if not self.iscontroller and not self.lines_hit:
            return

        try:
            self.cov.report(skip_covered=False, skip_empty=False)
        except coverage.exceptions.NoDataError:
            logger.warning('No storm coverage data was found.')

    def sysmon_py_start(self, code, instruction_offset): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        if (fname := self.freg.match(code.co_filename)):
            return self.handlers[fname.group(1)](code)
        return DISABLE

    def handle_ast(self, code, frame=None): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
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
            self.mark_lines(frame, info, nodeid=nodeid)
            return

        if node.__class__.__name__ != 'Query':
            self.node_map[nodeid] = None
            return

        info = self.text_map.get(node.text, s_common.novalu)
        if info is not s_common.novalu:
            self.mark_lines(frame, info, nodeid=nodeid)
            return

        tree = self.parser.parse(node.text)
        guid = s_common.guid(str(tree))

        subq = self.subq_map.get(guid)
        if subq is not None:
            (filename, offs, _) = subq
        else:
            filename = self.guid_map.get(guid)
            offs = 0

        if filename is None:
            self.node_map[nodeid] = None
            return

        self.node_map[nodeid] = (filename, offs)
        self.text_map[node.text] = (filename, offs)
        self.mark_lines(frame, (filename, offs), nodeid=nodeid)

    def finalize_arcs(self):
        for fname, prev in self.prev_line.items():
            self.arcs_hit[fname].add((prev, -1))

    def mark_lines(self, frame, info, nodeid=None): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        astn = frame.f_locals.get('self')
        fname, offs = info
        strt = astn.astinfo.sline
        if astn.astinfo.isterm:
            fini = astn.astinfo.eline
        else:
            fini = strt

        self.lines_hit[fname].update(range(strt + offs, fini + offs + 1))

        # Arc tracking
        if nodeid is not None and self.prev_nodeid.get(fname) != nodeid:
            prev = self.prev_line.get(fname)
            if prev is not None:
                self.arcs_hit[fname].add((prev, -1))
            self.prev_line.pop(fname, None)
            self.prev_nodeid[fname] = nodeid

        current_line = strt + offs
        prev = self.prev_line.get(fname)
        if prev is not None:
            self.arcs_hit[fname].add((prev, current_line))
        else:
            self.arcs_hit[fname].add((-1, current_line))

        last_line = fini + offs
        for line in range(current_line, last_line):
            self.arcs_hit[fname].add((line, line + 1))

        self.prev_line[fname] = last_line

    PIVOT_METHODS = {'nodesByPropValu', 'nodesByPropArray', 'nodesByTag', 'getNodeByNdef'}
    def handle_view(self, code): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
        if code.co_name not in self.PIVOT_METHODS:
            return DISABLE

        frame = inspect.currentframe().f_back.f_back
        if frame.f_code.co_name != 'run':
            return
        return self.handle_ast(code, frame=frame)

    def handle_stormctrl(self, code): # pragma: no cover
        # NB: no coverage since this runs inside of the sys.monitoring callback
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

    def arcs(self):
        tree = self._parser.parse(self.source())
        arcs = set()
        entries, exits, _, _ = self._analyze_query(tree, arcs)
        for entry in entries:
            arcs.add((-1, entry))
        for ex in exits:
            arcs.add((ex, -1))
        excluded = self.excluded_lines()
        return {(s, d) for (s, d) in arcs if s not in excluded and d not in excluded}

    def _analyze_query(self, query_tree, arcs):
        '''Analyze a query tree. Returns (entries, exits, break_lines, continue_lines).'''
        ops = self._get_query_ops(query_tree)
        if not ops:
            return (set(), set(), set(), set())

        all_breaks = set()
        all_continues = set()
        op_infos = []
        for op in ops:
            entries, exits, breaks, conts = self._analyze_op(op, arcs)
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

    def _get_query_ops(self, query_tree):
        '''Get meaningful operation nodes from a query tree.'''
        ops = []
        for child in query_tree.children:
            if isinstance(child, lark.Tree):
                ops.append(child)
            elif isinstance(child, lark.lexer.Token) and child.type in ('BREAK', 'CONTINUE'):
                ops.append(child)
        return ops

    def _analyze_op(self, op, arcs):
        '''Analyze a single op. Returns (entries, exits, break_lines, continue_lines).'''
        if isinstance(op, lark.lexer.Token):
            line = op.line
            if op.type == 'BREAK':
                return ({line}, set(), {line}, set())

            return ({line}, set(), set(), {line})

        if op.data == 'ifstmt':
            return self._analyze_ifstmt(op, arcs)
        if op.data == 'switchcase':
            return self._analyze_switchcase(op, arcs)
        if op.data == 'forloop':
            return self._analyze_forloop(op, arcs)
        if op.data == 'whileloop':
            return self._analyze_whileloop(op, arcs)
        if op.data == 'trycatch':
            return self._analyze_trycatch(op, arcs)
        if op.data in ('stop', 'return', 'emit'):
            return ({op.meta.line}, set(), set(), set())

        return ({op.meta.line}, {op.meta.line}, set(), set())

    def _analyze_baresubquery(self, bsq, arcs):
        '''Analyze a baresubquery and return (entries, exits, break_lines, continue_lines).'''
        query = [c for c in bsq.children if isinstance(c, lark.Tree) and c.data == 'query'][0]
        return self._analyze_query(query, arcs)

    def _analyze_ifstmt(self, tree, arcs):
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
            body_entries, body_exits, breaks, conts = self._analyze_baresubquery(body, arcs)
            for entry in body_entries:
                arcs.add((cond_line, entry))
            all_exits |= body_exits
            all_breaks |= breaks
            all_continues |= conts

        # Handle else clause
        last_cond = cond_lines[-1]
        if else_body is not None:
            body_entries, body_exits, breaks, conts = self._analyze_baresubquery(else_body, arcs)
            for entry in body_entries:
                arcs.add((last_cond, entry))
            all_exits |= body_exits
            all_breaks |= breaks
            all_continues |= conts
        else:
            all_exits.add(last_cond)

        return ({first_cond}, all_exits, all_breaks, all_continues)

    def _analyze_switchcase(self, tree, arcs):
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
            body_entries, body_exits, breaks, conts = self._analyze_baresubquery(body, arcs)
            for entry in body_entries:
                arcs.add((switch_line, entry))
            all_exits |= body_exits
            all_breaks |= breaks
            all_continues |= conts

        if not has_default:
            all_exits.add(switch_line)

        return ({switch_line}, all_exits, all_breaks, all_continues)

    def _analyze_forloop(self, tree, arcs):
        '''Analyze a for loop.'''
        loop_line = tree.meta.line
        body = None
        for child in tree.children:
            if isinstance(child, lark.Tree) and child.data == 'baresubquery':
                body = child
                break

        body_entries, body_exits, break_lines, continue_lines = self._analyze_baresubquery(body, arcs)

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

    def _analyze_whileloop(self, tree, arcs):
        '''Analyze a while loop.'''
        loop_line = tree.meta.line
        body = None
        for child in tree.children:
            if isinstance(child, lark.Tree) and child.data == 'baresubquery':
                body = child
                break

        body_entries, body_exits, break_lines, continue_lines = self._analyze_baresubquery(body, arcs)

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
        all_exits |= body_exits
        all_exits |= break_lines

        return ({loop_line}, all_exits, set(), set())

    def _analyze_trycatch(self, tree, arcs):
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
            try_entries, try_exits, breaks, conts = self._analyze_query(try_body, arcs)
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
                catch_entries, catch_exits, breaks, conts = self._analyze_query(catch_body, arcs)
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
        tree = self._parser.parse(self.source())

        if end == -1:
            return 'the exit was not reached'

        if start == -1:
            return f'the entry to line {end} was not reached'

        branching = self._find_branching_construct(tree, start)
        if branching is not None:
            ctype = branching
            if end > start:
                return f'the {ctype} on line {start} did not jump to line {end}'
            return f'the {ctype} on line {start} did not loop back to line {end}'

        return f'line {start} did not jump to line {end}'

    def _find_branching_construct(self, tree, line):
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

# StormReporterPlugin and coverage_init below are both to support the command
# line coverage tools being able to interpret coverage results generated by
# stormcov
class StormReporterPlugin(coverage.CoveragePlugin):
    def __init__(self):
        self.parser = get_parser()

    def file_reporter(self, filename):
        return StormReporter(filename, self.parser)

def coverage_init(reg, options): # pragma: no cover
    # NB: no coverage since this is the coverage plugin entrypoint
    plugin = StormReporterPlugin()
    reg.add_file_tracer(plugin)
