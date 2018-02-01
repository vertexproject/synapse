import random
import multiprocessing

import synapse.neuron as s_neuron

import synapse.lib.crypto.vault as s_vault

from synapse.tests.common import *

logger = logging.getLogger(__name__)

class TstCell(s_neuron.Cell):

    def postCell(self):
        self._counter = 0

    def handlers(self):
        return {
            'cell:ping': self._onCellPing,
            'cell:pong': self._onCellPong,
        }

    def _onCellPong(self, chan, mesg):
        self._counter = self._counter + 1
        chan.txfini(data={'mesg': 'pong', 'counter': self._counter})

def checkLock(fd, timeout, wait=0.1):
    wtime = 0

    if timeout < 0:
        raise ValueError('timeout must be > 0')

    while True:
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            if e.errno == 11:
                return True
            logger.exception('Error obtaining lock')
        else:
            fcntl.lockf(fd, fcntl.LOCK_UN)
        time.sleep(wait)
        wtime = wait + wtime
        if wtime >= timeout:
            return False

class NeuronTest(SynTest):

    def test_neuron_divide(self):
        with self.getTestDir() as dirn:

            celldirn = os.path.join(dirn, 'cell')
            userdirn = os.path.join(dirn, 'user')
            port = random.randint(20000, 50000)

            conf = {'user': 'cell@vertex.link',
                    'host': '127.0.0.1',
                    'port': port,
                    'ctor': 'synapse.tests.test_neuron.TstCell'}

            # Preload the cell vault
            vdir = os.path.join(celldirn, 'vault.lmdb')
            with s_vault.shared(vdir) as vault:
                auth = vault.genUserAuth('pennywise@vertex.link')

            proc = s_neuron.divide(celldirn, conf)

            # time.sleep(6)
            with genfile(celldirn, 'cell.lock') as fd:
                self.true(checkLock(fd, 10))

            try:
                # Try connecting to the cell
                user = s_neuron.CellUser(auth)
                addr = ('127.0.0.1', port)

                with user.open(addr, timeout=10) as sess:

                    with sess.task(('cell:ping', {'data': 'haha'})) as chan:
                        retn = chan.next(timeout=2)
                        self.eq(retn, 'haha')

                    retn = sess.call(('cell:ping', {'data': 'rofl'}), timeout=2)
                    self.eq(retn, 'rofl')

                    retn = sess.call(('cell:pong', {'data': 'rofl'}), timeout=2)
                    self.eq(retn, {'mesg': 'pong', 'counter': 1})

                    retn = sess.call(('cell:pong', {'data': 'rofl'}), timeout=2)
                    self.eq(retn, {'mesg': 'pong', 'counter': 2})

            except Exception as e:
                logger.exception('Error during test!')
                # Clean up the proc
                proc.terminate()
                proc.join(1)
                raise

            else:
                time.sleep(0.01)
                proc.terminate()
                proc.join(1)
                self.false(proc.is_alive())

    def test_neuron_cell_ping(self):

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
