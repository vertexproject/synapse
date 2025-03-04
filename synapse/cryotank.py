import os
import shutil
import asyncio
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.schemas as s_schemas
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn
import synapse.lib.slaboffs as s_slaboffs

logger = logging.getLogger(__name__)

class TankApi(s_cell.CellApi):

    async def slice(self, offs, size=None, wait=False, timeout=None):
        self.user.confirm(('cryo', 'tank', 'read'), gateiden=self.cell.iden())
        async for item in self.cell.slice(offs, size=size, wait=wait, timeout=timeout):
            yield item

    async def puts(self, items):
        self.user.confirm(('cryo', 'tank', 'put'), gateiden=self.cell.iden())
        return await self.cell.puts(items)

    async def metrics(self, offs, size=None):
        self.user.confirm(('cryo', 'tank', 'read'), gateiden=self.cell.iden())
        async for item in self.cell.metrics(offs, size=size):
            yield item

    async def iden(self):
        return self.cell.iden()

class CryoTank(s_base.Base):
    '''
    A CryoTank implements a stream of structured data.
    '''
    async def __anit__(self, dirn, iden, conf=None):

        await s_base.Base.__anit__(self)

        if conf is None:
            conf = {}

        self.conf = conf
        self.dirn = s_common.gendir(dirn)

        self._iden = iden

        path = s_common.gendir(self.dirn, 'tank.lmdb')

        self.slab = await s_lmdbslab.Slab.anit(path, map_async=True, **conf)

        self._items = s_slabseqn.SlabSeqn(self.slab, 'items')
        self._metrics = s_slabseqn.SlabSeqn(self.slab, 'metrics')

        self.onfini(self.slab.fini)

    def iden(self):
        return self._iden

    def last(self):
        '''
        Return an (offset, item) tuple for the last element in the tank ( or None ).
        '''
        return self._items.last()

    async def puts(self, items):
        '''
        Add the structured data from items to the CryoTank.

        Args:
            items (list):  A list of objects to store in the CryoTank.

        Returns:
            int: The ending offset of the items or seqn.
        '''
        size = 0

        for chunk in s_common.chunks(items, 1000):
            metrics = await self._items.save(chunk)
            self._metrics.add(metrics)
            await self.fire('cryotank:puts', numrecords=len(chunk))
            size += len(chunk)
            await asyncio.sleep(0)

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

    async def slice(self, offs, size=None, wait=False, timeout=None):
        '''
        Yield a number of items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.
            wait (bool): Once caught up, yield new results in realtime
            timeout (int): Max time to wait for a new item.

        Yields:
            ((index, object)): Index and item values.
        '''

        i = 0
        async for indx, item in self._items.aiter(offs, wait=wait, timeout=timeout):

            if size is not None and i >= size:
                return

            yield indx, item

            i += 1
            await asyncio.sleep(0)

    async def rows(self, offs, size=None):
        '''
        Yield a number of raw items from the CryoTank starting at a given offset.

        Args:
            offs (int): The index of the desired datum (starts at 0)
            size (int): The max number of items to yield.

        Yields:
            ((indx, bytes)): Index and msgpacked bytes.
        '''
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
        return {
            'iden': self._iden,
            'indx': self._items.index(),
            'metrics': self._metrics.index(),
            'stat': stat,
        }

class CryoApi(s_cell.CellApi):
    '''
    The CryoCell API as seen by a telepath proxy.

    This is the API to reference for remote CryoCell use.
    '''
    async def init(self, name, conf=None):
        tank = await self.cell.init(name, conf=conf, user=self.user)
        return tank.iden()

    async def slice(self, name, offs, size=None, wait=False, timeout=None):
        tank = await self.cell.init(name, user=self.user)
        self.user.confirm(('cryo', 'tank', 'read'), gateiden=tank.iden())
        async for item in tank.slice(offs, size=size, wait=wait, timeout=timeout):
            yield item

    async def list(self):
        return await self.cell.list(user=self.user)

    async def last(self, name):
        tank = await self.cell.init(name, user=self.user)
        self.user.confirm(('cryo', 'tank', 'read'), gateiden=tank.iden())
        return tank.last()

    async def puts(self, name, items):
        tank = await self.cell.init(name, user=self.user)
        self.user.confirm(('cryo', 'tank', 'put'), gateiden=tank.iden())
        return await tank.puts(items)

    async def rows(self, name, offs, size):
        tank = await self.cell.init(name, user=self.user)
        self.user.confirm(('cryo', 'tank', 'read'), gateiden=tank.iden())
        async for item in tank.rows(offs, size):
            yield item

    async def metrics(self, name, offs, size=None):
        tank = await self.cell.init(name, user=self.user)
        self.user.confirm(('cryo', 'tank', 'read'), gateiden=tank.iden())
        async for item in tank.metrics(offs, size=size):
            yield item

    @s_cell.adminapi(log=True)
    async def delete(self, name):
        return await self.cell.delete(name)

