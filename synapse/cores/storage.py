#!/usr/bin/env python
# -*- coding: utf-8 -*-
# XXX Update Docstring
"""
synapse - storage.py
Created on 7/19/17.


"""
# Stdlib
import time
import logging
import threading
import collections
# Custom Code
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.config as s_config
import synapse.lib.threads as s_threads
import synapse.lib.userauth as s_userauth

from synapse.common import reqstor

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

class Storage(s_config.Config):
    '''
    Base class for storage layer backends.  This implements functionality
    which is neccesary for a storage layer to operate, as well as providing
    stubs for the storage layer implementations to override.
    '''
    def __init__(self,
                 link,
                 **conf):
        s_config.Config.__init__(self)
        self.addConfDef('rev:storage', type='bool', defval=1, doc='Set to 0 to disallow storage version updates')
        if conf:
            self.setConfOpts(conf)

        #############################################################
        # buses to save/load *raw* save events
        #############################################################
        self.savebus = s_eventbus.EventBus()
        self.loadbus = s_eventbus.EventBus()

        self._link = link # XXX ???

        # XXX Can we eliminate this prop normalization need?
        # We do need to know how to do prop normalization/defs for some helpers.
        self.getPropNorm = None
        self.getPropDef = None
        # We need to be able to register tufosBy helpers
        # which are storage helpers
        # XXX Alternatively, provided a way for the cortex
        # XXX to call into the storage layer and ask it
        # To provide the tufo helper funcs?
        self.initTufosBy = None
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
        self.initRowsBy('gt', self.rowsByGt)
        self.initRowsBy('lt', self.rowsByLt)
        self.initRowsBy('ge', self.rowsByGe)
        self.initRowsBy('le', self.rowsByLe)
        self.initRowsBy('range', self.rowsByRange)

        self.initSizeBy('ge', self.sizeByGe)
        self.initSizeBy('le', self.sizeByLe)
        self.initSizeBy('range', self.sizeByRange)

        # Events for handling savefile loads/saves
        self.loadbus.on('core:save:add:rows', self._loadAddRows)
        self.loadbus.on('core:save:del:rows:by:iden', self._loadDelRowsById)
        self.loadbus.on('core:save:del:rows:by:prop', self._loadDelRowsByProp)
        self.loadbus.on('core:save:set:rows:by:idprop', self._loadSetRowsByIdProp)
        self.loadbus.on('core:save:del:rows:by:idprop', self._loadDelRowsByIdProp)
        self.loadbus.on('syn:core:blob:set', self._onSetBlobValu)
        self.loadbus.on('syn:core:blob:del', self._onDelBlobValu)

        # Cache blob save mesgs which may be fired during storage layer init
        _blobMesgCache = []
        self.savebus.on('syn:core:blob:set', _blobMesgCache.append)
        self.savebus.on('syn:core:blob:del', _blobMesgCache.append)

        # Perform storage layer initializations
        self._initCoreStor()

        # Disable the blob message caching
        self.savebus.off('syn:core:blob:set', _blobMesgCache.append)
        self.savebus.off('syn:core:blob:del', _blobMesgCache.append)

        # process a savefile/savefd if we have one (but only one of the two)
        savefd = self._link[1].get('savefd')
        if savefd is not None:
            self.setSaveFd(savefd)
        else:
            savefile = self._link[1].get('savefile')
            if savefile is not None:
                savefd = s_common.genfile(savefile)
                self.setSaveFd(savefd, fini=True)

        # The storage layer initialization blob events then trump anything
        # which may have been set during the savefile load and make sure they
        # get saved as well
        if 'savefd' in link[1] or 'savefile' in link[1]:
            for evtname, info in _blobMesgCache:
                self.savebus.fire(evtname, **info)
                self.loadbus.fire(evtname, **info)

        if not self.hasBlobValu('syn:core:created'):
            self.setBlobValu('syn:core:created', s_common.now())

        self.onfini(self._finiCoreStore)

    def register_cortex(self, core):
        '''
        Register a cortex with a storage layer.

        This sets various prop handlers and tufo helpers which may be needed.
        This also links the storage layer event bus to the cortex event bus.

        Args:
            core: Cortex to register.

        Returns:
            None
        '''
        # We do need to know how to do prop normalization/defs for some helpers.
        self.getPropNorm = core.getPropNorm
        self.getPropDef = core.getPropDef
        # Register tufo-level APIs which may have storage layer specific implementations
        self.initTufosBy = core.initTufosBy
        self.initTufosBy('ge', self.tufosByGe)
        self.initTufosBy('le', self.tufosByLe)
        self.initTufosBy('gt', self.tufosByGt)
        self.initTufosBy('lt', self.tufosByLt)
        # link events from the Storage back to the core Eventbus
        self.link(core.dist)
        def linkfini():
            self.unlink(core.dist)
        self.onfini(linkfini)
        # Give the storage layers a change to hook anything else they may optimize
        self._postCoreRegistration(core)

    # Handlers which should be untouched!!!
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

    def reqSizeByMeth(self, name):
        meth = self.sizebymeths.get(name)
        if meth is None:
            raise s_common.NoSuchGetBy(name=name)
        return meth

    def reqRowsByMeth(self, name):
        meth = self.rowsbymeths.get(name)
        if meth is None:
            raise s_common.NoSuchGetBy(name=name)
        return meth

    def _defaultFiniCoreStor(self):
        # Remove refs to the parent Cortex object for GC purposes
        delattr(self, 'getPropDef')
        delattr(self, 'getPropNorm')
        delattr(self, 'initTufosBy')
        # Close out savefile buses
        self.savebus.fini()
        self.loadbus.fini()

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

        xact = self.getStoreXact(size)
        self._core_xacts[iden] = xact
        return xact

    def _popCoreXact(self):
        # Used by the CoreXact fini routine
        self._core_xacts.pop(s_threads.iden(), None)

    # TODO: Wrap this in a userauth layer
    def getBlobValu(self, key, default=None):
        '''
        Get a value from the blob key/value (KV) store.

        This resides below the tufo storage layer and is Cortex implementation
        dependent. In purely memory backed cortexes, this KV store may not be
        persistent, even if the tufo-layer is persistent, through something
        such as the savefile mechanism.

        Notes:
            Data which is retrieved from the KV store is msgpacked, so caveats
            with that apply.

        Args:
            key (str): Value to retrieve
            default: Value returned if the key is not present in the blob store.

        Returns:
            The value from the KV store or the default valu (None).

        '''
        buf = self._getBlobValu(key)
        if buf is None:
            self.log(logging.WARNING, mesg='Requested key not present in blob store, returning default', name=key)
            return default
        return s_common.msgunpack(buf)

    # TODO: Wrap this in a userauth layer
    def getBlobKeys(self):
        '''
        Get a list of keys in the blob key/value store.

        Returns:
            list: List of keys in the store.
        '''
        return self._getBlobKeys()

    # TODO: Wrap this in a userauth layer
    def setBlobValu(self, key, valu):
        '''
        Set a value from the blob key/value (KV) store.

        This resides below the tufo storage layer and is Cortex implementation
        dependent. In purely memory backed cortexes, this KV store may not be
        persistent, even if the tufo-layer is persistent, through something
        such as the savefile mechanism.

        Notes:
            Data which is stored in the KV store is msgpacked, so caveats with
            that apply.

        Args:
            key (str): Name of the value to store.
            valu: Value to store in the KV store.

        Returns:
            The input value, unchanged.
        '''
        buf = s_common.msgenpack(valu)
        self._setBlobValu(key, buf)
        self.savebus.fire('syn:core:blob:set', key=key, valu=buf)
        return valu

    # TODO: Wrap this in a userauth layer
    def hasBlobValu(self, key):
        '''
        Check the blob store to see if a key is present.

        Args:
            key (str): Key to check

        Returns:
            bool: If the key is present, returns True, otherwise False.

        '''
        return self._hasBlobValu(key)

    # TODO: Wrap this in a userauth layer
    def delBlobValu(self, key):
        '''
        Remove and return a value from the blob store.

        Args:
            key (str): Key to remove.

        Returns:
            Content in the blob store for a given key.

        Raises:
            NoSuchName: If the key is not present in the store.
        '''
        if not self.hasBlobValu(key):
            raise s_common.NoSuchName(name=key, mesg='Cannot delete key which is not present in the blobstore.')
        buf = self._delBlobValu(key)
        self.savebus.fire('syn:core:blob:del', key=key)
        return s_common.msgunpack(buf)

    def _onSetBlobValu(self, mesg):
        key = mesg[1].get('key')
        valu = mesg[1].get('valu')
        self._setBlobValu(key, valu)

    def _onDelBlobValu(self, mesg):
        key = mesg[1].get('key')
        self._delBlobValu(key)

    def addSaveLink(self, func):
        '''
        Add an event callback to receive save events for this cortex.

        Example:

            def savemesg(mesg):
                dostuff()

            core.addSaveLink(savemesg)

        '''
        self.savebus.link(func)

    def setSaveFd(self, fd, load=True, fini=False):
        '''
        Set a save fd for the cortex and optionally load.

        Args:
            fd (file):  A file like object to save splice events to using msgpack
            load (bool):    If True, load splice event from fd before starting to record
            fini (bool):    If True, close() the fd automatically on cortex fini()

        Returns:
            (None)

        Example:

            core.setSaveFd(fd)

        NOTE: This save file is allowed to be storage layer specific.
              If you want to store cortex splice events, use addSpliceFd().

        '''
        self._setSaveFd(fd, load, fini)

    def addRows(self, rows):
        [reqstor(p, v) for (i, p, v, t) in rows]
        self.savebus.fire('core:save:add:rows', rows=rows)
        self._addRows(rows)

    def _loadAddRows(self, mesg):
        self._addRows(mesg[1].get('rows'))

    def delRowsById(self, iden):
        self.savebus.fire('core:save:del:rows:by:iden', iden=iden)
        self._delRowsById(iden)

    def _loadDelRowsById(self, mesg):
        self._delRowsById(mesg[1].get('iden'))

    def delRowsByIdProp(self, iden, prop, valu=None):
        self.savebus.fire('core:save:del:rows:by:idprop', iden=iden, prop=prop, valu=valu)
        return self._delRowsByIdProp(iden, prop, valu=valu)

    def _loadDelRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        self._delRowsByIdProp(iden, prop)

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete rows with a given prop[=valu].
        Example:
            core.delRowsByProp('foo',valu=10)
        '''
        self.savebus.fire('core:save:del:rows:by:prop', prop=prop, valu=valu, mintime=mintime, maxtime=maxtime)
        return self._delRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime)

    def _loadDelRowsByProp(self, mesg):
        prop = mesg[1].get('prop')
        valu = mesg[1].get('valu')
        mint = mesg[1].get('mintime')
        maxt = mesg[1].get('maxtime')
        self._delRowsByProp(prop, valu=valu, mintime=mint, maxtime=maxt)

    def setRowsByIdProp(self, iden, prop, valu):
        reqstor(prop, valu)
        self.savebus.fire('core:save:set:rows:by:idprop', iden=iden, prop=prop, valu=valu)
        self._setRowsByIdProp(iden, prop, valu)

    def _loadSetRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        valu = mesg[1].get('valu')
        self._setRowsByIdProp(iden, prop, valu)

    def rowsToTufos(self, rows):
        '''
        Convert rows into tufos
        Args:
            rows:

        Returns:

        '''
        res = collections.defaultdict(dict)
        [res[i].__setitem__(p, v) for (i, p, v, t) in rows]
        return list(res.items())

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
        vsn_str = 'syn:core:{}:version'.format(self.getStoreType())
        curv = self.getBlobValu(vsn_str, -1)

        maxver = revs[-1][0]
        if maxver == curv:
            return

        name = 'rev:storage'
        if not self.getConfOpt(name):
            mesg = 'add rev:storage=1 to cortex url to allow storage updates'
            self.log(level=logging.WARNING, mesg=mesg, name=name,)
            logger.warning(mesg)
            return

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

    # The following MUST be implemented by the storage layer in order to
    # support the basic idea of a cortex

    def _initCoreStor(self):
        raise s_common.NoSuchImpl(name='_initCoreStor', mesg='Store does not implement _initCoreStor')

    def getStoreType(self):  # pragma: no cover
        raise s_common.NoSuchImpl(name='getStoreType', mesg='Store does not implement getStoreType')

    def getStoreXact(self, size=None):
        raise s_common.NoSuchImpl(name='getStoreXact', mesg='Store does not implement getStoreXact')

    def _addRows(self, rows):
        raise s_common.NoSuchImpl(name='_addRows', mesg='Store does not implement _addRows')

    def getRowsById(self, iden):
        raise s_common.NoSuchImpl(name='getRowsById', mesg='Store does not implement getRowsById')

    def getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        raise s_common.NoSuchImpl(name='getRowsByProp', mesg='Store does not implement getRowsByProp')

    def getRowsByIdProp(self, iden, prop, valu=None):
        raise s_common.NoSuchImpl(name='getRowsByIdProp', mesg='Store does not implement _getRowsBgetRowsByIdPropyIdProp')

    def _delRowsById(self, iden):
        raise s_common.NoSuchImpl(name='_delRowsById', mesg='Store does not implement _delRowsById')

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        raise s_common.NoSuchImpl(name='_delRowsByProp', mesg='Store does not implement _delRowsByProp')

    def _delRowsByIdProp(self, iden, prop, valu=None):
        raise s_common.NoSuchImpl(name='_delRowsByIdProp', mesg='Store does not implement _delRowsByIdProp')

    def getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
        raise s_common.NoSuchImpl(name='getSizeByProp', mesg='Store does not implement getSizeByProp')

    def rowsByRange(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='rowsByRange', mesg='Store does not implement rowsByRange')

    def sizeByGe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='sizeByGe', mesg='Store does not implement sizeByGe')

    def rowsByGe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='rowsByGe', mesg='Store does not implement rowsByGe')

    def sizeByLe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='sizeByLe', mesg='Store does not implement sizeByLe')

    def rowsByLe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='rowsByLe', mesg='Store does not implement rowsByLe')

    def sizeByRange(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='sizeByRange', mesg='Store does not implement sizeByRange')

    def tufosByGe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='tufosByGe', mesg='Store does not implement tufosByGe')

    def tufosByLe(self, prop, valu, limit=None):
        raise s_common.NoSuchImpl(name='tufosByLe', mesg='Store does not implement tufosByLe')

    def _getBlobValu(self, key):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_getBlobValu', mesg='Store does not implement _getBlobValu')

    def _setBlobValu(self, key, valu):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_setBlobValu', mesg='Store does not implement _setBlobValu')

    def _hasBlobValu(self, key):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_hasBlobValu', mesg='Store does not implement _hasBlobValu')

    def _delBlobValu(self, key):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_delBlobValu', mesg='Store does not implement _delBlobValu')

    def _getBlobKeys(self):
        raise s_common.NoSuchImpl(name='_getBlobKeys', mesg='Store does not implement _getBlobKeys')

    def _genStoreRows(self, **kwargs):
        raise s_common.NoSuchImpl(name='_genStoreRows', mesg='Store does not implement _genStoreRows')

    # The following are things which SHOULD be overridden in order to provide
    # cortex features which are kind of optional

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
            rows = self.getRowsByIdProp(iden, prop)
            if len(rows) == 0:
                raise s_common.NoSuchTufo(iden=iden, prop=prop)

            oldv = rows[0][2]
            newv = oldv + incval

            self._setRowsByIdProp(iden, prop, newv)

            tufo[1][prop] = newv
            self.fire('node:prop:set', form=form, valu=valu, prop=prop, newv=newv, oldv=oldv, node=tufo)

        return tufo

    def getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit):
            for jrow in self.getRowsById(irow[0]):
                yield jrow

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

            self._delRowsById(iden)
            done.add(iden)

    def _setSaveFd(self, fd, load=True, fini=False):
        '''
        The default implementation of savefile for a Cortex.
        This may be overridden by a storage layer.
        '''
        if load:
            for mesg in s_common.msgpackfd(fd):
                self.loadbus.dist(mesg)

        self.onfini(fd.flush)
        if fini:
            self.onfini(fd.close)

        def savemesg(mesg):
            fd.write(s_common.msgenpack(mesg))

        self.savebus.link(savemesg)

    def getTufosByIdens(self, idens):
        # storage layers may optimize here!
        ret = []
        for iden in idens:
            tufo = self.getTufoByIden(iden)
            if tufo is None:
                continue
            ret.append(tufo)
        return ret

    def getTufoByIden(self, iden):
        rows = self.getRowsById(iden)
        if not rows:
            return None
        return (iden, {p: v for (i, p, v, t) in rows})

    def genStoreRows(self, **kwargs):
        for rows in self._genStoreRows(**kwargs):
            yield rows

    # XXX Docstring here!
    def _postCoreRegistration(self, core):
        self.log(level=logging.debug,
                 mesg='Storage layer does not implement _postCortexRegistration')
    # these helpers allow a storage layer to simply implement
    # and register _getTufosByGe and _getTufosByLe

    def rowsByLt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self.rowsByLe(prop, valu - 1, limit=limit)

    def rowsByGt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self.rowsByGe(prop, valu + 1, limit=limit)

    def tufosByLt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self.tufosByLe(prop, valu - 1, limit=limit)

    def tufosByGt(self, prop, valu, limit=None):
        valu, _ = self.getPropNorm(prop, valu)
        return self.tufosByGe(prop, valu + 1, limit=limit)
