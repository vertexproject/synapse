import os
import http
import socket
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
import synapse.lib.logging as s_logging
import synapse.lib.stormsvc as s_stormsvc
import synapse.lib.provision as s_provision

import synapse.tools.aha.list as s_a_list

import synapse.tools.aha.enroll as s_tools_enroll
import synapse.tools.aha.provision.user as s_tools_provision_user
import synapse.tools.aha.provision.service as s_tools_provision_service

import synapse.tests.utils as s_test

realaddsvc = s_aha.AhaCell.addAhaSvc
async def mockaddsvc(self, name, info):
    if getattr(self, 'testerr', False):
        raise s_exc.SynErr(mesg='newp')
    return await realaddsvc(self, name, info)

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

class SpecialPathApi(s_cell.CellApi):
    async def __anit__(self, cell, link, user, path):
        await super().__anit__(cell, link, user)
        self.path = path

    async def getTestPath(self):
        return self.path

class PathAwareCell(s_cell.Cell):
    async def getCellApi(self, link, user, path):
        if not path:
            return await self.cellapi.anit(self, link, user)
        return await SpecialPathApi.anit(self, link, user, path)

class AhaStormSvcApi(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_name = 'aha-storm-svc'
    _storm_svc_pkgs = (
        {  # type: ignore
            'name': 'ahastormsvc',
            'version': (0, 0, 1),
            'synapse_version': '>=3.0.0b2,<4.0.0',
            'commands': (
                {
                    'name': 'ahastormsvc.hi',
                    'storm': '$lib.print(hello)',
                },
            ),
        },
    )

class AhaStormSvcCell(s_cell.Cell):
    celltype = 'ahastormsvc'
    cellapi = AhaStormSvcApi

class AhaStormSvc2Api(s_cell.CellApi, s_stormsvc.StormSvc):
    _storm_svc_name = 'aha-storm-svc2'
    _storm_svc_pkgs = (
        {  # type: ignore
            'name': 'ahastormsvc2',
            'version': (0, 0, 1),
            'synapse_version': '>=3.0.0b2,<4.0.0',
            'commands': (
                {
                    'name': 'ahastormsvc2.hi',
                    'storm': '$lib.print(hello2)',
                },
            ),
        },
    )

class AhaStormSvc2Cell(s_cell.Cell):
    celltype = 'ahastormsvc2'
    cellapi = AhaStormSvc2Api

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
                    self.nn(aha1.conf.get('parent'))

                    serv0 = await aha0.getAhaServers()
                    serv1 = await aha1.getAhaServers()

                    self.len(ahacount + 1, serv0)
                    self.eq(serv0, serv1)

                    # ensure some basic functionality is being properly mirrored

                    iden = s_common.guid()
                    # Adding, downing, and removing service is also nexusified
                    info = {'urlinfo': {'host': '127.0.0.1', 'port': 8080,
                                        'scheme': 'tcp'},
                            'session': iden}

                    await aha0.addAhaSvc('test...', info)
                    await aha1.sync()
                    mnfo = await aha1.getAhaSvc('test...')
                    self.eq(mnfo.get('name'), 'test.synapse')

                    async with aha0.waiter(1, 'aha:svc:down', timeout=6):
                        await aha0.setAhaSvcDown('test...', iden)

                    await aha1.sync()

                    mnfo = await aha1.getAhaSvc('test...')
                    self.false(mnfo.get('online'))

                    await aha0.delAhaSvc('test...')
                    await aha1.sync()

                    mnfo = await aha1.getAhaSvc('test...')
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
            cell0_dirn = s_common.gendir(dirn, 'cell0')
            async with self.getTestAha(dirn=dirn) as aha:

                replaymult = 1
                if s_common.envbool('SYNDEV_NEXUS_REPLAY'):
                    replaymult = 2

                purl = await aha.addAhaSvcProv('0.cell')

                conf = {'aha:provision': purl}
                async with self.getTestCell(s_test.TestCell00, dirn=cell0_dirn, conf=conf) as cell:

                    await aha._waitAhaSvcOnline('0.cell...', timeout=10)

                    svc = await aha.getAhaSvc('0.cell...')
                    linkiden = aha._getSvcSess(svc.get('name'))

                    # a generic test cell reports its service type
                    self.eq('testcell00', svc['info']['type'])

                    # Tear down the Aha cell.
                    await aha.__aexit__(None, None, None)

            with self.getLoggerStream('synapse.lib.aha') as stream:
                async with self.getTestAha(dirn=dirn) as aha:
                    await stream.expect('Set [0.cell.synapse] offline.', timeout=12)
                    svc = await aha.getAhaSvc('0.cell...')
                    self.false(svc.get('online'))

                    # Try setting something down a second time
                    await aha.setAhaSvcDown('0.cell...', linkiden)
                    svc = await aha.getAhaSvc('0.cell...')
                    self.false(svc.get('online'))

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

            cell0_dirn = s_common.gendir(aha.dirn, 'cell0')

            ahaurls = await aha.getAhaUrls()

            conf = {'aha:provision': await aha.addAhaSvcProv('0.cell')}
            async with self.getTestCell(s_test.TestCell00, dirn=cell0_dirn, conf=conf) as cell:

                await aha._waitAhaSvcOnline('0.cell...', timeout=10)

                with self.raises(s_exc.NoSuchName):
                    await s_telepath.getAhaProxy({'host': 'hehe.haha'})

                async with await s_telepath.openurl('aha://testcell00...') as proxy:
                    self.nn(await proxy.getCellIden())

                with self.raises(s_exc.BadArg):
                    _proxy = await cell.ahaclient.proxy(timeout=2)
                    await _proxy.modAhaSvcInfo('cell...', {'newp': 'newp'})

                async with await s_telepath.openurl('aha://0.cell...') as proxy:
                    self.nn(await proxy.getCellIden())

                # force a reconnect...
                proxy = await cell.ahaclient.proxy(timeout=2)
                # re-registration fires a single aha:svc:add ( no separate
                # leader-alias registration ); a timeout avoids a hang if it changes.
                async with aha.waiter(1, 'aha:svc:add', timeout=6):
                    await proxy.fini()

                async with await s_telepath.openurl('aha://testcell00...') as proxy:
                    self.nn(await proxy.getCellIden())

                # force the service into passive mode; it remains the term
                # leader for its type and stays resolvable by type once online.
                # re-registration happens in place ( no disconnect ) so the
                # service never goes down.
                await cell.setCellActive(False)

                await aha._waitAhaSvcOnline('testcell00...', timeout=6)
                async with await s_telepath.openurl('aha://testcell00...') as proxy:
                    self.nn(await proxy.getCellIden())

                async with await s_telepath.openurl('aha://0.cell...') as proxy:
                    self.nn(await proxy.getCellIden())

                await cell.setCellActive(True)

                await aha._waitAhaSvcOnline('testcell00...', timeout=6)
                async with await s_telepath.openurl('aha://testcell00...') as proxy:
                    self.nn(await proxy.getCellIden())

            conf = {'aha:provision': await aha.addAhaSvcProv('0.cell')}
            async with self.getTestCell(ctor=PathAwareCell, conf=conf) as cell:

                info = await cell.getCellInfo()
                celliden = info['cell']['iden']

                self.eq(info['cell']['aha'], {'name': '0.cell', 'network': 'synapse'})

                await aha._waitAhaSvcOnline('pathawarecell...', timeout=10)
                await aha._waitAhaSvcOnline('0.cell...', timeout=10)

                async with await s_telepath.openurl('aha://pathawarecell.synapse') as proxy:
                    self.eq(celliden, await proxy.getCellIden())

                async with await s_telepath.openurl('aha://0.cell.synapse') as proxy:
                    self.eq(celliden, await proxy.getCellIden())

                async with await s_telepath.openurl('aha://0.cell.synapse/*/hehe/haha') as proxy:
                    self.eq(celliden, await proxy.getCellIden())
                    self.eq(('hehe', 'haha'), await proxy.getTestPath())

                async with aha.getLocalProxy() as ahaproxy:

                    svcs = [x async for x in ahaproxy.getAhaSvcs()]
                    self.len(1, svcs)
                    names = [s['name'] for s in svcs]
                    self.sorteq(('0.cell.synapse',), names)

                    self.nn(await ahaproxy.getCaCert())

            # We can use HTTP API to get the registered services
            await aha.addUser('lowuser', passwd='lowuser')
            await aha.auth.rootuser.setPasswd('secret')

            host, httpsport = await aha.addHttpsPort(0)
            svcsurl = f'https://localhost:{httpsport}/api/v3/aha/services'

            async with self.getHttpSess(auth=('root', 'secret'), port=httpsport) as sess:

                async with sess.get(svcsurl) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    info = await resp.json()
                    self.eq(info.get('status'), 'ok')
                    result = info.get('result')
                    self.len(1, result)
                    self.eq({'0.cell.synapse'},
                            {svcentry.get('name') for svcentry in result})

                async with sess.get(svcsurl) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)
                    info = await resp.json()
                    self.eq(info.get('status'), 'ok')
                    result = info.get('result')
                    self.len(1, result)
                    self.eq({'0.cell.synapse'},
                            {svcentry.get('name') for svcentry in result})

                # Sad path
                async with sess.get(svcsurl, json={'newp': 'hehe'}) as resp:
                    self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'BadArg')

            # Sad path
            async with self.getHttpSess(auth=('lowuser', 'lowuser'), port=httpsport) as sess:
                async with sess.get(svcsurl) as resp:
                    self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                    info = await resp.json()
                    self.eq(info.get('status'), 'err')
                    self.eq(info.get('code'), 'AuthDeny')

            async with aha.getLocalProxy() as ahaproxy:
                await ahaproxy.delAhaSvc('0.cell.synapse')
                self.none(await ahaproxy.getAhaSvc('0.cell.synapse'))
                self.len(0, [s async for s in ahaproxy.getAhaSvcs()])

            # test that services get updated aha server list
            with self.getTestDir() as dirn:

                conf = {'aha:provision': await aha.addAhaSvcProv('00.cell')}

                # can't assume just one due to enterprise tests with raft...
                ahacount = len(await aha.getAhaUrls())

                async with self.getTestCell(s_test.TestCell00, conf=conf, dirn=dirn) as cell:
                    self.len(ahacount, cell.conf.get('aha:servers'))

                await aha.addAhaServer({'host': 'zoinks.aha.loop.vertex.link'})

                self.len(ahacount + 1, await aha.getAhaServers())

                async with self.getTestCell(s_test.TestCell00, conf=conf, dirn=dirn) as cell:
                    await cell.ahaclient.proxy()
                    self.len(ahacount + 1, cell.conf.get('aha:servers'))

                self.nn(await aha.delAhaServer('zoinks.aha.loop.vertex.link', 27492))
                self.len(ahacount, await aha.getAhaServers())

                async with self.getTestCell(s_test.TestCell00, conf=conf, dirn=dirn) as cell:
                    await cell.ahaclient.proxy()
                    self.len(ahacount, cell.conf.get('aha:servers'))
                    s_common.yamlsave({'aha:servers': [cell.conf.get('aha:servers')[0]]}, dirn, 'cell.mods.yaml')

                async with self.getTestCell(s_test.TestCell00, conf=conf, dirn=dirn) as cell:
                    await cell.ahaclient.proxy()

                # aha:servers must be a list; a bare string is rejected
                with self.raises(s_exc.BadConfValu) as cm:
                    s_common.yamlsave({'aha:servers': 'ssl://newp'}, dirn, 'cell.mods.yaml')
                    async with self.getTestCell(s_test.TestCell00, conf=conf, dirn=dirn) as cell:
                        pass
                self.isin('Invalid config for aha:servers', cm.exception.get('mesg'))

                with self.raises(s_exc.BadConfValu) as cm:
                    s_common.yamlsave({'aha:servers': ['ssl://okay.com', 'tcp://newp']}, dirn, 'cell.mods.yaml')
                    async with self.getTestCell(s_test.TestCell00, conf=conf, dirn=dirn) as cell:
                        pass
                self.isin('Invalid config for aha:servers', cm.exception.get('mesg'))

                with self.raises(s_exc.BadConfValu) as cm:
                    s_common.yamlsave({'dmon:listen': 'tcp://newp'}, dirn, 'cell.mods.yaml')
                    async with self.getTestCell(s_aha.AhaCell, conf=conf, dirn=dirn) as cell:
                        pass
                self.isin('AHA bind URLs must begin with ssl://', cm.exception.get('mesg'))

                with self.raises(s_exc.BadConfValu) as cm:
                    s_common.yamlsave({'provision:listen': 'tcp://newp'}, dirn, 'cell.mods.yaml')
                    async with self.getTestCell(s_aha.AhaCell, conf=conf, dirn=dirn) as cell:
                        pass
                self.isin('Invalid config for provision:listen', cm.exception.get('mesg'))

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

            conf = {'aha:provision': await aha.addAhaSvcProv('0.cell')}

            async with self.getTestCell(s_test.TestCell00, conf=conf) as cell:

                await aha._waitAhaSvcOnline('0.cell...', timeout=10)

                async with await s_telepath.openurl('aha://0.cell...') as proxy:
                    self.nn(await proxy.getCellIden())

                proxy = await cell.ahaclient.proxy()

                # the AhaClient ( ClientV2 ) clears its ready state as part of
                # the proxy fini callbacks, so waitfini avoids the notify race.
                await aha.fini()
                self.true(await proxy.waitfini(timeout=10))

                with self.raises(asyncio.TimeoutError):
                    await cell.ahaclient.proxy(timeout=0.1)

    async def test_lib_aha_onlink_fail(self):

        with mock.patch('synapse.lib.aha.AhaCell.addAhaSvc', mockaddsvc):

            async with self.getTestAha() as aha:

                replaymult = 1
                if s_common.envbool('SYNDEV_NEXUS_REPLAY'):
                    replaymult = 2

                aha.testerr = True
                conf = {'aha:provision': await aha.addAhaSvcProv('0.cell')}
                async with self.getTestCell(s_test.TestCell00, conf=conf) as cell:

                    svc = await aha.getAhaSvc('0.cell...')
                    self.none(svc)

                    aha.testerr = False
                    await aha._waitAhaSvcOnline('0.cell...', timeout=10)

                    svc = await aha.getAhaSvc('0.cell...')
                    self.nn(svc)
                    self.true(svc.get('online'))

                    async with await s_telepath.openurl('aha://0.cell...') as proxy:
                        self.nn(await proxy.getCellIden())

    async def test_lib_aha_logging(self):

        s_logging.setup()

        # AHA service does not register as an AHA service so make sure
        # it sets the 'service' log key directly. The default test AHA
        # has 'aha:network' set to 'synapse' and 'dns:name' set but no
        # 'aha:name', so the service log key falls back to 'dns:name'
        # while 'ahasvcname' stays None.
        async with self.getTestAha() as aha:
            self.none(aha.ahasvcname)
            self.eq(aha.getSvcName(), '00.aha.loop.vertex.link')

            with self.getLoggerStream('synapse.lib.aha') as stream:
                s_aha.logger.warning('aha test message')
                mesg = stream.jsonlines()[0]
                self.eq(mesg['service'], '00.aha.loop.vertex.link')

        # An explicit 'aha:name' uses the standard '{name}.{network}' form.
        conf = {'aha:name': 'aha00'}
        async with self.getTestAha(conf=conf) as aha:
            self.eq(aha.ahasvcname, 'aha00.synapse')
            self.eq(aha.getSvcName(), 'aha00.synapse')

            with self.getLoggerStream('synapse.lib.aha') as stream:
                s_aha.logger.warning('aha test message')
                mesg = stream.jsonlines()[0]
                self.eq(mesg['service'], 'aha00.synapse')

        # When neither 'aha:name' nor 'dns:name' is set the key is unset.
        conf = {'dns:name': None}
        async with self.getTestAha(conf=conf) as aha:
            self.none(aha.ahasvcname)
            self.none(aha.getSvcName())

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

            with self.raises(s_exc.NeedConfValu):
                await aha.addAhaSvcProv('hehe')

            with self.raises(s_exc.NeedConfValu):
                await aha.addAhaUserEnroll('hehe')

            with self.raises(s_exc.NeedConfValu):
                await aha.addAhaUserEnroll('hehe')

    async def test_lib_aha_network_default(self):

        # the Aha cell defaults 'aha:network' to 'syn' when it is not configured
        # and bootstraps the network CA from that default.
        with self.getTestDir() as dirn:
            async with await s_aha.AhaCell.anit(dirn, conf={'health:sysctl:checks': False}) as aha:
                self.eq('syn', aha.conf.get('aha:network'))
                self.true(os.path.isfile(os.path.join(aha.dirn, 'certs', 'cas', 'syn.crt')))

        # the default is scoped to the Aha cell: the base Cell has no default
        self.eq('syn', s_aha.AhaCell.confbase['aha:network'].get('default'))
        self.none(s_cell.Cell.confbase['aha:network'].get('default'))

    def _freeUdpPort(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    async def test_lib_aha_svctype_index(self):

        async with self.getTestAha() as aha:

            # fetch-and-increment returns the next index per service type
            self.eq(0, await aha.getSvcTypeIndex('footype'))
            self.eq(1, await aha.getSvcTypeIndex('footype'))
            self.eq(2, await aha.getSvcTypeIndex('footype'))

            # each service type has an independent index
            self.eq(0, await aha.getSvcTypeIndex('bartype'))

            # the index may be set explicitly
            self.eq(10, await aha.setAhaSvcTypeIndex('footype', 10))
            self.eq(10, await aha.getSvcTypeIndex('footype'))

            # the interlocked check-and-set rejects a stale current value
            self.false(await aha._push('aha:svc:type:index:set', 'footype', 0, 99))
            self.eq(11, await aha.getSvcTypeIndex('footype'))

            # the setter is exposed via telepath
            async with aha.getLocalProxy() as proxy:
                await proxy.setAhaSvcTypeIndex('bartype', 5)

            self.eq(5, await aha.getSvcTypeIndex('bartype'))

    async def test_lib_aha_lead_term(self):

        async with self.getTestAha() as aha:

            svctype = 'cortex'
            svc00 = '00.cortex.synapse'
            svc01 = '01.cortex.synapse'

            # no term exists for a fresh service type
            self.none(await aha.getLeadTerm(svctype))

            # the first service to register takes leadership at its nexus offset
            t0 = await aha.regLeadTerm(svctype, svc00, 10)
            self.eq(t0['name'], svc00)
            self.eq(t0['nexsoffs'], 10)
            self.nn(t0['iden'])
            self.nn(t0['id'])
            self.eq(t0, await aha.getLeadTerm(svctype))

            # a second service booting behind the leader joins as a follower and
            # receives the current ( leader's ) term
            t1 = await aha.regLeadTerm(svctype, svc01, 5)
            self.eq(t1['name'], svc00)
            self.eq(t1['iden'], t0['iden'])

            # the current leader re-registering ( e.g. after a restart ) creates
            # a new term at its updated nexus offset
            t2 = await aha.regLeadTerm(svctype, svc00, 15, term=t0)
            self.eq(t2['name'], svc00)
            self.eq(t2['nexsoffs'], 15)
            self.ne(t2['iden'], t0['iden'])

            # a follower handing back an old svc00 term ( it only ever followed
            # svc00, which re-registered as t2 ) must not falsely detect a schism
            # even when its offset is past the newer same-leader term boundary.
            tf = await aha.regLeadTerm(svctype, svc01, 16, term=t0)
            self.eq(tf['name'], svc00)

            # an API driven ( forced ) promotion of svc01 records a new term
            t3 = await aha.setLeadTerm(svctype, svc01, 20)
            self.eq(t3['name'], svc01)
            self.eq(t3['nexsoffs'], 20)
            self.eq(t3, await aha.getLeadTerm(svctype))

            # the old leader returns having written past the new term boundary and
            # is detected as a schism ( it must be restored from a backup )
            with self.raises(s_exc.LeaderSchism):
                await aha.regLeadTerm(svctype, svc00, 25, term=t2)

            # the schism is signalled to the nexus handler as a None return
            self.none(await aha._push('aha:lead:term:reg', svctype, svc00, 25, t2, s_common.now()))

            # the old leader returning behind the new term boundary safely rejoins
            t4 = await aha.regLeadTerm(svctype, svc00, 18, term=t2)
            self.eq(t4['name'], svc01)
            self.eq(t4['iden'], t3['iden'])

            # a follower which has adopted the current term rejoins without schism
            t5 = await aha.regLeadTerm(svctype, svc00, 22, term=t3)
            self.eq(t5['name'], svc01)

            # with no known term the caller has no anchor and joins as a follower
            # rather than falsely detecting a schism
            t6 = await aha.regLeadTerm(svctype, svc00, 12)
            self.eq(t6['name'], svc01)

            # historical terms are retained in chronological order
            terms = aha._getLeadTerms(svctype)
            self.eq([t['name'] for t in terms], [svc00, svc00, svc01])
            self.eq([t['nexsoffs'] for t in terms], [10, 15, 20])

            # the APIs are exposed via telepath
            async with aha.getLocalProxy() as proxy:
                self.eq(svc01, (await proxy.getLeadTerm(svctype))['name'])
                p0 = await proxy.setLeadTerm(svctype, svc00, 30)
                self.eq(p0['name'], svc00)
                p1 = await proxy.regLeadTerm(svctype, svc00, 31, term=p0)
                self.eq(p1['name'], svc00)

            # removing the last service of a type pops the current term
            axoninfo = {
                'iden': 'a' * 32,
                'type': 'axon',
                'urlinfo': {'scheme': 'ssl', 'host': '127.0.0.1', 'port': 1234},
            }
            await aha.addAhaSvc('00.axon...', axoninfo)
            await aha.setLeadTerm('axon', '00.axon.synapse', 3)
            self.nn(await aha.getLeadTerm('axon'))

            await aha.delAhaSvc('00.axon...')
            self.none(await aha.getLeadTerm('axon'))

    async def test_lib_aha_lead_term_schism_offset_order(self):

        # A lagging peer force-promoted at a lower service nexus offset creates a
        # term *after* one at a higher offset. The earlier high-offset leader
        # returning must still be detected as a schism even though the
        # superseding term sorts below it by service nexus offset. Regression:
        # history keyed by service nexus offset missed the sequentially-later,
        # lower-offset term and let the diverged former leader rejoin as a
        # mirror. The history is now keyed by AHA's monotonic nexus offset.
        async with self.getTestAha() as aha:

            svctype = 'cortex'
            svc00 = '00.cortex.synapse'
            svc01 = '01.cortex.synapse'

            # svc00 leads and advances to a high service nexus offset
            t0 = await aha.regLeadTerm(svctype, svc00, 200)
            self.eq(t0['name'], svc00)
            self.eq(t0['nexsoffs'], 200)

            # svc00 crashes and the lagging svc01 is force-promoted well behind
            # it, creating a superseding term at a lower service offset but a
            # later ( higher ) AHA nexus offset ( the term id ).
            t1 = await aha.setLeadTerm(svctype, svc01, 150)
            self.eq(t1['name'], svc01)
            self.eq(t1['nexsoffs'], 150)
            self.true(t1['id'] > t0['id'])

            # svc00 returns ( handing back its own t0 ) having led past the new
            # term boundary: schism
            with self.raises(s_exc.LeaderSchism):
                await aha.regLeadTerm(svctype, svc00, 200, term=t0)

            # a peer which only ever *followed* t0 ( never led it ) rejoins as a
            # mirror of the current leader without a false schism.
            tf = await aha.regLeadTerm(svctype, '02.cortex.synapse', 175, term=t0)
            self.eq(tf['name'], svc01)
            self.eq(tf['iden'], t1['iden'])

            # history is retained in creation ( AHA nexus offset ) order, not
            # service nexus offset order
            self.eq([t['nexsoffs'] for t in aha._getLeadTerms(svctype)], [200, 150])

    async def test_lib_aha_provision_mcast(self):

        port = self._freeUdpPort()
        group = '239.192.10.1'
        secret = 'test-provision-secret'

        with mock.patch.object(s_provision, 'DEFAULT_MCAST_PORT', port), \
             mock.patch.object(s_provision, 'DEFAULT_MCAST_GROUP', group), \
             mock.patch.dict(os.environ, {'SYN_PROVISION_SECRET': secret}):

            async with self.getTestAha() as aha:

                # the multicast discovery listener is running
                self.nn(aha.provmcast)

                # each instance provisions as NNN.<type>; the first to register a
                # leadership term becomes the leader and the rest follow it.
                self.eq('000.newtype', await aha._getProvMcastName('newtype'))
                self.eq('001.newtype', await aha._getProvMcastName('newtype'))

                with self.getTestDir() as dirn:

                    async with await s_test.TestCell00.anit(dirn, conf=self.getCellConf()) as svc:

                        await aha._waitAhaSvcOnline('000.testcell00...', timeout=10)

                        # the service discovered AHA, provisioned as the 000 leader, and registered
                        self.true(os.path.isfile(os.path.join(dirn, 'prov.done')))
                        self.eq('synapse', svc.conf.get('aha:network'))

                        svcentry = await aha.getAhaSvcByType('testcell00')
                        self.eq('000.testcell00.synapse', svcentry.get('name'))

                        # a discovery request for the existing type mints the next peer URL
                        key = s_provision.deriveKey(secret)
                        async with await s_provision.ProvCast.anit(key, port, group=group) as cli:

                            cli.send({'type': 'service', 'data': {'type': 'testcell00'}})

                            item = await cli.recv(timeout=10)
                            self.nn(item)
                            self.true(item[0]['data'][0])
                            self.isin('ssl://', item[0]['data'][1].get('url'))

                        # the leader consumed index 0 and the mirror request index 1
                        self.eq(2, await aha.getSvcTypeIndex('testcell00'))

    async def test_lib_aha_provision_mcast_errors(self):

        port = self._freeUdpPort()
        group = '239.192.10.2'
        secret = 'test-provision-secret'

        with mock.patch.object(s_provision, 'DEFAULT_MCAST_PORT', port), \
             mock.patch.object(s_provision, 'DEFAULT_MCAST_GROUP', group), \
             mock.patch.dict(os.environ, {'SYN_PROVISION_SECRET': secret}):

            async with self.getTestAha() as aha:

                self.nn(aha.provmcast)

                key = s_provision.deriveKey(secret)

                async with await s_provision.ProvCast.anit(key, port, group=group) as cli:

                    # a valid request whose provisioning fails ( hostname too long )
                    # gets an error response
                    cli.send({'type': 'service', 'data': {'type': 'x' * 70}})

                    item = await cli.recv(timeout=10)
                    self.nn(item)
                    self.false(item[0]['data'][0])
                    self.eq('BadArg', item[0]['data'][1][0])

                    # a schema-invalid request ( missing service type ) is silently ignored
                    cli.send({'type': 'service', 'data': {}})
                    self.none(await cli.recv(timeout=1))

                    # a non-leader AHA does not respond to discovery requests
                    aha.isactive = False
                    try:
                        cli.send({'type': 'service', 'data': {'type': 'testcell00'}})
                        self.none(await cli.recv(timeout=1))
                    finally:
                        aha.isactive = True

                # a request encrypted with the wrong secret is dropped by AHA
                async with await s_provision.ProvCast.anit(s_provision.deriveKey('nope'), port, group=group) as bad:
                    bad.send({'type': 'service', 'data': {'type': 'cortex'}})
                    self.none(await bad.recv(timeout=1))

    async def test_lib_aha_provision_mcast_clone(self):

        port = self._freeUdpPort()
        group = '239.192.10.3'
        secret = 'test-provision-secret'

        with mock.patch.object(s_provision, 'DEFAULT_MCAST_PORT', port), \
             mock.patch.object(s_provision, 'DEFAULT_MCAST_GROUP', group), \
             mock.patch.dict(os.environ, {'SYN_PROVISION_SECRET': secret}):

            async with self.getTestAha() as aha:

                self.nn(aha.provmcast)

                key = s_provision.deriveKey(secret)
                async with await s_provision.ProvCast.anit(key, port, group=group) as cli:

                    # an 'aha' discovery request enrolls the sender as an AHA clone
                    cli.send({'type': 'aha', 'data': {'host': 'aha01.synapse'}})

                    item = await cli.recv(timeout=10)
                    self.nn(item)
                    self.true(item[0]['data'][0])
                    url = item[0]['data'][1].get('url')
                    self.isin('ssl://', url)

                    # the enrolled clone carries an explicit parent to the leader AHA
                    iden = s_telepath.chopurl(url).get('path').strip('/')
                    clone = await aha.getAhaClone(iden)
                    self.eq('aha01.synapse', clone.get('host'))
                    self.eq(aha.getMyUrl(), clone.get('conf').get('parent'))

    async def test_aha_boot_clone_mcast(self):

        port = self._freeUdpPort()
        group = '239.192.11.2'
        secret = 'test-provision-secret'
        key = s_provision.deriveKey(secret)

        secretenv = {'SYN_PROVISION_SECRET': secret}
        followerenv = {'SYN_PROVISION_SECRET': secret, 'SYN_PROVISION_FOLLOWER': '1'}

        with mock.patch.object(s_provision, 'DEFAULT_MCAST_PORT', port), \
             mock.patch.object(s_provision, 'DEFAULT_MCAST_GROUP', group), \
             mock.patch.object(s_provision, 'MCAST_ATTEMPTS', 1):

            # the leader AHA is created without the discovery listener ( no secret
            # env at boot ) so only our fake responder is on the group.
            async with self.getTestAha() as aha:

                self.none(aha.provmcast)

                # a clone conf short circuits discovery
                aha.conf['clone'] = 'ssl://leader/deadb33f'
                with mock.patch.dict(os.environ, followerenv):
                    await aha._bootCloneMcast()
                self.eq('ssl://leader/deadb33f', aha.conf.get('clone'))
                aha.conf.pop('clone', None)

                # a non-inaugural boot ( cell.guid present ) skips discovery
                with mock.patch.dict(os.environ, followerenv):
                    await aha._bootCloneMcast()
                self.none(aha.conf.get('clone'))

                # remove cell.guid so the method treats this as an inaugural boot
                os.unlink(s_common.genpath(aha.dirn, 'cell.guid'))

                # without SYN_PROVISION_FOLLOWER no discovery is attempted
                with mock.patch.dict(os.environ, secretenv):
                    await aha._bootCloneMcast()
                self.none(aha.conf.get('clone'))

                # follower env but no dns:name -> fatal
                aha.conf.pop('dns:name', None)
                with mock.patch.dict(os.environ, followerenv):
                    with self.raises(s_exc.FatalErr):
                        await aha._bootCloneMcast()

                aha.conf['dns:name'] = 'aha01.synapse'

                # a fake leader AHA replies with a clone provisioning url
                async with await s_provision.ProvCast.anit(key, port, group=group, join=True) as srv:

                    requests = []

                    async def serve():
                        while not srv.isfini:
                            mesg, addr = await srv.recv()
                            requests.append(mesg)
                            srv.send({'type': 'retn', 'data': (True, {'url': 'ssl://leader/deadb33f'})}, addr)

                    srv.schedCoro(serve())

                    with mock.patch.dict(os.environ, followerenv):
                        await aha._bootCloneMcast()

                    self.eq('ssl://leader/deadb33f', aha.conf.get('clone'))
                    self.gt(len(requests), 0)
                    self.eq('aha', requests[-1].get('type'))
                    self.eq('aha01.synapse', requests[-1]['data'].get('host'))

                aha.conf.pop('clone', None)

                # follower env + dns:name set: discovery is retried until the leader
                # AHA responds, logging a warning while it remains unresolved
                async with await s_provision.ProvCast.anit(key, port, group=group, join=True) as srv:

                    reqs = []

                    async def servelate():
                        while not srv.isfini:
                            mesg, addr = await srv.recv()
                            reqs.append(mesg)

                            # ignore the first request to force at least one retry
                            if len(reqs) < 2:
                                continue

                            srv.send({'type': 'retn', 'data': (True, {'url': 'ssl://leader/l8'})}, addr)

                    srv.schedCoro(servelate())

                    with mock.patch.object(s_provision, 'MCAST_TIMEOUT', 0.2), \
                         mock.patch.object(s_cell, 'PROV_FOLLOWER_WARN_TIMEOUT', 0.0):
                        with self.getLoggerStream('synapse.lib.cell') as stream:
                            with mock.patch.dict(os.environ, followerenv):
                                await aha._bootCloneMcast()
                            await stream.expect('waiting for the leader AHA')

                    self.eq('ssl://leader/l8', aha.conf.get('clone'))
                    self.ge(len(reqs), 2)

    async def test_lib_aha_provision(self):

        with self.getTestDir() as dirn:

            conf = {'dns:name': 'aha.loop.vertex.link'}
            async with self.getTestAha(dirn=dirn, conf=conf) as aha:
                await aha.enter_context(self.withSetLoggingMock())

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
                    self.eq('00.axon', yamlconf.get('aha:name'))
                    self.eq('synapse', yamlconf.get('aha:network'))
                    self.none(yamlconf.get('aha:admin'))

                    self.eq(await aha.getAhaUrls(), yamlconf.get('aha:servers'))
                    self.eq('ssl://0.0.0.0:0?hostname=00.axon.synapse&ca=synapse', yamlconf.get('dmon:listen'))

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
                }
                s_common.yamlsave(overconf, axonpath, 'cell.mods.yaml')

                # force a re-provision... (because the providen is different)
                with self.getLoggerStream('synapse.lib.cell') as stream:
                    async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:
                        await stream.expect('Provisioning axon from AHA service', timeout=6)
                        self.ne(axon.conf.get('dmon:listen'), 'tcp://0.0.0.0:0')

                overconf2 = s_common.yamlload(axonpath, 'cell.mods.yaml')
                self.eq(overconf2, {})

                # tests startup logic that recognizes it's already done
                with self.getLoggerStream('synapse.lib.cell') as stream:
                    async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:
                        pass
                    self.notin('Provisioning axon from AHA service', stream.getvalue())

                async with await s_axon.Axon.initFromArgv((axonpath,)) as axon:
                    # testing second run...
                    pass

                # With one axon up, we can provision a mirror of him.
                axn2path = s_common.genpath(dirn, 'axon2')

                argv = ['--url', aha.getLocalUrl(), '01.axon', '--only-url']
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

                            with s_common.genfile(axn2path, 'prov.done') as fd:
                                axon2providen = fd.read().decode().strip()
                            self.eq(providen, axon2providen)

                        # Turn the mirror back on with the provisioning url in the config
                        async with await s_axon.Axon.initFromArgv((axn2path,)) as axon2:
                            await axon2.sync()
                            self.true(axon.isactive)
                            self.false(axon2.isactive)

                # Provision a mirror using aha:provision in the mirror cell.yaml as well.
                # This is similar to the previous test block.
                axn3path = s_common.genpath(dirn, 'axon3')

                argv = ['--url', aha.getLocalUrl(), '02.axon']
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

                        retn, outp = await self.execToolMain(s_a_list.main, ['--url', aha.getLocalUrl()])
                        self.eq(retn, 0)
                        outp.expect('Service Leader', whitespace=False)
                        outp.expect('00.axon.synapse  true', whitespace=False)
                        outp.expect('01.axon.synapse  false', whitespace=False)
                        outp.expect('02.axon.synapse  false', whitespace=False)
                        outp.expect('axon.synapse     true', whitespace=False)

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
                    provurls.append(await proxy.addAhaSvcProv('01.cell'))
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
                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')

                    core00 = await base.enter_context(self.addSvcToAha(aha, '00.cortex', s_cortex.Cortex, dirn=dirn00))

                    core01 = await base.enter_context(self.addSvcToAha(aha, '01.cortex', s_cortex.Cortex, dirn=dirn01))

                    await asyncio.wait_for(core01.nexsroot.ready.wait(), timeout=8)

                    async with aha.getLocalProxy() as ahaproxy:
                        self.eq(None, await ahaproxy.getAhaSvcMirrors('99.bogus'))
                        self.len(1, await ahaproxy.getAhaSvcMirrors('00.cortex.synapse'))
                        self.nn(await ahaproxy.getAhaServer(host=aha._getDnsName(), port=aha.sockaddr[1]))

                        todo = s_common.todo('getCellInfo')
                        res = await asyncio.wait_for(await aha.callAhaSvcApi('00.cortex.synapse', todo, timeout=3), 3)
                        self.nn(res)

    async def test_aha_topo(self):

        async with self.getTestAha() as aha:

            queue = asyncio.Queue()

            async def consume():
                async for mesg in aha.getAhaTopo():
                    await queue.put(mesg)

            task = aha.schedCoro(consume())

            async def nextmatch(func):
                # match on the expected state, tolerating duplicate/interleaved
                # events under SYNDEV_NEXUS_REPLAY.
                while True:
                    mesg = await asyncio.wait_for(queue.get(), timeout=6)
                    if func(mesg):
                        return mesg

            # the snapshot begins with the aha:servers message ( current AHA
            # urls ), then ( with no services registered ) the sync sentinel.
            mesg = await asyncio.wait_for(queue.get(), timeout=6)
            self.eq('aha:servers', mesg[0])
            self.isinstance(mesg[1]['urls'], (list, tuple))
            self.eq(('svc:sync', {}), await asyncio.wait_for(queue.get(), timeout=6))
            self.len(1, aha.topowindows)

            onln = s_common.guid()
            info = {
                'iden': s_common.guid(),
                'run': s_common.guid(),
                'type': 'testcell00',
                'session': onln,
                'urlinfo': {'scheme': 'ssl', 'host': '127.0.0.1', 'port': 4443},
            }

            # a newly added service produces svc:add with a boolean online flag
            await aha.addAhaSvc('00.foo...', info)
            mesg = await nextmatch(lambda m: m[0] == 'svc:add')
            self.eq('00.foo.synapse', mesg[1]['entry']['name'])
            self.true(mesg[1]['entry'].get('online'))

            # a service info update is reflected via svc:mod carrying the update
            await aha.modAhaSvcInfo('00.foo...', {'ready': True})
            mesg = await nextmatch(lambda m: m[0] == 'svc:mod' and m[1]['entry']['info'].get('ready'))
            self.true(mesg[1]['entry']['info']['ready'])

            # a leadership term change produces a svc:lead message enveloping the term
            await aha.setLeadTerm('testcell00', '00.foo.synapse', 30)
            mesg = await nextmatch(lambda m: m[0] == 'svc:lead')
            self.eq('testcell00', mesg[1]['type'])
            self.eq('00.foo.synapse', mesg[1]['term']['name'])

            # a service going offline produces svc:mod with the online flag cleared
            await aha.setAhaSvcDown('00.foo...', onln)
            mesg = await nextmatch(lambda m: m[0] == 'svc:mod' and not m[1]['entry'].get('online'))
            self.false(mesg[1]['entry'].get('online'))

            # deleting a service produces svc:del
            await aha.delAhaSvc('00.foo...')
            mesg = await nextmatch(lambda m: m[0] == 'svc:del')
            self.eq({'name': '00.foo.synapse'}, mesg[1])

            # a new AHA server ( e.g. a clone calling in ) produces aha:servers
            await aha.addAhaServer({'host': 'ahaclone.loop.vertex.link', 'port': 12345})
            mesg = await nextmatch(lambda m: m[0] == 'aha:servers' and
                                   any('ahaclone.loop.vertex.link' in u for u in m[1]['urls']))
            self.true(any('ahaclone.loop.vertex.link' in u for u in mesg[1]['urls']))

            # removing the AHA server produces another aha:servers without it
            await aha.delAhaServer('ahaclone.loop.vertex.link', 12345)
            await nextmatch(lambda m: m[0] == 'aha:servers' and
                            not any('ahaclone.loop.vertex.link' in u for u in m[1]['urls']))

            # closing the consumer removes the window from the registry
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            self.len(0, aha.topowindows)

    async def test_aha_topo_client(self):

        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:

                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')

                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00', s_test.TestCell00, dirn=dirn00))

                    client = cell00.ahaclient
                    self.isinstance(client, s_telepath.AhaClient)

                    # the cache is eventually consistent, so poll for a condition
                    async def waitCache(func):
                        for _ in range(200):
                            if func():
                                return True
                            await asyncio.sleep(0.05)
                        return False  # pragma: no cover

                    # the client keeps a live view including its own registration
                    await client.waitTopoReady(timeout=10)
                    self.true(await waitCache(lambda: '00.synapse' in client.svcs))

                    # callers may subscribe to topology updates via the client
                    waiter = client.waiter(1, 'svc:add', timeout=10)
                    async with self.addSvcToAha(aha, '01', s_test.TestCell01, dirn=dirn01) as cell01:

                        # the svc:add event fires and the service becomes visible
                        self.nn(await waiter.wait())
                        self.true(await waitCache(lambda: '01.synapse' in client.svcs))

                        # the cached entry carries the server-provided info
                        svcentry = client.svcs.get('01.synapse')
                        self.eq(cell01.iden, svcentry['info'].get('iden'))
                        self.true(svcentry.get('online'))

                    # exiting the context fini's cell01 which marks it offline
                    self.true(await waitCache(
                        lambda: not client.svcs.get('01.synapse', {}).get('online')))

                    # deleting the offline service is reflected via svc:del
                    await aha.delAhaSvc('01...')
                    self.true(await waitCache(lambda: '01.synapse' not in client.svcs))

    async def test_aha_topo_consumers(self):

        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:
                with self.getTestDir() as dirn:

                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')

                    core00 = await base.enter_context(self.addSvcToAha(aha, '00.cortex', s_cortex.Cortex, dirn=dirn00))
                    core01 = await base.enter_context(self.addSvcToAha(aha, '01.cortex', s_cortex.Cortex, dirn=dirn01,
                                                                       provinfo={'mirror': '00.cortex'}))

                    await asyncio.wait_for(core01.nexsroot.ready.wait(), timeout=8)

                    # topology reads that must be authoritative ( mirror URL
                    # enumeration and promotion peer discovery ) query the AHA
                    # server directly rather than the eventually-consistent
                    # AhaClient cache.
                    urls = await core00.getMirrorUrls()
                    self.eq(['aha://01.cortex.synapse'], urls)

                    peers = await core00._getDemotePeers(timeout=6)
                    self.len(1, peers)
                    self.eq('01.cortex.synapse', peers[0]['name'])

    async def test_aha_httpapi(self):

        async with self.getTestAha() as aha:

            await aha.auth.rootuser.setPasswd('secret')

            host, httpsport = await aha.addHttpsPort(0)
            url = f'https://localhost:{httpsport}/api/v3/aha/provision/service'

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
                    self.none(conf.get('aha:user'))
                    dmon_listen = conf.get('dmon:listen')
                    parts = s_telepath.chopurl(dmon_listen)
                    self.eq(parts.get('port'), 0)
                    self.none(conf.get('https:port'))

                # Full api works as well
                data = {'name': '01.foosvc',
                        'provinfo': {
                            'dmon:port': 12345,
                            'https:port': 8443,
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
            async with self.addSvcToAha(aha, '00.cell', s_test.TestCell00) as cell00:  # type: s_cell.Cell
                async with self.addSvcToAha(aha, '01.cell', s_test.TestCell00) as cell01:  # type: s_cell.Cell
                    await cell01.sync()
                    # This should teardown cleanly.

    async def test_aha_restart(self):

        with self.getTestDir() as dirn:

            ahadirn = s_common.gendir(dirn, 'aha')
            svc0dirn = s_common.gendir(dirn, 'svc00')
            svc1dirn = s_common.gendir(dirn, 'svc01')

            async with await s_base.Base.anit() as cm:

                async with self.getTestAha(dirn=ahadirn) as aha:

                    onetime = await aha.addAhaSvcProv('00.svc', provinfo=None)
                    conf = {'aha:provision': onetime}
                    svc0 = await cm.enter_context(self.getTestCell(s_test.TestCell00, conf=conf))
                    await aha._waitAhaSvcOnline('00.svc...')

                    onetime = await aha.addAhaSvcProv('01.svc')
                    conf = {'aha:provision': onetime}
                    svc1 = await cm.enter_context(self.getTestCell(s_test.TestCell00, conf=conf))
                    await aha._waitAhaSvcOnline('01.svc...')

                    # Ensure that services have connected
                    await asyncio.wait_for(svc1.nexsroot._mirready.wait(), timeout=6)
                    await svc1.sync()

                    # Get Aha services
                    snfo = await aha.getAhaSvc('01.svc...')
                    self.true(snfo['info']['ready'])

                    self.true(snfo.get('online'))

                # Restart aha
                async with self.getTestAha(dirn=ahadirn) as aha:

                    snfo = await aha._waitAhaSvcDown('01.svc...', timeout=10)
                    self.false(snfo.get('online'))
                    self.false(snfo['info']['ready'])

                    # svc01 has reconnected and the ready state has been re-registered
                    snfo = await aha._waitAhaSvcOnline('01.svc...', timeout=10)
                    self.true(snfo.get('online'))
                    self.true(snfo['info']['ready'])

    async def test_aha_service_pools(self):

        async with self.getTestAha() as aha:

            async with await s_base.Base.anit() as base:

                with self.getTestDir() as dirn:

                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')
                    dirn02 = s_common.genpath(dirn, 'cell02')

                    # each service type is unique, so the two pool members use
                    # distinct service types.
                    cell00 = await base.enter_context(self.addSvcToAha(aha, '00', s_test.TestCell00, dirn=dirn00))
                    cell01 = await base.enter_context(self.addSvcToAha(aha, '01', s_test.TestCell01, dirn=dirn01))

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

                    pdef = await core00.callStorm('return($lib.aha.pool.get(pool00.synapse))')
                    self.eq('pool00.synapse', pdef.get('name'))
                    self.isin('00.synapse', pdef.get('services'))

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

                        async with pool.waiter(1, 'pool:reset', timeout=3):
                            ahaproxy = await pool.aha.proxy()
                            await ahaproxy.fini()

                        # ensure we are reconnected before moving on...
                        async with pool.waiter(1, 'svc:add', timeout=3):
                            await pool.aha.proxy(timeout=3)

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

                    purl = await aha.addAhaSvcProv('00.svc')
                    svc0 = await s_test.TestCell00.anit(svc0dirn, conf={'aha:provision': purl})
                    await cm.enter_context(svc0)
                    await aha._waitAhaSvcOnline('00.svc...', timeout=10)

                    purl = await aha.addAhaSvcProv('01.svc')
                    svc1 = await s_test.TestCell00.anit(svc1dirn, conf={'aha:provision': purl})
                    await cm.enter_context(svc1)
                    await aha._waitAhaSvcOnline('01.svc...', timeout=10)

                    await asyncio.wait_for(svc1.nexsroot._mirready.wait(), timeout=6)
                    await svc1.sync()

                    snfo = self.nn(await aha.getAhaSvc('01.svc...'))
                    self.true(snfo['info']['ready'])

                # Now re-deploy the AHA Service and re-provision the two cells
                # with the same AHA configuration
                async with await s_base.Base.anit() as cm:

                    aha = await cm.enter_context(self.getTestAha(dirn=aha01dirn))

                    purl = await aha.addAhaSvcProv('00.svc')
                    svc0 = await s_test.TestCell00.anit(svc0dirn, conf={'aha:provision': purl})
                    await cm.enter_context(svc0)
                    await aha._waitAhaSvcOnline('00.svc...', timeout=10)

                    purl = await aha.addAhaSvcProv('01.svc')
                    svc1 = await s_test.TestCell00.anit(svc1dirn, conf={'aha:provision': purl})
                    await cm.enter_context(svc1)
                    await aha._waitAhaSvcOnline('01.svc...', timeout=10)

                    await asyncio.wait_for(svc1.nexsroot._mirready.wait(), timeout=6)
                    await svc1.sync()

                    # Get Aha services
                    snfo = self.nn(await aha.getAhaSvc('01.svc...'))
                    self.true(snfo['info']['ready'])

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

                    with self.raises(s_exc.BadArg) as errcm:
                        await aha.addAhaSvcProv('00.svc', provinfo=None)
                    self.isin('Hostname value must not exceed 64 characters in length.',
                              errcm.exception.get('mesg'))
                    self.isin('len=65', errcm.exception.get('mesg'))

                    # We can generate a 64 character names though.
                    onetime = await aha.addAhaSvcProv('00.sv', provinfo=None)

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
                    dirn00 = s_common.genpath(dirn, 'cell00')
                    dirn01 = s_common.genpath(dirn, 'cell01')

                    axon00 = await base.enter_context(self.addSvcToAha(aha, '00.axon', s_axon.Axon, dirn=dirn00))
                    core00 = await base.enter_context(self.addSvcToAha(aha, '00.core', s_cortex.Cortex, dirn=dirn01))
                    # Svc to svc connections authenticate as the root user.
                    prox = self.nn(await asyncio.wait_for(core00.axon.proxy(), timeout=12))
                    unfo = await prox.getCellUser()
                    self.eq(unfo.get('name'), 'root')

    async def test_aha_svc_by_type(self):

        def mkinfo(iden, celltype, online=True):
            return {
                'iden': iden,
                'run': iden + 'run',
                'type': celltype,
                'ready': True,
                'session': ('sess' + iden) if online else None,
                'urlinfo': {'scheme': 'ssl', 'host': '127.0.0.1', 'port': 1234},
            }

        async with self.getTestAha() as aha:

            await aha.addAhaSvc('01.core...', mkinfo('aaa', 'cortex'))
            # leadership is assigned exclusively by the leadership terms.
            await aha.setLeadTerm('cortex', '01.core.synapse', 1)

            # by-type lookup returns the online leader
            svcentry = await aha.getAhaSvcByType('cortex')
            self.eq(svcentry['info']['iden'], 'aaa')
            self.true(svcentry['leader'])

            svcs = [s async for s in aha.getAhaSvcsByType('cortex')]
            self.len(1, svcs)

            # aha://cortex... resolves by cell type when no service is named cortex
            byname = await aha.getAhaSvc('cortex...')
            self.eq(byname['info']['iden'], 'aaa')

            # re-registration of the same iden is allowed
            await aha.addAhaSvc('01.core...', mkinfo('aaa', 'cortex'))

            # a different iden of the same type is rejected
            with self.raises(s_exc.BadArg):
                await aha.addAhaSvc('02.core...', mkinfo('bbb', 'cortex'))

            # deleting the existing instance ( by ... suffixed name ) frees the
            # type so a new instance may register.
            await aha.delAhaSvc('01.core...')
            await aha.addAhaSvc('02.core...', mkinfo('bbb', 'cortex'))
            await aha.setLeadTerm('cortex', '02.core.synapse', 2)
            self.eq('bbb', (await aha.getAhaSvcByType('cortex'))['info']['iden'])

            # every service type is unique; a second instance of any type
            # ( with a different iden ) is rejected.
            await aha.addAhaSvc('w0...', mkinfo('w0', 'fileparser:worker'))
            with self.raises(s_exc.BadArg):
                await aha.addAhaSvc('w1...', mkinfo('w1', 'fileparser:worker'))
            self.len(1, [s async for s in aha.getAhaSvcsByType('fileparser:worker')])

            # unknown types resolve to nothing
            self.none(await aha.getAhaSvcByType('newp'))
            self.none(await aha.getAhaSvc('newp...'))

            # the base cell service type may not register; implementers must
            # override the service type.
            with self.raises(s_exc.BadArg):
                await aha.addAhaSvc('base...', mkinfo('baseiden', 'cell'))

            # a service of a new type registers alongside existing types
            await aha.addAhaSvc('00.axon...', mkinfo('axn', 'axon'))
            await aha.setLeadTerm('axon', '00.axon.synapse', 1)
            self.eq('axn', (await aha.getAhaSvcByType('axon'))['info']['iden'])

            # a type with no leadership term ( no leader ) resolves to nothing
            await aha.addAhaSvc('00.jsonstor...', mkinfo('js0', 'jsonstor'))
            self.none(await aha.getAhaSvcByType('jsonstor'))

            # a leader with a registered mirror ( same iden ) dedups to one
            # instance by type and supports the mirror filter.
            await aha.addAhaSvc('01.axon...', mkinfo('axn', 'axon'))
            self.len(1, [s async for s in aha.getAhaSvcsByType('axon')])
            self.true((await aha.getAhaSvcByType('axon'))['leader'])
            mirror = await aha.getAhaSvcByType('axon', filters={'mirror': True})
            self.false(mirror['leader'])

            # the mirror filter falls back to the leader when no mirror exists
            self.eq('bbb', (await aha.getAhaSvcByType('cortex', filters={'mirror': True}))['info']['iden'])

            # additional axon mirrors ( same iden ) exercise the mirror
            # selection filters: an offline mirror and an online-but-not-ready
            # mirror are both skipped.
            await aha.addAhaSvc('02.axon...', mkinfo('axn', 'axon', online=False))
            notready = mkinfo('axn', 'axon')
            notready['ready'] = False
            await aha.addAhaSvc('03.axon...', notready)

            mirrors = await aha.getAhaSvcMirrors('axn')
            self.len(1, mirrors)
            self.false(mirrors[0]['leader'])
            self.true(mirrors[0]['info']['ready'])

            # resolving a named service with the mirror filter returns a mirror
            axonmirror = await aha.getAhaSvc('00.axon...', filters={'mirror': True})
            self.false(axonmirror['leader'])

            # deleting a service that does not exist is a no-op
            await aha.delAhaSvc('nosuch...')

            # modifying a service that does not exist returns False
            self.false(await aha.modAhaSvcInfo('nosuch...', {'ready': False}))

            # multi-label and non-network-suffixed names do not resolve by type
            self.none(await aha.getAhaSvc('foo.bar...'))
            self.none(await aha.getAhaSvc('nonetwork.example.com'))

            # offline instances are skipped by both by-type lookups
            await aha.addAhaSvc('off.svc...', mkinfo('offiden', 'offtype', online=False))
            self.none(await aha.getAhaSvcByType('offtype'))
            self.len(0, [s async for s in aha.getAhaSvcsByType('offtype')])

            # a service that advertises no type skips uniqueness checks
            notype = mkinfo('ntiden', 'placeholder')
            notype.pop('type')
            await aha.addAhaSvc('notype...', notype)

            # setting a service down that was never registered is a no-op
            await aha.setAhaSvcDown('nosuch...', 'sess00')

            # the AhaApi wrappers expose the by-type lookups over telepath
            async with aha.getLocalProxy() as prox:
                self.eq('bbb', (await prox.getAhaSvcByType('cortex'))['info']['iden'])
                self.len(1, [s async for s in prox.getAhaSvcsByType('cortex')])
                self.none(await prox.getAhaSvcByType('newp'))

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

            conf = {'aha:provision': await aha.addAhaSvcProv('00.cell')}
            cell00 = await aha.enter_context(self.getTestCell(s_test.TestCell00, conf=conf))
            await aha._waitAhaSvcOnline('00.cell...', timeout=10)

            conf = {'aha:provision': await aha.addAhaSvcProv('01.cell')}
            cell01 = await aha.enter_context(self.getTestCell(s_test.TestCell00, conf=conf))
            await aha._waitAhaSvcOnline('00.cell...', timeout=10)

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
            async with aha.waiter(1, 'aha:svc:down', timeout=10):
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
            purl01 = await aha.addAhaSvcProv('1.cell')
            purl02 = await aha.addAhaSvcProv('2.cell')

            cell00 = await aha.enter_context(self.getTestCell(s_test.TestCell00, conf={'aha:provision': purl00}))
            cell01 = await aha.enter_context(self.getTestCell(s_test.TestCell00, conf={'aha:provision': purl01}))
            cell02 = await aha.enter_context(self.getTestCell(s_test.TestCell00, conf={'aha:provision': purl02}))

            await cell01.sync()
            await cell02.sync()

            todo = s_common.todo('getCellInfo')
            items = [item async for item in cell00.callPeerApi(todo)]
            self.len(2, items)

    async def test_lib_aha_peer_genr(self):

        async with self.getTestAha() as aha:

            purl00 = await aha.addAhaSvcProv('0.cell')
            purl01 = await aha.addAhaSvcProv('1.cell')

            cell00 = await aha.enter_context(self.getTestCell(s_test.TestCell00, conf={'aha:provision': purl00}))
            cell01 = await aha.enter_context(self.getTestCell(s_test.TestCell00, conf={'aha:provision': purl01}))

            await cell01.sync()

            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = dict([item async for item in cell00.callPeerGenr(todo)])
            self.len(1, items)

            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = dict([item async for item in cell00.callPeerGenr(todo, timeout=2)])
            self.len(1, items)

    async def test_lib_aha_call_aha_peer_api_isactive(self):

        async with self.getTestAha() as aha0:

            conf = {'aha:provision': await aha0.addAhaSvcProv('00.cell')}
            cell00 = await aha0.enter_context(self.getTestCell(s_test.TestCell00, conf=conf))
            await aha0._waitAhaSvcOnline('00.cell...', timeout=10)

            conf = {'aha:provision': await aha0.addAhaSvcProv('01.cell')}
            cell01 = await aha0.enter_context(self.getTestCell(s_test.TestCell00, conf=conf))
            await aha0._waitAhaSvcOnline('00.cell...', timeout=10)

            await cell01.sync()

            # test active AHA peer
            todo = s_common.todo('getCellInfo')
            items = dict([item async for item in aha0.callAhaPeerApi(cell00.iden, todo, timeout=3)])
            self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

            todo = s_common.todo('getNexusChanges', 0, wait=False)
            items = dict([item async for item in aha0.callAhaPeerGenr(cell00.iden, todo, timeout=3)])
            self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

            async with aha0.getLocalProxy() as proxy0:
                purl = await proxy0.addAhaClone('01.aha.loop.vertex.link', port=0)

            conf1 = {'clone': purl}
            async with self.getTestAha(conf=conf1) as aha1:

                await aha1.sync()

                self.eq(aha0.iden, aha1.iden)
                self.nn(aha1.conf.get('parent'))

                self.true(aha0.isactive)
                self.false(aha1.isactive)

                # test non-active AHA peer
                todo = s_common.todo('getCellInfo')
                items = dict([item async for item in aha1.callAhaPeerApi(cell00.iden, todo, timeout=3)])
                self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

                todo = s_common.todo('getNexusChanges', 0, wait=False)
                items = dict([item async for item in aha1.callAhaPeerGenr(cell00.iden, todo, timeout=3)])
                self.sorteq(items.keys(), ('00.cell.synapse', '01.cell.synapse'))

    async def test_aha_storm_svc_discovery(self):

        async with self.getTestAha() as aha:
            async with await s_base.Base.anit() as base:

                # a storm service capable cell advertises the feature. it is
                # registered before the cortex so the cortex discovers it from
                # the initial AHA service listing.
                svc = await base.enter_context(self.addSvcToAha(aha, '00.ahastormsvc', AhaStormSvcCell))
                self.eq(1, svc.features.get('stormservice'))

                core = await base.enter_context(self.addSvcToAha(aha, '00.cortex', s_cortex.Cortex))

                # a plain ( non storm service ) cell does not advertise the
                # feature and is not auto added by the cortex.
                testcell = await base.enter_context(self.addSvcToAha(aha, '00.testcell', s_test.TestCell00))
                self.notin('stormservice', testcell.features)

                # the cortex discovered the pre-existing storm service from the
                # initial service listing and added it as aha://<type>...
                ssvc = await self.waitCoreStormSvc(core, 'ahastormsvc')
                self.nn(ssvc)
                self.eq('ahastormsvc', ssvc.sdef.get('name'))
                self.eq('aha://ahastormsvc...', ssvc.sdef.get('url'))
                self.eq(s_common.guid(('aha', 'stormsvc', 'ahastormsvc')), ssvc.sdef.get('iden'))

                # the auto added aha://<type>... url resolves to the running
                # service and its packages / commands are usable.
                self.true(await core.callStorm('return($lib.service.wait(ahastormsvc))'))
                self.stormIsInPrint('hello', await core.stormlist('ahastormsvc.hi'))

                # a storm service which registers AFTER the cortex is discovered
                # via a live svc:add topology update.
                svc2 = await base.enter_context(self.addSvcToAha(aha, '00.ahastormsvc2', AhaStormSvc2Cell))
                ssvc2 = await self.waitCoreStormSvc(core, 'ahastormsvc2')
                self.nn(ssvc2)
                self.eq('aha://ahastormsvc2...', ssvc2.sdef.get('url'))
                self.true(await core.callStorm('return($lib.service.wait(ahastormsvc2))'))
                self.stormIsInPrint('hello2', await core.stormlist('ahastormsvc2.hi'))

                # the non storm service cell was not added.
                self.none(core.getStormSvc('testcell00'))

                # re-discovery ( eg a reconnect / re-check-in ) is idempotent
                # and does not add a duplicate service.
                svccount = len(core.getStormSvcs())
                entry = {'info': {'type': 'ahastormsvc', 'features': {'stormservice': 1}}}
                await core._addAhaStormSvc(entry)
                await core._onAhaStormSvc(('svc:add', {'entry': entry}))
                self.len(svccount, core.getStormSvcs())

    async def test_aha_storm_svc_discovery_guards(self):

        # a cortex with no AHA client still runs the discovery active coro,
        # which simply idles until fini.
        async with self.getTestCore() as core:

            self.none(core.ahaclient)

            # a topology message with no service entry is ignored.
            await core._onAhaStormSvc(('svc:add', {}))

            # a service which does not expose a storm service API is skipped.
            await core._addAhaStormSvc({'info': {'type': 'nope', 'features': {}}})
            self.none(core.getStormSvc('nope'))

            # a manually added service using the type as its name blocks the
            # automatic add so we never clobber operator configuration.
            await core.addStormSvc({'name': 'manual', 'url': 'tcp://127.0.0.1:1/svc'})
            await core._addAhaStormSvc({'info': {'type': 'manual', 'features': {'stormservice': 1}}})
            self.none(core.svcsbyiden.get(s_common.guid(('aha', 'stormsvc', 'manual'))))
