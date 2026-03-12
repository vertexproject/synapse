import os
import logging
import unittest.mock as mock

import pytest
import coverage

import synapse.lib.json as s_json

import synapse.tests.utils as s_utils

import synapse.utils.testcov as s_testcov
import synapse.utils.testcov.show as s_testcov_show

logger = logging.getLogger(__name__)

class TestUtilsTestcov(s_utils.SynTest):

    async def test_plugin_sessionstart_no_cov(self):
        # If no active coverage instance, pytest.exit is called.
        plugin = s_testcov.TestCovPlugin('/tmp/testcov.json')
        session = mock.MagicMock()

        with mock.patch('synapse.utils.testcov.coverage.Coverage.current', return_value=None):
            with self.raises(pytest.exit.Exception):
                plugin.pytest_sessionstart(session)

    async def test_plugin_sessionstart_with_cov(self):
        # Active coverage instance is stored on the plugin.
        plugin = s_testcov.TestCovPlugin('/tmp/testcov.json')
        session = mock.MagicMock()
        activecov = mock.MagicMock()

        with mock.patch('synapse.utils.testcov.coverage.Coverage.current', return_value=activecov):
            plugin.pytest_sessionstart(session)

        self.eq(plugin._activecov, activecov)

    async def test_plugin_hookwrapper(self):
        # pytest_runtest_protocol switches context, yields, switches back, collects.
        plugin = s_testcov.TestCovPlugin('/tmp/testcov.json')
        plugin._activecov = mock.MagicMock()

        item = mock.MagicMock()
        item.nodeid = 'synapse/tests/test_foo.py::TestFoo::test_hook'

        with mock.patch.object(plugin, '_collectone') as mock_collect:
            gen = plugin.pytest_runtest_protocol(item, None)
            next(gen)
            plugin._activecov.switch_context.assert_called_with(item.nodeid)
            mock_collect.assert_not_called()
            try:
                gen.send(None)
            except StopIteration:
                pass

        plugin._activecov.switch_context.assert_called_with('')
        mock_collect.assert_called_once_with(item.nodeid)

    async def test_plugin_collectone(self):
        # _collectone queries the active coverage data with a wildcard and
        # stores relative file paths.
        with self.getTestDir() as dirn:
            output = os.path.join(dirn, 'testcov.json')
            plugin = s_testcov.TestCovPlugin(output)

            # Use mocked coverage data to avoid competing with pytest-cov's tracer.
            # Two files: one absolute (should be relativised), one already relative.
            abspath = os.path.abspath('synapse/common.py')
            mockdata = mock.MagicMock()
            mockdata.measured_files.return_value = [abspath, '/no/such/file.py']
            mockdata.lines.side_effect = lambda path: [1, 2, 3] if path == abspath else []

            mockcov = mock.MagicMock()
            mockcov.get_data.return_value = mockdata

            plugin._activecov = mockcov
            plugin._collectone('test::alpha')

            mockdata.set_query_contexts.assert_any_call(['test::alpha*'])
            mockdata.set_query_contexts.assert_called_with(None)

            self.isin('test::alpha', plugin.covmap)
            filemap = plugin.covmap['test::alpha']

            # Absolute path must be stored as relative
            relpath = os.path.relpath(abspath)
            self.isin(relpath, filemap)
            self.eq(filemap[relpath], [1, 2, 3])

            # File with no lines must not appear
            self.notin('/no/such/file.py', filemap)
            self.notin(os.path.relpath('/no/such/file.py'), filemap)

            # All stored paths must be relative
            for path in filemap:
                self.false(os.path.isabs(path), msg=f'Expected relative path: {path}')

    async def test_plugin_collectone_with_phases(self):
        # Wildcard query pattern {nodeid}* aggregates setup/run/teardown sub-contexts.
        with self.getTestDir() as dirn:
            output = os.path.join(dirn, 'testcov.json')
            plugin = s_testcov.TestCovPlugin(output)

            mockdata = mock.MagicMock()
            mockdata.measured_files.return_value = ['synapse/common.py']
            mockdata.lines.return_value = [10, 11, 12]

            mockcov = mock.MagicMock()
            mockcov.get_data.return_value = mockdata

            plugin._activecov = mockcov
            plugin._collectone('test::foo')

            # Wildcard must be used so all phases are aggregated
            mockdata.set_query_contexts.assert_any_call(['test::foo*'])

    async def test_plugin_sessionfinish_local(self):
        # Non-xdist: writes JSON file.
        with self.getTestDir() as dirn:
            output = os.path.join(dirn, 'testcov.json')
            plugin = s_testcov.TestCovPlugin(output)
            plugin.covmap['test::foo'] = {'synapse/common.py': [1, 2]}

            session = mock.MagicMock()
            del session.config.workeroutput
            plugin.pytest_sessionfinish(session, 0)

            self.true(os.path.isfile(output))
            with open(output, 'rb') as fp:
                data = s_json.load(fp)
            self.eq(data, {'test::foo': {'synapse/common.py': [1, 2]}})

    async def test_plugin_sessionfinish_worker(self):
        # xdist worker: stashes covmap in workeroutput, does not write file.
        with self.getTestDir() as dirn:
            output = os.path.join(dirn, 'testcov.json')
            plugin = s_testcov.TestCovPlugin(output)
            plugin.covmap['test::bar'] = {'synapse/common.py': [5, 6]}

            workeroutput = {}
            session = mock.MagicMock()
            session.config.workeroutput = workeroutput

            plugin.pytest_sessionfinish(session, 0)

            self.false(os.path.isfile(output))
            self.eq(workeroutput['testcov'], {'test::bar': {'synapse/common.py': [5, 6]}})

    async def test_plugin_testnodedown(self):
        # Controller merges per-worker covmaps.
        with self.getTestDir() as dirn:
            output = os.path.join(dirn, 'testcov.json')
            plugin = s_testcov.TestCovPlugin(output)

            node1 = mock.MagicMock()
            node1.workeroutput = {'testcov': {'test::a': {'synapse/f.py': [1]}}}
            node2 = mock.MagicMock()
            node2.workeroutput = {'testcov': {'test::b': {'synapse/f.py': [2]}}}
            node3 = mock.MagicMock()
            node3.workeroutput = {}

            plugin.pytest_testnodedown(node1, None)
            plugin.pytest_testnodedown(node2, None)
            plugin.pytest_testnodedown(node3, None)

            self.eq(plugin.covmap, {
                'test::a': {'synapse/f.py': [1]},
                'test::b': {'synapse/f.py': [2]},
            })

    async def test_pytest_configure_enabled(self):
        config = mock.MagicMock()
        config.getoption.return_value = '/tmp/testcov.json'

        s_testcov.pytest_configure(config)

        config.pluginmanager.register.assert_called_once()
        (args, kwargs) = config.pluginmanager.register.call_args
        self.isinstance(args[0], s_testcov.TestCovPlugin)
        self.eq(args[1], 'testcov_plugin')

    async def test_pytest_configure_disabled(self):
        config = mock.MagicMock()
        config.getoption.return_value = None

        s_testcov.pytest_configure(config)

        config.pluginmanager.register.assert_not_called()

    async def test_pytest_addoption(self):
        parser = mock.MagicMock()
        s_testcov.pytest_addoption(parser)
        parser.addoption.assert_called_once_with(
            '--testcov',
            metavar='PATH',
            default=None,
            help='Enable per-test coverage mapping and write results to PATH as JSON.',
        )

    async def test_show_parsesrc(self):
        # _parsesrc handles line specs including ranges and bare filenames.
        (path, lines) = s_testcov_show._parsesrc('synapse/common.py:130,139-140')
        self.eq('synapse/common.py', path)
        self.eq(frozenset({130, 139, 140}), lines)

        (path, lines) = s_testcov_show._parsesrc('synapse/common.py:5')
        self.eq(frozenset({5}), lines)

        (path, lines) = s_testcov_show._parsesrc('synapse/common.py')
        self.none(lines)

        (path, lines) = s_testcov_show._parsesrc('synapse/common.py:')
        self.none(lines)

    async def test_show_parsediff(self):
        diff = '''\
diff --git a/synapse/common.py b/synapse/common.py
index abc1234..def5678 100644
--- a/synapse/common.py
+++ b/synapse/common.py
@@ -128,7 +128,9 @@
 context
 context
-removed line
+added line one
+added line two
 context
diff --git a/synapse/lib/cell.py b/synapse/lib/cell.py
index 111..222 100644
--- a/synapse/lib/cell.py
+++ b/synapse/lib/cell.py
@@ -10,3 +10,4 @@
 context
+new line
 context
'''
        result = s_testcov_show._parsediff(diff)

        # common.py: two added lines at new-side positions 130 and 131
        self.isin('synapse/common.py', result)
        self.eq(frozenset({130, 131}), result['synapse/common.py'])

        # cell.py: one added line at new-side position 11
        self.isin('synapse/lib/cell.py', result)
        self.eq(frozenset({11}), result['synapse/lib/cell.py'])

    async def test_show_parsediff_no_newline(self):
        # "\ No newline at end of file" markers are skipped gracefully.
        diff = '''\
diff --git a/synapse/common.py b/synapse/common.py
--- a/synapse/common.py
+++ b/synapse/common.py
@@ -1,2 +1,2 @@
-old
+new
\\ No newline at end of file
'''
        result = s_testcov_show._parsediff(diff)
        self.isin('synapse/common.py', result)
        self.eq(frozenset({1}), result['synapse/common.py'])

    async def test_show_parsediff_deleted_file(self):
        # Files deleted (/dev/null target) produce no entries.
        diff = '''\
diff --git a/synapse/old.py b/synapse/old.py
--- a/synapse/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-line1
-line2
-line3
'''
        result = s_testcov_show._parsediff(diff)
        self.notin('synapse/old.py', result)

    async def test_show_buildrevmap(self):
        covmap = {
            'test::alpha': {'synapse/common.py': [1, 2, 3]},
            'test::beta': {'synapse/common.py': [2, 3, 4], 'synapse/lib/cell.py': [10]},
        }
        revmap = s_testcov_show._buildrevmap(covmap)

        self.isin('synapse/common.py', revmap)
        self.isin('synapse/lib/cell.py', revmap)

        # Line 2 of common.py is covered by both tests
        self.eq(sorted(revmap['synapse/common.py'][2]), ['test::alpha', 'test::beta'])
        # Line 1 only by alpha
        self.eq(revmap['synapse/common.py'][1], ['test::alpha'])
        # Line 10 of cell.py only by beta
        self.eq(revmap['synapse/lib/cell.py'][10], ['test::beta'])

    async def test_show_querytests(self):
        covmap = {
            'test::alpha': {'synapse/common.py': [1, 2, 5]},
            'test::beta': {'synapse/common.py': [3, 4], 'synapse/lib/cell.py': [10]},
            'test::gamma': {'synapse/lib/cell.py': [20]},
        }
        revmap = s_testcov_show._buildrevmap(covmap)

        # Query specific lines
        result = s_testcov_show._querytests(revmap, [('synapse/common.py', frozenset({1, 3}))])
        self.eq(sorted(result), ['test::alpha', 'test::beta'])

        # Query with None (all lines in file)
        result = s_testcov_show._querytests(revmap, [('synapse/lib/cell.py', None)])
        self.eq(sorted(result), ['test::beta', 'test::gamma'])

        # File not in revmap returns empty
        result = s_testcov_show._querytests(revmap, [('synapse/missing.py', frozenset({1}))])
        self.eq(result, [])

        # Results are sorted
        result = s_testcov_show._querytests(revmap, [
            ('synapse/common.py', frozenset({1})),
            ('synapse/lib/cell.py', frozenset({10})),
        ])
        self.eq(result, ['test::alpha', 'test::beta'])

    async def test_show_src(self):
        # Positional FILE[:LINES] args perform reverse lookup.
        with self.getTestDir() as dirn:
            covfile = os.path.join(dirn, 'testcov.json')

            covmap = {
                'synapse/tests/test_foo.py::TestFoo::test_alpha': {
                    'synapse/common.py': [1, 2, 130, 140],
                },
                'synapse/tests/test_foo.py::TestFoo::test_beta': {
                    'synapse/common.py': [139, 140],
                },
                'synapse/tests/test_bar.py::TestBar::test_gamma': {
                    'synapse/cortex.py': [7],
                },
            }

            with open(covfile, 'wb') as fp:
                s_json.dump(covmap, fp)

            outp = self.getTestOutp()
            ret = await s_testcov_show.main([
                covfile,
                'synapse/common.py:130,139-140',
            ], outp=outp)
            self.eq(0, ret)
            outp.expect('synapse/tests/test_foo.py::TestFoo::test_alpha')
            outp.expect('synapse/tests/test_foo.py::TestFoo::test_beta')
            # test_gamma does not cover those lines
            self.false(outp.expect('test_gamma', throw=False))

    async def test_show_src_all_lines(self):
        # A bare filename (no line spec) returns all tests covering that file.
        with self.getTestDir() as dirn:
            covfile = os.path.join(dirn, 'testcov.json')

            covmap = {
                'test::alpha': {'synapse/common.py': [1, 2]},
                'test::beta': {'synapse/lib/cell.py': [10]},
            }

            with open(covfile, 'wb') as fp:
                s_json.dump(covmap, fp)

            outp = self.getTestOutp()
            ret = await s_testcov_show.main([covfile, 'synapse/common.py'], outp=outp)
            self.eq(0, ret)
            outp.expect('test::alpha')
            self.false(outp.expect('test::beta', throw=False))

    async def test_show_diff(self):
        # No positional args + non-TTY stdin reads git diff automatically.
        diff = '''\
diff --git a/synapse/common.py b/synapse/common.py
--- a/synapse/common.py
+++ b/synapse/common.py
@@ -128,4 +128,5 @@
 context
+new line
 context
'''
        with self.getTestDir() as dirn:
            covfile = os.path.join(dirn, 'testcov.json')

            covmap = {
                'test::alpha': {'synapse/common.py': [129]},
                'test::beta': {'synapse/common.py': [1]},
            }

            with open(covfile, 'wb') as fp:
                s_json.dump(covmap, fp)

            outp = self.getTestOutp()
            with mock.patch('synapse.utils.testcov.show.sys.stdin') as mockstdin:
                mockstdin.isatty.return_value = False
                mockstdin.read.return_value = diff
                ret = await s_testcov_show.main([covfile], outp=outp)

            self.eq(0, ret)
            outp.expect('test::alpha')
            self.false(outp.expect('test::beta', throw=False))

    async def test_show_tty_no_args(self):
        # No positional args + TTY stdin prints help and returns 0.
        with self.getTestDir() as dirn:
            covfile = os.path.join(dirn, 'testcov.json')

            with open(covfile, 'wb') as fp:
                s_json.dump({}, fp)

            outp = self.getTestOutp()
            with mock.patch('synapse.utils.testcov.show.sys.stdin') as mockstdin:
                mockstdin.isatty.return_value = True
                ret = await s_testcov_show.main([covfile], outp=outp)

            self.eq(0, ret)
            outp.expect('FILE[:LINES]')
