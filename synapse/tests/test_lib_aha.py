import contextlib

import synapse.telepath as s_telepath

import synapse.lib.aha as s_aha

import synapse.tests.utils as s_test

class AhaTest(s_test.SynTest):

    @contextlib.asynccontextmanager
    async def getTestAha(self):
        with self.getTestDir() as dirn:
            async with await s_aha.AhaCell.anit(dirn) as aha:
                yield aha

    async def test_lib_aha(self):

        async with self.getTestAha() as aha:

            host, port = await aha.dmon.listen('tcp://127.0.0.1:0')
            await aha.auth.rootuser.setPasswd('hehehaha')

            wait00 = aha.waiter(1, 'aha:svcadd')
            conf = {
                'aha:name': 'cryo',
                'aha:network': 'mynet',
                'aha:registry': f'tcp://root:hehehaha@127.0.0.1:{port}',
                'dmon:listen': 'tcp://0.0.0.0:0/',
            }
            async with self.getTestCryo(conf=conf) as cryo:

                await cryo.auth.rootuser.setPasswd('secret')

                await wait00.wait(timeout=2)

                async with await s_telepath.openurl('aha://root:secret@mynet/cryo') as proxy:
                    self.nn(await proxy.getCellIden())

            wait01 = aha.waiter(1, 'aha:svcadd')
            conf = {
                'aha:name': 'cryo',
                'aha:registry': f'tcp://root:hehehaha@127.0.0.1:{port}',
                'dmon:listen': 'tcp://0.0.0.0:0/',
            }
            async with self.getTestCryo(conf=conf) as cryo:

                await cryo.auth.rootuser.setPasswd('secret')

                await wait01.wait(timeout=2)

                async with await s_telepath.openurl('aha://root:secret@cryo') as proxy:
                    self.nn(await proxy.getCellIden())

                svcs = [x async for x in aha.getAhaSvcs()]
                self.len(1, svcs)
                self.eq('cryo', svcs[0]['name'])
