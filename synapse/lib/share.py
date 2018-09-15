import logging

import synapse.common as s_common

import synapse.lib.base as s_base


logger = logging.getLogger(__name__)

class Share(s_base.Base):
    '''
    Class to wrap a dynamically shared object.
    '''
    def __init__(self, link, item):
        s_base.Base.__init__(self)

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
