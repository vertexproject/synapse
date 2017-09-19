#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
synapse - xact.py.py
Created on 8/1/17.

StoreXact implementation.  This is designed to be subclassed by Storage layer implementors.
"""
import time
import logging

import synapse.common as s_common
import synapse.lib.auth as s_auth

logger = logging.getLogger(__name__)

class StoreXact:
    '''
    A context manager for a storage "transaction".
    '''
    def __init__(self, store, size=None, core=None):
        self.store = store
        self.size = size
        self.core = core

        self.tick = s_common.now()

        self.refs = 0
        self.ready = False
        self.exiting = False

        self.events = []
        self.triggers = []

    def trigger(self, node, name, **info):
        '''
        Fire a trigger from the transaction

        Args:
            node ((str,dict)):  The node for the trigger
            name (str):  The trigger permission string
            info (dict): The trigger permission metadata
        '''
        perm = (name, info)
        self.triggers.append((node, perm))

    def spliced(self, act, **info):
        '''
        Fire a splice event from the transaction.

        Args:
            act (str): Splice action.
            **info: Event values.

        Returns:
            None
        '''
        # Splice events only matter for StoreXacts which have a Cortex
        if not self.core:
            return

        form = info.get('form')

        pdef = self.core.getPropDef(form)
        if pdef is not None and pdef[1].get('local'):
            return

        info['act'] = act
        info['time'] = self.tick
        info['user'] = s_auth.whoami()

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

    def _coreXactBegin(self):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_coreXactBegin')

    def _coreXactCommit(self):  # pragma: no cover
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
        triggers = self.triggers

        self.events = []
        self.triggers = []

        [self.store.fire(name, **props) for (name, props) in events]

        if self.core is not None:
            for node, perm in triggers:
                self.core._fireNodeTrig(node, perm)

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
