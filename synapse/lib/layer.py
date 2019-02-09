'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import asyncio
import logging
import collections

import regex

import synapse.common as s_common

import synapse.exc as s_exc
import synapse.lib.base as s_base
#import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

FAIR_ITERS = 10  # every this many rows, yield CPU to other tasks

class Encoder(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8') + b'\x00'

class Utf8er(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8')

class Layer(s_base.Base):
    '''
    The base class for a cortex layer.
    '''
    confdefs = ()
    async def __anit__(self, core, node):

        await s_base.Base.__anit__(self)

        self.core = core
        self.node = node
        self.iden = node.name()

        self.info = await node.dict()
        self.info.setdefault('owner', 'root')

        self.owner = self.info.get('owner')

        self.conf = await (await node.open('config')).dict()

        for name, info in self.confdefs:

            dval = info.get('defval', s_common.novalu)
            if dval is s_common.novalu:
                continue

            self.conf.setdefault(name, dval)

        self.dirn = s_common.gendir(core.dirn, 'layers', self.iden)
        #await s_cell.Cell.__anit__(self, dirn)

        self._lift_funcs = {
            'indx': self._liftByIndx,
            'prop:re': self._liftByPropRe,
            'univ:re': self._liftByUnivRe,
            'form:re': self._liftByFormRe,
        }

        self._stor_funcs = {
            'prop:set': self._storPropSet,
            'prop:del': self._storPropDel,
            'buid:set': self._storBuidSet,
        }

        self.indxfunc = {
            'eq': self._rowsByEq,
            'pref': self._rowsByPref,
            'range': self._rowsByRange,
        }

        self.fresh = False
        self.canrev = True
        self.spliced = asyncio.Event(loop=self.loop)
        self.splicelist = []
        self.onfini(self.spliced.set)

    @classmethod
    async def validate(conf):
        raise NotImplementedError

    async def setLayerInfo(self, **info):

        name = info.pop('name', None)
        if name is not None:
            await self.info.set('name', name)

        ownr = info.pop('owner', None)
        if ownr is not None:
            await self.info.set('owner', ownr)

    async def setLayerConf(self, **conf):
        #TODO self.__class__.validate(conf)
        for name, valu in conf.items():
            await self.conf.set(name, valu)

    async def splicelistAppend(self, mesg):
        self.splicelist.append(mesg)

    async def getLiftRows(self, lops):
        for oper in lops:

            func = self._lift_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchLift(name=oper[0])

            async for row in func(oper):
                yield row

    async def stor(self, sops):
        '''
        Execute a series of storage operations.
        '''
        for oper in sops:
            func = self._stor_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchStor(name=oper[0])
            await func(oper)

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

    async def commit(self):  # pragma: no cover
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

    async def _rowsByEq(self, curs, pref, valu):  # pragma: no cover
        raise NotImplementedError

    async def _rowsByPref(self, curs, pref, valu):  # pragma: no cover
        raise NotImplementedError

    async def _rowsByRange(self, curs, pref, valu):  # pragma: no cover
        raise NotImplementedError

    async def iterFormRows(self, form):  # pragma: no cover
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''
        raise NotImplementedError

    async def iterPropRows(self, form, prop):  # pragma: no cover
        '''
        Iterate (buid, valu) rows for the given form:prop in this layer.
        '''
        raise NotImplementedError

    async def iterUnivRows(self, prop):  # pragma: no cover
        '''
        Iterate (buid, valu) rows for the given universal prop
        '''
        raise NotImplementedError

    async def stat(self):
        raise NotImplementedError

    async def splices(self, offs, size):  # pragma: no cover
        raise NotImplementedError

    async def getNodeNdef(self, buid):
        raise NotImplementedError
