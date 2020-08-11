import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.autodoc as s_autodoc

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
            self.isin('synapse.models.inet.Addr', s)
            self.isin('Regular types are derived from BaseTypes.', s)
            self.isin(r'inet\:server', s)

            with s_common.genfile(path, 'datamodel_forms.rst') as fd:
                buf = fd.read()

            s = buf.decode()
            self.isin('Forms are derived from types, or base types. Forms represent node types in the graph.', s)
            self.isin(r'inet\:ipv4', s)
            self.notin(r'file\:bytes:.created', s)
            self.isin('Universal props are system level properties which may be present on every node.', s)
            self.isin('.created', s)
            self.notin('..created\n', s)
            self.isin('An example of ``inet:dns:a``\\:', s)

    async def test_tools_autodoc_confdefs(self):

        with self.getTestDir() as path:

            argv = ['--savedir', path, '--doc-conf',
                    'synapse.tests.test_lib_stormsvc.StormvarServiceCell']

            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)

            with s_common.genfile(path, 'conf_stormvarservicecell.rst') as fd:
                buf = fd.read()
            s = buf.decode()

            self.isin('autodoc-stormvarservicecell-conf', s)
            self.isin('StormvarServiceCell Configuration Options', s)
            self.isin('See :ref:`devops-cell-config` for', s)
            self.isin('auth\\:passwd', s)
            self.isin('Environment Variable\n    ``SYN_STORMVARSERVICECELL_AUTH_PASSWD``', s)
            self.isin('``--auth-passwd``', s)

            argv.append('--doc-conf-reflink')
            argv.append('`Configuring a Cell Service <https://synapse.docs.vertex.link/en/latest/synapse/devguides/devops_cell.html>`_')

            # truncate the current file
            with s_common.genfile(path, 'conf_stormvarservicecell.rst') as fd:
                fd.truncate()

            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)
            with s_common.genfile(path, 'conf_stormvarservicecell.rst') as fd:
                buf = fd.read()
            s = buf.decode()

            self.isin('StormvarServiceCell Configuration Options', s)
            self.isin('See `Configuring a Cell Service <https://synapse', s)

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
            self.isin('magic\n-----', s)
            self.isin('Test stormvar support', s)
            self.isin('forms as input nodes', s)
            self.isin('``test:str``', s)
            self.isin('nodes in the graph', s)
            self.isin('``test:comp``', s)

    async def test_tools_autodoc_stormtypes(self):
        with self.getTestDir() as path:

            argv = ['--savedir', path, '--doc-stormtypes']
            outp = self.getTestOutp()
            self.eq(await s_autodoc.main(argv, outp=outp), 0)

            with s_common.genfile(path, 'stormtypes_libs.rst') as fd:
                libbuf = fd.read()
            libtext = libbuf.decode()

            self.isin('.. _stormlibs-lib-print:\n\n$lib.print(mesg, \\*\\*kwargs)\n============================',
                      libtext)
            self.isin('Print a message to the runtime.', libtext)
            self.isin('\\*\\*kwargs: Keyword arguments to substitute into the mesg.', libtext)
            self.isin('.. _stormlibs-lib-time:\n\n*********\n$lib.time\n*********', libtext)
            self.isin('A Storm Library for interacting with timestamps.', libtext)

            with s_common.genfile(path, 'stormtypes_prims.rst') as fd:
                primbuf = fd.read()
            primstext = primbuf.decode()
            self.isin('.. _stormprims-User:\n\n****\nUser\n****', primstext)
            self.isin('User.iden\n=========\n\nConstant representing the user iden.', primstext)
