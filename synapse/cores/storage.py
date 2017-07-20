#!/usr/bin/env python
# -*- coding: utf-8 -*-
# XXX Update Docstring
"""
synapse - storage.py
Created on 7/19/17.


"""
# Stdlib
import os
import sys
import json
import time
import argparse
import logging
import threading

# Third Party Code
# Custom Code

import synapse.common as s_common
import synapse.compat as s_compat

import synapse.lib.config as s_config
import synapse.lib.threads as s_threads
import synapse.lib.userauth as s_userauth

logger = logging.getLogger(__name__)

class StoreXact:
    '''
    A context manager for a storage "transaction".
    '''
    def __init__(self, store, size=None):
        self.store = store
        self.size = size

        self.tick = s_common.now()

        self.refs = 0
        self.ready = False
        self.exiting = False

        self.events = []

    def spliced(self, act, **info):

        form = info.get('form')

        pdef = self.store.getPropDef(form)
        if pdef is not None and pdef[1].get('local'):
            return

        info['act'] = act
        info['time'] = self.tick
        info['user'] = s_userauth.getSynUser()

        self.fire('splice', **info)

    def _coreXactAcquire(self):
        # allow implementors to acquire any synchronized resources
        pass

    def _coreXactRelease(self):
        # allow implementors to release any synchronized resources
        pass

    def _coreXactInit(self):
        # called once during the first __enter__
        pass

    def _coreXactFini(self):
        # called once during the last __exit__
        pass

    def _coreXactBegin(self):
        raise s_common.NoSuchImpl(name='_coreXactBegin')

    def _coreXactCommit(self):
        raise s_common.NoSuchImpl(name='_coreXactCommit')

    def acquire(self):
        self._coreXactAcquire()
        self.store.xlock.acquire()

    def release(self):
        self.store.xlock.release()
        self._coreXactRelease()

    def begin(self):
        self._coreXactBegin()

    def commit(self):
        '''
        Commit the results thus far ( without closing / releasing )
        '''
        self._coreXactCommit()

    def fireall(self):

        events = self.events
        self.events = []

        [self.store.fire(name, **props) for (name, props) in events]

    def cedetime(self):
        # release and re acquire the form lock to allow others a shot
        # give up our scheduler quanta to allow acquire() priority to go
        # to any existing waiters.. ( or come back almost immediately if none )
        self.release()
        time.sleep(0)
        self.acquire()

    def fire(self, name, **props):
        '''
        Pend an event to fire when the transaction next commits.
        '''
        self.events.append((name, props))

        if self.size is not None and len(self.events) >= self.size:
            self.sync()
            self.cedetime()
            self.begin()

    def sync(self):
        '''
        Loop commiting and syncing events until there are no more
        events that need to fire.
        '''
        self.commit()

        # odd thing during exit... we need to fire events
        # ( possibly causing more xact uses ) until there are
        # no more events left to fire.
        while self.events:
            self.begin()
            self.fireall()
            self.commit()

    def __enter__(self):
        self.refs += 1
        if self.refs == 1 and not self.ready:
            self._coreXactInit()
            self.acquire()
            self.begin()
            self.ready = True

        return self

    def __exit__(self, exc, cls, tb):
        # FIXME handle rollback on exc not None
        self.refs -= 1
        if self.refs > 0 or self.exiting:
            return

        self.exiting = True

        self.sync()
        self.release()
        self._coreXactFini()
        self.store._popCoreXact()


