import shutil
import argparse

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.lib.output as s_output
import synapse.lib.mdstorm as s_mdstorm

import synapse.tools.storm._cli as s_storm

import synapse.tests.utils as s_test

class NonCellMockCell:
    def __init__(self, dirn, conf):
        self.dirn = dirn
        self.conf = conf

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

class NonCellMockCtor:
    '''
    A minimal getDocsCell() ctor that is not a real Cell (e.g. a doc-only
    test double with a custom anit()) and so has no initCellConf() to build
    a Config from.
    '''
    @classmethod
    async def anit(cls, dirn, conf=None):
        return NonCellMockCell(dirn, conf)

class BoomCortexCtor:
    '''
    A getDocsCluster() ctor whose anit() always raises, simulating a Cortex boot
    failure after axon / jsonstor have already booted.
    '''
    @classmethod
    def getCellType(cls):
        return 'cortex'

    @classmethod
    async def anit(cls, dirn, conf=None):
        raise s_exc.SynErr(mesg='boom')

class BoomPeerCtor:
    '''An addSvc() ctor whose anit() always raises, simulating a peer boot failure.'''
    @classmethod
    def getCellType(cls):
        return 'boompeer'

    @classmethod
    async def anit(cls, dirn, conf=None):
        raise s_exc.SynErr(mesg='peerboom')

class ReadPoolCortex(s_cortex.Cortex):
    '''A Cortex subclass declaring a readpool:size confdef, for the getDocsCluster() readpool-default test.'''
    confbase = dict(s_cortex.Cortex.confbase)
    confbase['readpool:size'] = {'type': ['integer', 'null'], 'default': None}

md_in = '''
# HI

Some regular markdown text that is not a directive.

```python
print('not a directive, left alone')
```

```mdstorm-setup
```

```mdstorm
$lib.print(hello)
```
'''

md_out_query_line = 'storm> $lib.print(hello)'

