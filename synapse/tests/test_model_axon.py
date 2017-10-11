import stat

import synapse.axon as s_axon

from synapse.tests.common import *

class AxonModelTest(SynTest):

    def test_axonblob(self):
        with self.getTestDir() as axondir:
            axon = s_axon.Axon(axondir)
            core = axon.core

            hset = s_axon.HashSet()
            hset.update(b'visi')

            valu, props = hset.guid()
            props.update({'off': 0})

            t0 = core.formTufoByProp('axon:blob', valu, **props)
            self.eq(t0[1].get('axon:blob:off'), 0)
            self.eq(t0[1].get('axon:blob:size'), 4)
            self.eq(t0[1].get('axon:blob'), '442f602ecf8230b2a59a44b4f845be27')
            self.eq(t0[1].get('axon:blob:md5'), '1b2e93225959e3722efed95e1731b764')
            self.eq(t0[1].get('axon:blob:sha1'), '93de0c7d579384feb3561aa504acd8f23f388040')
            self.eq(t0[1].get('axon:blob:sha256'), 'e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f')
            self.eq(t0[1].get('axon:blob:sha512'), '8238be12bcc3c10da7e07dbea528e9970dc809c07c5aef545a14e5e8d2038563b29c2e818d167b06e6a33412e6beb8347fcc44520691347aea9ee21fcf804e39')

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
