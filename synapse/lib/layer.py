'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import os
import lmdb
import regex
import logging
import threading
import contextlib
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.cell as s_cell
import synapse.lib.lmdb as s_lmdb
import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads

logger = logging.getLogger(__name__)

class Encoder(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8') + b'\x00'

class Utf8er(collections.defaultdict):
    def __missing__(self, name):
        return name.encode('utf8')

class Xact(s_eventbus.EventBus):
    '''
    A Layer transaction which encapsulates the storage implementation.
    '''
    def __init__(self, layr, write=False):

        s_eventbus.EventBus.__init__(self)

        self.layr = layr
        self.write = write
        self.spliced = False
        self.splices = []

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

        self.xact = layr.lenv.begin(write=write)

        self.buidcurs = self.xact.cursor(db=layr.bybuid)
        self.buidcache = s_cache.FixedCache(self._getBuidProps, size=10000)
        self.tid = s_threads.iden()

        # our constructor gets a ref!
        self.refs = 1

        self._stor_funcs = {
            'prop:set': self._storPropSet,
            'prop:del': self._storPropDel,
        }

    @contextlib.contextmanager
    def incxref(self):
        '''
        A reference count context manager for the Xact.

        This API is *not* thread safe and is meant only for use
        in determining when generators running within one thread
        are complete.
        '''
        self.refs += 1

        yield

        self.decref()

    def decref(self):
        '''
        Decrement the reference count for the Xact.

        This API is *not* thread safe and is meant only for use
        in determining when generators running within one thread
        are complete.
        '''
        self.refs -= 1
        if self.refs == 0:
            self.commit()

    def setOffset(self, iden, offs):
        return self.layr.offs.xset(self.xact, iden, offs)

    def getOffset(self, iden):
        return self.layr.offs.xget(self.xact, iden)

    def stor(self, sops):
        '''
        Execute a series of storage operations.
        '''
        for oper in sops:
            func = self._stor_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchStor(name=oper[0])
            func(oper)

    def getLiftRows(self, lops):

        for oper in lops:

            func = self._lift_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchLift(name=oper[0])

            yield from func(oper)

    def abort(self):

        if self.tid != s_threads.iden():
            raise s_exc.BadThreadIden()

        self.xact.abort()

        # LMDB transaction requires explicit delete to recover resources
        del self.xact

    def commit(self):

        if self.tid != s_threads.iden():
            raise s_exc.BadThreadIden()

        if self.splices:
            self.layr.splicelog.save(self.xact, self.splices)

        self.xact.commit()

        # LMDB transaction requires explicit delete to recover resources
        del self.xact

        # wake any splice waiters...
        if self.splices:
            self.layr.spliced.set()

    def getBuidProps(self, buid):
        return self.buidcache.get(buid)

    def _getBuidProps(self, buid):

        props = {}

        if not self.buidcurs.set_range(buid):
            return props

        for lkey, lval in self.buidcurs.iternext():

            if lkey[:32] != buid:
                break

            prop = lkey[32:].decode('utf8')
            valu, indx = s_msgpack.un(lval)
            props[prop] = valu

        return props

    def _storPropSet(self, oper):

        _, (buid, form, prop, valu, indx, info) = oper

        if len(indx) > 256: # max index size...
            mesg = 'index bytes are too large'
            raise s_exc.BadIndxValu(mesg=mesg, prop=prop, valu=valu)

        fenc = self.layr.encoder[form]
        penc = self.layr.encoder[prop]

        univ = info.get('univ')

        # special case for setting primary property
        if not prop:
            prop = '*' + form

        bpkey = buid + self.layr.utf8[prop]

        cacheval = self.buidcache.cache.get(buid)
        if cacheval is not None:
            cacheval[prop] = valu

        bpval = s_msgpack.en((valu, indx))

        pvpref = fenc + penc
        pvvalu = s_msgpack.en((buid,))

        byts = self.xact.replace(bpkey, bpval, db=self.layr.bybuid)
        if byts is not None:

            oldv, oldi = s_msgpack.un(byts)

            self.xact.delete(pvpref + oldi, pvvalu, db=self.layr.byprop)

            if univ:
                unkey = penc + oldi
                self.xact.delete(unkey, pvvalu, db=self.layr.byuniv)

        self.xact.put(pvpref + indx, pvvalu, dupdata=True, db=self.layr.byprop)

        if univ:
            self.xact.put(penc + indx, pvvalu, dupdata=True, db=self.layr.byuniv)

    def _storPropDel(self, oper):

        _, (buid, form, prop, info) = oper

        self.buidcache.pop(buid)

        fenc = self.layr.encoder[form]
        penc = self.layr.encoder[prop]

        if prop:
            bpkey = buid + self.layr.utf8[prop]
        else:
            bpkey = buid + b'*' + self.layr.utf8[form]

        univ = info.get('univ')

        byts = self.xact.pop(bpkey, db=self.layr.bybuid)
        if byts is None:
            return

        oldv, oldi = s_msgpack.un(byts)

        pvvalu = s_msgpack.en((buid,))
        self.xact.delete(fenc + penc + oldi, pvvalu, db=self.layr.byprop)

        if univ:
            self.xact.delete(penc + oldi, pvvalu, db=self.layr.byuniv)

    def _liftByFormRe(self, oper):

        form, query, info = oper[1]

        regx = regex.compile(query)

        for buid, valu in self.iterFormRows(form):

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            yield (buid, )

    def _liftByUnivRe(self, oper):

        prop, query, info = oper[1]

        regx = regex.compile(query)

        for buid, valu in self.iterUnivRows(prop):

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            yield (buid, )

    def _liftByPropRe(self, oper):

        # ('regex', (<form>, <prop>, <regex>, info))
        form, prop, query, info = oper[1]

        regx = regex.compile(query)

        # full table scan...
        for buid, valu in self.iterPropRows(form, prop):

            # for now... but maybe repr eventually?
            if not isinstance(valu, str):
                valu = str(valu)

            if not regx.search(valu):
                continue

            #yield buid, form, prop, valu
            yield (buid, )

    def _liftByIndx(self, oper):
        # ('indx', (<dbname>, <prefix>, (<indxopers>...))
        # indx opers:  ('eq', <indx>)  ('pref', <indx>) ('range', (<indx>, <indx>)
        name, pref, iops = oper[1]

        db = self.layr.dbs.get(name)
        if db is None:
            raise s_exc.NoSuchName(name=name)

        # row operations...
        with self.xact.cursor(db=db) as curs:

            for (name, valu) in iops:

                func = self.indxfunc.get(name)
                if func is None:
                    mesg = 'unknown index operation'
                    raise s_exc.NoSuchName(name=name, mesg=mesg)

                for row in func(curs, pref, valu):

                    yield row

    def _rowsByEq(self, curs, pref, valu):
        lkey = pref + valu
        if not curs.set_key(lkey):
            return

        for byts in curs.iternext_dup():
            yield s_msgpack.un(byts)

    def _rowsByPref(self, curs, pref, valu):
        pref = pref + valu
        if not curs.set_range(pref):
            return

        size = len(pref)
        for lkey, byts in curs.iternext():

            if lkey[:size] != pref:
                return

            yield s_msgpack.un(byts)

    def _rowsByRange(self, curs, pref, valu):

        lmin = pref + valu[0]
        lmax = pref + valu[1]

        size = len(lmax)
        if not curs.set_range(lmin):
            return

        for lkey, byts in curs.iternext():

            if lkey[:size] > lmax:
                return

            yield s_msgpack.un(byts)

    def iterFormRows(self, form):
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''

        # <form> 00 00 (no prop...)
        pref = self.layr.encoder[form] + b'\x00'
        penc = self.layr.utf8['*' + form]

        with self.xact.cursor(db=self.layr.byprop) as curs:

            if not curs.set_range(pref):
                return

            size = len(pref)

            for lkey, pval in curs.iternext():

                if lkey[:size] != pref:
                    return

                buid = s_msgpack.un(pval)[0]

                byts = self.xact.get(buid + penc, db=self.layr.bybuid)
                if byts is None:
                    continue

                valu, indx = s_msgpack.un(byts)

                yield buid, valu

    def iterPropRows(self, form, prop):
        '''
        Iterate (buid, valu) rows for the given form:prop in this layer.
        '''
        # iterate byprop and join bybuid to get to value

        penc = self.layr.utf8[prop]
        pref = self.layr.encoder[form] + self.layr.encoder[prop]

        with self.xact.cursor(db=self.layr.byprop) as curs:

            if not curs.set_range(pref):
                return

            size = len(pref)

            for lkey, pval in curs.iternext():

                if lkey[:size] != pref:
                    return

                buid = s_msgpack.un(pval)[0]

                byts = self.xact.get(buid + penc, db=self.layr.bybuid)
                if byts is None:
                    continue

                valu, indx = s_msgpack.un(byts)

                yield buid, valu

    def iterUnivRows(self, prop):
        '''
        Iterate (buid, valu) rows for the given universal prop
        '''
        penc = self.layr.utf8[prop]
        pref = self.layr.encoder[prop]

        with self.xact.cursor(db=self.layr.byuniv) as curs:

            if not curs.set_range(pref):
                return

            size = len(pref)

            for lkey, pval in curs.iternext():

                if lkey[:size] != pref:
                    return

                buid = s_msgpack.un(pval)[0]

                byts = self.xact.get(buid + penc, db=self.layr.bybuid)
                if byts is None:
                    continue

                valu, indx = s_msgpack.un(byts)

                yield buid, valu

class Layer(s_cell.Cell):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    confdefs = (
        ('lmdb:mapsize', {'type': 'int', 'defval': s_lmdb.DEFAULT_MAP_SIZE}),
    )

    def __init__(self, dirn):

        s_cell.Cell.__init__(self, dirn)

        path = os.path.join(self.dirn, 'layer.lmdb')

        mapsize = self.conf.get('lmdb:mapsize')

        self.lenv = lmdb.open(path, max_dbs=128, map_size=mapsize, writemap=True)

        self.dbs = {}

        self.utf8 = Utf8er()
        self.encoder = Encoder()

        self.bybuid = self.initdb('bybuid') # <buid><prop>=<valu>
        self.byprop = self.initdb('byprop', dupsort=True) # <form>00<prop>00<indx>=<buid>
        self.byuniv = self.initdb('byuniv', dupsort=True) # <prop>00<indx>=<buid>

        offsdb = self.initdb('offsets')
        self.offs = s_lmdb.Offs(self.lenv, offsdb)

        self.spliced = threading.Event()
        self.onfini(self.spliced.set)

        self.splicedb = self.initdb('splices')
        self.splicelog = s_lmdb.Seqn(self.lenv, b'splices')

        def finiLayer():
            self.lenv.sync()
            self.lenv.close()

        self.onfini(finiLayer)

    def getOffset(self, iden):
        return self.offs.get(iden)

    def setOffset(self, iden, offs):
        return self.offs.set(iden, offs)

    def splices(self, offs, size):
        with self.lenv.begin() as xact:
            for i, mesg in self.splicelog.slice(xact, offs, size):
                yield mesg

    def db(self, name):
        return self.dbs.get(name)

    def initdb(self, name, dupsort=False):
        db = self.lenv.open_db(name.encode('utf8'), dupsort=dupsort)
        self.dbs[name] = db
        return db

    def xact(self, write=False):
        '''
        Return a transaction object for the layer.
        '''
        return Xact(self, write=write)

opendir = s_eventbus.BusRef(Layer)
opendir._fini_atexit = True
