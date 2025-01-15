import os
import sys
import json
import pathlib

_events = {}

def audithook(event, args):
    if event == 'socket.bind':
        testname = os.environ.get('PYTEST_CURRENT_TEST')
        _events.setdefault(testname, [])
        sock, addr = args
        if isinstance(addr, (list, tuple)) and (port := addr[1]) != 0:
            raise RuntimeError(f'socket.bind() to port {port}')
        _events[testname].append(addr)

def pytest_sessionstart(session):
    sys.addaudithook(audithook)

def pytest_sessionfinish(session, exitstatus):

    dirn = pathlib.Path('test-reports')
    dirn.mkdir(exist_ok=True)

    if (workerid := os.environ.get('PYTEST_XDIST_WORKER')) is not None:
        filename = dirn / f'socket.bind.{workerid}.json'
    else:
        filename = dirn / 'socket.bind.json'

    with filename.open('w') as fp:
        json.dump(_events, fp)
