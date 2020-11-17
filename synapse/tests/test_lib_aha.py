import contextlib

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.aha as s_aha

import synapse.tests.utils as s_test
import synapse.servers.aha as s_servers_aha

class AhaTest(s_test.SynTest):

    @contextlib.asynccontextmanager
    async def getTestAha(self):
        with self.getTestDir() as dirn:
            async with await s_aha.AhaCell.anit(dirn) as aha:
                yield aha

    async def test_lib_aha(self):

        client = await s_telepath.addAhaUrl('newp://newp@newp')
        client = await s_telepath.addAhaUrl('newp://newp@newp')

        with self.raises(s_exc.NoSuchName):
            await s_telepath.getAhaProxy({'host': 'hehe'})

        await s_telepath.delAhaUrl('newp://newp@newp')
        self.len(1, s_telepath.aha_clients)
        await s_telepath.delAhaUrl('newp://newp@newp')
        self.len(0, s_telepath.aha_clients)

        self.eq(0, await s_telepath.delAhaUrl('newp'))

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

                with self.raises(s_exc.NoSuchName):
                    await s_telepath.getAhaProxy({'host': 'hehe'})

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

            async with await s_telepath.openurl(f'tcp://root:hehehaha@127.0.0.1:{port}') as ahaproxy:
                svcs = [x async for x in ahaproxy.getAhaSvcs()]
                self.len(1, svcs)
                self.eq('cryo', svcs[0]['name'])
