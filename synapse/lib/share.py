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

        sess = link.get('sess')

        async def fini():
            sess.popSessItem(self.iden)

        self.onfini(fini)

        sess.setSessItem(self.iden, self)

    async def _runShareLoop(self):
        return
