'''
The layer library contains the base Layer object and helpers used for
cortex construction.

Note:  this interface is subject to change between minor revisions.
'''
import shutil
import asyncio
import logging
import contextlib

import regex

import synapse.common as s_common

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.hive as s_hive
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

    async def getLiftRows(self, lops):
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.getLiftRows(lops):
            yield item

    async def iterFormRows(self, form):
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.iterFormRows(form):
            yield item

    async def iterPropRows(self, form, prop):
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.iterPropRows(form, prop):
            yield item

    async def iterUnivRows(self, univ):
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.iterUnivRows(univ):
            yield item

    async def stor(self, sops, splices=None):
        await self._reqUserAllowed(self.storperm)
        return await self.layr.stor(sops, splices=splices)

    async def getBuidProps(self, buid):
        await self._reqUserAllowed(self.liftperm)
        return await self.layr.getBuidProps(buid)

    async def getModelVers(self):
        return await self.layr.getModelVers()

    async def getOffset(self, iden):
        return await self.layr.getOffset(iden)

    async def setOffset(self, iden, valu):
        return await self.layr.setOffset(iden, valu)

    async def delOffset(self, iden):
        return await self.layr.delOffset(iden)

    async def splices(self, offs, size):
        await self._reqUserAllowed(self.liftperm)
        async for item in self.layr.splices(offs, size):
            yield item

    async def hasTagProp(self, name):
        return await self.layr.hasTagProp(name)

class Layer(s_hive.AuthGater):
    '''
    The base class for a cortex layer.
    '''
    confdefs = ()
    readonly = False

    authgatetype = 'layr'

    def __repr__(self):
        return f'Layer ({self.__class__.__name__}): {self.iden}'

    async def __anit__(self, core, node):

        self.core = core
        self.node = node
        self.iden = node.name()
        await s_hive.AuthGater.__anit__(self, self.core.auth)
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
            'tag:prop': self._liftByTagProp,
        }

        self._stor_funcs = {
            'prop:set': self._storPropSet,
            'prop:del': self._storPropDel,
            'buid:set': self._storBuidSet,
            'tag:prop:set': self._storTagPropSet,
            'tag:prop:del': self._storTagPropDel,
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
            await self._storFireSplices(splices)

    async def _storFireSplices(self, splices):
        '''
        Fire events, windows, etc for splices.
        '''
        indx = await self._storSplices(splices)

        self.spliced.set()
        self.spliced.clear()

        items = [(indx + i, s) for (i, s) in enumerate(splices)]

        # go fast and protect against edit-while-iter issues
        [(await wind.puts(items)) for wind in tuple(self.windows)]

        [(await self.dist(s)) for s in splices]

    async def _storSplices(self, splices):  # pragma: no cover
        '''
        Store the splices into a sequentially accessible storage structure.
        Returns the indx of the first splice stored.
        '''
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

            yield (buid,)

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

            yield (buid,)

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
            yield (buid,)

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

            yield (buid,)

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

            yield (buid,)

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

            yield (buid,)

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

    async def _storTagPropSet(self, oper): # pragma: no cover
        raise NotImplementedError

    async def _storTagPropDel(self, oper): # pragma: no cover
        raise NotImplementedError

    async def _storBuidSet(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _storPropDel(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _liftByIndx(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _liftByTagProp(self, oper): # pragma: no cover
        raise NotImplementedError

    async def iterFormRows(self, form):  # pragma: no cover
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''
        for x in (): yield x
        raise NotImplementedError

    async def hasTagProp(self, name): # pragma: no cover
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

    async def delUnivProp(self, propname, info=None): # pragma: no cover
        '''
        Bulk delete all instances of a universal prop.
        '''
        raise NotImplementedError

    async def delFormProp(self, formname, propname, info=None): # pragma: no cover
        '''
        Bulk delete all instances of a form prop.
        '''

    async def setNodeData(self, buid, name, item): # pragma: no cover
        raise NotImplementedError

    async def getNodeData(self, buid, name, defv=None): # pragma: no cover
        raise NotImplementedError

    async def iterNodeData(self, buid): # pragma: no cover
        for x in (): yield x
        raise NotImplementedError

    async def trash(self):
        '''
        Delete the underlying storage
        '''
        await s_hive.AuthGater.trash(self)
        shutil.rmtree(self.dirn, ignore_errors=True)
