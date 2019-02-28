import os
import shutil
import struct
import asyncio
import logging

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common

import synapse.lib.kv as s_kv
import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

logger = logging.getLogger(__name__)

class TankApi(s_cell.CellApi):

    async def slice(self, size, offs, iden=None):
        async for item in self.cell.slice(size, offs, iden=iden):
            yield item

    async def puts(self, items, seqn=None):
        return await self.cell.puts(items, seqn=seqn)

    async def metrics(self, offs, size=None):
        async for item in self.cell.metrics(offs, size=size):
            yield item

    async def offset(self, iden):
        return self.cell.getOffset(iden)

    def iden(self):
        return self.cell.iden()

class CryoTank(s_base.Base):
    '''
    A CryoTank implements a stream of structured data.
    '''
    async def __anit__(self, dirn, conf=None):

        await s_base.Base.__anit__(self)

        self.dirn = s_common.gendir(dirn)

        if conf is not None:
            self.conf.update(conf)

        self._iden = self._getTankIden()

        path = s_common.gendir(self.dirn, 'tank.lmdb')

        self.slab = await s_lmdbslab.Slab.anit(path)

        self.offs = s_lmdbslab.Offs(self.slab, 'offsets')

        self._items = s_slabseqn.SlabSeqn(self.slab, 'items')
        self._metrics = s_slabseqn.SlabSeqn(self.slab, 'metrics')

        self.onfini(self.slab.fini)

    def iden(self):
        return self._iden

    def _getTankIden(self):

        path = s_common.genpath(self.dirn, 'guid')
        if os.path.isfile(path):
            with open(path, 'r') as fd:
                return fd.read().strip()

        # legacy cell code...
        cellpath = s_common.genpath(self.dirn, 'cell.guid')
        if os.path.isfile(cellpath):

            with open(cellpath, 'r') as fd:
                iden = fd.read().strip()

            with open(path, 'w') as fd:
                fd.write(iden)

            os.unlink(cellpath)
            return iden

        iden = s_common.guid()
        with open(path, 'w') as fd:
            fd.write(iden)

        return iden

    def getOffset(self, iden):
        return self.offs.get(iden)

    def setOffset(self, iden, offs):
        return self.offs.set(iden, offs)

    def last(self):
        '''
        Return an (offset, item) tuple for the last element in the tank ( or None ).
        '''
        return self._items.last()

    async def puts(self, items, seqn=None):
        '''
        Add the structured data from items to the CryoTank.

        Args:
            items (list):  A list of objects to store in the CryoTank.
            seqn (iden, offs): An iden / offset pair to record.

        Returns:
            int: The ending offset of the items or seqn.
        '''
        size = 0

        for chunk in s_common.chunks(items, 1000):
            metrics = self._items.save(chunk)
            self._metrics.add(metrics)
            await self.fire('cryotank:puts', numrecords=len(chunk))
            size += len(chunk)
            await asyncio.sleep(0)

        if seqn is not None:
            iden, offs = seqn
            self.setOffset(iden, offs + size)

        return size

    async def metrics(self, offs, size=None):
        '''
        Yield metrics rows starting at offset.

        Args:
            offs (int): The index offset.
            size (int): The maximum number of records to yield.

        Yields:
            ((int, dict)): An index offset, info tuple for metrics.
        '''
        for i, (indx, item) in enumerate(self._metrics.iter(offs)):

            if size is not None and i >= size:
                return

            yield indx, item

    async def slice(self, offs, size=None, iden=None):
        '''
        Yield a number of items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Yields:
            ((index, object)): Index and item values.
        '''
        if iden is not None:
            self.setOffset(iden, offs)

        for i, (indx, item) in enumerate(self._items.iter(offs)):

            if size is not None and i >= size:
                return

            yield indx, item

    async def rows(self, offs, size=None, iden=None):
        '''
        Yield a number of raw items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Yields:
            ((indx, bytes)): Index and msgpacked bytes.
        '''
        if iden is not None:
            self.setOffset(iden, offs)

        for i, (indx, byts) in enumerate(self._items.rows(offs)):

            if size is not None and i >= size:
                return

            yield indx, byts

    async def info(self):
        '''
        Returns information about the CryoTank instance.

        Returns:
            dict: A dict containing items and metrics indexes.
        '''
        stat = self._items.stat()
        return {'indx': self._items.index(), 'metrics': self._metrics.index(), 'stat': stat}

class CryoApi(s_cell.CellApi):
    '''
    The CryoCell API as seen by a telepath proxy.

    This is the API to reference for remote CryoCell use.
    '''
    async def init(self, name, conf=None):
        await self.cell.init(name, conf=conf)
        return True

    async def slice(self, name, offs, size, iden=None):
        tank = await self.cell.init(name)
        async for item in tank.slice(offs, size, iden=iden):
            yield item

    async def list(self):
        return await self.cell.list()

    async def last(self, name):
        tank = await self.cell.init(name)
        return tank.last()

    async def puts(self, name, items, seqn=None):
        tank = await self.cell.init(name)
        return await tank.puts(items, seqn=seqn)

    async def offset(self, name, iden):
        tank = await self.cell.init(name)
        return tank.getOffset(iden)

    async def rows(self, name, offs, size, iden=None):
        tank = await self.cell.init(name)
        async for item in tank.rows(offs, size, iden=iden):
            yield item

    async def metrics(self, name, offs, size=None):
        tank = await self.cell.init(name)
        async for item in tank.metrics(offs, size=size):
            yield item

    @s_cell.adminapi
    async def delete(self, name):
        return self.cell.delete(name)

class CryoCell(s_cell.Cell):

    cellapi = CryoApi

    confdefs = ()

    async def __anit__(self, dirn):

        await s_cell.Cell.__anit__(self, dirn)

        self.dmon.share('cryo', self)

        path = s_common.gendir(self.dirn, 'cryo.lmdb')

        self.kvstor = s_kv.KvStor(path)
        self.onfini(self.kvstor.fini)

        self.names = self.kvstor.getKvDict('cryo:names')
        self.confs = self.kvstor.getKvDict('cryo:confs')

        self.tanks = await s_base.BaseRef.anit()
        self.onfini(self.tanks.fini)

        for name, iden in self.names.items():

            logger.info('Bringing tank [%s][%s] online', name, iden)

            path = s_common.genpath(self.dirn, 'tanks', iden)

            conf = self.confs.get(name)
            tank = await CryoTank.anit(path, conf)
            self.tanks.put(name, tank)

    async def getCellApi(self, link, user, path):

        if not path:
            return await CryoApi.anit(self, link, user)

        if len(path) == 1:
            tank = await self.init(path[0])
            return await TankApi.anit(tank, link, user)

        raise s_exc.NoSuchPath(path=path)

    def getTeleMethInfo(self):
        return {
            'rows': {'genr': True},
            'slice': {'genr': True},
            'metrics': {'genr': True},
        }

    async def init(self, name, conf=None):
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

        path = s_common.genpath(self.dirn, 'tanks', iden)

        tank = await CryoTank.anit(path, conf)

        self.names.set(name, iden)
        self.confs.set(name, conf)
        self.tanks.put(name, tank)

        return tank

    async def list(self):
        '''
        Get a list of (name, info) tuples for the CryoTanks.

        Returns:
            list: A list of tufos.
        '''
        return [(name, await tank.info()) for (name, tank) in self.tanks.items()]

    def delete(self, name):

        tank = self.tanks.pop(name)
        if tank is None:
            return False

        self.names.pop(name)

        tank.fini()
        shutil.rmtree(tank.dirn, ignore_errors=True)

        return True
