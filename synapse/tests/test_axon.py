import io
import logging

import synapse.axon as s_axon
import synapse.common as s_common
import synapse.neuron as s_neuron
#import synapse.daemon as s_daemon
#import synapse.telepath as s_telepath

#import synapse.lib.tufo as s_tufo
#import synapse.lib.service as s_service
import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

asdfmd5 = hashlib.md5(b'asdfasdf').digest()
asdfsha1 = hashlib.sha1(b'asdfasdf').digest()
asdfsha256 = hashlib.sha256(b'asdfasdf').digest()

logger = logging.getLogger(__name__)

class AxonTest(SynTest):

    def test_axon_base(self):

        with self.getTestDir() as dirn:

            with s_axon.Axon(dirn) as axon:

                self.false(axon.has('md5', asdfmd5))

                iden = axon.wants('sha256', asdfsha256, 8)

                self.nn(iden)
                self.true(axon.chunk(iden, b'asdfasdf'))

                self.true(axon.has('md5', asdfmd5))
                self.true(axon.has('sha256', asdfsha256))

                answ = axon.find('sha256', asdfsha256)
                self.len(1, answ)

                byts = b''.join(axon.iterblob(answ[0]))
                self.eq(b'asdfasdf', byts)

    def test_axon_cell(self):

        with self.getTestDir() as dirn:


            conf = {'user': 'cell@vertex.link', 'host': '127.0.0.1'}

            with s_axon.Axon(dirn, conf) as axon:

                iden = axon.wants('sha256', asdfsha256, 8)
                axon.chunk(iden, b'asdfasdf')

                port = axon.getCellPort()

                auth = axon.genUserAuth('visi@vertex.link')

                user = s_neuron.CellUser(auth)

                addr = ('127.0.0.1', port)

                with user.open(addr, timeout=2) as sess:

                    mesg = ('axon:find', {'name': 'sha256', 'valu': asdfsha256})
                    self.eq(sess.call(mesg, timeout=2), ((8, 8), ))

                    retn = b''

                    mesg = ('axon:blob', {'blob': (8, 8)})
                    for byts in sess.iter(mesg, timeout=2):
                        retn += byts

                    self.eq(retn, b'asdfasdf')
