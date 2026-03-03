import os
import logging
import argparse

import synapse.tests.files as s_files
import synapse.tests.utils as s_utils

import synapse.utils.stormcov as s_stormcov

logger = logging.getLogger(__name__)

class StormcovConfig:
    '''
    Helper class to simulate pytest config
    '''
    def __init__(self, stormcov=False, stormdirs=[], stormexts='storm', stormcov_append=False, stormcov_basedir=s_stormcov.PACKAGE_DIR):
        self.option = argparse.Namespace(
            stormcov=stormcov,
            stormdirs=stormdirs,
            stormexts=stormexts,
            stormcov_append=stormcov_append,
            stormcov_basedir=stormcov_basedir,
        )

class TestUtilsStormcov(s_utils.SynTest):
    async def test_stormcov_basics(self):
        basedir = s_files.ASSETS
        stormdir = os.path.join(basedir, 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.find_storm_files(stormdir)
        self.eq(
            list(stormcov.guid_map.values()),
            [
                s_files.getAssetPath('stormcov/spin.storm'),
                s_files.getAssetPath('stormcov/stormctrl.storm'),
                s_files.getAssetPath('stormcov/lookup.storm'),
                s_files.getAssetPath('stormcov/pragma-nocov.storm'),
                s_files.getAssetPath('stormcov/dupesubs.storm'),
                s_files.getAssetPath('stormcov/pivot.storm'),
                s_files.getAssetPath('stormcov/argvquery.storm'),
            ]
        )

        async with self.getTestCore() as core:
            async def check_cov(filename, expected, stormopts=None):
                stormcov._start_sysmon()
                await core.stormlist(s_files.getAssetStr(filename), opts=stormopts)
                stormcov._stop_sysmon()

                self.eq(dict(stormcov.lines_hit), {s_files.getAssetPath(filename): expected})

                stormcov.reset()

            # await check_cov('stormcov/dupesubs.storm', {1, 2, 3, 4, 5, 6, 8, 9, 11})
            # await check_cov('stormcov/argvquery.storm', {1, 2, 3, 4, 8})
            await check_cov('stormcov/stormctrl.storm', {1, 2, 3, 6})
            await check_cov('stormcov/pivot.storm', {1, 2})
            await check_cov('stormcov/pragma-nocov.storm', {1, 2, 3, 18})
            await check_cov('stormcov/spin.storm', {2, 3})

    async def test_stormcov_lookup(self):
        basedir = s_files.ASSETS
        stormdir = os.path.join(basedir, 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.find_storm_files(stormdir)

        async with self.getTestCore() as core:
            await core.nodes('[ inet:fqdn=vertex.link ]')
            stormcov._start_sysmon()
            await core.stormlist(s_files.getAssetStr('stormcov/lookup.storm'), opts={'mode': 'lookup'})
            stormcov._stop_sysmon()

            # No coverage for lookup mode
            self.len(0, dict(stormcov.lines_hit))

    async def test_stormcov_stormreporter(self):
        parser = s_stormcov.get_parser()

        async def check_lines(filename, expected):
            reporter = s_stormcov.StormReporter(s_files.getAssetPath(filename), parser)
            self.eq(reporter.lines(), expected)

        await check_lines('stormcov/pivot.storm', {1, 2})
        await check_lines('stormcov/stormctrl.storm', {1, 2, 3, 6})
        await check_lines('stormcov/pragma-nocov.storm', {1, 2, 3, 12, 18})
        await check_lines('stormcov/spin.storm', {2, 3})
        await check_lines('stormcov/argvquery.storm', {1, 2, 3, 4, 8})
        await check_lines('stormcov/lookup.storm', {1, 2, 3, 5, 6})
        await check_lines('stormcov/dupesubs.storm', {1, 2, 4, 5, 7, 8, 9, 10, 12, 13, 14, 17})

    async def test_stormcov_stormreporter_plugin(self):
        plugin = s_stormcov.StormReporterPlugin()
        reporter = plugin.file_reporter(s_files.getAssetPath('stormcov/pivot.storm'))
        self.eq(reporter.lines(), {1, 2})
