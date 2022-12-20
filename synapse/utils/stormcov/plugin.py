import os
import lark
import regex
import coverage

import synapse.common as s_common

import synapse.lib.ast as s_ast
import synapse.lib.parser as s_parser
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

        self.text_map = {}
        self.query_map = {}
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
                        self.query_map[guid] = os.path.abspath(path)

    def file_tracer(self, filename):
        if filename.endswith('synapse/lib/ast.py'):
            return self
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

    def _parent_text(self, node):
        if not hasattr(node, 'parent'):
            return node.text
        return self._parent_text(node.parent)

    PARSE_METHODS = {"run", "compute"}

    def dynamic_source_filename(self, filename, frame):
        if frame.f_code.co_name not in self.PARSE_METHODS:
            return None

        node = frame.f_locals.get('self')
        text = self._parent_text(node)
        filename = self.text_map.get(text)
        if filename:
            return filename

        tree = self.parser.parse(text)
        guid = s_common.guid(str(tree))
        filename = self.query_map.get(guid)
        self.text_map[text] = filename
        return filename

    def line_number_range(self, frame):
        if frame.f_code.co_name not in self.PARSE_METHODS:
            return (-1, -1)

        return frame.f_locals.get('self').lines

SHOW_PARSING = False

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
            if token.type not in s_parser.terminalClassMap:
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

def dump_frame(frame, label=""):
    """Dump interesting information about this frame."""
    locals = dict(frame.f_locals)
    self = locals.get('self', None)
    context = locals.get('context', None)
    if "__builtins__" in locals:
        del locals["__builtins__"]

    if label:
        label = " ( %s ) " % label
    print("-- frame --%s---------------------" % label)
    print("{}:{}:{}".format(
        os.path.basename(frame.f_code.co_filename),
        frame.f_lineno,
        type(self),
        ))
    print(locals)
    if self:
        print("self:", self.__dict__)
    if context:
        print("context:", context.__dict__)
    print("\\--")
