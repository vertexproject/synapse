import textwrap

import synapse.common as s_common

import synapse.tests.files as s_t_files
import synapse.tests.utils as s_t_utils

import synapse.lib.autodoc as s_l_autodoc

import synapse.tools.utils.autodoc as s_autodoc

class TestAutoDoc(s_t_utils.SynTest):

    async def test_tools_autodoc_docmodel(self):

        with self.getTestDir() as path:

            argv = ['--doc-model', '--savedir', path]

            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)

            with s_common.genfile(path, 'datamodel_types.rst') as fd:
                buf = fd.read()

            s = buf.decode()
            self.isin('Base types are defined via Python classes.', s)
            self.isin('synapse.models.inet.SockAddr', s)
            self.isin('Regular types are derived from BaseTypes.', s)
            self.isin(r'inet\:server', s)

            # Enums for int
            self.isin('``pe:resource:type``', s)
            self.isin('=== ===============', s)
            self.isin('int valu           ', s)
            self.isin('1   RT_CURSOR      ', s)

            self.isin('''This type has the following virtual properties:

 * ``min``
 * ``max``
 * ``duration``''', s)

            self.isin('''This type supports lifting using the following operators:

 * ``=``
 * ``~=``
 * ``?=``
 * ``in=``''', s)

            self.isin('This type implements the following interfaces:', s)
            self.isin('''('inet:service:object', {''', s)
            self.isin('''('phys:object', {''', s)

            # Interfaces section must be present with anchors that form props can ref.
            self.isin('Interfaces define common properties inherited by multiple forms.', s)
            self.isin('.. _dm-interfaces:', s)
            self.isin('.. _dm-type-crypto-hash:', s)
            self.isin('An interface implemented by all cryptographic hashes.', s)
            self.isin('.. _dm-type-auth-credential:', s)
            self.isin('.. _dm-type-entity-actor:', s)
            self.isin('.. _dm-type-entity-identifier:', s)

            with s_common.genfile(path, 'datamodel_forms.rst') as fd:
                buf = fd.read()

            s = buf.decode()
            self.isin('Forms are derived from types, or base types. Forms represent node types in the graph.', s)
            self.isin(r'inet\:ip', s)
            self.notin(r'file\:bytes:seen', s)
            self.isin('An example of ``inet:dns:a``\\:', s)

            # IP property
            self.isin('''* - ``:asn``
        - | :ref:`dm-type-poly`
          | types: ``(\'inet:asn\',)``
        - The ASN to which the IP address is currently assigned.''', s)

            # Readonly inet:form:password:md5 value
            self.isin('''* - ``:md5``
        - | :ref:`dm-type-poly`
          | types: ``(\'crypto:hash:md5\',)``
        - The MD5 hash of the password.
        - Computed: ``True``''', s)

            # Refs edges def
            self.isin('''      * - ``*``
        - ``-(refs)>``
        - ``*``
        - The source node contains a reference to the target node.''', s)

            async with self.getTestCore() as core:
                lurl = core.getLocalUrl()
                argv = ['--doc-model', '--savedir', path, '--cortex', lurl]
                outp = self.getTestOutp()
                self.eq(await s_autodoc.main(argv, outp=outp), 0)

                with s_common.genfile(path, 'datamodel_types.rst') as fd:
                    buf = fd.read()

                s = buf.decode()
                self.isin('Base types are defined via Python classes.', s)

                # Enums for str
                self.isin('``test:enums:str``', s)
                self.isin('+-----+', s)
                self.isin('+valu +', s)
                self.isin('+=====+', s)
                self.isin('+testx+', s)

    async def test_tools_autodoc_confdefs(self):

        with self.getTestDir() as path:

            argv = ['--savedir', path, '--doc-conf',
                    'synapse.tests.test_lib_stormsvc.StormvarServiceCell']

            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)

            with s_common.genfile(path, 'conf_stormvarservicecell.rst') as fd:
                buf = fd.read()
            s = buf.decode()

            self.isin('auth\\:passwd', s)
            self.isin('Environment Variable\n    ``SYN_STORMVARSERVICECELL_AUTH_PASSWD``', s)
            self.isin('The object expects the following properties', s)
            self.notin('``--mirror``', s)
            self.notin('SYN_STORMVARSERVICECELL_CELL_GUID', s)

            # truncate the current file
            with s_common.genfile(path, 'conf_stormvarservicecell.rst') as fd:
                fd.truncate()

            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)
            with s_common.genfile(path, 'conf_stormvarservicecell.rst') as fd:
                buf = fd.read()
            s = buf.decode()

    async def test_tools_autodoc_stormsvc(self):

        with self.getTestDir() as path:

            argv = ['--savedir', path, '--doc-storm',
                    'synapse.tests.test_lib_stormsvc.StormvarServiceCell']

            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)

            with s_common.genfile(path, 'stormsvc_stormvarservicecell.rst') as fd:
                buf = fd.read()
            s = buf.decode()

            self.isin('StormvarServiceCell Storm Service', s)
            self.isin('This documentation is generated for version 0.0.1 of the service.', s)
            self.isin('Storm Package\\: stormvar', s)

            self.isin('.. _stormcmd-stormvar-magic:\n', s)
            self.isin('magic\n-----', s)
            self.isin('Test stormvar support', s)

            self.isin('test:int                    : test:int nodes', s)
            self.isin('test:str                    : test:str nodes', s)

            self.isin('.. _stormmod-stormvar-apimod', s)
            self.isin('status()', s)
            self.notin('testmod', s)

    async def test_tools_autodoc_stormpkg(self):

        with self.getTestDir() as path:

            ymlpath = s_t_files.getAssetPath('stormpkg/testpkg.yaml')

            argv = ['--savedir', path, '--doc-stormpkg', ymlpath]

            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)

            with s_common.genfile(path, 'stormpkg_testpkg.rst') as fd:
                buf = fd.read()
            s = buf.decode()

            self.isin('Storm Package\\: testpkg', s)
            self.isin('This documentation is generated for version 0.0.1 of the package.', s)

            self.isin('This package implements the following Storm Commands.', s)
            self.isin('.. _stormcmd-testpkg-testpkgcmd', s)

            self.isin('testpkgcmd does some stuff', s)
            self.isin('Help on foo opt', s)
            self.isin('Help on bar opt', s)

            self.isin('test:int                    : Some integer input', s)
            self.isin('test:str                    : test:str nodes', s)

            # Tuplelized output
            self.isin('testpkg.baz', s)
            self.isin("Help on baz opt (default: ('-7days', 'now'))", s)

            self.isin('This package implements the following Storm Modules.', s)
            self.isin('.. _stormmod-testpkg-apimod', s)

            self.notin('testmod', s)

            # modconf.endpoints, grouped by resolved base URL, at the bottom of the
            # doc, rendered as an rst grid table (which survives rst -> md
            # conversion as a proper table, rather than a literal code block)

            self.isin('Endpoints', s)
            self.isin('This package communicates with the following API endpoints.', s)

            self.isin('| Path', s)
            self.isin('| Description', s)
            self.isin('+=', s)

            self.isin('https://api.example.com', s)
            self.isin('| /v1/search ', s)
            self.isin('| Run a search.', s)

            self.isin('https://enrich.example.com', s)
            self.isin('| /v1/enrich/{iden} ', s)
            self.isin('| Enrich an item.', s)

            self.isin('(user-configured base URL)', s)
            self.isin('| /v1/noconf ', s)
            self.isin('| An endpoint with no configured base.', s)

            # coverage for no endpoints
            rst = s_l_autodoc.RstHelp()
            await s_autodoc.processModEndpoints(rst, 'foo', [])
            self.eq('', rst.getRstText())

            # coverage for an endpoint with no desc, and a desc long enough to
            # wrap across multiple output lines
            longdesc = ' '.join(f'word{i}' for i in range(20))
            rst = s_l_autodoc.RstHelp()
            await s_autodoc.processModEndpoints(rst, 'foo', [
                {'name': 'covmod', 'modconf': {
                    'endpoints': {
                        'nodesc': {'path': '/v1/nodesc'},
                        'wrapped': {'path': '/v1/wrapped', 'desc': longdesc},
                    },
                }},
            ])
            rsttext = rst.getRstText()
            self.isin('| /v1/nodesc ', rsttext)
            self.isin('| /v1/wrapped | word0', rsttext)
            self.isin('| word10 word11', rsttext)
            self.isin('| word18 word19', rsttext)

            self.isin('search(text, mintime=-30days)', s)
            self.isin('text (str): The text.', s)
            self.isin('Yields:', s)
            self.isin('The return type is ``node``.', s)

            self.isin('status()', s)

            self.isin('newp()', s)
            self.isin('.. warning::\n', s)
            self.isin('``newp`` has been deprecated and will be removed in version v2.300.4.', s)
            self.isin('Newp is no longer maintained. Use bar() instead.', s)
            self.isin('Some nonexistent function', s)

            # coverage for no apidefs
            rst = s_l_autodoc.RstHelp()
            await s_autodoc.processStormModules(rst, 'foo', [])
            self.eq('\nStorm Modules\n=============\n\nThis package does not export any Storm APIs.\n', rst.getRstText())

            pkgdef = s_common.yamlload(ymlpath)
            await s_autodoc.processStormCmds(rst, 'foo', pkgdef.get('commands'))
            rsttext = rst.getRstText()

            self.isin('    Endpoints:', rsttext)
            self.isin('      /v1/test/one\n', rsttext)
            self.isin('      /v1/test/two\n', rsttext)
            self.isin('        /v1/test/three            : endpoint three', rsttext)

            self.isin('    Inputs:\n', rsttext)
            self.isin('      test:int                    : Some integer input\n', rsttext)
            self.isin('      test:str                    : test:str nodes\n', rsttext)

            exp = textwrap.dedent('''\
                The command is accessible to users with one or more of the following permissions:

                - ``power-ups.testpkg.admin``
                - ``power-ups.testpkg.user``
            '''.rstrip())
            self.isin(exp, rsttext)

    def test_tools_autodoc_process_interfaces(self):
        rst = s_l_autodoc.RstHelp()
        ifaces = [
            ('no:doc', {}),
            ('has:doc', {'doc': 'Has a doc string.'}),
            ('has:parent', {
                'doc': 'Extends another interface.',
                'interfaces': (('no:doc', {}), ('phantom:iface', {})),
            }),
            ('has:props', {
                'doc': 'Has props.',
                'props': (
                    ('size', ('int', {}), {'doc': 'The size.'}),
                    ('poly', (('ou:org', {}), ('ps:person', {})), {'doc': 'Poly prop.'}),
                    ('empty', ('', {}), {'doc': 'Empty type.'}),
                    ('unresolved', ('{rule:type}', {}), {'doc': 'Unresolved template.'}),
                    ('phantom', ('not:a:real:type', {}), {'doc': 'Unknown type.'}),
                    ('nodoc', ('str', {}), {}),
                ),
            }),
        ]
        knownnames = {'int', 'str', 'no:doc', 'has:doc', 'has:parent', 'has:props'}
        s_autodoc.processInterfaces(rst, ifaces, knownnames=knownnames)
        s = rst.getRstText()
        self.isin('.. _dm-interfaces:', s)
        self.isin('.. _dm-type-no-doc:', s)
        self.isin('The ``no:doc`` interface.', s)
        self.isin('.. _dm-type-has-doc:', s)
        self.isin('Has a doc string.', s)
        self.isin('This interface extends the following interfaces:', s)
        self.isin(':ref:`dm-type-no-doc`', s)
        # Unknown parent iface should render literal, not a broken ref.
        self.isin(' * ``phantom:iface``', s)
        self.notin(':ref:`dm-type-phantom-iface`', s)
        self.isin('This interface defines the following properties:', s)
        self.isin('``:size`` (:ref:`dm-type-int`) - The size.', s)
        self.isin('``:poly`` (poly) - Poly prop.', s)
        # Empty / template-placeholder / unknown typenames render as literals,
        # not broken :ref: links.
        self.isin('``:empty`` (``unknown``) - Empty type.', s)
        self.isin('``:unresolved`` (``{rule:type}``) - Unresolved template.', s)
        self.isin('``:phantom`` (``not:a:real:type``) - Unknown type.', s)
        self.notin(':ref:`dm-type-`', s)
        self.notin(':ref:`dm-type--rule-type-`', s)
        self.notin(':ref:`dm-type-not-a-real-type`', s)
        self.isin('``:nodoc`` (:ref:`dm-type-str`) - The ``nodoc`` property.', s)

        # When the caller omits knownnames, the default uses the iface names
        # themselves so parent-iface refs in the set still resolve.
        rst2 = s_l_autodoc.RstHelp()
        s_autodoc.processInterfaces(rst2, [
            ('foo:iface', {'doc': 'Foo.'}),
            ('bar:iface', {'doc': 'Bar.', 'interfaces': (('foo:iface', {}),)}),
        ])
        s2 = rst2.getRstText()
        self.isin('.. _dm-type-foo-iface:', s2)
        self.isin(':ref:`dm-type-foo-iface`', s2)

    async def test_tools_autodoc_stormtypes(self):
        with self.getTestDir() as path:

            argv = ['--savedir', path, '--doc-stormtypes']
            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)

            with s_common.genfile(path, 'stormtypes_libs.rst') as fd:
                libbuf = fd.read()
            libtext = libbuf.decode()

            self.isin('.. _stormlibs-lib-print:\n\n$lib.print(mesg)\n================',
                      libtext)
            self.isin('Print a message to the runtime.', libtext)
            self.isin('.. _stormlibs-lib-time:\n\n*********\n$lib.time\n*********', libtext)
            self.isin('A Storm Library for interacting with timestamps.', libtext)

            with s_common.genfile(path, 'stormtypes_prims.rst') as fd:
                primbuf = fd.read()
            primstext = primbuf.decode()
            self.isin('.. _stormprims-auth-user-f527:\n\n**********\nauth\\:user\n**********', primstext)
            self.isin('iden\n====\n\nThe User iden.', primstext)
