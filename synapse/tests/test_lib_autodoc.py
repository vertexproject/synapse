import copy
import textwrap

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.parser as s_parser
import synapse.lib.autodoc as s_autodoc
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.files as s_t_files
import synapse.tests.utils as s_t_utils

class _FakeDocHelp:
    '''
    A minimal stand-in for autodoc.DocHelp, for tests that exercise a single
    processXMd() function directly with hand-built data rather than a live
    Cortex's full data model.
    '''
    def __init__(self, ctors=None, types=None, forms=None, formhelp=None, props=None):
        self.ctors = ctors or {}
        self.types = types or {}
        self.forms = forms or {}
        self.formhelp = formhelp or {}
        self.props = props or {}

class _ExtendedDescConfCell(s_cell.Cell):
    confdefs = {
        'extra': {
            'type': 'string',
            'default': 'stuff',
            'description': 'An extra option.',
            'extended_description': 'This option has additional detail beyond the summary line.',
        },
    }

class _FakeTelepathApi:
    '''
    A fake API class.

    Used only to exercise docApiMd() against a hand-written Google-style
    docstring, mirroring the shape of a real CellApi subclass without the
    overhead of standing one up.
    '''

    async def has(self, sha256):
        '''
        Check if a file is present.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Returns:
            boolean: True if the file is present; false otherwise.
        '''
        return True

    async def get(self, sha256, *, offs=None):
        '''
        Get bytes of a file.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.
            offs (int): The offset to start reading from.

        Yields:
            bytes: Chunks of the file bytes.

        Raises:
            synapse.exc.NoSuchFile: If the file does not exist.
        '''
        yield b''

    async def cancel(self, iden, timeout=None):
        '''
        Send a cancel request.

        Args:
            iden (str): The iden of the channel.
            timeout (int): Optional timeout in seconds.

        Returns:
            bool, str: Whether the cancel request was successfully sent and a message.
        '''
        return True, 'ok'

    def status(self):
        '''No frills status, with no sections at all.'''
        return {}

    async def example(self):
        '''
        A method with an Examples section.

        Examples:

            Get the bytes from an Axon and process them::

                buf = b''
                async for bytz in axon.get(sha256):
                    buf += bytz
        '''
        return None

    async def undocumented(self, x):
        return x

    async def _private(self):
        '''Not part of the public API and must never be documented.'''
        return None

