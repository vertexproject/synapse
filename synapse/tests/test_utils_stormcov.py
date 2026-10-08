import gc
import os
import sys
import glob
import types
import logging
import pathlib
import argparse

import regex
import coverage
import coverage.exceptions

import synapse.lib.parser as s_parser
import synapse.tests.files as s_files
import synapse.tests.utils as s_utils

import synapse.utils.stormcov as s_stormcov

logger = logging.getLogger(__name__)

class StormcovConfig:
    '''
    Helper class to simulate pytest config
    '''
    def __init__(self, **kwargs):
        defaults = {
            'stormcov': False,
            'stormdirs': '',
            'stormexts': 'storm',
            'stormcov_append': False,
            'stormcov_basedir': s_stormcov.PACKAGE_DIR,
            'stormembedexts': ','.join(s_stormcov.DEFAULT_EMBED_EXTS),
            'stormpykeys': ','.join(s_stormcov.DEFAULT_PY_KEYS),
            'stormyamlkeys': ','.join(s_stormcov.DEFAULT_YAML_KEYS),
            'stormcov_data': s_stormcov.DEFAULT_DATA,
            'stormcov_branch': False,
        }

        defaults.update(kwargs)
        defaults['stormcov_basedir'] = pathlib.Path(defaults['stormcov_basedir'])
        self.option = argparse.Namespace(**defaults)

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
            s_files.getAssetPath('stormcov/dupfunc.storm'),
            s_files.getAssetPath('stormcov/continueloop.storm'),
            s_files.getAssetPath('stormcov/dupewarn.storm'),
            s_files.getAssetPath('stormcov/embedquery.storm'),
            s_files.getAssetPath('stormcov/embedquery2.storm'),
            s_files.getAssetPath('stormcov/embedquery3.storm'),
            s_files.getAssetPath('stormcov/embedquery4.storm'),
            s_files.getAssetPath('stormcov/embedquery5.storm'),
            s_files.getAssetPath('stormcov/emptybody.storm'),
            s_files.getAssetPath('stormcov/exprdict.storm'),
            s_files.getAssetPath('stormcov/forloop.storm'),
            s_files.getAssetPath('stormcov/ifelif.storm'),
            s_files.getAssetPath('stormcov/ifelse.storm'),
            s_files.getAssetPath('stormcov/lookup.storm'),
            s_files.getAssetPath('stormcov/pivot.storm'),
            s_files.getAssetPath('stormcov/pragma-nocov.storm'),
            s_files.getAssetPath('stormcov/runtsafety.storm'),
            s_files.getAssetPath('stormcov/spin.storm'),
            s_files.getAssetPath('stormcov/stormctrl.storm'),
            s_files.getAssetPath('stormcov/stopreturn.storm'),
            s_files.getAssetPath('stormcov/switch.storm'),
            s_files.getAssetPath('stormcov/switchnodefault.storm'),
            s_files.getAssetPath('stormcov/trycatch.storm'),
            s_files.getAssetPath('stormcov/whilebackedge.storm'),
            s_files.getAssetPath('stormcov/whilecontinue.storm'),
            s_files.getAssetPath('stormcov/whileloop.storm'),
            s_files.getAssetPath('stormcov/whilewithnode.storm'),
        ]

        stormcov = s_stormcov.StormcovPlugin(opts)
        with self.getLoggerStream('synapse.utils.stormcov') as stream:
            stormcov.findStormFiles(stormdir)

        badstorm = s_files.getAssetPath('stormcov/badstorm.storm')
        await stream.expect(f'Skipping invalid storm file: {badstorm}', timeout=1)

        self.sorteq([p for v in stormcov.guid_map.values() for p in v], stormfiles)
        stormcov.reset()

        stormcov.discoverStormdirs('')
        self.sorteq([p for v in stormcov.guid_map.values() for p in v], stormfiles)
        stormcov.reset()

        stormcov.stormdirs = []
        stormcov.discoverStormdirs([pathlib.Path(stormdir)])
        self.sorteq([p for v in stormcov.guid_map.values() for p in v], stormfiles)
        stormcov.reset()

    async def test_stormcov_dups(self):
        basedir = pathlib.Path(s_files.ASSETS)
        stormdir = str(basedir / 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.findStormFiles(stormdir)

        dupewarn = s_files.getAssetPath('stormcov/dupewarn.storm')
        self.isin(dupewarn, [p for v in stormcov.guid_map.values() for p in v])

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

        # Pairs where positions differ should produce 2 entries in subq_map (one per
        # occurrence); same-position pairs collapse to 1 entry since the entry tuple is
        # identical.  embddups has 2 differing pairs and argvdups has 2 differing pairs,
        # so exactly 4 GUIDs (restricted to dupewarn.storm entries) should have 2+ entries.
        multi_entry_guids = {
            guid for guid, entries in stormcov.subq_map.items()
            if sum(1 for p, _, _ in entries if p == dupewarn) > 1
        }

        embd_diff = sum(1 for pair in map(splitpair, embdpairs) if pair[0] != pair[1])
        argv_diff = sum(1 for pair in map(splitpair, argvpairs) if pair[0] != pair[1])
        self.eq(len(multi_entry_guids), embd_diff + argv_diff)

    async def test_stormcov_coverage(self):
        basedir = pathlib.Path(s_files.ASSETS)
        stormdir = str(basedir / 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.findStormFiles(stormdir)

        async with self.getTestCore() as core:
            async def check_cov(filename):
                storm = s_files.getAssetStr(filename)
                stormcov._startSysmon()
                await core.stormlist(storm)
                stormcov._stopSysmon()

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
            await check_cov('stormcov/dupfunc.storm')
            await check_cov('stormcov/embedquery.storm')
            await check_cov('stormcov/embedquery2.storm'),
            await check_cov('stormcov/embedquery3.storm'),
            await check_cov('stormcov/embedquery4.storm'),
            await check_cov('stormcov/embedquery5.storm'),
            await check_cov('stormcov/emptybody.storm')
            await check_cov('stormcov/exprdict.storm')
            await check_cov('stormcov/ifelif.storm')
            await check_cov('stormcov/ifelse.storm')
            await check_cov('stormcov/pivot.storm')
            await check_cov('stormcov/pragma-nocov.storm')
            await check_cov('stormcov/runtsafety.storm')
            await check_cov('stormcov/spin.storm')
            await check_cov('stormcov/stormctrl.storm')
            await check_cov('stormcov/switch.storm')
            await check_cov('stormcov/switchnodefault.storm')
            await check_cov('stormcov/whilebackedge.storm')
            await check_cov('stormcov/whilecontinue.storm')
            await check_cov('stormcov/whileloop.storm')

    async def test_stormcov_reused_id(self):
        basedir = pathlib.Path(s_files.ASSETS)
        stormdir = str(basedir / 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.findStormFiles(stormdir)

        def mark(query):
            stormcov.handleAst(None, frame=types.SimpleNamespace(f_locals={'self': query}))

        # Dead-end queries (no storm source) are freed and a storm file query may then be
        # allocated at one of their addresses; it must still be attributed to its file.
        text = s_files.getAssetStr('stormcov/ifelse.storm')

        reused = None
        for _ in range(20):
            dead = [s_parser.parseQuery('[ inet:fqdn=newp.com ]') for _ in range(50)]
            for query in dead:
                mark(query)

            deadids = {id(query) for query in dead}
            del dead
            gc.collect()

            keep = []
            for _ in range(200):
                query = s_parser.parseQuery(text)
                if id(query) in deadids:
                    reused = query
                    break

                keep.append(query)

            if reused is not None:
                break

        self.nn(reused)
        self.len(0, stormcov.lines_hit)

        mark(reused)
        self.eq(dict(stormcov.lines_hit), {s_files.getAssetPath('stormcov/ifelse.storm'): {1}})

    async def test_stormcov_lookup(self):
        basedir = s_files.ASSETS
        stormdir = os.path.join(basedir, 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.findStormFiles(stormdir)

        async with self.getTestCore() as core:
            await core.nodes('[ inet:fqdn=vertex.link ]')
            stormcov._startSysmon()
            await core.stormlist(s_files.getAssetStr('stormcov/lookup.storm'), opts={'mode': 'lookup'})
            stormcov._stopSysmon()

            # No coverage for lookup mode
            self.len(0, dict(stormcov.lines_hit))

    async def test_stormcov_stormreporter(self):
        parser = s_stormcov.getParser()

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
        await check_lines('stormcov/dupfunc.storm')
        await check_lines('stormcov/embedquery.storm'),
        await check_lines('stormcov/embedquery2.storm'),
        await check_lines('stormcov/embedquery3.storm'),
        await check_lines('stormcov/embedquery4.storm'),
        await check_lines('stormcov/embedquery5.storm'),
        await check_lines('stormcov/emptybody.storm')
        await check_lines('stormcov/exprdict.storm')
        await check_lines('stormcov/continueloop.storm')
        await check_lines('stormcov/forloop.storm')
        await check_lines('stormcov/ifelif.storm')
        await check_lines('stormcov/ifelse.storm')
        await check_lines('stormcov/lookup.storm')
        await check_lines('stormcov/pivot.storm')
        await check_lines('stormcov/pragma-nocov.storm')
        await check_lines('stormcov/runtsafety.storm')
        await check_lines('stormcov/spin.storm')
        await check_lines('stormcov/stormctrl.storm')
        await check_lines('stormcov/stopreturn.storm')
        await check_lines('stormcov/switch.storm')
        await check_lines('stormcov/switchnodefault.storm')
        await check_lines('stormcov/trycatch.storm')
        await check_lines('stormcov/whilebackedge.storm')
        await check_lines('stormcov/whilecontinue.storm')
        await check_lines('stormcov/whileloop.storm')

        # Non-existent file
        reporter = s_stormcov.StormReporter('newp', parser)
        with self.raises(coverage.exceptions.NoSource) as exc:
            reporter.source()
        self.eq(str(exc.exception), "Couldn't read newp: [Errno 2] No such file or directory: 'newp'")

    async def test_stormcov_stormreporter_plugin(self):
        plugin = s_stormcov.StormReporterPlugin()
        reporter = plugin.file_reporter(s_files.getAssetPath('stormcov/pivot.storm'))
        self.eq(reporter.lines(), {1, 2})

    async def test_stormcov_arcs_reporter(self):
        parser = s_stormcov.getParser()

        def parse_arcs(text):
            pairs = regex.findall(r'\((-?\d+),(-?\d+)\)', text)
            return {(int(a), int(b)) for a, b in pairs}

        async def check_arcs(filename):
            storm = s_files.getAssetStr(filename)
            reporter = s_stormcov.StormReporter(s_files.getAssetPath(filename), parser)

            arcs_line = regex.search(r'\/\/ arcs:.*?$', storm, flags=regex.M)
            self.nn(arcs_line, msg=f'{filename} requires a "// arcs: (-1,1), (1,2), ..." line')

            expected = parse_arcs(arcs_line.group())
            self.eq(reporter.arcs(), expected, msg=f'arcs mismatch for {filename}')

        await check_arcs('stormcov/emptybody.storm')
        await check_arcs('stormcov/ifelif.storm')
        await check_arcs('stormcov/ifelse.storm')
        await check_arcs('stormcov/switch.storm')
        await check_arcs('stormcov/switchnodefault.storm')
        await check_arcs('stormcov/forloop.storm')
        await check_arcs('stormcov/whileloop.storm')
        await check_arcs('stormcov/trycatch.storm')
        await check_arcs('stormcov/continueloop.storm')
        await check_arcs('stormcov/stopreturn.storm')
        await check_arcs('stormcov/runtsafety.storm')
        await check_arcs('stormcov/whilebackedge.storm')
        await check_arcs('stormcov/whilecontinue.storm')

    async def test_stormcov_arcs_runtime(self):
        basedir = pathlib.Path(s_files.ASSETS)
        stormdir = str(basedir / 'stormcov')
        opts = StormcovConfig(stormdirs=stormdir, stormcov_basedir=basedir)

        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.findStormFiles(stormdir)

        def parse_arcs(text):
            pairs = regex.findall(r'\((-?\d+),(-?\d+)\)', text)
            return {(int(a), int(b)) for a, b in pairs}

        async with self.getTestCore() as core:

            async def check_arcs(filename):
                storm = s_files.getAssetStr(filename)
                stormcov._startSysmon()
                await core.stormlist(storm)
                stormcov._stopSysmon()
                stormcov.finalizeArcs()

                arcs_line = regex.search(r'\/\/ arcs_hit:.*?$', storm, flags=regex.M)
                self.nn(arcs_line, msg=f'{filename} requires a "// arcs_hit: (-1,1), (1,2), ..." line')

                expected_arcs = parse_arcs(arcs_line.group())

                fpath = s_files.getAssetPath(filename)
                actual = stormcov.arcs_hit.get(fpath, set())
                self.true(expected_arcs.issubset(actual),
                          msg=f'arcs_hit mismatch for {filename}: missing {expected_arcs - actual}')

                stormcov.reset()

            await check_arcs('stormcov/ifelse.storm')
            await check_arcs('stormcov/switch.storm')
            await check_arcs('stormcov/forloop.storm')
            await check_arcs('stormcov/whileloop.storm')
            await check_arcs('stormcov/exprdict.storm')
            await check_arcs('stormcov/ifelif.storm')
            await check_arcs('stormcov/switchnodefault.storm')
            await check_arcs('stormcov/whilecontinue.storm')
            await check_arcs('stormcov/emptybody.storm')
            await check_arcs('stormcov/runtsafety.storm')
            await check_arcs('stormcov/whilebackedge.storm')

    async def test_stormcov_exit_counts(self):
        parser = s_stormcov.getParser()

        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/ifelse.storm'), parser)
        counts = reporter.exit_counts()
        # Line 1 (if condition) has 2 destinations: line 2 (true) and line 4 (else)
        self.eq(counts.get(1), 2)
        # Lines 2 and 4 have 1 destination each (exit)
        self.eq(counts.get(2), 1)
        self.eq(counts.get(4), 1)

    async def test_stormcov_missing_arc_description(self):
        parser = s_stormcov.getParser()

        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/ifelse.storm'), parser)
        self.eq(reporter.missing_arc_description(1, 4), 'the if/elif condition on line 1 did not jump to line 4')
        self.eq(reporter.missing_arc_description(2, -1), 'the exit was not reached')
        self.eq(reporter.missing_arc_description(-1, 1), 'the entry to line 1 was not reached')

        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/forloop.storm'), parser)
        self.eq(reporter.missing_arc_description(1, 2), 'the for loop on line 1 did not jump to line 2')
        self.eq(reporter.missing_arc_description(2, -1), 'the exit was not reached')

        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/whileloop.storm'), parser)
        self.eq(reporter.missing_arc_description(1, 2), 'the while loop on line 1 did not jump to line 2')

        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/whilebackedge.storm'), parser)
        self.eq(reporter.missing_arc_description(2, 1), 'the while loop on line 2 did not loop back to line 1')

        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/switch.storm'), parser)
        self.eq(reporter.missing_arc_description(2, 4), 'the switch on line 2 did not jump to line 4')

        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/trycatch.storm'), parser)
        # trycatch starts on line 1 even though first executable token is on line 2
        self.eq(reporter.missing_arc_description(1, 3), 'the try/catch on line 1 did not jump to line 3')

        # Fallback for non-branching line
        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/pivot.storm'), parser)
        self.eq(reporter.missing_arc_description(1, 2), 'line 1 did not jump to line 2')

    async def test_stormcov_no_branch_lines(self):
        parser = s_stormcov.getParser()
        reporter = s_stormcov.StormReporter(s_files.getAssetPath('stormcov/pragma-nocov.storm'), parser)
        self.eq(reporter.no_branch_lines(), reporter.excluded_lines())

    async def test_stormcov_embedded_extract(self):
        pykeys = frozenset(s_stormcov.DEFAULT_PY_KEYS)
        yamlkeys = frozenset(s_stormcov.DEFAULT_YAML_KEYS)

        def getstorm(path, pyk=pykeys, yamlk=yamlkeys):
            return list(s_stormcov.getEmbeddedStorm(path, pyk, yamlk))

        pypath = s_files.getAssetPath('stormcov/embed/embed.py')
        yamlpath = s_files.getAssetPath('stormcov/embed/embed.yaml')

        # Escaped newlines, implicit concatenation, f-strings, and other names are skipped
        found = getstorm(pypath)
        self.eq([offs for _, offs in found], [1, 9, 13, 26, 32])
        self.eq(found[2][0], 'inet:fqdn=vertex.link')
        self.eq(found[3][0], 'inet:fqdn=class.link')

        found = getstorm(pypath, pyk=frozenset(['notstorm']))
        self.eq([offs for _, offs in found], [16])

        # Folded scalars, non-strings, and aliases are skipped
        found = getstorm(yamlpath)
        self.eq([offs for _, offs in found], [5, 10, 17, 30, 39, 45])
        self.eq(found[1][0], 'inet:fqdn=vertex.link | limit 1')

        found = getstorm(yamlpath, yamlk=frozenset(['value']))
        self.eq([offs for _, offs in found], [33])

        self.eq([], getstorm(s_files.getAssetPath('stormcov/argvquery.storm')))

        with self.getTestDir() as dirn:

            def write(name, text):
                path = os.path.join(dirn, name)
                with open(path, 'w') as fd:
                    fd.write(text)
                return path

            badpy = write('bad.py', 'def (:\n')
            with self.getLoggerStream('synapse.utils.stormcov') as stream:
                self.eq([], getstorm(badpy))
            await stream.expect(f'Skipping unparsable python file: {badpy}', timeout=1)

            badyaml = write('bad.yaml', 'a: [\n')
            with self.getLoggerStream('synapse.utils.stormcov') as stream:
                self.eq([], getstorm(badyaml))
            await stream.expect(f'Skipping unparsable yaml file: {badyaml}', timeout=1)

            multi = write('multi.yaml', (
                '---\n'
                'query: foo\n'
                '---\n'
                '- storm: bar\n'
                '- query: "a\\nb"\n'
                '- query: ""\n'
                '- query: "  "\n'
                '- query: "multi\n'
                '    line"\n'
                '- query: 5\n'
                '- query:\n'
                '- storm: |-\n'
                '    baz\n'
                '---\n'
                '? [a]\n'
                ': b\n'
            ))
            self.eq(getstorm(multi), [('foo', 1), ('bar', 3), ('baz', 12)])

    async def test_stormcov_embedded_discovery(self):
        basedir = s_files.ASSETS
        embeddir = os.path.join(basedir, 'stormcov', 'embed')
        pypath = s_files.getAssetPath('stormcov/embed/embed.py')
        yamlpath = s_files.getAssetPath('stormcov/embed/embed.yaml')

        # Embedded storm is found by default
        opts = StormcovConfig(stormdirs=embeddir, stormcov_basedir=basedir)
        stormcov = s_stormcov.StormcovPlugin(opts)
        self.sorteq(stormcov.embedexts, ['py', 'yaml', 'yml'])
        stormcov.findStormFiles(embeddir)
        self.eq(stormcov.embed_hosts, {pypath, yamlpath})

        # An empty extension list disables it
        opts = StormcovConfig(stormdirs=embeddir, stormcov_basedir=basedir, stormembedexts='')
        stormcov = s_stormcov.StormcovPlugin(opts)
        self.eq(stormcov.embedexts, [])
        stormcov.findStormFiles(embeddir)
        self.eq(stormcov.embed_map, {})
        self.eq(stormcov.embed_hosts, set())

        opts = StormcovConfig(stormdirs=embeddir, stormcov_basedir=basedir, stormembedexts='py, yaml,bogus')
        stormcov = s_stormcov.StormcovPlugin(opts)
        self.sorteq(stormcov.embedexts, ['py', 'yaml'])
        stormcov.findStormFiles(embeddir)

        self.eq(stormcov.guid_map, {})
        self.eq(stormcov.embed_hosts, {pypath, yamlpath})

        expected = [(pypath, offs) for offs in (1, 9, 13, 26, 32)]
        expected += [(yamlpath, offs) for offs in (5, 10, 17, 30, 39, 45)]
        self.sorteq([loc for v in stormcov.embed_map.values() for loc in v], expected)

        # The two identical subqueries are tracked by their position in the embedded text
        self.eq([sorted(v) for v in stormcov.subq_map.values()], [[(yamlpath, 17, 0), (yamlpath, 20, 3)]])

        with self.getTestDir() as dirn:

            def write(name, text):
                path = os.path.join(dirn, name)
                with open(path, 'w') as fd:
                    fd.write(text)
                return path

            foopy = write('foo.py', "_storm_query = 'inet:fqdn'\n")
            fooyaml = write('foo.yaml', 'query: inet:fqdn\n')
            badstorm = write('bad.yaml', 'query: "|||"\n')

            # Test files are not product code
            write('test_foo.py', "_storm_query = 'inet:fqdn'\n")
            write('conftest.py', "_storm_query = 'inet:fqdn'\n")

            # Recorded HTTP cassettes are not product code either
            write('foo.vcr.yaml', 'query: inet:fqdn\n')

            opts = StormcovConfig(stormdirs=dirn, stormcov_basedir=basedir, stormembedexts='py,yaml,yml')
            stormcov = s_stormcov.StormcovPlugin(opts)
            stormcov.findStormFiles(dirn)

            self.eq(stormcov.embed_hosts, {foopy, fooyaml})
            self.notin(badstorm, stormcov.embed_hosts)

            # Custom keys
            opts = StormcovConfig(stormdirs=dirn, stormcov_basedir=basedir, stormembedexts='py', stormpykeys='other')
            stormcov = s_stormcov.StormcovPlugin(opts)
            stormcov.findStormFiles(dirn)
            self.eq(stormcov.embed_hosts, set())

    async def test_stormcov_embedded_coverage(self):
        basedir = s_files.ASSETS
        embeddir = os.path.join(basedir, 'stormcov', 'embed')
        pypath = s_files.getAssetPath('stormcov/embed/embed.py')
        yamlpath = s_files.getAssetPath('stormcov/embed/embed.yaml')

        opts = StormcovConfig(stormdirs=embeddir, stormcov_basedir=basedir, stormembedexts='py,yaml')
        stormcov = s_stormcov.StormcovPlugin(opts)
        stormcov.findStormFiles(embeddir)

        expected = {
            pypath: {
                1: {3, 4, 5},
                9: {11, 12},
                13: {14},
                26: {27},
                32: {33},
            },
            yamlpath: {
                5: {6, 7, 8},
                10: {11},
                # The identical subqueries are attributed to their own lines
                17: {18, 19, 21, 22, 24},
                30: {31},
                39: {40},
                45: {46, 47},
            },
        }

        async with self.getTestCore() as core:

            for path, snips in expected.items():
                for text, offs in s_stormcov.getEmbeddedStorm(path, stormcov.pykeys, stormcov.yamlkeys):
                    stormcov._startSysmon()
                    await core.stormlist(text)
                    stormcov._stopSysmon()

                    self.eq(dict(stormcov.lines_hit), {path: snips[offs]}, msg=f'{path} {offs}')
                    stormcov.reset()

            # Storm which is not embedded anywhere is not attributed
            stormcov._startSysmon()
            await core.stormlist('inet:fqdn=nothing.link')
            stormcov._stopSysmon()
            self.eq(dict(stormcov.lines_hit), {})
            stormcov.reset()

            text = next(s_stormcov.getEmbeddedStorm(pypath, stormcov.pykeys, stormcov.yamlkeys))[0]
            stormcov._startSysmon()
            await core.stormlist(text)
            stormcov._stopSysmon()
            stormcov.finalizeArcs()
            self.eq(list(stormcov.arcs_hit), [pypath])
            self.true({(-1, 3), (3, 4), (4, 5), (5, -1)}.issubset(stormcov.arcs_hit[pypath]))

    async def test_stormcov_embedded_reporter(self):
        pypath = s_files.getAssetPath('stormcov/embed/embed.py')
        yamlpath = s_files.getAssetPath('stormcov/embed/embed.yaml')

        plugin = s_stormcov.StormReporterPlugin()

        reporter = plugin.file_reporter(pypath)
        self.isinstance(reporter, s_stormcov.EmbeddedStormReporter)
        self.eq(reporter.lines(), {3, 4, 5, 11, 12, 14, 27, 33})
        self.eq(reporter.arcs(), {
            (-1, 3), (-1, 11), (-1, 14), (-1, 27), (-1, 33), (33, -1),
            (3, 4), (4, 5), (4, -1), (5, -1),
            (11, 12), (12, -1), (14, -1), (27, -1),
        })

        # The source shown is the host file
        self.eq(reporter.source(), s_files.getAssetStr('stormcov/embed/embed.py'))

        reporter = plugin.file_reporter(yamlpath)
        self.isinstance(reporter, s_stormcov.EmbeddedStormReporter)

        # The no cover pragma inside the embedded storm excludes its line
        self.eq(reporter.excluded_lines(), {46})
        self.eq(reporter.lines(), {6, 7, 8, 11, 18, 19, 21, 22, 24, 31, 40, 47})

        arcs = reporter.arcs()
        self.isin((7, 8), arcs)
        self.isin((18, 21), arcs)
        self.isin((21, 24), arcs)
        self.isin((47, -1), arcs)
        self.notin((-1, 46), arcs)
        self.notin((46, 47), arcs)

        self.eq(reporter.exit_counts().get(7), 2)
        self.eq(reporter.no_branch_lines(), {46})

        self.eq(reporter.missing_arc_description(7, 8), 'the if/elif condition on line 7 did not jump to line 8')
        self.eq(reporter.missing_arc_description(6, 7), 'line 6 did not jump to line 7')
        self.eq(reporter.missing_arc_description(7, -1), 'the exit was not reached')
        self.eq(reporter.missing_arc_description(-1, 6), 'the entry to line 6 was not reached')

        # Reporting uses the same keys as collection
        plugin = s_stormcov.StormReporterPlugin(pykeys=s_stormcov.splitKeys('notstorm'), yamlkeys=('value',))
        self.eq(plugin.pykeys, frozenset({'notstorm'}))
        self.eq(plugin.yamlkeys, frozenset({'value'}))
        self.eq(plugin.file_reporter(pypath).lines(), {18})
        self.eq(plugin.file_reporter(yamlpath).lines(), {34})

        # Other files are not embedded hosts
        reporter = plugin.file_reporter(s_files.getAssetPath('stormcov/ifelse.storm'))
        self.false(isinstance(reporter, s_stormcov.EmbeddedStormReporter))

        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'foo.yml')
            with open(path, 'w') as fd:
                fd.write('a:\n  query: "|||"\nb:\n  query: inet:fqdn\n')

            plugin = s_stormcov.StormReporterPlugin()
            self.eq(plugin.pykeys, frozenset(s_stormcov.DEFAULT_PY_KEYS))
            self.eq(plugin.yamlkeys, frozenset(s_stormcov.DEFAULT_YAML_KEYS))

            reporter = plugin.file_reporter(path)
            self.isinstance(reporter, s_stormcov.EmbeddedStormReporter)
            self.eq(reporter.lines(), {4})

    async def test_stormcov_embedded_data(self):
        stormcov = s_stormcov.StormcovPlugin(StormcovConfig())
        self.true(stormcov.isEmbedHost('/a/b.py'))
        self.true(stormcov.isEmbedHost('/a/b.PY'))
        self.true(stormcov.isEmbedHost('/a/b.yaml'))
        self.true(stormcov.isEmbedHost('/a/b.yml'))
        self.false(stormcov.isEmbedHost('/a/b.storm'))
        self.false(stormcov.isEmbedHost('/a/b'))

        with self.getTestDir() as dirn:
            embeddata = os.path.join(dirn, 'stormembed')
            stormcov = s_stormcov.StormcovPlugin(StormcovConfig(stormembedexts='py,yaml', stormcov_data=embeddata))

            # Nothing to combine
            stormcov.combineEmbedData()
            self.false(os.path.exists(embeddata))

            files = ['/x/a.py', '/x/b.py', '/x/c.yaml']
            hits = (
                {'/x/a.py': {1, 2}},
                {'/x/a.py': {2, 3}, '/x/b.py': {5}, '/x/c.yaml': {7}},
            )
            for lines in hits:
                data = coverage.CoverageData(basename=embeddata, suffix=True)
                stormcov.addHits(data, lines, False, files)
                data.write()
                data.close()

            self.len(2, glob.glob(f'{embeddata}.*'))

            stormcov.combineEmbedData()
            self.eq(glob.glob(f'{embeddata}.*'), [])

            data = coverage.CoverageData(basename=embeddata)
            data.read()
            self.eq(sorted(data.lines('/x/a.py')), [1, 2, 3])
            self.eq(sorted(data.lines('/x/b.py')), [5])
            self.eq(sorted(data.lines('/x/c.yaml')), [7])
            self.eq(data.file_tracer('/x/a.py'), s_stormcov.PLUGIN_NAME)
            self.eq(data.file_tracer('/x/c.yaml'), s_stormcov.PLUGIN_NAME)
            data.close()

            arcdata = coverage.CoverageData(basename=os.path.join(dirn, 'stormarcs'))
            stormcov.addHits(arcdata, {'/x/a.py': {(-1, 1), (1, -1)}}, True, files)
            self.eq(sorted(arcdata.arcs('/x/a.py')), [(-1, 1), (1, -1)])
            self.eq(arcdata.file_tracer('/x/b.py'), s_stormcov.PLUGIN_NAME)
            arcdata.close()

    async def test_stormcov_identical_text(self):
        basedir = s_files.ASSETS

        with self.getTestDir() as dirn:

            def write(name, text):
                path = os.path.join(dirn, name)
                with open(path, 'w') as fd:
                    fd.write(text)
                return path

            # The same text in two python literals, a storm file and a yaml file with an alias
            dups = write('dups.py', "a = {'storm': 'inet:fqdn=dup.link'}\nb = {'storm': 'inet:fqdn=dup.link'}\n")
            one = write('one.storm', 'inet:fqdn=dup.link\n')
            two = write('two.storm', 'inet:fqdn=dup.link\n')
            yml = write('dups.yaml', 'a:\n  query: &q |\n    inet:fqdn=dup.link\nb:\n  query: *q\n')

            # The same subquery at the same line of two different queries
            sub1 = write('sub1.storm', 'tee ${ inet:fqdn=sub.link }\n')
            sub2 = write('sub2.storm', 'tee ${ inet:fqdn=sub.link } | limit 1\n')

            opts = StormcovConfig(stormdirs=dirn, stormcov_basedir=basedir)
            stormcov = s_stormcov.StormcovPlugin(opts)
            stormcov.findStormFiles(dirn)

            # Every location is kept, once
            self.sorteq([p for v in stormcov.guid_map.values() for p in v if p in (one, two)], [one, two])
            self.sorteq([loc for v in stormcov.embed_map.values() for loc in v if loc[0] in (dups, yml)],
                        [(dups, 0), (dups, 1), (yml, 2)])

            async with self.getTestCore() as core:

                stormcov._startSysmon()
                await core.stormlist('inet:fqdn=dup.link')
                stormcov._stopSysmon()
                stormcov.finalizeArcs()

                # Running the text credits all of the places it appears
                hits = dict(stormcov.lines_hit)
                self.eq(hits[dups], {1, 2})
                self.eq(hits[one], {1})
                self.eq(hits[two], {1})
                self.eq(hits[yml], {3})
                self.notin(sub1, hits)

                # Copies in one file do not link to each other
                arcs = stormcov.arcs_hit[dups]
                self.true({(-1, 1), (1, -1), (-1, 2), (2, -1)}.issubset(arcs))
                self.false({(1, 2), (2, 1)} & arcs)
                stormcov.reset()

                # An identical subquery at the same line is credited in both queries
                stormcov._startSysmon()
                await core.stormlist('tee ${ inet:fqdn=sub.link }')
                stormcov._stopSysmon()

                self.isin(sub1, stormcov.lines_hit)
                self.isin(sub2, stormcov.lines_hit)
                self.notin(one, stormcov.lines_hit)

    async def test_stormcov_embedded_nonstorm(self):
        basedir = s_files.ASSETS

        with self.getTestDir() as dirn:

            def write(name, text):
                path = os.path.join(dirn, name)
                with open(path, 'w') as fd:
                    fd.write(text)
                return path

            # Values under a Storm key name which are not Storm at all are skipped
            write('nostr.py', "storm = None\n_storm_query = 5\nstorm = {'a': 1}\n")
            write('nostr.yaml', 'a:\n  query: true\nb:\n  query:\n  onload: null\nc:\n  query: 1\nd:\n  storm: [a, b]\n')

            # Text which is not valid Storm is skipped
            write('bad.py', "storm = 'not storm |||'\n")
            write('bad.yaml', 'query: "not storm |||"\n')

            opts = StormcovConfig(stormdirs=dirn, stormcov_basedir=basedir)
            stormcov = s_stormcov.StormcovPlugin(opts)
            stormcov.findStormFiles(dirn)

            self.eq(stormcov.embed_hosts, set())
            self.eq(stormcov.embed_map, {})

            # Other text which happens to parse is indistinguishable from Storm, so it is measured
            text = write('words.yaml', 'query: some search text\n')
            stormcov.findStormFiles(dirn)
            self.eq(stormcov.embed_hosts, {text})

    async def test_stormcov_save_hits(self):
        basedir = s_files.ASSETS
        embeddir = os.path.join(basedir, 'stormcov', 'embed')
        pypath = s_files.getAssetPath('stormcov/embed/embed.py')
        stormfile = s_files.getAssetPath('stormcov/ifelse.storm')

        with self.getTestDir() as dirn:
            embeddata = os.path.join(dirn, 'stormembed')

            def getplugin():
                opts = StormcovConfig(stormdirs=embeddir, stormcov_basedir=basedir, stormcov_data=embeddata)
                stormcov = s_stormcov.StormcovPlugin(opts)
                stormcov.findStormFiles(os.path.join(basedir, 'stormcov'))
                return stormcov

            def getfiles(basename):
                data = coverage.CoverageData(basename=basename)
                data.read()
                files = set(data.measured_files())
                data.close()
                return files

            # Hits only in an embedded file still register the storm files which never ran
            stormcov = getplugin()
            main = coverage.CoverageData(basename=os.path.join(dirn, 'main'))
            stormcov.saveHits(main, {pypath: {3}}, False)
            main.close()

            self.isin(stormfile, getfiles(os.path.join(dirn, 'main')))
            self.eq(getfiles(os.path.join(dirn, 'main')), {p for v in stormcov.guid_map.values() for p in v})

            stormcov.combineEmbedData()
            self.eq(getfiles(embeddata), stormcov.embed_hosts)

            # Hits only in a storm file still register the embedded files which never ran
            stormcov = getplugin()
            main = coverage.CoverageData(basename=os.path.join(dirn, 'main2'))
            stormcov.saveHits(main, {stormfile: {1}}, False)
            main.close()

            self.eq(getfiles(os.path.join(dirn, 'main2')), {p for v in stormcov.guid_map.values() for p in v})

            stormcov.combineEmbedData()
            self.isin(pypath, getfiles(embeddata))

    async def test_stormcov_sysmon_toolid(self):
        # Use a tool id of our own so the tool is free even when stormcov is already loaded for the test session
        stormcov = s_stormcov.StormcovPlugin(StormcovConfig())
        stormcov.toolid = 3

        self.none(sys.monitoring.get_tool(3))

        stormcov._startSysmon()
        self.eq(sys.monitoring.get_tool(3), 'pytest-stormcov')
        self.true(stormcov._freetool)

        stormcov._stopSysmon()
        self.none(sys.monitoring.get_tool(3))
        self.false(stormcov._freetool)
