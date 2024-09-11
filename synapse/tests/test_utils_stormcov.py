import logging
import inspect
import unittest.mock as mock

from coverage.exceptions import NoSource

import synapse.lib.ast as s_ast
import synapse.lib.snap as s_snap
import synapse.lib.stormctrl as s_stormctrl

import synapse.tests.files as s_files
import synapse.tests.utils as s_utils

import synapse.utils.stormcov as s_stormcov

logger = logging.getLogger(__name__)

class TestUtilsStormcov(s_utils.SynTest):
    async def test_basics(self):

        opts = {"storm_dirs": "synapse/tests/files/stormcov"}
        s_stormcov.coverage_init(mock.MagicMock(), opts)
        plugin = s_stormcov.StormPlugin(opts)

        reporter = plugin.file_reporter(s_files.getAssetPath('stormcov/stormctrl.storm'))
        self.eq(s_files.getAssetStr('stormcov/stormctrl.storm'), reporter.source())
        self.eq(reporter.lines(), {1, 2, 3, 6})
        self.eq(reporter.translate_lines({1, 2}), {1, 2})

        # no cover, no cover start, and no cover stop
        reporter = plugin.file_reporter(s_files.getAssetPath('stormcov/pragma-nocov.storm'))
        self.eq(reporter.lines(), {1, 2, 3, 12, 18})
        self.eq(reporter.excluded_lines(), {6, 8, 9, 10, 14, 15, 16})

        # We no longer do whitespace transformations of lines.
        reporter = plugin.file_reporter(s_files.getAssetPath('stormcov/spin.storm'))
        self.eq(reporter.translate_lines({1, 2}), {1, 2})

        with self.raises(NoSource):
            reporter = plugin.file_reporter('newp')
            reporter.source()

        stormtracer = plugin.file_tracer('synapse/lib/ast.py')
        self.true(stormtracer.has_dynamic_source_filename())
        self.none(stormtracer.dynamic_source_filename(None, inspect.currentframe()))

        ctrltracer = plugin.file_tracer('synapse/lib/stormctrl.py')
        self.true(ctrltracer.has_dynamic_source_filename())
        self.none(ctrltracer.dynamic_source_filename(None, inspect.currentframe()))

        pivotracer = plugin.file_tracer('synapse/lib/snap.py')
        self.true(pivotracer.has_dynamic_source_filename())
        self.none(pivotracer.dynamic_source_filename(None, inspect.currentframe()))

        self.none(plugin.file_tracer('newp'))

        async with self.getTestCore() as core:
            orig = s_stormctrl.StormCtrlFlow.__init__
            def __init__(self, item=None):
                frame = inspect.currentframe()
                assert 'stormctrl.storm' in ctrltracer.dynamic_source_filename(None, frame)
                assert (3, 3) == ctrltracer.line_number_range(frame)
                orig(self, item=item)

            with mock.patch('synapse.lib.stormctrl.StormCtrlFlow.__init__', __init__):
                await core.nodes(s_files.getAssetStr('stormcov/stormctrl.storm'))

            def __init__(self, item=None):
                frame = inspect.currentframe()
                assert 'argvquery.storm' in ctrltracer.dynamic_source_filename(None, frame)
                assert (4, 4) == ctrltracer.line_number_range(frame)
                orig(self, item=item)

            with mock.patch('synapse.lib.stormctrl.StormCtrlFlow.__init__', __init__):
                await core.stormlist(s_files.getAssetStr('stormcov/argvquery.storm'))

            def __init__(self, item=None):
                frame = inspect.currentframe()
                assert ctrltracer.dynamic_source_filename(None, frame) is None
                orig(self, item=item)

            with mock.patch('synapse.lib.stormctrl.StormCtrlFlow.__init__', __init__):
                await core.stormlist(s_files.getAssetStr('stormcov/lookup.storm'), opts={'mode': 'lookup'})

            orig = s_snap.Snap.nodesByPropValu
            async def nodesByPropValu(self, full, cmpr, valu, norm=True):
                frame = inspect.currentframe()
                if pivotracer.dynamic_source_filename(None, frame) is not None:
                    assert (2, 2) == pivotracer.line_number_range(frame)

                async for item in orig(self, full, cmpr, valu):
                    yield item

            with mock.patch('synapse.lib.snap.Snap.nodesByPropValu', nodesByPropValu):
                await core.nodes(s_files.getAssetStr('stormcov/pivot.storm'))

            async def pullone(genr):
                gotone = None
                async for gotone in genr:
                    break

                async def pullgenr():
                    frame = inspect.currentframe()
                    assert 'spin.storm' in stormtracer.dynamic_source_filename(None, frame)
                    assert (3, 3) == stormtracer.line_number_range(frame)

                    if gotone is None:
                        return

                    yield gotone
                    async for item in genr:
                        yield item

                return pullgenr(), gotone is None

            with mock.patch('synapse.lib.ast.pullone', pullone):
                await core.nodes(s_files.getAssetStr('stormcov/spin.storm'))

            async def pullone(genr):
                gotone = None
                async for gotone in genr:
                    break

                async def pullgenr():
                    frame = inspect.currentframe()
                    assert stormtracer.dynamic_source_filename(None, frame) is None

                    if gotone is None:
                        return

                    yield gotone
                    async for item in genr:
                        yield item

                return pullgenr(), gotone is None

            with mock.patch('synapse.lib.ast.pullone', pullone):
                await core.nodes(s_files.getAssetStr('stormcov/pivot.storm'))

            orig = s_ast.Const.compute
            async def compute(self, runt, valu):
                frame = inspect.currentframe()
                assert 'pivot.storm' in stormtracer.dynamic_source_filename(None, frame)
                assert stormtracer.line_number_range(frame) in ((1, 1), (2, 2))
                return await orig(self, runt, valu)

            with mock.patch('synapse.lib.ast.Const.compute', compute):
                await core.nodes(s_files.getAssetStr('stormcov/pivot.storm'))
