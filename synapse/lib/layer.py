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

        self.layr = layr
        self.write = write

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
        raise NotImplementedError

    def getOffset(self, iden):
        raise NotImplementedError

    def stor(self, sops):
        '''
        Execute a series of storage operations.
        '''
        raise NotImplementedError

    def getLiftRows(self, lops):
        raise NotImplementedError

    def abort(self):
        raise NotImplementedError

    def commit(self):
        raise NotImplementedError

    def getBuidProps(self, buid):
        raise NotImplementedError

    def _storPropSet(self, oper):
        raise NotImplementedError

    def _storPropDel(self, oper):
        raise NotImplementedError

    def _liftByFormRe(self, oper):
        raise NotImplementedError

    def _liftByUnivRe(self, oper):
        raise NotImplementedError

    def _liftByPropRe(self, oper):
        raise NotImplementedError

    def _liftByIndx(self, oper):
        raise NotImplementedError

    def _rowsByEq(self, curs, pref, valu):
        raise NotImplementedError

    def _rowsByPref(self, curs, pref, valu):
        raise NotImplementedError

    def _rowsByRange(self, curs, pref, valu):
        raise NotImplementedError

    def iterFormRows(self, form):
        '''
        Iterate (buid, valu) rows for the given form in this layer.
        '''
        raise NotImplementedError

    def iterPropRows(self, form, prop):
        '''
        Iterate (buid, valu) rows for the given form:prop in this layer.
        '''
        raise NotImplementedError

    def iterUnivRows(self, prop):
        '''
        Iterate (buid, valu) rows for the given universal prop
        '''
        raise NotImplementedError

class Layer(s_cell.Cell):
    '''
    A layer implements btree indexed storage for a cortex.

    TODO:
        metadata for layer contents (only specific type / tag)
    '''
    def __init__(self, dirn):
        s_cell.Cell.__init__(self, dirn)

    def getOffset(self, iden):
        raise NotImplementedError

    def setOffset(self, iden, offs):
        raise NotImplementedError

    def splices(self, offs, size):
        raise NotImplementedError

    def xact(self, write=False):
        '''
        Return a transaction object for the layer.
        '''
        return Xact(self, write=write)

