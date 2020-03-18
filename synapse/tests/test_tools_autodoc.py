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