class AutodocTest(s_t_utils.SynTest):

    def test_autodoc_rsthelp(self):

        page = s_autodoc.RstHelp()

        page.addHead('test', lvl=0, link='fakeLink')
        page.addLines('test', 'words\n go', 'here')
        page.addHead('burma', lvl=1)
        page.addLines('burma', 'shave')
        text = page.getRstText()
        expected = '''

fakeLink

####
test
####

test
words\n go
here

*****
burma
*****

burma
shave'''
        self.eq(text, expected)

    def test_autodoc_helpers(self):

        # callsig
        rtype = {
            'args': (
                {'name': 'foo',
                 'type': 'str',
                 'desc': 'The foos!'},
                {'name': 'bar',
                 'type': ['str', 'int'],
                 'desc': 'The bar.',
                 'default': None},
                {'name': '**kwargs',
                 'type': 'any',
                 'desc': 'Extra foobars.',
                 },
            )
        }
        callsig = s_autodoc.genCallsig(rtype)
        self.eq(callsig, '(foo, bar=(null), **kwargs)')
        self.eq(s_autodoc.genCallsig({}), '()')
        self.eq(s_autodoc.genCallsig({'args': ({'name': 'beep'},)}), '(beep)')

        # prepare lines
        text = '''
        Hello

        Notes:
            Beep beep goes the docs

        Examples:
            Words!::

                example stuff
        '''
        lines = s_autodoc.prepareRstLines(text)
        self.eq(lines, ['Hello', '', 'Notes:', '    Beep beep goes the docs', '', 'Examples:',
                        '    Words!::', '', '        example stuff', ''])

    def test_autodoc_callsig_defaults(self):

        def callsig(defv):
            return s_autodoc.genCallsig({'args': ({'name': 'types', 'default': defv},)})

        # scalar defaults are rendered as their storm literals
        self.eq('(types=(null))', callsig(None))
        self.eq('(types=(true))', callsig(True))
        self.eq('(types=(false))', callsig(False))
        self.eq('(types=(10))', callsig(10))

        # a string is always quoted. a bare token is valid storm for many values but
        # not all of them, and an unquoted "=" renders as the confusing types==
        self.eq("(types='A')", callsig('A'))
        self.eq("(types='=')", callsig('='))
        self.eq("(types='')", callsig(''))
        self.eq("(types=' ')", callsig(' '))
        self.eq("(types='hello world')", callsig('hello world'))
        self.eq("(types='a,b')", callsig('a,b'))

        # $lib.undef is declared as a string but documents the undef constant, which
        # is a variable reference rather than a value, so it stays bare
        self.eq('(types=$lib.undef)', callsig('$lib.undef'))

        # a single quoted storm string is raw, so a value holding a single quote uses
        # the double quoted form. the triple quoted form is raw too, so it could not
        # hold a value containing ''' or ending in a single quote.
        self.eq('(types="it\'s here")', callsig("it's here"))
        self.eq('(types="it\'s \'\'\'here\'\'\'")', callsig("it's '''here'''"))
        self.eq('(types="ends with quote\'")', callsig("ends with quote'"))

        # a control character is only representable in the double quoted form, so
        # it never reaches the docs as itself and never breaks the rendered heading
        self.eq('(types="\\n")', callsig('\n'))
        self.eq('(types="\\r\\n")', callsig('\r\n'))
        self.eq('(types="\\u0001")', callsig('\x01'))
        self.eq('(types="a\\\\b\\n")', callsig('a\\b\n'))
        self.eq('(types="a\\"b\\n")', callsig('a"b\n'))

        # a double quote is raw in the single quoted form and escaped in the other
        self.eq("(types='say \"hi\"')", callsig('say "hi"'))
        self.eq('(types="it\'s \\"quoted\\"")', callsig('it\'s "quoted"'))

        self.eq("(types=('hello world',))", callsig(['hello world']))
        self.eq("(types=('', 'A'))", callsig(['', 'A']))
        self.eq('(types=("it\'s here",))', callsig(["it's here"]))

        # a list default is rendered as a storm list literal. a single item
        # list requires the trailing comma, since ('A') is not a list.
        self.eq("(types=('A',))", callsig(['A']))
        self.eq("(types=('A', 'AAAA'))", callsig(['A', 'AAAA']))
        self.eq('(types=())', callsig([]))
        self.eq("(types=('A', (null), (true), (1)))", callsig(['A', None, True, 1]))

        # the docs are rendered from the msgpack deepcopy of the declaration,
        # which converts the declared list back into a tuple.
        self.eq("(types=('A',))", callsig(('A',)))
        self.eq("(types=('A', 'AAAA'))", callsig(('A', 'AAAA')))

        # everything genCallsig() renders must be valid storm
        for defv in (None, True, False, 10, 'A', ['A'], ['A', 'AAAA'], [], ['A', None, True, 1],
                     '', ' ', '=', 'hello world', 'a,b', '\n', '\x01', 'a\\b\n', 'a"b\n', "it's here",
                     [''], ['='], ['hello world'], ['\n'], ["it's here"]):
            s_parser.parseQuery(f'function foo{callsig(defv)} {{ }}')

        with self.raises(s_exc.BadArg):
            callsig({'newp': 'newp'})

    def test_autodoc_callsig_str_roundtrip(self):

        # Rendering a string default is total rather than an enumeration of the cases
        # someone has thought of, so assert the property directly: every string comes
        # back out of the parser as itself. parseEval() returns the decoded Const.

        # every codepoint that can stand alone, including the control characters and
        # both quote characters
        valus = [chr(indx) for indx in range(0x0300)]
        valus.extend(('\U0001f600', '￿'))

        # the delimiters of each storm string form, alone and embedded
        valus.extend(("'", "''", "'''", '"', '""', '"""', '\\', '\\\\',
                      "it's here", "it's '''here'''", "ends with quote'",
                      'trailing backslash\\', '"""\'\'\'"""', 'say "hi" now'))

        # values that are syntax in some other storm context
        valus.extend(('$lib.undef', '$foo', '${foo}', '`backtick`', '{brace}', '(paren)',
                      '=', ',', '', ' ', 'a,b', 'hello world'))

        # every pairing of the characters that terminate or escape a literal
        valus.extend([a + b for a in ('"', "'", '\\', '\n') for b in ('"', "'", '\\', 'x')])

        for valu in valus:
            text = s_autodoc._genCallsigStr(valu)

            # the undef constant is a variable reference, not a string literal
            if valu == '$lib.undef':
                self.eq('$lib.undef', text)
                continue

            self.eq(valu, s_parser.parseEval(text).valu)

    def test_autodoc_schema_defaults(self):

        def doc(defv):
            return {
                'path': ('lib', 'test'),
                'desc': 'A test library.',
                'locals': [
                    {'name': 'lookup', 'desc': 'Look it up.',
                     'type': {'type': 'function', '_funcname': 'lookup',
                              'args': ({'name': 'types', 'type': 'list', 'default': defv,
                                        'desc': 'The types to look up.'},),
                              'returns': {'type': 'list', 'desc': 'The records.'}}},
                ],
            }

        # scalar defaults and arrays of scalars are valid
        for defv in (None, True, False, 10, 'A', ['A'], ['A', 'AAAA'], [], ('A',), ('A', None, True, 1)):
            s_autodoc.reqValidStormTypeDoc(doc(defv))

        # a default may not contain nested containers
        for defv in ([['A']], [{'newp': 'newp'}], {'newp': 'newp'}):
            with self.raises(s_exc.SchemaViolation):
                s_autodoc.reqValidStormTypeDoc(doc(defv))

    def test_mdslugify(self):
        self.eq('hello-world', s_autodoc.mdSlugify('Hello World'))
        self.eq('inet-fqdn', s_autodoc.mdSlugify('inet:fqdn'.replace(':', ' ')))
        seen = {}
        self.eq('dup', s_autodoc.mdSlugify('dup', seen))
        self.eq('dup-1', s_autodoc.mdSlugify('dup', seen))
        self.eq('dup-2', s_autodoc.mdSlugify('dup', seen))

    def test_mdhelp_addhead_with_anchor(self):
        page = s_autodoc.MdHelp()
        page.addHead('Types', lvl=0, anchor='dm-types')
        page.addHead('inet:fqdn', lvl=1, anchor='dm-type-inet-fqdn')
        page.addLines('Some body text.')
        text = page.getMdText()
        self.isin('<a id="dm-types"></a>', text)
        self.isin('# Types', text)
        self.isin('<a id="dm-type-inet-fqdn"></a>', text)
        self.isin('## inet:fqdn', text)
        self.isin('Some body text.', text)

    def test_mdhelp_addhead_no_anchor(self):
        page = s_autodoc.MdHelp()
        page.addHead('No Anchor', lvl=0)
        text = page.getMdText()
        self.notin('<a id=', text)
        self.isin('# No Anchor', text)

    def test_getmdlink_and_ref(self):
        anchorid = s_autodoc.getMdLink('inet:fqdn', 'dm-type')
        self.eq('dm-type-inet-fqdn', anchorid)

        anchorid_suffixed = s_autodoc.getMdLink('inet:fqdn', 'stormprims', suffix='f527')
        self.eq('stormprims-inet-fqdn-f527', anchorid_suffixed)

        ref = s_autodoc.mdRef('inet:fqdn', anchorid)
        self.eq('[`inet:fqdn`](#dm-type-inet-fqdn)', ref)

        xref = s_autodoc.mdRef('inet:fqdn', anchorid, mdfile='datamodel_types.md')
        self.eq('[`inet:fqdn`](datamodel_types.md#dm-type-inet-fqdn)', xref)

    def test_getreturnlinesmd_and_getarglinesmd(self):
        rtype = {'type': 'function', '_funcname': 'foo',
                 'args': ({'name': 'x', 'desc': 'the x', 'type': 'str'},),
                 'returns': {'type': 'int', 'desc': 'the answer'}}
        arglines = s_autodoc.getArgLinesMd(rtype)
        self.isin('- `x` (`str`): the x', '\n'.join(arglines))

        retlines = s_autodoc.getReturnLinesMd(rtype)
        self.isin('**Returns:**', '\n'.join(retlines))
        self.isin('the answer', '\n'.join(retlines))

    def test_gendeprecationwarningmd(self):
        depr = {'eolvers': '3.0.0', 'mesg': 'use $lib.newthing instead.'}
        lines = s_autodoc.genDeprecationWarningMd('$lib.oldthing', depr)
        text = '\n'.join(lines)
        self.isin('> **Warning:**', text)
        self.isin('has been deprecated and will be removed in version 3.0.0', text)
        self.isin('use $lib.newthing instead.', text)

        depr2 = {'eoldate': '8080-08-08'}
        lines2 = s_autodoc.genDeprecationWarningMd('$lib.olderthing', depr2)
        text2 = '\n'.join(lines2)
        self.isin('has been deprecated and will be removed on or after 8080-08-08.', text2)

    def test_getrtypestrmd(self):
        known = {'inet:fqdn'}
        s = s_autodoc.getRtypeStrMd('inet:fqdn', known, 'dm-type', None)
        self.eq(s, '[`inet:fqdn`](#dm-type-inet-fqdn)')

        s2 = s_autodoc.getRtypeStrMd('str', known, 'dm-type', None)
        self.eq(s2, '`str`')

    def test_getarglinesmd_variants(self):
        self.eq(s_autodoc.getArgLinesMd({}), [])

        rtype = {'args': (
            {'name': 'foo', 'type': 'str', 'desc': 'The foos!'},
            {'name': 'bar', 'type': ['str', 'int'], 'desc': 'The bar.'},
            {'name': 'cmplx', 'type': {}, 'desc': 'unsupported'},
        )}
        lines = s_autodoc.getArgLinesMd(rtype)
        text = '\n'.join(lines)
        self.isin('- `foo` (`str`): The foos!', text)
        self.isin('- `bar`: The bar. The input type may be one of the following: `str`, `int`.', text)
        self.isin('- `cmplx`: unsupported The input type is derived from the declarative type `{}`.', text)

        with self.raises(s_exc.BadArg):
            s_autodoc.getArgLinesMd({'args': ({'name': 'newp', 'type': 1234, 'desc': 'newp'},)})

    def test_getreturnlinesmd_variants(self):
        lines = s_autodoc.getReturnLinesMd('str')
        text = '\n'.join(lines)
        self.isin('**Returns:**', text)
        self.isin('The type is `str`.', text)

        lines = s_autodoc.getReturnLinesMd(('str', 'int'))
        text = '\n'.join(lines)
        self.isin('The type may be one of the following: `str`, `int`.', text)

        lines = s_autodoc.getReturnLinesMd({'returns': {'type': ['str', 'bool']}})
        text = '\n'.join(lines)
        self.isin('The return type may be one of the following: `str`, `bool`.', text)

        lines = s_autodoc.getReturnLinesMd({'returns': {'type': {}}})
        text = '\n'.join(lines)
        self.isin('The return type is derived from the declarative type `{}`.', text)

        lines = s_autodoc.getReturnLinesMd({'returns': {'type': 'str'}}, isstor=True)
        text = '\n'.join(lines)
        self.isin('When this is used to set the value, it does not have a return type.', text)

        with self.raises(s_exc.BadArg):
            s_autodoc.getReturnLinesMd({'returns': {'type': 1234}})

        # A full type-definition dict missing its 'returns' key is a genuine
        # upstream data bug and must raise loudly, not silently fall back to
        # treating the outer dict as the returns spec.
        with self.raises(s_exc.BadArg):
            s_autodoc.getReturnLinesMd({'type': 'function', 'args': ()})

    def test_preparemdlines(self):
        text = '''
        Hello

        Notes:
            Beep beep goes the docs
        '''
        lines = s_autodoc.prepareMdLines(text)
        self.eq(lines, ['Hello', '', 'Notes:', '    Beep beep goes the docs', ''])

    def test_docstormtypesmd_lib(self):
        # Exercise docStormTypesMd directly (not through the registry-level
        # wrappers) so the known_types=None default-init branch and the
        # per-local deprecation-warning branches (a locl-level 'deprecated'
        # key, and a library-level 'deprecated' key applied to a
        # non-deprecated locl) are hit.
        libtst = s_t_utils.LibTst

        locls = copy.deepcopy(libtst._storm_locals)
        [obj.get('type', {}).pop('_funcname', None) for obj in locls]
        doc = {
            'desc': s_stormtypes.getDoc(libtst, "err"),
            'path': ('lib',) + libtst._storm_lib_path,
            'locals': locls,
        }
        md = s_autodoc.MdHelp()
        md.addHead('Test', lvl=0)
        md.addLines('I am a line.')
        # known_types omitted entirely -- hits the `if known_types is None`
        # default-init branch.
        s_autodoc.docStormTypesMd(md, (doc,), linkprefix='test')
        text = md.getMdText()

        self.isin('# Test', text)
        self.isin('lib.test', text)
        self.isin('> **Warning:**', text)
        self.isin('`$lib.test.beep` has been deprecated and will be removed on or after 8080-08-08.', text)
        self.isin('`$lib.test.someargs` has been deprecated and will be removed in version v3.0.0.', text)

        # Now as a library, with a library-level (not locl-level) deprecation,
        # to hit the `elif libdepr is not None` branch for a locl that has no
        # 'deprecated' key of its own.
        libdepr = s_t_utils.LibDepr
        locls = copy.deepcopy(libdepr._storm_locals)
        [obj.get('type', {}).pop('_funcname', None) for obj in locls]
        doc = {
            'desc': s_stormtypes.getDoc(libdepr, "err"),
            'path': ('lib',) + libdepr._storm_lib_path,
            'locals': locls,
            'deprecated': libdepr._storm_lib_deprecation,
        }
        md = s_autodoc.MdHelp()
        s_autodoc.docStormTypesMd(md, (doc,), linkprefix='test', islib=True, known_types=None)
        text = md.getMdText()

        self.isin('$lib.depr', text)
        self.isin('$lib.depr.boop', text)
        self.isin('> **Warning:**', text)
        self.isin('`$lib.depr.boop` has been deprecated and will be removed in version v3.0.0.', text)

    def test_parseapidocstring_empty(self):
        self.eq(('', []), s_autodoc.parseApiDocstring(''))
        self.eq(('', []), s_autodoc.parseApiDocstring(None))

    def test_parseapidocstring_summary_only(self):
        summary, sections = s_autodoc.parseApiDocstring('Just a summary line.')
        self.eq('Just a summary line.', summary)
        self.eq([], sections)

    def test_parseapidocstring_multiple_sections(self):
        doc = '\n'.join((
            'Summary line.',
            '',
            'Args:',
            '    x (int): the x value.',
            '',
            'Returns:',
            '    int: the result.',
        ))
        summary, sections = s_autodoc.parseApiDocstring(doc)
        self.eq('Summary line.', summary)
        self.eq(['Args', 'Returns'], [head for head, _ in sections])

    def test_apisectionitems_continuation_line(self):
        # a wrapped description line, indented further than the item's own
        # first line, folds into that item's desc rather than becoming a
        # separate (unparseable) item
        lines = [
            '    x (int): the x value',
            '        that wraps onto a second line.',
        ]
        items = s_autodoc._apiSectionItems(lines)
        self.len(1, items)
        self.eq('the x value that wraps onto a second line.', items[0]['desc'])

    def test_apisectionitems_unparseable_line_before_any_item(self):
        # a line that never matches "name: desc" and precedes any item is dropped
        lines = ['not a valid item line at all']
        self.eq([], s_autodoc._apiSectionItems(lines))

    def test_apisectionitems_unparseable_line_after_item(self):
        # an unparseable, same-or-lesser-indent line after an item folds
        # into that item's desc rather than being dropped
        lines = [
            'x (int): the x value.',
            'a stray line with no colon',
        ]
        items = s_autodoc._apiSectionItems(lines)
        self.len(1, items)
        self.eq('the x value. a stray line with no colon', items[0]['desc'])

    def test_renderapireturnmd_unexpected_name_and_type(self):
        # "name (type): desc" is not the expected Returns/Yields shape (no
        # bare name expected), but renders faithfully rather than dropping the type
        lines = ['thing (int): an unexpected named+typed return.']
        rendered = s_autodoc.renderApiReturnMd(lines)
        self.eq(['*thing (int)*: an unexpected named+typed return.'], rendered)

    def test_renderapipassthroughmd_trims_blank_lines(self):
        lines = ['', '', 'Some example text.', '', 'More text.', '', '']
        rendered = s_autodoc.renderApiPassthroughMd(lines)
        self.eq(['> Some example text.', '>', '> More text.'], rendered)

    def test_process_interfaces_md(self):
        md = s_autodoc.MdHelp()
        s_autodoc.processInterfacesMd(md, [
            ('no:doc', {}),
            ('has:doc', {'doc': 'Has a doc string.'}),
        ])
        s = md.getMdText()
        self.isin('The `no:doc` interface.', s)
        self.isin('Has a doc string.', s)

    def test_dochelp_formhelp_ctor_only_form(self):
        # a form built directly from a base ctor (e.g. a bare guid/str form)
        # has no separate entry in the model's "types" dict -- formhelp must
        # fall back to the ctor's own "ex", not just a derived type's.
        ctors = [('test:ctor', 'synapse.tests.utils.TestType', {}, {'ex': 'ctorexample'})]
        types = {}
        forms = [('test:ctor', {}, [])]
        dochelp = s_autodoc.DocHelp(ctors, types, forms, {})
        self.eq('ctorexample', dochelp.formhelp['test:ctor'])

    def test_process_ctors_md(self):
        md = s_autodoc.MdHelp()
        dochelp = _FakeDocHelp(ctors={'test:ctor': 'Docstring missing a period'})
        ctors = [
            ('test:ctor', 'synapse.tests.utils.TestType', {}, {}),
        ]
        types = {'test:ctor': {'virts': None, 'lift_cmprs': ()}}
        s_autodoc.processCtorsMd(md, dochelp, ctors, types)
        s = md.getMdText()
        self.isin('Docstring missing a period.', s)

    def test_process_types_md(self):
        md = s_autodoc.MdHelp()
        dochelp = _FakeDocHelp(types={'test:type': 'Docstring missing a period'})
        types = {
            'test:type': {'info': {'bases': ['test:ctorbase']}},
        }
        s_autodoc.processTypesMd(md, dochelp, types)
        s = md.getMdText()
        self.isin('Docstring missing a period.', s)

    def test_lookupedgesforform_all_branches(self):
        # src/dst may each be None, == form, or != form -- 9 states, per the
        # table in lookupedgesforform's docstring comment.
        generic = ((None, 'generic', None), {})
        src_none_dst_other = ((None, 'srcnonedstother', 'other:form'), {})
        src_none_dst_form = ((None, 'srcnonedstform', 'test:form'), {})
        src_other_dst_none = (('other:form', 'srcotherdstnone', None), {})
        src_form_dst_none = (('test:form', 'srcformdstnone', None), {})
        src_other_dst_form = (('other:form', 'srcotherdstform', 'test:form'), {})
        src_form_dst_other = (('test:form', 'srcformdstother', 'other:form'), {})
        src_other_dst_other = (('other:form', 'srcotherdstother', 'other:form'), {})
        src_form_dst_form = (('test:form', 'srcformdstform', 'test:form'), {})

        edges = [generic, src_none_dst_other, src_none_dst_form, src_other_dst_none,
                src_form_dst_none, src_other_dst_form, src_form_dst_other,
                src_other_dst_other, src_form_dst_form]

        ret = s_autodoc.lookupedgesforform('test:form', edges)

        self.eq(ret['generic'], [generic])
        self.eq(ret['source'], [src_none_dst_other, src_form_dst_none, src_form_dst_other, src_form_dst_form])
        self.eq(ret['target'], [src_none_dst_form, src_other_dst_none, src_other_dst_form, src_form_dst_form])
        # src != form and dst != form is a no-op -- appears in neither list
        self.notin(src_other_dst_other, ret['source'])
        self.notin(src_other_dst_other, ret['target'])

    def test_process_forms_props_md(self):
        md = s_autodoc.MdHelp()
        dochelp = _FakeDocHelp(forms={'test:form': 'Docstring missing a period'})
        forms = [('test:form', {}, [])]
        alledges = [
            (('test:form', 'refs', None), {'doc': 'An edge.', 'extra': 'unhandled'}),
        ]
        s_autodoc.processFormsPropsMd(md, dochelp, forms, alledges)
        s = md.getMdText()
        self.isin('Docstring missing a period.', s)
        self.isin('**Source Edges:**', s)
        self.isin('| `test:form` | `-(refs)>` | `*` | An edge. |', s)

