import lmdb
import shutil
import struct
import logging

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.cell as s_cell
import synapse.lib.const as s_const
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

class CryoTank(s_config.Config):
    '''
    A CryoTank implements a stream of structured data.
    '''
    def __init__(self, dirn, conf=None):
        s_config.Config.__init__(self, conf)

        self.path = s_common.gendir(dirn)

        path = s_common.gendir(self.path, 'cryo.lmdb')

        mapsize = self.getConfOpt('mapsize')
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

    @staticmethod
    @s_config.confdef(name='cryotank')
    def _crytotank_confdefs():
        defs = (
            # from LMDB docs
            ('mapsize', {'type': 'int', 'doc': 'LMDB Mapsize value', 'defval': s_const.tebibyte}),
        )
        return defs

    def last(self):
        '''
        Return the last item stored in this CryoTank.
        '''
        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_items) as curs:

                if not curs.last():
                    return None

                indx = struct.unpack('>Q', curs.key())[0]
                return indx, s_msgpack.un(curs.value())

    def puts(self, items):
        '''
        Add the structured data from items to the CryoTank.

        Args:
            items (list):  A list of objects to store in the CryoTank.

        Returns:
            int: The index that the item storage began at.
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

    def metrics(self, offs, size=None):
        '''
        Yield metrics rows starting at offset.

        Args:
            offs (int): The index offset.
            size (int): The maximum number of records to yield.

        Yields:
            ((int, dict)): An index offset, info tuple for metrics.
        '''
        mink = struct.pack('>Q', offs)

        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_metrics) as curs:

                if not curs.set_range(mink):
                    return

                for i, (lkey, lval) in enumerate(curs):

                    if size is not None and i >= size:
                        return

                    indx = struct.unpack('>Q', lkey)[0]
                    item = s_msgpack.un(lval)

                    yield indx, item

    def slice(self, offs, size):
        '''
        Yield a number of items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Notes:
            This API performs msgpack unpacking on the bytes, and could be
            slow to call remotely.

        Yields:
            ((index, object)): Index and item values.
        '''
        lmin = struct.pack('>Q', offs)

        with self.lmdb.begin() as xact:

            with xact.cursor(db=self.lmdb_items) as curs:

                if not curs.set_range(lmin):
                    return

                for i, (lkey, lval) in enumerate(curs):

                    if i >= size:
                        return

                    indx = struct.unpack('>Q', lkey)[0]
                    yield indx, s_msgpack.un(lval)

    def rows(self, offs, size):
        '''
        Yield a number of raw items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Yields:
            ((indx, bytes)): Index and msgpacked bytes.
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
        Returns information about the CryoTank instance.

        Returns:
            dict: A dict containing items and metrics indexes.
        '''
        return {'indx': self.items_indx, 'metrics': self.metrics_indx, 'stat': self.lmdb.stat()}

class CryoCell(s_cell.Cell):

    def postCell(self):
        '''
        CryoCell initialization routines.
        '''
        self.names = self.getCellDict('cryo:names')
        self.confs = self.getCellDict('cryo:confs')
        self.tanks = s_eventbus.BusRef()

        for name, iden in self.names.items():
            logger.info('Bringing tank [%s][%s] online', name, iden)
            path = self.getCellPath('tanks', iden)
            conf = self.confs.get(name)
            tank = CryoTank(path, conf)
            self.tanks.put(name, tank)

    def finiCell(self):
        '''
        Fini handlers for the CryoCell
        '''
        self.tanks.fini()

    def handlers(self):
        '''
        CryoCell message handlers.
        '''
        return {
            'cryo:init': self._onCryoInit,
            'cryo:list': self._onCryoList,
            'cryo:last': self._onCryoLast,
            'cryo:puts': self._onCryoPuts,
            'cryo:dele': self._onCryoDele,
            'cryo:rows': self._onCryoRows,
            'cryo:slice': self._onCryoSlice,
            'cryo:metrics': self._onCryoMetrics,
        }

    def genCryoTank(self, name, conf=None):
        '''
        Generate a new CryoTank with a given name or get an reference to an existing CryoTank.

        Args:
            name (str): Name of the CryoTank.

        Returns:
            CryoTank: A CryoTank instance.
        '''
        tank = self.tanks.get(name)
        if tank is not None:
            return tank

        iden = s_common.guid()

        logger.info('Creating new tank: %s', name)

        path = self.getCellPath('tanks', iden)
        tank = CryoTank(path, conf)

        self.names.set(name, iden)
        self.confs.set(name, conf)
        self.tanks.put(name, tank)
        return tank

    def getCryoList(self):
        '''
        Get a list of (name, info) tuples for the CryoTanks.

        Returns:
            list: A list of tufos.
        '''
        return [(name, tank.info()) for (name, tank) in self.tanks.items()]

    def _onCryoLast(self, chan, mesg):

        name = mesg[1].get('name')

        with chan:

            tank = self.tanks.get(name)
            if tank is None:
                return chan.txfini(None)

            return chan.txfini(tank.last())

    def _onCryoList(self, chan, mesg):
        chan.txfini((True, self.getCryoList()))

    @s_glob.inpool
    def _onCryoDele(self, chan, mesg):

        name = mesg[1].get('name')

        logger.info('Deleting tank: %s' % (name,))

        tank = self.tanks.pop(name)  # type: CryoTank
        if tank is None:
            return chan.txfini(False)

        self.names.pop(name)

        tank.fini()
        shutil.rmtree(tank.path, ignore_errors=True)
        return chan.txfini(True)

    @s_glob.inpool
    def _onCryoSlice(self, chan, mesg):

        name = mesg[1].get('name')
        offs = mesg[1].get('offs')
        size = mesg[1].get('size')

        with chan:

            tank = self.tanks.get(name)
            if tank is None:
                return chan.tx((False, ('NoSuchName', {'name': name})))

            chan.setq()
            chan.tx((True, True))

            genr = tank.slice(offs, size)
            genr = s_common.chunks(genr, 100)

            # 100 chunks of 100 in flight...
            chan.txwind(genr, 100, timeout=30)

    @s_glob.inpool
    def _onCryoRows(self, chan, mesg):

        name = mesg[1].get('name')
        offs = mesg[1].get('offs')
        size = mesg[1].get('size')

        with chan:

            tank = self.tanks.get(name)
            if tank is None:
                return chan.tx((False, ('NoSuchName', {'name': name})))

            chan.setq()
            chan.tx((True, True))

            rows = tank.rows(offs, size=size)
            genr = s_common.chunks(rows, 1000)

            chan.txwind(genr, 100, timeout=30)

    @s_glob.inpool
    def _onCryoMetrics(self, chan, mesg):
        name = mesg[1].get('name')
        offs = mesg[1].get('offs')
        size = mesg[1].get('size')

        with chan:

            tank = self.tanks.get(name)
            if tank is None:
                return chan.txfini((False, ('NoSuchName', {'name': name})))

            chan.setq()
            chan.tx((True, True))

            metr = tank.metrics(offs, size=size)

            genr = s_common.chunks(metr, 1000)
            chan.txwind(genr, 100, timeout=30)

    @s_glob.inpool
    def _onCryoPuts(self, chan, mesg):

        name = mesg[1].get('name')

        chan.setq()
        chan.tx(True)

        with chan:

            size = 0
            tank = self.genCryoTank(name)
            for items in chan.rxwind(timeout=30):
                tank.puts(items)
                size += len(items)

            chan.txok(size)

    @s_glob.inpool
    def _onCryoInit(self, chan, mesg):
        name = mesg[1].get('name')
        conf = mesg[1].get('conf')

        with chan:

            tank = self.tanks.get(name)
            if tank:
                return chan.tx((True, False))

            try:
                self.genCryoTank(name, conf)
                return chan.tx((True, True))

            except Exception as e:
                retn = s_common.getexcfo(e)
                return chan.tx((False, retn))

class CryoClient:
    '''
    Client-side helper for interacting with a CryoCell which hosts CryoTanks.

    Args:
        auth ((str, dict)): A user auth tufo
        addr ((str, int)): The address / port tuple.
        timeout (int): Connect timeout
    '''
    _chunksize = 10000
    def __init__(self, sess):
        self.sess = sess

    def puts(self, name, items, timeout=None):
        '''
        Add data to the named remote CryoTank by consuming from items.

        Args:
            name (str): The name of the remote CryoTank.
            items (iter): An iterable of data items to load.
            timeout (float/int): The maximum timeout for an ack.

        Returns:
            None
        '''
        with self.sess.task(('cryo:puts', {'name': name})) as chan:

            if not chan.next(timeout=timeout):
                return False

            genr = s_common.chunks(items, self._chunksize)
            chan.txwind(genr, 100, timeout=timeout)
            return chan.next(timeout=timeout)

    def last(self, name, timeout=None):
        '''
        Return the last entry in the named CryoTank.

        Args:
            name (str): The name of the remote CryoTank.
            timeout (int): Request timeout

        Returns:
            ((int, object)): The last entry index and object from the CryoTank.
        '''
        return self.sess.call(('cryo:last', {'name': name}), timeout=timeout)

    def delete(self, name, timeout=None):
        '''
        Delete a named CryoTank.

        Args:
            name (str): The name of the remote CryoTank.
            timeout (int): Request timeout

        Returns:
            bool: True if the CryoTank was deleted, False if it was not deleted.
        '''
        return self.sess.call(('cryo:dele', {'name': name}), timeout=timeout)

    def list(self, timeout=None):
        '''
        Get a list of the remote CryoTanks.

        Args:
            timeout (int): Request timeout

        Returns:
            tuple: A tuple containing name, info tufos for the remote CryoTanks.
        '''
        ok, retn = self.sess.call(('cryo:list', {}), timeout=timeout)
        return s_common.reqok(ok, retn)

    def slice(self, name, offs, size, timeout=None):
        '''
        Slice and return a section from the named CryoTank.

        Args:
            name (str): The name of the remote CryoTank.
            offs (int): The offset to begin the slice.
            size (int): The number of records to slice.
            timeout (int): Request timeout

        Yields:
            (int, obj): (indx, item) tuples for the sliced range.
        '''
        mesg = ('cryo:slice', {'name': name, 'offs': offs, 'size': size})
        with self.sess.task(mesg, timeout=timeout) as chan:

            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)

            for bloc in chan.rxwind(timeout=timeout):
                for item in bloc:
                    yield item

    def rows(self, name, offs, size, timeout=None):
        '''
        Retrive raw rows from a section of the named CryoTank.

        Args:
            name (str): The name of the remote CryoTank.
            offs (int): The offset to begin the row retrieval from.
            size (int): The number of records to retrieve.
            timeout (int): Request timeout.

        Notes:
            This returns msgpack encoded records. It is the callers
            responsibility to decode them.

        Yields:
            (int, bytes): (indx, bytes) tuples for the rows in range.
        '''
        mesg = ('cryo:rows', {'name': name, 'offs': offs, 'size': size})
        with self.sess.task(mesg, timeout=timeout) as chan:

            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)

            for bloc in chan.rxwind(timeout=timeout):
                for item in bloc:
                    yield item

    def metrics(self, name, offs, size=None, timeout=None):
        '''
        Carve a slice of metrics data from the named CryoTank.

        Args:
            name (str): The name of the remote CryoTank.
            offs (int): The index offset.
            timeout (int): Request timeout

        Returns:
            tuple: A tuple containing metrics tufos for the named CryoTank.
        '''
        mesg = ('cryo:metrics', {'name': name, 'offs': offs, 'size': size})
        with self.sess.task(mesg, timeout=timeout) as chan:

            ok, retn = chan.next(timeout=timeout)
            s_common.reqok(ok, retn)

            for bloc in chan.rxwind(timeout=timeout):
                for item in bloc:
                    yield item

    def init(self, name, conf=None, timeout=None):
        '''
        Create a new named Cryotank.

        Args:
            name (str): Name of the Cryotank to make.
            conf (dict): Additional configable options for the Cryotank.
            timeout (int): Request timeout

        Returns:
            True if the tank was created, False if the tank existed or
            there was an error during CryoTank creation.
        '''
        mesg = ('cryo:init', {'name': name, 'conf': conf})
        ok, retn = self.sess.call(mesg, timeout=timeout)
        return s_common.reqok(ok, retn)
