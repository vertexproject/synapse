import synapse.neuron as s_neuron

import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

class NeuronTest(SynTest):

    def test_cell_ping(self):

        with self.getTestDir() as dirn:

            conf = {'user': 'cell@vertex.link', 'host': '127.0.0.1'}

            with s_neuron.Cell(dirn, conf) as cell:

                port = cell.getCellPort()

                auth = cell.genUserAuth('visi@vertex.link')

                user = s_neuron.CellUser(auth)

                addr = ('127.0.0.1', port)

                with user.open(addr, timeout=2) as sess:

                    with sess.task(('cell:ping', {'data': 'haha'})) as chan:

                        retn = chan.next(timeout=2)
                        self.eq(retn, 'haha')

                    retn = sess.call(('cell:ping', {'data': 'rofl'}), timeout=2)
                    self.eq(retn, 'rofl')
