from binascii import hexlify

import unittest
raise unittest.SkipTest('US GOV MODEL')

import synapse.cortex as s_cortex

import synapse.lib.tufo as s_tufo
import synapse.lib.version as s_version

import synapse.models.crypto as s_m_crypto

from synapse.tests.common import *

def initcomp(*args, **kwargs):
    retn = list(args)
    retn.extend(kwargs.items())
    return retn

class InfoTechTest(SynTest):

    def test_model_infotech_host(self):
        with self.getRamCore() as core:
            node = core.formTufoByProp('it:host', guid())
            self.nn(node)
            self.nn(node[1].get('it:host'))

    def test_model_infotech_cve(self):
        with self.getRamCore() as core:

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
        with self.getRamCore() as core:
            prodguid = '11111111111111111111111111111111'
            bytesguid = '1234567890ABCDEFFEDCBA0987654321'

            sigval = (prodguid, 'Bar.BAZ.faZ')
            valu = (bytesguid, sigval)

            asig = core.formTufoByProp('it:av:sig', sigval)
            self.eq(asig[1].get('it:av:sig:soft'), prodguid)
            self.eq(asig[1].get('it:av:sig:name'), 'bar.baz.faz')

            fhit = core.formTufoByProp('it:av:filehit', (bytesguid, sigval))
            self.eq(fhit[1].get('it:av:filehit:sig'), asig[1].get('it:av:sig'))
            self.eq(fhit[1].get('it:av:filehit:file'), '1234567890abcdeffedcba0987654321')

    def test_model_infotech_hostname(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('it:host', None, name='hehehaha')
            self.nn(node)
            self.eq(node[1].get('it:host:name'), 'hehehaha')

            node = core.getTufoByProp('it:hostname', 'hehehaha')
            self.nn(node)

    def test_model_infotech_itdev(self):
        with self.getRamCore() as core:

            node = core.formTufoByProp('it:dev:str', 'He He Ha Ha')
            self.nn(node)
            self.eq(node[1].get('it:dev:str'), 'He He Ha Ha')
            self.eq(node[1].get('it:dev:str:norm'), 'he he ha ha')

            node = core.formTufoByProp('it:dev:pipe', 'mypipe')
            self.eq(node[1].get('it:dev:pipe'), 'mypipe')
            self.nn(core.getTufoByProp('it:dev:str', 'mypipe'))

            node = core.formTufoByProp('it:dev:mutex', 'mymutex')
            self.eq(node[1].get('it:dev:mutex'), 'mymutex')
            self.nn(core.getTufoByProp('it:dev:str', 'mymutex'))

            node = core.formTufoByProp('it:dev:regkey', 'myregkey')
            self.eq(node[1].get('it:dev:regkey'), 'myregkey')
            self.nn(core.getTufoByProp('it:dev:str', 'myregkey'))

            node = core.eval(r'[ it:dev:regval=("HKEY_LOCAL_MACHINE\\Foo\\Bar", str=hehe) ]')[0]
            self.eq(node[1].get('it:dev:regval:key'), r'hkey_local_machine\foo\bar')
            self.eq(node[1].get('it:dev:regval:str'), 'hehe')

            node = core.eval(r'[ it:dev:regval=("HKEY_LOCAL_MACHINE\\Foo\\Bar", int=20) ]')[0]
            self.eq(node[1].get('it:dev:regval:key'), r'hkey_local_machine\foo\bar')
            self.eq(node[1].get('it:dev:regval:int'), 20)

            iden = guid()
            node = core.eval(r'[ it:dev:regval=("HKEY_LOCAL_MACHINE\\Foo\\Bar", bytes=%s) ]' % iden)[0]
            self.eq(node[1].get('it:dev:regval:key'), r'hkey_local_machine\foo\bar')
            self.eq(node[1].get('it:dev:regval:bytes'), iden)

    def test_model_infotech_hostexec(self):
        with self.getRamCore() as core:

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
            node = core.formTufoByProp('it:exec:proc', proc, pid=20, time=tick, host=host, user='visi', exe=exe,
                                       path=path)
            self.eq(node[1].get('it:exec:proc'), proc)
            self.eq(node[1].get('it:exec:proc:exe'), exe)
            self.eq(node[1].get('it:exec:proc:pid'), 20)
            self.eq(node[1].get('it:exec:proc:time'), tick)
            self.eq(node[1].get('it:exec:proc:host'), host)
            self.eq(node[1].get('it:exec:proc:user'), 'visi')
            self.eq(node[1].get('it:exec:proc:path'), norm)

            p0 = guid()
            f0 = guid()
            node = core.formTufoByProp('it:exec:proc', p0, **{'src:proc': proc, 'src:exe': f0})
            self.eq(node[1].get('it:exec:proc'), p0)
            self.eq(node[1].get('it:exec:proc:src:proc'), proc)
            self.eq(node[1].get('it:exec:proc:src:exe'), f0)

            node = core.formTufoByProp('it:exec:mutex', '*', host=host, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:mutex:exe'), exe)
            self.eq(node[1].get('it:exec:mutex:host'), host)
            self.eq(node[1].get('it:exec:mutex:proc'), proc)

            node = core.formTufoByProp('it:exec:pipe', '*', host=host, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:pipe:exe'), exe)
            self.eq(node[1].get('it:exec:pipe:host'), host)
            self.eq(node[1].get('it:exec:pipe:proc'), proc)

            node = core.formTufoByProp('it:exec:file:add', '*', host=host, path=path, file=file, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:file:add:exe'), exe)
            self.eq(node[1].get('it:exec:file:add:host'), host)
            self.eq(node[1].get('it:exec:file:add:proc'), proc)
            self.eq(node[1].get('it:exec:file:add:file'), file)
            self.eq(node[1].get('it:exec:file:add:path'), norm)

            node = core.formTufoByProp('it:exec:file:del', '*', host=host, path=path, file=file, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:file:del:exe'), exe)
            self.eq(node[1].get('it:exec:file:del:host'), host)
            self.eq(node[1].get('it:exec:file:del:proc'), proc)
            self.eq(node[1].get('it:exec:file:del:file'), file)
            self.eq(node[1].get('it:exec:file:del:path'), norm)
            self.eq(node[1].get('it:exec:file:del:time'), tick)

            node = core.formTufoByProp('it:exec:bind:tcp', '*', host=host, port=port, ipv4=ipv4, ipv6=ipv6, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:bind:tcp:exe'), exe)
            self.eq(node[1].get('it:exec:bind:tcp:host'), host)
            self.eq(node[1].get('it:exec:bind:tcp:port'), port)
            self.eq(node[1].get('it:exec:bind:tcp:ipv4'), ipv4)
            self.eq(node[1].get('it:exec:bind:tcp:ipv6'), ipv6)
            self.eq(node[1].get('it:exec:bind:tcp:proc'), proc)
            self.eq(node[1].get('it:exec:bind:tcp:time'), tick)

            node = core.formTufoByProp('it:exec:bind:udp', '*', host=host, port=port, ipv4=ipv4, ipv6=ipv6, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:bind:udp:exe'), exe)
            self.eq(node[1].get('it:exec:bind:udp:host'), host)
            self.eq(node[1].get('it:exec:bind:udp:port'), port)
            self.eq(node[1].get('it:exec:bind:udp:ipv4'), ipv4)
            self.eq(node[1].get('it:exec:bind:udp:ipv6'), ipv6)
            self.eq(node[1].get('it:exec:bind:udp:proc'), proc)
            self.eq(node[1].get('it:exec:bind:udp:time'), tick)

            regval = initcomp('foo/bar', int=20)
            node = core.formTufoByProp('it:exec:reg:del', '*', host=host, reg=regval, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:reg:del:reg:int'), 20)
            self.eq(node[1].get('it:exec:reg:del:reg:key'), 'foo/bar')
            self.eq(node[1].get('it:exec:reg:del:exe'), exe)
            self.eq(node[1].get('it:exec:reg:del:host'), host)
            self.eq(node[1].get('it:exec:reg:del:proc'), proc)
            self.eq(node[1].get('it:exec:reg:del:time'), tick)

            regval = initcomp('foo/bar', str='hehe')
            node = core.formTufoByProp('it:exec:reg:set', '*', host=host, reg=regval, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:reg:set:reg:str'), 'hehe')
            self.eq(node[1].get('it:exec:reg:set:reg:key'), 'foo/bar')
            self.eq(node[1].get('it:exec:reg:set:exe'), exe)
            self.eq(node[1].get('it:exec:reg:set:host'), host)
            self.eq(node[1].get('it:exec:reg:set:proc'), proc)
            self.eq(node[1].get('it:exec:reg:set:time'), tick)

            regval = initcomp('foo/bar', int=20)
            node = core.formTufoByProp('it:exec:reg:get', '*', host=host, reg=regval, exe=exe, proc=proc, time=tick)
            self.eq(node[1].get('it:exec:reg:get:reg:int'), 20)
            self.eq(node[1].get('it:exec:reg:get:reg:key'), 'foo/bar')
            self.eq(node[1].get('it:exec:reg:get:exe'), exe)
            self.eq(node[1].get('it:exec:reg:get:host'), host)
            self.eq(node[1].get('it:exec:reg:get:proc'), proc)
            self.eq(node[1].get('it:exec:reg:get:time'), tick)

    def test_model_infotech_semvertype(self):
        with self.getRamCore() as core:
            # Norm tests with strings
            data = (
                ('1.2.3', (0x000010000200003,
                           {'major': 1, 'minor': 2, 'patch': 3, })),
                ('0.0.1', (0x000000000000001,
                           {'major': 0, 'minor': 0, 'patch': 1, })),
                ('1.2.3-alpha', (0x000010000200003,
                                 {'major': 1, 'minor': 2, 'patch': 3,
                                 'pre': 'alpha', })),
                ('1.2.3-alpha.1', (0x000010000200003,
                                   {'major': 1, 'minor': 2, 'patch': 3,
                                   'pre': 'alpha.1', })),
                ('1.2.3-0.3.7', (0x000010000200003,
                                 {'major': 1, 'minor': 2, 'patch': 3,
                                 'pre': '0.3.7', })),
                ('1.2.3-x.7.z.92', (0x000010000200003,
                                    {'major': 1, 'minor': 2, 'patch': 3,
                                    'pre': 'x.7.z.92', })),
                ('1.2.3-alpha+001', (0x000010000200003,
                                     {'major': 1, 'minor': 2, 'patch': 3,
                                     'pre': 'alpha', 'build': '001'})),
                ('1.2.3+20130313144700', (0x000010000200003,
                                          {'major': 1, 'minor': 2, 'patch': 3,
                                          'build': '20130313144700'})),
                ('1.2.3-beta+exp.sha.5114f85', (0x000010000200003,
                                                {'major': 1, 'minor': 2, 'patch': 3,
                                                'pre': 'beta',
                                                 'build': 'exp.sha.5114f85'})),
                # Real world examples
                ('1.2.3-B5CD5743F', (0x000010000200003,
                                     {'major': 1, 'minor': 2, 'patch': 3,
                                     'pre': 'B5CD5743F', })),
                ('V1.2.3', (0x000010000200003,
                            {'major': 1, 'minor': 2, 'patch': 3, })),
                ('V1.4.0-RC0', (0x000010000400000,
                                {'major': 1, 'minor': 4, 'patch': 0,
                                'pre': 'RC0', })),
                ('v2.4.1-0.3.rc1', (0x000020000400001,
                                   {'major': 2, 'minor': 4, 'patch': 1,
                                    'pre': '0.3.rc1'})),
                ('0.18.1', (0x000000001200001,
                            {'major': 0, 'minor': 18, 'patch': 1, })),
            )
            for s, e in data:
                ev, es = e
                valu, subs = core.getTypeNorm('it:semver', s)
                self.eq(valu, ev)
                self.eq(subs, es)

            # norm ints
            data = (
                (0, {'major': 0, 'minor': 0, 'patch': 0}),
                (1, {'major': 0, 'minor': 0, 'patch': 1}),
                (2, {'major': 0, 'minor': 0, 'patch': 2}),
                (0xFFFFF, {'major': 0, 'minor': 0, 'patch': 0xFFFFF}),
                (0xFFFFF + 1, {'major': 0, 'minor': 1, 'patch': 0}),
                (0xdeadb33f1337133, {'major': 0xdeadb, 'minor': 0x33f13, 'patch': 0x37133}),
                (0xFFFFFFFFFFFFFFF, {'major': 0xFFFFF, 'minor': 0xFFFFF, 'patch': 0xFFFFF})
            )
            for intval, e in data:
                valu, subs = core.getTypeNorm('it:semver', intval)
                self.eq(valu, intval)
                self.eq(subs, e)

            # Bad strings / ints
            badsemvers = (
                # Invalid strings
                '1',
                '1.2',
                '2.0A1',
                '0.18rc2',
                '0.0.00001',
                '2016-03-01',
                'v2.4.0.0-1',
                '1.3a2.dev12',
                'OpenSSL_1_0_2l',
                '1.2.windows-RC1',
                'v2.4.1.0-0.3.rc1',
                # invalid ints
                -1,
                0xFFFFFFFFFFFFFFFFFFFFFFFF + 1,
                # Invalid build and prerelease values
                '1.2.3-alpha.foo..+001',
                '1.2.3-alpha.foo.001+001',
                '1.2.3-alpha+001.blahblahblah...',
                '1.2.3-alpha+001.blahblahblah.*iggy',
                # Just bad input
                (),
                '   ',
                ' alpha ',

            )
            for valu in badsemvers:
                self.raises(BadTypeValu, core.getTypeNorm, 'it:semver', valu)

            reprs = (
                (0, '0.0.0'),
                (1, '0.0.1'),
                (0x000010000200003, '1.2.3'),
            )
            for v, e in reprs:
                self.eq(core.getTypeRepr('it:semver', v), e)

    def test_model_infotech_brutecast(self):

        with self.getRamCore() as core:

            # Try some integers
            valu = core.getTypeCast('it:version:brute', s_version.packVersion(1))
            self.eq(valu, 0x000010000000000)

            valu = core.getTypeCast('it:version:brute', s_version.packVersion(1, 2, 255))
            self.eq(valu, 0x0000100002000FF)

            valu = core.getTypeCast('it:version:brute', '1')
            self.eq(valu, 0x000010000000000)

            # A valid semver
            valu = core.getTypeCast('it:version:brute', '1.2.3-B5CD5743F')
            self.eq(valu, 0x000010000200003)

            valu = core.getTypeCast('it:version:brute', '1.2.3-beta+exp.sha.5114f85')
            self.eq(valu, 0x000010000200003)

            # Part extections
            data = (
                ('1', (0x000010000000000,
                       {'major': 1, 'minor': 0, 'patch': 0})),
                ('2.0A1', (0x000020000000000,
                           {'major': 2, 'minor': 0, 'patch': 0})),
                ('2016-03-01', (0x007e00000300001,
                                {'major': 2016, 'minor': 3, 'patch': 1})),
                ('1.2.windows-RC1', (0x000010000200000,
                                     {'major': 1, 'minor': 2, 'patch': 0})),
                ('3.4', (0x000030000400000,
                         {'major': 3, 'minor': 4, 'patch': 0})),
                ('1.3a2.dev12', (0x000010000000000,
                                 {'major': 1, 'minor': 0, 'patch': 0})),
                ('v2.4.0.0-1', (0x000020000400000,
                                {'major': 2, 'minor': 4, 'patch': 0})),
                ('v2.4.1.0-0.3.rc1', (0x000020000400001,
                                      {'major': 2, 'minor': 4, 'patch': 1})),
                ('0.18rc2', (0, {'major': 0, 'minor': 0, 'patch': 0})),
                ('OpenSSL_1_0_2l', (0x000010000000000,
                                    {'major': 1, 'minor': 0, 'patch': 0})),
            )

            for s, e in data:
                ev, es = e
                valu = core.getTypeCast('it:version:brute', s)
                self.eq(valu, ev)

            self.raises(BadTypeValu, core.getTypeCast, 'it:version:brute', 'alpha')
            self.raises(BadTypeValu, core.getTypeCast, 'it:version:brute', ())

    def test_model_infotech_software(self):
        with self.getRamCore() as core:
            a1 = core.formTufoByProp('inet:web:acct', 'vertex.link/pennywise')
            o1 = core.formTufoByProp('ou:org:alias', 'deadlights')
            p1 = core.formTufoByProp('ps:person', [['guidname', 'Robert Gray']])
            h1 = core.formTufoByProp('it:host', '(name=pennywise001)')
            self.nn(a1)
            self.nn(o1)
            self.nn(p1)
            self.nn(h1)
            # Random guid
            s1 = core.formTufoByProp('it:prod:soft', '*',
                                     **{'name': 'Balloon Maker',
                                        'desc': "Pennywise's patented balloon blower uper",
                                        'desc:short': 'Balloon blower',
                                        'author:org': o1[1].get('ou:org'),
                                        'author:acct': a1[1].get('inet:web:acct'),
                                        'author:person': p1[1].get('ps:person'),
                                        'url': 'https://vertex.link/products/balloonmaker'
                                        })
            self.eq(s1[1].get('it:prod:soft:name'), 'balloon maker')
            self.eq(s1[1].get('it:prod:soft:desc'), "Pennywise's patented balloon blower uper")
            self.eq(s1[1].get('it:prod:soft:desc:short'), 'balloon blower')
            self.eq(s1[1].get('it:prod:soft:author:acct'), a1[1].get('inet:web:acct'),)
            self.eq(s1[1].get('it:prod:soft:author:org'), o1[1].get('ou:org'))
            self.eq(s1[1].get('it:prod:soft:author:person'), p1[1].get('ps:person'))
            self.eq(s1[1].get('it:prod:soft:url'), 'https://vertex.link/products/balloonmaker')

            # Stable guid
            s2 = core.formTufoByProp('it:prod:soft', '(name="Balloon Maker",author:acct=vertex.link/pennywise)')
            self.eq(s2[1].get('it:prod:soft'), '5fd0340d2ad8878fe53ccd28843ff2dc')

            nodes = core.getTufosByProp('it:prod:soft:name', 'balloon maker')
            self.len(2, nodes)

            # Make some version nodes
            # Ensure :semver is populated by the vers value.
            sv1 = core.formTufoByProp('it:prod:softver',
                                     '*',
                                     software='5fd0340d2ad8878fe53ccd28843ff2dc',
                                     vers='V1.0.1',
                                     url='https://vertex.link/products/balloonmaker/release_101.exe'
                                     )
            self.eq(sv1[1].get('it:prod:softver:software'), '5fd0340d2ad8878fe53ccd28843ff2dc')
            self.eq(sv1[1].get('it:prod:softver:software:name'), 'balloon maker')
            self.eq(sv1[1].get('it:prod:softver:vers'), 'V1.0.1')
            self.eq(sv1[1].get('it:prod:softver:vers:norm'), 'v1.0.1')
            self.eq(sv1[1].get('it:prod:softver:semver'), 0x000010000000001)
            self.eq(sv1[1].get('it:prod:softver:semver:major'), 1)
            self.eq(sv1[1].get('it:prod:softver:semver:minor'), 0)
            self.eq(sv1[1].get('it:prod:softver:semver:patch'), 1)
            self.eq(sv1[1].get('it:prod:softver:url'),
                    'https://vertex.link/products/balloonmaker/release_101.exe')
            # Link the softver to a host
            hs1 = core.formTufoByProp('it:hostsoft',
                                      (h1[1].get('it:host'),
                                       sv1[1].get('it:prod:softver')),
                                      **{'seen:min': '2013',
                                         'seen:max': '2017', }
                                      )
            self.eq(hs1[1].get('it:hostsoft:host'), h1[1].get('it:host'))
            self.eq(hs1[1].get('it:hostsoft:softver'), sv1[1].get('it:prod:softver'))
            self.eq(hs1[1].get('it:hostsoft:seen:min'), core.getTypeNorm('time', '2013')[0])
            self.eq(hs1[1].get('it:hostsoft:seen:max'), core.getTypeNorm('time', '2017')[0])

            nodes = core.eval('it:prod:soft:name="balloon maker" ->it:prod:softver:software ->it:hostsoft:softver '
                              ':host->it:host')
            self.len(1, nodes)
            form, prop = s_tufo.ndef(nodes[0])
            self.eq(form, 'it:host')
            self.eq(prop, 'e862b0d7f3a9e015171a4113e0dbe861')

            # Go backwards from the host
            nodes = core.eval('it:host=e862b0d7f3a9e015171a4113e0dbe861 ->it:hostsoft:host :softver '
                              '->it:prod:softver')
            self.len(1, nodes)
            form, prop = s_tufo.ndef(nodes[0])
            self.eq(form, 'it:prod:softver')
            self.eq(prop, sv1[1].get('it:prod:softver'))

            # Make a bunch of softver nodes in order to do filtering via storm
            sv = core.formTufoByProp('it:prod:softver',
                                      (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                       ('vers', 'V1.0.0'))
                                      )
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', 'V1.1.0'))
                                     )
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', 'V0.0.1'))
                                     )
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', 'V0.1.0'))
                                     )
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', '0.1.1'))
                                     )
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', 'V2.0.0-alpha+b1'))
                                     )

            nodes = core.eval('it:prod:softver:semver<1.0.0')
            self.len(3, nodes)
            nodes = core.eval('it:prod:softver:semver<1.0.0 +it:prod:softver:semver:minor=1')
            self.len(2, nodes)
            nodes = core.eval('it:prod:softver:semver<=1.0.0')
            self.len(4, nodes)
            nodes = core.eval('it:prod:softver:semver>1.1.0')
            self.len(1, nodes)
            nodes = core.eval('it:prod:softver:semver:pre=alpha')
            self.len(1, nodes)

            # Try some non-standard semver values
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', '  OhMy2016-12-10  '))
                                     )
            self.eq(sv[1].get('it:prod:softver:vers'), '  OhMy2016-12-10  ')
            self.eq(sv[1].get('it:prod:softver:vers:norm'), 'ohmy2016-12-10')
            self.eq(sv[1].get('it:prod:softver:semver:major'), 2016)
            self.eq(sv[1].get('it:prod:softver:semver:minor'), 12)
            self.eq(sv[1].get('it:prod:softver:semver:patch'), 10)
            nodes = core.eval('it:prod:softver:semver:major=2016')
            self.len(1, nodes)

            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', '1.2'))
                                     )
            self.eq(sv[1].get('it:prod:softver:semver:major'), 1)
            self.eq(sv[1].get('it:prod:softver:semver:minor'), 2)
            self.none(sv[1].get('it:prod:softver:semver:patch'))

            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', '1.2.3.4'))
                                     )
            self.eq(sv[1].get('it:prod:softver:semver:major'), 1)
            self.eq(sv[1].get('it:prod:softver:semver:minor'), 2)
            self.eq(sv[1].get('it:prod:softver:semver:patch'), 3)

            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', 'AlPHa'))
                                     )
            self.eq(sv[1].get('it:prod:softver:vers'), 'AlPHa')
            self.eq(sv[1].get('it:prod:softver:vers:norm'), 'alpha')
            self.none(sv[1].get('it:prod:softver:semver'))

            # Set the software:name directly
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', 'beta')),
                                     **{'software:name': 'ballon maker-beta'}
                                     )
            self.eq(sv[1].get('it:prod:softver:vers'), 'beta')
            self.eq(sv[1].get('it:prod:softver:software:name'), 'ballon maker-beta')

            # Set the semver value separately from the vers.
            # This bypasses the node:form callback from setting the prop and instead
            # relys on regular prop-norming.
            sv = core.formTufoByProp('it:prod:softver',
                                     (('software', '5fd0340d2ad8878fe53ccd28843ff2dc'),
                                      ('vers', 'AlPHa001')),
                                     semver='0.0.1-alpha+build.001'
                                     )
            self.eq(sv[1].get('it:prod:softver:vers'), 'AlPHa001')
            self.eq(sv[1].get('it:prod:softver:vers:norm'), 'alpha001')
            self.eq(sv[1].get('it:prod:softver:semver'), 1)
            self.eq(sv[1].get('it:prod:softver:semver:major'), 0)
            self.eq(sv[1].get('it:prod:softver:semver:minor'), 0)
            self.eq(sv[1].get('it:prod:softver:semver:patch'), 1)
            self.eq(sv[1].get('it:prod:softver:semver:build'), 'build.001')
            self.eq(sv[1].get('it:prod:softver:semver:pre'), 'alpha')

    def test_model_infotech_passwdhash(self):

        with self.getRamCore() as core:

            md5_node = core.formTufoByProp('it:auth:passwdhash', '(salt=f0f0,hash:md5=%s)' % s_m_crypto.ex_md5)
            sha1_node = core.formTufoByProp('it:auth:passwdhash', '(salt=f0f0,hash:sha1=%s)' % s_m_crypto.ex_sha1)
            sha256_node = core.formTufoByProp('it:auth:passwdhash', '(salt=f0f0,hash:sha256=%s)' % s_m_crypto.ex_sha256)
            sha512_node = core.formTufoByProp('it:auth:passwdhash', '(salt=f0f0,hash:sha512=%s)' % s_m_crypto.ex_sha512)

            self.eq(md5_node[1].get('it:auth:passwdhash:salt'), 'f0f0')
            self.eq(md5_node[1].get('it:auth:passwdhash:hash:md5'), s_m_crypto.ex_md5)

            self.eq(sha1_node[1].get('it:auth:passwdhash:salt'), 'f0f0')
            self.eq(sha1_node[1].get('it:auth:passwdhash:hash:sha1'), s_m_crypto.ex_sha1)

            self.eq(sha256_node[1].get('it:auth:passwdhash:salt'), 'f0f0')
            self.eq(sha256_node[1].get('it:auth:passwdhash:hash:sha256'), s_m_crypto.ex_sha256)

            self.eq(sha512_node[1].get('it:auth:passwdhash:salt'), 'f0f0')
            self.eq(sha512_node[1].get('it:auth:passwdhash:hash:sha512'), s_m_crypto.ex_sha512)

            node = core.setTufoProp(md5_node, 'passwd', 'foobar')
            self.eq(node[1].get('it:auth:passwdhash:passwd'), 'foobar')

            self.nn(core.getTufoByProp('inet:passwd', 'foobar'))

            node = core.formTufoByProp('it:auth:passwdhash', {'hash:lm': s_m_crypto.ex_md5})
            self.eq(node[1].get('it:auth:passwdhash:hash:lm'), s_m_crypto.ex_md5)

            node = core.formTufoByProp('it:auth:passwdhash', {'hash:ntlm': s_m_crypto.ex_md5})
            self.eq(node[1].get('it:auth:passwdhash:hash:ntlm'), s_m_crypto.ex_md5)

            self.raises(BadTypeValu, core.formTufoByProp, 'it:auth:passwdhash', {'salt': 'asdf', 'hash:md5': s_m_crypto.ex_md5})