class MdStormTest(s_test.SynTest):

    async def test_mdstorm_passthrough_and_fence(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'test.md')
            with open(path, 'w') as fd:
                fd.write(md_in)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('# HI', text)
            self.isin('Some regular markdown text that is not a directive.', text)
            self.isin(md_out_query_line, text)
            self.notin('```mdstorm-setup', text)
            self.notin('```mdstorm\n', text)

            # a non-directive fence (e.g. a ```python example) is left alone
            self.isin('```python', text)
            self.isin("print('not a directive, left alone')", text)

    async def test_mdstorm_handlers_are_parser_callback_tuples(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'test.md')
            with open(path, 'w') as fd:
                fd.write(md_in)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                self.eq(set(mdstorm.handlers.keys()),
                       {'mdstorm', 'mdshell', 'mdstorm-setup', 'mdinclude', 'mdautodoc'})
                for parser, callback in mdstorm.handlers.values():
                    self.true(isinstance(parser, argparse.ArgumentParser))
                    self.true(callable(callback))

    async def test_mdstorm_requires_existing_file(self):
        with self.raises(s_exc.BadConfValu):
            await s_mdstorm.MdStorm.anit('/tmp/does-not-exist-mdstorm.md')

    async def test_mdstorm_unknown_directive(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'test.md')
            with open(path, 'w') as fd:
                fd.write('```mdstorm-nope\nfoo\n```\n')

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchName):
                    await mdstorm.run()

    async def test_mdstorm_storm_vars_flag(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--vars {"targ": "vertex.link"}',
            '--',
            '$lib.print($targ)',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'vars.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            self.isin('vertex.link', ''.join(lines))

    async def test_mdstorm_storm_vars_flag_on_fence_line(self):
        # Flags may also be given on the opening fence line instead of the
        # body -- no "--" terminator needed there since the fence line is
        # already unambiguously separate from the body.
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm --vars {"targ": "vertex.link"}',
            '$lib.print($targ)',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'varsfence.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            self.isin('vertex.link', ''.join(lines))

    async def test_mdstorm_storm_fence_has_no_blank_line_or_indent(self):
        # the rendered ```stormdoc fence must open directly onto the echoed query
        # line (no blank line inserted at the top) and its content must not
        # be indented -- the fence itself already delimits the code, so a
        # synthetic 4-space indent (a holdover from the pre-fence RST era) is
        # wrong here.
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '[ inet:fqdn=vertex.link ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'noindent.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('```stormdoc\nstorm> [ inet:fqdn=vertex.link ]\n', text)
            self.isin('\ninet:fqdn=vertex.link\n', text)
            self.notin('    storm>', text)
            self.notin('```stormdoc\n\n', text)

    async def test_mdstorm_storm_flags_on_fence_line_and_body(self):
        # Fence-line and body flags combine -- one flag on the fence line,
        # another (terminated by "--") in the body.
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm --hide-query',
            '--vars {"targ": "vertex.link"}',
            '--',
            '$lib.print($targ)',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'varsboth.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('vertex.link', text)
            self.notin('storm>', text)

    async def test_mdstorm_storm_body_flags_need_not_be_one_per_line(self):
        # Body flags may be spread across multiple lines however the author
        # likes (here two flags share one line and a third sits on its own)
        # -- only the terminator itself must be alone on its line.
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--hide-query --hide-tags',
            '--vars {"targ": "vertex.link"}',
            '--',
            '$lib.print($targ)',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'multilineflags.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('vertex.link', text)
            self.notin('storm>', text)

    async def test_mdstorm_storm_opts_flag(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--opts {"vars": {"targ": "vertex.link"}}',
            '--',
            '$lib.print($targ)',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'opts.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            self.isin('vertex.link', ''.join(lines))

    async def test_mdstorm_storm_hide_and_fail_flag(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--hide --fail',
            '--',
            '$lib.raise(FooBar, "boom")',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'hidefail2.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.notin('storm>', text)
            self.notin('boom', text)

    async def test_mdstorm_storm_vars_and_opts_mutually_exclusive(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--vars {"a": 1} --opts {"vars": {"a": 1}}',
            '--',
            '$lib.print($a)',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'varsopts.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.BadArg):
                    await mdstorm.run()

    async def test_mdstorm_storm_fail_flag(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--fail',
            '--',
            '$lib.raise(FooBar, "boom")',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'fail.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()
            self.isin('boom', ''.join(lines))

    async def test_mdstorm_storm_fail_flag_but_none_occurred(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--fail',
            '--',
            '$lib.print(fine)',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'fail2.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.StormRuntimeError):
                    await mdstorm.run()

    async def test_mdstorm_storm_hide_output_flag(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--hide-output',
            '--',
            '[ inet:fqdn=vertex.link ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'hideoutput.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

                text = ''.join(lines)
                self.isin('storm> [ inet:fqdn=vertex.link ]', text)
                self.notin('inet:fqdn=vertex.link\n\n', text)

                # confirm the query actually executed (a real side effect), not
                # just that it was syntactically accepted -- --hide-output suppresses
                # *display*, it does not skip execution.
                nodes = await mdstorm.core.nodes('inet:fqdn=vertex.link')
                self.len(1, nodes)

    async def test_mdstorm_storm_hide_output_flag_still_raises_on_bad_query(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--hide-output',
            '--',
            '$lib.raise(FooBar, "boom")',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'hideoutputfail.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.StormRuntimeError):
                    await mdstorm.run()

    async def test_mdstorm_storm_hide_flag_prints_nothing(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--hide',
            '--',
            '[ inet:fqdn=vertex.link ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'hide.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

                text = ''.join(lines)
                self.notin('storm>', text)
                self.notin('inet:fqdn=vertex.link', text)

                # confirm the query actually executed despite printing nothing
                nodes = await mdstorm.core.nodes('inet:fqdn=vertex.link')
                self.len(1, nodes)

    async def test_mdstorm_storm_hide_flag_still_raises_on_bad_query(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--hide',
            '--',
            '$lib.raise(FooBar, "boom")',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'hidefail.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.StormRuntimeError):
                    await mdstorm.run()

    async def test_mdstorm_storm_hide_flags(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '--hide-query --hide-tags --hide-props',
            '--',
            '[ inet:fqdn=vertex.link ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'hide.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.notin('storm>', text)
            self.isin('inet:fqdn=vertex.link', text)

    async def test_mdstorm_storm_no_cortex_set(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'nocortex.md')
            with open(path, 'w') as fd:
                fd.write('```mdstorm\n$lib.print(hi)\n```\n')

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchVar):
                    await mdstorm.run()

    async def test_mdstorm_merge_view_opts_noop_when_no_fork(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'noop.md')
            with open(path, 'w') as fd:
                fd.write('# nothing\n')

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                self.eq({}, mdstorm._mergeViewOpts({}))
                mdstorm._forkediden = 'someiden'
                self.eq({'view': 'someiden'}, mdstorm._mergeViewOpts({}))

    async def test_mdstorm_shell_directive(self):
        md = '\n'.join((
            '```mdshell',
            'echo hello',
            '```',
            '',
            '```mdshell',
            '--hide-query',
            '--',
            'echo ok',
            '```',
            '',
            '```mdshell',
            '--fail-ok',
            '--',
            'false',
            '```',
            '',
            '```mdshell',
            '--include-stderr',
            '--',
            'echo stdoutline',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'shell.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('echo hello', text)
            self.isin('hello', text)
            self.isin('ok', text)
            self.notin('echo ok', text)
            self.isin('stdoutline', text)

    async def test_mdstorm_shell_directive_flags_on_fence_line(self):
        md = '\n'.join((
            '```mdshell --hide-query',
            'echo ok',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'shellfence.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('ok', text)
            self.notin('echo ok', text)

    async def test_mdstorm_shell_directive_fails_on_error(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'shellfail.md')
            with open(path, 'w') as fd:
                fd.write('```mdshell\nfalse\n```\n')

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.SynErr):
                    await mdstorm.run()

    async def test_mdstorm_old_shell_directive_name_unrecognized(self):
        # "mdstorm-shell" was renamed to "mdshell" -- the old name still
        # looks like an attempted mdstorm-* directive (matches the naming
        # regex) so it raises NoSuchName rather than silently passing
        # through as an ordinary code block.
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'oldshellname.md')
            with open(path, 'w') as fd:
                fd.write('```mdstorm-shell\necho hi\n```\n')

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchName):
                    await mdstorm.run()

    async def test_mdstorm_unterminated_fence(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'unterminated.md')
            with open(path, 'w') as fd:
                fd.write('```mdstorm\n$lib.print(hi)\n')

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.BadSyntax):
                    await mdstorm.run()

    async def test_mdstorm_only_one_setup_per_document(self):
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm-setup',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'twosetup.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.BadArg):
                    await mdstorm.run()

md_in_full = '''
# HI

```mdstorm-setup
--load-pkg synapse/tests/files/stormpkg/testpkg.yaml --load-svc 'synapse.tests.files.mdstorm.testsvc.Testsvc testsvc {"secret": "jupiter"}'
```

```mdstorm
--hide --vars {"foo": 10, "bar": "baz"}
--
[ inet:asn=$foo ]
```

```mdstorm
--vars {"foo": 10, "bar": "baz"}
--
$lib.print($bar) $lib.warn(omgomgomg)
```

```mdstorm
--hide
--
[ inet:ip='::ffff:0.0.0.0' ]
```

```mdstorm
--hide-props
--
testpkgcmd foo
```

```mdstorm
testsvc.test
```
'''

class MdStormFullTest(s_test.SynTest):

    async def test_mdstorm_full_directive_set(self):
        testpkg_yaml = self.getTestFilePath('stormpkg', 'testpkg.yaml')
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'full.md')
            with open(path, 'w') as fd:
                fd.write(md_in_full.replace('synapse/tests/files/stormpkg/testpkg.yaml', testpkg_yaml))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('storm> $lib.print($bar) $lib.warn(omgomgomg)', text)
            self.isin('baz', text)
            self.isin('WARNING: omgomgomg', text)
            self.isin('storm> testpkgcmd foo', text)
            self.isin('inet:ip=::ffff:0.0.0.0', text)
            self.isin('storm> testsvc.test', text)
            self.isin('jupiter', text)
            self.isin('testsvc-done', text)

    async def test_mdstorm_storm_cortex_pkg_and_svc_flags_independently(self):
        testpkg_yaml = self.getTestFilePath('stormpkg', 'testpkg.yaml')
        # --pkg alone
        md_pkg = '\n'.join((
            '```mdstorm-setup',
            f'--load-pkg {testpkg_yaml}',
            '```',
            '',
            '```mdstorm',
            '--hide',
            '--',
            "[ inet:ip='::ffff:0.0.0.0' ]",
            '```',
            '',
            '```mdstorm',
            '--hide-props',
            '--',
            'testpkgcmd foo',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'pkgonly.md')
            with open(path, 'w') as fd:
                fd.write(md_pkg)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()
            self.isin('inet:ip=::ffff:0.0.0.0', ''.join(lines))

        # --svc alone
        md_svc = '\n'.join((
            '```mdstorm-setup',
            "--load-svc 'synapse.tests.files.mdstorm.testsvc.Testsvc testsvc {\"secret\": \"jupiter\"}'",
            '```',
            '',
            '```mdstorm',
            'testsvc.test',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'svconly.md')
            with open(path, 'w') as fd:
                fd.write(md_svc)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()
            self.isin('jupiter', ''.join(lines))

    async def test_mdstorm_pkg_and_svc_idempotent_on_already_loaded(self):
        testpkg_yaml = self.getTestFilePath('stormpkg', 'testpkg.yaml')
        # Same --pkg path twice: Cortex.addStormPkg is already idempotent
        # (a byte-identical re-add is a no-op), so no code change was needed
        # for --pkg -- this test simply locks that behavior in.
        md_pkg = '\n'.join((
            '```mdstorm-setup',
            f'--load-pkg {testpkg_yaml} --load-pkg {testpkg_yaml}',
            '```',
            '',
            '```mdstorm',
            '--hide',
            '--',
            "[ inet:ip='::ffff:0.0.0.0' ]",
            '```',
            '',
            '```mdstorm',
            '--hide-props',
            '--',
            'testpkgcmd foo',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'pkgtwice.md')
            with open(path, 'w') as fd:
                fd.write(md_pkg)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()
            self.isin('inet:ip=::ffff:0.0.0.0', ''.join(lines))

        # Same --svc name twice: _startStormSvc must skip re-registration
        # rather than starting a second temp service cell under the same name.
        md_svc = '\n'.join((
            '```mdstorm-setup',
            "--load-svc 'synapse.tests.files.mdstorm.testsvc.Testsvc testsvc {\"secret\": \"jupiter\"}' "
            "--load-svc 'synapse.tests.files.mdstorm.testsvc.Testsvc testsvc {\"secret\": \"jupiter\"}'",
            '```',
            '',
            '```mdstorm',
            'testsvc.test',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'svctwice.md')
            with open(path, 'w') as fd:
                fd.write(md_svc)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()
            self.isin('jupiter', ''.join(lines))

    async def test_mdstorm_load_svc_aha_join(self):
        # a --load-svc ctor whose registration name matches its own
        # getCellType() ( AhaTestsvc's celltype == 'ahatestsvc', the svcname
        # used below ) is booted onto the default doc Cortex's own AHA
        # network rather than standalone -- required since AhaTestsvc calls
        # _reqAhaServers() in initServiceRuntime() and would otherwise fail
        # to boot at all.
        md_svc = '\n'.join((
            '```mdstorm-setup',
            "--load-svc 'synapse.tests.files.mdstorm.testsvc.AhaTestsvc ahatestsvc'",
            '```',
            '',
            '```mdstorm',
            'ahatestsvc.test',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'svcahajoin.md')
            with open(path, 'w') as fd:
                fd.write(md_svc)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()
            self.isin('ahatestsvc-ok', ''.join(lines))

    async def test_mdstorm_load_svc_name_mismatch(self):
        # a --load-svc registration name that does NOT match the ctor's own
        # getCellType() is rejected up front. A service is registered under, and
        # addressed by, its cell type, and the Cortex refuses a link reporting any
        # other type -- so booting it would leave $lib.service.wait() blocking on a
        # service which can never become ready.
        md_svc = '\n'.join((
            '```mdstorm-setup',
            "--load-svc 'synapse.tests.files.mdstorm.testsvc.AhaTestsvc notthecelltype'",
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'svcahamismatch.md')
            with open(path, 'w') as fd:
                fd.write(md_svc)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.BadArg) as ectx:
                    await mdstorm.run()
                self.isin('must be loaded under its cell type ahatestsvc, not notthecelltype',
                          ectx.exception.errinfo['mesg'])

    async def test_mdstorm_setup_cortex_subclass(self):
        # a --cortex naming a real Cortex subclass ( rather than the default )
        # boots via getDocsCluster(ctor=loc), same as the default Cortex, so it
        # still has its axon / jsonstor peers resolved via AHA.
        md_svc = '\n'.join((
            '```mdstorm-setup',
            '--cortex synapse.cortex.Cortex',
            '```',
            '',
            '```mdstorm',
            '--',
            '[ inet:asn=1 ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'cortexsubclass.md')
            with open(path, 'w') as fd:
                fd.write(md_svc)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()
            self.isin('inet:asn=1', ''.join(lines))

    async def test_mdstorm_setup_cortex_noncell_ctor(self):
        # a --cortex naming a ctor that is not a real Cell/Cortex ( eg a
        # doc-only test double with its own self-contained anit() ) must not
        # be wrapped in a second, redundant AHA network -- it boots via the
        # plain getCell() path instead of getDocsCluster().
        md_svc = '\n'.join((
            '```mdstorm-setup',
            '--cortex synapse.tests.test_lib_mdstorm.NonCellMockCtor',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'cortexnoncell.md')
            with open(path, 'w') as fd:
                fd.write(md_svc)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                await mdstorm.run()
                self.none(mdstorm.clus)

    async def test_mdstorm_setup_cortex_unresolvable(self):
        # a --cortex naming a ctor that cannot be resolved at all is rejected
        # outright, rather than falling through to either boot path.
        md_svc = '\n'.join((
            '```mdstorm-setup',
            '--cortex synapse.tests.test_lib_mdstorm.NotARealCtor',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'cortexunresolvable.md')
            with open(path, 'w') as fd:
                fd.write(md_svc)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchCtor):
                    await mdstorm.run()

    async def test_mdstorm_folded_or_dropped_directives_unrecognized(self):
        # mdstorm-expect, mdstorm-multiline: dropped outright, matching rstorm's
        # storm-expect/storm-multiline ("Key findings" #1-#2). mdstorm-opts,
        # mdstorm-pkg, mdstorm-svc, mdstorm-fail, mdstorm-pre: folded into
        # --vars/--opts/--fail/--hide flags on mdstorm (--pkg/--svc live on as
        # --load-pkg/--load-svc under mdstorm-setup) rather than remaining
        # standalone directives, matching rstorm's storm-opts/storm-pkg/storm-svc/
        # storm-fail/storm-pre ("Key findings" #8, #10, #14).
        dropped = ('mdstorm-expect', 'mdstorm-multiline', 'mdstorm-opts', 'mdstorm-pkg',
                   'mdstorm-svc', 'mdstorm-fail', 'mdstorm-pre')

        with self.getTestDir() as dirn:
            for i, directive in enumerate(dropped):
                path = s_common.genpath(dirn, f'dropped{i}.md')
                with open(path, 'w') as fd:
                    fd.write(f'```{directive}\nfoo\n```\n')

                async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                    with self.raises(s_exc.NoSuchName):
                        await mdstorm.run()

    async def test_mdstorm_hide_flag_merges_stormvars(self):
        # This test exercises the one behavior unique to --hide (Task 1) that
        # could not be tested until mdstorm-setup's --envvar existed --
        # merging self.stormvars into the call.
        md = '\n'.join((
            '```mdstorm-setup',
            '--envvar MDSTORM_TEST_TARG=vertex.link',
            '```',
            '',
            '```mdstorm',
            '--hide',
            '--',
            '[ inet:fqdn=$MDSTORM_TEST_TARG ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'hidemerge.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

                self.eq('', ''.join(lines).strip())

                nodes = await mdstorm.core.nodes('inet:fqdn=vertex.link')
                self.len(1, nodes)

    async def test_mdstorm_mock_http_flag(self):
        cassette = self.getTestFilePath('mdstorm', 'httprespmulti.yaml')
        md = '\n'.join((
            '```mdstorm-setup',
            '--vcr-opts \'{"record_mode": "none"}\'',
            '```',
            '',
            '```mdstorm',
            '$resp=$lib.inet.http.get("http://example.com") '
            '[ it:dev:str=$resp.body.decode() ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'mockhttp.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path, mockhttp=cassette) as mdstorm:
                lines = await mdstorm.run()

                text = ''.join(lines)
                self.isin('<ANSI STANDARD PIZZA>', text)

                nodes = await mdstorm.core.nodes('it:dev:str')
                self.len(1, nodes)
                self.eq('<ANSI STANDARD PIZZA>', nodes[0].ndef[1])

    async def test_mdstorm_mock_http_relative_path(self):
        cassette = self.getTestFilePath('mdstorm', 'httprespmulti.yaml')
        md = '\n'.join((
            '```mdstorm-setup',
            '```',
            '',
            '```mdstorm',
            '$resp=$lib.inet.http.get("http://example.com") '
            '[ it:dev:str=$resp.body.decode() ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            shutil.copy(cassette, s_common.genpath(dirn, 'cassette.yaml'))

            path = s_common.genpath(dirn, 'mockhttp.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path, mockhttp='cassette.yaml') as mdstorm:
                self.eq(s_common.genpath(dirn, 'cassette.yaml'), mdstorm.mockhttp)
                lines = await mdstorm.run()

            self.isin('<ANSI STANDARD PIZZA>', ''.join(lines))

    async def test_mdstorm_mock_http_not_set(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'nomock.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdstorm-setup',
                    '```',
                    '',
                    '```mdstorm',
                    '$lib.print(hi)',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                self.none(mdstorm.mockhttp)
                lines = await mdstorm.run()
            self.isin('hi', ''.join(lines))

    async def test_mdstorm_mock_http_per_fence_flag(self):
        # a per-fence --mock-http is used when no document-wide cassette was given
        cassette = self.getTestFilePath('mdstorm', 'httprespmulti.yaml')
        md = '\n'.join((
            '```mdstorm-setup',
            '--vcr-opts \'{"record_mode": "none"}\'',
            '```',
            '',
            f'```mdstorm --mock-http {cassette}',
            '$resp=$lib.inet.http.get("http://example.com") '
            '[ it:dev:str=$resp.body.decode() ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'mockhttpfence.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                self.none(mdstorm.mockhttp)
                lines = await mdstorm.run()

                text = ''.join(lines)
                self.isin('<ANSI STANDARD PIZZA>', text)

                nodes = await mdstorm.core.nodes('it:dev:str')
                self.len(1, nodes)
                self.eq('<ANSI STANDARD PIZZA>', nodes[0].ndef[1])

    async def test_mdstorm_mock_http_per_fence_relative_path(self):
        # a per-fence --mock-http resolves relative to the md file's directory
        cassette = self.getTestFilePath('mdstorm', 'httprespmulti.yaml')
        with self.getTestDir() as dirn:
            shutil.copy(cassette, s_common.genpath(dirn, 'fence-cassette.yaml'))

            md = '\n'.join((
                '```mdstorm-setup',
                '--vcr-opts \'{"record_mode": "none"}\'',
                '```',
                '',
                '```mdstorm --mock-http fence-cassette.yaml',
                '$resp=$lib.inet.http.get("http://example.com") '
                '[ it:dev:str=$resp.body.decode() ]',
                '```',
                '',
            ))
            path = s_common.genpath(dirn, 'mockhttpfencerel.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            self.isin('<ANSI STANDARD PIZZA>', ''.join(lines))

    async def test_mdstorm_mock_http_resolves_via_srcbasedir(self):
        # mddocs.buildDocs' stageTree never copies a bundle's mocks/
        # directory into the staged outdir -- a relative --mock-http
        # cassette must therefore resolve against the file's ORIGINAL
        # location (srcbasedir), not wherever it was staged to, the same
        # way mdautodoc's --stormpkg already does.
        cassette = self.getTestFilePath('mdstorm', 'httprespmulti.yaml')
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            outdir = s_common.genpath(workdir, 'built')
            s_common.gendir(srcdir, 'mocks')
            s_common.gendir(outdir)
            shutil.copy(cassette, s_common.genpath(srcdir, 'mocks', 'cassette.yaml'))

            md = '\n'.join((
                '```mdstorm-setup',
                '--vcr-opts \'{"record_mode": "none"}\'',
                '```',
                '',
                '```mdstorm --mock-http mocks/cassette.yaml',
                '$resp=$lib.inet.http.get("http://example.com") '
                '[ it:dev:str=$resp.body.decode() ]',
                '```',
                '',
            ))
            # the staged copy: same relpath-to-outdir structure as srcdir,
            # but mocks/ itself was never staged
            stagedpath = s_common.genpath(outdir, 'page.md')
            with open(stagedpath, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(stagedpath, srcdir=srcdir, outdir=outdir) as mdstorm:
                self.eq(srcdir, mdstorm.srcbasedir)
                lines = await mdstorm.run()

            self.isin('<ANSI STANDARD PIZZA>', ''.join(lines))

    async def test_mdstorm_mock_http_per_fence_overrides_document_default(self):
        # two fences, each with its own distinct cassette, override the document-wide default
        cassette = self.getTestFilePath('mdstorm', 'httprespmulti.yaml')
        md = '\n'.join((
            '```mdstorm-setup',
            '--vcr-opts \'{"record_mode": "none"}\'',
            '```',
            '',
            f'```mdstorm --mock-http {cassette}',
            '$resp=$lib.inet.http.get("http://example.com") '
            '[ it:dev:str=$resp.body.decode() ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'mockhttpfenceoverride.md')
            with open(path, 'w') as fd:
                fd.write(md)

            # a bogus document-wide default must never be consulted, since the fence
            # supplies its own cassette
            async with await s_mdstorm.MdStorm.anit(path, mockhttp='/does/not/exist.yaml') as mdstorm:
                lines = await mdstorm.run()

            self.isin('<ANSI STANDARD PIZZA>', ''.join(lines))

    async def test_mdinclude_splices_markdown_raw(self):
        with self.getTestDir() as dirn:
            fragpath = s_common.genpath(dirn, 'frag.md')
            with open(fragpath, 'w') as fd:
                fd.write('## Conf Option\n\nSome autodoc-generated markdown.\n')

            path = s_common.genpath(dirn, 'inc.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    'before',
                    '',
                    '```mdinclude',
                    'frag.md',
                    '```',
                    '',
                    'after',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('## Conf Option', text)
            self.isin('Some autodoc-generated markdown.', text)
            self.notin('```mdinclude', text)
            self.isin('before', text)
            self.isin('after', text)

    async def test_mdinclude_code_flag_wraps_fence(self):
        with self.getTestDir() as dirn:
            fragpath = s_common.genpath(dirn, 'script.sh')
            with open(fragpath, 'w') as fd:
                fd.write('echo hello\n')

            path = s_common.genpath(dirn, 'inc.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude --code bash',
                    'script.sh',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('```bash\n', text)
            self.isin('echo hello\n', text)

    async def test_mdinclude_code_flag_adds_trailing_newline(self):
        # the included file has no trailing newline; the closing fence must
        # still land on its own line
        with self.getTestDir() as dirn:
            fragpath = s_common.genpath(dirn, 'noeol.py')
            with open(fragpath, 'w') as fd:
                fd.write('print("no trailing newline")')

            path = s_common.genpath(dirn, 'inc.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude --code python',
                    'noeol.py',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('print("no trailing newline")\n```\n', text)

    async def test_mdinclude_absolute_path(self):
        with self.getTestDir() as dirn:
            fragpath = s_common.genpath(dirn, 'abs.md')
            with open(fragpath, 'w') as fd:
                fd.write('absolute content\n')

            path = s_common.genpath(dirn, 'inc.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude',
                    f'{fragpath}',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            self.isin('absolute content', ''.join(lines))

    async def test_mdinclude_missing_file(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'inc.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude',
                    'doesnotexist.md',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchFile):
                    await mdstorm.run()

    async def test_mdinclude_missing_absolute_path(self):
        # an absolute target is never retried against srcbasedir -- that
        # fallback only applies to a relative target that climbs outside
        # the docroot.
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'inc.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude',
                    s_common.genpath(dirn, 'doesnotexist.md'),
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchFile):
                    await mdstorm.run()

    async def test_mdinclude_path_on_fence_line(self):
        # the path may also be given on the opening fence line rather than the body
        with self.getTestDir() as dirn:
            fragpath = s_common.genpath(dirn, 'frag.md')
            with open(fragpath, 'w') as fd:
                fd.write('inline path content\n')

            path = s_common.genpath(dirn, 'inc.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude frag.md',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            self.isin('inline path content', ''.join(lines))

    async def test_mdinclude_falls_back_to_srcbasedir(self):
        # a target authored as "../CHANGELOG.md" (or similar) deliberately
        # climbs outside the docroot -- stageTree only mirrors the docroot
        # itself, so that target is never staged into self.basedir. It must
        # still resolve against self.srcbasedir, the doc's original,
        # unstaged location (see SYN-11365).
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            outdir = s_common.genpath(workdir, 'built')
            s_common.gendir(srcdir)
            s_common.gendir(outdir)

            with open(s_common.genpath(workdir, 'CHANGELOG.md'), 'w') as fd:
                fd.write('changelog content\n')

            # the staged copy: same relpath-to-outdir structure as srcdir
            stagedpath = s_common.genpath(outdir, 'changelog.md')
            with open(stagedpath, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude',
                    '../CHANGELOG.md',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(stagedpath, srcdir=srcdir, outdir=outdir) as mdstorm:
                lines = await mdstorm.run()

            self.isin('changelog content', ''.join(lines))

    async def test_mdinclude_prefers_staged_basedir_over_srcbasedir(self):
        # a relative target that DOES live inside the docroot resolves from
        # the staged copy (self.basedir), not the original source location,
        # the same way it always has.
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            outdir = s_common.genpath(workdir, 'built')
            s_common.gendir(srcdir)
            s_common.gendir(outdir)

            with open(s_common.genpath(srcdir, 'frag.md'), 'w') as fd:
                fd.write('original content\n')
            with open(s_common.genpath(outdir, 'frag.md'), 'w') as fd:
                fd.write('staged content\n')

            stagedpath = s_common.genpath(outdir, 'inc.md')
            with open(stagedpath, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude',
                    'frag.md',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(stagedpath, srcdir=srcdir, outdir=outdir) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('staged content', text)
            self.notin('original content', text)

    async def test_mdinclude_missing_from_both_basedir_and_srcbasedir(self):
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            outdir = s_common.genpath(workdir, 'built')
            s_common.gendir(srcdir)
            s_common.gendir(outdir)

            stagedpath = s_common.genpath(outdir, 'inc.md')
            with open(stagedpath, 'w') as fd:
                fd.write('\n'.join((
                    '```mdinclude',
                    '../doesnotexist.md',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(stagedpath, srcdir=srcdir, outdir=outdir) as mdstorm:
                with self.raises(s_exc.NoSuchFile):
                    await mdstorm.run()

    async def test_mdautodoc_conf(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'conf.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --conf synapse.tests.test_lib_stormsvc.StormvarServiceCell',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('### auth:passwd', text)
            self.notin('```mdautodoc', text)

    async def test_mdautodoc_api(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'api.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --api synapse.axon.AxonApi',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('# AxonApi', text)
            self.notin('```mdautodoc', text)

    async def test_mdautodoc_stormpkg_relative_path(self):
        with self.getTestDir() as dirn:
            pkgpath = s_common.genpath(dirn, 'minimalpkg.yaml')
            s_common.yamlsave({'name': 'minimalpkg', 'version': '0.0.1'}, pkgpath)

            s_common.gendir(dirn, 'docs')
            path = s_common.genpath(dirn, 'docs', 'stormpackage.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --stormpkg ../minimalpkg.yaml',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('# Storm Package: minimalpkg', text)

    async def test_mdautodoc_stormpkg_missing_file(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'missingpkg.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --stormpkg doesnotexist.yaml',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchFile):
                    await mdstorm.run()

    async def test_mdautodoc_model_types_and_forms(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'model.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --model-types',
                    '```',
                    '',
                    '```mdautodoc --model-forms',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('# Synapse Data Model - Types', text)
            self.isin('# Synapse Data Model - Forms', text)

    async def test_mdautodoc_stormtypes_libs_and_prims(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'stormtypes.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --stormtypes-libs',
                    '```',
                    '',
                    '```mdautodoc --stormtypes-prims',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('# Storm Libraries', text)
            self.isin('# Storm Types', text)

    async def test_mdautodoc_level_shifts_headings(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'api.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --api synapse.axon.AxonApi --level 1',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            text = ''.join(lines)
            self.isin('\n## AxonApi\n', text)
            self.notin('\n# AxonApi\n', text)

    async def test_mdautodoc_requires_exactly_one_flag(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'zeroflags.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(SystemExit):
                    await mdstorm.run()

            path = s_common.genpath(dirn, 'twoflags.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --conf synapse.cortex.Cortex --api synapse.axon.AxonApi',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(SystemExit):
                    await mdstorm.run()

    async def test_mdautodoc_srcbasedir_reaches_outside_staged_docroot(self):
        # a staged doc bundle (outdir mirroring srcdir) resolves --stormpkg
        # against the ORIGINAL srcdir, not the staged copy, since a package's
        # own yaml is never staged into outdir.
        with self.getTestDir() as dirn:
            srcdir = s_common.genpath(dirn, 'src', 'pkgdocs')
            outdir = s_common.genpath(dirn, 'out', 'pkgdocs')
            s_common.gendir(srcdir, 'docs')
            s_common.gendir(outdir, 'docs')

            pkgpath = s_common.genpath(srcdir, 'srcbasedirpkg.yaml')
            s_common.yamlsave({'name': 'srcbasedirpkg', 'version': '0.0.1'}, pkgpath)

            outpath = s_common.genpath(outdir, 'docs', 'stormpackage.md')
            with open(outpath, 'w') as fd:
                fd.write('\n'.join((
                    '```mdautodoc --stormpkg ../srcbasedirpkg.yaml',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(outpath, srcdir=srcdir, outdir=outdir) as mdstorm:
                self.eq(mdstorm.srcbasedir, s_common.genpath(srcdir, 'docs'))
                lines = await mdstorm.run()

            self.isin('# Storm Package: srcbasedirpkg', ''.join(lines))

    async def test_mdautodoc_srcbasedir_defaults_to_basedir_without_srcdir(self):
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'nosrcdir.md')
            with open(path, 'w') as fd:
                fd.write('```mdautodoc --model-types\n```\n')

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                self.eq(mdstorm.srcbasedir, mdstorm.basedir)

    async def test_mdstorm_pkg_missing_file(self):
        # absolute path that does not exist
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'pkgmissing.md')
            missing = s_common.genpath(dirn, 'newp.yaml')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdstorm-setup',
                    f'--load-pkg {missing}',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchFile):
                    await mdstorm.run()

        # relative path resolves against the md file's directory and does not exist
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'pkgmissingrel.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdstorm-setup',
                    '--load-pkg newp.yaml',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                with self.raises(s_exc.NoSuchFile):
                    await mdstorm.run()

    async def test_mdstorm_pkg_without_onload(self):
        # a package with no onload key does not wait on a waiter
        with self.getTestDir() as dirn:
            noonload_yaml = s_common.genpath(dirn, 'noonload.yaml')
            with open(noonload_yaml, 'w') as fd:
                fd.write('name: noonloadpkg\nversion: 0.0.1\n')

            path = s_common.genpath(dirn, 'pkgnoonload.md')
            with open(path, 'w') as fd:
                fd.write('\n'.join((
                    '```mdstorm-setup',
                    f'--load-pkg {noonload_yaml}',
                    '```',
                    '',
                )))

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                await mdstorm.run()

    async def test_mdstorm_pkg_and_svc_onload_timeout(self):
        testpkg_yaml = self.getTestFilePath('stormpkg', 'testpkg.yaml')
        oldv = s_mdstorm.ONLOAD_TIMEOUT
        s_mdstorm.ONLOAD_TIMEOUT = 0.1
        try:
            with self.getTestDir() as dirn:
                path = s_common.genpath(dirn, 'pkgtimeout.md')
                with open(path, 'w') as fd:
                    fd.write('\n'.join((
                        '```mdstorm-setup',
                        '```',
                        '',
                        '```mdstorm',
                        '--hide',
                        '--',
                        '$lib.globals.onload_sleep = 2',
                        '```',
                        '',
                    )))

                async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                    await mdstorm.run()
                    with self.raises(s_exc.SynErr) as ectx:
                        await mdstorm._loadStormPkg(testpkg_yaml)
                    self.eq('Package onload failed to run for testpkg', ectx.exception.errinfo['mesg'])

                    with self.raises(s_exc.SynErr) as ectx:
                        await mdstorm._startStormSvc(
                            "synapse.tests.files.mdstorm.testsvc.Testsvc testsvc {\"secret\": \"jupiter\"}")
                    self.eq('Package onload failed to run for service testsvc', ectx.exception.errinfo['mesg'])
        finally:
            s_mdstorm.ONLOAD_TIMEOUT = oldv

class MdStormRemoteCortexTest(s_test.SynTest):

    async def test_mdstorm_syn_docs_cortex_forks_view(self):
        async with self.getTestCore() as core:
            async with core.getLocalProxy() as prox:
                url = core.getLocalUrl()

                md = '\n'.join((
                    '```mdstorm-setup',
                    '```',
                    '',
                    '```mdstorm',
                    "[ inet:fqdn=vertex.link ]",
                    '```',
                    '',
                ))
                with self.getTestDir() as dirn:
                    path = s_common.genpath(dirn, 'remote.md')
                    with open(path, 'w') as fd:
                        fd.write(md)

                    with self.setTstEnvars(SYN_DOCS_CORTEX=url):
                        async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                            lines = await mdstorm.run()

                    text = ''.join(lines)
                    self.isin('inet:fqdn=vertex.link', text)

                    # the fork must not have leaked the node into the main view
                    nodes = await core.nodes('inet:fqdn=vertex.link')
                    self.len(0, nodes)

                    # and the forked view must have been torn down (only the
                    # original default view remains)
                    views = await core.callStorm('return($lib.view.list())')
                    self.len(1, views)

    async def test_mdstorm_vars_flag_preserves_view_under_fork(self):
        async with self.getTestCore() as core:
            url = core.getLocalUrl()
            md = '\n'.join((
                '```mdstorm-setup',
                '```',
                '',
                '```mdstorm',
                '--vars {"targ": "vertex.link"}',
                '--',
                '[ inet:fqdn=$targ ]',
                '```',
                '',
            ))
            with self.getTestDir() as dirn:
                path = s_common.genpath(dirn, 'opts.md')
                with open(path, 'w') as fd:
                    fd.write(md)

                with self.setTstEnvars(SYN_DOCS_CORTEX=url):
                    async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                        await mdstorm.run()

                # the fork must not have leaked the node into the main view
                nodes = await core.nodes('inet:fqdn=vertex.link')
                self.len(0, nodes)

    async def test_mdstorm_finicore_closes_proxy_even_if_delview_fails(self):
        async with self.getTestCore() as core:
            url = core.getLocalUrl()
            md = '\n'.join((
                '```mdstorm-setup',
                '```',
                '',
            ))
            with self.getTestDir() as dirn:
                path = s_common.genpath(dirn, 'delviewfail.md')
                with open(path, 'w') as fd:
                    fd.write(md)

                with self.setTstEnvars(SYN_DOCS_CORTEX=url):
                    mdstorm = await s_mdstorm.MdStorm.anit(path)
                    await mdstorm.run()

                    proxy = mdstorm.core

                    async def _boom(text, opts=None):
                        raise s_exc.SynErr(mesg='boom')

                    proxy.callStorm = _boom

                    # _finiCore is an onfini callback wrapped in Base.fini()'s
                    # own try/except-and-log, so this must not raise -- but
                    # the important assertion is that the proxy still gets
                    # closed despite the delView-equivalent call blowing up.
                    await mdstorm.fini()

                    self.true(proxy.isfini)

    async def test_mdstorm_pkg_and_svc_rejected_under_syn_docs_cortex(self):
        async with self.getTestCore() as core:
            url = core.getLocalUrl()
            md = '\n'.join((
                '```mdstorm-setup',
                '--load-pkg synapse/tests/files/stormpkg/testpkg.yaml',
                '```',
                '',
            ))
            with self.getTestDir() as dirn:
                path = s_common.genpath(dirn, 'guard.md')
                with open(path, 'w') as fd:
                    fd.write(md)

                with self.setTstEnvars(SYN_DOCS_CORTEX=url):
                    async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                        with self.raises(s_exc.BadArg):
                            await mdstorm.run()

class MdStormEngineTest(s_test.SynTest):
    '''
    Coverage for MdStormCli / getDocsCell / getDocsCluster -- the cell-boot and
    CLI-output helpers mdstorm inlined from the old rstorm engine.
    '''

    async def test_mdstorm_cli_output_runcmdline(self):
        async with self.getTestCore() as core:

            echoline_during = []

            async def spy_run(self_arg, text, opts=None):
                echoline_during.append(self_arg.echoline)

            # ! path with echoline=True: command is echoed; echoline is False during the delegated call
            outp = s_output.OutPutStr()
            async with await s_mdstorm.MdStormCli.anit(item=core, outp=outp) as cli:
                cli.echoline = True
                with mock.patch.object(s_storm.StormCli, 'runCmdLine', spy_run):
                    await cli.runCmdLine('!help')
                self.isin('!help', str(outp))
                self.eq(echoline_during, [False])
                self.true(cli.echoline)

            # ! path with echoline=False: no echo; echoline restored to False after call
            outp2 = s_output.OutPutStr()
            async with await s_mdstorm.MdStormCli.anit(item=core, outp=outp2) as cli2:
                cli2.echoline = False
                echoline_during.clear()
                with mock.patch.object(s_storm.StormCli, 'runCmdLine', spy_run):
                    await cli2.runCmdLine('!help')
                self.notin('!help', str(outp2))
                self.eq(echoline_during, [False])
                self.false(cli2.echoline)

            # ! path with exception: finally block restores echoline
            outp3 = s_output.OutPutStr()
            async with await s_mdstorm.MdStormCli.anit(item=core, outp=outp3) as cli3:
                cli3.echoline = True

                async def raising_run(self_arg, text, opts=None):
                    raise s_exc.SynErr(mesg='test')

                with mock.patch.object(s_storm.StormCli, 'runCmdLine', raising_run):
                    with self.raises(s_exc.SynErr):
                        await cli3.runCmdLine('!oops')
                self.true(cli3.echoline)

            # non-! path: Storm query executes normally
            outp4 = s_output.OutPutStr()
            async with await s_mdstorm.MdStormCli.anit(item=core, outp=outp4) as cli4:
                await cli4.runDocCmdLine('$lib.print(hello)', {})
                self.isin('hello', str(outp4))

    async def test_mdstorm_cli_printnodeprop_multiline(self):
        async with self.getTestCore() as core:
            outp = s_output.OutPutStr()
            async with await s_mdstorm.MdStormCli.anit(item=core, outp=outp) as cli:
                cli._printNodeProp('text', 'line1\nline2\nline3')

            text = str(outp)
            self.isin('text = line1', text)
            self.isin('line2', text)
            self.isin('line3', text)

    async def test_mdstorm_getdocscell_nosuchctor(self):
        with self.raises(s_exc.NoSuchCtor):
            async with s_mdstorm.getDocsCell('synapse.tests.test_lib_mdstorm.NoSuchThingHere', {}):
                pass

    async def test_mdstorm_getdocscell_envars(self):

        # SYN_CORTEX_STORM_LOG applies to a Cortex booted by getDocsCell(), matching
        # the SYN_<CELL>_* environment behavior of a production boot (initFromArgv).
        with self.setTstEnvars(SYN_CORTEX_STORM_LOG='true'):
            async with s_mdstorm.getDocsCell('synapse.cortex.Cortex', {}) as core:
                self.true(core.conf.get('storm:log'))

        # An explicitly provided conf value takes precedence over the environment.
        with self.setTstEnvars(SYN_CORTEX_STORM_LOG='true'):
            async with s_mdstorm.getDocsCell('synapse.cortex.Cortex', {'storm:log': False}) as core:
                self.false(core.conf.get('storm:log'))

        # With no envar set, the schema default is used.
        async with s_mdstorm.getDocsCell('synapse.cortex.Cortex', {}) as core:
            self.false(core.conf.get('storm:log'))

    async def test_mdstorm_getdocscell_noncell_ctor(self):

        # A ctor with no initCellConf() (a doc-only test double with a custom
        # anit(), not a real Cell) falls back to the bare conf dict rather than
        # erroring, and env vars are not applied to it (it never supported them).
        with self.setTstEnvars(SYN_CORTEX_STORM_LOG='true'):
            async with s_mdstorm.getDocsCell('synapse.tests.test_lib_mdstorm.NonCellMockCtor',
                                              {'hehe': 'haha'}) as cell:
                self.eq({'hehe': 'haha'}, cell.conf)

    async def test_mdstorm_getdocscluster_cortex_subclass(self):

        # an mdstorm-setup --cortex naming a Cortex subclass ( here the base
        # Cortex itself ) boots via getDocsCluster() with AHA-resolved axon/jsonstor peers.
        md = '\n'.join((
            '```mdstorm-setup --cortex synapse.cortex.Cortex',
            '```',
            '```mdstorm',
            '[ inet:asn=1 ]',
            '```',
            '',
        ))
        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'cortex_subclass.md')
            with open(path, 'w') as fd:
                fd.write(md)

            async with await s_mdstorm.MdStorm.anit(path) as mdstorm:
                lines = await mdstorm.run()

            self.isin('inet:asn=1', ''.join(lines))

    async def test_mdstorm_getdocscluster_readpool_default(self):

        # readpool:size is only defaulted for a ctor that actually declares
        # that confdef ( eg synmods.enterprise.cortex.Cortex ) -- the base
        # synapse.cortex.Cortex has no such confdef, so getDocsCluster() must not
        # set it there ( see test_mdstorm_getdocscluster_cortex_subclass, which
        # boots the base Cortex through the same path without it ).
        async with s_mdstorm.getDocsCluster(ctor=ReadPoolCortex) as clus:
            self.eq(0, clus.cortex.conf.get('readpool:size'))

    async def test_mdstorm_getdocscluster_bootfail(self):

        # if the Cortex ctor's anit() raises after axon / jsonstor have
        # already booted, the Cluster's teardown must still tear the
        # already-booted peers down cleanly, rather than leaking them.
        with self.getLoggerStream('synapse.lib.cluster') as stream:
            with self.raises(s_exc.SynErr):
                async with s_mdstorm.getDocsCluster(ctor=BoomCortexCtor):
                    pass

        stream.seek(0)
        self.notin('ERROR', stream.read())

    async def test_mdstorm_getdocscluster_peers(self):

        import synapse.tests.files.mdstorm.testsvc as s_testsvc

        async with s_mdstorm.getDocsCluster() as clus:
            core = clus.cortex

            # a caller needing an additional power-up peer alongside the doc
            # Cortex ( eg a doc fixture's FileParser ) boots it with the
            # yielded Cluster's addSvc(), which already awaits its discovery
            # as a storm service.
            await clus.addSvc(s_testsvc.Testsvc, conf={'secret': 'sesame'})

            ssvc = core.getStormSvc(s_testsvc.Testsvc.getCellType())
            self.nn(ssvc)
            self.true(ssvc.svcready.is_set())

            # the peer's declared storm package ( registered on link, same as
            # any other storm service ) is usable.
            msgs = await core.stormlist('testsvc.test')
            self.stormIsInPrint('sesame', msgs)

    async def test_mdstorm_getdocscluster_peers_bootfail(self):

        # a peer ctor's anit() raising after the Cortex has already booted must
        # still tear the Cortex / jsonstor / axon / aha down cleanly, same as a
        # Cortex-boot failure.
        with self.getLoggerStream('synapse.lib.cluster') as stream:
            with self.raises(s_exc.SynErr):
                async with s_mdstorm.getDocsCluster() as clus:
                    await clus.addSvc(BoomPeerCtor)

        stream.seek(0)
        self.notin('ERROR', stream.read())
