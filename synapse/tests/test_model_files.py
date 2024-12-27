import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.time as s_time

import synapse.tests.utils as s_t_utils

class FileTest(s_t_utils.SynTest):

    async def test_model_filebytes(self):

        async with self.getTestCore() as core:
            valu = 'sha256:' + ('a' * 64)
            fbyts = core.model.type('file:bytes')
            norm, info = fbyts.norm(valu)
            self.eq(info['subs']['sha256'], 'a' * 64)

            norm, info = fbyts.norm('b' * 64)
            self.eq(info['subs']['sha256'], 'b' * 64)

            # Allow an arbitrary struct to be ground into a file:bytes guid.
            norm, info = fbyts.norm(('md5', 'b' * 32))
            self.eq(norm, 'guid:d32efb12cb5a0f83ffd12788572e1c88')
            self.eq(info, {})

            self.raises(s_exc.BadTypeValu, fbyts.norm, s_common.guid())
            self.raises(s_exc.BadTypeValu, fbyts.norm, 'guid:0101')
            self.raises(s_exc.BadTypeValu, fbyts.norm, 'helo:moto')
            self.raises(s_exc.BadTypeValu, fbyts.norm, f'sha256:{s_common.guid()}')
            self.raises(s_exc.BadTypeValu, fbyts.norm, 1.23)

            nodes = await core.nodes('''
                [ file:bytes=$byts
                    :exe:packer = {[ it:prod:softver=* :name="Visi Packer 31337" ]}
                    :exe:compiler = {[ it:prod:softver=* :name="Visi Studio 31337" ]}
                ]
            ''', opts={'vars': {'byts': b'visi'}})
            pref = nodes[0].props.get('sha256')[:4]

            self.nn(nodes[0].get('exe:packer'))
            self.nn(nodes[0].get('exe:compiler'))
            self.len(1, await core.nodes('file:bytes :exe:packer -> it:prod:softver +:name="Visi Packer 31337"'))
            self.len(1, await core.nodes('file:bytes :exe:compiler -> it:prod:softver +:name="Visi Studio 31337"'))

            self.len(1, await core.nodes('file:bytes:sha256^=$pref +file:bytes:sha256^=$pref', opts={'vars': {'pref': pref}}))

            with self.raises(s_exc.BadTypeValu):
                opts = {'vars': {'a': 'a' * 64}}
                await core.nodes('file:bytes [:sha256=$a]', opts=opts)

            badv = 'z' * 64
            opts = {'vars': {'z': badv}}
            msgs = await core.stormlist('[ file:bytes=$z ]', opts=opts)
            self.stormIsInErr(f'invalid unadorned file:bytes value: Non-hexadecimal digit found - valu={badv}', msgs)

            msgs = await core.stormlist('[ file:bytes=`sha256:{$z}` ]', opts=opts)
            self.stormIsInErr(f'invalid file:bytes sha256 value: Non-hexadecimal digit found - valu={badv}', msgs)

            msgs = await core.stormlist('[file:bytes=base64:foo]')
            self.stormIsInErr(f'invalid file:bytes base64 value: Incorrect padding - valu=foo', msgs)

            msgs = await core.stormlist('[file:bytes=hex:foo]')
            self.stormIsInErr(f'invalid file:bytes hex value: Odd-length string - valu=foo', msgs)

            msgs = await core.stormlist('[file:bytes=hex:foo]')
            self.stormIsInErr(f'invalid file:bytes hex value: Odd-length string - valu=foo', msgs)

            msgs = await core.stormlist('[file:bytes=guid:foo]')
            self.stormIsInErr(f'guid is not a guid - valu=foo', msgs)

            msgs = await core.stormlist('[file:bytes=newp:foo]')
            self.stormIsInErr(f'unable to norm as file:bytes - valu=newp:foo', msgs)

    async def test_model_filebytes_pe(self):
        # test to make sure pe metadata is well formed
        async with self.getTestCore() as core:
            filea = 'a' * 64
            exp_time = '201801010233'
            props = {
                'imphash': 'e' * 32,
                'pdbpath': r'c:\this\is\my\pdbstring',
                'exports:time': exp_time,
                'exports:libname': 'ohgood',
                'richhdr': 'f' * 64,
            }
            q = '''[(file:bytes=$valu :mime:pe:imphash=$p.imphash :mime:pe:pdbpath=$p.pdbpath
            :mime:pe:exports:time=$p."exports:time" :mime:pe:exports:libname=$p."exports:libname"
            :mime:pe:richhdr=$p.richhdr )]'''
            nodes = await core.nodes(q, opts={'vars': {'valu': filea, 'p': props}})
            self.len(1, nodes)
            fnode = nodes[0]
            # pe props
            self.eq(fnode.get('mime:pe:imphash'), 'e' * 32)
            self.eq(fnode.get('mime:pe:pdbpath'), r'c:/this/is/my/pdbstring')
            self.eq(fnode.get('mime:pe:exports:time'), s_time.parse(exp_time))
            self.eq(fnode.get('mime:pe:exports:libname'), 'ohgood')
            self.eq(fnode.get('mime:pe:richhdr'), 'f' * 64)
            # pe resource
            nodes = await core.nodes('[file:mime:pe:resource=$valu]',
                                     opts={'vars': {'valu': (filea, 2, 0x409, 'd' * 64)}})
            self.len(1, nodes)
            rnode = nodes[0]
            self.eq(rnode.get('langid'), 0x409)
            self.eq(rnode.get('type'), 2)
            self.eq(rnode.repr('langid'), 'en-US')
            self.eq(rnode.repr('type'), 'RT_BITMAP')
            # pe section
            nodes = await core.nodes('[file:mime:pe:section=$valu]',
                                     opts={'vars': {'valu': (filea, 'foo', 'b' * 64)}})
            self.len(1, nodes)
            s1node = nodes[0]
            self.eq(s1node.get('name'), 'foo')
            self.eq(s1node.get('sha256'), 'b' * 64)
            # pe export
            nodes = await core.nodes('[file:mime:pe:export=$valu]', opts={'vars': {'valu': (filea, 'myexport')}})
            self.len(1, nodes)
            enode = nodes[0]
            self.eq(enode.get('file'), fnode.ndef[1])
            self.eq(enode.get('name'), 'myexport')
            # vsversion
            nodes = await core.nodes('[file:mime:pe:vsvers:keyval=(foo, bar)]')
            self.len(1, nodes)
            vskvnode = nodes[0]
            self.eq(vskvnode.get('name'), 'foo')
            self.eq(vskvnode.get('value'), 'bar')
            nodes = await core.nodes('[file:mime:pe:vsvers:info=$valu]',
                                     opts={'vars': {'valu': (filea, vskvnode.ndef[1])}})
            self.len(1, nodes)
            vsnode = nodes[0]
            self.eq(vsnode.get('file'), fnode.ndef[1])
            self.eq(vsnode.get('keyval'), vskvnode.ndef[1])

    async def test_model_filebytes_macho(self):
        async with self.getTestCore() as core:
            file0 = 'a' * 64
            nodes = await core.nodes('[file:bytes=$valu]', opts={'vars': {'valu': file0}})
            self.len(1, nodes)
            fnode = nodes[0]

            # loadcmds
            opts = {'vars': {'file': fnode.get('sha256')}}
            gencmd = await core.nodes('''[
                file:mime:macho:loadcmd=*
                    :file=$file
                    :type=27
                    :size=123456
            ]''', opts=opts)
            self.len(1, gencmd)
            gencmd = gencmd[0]
            self.eq(27, gencmd.get('type'))
            self.eq(123456, gencmd.get('size'))
            self.eq('sha256:' + file0, gencmd.get('file'))

            # uuid
            opts = {'vars': {'file': fnode.get('sha256')}}
            uuid = await core.nodes(f'''[
                file:mime:macho:uuid=*
                    :file=$file
                    :type=27
                    :size=32
                    :uuid=BCAA4A0BBF703A5DBCF972F39780EB67
            ]''', opts=opts)
            self.len(1, uuid)
            uuid = uuid[0]
            self.eq('bcaa4a0bbf703a5dbcf972f39780eb67', uuid.get('uuid'))
            self.eq('sha256:' + file0, uuid.get('file'))

            # version
            ver = await core.nodes(f'''[
                file:mime:macho:version=*
                    :file=$file
                    :type=42
                    :size=32
                    :version="7605.1.33.1.4"
            ]''', opts=opts)
            self.len(1, ver)
            ver = ver[0]
            self.eq('7605.1.33.1.4', ver.get('version'))
            self.eq('sha256:' + file0, ver.get('file'))
            self.eq(42, ver.get('type'))
            self.eq(32, ver.get('size'))
            self.eq('sha256:' + file0, ver.get('file'))

            # segment
            seghash = 'e' * 64
            opts = {'vars': {'file': file0, 'sha256': seghash}}
            seg = await core.nodes(f'''[
                file:mime:macho:segment=*
                    :file=$file
                    :type=1
                    :size=48
                    :name="__TEXT"
                    :memsize=4092
                    :disksize=8192
                    :sha256=$sha256
                    :offset=1234
            ]''', opts=opts)
            self.len(1, seg)
            seg = seg[0]
            self.eq('sha256:' + file0, seg.get('file'))
            self.eq(1, seg.get('type'))
            self.eq(48, seg.get('size'))
            self.eq('__TEXT', seg.get('name'))
            self.eq(4092, seg.get('memsize'))
            self.eq(8192, seg.get('disksize'))
            self.eq(seghash, seg.get('sha256'))
            self.eq(1234, seg.get('offset'))

            # section
            opts = {'vars': {'seg': seg.ndef[1]}}
            sect = await core.nodes(f'''[
                file:mime:macho:section=*
                    :segment=$seg
                    :name="__text"
                    :size=12
                    :type=0
                    :offset=5678
            ]''', opts=opts)
            self.len(1, sect)
            sect = sect[0]
            self.eq(seg.ndef[1], sect.get('segment'))
            self.eq("__text", sect.get('name'))
            self.eq(12, sect.get('size'))
            self.eq(0, sect.get('type'))
            self.eq(5678, sect.get('offset'))

    async def test_model_filebytes_string(self):
        async with self.getTestCore() as core:
            file0 = 'a' * 64
            nodes = await core.nodes('[file:string=($valu, foo)]', opts={'vars': {'valu': file0}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('file'), f'sha256:{file0}')
            self.eq(node.get('string'), 'foo')

    async def test_model_file_types(self):

        async with self.getTestCore() as core:

            base = core.model.type('file:base')
            path = core.model.type('file:path')

            norm, info = base.norm('FOO.EXE')
            subs = info.get('subs')

            self.eq('foo.exe', norm)
            self.eq('exe', subs.get('ext'))

            self.raises(s_exc.BadTypeValu, base.norm, 'foo/bar.exe')
            self.raises(s_exc.BadTypeValu, base.norm, '/haha')

            norm, info = path.norm('../.././..')
            self.eq(norm, '')

            norm, info = path.norm('c:\\Windows\\System32\\calc.exe')

            self.eq(norm, 'c:/windows/system32/calc.exe')
            self.eq(info['subs']['dir'], 'c:/windows/system32')
            self.eq(info['subs']['base'], 'calc.exe')

            norm, info = path.norm(r'/foo////bar/.././baz.json')
            self.eq(norm, '/foo/baz.json')

            norm, info = path.norm(r'./hehe/haha')
            self.eq(norm, 'hehe/haha')
            # '.' has no normable value.
            self.raises(s_exc.BadTypeValu, path.norm, '.')
            self.raises(s_exc.BadTypeValu, path.norm, '..')

            norm, info = path.norm('c:')
            self.eq(norm, 'c:')
            subs = info.get('subs')
            self.none(subs.get('ext'))
            self.none(subs.get('dir'))
            self.eq(subs.get('base'), 'c:')

            norm, info = path.norm('/foo')
            self.eq(norm, '/foo')
            subs = info.get('subs')
            self.none(subs.get('ext'))
            self.none(subs.get('dir'))
            self.eq(subs.get('base'), 'foo')

            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': '/foo/bar/baz.exe'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('base'), 'baz.exe')
            self.eq(node.get('base:ext'), 'exe')
            self.eq(node.get('dir'), '/foo/bar')
            self.len(1, await core.nodes('file:path="/foo/bar"'))
            self.len(1, await core.nodes('file:path^="/foo/bar/b"'))
            self.len(1, await core.nodes('file:base^=baz'))
            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': '/'}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], '')
            self.none(node.get('base'))
            self.none(node.get('base:ext'))
            self.none(node.get('dir'))

            nodes = await core.nodes('[file:path=$valu]', opts={'vars': {'valu': ''}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], '')
            self.none(node.get('base'))
            self.none(node.get('base:ext'))
            self.none(node.get('dir'))

            nodes = await core.nodes('[file:bytes=$valu]', opts={'vars': {'valu': 'hex:56565656'}})
            self.len(1, nodes)
            node0 = nodes[0]

            nodes = await core.nodes('[file:bytes=$valu]', opts={'vars': {'valu': 'base64:VlZWVg=='}})
            self.len(1, nodes)
            node1 = nodes[0]

            nodes = await core.nodes('[file:bytes=$valu]', opts={'vars': {'valu': b'VVVV'}})
            self.len(1, nodes)
            node2 = nodes[0]

            self.eq(node0.ndef, node1.ndef)
            self.eq(node1.ndef, node2.ndef)

            self.nn(node0.get('md5'))
            self.nn(node0.get('sha1'))
            self.nn(node0.get('sha256'))
            self.nn(node0.get('sha512'))

            nodes = await core.nodes('[file:bytes=$valu]', opts={'vars': {'valu': '*'}})
            self.len(1, nodes)
            fake = nodes[0]
            self.true(fake.ndef[1].startswith('guid:'))

            nodes = await core.nodes('[file:subfile=$valu :name=embed.BIN :path="foo/embed.bin"]',
                                     opts={'vars': {'valu': (node1.ndef[1], node2.ndef[1])}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[1], (node1.ndef[1], node2.ndef[1]))
            self.eq(node.get('parent'), node1.ndef[1])
            self.eq(node.get('child'), node2.ndef[1])
            self.eq(node.get('name'), 'embed.bin')
            self.eq(node.get('path'), 'foo/embed.bin')

            fp = 'C:\\www\\woah\\really\\sup.exe'
            nodes = await core.nodes('[file:filepath=$valu]', opts={'vars': {'valu': (node0.ndef[1], fp)}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('file'), node0.ndef[1])
            self.eq(node.get('path'), 'c:/www/woah/really/sup.exe')
            self.eq(node.get('path:dir'), 'c:/www/woah/really')
            self.eq(node.get('path:base'), 'sup.exe')
            self.eq(node.get('path:base:ext'), 'exe')

            self.len(1, await core.nodes('file:path="c:/www/woah/really"'))
            self.len(1, await core.nodes('file:path="c:/www"'))
            self.len(1, await core.nodes('file:path=""'))
            self.len(1, await core.nodes('file:base="sup.exe"'))

    async def test_model_file_ismime(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ file:bytes="*" :mime=text/PLAIN ]')

            self.len(1, nodes)
            guid = nodes[0].ndef[1]
            self.eq('text/plain', nodes[0].get('mime'))

            nodes = await core.nodes('file:mime=text/plain')
            self.len(1, nodes)

            opts = {'vars': {'guid': guid}}
            nodes = await core.nodes('file:ismime:file=$guid', opts=opts)
            self.len(1, nodes)

            node = nodes[0]
            self.eq(node.ndef, ('file:ismime', (guid, 'text/plain')))

    async def test_model_file_mime_msoffice(self):

        async with self.getTestCore() as core:

            fileguid = s_common.guid()
            opts = {'vars': {'fileguid': f'guid:{fileguid}'}}

            def testmsoffice(n):
                self.eq('lolz', n.get('title'))
                self.eq('deep_value', n.get('author'))
                self.eq('GME stonks', n.get('subject'))
                self.eq('stonktrader3000', n.get('application'))
                self.eq(1611100800000, n.get('created'))
                self.eq(1611187200000, n.get('lastsaved'))

                self.eq(f'guid:{fileguid}', n.get('file'))
                self.eq(0, n.get('file:offs'))
                self.eq(('foo', 'bar'), n.get('file:data'))

            nodes = await core.nodes('''[
                file:mime:msdoc=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :title=lolz
                    :author=deep_value
                    :subject="GME stonks"
                    :application=stonktrader3000
                    :created=20210120
                    :lastsaved=20210121
            ]''', opts=opts)
            self.len(1, nodes)
            testmsoffice(nodes[0])

            nodes = await core.nodes('''[
                file:mime:msxls=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :title=lolz
                    :author=deep_value
                    :subject="GME stonks"
                    :application=stonktrader3000
                    :created=20210120
                    :lastsaved=20210121
            ]''', opts=opts)
            self.len(1, nodes)
            testmsoffice(nodes[0])

            nodes = await core.nodes('''[
                file:mime:msppt=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :title=lolz
                    :author=deep_value
                    :subject="GME stonks"
                    :application=stonktrader3000
                    :created=20210120
                    :lastsaved=20210121
            ]''', opts=opts)
            self.len(1, nodes)
            testmsoffice(nodes[0])

    async def test_model_file_mime_rtf(self):

        async with self.getTestCore() as core:

            fileguid = s_common.guid()
            opts = {'vars': {'fileguid': f'guid:{fileguid}'}}

            nodes = await core.nodes('''[
                file:mime:rtf=*
                    :file=$fileguid
                    :file:offs=0
                    :file:data=(foo, bar)
                    :guid=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            ]''', opts=opts)

            self.len(1, nodes)
            self.eq(f'guid:{fileguid}', nodes[0].get('file'))
            self.eq(0, nodes[0].get('file:offs'))
            self.eq(('foo', 'bar'), nodes[0].get('file:data'))
            self.eq('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', nodes[0].get('guid'))

    async def test_model_file_meta_exif(self):

        async with self.getTestCore() as core:

            fileguid = s_common.guid()
            conguid = s_common.guid()
            opts = {'vars': {
                        'fileguid': f'guid:{fileguid}',
                        'conguid': conguid
                }
            }

            def testexif(n):
                self.eq(f'guid:{fileguid}', n.get('file'))
                self.eq(0, n.get('file:offs'))
                self.eq(('foo', 'bar'), n.get('file:data'))
                self.eq('aaaa', n.get('desc'))
                self.eq('bbbb', n.get('comment'))
                self.eq('foo bar', n.get('text'))
                self.eq(1578236238000, n.get('created'))
                self.eq('a6b4', n.get('imageid'))
                self.eq(conguid, n.get('author'))
                self.eq((38.9582839, -77.358946), n.get('latlong'))
                self.eq(6371137800, n.get('altitude'))

            nodes = await core.nodes(f'''[
                ps:contact=$conguid
                    :name="Steve Rogers"
                    :title="Captain"
                    :orgname="U.S. Army"
                    :address="569 Leaman Place, Brooklyn, NY, 11201, USA"
            ]''', opts=opts)

            props = '''
                :file=$fileguid
                :file:offs=0
                :file:data=(foo, bar)
                :desc=aaaa
                :comment=bbbb
                :text="  Foo   Bar   "
                :created="2020-01-05 14:57:18"
                :imageid=a6b4
                :author=$conguid
                :latlong="38.9582839,-77.358946"
                :altitude="129 meters"'''

            nodes = await core.nodes(f'''[
                file:mime:jpg=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

            nodes = await core.nodes(f'''[
                file:mime:tif=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

            nodes = await core.nodes(f'''[
                file:mime:gif=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

            nodes = await core.nodes(f'''[
                file:mime:png=*
                    {props}
            ]''', opts=opts)

            self.len(1, nodes)
            testexif(nodes[0])

    async def test_model_file_archive_entry(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ file:archive:entry=*
                    :parent=*
                    :file=*
                    :path=foo/bar.exe
                    :user=visi
                    :added=20230630
                    :created=20230629
                    :modified=20230629
                    :comment="what exe. much wow."
                    :posix:uid=1000
                    :posix:gid=1000
                    :posix:perms=0x7f
                    :archived:size=999
                ]
            ''')

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('parent'))

            self.eq('visi', nodes[0].get('user'))
            self.eq('what exe. much wow.', nodes[0].get('comment'))

            self.eq(1688083200000, nodes[0].get('added'))
            self.eq(1687996800000, nodes[0].get('created'))
            self.eq(1687996800000, nodes[0].get('modified'))

            self.eq(1000, nodes[0].get('posix:uid'))
            self.eq(1000, nodes[0].get('posix:gid'))
            self.eq(127, nodes[0].get('posix:perms'))

            self.len(1, await core.nodes('file:archive:entry :path -> file:path'))
            self.len(1, await core.nodes('file:archive:entry :user -> inet:user'))
            self.len(1, await core.nodes('file:archive:entry :file -> file:bytes'))
            self.len(1, await core.nodes('file:archive:entry :parent -> file:bytes'))

    async def test_model_file_lnk(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes(r'''[
                file:mime:lnk=*
                    :entry:primary="c:\\some\\stuff\\prog~2\\cmd.exe"
                    :entry:secondary="c:\\some\\stuff\program files\\cmd.exe"
                    :entry:extended="c:\\some\\actual\\stuff\\I\\swear\\cmd.exe"
                    :entry:localized="c:\\some\\actual\\archivos\\I\\swear\\cmd.exe"
                    :entry:icon="%windir%\\system32\\notepad.exe"

                    :environment:path="%windir%\\system32\\cmd.exe"
                    :environment:icon="%some%%envvar%"
                    :working="%HOMEDRIVE%%HOMEPATH%"
                    :relative="..\\..\\..\\some\\foo.bar.txt"
                    :arguments="/q /c copy %systemroot%\\system32\\msh*.exe"
                    :desc="I've been here the whole time."

                    :flags=0x40df
                    :target:attrs=0x20
                    :target:size=12345
                    :target:created="2023/01/25 18:57:45.284"
                    :target:accessed="2023/01/25 18:57:45.284"
                    :target:written="2023/01/25 18:57:45.284"

                    :driveserial=0x6af54670
                    :machineid=stellarcollapse
                    :iconindex=1
            ]''')
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.get('entry:primary'), 'c:/some/stuff/prog~2/cmd.exe')
            self.eq(node.get('entry:secondary'), 'c:/some/stuff/program files/cmd.exe')
            self.eq(node.get('entry:extended'), 'c:/some/actual/stuff/i/swear/cmd.exe')
            self.eq(node.get('entry:localized'), 'c:/some/actual/archivos/i/swear/cmd.exe')

            self.eq(node.get('entry:icon'), '%windir%/system32/notepad.exe')
            self.eq(node.get('environment:path'), '%windir%/system32/cmd.exe')
            self.eq(node.get('environment:icon'), '%some%%envvar%')

            self.eq(node.get('working'), '%homedrive%%homepath%')
            self.eq(node.get('relative'), '..\\..\\..\\some\\foo.bar.txt')
            self.eq(node.get('arguments'), '/q /c copy %systemroot%\\system32\\msh*.exe')
            self.eq(node.get('desc'), "I've been here the whole time.")

            self.eq(node.get('flags'), 0x40df)
            self.eq(node.get('target:attrs'), 0x20)
            self.eq(node.get('target:size'), 12345)

            time = 1674673065284
            self.eq(node.get('target:created'), time)
            self.eq(node.get('target:accessed'), time)
            self.eq(node.get('target:written'), time)

            self.eq(node.get('driveserial'), 0x6af54670)
            self.eq(node.get('machineid'), 'stellarcollapse')
            self.eq(node.get('iconindex'), 1)

            self.len(1, await core.nodes('file:mime:lnk -> it:hostname'))

    async def test_model_file_attachment(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('''
                [ file:attachment=*
                    :name=Foo/Bar.exe
                    :text="foo bar"
                    :file=*
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('file'))
            self.eq('foo bar', nodes[0].get('text'))
            self.eq('foo/bar.exe', nodes[0].get('name'))

            self.len(1, await core.nodes('file:attachment -> file:bytes'))
            self.len(1, await core.nodes('file:attachment -> file:path'))
