import os
import ssl
import sys
import shutil
import socket
import logging
import tempfile
import unittest
import threading
import contextlib

import unittest.mock as mock


loglevel = os.getenv('SYN_TEST_LOG_LEVEL', 'WARNING')
logging.basicConfig(level=loglevel,
                    format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s:%(threadName)s:%(processName)s]')

import synapse.link as s_link
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.cores.common as s_cores_common

import synapse.lib.scope as s_scope
import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.thishost as s_thishost

from synapse.common import *

from synapse.lib.iq import TstEnv, TstOutPut, SynTest, CmdGenerator

# create the global multi-plexor *not* within a test
# to avoid "leaked resource" when a test triggers creation
s_scope.get('plex')

class TooFewEvents(Exception): pass

TstSSLInvalidClientCertErr = socket.error
TstSSLConnectionResetErr = socket.error

testdir = os.path.dirname(__file__)
def getTestPath(*paths):
    return os.path.join(testdir, *paths)

def getCellAuth():

    path = getTestPath('files', 'cell.auth')
    cell = s_msgpack.loadfile(path)

    path = getTestPath('files', 'user.auth')
    user = s_msgpack.loadfile(path)

    return cell, user

def initCellDir(*path):

    cell, user = getCellAuth()

    dirn = gendir(*path)

    path = os.path.join(dirn, 'cell.auth')
    s_msgpack.dumpfile(cell, path)

    path = os.path.join(dirn, 'user.auth')
    s_msgpack.dumpfile(user, path)

    return dirn

def getIngestCore(path, core=None):
    if core is None:
        core = s_cortex.openurl('ram:///')

    gest = s_ingest.loadfile(path)
    with core.getCoreXact() as xact:
        gest.ingest(core)

    return core

def checkLock(fd, timeout, wait=0.5):
    wtime = 0

    if timeout < 0:
        raise ValueError('timeout must be > 0')

    while True:
        try:
            fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            if e.errno == 11:
                return True
        else:
            fcntl.lockf(fd, fcntl.LOCK_UN)
        time.sleep(wait)
        wtime += wait
        if wtime >= timeout:
            return False
