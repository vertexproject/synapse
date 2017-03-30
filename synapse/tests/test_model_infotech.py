
from synapse.tests.common import *

class InfoTechTest(SynTest):

    def test_model_infotech_host(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)
            node = core.formTufoByProp('it:host',guid())
            self.nn(node)
            self.nn(node[1].get('it:host'))

    def test_model_infotech_cve(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)
            node = core.formTufoByProp('it:sec:cve','CVE-2013-9999', desc='This is a description')
            self.nn(node)
            self.eq( node[1].get('it:sec:cve'), 'CVE-2013-9999')
            self.eq( node[1].get('it:sec:cve:desc'), 'This is a description' )
            self.raises( BadTypeValu, core.formTufoByProp, 'it:sec:cve', 'dERP' )

    def test_model_infotech_av(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce',1)
            bytesguid = '1234567890ABCDEFFEDCBA0987654321'
            orgname = 'Foo'
            signame = 'Bar.BAZ.faZ'
            valu = (bytesguid, (orgname, signame))

            tufo = core.formTufoByFrob('it:av:filehit', valu)
            self.eq(tufo[1].get('it:av:filehit:sig'), 'foo/bar.baz.faz')
            self.eq(tufo[1].get('it:av:filehit:file'), '1234567890abcdeffedcba0987654321')

            tufo = core.getTufoByProp('it:av:sig', 'foo/bar.baz.faz')
            self.eq(tufo[1].get('it:av:sig'), 'foo/bar.baz.faz')
            self.eq(tufo[1].get('it:av:sig:org'), 'foo')
            self.eq(tufo[1].get('it:av:sig:sig'), 'bar.baz.faz')

            tufo = core.getTufoByProp('ou:alias', 'foo')
            self.eq(tufo, None) # ou:alias will not be automatically formed at this time
