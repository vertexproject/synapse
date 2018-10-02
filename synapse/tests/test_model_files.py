import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class FileTest(s_t_utils.SynTest):

    async def test_model_filebytes(self):

        # test that sha256: form kicks out a sha256 sub.
        async with self.getTestCore() as core:
            valu = 'sha256:' + ('a' * 64)
            fbyts = core.model.type('file:bytes')
            norm, info = fbyts.norm(valu)
            self.eq(info['subs']['sha256'], 'a' * 64)

            norm, info = fbyts.norm('b' * 64)
            self.eq(info['subs']['sha256'], 'b' * 64)

            self.raises(s_exc.BadTypeValu, fbyts.norm, s_common.guid())
            self.raises(s_exc.BadTypeValu, fbyts.norm, 'guid:0101')
            self.raises(s_exc.BadTypeValu, fbyts.norm, 'helo:moto')
            self.raises(s_exc.BadTypeValu, fbyts.norm, f'sha256:{s_common.guid()}')

    async def test_model_file_types(self):

        async with self.getTestCore() as core:

            base = core.model.type('file:base')
            path = core.model.type('file:path')

            norm, info = base.norm('FOO.EXE')
            subs = info.get('subs')

            self.eq('foo.exe', norm)
            self.eq('exe', subs.get('ext'))

            self.eq(b'oh\xed\xb3\xbesnap', base.indx('oh\udcfesnap'))
            self.eq(b'oh\xed\xb3\xbes', base.indxByPref('oh\udcfes')[0][1])
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

            self.eq(b'c:/the/real/world/\xed\xb3\xbeis/messy', path.indx('c:/the/real/world/\udcfeis/messy'))
            self.eq(b'c:/the/real/world/\xed\xb3\xbe', path.indxByPref('c:/the/real/world/\udcfe')[0][1])

            async with await core.snap() as snap:

                node = await snap.addNode('file:path', '/foo/bar/baz.exe')

                self.eq(node.get('base'), 'baz.exe')
                self.eq(node.get('base:ext'), 'exe')
                self.eq(node.get('dir'), '/foo/bar')
                self.nn(await snap.getNodeByNdef(('file:path', '/foo/bar')))

                nodes = await alist(snap.getNodesBy('file:path', '/foo/bar/b', cmpr='^='))
                self.len(1, nodes)
                self.eq(node.ndef, nodes[0].ndef)
                nodes = await alist(snap.getNodesBy('file:base', 'baz', cmpr='^='))
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

                node = await snap.addNode('file:subfile', (node1.ndef[1], node2.ndef[1]), {'name': 'embed.BIN'})
                self.eq(node.ndef[1], (node1.ndef[1], node2.ndef[1]))
                self.eq(node.get('parent'), node1.ndef[1])
                self.eq(node.get('child'), node2.ndef[1])
                self.eq(node.get('name'), 'embed.bin')

                fp = 'C:\\www\\woah\\really\\sup.exe'
                node = await snap.addNode('file:filepath', (node0.ndef[1], fp))
                self.eq(node.get('file'), node0.ndef[1])
                self.eq(node.get('path'), 'c:/www/woah/really/sup.exe')
                self.eq(node.get('path:dir'), 'c:/www/woah/really')
                self.eq(node.get('path:base'), 'sup.exe')
                self.eq(node.get('path:base:ext'), 'exe')
