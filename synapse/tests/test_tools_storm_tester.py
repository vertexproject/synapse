import io
import os
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils
import synapse.tools.storm.tester as s_tester

class TestStormTester(s_t_utils.SynTest):

    async def test_tools_storm_tester(self):

        with self.getTestDir() as dirn:

            # Valid query with node, props, tags, tag timestamp
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=example.com +#test.tag +#foo=(2020, 2021) ]\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main([fpath], outp=outp), 0)
            outp.expect('inet:fqdn=example.com')
            outp.expect('#test.tag')
            outp.expect('#foo = (2020-01-01')
            outp.expect('complete.')

            # Print and warn messages
            fpath = os.path.join(dirn, 'msg.storm')
            with open(fpath, 'w') as fd:
                fd.write('$lib.print(hello) $lib.warn("uh oh")\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main([fpath], outp=outp), 0)
            outp.expect('hello')
            outp.expect('WARNING: uh oh')

            # Bad syntax
            fpath = os.path.join(dirn, 'bad.storm')
            with open(fpath, 'w') as fd:
                fd.write('%%%badquery\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main([fpath], outp=outp), 1)
            s = str(outp)
            self.true('Syntax Error' in s or 'ERROR' in s)

            # Runtime error
            fpath = os.path.join(dirn, 'rterr.storm')
            with open(fpath, 'w') as fd:
                fd.write('$lib.raise(FooBar, boom)\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main([fpath], outp=outp), 1)
            outp.expect('ERROR:')

            # Empty file
            fpath = os.path.join(dirn, 'empty.storm')
            with open(fpath, 'w') as fd:
                fd.write('')

            outp = self.getTestOutp()
            self.eq(await s_tester.main([fpath], outp=outp), 1)
            outp.expect('No Storm query text provided')

        # Stdin
        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('[ inet:fqdn=stdin.example.com ]\n')):
            self.eq(await s_tester.main(['-'], outp=outp), 0)
        outp.expect('inet:fqdn=stdin.example.com')

        # Help
        outp = self.getTestOutp()
        with self.raises(s_exc.ParserExit):
            await s_tester.main(['-h'], outp=outp)

    async def test_tools_storm_tester_views(self):

        with self.getTestDir() as dirn:
            coredir = os.path.join(dirn, 'mycore')

            # Create a node with --dir
            fpath = os.path.join(dirn, 'create.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=reuse.example.com ]\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--dir', coredir, fpath], outp=outp), 0)
            outp.expect('inet:fqdn=reuse.example.com')
            self.true(os.path.isdir(coredir))

            # Reuse the dir -- node persists
            qpath = os.path.join(dirn, 'query.storm')
            with open(qpath, 'w') as fd:
                fd.write('inet:fqdn=reuse.example.com\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--dir', coredir, qpath], outp=outp), 0)
            outp.expect('inet:fqdn=reuse.example.com')

            # Raw JSON output
            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--raw', '--dir', coredir, qpath], outp=outp), 0)
            s = str(outp)
            self.isin('"node"', s)
            self.isin('"fini"', s)

            # Fork a child view for --view tests
            async with await s_cortex.Cortex.anit(coredir) as core:
                vdef = await core.view.fork()
                viewiden = vdef.get('iden')

            # --view: query the child view (inherits parent data)
            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--dir', coredir, '--view', viewiden, qpath], outp=outp), 0)
            outp.expect('inet:fqdn=reuse.example.com')

            # --forked: create a node in a disposable fork
            fpath2 = os.path.join(dirn, 'forked.storm')
            with open(fpath2, 'w') as fd:
                fd.write('[ inet:fqdn=forked.example.com ]\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--dir', coredir, '--forked', fpath2], outp=outp), 0)
            outp.expect('inet:fqdn=forked.example.com')

            # Forked node is NOT in the default view
            qpath2 = os.path.join(dirn, 'qforked.storm')
            with open(qpath2, 'w') as fd:
                fd.write('inet:fqdn=forked.example.com\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--dir', coredir, qpath2], outp=outp), 0)
            self.notin('inet:fqdn=forked.example.com', str(outp))

            # --view + --forked: fork from child view, data does not persist
            fpath3 = os.path.join(dirn, 'forkview.storm')
            with open(fpath3, 'w') as fd:
                fd.write('[ inet:fqdn=forkview.example.com ]\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--dir', coredir, '--view', viewiden, '--forked', fpath3], outp=outp), 0)
            outp.expect('inet:fqdn=forkview.example.com')

            # Not visible in the child view
            qpath3 = os.path.join(dirn, 'qforkview.storm')
            with open(qpath3, 'w') as fd:
                fd.write('inet:fqdn=forkview.example.com\n')

            outp = self.getTestOutp()
            self.eq(await s_tester.main(['--dir', coredir, '--view', viewiden, qpath3], outp=outp), 0)
            self.notin('inet:fqdn=forkview.example.com', str(outp))
