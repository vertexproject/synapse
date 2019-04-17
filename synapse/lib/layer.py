'''
The layer library contains the base Layer object and helpers used for
cortex construction.

Note:  this interface is subject to change between minor revisions.
'''
import asyncio
import logging
import contextlib

import regex

import synapse.common as s_common

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.cache as s_cache
import synapse.lib.queue as s_queue

logger = logging.getLogger(__name__)

FAIR_ITERS = 10  # every this many rows, yield CPU to other tasks
BUID_CACHE_SIZE = 10000

class LayerApi(s_cell.CellApi):

    async def __anit__(self, core, link, user, layr):

        await s_cell.CellApi.__anit__(self, core, link, user)

        self.layr = layr
        self.liftperm = ('layer:lift', self.layr.iden)
        self.storperm = ('layer:stor', self.layr.iden)

    def allowed(self, perm):
        if not self.user.allowed(perm):
            raise s_exc.AuthDeny(user=self.user.name, perm=perm)

    async def getLiftRows(self, lops):
        self.allowed(self.liftperm)
        async for item in self.layr.getLiftRows(lops):
            yield item

    async def iterFormRows(self, form):
        self.allowed(self.liftperm)
        async for item in self.layr.iterFormRows(form):
            yield item

    async def iterPropRows(self, form, prop):
        self.allowed(self.liftperm)
        async for item in self.layr.iterPropRows(form, prop):
            yield item

    async def iterUnivRows(self, univ):
        self.allowed(self.liftperm)
        async for item in self.layr.iterUnivRows(univ):
            yield item

    async def stor(self, sops, splices=None):
        self.allowed(self.storperm)
        return await self.layr.stor(sops, splices=splices)

    async def getBuidProps(self, buid):
        self.allowed(self.liftperm)
        return await self.layr.getBuidProps(buid)

    async def getModelVers(self):
        return await self.layr.getModelVers()

    async def getOffset(self, iden):
        return await self.layr.getOffset(iden)

    async def setOffset(self, iden, valu):
        return await self.layr.setOffset(iden, valu)

    async def splices(self, offs, size):
        self.allowed(self.liftperm)
        async for item in self.layr.splices(offs, size):
            yield item

