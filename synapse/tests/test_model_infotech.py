import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.tufo as s_tufo
import synapse.lib.version as s_version

import synapse.models.crypto as s_m_crypto

import synapse.tests.common as s_test

# 010 TODO / Fixme!
# Test it:prod:softver by range!
#

class InfotechModelTest(s_test.SynTest):
    def test_it_forms_simple(self):
        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                node = snap.addNode('it:hostname', 'Bobs Computer')
                self.eq(node.ndef[1], 'bobs computer')
                host0 = s_common.guid()
                hprops = {
                    'name': 'Bobs laptop',
                    'desc': 'Bobs paperweight',
                    'ipv4': '1.2.3.4',
                    'latlong': '0.0, 0.0'
                }
                node = snap.addNode('it:host', host0, hprops)
                self.eq(node.ndef[1], host0)
                self.eq(node.get('name'), 'bobs laptop')
                self.eq(node.get('desc'), 'Bobs paperweight')
                self.eq(node.get('ipv4'), 0x01020304)
                self.eq(node.get('latlong'), (0.0, 0.0))

                node = snap.addNode('it:hosturl', (host0, 'http://vertex.ninja/cool.php'))
                self.eq(node.ndef[1], (host0, 'http://vertex.ninja/cool.php'))
                self.eq(node.get('host'), host0)
                self.eq(node.get('url'), 'http://vertex.ninja/cool.php')

                node = snap.addNode('it:dev:int', 0x61C88648)
                self.eq(node.ndef[1], 1640531528)

                cprops = {
                    'desc': 'Some words.',
                }
                node = snap.addNode('it:sec:cve', 'CVE-2013-9999', cprops)
                self.eq(node.ndef[1], 'cve-2013-9999')
                self.eq(node.get('desc'), 'Some words.')

                hash0 = s_common.guid()
                hprops = {
                    'salt': 'B33F',
                    'hash:md5': s_m_crypto.ex_md5,
                    'hash:sha1': s_m_crypto.ex_sha1,
                    'hash:sha256': s_m_crypto.ex_sha256,
                    'hash:sha512': s_m_crypto.ex_sha512,
                    'hash:lm': s_m_crypto.ex_md5,
                    'hash:ntlm': s_m_crypto.ex_md5,
                    'passwd': "I've got the same combination on my luggage!",
                }
                node = snap.addNode('it:auth:passwdhash', hash0, hprops)
                self.eq(node.ndef[1], hash0)
                self.eq(node.get('salt'), 'b33f')
                self.eq(node.get('hash:md5'), s_m_crypto.ex_md5)
                self.eq(node.get('hash:sha1'), s_m_crypto.ex_sha1)
                self.eq(node.get('hash:sha256'), s_m_crypto.ex_sha256)
                self.eq(node.get('hash:sha512'), s_m_crypto.ex_sha512)
                self.eq(node.get('hash:lm'), s_m_crypto.ex_md5)
                self.eq(node.get('hash:ntlm'), s_m_crypto.ex_md5)
                self.eq(node.get('passwd'), "I've got the same combination on my luggage!")

    def test_it_forms_prodsoft(self):
        # Test all prodsoft and prodsoft associated linked forms
        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                # it:prod:soft
                prod0 = s_common.guid()
                org0 = s_common.guid()
                person0 = s_common.guid()
                acct0 = ('vertex.link', 'pennywise')
                url0 = 'https://vertex.link/products/balloonmaker'
                sprops = {
                    'name': 'Balloon Maker',
                    'desc': "Pennywise's patented balloon blower upper",
                    'desc:short': 'Balloon blower',
                    'author:org': org0,
                    'author:acct': acct0,
                    'author:person': person0,
                    'url': url0,
                }
                node = snap.addNode('it:prod:soft', prod0, sprops)
                self.eq(node.ndef[1], prod0)
                self.eq(node.get('name'), 'balloon maker')
                self.eq(node.get('desc'), "Pennywise's patented balloon blower upper")
                self.eq(node.get('desc:short'), 'balloon blower')
                self.eq(node.get('author:org'), org0)
                self.eq(node.get('author:acct'), acct0)
                self.eq(node.get('author:person'), person0)
                self.eq(node.get('url'), url0)

                # it:prod:softver - this does test a bunch of property related callbacks
                url1 = 'https://vertex.link/products/balloonmaker/release_101-beta.exe'
                vprops = {
                    'vers': 'V1.0.1-beta+exp.sha.5114f85',
                    'url': url1,
                    'software': prod0,
                    'arch': 'amd64'
                }
                ver0 = s_common.guid()
                node = snap.addNode('it:prod:softver', ver0, vprops)

                self.eq(node.ndef[1], ver0)
                self.eq(node.get('arch'), 'amd64')
                self.eq(node.get('software'), prod0)
                self.eq(node.get('software:name'), 'balloon maker')
                self.eq(node.get('vers'), 'V1.0.1-beta+exp.sha.5114f85')
                self.eq(node.get('vers:norm'), 'v1.0.1-beta+exp.sha.5114f85')
                self.eq(node.get('semver'), 0x000010000000001)
                self.eq(node.get('semver:major'), 1)
                self.eq(node.get('semver:minor'), 0)
                self.eq(node.get('semver:patch'), 1)
                self.eq(node.get('semver:pre'), 'beta')
                self.eq(node.get('semver:build'), 'exp.sha.5114f85')
                self.eq(node.get('url'), url1)
                # callback node creation checks
                nodes = list(snap.getNodesBy('it:dev:str', 'V1.0.1-beta+exp.sha.5114f85'))
                self.len(1, nodes)
                nodes = list(snap.getNodesBy('it:dev:str', 'amd64'))
                self.len(1, nodes)

                host0 = s_common.guid()
                node = snap.addNode('it:hostsoft', (host0, ver0))
                self.eq(node.ndef[1], (host0, ver0))
                self.eq(node.get('host'), host0)
                self.eq(node.get('softver'), ver0)

                prod1 = s_common.guid()
                sigprops = {
                    'desc': 'The evil balloon virus!',
                    'url': url1,
                }
                sig0 = (prod1, 'Bar.BAZ.faZ')
                node = snap.addNode('it:av:sig', sig0, sigprops)
                self.eq(node.ndef[1], (prod1, 'Bar.BAZ.faZ'.lower()))
                self.eq(node.get('soft'), prod1)
                self.eq(node.get('name'), 'bar.baz.faz')
                self.eq(node.get('desc'), 'The evil balloon virus!')
                self.eq(node.get('url'), url1)

                file0 = 'a' * 64
                node = snap.addNode('it:av:filehit', (file0, sig0))
                self.eq(node.ndef[1], (f'sha256:{file0}', (prod1, 'Bar.BAZ.faZ'.lower())))
                self.eq(node.get('file'), f'sha256:{file0}')
                self.eq(node.get('sig'), (prod1, 'Bar.BAZ.faZ'.lower()))

                # Test 'vers' semver brute forcing
                testvectors = [
                    ('1', 0x000010000000000, {'major': 1, 'minor': 0, 'patch': 0}),
                    ('2.0A1', 0x000020000000000, {'major': 2, 'minor': 0, 'patch': 0}),
                    ('2016-03-01', 0x007e00000300001, {'major': 2016, 'minor': 3, 'patch': 1}),
                    ('1.2.windows-RC1', 0x000010000200000, {'major': 1, 'minor': 2, 'patch': 0}),
                    ('3.4', 0x000030000400000, {'major': 3, 'minor': 4, 'patch': 0}),
                    ('1.3a2.dev12', 0x000010000000000, {'major': 1, 'minor': 0, 'patch': 0}),
                    ('v2.4.0.0-1', 0x000020000400000, {'major': 2, 'minor': 4, 'patch': 0}),
                    ('v2.4.1.0-0.3.rc1', 0x000020000400001, {'major': 2, 'minor': 4, 'patch': 1}),
                    ('0.18rc2', 0, {'major': 0, 'minor': 0, 'patch': 0}),
                    ('OpenSSL_1_0_2l', 0x000010000000000, {'major': 1, 'minor': 0, 'patch': 0}),
                ]
                for tv, te, subs in testvectors:
                    props = {
                        'vers': tv
                    }
                    node = snap.addNode('it:prod:softver', '*', props)
                    self.eq(node.get('semver'), te)
                    self.eq(node.get('semver:major'), subs.get('major'))
                    self.eq(node.get('semver:minor'), subs.get('minor'))
                    self.eq(node.get('semver:patch'), subs.get('patch'))

                node = snap.addNode('it:prod:softver', '*', {'vers': ''})
                self.eq(node.get('vers'), '')
                self.none(node.get('vers:norm'))
                self.none(node.get('semver'))

                with self.getLoggerStream('synapse.models.infotech',
                                          'Unable to brute force version parts out of the string') as stream:

                    node = snap.addNode('it:prod:softver', '*', {'vers': 'Alpha'})
                    self.none(node.get('semver'))
                    self.true(stream.is_set())

    def test_it_form_callbacks(self):
        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                # it:dev:str kicks out the :norm property on him when he is made
                node = snap.addNode('it:dev:str', 'evil RAT')
                self.eq(node.ndef[1], 'evil RAT')
                self.eq(node.get('norm'), 'evil rat')

                pipe = 'MyPipe'
                node = snap.addNode('it:dev:pipe', pipe)
                self.eq(node.ndef[1], pipe)
                nodes = list(snap.getNodesBy('it:dev:str', pipe))
                self.len(1, nodes)
                # The callback created node also has norm set on it
                self.eq(nodes[0].get('norm'), pipe.lower())

                mutex = 'MyMutxex'
                node = snap.addNode('it:dev:mutex', mutex)
                self.eq(node.ndef[1], mutex)
                nodes = list(snap.getNodesBy('it:dev:str', mutex))
                self.len(1, nodes)

                key = 'HKEY_LOCAL_MACHINE\\Foo\\Bar'
                node = snap.addNode('it:dev:regkey', key)
                self.eq(node.ndef[1], key)
                nodes = list(snap.getNodesBy('it:dev:str', key))
                self.len(1, nodes)

                fbyts = 'sha256:' + 64 * 'f'
                key = 'HKEY_LOCAL_MACHINE\\DUCK\\QUACK'
                valus = [
                    ('str', 'knight'),
                    ('int', 20),
                    ('bytes', fbyts),
                ]
                for prop, valu in valus:
                    guid = s_common.guid((key, valu))
                    props = {
                        'key': key,
                        prop: valu,
                    }
                    node = snap.addNode('it:dev:regval', guid, props)
                    self.eq(node.ndef[1], guid)
                    self.eq(node.get('key'), key)
                    self.eq(node.get(prop), valu)

                nodes = list(snap.getNodesBy('it:dev:str', key))
                self.len(1, nodes)

    def test_it_semvertype(self):
        with self.getTestCore() as core:
            t = core.model.type('it:semver')
            testvectors = (
                # Strings
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
                # Integer values
                (0, (0, {'major': 0, 'minor': 0, 'patch': 0})),
                (1, (1, {'major': 0, 'minor': 0, 'patch': 1})),
                (2, (2, {'major': 0, 'minor': 0, 'patch': 2})),
                (0xFFFFF, (0xFFFFF, {'major': 0, 'minor': 0, 'patch': 0xFFFFF})),
                (0xFFFFF + 1, (0xFFFFF + 1, {'major': 0, 'minor': 1, 'patch': 0})),
                (0xdeadb33f1337133, (0xdeadb33f1337133, {'major': 0xdeadb, 'minor': 0x33f13, 'patch': 0x37133})),
                (0xFFFFFFFFFFFFFFF, (0xFFFFFFFFFFFFFFF, {'major': 0xFFFFF, 'minor': 0xFFFFF, 'patch': 0xFFFFF}))
            )

            for v, e in testvectors:
                ev, es = e
                valu, rdict = t.norm(v)
                subs = rdict.get('subs')
                self.eq(valu, ev)
                self.eq(subs, es)

            testvectors_bad = (
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
                '   ',
                ' alpha ',
            )
            for v in testvectors_bad:
                self.raises(s_exc.BadTypeValu, t.norm, v)

            testvectors_repr = (
                (0, '0.0.0'),
                (1, '0.0.1'),
                (0x000010000200003, '1.2.3'),
            )
            for v, e in testvectors_repr:
                self.eq(t.repr(v), e)

    def test_it_forms_hostexec(self):
        # forms related to the host execution model
        with self.getTestCore() as core:
            with core.snap(write=True) as snap:
                exe = 'sha256:' + 'a' * 64
                port = 80
                tick = s_common.now()
                host = s_common.guid()
                proc = s_common.guid()
                mutex = 'giggleXX_X0'
                pipe = 'pipe\\mynamedpipe'
                user = 'serviceadmin'
                pid = 20
                key = 'HKEY_LOCAL_MACHINE\\Foo\\Bar'
                ipv4 = 0x01020304
                ipv6 = '::1'

                addr4 = f'tcp://1.2.3.4:{port}'
                addr6 = f'udp://[::1]:{port}'
                url = 'http://www.google.com/sekrit.html'
                raw_path = r'c:\Windows\System32\rar.exe'
                norm_path = r'c:/windows/system32/rar.exe'
                src_proc = s_common.guid()
                src_path = r'c:/temp/ping.exe'
                cmd0 = 'rar a -r yourfiles.rar *.txt'
                fpath = 'c:/temp/yourfiles.rar'
                fbyts = 'sha256:' + 'b' * 64
                pprops = {
                    'exe': exe,
                    'pid': pid,
                    'cmd': cmd0,
                    'host': host,
                    'time': tick,
                    'user': user,
                    'path': raw_path,
                    'src:exe': src_path,
                    'src:proc': src_proc,
                }
                node = snap.addNode('it:exec:proc', proc, pprops)
                self.eq(node.ndef[1], proc)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('pid'), pid)
                self.eq(node.get('cmd'), cmd0)
                self.eq(node.get('host'), host)
                self.eq(node.get('time'), tick)
                self.eq(node.get('user'), user)
                self.eq(node.get('path'), norm_path)
                self.eq(node.get('src:exe'), src_path)
                self.eq(node.get('src:proc'), src_proc)

                m0 = s_common.guid()
                mprops = {
                    'exe': exe,
                    'proc': proc,
                    'name': mutex,
                    'host': host,
                    'time': tick,
                }
                node = snap.addNode('it:exec:mutex', m0, mprops)
                self.eq(node.ndef[1], m0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('host'), host)
                self.eq(node.get('time'), tick)
                self.eq(node.get('name'), mutex)

                p0 = s_common.guid()
                pipeprops = {
                    'exe': exe,
                    'proc': proc,
                    'name': pipe,
                    'host': host,
                    'time': tick,
                }
                node = snap.addNode('it:exec:pipe', p0, pipeprops)
                self.eq(node.ndef[1], p0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('host'), host)
                self.eq(node.get('time'), tick)
                self.eq(node.get('name'), pipe)

                u0 = s_common.guid()
                uprops = {
                    'proc': proc,
                    'host': host,
                    'exe': exe,
                    'time': tick,
                    'url': url,
                    'client': addr4,
                }
                node = snap.addNode('it:exec:url', u0, uprops)
                self.eq(node.ndef[1], u0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('host'), host)
                self.eq(node.get('time'), tick)
                self.eq(node.get('url'), url)
                self.eq(node.get('client'), addr4)
                self.eq(node.get('client:ipv4'), ipv4)
                self.eq(node.get('client:port'), port)

                u1 = s_common.guid()
                uprops['client'] = addr6
                node = snap.addNode('it:exec:url', u1, uprops)
                self.eq(node.ndef[1], u1)
                self.eq(node.get('client'), addr6)
                self.eq(node.get('client:ipv6'), ipv6)
                self.eq(node.get('client:port'), port)

                b0 = s_common.guid()
                bprops = {
                    'proc': proc,
                    'host': host,
                    'exe': exe,
                    'time': tick,
                    'server': addr4
                }
                node = snap.addNode('it:exec:bind', b0, bprops)
                self.eq(node.ndef[1], b0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('host'), host)
                self.eq(node.get('time'), tick)
                self.eq(node.get('server'), addr4)
                self.eq(node.get('server:ipv4'), ipv4)
                self.eq(node.get('server:port'), port)

                b1 = s_common.guid()
                bprops['server'] = addr6
                node = snap.addNode('it:exec:bind', b1, bprops)
                self.eq(node.ndef[1], b1)
                self.eq(node.get('server'), addr6)
                self.eq(node.get('server:ipv6'), ipv6)
                self.eq(node.get('server:port'), port)

                faprops = {
                    'exe': exe,
                    'host': host,
                    'proc': proc,
                    'file': fbyts,
                    'time': tick,
                    'path': fpath,
                }
                fa0 = s_common.guid()
                node = snap.addNode('it:exec:file:add', fa0, faprops)
                self.eq(node.ndef[1], fa0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('host'), host)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('time'), tick)
                self.eq(node.get('file'), fbyts)
                self.eq(node.get('path'), fpath)
                self.eq(node.get('path:dir'), 'c:/temp')
                self.eq(node.get('path:base'), 'yourfiles.rar')
                self.eq(node.get('path:ext'), 'rar')

                fr0 = s_common.guid()
                node = snap.addNode('it:exec:file:read', fr0, faprops)
                self.eq(node.ndef[1], fr0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('host'), host)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('time'), tick)
                self.eq(node.get('file'), fbyts)
                self.eq(node.get('path'), fpath)
                self.eq(node.get('path:dir'), 'c:/temp')
                self.eq(node.get('path:base'), 'yourfiles.rar')
                self.eq(node.get('path:ext'), 'rar')

                fw0 = s_common.guid()
                node = snap.addNode('it:exec:file:write', fw0, faprops)
                self.eq(node.ndef[1], fw0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('host'), host)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('time'), tick)
                self.eq(node.get('file'), fbyts)
                self.eq(node.get('path'), fpath)
                self.eq(node.get('path:dir'), 'c:/temp')
                self.eq(node.get('path:base'), 'yourfiles.rar')
                self.eq(node.get('path:ext'), 'rar')

                fd0 = s_common.guid()
                node = snap.addNode('it:exec:file:del', fd0, faprops)
                self.eq(node.ndef[1], fd0)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('host'), host)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('time'), tick)
                self.eq(node.get('file'), fbyts)
                self.eq(node.get('path'), fpath)
                self.eq(node.get('path:dir'), 'c:/temp')
                self.eq(node.get('path:base'), 'yourfiles.rar')
                self.eq(node.get('path:ext'), 'rar')

                file0 = s_common.guid()
                fsprops = {
                    'host': host,
                    'path': fpath,
                    'file': fbyts,
                    'ctime': tick,
                    'mtime': tick + 1,
                    'atime': tick + 2,
                    'user': user,
                    'group': 'domainadmin'
                }
                node = snap.addNode('it:fs:file', file0, fsprops)
                self.eq(node.ndef[1], file0)
                self.eq(node.get('host'), host)
                self.eq(node.get('user'), user)
                self.eq(node.get('group'), 'domainadmin')
                self.eq(node.get('file'), fbyts)
                self.eq(node.get('ctime'), tick)
                self.eq(node.get('mtime'), tick + 1)
                self.eq(node.get('atime'), tick + 2)
                self.eq(node.get('path'), fpath)
                self.eq(node.get('path:dir'), 'c:/temp')
                self.eq(node.get('path:base'), 'yourfiles.rar')
                self.eq(node.get('path:ext'), 'rar')

                # FIXME - This test would be cleaner with stable guid generation
                rprops = {
                    'host': host,
                    'proc': proc,
                    'exe': exe,
                    'time': tick,
                    'reg': '*',
                    'reg:key': key,
                }
                forms = ('it:exec:reg:get',
                         'it:exec:reg:set',
                         'it:exec:reg:del',
                         )
                valus = (('reg:str', 'oh my'),
                         ('reg:int', 20),
                         ('reg:bytes', fbyts),
                         )
                for form in forms:
                    for ekey, valu in valus:
                        rk0 = s_common.guid()
                        nprops = rprops.copy()
                        nprops[ekey] = valu
                        node = snap.addNode(form, rk0, nprops)
                        self.eq(node.ndef[1], rk0)
                        self.eq(node.get('host'), host)
                        self.eq(node.get('proc'), proc)
                        self.eq(node.get('exe'), exe)
                        self.eq(node.get('time'), tick)
                        self.nn(node.get('reg'))
                        self.eq(node.get('reg:key'), key)
                        self.eq(node.get(ekey), valu)

class OldInfoTechTst:
    def test_model_infotech_software(self):
        with self.getRamCore() as core:
            # Make some version nodes
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
