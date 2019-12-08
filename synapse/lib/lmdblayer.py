'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import os
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cache as s_cache
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
    '''
    # TODO: metadata for layer contents (only specific type / tag)

    confdefs = (  # type: ignore
        ('lmdb:mapsize', {'type': 'int', 'defval': LMDB_LAYER_DEFAULT_MAP_SIZE}),
        ('lmdb:maxsize', {'type': 'int', 'defval': None, 'doc': 'The largest the DB file will grow to'}),
        ('lmdb:growsize', {'type': 'int', 'defval': None,
                           'doc': 'The amount in bytes to grow the DB file when full.  Defaults to doubling'}),
        ('lmdb:readahead', {'type': 'bool', 'defval': True}),
        ('lmdb:lockmemory', {'type': 'bool', 'defval': None,
                             'doc': 'Whether to prefault and lock the data into memory'}),
        ('lmdb:map_async', {'type': 'bool', 'defval': False,
                            'doc': 'Enables map_async option in LMDB to avoid blocking on mmap syncs.'}),
    )

    async def __anit__(self, core, node):

        await s_layer.Layer.__anit__(self, core, node)

        path = os.path.join(self.dirn, 'layer.lmdb')
        datapath = os.path.join(self.dirn, 'nodedata.lmdb')
        splicepath = os.path.join(self.dirn, 'splices.lmdb')

        self.fresh = not os.path.exists(path)

        mapsize = self.conf.get('lmdb:mapsize')
        readahead = self.conf.get('lmdb:readahead')
        maxsize = self.conf.get('lmdb:maxsize')
        growsize = self.conf.get('lmdb:growsize')

        map_async = core.conf.get('layer:lmdb:map_async')
        self.conf.setdefault('lmdb:map_async', map_async)

        map_async = self.conf.get('lmdb:map_async')

        # First check hive configuration.  If not set, use passed-in parameter (that defaults to False)
        self.lockmemory = self.conf.get('lmdb:lockmemory')
        if self.lockmemory is None:
            self.lockmemory = core.conf.get('dedicated')

        self.layrslab = await s_lmdbslab.Slab.anit(path, max_dbs=128, map_size=mapsize, maxsize=maxsize,
                                                   growsize=growsize, writemap=True, readahead=readahead,
                                                   lockmemory=self.lockmemory, map_async=map_async)
        self.onfini(self.layrslab.fini)

        self.spliceslab = await s_lmdbslab.Slab.anit(splicepath, max_dbs=128, map_size=mapsize, maxsize=maxsize,
                                                     growsize=growsize, writemap=True, readahead=readahead,
                                                     map_async=map_async)
        self.onfini(self.spliceslab.fini)

        self.dataslab = await s_lmdbslab.Slab.anit(datapath, map_async=True)
        self.databyname = self.dataslab.initdb('byname')
        self.databybuid = self.dataslab.initdb('bybuid')
        self.onfini(self.dataslab.fini)

        metadb = self.layrslab.initdb('meta')
        self.metadict = s_lmdbslab.SlabDict(self.layrslab, metadb)

        self._migrate_splices_pre010()

        self.dbs = {}

        self.name2offs = await self.initdb('name2offs')
        self.offs2name = await self.initdb('offs2name')

        self.bybuid = await self.initdb('bybuid') # <buid><prop>=<valu>
        self.byprop = await self.initdb('byprop', dupsort=True) # <form>00<prop>00<indx>=<buid>
        self.byuniv = await self.initdb('byuniv', dupsort=True) # <prop>00<indx>=<buid>

        # tagprop indexes...
        self.by_tp_pi = await self.initdb('by_tp_pi', dupsort=True)       # <abrv(prop)><indx> = <buid>
        self.by_tp_tpi = await self.initdb('by_tp_tpi', dupsort=True)     # <abrv(#tag:prop)><indx> = <buid>
        self.by_tp_ftpi = await self.initdb('by_tp_ftpi', dupsort=True)   # <abrv(form#tag:prop)><indx> = <buid>

        self.name2abrv = await self.initdb('name2abrv')
        self.abrv2name = await self.initdb('abrv2name')

        offsdb = await self.initdb('offsets')
        self.offs = s_slaboffs.SlabOffs(self.layrslab, offsdb)
        self.splicelog = s_slabseqn.SlabSeqn(self.spliceslab, 'splices')

        self.indxfunc = {
            'eq': self._rowsByEq,
            'pref': self._rowsByPref,
            'range': self._rowsByRange,
        }

    @s_cache.memoize(10000)
    def getNameAbrv(self, name):
        '''
        Create or return a layer specific abbreviation for the given name.
        '''
        utf8 = name.encode()

        abrv = self.layrslab.get(utf8, db=self.name2abrv)
        if abrv is not None:
            return abrv

        nexi = self.metadict.get('nameabrv', 0)
        self.metadict.set('nameabrv', nexi + 1)

        abrv = s_common.int64en(nexi)

        self.layrslab.put(utf8, abrv, db=self.name2abrv)
        self.layrslab.put(abrv, utf8, db=self.abrv2name)

        return abrv

    s_cache.memoize(10000)
    def getAbrvName(self, abrv):

        byts = self.layrslab.get(abrv, db=self.abrv2name)
        if byts is None:
            return None

        return byts.decode()

    async def popNodeData(self, buid, name):
        utf8 = name.encode()
        self.dataslab.pop(utf8 + b'\x00' + buid, db=self.databyname)
        byts = self.dataslab.pop(buid + utf8, db=self.databybuid)
        if byts is not None:
            return s_msgpack.un(byts)

    async def setNodeData(self, buid, name, item):
        utf8 = name.encode()
        self.dataslab.put(utf8 + b'\x00' + buid, b'\x00', db=self.databyname)
        self.dataslab.put(buid + utf8, s_msgpack.en(item), db=self.databybuid)

    async def getNodeData(self, buid, name, defv=None):
        byts = self.dataslab.get(buid + name.encode(), db=self.databybuid)
        if byts is None:
            return None
        return s_msgpack.un(byts)

    async def iterNodeData(self, buid):
        for lkey, lval in self.dataslab.scanByPref(buid, db=self.databybuid):
            yield lkey[32:].decode(), s_msgpack.un(lval)

    def _wipeNodeData(self, buid):
        for lkey, lval in self.dataslab.scanByPref(buid, db=self.databybuid):
            name = lkey[32:]
            self.dataslab.pop(name + b'\x00' + buid, db=self.databyname)
            self.dataslab.pop(buid + name, db=self.databybuid)

    async def stor(self, sops, splices=None):
        '''
        Execute a series of storage operations.

        Overrides implementation in layer.py to avoid unnecessary async calls.
        '''
        for oper in sops:
            func = self._stor_funcs.get(oper[0])
            if func is None:  # pragma: no cover
                raise s_exc.NoSuchStor(name=oper[0])
            func(oper)

        if splices:
            await self._storFireSplices(splices)

    def _migrate_db_pre010(self, dbname, newslab):
        '''
        Check for any pre-010 entries in 'dbname' in my slab and migrate those to the new slab.

        Once complete, drop the database from me with the name 'dbname'

        Returns (bool): True if a migration occurred, else False
        '''
        donekey = f'migrdone:{dbname}'

        if self.metadict.get(donekey, False):
            return

        if not self.layrslab.dbexists(dbname):
            self.metadict.set(donekey, True)
            return False

        oldslab = self.layrslab
        olddb = oldslab.initdb(dbname)

        entries = oldslab.stat(olddb)['entries']
        if not entries:
            self.metadict.set(donekey, True)
            return False

        if newslab.dbexists(dbname):
            logger.warning('Incomplete migration detected.  Dropping new splices to restart.')
            newslab.dropdb(dbname)
            logger.info('New splice dropping complete.')

        logger.info('Pre-010 %s migration starting.  Total rows: %d...', dbname, entries)

        def progfunc(count):
            logger.info('Progress %d/%d (%2.2f%%)', count, entries, count / entries * 100)

        oldslab.copydb(olddb, newslab, destdbname=dbname, progresscb=progfunc)
        logger.info('Pre-010 %s migration copying done.  Deleting from old location...', dbname)
        oldslab.dropdb(dbname)
        logger.info('Pre-010 %s migration completed.', dbname)

        self.metadict.set(donekey, True)

        return True

    def _migrate_splices_pre010(self):
        self._migrate_db_pre010('splices', self.spliceslab)

    def migrateProvPre010(self, newslab):
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

        props = self.buidcache.get(buid, {})

        if props:
            return props

        for lkey, lval in self.layrslab.scanByPref(buid, db=self.bybuid):

            prop = lkey[32:].decode()
            valu, indx = s_msgpack.un(lval)
            props[prop] = valu

        self.buidcache[buid] = props

        return props

    async def getNodeNdef(self, buid):
        for lkey, lval in self.layrslab.scanByPref(buid + b'*', db=self.bybuid):
            valu, indx = s_msgpack.un(lval)
            return lkey[33:].decode(), valu

    async def getFormIndx(self, buid):
        for lkey, lval in self.layrslab.scanByPref(buid + b'*', db=self.bybuid):
            valu, indx = s_msgpack.un(lval)
            return indx

    async def editNodeNdef(self, oldv, newv):
        '''
        Migration-only method

        Notes:
            Precondition: buid cache must be disabled
        '''
        assert self.buidcache.disabled

        oldb = s_common.buid(oldv)
        newb = s_common.buid(newv)

        pvoldval = s_msgpack.en((oldb,))
        pvnewval = s_msgpack.en((newb,))

        oldfenc = oldv[0].encode() + b'\x00'
        newfenc = newv[0].encode() + b'\x00'

        newprel = b'*' + newv[0].encode()

        newnindx = self.core.model.prop(newv[0]).type.indx(newv[1])

        # avoid any potential iter/edit issues...
        todo = list(self.layrslab.scanByPref(oldb, db=self.bybuid))

        for lkey, lval in todo:

            proputf8 = lkey[32:]
            valu, indx = s_msgpack.un(lval)

            # for the *<form> prop, the byprop index has <form><00><00><indx>
            if proputf8[0] == 42:

                newpropkey = newfenc + b'\x00' + newnindx

                if indx is not None:
                    oldpropkey = oldfenc + b'\x00' + indx
                    if not self.layrslab.delete(oldpropkey, pvoldval, db=self.byprop): # pragma: no cover
                        logger.warning(f'editNodeNdef del byprop missing for {repr(oldv)} {repr(oldpropkey)}')

                self.layrslab.put(newpropkey, pvnewval, dupdata=True, db=self.byprop)

                byts = s_msgpack.en((newv[1], newnindx))
                self.layrslab.put(newb + newprel, byts, db=self.bybuid)

            else:

                # <prop><00><indx>
                propindx = proputf8 + b'\x00' + indx

                if proputf8[0] in (46, 35): # ".univ" or "#tag"
                    self.layrslab.put(propindx, pvnewval, dupdata=True, db=self.byuniv)
                    self.layrslab.delete(propindx, pvoldval, db=self.byuniv)

                oldpropkey = oldfenc + propindx
                newpropkey = newfenc + propindx

                if not self.layrslab.delete(oldpropkey, pvoldval, db=self.byprop): # pragma: no cover
                    logger.warning(f'editNodeNdef del byprop missing for {repr(oldv)} {repr(oldpropkey)}')

                self.layrslab.put(newpropkey, pvnewval, dupdata=True, db=self.byprop)
                self.layrslab.put(newb + proputf8, lval, db=self.bybuid)

            self.layrslab.delete(lkey, db=self.bybuid)

    async def _storBuidSet(self, oper):
        '''
        Migration-only method

        Notes:
            Precondition: buid cache must be disabled
        '''
        assert self.buidcache.disabled

        _, (form, oldb, newb) = oper

        fenc = form.encode() + b'\x00'

        pvoldval = s_msgpack.en((oldb,))
        pvnewval = s_msgpack.en((newb,))

        for lkey, lval in self.layrslab.scanByPref(oldb, db=self.bybuid):

            proputf8 = lkey[32:]
            valu, indx = s_msgpack.un(lval)

            if indx is not None:

                # <prop><00><indx>
                propindx = proputf8 + b'\x00' + indx

                if proputf8[0] in (46, 35): # ".univ" or "#tag"
                    self.layrslab.put(propindx, pvnewval, dupdata=True, db=self.byuniv)
                    self.layrslab.delete(propindx, pvoldval, db=self.byuniv)

                bypropkey = fenc + propindx

                self.layrslab.put(bypropkey, pvnewval, db=self.byprop)
                self.layrslab.delete(bypropkey, pvoldval, db=self.byprop)

            self.layrslab.put(newb + proputf8, lval, db=self.bybuid)
            self.layrslab.delete(lkey, db=self.bybuid)

    async def hasTagProp(self, name):
        abrv = self.getNameAbrv(name)
        for item in self.layrslab.scanByPref(abrv, db=self.by_tp_pi):
            return True
        return False

    def _storTagPropSet(self, oper):

        _, (buid, form, tag, prop, valu, indx, info) = oper

        tagprop = f'#{tag}:{prop}'

        abrv_p = self.getNameAbrv(prop)
        abrv_tp = self.getNameAbrv(tagprop)
        abrv_ftp = self.getNameAbrv(f'{form}{tagprop}')

        bpkey = buid + tagprop.encode()
        byts = s_msgpack.en((valu, indx))

        curb = self.layrslab.replace(bpkey, byts, db=self.bybuid)
        if curb is not None:

            curv, curi = s_msgpack.un(curb)

            self.layrslab.delete(abrv_p + curi, val=buid, db=self.by_tp_pi)
            self.layrslab.delete(abrv_tp + curi, val=buid, db=self.by_tp_tpi)
            self.layrslab.delete(abrv_ftp + curi, val=buid, db=self.by_tp_ftpi)

        if indx is not None:
            self.layrslab.put(abrv_p + indx, buid, dupdata=True, db=self.by_tp_pi)
            self.layrslab.put(abrv_tp + indx, buid, dupdata=True, db=self.by_tp_tpi)
            self.layrslab.put(abrv_ftp + indx, buid, dupdata=True, db=self.by_tp_ftpi)

        self._putBuidCache(buid, tagprop, valu)

    def _storTagPropDel(self, oper):

        _, (buid, form, tag, prop, info) = oper

        tagprop = f'#{tag}:{prop}'

        abrv_p = self.getNameAbrv(prop)
        abrv_tp = self.getNameAbrv(tagprop)
        abrv_ftp = self.getNameAbrv(f'{form}{tagprop}')

        bpkey = buid + tagprop.encode()

        curb = self.layrslab.pop(bpkey, db=self.bybuid)

        # this *should* be completely impossible
        if curb is None: # pragma: no cover
            logger.warning('_storTagPropDel has no current value!')
            return

        curv, curi = s_msgpack.un(curb)

        self.layrslab.delete(abrv_p + curi, val=buid, db=self.by_tp_pi)
        self.layrslab.delete(abrv_tp + curi, val=buid, db=self.by_tp_tpi)
        self.layrslab.delete(abrv_ftp + curi, val=buid, db=self.by_tp_ftpi)

        self._popBuidCache(buid, tagprop)

    def _putBuidCache(self, buid, prop, valu):
        cacheval = self.buidcache.get(buid)
        if cacheval is not None:
            cacheval[prop] = valu

    def _popBuidCache(self, buid, prop):
        cacheval = self.buidcache.get(buid)
        if cacheval is not None:
            cacheval.pop(prop, None)

    def _storPropSet(self, oper):

        _, (buid, form, prop, valu, indx, info) = oper

        if indx is not None and len(indx) > MAX_INDEX_LEN:
            mesg = 'index bytes are too large'
            raise s_exc.BadIndxValu(mesg=mesg, prop=prop, valu=valu)

        fenc = form.encode() + b'\x00'
        penc = prop.encode() + b'\x00'
        pvpref = fenc + penc

        univ = info.get('univ')

        # special case for setting primary property
        if not prop:
            assert not univ
            prop = '*' + form

        bpkey = buid + prop.encode()

        self._putBuidCache(buid, prop, valu)

        self._storPropSetCommon(buid, penc, bpkey, pvpref, univ, valu, indx)

    async def storPropSet(self, buid, prop, valu):
        '''
        Migration-only function
        '''
        assert self.buidcache.disabled

        indx = prop.type.indx(valu)
        if indx is not None and len(indx) > MAX_INDEX_LEN:
            mesg = 'index bytes are too large'
            raise s_exc.BadIndxValu(mesg=mesg, prop=prop, valu=valu)

        univ = prop.utf8name[0] in (46, 35) # leading . or #
        bpkey = buid + prop.utf8name

        self._storPropSetCommon(buid, prop.utf8name, bpkey, prop.pref, univ, valu, indx)

    def _storPropSetCommon(self, buid, penc, bpkey, pvpref, univ, valu, indx):

        bpval = s_msgpack.en((valu, indx))
        pvvalu = s_msgpack.en((buid,))

        byts = self.layrslab.replace(bpkey, bpval, db=self.bybuid)
        if byts is not None:

            oldv, oldi = s_msgpack.un(byts)
            if oldi is not None:

                if isinstance(oldi, bytes):

                    self.layrslab.delete(pvpref + oldi, pvvalu, db=self.byprop)
                    if univ:
                        self.layrslab.delete(penc + oldi, pvvalu, db=self.byuniv)

                else:
                    for oldibyts in oldi:
                        self.layrslab.delete(pvpref + oldibyts, pvvalu, db=self.byprop)
                        if univ:
                            self.layrslab.delete(penc + oldibyts, pvvalu, db=self.byuniv)

        if indx is not None:

            if isinstance(indx, bytes):

                self.layrslab.put(pvpref + indx, pvvalu, dupdata=True, db=self.byprop)

                if univ:
                    self.layrslab.put(penc + indx, pvvalu, dupdata=True, db=self.byuniv)

            else:

                for indxbyts in indx:
                    self.layrslab.put(pvpref + indxbyts, pvvalu, dupdata=True, db=self.byprop)

                    if univ:
                        self.layrslab.put(penc + indxbyts, pvvalu, dupdata=True, db=self.byuniv)

    def _storPropDel(self, oper):

        _, (buid, form, prop, info) = oper

        fenc = form.encode() + b'\x00'
        penc = prop.encode() + b'\x00'

        if prop:
            bpkey = buid + prop.encode()
        else:
            bpkey = buid + b'*' + form.encode()
            # we are deleting the primary property. wipe data.
            self._wipeNodeData(buid)

        univ = info.get('univ')

        byts = self.layrslab.pop(bpkey, db=self.bybuid)
        if byts is None:
            return

        del self.buidcache[buid]

        oldv, oldi = s_msgpack.un(byts)

        pvvalu = s_msgpack.en((buid,))

        if oldi is not None:

            if isinstance(oldi, bytes):

                self.layrslab.delete(fenc + penc + oldi, pvvalu, db=self.byprop)

                if univ:
                    self.layrslab.delete(penc + oldi, pvvalu, db=self.byuniv)

            else:
                for oldibyts in oldi:

                    self.layrslab.delete(fenc + penc + oldibyts, pvvalu, db=self.byprop)

                    if univ:
                        self.layrslab.delete(penc + oldibyts, pvvalu, db=self.byuniv)

    async def _storSplices(self, splices):
        info = self.splicelog.save(splices)
        return info.get('orig')

    async def _liftByTagProp(self, oper):

        tag = oper[1].get('tag')
        form = oper[1].get('form')
        prop = oper[1].get('prop')
        iops = oper[1].get('iops')

        # #:prop
        name = prop
        db = self.by_tp_pi

        # #tag:prop
        if tag is not None:
            name = f'#{tag}:{prop}'
            db = self.by_tp_tpi

        # form#tag:prop
        if form is not None:
            name = f'{form}#{tag}:{prop}'
            db = self.by_tp_ftpi

        abrv = self.getNameAbrv(name)

        if iops is None:
            for lkey, buid in self.layrslab.scanByPref(abrv, db=db):
                yield (buid,)
            return

        for iopr in iops:

            if iopr[0] == 'eq':
                for lkey, buid in self.layrslab.scanByDups(abrv + iopr[1], db=db):
                    yield (buid,)
                continue

            if iopr[0] == 'pref':
                for lkey, buid in self.layrslab.scanByPref(abrv + iopr[1], db=db):
                    yield (buid,)
                continue

            if iopr[0] == 'range':
                kmin = abrv + iopr[1][0]
                kmax = abrv + iopr[1][1]
                for lkey, buid in self.layrslab.scanByRange(kmin, kmax, db=db):
                    yield (buid,)
                continue

            #pragma: no cover
            mesg = f'No such index function for tag props: {iopr[0]}'
            raise s_exc.NoSuchName(name=iopr[0], mesg=mesg)

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

            for row in func(db, pref, valu):

                yield row

    def _rowsByEq(self, db, pref, valu):
        lkey = pref + valu
        for _, byts in self.layrslab.scanByDups(lkey, db=db):
            yield s_msgpack.un(byts)

    def _rowsByPref(self, db, pref, valu):
        pref = pref + valu
        for _, byts in self.layrslab.scanByPref(pref, db=db):
            yield s_msgpack.un(byts)

    def _rowsByRange(self, db, pref, valu):
        lmin = pref + valu[0]
        lmax = pref + valu[1]

        for _, byts in self.layrslab.scanByRange(lmin, lmax, db=db):
            yield s_msgpack.un(byts)

    async def iterFormRows(self, form):
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''

        # <form> 00 00 (no prop...)
        pref = form.encode() + b'\x00\x00'
        penc = b'*' + form.encode()

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

        penc = prop.encode()
        pref = form.encode() + b'\x00' + penc + b'\x00'

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
        penc = prop.encode()
        pref = penc + b'\x00'

        for _, pval in self.layrslab.scanByPref(pref, db=self.byuniv):
            buid = s_msgpack.un(pval)[0]

            byts = self.layrslab.get(buid + penc, db=self.bybuid)
            if byts is None:
                continue

            valu, indx = s_msgpack.un(byts)

            yield buid, valu

    async def iterPropIndx(self, form, prop, indx):
        '''
        Yield (buid, valu) tuples for the given prop with the specified indx valu
        '''
        penc = prop.encode()
        pref = form.encode() + b'\x00' + penc + b'\x00' + indx

        for _, pval in self.layrslab.scanByPref(pref, db=self.byprop):

            buid = s_msgpack.un(pval)[0]

            byts = self.layrslab.get(buid + penc, db=self.bybuid)
            if byts is None:
                continue

            valu, indx = s_msgpack.un(byts)

            yield buid, valu

    async def getOffset(self, iden):
        '''
        Note:
            This method doesn't need to be async, but it is probable that future layer implementations would need it to
            be async
        '''
        return self.offs.get(iden)

    async def setOffset(self, iden, offs):
        '''
        Note:
            This method doesn't need to be async, but it is probable that future layer implementations would need it to
            be async
        '''
        return self.offs.set(iden, offs)

    async def delOffset(self, iden):
        '''
        Note:
            This method doesn't need to be async, but it is probable that future layer implementations would need it to
            be async
        '''
        return self.offs.delete(iden)

    async def splices(self, offs, size):
        for _, mesg in self.splicelog.slice(offs, size):
            yield mesg

    async def syncSplices(self, offs):

        for item in self.splicelog.iter(offs):
            yield item

        async with self.getSpliceWindow() as wind:
            async for item in wind:
                yield item

    async def stat(self):
        return {
            'splicelog_indx': self.splicelog.index(),
            **self.layrslab.statinfo()
        }

    async def initdb(self, name, dupsort=False):
        db = self.layrslab.initdb(name, dupsort)
        self.dbs[name] = db
        return db

    async def trash(self):
        '''
        Delete the underlying storage

        Note:  object must be fini'd first
        '''
        self.layrslab.trash()
        self.spliceslab.trash()
        self.dataslab.trash()
        await s_layer.Layer.trash(self)
