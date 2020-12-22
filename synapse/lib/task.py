import copy
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
        self.name = name
        self.user = user
        self.root = root
        self.info = info
        self.kids = {}

        self.boss.tasks[self.iden] = self
        if root is not None:
            root.kids[self.iden] = self

        self.task.add_done_callback(self._onTaskDone)
        self.onfini(self._onTaskFini)

    def __repr__(self):

        user = 'root'
        if self.user is not None:
            user = self.user.name

        return 'task: %s (%s) %r' % (self.iden, user, self.info)

    def _onTaskDone(self, t):
        if not self.isfini:
            self.boss.schedCoroSafe(self.fini())

    async def _onTaskFini(self):

        for task in list(self.kids.values()):
            await task.fini()

        self.task.cancel()

        try:
            await self.task
        except asyncio.CancelledError:
            pass
        except Exception:  # pragma:  no cover
            logger.exception('Task completed with exception')

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
            'info': copy.deepcopy(self.info),
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
    except Exception:
        return None

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

# Task vars:  task-local variables

_TaskDictCtors = {}  # type: ignore

def varinit(task=None):
    '''
    Initializes (or re-initializes for testing purposes) all of a task's task-local variables

    Precondition:
        If task is None, this must be called from task context
    '''
    if task is None:
        task = asyncio.current_task()
    taskvars = {}
    task._syn_taskvars = taskvars
    return taskvars

def _taskdict(task):
    '''
    Note: No locking is provided.  Under normal circumstances, like the other task is not running (e.g. this is running
    from the same event loop as the task) or task is the current task, this is fine.
    '''
    if task is None:
        task = asyncio.current_task()

    assert task
    taskvars = getattr(task, '_syn_taskvars', None)

    if taskvars is None:
        taskvars = varinit(task)

    return taskvars

def varget(name, defval=None, task=None):
    '''
    Access a task local variable by name

    Precondition:
        If task is None, this must be called from task context
    '''
    taskdict = _taskdict(task)
    retn = taskdict.get(name, s_common.NoValu)
    if retn is not s_common.NoValu:
        return retn

    func = _TaskDictCtors.get(name)
    if func is None:
        return defval

    item = func()
    taskdict[name] = item

    return item

def varset(name, valu, task=None):
    '''
    Set a task-local variable

    Args:
        task: If task is None, uses current task

    Precondition:
        If task is None, this must be called from task context
    '''
    _taskdict(task)[name] = valu

def vardefault(name, func):
    '''
    Add a default constructor for a particular task-local variable

    All future calls to taskVarGet with the same name will return the result of calling func
    '''
    _TaskDictCtors[name] = func
