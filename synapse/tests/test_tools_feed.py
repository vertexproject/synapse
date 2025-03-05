import hashlib

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.msgpack as s_msgpack

import synapse.tools.feed as s_feed

import synapse.tests.utils as s_t_utils

class FeedTest(s_t_utils.SynTest):

    def _getOldSynVers(self):
        return (0, 0, 0)

    async def test_synnodes_remote(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

            curl = f'tcp://icanadd:secret@{host}:{port}/'

            with self.getTestDir() as dirn:

                jsonlfp = s_common.genpath(dirn, 'podes.jsonl')
                with s_common.genfile(jsonlfp) as fd:
                    for i in range(20):
                        pode = (('test:int', i), {})
                        _ = fd.write(s_json.dumps(pode, newline=True))

                argv = ['--cortex', curl,
                        '--format', 'syn.nodes',
                        '--modules', 'synapse.tests.utils.TestModule',
                        '--chunksize', '3',
                        jsonlfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)

            nodes = await core.nodes('test:int')
            self.len(20, nodes)

            with mock.patch('synapse.telepath.Proxy._getSynVers', self._getOldSynVers):
                await s_feed.main(argv, outp=outp)
                outp.expect(f'Cortex version 0.0.0 is outside of the feed tool supported range')

    async def test_synnodes_offset(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
            curl = f'tcp://icanadd:secret@{host}:{port}/'

            with self.getTestDir() as dirn:

                mpkfp = s_common.genpath(dirn, 'podes.mpk')
                with s_common.genfile(mpkfp) as fd:
                    for i in range(20):
                        pode = (('test:int', i), {})
                        fd.write(s_msgpack.en(pode))

                argv = ['--cortex', curl,
                        '--format', 'syn.nodes',
                        '--modules', 'synapse.tests.utils.TestModule',
                        '--chunksize', '4',
                        '--offset', '15',
                        mpkfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)

                # Sad path catch
                outp = self.getTestOutp()
                argv.append(mpkfp)
                self.eq(await s_feed.main(argv, outp=outp), 1)
                self.true(outp.expect('Cannot start from a arbitrary offset for more than 1 file.'))

            nodes = await core.nodes('test:int')
            self.len(8, nodes)

    async def test_synnodes_view(self):

        async with self.getTestCore() as core:
            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
            curl = f'tcp://icanadd:secret@{host}:{port}/'

            oldview = await core.callStorm('$view = $lib.view.get() return($view.iden)')
            newview = await core.callStorm('$view = $lib.view.get() return($view.fork().iden)')

            with self.getTestDir() as dirn:

                mpkfp = s_common.genpath(dirn, 'podes.mpk')
                with s_common.genfile(mpkfp) as fd:
                    for i in range(20):
                        pode = (('test:int', i), {})
                        fd.write(s_msgpack.en(pode))

                base = ['--cortex', curl,
                        '--format', 'syn.nodes',
                        '--modules', 'synapse.tests.utils.TestModule']

                argv = base + ['--view', newview, mpkfp]

                outp = self.getTestOutp()
                # perms are still a thing
                with self.raises(s_exc.AuthDeny):
                    await s_feed.main(argv, outp=outp)
                nodes = await core.nodes('test:int', opts={'view': newview})
                self.len(0, nodes)
                nodes = await core.nodes('test:int', opts={'view': oldview})
                self.len(0, nodes)

                icanadd = await core.auth.getUserByName('icanadd')
                await icanadd.addRule((True, ('view', 'read')))
                # now actually do the ingest
                self.eq(await s_feed.main(argv, outp=outp), 0)

                # sad path
                outp = self.getTestOutp()
                badview = hashlib.md5(newview.encode(), usedforsecurity=False).hexdigest()
                argv = base + ['--view', badview, mpkfp]
                with self.raises(s_exc.NoSuchView):
                    await s_feed.main(argv, outp=outp)

            nodes = await core.nodes('test:int', opts={'view': newview})
            self.len(20, nodes)

            nodes = await core.nodes('test:int', opts={'view': oldview})
            self.len(0, nodes)

    async def test_synnodes_json(self):
        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

            curl = f'tcp://icanadd:secret@{host}:{port}/'

            with self.getTestDir() as dirn:

                jsonfp = s_common.genpath(dirn, 'podes.json')
                with s_common.genfile(jsonfp) as fd:
                    podes = [(('test:int', ii), {}) for ii in range(20)]
                    s_json.dump(podes, fd)

                argv = ['--cortex', curl,
                        '--format', 'syn.nodes',
                        '--modules', 'synapse.tests.utils.TestModule',
                        '--chunksize', '3',
                        jsonfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)

            nodes = await core.nodes('test:int')
            self.len(20, nodes)
