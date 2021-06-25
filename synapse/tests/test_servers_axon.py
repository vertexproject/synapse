import hashlib

import synapse.axon as s_axon

import synapse.tests.utils as s_t_utils

asdfhash = hashlib.sha256(b'asdfasdf').digest()

class AxonServerTest(s_t_utils.SynTest):

    async def test_server(self):

        with self.getTestDir() as dirn:
            async with self.withSetLoggingMock() as mock:

                argv = [dirn,
                        '--telepath', 'tcp://127.0.0.1:0/',
                        '--https', '0',
                        '--name', 'teleaxon']

                async with await s_axon.Axon.initFromArgv(argv,) as axon:
                    async with axon.getLocalProxy() as proxy:
                        async with await proxy.upload() as fd:
                            await fd.write(b'asdfasdf')
                            await fd.save()

                    self.true(axon.dmon.shared.get('teleaxon') is axon)

                # And data persists...
                async with await s_axon.Axon.initFromArgv(argv,) as axon:
                    async with axon.getLocalProxy() as proxy:
                        self.true(await proxy.has(asdfhash))
