import synapse.exc as s_exc

import synapse.tests.common as s_test

class FileTest(s_test.SynTest):

    def test_model_filebytes(self):

        # test that sha256: form kicks out a sha256 sub.
        with self.getTestCore() as core:
            valu = 'sha256:' + ('a' * 64)
            norm, info = core.model.type('file:bytes').norm(valu)
            self.eq(info['subs']['sha256'], 'a' * 64)

            norm, info = core.model.type('file:bytes').norm('b' * 64)
            self.eq(info['subs']['sha256'], 'b' * 64)

    def test_model_file_types(self):

        with self.getTestCore() as core:

            base = core.model.type('file:base')
            path = core.model.type('file:path')

            norm, info = base.norm('FOO.EXE')
            subs = info.get('subs')

            self.eq('foo.exe', norm)
            self.eq('exe', subs.get('ext'))

            self.raises(s_exc.BadTypeValu, base.norm, 'foo/bar.exe')

            norm, info = path.norm('c:\\Windows\\System32\\calc.exe')

            self.eq(norm, 'c:/windows/system32/calc.exe')
            self.eq(info['subs']['dir'], 'c:/windows/system32')
            self.eq(info['subs']['base'], 'calc.exe')

            with core.snap() as snap:

                node = snap.addNode('file:path', '/foo/bar/baz.exe')

                self.eq(node.get('base'), 'baz.exe')
                self.eq(node.get('base:ext'), 'exe')
                self.eq(node.get('dir'), '/foo/bar')
                self.nn(snap.getNodeByNdef(('file:path', '/foo/bar')))

                node0 = snap.addNode('file:bytes', 'hex:56565656')
                node1 = snap.addNode('file:bytes', 'base64:VlZWVg==')
                node2 = snap.addNode('file:bytes', b'VVVV')

                self.eq(node0.ndef, node1.ndef)
                self.eq(node1.ndef, node2.ndef)

                self.nn(node0.get('md5'))
                self.nn(node0.get('sha1'))
                self.nn(node0.get('sha256'))
                self.nn(node0.get('sha512'))

                fake = snap.addNode('file:bytes', '*')
                self.true(fake.ndef[1].startswith('guid:'))

                node = snap.addNode('file:subfile', (node1.ndef[1], node2.ndef[1]), {'name': 'embed.BIN'})
                self.eq(node.ndef[1], (node1.ndef[1], node2.ndef[1]))
                self.eq(node.get('parent'), node1.ndef[1])
                self.eq(node.get('child'), node2.ndef[1])
                self.eq(node.get('name'), 'embed.bin')

class Newp:

    def test_model_filepath_complex(self):
        with self.getRamCore() as core:

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

    def test_filepath(self):
        with self.getRamCore() as core:

            core.formTufoByProp('file:path', '/foo/bar/baz/faz/')

            self.nn(core.getTufoByProp('file:path', '/foo/bar/baz/faz'))
            self.nn(core.getTufoByProp('file:base', 'faz'))
            self.nn(core.getTufoByProp('file:path', '/foo/bar/baz'))
            self.nn(core.getTufoByProp('file:base', 'baz'))
            self.nn(core.getTufoByProp('file:path', '/foo/bar'))
            self.nn(core.getTufoByProp('file:base', 'bar'))
            self.nn(core.getTufoByProp('file:path', '/foo'))
            self.nn(core.getTufoByProp('file:base', 'foo'))
            self.none(core.getTufoByProp('file:base', ''))

    def test_filebase(self):
        with self.getRamCore() as core:

            core.formTufoByProp('file:base', 'baz.quux')
            self.nn(core.getTufoByProp('file:base', 'baz.quux'))

            self.raises(BadTypeValu, core.formTufoByProp, 'file:base', '/haha')
