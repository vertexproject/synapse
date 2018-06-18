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

                node = snap.addNode('file:path', '/')
                self.none(node.get('base'))
                self.none(node.get('base:exe'))
                self.none(node.get('dir'))
                self.eq(node.ndef[1], '')

                node = snap.addNode('file:path', '')
                self.none(node.get('base'))
                self.none(node.get('base:exe'))
                self.none(node.get('dir'))
                self.eq(node.ndef[1], '')

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

class Newp:

    def test_model_file_bytes(self):
        with self.getRamCore() as core:

            hset = s_hashset.HashSet()
            hset.update(b'visi')

            valu, props = hset.guid()
            t0 = core.formTufoByProp('file:bytes', valu, **props)

            self.eq(t0[1].get('file:bytes:size'), 4)

            self.eq(t0[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
            self.eq(t0[1].get('file:bytes:md5'), '1b2e93225959e3722efed95e1731b764')
            self.eq(t0[1].get('file:bytes:sha1'), '93de0c7d579384feb3561aa504acd8f23f388040')
            self.eq(t0[1].get('file:bytes:sha256'), 'e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f')
            self.eq(t0[1].get('file:bytes:sha512'), '8238be12bcc3c10da7e07dbea528e9970dc809c07c5aef545a14e5e8d2038563b29c2e818d167b06e6a33412e6beb8347fcc44520691347aea9ee21fcf804e39')

    def test_model_file_seeds(self):
        with self.getRamCore() as core:

            hset = s_hashset.HashSet()
            hset.update(b'visi')

            valu, props = hset.guid()
            t0 = core.formTufoByProp('file:bytes', valu, **props)

            self.eq(t0[0], core.formTufoByProp('file:bytes:sha256', props.get('sha256'))[0])
            self.eq(t0[0], core.formTufoByProp('file:bytes:sha512', props.get('sha512'))[0])

            self.ne(t0[0], core.formTufoByProp('file:bytes:sha1', props.get('sha1'))[0])
            self.ne(t0[0], core.formTufoByProp('file:bytes:md5', props.get('md5'))[0])

    def test_model_file_seeds_capitalization(self):
        fhash = '6ACC29BFC5F8F772FA7AAF4A705F91CB68DC88CB22F4EF5101281DC42109A104'
        fhash_lower = fhash.lower()
        stable_guid = 'ed73917b1dc4011627f7a101ace491c8'

        with self.getRamCore() as core:

            n1 = core.formTufoByProp('file:bytes:sha256', fhash)
            n2 = core.formTufoByProp('file:bytes:sha256', fhash_lower)
            # Sha256 should be lowercase since the prop type is lowercased
            n1def = s_tufo.ndef(n1)
            n2def = s_tufo.ndef(n2)
            self.eq(n1def[1], stable_guid)
            self.eq(n2def[1], stable_guid)
            self.eq(n1[0], n2[0])

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

    def test_model_files_imgof(self):
        with self.getRamCore() as core:

            pnod = core.formTufoByProp('ps:person', None)
            fnod = core.formTufoByProp('file:bytes', None)

            piden = pnod[1].get('ps:person')
            fiden = fnod[1].get('file:bytes')

            img0 = core.formTufoByProp('file:imgof', (fiden, ('ps:person', piden)))
            img1 = core.formTufoByProp('file:imgof', '(%s,ps:person=%s)' % (fiden, piden))

            self.eq(img0[0], img1[0])
            self.eq(img0[1].get('file:imgof:file'), fiden)
            self.eq(img0[1].get('file:imgof:xref'), 'ps:person=' + piden)
            self.eq(img0[1].get('file:imgof:xref:prop'), 'ps:person')
            self.eq(img0[1].get('file:imgof:xref:strval'), piden)
            self.eq(img0[1].get('file:imgof:xref:intval'), None)

    def test_model_files_txtref(self):
        with self.getRamCore() as core:

            iden = guid()

            img0 = core.formTufoByProp('file:txtref', (iden, ('inet:email', 'visi@vertex.link')))
            img1 = core.formTufoByProp('file:txtref', '(%s,inet:email=visi@VERTEX.LINK)' % iden)

            self.eq(img0[0], img1[0])
            self.eq(img0[1].get('file:txtref:file'), iden)
            self.eq(img0[1].get('file:txtref:xref'), 'inet:email=visi@vertex.link')
            self.eq(img0[1].get('file:txtref:xref:prop'), 'inet:email')
            self.eq(img0[1].get('file:txtref:xref:strval'), 'visi@vertex.link')
            self.eq(img0[1].get('file:txtref:xref:intval'), None)

    def test_model_file_bytes_axon(self):
        self.skipLongTest()
        with self.getAxonCore() as env:
            with s_daemon.Daemon() as dmon:

                dmonlink = dmon.listen('tcp://127.0.0.1:0/')
                dmonport = dmonlink[1].get('port')
                dmon.share('core', env.core)

                coreurl = 'tcp://127.0.0.1:%d/core' % dmonport
                core = s_telepath.openurl(coreurl)

                node = core.formNodeByBytes(b'visi', name='visi.bin')
                self.eq(node[1].get('file:bytes:size'), 4)
                self.eq(node[1].get('file:bytes:name'), 'visi.bin')
                self.eq(node[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
                self.eq(node[1].get('file:bytes:md5'), '1b2e93225959e3722efed95e1731b764')
                self.eq(node[1].get('file:bytes:sha1'), '93de0c7d579384feb3561aa504acd8f23f388040')
                self.eq(node[1].get('file:bytes:sha256'), 'e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f')
                self.eq(node[1].get('file:bytes:sha512'), '8238be12bcc3c10da7e07dbea528e9970dc809c07c5aef545a14e5e8d2038563b'
                                                            '29c2e818d167b06e6a33412e6beb8347fcc44520691347aea9ee21fcf804e39')

                fd = io.BytesIO(b'foobar')
                node = core.formNodeByFd(fd, name='foobar.exe')
                self.eq(node[1].get('file:bytes:size'), 6)
                self.eq(node[1].get('file:bytes:name'), 'foobar.exe')
