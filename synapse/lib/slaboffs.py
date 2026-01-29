import synapse.common as s_common

import synapse.lib.lmdbslab as s_lmdbslab

class SlabOffs:
    '''
    A helper for storing offset integers by iden.

    As with all slab objects, this is meant for single-thread async loop use.
    '''
    def __init__(self, slab: s_lmdbslab.Slab, db: str) -> None:
        self.db = slab.initdb(db)
        self.slab = slab

    def get(self, iden):

        buid = s_common.uhex(iden)

        byts = self.slab.get(buid, db=self.db)
        if byts is None:
            return 0

        return s_common.int64un(byts)

    def set(self, iden, offs):
        buid = s_common.uhex(iden)
        byts = s_common.int64en(offs)
        self.slab.put(buid, byts, db=self.db)

    def delete(self, iden):
        buid = s_common.uhex(iden)
        self.slab.delete(buid, db=self.db)
