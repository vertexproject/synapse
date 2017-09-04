from __future__ import absolute_import, unicode_literals

import synapse.axon as s_axon
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.tufo as s_tufo

from synapse.tests.common import *

class FileModelTest(SynTest):

    def test_model_file_bytes(self):

        with s_cortex.openurl('ram:///') as core:

            hset = s_axon.HashSet()
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

        with s_cortex.openurl('ram:///') as core:

            hset = s_axon.HashSet()
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

        with s_cortex.openurl('ram:///') as core:

            n1 = core.formTufoByProp('file:bytes:sha256', fhash)
            n2 = core.formTufoByProp('file:bytes:sha256', fhash_lower)
            # Sha256 should be lowercase since the prop type is lowercased
            n1def = s_tufo.ndef(n1)
            n2def = s_tufo.ndef(n2)
            self.eq(n1def[1], stable_guid)
            self.eq(n2def[1], stable_guid)
            self.eq(n1[0], n2[0])

    def test_filepath(self):

        with s_cortex.openurl('ram:///') as core:

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

        with s_cortex.openurl('ram:///') as core:

            core.formTufoByProp('file:base', 'baz.quux')
            self.nn(core.getTufoByProp('file:base', 'baz.quux'))

            self.raises(BadTypeValu, core.formTufoByProp, 'file:base', '/haha')

    def test_model_files_imgof(self):

        with s_cortex.openurl('ram:///') as core:

            core.setConfOpt('enforce', 1)

            pnod = core.formTufoByProp('ps:person', None)
            fnod = core.formTufoByProp('file:bytes', None)

            piden = pnod[1].get('ps:person')
            fiden = fnod[1].get('file:bytes')

            img0 = core.formTufoByProp('file:imgof', (fiden, 'ps:person', piden))
            img1 = core.formTufoByProp('file:imgof', '%s|ps:person|%s' % (fiden, piden))

            self.eq(img0[0], img1[0])
            self.eq(img0[1].get('file:imgof:file'), fiden)
            self.eq(img0[1].get('file:imgof:xref:ps:person'), piden)

    def test_model_files_txtref(self):

        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            iden = guid()

            img0 = core.formTufoByProp('file:txtref', (iden, 'inet:email', 'visi@vertex.link'))
            img1 = core.formTufoByProp('file:txtref', '%s|inet:email|visi@VERTEX.LINK' % iden)

            self.eq(img0[0], img1[0])
            self.eq(img0[1].get('file:txtref:file'), iden)
            self.eq(img0[1].get('file:txtref:xref:inet:email'), 'visi@vertex.link')

    def test_model_file_bytes_axon(self):

        fd = s_compat.BytesIO(b'foobar')

        # create an cortex with access to an axon
        with self.getTestDir() as dirname:

            conf = {
                'ctors': (
                    ('axon00', 'syn:axon', {'datadir': dirname}),
                    ('core00', 'syn:cortex', {'url': 'ram:///', 'axon:url': 'dmon://axon00'}),
                ),

                'share': (
                    ('core00', {}),
                ),

            }

            with s_daemon.Daemon() as dmon:

                dmon.loadDmonConf(conf)
                link = dmon.listen('tcp://127.0.0.1:0/')

                port = link[1].get('port')

                core = s_telepath.openurl('tcp://127.0.0.1/core00', port=port)

                node = core.formNodeByBytes(b'visi', name='visi.bin')

                self.eq(node[1].get('file:bytes:size'), 4)
                self.eq(node[1].get('file:bytes:name'), 'visi.bin')

                self.eq(node[1].get('file:bytes'), '442f602ecf8230b2a59a44b4f845be27')
                self.eq(node[1].get('file:bytes:md5'), '1b2e93225959e3722efed95e1731b764')
                self.eq(node[1].get('file:bytes:sha1'), '93de0c7d579384feb3561aa504acd8f23f388040')
                self.eq(node[1].get('file:bytes:sha256'), 'e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f')
                self.eq(node[1].get('file:bytes:sha512'), '8238be12bcc3c10da7e07dbea528e9970dc809c07c5aef545a14e5e8d2038563b29c2e818d167b06e6a33412e6beb8347fcc44520691347aea9ee21fcf804e39')

                node = core.formNodeByFd(fd, name='foobar.exe')

                self.eq(node[1].get('file:bytes:size'), 6)
                self.eq(node[1].get('file:bytes:name'), 'foobar.exe')

    def test_model_file_filepath(self):
        with s_cortex.openurl('ram:///') as core:
            core.setConfOpt('enforce', 1)

            byts = guid()
            node = core.formTufoByProp('file:filepath', (byts, r'c:\Windows\System32\woot.exe'))

            self.eq(node[1].get('file:filepath:bytes'), byts)
            self.eq(node[1].get('file:filepath:path'), r'c:\windows\system32\woot.exe')
            self.eq(node[1].get('file:filepath:path:dir'), r'c:\windows\system32')
            self.eq(node[1].get('file:filepath:path:base'), 'woot.exe')

            self.nn(core.getTufoByProp('file:path', r'c:\Windows\System32\woot.exe'))
            self.nn(core.getTufoByProp('file:bytes', guid))