class CryoCell(s_cell.Cell):

    cellapi = CryoApi
    tankapi = TankApi

    async def __anit__(self, dirn, conf=None, readonly=False):

        await s_cell.Cell.__anit__(self, dirn, conf)

        await self.auth.addAuthGate('cryo', 'cryo')

        self._cryo_permdefs = []
        self._initCryoPerms()

        self.dmon.share('cryotank', self)

    async def initServiceStorage(self):

        self.names = self.slab.getSafeKeyVal('cryo:names')

        await self._bumpCellVers('cryotank', (
            (2, self._migrateToV2),
            (3, self._migrateToV3),
        ), nexs=False)

        self.tanks = await s_base.BaseRef.anit()
        self.onfini(self.tanks.fini)

        for name, (iden, conf) in self.names.items():

            logger.info('Bringing tank [%s][%s] online', name, iden)

            path = s_common.genpath(self.dirn, 'tanks', iden)

            tank = await CryoTank.anit(path, iden, conf)

            self.tanks.put(name, tank)

            await self.auth.addAuthGate(iden, 'tank')

    async def _migrateToV2(self):

        logger.warning('Beginning migration to V2')

        async with await self.hive.open(('cryo', 'names')) as names:
            for name, node in names:

                iden, conf = node.valu
                if conf is None:
                    conf = {}

                logger.info(f'Migrating tank {name=} {iden=}')

                path = s_common.genpath(self.dirn, 'tanks', iden)

                # remove old guid file
                guidpath = s_common.genpath(path, 'guid')
                if os.path.isfile(guidpath):
                    os.unlink(guidpath)

                # if its a legacy cell remove that too
                cellpath = s_common.genpath(path, 'cell.guid')
                if os.path.isfile(cellpath):

                    os.unlink(cellpath)

                    cellslabpath = s_common.genpath(path, 'slabs', 'cell.lmdb')
                    if os.path.isdir(cellslabpath):
                        shutil.rmtree(cellslabpath, ignore_errors=True)

                # drop offsets
                slabpath = s_common.genpath(path, 'tank.lmdb')
                async with await s_lmdbslab.Slab.anit(slabpath, **conf) as slab:
                    offs = s_slaboffs.SlabOffs(slab, 'offsets')
                    slab.dropdb(offs.db)

        logger.warning('...migration complete')

    async def _migrateToV3(self):

        logger.warning('Beginning migration to V3')

        async with await self.hive.open(('cryo', 'names')) as hivenames:
            for name, node in hivenames:
                iden, conf = node.valu
                self.names.set(name, (iden, conf))

        logger.warning('...migration complete')

    @classmethod
    def getEnvPrefix(cls):
        return ('SYN_CRYOTANK', )

    def _initCryoPerms(self):
        self._cryo_permdefs.extend((
            {'perm': ('cryo', 'tank', 'add'), 'gate': 'cryo',
             'desc': 'Controls access to creating a new tank.'},
            {'perm': ('cryo', 'tank', 'put'), 'gate': 'tank',
             'desc': 'Controls access to adding data to a specific tank.'},
            {'perm': ('cryo', 'tank', 'read'), 'gate': 'tank',
             'desc': 'Controls access to reading data from a specific tank.'},
        ))

        for pdef in self._cryo_permdefs:
            s_schemas.reqValidPermDef(pdef)

    def _getPermDefs(self):
        permdefs = list(s_cell.Cell._getPermDefs(self))
        permdefs.extend(self._cryo_permdefs)
        permdefs.sort(key=lambda x: x['perm'])
        return tuple(permdefs)

    async def getCellApi(self, link, user, path):

        if not path:
            return await self.cellapi.anit(self, link, user)

        if len(path) == 1:
            tank = await self.init(path[0], user=user)
            return await self.tankapi.anit(tank, link, user)

        raise s_exc.NoSuchPath(path=path)

    async def init(self, name, conf=None, user=None):
        '''
        Generate a new CryoTank with a given name or get a reference to an existing CryoTank.

        Args:
            name (str): Name of the CryoTank.
            user (User): The Telepath user.

        Returns:
            CryoTank: A CryoTank instance.
        '''
        tank = self.tanks.get(name)
        if tank is not None:
            return tank

        if user is not None:
            user.confirm(('cryo', 'tank', 'add'), gateiden='cryo')

        iden = s_common.guid()

        logger.info('Creating new tank: [%s][%s]', name, iden)

        path = s_common.genpath(self.dirn, 'tanks', iden)

        tank = await CryoTank.anit(path, iden, conf)

        self.names.set(name, (iden, conf))

        self.tanks.put(name, tank)

        await self.auth.addAuthGate(iden, 'tank')

        if user is not None:
            await user.setAdmin(True, gateiden=tank.iden())

        return tank

    async def list(self, user=None):
        '''
        Get a list of (name, info) tuples for the CryoTanks.

        Returns:
            list: A list of tufos.
            user (User): The Telepath user.
        '''

        infos = []

        for name, tank in self.tanks.items():

            if user is not None and not user.allowed(('cryo', 'tank', 'read'), gateiden=tank.iden()):
                continue

            infos.append((name, await tank.info()))

        return infos

    async def delete(self, name):

        tank = self.tanks.pop(name)
        if tank is None:
            return False

        iden, _ = self.names.pop(name)
        await tank.fini()
        shutil.rmtree(tank.dirn, ignore_errors=True)

        await self.auth.delAuthGate(iden)

        return True
