import types

import synapse.common as s_common
from synapse.eventbus import EventBus

class Task(EventBus):
    '''
    A cancelable Task abstraction which operates much like a Future
    but with some additional features.
    '''
    def __init__(self, iden=None):

        EventBus.__init__(self)

        if iden is None:
            iden = s_common.guid()

        self.info = {}
        self.iden = iden

        self.on('task:fini', self._onTaskFini)

    def _onTaskFini(self, mesg):

        retn = mesg[1].get('retn')
        if retn is not None:
            self.fire('task:retn', retn=retn)

        self.fini()

    def get(self, prop, defval=None):
        return self.info.get(prop, defval)

    def set(self, prop, valu):
        self.info[prop] = valu

    def err(self, info):
        retn = (False, info)
        self.fire('task:retn', retn=retn)

    def retn(self, valu):
        retn = (True, valu)
        self.fire('task:retn', retn=retn)

    def onretn(self, func):
        '''
        Provide a function to receive return values.
        '''
        def prox(mesg):
            return func(mesg[1].get('retn'))
        self.on('task:retn', prox)

    def run(self):

        if not self.isfini:
            self._task_run()
            self.fini()

    def _task_run(self):
        raise s_common.NoSuchImpl(name='_task_run')

    def __call__(self):
        self.run()

class CallTask(Task):

    '''
    An extnsion for a runnable task.

    Args:
        call ((func,[],{})): A tuple of call details.

    '''
    def __init__(self, call):

        Task.__init__(self)
        self._call = call

    def _task_run(self):

        func, args, kwargs = self._call

        try:

            valu = func(*args, **kwargs)

            if isinstance(valu, types.GeneratorType):
                for v in valu:
                    self.retn(v)

            else:
                self.retn(valu)

        except Exception as e:
            self.err(s_common.excinfo(e))
