import os
import logging
import pathlib
import argparse

import regex
import coverage.exceptions

import synapse.tests.files as s_files
import synapse.tests.utils as s_utils

import synapse.utils.stormcov as s_stormcov

logger = logging.getLogger(__name__)

class StormcovConfig:
    '''
    Helper class to simulate pytest config
    '''
    def __init__(self, stormcov=False, stormdirs='', stormexts='storm', stormcov_append=False, stormcov_basedir=s_stormcov.PACKAGE_DIR):
        self.option = argparse.Namespace(
            stormcov=stormcov,
            stormdirs=stormdirs,
            stormexts=stormexts,
            stormcov_append=stormcov_append,
            stormcov_basedir=pathlib.Path(stormcov_basedir)
        )

class TestUtilsStormcov(s_utils.SynTest):
    async def test_stormcov_basics(self):
        basedir = pathlib.Path(s_files.ASSETS)
        stormdir = str(basedir / 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormfiles = [
            s_files.getAssetPath('stormcov/argvquery.storm'),
            s_files.getAssetPath('stormcov/argvquery2.storm'),
            s_files.getAssetPath('stormcov/argvquery3.storm'),
            s_files.getAssetPath('stormcov/argvquery4.storm'),
            s_files.getAssetPath('stormcov/argvquery5.storm'),
            s_files.getAssetPath('stormcov/dupesubs.storm'),
            s_files.getAssetPath('stormcov/dupewarn.storm'),
            s_files.getAssetPath('stormcov/embedquery.storm'),
            s_files.getAssetPath('stormcov/embedquery2.storm'),
            s_files.getAssetPath('stormcov/embedquery3.storm'),
            s_files.getAssetPath('stormcov/embedquery4.storm'),
            s_files.getAssetPath('stormcov/embedquery5.storm'),
            s_files.getAssetPath('stormcov/lookup.storm'),
            s_files.getAssetPath('stormcov/pivot.storm'),
            s_files.getAssetPath('stormcov/pragma-nocov.storm'),
            s_files.getAssetPath('stormcov/spin.storm'),
            s_files.getAssetPath('stormcov/stormctrl.storm'),
        ]

        stormcov = s_stormcov.StormcovPlugin(opts)
        with self.getLoggerStream('synapse.utils.stormcov') as stream:
            stormcov.find_storm_files(stormdir)

        badstorm = s_files.getAssetPath('stormcov/badstorm.storm')
        stream.expect(f'Skipping invalid storm file: {badstorm}')

        self.sorteq(list(stormcov.guid_map.values()), stormfiles)
        stormcov.reset()

        stormcov.discover_stormdirs('')
        self.sorteq(list(stormcov.guid_map.values()), stormfiles)
        stormcov.reset()

        stormcov.stormdirs = []
        stormcov.discover_stormdirs([pathlib.Path(stormdir)])
        self.sorteq(list(stormcov.guid_map.values()), stormfiles)
        stormcov.reset()

    async def test_stormcov_dups(self):
        basedir = pathlib.Path(s_files.ASSETS)
        stormdir = str(basedir / 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        with self.getLoggerStream('synapse.utils.stormcov') as stream:
            stormcov.find_storm_files(stormdir)

        dupewarn = s_files.getAssetPath('stormcov/dupewarn.storm')
        self.isin(dupewarn, list(stormcov.guid_map.values()))

        storm = s_files.getAssetStr('stormcov/dupewarn.storm')

        # Read argvquery duplicate pairs
        argvdups = regex.search(r'\/\/ argvdups:.*?$', storm, flags=regex.M)
        self.nn(argvdups, msg='dupewarn.storm requires a "// argvdups: #:#, #:#, #:#" line')
        argvpairs = regex.findall(r'\d+:\d+', argvdups.group())

        # Read embedquery duplicate pairs
        embddups = regex.search(r'\/\/ embddups:.*?$', storm, flags=regex.M)
        self.nn(embddups, msg='dupewarn.storm requires a "// embddups: #:#, #:#, #:#" line')
        embdpairs = regex.findall(r'\d+:\d+', embddups.group())

        def splitpair(x):
            return list(map(int, x.split(':')))

        argvexp = map(splitpair, argvpairs)
        embdexp = map(splitpair, embdpairs)

        for last, first in embdexp:
            stream.expect(f'Duplicate embedquery in {dupewarn} at line {last}, coverage will be reported on first instance in {dupewarn} at line {first}')

        for last, first in argvexp:
            stream.expect(f'Duplicate argvquery in {dupewarn} at line {last}, coverage will be reported on first instance in {dupewarn} at line {first}')

    async def test_stormcov_coverage(self):
        basedir = pathlib.Path(s_files.ASSETS)
        stormdir = str(basedir / 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.find_storm_files(stormdir)

        async with self.getTestCore() as core:
            async def check_cov(filename):
                storm = s_files.getAssetStr(filename)
                stormcov._start_sysmon()
                await core.stormlist(storm)
                stormcov._stop_sysmon()

                coverage = regex.search(r'\/\/ coverage:.*?$', storm, flags=regex.M)
                self.nn(coverage, msg='Stormcov sample files require a "// coverage: #, #, #" line')

                linenums = regex.findall(r'\d+', coverage.group())
                expected = set(map(int, linenums))

                self.eq(dict(stormcov.lines_hit), {s_files.getAssetPath(filename): expected})

                stormcov.reset()

            await check_cov('stormcov/argvquery.storm')
            await check_cov('stormcov/argvquery2.storm')
            await check_cov('stormcov/argvquery3.storm')
            await check_cov('stormcov/argvquery4.storm')
            await check_cov('stormcov/argvquery5.storm')
            await check_cov('stormcov/dupesubs.storm')
            await check_cov('stormcov/embedquery.storm')
            await check_cov('stormcov/embedquery2.storm'),
            await check_cov('stormcov/embedquery3.storm'),
            await check_cov('stormcov/embedquery4.storm'),
            await check_cov('stormcov/embedquery5.storm'),
            await check_cov('stormcov/pivot.storm')
            await check_cov('stormcov/pragma-nocov.storm')
            await check_cov('stormcov/spin.storm')
            await check_cov('stormcov/stormctrl.storm')

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

        async def check_lines(filename):
            storm = s_files.getAssetStr(filename)
            reporter = s_stormcov.StormReporter(s_files.getAssetPath(filename), parser)

            lines = regex.search(r'\/\/ lines:.*?$', storm, flags=regex.M)
            self.nn(lines, msg='Stormcov sample files require a "// lines: #, #, #" line')

            linenums = regex.findall(r'\d+', lines.group())
            expected = set(map(int, linenums))

            self.eq(reporter.lines(), expected)

        await check_lines('stormcov/argvquery.storm')
        await check_lines('stormcov/argvquery2.storm')
        await check_lines('stormcov/argvquery3.storm')
        await check_lines('stormcov/argvquery4.storm')
        await check_lines('stormcov/argvquery5.storm')
        await check_lines('stormcov/dupesubs.storm')
        await check_lines('stormcov/embedquery.storm'),
        await check_lines('stormcov/embedquery2.storm'),
        await check_lines('stormcov/embedquery3.storm'),
        await check_lines('stormcov/embedquery4.storm'),
        await check_lines('stormcov/embedquery5.storm'),
        await check_lines('stormcov/lookup.storm')
        await check_lines('stormcov/pivot.storm')
        await check_lines('stormcov/pragma-nocov.storm')
        await check_lines('stormcov/spin.storm')
        await check_lines('stormcov/stormctrl.storm')

        # Non-existent file
        reporter = s_stormcov.StormReporter('newp', parser)
        with self.raises(coverage.exceptions.NoSource) as exc:
            reporter.source()
        self.eq(str(exc.exception), "Couldn't read newp: [Errno 2] No such file or directory: 'newp'")

    async def test_stormcov_stormreporter_plugin(self):
        plugin = s_stormcov.StormReporterPlugin()
        reporter = plugin.file_reporter(s_files.getAssetPath('stormcov/pivot.storm'))
        self.eq(reporter.lines(), {1, 2})
