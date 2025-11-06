import hashlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.const as s_const
import synapse.lib.scrape as s_scrape

import synapse.models.crypto as s_m_crypto

import synapse.tests.files as s_t_files
import synapse.tests.utils as s_t_utils
import synapse.tests.test_lib_scrape as s_t_scrape

class InfotechModelTest(s_t_utils.SynTest):

    async def test_infotech_basics(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''[
                it:sec:cwe=CWE-120
                    :name=omg
                    :desc=omgwtfbbq
                    :url=https://cwe.mitre.org/data/definitions/120.html
                    :parents=(CWE-119,)
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:sec:cwe', 'CWE-120'))
            self.eq(nodes[0].get('name'), 'omg')
            self.eq(nodes[0].get('desc'), 'omgwtfbbq')
            self.eq(nodes[0].get('url'), 'https://cwe.mitre.org/data/definitions/120.html')
            self.eq(nodes[0].get('parents'), ('CWE-119',))

            nodes = await core.nodes('''[
                it:exec:thread=*
                    :proc=*
                    :created=20210202
                    :exited=20210203
                    :exitcode=0
                    :src:proc=*
                    :src:thread=*
                    :sandbox:file=*
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].ndef[1])
            self.eq(nodes[0].get('created'), 1612224000000000)
            self.eq(nodes[0].get('exited'), 1612310400000000)
            self.eq(nodes[0].get('exitcode'), 0)
            self.len(1, await core.nodes('it:exec:thread:created :proc -> it:exec:proc'))
            self.len(1, await core.nodes('it:exec:thread:created :src:proc -> it:exec:proc'))
            self.len(1, await core.nodes('it:exec:thread:created :src:thread -> it:exec:thread'))
            self.len(1, await core.nodes('it:exec:thread:created :sandbox:file -> file:bytes'))

            nodes = await core.nodes('''[
                it:exec:loadlib=*
                    :proc=*
                    :va=0x00a000
                    :loaded=20210202
                    :unloaded=20210203
                    :path=/home/invisigoth/rootkit.so
                    :file=*
                    :sandbox:file=*
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].ndef[1])
            self.nn(nodes[0].get('proc'))
            self.eq(nodes[0].get('va'), 0x00a000)
            self.eq(nodes[0].get('loaded'), 1612224000000000)
            self.eq(nodes[0].get('unloaded'), 1612310400000000)
            self.len(1, await core.nodes('it:exec:loadlib :file -> file:bytes'))
            self.len(1, await core.nodes('it:exec:loadlib :proc -> it:exec:proc'))
            self.len(1, await core.nodes('it:exec:loadlib -> file:path +file:path=/home/invisigoth/rootkit.so'))
            self.len(1, await core.nodes('it:exec:loadlib :sandbox:file -> file:bytes'))

            nodes = await core.nodes('''[
                it:exec:mmap=*
                    :proc=*
                    :va=0x00a000
                    :size=4096
                    :perms:read=1
                    :perms:write=0
                    :perms:execute=1
                    :created=20210202
                    :deleted=20210203
                    :path=/home/invisigoth/rootkit.so
                    :hash:sha256=ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c
                    :sandbox:file=*
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].ndef[1])
            self.nn(nodes[0].get('proc'))
            self.eq(nodes[0].get('va'), 0x00a000)
            self.eq(nodes[0].get('size'), 4096)
            self.eq(nodes[0].get('perms:read'), 1)
            self.eq(nodes[0].get('perms:write'), 0)
            self.eq(nodes[0].get('perms:execute'), 1)
            self.eq(nodes[0].get('created'), 1612224000000000)
            self.eq(nodes[0].get('deleted'), 1612310400000000)
            self.eq(nodes[0].get('hash:sha256'), 'ad9f4fe922b61e674a09530831759843b1880381de686a43460a76864ca0340c')
            self.len(1, await core.nodes('it:exec:mmap -> crypto:hash:sha256'))
            self.len(1, await core.nodes('it:exec:mmap :proc -> it:exec:proc'))
            self.len(1, await core.nodes('it:exec:mmap -> file:path +file:path=/home/invisigoth/rootkit.so'))
            self.len(1, await core.nodes('it:exec:mmap :sandbox:file -> file:bytes'))

            nodes = await core.nodes('''[
                it:exec:proc=80e6c59d9c349ac15f716eaa825a23fa
                    :killedby=*
                    :exitcode=0
                    :exited=20210202
                    :sandbox:file=*
                    :name=RunDLL32
                    :path=c:/windows/system32/rundll32.exe
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], '80e6c59d9c349ac15f716eaa825a23fa')
            self.nn(nodes[0].get('killedby'))
            self.eq(nodes[0].get('exitcode'), 0)
            self.eq(nodes[0].get('exited'), 1612224000000000)
            self.eq(nodes[0].get('name'), 'RunDLL32')
            self.eq(nodes[0].get('path'), 'c:/windows/system32/rundll32.exe')
            self.len(1, await core.nodes('it:exec:proc:path.base=rundll32.exe'))
            self.len(1, await core.nodes('it:exec:proc=80e6c59d9c349ac15f716eaa825a23fa :killedby -> it:exec:proc'))
            self.len(1, await core.nodes('it:exec:proc=80e6c59d9c349ac15f716eaa825a23fa :sandbox:file -> file:bytes'))

            # FIXME host:activity interface?
            nodes = await core.nodes('''[
                it:av:scan:result=*
                    :time=20231117
                    :verdict=suspicious
                    :scanner={[ it:software=* :name="visi scan" ]}
                    :scanner:name="visi scan"
                    :categories=("Foo  Bar", "baz faz")
                    :signame=omgwtfbbq
                    :target={[ file:bytes=({"sha256": "80e6c59d9c349ac15f716eaa825a23fa80e6c59d9c349ac15f716eaa825a23fa"}) ]}
                    :multi:scan={[ it:av:scan:result=*
                        :scanner:name="visi total"
                        :multi:count=10
                        :multi:count:benign=3
                        :multi:count:unknown=1
                        :multi:count:suspicious=4
                        :multi:count:malicious=2
                    ]}
            ]''')
            self.eq(nodes[0].get('time'), 1700179200000000)
            self.eq(nodes[0].get('verdict'), 30)
            self.eq(nodes[0].get('scanner:name'), 'visi scan')
            self.eq(nodes[0].get('target'), ('file:bytes', '09d214b60cdc6378a45de889fbb084cc'))
            self.eq(nodes[0].get('signame'), 'omgwtfbbq')
            self.eq(nodes[0].get('categories'), ('baz faz', 'foo bar'))

            self.len(1, await core.nodes('it:av:scan:result:scanner:name="visi scan" -> meta:name'))
            self.len(1, await core.nodes('it:av:scan:result:scanner:name="visi scan" -> file:bytes'))
            self.len(1, await core.nodes('it:av:scan:result:scanner:name="visi scan" -> it:software'))
            self.len(1, await core.nodes('it:av:scan:result:scanner:name="visi scan" -> it:av:signame'))

            nodes = await core.nodes('it:av:scan:result:scanner:name="visi total"')
            self.len(1, nodes)

            self.eq(10, nodes[0].get('multi:count'))
            self.eq(3, nodes[0].get('multi:count:benign'))
            self.eq(1, nodes[0].get('multi:count:unknown'))
            self.eq(4, nodes[0].get('multi:count:suspicious'))
            self.eq(2, nodes[0].get('multi:count:malicious'))

            self.len(1, await core.nodes('it:av:scan:result:scanner:name="visi total" -> it:av:scan:result +:scanner:name="visi scan"'))

            q = '''
            [ it:network=(vertex, ops, lan)
                :desc="Vertex Project Operations LAN"
                :name="opslan.lax.vertex.link"
                :net="10.1.0.0/16"
                :org={ gen.ou.org "Vertex Project" }
                :type=virtual.sdn
                :dns:resolvers=(1.2.3.4, tcp://1.2.3.4:99)
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:network', s_common.guid(('vertex', 'ops', 'lan'))))
            self.eq(nodes[0].get('desc'), 'Vertex Project Operations LAN')
            self.eq(nodes[0].get('name'), 'opslan.lax.vertex.link')
            self.eq(nodes[0].get('net'), ((4, 167837696), (4, 167903231)))
            self.eq(nodes[0].get('type'), 'virtual.sdn.')
            self.eq(nodes[0].get('dns:resolvers'), ('udp://1.2.3.4:53', 'tcp://1.2.3.4:99'))

            nodes = await core.nodes('''[
                it:sec:stix:indicator=*
                    :id=zoinks
                    :name=woot
                    :confidence=90
                    :revoked=(false)
                    :desc="my neato indicator"
                    :pattern="some rule text"
                    :pattern_type=yara
                    :created=20240815
                    :updated=20240815
                    :labels=(hehe, haha)
                    :valid_from=20240815
                    :valid_until=20240815
            ]''')
            self.len(1, nodes)
            self.eq('zoinks', nodes[0].get('id'))
            self.eq('woot', nodes[0].get('name'))
            self.eq(90, nodes[0].get('confidence'))
            self.eq(False, nodes[0].get('revoked'))
            self.eq('my neato indicator', nodes[0].get('desc'))
            self.eq('some rule text', nodes[0].get('pattern'))
            self.eq('yara', nodes[0].get('pattern_type'))
            self.eq(('haha', 'hehe'), nodes[0].get('labels'))
            self.eq(1723680000000000, nodes[0].get('created'))
            self.eq(1723680000000000, nodes[0].get('updated'))
            self.eq(1723680000000000, nodes[0].get('valid_from'))
            self.eq(1723680000000000, nodes[0].get('valid_until'))

    async def test_infotech_android(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[it:os:android:perm="Foo Perm"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:os:android:perm', 'Foo Perm'))

            nodes = await core.nodes('[it:os:android:intent="Foo Intent"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:os:android:intent', 'Foo Intent'))

            softver = s_common.guid()
            valu = (softver, 'Listen Test')
            nodes = await core.nodes('[it:os:android:ilisten=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:os:android:ilisten', (softver, 'Listen Test')))
            self.eq(node.get('app'), softver)
            self.eq(node.get('intent'), 'Listen Test')

            valu = (softver, 'Broadcast Test')
            nodes = await core.nodes('[it:os:android:ibroadcast=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:os:android:ibroadcast', (softver, 'Broadcast Test')))
            self.eq(node.get('app'), softver)
            self.eq(node.get('intent'), 'Broadcast Test')

            valu = (softver, 'Test Perm')
            nodes = await core.nodes('[it:os:android:reqperm=$valu]', opts={'vars': {'valu': valu}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:os:android:reqperm', (softver, 'Test Perm')))
            self.eq(node.get('app'), softver)
            self.eq(node.get('perm'), 'Test Perm')

    async def test_it_forms_simple(self):
        async with self.getTestCore() as core:
            place = s_common.guid()
            nodes = await core.nodes('[it:hostname="Bobs Computer"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:hostname', 'bobs computer'))

            q = '''
            [ it:software:image=(ubuntu, 24.10, amd64, vhdx)
                :name="ubuntu-24.10-amd64.vhdx"
                :published=202405170940
                :publisher={[ entity:contact=(blackout,) :name=blackout ]}
                :creator={[ inet:service:account=* :user=visi ]}
                :parents={[ it:software:image=* :name=zoom ]}
            ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.len(1, nodes[0].get('parents'))
            self.eq(nodes[0].ndef, ('it:software:image', s_common.guid(('ubuntu', '24.10', 'amd64', 'vhdx'))))
            self.eq(nodes[0].get('name'), 'ubuntu-24.10-amd64.vhdx')
            self.eq(nodes[0].get('published'), 1715938800000000)
            self.eq(nodes[0].get('publisher'), s_common.guid(('blackout',)))

            nodes = await core.nodes('''
                [ it:host=*

                    :id=foo123
                    :name="Bobs laptop"
                    :desc="Bobs paperweight"

                    :ip=1.2.3.4
                    :place=*
                    :place:latlong=(0, 0)

                    :os=*
                    :image={ it:software:image | limit 1 }
                    :serial=111-222
                    :place:loc=us.hehe.haha
                    :operator={[ entity:contact=* ]}
                    :org=*

                    :phys:mass=10kg
                    :phys:width=5m
                    :phys:height=10m
                    :phys:length=20m
                    :phys:volume=1000m
                ]
            ''')
            self.len(1, nodes)

            self.eq(nodes[0].get('id'), 'foo123')
            self.eq(nodes[0].get('name'), 'bobs laptop')
            self.eq(nodes[0].get('desc'), 'Bobs paperweight')
            self.eq(nodes[0].get('ip'), (4, 0x01020304))
            self.eq(nodes[0].get('place:latlong'), (0.0, 0.0))
            self.eq(nodes[0].get('place:loc'), 'us.hehe.haha')
            self.eq(nodes[0].get('phys:mass'), '10000')
            self.eq(nodes[0].get('phys:width'), 5000)
            self.eq(nodes[0].get('phys:height'), 10000)
            self.eq(nodes[0].get('phys:length'), 20000)
            self.eq(nodes[0].get('phys:volume'), 1000000)

            self.len(1, await core.nodes('it:host :os -> it:software'))
            self.len(1, await core.nodes('it:host :org -> ou:org'))
            self.len(1, await core.nodes('it:host :place -> geo:place'))
            self.len(1, await core.nodes('it:host :operator -> entity:contact'))

            host = node

            nodes = await core.nodes(r'''
            [ it:storage:volume=(smb, 192.168.0.10, c$, temp)
                :name="\\\\192.168.0.10\\c$\\temp"
                :size=(10485760)
                :type=windows.smb.share
            ]
            ''')

            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:storage:volume', s_common.guid(('smb', '192.168.0.10', 'c$', 'temp'))))
            self.eq(nodes[0].get('name'), '\\\\192.168.0.10\\c$\\temp')
            self.eq(nodes[0].get('size'), s_const.mebibyte * 10)
            self.eq(nodes[0].get('type'), 'windows.smb.share.')
            volume = nodes[0]

            nodes = await core.nodes(r'''
                [ it:storage:mount=*
                    :host={ it:host | limit 1 }
                    :path="z:\\"
                    :volume={ it:storage:volume | limit 1 }
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('it:storage:mount :host -> it:host'))
            self.len(1, await core.nodes('it:storage:mount :path -> file:path'))
            self.len(1, await core.nodes('it:storage:mount :volume -> it:storage:volume'))

            nodes = await core.nodes('[it:dev:int=0x61c88648]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:int', 1640531528))

            nodes = await core.nodes('''[
                it:sec:cve=CVE-2013-9999
                    //:nist:nvd:source=NistSource
                    //:nist:nvd:published=2021-10-11
                    //:nist:nvd:modified=2021-10-11

                    //:cisa:kev:name=KevName
                    //:cisa:kev:desc=KevDesc
                    //:cisa:kev:action=KevAction
                    //:cisa:kev:vendor=KevVendor
                    //:cisa:kev:product=KevProduct
                    //:cisa:kev:added=2022-01-02
                    //:cisa:kev:duedate=2022-01-02
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:sec:cve', 'CVE-2013-9999'))
            # self.eq(node.get('nist:nvd:source'), 'nistsource')
            # self.eq(node.get('nist:nvd:published'), 1633910400000000)
            # self.eq(node.get('nist:nvd:modified'), 1633910400000000)
            # self.eq(node.get('cisa:kev:name'), 'KevName')
            # self.eq(node.get('cisa:kev:desc'), 'KevDesc')
            # self.eq(node.get('cisa:kev:action'), 'KevAction')
            # self.eq(node.get('cisa:kev:vendor'), 'kevvendor')
            # self.eq(node.get('cisa:kev:product'), 'kevproduct')
            # self.eq(node.get('cisa:kev:added'), 1641081600000000)
            # self.eq(node.get('cisa:kev:duedate'), 1641081600000000)

            nodes = await core.nodes('[it:sec:cve=$valu]', opts={'vars': {'valu': 'CVE\u20122013\u20131138'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:sec:cve', 'CVE-2013-1138'))

            nodes = await core.nodes('[it:sec:cve=$valu]', opts={'vars': {'valu': 'CVE\u20112013\u20140001'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:sec:cve', 'CVE-2013-0001'))

            nodes = await core.nodes('[ it:adid=visi ]')
            self.eq(('it:adid', 'visi'), nodes[0].ndef)

            nodes = await core.nodes('''
                init {
                    $org = $lib.guid()
                    $host = $lib.guid()
                    $acct = $lib.guid()
                }
                [
                    it:host:account=$acct
                        :host=$host
                        :user=visi
                        :contact={[ entity:contact=* :email=visi@vertex.link ]}
                        // FIXME
                        //:domain={[ it:domain=* :org=$org :name=vertex :desc="the vertex project domain" ]}

                    (it:host:login=*
                        :period=(20210314,202103140201)
                        :account=$acct
                        :host=$host
                        :creds={[ auth:passwd=cool ]}
                        :flow={[ inet:flow=(foo,) ]})
                ]
            ''')
            self.len(2, nodes)
            self.eq('visi', nodes[0].get('user'))
            self.nn(nodes[0].get('host'))
            # FIXME :domain
            # self.nn(nodes[0].get('domain'))
            self.nn(nodes[0].get('contact'))

            self.nn(nodes[1].get('host'))
            self.nn(nodes[1].get('account'))
            self.eq(nodes[1].get('period'), (1615680000000000, 1615687260000000, 7260000000))
            self.eq(nodes[1].get('creds'), (('auth:passwd', 'cool'),))

            # Sample SIDs from here:
            # https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/81d92bba-d22b-4a8c-908a-554ab29148ab
            sids = [
                'S-1-0-0', 'S-1-1-0', 'S-1-2-0', 'S-1-2-1', 'S-1-3', 'S-1-3-0',
                'S-1-3-1', 'S-1-3-2', 'S-1-3-3', 'S-1-3-4', 'S-1-5', 'S-1-5-1',
                'S-1-5-2', 'S-1-5-3', 'S-1-5-4', 'S-1-5-6', 'S-1-5-7', 'S-1-5-8',
                'S-1-5-9', 'S-1-5-10', 'S-1-5-11', 'S-1-5-12', 'S-1-5-13', 'S-1-5-14',
                'S-1-5-15', 'S-1-5-17', 'S-1-5-18', 'S-1-5-19', 'S-1-5-20',
                'S-1-5-21-0-0-0-496', 'S-1-5-21-0-0-0-497', 'S-1-5-32-544',
                'S-1-5-32-545', 'S-1-5-32-546', 'S-1-5-32-547', 'S-1-5-32-548',
                'S-1-5-32-549', 'S-1-5-32-550', 'S-1-5-32-551', 'S-1-5-32-552',
                'S-1-5-32-554', 'S-1-5-32-555', 'S-1-5-32-556', 'S-1-5-32-557',
                'S-1-5-32-558', 'S-1-5-32-559', 'S-1-5-32-560', 'S-1-5-32-561',
                'S-1-5-32-562', 'S-1-5-32-568', 'S-1-5-32-569', 'S-1-5-32-573',
                'S-1-5-32-574', 'S-1-5-32-575', 'S-1-5-32-576', 'S-1-5-32-577',
                'S-1-5-32-578', 'S-1-5-32-579', 'S-1-5-32-580', 'S-1-5-32-582',
                'S-1-5-33', 'S-1-5-64-10', 'S-1-5-64-14', 'S-1-5-64-21', 'S-1-5-65-1',
                'S-1-5-80', 'S-1-5-80-0', 'S-1-5-83-0', 'S-1-5-84-0-0-0-0-0',
                'S-1-5-90-0', 'S-1-5-113', 'S-1-5-114', 'S-1-5-1000', 'S-1-15-2-1',
                'S-1-16-0', 'S-1-16-4096', 'S-1-16-8192', 'S-1-16-8448', 'S-1-16-12288',
                'S-1-16-16384', 'S-1-16-20480', 'S-1-16-28672', 'S-1-18-1', 'S-1-18-2',
                'S-1-18-3', 'S-1-18-4', 'S-1-18-5', 'S-1-18-6',
            ]

            opts = {'vars': {'sids': sids}}
            nodes = await core.nodes('for $sid in $sids {[ it:host:account=* :windows:sid=$sid ]}', opts=opts)
            self.len(88, nodes)

            nodes = await core.nodes('inet:email=visi@vertex.link -> entity:contact -> it:host:account -> it:host:login -> it:host')
            self.len(1, nodes)
            self.eq('it:host', nodes[0].ndef[0])

            self.len(1, await core.nodes('inet:email=visi@vertex.link -> entity:contact -> it:host:account -> it:host:login -> inet:flow'))

            # FIXME :domain
            # nodes = await core.nodes('it:host:account -> it:domain')
            # self.len(1, nodes)
            # self.nn(nodes[0].get('org'))
            # self.eq('vertex', nodes[0].get('name'))
            # self.eq('the vertex project domain', nodes[0].get('desc'))

            nodes = await core.nodes('''[
                it:log:event=*
                    :mesg=foobar
                    :data=(foo, bar, baz)
                    :severity=debug

                    :host={it:host | limit 1}
                    :sandbox:file=*
                    :service:platform=*
                    :service:account=*
            ]''')
            self.len(1, nodes)
            self.eq(10, nodes[0].get('severity'))
            self.eq('foobar', nodes[0].get('mesg'))
            self.eq(('foo', 'bar', 'baz'), nodes[0].get('data'))
            # check that the host activity model was inherited
            self.nn(nodes[0].get('host'))
            self.len(1, await core.nodes('it:log:event :sandbox:file -> file:bytes'))
            self.len(1, await core.nodes('it:log:event :service:account -> inet:service:account'))
            self.len(1, await core.nodes('it:log:event :service:platform -> inet:service:platform'))

            nodes = await core.nodes('it:host | limit 1 | [ :keyboard:layout=qwerty :keyboard:language=$lib.gen.langByCode(en.us) ]')
            self.len(1, nodes)
            self.nn(nodes[0].get('keyboard:language'))
            self.len(1, await core.nodes('it:host:keyboard:layout=QWERTY'))
            self.len(1, await core.nodes('lang:language:code=en.us -> it:host'))

    async def test_it_software(self):
        # Test all prodsoft and prodsoft associated linked forms
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                it:software=*
                    :id="Foo "
                    :name="Balloon Maker"
                    :names=("clowns inc",)
                    :type=hehe.haha
                    :desc="Pennywise's patented balloon blower upper"
                    :url=https://vertex.link/products/balloonmaker
                    :version=V1.0.1-beta+exp.sha.5114f85
                    :released="2018-04-03 08:44:22"
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('id'), 'Foo')
            self.eq(node.get('name'), 'balloon maker')
            self.eq(node.get('desc'), "Pennywise's patented balloon blower upper")
            self.eq(node.get('url'), 'https://vertex.link/products/balloonmaker')
            self.eq(node.get('released'), 1522745062000000)
            # FIXME resiliant semver
            # self.eq(node.get('version'), 'V1.0.1-beta+exp.sha.5114f85')
            self.len(1, await core.nodes('it:software:name="balloon maker" -> it:software:type:taxonomy'))
            self.len(2, await core.nodes('meta:name="balloon maker" -> it:software -> meta:name'))

            self.len(1, nodes := await core.nodes('[ it:software=({"name": "clowns inc"}) ]'))
            self.eq(node.ndef, nodes[0].ndef)

            # Test 'vers' semver brute forcing
            testvectors = [
                ('1', 0x000010000000000),
                ('2.0A1', 0x000020000000000),
                ('2016-03-01', 0x007e00000300001),
                ('1.2.windows-RC1', 0x000010000200000),
                ('3.4', 0x000030000400000),
                ('1.3a2.dev12', 0x000010000000000),
                ('v2.4.0.0-1', 0x000020000400000),
                ('v2.4.1.0-0.3.rc1', 0x000020000400001),
                ('0.18rc2', 0),
                ('OpenSSL_1_0_2l', 0x000010000000000),
            ]

            for tv, te in testvectors:
                nodes = await core.nodes('[it:software=* :version=$valu]', opts={'vars': {'valu': tv}})
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.get('version'), te)

            # FIXME resiliant semver
            # nodes = await core.nodes('[it:software=* :version=$valu]', opts={'vars': {'valu': ''}})
            # self.len(1, nodes)
            # node = nodes[0]
            # self.eq(node.get('version'), '')
            # self.none(node.get('semver'))

            # with self.getLoggerStream('synapse.models.infotech',
            #                           'Unable to parse string as a semver') as stream:

            #     nodes = await core.nodes('[it:software=* :version=$valu]', opts={'vars': {'valu': 'alpha'}})
            #     self.len(1, nodes)
            #     node = nodes[0]
            #     self.eq(node.get('version'), 'alpha')
            #     #self.none(node.get('semver'))
            #     self.true(stream.is_set())

    async def test_it_form_callbacks(self):
        async with self.getTestCore() as core:
            # it:dev:str kicks out the :norm property on him when he is made
            nodes = await core.nodes('[it:dev:str="evil RAT"]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:str', 'evil RAT'))
            # FIXME make this type behavior rather than a callback
            # self.eq(node.get('norm'), 'evil rat')

    async def test_it_semvertype(self):
        async with self.getTestCore() as core:
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
                (0xFFFFFFFFFFFFFFF, (0xFFFFFFFFFFFFFFF, {'major': 0xFFFFF, 'minor': 0xFFFFF, 'patch': 0xFFFFF})),
                # Brute forced strings
                ('1', (1099511627776, {'major': 1, 'minor': 0, 'patch': 0})),
                ('1.2', (1099513724928, {'major': 1, 'minor': 2, 'patch': 0})),
                ('2.0A1', (2199023255552, {'major': 2, 'minor': 0, 'patch': 0})),
                ('0.18rc2', (0, {'major': 0, 'minor': 0, 'patch': 0})),
                ('0.0.00001', (1, {'major': 0, 'minor': 0, 'patch': 1})),
                ('2016-03-01', (2216615444742145, {'major': 2016, 'minor': 3, 'patch': 1})),
                ('v2.4.0.0-1', (2199027449856, {'major': 2, 'minor': 4, 'patch': 0})),
                ('1.3a2.dev12', (1099511627776, {'major': 1, 'minor': 0, 'patch': 0})),
                ('OpenSSL_1_0_2l', (1099511627776, {'major': 1, 'minor': 0, 'patch': 0})),
                ('1.2.windows-RC1', (1099513724928, {'major': 1, 'minor': 2, 'patch': 0})),
                ('v2.4.1.0-0.3.rc1', (2199027449857, {'major': 2, 'minor': 4, 'patch': 1})),
                ('1.2.3-alpha.foo..+001', (1099513724931, {'major': 1, 'minor': 2, 'patch': 3})),
                ('1.2.3-alpha.foo.001+001', (1099513724931, {'major': 1, 'minor': 2, 'patch': 3})),
                ('1.2.3-alpha+001.blahblahblah...', (1099513724931, {'major': 1, 'minor': 2, 'patch': 3})),
                ('1.2.3-alpha+001.blahblahblah.*iggy', (1099513724931, {'major': 1, 'minor': 2, 'patch': 3}))
            )

            for v, e in testvectors:
                ev, es = e
                valu, rdict = await t.norm(v)
                self.eq(valu, ev)

            testvectors_bad = (
                # invalid ints
                -1,
                0xFFFFFFFFFFFFFFFFFFFFFFFF + 1,
                # Just bad input
                '   ',
                ' alpha ',
            )
            for v in testvectors_bad:
                await self.asyncraises(s_exc.BadTypeValu, t.norm(v))

            testvectors_repr = (
                (0, '0.0.0'),
                (1, '0.0.1'),
                (0x000010000200003, '1.2.3'),
            )
            for v, e in testvectors_repr:
                self.eq(t.repr(v), e)

    async def test_it_forms_screenshot(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                it:exec:screenshot=*
                    :host=*
                    :image=*
                    :desc=WootWoot
                    :sandbox:file=*
            ]''')

            self.len(1, nodes)
            self.eq('it:exec:screenshot', nodes[0].ndef[0])
            self.eq('WootWoot', nodes[0].get('desc'))

            self.len(1, await core.nodes('it:exec:screenshot :host -> it:host'))
            self.len(1, await core.nodes('it:exec:screenshot :image -> file:bytes'))
            self.len(1, await core.nodes('it:exec:screenshot :sandbox:file -> file:bytes'))

    async def test_it_forms_hardware(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''[
                it:hardware=*
                    :manufacturer={ gen.ou.org dell }
                    :manufacturer:name=dell
                    :model=XPS13
                    :version=1.2.3
                    :type=pc.laptop
                    :desc=WootWoot
                    :released=20220202
                    :cpe=cpe:2.3:h:dell:xps13:*:*:*:*:*:*:*:*
                    :parts = (*, *)
            ]''')
            self.eq('WootWoot', nodes[0].get('desc'))
            self.eq('xps13', nodes[0].get('model'))
            self.eq(1099513724931, nodes[0].get('version'))
            self.eq('cpe:2.3:h:dell:xps13:*:*:*:*:*:*:*:*', nodes[0].get('cpe'))
            self.eq(1643760000000000, nodes[0].get('released'))
            self.len(1, await core.nodes('it:hardware :type -> it:hardware:type:taxonomy'))
            self.len(2, await core.nodes('it:hardware:model=XPS13 -> it:hardware'))
            self.eq('dell', nodes[0].get('manufacturer:name'))
            self.len(1, await core.nodes('it:hardware -> ou:org +:name=dell'))

            nodes = await core.nodes('''[
                it:host:component=*
                    :hardware={it:hardware:model=XPS13}
                    :serial=asdf1234
                    :host=*
            ]''')
            self.nn(nodes[0].get('host'))
            self.eq('asdf1234', nodes[0].get('serial'))
            self.len(1, await core.nodes('it:host:component -> it:host'))
            self.len(1, await core.nodes('it:host:component -> it:hardware +:model=XPS13'))

    async def test_it_forms_hostexec(self):
        # forms related to the host execution model
        async with self.getTestCore() as core:
            exe = s_common.guid()
            port = 80
            tick = s_common.now()
            host = s_common.guid()
            proc = s_common.guid()
            mutex = 'giggleXX_X0'
            pipe = 'pipe\\mynamedpipe'
            pid = 20
            key = 'HKEY_LOCAL_MACHINE\\Foo\\Bar'

            sandfile = s_common.guid()
            addr4 = f'tcp://1.2.3.4:{port}'
            addr6 = f'udp://[::1]:{port}'
            url = 'http://www.google.com/sekrit.html'
            raw_path = r'c:\Windows\System32\rar.exe'
            norm_path = r'c:/windows/system32/rar.exe'
            src_proc = s_common.guid()
            src_path = r'c:/temp/ping.exe'
            cmd0 = 'rar a -r yourfiles.rar *.txt'
            fpath = 'c:/temp/yourfiles.rar'
            fbyts = s_common.guid()
            pprops = {
                'exe': exe,
                'pid': pid,
                'cmd': cmd0,
                'host': host,
                'time': tick,
                'account': '*',
                'path': raw_path,
                'src:proc': src_proc,
                'sandbox:file': sandfile,
            }
            q = '''[(it:exec:proc=$valu :exe=$p.exe :pid=$p.pid :cmd=$p.cmd :host=$p.host :time=$p.time
                :account=$p.account :path=$p.path :src:proc=$p."src:proc"
                :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': proc, 'p': pprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:proc', proc))
            self.eq(node.get('exe'), exe)
            self.eq(node.get('pid'), pid)
            self.eq(node.get('cmd'), cmd0)
            self.eq(node.get('host'), host)
            self.eq(node.get('time'), tick)
            self.eq(node.get('path'), norm_path)
            self.eq(node.get('src:proc'), src_proc)
            self.eq(node.get('sandbox:file'), sandfile)
            self.nn(node.get('account'))
            self.len(1, await core.nodes('it:exec:proc -> it:host:account'))

            nodes = await core.nodes('it:cmd')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:cmd', 'rar a -r yourfiles.rar *.txt'))

            q = '''
            [ it:host=(VTX001, 192.168.0.10) :name=VTX001 :ip=192.168.0.10 ]
            $host = $node

            [( it:cmd:session=(202405170900, 202405171000, bash, $host)
                :host=$host
                :period=(202405170900, 202405171000)
                :host:account={ it:host:account | limit 1 }
            )]
            '''
            nodes = await core.nodes(q)
            self.len(2, nodes)
            hostguid = s_common.guid(('VTX001', '192.168.0.10'))
            self.eq(nodes[0].ndef, ('it:host', hostguid))
            self.eq(nodes[1].ndef, ('it:cmd:session', s_common.guid(('202405170900', '202405171000', 'bash', hostguid))))
            self.eq(nodes[1].get('host'), hostguid)
            self.eq(nodes[1].get('period'), (1715936400000000, 1715940000000000, 3600000000))
            self.nn(nodes[1].get('host:account'))

            cmdsess = nodes[1]

            q = '''
            [
                (it:cmd:history=(1715936400000001, $sessiden)
                    :cmd="ls -la"
                    :time=(1715936400000001)
                )

                (it:cmd:history=(1715936400000002, $sessiden)
                    :cmd="cd /"
                    :time=(1715936400000002)
                )

                (it:cmd:history=(1715936400000003, $sessiden)
                    :cmd="ls -laR"
                    :time=(1715936400000003)
                )

                :session=$sessiden
            ]
            '''
            opts = {'vars': {'sessiden': cmdsess.ndef[1]}}
            nodes = await core.nodes(q, opts=opts)
            self.len(3, nodes)
            self.eq(nodes[0].ndef, ('it:cmd:history', s_common.guid(('1715936400000001', cmdsess.ndef[1]))))
            self.eq(nodes[0].get('cmd'), 'ls -la')
            self.eq(nodes[0].get('time'), 1715936400000001)
            self.eq(nodes[0].get('session'), cmdsess.ndef[1])

            self.eq(nodes[1].ndef, ('it:cmd:history', s_common.guid(('1715936400000002', cmdsess.ndef[1]))))
            self.eq(nodes[1].get('cmd'), 'cd /')
            self.eq(nodes[1].get('time'), 1715936400000002)
            self.eq(nodes[1].get('session'), cmdsess.ndef[1])

            self.eq(nodes[2].ndef, ('it:cmd:history', s_common.guid(('1715936400000003', cmdsess.ndef[1]))))
            self.eq(nodes[2].get('cmd'), 'ls -laR')
            self.eq(nodes[2].get('time'), 1715936400000003)
            self.eq(nodes[2].get('session'), cmdsess.ndef[1])

            m0 = s_common.guid()
            mprops = {
                'exe': exe,
                'proc': proc,
                'name': mutex,
                'host': host,
                'time': tick,
                'sandbox:file': sandfile,
            }
            q = '''[(it:exec:mutex=$valu :exe=$p.exe :proc=$p.proc :name=$p.name :host=$p.host :time=$p.time
                    :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': m0, 'p': mprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:mutex', m0))
            self.eq(node.get('exe'), exe)
            self.eq(node.get('proc'), proc)
            self.eq(node.get('host'), host)
            self.eq(node.get('time'), tick)
            self.eq(node.get('name'), mutex)
            self.eq(node.get('sandbox:file'), sandfile)

            p0 = s_common.guid()
            pipeprops = {
                'exe': exe,
                'proc': proc,
                'name': pipe,
                'host': host,
                'time': tick,
                'sandbox:file': sandfile,
            }
            q = '''[(it:exec:pipe=$valu :exe=$p.exe :proc=$p.proc :name=$p.name :host=$p.host :time=$p.time
                    :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': p0, 'p': pipeprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:pipe', p0))
            self.eq(node.get('exe'), exe)
            self.eq(node.get('proc'), proc)
            self.eq(node.get('host'), host)
            self.eq(node.get('time'), tick)
            self.eq(node.get('name'), pipe)
            self.eq(node.get('sandbox:file'), sandfile)

            nodes = await core.nodes('''
                [ it:exec:fetch=*
                    :proc=*
                    :host={ it:host | limit 1 }
                    :url=https://vertex.link
                    :time=20250718

                    :browser=*

                    :page:pdf=*
                    :page:html=*
                    :page:image=*
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('url'), 'https://vertex.link')
            self.eq(nodes[0].get('time'), 1752796800000000)

            self.len(1, await core.nodes('it:exec:fetch :host -> it:host'))
            self.len(1, await core.nodes('it:exec:fetch :browser -> it:software'))
            self.len(1, await core.nodes('it:exec:fetch :page:pdf -> file:bytes'))
            self.len(1, await core.nodes('it:exec:fetch :page:html -> file:bytes'))
            self.len(1, await core.nodes('it:exec:fetch :page:image -> file:bytes'))

            b0 = s_common.guid()
            bprops = {
                'proc': proc,
                'host': host,
                'exe': exe,
                'time': tick,
                'server': addr4,
                'sandbox:file': sandfile,
            }
            q = '''[(it:exec:bind=$valu :exe=$p.exe :proc=$p.proc :host=$p.host :time=$p.time
                :server=$p.server :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': b0, 'p': bprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:bind', b0))
            self.eq(node.ndef[1], b0)
            self.eq(node.get('exe'), exe)
            self.eq(node.get('proc'), proc)
            self.eq(node.get('host'), host)
            self.eq(node.get('time'), tick)
            self.eq(node.get('server'), addr4)
            self.eq(node.get('sandbox:file'), sandfile)

            b1 = s_common.guid()
            bprops['server'] = addr6
            nodes = await core.nodes(q, opts={'vars': {'valu': b1, 'p': bprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:bind', b1))
            self.eq(node.get('server'), addr6)

            faprops = {
                'exe': exe,
                'host': host,
                'proc': proc,
                'file': fbyts,
                'time': tick,
                'path': fpath,
                'sandbox:file': sandfile,
            }
            fa0 = s_common.guid()
            q = '''[(it:exec:file:add=$valu :exe=$p.exe :proc=$p.proc :host=$p.host :time=$p.time
                :file=$p.file :path=$p.path
                :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': fa0, 'p': faprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:file:add', fa0))
            self.eq(node.get('exe'), exe)
            self.eq(node.get('host'), host)
            self.eq(node.get('proc'), proc)
            self.eq(node.get('time'), tick)
            self.eq(node.get('file'), fbyts)
            self.eq(node.get('path'), fpath)
            self.len(1, await core.nodes('it:exec:file:add:path.dir=c:/temp'))
            self.len(1, await core.nodes('it:exec:file:add:path.base=yourfiles.rar'))
            self.len(1, await core.nodes('it:exec:file:add:path.ext=rar'))
            self.eq(node.get('sandbox:file'), sandfile)

            fr0 = s_common.guid()
            q = '''[(it:exec:file:read=$valu :exe=$p.exe :proc=$p.proc :host=$p.host :time=$p.time
                            :file=$p.file :path=$p.path
                            :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': fr0, 'p': faprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:file:read', fr0))
            self.eq(node.get('exe'), exe)
            self.eq(node.get('host'), host)
            self.eq(node.get('proc'), proc)
            self.eq(node.get('time'), tick)
            self.eq(node.get('file'), fbyts)
            self.eq(node.get('path'), fpath)
            self.len(1, await core.nodes('it:exec:file:read:path.dir=c:/temp'))
            self.len(1, await core.nodes('it:exec:file:read:path.base=yourfiles.rar'))
            self.len(1, await core.nodes('it:exec:file:read:path.ext=rar'))
            self.eq(node.get('sandbox:file'), sandfile)

            fw0 = s_common.guid()
            q = '''[(it:exec:file:write=$valu :exe=$p.exe :proc=$p.proc :host=$p.host :time=$p.time
                    :file=$p.file :path=$p.path
                    :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': fw0, 'p': faprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:file:write', fw0))
            self.eq(node.get('exe'), exe)
            self.eq(node.get('host'), host)
            self.eq(node.get('proc'), proc)
            self.eq(node.get('time'), tick)
            self.eq(node.get('file'), fbyts)
            self.eq(node.get('path'), fpath)
            self.len(1, await core.nodes('it:exec:file:write:path.dir=c:/temp'))
            self.len(1, await core.nodes('it:exec:file:write:path.base=yourfiles.rar'))
            self.len(1, await core.nodes('it:exec:file:write:path.ext=rar'))
            self.eq(node.get('sandbox:file'), sandfile)

            fd0 = s_common.guid()
            q = '''[(it:exec:file:del=$valu :exe=$p.exe :proc=$p.proc :host=$p.host :time=$p.time
                                :file=$p.file :path=$p.path
                                :sandbox:file=$p."sandbox:file")]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': fd0, 'p': faprops}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:exec:file:del', fd0))
            self.eq(node.get('exe'), exe)
            self.eq(node.get('host'), host)
            self.eq(node.get('proc'), proc)
            self.eq(node.get('time'), tick)
            self.eq(node.get('file'), fbyts)
            self.eq(node.get('path'), fpath)
            self.len(1, await core.nodes('it:exec:file:del:path.dir=c:/temp'))
            self.len(1, await core.nodes('it:exec:file:del:path.base=yourfiles.rar'))
            self.len(1, await core.nodes('it:exec:file:del:path.ext=rar'))
            self.eq(node.get('sandbox:file'), sandfile)

            file0 = s_common.guid()
            fsprops = {
                'host': host,
                'path': fpath,
                'file': fbyts,
                'ctime': tick,
                'mtime': tick + 1,
                'atime': tick + 2,
                'group': 'domainadmin'
            }
            nodes = await core.nodes('''[
                it:host:filepath=*
                    :host={ it:host | limit 1 }
                    :path=c:/temp/yourfiles.rar
                    :file=*
                    :group={[ it:host:group=({"name": "domainadmin"}) ]}
                    :created=20200202
                    :modified=20200203
                    :accessed=20200204
            ]''')
            self.len(1, nodes)
            node = nodes[0]
            self.nn(node.get('host'))
            self.nn(node.get('file'))
            self.nn(node.get('group'))

            self.eq(node.get('created'), 1580601600000000)
            self.eq(node.get('modified'), 1580688000000000)
            self.eq(node.get('accessed'), 1580774400000000)
            self.eq(node.get('path'), 'c:/temp/yourfiles.rar')

            self.len(1, await core.nodes('it:host:filepath:path.dir=c:/temp'))
            self.len(1, await core.nodes('it:host:filepath:path.base=yourfiles.rar'))
            self.len(1, await core.nodes('it:host:filepath:path.ext=rar'))

            rprops = {
                'host': host,
                'proc': proc,
                'exe': exe,
                'time': tick,
                'reg': '*',
                'sandbox:file': sandfile,
            }
            forms = ('it:exec:windows:registry:get',
                     'it:exec:windows:registry:set',
                     'it:exec:windows:registry:del',
                     )
            for form in forms:
                rk0 = s_common.guid()
                nprops = rprops.copy()
                q = '''[(*$form=$valu :host=$p.host :proc=$p.proc :exe=$p.exe :time=$p.time :entry=$p.reg
                    :sandbox:file=$p."sandbox:file")]'''
                nodes = await core.nodes(q, opts={'vars': {'form': form, 'valu': rk0, 'p': nprops}})
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.ndef, (form, rk0))
                self.eq(node.get('host'), host)
                self.eq(node.get('proc'), proc)
                self.eq(node.get('exe'), exe)
                self.eq(node.get('time'), tick)
                self.nn(node.get('entry'))
                self.eq(node.get('sandbox:file'), sandfile)

        async with self.getTestCore() as core:
            forms = [
                'it:host:filepath',
                'it:exec:file:add',
                'it:exec:file:del',
                'it:exec:file:read',
                'it:exec:file:write',
            ]

            for form in forms:
                opts = {'vars': {'form': form, 'prop': f'{form}:path'}}
                nodes = await core.nodes('[ *$form=($form, calc) :path="c:/windows/system32/calc.exe" ]', opts=opts)
                self.len(1, nodes)
                self.eq(nodes[0].get('path'), 'c:/windows/system32/calc.exe')
                self.len(1, await core.nodes(f'*($prop).dir=c:/windows/system32', opts=opts))
                self.len(1, await core.nodes(f'*($prop).base=calc.exe', opts=opts))
                self.len(1, await core.nodes(f'*($prop).ext=exe', opts=opts))

                nodes = await core.nodes('*$form=($form, calc) [ :path="c:/users/blackout/script.ps1" ]', opts=opts)
                self.len(1, nodes)
                self.eq(nodes[0].get('path'), 'c:/users/blackout/script.ps1')
                self.len(1, await core.nodes(f'*($prop).dir=c:/users/blackout', opts=opts))
                self.len(1, await core.nodes(f'*($prop).base=script.ps1', opts=opts))
                self.len(1, await core.nodes(f'*($prop).ext=ps1', opts=opts))

                nodes = await core.nodes('*$form=($form, calc) [ :path="c:/users/admin/superscript.bat" ]', opts=opts)
                self.len(1, nodes)
                self.eq(nodes[0].get('path'), 'c:/users/admin/superscript.bat')
                self.len(1, await core.nodes(f'*($prop).dir=c:/users/admin', opts=opts))
                self.len(1, await core.nodes(f'*($prop).base=superscript.bat', opts=opts))
                self.len(1, await core.nodes(f'*($prop).ext=bat', opts=opts))

    async def test_it_app_yara(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ it:app:yara:rule=*
                    :id=V-31337
                    :url=https://vertex.link/yara-lolz/V-31337
                    :created=20200202 :updated=20220401
                    :enabled=true :text=gronk
                    :author={[ entity:contact=* ]}
                    :name=foo :version=1.2.3 ]
            ''')

            self.len(1, nodes)
            self.eq('foo', nodes[0].get('name'))
            self.eq('V-31337', nodes[0].get('id'))
            self.eq('https://vertex.link/yara-lolz/V-31337', nodes[0].get('url'))
            self.eq(True, nodes[0].get('enabled'))
            self.eq(1580601600000000, nodes[0].get('created'))
            self.eq(1648771200000000, nodes[0].get('updated'))
            self.eq('gronk', nodes[0].get('text'))
            self.eq(0x10000200003, nodes[0].get('version'))

            self.len(1, await core.nodes('it:app:yara:rule -> entity:contact'))

            nodes = await core.nodes('''
                $file = {[ file:bytes=* ]}
                $rule = { it:app:yara:rule:id=V-31337 }
                [ it:app:yara:match=({"rule": $rule, "target": ["file:bytes", $file]})
                    :version=1.2.3
                    :matched=20200202
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('rule'))
            self.nn(nodes[0].get('target'))
            self.eq(nodes[0].get('version'), 0x10000200003)
            self.eq(nodes[0].get('matched'), 1580601600000000)

    async def test_it_app_snort(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
            [ it:app:snort:rule=*
                :id=999
                :engine=1
                :text=gronk
                :name=foo
                :author = {[ entity:contact=* :name=visi ]}
                :created = 20120101
                :updated = 20220101
                :enabled=1
                :version=1.2.3 ]
            ''')

            self.len(1, nodes)
            self.eq(nodes[0].get('id'), '999')
            self.eq(nodes[0].get('engine'), 1)
            self.eq(nodes[0].get('name'), 'foo')
            self.eq(nodes[0].get('text'), 'gronk')
            self.eq(nodes[0].get('enabled'), True)
            self.eq(nodes[0].get('version'), 0x10000200003)
            self.eq(nodes[0].get('created'), 1325376000000000)
            self.eq(nodes[0].get('updated'), 1640995200000000)
            self.nn(nodes[0].get('author'))

            rule = nodes[0].ndef[1]

            nodes = await core.nodes('''[
                it:app:snort:match=*
                    :rule={[ it:app:snort:rule=({"id": 999}) ]}
                    :matched=2015
                    :target={[ inet:flow=* ]}
                    :sensor={[ it:host=* ]}
                    :version=1.2.3
                    :dropped=true
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('target'))
            self.nn(nodes[0].get('sensor'))
            self.true(nodes[0].get('dropped'))
            self.eq(nodes[0].get('rule'), rule)
            self.eq(nodes[0].get('version'), 0x10000200003)
            self.eq(nodes[0].get('matched'), 1420070400000000)

    async def test_it_function(self):

        async with self.getTestCore() as core:

            fileiden = s_common.guid()

            q = '''[
                it:dev:function=*
                    :id=ZIP10
                    :name=woot_woot
                    :desc="Woot woot"
                    :strings=(foo, bar, foo)
                    :impcalls=(foo, bar, foo)
            ]'''

            opts = {'vars': {'file': fileiden}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('id'), 'ZIP10')
            self.eq(nodes[0].get('name'), 'woot_woot')
            self.eq(nodes[0].get('desc'), 'Woot woot')
            self.eq(nodes[0].get('strings'), ('bar', 'foo'))
            self.eq(nodes[0].get('impcalls'), ('bar', 'foo'))
            self.len(1, await core.nodes('it:dev:function :name -> it:dev:str'))
            self.len(2, await core.nodes('it:dev:function :strings -> it:dev:str'))
            self.len(2, await core.nodes('it:dev:function :impcalls -> it:dev:str'))

            q = '''[
                it:dev:function:sample=*
                    :file=*
                    :function={ it:dev:function }
                    :va=0x404438
                    :calls=(*, *)
            ]'''
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].get('va'), 0x404438)
            self.len(1, await core.nodes('it:dev:function:sample:va=0x404438 -> file:bytes'))
            self.len(1, await core.nodes('it:dev:function:sample:va=0x404438 -> it:dev:function'))
            self.len(2, await core.nodes('it:dev:function:sample:va=0x404438 :calls -> it:dev:function:sample'))

    async def test_infotech_cpes(self):

        async with self.getTestCore() as core:
            self.eq(r'foo:bar', (await core.model.type('it:sec:cpe').norm(r'cpe:2.3:a:foo\:bar:*:*:*:*:*:*:*:*:*'))[1]['subs']['vendor'][1])

            with self.raises(s_exc.BadTypeValu):
                nodes = await core.nodes('[it:sec:cpe=asdf]')

            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('[ it:sec:cpe="cpe:2.3:a:vendor001:product-foo" :v2_2="cpe:/a:vendor:product\\foo" ]')

            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('[ it:sec:cpe="cpe:/a:vend🙃:prod:vers" ]')

            with self.raises(s_exc.BadTypeValu):
                nodes = await core.nodes('[it:sec:cpe=cpe:2.3:1:2:3:4:5:6:7:8:9:10:11:12]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ it:sec:cpe=cpe:2.3:a:vertex:synapse ]')

            with self.raises(s_exc.BadTypeValu):
                await core.callStorm(r'$lib.cast(it:sec:cpe, "cpe:2.3:a:openbsd:openssh:7.4\r\n:*:*:*:*:*:*:*")')

            with self.raises(s_exc.BadTypeValu):
                await core.callStorm(r'$lib.cast(it:sec:cpe:v2_2, "cpe:/a:01generator:pireospay\r\n:-::~~~prestashop~~")')

            with self.raises(s_exc.BadTypeValu):
                await core.callStorm('$lib.cast(it:sec:cpe:v2_2, "cpe:2.3:*")')

            nodes = await core.nodes('''[
                it:sec:cpe=cpe:2.3:a:microsoft:internet_explorer:8.0.6001:beta:*:*:*:*:*:*
            ]''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:sec:cpe', 'cpe:2.3:a:microsoft:internet_explorer:8.0.6001:beta:*:*:*:*:*:*'))
            self.eq(nodes[0].get('part'), 'a')
            self.eq(nodes[0].get('vendor'), 'microsoft')
            self.eq(nodes[0].get('product'), 'internet_explorer')
            self.eq(nodes[0].get('version'), '8.0.6001')
            self.eq(nodes[0].get('update'), 'beta')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes("[ it:sec:cpe='cpe:2.3:a:openbsd:openssh:7.4\r\n:*:*:*:*:*:*:*' ]")

            nodes = await core.nodes(r'[ it:sec:cpe="cpe:2.3:o:cisco:ios:12.1\\(22\\)ea1a:*:*:*:*:*:*:*" ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:sec:cpe', r'cpe:2.3:o:cisco:ios:12.1\(22\)ea1a:*:*:*:*:*:*:*'))
            self.eq(nodes[0].get('part'), 'o')
            self.eq(nodes[0].get('product'), 'ios')
            self.eq(nodes[0].get('vendor'), 'cisco')
            self.eq(nodes[0].get('version'), '12.1(22)ea1a')
            self.eq(nodes[0].get('v2_2'), 'cpe:/o:cisco:ios:12.1%2822%29ea1a')

            cpe23 = core.model.type('it:sec:cpe')
            cpe22 = core.model.type('it:sec:cpe:v2_2')

            with self.raises(s_exc.BadTypeValu):
                await cpe22.norm('cpe:/a:vertex:synapse:0:1:2:3:4:5:6:7:8:9')

            with self.raises(s_exc.BadTypeValu):
                await cpe23.norm('cpe:/a:vertex:synapse:0:1:2:3:4:5:6:7:8:9')

            # test cast 2.2 -> 2.3 upsample
            norm, info = await cpe23.norm('cpe:/a:vertex:synapse')
            self.eq(norm, 'cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:*')

            # test cast 2.3 -> 2.2 downsample
            norm, info = await cpe22.norm('cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:*')
            self.eq(norm, 'cpe:/a:vertex:synapse')

            nodes = await core.nodes('[ it:sec:cpe=cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:* ]')
            self.eq('cpe:/a:vertex:synapse', nodes[0].get('v2_2'))

            # test lift by either via upsample and downsample
            self.len(1, await core.nodes('it:sec:cpe=cpe:/a:vertex:synapse +:v2_2=cpe:/a:vertex:synapse'))
            self.len(1, await core.nodes('it:sec:cpe=cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:*'))
            self.len(1, await core.nodes('it:sec:cpe:v2_2=cpe:/a:vertex:synapse'))
            self.len(1, await core.nodes('it:sec:cpe:v2_2=cpe:2.3:a:vertex:synapse:*:*:*:*:*:*:*:*'))

            # Test cpe22 -> cpe23 escaping logic
            norm, info = await cpe23.norm('cpe:/a:%21')
            self.eq(norm, 'cpe:2.3:a:\\!:*:*:*:*:*:*:*:*:*')

            norm, info = await cpe23.norm('cpe:/a:%5c%21')
            self.eq(norm, 'cpe:2.3:a:\\!:*:*:*:*:*:*:*:*:*')

            norm, info = await cpe23.norm('cpe:/a:%5cb')
            self.eq(norm, 'cpe:2.3:a:\\\\b:*:*:*:*:*:*:*:*:*')

            norm, info = await cpe23.norm('cpe:/a:b%5c')
            self.eq(norm, 'cpe:2.3:a:b\\\\:*:*:*:*:*:*:*:*:*')

            norm, info = await cpe23.norm('cpe:/a:b%5c%5c')
            self.eq(norm, 'cpe:2.3:a:b\\\\:*:*:*:*:*:*:*:*:*')

            norm, info = await cpe23.norm('cpe:/a:b%5c%5cb')
            self.eq(norm, 'cpe:2.3:a:b\\\\b:*:*:*:*:*:*:*:*:*')

            # Examples based on customer reports
            q = r'''
            [
                it:sec:cpe="cpe:/a:10web:social_feed_for_instagram:1.0.0::~~premium~wordpress~~"
                it:sec:cpe="cpe:/a:1c:1c%3aenterprise:-"
                it:sec:cpe="cpe:/a:acurax:under_construction_%2f_maintenance_mode:-::~~~wordpress~~"
                it:sec:cpe="cpe:/o:zyxel:nas326_firmware:5.21%28aazf.14%29c0"
            ]
            '''
            msgs = await core.stormlist(q)
            self.stormHasNoWarnErr(msgs)

            # Examples based on customer reports
            q = r'''
            [
                it:sec:cpe="cpe:2.3:a:x1c:1c\\:enterprise:-:*:*:*:*:*:*:*"
                it:sec:cpe="cpe:2.3:a:xacurax:under_construction_\\/_maintenance_mode:-:*:*:*:*:wordpress:*:*"
                it:sec:cpe="cpe:2.3:o:xzyxel:nas326_firmware:5.21\\(aazf.14\\)c0:*:*:*:*:*:*:*"
                it:sec:cpe="cpe:2.3:a:vendor:product\\%45:version:update:edition:lng:sw_edition:target_sw:target_hw:other"
                it:sec:cpe="cpe:2.3:a:vendor2:product\\%23:version:update:edition:lng:sw_edition:target_sw:target_hw:other"
            ]
            '''
            msgs = await core.stormlist(q)
            self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes('it:sec:cpe:vendor=vendor')
            self.len(1, nodes)
            self.eq(nodes[0].get('product'), 'product%45')

            nodes = await core.nodes('it:sec:cpe:vendor=vendor2')
            self.len(1, nodes)
            self.eq(nodes[0].get('product'), 'product%23')

    async def test_infotech_cpe_conversions(self):
        self.thisEnvMust('CIRCLECI')

        async with self.getTestCore() as core:
            cpe23 = core.model.type('it:sec:cpe')
            cpe22 = core.model.type('it:sec:cpe:v2_2')
            # Test 2.2->2.3 and 2.3->2.2 conversions
            filename = s_t_files.getAssetPath('cpedata.json')
            with open(filename, 'r') as fp:
                cpedata = s_json.load(fp)

            for (_cpe22, _cpe23) in cpedata:
                # Convert cpe22 -> cpe23
                norm_22, _ = await cpe23.norm(_cpe22)
                self.eq(norm_22, _cpe23)

                norm_23, info_23 = await cpe23.norm(_cpe23)
                self.eq(norm_23, _cpe23)

                # No escaped characters in the secondary props
                for name, valu in info_23.items():
                    if name == 'v2_2':
                        continue

                    self.notin('\\', valu)

                # Norm cpe23 and check the cpe22 conversion
                sub_23_v2_2 = info_23['subs']['v2_2'][1]

                norm_sub_23_v2_2, _ = await cpe22.norm(sub_23_v2_2)
                self.eq(norm_sub_23_v2_2, sub_23_v2_2)

    async def test_cpe_scrape_one_to_one(self):

        async with self.getTestCore() as core:
            q = '[it:sec:cpe=$valu]'
            for _, valu in s_scrape.scrape(s_t_scrape.cpedata, ptype='it:sec:cpe'):
                nodes = await core.nodes(q, opts={'vars': {'valu': valu}})
                self.len(1, nodes)
                node = nodes[0]
                self.eq(node.ndef[1], valu.lower(), msg=valu.lower())

    async def test_infotech_c2config(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ it:sec:c2:config=*
                    :file=*
                    :family=Beacon
                    :servers=(http://1.2.3.4, tcp://visi:secret@vertex.link)
                    :decoys=(https://woot.com, https://foo.bar)
                    :listens=(https://0.0.0.0:443,)
                    :proxies=(socks5://visi:secret@1.2.3.4:1234,)
                    :dns:resolvers=(udp://8.8.8.8:53,)
                    :http:headers=(
                        (user-agent, wootbot),
                    )
                    :mutex=OnlyOnce
                    :crypto:key={[ crypto:key:secret=* ]}
                    :campaigncode=WootWoot
                    :raw = ({"hehe": "haha"})
                    :connect:delay=01:00:00
                    :connect:interval=08:00:00
                ]
            ''')
            node = nodes[0]
            self.nn(node.get('file'))
            self.nn(node.get('crypto:key'))
            self.eq('OnlyOnce', node.get('mutex'))
            self.eq('beacon', node.get('family'))
            self.eq('WootWoot', node.get('campaigncode'))
            self.eq(('http://1.2.3.4', 'tcp://visi:secret@vertex.link'), node.get('servers'))
            self.eq(3600000000, node.get('connect:delay'))
            self.eq(28800000000, node.get('connect:interval'))
            self.eq({'hehe': 'haha'}, node.get('raw'))
            self.eq(('https://0.0.0.0:443',), node.get('listens'))
            self.eq(('socks5://visi:secret@1.2.3.4:1234',), node.get('proxies'))
            self.eq(('udp://8.8.8.8:53',), node.get('dns:resolvers'))
            self.eq(('https://woot.com', 'https://foo.bar',), node.get('decoys'))

    async def test_infotech_query(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'root': core.auth.rootuser.iden}}
            nodes = await core.nodes('''
                [ it:exec:query=*
                    :text="SELECT * FROM threats"
                    :language="SQL"
                    :opts=({"foo": "bar"})
                    :api:url=https://vertex.link/api/v1.
                    :time=20220720
                    :offset=99
                    :synuser=$root
                    // we can assume the rest of the interface props work
                    :service:platform = *
                    :service:account = *
                ]
            ''', opts=opts)
            self.eq(1658275200000000, nodes[0].get('time'))
            self.eq(99, nodes[0].get('offset'))
            self.eq('sql', nodes[0].get('language'))
            self.eq({"foo": "bar"}, nodes[0].get('opts'))
            self.eq('SELECT * FROM threats', nodes[0].get('text'))
            self.eq(core.auth.rootuser.iden, nodes[0].get('synuser'))
            self.len(1, await core.nodes('it:exec:query -> it:query +it:query="SELECT * FROM threats"'))

            self.len(1, await core.nodes('it:exec:query :service:account -> inet:service:account'))
            self.len(1, await core.nodes('it:exec:query :service:platform -> inet:service:platform'))

    async def test_infotech_softid(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ it:softid=*
                    :id=Woot
                    :host=*
                    :software={[ it:software=* :name=beacon ]}
                    :software:name=beacon
                ]
            ''')
            self.len(1, nodes)
            self.eq('Woot', nodes[0].get('id'))
            self.nn(nodes[0].get('host'))
            self.nn(nodes[0].get('software'))
            self.len(1, await core.nodes('it:host -> it:softid'))
            self.len(1, await core.nodes('it:software:name=beacon -> it:softid'))

    async def test_infotech_repo(self):

        async with self.getTestCore() as core:
            diff = s_common.guid()
            repo = s_common.guid()
            issue = s_common.guid()
            commit = s_common.guid()
            branch = s_common.guid()
            icom = s_common.guid()
            dcom = s_common.guid()
            origin = s_common.guid()
            label = s_common.guid()
            issuelabel = s_common.guid()
            submod = s_common.guid()
            remote = s_common.guid()
            parent = s_common.guid()
            replyto = s_common.guid()
            file = s_common.guid()

            props = {
                'name': 'synapse',
                'desc': 'Synapse Central Intelligence System',
                'url': 'https://github.com/vertexproject/synapse',
                'type': 'svn.',
                'submodules': (submod,),
            }
            q = '''[(it:dev:repo=$valu :name=$p.name :desc=$p.desc :url=$p.url :type=$p.type
                :submodules=$p.submodules )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': repo, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo', repo))
            self.eq(node.get('name'), 'synapse')
            self.eq(node.get('desc'), 'Synapse Central Intelligence System')
            self.eq(node.get('url'), 'https://github.com/vertexproject/synapse')
            self.eq(node.get('type'), 'svn.')
            self.eq(node.get('submodules'), (submod,))

            props = {
                'name': 'origin',
                'repo': repo,
                'url': 'git://git.kernel.org/pub/scm/linux/kernel/git/gregkh/staging',
                'remote': origin,
            }
            q = '''[(it:dev:repo:remote=$valu :name=$p.name :repo=$p.repo :url=$p.url :remote=$p.remote)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': remote, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:remote', remote))
            self.eq(node.get('name'), 'origin')
            self.eq(node.get('repo'), repo),
            self.eq(node.get('url'), 'git://git.kernel.org/pub/scm/linux/kernel/git/gregkh/staging')
            self.eq(node.get('remote'), origin)

            props = {
                'repo': repo,
                'branch': branch,
                'parents': (parent,),
                'mesg': 'a fancy new release',
                'id': 'r12345',
                'url': 'https://github.com/vertexproject/synapse/commit/03c71e723bceedb38ef8fc14543c30b9e82e64cf',
            }
            q = '''[(it:dev:repo:commit=$valu :repo=$p.repo :branch=$p.branch :parents=$p.parents :mesg=$p.mesg
                :id=$p.id :url=$p.url)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': commit, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:commit', commit))
            self.eq(node.get('repo'), repo)
            self.eq(node.get('branch'), branch)
            self.eq(node.get('parents'), (parent,))
            self.eq(node.get('mesg'), 'a fancy new release')
            self.eq(node.get('id'), 'r12345')
            self.eq(node.get('url'),
                    'https://github.com/vertexproject/synapse/commit/03c71e723bceedb38ef8fc14543c30b9e82e64cf')

            nodes = await core.nodes('''
                [ it:dev:repo:entry=*
                    :repo={it:dev:repo | limit 1}
                    :file=*
                    :path=foo/bar/baz.exe
                    <(has)+ { it:dev:repo:commit | limit 1 }
                ]
            ''')
            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('repo'))
            self.eq(nodes[0].get('path'), 'foo/bar/baz.exe')

            self.len(1, await core.nodes('it:dev:repo:entry <(has)- it:dev:repo:commit'))

            props = {
                'commit': commit,
                'file': file,
                'path': 'synapse/tets/test_model_infotech.py',
                'url': 'https://github.com/vertexproject/synapse/compare/it_dev_repo_models?expand=1',
            }
            q = '''[(it:dev:repo:diff=$valu :commit=$p.commit :file=$p.file :path=$p.path :url=$p.url)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': diff, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:diff', diff))
            self.eq(node.get('commit'), commit)
            self.eq(node.get('file'), file)
            self.eq(node.get('path'), 'synapse/tets/test_model_infotech.py')
            self.eq(node.get('url'), 'https://github.com/vertexproject/synapse/compare/it_dev_repo_models?expand=1')

            props = {
                'repo': repo,
                'title': 'a fancy new release',
                'desc': 'Gonna be a big release friday',
                'updated': 1,
                'id': '1234',
                'url': 'https://github.com/vertexproject/synapse/issues/2821',
            }
            q = '''[(it:dev:repo:issue=$valu :repo=$p.repo :title=$p.title :desc=$p.desc
                :updated=$p.updated :id=$p.id :url=$p.url)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': issue, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:issue', issue))
            self.eq(node.get('repo'), repo)
            self.eq(node.get('title'), 'a fancy new release')
            self.eq(node.get('desc'), 'Gonna be a big release friday')
            self.eq(node.get('updated'), 1)
            self.eq(node.get('id'), '1234')
            self.eq(node.get('url'), 'https://github.com/vertexproject/synapse/issues/2821')

            props = {
                'id': '123456789',
                'title': 'new feature',
                'desc': 'a super cool new feature'
            }
            q = '[(it:dev:repo:label=$valu :id=$p.id :title=$p.title :desc=$p.desc)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': label, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:label', label))
            self.eq(node.get('id'), '123456789')
            self.eq(node.get('title'), 'new feature')
            self.eq(node.get('desc'), 'a super cool new feature')

            props = {
                'issue': issue,
                'label': label,
            }
            q = '[(it:dev:repo:issue:label=$valu :issue=$p.issue :label=$p.label)]'
            nodes = await core.nodes(q, opts={'vars': {'valu': issuelabel, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:issue:label', issuelabel))
            self.eq(node.get('label'), label)
            self.eq(node.get('issue'), issue)

            props = {
                'issue': issue,
                'text': 'a comment on an issue',
                'replyto': replyto,
                'url': 'https://github.com/vertexproject/synapse/issues/2821#issuecomment-1557053758',
                'updated': 93
            }
            q = '''[(it:dev:repo:issue:comment=$valu :issue=$p.issue :text=$p.text :replyto=$p.replyto
                :url=$p.url :updated=$p.updated)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': icom, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:issue:comment', icom))
            self.eq(node.get('issue'), issue)
            self.eq(node.get('text'), 'a comment on an issue')
            self.eq(node.get('replyto'), replyto)
            self.eq(node.get('url'), 'https://github.com/vertexproject/synapse/issues/2821#issuecomment-1557053758')
            self.eq(node.get('updated'), 93)

            props = {
                'diff': diff,
                'text': 'types types types types types',
                'replyto': replyto,
                'line': 100,
                'offset': 100,
                'url': 'https://github.com/vertexproject/synapse/pull/3257#discussion_r1273368069',
                'updated': 3
            }
            q = '''[(it:dev:repo:diff:comment=$valu :diff=$p.diff :text=$p.text :replyto=$p.replyto
                :line=$p.line :offset=$p.offset :url=$p.url :updated=$p.updated)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': dcom, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:diff:comment', dcom))
            self.eq(node.get('diff'), diff)
            self.eq(node.get('text'), 'types types types types types')
            self.eq(node.get('replyto'), replyto)
            self.eq(node.get('line'), 100)
            self.eq(node.get('offset'), 100)
            self.eq(node.get('url'), 'https://github.com/vertexproject/synapse/pull/3257#discussion_r1273368069')
            self.eq(node.get('updated'), 3)

            props = {
                'parent': parent,
                'start': commit,
                'name': 'IT_dev_repo_models',
                'url': 'https://github.com/vertexproject/synapse/tree/it_dev_repo_models',
                'merged': 1,
            }
            q = '''[(it:dev:repo:branch=$valu :parent=$p.parent :start=$p.start :name=$p.name
                :url=$p.url :merged=$p.merged)]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': branch, 'p': props}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('it:dev:repo:branch', branch))
            self.eq(node.get('parent'), parent)
            self.eq(node.get('start'), commit)
            self.eq(node.get('name'), 'IT_dev_repo_models')
            self.eq(node.get('url'), 'https://github.com/vertexproject/synapse/tree/it_dev_repo_models')
            self.eq(node.get('merged'), 1)

            nodes = await core.nodes('it:dev:repo')
            self.len(2, nodes)

            nodes = await core.nodes('it:dev:repo <- *')
            self.len(5, nodes)

            nodes = await core.nodes('it:dev:repo:commit')
            self.len(3, nodes)

            nodes = await core.nodes('it:dev:repo:type:taxonomy')
            self.len(1, nodes)

            nodes = await core.nodes('it:dev:repo:issue:comment')
            self.len(2, nodes)

            nodes = await core.nodes('it:dev:repo:diff:comment')
            self.len(2, nodes)

            nodes = await core.nodes('it:dev:repo:remote')
            self.len(1, nodes)

            nodes = await core.nodes('it:dev:repo:remote :repo -> it:dev:repo')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:dev:repo', repo))

            nodes = await core.nodes('it:dev:repo:remote :remote -> it:dev:repo')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:dev:repo', origin))

            nodes = await core.nodes('it:dev:repo:issue:comment=$guid :replyto -> *', {'vars': {'guid': icom}})
            self.len(1, nodes)

            nodes = await core.nodes('it:dev:repo:diff:comment=$guid :replyto -> *', {'vars': {'guid': dcom}})
            self.len(1, nodes)

            nodes = await core.nodes('it:dev:repo:branch=$guid :parent -> *', {'vars': {'guid': branch}})
            self.len(1, nodes)

    async def test_infotech_vulnscan(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ it:sec:vuln:scan=*
                    :time=202308180819
                    :desc="Woot Woot"
                    :id=FOO-10
                    :ext:url=https://vertex.link/scans/FOO-10
                    :software:name=nessus
                    :software={[ it:software=* :name=nessus ]}
                    :operator={[ entity:contact=* :name=visi ]}
                ]
            ''')
            self.len(1, nodes)

            self.eq(1692346740000000, nodes[0].get('time'))
            self.eq('nessus', nodes[0].get('software:name'))
            self.eq('Woot Woot', nodes[0].get('desc'))
            self.eq('FOO-10', nodes[0].get('id'))
            self.eq('https://vertex.link/scans/FOO-10', nodes[0].get('ext:url'))

            self.nn(nodes[0].get('operator'))
            self.nn(nodes[0].get('software'))

            self.len(1, await core.nodes('it:sec:vuln:scan -> entity:contact +:name=visi'))
            self.len(1, await core.nodes('it:sec:vuln:scan -> it:software +:name=nessus'))

            nodes = await core.nodes('''
                [ it:sec:vuln:scan:result=*
                    :scan={it:sec:vuln:scan}
                    :vuln={[ risk:vuln=* :name="nucsploit9k" ]}
                    :desc="Network service is vulnerable to nucsploit9k"
                    :id=FOO-10.0
                    :ext:url=https://vertex.link/scans/FOO-10/0
                    :time=2023081808190828
                    :mitigated=2023081808190930
                    :mitigation={[ risk:mitigation=* :name="mitigate this" ]}
                    :asset=(inet:server, tcp://1.2.3.4:443)
                    :priority=high
                    :severity=highest
                ]
            ''')
            self.len(1, nodes)
            self.eq(40, nodes[0].get('priority'))
            self.eq(50, nodes[0].get('severity'))
            self.eq(1692346748280000, nodes[0].get('time'))
            self.eq(1692346749300000, nodes[0].get('mitigated'))
            self.eq('Network service is vulnerable to nucsploit9k', nodes[0].get('desc'))
            self.eq('FOO-10.0', nodes[0].get('id'))
            self.eq('https://vertex.link/scans/FOO-10/0', nodes[0].get('ext:url'))

            self.len(1, await core.nodes('it:sec:vuln:scan:result :asset -> * +inet:server'))
            self.len(1, await core.nodes('it:sec:vuln:scan:result -> risk:vuln +:name=nucsploit9k'))
            self.len(1, await core.nodes('it:sec:vuln:scan:result -> risk:mitigation +:name="mitigate this"'))

    async def test_infotech_it_sec_metrics(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ it:sec:metrics=*

                    :org={ gen.ou.org vertex }
                    :org:name=vertex
                    :org:fqdn=vertex.link

                    :period=(202307, 202308)

                    :alerts:count=100
                    :alerts:falsepos=90
                    :alerts:meantime:triage=2:00:00

                    :assets:users=13
                    :assets:hosts=123

                    :assets:vulns:count=4
                    :assets:vulns:mitigated=2
                    :assets:vulns:discovered=4
                    :assets:vulns:preexisting=2

                    :assets:vulns:meantime:mitigate="1D 2:37:00"

                ]
            ''')
            self.len(1, nodes)

            self.eq('vertex', nodes[0].get('org:name'))
            self.eq('vertex.link', nodes[0].get('org:fqdn'))
            self.eq((1688169600000000, 1690848000000000, 2678400000000), nodes[0].get('period'))

            self.eq(100, nodes[0].get('alerts:count'))
            self.eq(90, nodes[0].get('alerts:falsepos'))
            self.eq(7200000000, nodes[0].get('alerts:meantime:triage'))

            self.eq(13, nodes[0].get('assets:users'))
            self.eq(123, nodes[0].get('assets:hosts'))

            self.eq(4, nodes[0].get('assets:vulns:count'))
            self.eq(2, nodes[0].get('assets:vulns:mitigated'))
            self.eq(4, nodes[0].get('assets:vulns:discovered'))
            self.eq(2, nodes[0].get('assets:vulns:preexisting'))

            self.len(1, await core.nodes('it:sec:metrics -> ou:org +:name=vertex'))

    async def test_infotech_windows(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ it:os:windows:service=*
                    :name=Woot
                    :host=*
                    :type=(0x20)
                    :start=(0x20)
                    :errorcontrol=(0x20)
                    :displayname="Foo Bar Baz"
                    :imagepath=c:/windows/system32/woot.exe
                    :description="Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                ]
            ''')

            self.len(1, nodes)
            self.eq(nodes[0].get('name'), 'woot')
            self.eq(nodes[0].get('type'), 0x20)
            self.eq(nodes[0].get('start'), 0x20)
            self.eq(nodes[0].get('errorcontrol'), 0x20)
            self.eq(nodes[0].get('displayname'), 'foo bar baz')
            self.eq(nodes[0].get('imagepath'), 'c:/windows/system32/woot.exe')
            self.eq(nodes[0].get('description'), 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.')

            self.len(1, await core.nodes('it:os:windows:service -> it:host'))
            self.len(1, await core.nodes('it:os:windows:service -> file:path'))

            self.len(1, await core.nodes('[ it:exec:proc=* :windows:service={ it:os:windows:service } ] -> it:os:windows:service'))
