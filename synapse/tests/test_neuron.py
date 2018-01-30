import synapse.neuron as s_neuron

import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

class NeuronTest(SynTest):

    def test_cell_ping(self):

        with self.getTestDir() as dirn:

            celldirn = os.path.join(dirn, 'cell')
            userdirn = os.path.join(dirn, 'user')

            conf = {'user': 'cell@vertex.link', 'host': '127.0.0.1'}

            with s_neuron.Cell(celldirn, conf) as cell:

                port = cell.getCellPort()

                root = cell.genRootCert()
                auth = cell.genUserAuth('visi@vertex.link')

                with s_vault.shared(userdirn) as vault:
                    vault.addRootCert(root)
                    vault.addUserAuth(auth)

                user = s_neuron.CellUser('visi@vertex.link', path=userdirn)

                addr = ('127.0.0.1', port)

                with user.open(addr, timeout=2) as sess:

                    with sess.task(('cell:ping', {'data': 'haha'})) as chan:

                        mesg = chan.next(timeout=2)

                        self.nn(mesg)

                        self.eq('retn', mesg[0])
                        self.eq('haha', mesg[1].get('data'))
