import os
import shutil

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cell as s_cell
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils

import synapse.tools.aha.list as s_a_list
import synapse.tools.aha.clone as s_a_clone
import synapse.tools.aha.enroll as s_a_enroll
import synapse.tools.aha.mirror as s_a_mirror
import synapse.tools.aha.easycert as s_a_easycert
import synapse.tools.aha.provision.user as s_a_provision_user

class AhaToolsTest(s_t_utils.SynTest):

    async def test_aha_list(self):

        async with self.getTestAha() as aha:

            waiter = aha.waiter(2, 'aha:svcadd')
            conf0 = {'aha:provision': await aha.addAhaSvcProv('cell0')}

            provinfo = {'aha:network': 'example.net'}
            conf1 = {'aha:provision': await aha.addAhaSvcProv('cell1', provinfo=provinfo)}

            ahaurl = aha.getLocalUrl()

            async with self.getTestCell(s_cell.Cell, conf=conf0) as cell0:

                async with self.getTestCell(s_cell.Cell, conf=conf1) as cell1:

                    self.true(await waiter.wait(timeout=6))

                    argv = [ahaurl]
                    retn, outp = await self.execToolMain(s_a_list._main, argv)
                    self.eq(retn, 0)

                    outp.expect('''
                        Service              network                        leader
                        cell0                synapse                        None
                        cell1                example.net                    None
                    ''', whitespace=False)

                    argv = [ahaurl, 'demo.net']
                    retn, outp = await self.execToolMain(s_a_list._main, argv)
                    self.eq(retn, 0)
                    outp.expect('Service              network', whitespace=False)
                    outp.expect('cell0                demo.net', whitespace=False)

        async with self.getTestCore() as core:
            curl = core.getLocalUrl()
            argv = [curl]
            retn, outp = await self.execToolMain(s_a_list._main, argv)
            self.eq(1, retn)
            outp.expect(f'Service at {curl} is not an Aha server')

    async def test_aha_easycert(self):

        ephemeral_address = 'tcp://0.0.0.0:0/'
        async with self.getTestAha(conf={'auth:passwd': 'root',
                                         'dmon:listen': ephemeral_address}) as aha:
            _, port = aha.sockaddr
            ahaurl = f'tcp://root:root@127.0.0.1:{port}'

            with self.getTestDir() as dirn:
                argvbase = ['-a', ahaurl, '--certdir', dirn]
                argv = argvbase + ['--ca', 'demo.net']
                retn, outp = await self.execToolMain(s_a_easycert._main, argv)
                self.eq(retn, 0)
                outp.expect('Saved CA cert')
                outp.expect('cas/demo.net.crt')

                argv = argvbase + ['--server', '--server-sans', 'DNS:beeper.demo.net,DNS:booper.demo.net',
                                   '--network', 'demo.net', 'beep.demo.net']
                retn, outp = await self.execToolMain(s_a_easycert._main, argv)
                self.eq(retn, 0)
                outp.expect('key saved')
                outp.expect('hosts/beep.demo.net.key')
                outp.expect('crt saved')
                outp.expect('hosts/beep.demo.net.crt')

                argv = argvbase + ['--network', 'demo.net', 'mallory@demo.net']
                retn, outp = await self.execToolMain(s_a_easycert._main, argv)
                self.eq(retn, 0)
                outp.expect('key saved')
                outp.expect('users/mallory@demo.net.key')
                outp.expect('crt saved')
                outp.expect('users/mallory@demo.net.crt')

    async def test_aha_enroll(self):

        async with self.getTestAha() as aha:

            argv = ['--url', aha.getLocalUrl(), '01.aha.loop.vertex.link']
            retn, outp = await self.execToolMain(s_a_clone.main, argv)
            self.eq(retn, 0)
            self.isin('one-time use URL:', str(outp))

            argv = ['--url', aha.getLocalUrl(), '01.aha.loop.vertex.link', '--only-url']
            retn, outp = await self.execToolMain(s_a_clone.main, argv)
            self.eq(retn, 0)
            self.notin('one-time use URL:', str(outp))

            argv = ['--url', 'newp://1.2.3.4', '01.aha.loop.vertex.link']
            retn, outp = await self.execToolMain(s_a_clone.main, argv)
            self.eq(retn, 1)
            self.isin('ERROR: Invalid URL scheme: newp', str(outp))

            argv = ['--url', aha.getLocalUrl(), 'visi']
            retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
            self.isin('one-time use URL:', str(outp))

            provurl = str(outp).split(':', 1)[1].strip()
            with self.getTestSynDir() as syndir:

                capath = s_common.genpath(syndir, 'certs', 'cas', 'synapse.crt')
                crtpath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.crt')
                keypath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.crt')

                retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))
                self.eq(0, retn)

                for path in (capath, crtpath, keypath):
                    self.true(os.path.isfile(path))
                    self.gt(os.path.getsize(path), 0)

                teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                self.eq(teleyaml.get('version'), 1)
                self.len(1, teleyaml.get('aha:servers'))

                shutil.rmtree(s_common.genpath(syndir, 'certs'))

                argv = ['--again', '--url', aha.getLocalUrl(), 'visi']
                retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
                self.eq(retn, 0)
                self.isin('one-time use URL:', str(outp))

                provurl = str(outp).split(':', 1)[1].strip()

                retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))

                # Just return the URL
                retn, outp = await self.execToolMain(s_a_provision_user.main, argv + ['--only-url'])
                self.eq(retn, 0)
                self.notin('one-time use URL:', str(outp))
                self.isin('ssl://', str(outp))

            with self.getTestSynDir() as syndir:

                argv = ['--again', '--url', aha.getLocalUrl(), 'visi']
                retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
                self.eq(retn, 0)
                provurl = str(outp).split(':', 1)[1].strip()

                capath = s_common.genpath(syndir, 'certs', 'cas', 'synapse.crt')
                crtpath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.crt')
                keypath = s_common.genpath(syndir, 'certs', 'users', 'visi@synapse.key')

                for path in (capath, crtpath, keypath):
                    s_common.genfile(path)

                retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))
                self.eq(0, retn)

                for path in (capath, crtpath, keypath):
                    self.gt(os.path.getsize(path), 0)

                teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                self.eq(teleyaml.get('version'), 1)

    async def test_aha_mirror(self):

        async with self.getTestAha() as aha:

            base_svcinfo = {
                'iden': 'test_iden',
                'leader': 'leader',
                'urlinfo': {
                    'scheme': 'tcp',
                    'host': '127.0.0.1',
                    'port': 0,
                    'hostname': 'test.host'
                }
            }

            conf_no_iden = {'aha:provision': await aha.addAhaSvcProv('no.iden')}
            async with self.getTestCell(s_cell.Cell, conf=conf_no_iden) as cell_no_iden:
                svcinfo = {k: v for k, v in base_svcinfo.items() if k != 'iden'}
                await aha.addAhaSvc('no.iden', svcinfo)

                argv = ['--url', aha.getLocalUrl()]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 0)
                outp.expect('Service Mirror Groups:')
                self.notin('no.iden', str(outp))

            conf_no_host = {'aha:provision': await aha.addAhaSvcProv('no.host')}
            async with self.getTestCell(s_cell.Cell, conf=conf_no_host) as cell_no_host:
                svcinfo = dict(base_svcinfo)
                svcinfo['urlinfo'] = {k: v for k, v in base_svcinfo['urlinfo'].items() if k != 'hostname'}
                await aha.addAhaSvc('no.host', svcinfo)

                argv = ['--url', aha.getLocalUrl()]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 0)
                outp.expect('Service Mirror Groups:')
                self.notin('no.host', str(outp))

            conf_no_leader = {'aha:provision': await aha.addAhaSvcProv('no.leader')}
            async with self.getTestCell(s_cell.Cell, conf=conf_no_leader) as cell_no_leader:
                svcinfo = {k: v for k, v in base_svcinfo.items() if k != 'leader'}
                await aha.addAhaSvc('no.leader', svcinfo)

                argv = ['--url', aha.getLocalUrl()]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 0)
                outp.expect('Service Mirror Groups:')
                self.notin('no.leader', str(outp))

            conf_no_primary = {'aha:provision': await aha.addAhaSvcProv('no.primary')}
            async with self.getTestCell(s_cell.Cell, conf=conf_no_primary) as cell_no_primary:
                svcinfo = dict(base_svcinfo)
                svcinfo['urlinfo']['hostname'] = 'nonexistent.host'
                await aha.addAhaSvc('no.primary', svcinfo)

            async with aha.waiter(3, 'aha:svcadd', timeout=10):

                conf = {'aha:provision': await aha.addAhaSvcProv('00.cell')}
                cell00 = await aha.enter_context(self.getTestCell(conf=conf))

                conf = {'aha:provision': await aha.addAhaSvcProv('01.cell', {'mirror': 'cell'})}
                cell01 = await aha.enter_context(self.getTestCell(conf=conf))

                await cell01.sync()

            ahaurl = aha.getLocalUrl()

            argv = ['--url', ahaurl]
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 0)
            outp.expect('Service Mirror Groups:')
            outp.expect('00.cell.synapse')
            outp.expect('01.cell.synapse')
            outp.expect('Group Status: In Sync')

            argv = ['--url', ahaurl, '--timeout', '30']
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 0)

            with mock.patch('synapse.telepath.Proxy._hasTeleFeat',
                          return_value=False):
                argv = ['--url', ahaurl]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 1)
                outp.expect(f'Service at {ahaurl} does not support the required callpeers feature.')

            with mock.patch('synapse.telepath.Proxy._hasTeleFeat',
                          side_effect=s_exc.NoSuchMeth(name='_hasTeleFeat')):
                argv = ['--url', ahaurl]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(retn, 1)
                outp.expect(f'Service at {ahaurl} does not support the required callpeers feature.')

            argv = ['--url', 'tcp://newp:1234/']
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 1)
            outp.expect('ERROR:')

            async def mockCellInfo():
                return {
                    'cell': {'ready': True, 'nexsindx': 10, 'uplink': None},
                    'synapse': {'verstring': s_version.verstring},
                }

            async def mockOutOfSyncCellInfo():
                return {
                    'cell': {'ready': True, 'nexsindx': 5, 'uplink': cell00.iden},
                    'synapse': {'verstring': s_version.verstring},
                }

            with mock.patch.object(cell00, 'getCellInfo', mockCellInfo):
                with mock.patch.object(cell01, 'getCellInfo', mockOutOfSyncCellInfo):
                    async def mock_call_aha(*args, **kwargs):
                        todo = args[1]
                        if todo[0] == 'waitNexsOffs':
                            yield ('00.cell.synapse', (True, True))
                            yield ('01.cell.synapse', (True, True))
                        elif todo[0] == 'getCellInfo':
                            if not hasattr(mock_call_aha, 'called'):
                                mock_call_aha.called = True
                                yield ('00.cell.synapse', (True, await mockCellInfo()))
                                yield ('01.cell.synapse', (True, await mockOutOfSyncCellInfo()))
                            else:
                                yield ('00.cell.synapse', (True, await mockCellInfo()))
                                yield ('01.cell.synapse', (True, await mockCellInfo()))

                    with mock.patch.object(aha, 'callAhaPeerApi', mock_call_aha):
                        argv = ['--url', ahaurl, '--wait']
                        retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                        self.eq(retn, 0)
                        outp.expect('Group Status: Out of Sync')
                        outp.expect('Updated status:')
                        outp.expect('Group Status: In Sync')

            with mock.patch.object(cell00, 'getCellInfo', mockCellInfo):
                with mock.patch.object(cell01, 'getCellInfo', mockOutOfSyncCellInfo):
                    argv = ['--url', ahaurl, '--timeout', '1']
                    retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                    self.eq(retn, 0)
                    outp.expect('Group Status: Out of Sync')

            async with self.getTestCore() as core:
                curl = core.getLocalUrl()
                argv = ['--url', curl]
                with mock.patch('synapse.telepath.Proxy._hasTeleFeat',
                          return_value=True):
                    retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                    self.eq(1, retn)
                    outp.expect(f'Service at {curl} is not an Aha server')

            async with aha.waiter(1, 'aha:svcadd', timeout=10):

                conf = {'aha:provision': await aha.addAhaSvcProv('02.cell', {'mirror': 'cell'})}
                cell02 = await aha.enter_context(self.getTestCell(conf=conf))
                await cell02.sync()

            async def mock_failed_api(*args, **kwargs):
                yield ('00.cell.synapse', (True, {'cell': {'ready': True, 'nexsindx': 10}}))
                yield ('01.cell.synapse', (False, 'error'))
                yield ('02.cell.synapse', (True, {'cell': {'ready': True, 'nexsindx': 12}}))

            with mock.patch.object(aha, 'callAhaPeerApi', mock_failed_api):
                argv = ['--url', ahaurl, '--timeout', '1']
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                outp.expect('00.cell.synapse                          leader     True     True    127.0.0.1', whitespace=False)
                outp.expect('nexsindx      10', whitespace=False)
                outp.expect('02.cell.synapse                          leader     True     True    127.0.0.1', whitespace=False)
                outp.expect('nexsindx      12', whitespace=False)
                outp.expect('01.cell.synapse                          <unknown>  True     True', whitespace=False)
                outp.expect('<unknown>    <unknown>', whitespace=False)

        self.eq(s_a_mirror.timeout_type('30'), 30)
        self.eq(s_a_mirror.timeout_type('0'), 0)

        with self.raises(s_exc.BadArg) as cm:
            s_a_mirror.timeout_type('-1')
        self.isin('is not a valid non-negative integer', cm.exception.get('mesg'))

        with self.raises(s_exc.BadArg) as cm:
            s_a_mirror.timeout_type('foo')
        self.isin('is not a valid non-negative integer', cm.exception.get('mesg'))

        synerr = s_exc.SynErr(mesg='Oof')
        with mock.patch('synapse.telepath.openurl', side_effect=synerr):
            argv = ['--url', 'tcp://test:1234/']
            retn, outp = await self.execToolMain(s_a_mirror.main, argv)
            self.eq(retn, 1)
            outp.expect('ERROR: Oof')
