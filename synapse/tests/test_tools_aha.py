import os
import shutil

from unittest import mock

import synapse.common as s_common
import synapse.lib.cell as s_cell

import synapse.tests.utils as s_t_utils

import synapse.tools.aha.list as s_a_list
import synapse.tools.aha.enroll as s_a_enroll
import synapse.tools.aha.easycert as s_a_easycert
import synapse.tools.aha.provision.user as s_a_provision_user

class AhaToolsTest(s_t_utils.SynTest):

    async def test_aha_list(self):

        ephemeral_address = 'tcp://0.0.0.0:0/'
        async with self.getTestAha(conf={'auth:passwd': 'root',
                                         'dmon:listen': ephemeral_address}) as aha:
            _, port = aha.sockaddr
            ahaurl = f'tcp://root:root@127.0.0.1:{port}'
            conf0 = {
                'aha:registry': ahaurl,
                'aha:name': 'cell0',
                'aha:network': 'demo.net',
                'dmon:listen': ephemeral_address,
            }
            conf1 = {
                'aha:registry': ahaurl,
                'aha:name': 'cell1',
                'aha:network': 'example.net',
                'dmon:listen': ephemeral_address,
            }
            waiter = aha.waiter(2, 'aha:svcadd')
            async with self.getTestCell(s_cell.Cell, conf=conf0) as cell0:
                async with self.getTestCell(s_cell.Cell, conf=conf1) as cell1:
                    self.true(await waiter.wait(timeout=6))
                    argv = [ahaurl]
                    retn, outp = await self.execToolMain(s_a_list._main, argv)
                    self.eq(retn, 0)
                    outp.expect('Service              network                        leader')
                    outp.expect('cell0                demo.net                       None')
                    outp.expect('cell1                example.net                    None')

                    argv = [ahaurl, 'demo.net']
                    retn, outp = await self.execToolMain(s_a_list._main, argv)
                    self.eq(retn, 0)
                    outp.expect('Service              network')
                    outp.expect('cell0                demo.net')
                    self.false(outp.expect('cell1                example.net', throw=False))

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

        with self.getTestDir() as dirn:

            conf = {
                'aha:name': 'aha',
                'aha:network': 'loop.vertex.link',
                'provision:listen': 'ssl://aha.loop.vertex.link:0',
                'dmon:listen': 'tcp://0.0.0.0:0'
            }
            async with self.getTestAha(dirn=dirn, conf=conf) as aha:

                addr, port = aha.provdmon.addr
                aha.conf['provision:listen'] = f'ssl://aha.loop.vertex.link:{port}'

                host_, ahaport = aha.sockaddr
                self.eq(aha._getAhaUrls(), [f'ssl://aha.loop.vertex.link:{ahaport}'])

                argv = ['--url', aha.getLocalUrl(), 'visi']
                retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
                self.isin('one-time use URL:', str(outp))

                provurl = str(outp).split(':', 1)[1].strip()
                with self.getTestSynDir() as syndir:

                    capath = s_common.genpath(syndir, 'certs', 'cas', 'loop.vertex.link.crt')
                    crtpath = s_common.genpath(syndir, 'certs', 'users', 'visi@loop.vertex.link.crt')
                    keypath = s_common.genpath(syndir, 'certs', 'users', 'visi@loop.vertex.link.key')

                    for path in (capath, crtpath, keypath):
                        s_common.genfile(path)

                    yamlpath = s_common.genpath(syndir, 'telepath.yaml')
                    s_common.yamlsave({'aha:servers': 'cell://aha'}, yamlpath)

                    retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))
                    self.eq(0, retn)

                    for path in (capath, crtpath, keypath):
                        self.gt(os.path.getsize(path), 0)

                    teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                    self.eq(teleyaml.get('version'), 1)
                    self.eq(teleyaml.get('aha:servers'), ('cell://aha', f'ssl://visi@aha.loop.vertex.link:{ahaport}'))

                    shutil.rmtree(s_common.genpath(syndir, 'certs'))

                    def _strUrl(self):
                        return 'ssl://aha.loop.vertex.link'

                    with mock.patch('synapse.lib.aha.AhaCell._getAhaUrls', _strUrl):

                        argv = ['--again', '--url', aha.getLocalUrl(), 'visi']
                        retn, outp = await self.execToolMain(s_a_provision_user.main, argv)
                        self.eq(retn, 0)
                        self.isin('one-time use URL:', str(outp))

                        provurl = str(outp).split(':', 1)[1].strip()

                        retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))

                        servers = ['cell://aha',
                                   'ssl://visi@aha.loop.vertex.link',
                                   f'ssl://visi@aha.loop.vertex.link:{ahaport}']

                        teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                        self.sorteq(teleyaml.get('aha:servers'), servers)

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

                    capath = s_common.genpath(syndir, 'certs', 'cas', 'loop.vertex.link.crt')
                    crtpath = s_common.genpath(syndir, 'certs', 'users', 'visi@loop.vertex.link.crt')
                    keypath = s_common.genpath(syndir, 'certs', 'users', 'visi@loop.vertex.link.key')

                    for path in (capath, crtpath, keypath):
                        s_common.genfile(path)

                    yamlpath = s_common.genpath(syndir, 'telepath.yaml')
                    s_common.yamlsave({'aha:servers': ['cell://aha', 'cell://foo', ['cell://bar']]}, yamlpath)

                    retn, outp = await self.execToolMain(s_a_enroll.main, (provurl,))
                    self.eq(0, retn)

                    for path in (capath, crtpath, keypath):
                        self.gt(os.path.getsize(path), 0)

                    teleyaml = s_common.yamlload(syndir, 'telepath.yaml')
                    self.eq(teleyaml.get('version'), 1)
                    self.eq(teleyaml.get('aha:servers'), ('cell://aha', 'cell://foo', ('cell://bar',),
                                                          f'ssl://visi@aha.loop.vertex.link:{ahaport}'))
