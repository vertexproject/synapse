import asyncio
import logging

import synapse.common as s_common

import synapse.lib.base as s_base

logger = logging.getLogger(__name__)

class Task(s_base.Base):
    '''
    The synapse Task object implements concepts similar to process trees
    for asyncio.Task instances.
    '''
    async def __anit__(self, boss, task, name, user, info=None, root=None):

        await s_base.Base.__anit__(self)

        if info is None:
            info = {}

        self.boss = boss

        task._syn_task = self

        self.task = task                # the real task...
        self.iden = s_common.guid()
        self.tick = s_common.now()

        self.boss.tasks[self.iden] = self
        if root is not None:
            root.kids[self.iden] = self

        self.task.add_done_callback(self._onTaskDone)

        self.name = name
        self.user = user
        self.root = root
        self.info = info

        self.kids = {}

        self.onfini(self._onTaskFini)

    def __repr__(self):

        user = 'root'
        if self.user is not None:
            user = self.user.name

        return 'task: %s (%s) %r' % (self.iden, user, self.info)

    def _onTaskDone(self, t):
        if not self.isfini:
            self.boss.schedCoro(self.fini())

    async def _onTaskFini(self):

        for task in list(self.kids.values()):
            await task.fini()

        self.task.cancel()

        try:
            await self.task
        except Exception as e:
            pass

        if self.root is not None:
            self.root.kids.pop(self.iden)

        self.boss.tasks.pop(self.iden)

    async def worker(self, coro, name='worker'):

        task = self.boss.schedCoro(coro)
        synt = await Task.anit(self.boss, task, name, self.user, root=self)

        self.kids[synt.iden] = synt

    async def kill(self):
        # task kill and fini are the same...
        await self.fini()

    def pack(self):

        pask = {
            'iden': self.iden,
            'name': self.name,
            'info': self.info,
            'tick': self.tick,
            'user': 'root',
            'kids': {i: k.pack() for i, k in self.kids.items()},
        }

        if self.user is not None:
            pask['user'] = self.user.name

        return pask

def loop():
    try:
        return asyncio.get_running_loop()
    except Exception as e:
        return None

#def fork(coro, name, user=None, info=None):

def current():
    '''
    Return the current synapse task.
    '''
    task = asyncio.current_task()
    return getattr(task, '_syn_task', None)

def user():
    '''
    Return the current task user.
    '''
    task = current()
    if task is not None:
        return task.user

def username():
    '''
    Return the current task user name.
    '''
    item = user()
    if item is not None:
        return item.name

async def executor(func, *args, **kwargs):
    '''
    Execute a function in an executor thread.

    Args:
        todo ((func,args,kwargs)): A todo tuple.
    '''
    def syncfunc():
        return func(*args, **kwargs)

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, syncfunc)
