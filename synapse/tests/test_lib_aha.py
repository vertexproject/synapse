from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.aha as s_aha

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_test

realaddsvc = s_aha.AhaCell.addAhaSvc
async def mockaddsvc(self, name, info, network=None):
    if getattr(self, 'testerr', False):
        raise s_exc.SynErr(mesg='newp')
    return await realaddsvc(self, name, info, network=network)

class AhaTest(s_test.SynTest):
    aha_ctor = s_aha.AhaCell.anit

    async def test_lib_aha_mirrors(self):

        with self.getTestDir() as dirn:
            dir0 = s_common.gendir(dirn, 'aha0')
            dir1 = s_common.gendir(dirn, 'aha1')

            conf = {'nexslog:en': True}

            async with self.getTestAha(conf={'nexslog:en': True}, dirn=dir0) as aha0:
                user = await aha0.auth.addUser('reguser', passwd='secret')
                await user.setAdmin(True)

            s_tools_backup.backup(dir0, dir1)

            async with self.getTestAha(conf=conf, dirn=dir0) as aha0:
                upstream_url = aha0.getLocalUrl()

                mirrorconf = {
                    'nexslog:en': True,
                    'mirror': upstream_url,
                }

                async with self.getTestAha(conf=mirrorconf, dirn=dir1) as aha1:
                    # CA is nexus-fied
                    cabyts = await aha0.genCaCert('mirrorca')
                    await aha1.sync()
                    mirbyts = await aha1.genCaCert('mirrorca')
                    self.eq(cabyts, mirbyts)
                    iden = s_common.guid()
                    # Adding, downing, and removing service is also nexusified
                    info = {'urlinfo': {'host': '127.0.0.1', 'port': 8080,
                                        'scheme': 'tcp'},
                            'online': iden}
                    await aha0.addAhaSvc('test', info, network='example.net')
                    await aha1.sync()
                    mnfo = await aha1.getAhaSvc('test.example.net')
                    self.eq(mnfo.get('name'), 'test.example.net')

                    wait00 = aha0.waiter(1, 'aha:svcdown')
                    await aha0.setAhaSvcDown('test', iden, network='example.net')
                    self.len(1, await wait00.wait(timeout=6))
                    await aha1.sync()
                    mnfo = await aha1.getAhaSvc('test.example.net')
                    self.notin('online', mnfo)

                    await aha0.delAhaSvc('test', network='example.net')
                    await aha1.sync()
                    mnfo = await aha1.getAhaSvc('test.example.net')
                    self.none(mnfo)

    async def test_lib_aha_offon(self):
        with self.getTestDir() as dirn:
            cryo0_dirn = s_common.gendir(dirn, 'cryo0')
            conf = {'auth:passwd': 'secret'}
            async with self.getTestAha(conf=conf.copy(), dirn=dirn) as aha:
                host, port = await aha.dmon.listen('tcp://127.0.0.1:0')

                wait00 = aha.waiter(1, 'aha:svcadd')
                cryo_conf = {
                    'aha:name': '0.cryo.mynet',
                    'aha:admin': 'root@cryo.mynet',
                    'aha:registry': f'tcp://root:secret@127.0.0.1:{port}',
                    'dmon:listen': 'tcp://0.0.0.0:0/',
                }
                async with self.getTestCryo(dirn=cryo0_dirn, conf=cryo_conf.copy()) as cryo:
                    self.len(1, await wait00.wait(timeout=6))

                    svc = await aha.getAhaSvc('0.cryo.mynet')
                    linkiden = svc.get('svcinfo', {}).get('online')
                    self.nn(linkiden)

                    # Tear down the Aha cell.
                    await aha.__aexit__(None, None, None)

            async with self.getTestAha(conf=conf.copy(), dirn=dirn) as aha:
                wait01 = aha.waiter(1, 'aha:svcdown')
                await wait01.wait(timeout=6)
                svc = await aha.getAhaSvc('0.cryo.mynet')
                self.notin('online', svc.get('svcinfo'))

                # Try setting something down a second time
                await aha.setAhaSvcDown('0.cryo.mynet', linkiden, network=None)
                svc = await aha.getAhaSvc('0.cryo.mynet')
                self.notin('online', svc.get('svcinfo'))

    async def test_lib_aha(self):

        with self.raises(s_exc.NoSuchName):
            await s_telepath.getAhaProxy({})

        with self.raises(s_exc.NoSuchName):
            await s_telepath.getAhaProxy({'host': 'hehe.haha'})

        # We do inprocess reference counting for urls and clients.
        urls = ['newp://newp@newp', 'newp://newp@newp']
        info = await s_telepath.addAhaUrl(urls)
        self.eq(info.get('refs'), 1)
        # There is not yet a telepath client which is using these urls.
        self.none(info.get('client'))
        info = await s_telepath.addAhaUrl(urls)
        self.eq(info.get('refs'), 2)

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

                with self.raises(s_exc.BadArg):
                    info = {'urlinfo': {'host': '127.0.0.1', 'port': 8080, 'scheme': 'tcp'}}
                    await ahaproxy.addAhaSvc('newp', info, network=None)

        # The aha service can also be configured with a set of URLs that could represent itself.
        urls = ('cell://home0', 'cell://home1')
        conf = {'aha:urls': urls}
        async with self.getTestAha(conf=conf) as aha:
            async with aha.getLocalProxy() as ahaproxy:
                aurls = await ahaproxy.getAhaUrls()
                self.eq(urls, aurls)

    async def test_lib_aha_loadenv(self):

        with self.getTestDir() as dirn:

            async with self.getTestAha() as aha:
                host, port = await aha.dmon.listen('tcp://127.0.0.1:0')
                await aha.auth.rootuser.setPasswd('hehehaha')

                conf = {
                    'version': 1,
                    'aha:servers': [
                        f'tcp://root:hehehaha@127.0.0.1:{port}/',
                    ],
                }

                path = s_common.genpath(dirn, 'telepath.yaml')
                s_common.yamlsave(conf, path)

                fini = await s_telepath.loadTeleEnv(path)

                # Should be one uninitialized aha client
                self.len(1, s_telepath.aha_clients)
                [info] = s_telepath.aha_clients.values()
                self.none(info.get('client'))

                with self.raises(s_exc.NoSuchName):
                    await s_telepath.openurl('aha://visi@foo.bar.com')

                # Connecting to an aha url should have initialized the client
                self.len(1, s_telepath.aha_clients)
                self.nn(info.get('client'))
                await fini()

    async def test_lib_aha_finid_cell(self):

        with self.getTestDir() as dirn:
            async with await self.aha_ctor(dirn) as aha:

                cryo0_dirn = s_common.gendir(aha.dirn, 'cryo0')

                host, port = await aha.dmon.listen('tcp://127.0.0.1:0')
                await aha.auth.rootuser.setPasswd('hehehaha')

                wait00 = aha.waiter(1, 'aha:svcadd')
                conf = {
                    'aha:name': '0.cryo.mynet',
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

                    async with await s_telepath.openurl('aha://root:secret@0.cryo.mynet') as proxy:
                        self.nn(await proxy.getCellIden())

                    await aha.fini()

                    with self.raises(s_exc.IsFini):

                        async with await s_telepath.openurl('aha://root:secret@0.cryo.mynet') as proxy:
                            self.fail('Should never reach a connection.')

    async def test_lib_aha_onlink_fail(self):

        with self.getTestDir() as dirn:

            with mock.patch('synapse.lib.aha.AhaCell.addAhaSvc', mockaddsvc):

                async with await self.aha_ctor(dirn) as aha:

                    cryo0_dirn = s_common.gendir(aha.dirn, 'cryo0')

                    host, port = await aha.dmon.listen('tcp://127.0.0.1:0')
                    await aha.auth.rootuser.setPasswd('secret')

                    aha.testerr = True

                    wait00 = aha.waiter(1, 'aha:svcadd')
                    conf = {
                        'aha:name': '0.cryo.mynet',
                        'aha:admin': 'root@cryo.mynet',
                        'aha:registry': f'tcp://root:secret@127.0.0.1:{port}',
                        'dmon:listen': 'tcp://0.0.0.0:0/',
                    }
                    async with self.getTestCryo(dirn=cryo0_dirn, conf=conf) as cryo:

                        await cryo.auth.rootuser.setPasswd('secret')

                        self.none(await wait00.wait(timeout=2))

                        svc = await aha.getAhaSvc('0.cryo.mynet')
                        self.none(svc)

                        wait01 = aha.waiter(1, 'aha:svcadd')
                        aha.testerr = False

                        self.nn(await wait01.wait(timeout=2))

                        svc = await aha.getAhaSvc('0.cryo.mynet')
                        self.nn(svc)
                        self.nn(svc.get('svcinfo', {}).get('online'))

                        async with await s_telepath.openurl('aha://root:secret@0.cryo.mynet') as proxy:
                            self.nn(await proxy.getCellIden())
