'''
The layer library contains the base Layer object and helpers used for
cortex construction.
'''
import os
import lmdb
import logging
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.datamodel as s_datamodel

import synapse.lib.cache as s_cache
import synapse.lib.const as s_const
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack

logger = logging.getLogger(__name__)

class Layer(s_config.Config):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    def __init__(self, dirn, conf=None):

        self.dirn = s_common.gendir(dirn)
        s_config.Config.__init__(self, opts=conf)

        path = os.path.join(self.dirn, 'layer.lmdb')

        mapsize = self.getConfOpt('lmdb:mapsize')

        # TODO: why is writemap=True no faster?
        self.lenv = lmdb.open(path, max_dbs=128, map_size=mapsize)

        self.dbs = {}

        self.initdb('grafts') # <seqn>=<valu>

        self._db_nodes = self.initdb('nodes') # <buid>=(<form>,<valu>)
        self._db_bybuid = self.initdb('bybuid') # <buid><prop>=<valu>

        self._db_bytag = self.initdb('bytag', dupsort=True) # <tag>00<indx>=<buid>
        self._db_byprop = self.initdb('byprop', dupsort=True) # <form>00<prop>00<indx>=<buid>

        self.graftseq = self.getSeqnOffs('grafts')

        #self.initdb('grafts')

        self._lift_funcs = {

            'tag': self._liftByTag,
            'tag:form': self._liftByTagForm,


            'prop': self._liftByProp,
            'prop:eq': self._liftByPropEq,
            'prop:pref': self._liftByPropPref,
            'prop:range': self._liftByPropRange,

        }

        self._stor_funcs = {

            'node:add': self._storNodeAdd,
            'node:del': self._storNodeDel,

            'node:prop:set': self._storNodePropSet,

            'node:tag:add': self._storNodeTagAdd,
            'node:tag:del': self._storNodeTagDel,
        }

    # top level API for cortex bypass
    #def addBuidTag(
    #def delBuidTag(

    def _storNodeAdd(self, xact, mesg):

        buid = mesg[1].get('buid')
        fenc = mesg[1].get('form')
        valu = mesg[1].get('valu')
        indx = mesg[1].get('indx')

        # primary property gets stored a bit specially...
        lkey = buid + b'*' + fenc
        byts = s_msgpack.en((valu, indx))

        xact.put(lkey, byts, db=self._db_bybuid)

        lkey = fenc + b'\x00\x00' + indx

        xact.put(lkey, buid, dupdata=True, db=self._db_byprop)

    def _storNodeDel(self, xact, mesg):
        buid = mesg[1].get('buid')
        xact.delete(buid, db=self._db_nodes)

    def _storNodeTagAdd(self, xact, mesg):

        buid = mesg[1].get('buid')
        valu = mesg[1].get('valu')

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')

        return self._xactNodeTagAdd(xact, buid, form, tag, valu)

    def _xactNodeTagAdd(self, xact, buid, form, tag, valu):

        indx = struct.pack('>Q', valu)

        lkey = buid + tag
        with xact.cursor(db=self._db_bybuid) as curs:

            # does it already have it?
            if curs.set_key(lkey):
                return

            byts = s_msgpack.en((valu, indx))
            curs.put(lkey, byts)

        # add to byprop index
        lkey = form + b'\x00' + tag + b'\x00' + indx
        xact.put(lkey, buid, dupdata=True, db=self._db_byprop)

        # add to bytag index
        lkey = tag + b'\x00' + indx
        xact.put(lkey, buid, dupdata=True, db=self._db_bytag)

    def _storNodeTagDel(self, xact, mesg):

        buid = mesg[1].get('buid')

        tag = mesg[1].get('tag')
        form = mesg[1].get('form')

        return self._xactNodeTagDel(buid, form, tag)

    def _xactNodeTagDel(self, xact, buid, form, tag):

        byts = xact.pop(buid + tag, db=self._db_bybuid)
        if byts is None:
            return

        valu, indx = s_msgpack.decode(byts)

        if indx is not None:

            # delete from the byprop index
            lkey = form + b'\x00' + tag + b'\x00' + indx
            xact.delete(lkey, value=buid, db=self._db_byprop)

            # delete from the bytag index
            lkey = tag + b'\x00' + indx
            xact.delete(lkey, value=buid, db=self._db_bytag)

    def initConfDefs(self):
        self.addConfDefs((
            ('lmdb:mapsize', {'type': 'int', 'defval': s_const.tebibyte}),
        ))

    def db(self, name):
        return self.dbs.get(name)

    def initdb(self, name, dupsort=False):
        db = self.lenv.open_db(name.encode('utf8'), dupsort=dupsort)
        self.dbs[name] = db
        return db

    def getSeqnOffs(self, name):
        offs = 0

        db = self.dbs.get(name)
        with self.lenv.begin() as xact:
            with xact.cursor(db=db) as curs:
                if curs.last():
                    offs = struct.unpack('>Q', curs.key())[0] + 1

        return offs

    def getNodeByBuid(self, buid):
        '''
        '''
        with self.view() as view:
            return view.getNodeByBuid(buid)

    def setLiftFunc(self, name, func):
        self._lift_funcs[name] = func

    def setStorFunc(self, name, func):
        self._stor_funcs[name] = func

    def getLiftFunc(self, name):
        return self._lift_funcs.get(name)

    def _xact_prop_del(self, xact, buid, fenc, penc):

        lkey = buid + penc
        pref = fenc + b'\x00' + penc + b'\x00'

        oldb = xact.pop(lkey, db=self._db_byiden)
        if oldb is None:
            return

        oldv, oldi = s_msgpack.un(oldb)
        if oldi is not None:
            xact.delete(pref + oldi, buid, db=self._db_byprop)

        return oldv

    def _storNodePropSet(self, xact, mesg):

        buid = mesg[1].get('buid')
        valu = mesg[1].get('valu')
        indx = mesg[1].get('indx')

        fenc = mesg[1].get('form')
        penc = mesg[1].get('prop')

        return self._xactPropSet(xact, buid, fenc, penc, valu, indx)

    def _xactPropSet(self, xact, buid, fenc, penc, valu, indx):

        lkey = buid + penc
        lval = s_msgpack.en((valu, indx))
        pref = fenc + b'\x00' + penc + b'\x00'

        oval = xact.replace(lkey, lval, db=self._db_bybuid)
        if oval is not None:
            oldv, oldi = s_msgpack.un(oval)
            if oldi is not None:
                oldk = pref + oldi
                xact.delete(oldk, buid, db=self._db_byprop)

        if indx is not None:
            lkey = pref + indx
            xact.put(lkey, buid, dupdata=True, db=self._db_byprop)

    def lift(self, lops):
        '''
        Execute a series of lift operations using a single transaction.

        NOTE: This API is mostly for testing and special case use.
        '''
        with self.lenv.begin() as xact:
            for item in self._xactRunLifts(xact, lops):
                yield item

    def stor(self, sops):
        '''
        Execute a series of stor operations using a single transaction.

        NOTE: This API is mostly for testing and special case use.
        '''
        with self.lenv.begin(write=True) as xact:
            self._xactRunStors(xact, sops)
            #self._xact_stor(xact, sops)
            #for item in self._xact_stor(xact, sops):
                #yield item

    #def join(self, buid):
        #with self.lenv.begin() as xact:
            #return self._xact_join(xact, buid)

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

    def _liftByTag(self, xact, oper):

        tenc = oper[1].get('tag').encode('utf8')

        lkey = tenc + b'\x00'

        size = len(lkey)

        with xact.cursor(db=self._db_bytag) as curs:

            if not curs.set_range(lkey):
                return

            for lkey, buid in curs.iternext():

                if lkey[:size] != pref:
                    return

                yield (buid,)

    def _liftByTagForm(self, xact, oper):

        tenc = oper[1].get('tag').encode('utf8')
        fenc = oper[1].get('form').encode('utf8')

        lkey = fenc + b'\x00' + tenc + b'\x00'
        for lkey, buid in self._iterPropPref(xact, pref):
            # maybe make this contain form/time?
            yield (buid, )

    def _iterPropPref(self, xact, pref):

        size = len(pref)
        with xact.cursor(db=self._db_byprop) as curs:

            if not curs.set_range(pref):
                return

            for lkey, lval in curs.iternext():

                if lkey[:size] != pref:
                    return

                yield lkey, lval

    def _liftByProp(self, xact, oper):

        form = oper[1].get('form')
        prop = oper[1].get('prop')

        lkey = form + b'\x00' + prop + b'\x00'

        with xact.cursor(db=self._db_byprop) as curs:

            if not curs.set_range(indx):
                return

    def _liftByPropEq(self, xact, oper):

        fenc = oper[1].get('form')
        penc = oper[1].get('prop')
        indx = oper[1].get('indx')
        valu = oper[1].get('valu')

        with xact.cursor(db=self._db_byprop) as curs:

            lkey = fenc + b'\x00' + penc + b'\x00' + indx
            if not curs.set_key(lkey):
                return

            # our rows are only (buid, )
            # (subsequent join and last cmpr are used to filt eq)
            for buid in curs.iternext_dup():
                yield (buid, )

    def _liftByPropPref(self, xact, oper):

        fenc = oper[1].get('form')
        penc = oper[1].get('prop')
        indx = oper[1].get('indx')

        pref = fenc + b'\x00' + penc + b'\x00' + indx

        size = len(pref)

        with xact.cursor(db=self._db_byprop) as curs:

            if not curs.set_range(pref):
                return

            for lkey, buid in curs.iternext():

                if lkey[:size] != pref:
                    break

                yield (buid,)

    def _liftByPropRange(self, xact, oper):

        fenc = oper[1].get('form')
        penc = oper[1].get('prop')

        minv = oper[1].get('minindx')
        maxv = oper[1].get('maxindx')

        pref = fenc + b'\x00' + penc + b'\x00'

        imin = pref + minv
        imax = pref + maxv

        size = len(imax)

        with xact.cursor(db=self._db_byprop) as curs:

            if not curs.set_range(imin):
                return

            for lkey, buid in curs.iternext():
                if lkey[:size] > imax:
                    break

                yield (buid,)

    def xact(self, write=False):
        '''
        Return a transaction object for the layer.
        '''
        return self.lenv.begin(write=write)
