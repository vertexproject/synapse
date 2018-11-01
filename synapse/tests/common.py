import os
import logging
import threading

loglevel = os.getenv('SYN_TEST_LOG_LEVEL', 'WARNING')
_logformat = '%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s:%(threadName)s:%(processName)s]'
logging.basicConfig(level=loglevel, format=_logformat)

# import synapse.lib.scope as s_scope

testdir = os.path.dirname(__file__)

def getTestPath(*paths):
    return os.path.join(testdir, *paths)

class CallBack:
    '''
    An easy to use test helper for *synchronous* callbacks.
    '''
    def __init__(self, retval=None):
        self.args = None
        self.kwargs = None
        self.retval = retval
        self.event = threading.Event()

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.event.set()
        return self.retval

    def wait(self, timeout=None):
        return self.event.wait(timeout=timeout)
