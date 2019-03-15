'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import os
import logging

import synapse.exc as s_exc

import synapse.lib.const as s_const
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn
import synapse.lib.slaboffs as s_slaboffs
import synapse.lib.layer as s_layer
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

# Maximum number of bytes we're going to put in an index
MAX_INDEX_LEN = 256

# The layer map size can start much lower because the underlying slab auto-grows.
LMDB_LAYER_DEFAULT_MAP_SIZE = 512 * s_const.mebibyte

class LmdbLayer(s_layer.Layer):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''

    confdefs = (  # type: ignore
        ('lmdb:mapsize', {'type': 'int', 'defval': LMDB_LAYER_DEFAULT_MAP_SIZE}),
        ('lmdb:maxsize', {'type': 'int', 'defval': None, 'doc': 'The largest the DB file will grow to'}),
        ('lmdb:growsize', {'type': 'int', 'defval': None,
                           'doc': 'The amount in bytes to grow the DB file when full.  Defaults to doubling'}),
        ('lmdb:readahead', {'type': 'bool', 'defval': True}),
    )

    async def __anit__(self, core, node):

        await s_layer.Layer.__anit__(self, core, node)

        path = os.path.join(self.dirn, 'layer.lmdb')
        splicepath = os.path.join(self.dirn, 'splices.lmdb')

        self.fresh = not os.path.exists(path)

        mapsize = self.conf.get('lmdb:mapsize')
        readahead = self.conf.get('lmdb:readahead')
        maxsize = self.conf.get('lmdb:maxsize')
        growsize = self.conf.get('lmdb:growsize')

        self.layrslab = await s_lmdbslab.Slab.anit(path, max_dbs=128, map_size=mapsize, maxsize=maxsize,
                                                   growsize=growsize, writemap=True, readahead=readahead)
        self.onfini(self.layrslab.fini)

        self.spliceslab = await s_lmdbslab.Slab.anit(splicepath, max_dbs=128, map_size=mapsize, maxsize=maxsize,
                                                     growsize=growsize, writemap=True, readahead=readahead)
        self.onfini(self.spliceslab.fini)

        self._migrate_splices_pre010()

        self.dbs = {}

        self.utf8 = s_layer.Utf8er()
        self.encoder = s_layer.Encoder()

        self.bybuid = await self.initdb('bybuid') # <buid><prop>=<valu>
        self.byprop = await self.initdb('byprop', dupsort=True) # <form>00<prop>00<indx>=<buid>
        self.byuniv = await self.initdb('byuniv', dupsort=True) # <prop>00<indx>=<buid>
        offsdb = await self.initdb('offsets')
        self.offs = s_slaboffs.SlabOffs(self.layrslab, offsdb)
        self.splicelog = s_slabseqn.SlabSeqn(self.spliceslab, 'splices')

    def _migrate_db_pre010(self, dbname, newslab):
        '''
        Check for any pre-010 entries in 'dbname' in my slab and migrate those to the new slab.

        Once complete, drop the database from me with the name 'dbname'

        Returns (bool): True if a migration occurred, else False

        '''
        if not self.layrslab.dbexists(dbname):
            return False

        oldslab = self.layrslab
        olddb = oldslab.initdb(dbname)

        entries = oldslab.stat(olddb)['entries']
        if not entries:
            return False

        logger.info('Pre-010 %s migration starting.  Total rows: %d...', dbname, entries)

        def progfunc(count):
            logger.info('Progress %d/%d (%2.2f%)', count, entries, count / entries * 100)

        oldslab.copydb(olddb, newslab, destdbname=dbname, progresscb=progfunc)
        logger.info('Pre-010 %s migration copying done.  Deleting from old location...', dbname)
        oldslab.dropdb(olddb)
        logger.info('Pre-010 %s migration completed.', dbname)

        return True

    def _migrate_splices_pre010(self):
        self._migrate_db_pre010('splices', self.spliceslab)

    def migrate_provstack_pre010(self, newslab):
        '''
        Check for any pre-010 provstacks and migrate those to the new slab.
        '''
        did_migrate = self._migrate_db_pre010('prov', newslab)
        if not did_migrate:
            return

        self._migrate_db_pre010('provs', newslab)

    async def getModelVers(self):
        byts = self.layrslab.get(b'layer:model:version')
        if byts is None:
            return (-1, -1, -1)

        return s_msgpack.un(byts)

    async def setModelVers(self, vers):
        byts = s_msgpack.en(vers)
        self.layrslab.put(b'layer:model:version', byts)

    async def getBuidProps(self, buid):

        props = {}

        for lkey, lval in self.layrslab.scanByPref(buid, db=self.bybuid):

            prop = lkey[32:].decode('utf8')
            valu, indx = s_msgpack.un(lval)
            props[prop] = valu

        return props

    async def getNodeNdef(self, buid):
        for lkey, lval in self.layrslab.scanByPref(buid + b'*', db=self.bybuid):
            valu, indx = s_msgpack.un(lval)
            return lkey[33:].decode('utf'), valu

    async def _storBuidSet(self, oper):

        _, (form, oldb, newb) = oper

        fenc = self.encoder[form]

        pvoldval = s_msgpack.en((oldb,))
        pvnewval = s_msgpack.en((newb,))

        for lkey, lval in self.layrslab.scanByPref(oldb, db=self.bybuid):

            proputf8 = lkey[32:]
            valu, indx = s_msgpack.un(lval)

            #<prop><00><indx>
            propindx = proputf8 + b'\x00' + indx

            if proputf8[0] in (46, 35): # ".univ" or "#tag"
                self.layrslab.put(propindx, pvnewval, dupdata=True, db=self.byuniv)
                self.layrslab.delete(propindx, pvoldval, db=self.byuniv)

            bypropkey = fenc + propindx

            self.layrslab.put(bypropkey, pvnewval, db=self.byprop)
            self.layrslab.delete(bypropkey, pvoldval, db=self.byprop)

            self.layrslab.put(newb + proputf8, lval, db=self.bybuid)
            self.layrslab.delete(lkey, db=self.bybuid)

    async def _storPropSet(self, oper):

        _, (buid, form, prop, valu, indx, info) = oper

        if indx is not None and len(indx) > MAX_INDEX_LEN:
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

        byts = self.layrslab.replace(bpkey, bpval, db=self.bybuid)
        if byts is not None:

            oldv, oldi = s_msgpack.un(byts)

            self.layrslab.delete(pvpref + oldi, pvvalu, db=self.byprop)

            if univ:
                unkey = penc + oldi
                self.layrslab.delete(unkey, pvvalu, db=self.byuniv)

        if indx is not None:

            self.layrslab.put(pvpref + indx, pvvalu, dupdata=True, db=self.byprop)

            if univ:
                self.layrslab.put(penc + indx, pvvalu, dupdata=True, db=self.byuniv)

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

        byts = self.layrslab.pop(bpkey, db=self.bybuid)
        if byts is None:
            return

        oldv, oldi = s_msgpack.un(byts)

        pvvalu = s_msgpack.en((buid,))
        self.layrslab.delete(fenc + penc + oldi, pvvalu, db=self.byprop)

        if univ:
            self.layrslab.delete(penc + oldi, pvvalu, db=self.byuniv)

    async def _storSplices(self, splices):
        self.splicelog.save(splices)

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
        for _, byts in self.layrslab.scanByDups(lkey, db=db):
            yield s_msgpack.un(byts)

    async def _rowsByPref(self, db, pref, valu):
        pref = pref + valu
        for _, byts in self.layrslab.scanByPref(pref, db=db):
            yield s_msgpack.un(byts)

    async def _rowsByRange(self, db, pref, valu):
        lmin = pref + valu[0]
        lmax = pref + valu[1]

        for _, byts in self.layrslab.scanByRange(lmin, lmax, db=db):
            yield s_msgpack.un(byts)

    async def iterFormRows(self, form):
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''

        # <form> 00 00 (no prop...)
        pref = self.encoder[form] + b'\x00'
        penc = self.utf8['*' + form]

        for _, pval in self.layrslab.scanByPref(pref, db=self.byprop):

            buid = s_msgpack.un(pval)[0]

            byts = self.layrslab.get(buid + penc, db=self.bybuid)
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

        for _, pval in self.layrslab.scanByPref(pref, db=self.byprop):

            buid = s_msgpack.un(pval)[0]

            byts = self.layrslab.get(buid + penc, db=self.bybuid)
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

        for _, pval in self.layrslab.scanByPref(pref, db=self.byuniv):
            buid = s_msgpack.un(pval)[0]

            byts = self.layrslab.get(buid + penc, db=self.bybuid)
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
        for _, mesg in self.splicelog.slice(offs, size):
            yield mesg

    async def stat(self):
        return {
            'splicelog_indx': self.splicelog.index(),
        }

    async def initdb(self, name, dupsort=False):
        db = self.layrslab.initdb(name, dupsort)
        self.dbs[name] = db
        return db
