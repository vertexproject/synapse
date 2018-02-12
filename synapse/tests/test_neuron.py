import random

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
        self._counter += 1
        chan.txfini(data={'mesg': 'pong', 'counter': self._counter})

class NeuronTest(SynTest):

    def test_neuron_cell_base(self):
        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}

            with s_neuron.Cell(dirn, conf) as cell:
                # A bunch of API tests here
                port = cell.getCellPort()
                self.isinstance(port, int)

                auth = cell.genUserAuth('bobgrey@vertex.link')
                self.istufo(auth)

                root = cell.getRootCert()
                self.isinstance(root, s_vault.Cert)

                # We have a default ping handler
                hdlrs = cell.handlers()
                self.isinstance(hdlrs, dict)
                self.isin('cell:ping', hdlrs)

                p1 = cell.getCellPath('hehe.wut')
                p2 = cell.getCellPath('woah', 'dude.txt')
                self.isinstance(p1, str)
                self.isinstance(p2, str)
                self.eq(os.path.relpath(p1, dirn), os.path.join('cell', 'hehe.wut'))
                self.eq(os.path.relpath(p2, dirn), os.path.join('cell', 'woah', 'dude.txt'))
                self.false(os.path.isdir(os.path.join(dirn, 'cell', 'woah')))

                p3 = cell.getCellDir('woah')
                self.eq(os.path.relpath(p3, dirn), os.path.join('cell', 'woah'))
                self.true(os.path.isdir(p3))
                # Demonstrate the use of getCellDict()
                celld = cell.getCellDict('derry:sewers')
                celld.set('float:junction', 'the narrows')
                celld.set('float:place', (None, {'paperboat': 1}))

            with s_neuron.Cell(dirn, conf) as cell:
                # We persist the port if it is not specified in the config
                self.eq(cell.getCellPort(), port)

                # These are largely demonstrative tests
                celld = cell.getCellDict('derry:sewers')
                self.eq(celld.get('float:junction'), 'the narrows')
                self.eq(celld.get('float:place'), (None, {'paperboat': 1}))
                celld.pop('float:place')
                self.none(celld.get('float:place'))

    def test_neuron_locked(self):
        with self.getTestDir() as dirn:
            celldirn = os.path.join(dirn, 'cell')

            port = random.randint(20000, 50000)

            conf = {'host': '127.0.0.1',
                    'port': port,
                    'ctor': 'synapse.neuron.Cell'}
            # lock the cell
            with genfile(celldirn, 'cell.lock') as fd:
                fcntl.lockf(fd, fcntl.LOCK_EX)
                # The cell process should die right away
                proc = s_neuron.divide(celldirn, conf)
                proc.join(30)
                self.false(proc.is_alive())
                self.eq(proc.exitcode, 1)

    def test_neuron_divide(self):
        with self.getTestDir() as dirn:

            celldirn = os.path.join(dirn, 'cell')
            port = random.randint(20000, 50000)

            conf = {'host': '127.0.0.1',
                    'port': port,
                    'ctor': 'synapse.tests.test_neuron.TstCell'}

            # Preload the cell vault
            vdir = os.path.join(celldirn, 'vault.lmdb')
            with s_vault.shared(vdir) as vault:
                auth = vault.genUserAuth('pennywise@vertex.link')

            proc = s_neuron.divide(celldirn, conf)

            with genfile(celldirn, 'cell.lock') as fd:
                self.true(checkLock(fd, 30))

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
                proc.join(30)
                self.false(proc.is_alive())
                self.eq(proc.exitcode, 0)

    def test_neuron_cell_ping(self):

        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}

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

    def test_cell_getcellctor(self):
        with self.getTestDir() as dirn:
            jssave({'ctor': 'synapse.neuron.Cell'}, dirn, 'config.json')

            conf = {'ctor': 'synapse.neuron.Cell'}
            ctor, func = s_neuron.getCellCtor(dirn, conf)
            self.eq(ctor, 'synapse.neuron.Cell')
            self.true(callable(func))

            ctor, func = s_neuron.getCellCtor(dirn, {})
            self.eq(ctor, 'synapse.neuron.Cell')
            self.true(callable(func))

            self.raises(NoSuchCtor, s_neuron.getCellCtor, dirn,
                        {'ctor': 'synapse.neuron.NotACell'})

            jssave({'lolnewp': 'synapse.neuron.Cell'}, dirn, 'config.json')
            self.raises(ReqConfOpt, s_neuron.getCellCtor, dirn, {})

    def test_neuron_cell_authfail(self):
        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}

            c1 = os.path.join(dirn, 'c1')
            c2 = os.path.join(dirn, 'c2')

            with s_neuron.Cell(c1, conf) as cell:
                auth = cell.genUserAuth('bobgrey@vertex.link')

            with s_neuron.Cell(c2, conf) as cell:
                # A bunch of API tests here
                port = cell.getCellPort()
                self.isinstance(port, int)
                user = s_neuron.CellUser(auth)

                addr = ('127.0.0.1', port)

                with self.getLoggerStream('synapse.neuron') as stream:
                    self.raises(CellUserErr, user.open, addr, timeout=1)

                stream.seek(0)
                mesgs = stream.read()
                self.isin('got bad cert', mesgs)

    def test_neuron_cell_notok(self):

        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}

            with s_neuron.Cell(dirn, conf) as cell:

                port = cell.getCellPort()
                auth = cell.genUserAuth('visi@vertex.link')

                user = s_neuron.CellUser(auth)
                addr = ('127.0.0.1', 0)
                self.raises(CellUserErr, user.open, addr, timeout=1)
                self.raises(CellUserErr, user.open, addr, timeout=-1)
