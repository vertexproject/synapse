import os
import socket
import logging

import unittest.mock as mock


loglevel = os.getenv('SYN_TEST_LOG_LEVEL', 'WARNING')
logging.basicConfig(level=loglevel,
                    format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s:%(threadName)s:%(processName)s]')

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

#import synapse.cores.common as s_cores_common

import synapse.lib.scope as s_scope
import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.thishost as s_thishost

from synapse.common import *

from synapse.tests.utils import CmdGenerator, SynTest, TstEnv, TstOutPut,\
    TEST_MAP_SIZE, writeCerts

# create the global multi-plexor *not* within a test
# to avoid "leaked resource" when a test triggers creation
s_scope.get('plex')

class TooFewEvents(Exception): pass

TstSSLInvalidClientCertErr = socket.error
TstSSLConnectionResetErr = socket.error

testdir = os.path.dirname(__file__)

writeCerts(testdir)

def getTestPath(*paths):
    return os.path.join(testdir, *paths)

def checkLock(fd, timeout, wait=0.5):
    wtime = 0

    if timeout < 0:
        raise ValueError('timeout must be > 0')

    while True:
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        except OSError as e:
            if e.errno == 11:
                return True
        else:
            fcntl.lockf(fd, fcntl.LOCK_UN)
        time.sleep(wait)
        wtime += wait
        if wtime >= timeout:
            return False

def mesg_cmd(query, oper):
    '''
    Test command which adds messages to the storm message queue.

    Args:
        query (s_storm.Query): Query object.
        oper ((str, dict)): Oper tuple

    Returns:
        None
    '''
    query.mesg('Log test messages')
    query.mesg('Query has [%s] nodes' % len(query.data()))

class ModelSeenMixin:

    def check_seen(self, core, node):
        form = node[1]['tufo:form']
        minp = form + ':seen:min'
        maxp = form + ':seen:max'

        self.none(node[1].get(minp))
        self.none(node[1].get(maxp))

        core.setTufoProps(node, **{'seen:min': 100, 'seen:max': 100})
        self.eq(node[1].get(minp), 100)
        self.eq(node[1].get(maxp), 100)

        core.setTufoProps(node, **{'seen:min': 0, 'seen:max': 0})
        self.eq(node[1].get(minp), 0)
        self.eq(node[1].get(maxp), 100)

        core.setTufoProps(node, **{'seen:min': 1000, 'seen:max': 1000})
        self.eq(node[1].get(minp), 0)
        self.eq(node[1].get(maxp), 1000)

###########################################################################
# 010 stuff

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

def run_sync(coro):
    '''
    Decorator that wraps an async test so that it runs synchronously
    '''
    def wrapper(*args, **kwargs):
        s_glob.sync(coro(*args, **kwargs))
    return wrapper
