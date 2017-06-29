import threading
import multiprocessing

import synapse.compat as s_compat
import synapse.dyndeps as s_dyndeps
from synapse.eventbus import EventBus
from synapse.common import *

psutil = s_dyndeps.getDynMod('psutil')

class Process(EventBus):
    '''
    Process provides a convenient API for executing a controlled process.

    This class manages the invocation of a 'multiprocessing.Process'. Various parameters may be specified to ensure
    that the spawned process is terminated in the event it goes off the rails. The most basic use case is to provide
    a pure python function to execute as a separate process, however, more advanced usage can rely on 'os.exec*'
    functionality to invoke various external commands.

    Keyword Arguments:
        task (tuple):
            Tuple with the form (task, args, kwargs) specifying task function and parameters to invoke as a process.

        timeout (float):
            Limit the process execution elapsed time, specified in seconds.

        maxmemory (int):
            Limit the resident set size(RSS) of the process, specified in bytes.

        monitorinterval (float):
            The time between sampling of the process' resource utilization. Defaults to 10 seconds.

    Raises:
        TypeError:
            If kwarg 'task' is not provided or is not of the correct form.
    '''
    DEFAULT_MONITOR_INTERVAL = 10

    def __init__(self, **kwargs):
        EventBus.__init__(self)
        self.task      = kwargs.get('task')
        self.timeout   = kwargs.get('timeout')
        self.monitint  = kwargs.get('monitorinterval', Process.DEFAULT_MONITOR_INTERVAL)
        self.maxmemory = kwargs.get('maxmemory')
        self.pinfo     = None
        self.errinfo   = None
        self.proc      = None
        self.procLock  = threading.Lock()
        self.queue     = multiprocessing.Queue()
        if not self.monitint > 0:
            self.monitint = Process.DEFAULT_MONITOR_INTERVAL
        if not isinstance(self.task, tuple):
            raise TypeError('kwargs task must be specified as (func, args, kwargs)')
        if self.maxmemory and psutil == None:
            raise Exception('psutils module not found, but is required when specifying maxmemory.')

    def run(self):
        '''
        Run the process governed by the parameters specified during object construction.

        Returns:
            object: The return value of the task function. If the process was terminated, a value of None will be
                    returned and 'error()' can be called to retrieve the error string.

        Raises:
            Exception:
                If process is currently running.
        '''
        with self.procLock:
            if self.isAlive():
                raise Exception('cannot call run on an already running process')

        func, args, kwargs = self.task

        def doit(queue):
            result = {}
            try:
                result['ret'] = func(*args, **kwargs)
            except Exception as e:
                result['err'] = excinfo(e)
            queue.put(result)

        self.proc = multiprocessing.Process(target=doit, args=(self.queue,))
        self.proc.start()
        self._initTimestamps()
        self._initProcessInfo(self.proc)
        while self.proc.is_alive():
            if self._shouldKillProcess():
                self.kill()
                break
            else:
                self.proc.join(self._sleepInterval())
                self._fireTick()
        self.endts = now()
        result = self._readResult()
        return result

    def kill(self):
        '''
        Terminates the process.
        '''
        with self.procLock:
            if self.isAlive():
                self.proc.terminate()

    def error(self):
        '''
        Provides an error string if an error occurred during process execution.

        Returns:
            dict: Containing err and when available: errfile, errline, errmsg. Or, None if process execution completed
                  successfully.
        '''
        return self.errinfo

    def runtime(self):
        '''
        Current runtime of running process, or total runtime of completed process.

        Returns:
            int: Runtime of process expressed in milliseconds.
        '''
        if self.isAlive():
            result = now() - self.startts
        elif self.endts and self.startts:
            result = self.endts - self.startts
        else:
            result = 0
        return result

    def memusage(self):
        '''
        Current RSS memory usage of process.

        Returns:
            int: Memory usage expressed in bytes.
        '''
        result = 0
        if self.pinfo:
            result = self.pinfo.memory_info().rss
        return result

    def isAlive(self):
        '''
        Indicates whether the process is still running.

        Returns:
            bool: True if process is still running, False otherwise.
        '''
        return self.proc != None and self.proc.is_alive()

    def _fireTick(self):
        if self.isAlive():
            self.fire('proc:tick', proc=self)

    def _readResult(self):
        ret = None
        try:
            result = self.queue.get_nowait()
            if not self.errinfo and result.get('err'):
                self.errinfo = result.get('err')
            ret = result.get('ret')
        except s_compat.queue.Empty:
            pass
        return ret

    def _shouldKillProcess(self):
        currTime = now()
        if self.endts and currTime >= self.endts:
            self.errinfo = {'err': 'HitMaxTime'}
            return True
        if self.maxmemory and self.pinfo.memory_info().rss > self.maxmemory:
            self.errinfo = {'err': 'HitMaxMemory'}
            return True
        return False

    def _sleepInterval(self):
        currTime = now()
        interval = self.monitint
        if self.endts and (currTime + self.monitint*1000) > self.endts:
            interval = (self.endts - currTime) / 1000
        return interval

    def _initTimestamps(self):
        self.startts = now()
        if self.timeout:
            self.endts = self.startts + self.timeout * 1000
        else:
            self.endts = None

    def _initProcessInfo(self, proc):
        if self.maxmemory:
            self.pinfo = psutil.Process(proc.pid)
