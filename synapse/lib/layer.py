'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import regex
import logging
import threading
import collections

import synapse.exc as s_exc
import synapse.lib.cell as s_cell

logger = logging.getLogger(__name__)

class Encoder(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8') + b'\x00'

class Utf8er(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8')

class Layer(s_cell.Cell):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    def __init__(self, dirn):
        s_cell.Cell.__init__(self, dirn)
        self._lift_funcs = {
            'indx': self._liftByIndx,
            'prop:re': self._liftByPropRe,
            'univ:re': self._liftByUnivRe,
            'form:re': self._liftByFormRe,
        }

        self._stor_funcs = {
            'prop:set': self._storPropSet,
            'prop:del': self._storPropDel,
        }

    async def getLiftRows(self, lops):
        for oper in lops:

            func = self._lift_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchLift(name=oper[0])

            async for row in func(oper):
                yield row

    async def setOffset(self, iden, offs):  # pragma: no cover
        raise NotImplementedError

    async def getOffset(self, iden):  # pragma: no cover
        raise NotImplementedError

    async def stor(self, sops):
        '''
        Execute a series of storage operations.
        '''
        for oper in sops:
            func = await self._stor_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchStor(name=oper[0])
            func(oper)

    async def abort(self):  # pragma: no cover
        raise NotImplementedError

    async def commit(self):  # pragma: no cover
        raise NotImplementedError

    async def getBuidProps(self, buid):  # pragma: no cover
        raise NotImplementedError

    async def _storPropSet(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _storPropDel(self, oper):  # pragma: no cover
        raise NotImplementedError

    async def _liftByFormRe(self, oper):

        form, query, info = oper[1]

        regx = regex.compile(query)

        async for buid, valu in self.iterFormRows(form):

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            yield (buid, )

    async def _liftByUnivRe(self, oper):

        prop, query, info = oper[1]

        regx = regex.compile(query)

        async for buid, valu in self.iterUnivRows(prop):

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

        # full table scan...
        async for buid, valu in self.iterPropRows(form, prop):

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            # yield buid, form, prop, valu
            yield (buid, )

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
        raise NotImplementedError()

    async def splices(self, offs, size):  # pragma: no cover
        raise NotImplementedError()
