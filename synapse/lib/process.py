import multiprocessing
from queue import Empty
from multiprocessing import Queue

from synapse.common import *
import synapse.dyndeps as s_dyndeps

psutil = s_dyndeps.getDynMod('psutil')

class Process:
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

        maxcpuavg (int):
            Limit the average cpu utilization of the process, specified as percentage.

        maxcpu (int):
            Limit the cpu utilization of the process, specified as percentage.

        maxcpucycles (int):
            The number of 'over the threshold' maxcpu samples required before terminating the process. If not specified,
            the process will be terminated on the first observation of it exceeding the maxcpu threshold. This parameter
            used in conjunction with maxcpu provides an alternative to maxcpuavg to allow for occasional spikes in cpu
            utilization.

        monitorinterval (float):
            The time between sampling of the process' resource utilization. Defaults to 10 seconds.

    Raises:
        TypeError:
            If kwarg 'task' is not provided or is not of the correct form.

        Exception:
            If 'maxmemory' or 'maxcpu' arguments are supplied and psutil module is not installed.

    '''
    DEFAULT_MONITOR_INTERVAL = 10

    def __init__(self, **kwargs):
        self.task      = kwargs.get('task')
        self.timeout   = kwargs.get('timeout')
        self.monitint  = kwargs.get('monitorinterval', Process.DEFAULT_MONITOR_INTERVAL)
        self.maxmemory = kwargs.get('maxmemory')
        self.maxcpuavg = kwargs.get('maxcpuavg')
        self.maxcpu    = kwargs.get('maxcpu')
        self.cpucycles = kwargs.get('maxcpucycles')
        self.pinfo     = None
        self.errinfo   = None
        self.queue     = Queue()
        if not self.monitint > 0:
            self.monitint = Process.DEFAULT_MONITOR_INTERVAL
        if not isinstance(self.task, tuple):
            raise TypeError('kwargs task must be specified as (func, args, kwargs)')
        if self.maxmemory or self.maxcpu or self.maxcpuavg:
            if psutil == None:
                raise Exception('psutils module not found, but is required when specifying maxmemory or maxcpu')

    def run(self):
        '''
        Run the process governed by the parameters specified during object construction.

        Returns:
            object: The return value of the task function. If the process was terminated, a value of None will be
                    returned and 'error()' can be called to retrieve the error string.
        '''
        func, args, kwargs = self.task

        def exec(queue):
            result = {}
            try:
                result['ret'] = func(*args, **kwargs)
            except Exception as e:
                result['err'] = excinfo(e)
            queue.put(result)

        p = multiprocessing.Process(target=exec, args=(self.queue,))
        p.start()
        self._initTimestamps()
        self._initProcessInfo(p)
        while p.is_alive():
            if self._shouldKillProcess():
                p.terminate()
                break
            else:
                p.join(self._sleepInterval())
        result = self._readResult()
        return result

    def error(self):
        '''
        Provides an error string if an error occurred during process execution.

        Returns:
            dict: Containing err and when available: errfile, errline, errmsg. Or, None if process execution completed
                  successfully.
        '''
        return self.errinfo

    def _readResult(self):
        ret = None
        try:
            result = self.queue.get_nowait()
            if not self.errinfo and result.get('err'):
                self.errinfo = result.get('err')
            ret = result.get('ret')
        except Empty:
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
        if self.pinfo != None:
            cpuPercent = self.pinfo.cpu_percent()
            if self.maxcpuavg and self._cpuAverage(cpuPercent) > self.maxcpuavg:
                self.errinfo = {'err': 'HitMaxCPU'}
                return True
            if self.maxcpu and cpuPercent > self.maxcpu:
                self.cpuoverages += 1
                if not self.cpucycles or (self.cpucycles and self.cpuoverages >= self.cpucycles):
                    self.errinfo = {'err': 'HitMaxCPU'}
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
        if self.maxmemory or self.maxcpu or self.maxcpuavg:
            self.pinfo = psutil.Process(proc.pid)
            self.cputotal = 0
            self.cpusamples = 0
            self.cpuoverages = 0

    def _cpuAverage(self, cpuPercent):
        self.cpusamples += 1
        self.cputotal += cpuPercent
        return self.cputotal / self.cpusamples
