import os
import http
import asyncio

from unittest import mock

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.aha as s_aha
import synapse.lib.base as s_base
import synapse.lib.cell as s_cell

import synapse.tools.aha.list as s_a_list

import synapse.tools.aha.enroll as s_tools_enroll
import synapse.tools.aha.provision.user as s_tools_provision_user
import synapse.tools.aha.provision.service as s_tools_provision_service

import synapse.tests.utils as s_test

realaddsvc = s_aha.AhaCell.addAhaSvc
async def mockaddsvc(self, name, info, network=None):
    if getattr(self, 'testerr', False):
        raise s_exc.SynErr(mesg='newp')
    return await realaddsvc(self, name, info, network=network)

class ExecTeleCallerApi(s_cell.CellApi):
    async def exectelecall(self, url, meth, *args, **kwargs):
        return await self.cell.exectelecall(url, meth, *args, **kwargs)

class ExecTeleCaller(s_cell.Cell):
    cellapi = ExecTeleCallerApi

    async def exectelecall(self, url, meth, *args, **kwargs):

        async with await s_telepath.openurl(url) as prox:
            meth = getattr(prox, meth)
            resp = await meth(*args, **kwargs)
            return resp

class AhaTest(s_test.SynTest):

    async def test_lib_aha_clone(self):

        zoinks = 'zoinks.aha.loop.vertex.link'

        with self.getTestDir() as dirn:

            dir0 = s_common.gendir(dirn, 'aha0')
            dir1 = s_common.gendir(dirn, 'aha1')

            async with self.getTestAha(dirn=dir0) as aha0:

                ahacount = len(await aha0.getAhaUrls())
                async with aha0.getLocalProxy() as proxy0:
                    self.len(ahacount, await proxy0.getAhaUrls())
                    self.len(ahacount, await proxy0.getAhaServers())

                    purl = await proxy0.addAhaClone(zoinks, port=0)

                conf1 = {'clone': purl}
                async with self.getTestAha(conf=conf1, dirn=dir1) as aha1:

                    await aha1.sync()

                    self.eq(aha0.iden, aha1.iden)
                    self.nn(aha1.conf.get('mirror'))

                    serv0 = await aha0.getAhaServers()
                    serv1 = await aha1.getAhaServers()

                    self.len(ahacount + 1, serv0)
                    self.eq(serv0, serv1)

                    # ensure some basic functionality is being properly mirrored

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

                    async with aha0.waiter(1, 'aha:svcdown', timeout=6):
                        await aha0.setAhaSvcDown('test', iden, network='example.net')

                    await aha1.sync()

                    mnfo = await aha1.getAhaSvc('test.example.net')
                    self.notin('online', mnfo)

                    await aha0.delAhaSvc('test', network='example.net')
                    await aha1.sync()

                    mnfo = await aha1.getAhaSvc('test.example.net')
                    self.none(mnfo)

                    self.true(aha0.isactive)
                    self.false(aha1.isactive)

                    async with aha1.getLocalProxy() as proxy:
                        await proxy.promote(graceful=True)

                    self.false(aha0.isactive)
                    self.true(aha1.isactive)

            # Remove 00.aha.loop.vertex.link since we're done with him + coverage
            async with self.getTestAha(conf={'dns:name': zoinks}, dirn=dir1) as aha1:
                async with aha1.getLocalProxy() as proxy1:
                    srvs = await proxy1.getAhaServers()
                    self.len(2, srvs)
                    aha00 = [info for info in srvs if info.get('host') == '00.aha.loop.vertex.link'][0]
                    data = await proxy1.delAhaServer(aha00.get('host'), aha00.get('port'))
                    self.eq(data.get('host'), aha00.get('host'))
                    self.eq(data.get('port'), aha00.get('port'))

                    srvs = await proxy1.getAhaServers()
                    self.len(1, srvs)
                    urls = await proxy1.getAhaUrls()
                    self.len(1, urls)

    async def test_lib_aha_offon(self):
        with self.getTestDir() as dirn:
            cryo0_dirn = s_common.gendir(dirn, 'cryo0')
            async with self.getTestAha(dirn=dirn) as aha:

                replaymult = 1
                if s_common.envbool('SYNDEV_NEXUS_REPLAY'):
                    replaymult = 2

                purl = await aha.addAhaSvcProv('0.cryo')

                wait00 = aha.waiter(1 * replaymult, 'aha:svcadd')

                conf = {'aha:provision': purl}
                async with self.getTestCryo(dirn=cryo0_dirn, conf=conf) as cryo:
                    self.len(1 * replaymult, await wait00.wait(timeout=6))

                    svc = await aha.getAhaSvc('0.cryo...')
                    linkiden = svc.get('svcinfo', {}).get('online')

                    # Tear down the Aha cell.
                    await aha.__aexit__(None, None, None)

            with self.getAsyncLoggerStream('synapse.lib.aha', f'Set [0.cryo.synapse] offline.') as stream:
                async with self.getTestAha(dirn=dirn) as aha:
                    self.true(await asyncio.wait_for(stream.wait(), timeout=12))
                    svc = await aha.getAhaSvc('0.cryo...')
                    self.notin('online', svc.get('svcinfo'))

                    # Try setting something down a second time
                    await aha.setAhaSvcDown('0.cryo', linkiden, network='synapse')
                    svc = await aha.getAhaSvc('0.cryo...')
                    self.notin('online', svc.get('svcinfo'))

    async def test_lib_aha_basics(self):

        with self.raises(s_exc.NoSuchName):
            await s_telepath.getAhaProxy({})

        with self.raises(s_exc.NotReady):
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

            ahaurls = await aha.getAhaUrls()

            wait00 = aha.waiter(1, 'aha:svcadd')

            replaymult = 1
            if s_common.envbool('SYNDEV_NEXUS_REPLAY'):
                replaymult = 2

            conf = {'aha:provision': await aha.addAhaSvcProv('0.cryo')}
            async with self.getTestCryo(dirn=cryo0_dirn, conf=conf) as cryo:

                await wait00.wait(timeout=2)

                with self.raises(s_exc.NoSuchName):
                    await s_telepath.getAhaProxy({'host': 'hehe.haha'})

                async with await s_telepath.openurl('aha://cryo...') as proxy:
                    self.nn(await proxy.getCellIden())

                with self.raises(s_exc.BadArg):
                    _proxy = await cryo.ahaclient.proxy(timeout=2)
                    await _proxy.modAhaSvcInfo('cryo...', {'newp': 'newp'})

                async with await s_telepath.openurl('aha://0.cryo...') as proxy:
                    self.nn(await proxy.getCellIden())

                # force a reconnect...
                proxy = await cryo.ahaclient.proxy(timeout=2)
                async with aha.waiter(2 * replaymult, 'aha:svcadd'):
                    await proxy.fini()

                async with await s_telepath.openurl('aha://cryo...') as proxy:
                    self.nn(await proxy.getCellIden())

                # force the service into passive mode...
                async with aha.waiter(3 * replaymult, 'aha:svcdown', 'aha:svcadd', timeout=6):
                    await cryo.setCellActive(False)

                with self.raises(s_exc.NoSuchName):
                    async with await s_telepath.openurl('aha://cryo...') as proxy:
                        pass

                async with await s_telepath.openurl('aha://0.cryo...') as proxy:
                    self.nn(await proxy.getCellIden())

                async with aha.waiter(1 * replaymult, 'aha:svcadd', timeout=6):
                    await cryo.setCellActive(True)

                async with await s_telepath.openurl('aha://cryo...') as proxy:
                    self.nn(await proxy.getCellIden())

            wait01 = aha.waiter(2 * replaymult, 'aha:svcadd')

            conf = {'aha:provision': await aha.addAhaSvcProv('0.cryo')}
            async with self.getTestCryo(conf=conf) as cryo:

                info = await cryo.getCellInfo()

                self.eq(info['cell']['aha'], {'name': '0.cryo', 'leader': 'cryo', 'network': 'synapse'})

                await wait01.wait(timeout=2)

                async with await s_telepath.openurl('aha://cryo.synapse') as proxy:
                    self.nn(await proxy.getCellIden())

                async with await s_telepath.openurl('aha://0.cryo.synapse') as proxy:
                    self.nn(await proxy.getCellIden())
                    await proxy.puts('hehe', ('hehe', 'haha'))

                async with await s_telepath.openurl('aha://0.cryo.synapse/*/hehe') as proxy:
                    self.nn(await proxy.iden())

                async with aha.getLocalProxy() as ahaproxy:

                    svcs = [x async for x in ahaproxy.getAhaSvcs('synapse')]
                    self.len(2, svcs)
                    names = [s['name'] for s in svcs]
                    self.sorteq(('cryo.synapse', '0.cryo.synapse'), names)

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

            # We can use HTTP API to get the registered services
            await aha.addUser('lowuser', passwd='lowuser')
            await aha.auth.rootuser.setPasswd('secret')

            host, httpsport = await aha.addHttpsPort(0)
            svcsurl = f'https://localhost:{httpsport}/api/v1/aha/services'

            async with self.getHttpSess(auth=('root', 'secret'), port=httpsport) as sess:
                async with sess.get(svcsurl) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    info = await resp.json()
                    self.eq(info.get('status'), 'ok')
                    result = info.get('result')
                    self.len(2, result)
                    self.eq({'0.cryo.synapse', 'cryo.synapse'},
                            {svcinfo.get('name') for svcinfo in result})

                async with sess.get(svcsurl, json={'network': 'synapse'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    info = await resp.json()
                    self.eq(info.get('status'), 'ok')
                    result = info.get('result')
                    self.len(2, result)
                    self.eq({'0.cryo.synapse', 'cryo.synapse'},
                            {svcinfo.get('name') for svcinfo in result})

                async with sess.get(svcsurl, json={'network': 'newp'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    info = await resp.json()
                    self.eq(info.get('status'), 'ok')
                    result = info.get('result')
                    self.len(0, result)

                # Sad path
                async with sess.get(svcsurl, json={'newp': 'hehe'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')

                async with sess.get(svcsurl, json={'network': 'mynet', 'newp': 'hehe'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')

            # Sad path
            async with self.getHttpSess(auth=('lowuser', 'lowuser'), port=httpsport) as sess:
                async with sess.get(svcsurl) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'AuthDeny')

            async with aha.getLocalProxy() as ahaproxy:
                await ahaproxy.delAhaSvc('cryo', network='synapse')
                await ahaproxy.delAhaSvc('0.cryo', network='synapse')
                self.none(await ahaproxy.getAhaSvc('cryo.synapse'))
                self.none(await ahaproxy.getAhaSvc('0.cryo.synapse'))
                self.len(0, [s async for s in ahaproxy.getAhaSvcs()])

                with self.raises(s_exc.BadArg):
                    info = {'urlinfo': {'host': '127.0.0.1', 'port': 8080, 'scheme': 'tcp'}}
                    await ahaproxy.addAhaSvc('newp', info, network=None)

            # test that services get updated aha server list
            with self.getTestDir() as dirn:

                conf = {'aha:provision': await aha.addAhaSvcProv('00.cell')}

                # can't assume just one due to enterprise tests with raft...
                ahacount = len(await aha.getAhaUrls())

                async with self.getTestCell(s_cell.Cell, conf=conf, dirn=dirn) as cell:
                    self.len(ahacount, cell.conf.get('aha:registry'))

                await aha.addAhaServer({'host': 'zoinks.aha.loop.vertex.link'})

                self.len(ahacount + 1, await aha.getAhaServers())

                async with self.getTestCell(s_cell.Cell, conf=conf, dirn=dirn) as cell:
                    await cell.ahaclient.proxy()
                    self.len(ahacount + 1, cell.conf.get('aha:registry'))

                self.nn(await aha.delAhaServer('zoinks.aha.loop.vertex.link', 27492))
                self.len(ahacount, await aha.getAhaServers())

                async with self.getTestCell(s_cell.Cell, conf=conf, dirn=dirn) as cell:
                    await cell.ahaclient.proxy()
                    self.len(ahacount, cell.conf.get('aha:registry'))

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

                # No clients have been loaded yet.
                with self.raises(s_exc.NotReady) as cm:
                    await s_telepath.openurl('aha://visi@foo.bar.com')
                self.eq(cm.exception.get('mesg'),
                        'No aha servers registered to lookup foo.bar.com')

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

        async with self.getTestAha() as aha:

            wait00 = aha.waiter(1, 'aha:svcadd')
            conf = {'aha:provision': await aha.addAhaSvcProv('0.cryo')}

            async with self.getTestCryo(conf=conf) as cryo:

                self.true(await wait00.wait(timeout=2))

                async with await s_telepath.openurl('aha://0.cryo...') as proxy:
                    self.nn(await proxy.getCellIden())

                proxy = await cryo.ahaclient.proxy()

                # avoid race to notify client...
                async with cryo.ahaclient.waiter(1, 'tele:client:linkloop', timeout=2):
                    await aha.fini()
                    self.true(await proxy.waitfini(timeout=10))

                with self.raises(asyncio.TimeoutError):
                    await cryo.ahaclient.proxy(timeout=0.1)

    async def test_lib_aha_onlink_fail(self):

        with mock.patch('synapse.lib.aha.AhaCell.addAhaSvc', mockaddsvc):

            async with self.getTestAha() as aha:

                replaymult = 1
                if s_common.envbool('SYNDEV_NEXUS_REPLAY'):
                    replaymult = 2

                aha.testerr = True
                wait00 = aha.waiter(1, 'aha:svcadd')

                conf = {'aha:provision': await aha.addAhaSvcProv('0.cryo')}
                async with self.getTestCryo(conf=conf) as cryo:

                    self.none(await wait00.wait(timeout=2))

                    svc = await aha.getAhaSvc('0.cryo...')
                    self.none(svc)

                    wait01 = aha.waiter(1 * replaymult, 'aha:svcadd')
                    aha.testerr = False

                    self.nn(await wait01.wait(timeout=2))

                    svc = await aha.getAhaSvc('0.cryo...')
                    self.nn(svc)
                    self.nn(svc.get('svcinfo', {}).get('online'))

                    async with await s_telepath.openurl('aha://0.cryo...') as proxy:
                        self.nn(await proxy.getCellIden())

    async def test_lib_aha_bootstrap(self):

        with self.getTestDir() as dirn:
            certdirn = s_common.gendir('certdir')
            with self.getTestCertDir(certdirn):

                conf = {
                    'aha:name': 'aha',
                    'aha:admin': 'root@do.vertex.link',
                    'aha:network': 'do.vertex.link',
                }

                async with self.getTestAha(dirn=dirn, conf=conf) as aha:
                    self.true(os.path.isfile(os.path.join(aha.dirn, 'certs', 'cas', 'do.vertex.link.crt')))
                    self.true(os.path.isfile(os.path.join(aha.dirn, 'certs', 'cas', 'do.vertex.link.key')))
                    self.true(os.path.isfile(os.path.join(aha.dirn, 'certs', 'hosts', 'aha.do.vertex.link.crt')))
                    self.true(os.path.isfile(os.path.join(aha.dirn, 'certs', 'hosts', 'aha.do.vertex.link.key')))
                    self.true(os.path.isfile(os.path.join(aha.dirn, 'certs', 'users', 'root@do.vertex.link.crt')))
                    self.true(os.path.isfile(os.path.join(aha.dirn, 'certs', 'users', 'root@do.vertex.link.key')))

                    host, port = await aha.dmon.listen('ssl://127.0.0.1:0?hostname=aha.do.vertex.link&ca=do.vertex.link')

                    async with await s_telepath.openurl(f'ssl://root@127.0.0.1:{port}?hostname=aha.do.vertex.link') as proxy:
                        await proxy.getCellInfo()

    async def test_lib_aha_noconf(self):

        conf = {'dns:name': None}
        async with self.getTestAha(conf=conf) as aha:

            with self.raises(s_exc.NeedConfValu):
                await aha.addAhaSvcProv('hehe')

            aha.conf['aha:urls'] = 'tcp://127.0.0.1:0/'

            with self.raises(s_exc.NeedConfValu):
                await aha.addAhaSvcProv('hehe')

            with self.raises(s_exc.NeedConfValu):
                await aha.addAhaUserEnroll('hehe')

            with self.raises(s_exc.NeedConfValu):
                await aha.addAhaUserEnroll('hehe')

    async def test_lib_aha_provision(self):

        with self.getTestDir() as dirn:

            conf = {'dns:name': 'aha.loop.vertex.link'}
            async with self.getTestAha(dirn=dirn, conf=conf) as aha:

                ahaport = aha.sockaddr[1]

                url = aha.getLocalUrl()

                outp = self.getTestOutp()
                await s_tools_provision_service.main(('--url', aha.getLocalUrl(), 'foobar'), outp=outp)
                self.isin('one-time use URL: ', str(outp))

                provurl = str(outp).split(':', 1)[1].strip()

                async with await s_telepath.openurl(provurl) as prov:
                    provinfo = await prov.getProvInfo()
                    self.isinstance(provinfo, dict)
                    conf = provinfo.get('conf')
                    # Default https port is not set; dmon is port 0
                    self.notin('https:port', conf)
                    dmon_listen = conf.get('dmon:listen')
                    parts = s_telepath.chopurl(dmon_listen)
                    self.eq(parts.get('port'), 0)
                    self.nn(await prov.getCaCert())

                with self.raises(s_exc.NoSuchName):
                    await s_telepath.openurl(provurl)

                async with aha.getLocalProxy() as proxy:
                    onebork = await proxy.addAhaSvcProv('bork')
                    await proxy.delAhaSvcProv(onebork)

                    onenewp = await proxy.addAhaSvcProv('newp')
                    async with await s_telepath.openurl(onenewp) as provproxy:

                        byts = aha.certdir.genHostCsr('lalala')
                        with self.raises(s_exc.BadArg):
                            await provproxy.signHostCsr(byts)

                        byts = aha.certdir.genUserCsr('lalala')
                        with self.raises(s_exc.BadArg):
                            await provproxy.signUserCsr(byts)

                    onebork = await proxy.addAhaUserEnroll('bork00')
                    await proxy.delAhaUserEnroll(onebork)

                    onebork = await proxy.addAhaUserEnroll('bork01')
                    async with await s_telepath.openurl(onebork) as provproxy:

                        byts = aha.certdir.genUserCsr('zipzop')
                        with self.raises(s_exc.BadArg):
                            await provproxy.signUserCsr(byts)

                onetime = await aha.addAhaSvcProv('00.axon')

                axonpath = s_common.gendir(dirn, 'axon')
                axonconf = {
                    'aha:provision': onetime,
                }
                s_common.yamlsave(axonconf, axonpath, 'cell.yaml')

                argv = (axonpath, '--auth-passwd', 'rootbeer', '--https', '0')
                async with await s_axon.Axon.initFromArgv(argv) as axon:

                    # opts were copied through successfully
                    self.true(await axon.auth.rootuser.tryPasswd('rootbeer'))

                    # test that nobody set aha:admin
                    self.none(await axon.auth.getUserByName('root@loop.vertex.link'))
                    self.none(await axon.auth.getUserByName('axon@loop.vertex.link'))

                    self.true(os.path.isfile(s_common.genpath(axon.dirn, 'prov.done')))
                    self.true(os.path.isfile(s_common.genpath(axon.dirn, 'certs', 'cas', 'synapse.crt')))
                    self.true(os.path.isfile(s_common.genpath(axon.dirn, 'certs', 'hosts', '00.axon.synapse.crt')))
                    self.true(os.path.isfile(s_common.genpath(axon.dirn, 'certs', 'hosts', '00.axon.synapse.key')))
                    self.true(os.path.isfile(s_common.genpath(axon.dirn, 'certs', 'users', 'root@synapse.crt')))
                    self.true(os.path.isfile(s_common.genpath(axon.dirn, 'certs', 'users', 'root@synapse.key')))

                    yamlconf = s_common.yamlload(axon.dirn, 'cell.yaml')
                    self.eq('axon', yamlconf.get('aha:leader'))
                    self.eq('00.axon', yamlconf.get('aha:name'))
                    self.eq('synapse', yamlconf.get('aha:network'))
                    self.none(yamlconf.get('aha:admin'))

                    self.eq(await aha.getAhaUrls(), yamlconf.get('aha:registry'))
                    self.eq(f'ssl://0.0.0.0:0?hostname=00.axon.synapse&ca=synapse', yamlconf.get('dmon:listen'))

                    unfo = await axon.addUser('visi')

                    outp = self.getTestOutp()
                    await s_tools_provision_user.main(('--url', aha.getLocalUrl(), 'visi'), outp=outp)
                    self.isin('one-time use URL:', str(outp))

                    provurl = str(outp).split(':', 1)[1].strip()
                    with self.getTestSynDir() as syndir:

                        capath = s_common.genpath(syndir, 'certs', 'cas', 'synapse.crt')
                        crtpath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.crt')
                        keypath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.key')

                        for path in (capath, crtpath, keypath):
                            s_common.genfile(path)

                        outp = self.getTestOutp()
                        await s_tools_enroll.main((provurl,), outp=outp)

                        for path in (capath, crtpath, keypath):
                            self.gt(os.path.getsize(path), 0)

                        teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                        self.eq(teleyaml.get('version'), 1)
                        self.sorteq(teleyaml.get('aha:servers'), await aha.getAhaUrls(user='visi'))

                        certdir = s_telepath.s_certdir.CertDir(os.path.join(syndir, 'certs'))
                        async with await s_telepath.openurl('aha://visi@axon...', certdir=certdir) as prox:
                            self.eq(axon.iden, await prox.getCellIden())

                        # Lock the user
                        await axon.setUserLocked(unfo.get('iden'), True)

                        with self.raises(s_exc.AuthDeny) as cm:
                            async with await s_telepath.openurl('aha://visi@axon...', certdir=certdir) as prox:
                                self.eq(axon.iden, await prox.getCellIden())
                        self.isin('locked', cm.exception.get('mesg'))

                    outp = self.getTestOutp()
                    await s_tools_provision_user.main(('--url', aha.getLocalUrl(), 'visi'), outp=outp)
                    self.isin('Need --again', str(outp))

                    outp = self.getTestOutp()
                    await s_tools_provision_user.main(('--url', aha.getLocalUrl(), '--again', 'visi'), outp=outp)
                    self.isin('one-time use URL:', str(outp))

                onetime = await aha.addAhaSvcProv('00.axon')
                axonconf = {
                    'https:port': None,
                    'aha:provision': onetime,
                }
                s_common.yamlsave(axonconf, axonpath, 'cell.yaml')

                # Populate data in the overrides file that will be removed from the
                # provisioning data
                overconf = {
                    'dmon:listen': 'tcp://0.0.0.0:0',  # This is removed
                    'nexslog:async': True,  # just set as a demonstrative value
                }
                s_common.yamlsave(overconf, axonpath, 'cell.mods.yaml')

                # force a re-provision... (because the providen is different)
                with self.getAsyncLoggerStream('synapse.lib.cell',
                                               'Provisioning axon from AHA service') as stream:
                    async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:
                        self.true(await stream.wait(6))
                        self.ne(axon.conf.get('dmon:listen'),
                                'tcp://0.0.0.0:0')
                overconf2 = s_common.yamlload(axonpath, 'cell.mods.yaml')
                self.eq(overconf2, {'nexslog:async': True})

                # tests startup logic that recognizes it's already done
                with self.getAsyncLoggerStream('synapse.lib.cell', ) as stream:
                    async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:
                        pass
                    stream.seek(0)
                    self.notin('Provisioning axon from AHA service', stream.read())

                async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:
                    # testing second run...
                    pass

                # With one axon up, we can provision a mirror of him.
                axn2path = s_common.genpath(dirn, 'axon2')

                argv = ['--url', aha.getLocalUrl(), '01.axon', '--mirror', 'axon', '--only-url']
                outp = self.getTestOutp()
                retn = await s_tools_provision_service.main(argv, outp=outp)
                self.eq(0, retn)
                provurl = str(outp).strip()
                self.notin('one-time use URL: ', provurl)
                self.isin('ssl://', provurl)
                urlinfo = s_telepath.chopurl(provurl)
                providen = urlinfo.get('path').strip('/')

                async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:
                    with s_common.genfile(axonpath, 'prov.done') as fd:
                        axonproviden = fd.read().decode().strip()
                    self.ne(axonproviden, providen)

                    # Punch the provisioning URL in like a environment variable
                    with self.setTstEnvars(SYN_AXON_AHA_PROVISION=provurl):

                        async with await s_axon.Axon.initFromArgv((axn2path,)) as axon2:
                            await axon2.sync()
                            self.true(axon.isactive)
                            self.false(axon2.isactive)
                            self.eq('aha://root@axon...', axon2.conf.get('mirror'))

                            with s_common.genfile(axn2path, 'prov.done') as fd:
                                axon2providen = fd.read().decode().strip()
                            self.eq(providen, axon2providen)

                        # Turn the mirror back on with the provisioning url in the config
                        async with await s_axon.Axon.initFromArgv((axn2path,)) as axon2:
                            await axon2.sync()
                            self.true(axon.isactive)
                            self.false(axon2.isactive)
                            self.eq('aha://root@axon...', axon2.conf.get('mirror'))

                # Provision a mirror using aha:provision in the mirror cell.yaml as well.
                # This is similar to the previous test block.
                axn3path = s_common.genpath(dirn, 'axon3')

                argv = ['--url', aha.getLocalUrl(), '02.axon', '--mirror', 'axon']
                outp = self.getTestOutp()
                await s_tools_provision_service.main(argv, outp=outp)
                self.isin('one-time use URL: ', str(outp))
                provurl = str(outp).split(':', 1)[1].strip()
                urlinfo = s_telepath.chopurl(provurl)
                providen = urlinfo.get('path').strip('/')

                async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:

                    with s_common.genfile(axonpath, 'prov.done') as fd:
                        axonproviden = fd.read().decode().strip()
                    self.ne(axonproviden, providen)

                    axon2conf = {
                        'aha:provision': provurl,
                    }
                    s_common.yamlsave(axon2conf, axn3path, 'cell.yaml')
                    async with await s_axon.Axon.initFromArgv((axn3path,)) as axon03:
                        await axon03.sync()
                        self.true(axon.isactive)
                        self.false(axon03.isactive)
                        self.eq('aha://root@axon...', axon03.conf.get('mirror'))

                        with s_common.genfile(axn3path, 'prov.done') as fd:
                            axon3providen = fd.read().decode().strip()
                        self.eq(providen, axon3providen)

                    # Ensure that the aha:provision value was popped from the cell.yaml file,
                    # since that would have mismatched what was used to provision the mirror.
                    copied_conf = s_common.yamlload(axn3path, 'cell.yaml')
                    self.notin('aha:provision', copied_conf)

                    # Turn the mirror back on with the provisioning url removed from the config
                    async with await s_axon.Axon.initFromArgv((axn3path,)) as axon3:
                        await axon3.sync()
                        self.true(axon.isactive)
                        self.false(axon3.isactive)
                        self.eq('aha://root@axon...', axon03.conf.get('mirror'))

                        retn, outp = await self.execToolMain(s_a_list._main, [aha.getLocalUrl()])
                        self.eq(retn, 0)
                        outp.expect('Service              network                        leader')
                        outp.expect('00.axon              synapse                        True')
                        outp.expect('01.axon              synapse                        False')
                        outp.expect('02.axon              synapse                        False')
                        outp.expect('axon                 synapse                        True')

                # Ensure we can provision a service on a given listening ports
                outp.clear()
                args = ('--url', aha.getLocalUrl(), 'bazfaz', '--dmon-port', '123456')
                ret = await s_tools_provision_service.main(args, outp=outp)
                self.eq(1, ret)
                outp.expect('ERROR: Invalid dmon port: 123456')

                outp.clear()
                args = ('--url', aha.getLocalUrl(), 'bazfaz', '--https-port', '123456')
                ret = await s_tools_provision_service.main(args, outp=outp)
                outp.expect('ERROR: Invalid HTTPS port: 123456')
                self.eq(1, ret)

                outp = self.getTestOutp()
                argv = ('--url', aha.getLocalUrl(), 'bazfaz', '--dmon-port', '1234', '--https-port', '443')
                await s_tools_provision_service.main(argv, outp=outp)
                self.isin('one-time use URL: ', str(outp))
                provurl = str(outp).split(':', 1)[1].strip()
                async with await s_telepath.openurl(provurl) as proxy:
                    provconf = await proxy.getProvInfo()
                    conf = provconf.get('conf')
                    dmon_listen = conf.get('dmon:listen')
                    parts = s_telepath.chopurl(dmon_listen)
                    self.eq(parts.get('port'), 1234)
                    https_port = conf.get('https:port')
                    self.eq(https_port, 443)

                # We can generate urls and then drop them en-mass. They will not usable.
                provurls = []
                enrlursl = []
                clonurls = []
                async with aha.getLocalProxy() as proxy:
                    provurls.append(await proxy.addAhaSvcProv('00.cell'))
                    provurls.append(await proxy.addAhaSvcProv('01.cell', {'mirror': 'cell'}))
                    enrlursl.append(await proxy.addAhaUserEnroll('bob'))
                    enrlursl.append(await proxy.addAhaUserEnroll('alice'))
                    clonurls.append(await proxy.addAhaClone('hehe.haha.com'))
                    clonurls.append(await proxy.addAhaClone('wow.haha.com', port='12345'))

                    await proxy.clearAhaSvcProvs()
                    await proxy.clearAhaUserEnrolls()
                    await proxy.clearAhaClones()

                for url in provurls:
                    with self.raises(s_exc.NoSuchName) as cm:
                        async with await s_telepath.openurl(url) as client:
                            self.fail(f'Connected to an expired provisioning URL {url}')  # pragma: no cover
                for url in enrlursl:
                    with self.raises(s_exc.NoSuchName) as cm:
                        async with await s_telepath.openurl(url) as prox:
                            self.fail(f'Connected to an expired enrollment URL {url}')  # pragma: no cover
                for url in clonurls:
                    with self.raises(s_exc.NoSuchName) as cm:
                        async with await s_telepath.openurl(url) as prox:
                            self.fail(f'Connected to an expired clone URL {url}')  # pragma: no cover

    async def test_lib_aha_mirrors(self):

        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    user = 'synuser'
                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')

                    core00 = await base.enter_context(self.addSvcToAha(aha, '00.cortex', s_cortex.Cortex, dirn=dirn00,
                                                                       provinfo={'conf': {'aha:user': user}}))
                    self.eq(core00.conf.get('aha:user'), user)

                    core01 = await base.enter_context(self.addSvcToAha(aha, '01.cortex', s_cortex.Cortex, dirn=dirn01,
                                                                       conf={'axon': 'aha://cortex...'},
                                                                       provinfo={'conf': {'aha:user': user}}))
                    self.eq(core01.conf.get('aha:user'), user)

                    async with aha.getLocalProxy() as ahaproxy:
                        self.eq(None, await ahaproxy.getAhaSvcMirrors('99.bogus'))
                        self.len(1, await ahaproxy.getAhaSvcMirrors('00.cortex.synapse'))
                        self.nn(await ahaproxy.getAhaServer(host=aha._getDnsName(), port=aha.sockaddr[1]))

                        todo = s_common.todo('getCellInfo')
                        res = await asyncio.wait_for(await aha.callAhaSvcApi('00.cortex.synapse', todo, timeout=3), 3)
                        self.nn(res)

    async def test_aha_httpapi(self):

        async with self.getTestAha() as aha:

            await aha.auth.rootuser.setPasswd('secret')

            host, httpsport = await aha.addHttpsPort(0)
            url = f'https://localhost:{httpsport}/api/v1/aha/provision/service'

            async with self.getHttpSess(auth=('root', 'secret'), port=httpsport) as sess:
                # Simple request works
                async with sess.post(url, json={'name': '00.foosvc'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    info = await resp.json()
                    self.eq(info.get('status'), 'ok')
                    result = info.get('result')
                    provurl = result.get('url')

                async with await s_telepath.openurl(provurl) as prox:
                    provconf = await prox.getProvInfo()
                    self.isin('iden', provconf)
                    conf = provconf.get('conf')
                    self.eq(conf.get('aha:user'), 'root')
                    dmon_listen = conf.get('dmon:listen')
                    parts = s_telepath.chopurl(dmon_listen)
                    self.eq(parts.get('port'), 0)
                    self.none(conf.get('https:port'))

                # Full api works as well
                data = {'name': '01.foosvc',
                        'provinfo': {
                            'dmon:port': 12345,
                            'https:port': 8443,
                            'mirror': 'foosvc',
                            'conf': {
                                'aha:user': 'test',
                            }
                        }
                        }
                async with sess.post(url, json=data) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    info = await resp.json()
                    self.eq(info.get('status'), 'ok')
                    result = info.get('result')
                    provurl = result.get('url')
                async with await s_telepath.openurl(provurl) as prox:
                    provconf = await prox.getProvInfo()
                    conf = provconf.get('conf')
                    self.eq(conf.get('aha:user'), 'test')
                    dmon_listen = conf.get('dmon:listen')
                    parts = s_telepath.chopurl(dmon_listen)
                    self.eq(parts.get('port'), 12345)
                    self.eq(conf.get('https:port'), 8443)

                # Sad path
                async with sess.post(url) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')
                async with sess.post(url, json={}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')
                async with sess.post(url, json={'name': 1234}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')
                async with sess.post(url, json={'name': ''}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')
                async with sess.post(url, json={'name': '00.newp', 'provinfo': 5309}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')
                async with sess.post(url, json={'name': '00.newp', 'provinfo': {'dmon:port': -1}}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'SchemaViolation')
                async with sess.post(url, json={'name': 'doom' * 16}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'BadArg')

            # Not an admin
            await aha.addUser('lowuser', passwd='lowuser')
            async with self.getHttpSess(auth=('lowuser', 'lowuser'), port=httpsport) as sess:
                async with sess.post(url, json={'name': '00.newp'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'AuthDeny')

    async def test_aha_connect_back(self):

        async with self.getTestAha() as aha:  # type: s_aha.AhaCell

            async with self.addSvcToAha(aha, '00.exec', ExecTeleCaller) as conn:
                ahaurl = aha.getMyUrl()
                await conn.exectelecall(ahaurl, 'getNexsIndx')

            self.true(conn.ahaclient.isfini)

    async def test_aha_util_helpers(self):

        # Mainly for test helper coverage.
        async with self.getTestAha() as aha:
            async with self.addSvcToAha(aha, '00.cell', s_cell.Cell) as cell00:  # type: s_cell.Cell
                async with self.addSvcToAha(aha, '01.cell', s_cell.Cell,
                                            provinfo={'mirror': 'cell'}) as cell01:  # type: s_cell.Cell
                    await cell01.sync()
                    # This should teardown cleanly.

    async def test_aha_restart(self):

        with self.getTestDir() as dirn:

            ahadirn = s_common.gendir(dirn, 'aha')
            svc0dirn = s_common.gendir(dirn, 'svc00')
            svc1dirn = s_common.gendir(dirn, 'svc01')

            async with await s_base.Base.anit() as cm:

                async with self.getTestAha(dirn=ahadirn) as aha:

                    async with aha.waiter(3, 'aha:svcadd', timeout=10):

                        onetime = await aha.addAhaSvcProv('00.svc', provinfo=None)
                        conf = {'aha:provision': onetime}
                        svc0 = await cm.enter_context(self.getTestCell(conf=conf))

                        onetime = await aha.addAhaSvcProv('01.svc', provinfo={'mirror': 'svc'})
                        conf = {'aha:provision': onetime}
                        svc1 = await cm.enter_context(self.getTestCell(conf=conf))

                    # Ensure that services have connected
                    await asyncio.wait_for(svc1.nexsroot._mirready.wait(), timeout=6)
                    await svc1.sync()

                    # Get Aha services
                    snfo = await aha.getAhaSvc('01.svc...')
                    self.true(snfo['svcinfo']['ready'])

                    online = snfo['svcinfo']['online']
                    self.nn(online)

                # Restart aha
                async with self.getTestAha(dirn=ahadirn) as aha:

                    snfo = await aha._waitAhaSvcDown('01.svc...', timeout=10)
                    self.none(snfo['svcinfo'].get('online'))
                    self.false(snfo['svcinfo']['ready'])

                    # svc01 has reconnected and the ready state has been re-registered
                    snfo = await aha._waitAhaSvcOnline('01.svc...', timeout=10)
                    self.nn(snfo['svcinfo']['online'])
                    self.true(snfo['svcinfo']['ready'])

    async def test_aha_service_pools(self):

        async with self.getTestAha() as aha:

            async with await s_base.Base.anit() as base:

                with self.getTestDir() as dirn:

                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')
                    dirn02 = s_common.genpath(dirn, 'cell02')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00', s_cell.Cell, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01', s_cell.Cell, dirn=dirn01))

                    core00 = await base.enter_context(self.addSvcToAha(aha, 'core', s_cortex.Cortex, dirn=dirn02))

                    msgs = await core00.stormlist('aha.pool.list')
                    self.stormHasNoWarnErr(msgs)
                    self.stormIsInPrint('0 pools', msgs)

                    msgs = await core00.stormlist('aha.pool.add pool00...')
                    self.stormHasNoWarnErr(msgs)
                    self.stormIsInPrint('Created AHA service pool: pool00.synapse', msgs)

                    # Pool has no members....
                    pool = await s_telepath.open('aha://pool00...')
                    self.eq(0, pool.size())

                    async with pool.waiter(1, 'svc:add', timeout=12):
                        msgs = await core00.stormlist('aha.pool.svc.add pool00... 00...')
                        self.stormHasNoWarnErr(msgs)
                        self.stormIsInPrint('AHA service (00...) added to service pool (pool00.synapse)', msgs)

                    prox = await pool.proxy(timeout=12)
                    info = await prox.getCellInfo()
                    self.eq('00', info.get('cell').get('aha').get('name'))
                    self.eq(1, pool.size())
                    await pool.fini()
                    self.eq(0, pool.size())
                    self.true(prox.isfini)

                    poolinfo = await aha.getAhaPool('pool00...')
                    self.len(1, poolinfo['services'])

                    msgs = await core00.stormlist('aha.pool.list')
                    self.stormIsInPrint('Pool: pool00.synapse', msgs)
                    self.stormIsInPrint('    00.synapse', msgs)
                    self.stormIsInPrint('1 pools', msgs)

                    msgs = await core00.stormlist('$lib.print($lib.aha.pool.get(pool00.synapse))')
                    self.stormIsInPrint('aha:pool: pool00.synapse', msgs)

                    async with await s_telepath.open('aha://pool00...') as pool:

                        replay = s_common.envbool('SYNDEV_NEXUS_REPLAY')
                        nevents = 5 if replay else 3

                        async with pool.waiter(nevents, 'svc:add', timeout=3):

                            msgs = await core00.stormlist('aha.pool.svc.add pool00... 01...')
                            self.stormHasNoWarnErr(msgs)
                            self.stormIsInPrint('AHA service (01...) added to service pool (pool00.synapse)', msgs)

                            msgs = await core00.stormlist('aha.pool.svc.add pool00... 01...')
                            self.stormHasNoWarnErr(msgs)
                            self.stormIsInPrint('AHA service (01...) added to service pool (pool00.synapse)', msgs)

                        poolinfo = await aha.getAhaPool('pool00...')
                        self.len(2, poolinfo['services'])

                        self.nn(poolinfo['created'])
                        self.nn(poolinfo['services']['00.synapse']['created'])
                        self.nn(poolinfo['services']['01.synapse']['created'])

                        self.eq(core00.auth.rootuser.iden, poolinfo['creator'])
                        self.eq(core00.auth.rootuser.iden, poolinfo['services']['00.synapse']['creator'])
                        self.eq(core00.auth.rootuser.iden, poolinfo['services']['01.synapse']['creator'])

                        for client in pool.clients.values():
                            await client.proxy(timeout=3)

                        proxy00 = await pool.proxy(timeout=3)
                        run00 = await (await pool.proxy(timeout=3)).getCellRunId()
                        run01 = await (await pool.proxy(timeout=3)).getCellRunId()
                        self.ne(run00, run01)

                        waiter = pool.waiter(1, 'pool:reset')

                        async with pool.waiter(1, 'pool:reset', timeout=3):
                            ahaproxy = await pool.aha.proxy()
                            await ahaproxy.fini()

                        # wait for the pool to be notified of the topology change
                        async with pool.waiter(1, 'svc:del', timeout=10):

                            msgs = await core00.stormlist('aha.pool.svc.del pool00... 00...')
                            self.stormHasNoWarnErr(msgs)
                            self.stormIsInPrint('AHA service (00.synapse) removed from service pool (pool00.synapse)', msgs)

                            msgs = await core00.stormlist('aha.pool.svc.del pool00... 00...')
                            self.stormHasNoWarnErr(msgs)
                            self.stormIsInPrint('Did not remove (00...) from the service pool.', msgs)

                        run00 = await (await pool.proxy(timeout=3)).getCellRunId()
                        self.eq(run00, await (await pool.proxy(timeout=3)).getCellRunId())

                        poolinfo = await aha.getAhaPool('pool00...')
                        self.len(1, poolinfo['services'])

                    msgs = await core00.stormlist('aha.pool.del pool00...')
                    self.stormHasNoWarnErr(msgs)
                    self.stormIsInPrint('Removed AHA service pool: pool00.synapse', msgs)

    async def test_aha_svc_api_exception(self):

        async with self.getTestAha() as aha:

            async def mockGetAhaSvcProxy(*args, **kwargs):
                raise s_exc.SynErr(mesg='proxy error')

            aha.getAhaSvcProxy = mockGetAhaSvcProxy
            name = '00.cortex.synapse'
            todo = ('bogus', (), {})
            retn = await asyncio.wait_for(await aha.callAhaSvcApi(name, todo), 3)

            self.false(retn[0])
            self.eq('SynErr', retn[1].get('err'))
            self.eq('proxy error', retn[1].get('errinfo').get('mesg'))

            bad_info = {
                'urlinfo': {
                    'host': 'nonexistent.host',
                    'port': 12345,
                    'scheme': 'ssl'
                }
            }

            await aha.addAhaSvc(name, bad_info)
            async for ok, info in aha.callAhaPeerGenr(name, ('nonexistent.method', (), {})):
                self.false(ok)
                self.isin('err', info)

    async def test_aha_reprovision(self):

        with self.withNexusReplay() as stack:
            with self.getTestDir() as dirn:

                aha00dirn = s_common.gendir(dirn, 'aha00')
                aha01dirn = s_common.gendir(dirn, 'aha01')
                svc0dirn = s_common.gendir(dirn, 'svc00')
                svc1dirn = s_common.gendir(dirn, 'svc01')

                async with await s_base.Base.anit() as cm:

                    aha = await cm.enter_context(self.getTestAha(dirn=aha00dirn))

                    async with aha.waiter(2, 'aha:svcadd', timeout=6):
                        purl = await aha.addAhaSvcProv('00.svc')
                        svc0 = await s_cell.Cell.anit(svc0dirn, conf={'aha:provision': purl})
                        await cm.enter_context(svc0)

                    async with aha.waiter(1, 'aha:svcadd', timeout=6):
                        purl = await aha.addAhaSvcProv('01.svc', provinfo={'mirror': 'svc'})
                        svc1 = await s_cell.Cell.anit(svc1dirn, conf={'aha:provision': purl})
                        await cm.enter_context(svc1)

                    await asyncio.wait_for(svc1.nexsroot._mirready.wait(), timeout=6)
                    await svc1.sync()

                    snfo = self.nn(await aha.getAhaSvc('01.svc...'))
                    self.true(snfo['svcinfo']['ready'])

                # Now re-deploy the AHA Service and re-provision the two cells
                # with the same AHA configuration
                async with await s_base.Base.anit() as cm:

                    aha = await cm.enter_context(self.getTestAha(dirn=aha01dirn))

                    async with aha.waiter(2, 'aha:svcadd', timeout=6):
                        purl = await aha.addAhaSvcProv('00.svc')
                        svc0 = await s_cell.Cell.anit(svc0dirn, conf={'aha:provision': purl})
                        await cm.enter_context(svc0)

                    async with aha.waiter(1, 'aha:svcadd', timeout=6):
                        purl = await aha.addAhaSvcProv('01.svc', provinfo={'mirror': 'svc'})
                        svc1 = await s_cell.Cell.anit(svc1dirn, conf={'aha:provision': purl})
                        await cm.enter_context(svc1)

                    await asyncio.wait_for(svc1.nexsroot._mirready.wait(), timeout=6)
                    await svc1.sync()

                    # Get Aha services
                    snfo = self.nn(await aha.getAhaSvc('01.svc...'))
                    self.true(snfo['svcinfo']['ready'])

    async def test_aha_provision_longname(self):
        # Run a long network name and try provisioning with values that would exceed CSR
        # and certificate functionality.
        with self.withNexusReplay() as stack:

            with self.getTestDir() as dirn:
                aha00dirn = s_common.gendir(dirn, 'aha00')
                svc0dirn = s_common.gendir(dirn, 'svc00')
                async with await s_base.Base.anit() as cm:
                    # Add enough space to allow aha CA bootstraping.
                    basenet = 'loop.vertex.link'
                    networkname = f'{"x" * (64 - 7 - len(basenet))}.{basenet}'
                    aconf = {
                        'aha:name': 'aha',
                        'aha:network': networkname,
                        'dmon:listen': f'ssl://aha.{networkname}:0',
                        'provision:listen': f'ssl://aha.{networkname}:0',
                    }
                    name = aconf.get('aha:name')
                    netw = aconf.get('aha:network')
                    dnsname = f'{name}.{netw}'

                    aha = await s_aha.AhaCell.anit(aha00dirn, conf=aconf)
                    await cm.enter_context(aha)

                    addr, port = aha.provdmon.addr
                    # update the config to reflect the dynamically bound port
                    aha.conf['provision:listen'] = f'ssl://{dnsname}:{port}'

                    # do this config ex-post-facto due to port binding...
                    host, ahaport = await aha.dmon.listen(f'ssl://0.0.0.0:0?hostname={dnsname}&ca={netw}')
                    aha.conf['aha:urls'] = (f'ssl://{dnsname}:{ahaport}',)

                    with self.raises(s_exc.BadArg) as errcm:
                        await aha.addAhaSvcProv('00.svc', provinfo=None)
                    self.isin('Hostname value must not exceed 64 characters in length.',
                              errcm.exception.get('mesg'))
                    self.isin('len=65', errcm.exception.get('mesg'))

                    # We can generate a 64 character names though.
                    onetime = await aha.addAhaSvcProv('00.sv', provinfo=None)
                    sconf = {'aha:provision': onetime}
                    s_common.yamlsave(sconf, svc0dirn, 'cell.yaml')
                    svc0 = await s_cell.Cell.anit(svc0dirn, conf=sconf)
                    await cm.enter_context(svc0)

                    # Cannot generate a user cert that would be a problem for signing
                    with self.raises(s_exc.BadArg) as errcm:
                        await aha.addAhaUserEnroll('ruhroh')
                    self.isin('Username value must not exceed 64 characters in length.',
                              errcm.exception.get('mesg'))
                    self.isin('len=65', errcm.exception.get('mesg'))

                    # We can generate a name that is 64 characters in length and have its csr signed
                    onetime = await aha.addAhaUserEnroll('vvvvv')
                    async with await s_telepath.openurl(onetime) as prox:
                        userinfo = await prox.getUserInfo()
                        ahauser = userinfo.get('aha:user')
                        ahanetw = userinfo.get('aha:network')
                        username = f'{ahauser}@{ahanetw}'
                        byts = aha.certdir.genUserCsr(username)
                        byts = await prox.signUserCsr(byts)
                        self.nn(byts)

                    # 0 length inputs
                    with self.raises(s_exc.BadArg) as errcm:
                        await aha.addAhaSvcProv('')
                    self.isin('Empty name values are not allowed for provisioning.', errcm.exception.get('mesg'))
                    with self.raises(s_exc.BadArg) as errcm:
                        await aha.addAhaUserEnroll('')
                    self.isin('Empty name values are not allowed for provisioning.', errcm.exception.get('mesg'))

            # add an aha bootstrapping test failure
            with self.getTestDir() as dirn:
                aha00dirn = s_common.gendir(dirn, 'aha00')
                async with await s_base.Base.anit() as cm:
                    # Make the network too long that we cannot bootstrap the CA
                    basenet = 'loop.vertex.link'
                    networkname = f'{"x" * (64 - len(basenet))}.{basenet}'
                    aconf = {
                        'aha:name': 'aha',
                        'aha:network': networkname,
                        'provision:listen': f'ssl://aha.{networkname}:0'
                    }
                    with self.raises(s_exc.CryptoErr) as errcm:
                        await s_aha.AhaCell.anit(aha00dirn, conf=aconf)
                    self.isin('Certificate name values must be between 1-64 bytes when utf8-encoded.',
                              errcm.exception.get('mesg'))

    async def test_aha_prov_with_user(self):

        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:
                    user = 'synuser'
                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')

                    axon00 = await base.enter_context(self.addSvcToAha(aha, '00.axon', s_axon.Axon, dirn=dirn00,
                                                                       provinfo={'conf': {'aha:user': user}}))
                    self.eq(axon00.conf.get('aha:user'), user)
                    core00 = await base.enter_context(self.addSvcToAha(aha, '00.core', s_cortex.Cortex, dirn=dirn01,
                                                                       conf={'axon': 'aha://axon...'},
                                                                       provinfo={'conf': {'aha:user': user}}))
                    self.eq(core00.conf.get('aha:user'), user)
                    # Svc to svc connections use the hinted aha:user value
                    prox = self.nn(await asyncio.wait_for(core00.axon.proxy(), timeout=12))
                    unfo = await prox.getCellUser()
                    self.eq(unfo.get('name'), user)

    async def test_aha_cell_with_tcp(self):
        # It's an older code, sir, but it checks out.
        # This should be removed in Synapse v3.0.0

        with self.getTestDir() as dirn:
            ahadir = s_common.gendir(dirn, 'aha')
            clldir = s_common.gendir(dirn, 'cell')
            ahaconf = {
                'aha:name': '00.aha',
                'aha:network': 'loop.vertex.link',
                'dmon:listen': 'tcp://127.0.0.1:0/',
                'auth:passwd': 'secret',
            }
            async with await s_aha.AhaCell.anit(dirn=ahadir, conf=ahaconf) as aha:
                urls = await aha.getAhaUrls()
                self.len(1, urls)
                self.true(urls[0].startswith('ssl://'))
                ahaurl = f'tcp://root:secret@127.0.0.1:{aha.sockaddr[1]}/'
                cllconf = {
                    'aha:name': '00.cell',
                    'aha:network': 'loop.vertex.link',
                    'aha:registry': ahaurl,
                    'dmon:listen': None,
                }
                async with await s_cell.Cell.anit(dirn=clldir, conf=cllconf) as cell:
                    self.none(await cell.ahaclient.waitready(timeout=12))
                    self.eq(cell.conf.get('aha:registry'), ahaurl)

                    prox = await cell.ahaclient.proxy()
                    await prox.fini()
                    self.false(cell.ahaclient._t_ready.is_set())

                    self.none(await cell.ahaclient.waitready(timeout=12))

                # No change when restarting
                async with await s_cell.Cell.anit(dirn=clldir, conf=cllconf) as cell:
                    self.none(await cell.ahaclient.waitready(timeout=12))
                    self.eq(cell.conf.get('aha:registry'), ahaurl)

    async def test_aha_provision_listen_dns_name(self):
        # Ensure that we use the dns:name for the provisioning listener when
        # the provision:listen value is not provided.
        conf = {
            'aha:network': 'synapse',
            'dns:name': 'here.loop.vertex.link',
            'dmon:listen': 'ssl://0.0.0.0:0?hostname=here.loop.vertex.link&ca=synapse',
        }

        orig = s_aha.AhaCell._getProvListen
        def _getProvListen(_self):
            ret = orig(_self)
            self.eq(ret, 'ssl://0.0.0.0:27272?hostname=here.loop.vertex.link')
            return 'ssl://0.0.0.0:0?hostname=here.loop.vertex.link'

        with mock.patch('synapse.lib.aha.AhaCell._getProvListen', _getProvListen):
            async with self.getTestCell(s_aha.AhaCell, conf=conf) as aha:
                # And the URL works with our listener :)
                provurl = await aha.addAhaUserEnroll('bob.grey')
                async with await s_telepath.openurl(provurl) as prox:
                    info = await prox.getUserInfo()
                    self.eq(info.get('aha:user'), 'bob.grey')

    async def test_aha_gather(self):

        async with self.getTestAha() as aha:

            async with aha.waiter(3, 'aha:svcadd', timeout=10):

                conf = {'aha:provision': await aha.addAhaSvcProv('00.cell')}
                cell00 = await aha.enter_context(self.getTestCell(conf=conf))

                conf = {'aha:provision': await aha.addAhaSvcProv('01.cell', {'mirror': 'cell'})}
                cell01 = await aha.enter_context(self.getTestCell(conf=conf))

            await cell01.sync()

            async with cell01.getLocalProxy() as proxy:
                self.true(proxy._hasTeleFeat('dynmirror'))
                self.true(proxy._hasTeleMeth('getNexsIndx'))

            nexsindx = await cell00.getNexsIndx()

            # test the call endpoint
            todo = s_common.todo('getCellInfo')
            items = dict([item async for item in aha.callAhaPeerApi(cell00.iden, todo, timeout=3)])
            self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))
            self.true(all(item[0] for item in items.values()))
            self.eq(cell00.runid, items['00.cell.synapse'][1]['cell']['run'])
            self.eq(cell01.runid, items['01.cell.synapse'][1]['cell']['run'])

            todo = s_common.todo('newp')
            items = dict([item async for item in aha.callAhaPeerApi(cell00.iden, todo, timeout=3)])
            self.false(any(item[0] for item in items.values()))
            self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

            # test the genr endpoint
            reals = [item async for item in cell00.getNexusChanges(0, wait=False)]
            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = [item async for item in aha.callAhaPeerGenr(cell00.iden, todo, timeout=3) if item[1]]
            self.len(nexsindx * 2, items)

            # ensure we handle down services correctly
            async with aha.waiter(1, 'aha:svcdown', timeout=10):
                await cell01.fini()

            # test the call endpoint
            todo = s_common.todo('getCellInfo')
            items = dict([item async for item in aha.callAhaPeerApi(cell00.iden, todo, timeout=3)])
            self.sorteq(items.keys(), ('00.cell.synapse',))
            self.true(all(item[0] for item in items.values()))
            self.eq(cell00.runid, items['00.cell.synapse'][1]['cell']['run'])

            # test the genr endpoint
            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = [item async for item in aha.callAhaPeerGenr(cell00.iden, todo, timeout=3) if item[1]]
            self.len(nexsindx, items)
            self.true(all(item[1][0] for item in items))

    async def test_lib_aha_peer_api(self):

        async with self.getTestAha() as aha:

            purl00 = await aha.addAhaSvcProv('0.cell')
            purl01 = await aha.addAhaSvcProv('1.cell', provinfo={'mirror': '0.cell'})
            purl02 = await aha.addAhaSvcProv('2.cell', provinfo={'mirror': '0.cell'})

            cell00 = await aha.enter_context(self.getTestCell(conf={'aha:provision': purl00}))
            cell01 = await aha.enter_context(self.getTestCell(conf={'aha:provision': purl01}))
            cell02 = await aha.enter_context(self.getTestCell(conf={'aha:provision': purl02}))

            await cell01.sync()
            await cell02.sync()

            todo = s_common.todo('getCellInfo')
            items = [item async for item in cell00.callPeerApi(todo)]
            self.len(2, items)

    async def test_lib_aha_peer_genr(self):

        async with self.getTestAha() as aha:

            purl00 = await aha.addAhaSvcProv('0.cell')
            purl01 = await aha.addAhaSvcProv('1.cell', provinfo={'mirror': '0.cell'})

            cell00 = await aha.enter_context(self.getTestCell(conf={'aha:provision': purl00}))
            cell01 = await aha.enter_context(self.getTestCell(conf={'aha:provision': purl01}))

            await cell01.sync()

            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = dict([item async for item in cell00.callPeerGenr(todo)])
            self.len(1, items)

            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = dict([item async for item in cell00.callPeerGenr(todo, timeout=2)])
            self.len(1, items)

    async def test_lib_aha_call_aha_peer_api_isactive(self):

        async with self.getTestAha() as aha0:

            async with aha0.waiter(3, 'aha:svcadd', timeout=10):

                conf = {'aha:provision': await aha0.addAhaSvcProv('00.cell')}
                cell00 = await aha0.enter_context(self.getTestCell(conf=conf))

                conf = {'aha:provision': await aha0.addAhaSvcProv('01.cell', {'mirror': 'cell'})}
                cell01 = await aha0.enter_context(self.getTestCell(conf=conf))

            await cell01.sync()

            # test active AHA peer
            todo = s_common.todo('getCellInfo')
            items = dict([item async for item in aha0.callAhaPeerApi(cell00.iden, todo, timeout=3)])
            self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = dict([item async for item in aha0.callAhaPeerGenr(cell00.iden, todo, timeout=3)])
            self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

            async with aha0.getLocalProxy() as proxy0:
                purl = await proxy0.addAhaClone('01.aha.loop.vertex.link')

            conf1 = {'clone': purl}
            async with self.getTestAha(conf=conf1) as aha1:

                await aha1.sync()

                self.eq(aha0.iden, aha1.iden)
                self.nn(aha1.conf.get('mirror'))

                self.true(aha0.isactive)
                self.false(aha1.isactive)

                # test non-active AHA peer
                todo = s_common.todo('getCellInfo')
                items = dict([item async for item in aha1.callAhaPeerApi(cell00.iden, todo, timeout=3)])
                self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

                todo = s_common.todo('getNexusChanges', 0, wait=False)
                items = dict([item async for item in aha1.callAhaPeerGenr(cell00.iden, todo, timeout=3)])
                self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))
