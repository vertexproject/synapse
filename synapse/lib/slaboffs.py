import synapse.common as s_common

import synapse.lib.lmdbslab as s_lmdbslab

class SlabOffs:
    '''
    A helper for storing offset integers by iden.

    As with all slab objects, this is meant for single-thread async loop use.
    '''
    def __init__(self, slab: s_lmdbslab.Slab, db) -> None:
        self.db = db
        self.lenv = slab

    def get(self, iden):

        buid = s_common.uhex(iden)

        byts = self.lenv.get(buid, db=self.db)
        if byts is None:
            return 0

        return s_common.int64un(byts)

    def set(self, iden, offs):
        buid = s_common.uhex(iden)
        byts = s_common.int64en(offs)
        self.lenv.put(buid, byts, db=self.db)

    def delete(self, iden):
        buid = s_common.uhex(iden)
        self.lenv.delete(buid, db=self.db)
