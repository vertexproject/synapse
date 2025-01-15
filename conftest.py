import os
import sys
import warnings

# Most of these bind to a random port but because it's not zero, it would emit
# the warning so just ignore these
allowed = [
    'synapse/tests/test_lib_aha.py::AhaTest::test_aha_clone',
    'synapse/tests/test_lib_aha.py::AhaTest::test_aha_restart',
    'synapse/tests/test_lib_aha.py::AhaTest::test_lib_aha_offon',
    'synapse/tests/test_lib_storm.py::StormTest::test_storm_pushpull',
    'synapse/tests/test_lib_stormsvc.py::StormSvcTest::test_storm_svc_restarts',

    # This test checks binding on port 27492 on purpose
    'synapse/tests/test_telepath.py::TeleTest::test_telepath_default_port',
]

def audithook(event, args):
    if event == 'socket.bind':
        _, addr = args
        if isinstance(addr, tuple) and (port := addr[1]) != 0:

            if (testname := os.environ.get('PYTEST_CURRENT_TEST')) is None:
                testname = '<unknown>'

            else:
                testname = testname.split(' ')[0]
                if testname in allowed:
                    return

            warnings.warn(f'Synapse tests should not bind to fixed ports: {testname=} {port=}')

def pytest_sessionstart(session):
    sys.addaudithook(audithook)
