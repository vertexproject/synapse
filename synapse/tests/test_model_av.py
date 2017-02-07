import synapse.cortex as s_cortex

from synapse.tests.common import *

class InetModelTest(SynTest):

    def test_model_av(self):
        with s_cortex.openurl('ram:///') as core:
            bytesguid = '1234567890ABCDEFFEDCBA0987654321'
            orgname = 'Foo'
            signame = 'Bar.BAZ.faZ'
            valu = (bytesguid, (orgname, signame))

            tufo = core.formTufoByFrob('tech:av:filehit', valu)
            self.eq(tufo[1].get('tech:av:filehit:sig'), 'foo/bar.baz.faz')
            self.eq(tufo[1].get('tech:av:filehit:sig:org'), 'foo')
            self.eq(tufo[1].get('tech:av:filehit:sig:sig'), 'bar.baz.faz')
            self.eq(tufo[1].get('tech:av:filehit:file'), '1234567890abcdeffedcba0987654321')

            tufo = core.getTufoByProp('tech:av:sig', 'foo/bar.baz.faz')
            self.eq(tufo[1].get('tech:av:sig'), 'foo/bar.baz.faz')
            self.eq(tufo[1].get('tech:av:sig:org'), 'foo')
            self.eq(tufo[1].get('tech:av:sig:sig'), 'bar.baz.faz')

            tufo = core.getTufoByProp('ou:alias', 'foo')
            self.eq(tufo, None) # ou:alias will not be automatically formed at this time
