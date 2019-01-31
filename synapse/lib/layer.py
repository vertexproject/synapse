'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import asyncio
import logging
import collections

import regex

import synapse.exc as s_exc
import synapse.lib.cell as s_cell
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

FAIR_ITERS = 10  # every this many rows, yield CPU to other tasks

class Encoder(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8') + b'\x00'

class Utf8er(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8')

class LayerApi(s_cell.PassThroughApi):
    allowed_methods = [
        'getLiftRows', 'stor', 'commit', 'abort', 'getBuidProps',
        'iterFormRows', 'iterPropRows', 'iterUnivRows', 'getOffset',
        'setOffset', 'initdb', 'splicelistAppend', 'splices', 'stat'
    ]
    async def getModelVers(self):
        return await self.cell.getModelVers()

class Layer(s_cell.Cell):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    cellapi = LayerApi

    async def __anit__(self, dirn, readonly=False):

        await s_cell.Cell.__anit__(self, dirn, readonly=readonly)

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

        self.indxfunc = {
            'eq': self._rowsByEq,
            'pref': self._rowsByPref,
            'range': self._rowsByRange,
        }

        self.fresh = False
        self.canrev = not readonly
        self.readonly = readonly
        self.spliced = asyncio.Event(loop=self.loop)
        self.splicelist = []
        self.onfini(self.spliced.set)

    async def getModelVers(self):
        byts = self.slab.get(b'layer:model:version')
        if byts is None:
            return (-1, -1, -1)

        return s_msgpack.un(byts)

    async def setModelVers(self, vers):
        byts = s_msgpack.en(vers)
        self.slab.put(b'layer:model:version', byts)

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

    async def _liftByPropIval(self, oper):
        form, prop, _, _ = oper[1]
        count = 0
        async for buid, valu in self.iterPropRows(form, prop):
            count += 1

            if not count % FAIR_ITERS:
                await asyncio.sleep(0)

            if type(valu) not in (int, list, tuple):
                continue

            yield (buid, )

    async def _liftByUnivIval(self, oper):
        prop = oper[1][0]
        count = 0
        async for buid, valu in self.iterUnivRows(prop):
            count += 1

            if not count % FAIR_ITERS:
                await asyncio.sleep(0)

            yield (buid, )

    async def _liftByFormIval(self, oper):
        form = oper[1][0]
        count = 0
        async for buid, valu in self.iterFormRows(form):
            count += 1

            if not count % FAIR_ITERS:
                await asyncio.sleep(0)

            if type(valu) not in (list, tuple):
                continue

            yield (buid, )

    # The following functions are abstract methods that must be implemented by a subclass

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
