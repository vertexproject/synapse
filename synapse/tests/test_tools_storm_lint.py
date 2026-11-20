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
        outp.expect('R005  high      yes      removed-api')
        outp.expect('S010  low       no       guarded-prop-set     ')
        outp.expect('S015  medium    no       return-import')

        outp = self.getTestOutp()
        with self.raises(s_exc.ParserExit) as cm:
            await s_lint.main([], outp=outp)
        self.eq(cm.exception.get('exitcode'), 2)
        outp.expect('at least one path or --manifest is required')

        outp = self.getTestOutp()
        with self.raises(s_exc.ParserExit) as cm:
            await s_lint.main(['-h'], outp=outp)
        self.eq(cm.exception.get('exitcode'), 0)
        outp.expect('--enable')

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

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['bad.storm'], outp=outp), 1)
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
            self.eq(await s_lint.main(['--ignore', 'R001,', 'bad.storm'], outp=outp), 1)
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
                self.eq(await s_lint.main(['-'], outp=outp), 1)
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
            self.eq(await s_lint.main([binf, bad], outp=outp), 2)
            outp.expect('bin.storm: error: ')
            outp.expect('Found 3 errors.')

            # json output is one object per line with no summary
            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', 'bad.storm'], outp=outp), 1)
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
                self.eq(await s_lint.main(['--format', 'json', '-'], outp=outp), 1)
            row = s_json.loads(str(outp))
            self.eq((row['path'], row['line'], row['column'], row['rule']), ('-', 1, 6, 'R001'))

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', 'newp.storm', bad], outp=outp), 2)
            rows = [s_json.loads(line) for line in str(outp).strip().split('\n')]
            self.len(4, rows)
            self.eq(rows[0]['path'], 'newp.storm')
            self.isin('No such file', rows[0]['error'])
            self.eq(rows[1]['path'], bad)
            outp.expect('All checks passed', False)

            outp = self.getTestOutp()
            with self.raises(s_exc.ParserExit) as cm:
                await s_lint.main(['--format', 'xml', 'bad.storm'], outp=outp)
            self.eq(cm.exception.get('exitcode'), 2)

            # directories are walked in sorted order for *.storm
            pkgd = os.path.join(dirn, 'pkg')
            _write(os.path.join(pkgd, 'z.storm'), '$x = $lib.true\n')
            _write(os.path.join(pkgd, 'a', 'b.storm'), '$x = $lib.true\n')
            _write(os.path.join(pkgd, 'a', 'b.yaml'), '$x = $lib.true\n')
            _write(os.path.join(pkgd, 'm.storm'), '$x = $lib.true\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['pkg'], outp=outp), 1)
            lines = str(outp).strip().split('\n')
            self.eq(lines, [
                'pkg/m.storm:1:6: R001 $lib.true was removed, use (true).',
                'pkg/z.storm:1:6: R001 $lib.true was removed, use (true).',
                'pkg/a/b.storm:1:6: R001 $lib.true was removed, use (true).',
                'Found 3 errors.',
            ])

            # manifests of queries embedded in other files
            queries = [
                {'path': '../src/a.ts', 'line': 10, 'text': '$x = $lib.true', 'site': 'src/a.ts:10:20'},
                {'path': '../src/a.ts', 'line': 20, 'text': '$x = (1)\n  $y = $lib.true', 'site': 'src/a.ts:20:4'},
                {'path': '../src/a.ts', 'line': 30, 'text': '$x = $lib.true // noqa', 'site': 'src/a.ts:30:8'},
                {'path': '../vendor/b.ts', 'line': 5, 'text': '$x = $lib.true', 'site': 'vendor/b.ts:5:0'},
                {'path': '../src/c.sh', 'line': 3, 'text': '$x = $lib.true'},
                {'path': '../src/d.py', 'line': 7, 'text': '$x = $lib.true', 'site': 'd.getQuery'},
            ]
            mani = os.path.join('coverage', 'queries.json')
            _write(mani, s_json.dumps({'queries': queries}).decode())

            # a .jsonl manifest has one query per line, and blank lines are skipped
            manl = os.path.join('coverage', 'queries.jsonl')
            _write(manl, '\n'.join(s_json.dumps(q).decode() for q in queries[:3]) + '\n\n  \n' +
                   '\n'.join(s_json.dumps(q).decode() for q in queries[3:]) + '\n')

            clean = os.path.join(dirn, 'clean.json')
            _write(clean, s_json.dumps({'queries': [
                {'path': 'src/a.ts', 'line': 1, 'text': 'inet:fqdn=vertex.link', 'site': 'src/a.ts:1:0'},
            ]}).decode())

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--manifest', clean], outp=outp), 0)
            self.eq(str(outp).strip(), 'All checks passed!')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--manifest', mani, '--manifest', clean, 'bad.storm'], outp=outp), 1)
            lines = str(outp).strip().split('\n')
            self.eq(lines[3:], [
                'src/a.ts:10:27: R001 $lib.true was removed, use (true).',
                'src/a.ts:21:8: R001 $lib.true was removed, use (true).',
                'vendor/b.ts:5:7: R001 $lib.true was removed, use (true).',
                'src/c.sh:3:6: R001 $lib.true was removed, use (true).',
                'src/d.py:7:6: R001 $lib.true was removed, use (true).',
                'Found 8 errors.',
            ])

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--manifest', manl, '--manifest', clean, 'bad.storm'], outp=outp), 1)
            self.eq(str(outp).strip().split('\n'), lines)

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', '--manifest', mani], outp=outp), 1)
            rows = [s_json.loads(line) for line in str(outp).strip().split('\n')]
            self.len(5, rows)
            self.eq(rows[1], {'path': 'src/a.ts', 'line': 21, 'column': 8, 'rule': 'R001', 'severity': 'high',
                              'mesg': '$lib.true was removed, use (true).'})

            # excludes apply to each query's host file
            _write(os.path.join(dirn, 'pyproject.toml'), '[tool.stormlint]\nexclude = ["vendor"]\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--manifest', mani], outp=outp), 1)
            outp.expect('vendor', False)
            outp.expect('Found 4 errors.')

            # unreadable or malformed manifests
            _write(os.path.join(dirn, 'badjson.json'), '{"queries": [')
            _write(os.path.join(dirn, 'noqueries.json'), '{"newp": []}')
            _write(os.path.join(dirn, 'badline.json'),
                   '{"queries": [{"path": "a.ts", "line": "1", "text": "", "site": "a.ts:1:0"}]}')
            _write(os.path.join(dirn, 'badkey.json'),
                   '{"queries": [{"path": "a.ts", "line": 1, "text": "", "newp": "a.ts:1:0"}]}')

            outp = self.getTestOutp()
            argv = ['--manifest', 'newp.json', '--manifest', 'badjson.json', '--manifest', 'noqueries.json',
                    '--manifest', 'badline.json', '--manifest', 'badkey.json', '--manifest', clean]
            self.eq(await s_lint.main(argv, outp=outp), 2)
            outp.expect('newp.json: error: [Errno 2] No such file or directory')
            outp.expect('badjson.json: error: ')
            outp.expect("noqueries.json: error: data must contain ['queries'] properties")
            outp.expect('badline.json: error: data.queries[0].line must be integer')
            outp.expect('badkey.json: error: data.queries[0] must not contain {\'newp\'} properties')
            outp.expect('All checks passed', False)

            # a .jsonl error names its line, after any blank lines and across chunks of lines
            good = s_json.dumps({'path': 'a.ts', 'line': 1, 'text': 'inet:fqdn'}).decode()
            _write(os.path.join(dirn, 'badjson.jsonl'), f'{good}\n\n{{"path": "a.ts"\n')
            _write(os.path.join(dirn, 'badline.jsonl'), f'{good}\n{{"path": "a.ts", "line": 0, "text": ""}}\n')
            _write(os.path.join(dirn, 'badkey.jsonl'), f'{good}\n' * 1200 + '{"path": "a.ts", "line": 1}\n')
            _write(os.path.join(dirn, 'notobj.jsonl'), '[]\n')

            outp = self.getTestOutp()
            argv = ['--manifest', 'newp.jsonl', '--manifest', 'badjson.jsonl', '--manifest', 'badline.jsonl',
                    '--manifest', 'badkey.jsonl', '--manifest', 'notobj.jsonl']
            self.eq(await s_lint.main(argv, outp=outp), 2)
            outp.expect('newp.jsonl: error: [Errno 2] No such file or directory')
            outp.expect('badjson.jsonl: error: line 3: ')
            outp.expect('badline.jsonl: error: line 2: data.line must be bigger than or equal to 1')
            outp.expect("badkey.jsonl: error: line 1201: data must contain ['text'] properties")
            outp.expect('notobj.jsonl: error: line 1: data must be object')

            # findings from chunks before a bad line are still reported
            bad = s_json.dumps({'path': 'a.ts', 'line': 1, 'text': '$x = $lib.true'}).decode()
            _write(os.path.join(dirn, 'stream.jsonl'), f'{bad}\n' + f'{good}\n' * 500 + '{"path": "a.ts"}\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--manifest', 'stream.jsonl'], outp=outp), 2)
            self.eq(str(outp).strip().split('\n'), [
                'a.ts:1:6: R001 $lib.true was removed, use (true).',
                "stream.jsonl: error: line 502: data must contain ['line', 'text'] properties",
                'Found 1 error.',
            ])

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', '--manifest', 'stream.jsonl'], outp=outp), 2)
            rows = [s_json.loads(line) for line in str(outp).strip().split('\n')]
            self.eq([r.get('rule') for r in rows], ['R001', None])
            self.eq(rows[1]['path'], 'stream.jsonl')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--format', 'json', '--manifest', 'newp.json'], outp=outp), 2)
            row = s_json.loads(str(outp))
            self.eq(row['path'], 'newp.json')
            self.isin('No such file', row['error'])

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
ignore = ["P"]
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

            # explicit --config, relative to the config file's directory not the cwd
            other = os.path.join(dirn, 'other', 'pyproject.toml')
            _write(other, '[tool.stormlint]\nselect = ["P"]\nenable = ["S"]\nexclude = ["skip.storm"]\n')
            _write(os.path.join(dirn, 'other', 'skip.storm'), 'spin\n')

            outp = self.getTestOutp()
            argv = ['--config', other, mod, os.path.join(dirn, 'other', 'skip.storm')]
            self.eq(await s_lint.main(argv, outp=outp), 1)
            outp.expect('R001', False)
            outp.expect('mod.storm:1:16: P001 ')
            outp.expect('Found 1 error.')

            # an explicit config without a table uses the defaults
            notab = os.path.join(dirn, 'notab', 'pyproject.toml')
            _write(notab, '[tool.ruff]\nline-length = 120\n')

            outp = self.getTestOutp()
            self.eq(await s_lint.main(['--config', notab, fixt], outp=outp), 1)
            outp.expect('R001')

            # no config found upward from the cwd
            with self.getTestDir(chdir=True) as emptydir:
                _write(os.path.join(emptydir, 'pyproject.toml'), '[project]\nname = "x"\n')
                outp = self.getTestOutp()
                self.eq(await s_lint.main([fixt], outp=outp), 1)
                outp.expect('R001')

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