class AutodocMdGeneratorsTest(s_t_utils.SynTest):

    async def test_docmodeltypesmd(self):
        async with self.getTestCore() as core:
            typesmd = await s_autodoc.docModelTypesMd(core)
            typestext = typesmd.getMdText()

            self.isin('# Synapse Data Model - Types', typestext)
            self.isin('## Base Types', typestext)
            self.isin('## Types', typestext)
            self.isin('## Interfaces', typestext)
            self.isin('<a id="dm-type-inet-fqdn"></a>', typestext)

    async def test_docmodelformsmd(self):
        async with self.getTestCore() as core:
            formsmd = await s_autodoc.docModelFormsMd(core)
            formstext = formsmd.getMdText()

            self.isin('# Synapse Data Model - Forms', formstext)
            self.isin('## Forms', formstext)
            self.isin('<a id="dm-form-inet-fqdn"></a>', formstext)
            # a form links back to its type definition in the sibling file
            self.isin(f'({s_autodoc._TYPES_MD_FILE}#dm-type-inet-fqdn)', formstext)

    async def test_docmodelformsmd_form_properties_table(self):
        async with self.getTestCore() as core:
            formsmd = await s_autodoc.docModelFormsMd(core)
            text = formsmd.getMdText()

            self.isin('| name | type | doc |', text)
            self.isin('| `:zone` |', text)

    async def test_docconfdefsmd(self):
        confdocs = await s_autodoc.docConfdefsMd('synapse.cortex.Cortex')
        text = confdocs.getMdText()
        self.isin('###', text)  # at least one h3-level conf entry heading
        self.isin('**Type**', text)

    async def test_docconfdefsmd_properties_and_negatives(self):
        confdocs = await s_autodoc.docConfdefsMd(
            'synapse.tests.test_lib_stormsvc.StormvarServiceCell')
        text = confdocs.getMdText()

        self.isin('### some:obj', text)
        self.isin('**Properties**', text)
        self.isin('The object expects the following properties', text)
        self.isin('```json', text)

        self.isin('### auth:passwd', text)
        self.isin('**Environment Variable**', text)
        self.isin('`SYN_STORMVARSERVICECELL_AUTH_PASSWD`', text)

        self.notin('`--mirror`', text)
        self.notin('SYN_STORMVARSERVICECELL_CELL_GUID', text)

    async def test_docconfdefsmd_extended_description(self):
        confdocs = await s_autodoc.docConfdefsMd(
            'synapse.tests.test_lib_autodoc._ExtendedDescConfCell')
        text = confdocs.getMdText()

        self.isin('This option has additional detail beyond the summary line.', text)

    async def test_docconfdefsmd_missing_confdefs_attr(self):
        with self.raises(s_exc.BadArg):
            await s_autodoc.docConfdefsMd('synapse.exc.SynErr')

    async def test_docapimd(self):
        apidocs = await s_autodoc.docApiMd('synapse.tests.test_lib_autodoc._FakeTelepathApi')
        text = apidocs.getMdText()

        # class-level docstring summary
        self.isin('A fake API class.', text)

        # methods are rendered in sorted order, each with its own heading + anchor
        idx_cancel = text.index('## cancel')
        idx_example = text.index('## example')
        self.lt(idx_cancel, idx_example)

        # self is stripped from the rendered signature
        self.isin('## cancel(iden, timeout=None)', text)
        self.isin('## get(sha256, *, offs=None)', text)
        self.notin('## get(self, sha256', text)

        # private methods are never documented, regardless of docstring
        self.notin('_private', text)
        self.notin('Not part of the public API', text)

        # Args section renders as a bullet list with type in parens
        self.isin('**Args**', text)
        self.isin('- **sha256** (*bytes*): The sha256 hash of the file in bytes.', text)
        self.isin('- **offs** (*int*): The offset to start reading from.', text)

        # Returns section renders without a bullet/bold parameter name
        self.isin('**Returns**', text)
        self.isin('*boolean*: True if the file is present; false otherwise.', text)

        # Yields section (async generator method) renders the same way as Returns
        self.isin('**Yields**', text)
        self.isin('*bytes*: Chunks of the file bytes.', text)

        # Raises section omits the type parens entirely
        self.isin('**Raises**', text)
        self.isin('- **synapse.exc.NoSuchFile**: If the file does not exist.', text)

        # a method with no docstring at all still gets a heading
        self.isin('## undocumented(x)', text)
        self.isin('No description available.', text)

        # a docstring with no recognized sections is rendered as a plain summary
        self.isin('No frills status, with no sections at all.', text)

        # an Examples section falls back to a blockquote passthrough
        self.isin('**Examples**', text)
        self.isin('> Get the bytes from an Axon and process them::', text)

    async def test_docapimd_anchor_and_class_doc(self):
        apidocs = await s_autodoc.docApiMd('synapse.tests.test_lib_autodoc._FakeTelepathApi')
        text = apidocs.getMdText()

        self.isin('<a id="api-get"></a>', text)
        self.isin('<a id="api-has"></a>', text)

    async def test_docapimd_multiple_returns_types(self):
        apidocs = await s_autodoc.docApiMd('synapse.tests.test_lib_autodoc._FakeTelepathApi')
        text = apidocs.getMdText()

        # "bool, str: ..." has no parenthesized type, so the whole
        # "bool, str" label (spaces and all) is taken as the type.
        self.isin('*bool, str*: Whether the cancel request was successfully sent and a message.', text)

    async def test_docapimd_not_a_class(self):
        with self.raises(s_exc.BadArg):
            await s_autodoc.docApiMd('synapse.common.now')

    def test_stripselffromsignature_no_self(self):
        # a signature that never had "self" (e.g. a staticmethod) is returned unchanged
        self.eq('(x, y)', s_autodoc._stripSelfFromSignature('(x, y)'))
        self.eq('(x)', s_autodoc._stripSelfFromSignature('(self, x)'))
        self.eq('()', s_autodoc._stripSelfFromSignature('(self)'))

    async def test_processstormcmdsmd_and_modulesmd_perms_and_deprecated(self):
        ymlpath = s_t_files.getAssetPath('stormpkg/testpkg.yaml')
        pkgdef = s_common.yamlload(ymlpath)

        md = s_autodoc.MdHelp()
        await s_autodoc.processStormCmdsMd(md, 'foo', pkgdef.get('commands'))
        text = md.getMdText()

        exp = textwrap.dedent('''\
            The command is accessible to users with one or more of the following permissions:

            - `power-ups.testpkg.admin`
            - `power-ups.testpkg.user`
        ''').rstrip()
        self.isin(exp, text)

        md = s_autodoc.MdHelp()
        await s_autodoc.processStormModulesMd(md, 'foo', pkgdef.get('modules'))
        text = md.getMdText()

        self.isin('newp()', text)
        self.isin('`newp` has been deprecated and will be removed in version v2.300.4.', text)
        self.isin('Newp is no longer maintained. Use bar() instead.', text)

        # coverage for no apidefs
        md = s_autodoc.MdHelp()
        await s_autodoc.processStormModulesMd(md, 'foo', [])
        self.isin('This package does not export any Storm APIs.', md.getMdText())

    async def test_docstormpkgmd(self):
        ymlpath = s_t_files.getAssetPath('stormpkg/testpkg.yaml')
        pkgdocs = await s_autodoc.docStormpkgMd(ymlpath)
        text = pkgdocs.getMdText()

        self.isin('# Storm Package: testpkg', text)

        # Dependencies, rendered as a markdown pipe table.
        self.isin('## Dependencies', text)
        self.isin('This package depends on the following packages.', text)
        self.isin('| Name | Version | Optional | Description |', text)
        self.isin('| synapse | >=3.0.0,<4.0.0 | no |  |', text)
        self.isin(
            '| testpkg-optdep | >=1.0.0,<2.0.0 | yes | Optional dependency used to enrich '
            'testpkg nodes with additional metadata. |', text)

        self.isin('This package implements the following Storm Commands.', text)
        self.isin('<a id="stormcmd-testpkg-testpkgcmd"></a>', text)
        self.isin('testpkgcmd does some stuff', text)

        self.isin('This package implements the following Storm Modules.', text)
        self.isin('<a id="stormmod-testpkg-apimod"></a>', text)
        self.notin('testmod', text)

        # modconf.endpoints, grouped by resolved base URL, at the bottom of
        # the doc, rendered as a markdown pipe table.
        self.isin('## Endpoints', text)
        self.isin('This package communicates with the following API endpoints.', text)
        self.isin('| Path | Description |', text)

        self.isin('### https://api.example.com', text)
        self.isin('| /v1/search | Run a search. |', text)

        self.isin('### https://enrich.example.com', text)
        self.isin('| /v1/enrich/{iden} | Enrich an item. |', text)

        self.isin('### (user-configured base URL)', text)
        self.isin('| /v1/noconf | An endpoint with no configured base. |', text)

        # coverage for no endpoints
        md = s_autodoc.MdHelp()
        await s_autodoc.processModEndpointsMd(md, 'foo', {})
        self.eq('', md.getMdText())

        # coverage for an endpoint with no desc
        md = s_autodoc.MdHelp()
        await s_autodoc.processModEndpointsMd(md, 'foo', {
            'nodesc': {'path': '/v1/nodesc'},
        })
        mdtext = md.getMdText()
        self.isin('| /v1/nodesc |  |', mdtext)

        # coverage for docStormpkgMd with no dependencies/commands/modules
        with self.getTestDir() as dirn:
            pkgpath = s_common.genpath(dirn, 'nodeps.yaml')
            s_common.yamlsave({'name': 'nodeps', 'version': '0.0.1'}, pkgpath)

            pkgdocs = await s_autodoc.docStormpkgMd(pkgpath)
            text = pkgdocs.getMdText()
            self.isin('# Storm Package: nodeps', text)
            self.notin('## Dependencies', text)
            self.notin('## Storm Commands', text)
            self.notin('## Storm Modules', text)
            self.notin('## Endpoints', text)

    async def test_docstormtypeslibsmd(self):
        libspage = await s_autodoc.docStormTypesLibsMd()
        libtext = libspage.getMdText()

        self.isin('# Storm Libraries', libtext)
        self.isin('$lib.', libtext)

    async def test_docstormtypesprimsmd(self):
        typespage = await s_autodoc.docStormTypesPrimsMd()
        typetext = typespage.getMdText()

        self.isin('# Storm Types', typetext)
