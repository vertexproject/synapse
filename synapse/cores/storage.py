#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
synapse - storage.py
Created on 7/19/17.

Base storage layer implementation for Synapse Cortex class.
See Storage class for more information.
"""
# Stdlib
import logging
import threading
# Custom Code
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.cores.xact as s_xact

import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads

from synapse.common import reqstor

logger = logging.getLogger(__name__)

class Storage(s_config.Config):
    '''
    Base class for Cortex storage layer backends.

    This implements functionality which is needed for a storage layer to
    operate, as well as providing stubs for the storage layer implementations
    to override.  See the Synapse Documentation for more details.

    Args:
        link ((str, dict)): Link tufo containing information for creating the Storage object.  This may include path
                            information, authentication information, etc.
        **conf (dict):  Additional configible options for the storage layer.
    '''
    def __init__(self,
                 link,
                 **conf):
        s_config.Config.__init__(self)
        if conf:
            self.setConfOpts(conf)

        #############################################################
        # buses to save/load *raw* save events
        #############################################################
        self.savebus = s_eventbus.EventBus()
        self.loadbus = s_eventbus.EventBus()

        self._link = link

        self.onfini(self._defaultFiniCoreStor)

        # Various locks
        self.xlock = threading.Lock()
        # Transactions are a storage-layer concept
        self._store_xacts = {}

        # Dicts for storing retrieval methods
        self.sizebymeths = {}
        self.rowsbymeths = {}
        self.joinsbymeths = {}

        # Register handlers for lifting rows/sizes/joins
        self.initRowsBy('gt', self.rowsByGt)
        self.initRowsBy('lt', self.rowsByLt)
        self.initRowsBy('ge', self.rowsByGe)
        self.initRowsBy('le', self.rowsByLe)
        self.initRowsBy('range', self.rowsByRange)

        self.initSizeBy('ge', self.sizeByGe)
        self.initSizeBy('le', self.sizeByLe)
        self.initSizeBy('range', self.sizeByRange)

        self.initJoinsBy('ge', self._joinsByGe)
        self.initJoinsBy('gt', self._joinsByGt)
        self.initJoinsBy('le', self._joinsByLe)
        self.initJoinsBy('lt', self._joinsByLt)
        self.initJoinsBy('in', self._joinsByIn)
        self.initJoinsBy('range', self._joinsByRange)

        # Events for handling savefile loads/saves
        self.loadbus.on('core:save:add:rows', self._loadAddRows)
        self.loadbus.on('core:save:del:rows:by:iden', self._loadDelRowsById)
        self.loadbus.on('core:save:del:rows:by:prop', self._loadDelRowsByProp)
        self.loadbus.on('core:save:set:rows:by:idprop', self._loadSetRowsByIdProp)
        self.loadbus.on('core:save:del:rows:by:idprop', self._loadDelRowsByIdProp)
        self.loadbus.on('core:save:set:up:prop', self._loadUpdateProperty)
        self.loadbus.on('core:save:set:up:propvalu', self._loadUpdatePropertyValu)
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

    @staticmethod
    @s_config.confdef(name='storage')
    def _storage_confdefs():
        confdefs = (
            ('rev:storage', {'type': 'bool', 'defval': 1, 'doc': 'Set to 0 to disallow storage version updates'}),
        )
        return confdefs

    def setModlVers(self, name, vers):
        '''
        Set the version number for a specific model.

        Args:
            name (str): The name of the model
            vers (int): The new (linear) version number

        Returns:
            (None)

        '''
        prop = '.:modl:vers:' + name
        with self.getCoreXact() as xact:

            rows = tuple(self.getRowsByProp(prop))

            if rows:
                iden = rows[0][0]
            else:
                iden = s_common.guid()

            self.fire('modl:vers:set', name=name, vers=vers)
            self.setRowsByIdProp(iden, prop, vers)
            return vers

    def initRowsBy(self, name, meth):
        '''
        Initialize a "rows by" handler for the Storage layer.

        These helpers are used by the Cortex to do special types of lifts.
        This allows different Storage layers to implement certain lifts in a optimized fashion.

        Args:
            name (str): Named handler to register.
            meth (func): Function to register.

        Examples:
            Registering a 'woot' handler::

                def getbywoot(prop,valu,limit=None):
                    return stuff() # list of rows

                core.initRowsBy('woot',getbywoot)

        Returns:
            None
        '''
        self.rowsbymeths[name] = meth

    def initSizeBy(self, name, meth):
        '''
        Initialize a "size by" handler for the Storage layer.

        These helpers are used by the Cortex to do size by lifts.
        This allows different Storage layers to implement certain lifts in a optimized fashion.

        Args:
            name (str): Named handler to register.
            meth (func): Function to register.

        Examples:
            Registering a 'woot' handler::

                def sizebywoot(prop,valu,limit=None):
                    return stuff() # size of rows

                core.initSizeBy('woot',meth)

        Returns:
            None
        '''
        self.sizebymeths[name] = meth

    def initJoinsBy(self, name, meth):
        '''
        Initialize a "joins by" handler for the Storage layer.

        These helpers are used by the Cortex to do special types of lifts.
        This allows different Storage layers to implement certain lifts in a optimized fashion.

        Args:
            name (str): Named handler to register.
            meth (func): Function to register.

        Examples:
            Registering a 'woot' handler::

                def getbywoot(prop,valu,limit=None):
                    return stuff() # list of rows

                core.initJoinsBy('woot',getbywoot)

        Returns:
            None
        '''
        self.joinsbymeths[name] = meth

    def reqSizeByMeth(self, name):
        '''
        Get a handler for a SizeBy lift.

        Args:
            name (str): Name of the registered handler to retrieve.

        Returns:
            Function used to lift by size.

        Raises:
            NoSuchGetBy: If the named handler does not exist.
        '''
        meth = self.sizebymeths.get(name)
        if meth is None:
            raise s_common.NoSuchGetBy(name=name)
        return meth

    def reqRowsByMeth(self, name):
        '''
        Get a handler for a RowsBy lift.

        Args:
            name (str): Name of the registered handler to retrieve.

        Returns:
            Function used to lift by rows.

        Raises:
            NoSuchGetBy: If the named handler does not exist.
        '''
        meth = self.rowsbymeths.get(name)
        if meth is None:
            raise s_common.NoSuchGetBy(name=name)
        return meth

    def reqJoinByMeth(self, name):
        '''
        Get a handler for a JoinBy lift.

        Args:
            name (str): Name of the registered handler to retrieve.

        Returns:
            Function used to lift joined rows.

        Raises:
            NoSuchGetBy: If the named handler does not exist.
        '''
        meth = self.joinsbymeths.get(name)
        if meth is None:
            raise s_common.NoSuchGetBy(name=name)
        return meth

    def getJoinsBy(self, name, prop, valu, limit=None):
        '''
        Retrieve joined rows by either a sepecified method or by falling back
        to the rowsBy handlers. Specialized methods will be dependent on the
        storage backind and the data indexed.

        Args:
            name (str): Name of the method to look up.
            prop (str): Prop to filter by.
            valu: Value (or values) to pass to the helper method.
            limit (int): Limit on the join.  Limit meaning may vary by
                implementation or named helper.

        Returns:

        '''
        meth = self.joinsbymeths.get(name)
        if not meth:
            meth = self.reqRowsByMeth(name)
            rows = meth(prop, valu, limit=limit)
            return self.getRowsByIdens({i for (i, p, v, t) in rows})
        return meth(prop, valu, limit=limit)

    def _defaultFiniCoreStor(self):
        '''
        Default fini handler. Do not override.
        '''
        # Close out savefile buses
        self.savebus.fini()
        self.loadbus.fini()

    def getCoreXact(self, size=1000, core=None):
        '''
        Get a Storage transaction context for use in a with block.

        This object allows bulk storage layer optimization and proper ordering
        of events.

        Args:
            size (int): Number of transactions to cache before starting to
                execute storage layer events.
            core: Cortex to attach to the StoreXact. Required for splice
                event support.

        Examples:
            Get a StoreXact object and use it::

                with store.getCoreXact() as xact:
                    store.dostuff()

        Returns:
            s_xact.StoreXact: A StoreXact object for the current thread.
        '''
        iden = s_threads.iden()

        xact = self._store_xacts.get(iden)
        if xact is not None:
            return xact

        xact = self.getStoreXact(size, core=core)
        self._store_xacts[iden] = xact
        return xact

    def _popCoreXact(self):
        # Used by the CoreXact fini routine
        self._store_xacts.pop(s_threads.iden(), None)

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
        return s_msgpack.un(buf)

    def getBlobKeys(self):
        '''
        Get a list of keys in the blob key/value store.

        Returns:
            list: List of keys in the store.
        '''
        return self._getBlobKeys()

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
        buf = s_msgpack.en(valu)
        self._setBlobValu(key, buf)
        self.savebus.fire('syn:core:blob:set', key=key, valu=buf)
        return valu

    def hasBlobValu(self, key):
        '''
        Check the blob store to see if a key is present.

        Args:
            key (str): Key to check

        Returns:
            bool: If the key is present, returns True, otherwise False.

        '''
        return self._hasBlobValu(key)

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
        return s_msgpack.un(buf)

    def _onSetBlobValu(self, mesg):
        key = mesg[1].get('key')
        valu = mesg[1].get('valu')
        self._setBlobValu(key, valu)

    def _onDelBlobValu(self, mesg):
        key = mesg[1].get('key')
        self._delBlobValu(key)

    def addSaveLink(self, func):
        '''
        Add an event callback to receive save events for this Storage object.

        Args:
            func: Function to receive events from the Storage savebus.

        Examples:
            Register a function to receive events::

                def savemesg(mesg):
                    dostuff()

                core.addSaveLink(savemesg)

        Returns:
            None
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

            store.setSaveFd(fd)

        NOTE: This save file is allowed to be storage layer specific.
              If you want to store cortex splice events, use addSpliceFd() from the Cortex class.
        '''
        self._setSaveFd(fd, load, fini)

    def addRows(self, rows):
        '''
        Add (iden, prop, valu, time) rows to the Storage object.

        Args:
            rows (list): List of rows containing (i, p, v, t) tuples.

        Examples:
            Adding a pair of rows to the storage object::

                import time
                tick = now()

                rows = [
                    (id1,'baz',30,tick),
                    (id1,'foo','bar',tick),
                ]

                store.addRows(rows)

        Notes:
            The general convention for the iden value is a 16 byte hex string,
            such as "e190d108bdd30a035a15764313f4c397". These can be made with
            the synapse.common.guid() function.  While the storage layer is
            free to STORE these idens however it sees fit, some tools may
            expect that, at the public row level APIs, idens may conform to
            that shape. If other types of idens are put into the system, that
            could cause unintentional issues.

            This does fire a "core:save:add:rows" event on the savebus to save
            the raw rows which are being send to the storage layer.

        Returns:
            None
        '''
        [reqstor(p, v) for (i, p, v, t) in rows]
        self.savebus.fire('core:save:add:rows', rows=rows)
        self._addRows(rows)

    def _loadAddRows(self, mesg):
        self._addRows(mesg[1].get('rows'))

    def delRowsById(self, iden):
        '''
        Delete all the rows for a given iden.

        Args:
            iden (str): Iden to delete rows for.

        Examples:
            Delete the rows for a given iden::

                store.delRowsById(iden)

        Notes:
            This does fire a "core:save:del:rows:by:iden" event on the savebus
            to record which rows were deleted.

        Returns:
            None
        '''
        self.savebus.fire('core:save:del:rows:by:iden', iden=iden)
        self._delRowsById(iden)

    def _loadDelRowsById(self, mesg):
        self._delRowsById(mesg[1].get('iden'))

    def delRowsByIdProp(self, iden, prop, valu=None):
        '''
        Delete rows with the given combination of iden and prop[=valu].

        Args:
            iden (str): Iden to delete rows for.
            prop (str): Prop to delete rows for.
            valu: Optional value to check. If present, only delete iden/prop
                rows with this value.

        Examples:
            Delete all 'foo' rows for a given iden::

                store.delRowsByIdProp(iden, 'foo')

        Notes:
            This does fire a "core:save:del:rows:by:idprop" event on the
            savebus to record which rows were deleted.

        Returns:
            None
        '''
        self.savebus.fire('core:save:del:rows:by:idprop', iden=iden, prop=prop, valu=valu)
        return self._delRowsByIdProp(iden, prop, valu=valu)

    def _loadDelRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        self._delRowsByIdProp(iden, prop)

    def delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
        '''
        Delete rows with a given property (and optional valu) combination.

        Args:
            prop (str): Property to delete.
            valu: Optional value to constrain the property deletion by.
            mintime (int): Optional, minimum time in which to constrain the
                deletion by.
            maxtime (int): Optional, maximum time in which to constrain the
                deletion by.

        Examples:
            Delete all 'foo' rows with the valu=10::

                store.delRowsByProp('foo',valu=10)

        Notes:
            This does fire a "core:save:del:rows:by:prop" event on the
            savebus to record which rows were deleted.

        Returns:
            None
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
        '''
        Update or insert the value of the row(s) with iden and prop to valu.

        Args:
            iden (str): Iden to update.
            prop (str): Property to update.
            valu: Value to set.

        Examples:
            Set the foo=10 value on a given iden::



        Notes:
            This does fire a "core:save:set:rows:by:idprop" event on the
            savebus to save the changes which are being sent to the storage
            layer.

        Returns:
            None
        '''
        reqstor(prop, valu)
        self.savebus.fire('core:save:set:rows:by:idprop', iden=iden, prop=prop, valu=valu)
        self._setRowsByIdProp(iden, prop, valu)

    def _loadSetRowsByIdProp(self, mesg):
        iden = mesg[1].get('iden')
        prop = mesg[1].get('prop')
        valu = mesg[1].get('valu')
        self._setRowsByIdProp(iden, prop, valu)

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
            mesg = 'add rev:storage=1 to storage confs to allow storage updates'
            self.log(level=logging.WARNING, mesg=mesg, name=name)
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

    def genStoreRows(self, **kwargs):
        '''
        A generator which yields raw rows from the storage layer.

        Args:
            **kwargs: Arguments which are passed to the storage layer
                implementation of _genStoreRows().

        Notes:
            Since this is intended for use as a backup mechanism for a Storage
            object, it is not to be considered a performant API.

        Yields:
            list: List of rows.  The number of rows and contents
            will vary by implementation.
        '''
        for rows in self._genStoreRows(**kwargs):
            yield rows

    def _loadUpdateProperty(self, mesg):
        oldprop = mesg[1].get('oldprop')
        newprop = mesg[1].get('newprop')
        self._updateProperty(oldprop, newprop)

    def updateProperty(self, oldprop, newprop):
        '''
        Do a wholesale replacement of one property with another property.

        Args:
            oldprop (str): The orginal property which is removed.
            newprop (str): The property that is updated in place.

        Examples:
            Rename "inet:tcp4:port" to "inet:tcp4:foobar"::

                nrows = store.updateProperty('inet:tcp4:port', 'inet:tcp4:foobar')

        Notes:
            This API does  fire syn:core:store:up:prop:pre and syn:core:store:up:prop:post events with the old
            and new property names in it, before and after the property update is done. This API is primarily designed
            for assisting with Cortex data migrations.

        Returns:
            int: Number of rows updated in place.
        '''
        if oldprop == newprop:
            raise s_common.BadPropName(mesg='OldProp and newprop cannot be the same.',
                                       oldprop=oldprop, newprop=newprop)

        if not isinstance(newprop, str):
            raise s_common.BadPropName(mesg='newprop must be a str', newprop=newprop)

        self.savebus.fire('core:save:set:up:prop', oldprop=oldprop, newprop=newprop)
        self.fire('syn:core:store:up:prop:pre', oldprop=oldprop, newprop=newprop)
        nrows = self._updateProperty(oldprop, newprop)
        self.fire('syn:core:store:up:prop:post', oldprop=oldprop, newprop=newprop, nrows=nrows)
        return nrows

    def _loadUpdatePropertyValu(self, mesg):
        prop = mesg[1].get('prop')
        oldval = mesg[1].get('oldval')
        newval = mesg[1].get('newval')
        self._updatePropertyValu(prop, oldval, newval)

    def updatePropertyValu(self, prop, oldval, newval):
        '''
        Do a wholesale update of one property=valu combination with a new valu.

        Args:
            prop (str): Property to select by for updating.
            oldval: Old valu to select rows by.
            newval: Valu to set the the prop=oldval rows to be.

        Examples:
            Rename "tufo:form"="inet:tcp4" to instead be "tufo:form"="inet:tcp4000"::

                nrows = store.updatePropertyValu('tufo:form', 'inet:tcp4', 'inet:tcp4000')

        Notes:
            This API does fire syn:core:store:up:propval:pre and syn:core:store:up:propval:post
            events with the property, old value and new values in it; before and after update is done. This API is
            primarily designed for assisting with Cortex data migrations.  The oldval and newval must be of the same
            type.

        Returns:
            int: Number of rows updated in place.
        '''
        if oldval == newval:
            raise s_common.SynErr(mesg='oldval and newval cannot be the same.',
                                  oldval=oldval, newval=newval)

        if not isinstance(newval, (int, str)):
            raise s_common.BadPropValu(mesg='newval must be a str or int', newval=newval)
        if not isinstance(oldval, type(newval)):
            raise s_common.BadPropValu(mesg='oldval and newval must be of the same type',
                                       newval=newval, oldval=oldval)

        self.savebus.fire('core:save:set:up:propvalu', prop=prop, oldval=oldval, newval=newval)
        self.fire('syn:core:store:up:propval:pre', prop=prop, oldval=oldval, newval=newval)
        nrows = self._updatePropertyValu(prop, oldval, newval)
        self.fire('syn:core:store:up:propval:post', prop=prop, oldval=oldval, newval=newval, nrows=nrows)
        return nrows

    # The following MUST be implemented by the storage layer in order to
    # support the basic idea of a cortex

    def _initCoreStor(self):  # pragma: no cover
        '''
        This is called to initialize any implementation specific resources.

        This is where things like filesystem allocations, DB connections,
        et cetera should be stood up.

        If the Storage layer has additional joinBy* handlers which it needs
        to register (for the purpose of the Cortex.getTufosBy() function),
        it should add them in this function.

        Returns:
            None
        '''
        raise s_common.NoSuchImpl(name='_initCoreStor', mesg='Store does not implement _initCoreStor')

    def getStoreType(self):  # pragma: no cover
        '''
        Get the Store type.

        This may be used by the Cortex to determine what its backing
        store is.

        Returns:
            str: String indicating what the backing storage layer is.
        '''
        raise s_common.NoSuchImpl(name='getStoreType', mesg='Store does not implement getStoreType')

    def getStoreXact(self, size=None, core=None):  # pragma: no cover
        '''
        Get a StoreXact object.

        This is normally called by the getCoreXact function.

        Args:
            size (int): Number of events to cache in the transaction before
                executing them.
            core: Cortex to attach to the transaction.  Required for splice
                event support.

        Returns:
            s_xact.StoreXact: A storage layer specific StoreXact object.
        '''
        raise s_common.NoSuchImpl(name='getStoreXact', mesg='Store does not implement getStoreXact')

    def _addRows(self, rows):  # pragma: no cover
        '''
        This should perform the actual addition of rows to the storage layer.

        Args:
            rows (list): Rows to add to the Storage layer.

        Returns:
            None
        '''
        raise s_common.NoSuchImpl(name='_addRows', mesg='Store does not implement _addRows')

    def getRowsById(self, iden):  # pragma: no cover
        '''
        Return all the rows for a given iden.

        Args:
            iden (str): Iden to get rows from the storage object for.

        Examples:
            Getting rows by iden and doing stuff::

                for row in store.getRowsById(iden):
                    stuff()

            Getting rows by iden and making a tufo out of them::

                rows = store.getRowsById(iden)
                tufo = (iden, {p: v for (i, p, v, t) in rows})

        Returns:
            list: List of rows for a given iden.
        '''
        raise s_common.NoSuchImpl(name='getRowsById', mesg='Store does not implement getRowsById')

    def getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):  # pragma: no cover
        '''
        Get rows from the Storage layer based on their property value
        and other, optional, constraints.

        Args:
            prop (str): Property to retrieve rows based on.
            valu: Optional, str or integer value to constrain the retrieval by.
            mintime (int): Optional, minimum (inclusive) time to constrain the retrieval by.
            maxtime (int): Optiona, maximum (exclusive) time to constrain the retrieval by.
            limit (int): Maximum number of rows to return.

        Returns:
            list: List of (i, p, v, t) rows.
        '''
        raise s_common.NoSuchImpl(name='getRowsByProp', mesg='Store does not implement getRowsByProp')

    def getRowsByIdProp(self, iden, prop, valu=None):  # pragma: no cover
        '''
        Return rows with the given <iden>,<prop>.

        Args:
            iden (str): Iden to get rows from the storage object for.
            prop (str): Prop to constrain the lift by.
            valu: Optional, value to constrain the lift by.

        Examples:
            Getting rows by iden, prop and doing stuff::

                for row in core.getRowsByIdProp(iden,'foo:bar'):
                    dostuff(row)

        Returns:
            list: List of rows for a given iden, prop, value comtination.
        '''
        raise s_common.NoSuchImpl(name='getRowsByIdProp', mesg='Store does not implement _getRowsBgetRowsByIdPropyIdProp')

    def _delRowsById(self, iden):  # pragma: no cover
        '''
        Delete rows from the storage layer with a given iden.
        '''
        raise s_common.NoSuchImpl(name='_delRowsById', mesg='Store does not implement _delRowsById')

    def _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):  # pragma: no cover
        '''
        Delete rows from the storage layer with a given prop and other,
        optional, constraints.
        '''
        raise s_common.NoSuchImpl(name='_delRowsByProp', mesg='Store does not implement _delRowsByProp')

    def _delRowsByIdProp(self, iden, prop, valu=None):  # pragma: no cover
        '''
        Delete rows from the storage layer with a given iden & prop, with an
        optional valu constraint.
        '''
        raise s_common.NoSuchImpl(name='_delRowsByIdProp', mesg='Store does not implement _delRowsByIdProp')

    def getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='getSizeByProp', mesg='Store does not implement getSizeByProp')

    def rowsByRange(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='rowsByRange', mesg='Store does not implement rowsByRange')

    def sizeByGe(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='sizeByGe', mesg='Store does not implement sizeByGe')

    def rowsByGe(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='rowsByGe', mesg='Store does not implement rowsByGe')

    def sizeByLe(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='sizeByLe', mesg='Store does not implement sizeByLe')

    def rowsByLe(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='rowsByLe', mesg='Store does not implement rowsByLe')

    def sizeByRange(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='sizeByRange', mesg='Store does not implement sizeByRange')

    def _joinsByGe(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='joinsByGe', mesg='Store does not implement joinsByGe')

    def _joinsByLe(self, prop, valu, limit=None):  # pragma: no cover
        raise s_common.NoSuchImpl(name='joinsByLe', mesg='Store does not implement joinsByLe')

    def _getBlobValu(self, key):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_getBlobValu', mesg='Store does not implement _getBlobValu')

    def _setBlobValu(self, key, valu):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_setBlobValu', mesg='Store does not implement _setBlobValu')

    def _hasBlobValu(self, key):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_hasBlobValu', mesg='Store does not implement _hasBlobValu')

    def _delBlobValu(self, key):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_delBlobValu', mesg='Store does not implement _delBlobValu')

    def _getBlobKeys(self):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_getBlobKeys', mesg='Store does not implement _getBlobKeys')

    def _genStoreRows(self, **kwargs):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_genStoreRows', mesg='Store does not implement _genStoreRows')

    # The following are default implementations that may be overridden by
    # a storage layer for various reasons.

    def _finiCoreStore(self):  # pragma: no cover
        '''
        This should be overriden to close out any storge layer specifc resources.
        '''
        pass

    def getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        return [row for row in self.genJoinByProp(prop, valu, mintime, maxtime, limit)]

    def genJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
        for irow in self.getRowsByProp(prop, valu=valu, mintime=mintime, maxtime=maxtime, limit=limit):
            for jrow in self.getRowsById(irow[0]):
                yield jrow

    def _joinsByRange(self, prop, valu, limit=None):
        '''
        Default implementation of a 'range' handler for joining rows together
        by.

        Args:
            prop (str): Prop to select joins by.
            valu (list): A list (or tuple) of two items. These should be a
            minvalu, maxvalue pair. These serve as the bound for doing the
            range lift by.
            limit (int): Limit on the umber of rows to lift by range.

        Returns:
            list: List of (i, p, v, t) rows.
        '''
        rows = self.rowsByRange(prop, valu, limit=limit)
        return self.getRowsByIdens({i for i, p, v, t in rows})

    def _joinsByIn(self, prop, valus, limit=None):
        '''
        Default implementation of a 'in' handler for joining rows together by.

        Args:
            prop (str): Prop to select joins by.
            valu (list): A list (or tuple) of values to query a Storage object
                for.  If a empty list is provided, an empty list is returned.
            limit (int): Limit on the number of joined idens to return.

        Returns:
            list: List of (i, p, v, t) rows.

        '''
        if len(valus) == 0:
            return []

        if limit is not None and limit < 1:
                return []

        rows = []
        for valu in valus:
            _rows = list(self.getJoinByProp(prop, valu, limit=limit))
            rows.extend(_rows)
            if limit is not None:
                rowidens = {i for (i, p, v, t) in _rows}
                limit -= len(rowidens)
                if limit <= 0:
                    break
        return rows

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
            for mesg in s_msgpack.iterfd(fd):
                self.loadbus.dist(mesg)

        self.onfini(fd.flush)
        if fini:
            self.onfini(fd.close)

        def savemesg(mesg):
            fd.write(s_msgpack.en(mesg))

        self.savebus.link(savemesg)

    def getRowsByIdens(self, idens):
        '''
        Return all the rows for a given list of idens.

        Args:
            idens (list): Idens to get rows from the storage object for.

        Examples:
            Getting rows by idens and doing stuff::

                for row in store.getRowsByIdens(idens):
                    stuff(row)

            Getting rows by idens and making a tufos out of them::

                rows = store.getRowsById(iden)
                tufos = s_common.rowstotufos(rows)

        Returns:
            list: List of rows for the given idens.
        '''
        ret = []
        for iden in idens:
            rows = self.getRowsById(iden)
            ret.extend(rows)
        return ret

    def _updateProperty(self, oldprop, newprop):
        '''
        Entrypoint for doing in-place property update type operations.
        This is called by self.updateProperty() to do the actual property update.
        '''
        adds = []
        for i, p, v, t in self.getRowsByProp(oldprop):
            adds.append((i, newprop, v, t))

        if adds:
            self._addRows(adds)
            self._delRowsByProp(oldprop)

        return len(adds)

    def _updatePropertyValu(self, prop, oldval, newval):
        '''
        Entrypoint for doing in-place property value update type operations.
        This is called by self.updatePropertyValu() to do the actual property update.
        '''
        adds = []
        rows = self.getRowsByProp(prop, oldval)
        for i, p, v, t in rows:
            adds.append((i, p, newval, t))

        if adds:
            self._delRowsByProp(prop, oldval)
            self._addRows(adds)
        return len(adds)

    # these helpers allow a storage layer to simply implement
    # and register _getTufosByGe and _getTufosByLe

    def rowsByLt(self, prop, valu, limit=None):
        return self.rowsByLe(prop, valu - 1, limit=limit)

    def rowsByGt(self, prop, valu, limit=None):
        return self.rowsByGe(prop, valu + 1, limit=limit)

    def _joinsByLt(self, prop, valu, limit=None):
        return self._joinsByLe(prop, valu - 1, limit=limit)

    def _joinsByGt(self, prop, valu, limit=None):
        return self._joinsByGe(prop, valu + 1, limit=limit)
