import synapse.common as s_common

import synapse.lib.base as s_base

class Share(s_base.Base):
    '''
    Class to wrap a dynamically shared object.
    '''
    async def __anit__(self, link, item):
        await s_base.Base.__anit__(self)

        self.link = link

        self.orig = item    # for context management
        self.item = item

        self.iden = s_common.guid()

        self.exited = False
        self.entered = False

        items = link.get('dmon:items')

        async def fini():
            items.pop(self.iden, None)

        self.onfini(fini)
        items[self.iden] = self

    async def _runShareLoop(self):
        return
