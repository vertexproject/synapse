
from synapse.tests.common import *

import synapse.tools.autodoc as s_autodoc

class TestAutoDoc(SynTest):

    def test_tools_autodoc(self):

        with self.getTestDir() as path:

            save = os.path.join(path, 'model.rst')
            outp = self.getTestOutp()
            argv = ['--doc-model', '--savefile', save]
            self.eq(s_autodoc.main(argv, outp=outp), 0)
