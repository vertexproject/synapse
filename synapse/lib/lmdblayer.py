'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import os
import asyncio
import logging

import synapse.exc as s_exc

import synapse.lib.lmdb as s_lmdb
import synapse.lib.slabseqn as s_slabseqn
import synapse.lib.slaboffs as s_slaboffs
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads

logger = logging.getLogger(__name__)

# Maximum number of bytes we're going to put in an index
MAX_INDEX_LEN = 256

class LmdbLayer(s_layer.Layer):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    confdefs = (  # type: ignore
        ('lmdb:mapsize', {'type': 'int', 'defval': s_lmdb.DEFAULT_MAP_SIZE}),
        ('lmdb:readahead', {'type': 'bool', 'defval': True}),
    )

    async def __anit__(self, dirn):

        await s_layer.Layer.__anit__(self, dirn)

        path = os.path.join(self.dirn, 'layer.lmdb')

        mapsize = self.conf.get('lmdb:mapsize')
        readahead = self.conf.get('lmdb:readahead')

        self.slab = await s_lmdb.Slab.anit(path, max_dbs=128, map_size=mapsize, writemap=True, readahead=readahead)

        self.onfini(self.slab.fini)

        self.dbs = {}

        self.utf8 = s_layer.Utf8er()
        self.encoder = s_layer.Encoder()

        self.indxfunc = {
            'eq': self._rowsByEq,
            'pref': self._rowsByPref,
            'range': self._rowsByRange,
        }

        self._lift_funcs = {
            'indx': self._liftByIndx,
            'prop:re': self._liftByPropRe,
            'univ:re': self._liftByUnivRe,
            'form:re': self._liftByFormRe,
        }

        self.tid = s_threads.iden()

        self.bybuid = await self.initdb('bybuid') # <buid><prop>=<valu>
        self.byprop = await self.initdb('byprop', dupsort=True) # <form>00<prop>00<indx>=<buid>
        self.byuniv = await self.initdb('byuniv', dupsort=True) # <prop>00<indx>=<buid>
        offsdb = await self.initdb('offsets')
        self.offs = s_slaboffs.SlabOffs(self.slab, offsdb)

        self.splicedb = await self.initdb('splices')
        self.splicelog = s_slabseqn.SlabSeqn(self.slab, 'splices')
        self.spliced = asyncio.Event(loop=self.loop)
        self.splicelist = []
        self.onfini(self.spliced.set)

    async def stor(self, sops):
        '''
        Execute a series of storage operations.
        '''
        for oper in sops:
            func = self._stor_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchStor(name=oper[0])
            await func(oper)

    async def commit(self):

        if self.splicelist:
            self.splicelog.save(self.splicelist)

        self.slab.commit(force=True)

        # wake any splice waiters and clear the splices out...
        if self.splicelist:
            self.spliced.set()
            self.spliced.clear()
            self.splicelist.clear()

    async def getBuidProps(self, buid):

        props = {}

        for lkey, lval in self.slab.scanByPref(buid, db=self.bybuid):

            prop = lkey[32:].decode('utf8')
            valu, indx = s_msgpack.un(lval)
            props[prop] = valu

        return props

    async def _storPropSet(self, oper):

        _, (buid, form, prop, valu, indx, info) = oper

        if len(indx) > MAX_INDEX_LEN:
            mesg = 'index bytes are too large'
            raise s_exc.BadIndxValu(mesg=mesg, prop=prop, valu=valu)

        fenc = self.encoder[form]
        penc = self.encoder[prop]

        univ = info.get('univ')

        # special case for setting primary property
        if not prop:
            prop = '*' + form

        bpkey = buid + self.utf8[prop]

        # FIXME:  might need to update any cortex buid cache

        bpval = s_msgpack.en((valu, indx))

        pvpref = fenc + penc
        pvvalu = s_msgpack.en((buid,))

        byts = self.slab.replace(bpkey, bpval, db=self.bybuid)
        if byts is not None:

            oldv, oldi = s_msgpack.un(byts)

            self.slab.delete(pvpref + oldi, pvvalu, db=self.byprop)

            if univ:
                unkey = penc + oldi
                self.slab.delete(unkey, pvvalu, db=self.byuniv)

        self.slab.put(pvpref + indx, pvvalu, dupdata=True, db=self.byprop)

        if univ:
            self.slab.put(penc + indx, pvvalu, dupdata=True, db=self.byuniv)

    async def _storPropDel(self, oper):

        _, (buid, form, prop, info) = oper

        # FIXME:  update any cortex-wide buid cache
        # FIXME:  this might not have the expected impact if

        fenc = self.encoder[form]
        penc = self.encoder[prop]

        if prop:
            bpkey = buid + self.utf8[prop]
        else:
            bpkey = buid + b'*' + self.utf8[form]

        univ = info.get('univ')

        byts = self.slab.pop(bpkey, db=self.bybuid)
        if byts is None:
            return

        oldv, oldi = s_msgpack.un(byts)

        pvvalu = s_msgpack.en((buid,))
        self.slab.delete(fenc + penc + oldi, pvvalu, db=self.byprop)

        if univ:
            self.slab.delete(penc + oldi, pvvalu, db=self.byuniv)

    async def _liftByIndx(self, oper):
        # ('indx', (<dbname>, <prefix>, (<indxopers>...))
        # indx opers:  ('eq', <indx>)  ('pref', <indx>) ('range', (<indx>, <indx>)
        name, pref, iops = oper[1]

        db = self.dbs.get(name)
        if db is None:
            raise s_exc.NoSuchName(name=name)

        for (name, valu) in iops:

            func = self.indxfunc.get(name)
            if func is None:
                mesg = 'unknown index operation'
                raise s_exc.NoSuchName(name=name, mesg=mesg)

            async for row in func(db, pref, valu):

                yield row

    async def _rowsByEq(self, db, pref, valu):
        lkey = pref + valu
        for byts in self.slab.scanByDups(lkey, db=db):
            yield s_msgpack.un(byts)

    async def _rowsByPref(self, db, pref, valu):
        pref = pref + valu
        for _, byts in self.slab.scanByPref(pref, db=db):
            yield s_msgpack.un(byts)

    async def _rowsByRange(self, db, pref, valu):
        lmin = pref + valu[0]
        lmax = pref + valu[1]

        for _, byts in self.slab.scanByRange(lmin, lmax, db=db):
            yield s_msgpack.un(byts)

    async def iterFormRows(self, form):
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''

        # <form> 00 00 (no prop...)
        pref = self.encoder[form] + b'\x00'
        penc = self.utf8['*' + form]

        for _, pval in self.slab.scanByPref(pref, db=self.byprop):

            buid = s_msgpack.un(pval)[0]

            byts = self.slab.get(buid + penc, db=self.bybuid)
            if byts is None:
                continue

            valu, indx = s_msgpack.un(byts)

            yield buid, valu

    async def iterPropRows(self, form, prop):
        '''
        Iterate (buid, valu) rows for the given form:prop in this layer.
        '''
        # iterate byprop and join bybuid to get to value

        penc = self.utf8[prop]
        pref = self.encoder[form] + self.encoder[prop]

        for _, pval in self.slab.scanByPref(pref, db=self.byprop):

            buid = s_msgpack.un(pval)[0]

            byts = self.slab.get(buid + penc, db=self.bybuid)
            if byts is None:
                continue

            valu, indx = s_msgpack.un(byts)

            yield buid, valu

    async def iterUnivRows(self, prop):
        '''
        Iterate (buid, valu) rows for the given universal prop
        '''
        penc = self.utf8[prop]
        pref = self.encoder[prop]

        for _, pval in self.slab.scanByPref(pref, db=self.byuniv):
            buid = s_msgpack.un(pval)[0]

            byts = self.slab.get(buid + penc, db=self.bybuid)
            if byts is None:
                continue

            valu, indx = s_msgpack.un(byts)

            yield buid, valu

    async def getOffset(self, iden):
        '''
        Note:  this method doesn't need to be async, but it is probable that future layer implementations would need it
        to be async
        '''
        return self.offs.get(iden)

    async def setOffset(self, iden, offs):
        '''
        Note:  this method doesn't need to be async, but it is probable that future layer implementations would need it
        to be async
        '''
        return self.offs.set(iden, offs)

    async def splices(self, offs, size):
        for i, mesg in self.splicelog.slice(offs, size):
            yield mesg

    async def stat(self):
        return {
            'splicelog_indx': self.splicelog.index(),
        }

    # FIXME: is this used anywhere?
    # async def db(self, name):
    #     return self.dbs.get(name)

    async def initdb(self, name, dupsort=False):
        db = self.slab.initdb(name, dupsort)
        self.dbs[name] = db
        return db
