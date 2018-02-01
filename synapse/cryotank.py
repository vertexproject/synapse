import lmdb
import shutil
import struct
import logging

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.neuron as s_neuron
import synapse.eventbus as s_eventbus

import synapse.lib.msgpack as s_msgpack
import synapse.lib.atomfile as s_atomfile

logger = logging.getLogger(__name__)

class CryoTank(s_eventbus.EventBus):
    '''
    A CryoTank implements a stream of structured data.
    '''
    def __init__(self, dirn, mapsize=1099511627776): # from LMDB docs....
        s_eventbus.EventBus.__init__(self)

        self.path = s_common.gendir(dirn)

        path = s_common.gendir(self.path, 'cryo.lmdb')

        self.lmdb = lmdb.open(path, writemap=True, max_dbs=128)
        self.lmdb.set_mapsize(mapsize)

        self.lmdb_items = self.lmdb.open_db(b'items')
        self.lmdb_metrics = self.lmdb.open_db(b'metrics')

        with self.lmdb.begin() as xact:
            self.items_indx = xact.stat(self.lmdb_items)['entries']
            self.metrics_indx = xact.stat(self.lmdb_metrics)['entries']

        def fini():
            self.lmdb.sync()
            self.lmdb.close()

        self.onfini(fini)

    def puts(self, items):
        '''
        Add the structured data from items to the CryoTank.

        Args:
            items ([obj]): A list of objects to store in the CryoTank.

        Returns:
            (int): The index that the item storage began at.
        '''
        itembyts = [s_msgpack.en(i) for i in items]

        tick = s_common.now()
        bytesize = sum([len(b) for b in itembyts])

        with self.lmdb.begin(db=self.lmdb_items, write=True) as xact:

            retn = self.items_indx

            todo = []
            for byts in itembyts:
                todo.append((struct.pack('>Q', self.items_indx), byts))
                self.items_indx += 1

            with xact.cursor() as curs:
                curs.putmulti(todo, append=True)

            took = s_common.now() - tick

            with xact.cursor(db=self.lmdb_metrics) as curs:

                lkey = struct.pack('>Q', self.metrics_indx)
                self.metrics_indx += 1

                info = {'time': tick, 'count': len(items), 'size': bytesize, 'took': took}
                curs.put(lkey, s_msgpack.en(info), append=True)

        return retn

    def metrics(self, offs, size):
        '''
        Retrieve size metrics rows starting at offset.

        Args:
            offs (int): The index offset.
            size (int): The number to retrieve.

        Yields:
            (int,dict): An (index, info) metrics entry.
        '''
        imax = offs + size
        mink = struct.pack('>Q', offs)

        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_metrics) as curs:

                if not curs.set_range(mink):
                    return

                for lkey, lval in curs:

                    indx = struct.unpack('>Q', lkey)[0]
                    if indx >= imax:
                        break

                    yield indx, s_msgpack.un(lval)

    def slice(self, offs, size):
        '''
        Return size data items from the given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Yields:
            (indx, item): Index and item values.
        '''
        lmin = struct.pack('>Q', offs)
        imax = offs + size

        # time slice the items from the cryo tank
        #with self.lmdb.begin(buffers=True) as xact:
        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_items) as curs:

                if not curs.set_range(lmin):
                    return

                for lkey, lval in curs:

                    indx = struct.unpack('>Q', lkey)[0]
                    if indx >= imax:
                        break

                    yield indx, s_msgpack.un(lval)

    def rows(self, offs, size):
        '''
        Yield raw (indx, byts) values for the given range.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Yields:
            (indx, item): Index and item values.
        '''
        lmin = struct.pack('>Q', offs)
        imax = offs + size

        # time slice the items from the cryo tank
        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_items) as curs:

                if not curs.set_range(lmin):
                    return

                for lkey, lval in curs:

                    indx = struct.unpack('>Q', lkey)[0]
                    if indx >= imax:
                        break

                    yield indx, lval

    def info(self):
        '''
        '''
        return {'indx': self.items_indx}

