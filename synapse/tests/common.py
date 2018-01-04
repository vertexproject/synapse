import os
import ssl
import sys
import shutil
import socket
import logging
import binascii
import tempfile
import unittest
import threading
import contextlib

import unittest.mock as mock


loglevel = int(os.getenv('SYN_TEST_LOG_LEVEL', logging.WARNING))
logging.basicConfig(level=loglevel,
                    format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')

import synapse.link as s_link
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.cores.common as s_cores_common

import synapse.lib.scope as s_scope
import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output
import synapse.lib.thishost as s_thishost

from synapse.common import *

from synapse.lib.iq import TstEnv, TstOutPut, SynTest, CmdGenerator

# create the global multi-plexor *not* within a test
# to avoid "leaked resource" when a test triggers creation
s_scope.get('plex')

def randhex(size):
    return binascii.hexlify(os.urandom(size)).decode('utf8')

class TooFewEvents(Exception): pass

TstSSLInvalidClientCertErr = socket.error
TstSSLConnectionResetErr = socket.error

testdir = os.path.dirname(__file__)
def getTestPath(*paths):
    return os.path.join(testdir, *paths)

def getIngestCore(path, core=None):
    if core is None:
        core = s_cortex.openurl('ram:///')

    gest = s_ingest.loadfile(path)
    with core.getCoreXact() as xact:
        gest.ingest(core)

    return core
