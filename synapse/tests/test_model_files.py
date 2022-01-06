import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.time as s_time

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

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

            nodes = await core.nodes('[ file:bytes=$byts ]', opts={'vars': {'byts': b'visi'}})
            pref = nodes[0].props.get('sha256')[:4]

            self.len(1, await core.nodes('file:bytes:sha256^=$pref +file:bytes:sha256^=$pref', opts={'vars': {'pref': pref}}))

            with self.raises(s_exc.BadTypeValu):
                opts = {'vars': {'a': 'a' * 64}}
                await core.nodes('file:bytes [:sha256=$a]', opts=opts)

    async def test_model_filebytes_pe(self):
        # test to make sure pe metadata is well formed
        async with self.getTestCore() as core:
            async with await core.snap() as snap:

                exp_time = '201801010233'
                exp_time_parse = s_time.parse(exp_time)
                props = {
                    'mime:pe:imphash': 'e' * 32,
                    'mime:pe:pdbpath': r'c:\this\is\my\pdbstring',
                    'mime:pe:exports:time': exp_time,
                    'mime:pe:exports:libname': 'ohgood',
                    'mime:pe:richhdr': 'f' * 64,
                }
                fnode = await snap.addNode('file:bytes', 'a' * 64, props=props)

                # pe props
                self.eq(fnode.get('mime:pe:imphash'), 'e' * 32)
                self.eq(fnode.get('mime:pe:pdbpath'), r'c:/this/is/my/pdbstring')
                self.eq(fnode.get('mime:pe:exports:time'), exp_time_parse)
                self.eq(fnode.get('mime:pe:exports:libname'), 'ohgood')
                self.eq(fnode.get('mime:pe:richhdr'), 'f' * 64)

                # pe resource
                rbnode = await snap.addNode('file:bytes', 'd' * 64)
                rnode = await snap.addNode('file:mime:pe:resource', (fnode.ndef[1], 2, 0x409, rbnode.ndef[1]))

                self.eq(rnode.get('langid'), 0x409)
                self.eq(rnode.get('type'), 2)
                self.eq(rnode.repr('langid'), 'en-US')
                self.eq(rnode.repr('type'), 'RT_BITMAP')

                # pe section
                s1node = await snap.addNode('file:mime:pe:section', (fnode.ndef[1], 'foo', 'b' * 64))

                self.eq(s1node.get('name'), 'foo')
                self.eq(s1node.get('sha256'), 'b' * 64)

                # pe export
                enode = await snap.addNode('file:mime:pe:export', (fnode.ndef[1], 'myexport'))

                self.eq(enode.get('file'), fnode.ndef[1])
                self.eq(enode.get('name'), 'myexport')

                # vsversion
                vskvnode = await snap.addNode('file:mime:pe:vsvers:keyval', ('foo', 'bar'))
                self.eq(vskvnode.get('name'), 'foo')
                self.eq(vskvnode.get('value'), 'bar')

                vsnode = await snap.addNode('file:mime:pe:vsvers:info', (fnode.ndef[1], vskvnode.ndef[1]))
                self.eq(vsnode.get('file'), fnode.ndef[1])
                self.eq(vsnode.get('keyval'), vskvnode.ndef[1])

    async def test_model_filebytes_macho(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                file = 'a' * 64
                fnode = await snap.addNode('file:bytes', file)

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
                self.eq('sha256:' + file, gencmd.get('file'))

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
                self.eq('sha256:' + file, uuid.get('file'))

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
                self.eq('sha256:' + file, ver.get('file'))
                self.eq(42, ver.get('type'))
                self.eq(32, ver.get('size'))
                self.eq('sha256:' + file, ver.get('file'))

                # segment
                seghash = 'e' * 64
                opts = {'vars': {'file': file, 'sha256': seghash}}
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
                self.eq('sha256:' + file, seg.get('file'))
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
            async with await core.snap() as snap:
                fnode = await snap.addNode('file:bytes', 'a' * 64)
                fsnode = await snap.addNode('file:string', (fnode.ndef[1], 'foo'))
                self.eq(fsnode.get('file'), fnode.ndef[1])
                self.eq(fsnode.get('string'), 'foo')

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

            async with await core.snap() as snap:

                node = await snap.addNode('file:path', '/foo/bar/baz.exe')

                self.eq(node.get('base'), 'baz.exe')
                self.eq(node.get('base:ext'), 'exe')
                self.eq(node.get('dir'), '/foo/bar')
                self.nn(await snap.getNodeByNdef(('file:path', '/foo/bar')))

                nodes = await snap.nodes('file:path^="/foo/bar/b"')
                self.len(1, nodes)
                self.eq(node.ndef, nodes[0].ndef)
                nodes = await snap.nodes('file:base^=baz')
                self.len(1, nodes)
                self.eq(node.get('base'), nodes[0].ndef[1])

                node = await snap.addNode('file:path', '/')
                self.none(node.get('base'))
                self.none(node.get('base:ext'))
                self.none(node.get('dir'))
                self.eq(node.ndef[1], '')

                node = await snap.addNode('file:path', '')
                self.none(node.get('base'))
                self.none(node.get('base:ext'))
                self.none(node.get('dir'))
                self.eq(node.ndef[1], '')

                node0 = await snap.addNode('file:bytes', 'hex:56565656')
                node1 = await snap.addNode('file:bytes', 'base64:VlZWVg==')
                node2 = await snap.addNode('file:bytes', b'VVVV')

                self.eq(node0.ndef, node1.ndef)
                self.eq(node1.ndef, node2.ndef)

                self.nn(node0.get('md5'))
                self.nn(node0.get('sha1'))
                self.nn(node0.get('sha256'))
                self.nn(node0.get('sha512'))

                fake = await snap.addNode('file:bytes', '*')
                self.true(fake.ndef[1].startswith('guid:'))

                node = await snap.addNode('file:subfile', (node1.ndef[1], node2.ndef[1]), {'name': 'embed.BIN', 'path': 'foo/embed.bin'})
                self.eq(node.ndef[1], (node1.ndef[1], node2.ndef[1]))
                self.eq(node.get('parent'), node1.ndef[1])
                self.eq(node.get('child'), node2.ndef[1])
                self.eq(node.get('name'), 'embed.bin')
                self.eq(node.get('path'), 'foo/embed.bin')

                fp = 'C:\\www\\woah\\really\\sup.exe'
                node = await snap.addNode('file:filepath', (node0.ndef[1], fp))
                self.eq(node.get('file'), node0.ndef[1])
                self.eq(node.get('path'), 'c:/www/woah/really/sup.exe')
                self.eq(node.get('path:dir'), 'c:/www/woah/really')
                self.eq(node.get('path:base'), 'sup.exe')
                self.eq(node.get('path:base:ext'), 'exe')

            expected_nodes = (
                ('file:path', 'c:/www/woah/really'),
                ('file:path', 'c:/www/woah'),
                ('file:path', 'c:/www'),
                ('file:base', 'sup.exe'),
            )
            await self.checkNodes(core, expected_nodes)

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
