import io
import os
import unittest.mock as mock

import synapse.exc as s_exc

import synapse.lib.json as s_json

import synapse.tests.utils as s_t_utils
import synapse.tools.storm.lint as s_lint

def _write(path, text, mode='w'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as fd:
        fd.write(text)

class TestStormLint(s_t_utils.SynTest):

    async def test_tools_storm_lint(self):

        outp = self.getTestOutp()
        self.eq(await s_lint.main(['--show-rules'], outp=outp), 0)
        outp.expect('ID    SEVERITY  DEFAULT  NAME                 DESCRIPTION')
        outp.expect('E001  high      yes      parse-failure')
        outp.expect('P001  low       yes      spin                 The spin command')
        outp.expect('M001  info      v3       renamed-form')
        outp.expect('R004  medium    yes      bare-constant')
        outp.expect('R005  high      v3       removed-api')
        outp.expect('R008  high      v3       dotted-prop')
        outp.expect('S010  low       no       guarded-prop-set     ')
        outp.expect('S015  medium    no       return-import')

        outp = self.getTestOutp()
        self.eq(await s_lint.main([], outp=outp), 2)
        outp.expect('at least one path is required')

        outp = self.getTestOutp()
        self.eq(await s_lint.main(['-h'], outp=outp), 0)
        outp.expect('--enable')
        outp.expect('--v3-ready')

        with self.getTestDir(chdir=True) as dirn:

            good = os.path.join(dirn, 'good.storm')
            _write(good, 'inet:fqdn=vertex.link\n')

            bad = os.path.join(dirn, 'bad.storm')
            _write(bad, 'inet:fqdn=vertex.link\n$x = $lib.true\n$y = $lib.false spin\n')

            empty = os.path.join(dirn, 'empty.storm')
            _write(empty, '')

            blank = os.path.join(dirn, 'blank.storm')
            _write(blank, '  \n\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main([good, empty, blank], outp=outp), 0)
            self.eq(str(outp).strip(), 'All checks passed!')

            # rules which report Storm that must change for 3.x are off by default
            outp = self.getTestOutp()
            self.eq(await s_lint.main(['bad.storm'], outp=outp), 1)
            outp.expect('R001', False)
            outp.expect('bad.storm:3:17: P001 ')
            outp.expect('Found 1 error.')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--enable', 'R001', 'bad.storm'], outp=outp), 1)
            outp.expect('bad.storm:2:6: R001 $lib.true was removed, use (true).')
            outp.expect('bad.storm:3:6: R001 $lib.false was removed')
            outp.expect('bad.storm:3:17: P001 ')
            outp.expect('Found 3 errors.')
            outp.expect('All checks passed', False)

            # duplicate paths are linted once
            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--select', 'P', 'bad.storm', 'bad.storm'], outp=outp), 1)
            outp.expect('R001', False)
            self.eq(1, str(outp).count('P001'))
            outp.expect('Found 1 error.')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--enable', 'R', '--ignore', 'R001,', 'bad.storm'], outp=outp), 1)
            outp.expect('R001', False)
            outp.expect('Found 1 error.')

            outp = self.getTestOutp()
            argv = ['--select', 'E', '--enable', ' P001 ', 'bad.storm']
            self.eq(await s_lint.main(argv, outp=outp), 1)
            outp.expect('R001', False)
            outp.expect('P001')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--select', 'X9', 'bad.storm'], outp=outp), 2)
            outp.expect("error: Unknown lint rule or prefix: 'X9'")

            # stdin
            outp = self.getTestOutp()
            with mock.patch('sys.stdin', io.StringIO('$x = $lib.null\n')):
                self.eq(await s_lint.main(['--enable', 'R001', '-'], outp=outp), 1)
            outp.expect('-:1:6: R001 ')

            outp = self.getTestOutp()
            with mock.patch('sys.stdin', io.StringIO('inet:fqdn |\n')):
                self.eq(await s_lint.main(['-'], outp=outp), 1)
            outp.expect('-:1:')
            outp.expect(' E001 ')

            # rules which are off by default run when selected
            text = 'function f() { $m = $lib.import(foo) return($m) }\n'
            outp = self.getTestOutp()
            with mock.patch('sys.stdin', io.StringIO(text)):
                self.eq(await s_lint.main(['-'], outp=outp), 0)

            outp = self.getTestOutp()
            with mock.patch('sys.stdin', io.StringIO(text)):
                self.eq(await s_lint.main(['--enable', 'S015', '-'], outp=outp), 1)
            outp.expect('-:1:38: S015 ')

            # unreadable files
            outp = self.getTestOutp()
            self.eq(await s_lint.main(['newp.storm', good], outp=outp), 2)
            outp.expect('newp.storm: error: ')
            outp.expect('All checks passed', False)

            binf = os.path.join(dirn, 'bin.storm')
            _write(binf, b'\xff\xfe\xfa', mode='wb')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--enable', 'R001', binf, bad], outp=outp), 2)
            outp.expect('bin.storm: error: ')
            outp.expect('Found 3 errors.')

            # --v3-ready adds the R and M rules, and info findings alone exit 0
            v3 = os.path.join(dirn, 'v3.storm')
            _write(v3, 'inet:ipv4=1.2.3.4\n[ .seen=now ]\ninet:ipv6\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--v3-ready', 'v3.storm'], outp=outp), 0)
            self.eq(str(outp).strip().split('\n'), [
                'v3.storm:1:1: M001 (info) inet:ipv4 is renamed to inet:ip in 3.x.',
                'v3.storm:2:3: M004 (info) The universal .seen prop is replaced by :seen in 3.x, '
                'on forms which implement meta:observable.',
                'v3.storm:3:1: M001 (info) inet:ipv6 is renamed to inet:ip in 3.x.',
                'Found 0 errors and 3 info findings.',
            ])

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--v3-ready', '--select', 'E', '--ignore', 'M004,M001', 'v3.storm'], outp=outp), 0)
            self.eq(str(outp).strip(), 'All checks passed!')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--v3-ready', '--ignore', 'M00', 'v3.storm', 'bad.storm'], outp=outp), 1)
            outp.expect('bad.storm:2:6: R001 $lib.true was removed, use (true).')
            outp.expect('(info)', False)
            outp.expect('Found 3 errors.')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--v3-ready', '--ignore', 'M004', 'v3.storm', 'bad.storm'], outp=outp), 1)
            outp.expect('Found 3 errors and 2 info findings.')

            outp = self.getTestOutp()
            with mock.patch('sys.stdin', io.StringIO('inet:ipv4 spin\n')):
                self.eq(await s_lint.main(['--v3-ready', '-'], outp=outp), 1)
            outp.expect('-:1:1: M001 (info) inet:ipv4 is renamed to inet:ip in 3.x.')
            outp.expect('-:1:11: P001 Avoid spin')
            outp.expect('Found 1 error and 1 info finding.')

            outp = self.getTestOutp()
            with mock.patch('sys.stdin', io.StringIO('$x = ($y .z)\n')):
                self.eq(await s_lint.main(['--v3-ready', '--select', 'R', '-'], outp=outp), 1)
            outp.expect('-:1:10: R006 Remove the whitespace before the . in a variable deref.')
            outp.expect('Found 1 error.')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', '--v3-ready', '--ignore', 'M004', 'v3.storm'], outp=outp), 0)
            rows = [s_json.loads(line) for line in str(outp).strip().split('\n')]
            self.eq(rows[0], {'path': 'v3.storm', 'line': 1, 'column': 1, 'rule': 'M001', 'severity': 'info',
                              'mesg': 'inet:ipv4 is renamed to inet:ip in 3.x.'})
            self.len(2, rows)

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--v3-ready', '--ignore', 'M004', 'newp.storm', v3], outp=outp), 2)
            outp.expect('newp.storm: error: ')
            outp.expect('Found 0 errors and 2 info findings.')

            # json output is one object per line with no summary
            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', '--enable', 'R001', 'bad.storm'], outp=outp), 1)
            rows = [s_json.loads(line) for line in str(outp).strip().split('\n')]
            self.len(3, rows)
            self.eq(rows[0], {'path': 'bad.storm', 'line': 2, 'column': 6, 'rule': 'R001', 'severity': 'high',
                              'mesg': '$lib.true was removed, use (true).'})
            self.eq(list(rows[2].keys()), ['path', 'line', 'column', 'rule', 'severity', 'mesg'])
            self.eq(rows[2]['rule'], 'P001')
            outp.expect('Found', False)

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', good, empty], outp=outp), 0)
            self.eq(str(outp), '')

            outp = self.getTestOutp()
            with mock.patch('sys.stdin', io.StringIO('$x = $lib.null\n')):
                self.eq(await s_lint.main(['--format', 'json', '--enable', 'R001', '-'], outp=outp), 1)
            row = s_json.loads(str(outp))
            self.eq((row['path'], row['line'], row['column'], row['rule']), ('-', 1, 6, 'R001'))

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', '--enable', 'R001', 'newp.storm', bad], outp=outp), 2)
            rows = [s_json.loads(line) for line in str(outp).strip().split('\n')]
            self.len(4, rows)
            self.eq(rows[0]['path'], 'newp.storm')
            self.isin('No such file', rows[0]['error'])
            self.eq(rows[1]['path'], bad)
            outp.expect('All checks passed', False)

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'xml', 'bad.storm'], outp=outp), 2)
            outp.expect("invalid choice: 'xml'")

            # directories are walked in sorted order for *.storm
            pkgd = os.path.join(dirn, 'pkg')
            _write(os.path.join(pkgd, 'z.storm'), '$x = $lib.true\n')
            _write(os.path.join(pkgd, 'a', 'b.storm'), '$x = $lib.true\n')
            _write(os.path.join(pkgd, 'a', 'b.yaml'), '$x = $lib.true\n')
            _write(os.path.join(pkgd, 'm.storm'), '$x = $lib.true\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--enable', 'R001', 'pkg'], outp=outp), 1)
            lines = str(outp).strip().split('\n')
            self.eq(lines, [
                'pkg/m.storm:1:6: R001 $lib.true was removed, use (true).',
                'pkg/z.storm:1:6: R001 $lib.true was removed, use (true).',
                'pkg/a/b.storm:1:6: R001 $lib.true was removed, use (true).',
                'Found 3 errors.',
            ])

    async def test_tools_storm_lint_config(self):

        with self.getTestDir() as dirn:

            ccdir = os.path.join(dirn, 'tmpl', '{{cookiecutter.package_name}}', 'storm')
            ccfile = os.path.join(ccdir, 'mod.storm')
            _write(ccfile, '$x = $lib.true\n')

            fixt = os.path.join(dirn, 'tests', 'files', 'bad.storm')
            _write(fixt, '$x = $lib.true\n')

            vend = os.path.join(dirn, 'vendor', 'deep', 'x.storm')
            _write(vend, '$x = $lib.true\n')

            mod = os.path.join(dirn, 'src', 'mod.storm')
            _write(mod, '$x = $lib.true spin\n')

            conf = os.path.join(dirn, 'pyproject.toml')
            _write(conf, '''
[tool.ruff]
line-length = 120

[tool.stormlint]
enable = ["R"]
ignore = ["P"]
v3_ready = true
exclude = [
    "tmpl/{{cookiecutter.package_name}}/*",
    "tests/files/bad.storm",
    "vendor",
]
''')

            # discovered upward from the cwd
            curd = os.getcwd()
            os.chdir(os.path.join(dirn, 'src'))
            try:
                outp = self.getTestOutp()
                self.eq(await s_lint.main(['mod.storm', ccfile, fixt, vend], outp=outp), 1)
                outp.expect('mod.storm:1:6: R001 ')
                outp.expect('P001', False)
                outp.expect('cookiecutter', False)
                outp.expect('tests/files', False)
                outp.expect('vendor', False)
                outp.expect('Found 1 error.')

                # excludes apply to directory walks and prune excluded directories
                outp = self.getTestOutp()
                self.eq(await s_lint.main([dirn], outp=outp), 1)
                outp.expect('cookiecutter', False)
                outp.expect('vendor', False)
                outp.expect('Found 1 error.')

                # an excluded directory named explicitly
                outp = self.getTestOutp()
                self.eq(await s_lint.main([os.path.join(dirn, 'vendor')], outp=outp), 0)
                outp.expect('All checks passed!')

                # CLI flags replace the config keys
                outp = self.getTestOutp()
                self.eq(await s_lint.main(['--ignore', 'R', 'mod.storm'], outp=outp), 1)
                outp.expect('R001', False)
                outp.expect('P001')

            finally:
                os.chdir(curd)

            # v3_ready in the config, which the CLI flag replaces
            m3 = os.path.join(dirn, 'src', 'm3.storm')
            _write(m3, 'inet:ipv4\n')

            os.chdir(os.path.join(dirn, 'src'))
            try:
                outp = self.getTestOutp()
                self.eq(await s_lint.main(['m3.storm'], outp=outp), 0)
                outp.expect('m3.storm:1:1: M001 (info) ')
                outp.expect('Found 0 errors and 1 info finding.')

                outp = self.getTestOutp()
                self.eq(await s_lint.main(['--no-v3-ready', 'm3.storm'], outp=outp), 0)
                outp.expect('All checks passed!')

            finally:
                os.chdir(curd)

            # explicit --config, relative to the config file's directory not the cwd
            other = os.path.join(dirn, 'other', 'pyproject.toml')
            _write(other, '[tool.stormlint]\nselect = ["P"]\nenable = ["S"]\nexclude = ["skip.storm"]\n')
            _write(os.path.join(dirn, 'other', 'skip.storm'), 'spin\n')

            outp = self.getTestOutp()
            argv = ['--config', other, mod, os.path.join(dirn, 'other', 'skip.storm')]
            self.eq(await s_lint.main(argv, outp=outp), 1)
            outp.expect('R001', False)

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--v3-ready'] + argv, outp=outp), 1)
            outp.expect('mod.storm:1:6: R001 ')
            outp.expect('mod.storm:1:16: P001 ')
            outp.expect('Found 2 errors.')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(argv, outp=outp), 1)
            outp.expect('mod.storm:1:16: P001 ')
            outp.expect('Found 1 error.')

            # an explicit config without a table uses the defaults
            notab = os.path.join(dirn, 'notab', 'pyproject.toml')
            _write(notab, '[tool.ruff]\nline-length = 120\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--config', notab, mod], outp=outp), 1)
            outp.expect('R001', False)
            outp.expect('mod.storm:1:16: P001 ')

            # an explicit config without a [tool] table uses the defaults
            notool = os.path.join(dirn, 'notool', 'pyproject.toml')
            _write(notool, '[project]\nname = "x"\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--config', notool, mod], outp=outp), 1)
            outp.expect('R001', False)
            outp.expect('mod.storm:1:16: P001 ')

            # no config found upward from the cwd
            with self.getTestDir(chdir=True) as emptydir:
                _write(os.path.join(emptydir, 'pyproject.toml'), '[project]\nname = "x"\n')
                outp = self.getTestOutp()
                self.eq(await s_lint.main([mod], outp=outp), 1)
                outp.expect('R001', False)
                outp.expect('mod.storm:1:16: P001 ')

            # a discovered config without a [tool.stormlint] table is skipped
            with self.getTestDir(chdir=True) as ruffdir:
                _write(os.path.join(ruffdir, 'pyproject.toml'), '[tool.ruff]\nline-length = 120\n')
                outp = self.getTestOutp()
                self.eq(await s_lint.main([mod], outp=outp), 1)
                outp.expect('R001', False)
                outp.expect('mod.storm:1:16: P001 ')

            # config errors
            async def confErr(text, mesg):
                path = os.path.join(dirn, 'errs', 'pyproject.toml')
                _write(path, text)
                outp = self.getTestOutp()
                self.eq(await s_lint.main(['--config', path, mod], outp=outp), 2)
                outp.expect(mesg)

            await confErr('[tool.stormlint\n', 'pyproject.toml: ')
            await confErr('[tool]\nstormlint = 1\n', '[tool.stormlint] data must be object')
            await confErr('[tool.stormlint]\nnewp = []\n', "[tool.stormlint] data must not contain {'newp'} properties")
            await confErr('[tool.stormlint]\nselect = "E"\n', '[tool.stormlint] data.select must be array')
            await confErr('[tool.stormlint]\nignore = [1]\n', '[tool.stormlint] data.ignore[0] must be string')
            await confErr('[tool.stormlint]\nv3_ready = "yes"\n', '[tool.stormlint] data.v3_ready must be boolean')
            await confErr('[tool.stormlint]\nselect = ["X9"]\n', "Unknown lint rule or prefix: 'X9'")

            with self.raises(s_exc.BadConfValu) as cm:
                s_lint._checkConf('pyproject.toml', 1)
            self.eq(cm.exception.get('mesg'), 'pyproject.toml: [tool.stormlint] data must be object')

            outp = self.getTestOutp()
            newp = os.path.join(dirn, 'newp', 'pyproject.toml')
            self.eq(await s_lint.main(['--config', newp, mod], outp=outp), 2)
            outp.expect('error: ')

            # a malformed discovered config is an error too
            with self.getTestDir(chdir=True) as baddir:
                _write(os.path.join(baddir, 'pyproject.toml'), '[tool.stormlint\n')
                outp = self.getTestOutp()
                self.eq(await s_lint.main([mod], outp=outp), 2)
                outp.expect('error: ')
