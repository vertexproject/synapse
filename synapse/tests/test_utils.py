import os
import time
import shutil
import asyncio
import logging
import unittest
import contextlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
import synapse.lib.stormsvc as s_stormsvc

import synapse.tests.utils as s_t_utils

import aiohttp
import aiohttp_socks

logger = logging.getLogger(__name__)

class ClusterSvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_pkg = {  # type: ignore
        'name': 'clustersvc',
        'version': '0.0.1',
        'commands': (
            {
                'name': 'clustersvc.hi',
                'storm': '$lib.print(hello)',
            },
        ),
    }

class ClusterSvcCell(s_cell.Cell):
    celltype = 'clustersvc'
    cellapi = ClusterSvcApi

class TestUtils(s_t_utils.SynTest):

    async def test_gettestcluster(self):

        # bare call boots a cortex with implicit axon + jsonstor on one AHA network
        async with self.getTestCluster() as clus:
            self.nn(clus.aha)
            self.nn(clus.cortex)
            self.nn(clus.axon)
            self.nn(clus.jsonstor)

            # the test model is loaded into the Cortex
            self.len(1, await clus.cortex.nodes('[ test:str=woot ]'))

            # every cortex gets built-in creds: root passwd + a 'user' account
            self.nn(await clus.cortex.auth.getUserByName('user'))
            self.true(await clus.cortex.auth.rootuser.tryPasswd('secret'))

            # the cortex discovers its axon/jsonstor peers by cell type via AHA
            aprox = await clus.cortex.getAxon()
            self.eq(await aprox.getCellIden(), clus.axon.iden)
            await clus.cortex.setJsonObj(('foo',), {'bar': 1})
            self.eq({'bar': 1}, await clus.cortex.getJsonObj(('foo',)))

            # services are reachable by AHA name, celltype, and the proxy helper
            self.isin('000.cortex', clus.svcs)
            self.isin('000.axon', clus.svcs)
            self.eq(clus.cortex.iden, clus.get('cortex').iden)
            self.none(clus.get('newp'))
            self.nn(clus.getLocalUrl())
            self.nn(clus.getLocalUrl('axon'))
            async with clus.proxy('cortex') as prox:
                self.nn(await prox.getCellIden())

            # an unknown attribute raises AttributeError
            with self.raises(AttributeError):
                clus.newpservice

        # mirrors: a leader plus one same-iden mirror reachable by AHA name and
        # the service config is provided under the ``conf`` envelope key
        async with self.getTestCluster({'cortex': {'conf': {'nexslog:en': True}, 'mirrors': 1}}) as clus:
            self.true(clus.cortex.conf.get('nexslog:en'))
            self.isin('001.cortex', clus.svcs)
            self.eq(clus.cortex.iden, clus.svcs['001.cortex'].iden)

        # model=False skips loading the synapse test model into the Cortex
        async with self.getTestCluster({'cortex': {'model': False}}) as clus:
            self.none(clus.cortex.model.form('test:str'))

        # a deployed Storm service is auto-discovered by the Cortex; a ctor
        # override boots a service type with no registered ctor
        svcs = {'cortex': {}, 'clustersvc': {'ctor': ClusterSvcCell}}
        async with self.getTestCluster(svcs) as clus:
            self.nn(clus.get('clustersvc'))
            self.isin('000.clustersvc', clus.svcs)
            self.nn(clus.cortex.getStormSvc('clustersvc'))

        # addSvc() dynamically boots a service onto the running cluster and awaits
        # its discovery so a test can immediately use / watch it
        async with self.getTestCluster({'cortex': {}}) as clus:

            svc = await clus.addSvc(ClusterSvcCell)
            self.eq(svc.iden, clus.get('clustersvc').iden)
            self.isin('000.clustersvc', clus.svcs)
            self.nn(clus.cortex.getStormSvc('clustersvc'))

            # a second same-type instance follows the leader as a mirror
            mirror = await clus.addSvc(ClusterSvcCell)
            self.isin('001.clustersvc', clus.svcs)
            self.eq(svc.iden, mirror.iden)

        # getSvcDirn is the predictable per-service dir under the cluster dir, and
        # restart() fini's and re-boots a service from that dir ( same iden )
        async with self.getTestCluster({'cortex': {}, 'clustersvc': {'ctor': ClusterSvcCell}}) as clus:

            self.eq(clus.getSvcDirn('000.clustersvc'), s_common.genpath(clus.dirn, '000.clustersvc'))

            iden = clus.get('clustersvc').iden
            svc = await clus.restart('000.clustersvc')
            self.eq(iden, svc.iden)
            self.true(clus.svcs['000.clustersvc'] is svc)
            self.nn(clus.cortex.getStormSvc('clustersvc'))

            # shutdown() leaves the dir intact for hand manipulation; startup()
            # re-boots it from the same dir with the same iden
            await clus.shutdown('000.clustersvc')
            self.true(clus.svcs['000.clustersvc'].isfini)
            svc = await clus.startup('000.clustersvc')
            self.false(svc.isfini)
            self.eq(iden, svc.iden)

            # restart/shutdown/startup of an unknown service is rejected
            with self.raises(s_exc.BadArg):
                await clus.restart('999.newp')

            with self.raises(s_exc.BadArg):
                await clus.shutdown('999.newp')

            with self.raises(s_exc.BadArg):
                await clus.startup('999.newp')

        # an unknown service type with no ctor override is rejected
        with self.raises(s_exc.BadArg):
            async with self.getTestCluster({'newpservice': {}}) as clus:
                pass  # pragma: no cover

        # an unknown envelope key is rejected -- for a 'cortex'/'axon'/'jsonstor'
        # entry, cluster.getCluster() itself catches this; for any other entry
        # ( added via addSvc() rather than getCluster()'s own envelope
        # validation ) getTestCluster() must reject it itself.
        with self.raises(s_exc.BadArg):
            async with self.getTestCluster({'cortex': {'newp': {}}}) as clus:
                pass  # pragma: no cover

        with self.raises(s_exc.BadArg):
            async with self.getTestCluster({'clustersvc': {'ctor': ClusterSvcCell, 'newp': {}}}) as clus:
                pass  # pragma: no cover

        # AHA is always used and cannot be disabled
        with self.raises(s_exc.BadArg):
            async with self.getTestCluster({'cortex': {}, 'aha': None}) as clus:
                pass  # pragma: no cover

    def test_syntest_helpers(self):
        # Execute all of the test helpers here
        self.len(2, (1, 2))

        self.le(1, 2)
        self.le(1, 1)
        self.lt(1, 2)
        self.ge(2, 1)
        self.ge(1, 1)
        self.gt(2, 1)

        self.isin('foo', ('foo', 'bar'))
        self.isin('foo', 'fooobarr')
        self.isin('foo', {'foo': 'bar'})
        self.isin('foo', {'foo', 'bar'})
        self.isin('foo', ['foo', 'bar'])

        self.notin('baz', ('foo', 'bar'))
        self.notin('baz', 'fooobarr')
        self.notin('baz', {'foo': 'bar'})
        self.notin('baz', {'foo', 'bar'})
        self.notin('baz', ['foo', 'bar'])

        self.isinstance('str', str)
        self.isinstance('str', (str, dict))

        self.sorteq((1, 2, 3), [2, 3, 1])

        def div0():
            return 1 / 0

        self.raises(ZeroDivisionError, div0)

        self.none(None)
        self.none({'foo': 'bar'}.get('baz'))

        self.nn(1)
        self.nn({'foo': 'bar'}.get('baz', 'woah'))

        self.true(True)
        self.true(1)
        self.true(-1)
        self.true('str')

        self.false(False)
        self.false(0)
        self.false('')
        self.false(())
        self.false([])
        self.false({})
        self.false(set())

        self.eq(True, 1)
        self.eq(False, 0)
        self.eq('foo', 'foo')
        self.eq({'1', '2'}, {'2', '1', '2'})
        self.eq({'key': 'val'}, {'key': 'val'})

        self.ne(True, 0)
        self.ne(False, 1)
        self.ne('foo', 'foobar')
        self.ne({'1', '2'}, {'2', '1', '2', '3'})
        self.ne({'key': 'val'}, {'key2': 'val2'})

        self.noprop({'key': 'valu'}, 'foo')

        with self.getTestDir() as fdir:
            self.true(os.path.isdir(fdir))
        self.false(os.path.isdir(fdir))

        # try mirroring an arbitrary direcotry
        with self.getTestDir() as fdir1:
            with s_common.genfile(fdir1, 'hehe.haha') as fd:
                fd.write('hehe'.encode())
            with self.getTestDir(fdir1) as fdir2:
                with s_common.genfile(fdir2, 'hehe.haha') as fd:
                    self.eq(fd.read(), 'hehe'.encode())

        outp = self.getTestOutp()
        self.isinstance(outp, s_output.OutPut)

        with self.raises(unittest.SkipTest) as cm:
            self.skipIfNoPath('newpDoesNotExist', mesg='hehe')
        self.isin('newpDoesNotExist mesg=hehe', str(cm.exception))

    async def test_syntest_logstream_base(self):
        with self.getLoggerStream('synapse.tests.test_utils') as stream:
            logger.error('ruh roh i am a error message')
            await stream.expect('ruh roh i am a error message', timeout=1)

        with self.raises(AssertionError):
            await stream.expect('does not exist', timeout=0.01)

        self.notin('newp', stream.getvalue())

    async def test_syntest_logstream_event(self):

        @s_common.firethread
        def logathing(mesg):
            time.sleep(0.01)
            logger.error(mesg)

        logger.error('notthere')
        with self.getLoggerStream('synapse.tests.test_utils') as stream:
            thr = logathing('Test Message')
            await stream.expect('Test Message', timeout=10)
            thr.join()

        self.notin('notthere', stream.getvalue())

        msgs = stream.jsonlines()
        self.len(1, msgs)
        self.eq(msgs[0]['message'], 'Test Message')

    def test_syntest_envars(self):
        os.environ['foo'] = '1'
        os.environ['bar'] = '2'

        with self.setTstEnvars(foo=1, bar='joke', baz=1234, FOO_THING=1, BAR_THING=0) as cm:
            self.none(cm)
            self.eq(os.environ.get('foo'), '1')
            self.eq(os.environ.get('bar'), 'joke')
            self.eq(os.environ.get('baz'), '1234')

            self.thisEnvMust('FOO_THING', 'baz')
            self.thisEnvMustNot('BAR_THING', 'NEWP_THING')
            with self.raises(unittest.SkipTest):
                self.thisEnvMust('MEWP_THING')
            with self.raises(unittest.SkipTest):
                self.thisEnvMust('BAR_THING')
            with self.raises(unittest.SkipTest):
                self.thisEnvMustNot('FOO_THING')

        self.eq(os.environ.get('foo'), '1')
        self.eq(os.environ.get('bar'), '2')
        self.none(os.environ.get('baz'))

    def test_outp(self):
        outp = s_t_utils.TstOutPut()
        outp.printf('Test message #1!')
        outp.expect('#1')
        self.raises(Exception, outp.expect, 'oh my')

    async def test_testenv(self):

        async with s_t_utils.TstEnv() as env:

            base = await s_base.Base.anit()
            foo = 'foo'
            env.add('foo', foo)
            env.add('base', base, fini=True)

            self.true(env.foo is foo)

            def blah():
                env.blah

            self.raises(AttributeError, blah)

        self.true(base.isfini)

    async def test_cmdg_simple_sequence(self):
        cmdg = s_t_utils.CmdGenerator(['foo', 'bar'])
        self.eq(await cmdg(), 'foo')
        self.eq(await cmdg(), 'bar')
        with self.raises(Exception):
            await cmdg()

    async def test_cmdg_end_exception(self):
        cmdg = s_t_utils.CmdGenerator(['foo', 'bar', EOFError()])
        self.eq(await cmdg(), 'foo')
        self.eq(await cmdg(), 'bar')

        with self.raises(EOFError):
            await cmdg()

        with self.raises(Exception) as cm:
            await cmdg()
            self.assertIn('No further actions', str(cm.exception))

    def test_istufo(self):
        node = (None, {})
        self.istufo(node)
        node = ('1234', {})
        self.istufo(node)

        self.raises(AssertionError, self.istufo, [None, {}])
        self.raises(AssertionError, self.istufo, (None, {}, {}))
        self.raises(AssertionError, self.istufo, (1234, set()))
        self.raises(AssertionError, self.istufo, (None, set()))

    async def test_async(self):

        async def araiser():
            return 1 / 0

        await self.asyncraises(ZeroDivisionError, araiser())

    async def test_storm_msgs(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('[test:str=1234] | count')
            self.stormIsInPrint('Counted 1 nodes.', msgs)

            msgs = await core.stormlist('$lib.warn("test warning message")')
            self.stormIsInWarn('test warning message', msgs)

            msgs = await core.stormlist('[test:str=')
            self.stormIsInErr("Unexpected token 'end of input'", msgs)

            with self.raises(AssertionError):
                self.stormHasNoErr(msgs)

            with self.raises(AssertionError):
                self.stormHasNoWarnErr(msgs)

            msgs = await core.stormlist('test:str')
            self.stormHasNoErr(msgs)

            msgs = await core.stormlist('test:str $lib.warn("oh hi")')
            with self.raises(AssertionError):
                self.stormHasNoWarnErr(msgs)

    def test_utils_certdir(self):
        oldcertdirn = s_certdir.getCertDirn()
        oldcertdir = s_certdir.getCertDir()

        self.eq(1, oldcertdir.pathrefs[oldcertdirn])

        with self.getTestDir() as dirn:
            path = s_common.genpath(dirn, 'haha')

            # Patch the singleton related functionality
            with self.getTestCertDir(path) as certdir:

                # The singleton functionality now refers to the patched objects
                self.eq(1, certdir.pathrefs[path])
                self.true(certdir is s_certdir.getCertDir())
                self.false(oldcertdir is s_certdir.getCertDir())

                self.eq(path, s_certdir.getCertDirn())
                self.ne(oldcertdirn, s_certdir.getCertDirn())

                # Adding / deleting paths does not affect the old singleton
                newpath = s_common.genpath(dirn, 'hehe')
                s_certdir.addCertPath(newpath)
                self.eq(1, certdir.pathrefs[path])
                self.eq(1, certdir.pathrefs[newpath])
                self.eq(1, oldcertdir.pathrefs[oldcertdirn])

                s_certdir.delCertPath(newpath)
                self.eq(1, certdir.pathrefs[path])
                self.eq(None, certdir.pathrefs.get(newpath))
                self.eq(1, oldcertdir.pathrefs[oldcertdirn])

        # Patch is removed and singleton behavior is restored
        self.true(oldcertdir is s_certdir.getCertDir())
        self.eq(oldcertdirn, s_certdir.getCertDirn())

    async def test_checknode(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[test:comp=(1, test)]')
            self.len(1, nodes)
            self.checkNode(nodes[0], (('test:comp', (1, 'test')), {'hehe': 1, 'haha': 'test'}))
            with self.raises(AssertionError):
                self.checkNode(nodes[0], (('test:comp', (1, 'newp')), {'hehe': 1, 'haha': 'test'}))
            with self.raises(AssertionError):
                self.checkNode(nodes[0], (('test:comp', (1, 'test')), {'hehe': 1, 'haha': 'newp'}))
            with self.getLoggerStream('synapse.tests.utils') as stream:
                self.checkNode(nodes[0], (('test:comp', (1, 'test')), {'hehe': 1}))
                await stream.expect('untested properties', timeout=12)

            await self.checkNodes(core, [('test:comp', (1, 'test'))])
            with self.raises(AssertionError):
                await self.checkNodes(core, [('test:comp', (1, 'newp'))])

    async def test_propeq(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ test:str=foo
                    :hehe=haha
                    :tick=2020
                    :seen=2020
                    :polyarry={[inet:fqdn=vertex.link inet:fqdn=foo.com]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'hehe', 'haha')
            self.propeq(nodes[0], 'tick', t0 := 1577836800000000)
            self.propeq(nodes[0], 'tick', '2020-01-01T00:00:00Z', repr=True)
            self.propeq(nodes[0], 'polyarry', ('foo.com', 'vertex.link'))
            self.propeq(nodes[0], 'seen.min', t0)
            self.propeq(nodes[0], '.created', nodes[0].get('.created'))

            with self.raises(AssertionError):
                self.propeq(nodes[0], 'hehe', 'newp')

            with self.raises(AssertionError):
                self.propeq(nodes[0], 'hehe', None)

            self.propeq(nodes[0], 'gprop', None)

            with self.raises(AssertionError):
                self.propeq(nodes[0], 'gprop', 'newp')

            # a comp-valued prop is compared against a bare comp tuple: the
            # stored value's per-field type tags are dropped recursively.
            cnode = (await core.nodes('[ test:haspivcomp=42 :have=(woot, rofl) ]'))[0]
            self.propeq(cnode, 'have', ('woot', 'rofl'))

            # the type= form asserts the stored poly's resolved type and compares
            # the bare inner value.
            pnode = (await core.nodes('[ test:str=poly :poly=5 ]'))[0]
            self.propeq(pnode, 'poly', 5, type='test:int')

    def test_tinfoil_dirn_copy(self):
        tinfoil = s_t_utils._getSyntestTinfoil()
        with self.getTestDir() as dirn:
            dirnsrc = s_common.gendir(dirn, 'src')
            dirndst = s_common.gendir(dirn, 'dst')
            s_common.gendir(dirnsrc, 'subdir0/subdir1')

            ifile0 = s_common.genpath(dirnsrc, 'file0.bin.tinfoil')
            ifile1 = s_common.genpath(dirnsrc, 'subdir1/subdir2/file1.txt.tinfoil')

            guid = s_common.uhex(s_common.guid())
            with s_common.genfile(ifile0) as fd:
                fd.write(tinfoil.enc(guid))
            with s_common.genfile(ifile1) as fd:
                fd.write(tinfoil.enc('beeptxt'.encode()))
            with s_common.genfile(dirnsrc, 'file2.txt') as fd:
                fd.write('beep2'.encode())

            # Ensure copy function works.
            shutil.copytree(dirnsrc, dirndst, dirs_exist_ok=True, copy_function=self._tinFoilCopy)

            with s_common.genfile(dirndst, 'file0.bin') as fd:
                self.eq(fd.read(), guid)
            with s_common.genfile(dirndst, 'subdir1/subdir2/file1.txt') as fd:
                self.eq(fd.read(), b'beeptxt')
            with s_common.genfile(dirndst, 'file2.txt') as fd:
                self.eq(fd.read(), b'beep2')

            # Now decode dirnsrc
            self.none(self.decTinFoilDir(dirnsrc))
            self.nn(os.path.exists(ifile0))
            self.nn(os.path.exists(ifile1))
            with s_common.genfile(dirnsrc, 'file0.bin') as fd:
                self.eq(fd.read(), guid)
            with s_common.genfile(dirnsrc, 'subdir1/subdir2/file1.txt') as fd:
                self.eq(fd.read(), b'beeptxt')
            with s_common.genfile(dirnsrc, 'file2.txt') as fd:
                self.eq(fd.read(), b'beep2')

class ProxyServerTest(s_t_utils.SynTest):
    '''
    Tests for the ConnectProxy / Socks5Proxy test helpers themselves. They are
    only useful if a request really does reach its destination through them, and
    only trustworthy if a refused one really does not, so both are asserted here
    rather than left to the suites which use them.
    '''
    @contextlib.asynccontextmanager
    async def getEchoServer(self):
        '''
        A minimal http origin for a proxied request to land on, yielding its
        port. Hand rolled rather than an aiohttp server, since the proxies under
        test speak raw asyncio streams and this keeps the test at that level.
        '''
        async def handle(reader, writer):

            with contextlib.suppress(Exception):
                await reader.readuntil(b'\r\n\r\n')
                writer.write(b'HTTP/1.1 200 OK\r\nContent-Length: 4\r\n'
                             b'Connection: close\r\n\r\nwoot')
                await writer.drain()

            writer.close()

        server = await asyncio.start_server(handle, '127.0.0.1', 0)
        try:
            async with server:
                yield server.sockets[0].getsockname()[1]

        finally:
            server.close()
            await server.wait_closed()

    async def fetch(self, proxyurl, url):
        connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)
        async with aiohttp.ClientSession(connector=connector) as sess:
            async with sess.get(url) as resp:
                return (resp.status, await resp.text())

    async def test_proxyserver(self):

        async with self.getEchoServer() as port:

            url = f'http://127.0.0.1:{port}/woot'

            for ctor in s_t_utils.PROXIES:
                with self.subTest(scheme=ctor.scheme):

                    # a request reaches the origin through the proxy, which records
                    # the (host, port) it was asked to reach
                    async with await ctor.anit() as proxy:
                        self.isin(f'{proxy.scheme}://127.0.0.1:', proxy.url)

                        (code, text) = await self.fetch(proxy.url, url)

                        self.eq(200, code)
                        self.eq('woot', text)
                        self.eq([('127.0.0.1', port)], proxy.connects)
                        self.eq(0, proxy.refused)

                        # which is what hostport() names, path or no path
                        self.eq(('127.0.0.1', port), proxy.hostport(url))
                        self.eq(('127.0.0.1', port), proxy.hostport(f'http://127.0.0.1:{port}'))

                    # the same with credentials the proxy demands
                    async with await ctor.anit(auth='visi:secret') as proxy:
                        proxyurl = proxy.url.replace('://', '://visi:secret@')

                        (code, text) = await self.fetch(proxyurl, url)

                        self.eq(200, code)
                        self.eq([('127.0.0.1', port)], proxy.connects)
                        self.eq(0, proxy.refused)

                    # the wrong password is refused, and no tunnel is established
                    async with await ctor.anit(auth='visi:secret') as proxy:
                        proxyurl = proxy.url.replace('://', '://visi:newp@')

                        with self.raises(aiohttp_socks.ProxyError):
                            await self.fetch(proxyurl, url)

                        self.eq([], proxy.connects)
                        self.eq(1, proxy.refused)

                    # credentials the proxy never asked for are ignored, and one it
                    # demands but never gets is refused
                    async with await ctor.anit() as proxy:
                        proxyurl = proxy.url.replace('://', '://visi:secret@')
                        with contextlib.suppress(Exception):
                            await self.fetch(proxyurl, url)

                    # an origin which is not listening cannot be tunnelled to, and
                    # the proxy answers the client rather than hanging
                    async with await ctor.anit() as proxy:
                        with self.raises(Exception):
                            await self.fetch(proxy.url, 'http://127.0.0.1:1/woot')

                        self.eq([], proxy.connects)

    async def test_proxyserver_socks5(self):
        '''
        The parts of the SOCKS5 handshake a well behaved client never exercises.
        '''
        async with self.getEchoServer() as port:

            async with await s_t_utils.Socks5Proxy.anit() as proxy:

                (host, sport) = ('127.0.0.1', int(proxy.url.rsplit(':', 1)[1]))

                # a domain name, rather than the ipv4 a socks5:// client sends
                (reader, writer) = await asyncio.open_connection(host, sport)
                writer.write(b'\x05\x01\x00')
                await writer.drain()
                self.eq(b'\x05\x00', await reader.readexactly(2))

                name = b'localhost'
                writer.write(b'\x05\x01\x00\x03' + bytes((len(name),)) + name +
                             port.to_bytes(2, 'big'))
                await writer.drain()

                self.eq(b'\x05\x00\x00\x01', (await reader.readexactly(10))[:4])
                writer.close()

                self.eq([('localhost', port)], proxy.connects)

                # a command which is not CONNECT
                (reader, writer) = await asyncio.open_connection(host, sport)
                writer.write(b'\x05\x01\x00')
                await writer.drain()
                await reader.readexactly(2)

                writer.write(b'\x05\x02\x00\x01' + bytes(4) + port.to_bytes(2, 'big'))
                await writer.drain()

                # 0x07 is "command not supported"
                self.eq(0x07, (await reader.readexactly(10))[1])
                writer.close()

                # a client offering no method the proxy accepts
                (reader, writer) = await asyncio.open_connection(host, sport)
                writer.write(b'\x05\x01\x02')
                await writer.drain()

                self.eq(b'\x05\xff', await reader.readexactly(2))
                writer.close()

                # a greeting which is not socks5 at all, and a truncated one
                for byts in (b'\x04\x01\x00', b'\x05'):
                    (reader, writer) = await asyncio.open_connection(host, sport)
                    writer.write(byts)
                    await writer.drain()
                    writer.close()

                # an ipv6 destination, which nothing is listening on, so the
                # tunnel is refused rather than established
                (reader, writer) = await asyncio.open_connection(host, sport)
                writer.write(b'\x05\x01\x00')
                await writer.drain()
                await reader.readexactly(2)

                writer.write(b'\x05\x01\x00\x04' + bytes(15) + b'\x01' + port.to_bytes(2, 'big'))
                await writer.drain()

                # 0x01 is "general failure"
                self.eq(0x01, (await reader.readexactly(10))[1])
                writer.close()

                # a request truncated after the greeting
                (reader, writer) = await asyncio.open_connection(host, sport)
                writer.write(b'\x05\x01\x00')
                await writer.drain()
                await reader.readexactly(2)

                writer.write(b'\x05\x01')
                await writer.drain()
                writer.close()

                await asyncio.sleep(0)

            # a proxy which demands credentials, offered a truncated auth
            async with await s_t_utils.Socks5Proxy.anit(auth='visi:secret') as proxy:

                sport = int(proxy.url.rsplit(':', 1)[1])

                (reader, writer) = await asyncio.open_connection(host, sport)
                writer.write(b'\x05\x01\x02')
                await writer.drain()
                self.eq(b'\x05\x02', await reader.readexactly(2))

                # half close, so the proxy sees the truncation and refuses. Its
                # own close is then the signal to assert on, rather than a sleep
                writer.write(b'\x01\x04visi')
                await writer.drain()
                writer.write_eof()

                self.eq(b'', await reader.read())
                writer.close()

                self.eq(1, proxy.refused)

    async def test_proxyserver_connect(self):
        '''
        The http proxy's non-CONNECT rejection, which aiohttp_socks never sends.
        '''
        async with await s_t_utils.ConnectProxy.anit() as proxy:

            port = int(proxy.url.rsplit(':', 1)[1])

            (reader, writer) = await asyncio.open_connection('127.0.0.1', port)
            writer.write(b'GET / HTTP/1.1\r\nHost: vertex.link\r\n\r\n')
            await writer.drain()

            self.isin(b'405', await reader.readline())
            writer.close()

            # a request which never completes its headers
            (reader, writer) = await asyncio.open_connection('127.0.0.1', port)
            writer.write(b'CONNECT vertex.link:443 HTTP/1.1\r\n')
            await writer.drain()
            writer.close()

            await asyncio.sleep(0)

        # a proxy which demands credentials, sent a request carrying none
        async with await s_t_utils.ConnectProxy.anit(auth='visi:secret') as proxy:

            port = int(proxy.url.rsplit(':', 1)[1])

            (reader, writer) = await asyncio.open_connection('127.0.0.1', port)
            writer.write(b'CONNECT vertex.link:443 HTTP/1.1\r\nHost: vertex.link\r\n\r\n')
            await writer.drain()

            self.isin(b'407', await reader.readline())
            writer.close()

            self.eq(1, proxy.refused)
