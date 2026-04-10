import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.cortex.docmodel as s_docmodel

class DocModelTest(s_t_utils.SynTest):

    async def test_tools_docmodel_tempcore(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main([], outp=outp), 0)

        text = str(outp)
        self.isin('# Synapse Data Model', text)
        self.isin('## Interfaces', text)
        self.isin('## Forms', text)
        self.isin('## Edges', text)
        self.isin('## Tag Properties', text)

        # Verify interfaces are present
        self.isin('### `meta:observable`', text)

        # Verify interface forms table is present
        self.isin('| Form |', text)
        self.isin('|------|', text)

        # Verify form-level interfaces table is present
        self.isin('| Interface |', text)
        self.isin('|-----------|', text)

        # Verify inherited interfaces are fully resolved
        # edu:class implements entity:participable which inherits base:activity,
        # which inherits meta:causal, and also implements meta:recordable
        classidx = text.index('### `edu:class`')
        # Find the next form heading after edu:class
        nextformidx = text.index('### `', classidx + 1)
        classtext = text[classidx:nextformidx]
        self.isin('`entity:participable`', classtext)
        self.isin('`base:activity`', classtext)
        self.isin('`meta:causal`', classtext)
        self.isin('`meta:recordable`', classtext)

        # Verify interface template variables are resolved
        # meta:observable uses {title} with default 'node'
        obsidx = text.index('### `meta:observable`')
        nextidx = text.index('### `', obsidx + 1)
        obstext = text[obsidx:nextidx]
        self.isin('The node was observed during the time interval.', obstext)
        self.notin('{title}', obstext)

        # geo:locatable uses {title} and {happened} defaults
        locidx = text.index('### `geo:locatable`')
        nextidx = text.index('### `', locidx + 1)
        loctext = text[locidx:nextidx]
        self.isin('The place where the item was located.', loctext)
        self.notin('{title}', loctext)
        self.notin('{happened}', loctext)

        # meta:taxonomy uses {$self} which resolves to interface name
        taxidx = text.index('### `meta:taxonomy`')
        nextidx = text.index('### `', taxidx + 1)
        taxtext = text[taxidx:nextidx]
        self.isin('`meta:taxonomy`', taxtext)
        self.notin('{$self}', taxtext)

        # Verify poly types are resolved to their actual type names
        self.notin('| `poly` |', text)

        # Verify array types are resolved to show their element type
        self.notin('| `array` |', text)
        self.isin('`array of inet:fqdn`', text)

        # Verify forms are present
        self.isin('### `inet:ip`', text)
        self.isin('### `inet:fqdn`', text)

        # Verify properties are present with docs
        self.isin('| Property | Type | Doc |', text)
        self.isin('`:asn`', text)

        # Verify edges are present
        self.isin('| Source | Verb | Target | Doc |', text)
        self.isin('`refs`', text)

    async def test_tools_docmodel_cortex(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            lurl = core.getLocalUrl()

            outp = self.getTestOutp()
            self.eq(await s_docmodel.main(['--cortex', lurl], outp=outp), 0)

            text = str(outp)
            self.isin('# Synapse Data Model', text)
            self.isin('## Interfaces', text)
            self.isin('## Forms', text)
            self.isin('## Edges', text)

    async def test_tools_docmodel_save(self):

        with self.getTestDir() as dirn:

            filepath = s_common.genpath(dirn, 'datamodel.md')

            outp = self.getTestOutp()
            self.eq(await s_docmodel.main(['--save', filepath], outp=outp), 0)

            outp.expect('Model documentation written to')

            with open(filepath, 'r') as fd:
                text = fd.read()

            self.isin('# Synapse Data Model', text)
            self.isin('## Interfaces', text)
            self.isin('## Forms', text)
            self.isin('## Edges', text)
            self.isin('### `inet:ip`', text)

    def test_tools_docmodel_resolvetypenames(self):

        resolve = s_docmodel._resolveTypeNames

        # Falsy inputs
        self.eq(resolve(None), [''])
        self.eq(resolve(''), [''])
        self.eq(resolve(()), [''])
        self.eq(resolve([]), [''])

        # String input
        self.eq(resolve('inet:fqdn'), ['inet:fqdn'])

        # Poly with interfaces
        self.eq(resolve(('poly', {'interfaces': ['b', 'a']})), ['a', 'b'])

        # Poly with forms
        self.eq(resolve(('poly', {'forms': ['z', 'm']})), ['m', 'z'])

        # Poly with both interfaces and forms aggregated, uniqued, and sorted
        self.eq(resolve(('poly', {'interfaces': ['c', 'a'], 'forms': ['b', 'a']})), ['a', 'b', 'c'])

        # Poly with non-dict opts
        self.eq(resolve(('poly', 'notadict')), ['poly'])

        # Bare poly with no interfaces or forms
        self.eq(resolve(('poly', {})), ['poly'])

        # Array with string element type
        self.eq(resolve(('array', {'type': 'inet:fqdn'})), ['array of inet:fqdn'])

        # Array with tuple element type
        self.eq(resolve(('array', {'type': ('str', 'int')})), ['array of int, str'])

        # Array with non-dict opts
        self.eq(resolve(('array', 'notadict')), ['array'])

        # Array with no type key
        self.eq(resolve(('array', {})), ['array'])

        # Generic tuple type (not poly or array)
        self.eq(resolve(('str', {})), ['str'])
        self.eq(resolve(('int',)), ['int'])

        # Non-string, non-tuple, non-list input
        self.eq(resolve(12345), [''])

    async def test_tools_docmodel_sorted(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main([], outp=outp), 0)

        text = str(outp)
        lines = text.split('\n')

        # Verify forms are sorted alphabetically
        formsidx = next(i for i, line in enumerate(lines) if line == '## Forms')
        edgesidx = next(i for i, line in enumerate(lines) if line == '## Edges')
        formlines = [line for line in lines[formsidx:edgesidx] if line.startswith('### `')]
        formnames = [line[5:-1] for line in formlines]
        self.eq(formnames, sorted(formnames))

        # Verify interfaces are sorted alphabetically
        ifaceidx = next(i for i, line in enumerate(lines) if line == '## Interfaces')
        ifacelines = [line for line in lines[ifaceidx:] if line.startswith('### `')]
        ifacenames = [line[5:-1] for line in ifacelines]
        self.eq(ifacenames, sorted(ifacenames))
        self.gt(len(ifacenames), 0)

        # Verify edges are sorted by extracting source/verb/target tuples
        edgeidx = next(i for i, line in enumerate(lines) if line == '## Edges')
        headeridx = next(i for i in range(edgeidx, len(lines)) if lines[i].startswith('| Source'))
        edgekeys = []
        for line in lines[headeridx + 2:]:
            if not line.startswith('|'):
                break
            parts = [p.strip().strip('`') for p in line.split('|')[1:4]]
            edgekeys.append(tuple(parts))
        self.gt(len(edgekeys), 0)
        self.eq(edgekeys, sorted(edgekeys))

    async def test_tools_docmodel_form(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'inet:fqdn'], outp=outp), 0)

        text = str(outp)

        # Top-level heading for the form
        self.isin('# `inet:fqdn`', text)

        # Properties section with table
        self.isin('## Properties', text)
        self.isin('| Property | Type | Doc |', text)

        # Referenced Types section
        self.isin('## Referenced Types', text)

        # Wildcard edges use plain * not escaped \*
        self.notin('`\\*`', text)

    async def test_tools_docmodel_form_edges(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'inet:fqdn'], outp=outp), 0)

        text = str(outp)

        # Edge verbs use Storm -(verb)> notation
        if '## Source Edges' in text or '## Target Edges' in text:
            self.isin('`-(', text)

    async def test_tools_docmodel_interface(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'meta:observable'], outp=outp), 0)

        text = str(outp)

        # Top-level heading for the interface
        self.isin('# `meta:observable`', text)

        # Properties section
        self.isin('## Properties', text)
        self.isin('| Property | Type | Doc |', text)

        # Implementing Forms section
        self.isin('## Implementing Forms', text)
        self.isin('| Form |', text)

        # Template variables resolved
        self.notin('{title}', text)

    async def test_tools_docmodel_form_notfound(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'notreal:form'], outp=outp), 0)

        text = str(outp)
        self.isin('not found in model', text)

    async def test_tools_docmodel_interface_notfound(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'notreal:iface'], outp=outp), 0)

        text = str(outp)
        self.isin('not found in model', text)

    def test_tools_docmodel_doc_helper_fallbacks(self):

        # _getFormDoc: forminfo has a direct 'doc' key -> return it (line 16)
        self.eq(s_docmodel._getFormDoc('foo', {'doc': 'direct doc'}, {}), 'direct doc')

        # _getFormDoc: no doc on forminfo and name not in types -> return '' (line 22)
        self.eq(s_docmodel._getFormDoc('foo', {}, {}), '')

        # _escpipe: None input -> return '' (line 42)
        self.eq(s_docmodel._escpipe(None), '')

    def test_tools_docmodel_getnestedtypenames_unit(self):

        getNested = s_docmodel._getNestedTypeNames

        # Falsy inputs -> empty tuple
        self.eq(getNested(None), ())
        self.eq(getNested(()), ())
        self.eq(getNested([]), ())

        # Regular type -> type name
        self.eq(getNested(('inet:fqdn', {})), ('inet:fqdn',))

        # Poly -> underlying type names
        self.eq(getNested(('poly', {'forms': ['inet:fqdn']})), ('inet:fqdn',))
        self.eq(getNested(('poly', {'types': ['ival']})), ('ival',))
        self.eq(getNested(('poly', {'forms': ['inet:fqdn'], 'types': ['str']})), ('inet:fqdn', 'str'))
        self.eq(getNested(('poly', {})), ())

        # Array with string element type -> element type name
        self.eq(getNested(('array', {'type': 'inet:fqdn'})), ('inet:fqdn',))

        # Array with tuple element type -> all element type names
        self.eq(getNested(('array', {'type': ('str', 'int')})), ('str', 'int'))

        # Array with no type key -> empty
        self.eq(getNested(('array', {})), ())

        # Array with non-dict opts -> empty
        self.eq(getNested(('array', 'notadict')), ())

    def test_tools_docmodel_getbasetypename_unit(self):

        getBase = s_docmodel._getBaseTypeName

        # typename not found in types dict -> None
        self.none(getBase('nonexistent', {}))

        # typename found but info has no bases -> None
        self.none(getBase('foo', {'foo': {'info': {}}}))

        # typename found with bases -> last base name
        types = {'foo': {'info': {'bases': ('base1', 'base2')}}}
        self.eq(getBase('foo', types), 'base2')

    def test_tools_docmodel_gentypedetail_unit(self):

        genDetail = s_docmodel._genTypeDetail

        interfaces = {
            'test:iface': {
                'doc': 'A test interface.',
                'interfaces': (),
                'props': (),
            },
        }

        types = {
            'test:withiface': {
                'info': {
                    'doc': 'Type with interface.',
                    'bases': ('str',),
                    'interfaces': (('test:iface', {}),),
                },
                'opts': {'items': ['alpha', 'beta']},
            },
        }

        # seen=None -> initialises internally (line 137), processes normally
        result = '\n'.join(genDetail('test:withiface', types, interfaces))
        self.isin('### `test:withiface`', result)
        self.isin('This type implements the following interfaces:', result)
        self.isin('`test:iface`', result)
        # non-empty list opt value -> line 191
        self.isin("['alpha', 'beta']", result)

        # typename already in seen -> early return [] (line 140)
        self.eq(genDetail('test:withiface', types, interfaces, seen={'test:withiface'}), [])

    def test_tools_docmodel_lookupedges_unit(self):

        lookup = s_docmodel._lookupEdgesForForm

        generic = ((None, 'refs', None), {'doc': 'generic'})
        src_null_other_dst = ((None, 'refs', 'other:form'), {'doc': ''})
        src_null_self_dst = ((None, 'refs', 'test:form'), {'doc': ''})
        other_src_null_dst = (('other:form', 'refs', None), {'doc': ''})
        self_src_null_dst = (('test:form', 'refs', None), {'doc': ''})
        other_src_self_dst = (('other:form', 'refs', 'test:form'), {'doc': ''})
        self_src_other_dst = (('test:form', 'refs', 'other:form'), {'doc': ''})
        self_src_self_dst = (('test:form', 'refs', 'test:form'), {'doc': ''})

        edges = [
            generic,
            src_null_other_dst,
            src_null_self_dst,
            other_src_null_dst,
            self_src_null_dst,
            other_src_self_dst,
            self_src_other_dst,
            self_src_self_dst,
        ]

        result = lookup('test:form', edges)

        # src=None, dst=None -> generic
        self.isin(generic, result.get('generic', []))

        # src=None, dst!=formname -> source (line 211)
        self.isin(src_null_other_dst, result.get('source', []))

        # src=None, dst==formname -> target (line 213)
        self.isin(src_null_self_dst, result.get('target', []))

        # src!=formname, dst=None -> target (line 215)
        self.isin(other_src_null_dst, result.get('target', []))

        # src==formname, dst=None -> source (line 217)
        self.isin(self_src_null_dst, result.get('source', []))

        # src!=formname, dst==formname -> target (line 219)
        self.isin(other_src_self_dst, result.get('target', []))

        # src==formname, dst!=formname -> source (line 221)
        self.isin(self_src_other_dst, result.get('source', []))

        # src==formname, dst==formname -> both source and target (lines 223-224)
        self.isin(self_src_self_dst, result.get('source', []))
        self.isin(self_src_self_dst, result.get('target', []))

    async def test_tools_docmodel_form_array_props(self):
        # edu:class has array-type properties (e.g. :assistants, :names),
        # exercising the array nestedtypes collection path via _getNestedTypeNames in genFormMarkdown

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'edu:class'], outp=outp), 0)

        text = str(outp)
        self.isin('# `edu:class`', text)
        self.isin('## Referenced Types', text)
        # The array element types should appear in Referenced Types
        self.isin('`entity:individual`', text)

    async def test_tools_docmodel_interface_parents(self):
        # entity:participable inherits from base:activity,
        # exercising the "## Inherits From" section in genIfaceMarkdown

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'entity:participable'], outp=outp), 0)

        text = str(outp)
        self.isin('# `entity:participable`', text)
        self.isin('## Inherits From', text)
        self.isin('`base:activity`', text)

    async def test_tools_docmodel_interface_array_props(self):
        # entity:contactable has array-type properties (e.g. :names, :emails),
        # exercising the array nestedtypes collection path via _genIfacePropTable in genIfaceMarkdown

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'entity:contactable'], outp=outp), 0)

        text = str(outp)
        self.isin('# `entity:contactable`', text)
        self.isin('## Referenced Types', text)

    async def test_tools_docmodel_tagprops(self):
        # A cortex with tag properties exercises the Tag Properties section
        # in genModelMarkdown

        async with self.getTestCoreAndProxy() as (core, prox):
            await core.addTagProp('test:score', ('int', {}), {'doc': 'A test tag score.'})

            lurl = core.getLocalUrl()
            outp = self.getTestOutp()
            self.eq(await s_docmodel.main(['--cortex', lurl], outp=outp), 0)

            text = str(outp)
            self.isin('## Tag Properties', text)
            self.isin('`test:score`', text)
            self.isin('A test tag score.', text)

    async def test_tools_docmodel_form_interface_nodoc(self):
        # A custom form whose type implements an interface with no doc triggers
        # the no-doc branch in the genFormMarkdown interfaces table

        async with self.getTestCore() as core:
            core.model.addModelDefs([{
                'interfaces': (
                    ('test:nodoc:iface', {
                        'props': (),
                        # deliberately no 'doc' key
                    }),
                ),
                'types': (
                    ('test:nodoc:form', ('str', {}), {
                        'interfaces': (('test:nodoc:iface', {}),),
                        'doc': 'A form with a no-doc interface.',
                    }),
                ),
                'forms': (
                    ('test:nodoc:form', {}, ()),
                ),
            }])

            text = await s_docmodel.genFormMarkdown(core, 'test:nodoc:form')
            self.isin('`test:nodoc:iface`', text)
            # Row has no " - <doc>" annotation because interface has no doc
            self.notin('test:nodoc:iface` -', text)

    async def test_tools_docmodel_iface_implementing_forms(self):
        # A custom interface implemented by a form exercises the
        # "## Implementing Forms" section in genIfaceMarkdown

        async with self.getTestCore() as core:
            core.model.addModelDefs([{
                'interfaces': (
                    ('test:impl:iface', {
                        'doc': 'A test interface with an implementing form.',
                        'props': (
                            ('score', ('int', {}), {'doc': 'A score.'}),
                        ),
                    }),
                ),
                'types': (
                    ('test:impl:form', ('str', {}), {
                        'doc': 'A form implementing test:impl:iface.',
                        'interfaces': (('test:impl:iface', {}),),
                    }),
                ),
                'forms': (
                    ('test:impl:form', {}, ()),
                ),
            }])

            text = await s_docmodel.genIfaceMarkdown(core, 'test:impl:iface')
            self.isin('# `test:impl:iface`', text)
            self.isin('## Implementing Forms', text)
            self.isin('`test:impl:form`', text)

    def test_tools_docmodel_findname_unit(self):

        findName = s_docmodel._findName

        modeldict = {
            'forms': {
                'inet:fqdn': {
                    'props': {
                        'domain': {'type': ('inet:fqdn', {}), 'doc': 'The domain.'},
                        'zone': {'type': ('inet:fqdn', {}), 'doc': 'The zone.'},
                    },
                },
                'inet:ipv4': {
                    'props': {
                        'asn': {'type': ('inet:asn', {}), 'doc': 'The ASN.'},
                    },
                },
            },
            'interfaces': {
                'meta:observable': {
                    'doc': 'An observable.',
                    'props': (
                        ('seen', ('ival', {}), {'doc': 'Observed interval.'}),
                        ('time', ('time', {}), {'doc': 'Observed time.'}),
                    ),
                    'interfaces': (),
                },
            },
            'tagprops': {
                'test:score': {'type': ('int', {}), 'doc': 'A score.'},
            },
        }

        # Exact form match
        result = findName('inet:fqdn', modeldict)
        self.eq(result[0], 'form')
        self.eq(result[1], 'inet:fqdn')

        # Exact interface match
        result = findName('meta:observable', modeldict)
        self.eq(result[0], 'interface')
        self.eq(result[1], 'meta:observable')

        # Form prop match
        result = findName('inet:fqdn:domain', modeldict)
        self.eq(result[0], 'formprop')
        self.eq(result[1], 'inet:fqdn')
        self.eq(result[2], 'domain')

        # Interface prop match
        result = findName('meta:observable:seen', modeldict)
        self.eq(result[0], 'ifaceprop')
        self.eq(result[1], 'meta:observable')
        self.eq(result[2], 'seen')

        # Tag prop match
        result = findName('test:score', modeldict)
        self.eq(result[0], 'tagprop')
        self.eq(result[1], 'test:score')

        # Unknown name
        self.none(findName('really:not:there', modeldict))

    async def test_tools_docmodel_find_formprop(self):
        # auth:passwd:seen has type ival (non-poly), exercises Referenced Types section

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'auth:passwd:seen'], outp=outp), 0)

        text = str(outp)
        self.isin('# `auth:passwd:seen`', text)
        self.isin('**Form:** `auth:passwd`', text)
        self.isin('| Property | Type | Doc |', text)
        self.isin('`:seen`', text)
        self.isin('## Referenced Types', text)

    async def test_tools_docmodel_find_ifaceprop(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'meta:observable:seen'], outp=outp), 0)

        text = str(outp)
        self.isin('# `meta:observable:seen`', text)
        self.isin('**Interface:** `meta:observable`', text)
        self.isin('| Property | Type | Doc |', text)
        self.isin('`:seen`', text)

    async def test_tools_docmodel_find_tagprop(self):

        async with self.getTestCoreAndProxy() as (core, prox):
            await core.addTagProp('test:score', ('int', {}), {'doc': 'A test tag score.'})

            lurl = core.getLocalUrl()
            outp = self.getTestOutp()
            self.eq(await s_docmodel.main(['--cortex', lurl, '--find', 'test:score'], outp=outp), 0)

            text = str(outp)
            self.isin('# `test:score`', text)
            self.isin('**Tag Property**', text)
            self.isin('| Property | Type | Doc |', text)
            self.isin('`test:score`', text)

    async def test_tools_docmodel_find_notfound(self):

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'really:not:there'], outp=outp), 0)

        text = str(outp)
        self.isin('not found in model', text)

    async def test_tools_docmodel_direct_notfound(self):
        # Exercises the not-found early-return paths in genFormMarkdown and
        # genIfaceMarkdown when called directly

        async with self.getTestCore() as core:
            text = await s_docmodel.genFormMarkdown(core, 'notreal:form')
            self.isin('not found in model', text)

            text = await s_docmodel.genIfaceMarkdown(core, 'notreal:iface')
            self.isin('not found in model', text)

            # genPropMarkdown with a form name (not a prop) -> not found path (line 511)
            text = await s_docmodel.genPropMarkdown(core, 'inet:fqdn')
            self.isin('not found in model', text)

    async def test_tools_docmodel_find_array_props(self):
        # biz:rfp:contributors has an array type, exercises the array nestedtypes
        # path via _getNestedTypeNames in genPropMarkdown for formprop and ifaceprop

        outp = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'biz:rfp:supersedes'], outp=outp), 0)

        text = str(outp)
        self.isin('# `biz:rfp:supersedes`', text)
        self.isin('**Form:** `biz:rfp`', text)

        outp2 = self.getTestOutp()
        self.eq(await s_docmodel.main(['--find', 'doc:authorable:supersedes'], outp=outp2), 0)

        text2 = str(outp2)
        self.isin('# `doc:authorable:supersedes`', text2)
        self.isin('**Interface:** `doc:authorable`', text2)
