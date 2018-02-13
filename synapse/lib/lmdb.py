import struct
import itertools

import synapse.lib.msgpack as s_msgpack

STOR_FLAG_NOINDEX = 0x0001      # there is no byprop index for this prop
STOR_FLAG_MULTIVAL = 0x0002     # this is a multi-value prop
STOR_FLAG_DEFVAL = 0x0004       # Only set this if it doesn't exist

class Seqn:
    '''
    An append optimized sequence of byte blobs.

    Args:
        lenv (lmdb.Environment): The LMDB Environment.
        name (str): The name of the sequence.
    '''
    def __init__(self, lenv, name):

        self.lenv = lenv
        self.db = lenv.open_db(name)

        with lenv.begin() as xact:

            indx = 0
            with xact.cursor(db=self.db) as curs:
                if curs.last():
                    indx = struct.unpack('>Q', curs.key())[0] + 1

            self.indx = itertools.count(indx)

    def save(self, xact, items):
        '''
        Save a series of items to a sequence.

        Args:
            xact (lmdb.Transaction): The LMDB Transaction.
            items (tuple): The series of items to save into the sequence.

        Returns:
            None
        '''
        rows = []
        for item in items:
            byts = s_msgpack.en(item)
            lkey = struct.pack('>Q', next(self.indx))
            rows.append((lkey, byts))

        with xact.cursor(db=self.db) as curs:
            curs.putmulti(rows, append=True)

    def iter(self, xact, offs):
        '''
        Iterate over items in a sequence from a given offset.

        Args:
            xact (lmdb.Transaction): The LMDB Transaction.
            offs (int): The offset to begin iterating from.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        lkey = struct.pack('>Q', offs)
        with xact.cursor(db=self.db) as curs:

            if not curs.set_key(lkey):
                return

            for lkey, lval in curs.iternext():
                indx = struct.unpack('>Q', lkey)[0]
                valu = s_msgpack.un(lval)
                yield indx, valu

class Metrics:

    def __init__(self, lenv, name=b'metrics'):

        self.lenv = lenv

        self._db_history = lenv.open_db(name + b':history')
        self._db_current = lenv.open_db(name + b':current')

        self.info = {}

        with lenv.begin() as xact:

            for lkey, lval in xact.cursor(db=self._db_current):

                name = lkey.decode('utf8')
                valu = struct.unpack('>Q', lval)[0]

                self.info[name] = valu

            indx = 0

            curs = xact.cursor(db=self._db_history)
            if curs.last():
                indx = struct.unpack('>Q', curs.key())[0]

            self.indx = itertools.count(indx)

    def inc(self, xact, prop, step=1):
        '''
        Increment the value of a global metric.
        '''
        valu = self.info.get(prop, 0)
        valu += step

        self.info[prop] = valu

        penc = prop.encode('utf8')
        pval = struct.pack('>Q', valu)

        xact.put(penc, pval, db=self._db_current)

    def stat(self):
        return self.info

    def iter(self, xact, offs):

        lkey = struct.pack('>Q', offs)

        with xact.cursor(db=self._db_history) as curs:

            if not curs.set_key(lkey):
                return

            for lkey, lval in curs.iternext():

                indx = struct.unpack('>Q', lkey)[0]
                sample = s_msgpack.un(lval)

                yield indx, sample

    def record(self, xact, info):
        '''
        Record metrics info.

        Args:
            xact (Transaction): An LMDB write transaction.
            info (dict): A dictionary of sample info to save.
        '''
        indx = struct.pack('>Q', next(self.indx))
        sample = s_msgpack.en(info)
        xact.put(indx, sample, db=self._db_history, append=True)

class PropSetr:
    '''
    A helper for setting properties.  Most to cache cursors.
    '''
    def __init__(self, psto, xact):

        self.xact = xact
        self.psto = psto

        self.purs = xact.cursor(db=psto.props)
        self.burs = xact.cursor(db=psto.byprop)

    def has(self, penc, byts):
        return self.burs.set_key(penc + b'\x00' + byts)

    #def rem(self, buid):
    #def addtag(self, buid, tag, times):
    #def deltag(self, buid, tag):

    def set(self, buid, penc, lval, flags=0):

        pkey = buid + penc

        noindex = flags & STOR_FLAG_NOINDEX
        multival = flags & STOR_FLAG_MULTIVAL

        if self.purs.set_key(pkey):

            # At a minimum, we have the key...
            if flags & STOR_FLAG_DEFVAL:
                return False

            # if this is a multi-val, iter to check for valu
            if multival:

                # if a multival prop=valu exists, skip adding
                for mval in self.purs.iternext_dup():
                    if mval == lval:
                        return False

            else:

                # if it's exactly what we want, skip...
                oldb = self.purs.value()
                if oldb == lval:
                    return False

                okey = penc + b'\x00' + oldb
                self.burs.delete(okey, value=buid)

        # we are now free and clear to set and index
        self.purs.put(pkey, lval, dupdata=multival)
        if not noindex:
            self.burs.put(penc + b'\x00' + lval, buid)

        return True

    def put(self, items):
        '''
        Put a list of (buid, ((penc, lval, flags),...)) tuples.

        Yields:
            (buid, <props>) edits (only yields changes).
        '''
        for buid, props in items:

            edits = []

            for penc, lval, flags in props:

                if self.set(buid, penc, lval, flags=flags):
                    edits.append((penc, lval, flags))

            if edits:
                yield (0, (buid, edits))

class PropStor:

    def __init__(self, lenv, name=b'stor', edits=False):

        self.lenv = lenv
        self.edits = None

        #self.tags = self.lenv.open_db(b'tags')                             # <tag>00<form>=<init><tick><tock>
        self.props = self.lenv.open_db(name + b':props', dupsort=True)      # <buid><pkey>=<pval>
        self.byprop = self.lenv.open_db(name + b':byprop', dupsort=True)    # <pkey>00<pval> = <buid>

    def getPropSetr(self, xact):
        return PropSetr(self, xact)

    def has(self, xact, penc, byts):
        with xact.cursor(db=self.byprop) as burs:
            return burs.set_key(penc + b'\x00' + byts)

    def pref(self, xact, penc, byts):
        '''
        Perform a prefix search and yield (buid, penc, pval) rows.
        '''
        bkey = penc + b'\x00' + byts

        blen = len(bkey)
        with xact.cursor(db=self.byprop) as burs:

            if not burs.set_range(bkey):
                return

            for lkey, buid in burs.iternext():

                if lkey[:blen] != bkey:
                    return

                renc, rval = lkey.split(b'\x00', 1)
                yield (buid, renc, rval)

    def range(self, xact, penc, bval, nval):
        '''
        Perform a range search and yield (buid, penc, pval) rows.
        '''
        bkey = penc + b'\x00' + bval
        nkey = penc + b'\x00' + nval

        blen = len(bkey)
        with xact.cursor(db=self.byprop) as burs:

            if not burs.set_range(bkey):
                return

            for lkey, buid in burs.iternext():

                if lkey >= nkey:
                    break

                renc, rval = lkey.split(b'\x00', 1)
                yield (buid, renc, rval)

    def recs(self, xact, rows):
        '''
        Yield full (buid, (props..)) records from rows.
        '''
        with xact.cursor(db=self.props) as purs:

            for buid, penc, pval in rows:

                # props: <buid><prop>=<valu>
                if not purs.set_range(buid):
                    # yield empty results for iterator alignment..
                    yield (buid, ())
                    continue

                props = []

                for lkey, lval in curs.iternext():
                    props.append(lkey[32:], lval)

                yield (buid, props)

    def eq(self, xact, penc, pval):
        '''
        Yield (buid, pkey, pval) rows by prop=valu.
        '''
        lkey = penc + b'\x00' + pval
        with xact.cursor(db=self.byprop) as burs:
            if not burs.set_key(lkey):
                return

            for buid in burs.iternext_dup():
                yield buid, penc, pval
