import synapse.common as s_common

import synapse.lib.lmdb as s_lmdb
import synapse.lib.msgpack as s_msgpack

class SlabSeqn:
    '''
    An append optimized sequence of byte blobs.

    Args:
        lenv (lmdb.Environment): The LMDB Environment.
        name (str): The name of the sequence.
    '''
    def __init__(self, slab: s_lmdb.Slab, name: str) -> None:

        self.lenv = slab
        self.db = self.lenv.initdb(name)

        self.indx = self.nextindx()

    def save(self, items):
        '''
        Save a series of items to a sequence.

        Args:
            items (tuple): The series of items to save into the sequence.

        Returns:
            None
        '''
        rows = []
        indx = self.indx

        for item in items:

            byts = s_msgpack.en(item)

            lkey = s_common.int64en(indx)
            indx += 1

            rows.append((lkey, byts))

        self.lenv.putmulti(rows, append=True, db=self.db)

        self.indx = indx

    def index(self):
        '''
        Return the current index to be used
        '''
        return self.indx

    def nextindx(self):
        '''
        Determine the next insert offset according to storage.

        Args:
            xact (lmdb.Transaction): An LMDB transaction.

        Returns:
            int: The next insert offset.
        '''
        indx = 0
        with s_lmdb.Scan(self.lenv, self.db) as curs:
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

        for lkey, lval in self.lenv.scanByRange(startkey, db=self.db):
            indx = s_common.int64un(lkey)
            valu = s_msgpack.un(lval)
            yield indx, valu

    def slice(self, offs, size):

        imax = size - 1

        for i, item in enumerate(self.iter(offs)):

            yield item

            if i == imax:
                break
