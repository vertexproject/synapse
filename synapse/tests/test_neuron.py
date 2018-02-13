import random

import synapse.common as s_common
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

    def test_neuron_cell_cellAuth(self):
        with self.getTestDir() as dirn:

            conf = {'host': '127.0.0.1'}

            with s_neuron.Cell(dirn, conf) as cell:
                auth = cell.getCellAuth()
                self.nn(auth)
                self.isinstance(auth, tuple)
                self.len(2, auth)
                self.eq(auth[0], 'user')
                self.isinstance(auth[1], dict)
                self.isinstance(auth[1].get('cert'), bytes)

    def test_neuron_cell_base(self):

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            initCellDir(dirn)

            with s_neuron.Cell(dirn, conf) as cell:
                # A bunch of API tests here

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

            conf = {'bind': '127.0.0.1',
                    'port': port,
                    'host': 'localhost',
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
            # FIXME: this could randomly fail if the port is in use!
            port = random.randint(20000, 50000)

            conf = {'bind': '127.0.0.1',
                    'port': port,
                    'host': 'localhost',
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

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            initCellDir(dirn)
            rootauth, userauth = getCellAuth()

            with s_neuron.Cell(dirn, conf) as cell:

                user = s_neuron.CellUser(userauth)

                addr = cell.getCellAddr()

                with user.open(addr, timeout=2) as sess:

                    with sess.task(('cell:ping', {'data': 'haha'})) as chan:

                        retn = chan.next(timeout=2)
                        self.eq(retn, 'haha')

                    retn = sess.call(('cell:ping', {'data': 'rofl'}), timeout=2)
                    self.eq(retn, 'rofl')

    def test_cell_getcellctor(self):
        with self.getTestDir() as dirn:

            conf = {'ctor': 'synapse.neuron.Cell'}
            jssave(conf, dirn, 'config.json')

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

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            newp = s_msgpack.loadfile(getTestPath('files', 'newp.auth'))

            initCellDir(dirn)

            with s_neuron.Cell(dirn, conf) as cell:

                user = s_neuron.CellUser(newp)

                addr = cell.getCellAddr()

                with self.getLoggerStream('synapse.neuron') as stream:
                    self.raises(CellUserErr, user.open, addr, timeout=1)

                stream.seek(0)
                mesgs = stream.read()
                self.isin('got bad cert', mesgs)

    def test_neuron_cell_notok(self):

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            initCellDir(dirn)
            rootauth, userauth = getCellAuth()

            with s_neuron.Cell(dirn, conf) as cell:

                user = s_neuron.CellUser(userauth)

                addr = ('localhost', 1)
                self.raises(CellUserErr, user.open, addr, timeout=1)
                self.raises(CellUserErr, user.open, addr, timeout=-1)

    def test_neuron_neuron(self):

        with self.getTestDir() as dirn:

            steps = self.getTestSteps(('cell:reg',))

            conf = {'host': 'localhost', 'bind': '127.0.0.1', 'port': 0}

            path = s_common.gendir(dirn, 'neuron')

            with s_neuron.Neuron(path, conf) as neur:

                path = s_common.genpath(path, 'cell.auth')
                root = s_msgpack.loadfile(path)

                def onreg(mesg):
                    steps.done('cell:reg')

                neur.on('cell:reg', onreg)
                self.eq(neur._genCellName('root'), 'root@localhost')

                user = s_neuron.CellUser(root)

                pool = s_neuron.CellPool(root, neur.getCellAddr())
                pool.neurok.wait(timeout=8)
                self.true(pool.neurok.is_set())

                with user.open(neur.getCellAddr()) as sess:

                    mesg = ('cell:init', {'name': 'cell00'})
                    ok, auth = sess.call(mesg, timeout=2)
                    self.true(ok)

                    path = s_common.gendir(dirn, 'cell')

                    authpath = s_common.genpath(path, 'cell.auth')
                    s_msgpack.dumpfile(auth, authpath)

                    conf = {'host': 'localhost', 'bind': '127.0.0.1'}

                    with s_neuron.Cell(path, conf) as cell:

                        steps.wait('cell:reg', timeout=3)
                        steps.clear('cell:reg')

                        # we should be able to get a session to him in the pool...
                        wait = pool.waiter(1, 'cell:add')
                        pool.add('cell00@localhost')

                        self.nn(wait.wait(timeout=3))
                        self.nn(pool.get('cell00@localhost'))

                        ok, cells = sess.call(('cell:list', {}))
                        self.true(ok)

                        self.eq(cells[0][0], 'cell00@localhost')

                        ok, info = sess.call(('cell:get', {'name': 'cell00@localhost'}))
                        self.true(ok)

                        self.eq(info.get('addr'), cell.getCellAddr())

                    # he'll come up on a new port...
                    with s_neuron.Cell(path, conf) as cell:

                        wait = pool.waiter(1, 'cell:add')

                        steps.wait('cell:reg', timeout=3)

                        self.nn(wait.wait(timeout=3))
                        self.nn(pool.get('cell00@localhost'))

                        mesg = ('cell:ping', {'data': 'hehe'})
                        self.eq(pool.get('cell00@localhost').call(mesg), 'hehe')
