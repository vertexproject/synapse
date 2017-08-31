from __future__ import absolute_import, unicode_literals

import stat

import synapse.axon as s_axon

from synapse.tests.common import *

class AxonModelTest(SynTest):

    def test_axonpath(self):

        with self.getTestDir() as axondir:
            axon = s_axon.Axon(axondir)

            defmode = axon.core.getConfOpt('axon:dirmode')

            mode = (stat.S_IFDIR | defmode)
            nlinks = 1

            axon.core.formTufoByProp('axon:path', '/foo/bar/baz/faz/',
                                     st_mode=mode,
                                     st_nlink=nlinks,
                                     )

            self.nn(axon.core.getTufoByProp('axon:path', '/foo/bar/baz/faz'))
            self.nn(axon.core.getTufoByProp('file:base', 'faz'))
            self.nn(axon.core.getTufoByProp('axon:path', '/foo/bar/baz'))
            self.nn(axon.core.getTufoByProp('file:base', 'baz'))
            self.nn(axon.core.getTufoByProp('axon:path', '/foo/bar'))
            self.nn(axon.core.getTufoByProp('file:base', 'bar'))
            self.nn(axon.core.getTufoByProp('axon:path', '/foo'))
            self.nn(axon.core.getTufoByProp('file:base', 'foo'))
            self.nn(axon.core.getTufoByProp('axon:path', '/'))
            self.nn(axon.core.getTufoByProp('file:base', ''))

            self.raises(BadTypeValu, axon.core.getTufoByProp, 'axon:path', '')
            self.raises(BadTypeValu, axon.core.getTufoByProp, 'axon:path', 3)
            self.raises(BadTypeValu, axon.core.getTufoByProp, 'file:base', '/')
