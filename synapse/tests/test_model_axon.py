from __future__ import absolute_import, unicode_literals

from synapse.tests.common import *

class AxonModelTest(SynTest):

    def test_axonpath(self):

        with s_cortex.openurl('ram:///') as core:

            core.formTufoByProp('axon:path', '/foo/bar/baz/faz/')

            self.nn(core.getTufoByProp('axon:path', '/foo/bar/baz/faz'))
            self.nn(core.getTufoByProp('file:base', 'faz'))
            self.nn(core.getTufoByProp('axon:path', '/foo/bar/baz'))
            self.nn(core.getTufoByProp('file:base', 'baz'))
            self.nn(core.getTufoByProp('axon:path', '/foo/bar'))
            self.nn(core.getTufoByProp('file:base', 'bar'))
            self.nn(core.getTufoByProp('axon:path', '/foo'))
            self.nn(core.getTufoByProp('file:base', 'foo'))
            self.nn(core.getTufoByProp('axon:path', '/'))

            self.raises(BadTypeValu, core.getTufoByProp, 'axon:path', '')
            self.raises(BadTypeValu, core.getTufoByProp, 'axon:path', 3)

            self.none(core.getTufoByProp('file:base', ''))
            self.raises(BadTypeValu, core.getTufoByProp, 'file:base', '/')
