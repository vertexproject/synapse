import os
import sys
import warnings

import synapse.common as s_common

THROW = False

def audithook(event, args):
    if event == 'socket.bind':
        _, addr = args
        if isinstance(addr, tuple) and (port := addr[1]) != 0:

            testname = os.environ.get('PYTEST_CURRENT_TEST', '<unknown>').split(' ')[0]

            mesg = f'Synapse tests should not bind to fixed ports: {testname=} {port=}'
            warnings.warn(mesg)

            if THROW:
                raise RuntimeError(mesg)

def pytest_sessionstart(session):
    if s_common.envbool('SYNDEV_AUDIT_PORT_BINDS'):
        sys.addaudithook(audithook)

    if s_common.envbool('SYNDEV_AUDIT_PORT_BINDS_RAISE'):
        global THROW
        THROW = True
