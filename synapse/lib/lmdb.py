import struct
import itertools

import synapse.exc as s_exc
import synapse.lib.msgpack as s_msgpack

'''
Some LMDB helpers...
'''

STOR_FLAG_NOINDEX = 0x0001    # there is no byprop index for this prop
STOR_FLAG_MULTIVAL = 0x0002    # this is a multi-value prop

STOR_TYPE_UTF8 = 0         # UTF8 encoded string byte value
STOR_TYPE_UINT64 = 1         # Big-endian encoded 64 bit unsigned integer
STOR_TYPE_UINT128 = 2         # Big-endian encoded 128 bit unsigned integer
STOR_TYPE_BYTES = 3         # Raw bytes ( likely interpreted by the model layer )
STOR_TYPE_IVAL = 4         # Interval tuple, stored as <uint64><uint64>

#STOR_EDIT_SETPROP = 0
#STOR_EDIT_DELPROP = 1

class Seqn:
    '''
    An append optimized sequence of byte blobs.
    '''
    def __init__(self, lenv, name):

        self.lenv = lenv
        self.db = lenv.open_db(name)

        with lenv.begin() as xact:
            indx = xact.stat(db=self.db)['entries']
            self.indx = itertools.count(indx)

    def save(self, xact, items):

        rows = []
        for item in items:
            byts = s_msgpack.en(item)
            lkey = struct.pack('>Q', next(self.indx))
            rows.append((lkey, byts))

        with xact.cursor(db=self.db) as curs:
            curs.putmulti(rows, append=True)

    def iter(self, offs):

        lkey = struct.pack('>Q', offs)

        with self.lenv.begin() as xact:

            with xact.cursor(db=self.db) as curs:

                if not curs.set_key(lkey):
                    return

                for lkey, lval in curs.iternext():
                    indx = struct.unpack('>Q', lkey)[0]
                    valu = s_msgpack.un(lval)
                    yield indx, valu