# XXX
# This is the base class for a cortex Storage object which storage layers must
# implement
class Storage(s_config.Config):
    '''
    Base class for storage layer backends for a Synapse Cortex.

    It is intended that storage layer implementations may override many of the functions provided here.
    '''
    def __init__(self, link, core, **conf):
        s_config.Config.__init__(self)
        self.link = link # XXX ???

        # XXX Can we eliminate this prop normalization need?
        # We do need to know how to do prop normalization/defs for some helpers.
        self.getPropNorm = core.getPropNorm
        self.getPropDef = core.getPropDef
        # We need to be able to regisrter
        self.initTufosBy = core.initTufosBy
        self.onfini(self._defaultFiniCoreStor)

        # Various locks
        self.inclock = threading.Lock()
        self.xlock = threading.Lock()
        # Transactions are a storage-layer concept
        self._core_xacts = {}

        # Dicts for storing retrieval methods
        self.sizebymeths = {}
        self.rowsbymeths = {}

        # Register handlers for lifting rows/siexes
        self.initRowsBy('gt', self._rowsByGt)
        self.initRowsBy('lt', self._rowsByLt)
        self.initRowsBy('ge', self._rowsByGe)
        self.initRowsBy('le', self._rowsByLe)
        self.initRowsBy('range', self._rowsByRange)

        self.initSizeBy('ge', self._sizeByGe)
        self.initSizeBy('le', self._sizeByLe)
        self.initSizeBy('range', self._sizeByRange)

        self.initTufosBy('ge', self._tufosByGe)
        self.initTufosBy('le', self._tufosByLe)
        self.initTufosBy('gt', self._tufosByGt)
        self.initTufosBy('lt', self._tufosByLt)

        # Perform storage layer initializations
        self._initCoreStor()

        self.onfini(self._finiCoreStore)

    # Handlers which should be untouched
    def initRowsBy(self, name, meth):
        '''
        Initialize a "rows by" handler for the Cortex.

        Example:

            def getbywoot(prop,valu,limit=None):
                return stuff() # list of rows

            core.initRowsBy('woot',getbywoot)

        Notes:

            * Used by Cortex implementors to facilitate
              getRowsBy(...)

        '''
        self.rowsbymeths[name] = meth

    def initSizeBy(self, name, meth):
        '''
        Initialize a "size by" handler for the Cortex.

        Example:

            def sizebywoot(prop,valu,limit=None):
                return stuff() # size of rows

            core.initSizeBy('woot',meth)

        '''
        self.sizebymeths[name] = meth

    def _defaultFiniCoreStor(self):
        # Remove refs to the parent Cortex object for GC purposes
        delattr(self, 'getPropDef')
        delattr(self, 'getPropNorm')
        delattr(self, 'initTufosBy')

    def getCoreXact(self, size=1000):
        '''
        Get a cortex transaction context for use in a with block.
        This object allows bulk storage layer optimization and
        proper ordering of events.

        Example:

            with core.getCoreXact() as xact:
                core.dostuff()

        '''
        iden = s_threads.iden()

        xact = self._core_xacts.get(iden)
        if xact is not None:
            return xact

        xact = self._getCoreXact(size)
        self._core_xacts[iden] = xact
        return xact

    def _popCoreXact(self):
        # Used by the CoreXact fini routine
        self._core_xacts.pop(s_threads.iden(), None)

    # The following MUST be implemented by the storage layer in order to
    # support the basic idea of a cortex

    def _initCoreStor(self):
        raise s_common.NoSuchImpl(name='_initCoreStor', mesg='Store does not implement _initCoreStor')

    def _getStoreType(self):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_getStoreType', mesg='Store does not implement getCoreType')

    def _getCoreXact(self, size=None):
        raise s_common.NoSuchImpl(name='_getCoreXact', mesg='Store does not implement _getCoreXact')

    def _addRows(self, rows):
        raise s_common.NoSuchImpl(name='_addRows', mesg='Store does not implement _addRows')

    def _getRowsById(self, iden):
        raise s_common.NoSuchImpl(name='_getRowsById', mesg='Store does not implement _getRowsById')

    def _getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        raise s_common.NoSuchImpl(name='_getRowsByProp', mesg='Store does not implement _getRowsByProp')

    def _getRowsByIdProp(self, iden, prop, valu=None):
        raise s_common.NoSuchImpl(name='_getRowsByIdProp', mesg='Store does not implement _getRowsByIdProp')

    def _delRowsById(self, iden):
        raise s_common.NoSuchImpl(name='_delRowsById', mesg='Store does not implement _delRowsById')

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        raise s_common.NoSuchImpl(name='_delRowsByProp', mesg='Store does not implement _delRowsByProp')

    def _delRowsByIdProp(self, iden, prop, valu=None):
        raise s_common.NoSuchImpl(name='_delRowsByIdProp', mesg='Store does not implement _delRowsByIdProp')

    def _getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
        raise s_common.NoSuchImpl(name='_getSizeByProp', mesg='Store does not implement _getSizeByProp')

    def _rowsByRange(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_rowsByRange', mesg='Store does not implement _rowsByRange')

    def _sizeByGe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_sizeByGe', mesg='Store does not implement _sizeByGe')

    def _rowsByGe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_rowsByGe', mesg='Store does not implement _rowsByGe')

    def _sizeByLe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_sizeByLe', mesg='Store does not implement _sizeByLe')

    def _rowsByLe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_rowsByLe', mesg='Store does not implement _rowsByLe')

    def _sizeByRange(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_sizeByRange', mesg='Store does not implement _sizeByRange')

    def _tufosByGe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_tufosByGe', mesg='Store does not implement _tufosByGe')

    def _tufosByLe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='_tufosByLe', mesg='Store does not implement _tufosByLe')

    # The following are things which SHOULD be overridden in order to provide
    # cortex features which are kind of optional

    def _getBlobValu(self, key):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _getBlobValu', name='_getBlobValu')
        return None

    def _setBlobValu(self, key, valu):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _setBlobValu', name='_setBlobValu')
        return None

    def _hasBlobValu(self, key):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _hasBlobValue', name='_hasBlobValue')
        return None

    def _delBlobValu(self, key):  # pragma: no cover
        self.log(logging.ERROR, mesg='Store does not implement _delBlobValu', name='_delBlobValu')
        return None

    def _getBlobKeys(self):
        self.log(logging.ERROR, mesg='Store does not implement _getBlobKeys', name='_getBlobKeys')
        return None

    def _finiCoreStore(self):
        '''

        '''
        # raise s_common.NoSuchImpl(name='_finiCoreStore', mesg='Store does not implement _finiCoreStore')
        pass

    # The following are default implementations that may be overridden by
    # a storage layer for various reasons.
    def _incTufoProp(self, tufo, prop, incval=1):

        # to allow storage layer optimization
        iden = tufo[0]

        form = tufo[1].get('tufo:form')
        valu = tufo[1].get(form)

        with self.inclock:
            rows = self._getRowsByIdProp(iden, prop)
            if len(rows) == 0:
                raise s_common.NoSuchTufo(iden=iden, prop=prop)

            oldv = rows[0][2]
            newv = oldv + incval

            self.setRowsByIdProp(iden, prop, newv)

            tufo[1][prop] = newv
            self.fire('node:prop:set', form=form, valu=valu, prop=prop, newv=newv, oldv=oldv, node=tufo)

        return tufo

    def _getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self._getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit):
            for jrow in self._getRowsById(irow[0]):
                yield jrow

    # Blobstore interface isn't clean to seperate
    def _revCorVers(self, revs):
        '''
        Update a the storage layer with a list of (vers,func) tuples.

        Args:
            revs ([(int,function)]):  List of (vers,func) revision tuples.

        Returns:
            (None)

        Each specified function is expected to update the storage layer including data migration.
        '''
        if not revs:
            return
        vsn_str = 'syn:core:{}:version'.format(self._getCoreType())
        curv = self.getBlobValu(vsn_str, -1)

        maxver = revs[-1][0]
        if maxver == curv:
            return

        if not self.getConfOpt('rev:storage'):
            raise s_common.NoRevAllow(name='rev:storage',
                                      mesg='add rev:storage=1 to cortex url to allow storage updates')

        for vers, func in sorted(revs):

            if vers <= curv:
                continue

            # allow the revision function to optionally return the
            # revision he jumped to ( to allow initial override )
            mesg = 'Warning - storage layer update occurring. Do not interrupt. [{}] => [{}]'.format(curv, vers)
            logger.warning(mesg)
            retn = func()
            logger.warning('Storage layer update completed.')
            if retn is not None:
                vers = retn

            curv = self.setBlobValu(vsn_str, vers)

    def _setRowsByIdProp(self, iden, prop, valu):
        # base case is delete and add
        self._delRowsByIdProp(iden, prop)
        rows = [(iden, prop, valu, s_common.now())]
        self._addRows(rows)

    def _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
        rows = self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)
        done = set()
        for row in rows:
            iden = row[0]
            if iden in done:
                continue

            self.delRowsById(iden)
            done.add(iden)

    # these helpers allow a storage layer to simply implement
    # and register _getTufosByGe and _getTufosByLe

    def _rowsByLt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self._rowsByLe(prop, valu - 1, limit=limit)

    def _rowsByGt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self._rowsByGe(prop, valu + 1, limit=limit)

    def _tufosByLt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self._tufosByLe(prop, valu - 1, limit=limit)

    def _tufosByGt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self._tufosByGe(prop, valu + 1, limit=limit)