class Layer(s_base.Base):
    '''
    The base class for a cortex layer.
    '''
    confdefs = ()
    readonly = False

    def __repr__(self):
        return f'Layer ({self.__class__.__name__}): {self.iden}'

    async def __anit__(self, core, node):

        await s_base.Base.__anit__(self)

        self.core = core
        self.node = node
        self.iden = node.name()
        self.buidcache = s_cache.LruDict(BUID_CACHE_SIZE)

        # splice windows...
        self.windows = []

        self.info = await node.dict()
        self.info.setdefault('owner', 'root')

        self.owner = self.info.get('owner')

        self.conf = await (await node.open(('config',))).dict()

        for name, info in self.confdefs:

            dval = info.get('defval', s_common.novalu)
            if dval is s_common.novalu:
                continue

            self.conf.setdefault(name, dval)

        self.dirn = s_common.gendir(core.dirn, 'layers', self.iden)

        self._lift_funcs = {
            'indx': self._liftByIndx,
            'prop:re': self._liftByPropRe,
            'univ:re': self._liftByUnivRe,
            'form:re': self._liftByFormRe,
            'prop:ival': self._liftByPropIval,
            'univ:ival': self._liftByUnivIval,
            'form:ival': self._liftByFormIval,
        }

        self._stor_funcs = {
            'prop:set': self._storPropSet,
            'prop:del': self._storPropDel,
            'buid:set': self._storBuidSet,
        }

        self.fresh = False
        self.canrev = True
        self.spliced = asyncio.Event(loop=self.loop)
        self.onfini(self.spliced.set)

        self.onfini(self._onLayrFini)

    async def _onLayrFini(self):
        [(await wind.fini()) for wind in self.windows]

    @contextlib.contextmanager
    def disablingBuidCache(self):
        '''
        Disable and invalidate the layer buid cache for migration
        '''
        self.buidcache = s_cache.LruDict(0)
        yield
        self.buidcache = s_cache.LruDict(BUID_CACHE_SIZE)

    @contextlib.asynccontextmanager
    async def getSpliceWindow(self):

        async with await s_queue.Window.anit(maxsize=10000) as wind:

            async def fini():
                self.windows.remove(wind)

            wind.onfini(fini)

            self.windows.append(wind)

            yield wind

    async def getLiftRows(self, lops):
        '''
        Returns:
            Iterable[Tuple[bytes, Dict[str, Any]]]:  yield a stream of tuple (buid, propdict)
        '''
        for oper in lops:

            func = self._lift_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchLift(name=oper[0])

            async for row in func(oper):
                buid = row[0]
                props = await self.getBuidProps(buid)
                yield (buid, props)

    async def stor(self, sops, splices=None):
        '''
        Execute a series of storage operations.
        '''
        for oper in sops:
            func = self._stor_funcs.get(oper[0])
            if func is None:  # pragma: no cover
                raise s_exc.NoSuchStor(name=oper[0])
            await func(oper)

        if splices:

            await self._storSplices(splices)

            self.spliced.set()
            self.spliced.clear()

            # go fast and protect against edit-while-iter issues
            [(await wind.puts(splices)) for wind in tuple(self.windows)]

    async def _storSplices(self, splices):  # pragma: no cover
        raise NotImplementedError

    async def _liftByFormRe(self, oper):

        form, query, info = oper[1]

        regx = regex.compile(query)

        count = 0

        async for buid, valu in self.iterFormRows(form):

            count += 1
            if not count % FAIR_ITERS:
                await asyncio.sleep(0)  # give other tasks a chance

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            yield (buid, )

    async def _liftByUnivRe(self, oper):

        prop, query, info = oper[1]

        regx = regex.compile(query)

        count = 0

        async for buid, valu in self.iterUnivRows(prop):

            count += 1
            if not count % FAIR_ITERS:
                await asyncio.sleep(0)  # give other tasks a chance

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            yield (buid, )

    async def _liftByPropRe(self, oper):
        # ('regex', (<form>, <prop>, <regex>, info))
        form, prop, query, info = oper[1]

        regx = regex.compile(query)

        count = 0

        # full table scan...
        async for buid, valu in self.iterPropRows(form, prop):

            count += 1
            if not count % FAIR_ITERS:
                await asyncio.sleep(0)  # give other tasks a chance

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            # yield buid, form, prop, valu
            yield (buid, )

    # TODO: Hack until we get interval trees pushed all the way through
    def _cmprIval(self, item, othr):

        if othr[0] >= item[1]:
            return False

        if othr[1] <= item[0]:
            return False

        return True

    async def _liftByPropIval(self, oper):
        form, prop, ival = oper[1]
        count = 0
        async for buid, valu in self.iterPropRows(form, prop):
            count += 1

            if not count % FAIR_ITERS:
                await asyncio.sleep(0)

            if type(valu) not in (list, tuple):
                continue

            if len(valu) != 2:
                continue

            if not self._cmprIval(ival, valu):
                continue

            yield (buid, )

    async def _liftByUnivIval(self, oper):
        _, prop, ival = oper[1]
        count = 0
        async for buid, valu in self.iterUnivRows(prop):
            count += 1

            if not count % FAIR_ITERS:
                await asyncio.sleep(0)

            if type(valu) not in (list, tuple):
                continue

            if len(valu) != 2:
                continue

            if not self._cmprIval(ival, valu):
                continue

            yield (buid, )

    async def _liftByFormIval(self, oper):
        _, form, ival = oper[1]
        count = 0
        async for buid, valu in self.iterFormRows(form):
            count += 1

            if not count % FAIR_ITERS:
                await asyncio.sleep(0)

            if type(valu) not in (list, tuple):
                continue

            if len(valu) != 2:
                continue

            if not self._cmprIval(ival, valu):
                continue

            yield (buid, )

    # The following functions are abstract methods that must be implemented by a subclass

    async def getModelVers(self):  # pragma: no cover
        raise NotImplementedError

    async def setModelVers(self, vers):  # pragma: no cover
        raise NotImplementedError

    async def setOffset(self, iden, offs):  # pragma: no cover
        raise NotImplementedError

    async def getOffset(self, iden):  # pragma: no cover
        raise NotImplementedError

    async def abort(self):  # pragma: no cover
        raise NotImplementedError

    async def getBuidProps(self, buid):  # pragma: no cover
        raise NotImplementedError

    async def _storPropSet(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _storBuidSet(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _storPropDel(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _liftByIndx(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def iterFormRows(self, form):  # pragma: no cover
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''
        for x in (): yield x
        raise NotImplementedError

    async def iterPropRows(self, form, prop):  # pragma: no cover
        '''
        Iterate (buid, valu) rows for the given form:prop in this layer.
        '''
        for x in (): yield x
        raise NotImplementedError

    async def iterUnivRows(self, prop):  # pragma: no cover
        '''
        Iterate (buid, valu) rows for the given universal prop
        '''
        for x in (): yield x
        raise NotImplementedError

    async def stat(self):  # pragma: no cover
        raise NotImplementedError

    async def splices(self, offs, size):  # pragma: no cover
        for x in (): yield x
        raise NotImplementedError

    async def syncSplices(self, offs):  # pragma: no cover
        '''
        Yield (offs, mesg) tuples from the given offset.

        Once caught up with storage, yield them in realtime.
        '''
        for x in (): yield x
        raise NotImplementedError

    async def getNodeNdef(self, buid):  # pragma: no cover
        raise NotImplementedError

    def migrateProvPre010(self, slab):  # pragma: no cover
        raise NotImplementedError
