import os
import logging

import pytest
import coverage

import synapse.lib.json as s_json

logger = logging.getLogger(__name__)

class TestCovPlugin:

    def __init__(self, output):
        self.output = output
        self.covmap = {}
        self._activecov = None

    def _collectone(self, nodeid):
        data = self._activecov.get_data()
        data.set_query_contexts([f'{nodeid}*'])

        result = {}
        for path in data.measured_files():
            lines = sorted(data.lines(path) or [])
            if lines:
                result[os.path.relpath(path)] = lines

        data.set_query_contexts(None)
        self.covmap[nodeid] = result

    @pytest.hookimpl(trylast=True)
    def pytest_sessionstart(self, session):
        self._activecov = coverage.Coverage.current()
        if self._activecov is None:
            pytest.exit('synapse.utils.testcov requires an active coverage instance; '
                        'pass --cov to enable pytest-cov before using --testcov.',
                        returncode=1)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        self._activecov.switch_context(item.nodeid)
        yield
        self._activecov.switch_context('')
        self._collectone(item.nodeid)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        # When running as an xdist worker, ship covmap to the controller
        # via workeroutput rather than writing the file directly.
        if hasattr(session.config, 'workeroutput'):
            session.config.workeroutput['testcov'] = self.covmap
            return

        self._writejson()

    def pytest_testnodedown(self, node, error):
        # Called on the xdist controller when a worker finishes.
        # Merge the worker's coverage data into our map.
        workerdata = getattr(node, 'workeroutput', {}).get('testcov', {})
        self.covmap.update(workerdata)

    def _writejson(self):
        with open(self.output, 'wb') as fp:
            s_json.dump(self.covmap, fp, indent=True)

def pytest_addoption(parser):
    parser.addoption(
        '--testcov',
        metavar='PATH',
        default=None,
        help='Enable per-test coverage mapping and write results to PATH as JSON.',
    )

def pytest_configure(config):
    output = config.getoption('--testcov', default=None)
    if output is None:
        return

    plugin = TestCovPlugin(output)
    config.pluginmanager.register(plugin, 'testcov_plugin')
