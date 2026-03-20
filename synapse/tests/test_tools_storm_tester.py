import io
import os
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.cortex as s_cortex

import synapse.tests.utils as s_t_utils
import synapse.tools.storm.tester as s_tester

class TestStormTester(s_t_utils.SynTest):

    async def test_tools_storm_tester_file(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('inet:fqdn=example.com')
            outp.expect('complete.')

    async def test_tools_storm_tester_bad(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'bad.storm')
            with open(fpath, 'w') as fd:
                fd.write('%%%badquery\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 1)
            s = str(outp)
            self.true('Syntax Error' in s or 'ERROR' in s)

    async def test_tools_storm_tester_raw(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--raw', fpath], outp=outp)
            self.eq(ret, 0)
            s = str(outp)
            self.isin('"node"', s)
            self.isin('"fini"', s)

    async def test_tools_storm_tester_dir(self):
        with self.getTestDir() as dirn:
            coredir = os.path.join(dirn, 'mycore')

            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, fpath], outp=outp)
            self.eq(ret, 0)
            self.true(os.path.isdir(coredir))

    async def test_tools_storm_tester_dir_reuse(self):
        with self.getTestDir() as dirn:
            coredir = os.path.join(dirn, 'mycore')

            fpath = os.path.join(dirn, 'create.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=reuse.example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('inet:fqdn=reuse.example.com')

            qpath = os.path.join(dirn, 'query.storm')
            with open(qpath, 'w') as fd:
                fd.write('inet:fqdn=reuse.example.com\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, qpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('inet:fqdn=reuse.example.com')

    async def test_tools_storm_tester_stdin(self):
        outp = self.getTestOutp()
        with mock.patch('sys.stdin', io.StringIO('[ inet:fqdn=stdin.example.com ]\n')):
            ret = await s_tester.main(['-'], outp=outp)
        self.eq(ret, 0)
        outp.expect('inet:fqdn=stdin.example.com')

    async def test_tools_storm_tester_empty(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'empty.storm')
            with open(fpath, 'w') as fd:
                fd.write('')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 1)
            outp.expect('No Storm query text provided')

    async def test_tools_storm_tester_print_warn(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('$lib.print(hello) $lib.warn("uh oh")\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('hello')
            outp.expect('WARNING: uh oh')

    async def test_tools_storm_tester_tags(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=tag.example.com +#test.tag ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('#test.tag')

    async def test_tools_storm_tester_tag_time(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=ttime.example.com +#foo=(2020, 2021) ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('#foo = (2020-01-01')

    async def test_tools_storm_tester_long_badsyntax(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'bad.storm')
            # Error near the end of a long query (>60 chars) — covers text truncation with trailing ...
            with open(fpath, 'w') as fd:
                fd.write('inet:fqdn=a.b.c.d.e.f.g.h.i.j.k.l.m.n.o.p.q.r.s.t.u.v.w.x %%%\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 1)
            s = str(outp)
            self.true('Syntax Error' in s or 'ERROR' in s)

    async def test_tools_storm_tester_long_badsyntax_mid(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'bad.storm')
            # Error in the middle of a long query — covers both leading ... and trailing ...
            padding = 'a' * 40
            with open(fpath, 'w') as fd:
                fd.write(f'{padding} %%% {padding}\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 1)
            s = str(outp)
            self.true('Syntax Error' in s or 'ERROR' in s or '...' in s)

    async def test_tools_storm_tester_runtime_err(self):
        with self.getTestDir() as dirn:
            fpath = os.path.join(dirn, 'test.storm')
            with open(fpath, 'w') as fd:
                fd.write('$lib.raise(FooBar, boom)\n')

            outp = self.getTestOutp()
            ret = await s_tester.main([fpath], outp=outp)
            self.eq(ret, 1)
            outp.expect('ERROR:')

    async def test_tools_storm_tester_mesg_funcs(self):
        outp = self.getTestOutp()

        # Test node with universal props
        node = (
            ('test:str', 'hello'),
            {
                'repr': 'hello',
                'props': {
                    '.created': 1234567890000,
                    '_ext': 'extval',
                    'tick': 1234567890000,
                },
                'reprs': {
                    '.created': '2009/02/13 23:31:30.000',
                    '_ext': 'extval',
                    'tick': '2009/02/13 23:31:30.000',
                },
                'tags': {
                    'foo': (None, None, None),
                    'bar': (1577836800000, 1609459200000, None),
                },
                'tagprops': {
                    'bar': {'risk': 50},
                },
                'tagpropreprs': {
                    'bar': {'risk': '50'},
                },
            },
        )
        ret = s_tester.printStormMesg(outp, ('node', node))
        self.true(ret)
        s = str(outp)
        self.isin('test:str=hello', s)
        self.isin(':tick', s)
        self.isin(':_ext', s)
        self.isin('.created', s)
        self.isin('#bar =', s)
        self.isin('#bar:risk = 50', s)

        # Test warn with extras
        outp = self.getTestOutp()
        ret = s_tester.printStormMesg(outp, ('warn', {'mesg': 'bad thing', 'key': 'val'}))
        self.true(ret)
        outp.expect('WARNING: bad thing key=val')

        # Test unknown message type returns True
        outp = self.getTestOutp()
        ret = s_tester.printStormMesg(outp, ('init', {}))
        self.true(ret)

    async def test_tools_storm_tester_view(self):
        with self.getTestDir() as dirn:
            coredir = os.path.join(dirn, 'mycore')

            # First run: create a node in the default view
            fpath = os.path.join(dirn, 'create.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=view.example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, fpath], outp=outp)
            self.eq(ret, 0)

            # Get the view iden from the cortex
            async with await s_cortex.Cortex.anit(coredir) as core:
                vdef = await core.view.fork()
                viewiden = vdef.get('iden')

            # Run a query in the forked view — it should see the node from the parent
            qpath = os.path.join(dirn, 'query.storm')
            with open(qpath, 'w') as fd:
                fd.write('inet:fqdn=view.example.com\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, '--view', viewiden, qpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('inet:fqdn=view.example.com')

    async def test_tools_storm_tester_forked(self):
        with self.getTestDir() as dirn:
            coredir = os.path.join(dirn, 'mycore')

            # Create a node in the forked view
            fpath = os.path.join(dirn, 'create.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=forked.example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, '--forked', fpath], outp=outp)
            self.eq(ret, 0)
            outp.expect('inet:fqdn=forked.example.com')

            # Query the default view — forked node should NOT be there
            qpath = os.path.join(dirn, 'query.storm')
            with open(qpath, 'w') as fd:
                fd.write('inet:fqdn=forked.example.com\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, qpath], outp=outp)
            self.eq(ret, 0)
            s = str(outp)
            self.notin('inet:fqdn=forked.example.com', s)

    async def test_tools_storm_tester_forked_view(self):
        with self.getTestDir() as dirn:
            coredir = os.path.join(dirn, 'mycore')

            # Create a node in the default view
            fpath = os.path.join(dirn, 'create.storm')
            with open(fpath, 'w') as fd:
                fd.write('[ inet:fqdn=parent.example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, fpath], outp=outp)
            self.eq(ret, 0)

            # Create a child view
            async with await s_cortex.Cortex.anit(coredir) as core:
                vdef = await core.view.fork()
                viewiden = vdef.get('iden')

            # Fork from that child view and create a node
            fpath2 = os.path.join(dirn, 'create2.storm')
            with open(fpath2, 'w') as fd:
                fd.write('[ inet:fqdn=forkedview.example.com ]\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, '--view', viewiden, '--forked', fpath2], outp=outp)
            self.eq(ret, 0)
            outp.expect('inet:fqdn=forkedview.example.com')

            # The child view should NOT have the forked node
            qpath = os.path.join(dirn, 'query.storm')
            with open(qpath, 'w') as fd:
                fd.write('inet:fqdn=forkedview.example.com\n')

            outp = self.getTestOutp()
            ret = await s_tester.main(['--dir', coredir, '--view', viewiden, qpath], outp=outp)
            self.eq(ret, 0)
            s = str(outp)
            self.notin('inet:fqdn=forkedview.example.com', s)

    async def test_tools_storm_tester_help(self):
        outp = self.getTestOutp()
        with self.raises(s_exc.ParserExit):
            await s_tester.main(['-h'], outp=outp)
