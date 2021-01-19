import contextlib

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.aha as s_aha

import synapse.tests.utils as s_test
import synapse.servers.aha as s_servers_aha

class AhaTest(s_test.SynTest):

    @contextlib.asynccontextmanager
    async def getTestAha(self, conf=None):
        with self.getTestDir() as dirn:
            async with await s_aha.AhaCell.anit(dirn, conf=conf) as aha:
                yield aha

    async def test_lib_aha_mirrors(self):

        urls = ('cell://home0', 'cell://home1')
        conf = {'aha:urls': urls}

        async with self.getTestAha(conf=conf) as aha:
            async with aha.getLocalProxy() as proxy:
                self.eq(urls, await proxy.getAhaUrls())

    async def test_lib_aha(self):

        with self.raises(s_exc.NoSuchName):
            await s_telepath.getAhaProxy({})

        with self.raises(s_exc.NoSuchName):
            await s_telepath.getAhaProxy({'host': 'hehe.haha'})

        urls = ['newp://newp@newp', 'newp://newp@newp']
        client = await s_telepath.addAhaUrl(urls)
        client = await s_telepath.addAhaUrl(urls)

        await s_telepath.delAhaUrl(urls)
        self.len(1, s_telepath.aha_clients)
        await s_telepath.delAhaUrl(urls)
        self.len(0, s_telepath.aha_clients)

        self.eq(0, await s_telepath.delAhaUrl('newp'))

        async with self.getTestAha() as aha:

            cryo0_dirn = s_common.gendir(aha.dirn, 'cryo0')

            host, port = await aha.dmon.listen('tcp://127.0.0.1:0')
            await aha.auth.rootuser.setPasswd('hehehaha')

            wait00 = aha.waiter(1, 'aha:svcadd')
            conf = {
                'aha:name': '0.cryo.mynet',
                'aha:leader': 'cryo.mynet',
                'aha:admin': 'root@cryo.mynet',
                'aha:registry': [f'tcp://root:hehehaha@127.0.0.1:{port}',
                                 f'tcp://root:hehehaha@127.0.0.1:{port}'],
                'dmon:listen': 'tcp://0.0.0.0:0/',
            }
            async with self.getTestCryo(dirn=cryo0_dirn, conf=conf) as cryo:

                await cryo.auth.rootuser.setPasswd('secret')

                ahaadmin = await cryo.auth.getUserByName('root@cryo.mynet')
                self.nn(ahaadmin)
                self.true(ahaadmin.isAdmin())

                await wait00.wait(timeout=2)

                with self.raises(s_exc.NoSuchName):
                    await s_telepath.getAhaProxy({'host': 'hehe.haha'})

                async with await s_telepath.openurl('aha://root:secret@cryo.mynet') as proxy:
                    self.nn(await proxy.getCellIden())

                async with await s_telepath.openurl('aha://root:secret@0.cryo.mynet') as proxy:
                    self.nn(await proxy.getCellIden())

                # force a reconnect...
                proxy = await cryo.ahaclient.proxy(timeout=2)
                await proxy.fini()

                async with await s_telepath.openurl('aha://root:secret@cryo.mynet') as proxy:
                    self.nn(await proxy.getCellIden())

                # force the service into passive mode...
                await cryo.setCellActive(False)

                with self.raises(s_exc.NoSuchName):
                    async with await s_telepath.openurl('aha://root:secret@cryo.mynet') as proxy:
                        pass

                async with await s_telepath.openurl('aha://root:secret@0.cryo.mynet') as proxy:
                    self.nn(await proxy.getCellIden())

                await cryo.setCellActive(True)

                async with await s_telepath.openurl('aha://root:secret@cryo.mynet') as proxy:
                    self.nn(await proxy.getCellIden())

                # some coverage edge cases...
                cryo.conf.pop('aha:leader', None)
                await cryo.setCellActive(False)

                # lock the aha:admin account so we can confirm it is unlocked upon restart
                # remove the admin flag from the account.
                self.false(ahaadmin.isLocked())
                await ahaadmin.setLocked(True, logged=False)
                self.true(ahaadmin.isLocked())
                # remove the admin status so we can confirm its an admin upon restart
                await ahaadmin.setAdmin(False, logged=False)
                self.false(ahaadmin.isAdmin())

            async with self.getTestCryo(dirn=cryo0_dirn, conf=conf) as cryo:
                ahaadmin = await cryo.auth.getUserByName('root@cryo.mynet')
                # And we should be unlocked and admin now
                self.false(ahaadmin.isLocked())
                self.true(ahaadmin.isAdmin())

            wait01 = aha.waiter(1, 'aha:svcadd')
            conf = {
                'aha:name': '0.cryo',
                'aha:leader': 'cryo',
                'aha:network': 'foo',
                'aha:registry': f'tcp://root:hehehaha@127.0.0.1:{port}',
                'dmon:listen': 'tcp://0.0.0.0:0/',
            }
            async with self.getTestCryo(conf=conf) as cryo:

                await cryo.auth.rootuser.setPasswd('secret')

                await wait01.wait(timeout=2)

                async with await s_telepath.openurl('aha://root:secret@cryo.foo') as proxy:
                    self.nn(await proxy.getCellIden())

                async with await s_telepath.openurl('aha://root:secret@0.cryo.foo') as proxy:
                    self.nn(await proxy.getCellIden())
                    await proxy.puts('hehe', ('hehe', 'haha'))

                async with await s_telepath.openurl('aha://root:secret@0.cryo.foo/*/hehe') as proxy:
                    self.nn(await proxy.iden())

                async with await s_telepath.openurl(f'tcp://root:hehehaha@127.0.0.1:{port}') as ahaproxy:
                    svcs = [x async for x in ahaproxy.getAhaSvcs('foo')]
                    self.len(2, svcs)
                    names = [s['name'] for s in svcs]
                    self.sorteq(('cryo.foo', '0.cryo.foo'), names)

                    self.none(await ahaproxy.getCaCert('vertex.link'))
                    cacert0 = await ahaproxy.genCaCert('vertex.link')
                    cacert1 = await ahaproxy.genCaCert('vertex.link')
                    self.nn(cacert0)
                    self.eq(cacert0, cacert1)
                    self.eq(cacert0, await ahaproxy.getCaCert('vertex.link'))

                    csrpem = cryo.certdir.genHostCsr('cryo.vertex.link').decode()

                    hostcert00 = await ahaproxy.signHostCsr(csrpem)
                    hostcert01 = await ahaproxy.signHostCsr(csrpem)

                    self.nn(hostcert00)
                    self.nn(hostcert01)
                    self.ne(hostcert00, hostcert01)

                    csrpem = cryo.certdir.genUserCsr('visi@vertex.link').decode()

                    usercert00 = await ahaproxy.signUserCsr(csrpem)
                    usercert01 = await ahaproxy.signUserCsr(csrpem)

                    self.nn(usercert00)
                    self.nn(usercert01)
                    self.ne(usercert00, usercert01)

            async with await s_telepath.openurl(f'tcp://root:hehehaha@127.0.0.1:{port}') as ahaproxy:
                await ahaproxy.delAhaSvc('cryo', network='foo')
                await ahaproxy.delAhaSvc('0.cryo', network='foo')
                self.none(await ahaproxy.getAhaSvc('cryo.foo'))
                self.none(await ahaproxy.getAhaSvc('0.cryo.foo'))
                self.len(2, [s async for s in ahaproxy.getAhaSvcs()])