class PropStor:

    def __init__(self, lenv, name=b'stor', edits=False):

        self.lenv = lenv
        self.edits = None

        #self.tags = self.lenv.open_db(b'tags')                      # <tag>00<form>=<tick><tock>
        self.props = self.lenv.open_db(name + b':props', dupsort=True)      # <buid><prop>=<valu>
        self.byprop = self.lenv.open_db(name + b':byprop', dupsort=True)    # <prop>00<pval> = <buid><type><flags

        if edits:
            self.edits = Seqn(self.lenv, name + b':edits')

        self._lift_funcs = {
            'rows:by:prop:eq': self._liftRowsByPropEq,
            'recs:by:buid': self._liftRecsByBuids,
        }

        self._stor_funcs = {
            #'tag:add': self._storTagAdd,
            #'tag:del': self._storTagDel,
            'prop:set': self._storPropSet,
            #'prop:del': self._storPropDel,
        }

        # type dump/load functions
        self._dump_funcs = [
            self._typeDumpUtf8,
            self._typeDumpUint64,
        ]

        self._load_funcs = [
            self._typeLoadUtf8,
            self._typeLoadUint64,
        ]

    def lift(self, lifts, chain=True):
        '''
        Select and yield results from a set of lift operations.
        '''
        if not lifts:
            return

        with self.lenv.begin() as xact:

            iters = []

            for i, lift in enumerate(lifts):

                lift = list(lift) # to allow us to splice in the inputs

                if i > 0:
                    lift[1] = iters[i - 1]

                func = self._lift_funcs.get(lift[0])
                if func is None:
                    logger.warning('no lift oper: %s' % (lift[0],))
                    return

                iters.append(func(xact, lift))

            for item in iters[-1]:
                yield item

    def store(self, stors):
        '''
        Execute a series of stor operations.
        '''
        with self.lenv.begin(write=True) as xact:

            for stor in stors:

                name = stor[0]

                func = self._stor_funcs.get(name)
                if func is None:
                    raise s_exc.NoSuchFunc(name=name)

                for edit in func(xact, stor):
                    yield edit

                if self.edits is not None:
                    self.edits.save(xact, stors)

    def load(self, byts):
        '''
        Parse a storage type from the given bytes.
        Bytes will be in <type><flags><bytes>... format.

        Args:
            byts (bytes): A serialized storage type.

        Returns:
            (int, int, obj): A (type, flags, valu) tuple.

        '''
        type, flags = struct.unpack_from('>HH', byts)
        valu = self._load_funcs[type](byts[4:])
        return type, flags, valu

    def dump(self, type, valu):
        '''
        Dump the bytes for a given storage type value.
        ( not including <type><flags> header )

        Args:
            type (int): A storage type integer.
            flags (int): A storage flags mask.
            valu (obj): The object to serialize.
        '''
        return self._dump_funcs[type](valu)

    def _liftRecsByBuids(self, xact, lift):
        return self.getRecsByBuids(lift[1])

    #def getRowsByProp(self, xact, prop):
    #def getRowsByBuid(self, xact, buid):

    def getRecsByBuids(self, xact, buids):
        '''
        Yield (buid, ((prop, valu), ...)) records by buid.
        '''
        with xact.cursor(db=self.props) as curs:

            for buid in buids:

                props = []

                if curs.set_range(buid):

                    for lkey, lval in curs.iternext():

                        if lkey[:32] != buid:
                            break

                        prop = lkey[32:].decode('utf8')

                        type, flags, valu = self.load(lval)
                        props.append((prop, valu))

                yield (buid, props)

    def addPropRows(self, xact, items):
        '''
        Add properties from a list of (buid, ((prop,type,flags,valu),...)) items.
        '''
        with xact.cursor(db=self.props) as purs:

            with xact.cursor(db=self.byprop) as burs:

                for buid, props in items:

                    edits = []
                    for prop, type, flags, valu in props:

                        penc = prop.encode('utf8')

                        pkey = buid + penc
                        byts = self._dump_funcs[type](valu) # speed

                        hedr = struct.pack('>HH', type, flags)
                        lval = hedr + byts

                        noindex = flags & STOR_FLAG_NOINDEX
                        multival = flags & STOR_FLAG_MULTIVAL

                        if purs.set_key(pkey):
                            # At a minimum, we have the key...

                            # if this is a multi-val, iter to check for valu
                            if multival:

                                # if a multival prop=valu exists, skip adding
                                skip = False
                                for mval in purs.iternext_dup():
                                    if mval == lval:
                                        skip = True
                                        break

                                if skip:
                                    continue # to next prop

                            else:

                                # if it's exactly what we want, skip...
                                oldb = purs.value()
                                if oldb == lval:
                                    continue # to next prop...

                                oldt, oldf, oldv = self._load_type(oldb)

                                # was the previous value indexed?
                                if not oldf & STOR_FLAGS_NOINDEX:
                                    # blow away his old index value
                                    oldi = penc + b'\x00' + oldb[32:]
                                    burs.delete(oldi, value=buid)

                        # we are now free and clear to set and index
                        purs.put(pkey, lval, dupdata=multival)
                        if not noindex:
                            burs.put(penc + b'\x00' + byts, buid + hedr)

                        edits.append((prop, type, flags, valu))

                    if edits:
                        yield (0, (buid, edits))

    def _liftRowsByPropEq(self, xact, lift):
        return self.getRowsByPropEq(xact, lift[1])

    def getRowsByPropEq(self, xact, props):
        '''
        '''
        with xact.cursor(db=self.byprop) as curs:

            for prop, type, flags, valu in props:

                penc = prop.encode('utf8')

                byts = self.dump(type, valu)
                # maybe we dont know about this type...
                if byts is None:
                    continue

                if curs.set_key(penc + b'\x00' + byts):
                    for lval in curs.iternext_dup(keys=False):
                        # lval: <buid><type><flags>
                        yield (lval[:32], prop, valu)

    def _typeDumpUtf8(self, valu):
        return valu.encode('utf8')

    def _typeLoadUtf8(self, valu):
        return valu.decode('utf8')

    def _typeDumpUint64(self, valu):
        return struct.pack('>Q', valu)

    def _typeLoadUint64(self, valu):
        return struct.unpack('>Q', valu)[0]

    def _storPropSet(self, xact, stor):
        return self.addPropRows(xact, stor[1])
