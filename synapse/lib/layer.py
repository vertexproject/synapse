'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import os
import lmdb
import logging
import threading
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
openlayers = {}


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

        self.xact = layr.lenv.begin(write=write)

        self.buidcurs = self.xact.cursor(db=layr.bybuid)
        self.buidcache = s_cache.FixedCache(self._getBuidProps, size=10000)
        self.tid = s_threads.iden()

    def save(self, msgs):
        '''
        Save the given splices to the splice log.
        '''
        self.spliced = True
        self.layr.splicelog.save(self.xact, msgs)

    def setOffset(self, iden, offs):
        return self.layr.offs.xset(self.xact, iden, offs)

    def getOffset(self, iden):
        return self.layr.offs.xget(self.xact, iden)

    def stor(self, sops):
        self.layr._xactRunStors(self.xact, sops)

    def getLiftRows(self, lops):
        for row in self.layr._xactRunLifts(self.xact, lops):
            yield row

    def abort(self):
        # aborting on a write transaction on a different thread than it was created is fatal
        assert(not self.write or self.tid == s_threads.iden())
        self.xact.abort()

    def commit(self):
        # committing on a write transaction on a different thread than it was created is fatal
        assert(not self.write or self.tid == s_threads.iden())
        self.xact.commit()
        if self.spliced:
            self.layr.spliced.set()

    def getBuidProps(self, buid):
        return self.buidcache.get(buid)

    def _getBuidProps(self, buid):

        props = []

        if not self.buidcurs.set_range(buid):
            return props

        for lkey, lval in self.buidcurs.iternext():

            if lkey[:32] != buid:
                break

            prop = lkey[32:].decode('utf8')
            valu, indx = s_msgpack.un(lval)
            props.append((prop, valu))

        return props


class Layer(s_cell.Cell):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    confdefs = (
        ('lmdb:mapsize', {'type': 'int', 'defval': s_const.tebibyte}),
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

        self.indxfunc = {
            'eq': self._rowsByEq,
            'pref': self._rowsByPref,
            'range': self._rowsByRange,
        }

        self._lift_funcs = {
            'indx': self._liftByIndx,
        }

        self._stor_funcs = {
            'prop:set': self._storPropSet,
            'prop:del': self._storPropDel,
        }

    def getOffset(self, iden):
        return self.offs.get(iden)

    def setOffset(self, iden, offs):
        return self.offs.set(iden, offs)

    def splices(self, offs, size):
        with self.lenv.begin() as xact:
            for i, mesg in self.splicelog.slice(xact, offs, size):
                yield mesg

    def _storPropSet(self, xact, oper):

        _, (buid, form, prop, valu, indx, info) = oper

        if len(indx) > 256: # max index size...
            mesg = 'index bytes are too large'
            raise s_exc.BadIndxValu(mesg=mesg, prop=prop, valu=valu)

        fenc = self.encoder[form]
        penc = self.encoder[prop]

        univ = info.get('univ')

        # special case for setting primary property
        if prop:
            bpkey = buid + self.utf8[prop]
        else:
            bpkey = buid + b'*' + self.utf8[form]

        bpval = s_msgpack.en((valu, indx))

        pvpref = fenc + penc
        pvvalu = s_msgpack.en((buid,))

        byts = xact.replace(bpkey, bpval, db=self.bybuid)
        if byts is not None:

            oldv, oldi = s_msgpack.un(byts)

            xact.delete(pvpref + oldi, pvvalu, db=self.byprop)

            if univ:
                unkey = penc + oldi
                xact.delete(unkey, pvvalu, db=self.byuniv)

        xact.put(pvpref + indx, pvvalu, dupdata=True, db=self.byprop)

        if univ:
            xact.put(penc + indx, pvvalu, dupdata=True, db=self.byuniv)

    def _storPropDel(self, xact, oper):

        _, (buid, form, prop, info) = oper

        fenc = self.encoder[form]
        penc = self.encoder[prop]

        if prop:
            bpkey = buid + self.utf8[prop]
        else:
            bpkey = buid + b'*' + self.utf8[form]

        univ = info.get('univ')

        byts = xact.pop(bpkey, db=self.bybuid)
        if byts is None:
            return

        oldv, oldi = s_msgpack.un(byts)

        pvvalu = s_msgpack.en((buid,))
        xact.delete(fenc + penc + oldi, pvvalu, db=self.byprop)

        if univ:
            xact.delete(penc + oldi, pvvalu, db=self.byuniv)

    def db(self, name):
        return self.dbs.get(name)

    def initdb(self, name, dupsort=False):
        db = self.lenv.open_db(name.encode('utf8'), dupsort=dupsort)
        self.dbs[name] = db
        return db

    def _xactRunLifts(self, xact, lops):
        for oper in lops:
            func = self._lift_funcs.get(oper[0])
            for item in func(xact, oper):
                yield item

    def _xactRunStors(self, xact, sops):
        '''
        Execute a series of storage operations.
        '''
        for oper in sops:
            func = self._stor_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchStor(name=oper[0])
            func(xact, oper)

    def _liftByIndx(self, xact, oper):
        # ('indx', (<dbname>, <prefix>, (<indxopers>...))
        # indx opers:  ('eq', <indx>)  ('pref', <indx>) ('range', (<indx>, <indx>)
        name, pref, iops = oper[1]

        db = self.dbs.get(name)
        if db is None:
            raise s_exc.NoSuchName(name=name)

        # row operations...
        with xact.cursor(db=db) as curs:

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

    def xact(self, write=False):
        '''
        Return a transaction object for the layer.
        '''
        return Xact(self, write=write)

def opendir(*path):
    '''
    Since a layer may not be opened twice, use the existing.
    '''
    path = s_common.genpath(*path)

    layr = openlayers.get(path)
    if layr is not None:
        return layr

    layr = Layer(path)
    openlayers[path] = layr

    return layr
