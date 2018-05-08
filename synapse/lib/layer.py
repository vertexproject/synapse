'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import os
import lmdb
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.const as s_const
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

#class LayerApi(s_cell.CellApi):

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

        # TODO: why is writemap=True no faster?
        self.lenv = lmdb.open(path, max_dbs=128, map_size=mapsize)

        self.dbs = {}

        self.initdb('grafts') # <seqn>=<valu>

        self.bybuid = self.initdb('bybuid') # <buid><prop>=<valu>

        self.byprop = self.initdb('byprop', dupsort=True) # <form>00<prop>00<indx>=<buid>
        self.byuniv = self.initdb('byuniv', dupsort=True) # <prop>00<indx>=<buid>

        #self.initdb('grafts')

        self.indxfunc = {
            'eq': self._rowsByEq,
            'pref': self._rowsByPref,
            'range': self._rowsByRange,
        }

        self._lift_funcs = {

            'indx': self.liftByIndx,

        }

        self._stor_funcs = {

            'node:add': self._storNodeAdd,
            'node:del': self._storNodeDel,

            'node:prop:set': self._storNodePropSet,
            'node:univ:set': self._storNodeUnivSet,
            'node:univ:del': self._storNodeUnivDel,

            'node:tag:add': self._storNodeTagAdd,
            'node:tag:del': self._storNodeTagDel,
        }

    # top level API for cortex bypass
    #def addBuidTag(
    #def delBuidTag(

    #def _fireEditThread(self):

    def _storNodeAdd(self, xact, mesg):

        buid = mesg[1].get('buid')
        fenc = mesg[1].get('form')
        valu = mesg[1].get('valu')
        indx = mesg[1].get('indx')

        # primary property gets stored a bit specially...
        lkey = buid + b'*' + fenc

        byts = s_msgpack.en((valu, indx))
        xact.put(lkey, byts, db=self.bybuid)

        lkey = fenc + b'\x00\x00' + indx

        byts = s_msgpack.en((buid,))
        xact.put(lkey, byts, dupdata=True, db=self.byprop)

    def _storNodeDel(self, xact, mesg):
        buid = mesg[1].get('buid')
        xact.delete(buid, db=self._db_nodes)

    def _storNodeTagAdd(self, xact, mesg):

        buid = mesg[1].get('buid')
        valu = mesg[1].get('valu')

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')

        return self._xactNodeTagAdd(xact, buid, form, tag, valu)

    def _storNodeTagDel(self, xact, mesg):

        buid = mesg[1].get('buid')

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')

        return self._xactNodeTagDel(buid, form, tag)

    def db(self, name):
        return self.dbs.get(name)

    def initdb(self, name, dupsort=False):
        db = self.lenv.open_db(name.encode('utf8'), dupsort=dupsort)
        self.dbs[name] = db
        return db

    def _storNodePropSet(self, xact, mesg):

        buid = mesg[1].get('buid')
        valu = mesg[1].get('valu')
        indx = mesg[1].get('indx')

        fenc = mesg[1].get('form')
        penc = mesg[1].get('prop')

        return self._xactPropSet(xact, buid, fenc, penc, valu, indx)

    def _storNodeUnivSet(self, xact, mesg):
        # set a universal property (same as normal, with non-form index)

        buid = mesg[1].get('buid')
        valu = mesg[1].get('valu')
        indx = mesg[1].get('indx')

        fenc = mesg[1].get('form')
        penc = mesg[1].get('prop')

        oval = self._xactPropSet(xact, buid, fenc, penc, valu, indx)
        if oval is not None:

            oldv, oldi = oval

            if oldi is not None:
                lkey = penc + b'\x00' + oldi
                xact.delete(lkey, buid, db=self.byuniv)

        lkey = fenc + b'\x00' + penc + b'\x00' + indx

        lval = s_msgpack.en((buid,))
        xact.put(lkey, lval, dupdata=True, db=self.byuniv)

    def _storNodeUnivDel(self, xact, mesg):
        buid = mesg[1].get('buid')
        fenc = mesg[1].get('form')
        penc = mesg[1].get('prop')

        oval = self._xactPropDel(xact, buid, fenc, penc)
        if oval is None:
            return

        oldv, oldi = oval
        if oldi is not None:
            lkey = penc + b'\x00' + oldi
            xact.delete(lkey, buid, db=self.byuniv)

    def _xactPropSet(self, xact, buid, fenc, penc, valu, indx):

        lkey = buid + penc
        lval = s_msgpack.en((valu, indx))
        pref = fenc + b'\x00' + penc + b'\x00'

        oval = None
        byts = xact.replace(lkey, lval, db=self.bybuid)

        if byts is not None:
            oval = s_msgpack.un(byts)

            oldv, oldi = oval
            if oldi is not None:
                oldk = pref + oldi
                xact.delete(oldk, buid, db=self.byprop)

        if indx is not None:
            lkey = pref + indx
            lval = s_msgpack.en((buid,))
            xact.put(lkey, lval, dupdata=True, db=self.byprop)

        return oval

    def _xactPropDel(self, xact, buid, fenc, penc):

        lkey = buid + penc

        byts = xact.pop(lkey, db=self.bybuid)
        if byts is None:
            return None

        oldv, oldi = s_msgpack.un(byts)

        if oldi is not None:
            oldk = fenc + b'\x00' + penc + b'\x00'
            xact.delete(oldk, buid, db=self.byprop)

        return (oldv, oldi)

    def stor(self, sops):
        '''
        Execute a series of stor operations using a single transaction.

        NOTE: This API is mostly for testing and special case use.
        '''
        with self.lenv.begin(write=True) as xact:
            self._xactRunStors(xact, sops)

    def _xactRunLifts(self, xact, lops):
        for oper in lops:
            func = self._lift_funcs.get(oper[0])
            for item in func(xact, oper):
                yield item

    def _xactRunStors(self, xact, sops):
        #Execute a series of storage operations.
        for oper in sops:
            func = self._stor_funcs.get(oper[0])
            if func is None:
                raise s_exc.NoSuchStor(name=oper[0])
            func(xact, oper)

    def liftByIndx(self, xact, oper):

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
        return self.lenv.begin(write=write)
