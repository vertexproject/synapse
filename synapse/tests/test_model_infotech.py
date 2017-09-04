
from synapse.tests.common import *

class InfoTechTest(SynTest):

    def test_model_infotech_host(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
            node = core.formTufoByProp('it:host', guid())
            self.nn(node)
            self.nn(node[1].get('it:host'))

    def test_model_infotech_cve(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('it:sec:cve', 'CVE-2013-9999', desc='This is a description')
            self.nn(node)
            self.eq(node[1].get('it:sec:cve'), 'cve-2013-9999')
            self.eq(node[1].get('it:sec:cve:desc'), 'This is a description')
            self.raises(BadTypeValu, core.formTufoByProp, 'it:sec:cve', 'dERP')

            node = core.formTufoByProp('it:sec:cve', 'Cve-2014-1234567890', desc='This is a description')
            self.nn(node)
            self.eq(node[1].get('it:sec:cve'), 'cve-2014-1234567890')
            self.eq(node[1].get('it:sec:cve:desc'), 'This is a description')

    def test_model_infotech_av(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
            bytesguid = '1234567890ABCDEFFEDCBA0987654321'
            orgname = 'Foo'
            signame = 'Bar.BAZ.faZ'
            valu = (bytesguid, (orgname, signame))

            tufo = core.formTufoByProp('it:av:filehit', valu)
            self.eq(tufo[1].get('it:av:filehit:sig'), 'foo/bar.baz.faz')
            self.eq(tufo[1].get('it:av:filehit:file'), '1234567890abcdeffedcba0987654321')

            tufo = core.getTufoByProp('it:av:sig', 'foo/bar.baz.faz')
            self.eq(tufo[1].get('it:av:sig'), 'foo/bar.baz.faz')
            self.eq(tufo[1].get('it:av:sig:org'), 'foo')
            self.eq(tufo[1].get('it:av:sig:sig'), 'bar.baz.faz')

            tufo = core.getTufoByProp('ou:alias', 'foo')
            self.eq(tufo, None) # ou:alias will not be automatically formed at this time

    def test_model_infotech_hostname(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('it:host', None, name='hehehaha')
            self.nn(node)
            self.eq(node[1].get('it:host:name'), 'hehehaha')

            node = core.getTufoByProp('it:hostname', 'hehehaha')
            self.nn(node)

    def test_model_infotech_filepath(self):

        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('file:path', '/Foo/Bar/Baz.exe')

            self.nn(node)
            self.eq(node[1].get('file:path:dir'), '/foo/bar')
            self.eq(node[1].get('file:path:ext'), 'exe')
            self.eq(node[1].get('file:path:base'), 'baz.exe')

            node = core.getTufoByProp('file:path', '/foo')

            self.nn(node)
            self.none(node[1].get('file:path:ext'))

            self.eq(node[1].get('file:path:dir'), '')
            self.eq(node[1].get('file:path:base'), 'foo')

            node = core.formTufoByProp('file:path', r'c:\Windows\system32\Kernel32.dll')

            self.nn(node)
            self.eq(node[1].get('file:path:dir'), 'c:/windows/system32')
            self.eq(node[1].get('file:path:ext'), 'dll')
            self.eq(node[1].get('file:path:base'), 'kernel32.dll')

            self.nn(core.getTufoByProp('file:base', 'kernel32.dll'))

            node = core.getTufoByProp('file:path', 'c:')

            self.nn(node)
            self.none(node[1].get('file:path:ext'))
            self.eq(node[1].get('file:path:dir'), '')
            self.eq(node[1].get('file:path:base'), 'c:')

            node = core.formTufoByProp('file:path', r'/foo////bar/.././baz.json')

            self.nn(node)
            self.eq(node[1].get('file:path'), '/foo/baz.json')

    def test_model_infotech_exec(self):
        # test host execution model elements
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)
            node = core.eval('[ it:exec:url=(*,"http://woot.com/haha",time="2016")  ]')
            # TODO lots more here...
