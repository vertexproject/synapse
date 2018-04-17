import random

import synapse.common as s_common
import synapse.neuron as s_neuron

import synapse.lib.cell as s_cell
import synapse.lib.crypto.vault as s_vault

import synapse.tools.neuron as s_tools_neuron

from synapse.tests.common import *

logger = logging.getLogger(__name__)

class TstCell(s_cell.Cell):

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

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with s_cell.Cell(dirn, conf) as cell:

                auth = cell.getCellAuth()
                self.nn(auth)
                self.isinstance(auth, tuple)
                self.len(2, auth)
                self.eq(auth[0], 'root')
                self.isinstance(auth[1], dict)
                self.isinstance(auth[1].get('cert'), bytes)

    def test_neuron_cell_base(self):

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with s_cell.Cell(dirn, conf) as cell:
                # Ensure making the cell makes auth files
                self.true(os.path.isfile(cell._path('cell.auth')))
                self.true(os.path.isfile(cell._path('user.auth')))

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

            with s_cell.Cell(dirn, conf) as cell:

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
                    'ctor': 'synapse.lib.cell.Cell'}
            # lock the cell
            with genfile(celldirn, 'cell.lock') as fd:
                fcntl.lockf(fd, fcntl.LOCK_EX)
                # The cell process should die right away
                proc = s_cell.divide(celldirn, conf)
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

            proc = s_cell.divide(celldirn, conf)

            with genfile(celldirn, 'cell.lock') as fd:
                self.true(checkLock(fd, 30))

            try:
                # Try connecting to the cell
                user = s_cell.CellUser(auth)
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

    def test_neuron_cell_openlist(self):

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}
            cell = s_cell.Cell(dirn)

            with s_cell.Cell(dirn, conf) as cell:

                user = s_cell.CellUser(cell.genUserAuth('foo'))
                addr = list(cell.getCellAddr())

                with user.open(addr, timeout=2) as sess:
                    with sess.task(('cell:ping', {'data': 'haha'})) as chan:
                        retn = chan.next(timeout=2)
                        self.eq(retn, 'haha')
                    retn = sess.call(('cell:ping', {'data': 'rofl'}), timeout=2)
                    self.eq(retn, 'rofl')

    def test_neuron_cell_ping(self):

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with s_cell.Cell(dirn, conf) as cell:

                user = cell.celluser
                addr = cell.getCellAddr()

                with user.open(addr, timeout=2) as sess:

                    with sess.task(('cell:ping', {'data': 'haha'})) as chan:

                        retn = chan.next(timeout=2)
                        self.eq(retn, 'haha')

                    retn = sess.call(('cell:ping', {'data': 'rofl'}), timeout=2)
                    self.eq(retn, 'rofl')

    def test_cell_getcellctor(self):
        with self.getTestDir() as dirn:

            conf = {'ctor': 'synapse.lib.cell.Cell'}
            jssave(conf, dirn, 'config.json')

            ctor, func = s_cell.getCellCtor(dirn, conf)
            self.eq(ctor, 'synapse.lib.cell.Cell')
            self.true(callable(func))

            ctor, func = s_cell.getCellCtor(dirn, {})
            self.eq(ctor, 'synapse.lib.cell.Cell')
            self.true(callable(func))

            self.raises(NoSuchCtor, s_cell.getCellCtor, dirn,
                        {'ctor': 'synapse.neuron.NotACell'})

            jssave({'lolnewp': 'synapse.lib.cell.Cell'}, dirn, 'config.json')
            self.raises(ReqConfOpt, s_cell.getCellCtor, dirn, {})

    def test_neuron_cell_authfail(self):
        '''
        Make a separate cell dir and make sure it can't connect to the first one
        '''
        with self.getTestDir() as dirn, self.getTestDir() as dirn2:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with s_cell.Cell(dirn, conf) as cell, s_cell.Cell(dirn2) as newp:

                user = s_cell.CellUser(newp.getCellAuth())

                addr = cell.getCellAddr()

                with self.getLoggerStream('synapse.lib.cell') as stream:
                    self.raises(CellUserErr, user.open, addr, timeout=1)

                stream.seek(0)
                mesgs = stream.read()
                self.isin('got bad cert', mesgs)

    def test_neuron_cell_notok(self):

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with s_cell.Cell(dirn, conf) as cell:

                user = s_cell.CellUser(cell.genUserAuth('foo'))

                addr = ('localhost', 1)
                self.raises(CellUserErr, user.open, addr, timeout=1)
                self.raises(CellUserErr, user.open, addr, timeout=-1)

    def test_neuron_double_initiate(self):
        '''
        Have the initiator send the listener two session initiation messages
        '''

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with self.getLoggerStream('synapse.lib.cell', 'ProtoErr') as stream, s_cell.Cell(dirn, conf) as cell:

                user = cell.celluser
                addr = cell.getCellAddr()

                with user.open(addr, timeout=2) as sess:
                    sess._initiateSession()
                    stream.wait(.1)
            stream.seek(0)
            self.isin('ProtoErr', stream.read())

    def test_neuron_wrong_version(self):
        '''
        Have the initiator send the listener a weird version
        '''

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with self.getLoggerStream('synapse.lib.cell', 'incompatible') as stream, s_cell.Cell(dirn, conf) as cell:

                user = cell.celluser
                addr = cell.getCellAddr()

                def bad_version_initiate(sess):
                    sess.link.tx(('helo', {'version': (42, 42), 'ephem_pub': b'', 'cert': b''}))

                with mock.patch('synapse.lib.cell.Sess._initiateSession', bad_version_initiate):
                    self.raises(CellUserErr, user.open, addr, timeout=1)
            stream.seek(0)
            self.isin('incompatible version', stream.read())

    def test_neuron_bad_sequence(self):
        '''
        Have the initiator send the listener a message with the wrong sequence number
        '''

        with self.getTestDir() as dirn:

            conf = {'bind': '127.0.0.1', 'host': 'localhost'}

            with self.getLoggerStream('synapse.lib.cell', 'remote peer') as stream, s_cell.Cell(dirn, conf) as cell:

                user = cell.celluser
                addr = cell.getCellAddr()

                with user.open(addr, timeout=2) as sess:

                    sess.tx('Test message')

                    # hand increment the sequence so we break
                    next(sess._crypter._tx_sn)

                    sess.tx('Test message')
                    stream.wait(.1)

            stream.seek(0)
            log_msgs = stream.read()
            self.isin('out of sequence', log_msgs)

            # Currently this fails due to fini killing the whole socket
            self.isin('Remote peer issued error', log_msgs)

    def test_neuron_neuron(self):

        with self.getTestDir() as dirn:

            steps = self.getTestSteps(('cell:reg',))

            conf = {'host': 'localhost', 'bind': '127.0.0.1', 'port': 0}

            path = s_common.gendir(dirn, 'neuron')

            with s_neuron.Neuron(path, conf) as neur:

                cdef = neur.getConfDef('port')
                self.eq(s_neuron.defport, cdef[1].get('defval'))

                def onreg(mesg):
                    steps.done('cell:reg')

                neur.on('cell:reg', onreg)
                self.eq(neur._genCellName('root'), 'root@localhost')

                path = neur._path('admin.auth')
                auth = s_msgpack.loadfile(path)
                user = s_cell.CellUser(auth)

                pool = s_cell.CellPool(neur.genUserAuth('foo'), neur.getCellAddr())
                pool.neurok.wait(timeout=8)
                self.true(pool.neurok.is_set())

                with user.open(neur.getCellAddr()) as sess:

                    ncli = s_neuron.NeuronClient(sess)

                    auth = ncli.genCellAuth('cell00')
                    path = s_common.gendir(dirn, 'cell')

                    authpath = s_common.genpath(path, 'cell.auth')
                    s_msgpack.dumpfile(auth, authpath)

                    conf = {'host': 'localhost', 'bind': '127.0.0.1'}

                    with s_cell.Cell(path, conf) as cell:

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
                        self.eq(info['type'], 'synapse.lib.cell.Cell')

                        self.eq(info.get('addr'), cell.getCellAddr())

                    # he'll come up on a new port...
                    with s_cell.Cell(path, conf) as cell:

                        wait = pool.waiter(1, 'cell:add')

                        steps.wait('cell:reg', timeout=3)
                        steps.clear('cell:reg')

                        self.nn(wait.wait(timeout=3))
                        self.nn(pool.get('cell00@localhost'))

                        mesg = ('cell:ping', {'data': 'hehe'})
                        self.eq(pool.get('cell00@localhost').call(mesg), 'hehe')

                # since we have an active neuron, lets test the CLI tools here as well...
                authpath = os.path.join(dirn, 'neuron', 'admin.auth')
                savepath = os.path.join(dirn, 'woot.auth')

                argv = ['genauth', authpath, 'woot', savepath]
                outp = self.getTestOutp()

                s_tools_neuron.main(argv, outp=outp)

                self.true(outp.expect('saved woot'))
                self.true(outp.expect('woot.auth'))

                auth = s_msgpack.loadfile(savepath)

                self.eq(auth[0], 'woot@localhost')
                self.nn(auth[1].get('neuron'))

                # Use wootauth for provisioning a test cell

                steps.clear('cell:reg')

                path = gendir(dirn, 'wootcell')

                authpath = s_common.genpath(path, 'cell.auth')
                s_msgpack.dumpfile(auth, authpath)

                conf = {'host': 'localhost', 'bind': '127.0.0.1'}
                with s_cell.Cell(path, conf) as cell:

                    wait = pool.waiter(1, 'cell:add')
                    pool.add('woot@localhost')

                    steps.wait('cell:reg', timeout=3)

                    self.nn(wait.wait(timeout=3))
                    self.nn(pool.get('woot@localhost'))

                    mesg = ('cell:ping', {'data': 'w00t!'})
                    self.eq(pool.get('woot@localhost').call(mesg), 'w00t!')

                pool.fini()
