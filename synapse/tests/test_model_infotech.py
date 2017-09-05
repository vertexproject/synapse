
from synapse.tests.common import *

def initcomp(*args,**kwargs):
    retn = list(args)
    retn.extend(kwargs.items())
    return retn

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

    def test_model_infotech_hostfile(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            host = core.formTufoByProp('it:host', None)
            byts = core.formTufoByProp('file:bytes', None)

            hiden = host[1].get('it:host')
            fiden = byts[1].get('file:bytes')

            hostfile = core.formTufoByProp('it:hostfile', (hiden, r'c:\Windows\system32\foo.exe', fiden), ctime='20501217')

            self.nn(hostfile)

            self.eq(hostfile[1].get('it:hostfile:host'), hiden)
            self.eq(hostfile[1].get('it:hostfile:path'), 'c:/windows/system32/foo.exe')
            self.eq(hostfile[1].get('it:hostfile:path:dir'), 'c:/windows/system32')
            self.eq(hostfile[1].get('it:hostfile:path:ext'), 'exe')
            self.eq(hostfile[1].get('it:hostfile:path:base'), 'foo.exe')
            self.eq(hostfile[1].get('it:hostfile:file'), fiden)

            self.eq(hostfile[1].get('it:hostfile:ctime'), 2554848000000)

    def test_model_infotech_itdev(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            node = core.formTufoByProp('it:dev:str','He He Ha Ha')
            self.nn(node)
            self.eq(node[1].get('it:dev:str'), 'He He Ha Ha')
            self.eq(node[1].get('it:dev:str:norm'), 'he he ha ha')

            node = core.formTufoByProp('it:dev:pipe','mypipe')
            self.eq(node[1].get('it:dev:pipe'), 'mypipe')
            self.nn(core.getTufoByProp('it:dev:str', 'mypipe'))

            node = core.formTufoByProp('it:dev:mutex','mymutex')
            self.eq(node[1].get('it:dev:mutex'), 'mymutex')
            self.nn(core.getTufoByProp('it:dev:str', 'mymutex'))

            node = core.formTufoByProp('it:dev:regkey','myregkey')
            self.eq(node[1].get('it:dev:regkey'), 'myregkey')
            self.nn(core.getTufoByProp('it:dev:str', 'myregkey'))

            node = core.eval(r'[ it:dev:regval=("HKEY_LOCAL_MACHINE\\Foo\\Bar", str=hehe) ]')[0]
            self.eq(node[1].get('it:dev:regval:key'),r'HKEY_LOCAL_MACHINE\Foo\Bar')
            self.eq(node[1].get('it:dev:regval:str'),'hehe')

            node = core.eval(r'[ it:dev:regval=("HKEY_LOCAL_MACHINE\\Foo\\Bar", int=20) ]')[0]
            self.eq(node[1].get('it:dev:regval:key'),r'HKEY_LOCAL_MACHINE\Foo\Bar')
            self.eq(node[1].get('it:dev:regval:int'),20)

            iden = guid()
            node = core.eval(r'[ it:dev:regval=("HKEY_LOCAL_MACHINE\\Foo\\Bar", bytes=%s) ]' % iden)[0]
            self.eq(node[1].get('it:dev:regval:key'),r'HKEY_LOCAL_MACHINE\Foo\Bar')
            self.eq(node[1].get('it:dev:regval:bytes'),iden)

    def test_model_infotech_hostexec(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            exe = guid()
            port = 80
            tick = now()
            host = guid()
            proc = guid()
            file = guid()
            ipv4 = 0x01020304
            ipv6 = 'ff::1'
            srv4 = (0x010203040 << 16) + port
            path = r'c:\Windows\System32\rar.exe'
            norm = r'c:/windows/system32/rar.exe'

            core.formTufoByProp('it:host', host)
            core.formTufoByProp('file:bytes', exe)

            # host execution process model
            #core.formTufoByProp('it:exec:proc', 
            node = core.formTufoByProp('it:exec:proc', proc, pid=20, time=tick, host=host, user='visi', exe=exe)
            self.eq(node[1].get('it:exec:proc:exe'), exe)
            self.eq(node[1].get('it:exec:proc:pid'), 20)
            self.eq(node[1].get('it:exec:proc:time'), tick)
            self.eq(node[1].get('it:exec:proc:host'), host)
            self.eq(node[1].get('it:exec:proc:user'), 'visi')

            p0 = guid()
            p1 = guid()

            node = core.formTufoByProp('it:exec:subproc', (p0,p1), host=host)
            self.eq(node[1].get('it:exec:subproc:proc'), p0)
            self.eq(node[1].get('it:exec:subproc:child'), p1)
            self.eq(node[1].get('it:exec:subproc:host'), host)

            node = core.formTufoByProp('it:exec:mutex', (host,'lol',('exe',exe),('proc',proc),('time',tick)))
            self.eq(node[1].get('it:exec:mutex:exe'), exe)
            self.eq(node[1].get('it:exec:mutex:host'), host)
            self.eq(node[1].get('it:exec:mutex:proc'), proc)

            node = core.formTufoByProp('it:exec:pipe', (host,'lol',('exe',exe),('proc',proc),('time',tick)))
            self.eq(node[1].get('it:exec:pipe:exe'), exe)
            self.eq(node[1].get('it:exec:pipe:host'), host)
            self.eq(node[1].get('it:exec:pipe:proc'), proc)

            node = core.formTufoByProp('it:exec:file:add', (host,('path',path),('file',file),('exe',exe),('proc',proc),('time',tick)))
            self.eq(node[1].get('it:exec:file:add:exe'), exe)
            self.eq(node[1].get('it:exec:file:add:host'), host)
            self.eq(node[1].get('it:exec:file:add:proc'), proc)
            self.eq(node[1].get('it:exec:file:add:file'), file)
            self.eq(node[1].get('it:exec:file:add:path'), norm)

            valu = initcomp(host, path=path, file=file, exe=exe, proc=proc, time=tick)
            node = core.formTufoByProp('it:exec:file:del', valu)
            self.eq(node[1].get('it:exec:file:del:exe'), exe)
            self.eq(node[1].get('it:exec:file:del:host'), host)
            self.eq(node[1].get('it:exec:file:del:proc'), proc)
            self.eq(node[1].get('it:exec:file:del:file'), file)
            self.eq(node[1].get('it:exec:file:del:path'), norm)
            self.eq(node[1].get('it:exec:file:del:time'), tick)

            #valu = initcomp(host, tcp4=srv4, path=path, exe=exe, proc=proc, time=tick)
            #props = {'src:ipv4':ipv4,'src:port':port}
            #node = core.formTufoByProp('it:exec:conn', valu, **props)
            #self.eq(node[1].get('it:exec:conn:tcp4'), srv4)
            #self.eq(node[1].get('it:exec:conn:tcp4:ipv4'), ipv4)
            #self.eq(node[1].get('it:exec:conn:tcp4:port'), port)
            #self.eq(node[1].get('it:exec:conn:exe'), exe)
            #self.eq(node[1].get('it:exec:conn:host'), host)
            #self.eq(node[1].get('it:exec:conn:proc'), proc)
            #self.eq(node[1].get('it:exec:conn:time'), tick)
            #self.eq(node[1].get('it:exec:conn:src:ipv4'), ipv4)
            #self.eq(node[1].get('it:exec:conn:src:port'), port)

            valu = initcomp(host, port, path=path, file=file, exe=exe, proc=proc, time=tick, ipv4=ipv4, ipv6=ipv6)
            node = core.formTufoByProp('it:exec:bind:tcp',valu)
            self.eq(node[1].get('it:exec:bind:tcp:exe'), exe)
            self.eq(node[1].get('it:exec:bind:tcp:host'), host)
            self.eq(node[1].get('it:exec:bind:tcp:port'), port)
            self.eq(node[1].get('it:exec:bind:tcp:ipv4'), ipv4)
            self.eq(node[1].get('it:exec:bind:tcp:ipv6'), ipv6)
            self.eq(node[1].get('it:exec:bind:tcp:proc'), proc)
            self.eq(node[1].get('it:exec:bind:tcp:time'), tick)

            valu = initcomp(host, port, path=path, file=file, exe=exe, proc=proc, time=tick, ipv4=ipv4, ipv6=ipv6)
            node = core.formTufoByProp('it:exec:bind:udp',valu)
            self.eq(node[1].get('it:exec:bind:udp:exe'), exe)
            self.eq(node[1].get('it:exec:bind:udp:host'), host)
            self.eq(node[1].get('it:exec:bind:udp:port'), port)
            self.eq(node[1].get('it:exec:bind:udp:ipv4'), ipv4)
            self.eq(node[1].get('it:exec:bind:udp:ipv6'), ipv6)
            self.eq(node[1].get('it:exec:bind:udp:proc'), proc)
            self.eq(node[1].get('it:exec:bind:udp:time'), tick)

            regval = initcomp('foo/bar', int=20)
            valu = initcomp(host, regval, path=path, file=file, exe=exe, proc=proc, time=tick)
            node = core.formTufoByProp('it:exec:reg:del', valu)
            self.eq(node[1].get('it:exec:reg:del:reg:int'), 20)
            self.eq(node[1].get('it:exec:reg:del:reg:key'), 'foo/bar')

            self.eq(node[1].get('it:exec:reg:del:exe'), exe)
            self.eq(node[1].get('it:exec:reg:del:host'), host)
            self.eq(node[1].get('it:exec:reg:del:proc'), proc)
            self.eq(node[1].get('it:exec:reg:del:time'), tick)
