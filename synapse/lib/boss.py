import asyncio
import logging

import synapse.lib.base as s_base
import synapse.lib.task as s_task

logger = logging.getLogger(__name__)

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

    async def promote(self, name, user, info=None, taskiden=None):
        '''
        Promote the currently running task.

        Args:
            name (str): The name of the task.
            user: The User who owns the task.
            taskiden: An optional GUID for the task.
            info: An optional information dictionary containing information about the task.

        Returns:
            s_task.Task: The Synapse Task object.
        '''
        task = asyncio.current_task()
        return await self.promotetask(task, name, user, info=info, taskiden=taskiden)

    async def promotetask(self, task, name, user, info=None, taskiden=None):

        synt = getattr(task, '_syn_task', None)

        if synt is not None:

            if taskiden is not None and synt.iden != taskiden:
                logger.warning(f'Iden specified for existing task={synt}. Ignored.')

            if synt.root is None:
                return synt

            synt.root.kids.pop(synt.iden)
            synt.root = None
            return synt

        return await s_task.Task.anit(self, task, name, user, info=info, iden=taskiden)

    async def execute(self, coro, name, user, info=None, iden=None):
        '''
        Create a synapse task from the given coroutine.
        '''
        task = self.schedCoro(coro)
        return await s_task.Task.anit(self, task, name, user, info=info, iden=iden)
