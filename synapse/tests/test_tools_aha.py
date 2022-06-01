import synapse.lib.cell as s_cell

import synapse.tests.utils as s_t_utils

import synapse.tools.aha.list as s_a_list
import synapse.tools.aha.easycert as s_a_easycert

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
                    outp.expect('Service              network')
                    outp.expect('cell0                demo.net')
                    outp.expect('cell1                example.net')

                    argv = [ahaurl, 'demo.net']
                    retn, outp = await self.execToolMain(s_a_list._main, argv)
                    self.eq(retn, 0)
                    outp.expect('Service              network')
                    outp.expect('cell0                demo.net')
                    self.false(outp.expect('cell1                example.net', throw=False))

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
