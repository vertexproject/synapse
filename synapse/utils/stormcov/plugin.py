import os
import lark
import regex
import logging
import coverage

from coverage.exceptions import NoSource

import synapse.common as s_common

import synapse.lib.datfile as s_datfile

logger = logging.getLogger(__name__)

class StormPlugin(coverage.CoveragePlugin, coverage.FileTracer):

    def __init__(self, options):
        extensions = options.get('storm_extensions', 'storm')
        self.extensions = [e.strip() for e in extensions.split(',')]

        with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
            grammar = larkf.read().decode()

        self.parser = lark.Lark(grammar, start='query', debug=True, regex=True,
                                parser='lalr', keep_all_tokens=True, maybe_placeholders=False,
                                propagate_positions=True)

        self.node_map = {}
        self.text_map = {}
        self.guid_map = {}
        self.subq_map = {}

        dirs = options.get('storm_dirs', '.')
        if dirs:
            self.stormdirs = [d.strip() for d in dirs.split(',')]
            for dirn in self.stormdirs:
                self.find_storm_files(dirn)

    def find_storm_files(self, dirn):
        for path in self.find_executable_files(dirn):
            with open(path, 'r') as f:
                apth = os.path.abspath(path)

                tree = self.parser.parse(f.read())
                self.find_subqueries(tree, apth)

                guid = s_common.guid(str(tree))
                self.guid_map[guid] = apth

    def find_subqueries(self, tree, path):
        for rule in ('argvquery', 'embedquery'):
            for node in tree.find_data(rule):

                subq = node.children[1]
                if subq.meta.empty:
                    continue

                subg = s_common.guid(str(subq))
                line = (subq.meta.line - 1)

                if subg in self.subq_map:
                    (pname, pline) = self.subq_map[subg]
                    logger.warning(f'Duplicate {rule} in {path} at line {line + 1}, coverage will '
                                   f'be reported on first instance in {pname} at line {pline + 1}')
                    continue

                self.subq_map[subg] = (path, subq.meta.line - 1)

    def file_tracer(self, filename):
        if filename.endswith('synapse/lib/ast.py'):
            return self

        if filename.endswith('synapse/lib/stormctrl.py'):
            return StormCtrlTracer(self)

        if filename.endswith('synapse/lib/snap.py'):
            return PivotTracer(self)

        return None

    def file_reporter(self, filename):
        return StormReporter(filename, self.parser)

    def find_executable_files(self, src_dir):
        rx = r"^[^#~!$@%^&*()+=,]+\.(" + "|".join(self.extensions) + r")$"
        for (dirpath, dirnames, filenames) in os.walk(src_dir):
            for filename in filenames:
                if regex.search(rx, filename):
                    path = os.path.join(dirpath, filename)
                    yield path

    def has_dynamic_source_filename(self):
        return True

    PARSE_METHODS = {'compute', 'once', 'lift', 'getPivsOut', 'getPivsIn'}

    def dynamic_source_filename(self, filename, frame, force=False):

        if frame.f_code.co_name == 'pullgenr':
            if frame.f_back.f_code.co_name != 'execStormCmd':
                return None
            frame = frame.f_back.f_back

        elif frame.f_code.co_name not in self.PARSE_METHODS and not force:
            return None

        realnode = frame.f_locals.get('self')
        node = realnode
        while hasattr(node, 'parent'):
            node = node.parent

        nodeid = id(node)

        info = self.node_map.get(nodeid, s_common.novalu)
        if info is None:
            return

        if info is not s_common.novalu:
            realnode._coverage_offs = info[1]
            return info[0]

        if not node.__class__.__name__ == 'Query':
            self.node_map[nodeid] = None
            return

        info = self.text_map.get(node.text, s_common.novalu)
        if info is not s_common.novalu:
            realnode._coverage_offs = info[1]
            return info[0]

        tree = self.parser.parse(node.text)
        guid = s_common.guid(str(tree))

        subq = self.subq_map.get(guid)
        if subq is not None:
            (filename, offs) = subq
        else:
            filename = self.guid_map.get(guid)
            offs = 0

        realnode._coverage_offs = offs

        self.node_map[nodeid] = (filename, offs)
        self.text_map[node.text] = (filename, offs)
        return filename

    def line_number_range(self, frame):
        if frame.f_code.co_name == 'pullgenr':
            frame = frame.f_back.f_back

        astn = frame.f_locals.get('self')

        offs = astn._coverage_offs
        strt = astn.astinfo.sline
        if astn.astinfo.isterm:
            fini = astn.astinfo.eline
        else:
            fini = strt

        return (strt + offs, fini + offs)

class StormCtrlTracer(coverage.FileTracer):
    def __init__(self, parent):
        self.parent = parent

    def has_dynamic_source_filename(self):
        return True

    def dynamic_source_filename(self, filename, frame):
        if frame.f_code.co_name != '__init__':
            return None
        return self.parent.dynamic_source_filename(None, frame.f_back, force=True)

    def line_number_range(self, frame):
        return self.parent.line_number_range(frame.f_back)

class PivotTracer(coverage.FileTracer):
    def __init__(self, parent):
        self.parent = parent

    def has_dynamic_source_filename(self):
        return True

    PARSE_METHODS = {'nodesByPropValu', 'nodesByPropArray', 'nodesByTag', 'getNodeByNdef'}

    def dynamic_source_filename(self, filename, frame):
        if frame.f_code.co_name not in self.PARSE_METHODS or frame.f_back.f_code.co_name != 'run':
            return None
        return self.parent.dynamic_source_filename(None, frame.f_back, force=True)

    def line_number_range(self, frame):
        return self.parent.line_number_range(frame.f_back)

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
