import asyncio

import synapse.lib.base as s_base
import synapse.lib.task as s_task

class Boss(s_base.Base):

    '''
    An object to track "promoted" async tasks.
    '''
    async def __anit__(self):
        await s_base.Base.__anit__(self)
        self.tasks = {}
        self.onfini(self._onBossFini)

    async def _onBossFini(self):
        for task in list(self.tasks.values()):
            await task.kill()

    def ps(self):
        # top level tasks only...
        return [t for t in self.tasks.values() if t.root is None]

    def get(self, iden):
        return self.tasks.get(iden)

    async def promote(self, name, user, info=None):
        '''
        Promote the currently running task.
        '''
        task = asyncio.current_task()

        synt = getattr(task, '_syn_task', None)

        if synt is not None:

            if synt.root is None:
                return synt

            synt.root.kids.pop(synt.iden)
            synt.root = None
            return synt

        return await s_task.Task.anit(self, task, name, user, info=info)

    async def execute(self, coro, name, user, info=None):
        '''
        Create a synapse task from the given coroutine.
        '''
        task = self.schedCoro(coro)
        return await s_task.Task.anit(self, task, name, user, info=info)
