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
            self.fire('task:retn', task=self.iden, retn=retn)

        self.fini()

    def get(self, prop, defval=None):
        '''
        Get a value from the info dict for the task.
        Args:
            prop (str): The name of the info value.
            defval (obj):   The default value to return if not found

        Returns:
            (obj):  The object from the info dict (or None)
        '''
        return self.info.get(prop, defval)

    def set(self, prop, valu):
        '''
        Set a value in the info dict for the task.

        Args:
            prop (str): The name of the info dict value
            valu (obj): The value to set in the info dict
        '''
        self.info[prop] = valu

    def err(self, info):
        '''
        Fire an error return value for the task.

        Args:
            info (dict): Exception info dict (see synapse.common.excinfo )
        '''
        retn = (False, info)
        self.fire('task:retn', task=self.iden, retn=retn)

    def retn(self, valu):
        '''
        Fire a result return value for the task.
        Args:
            valu (obj): The return value
        '''
        retn = (True, valu)
        self.fire('task:retn', task=self.iden, retn=retn)

    def onretn(self, func):
        '''
        Provide a function to receive return values.

        The specififed callback will be called with a retn tuple
        defined as (ok,valu).  If ok is True, valu is a return
        valu, if ok is False, valu is an excinfo dictionary.

        Args:
            func (function): Callback for a retn tuple.
        '''
        def prox(mesg):
            return func(mesg[1].get('retn'))
        self.on('task:retn', prox)

    def run(self):
        '''
        Execute the task.
        '''
        if not self.isfini:
            self._task_run()
            self.fini()

    def _task_run(self):  # pragma: no cover
        raise s_common.NoSuchImpl(name='_task_run')

    def __call__(self):
        self.run()

class CallTask(Task):

    '''
    An extension for a runnable task.

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
