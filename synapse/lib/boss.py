import asyncio
import logging

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.task as s_task

logger = logging.getLogger(__name__)

class Boss(s_base.Base):

    '''
    An object to track "promoted" async tasks.

    Promoted tasks are asyncio tasks, wrapped in a synapse task
    (``s_task.Task``), that are visible to storm users via the task tracking
    libs/commands such as ``ps.list`` and ``$lib.ps.list()``.
    '''
    async def __anit__(self):
        await s_base.Base.__anit__(self)
        self.tasks = {}
        self.is_shutdown = False
        self.shutdown_lock = asyncio.Lock()
        self.onfini(self._onBossFini)

    async def shutdown(self, timeout=None):
        # when a boss is "shutting down" it should not promote any new tasks,
        # but await the completion of any which are already underway...

        self.reqNotShut()

        async with self.shutdown_lock:

            for task in list(self.tasks.values()):

                # do not wait on child tasks
                if task.root is not None:
                    continue

                # do not wait on background tasks
                if task.background:
                    continue

                if not await s_coro.waittask(task.task, timeout=timeout):
                    return False

            self.is_shutdown = True
            return True

    def reqNotShut(self, mesg=None):
        if self.shutdown_lock.locked():
            if mesg is None:
                mesg = 'The service is shutting down.'
            raise s_exc.ShuttingDown(mesg=mesg)
        if self.is_shutdown:
            if mesg is None:
                mesg = 'The service is shut down.'
            raise s_exc.ShuttingDown(mesg=mesg)

    async def _onBossFini(self):
        for task in list(self.tasks.values()):
            await task.kill()

    def ps(self):
        # top level tasks only...
        return [t for t in self.tasks.values() if t.root is None]

    def get(self, iden):
        return self.tasks.get(iden)

    async def promote(self, name, user, info=None, taskiden=None, background=False):
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

        syntask = await self.promotetask(task, name, user, info=info, taskiden=taskiden)
        syntask.background = background

        return syntask

    async def promotetask(self, task, name, user, info=None, taskiden=None):

        self.reqNotShut()
        synt = s_task.syntask(task)

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
        self.reqNotShut()
        task = self.schedCoro(coro)
        return await s_task.Task.anit(self, task, name, user, info=info, iden=iden)
