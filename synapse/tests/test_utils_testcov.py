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
