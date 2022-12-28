import os
import lark
import regex
import coverage

import synapse.common as s_common

import synapse.lib.datfile as s_datfile

class StormPlugin(coverage.CoveragePlugin, coverage.FileTracer):

    def __init__(self, options):
        extensions = options.get("template_extensions", "storm")
        self.extensions = [e.strip() for e in extensions.split(",")]

        with s_datfile.openDatFile('synapse.lib/storm.lark') as larkf:
            grammar = larkf.read().decode()

        self.parser = lark.Lark(grammar, start='query', debug=True, regex=True,
                                parser='lalr', keep_all_tokens=True, maybe_placeholders=False,
                                propagate_positions=True)

        self.node_map = {}
        self.text_map = {}
        self.guid_map = {}
        dirs = options.get("storm_dirs", ".")
        if dirs:
            self.stormdirs = [d.strip() for d in dirs.split(",")]
            for dirn in self.stormdirs:
                self.find_storm_files(dirn)

    def find_storm_files(self, dirn):
        rx = r"^[^#~!$@%^&*()+=,]+\.(" + "|".join(self.extensions) + r")$"
        for (dirpath, dirnames, filenames) in os.walk(dirn):
            for filename in filenames:
                if regex.search(rx, filename):
                    path = os.path.join(dirpath, filename)
                    with open(path, "r") as f:
                        source = f.read()
                        tree = self.parser.parse(source)
                        guid = s_common.guid(str(tree))
                        self.guid_map[guid] = os.path.abspath(path)

    def file_tracer(self, filename):
        if filename.endswith('synapse/lib/ast.py'):
            return self
        if filename.endswith('synapse/lib/stormctrl.py'):
            return StormCtrlTracer(self)
        return None

    def file_reporter(self, filename):
        return FileReporter(filename, self.parser)

    def find_executable_files(self, src_dir):
        rx = r"^[^#~!$@%^&*()+=,]+\.(" + "|".join(self.extensions) + r")$"
        for (dirpath, dirnames, filenames) in os.walk(src_dir):
            for filename in filenames:
                if regex.search(rx, filename):
                    path = os.path.join(dirpath, filename)
                    yield path

    def has_dynamic_source_filename(self):
        return True

    def _parent_node(self, node):
        if not hasattr(node, 'parent'):
            return node
        return self._parent_node(node.parent)

    PARSE_METHODS = {"compute", "once"}

    def dynamic_source_filename(self, filename, frame, force=False):
        if frame.f_code.co_name not in self.PARSE_METHODS and not force:
            return None

        node = frame.f_locals.get('self')
        pnode = self._parent_node(node)
        filename = self.node_map.get(id(pnode), s_common.novalu)
        if filename is not s_common.novalu:
            return filename

        if not pnode.__class__.__name__ == 'Query':
            self.node_map[id(pnode)] = None
            return

        filename = self.text_map.get(pnode.text)
        if filename:
            return filename

        tree = self.parser.parse(pnode.text)
        guid = s_common.guid(str(tree))
        filename = self.guid_map.get(guid)

        self.node_map[id(pnode)] = filename
        self.text_map[pnode.text] = filename
        return filename

    def line_number_range(self, frame):
        return frame.f_locals.get('self').lines

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

SHOW_PARSING = False

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
    '_EMIT',
    '_STOP',
    '_RETURN',
]

class FileReporter(coverage.FileReporter):
    def __init__(self, filename, parser):
        super().__init__(filename)

        self._parser = parser
        self._source = None

    def source(self):
        if self._source is None:
            try:
                with open(self.filename, "r") as f:
                    self._source = f.read()

            except (OSError, UnicodeError) as exc:
                raise NoSource(f"Couldn't read {self.filename}: {exc}")
        return self._source

    def lines(self):
        source_lines = set()

        if SHOW_PARSING:
            print(f"-------------- {self.filename}")

        tree = self._parser.parse(self.source())

        for token in tree.scan_values(lambda v: isinstance(v, lark.lexer.Token)):
            if token.type not in TOKENS:
                continue

            if SHOW_PARSING:
                print("%20s %2d: %r" % (token.type, token.line, token.value))

            if token.line == token.end_line:
                source_lines.add(token.line)
            else:
                source_lines.update(range(token.line, token.end_line + 1))

            if SHOW_PARSING:
                print(f"\t\t\tNow source_lines is: {source_lines!r}")

        return source_lines
