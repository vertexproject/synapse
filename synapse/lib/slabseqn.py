import synapse.common as s_common

import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

class SlabSeqn:
    '''
    An append optimized sequence of byte blobs.

    Args:
        lenv (lmdb.Environment): The LMDB Environment.
        name (str): The name of the sequence.
    '''
    def __init__(self, slab: s_lmdbslab.Slab, name: str) -> None:

        self.slab = slab
        self.db = self.slab.initdb(name)

        self.indx = self.nextindx()

    def add(self, item):
        '''
        Add a single item to the sequence.
        '''
        byts = s_msgpack.en(item)
        lkey = s_common.int64en(self.indx)

        self.slab.put(lkey, byts, db=self.db)
        self.indx += 1

    def last(self):

        last = self.slab.last(db=self.db)
        if last is None:
            return None

        lkey, lval = last

        indx = s_common.int64un(lkey)
        return indx, s_msgpack.un(lval)

    def stat(self):
        return self.slab.stat(db=self.db)

    def save(self, items):
        '''
        Save a series of items to a sequence.

        Args:
            items (tuple): The series of items to save into the sequence.

        Returns:
            The index of the first item
        '''
        rows = []
        indx = self.indx

        size = 0
        tick = s_common.now()

        for item in items:

            byts = s_msgpack.en(item)

            size += len(byts)

            lkey = s_common.int64en(indx)
            indx += 1

            rows.append((lkey, byts))

        self.slab.putmulti(rows, append=True, db=self.db)
        took = s_common.now() - tick

        origindx = self.indx
        self.indx = indx
        return {'indx': indx, 'size': size, 'count': len(items), 'time': tick, 'took': took}

        return origindx

    def append(self, item):

        byts = s_msgpack.en(item)

        indx = self.indx
        lkey = s_common.int64en(indx)

        self.slab.put(lkey, byts, db=self.db)

        self.indx += 1
        return indx

    def index(self):
        '''
        Return the current index to be used
        '''
        return self.indx

    def nextindx(self):
        '''
        Determine the next insert offset according to storage.

        Returns:
            int: The next insert offset.
        '''
        indx = 0
        with s_lmdbslab.Scan(self.slab, self.db) as curs:
            last_key = curs.last_key()
            if last_key is not None:
                indx = s_common.int64un(last_key) + 1
        return indx

    def iter(self, offs):
        '''
        Iterate over items in a sequence from a given offset.

        Args:
            offs (int): The offset to begin iterating from.

        Yields:
            (indx, valu): The index and valu of the item.
        '''
        startkey = s_common.int64en(offs)

        for lkey, lval in self.slab.scanByRange(startkey, db=self.db):
            indx = s_common.int64un(lkey)
            valu = s_msgpack.un(lval)
            yield indx, valu

    def rows(self, offs):
        '''
        Iterate over raw indx, bytes tuples from a given offset.
        '''
        lkey = s_common.int64en(offs)
        for lkey, byts in self.slab.scanByRange(lkey, db=self.db):
            indx = s_common.int64un(lkey)
            yield indx, byts

    def slice(self, offs, size):

        imax = size - 1

        for i, item in enumerate(self.iter(offs)):

            yield item

            if i == imax:
                break
