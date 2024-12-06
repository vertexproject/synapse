import os
import shutil

from unittest import mock

import synapse.common as s_common
import synapse.lib.cell as s_cell

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

    async def test_aha_mirrors(self):

        async with self.getTestAha() as aha:

            waiter = aha.waiter(2, 'aha:svcadd')

            conf0 = {'aha:provision': await aha.addAhaSvcProv('mirror0')}
            conf1 = {'aha:provision': await aha.addAhaSvcProv('mirror1')}

            ahaurl = aha.getLocalUrl()

            async with self.getTestCell(s_cell.Cell, conf=conf0) as cell0:

                async with self.getTestCell(s_cell.Cell, conf=conf1) as cell1:

                    self.true(await waiter.wait(timeout=6))

                    argv = ['--url', ahaurl]
                    retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                    self.eq(retn, 0)
                    outp.expect('Mirror: mirror1')
                    outp.expect('  Status: ready')

                    argv = ['--url', ahaurl, '--timeout', '30']
                    retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                    self.eq(retn, 0)

                    argv = ['--url', 'tcp://newp:1234/']
                    retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                    self.eq(retn, 1)
                    outp.expect('ERROR:')

            async with self.getTestCore() as core:
                curl = core.getLocalUrl()
                argv = ['--url', curl]
                retn, outp = await self.execToolMain(s_a_mirror.main, argv)
                self.eq(1, retn)
                outp.expect(f'Service at {curl} is not an Aha server')