class CryoCell(s_neuron.Cell):

    def __init__(self, dirn, conf=None):

        s_neuron.Cell.__init__(self, dirn, conf=conf)

        self.names = self.getCellDict('cryo:names')

        self.tanks = s_eventbus.BusRef()

        for name, iden in self.names.items():
            path = self.getCellPath('tanks', iden)
            tank = CryoTank(path)
            self.tanks.put(name, tank)

    def genCryoTank(self, name):

        tank = self.tanks.get(name)
        if tank is not None:
            return tank

        iden = s_common.guid()
        self.names.set(name, iden)

        logger.info('CryoCell: creating new tank: %s' % (name,))

        path = self.getCellPath('tanks', iden)

        tank = CryoTank(path)

        self.tanks.put(name, tank)
        return tank

    def getCryoList(self):
        '''
        Return a list of (name, info) tuples for the CryoTanks.
        '''
        return [(name, tank.info()) for (name, tank) in self.tanks.items()]

    def handlers(self):
        return {
            'cryo:list': self._onCryoList,
            'cryo:puts': self._onCryoPuts,
            'cryo:dele': self._onCryoDele,
            'cryo:metrics': self._onCryoMetrics,
        }

    def _onCryoList(self, chan, mesg):
        chan.txfini(self.getCryoList())

    def _onCryoDele(self, chan, mesg):

        name = mesg[1].get('name')

        tank = self.tanks.pop(name)
        if tank is None:
            return chan.txfini(False)

        self.names.pop(name)

        tank.fini()

        shutil.rmtree(tempdir, ignore_errors=True)
        return chan.txfini(True)

    @s_glob.inpool
    def _onCryoMetrics(self, chan, mesg):
        name = mesg[1].get('name')
        offs = mesg[1].get('offs')
        size = mesg[1].get('size')

        tank = self.tanks.get(name)
        if tank is None:
            return chan.txfini()

        metr = list(tank.metrics(offs, size))
        chan.txfini(metr)

    @s_glob.inpool
    def _onCryoPuts(self, chan, mesg):

        name = mesg[1].get('name')
        items = mesg[1].get('items')

        chan.setq()

        with chan:

            tank = self.genCryoTank(name)

            if items is not None:
                chan.tx(tank.puts(items))

            items = chan.next(timeout=30)
            if items is None:
                return

            chan.tx(tank.puts(items))

class CryoUser(s_neuron.CellUser):

    def __init__(self, auth, addr, timeout=None):

        s_neuron.CellUser.__init__(self, auth)

        self._cryo_sess = self.open(addr, timeout=timeout)
        if self._cryo_sess is None:
            raise s_exc.HitMaxTime(timeout=timeout)

    def puts(self, name, items, timeout=None):
        '''
        Add data to the named remote CryoTank by consuming from items.

        Args:
            name (str): The name of the remote CryoTank.
            items (iter): An iterable of data items to load.
            timeout (float/int): The maximum timeout for an ack.
        '''
        retn = 0
        with self._cryo_sess.task(('cryo:puts', {'name': name})) as chan:

            for i, chun in enumerate(s_common.chunks(items, 10000)):

                chan.tx(chun)

                resp = chan.next(timeout=timeout)
                if resp is None:
                    raise s_exc.LinkTimeOut(timeout=timeout)

    def list(self, timeout=None):
        '''
        Return a list of (name, info) tuples for the remote CryoTanks.
        '''
        return self._cryo_sess.call(('cryo:list', {}), timeout=timeout)

    def metrics(self, name, offs, size, timeout=None):
        '''
        Carve a slice of metrics data from the named CryoTank.
        ( see CryoTank.metrics )
        '''
        mesg = ('cryo:metrics', {'name': name, 'offs': offs, 'size': size})
        return self._cryo_sess.call(mesg, timeout=timeout)
