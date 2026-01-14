import hashlib

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.msgpack as s_msgpack

import synapse.tools.cortex.feed as s_feed

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
                        '--summary',
                        jsonlfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)
                outp.expect('Warning: --summary and --extend-model are only supported')

                argv = ['--cortex', curl,
                        '--chunksize', '3',
                        jsonlfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)

            nodes = await core.nodes('test:int')
            self.len(20, nodes)

            with mock.patch('synapse.telepath.Proxy._getSynVers', self._getOldSynVers):
                await s_feed.main(argv, outp=outp)
                outp.expect(f'Cortex version 0.0.0 is outside of synapse.tools.cortex.feed supported range')

    async def test_synnodes_offset(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
            curl = f'tcp://icanadd:secret@{host}:{port}/'

            meta = {
                'type': 'meta',
                'vers': 1,
                'forms': {'test:int': 20},
                'count': 20,
                'synapse_ver': '3.0.0',
            }

            with self.getTestDir() as dirn:

                mpkfp = s_common.genpath(dirn, 'podes.mpk')
                with s_common.genfile(mpkfp) as fd:
                    for i in range(20):
                        pode = (('test:int', i), {})
                        fd.write(s_msgpack.en(pode))

                argv = ['--cortex', curl,
                        '--chunksize', '4',
                        '--offset', '15',
                        mpkfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)
                outp.expect('not a valid syn.nodes file')

                # reset file with meta
                with s_common.genfile(mpkfp) as fd:
                    fd.write(s_msgpack.en(meta))
                    for i in range(20):
                        fd.write(s_msgpack.en((('test:int', i), {})))
                self.eq(await s_feed.main(argv, outp=outp), 0)

                # Sad path catch
                outp = self.getTestOutp()
                argv.append(mpkfp)
                self.eq(await s_feed.main(argv, outp=outp), 1)
                self.true(outp.expect('Cannot start from a arbitrary offset for more than 1 file.'))

            nodes = await core.nodes('test:int')
            self.len(4, nodes)

    async def test_synnodes_view(self):

        async with self.getTestCore() as core:
            await self.addCreatorDeleterRoles(core)

            icanadd = await core.auth.getUserByName('icanadd')
            creator = await core.auth.getRoleByName('creator')

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
            curl = f'tcp://icanadd:secret@{host}:{port}/'

            oldview = await core.callStorm('$view = $lib.view.get() return($view.iden)')
            newview = await core.callStorm('$view = $lib.view.get() return($view.fork().iden)')
            badview = hashlib.md5(newview.encode(), usedforsecurity=False).hexdigest()

            meta = {
                'type': 'meta',
                'vers': 1,
                'forms': {'test:int': 20},
                'count': 20,
                'synapse_ver': '3.0.0',
                'created': 1747831406876525,
            }

            with self.getTestDir() as dirn:

                mpkfp = s_common.genpath(dirn, 'podes.mpk')
                with s_common.genfile(mpkfp) as fd:
                    fd.write(s_msgpack.en(meta))
                    for i in range(20):
                        pode = (('test:int', i), {})
                        fd.write(s_msgpack.en(pode))

                base = ['--cortex', curl]

                argv = base + ['--view', newview, mpkfp]
                outp = self.getTestOutp()

                # perms are still a thing
                await icanadd.revoke(creator.iden)
                with self.raises(s_exc.AuthDeny):
                    await s_feed.main(argv, outp=outp)
                await icanadd.grant(creator.iden)

                nodes = await core.nodes('test:int', opts={'view': newview})
                self.len(0, nodes)
                nodes = await core.nodes('test:int', opts={'view': oldview})
                self.len(0, nodes)

                await icanadd.addRule((True, ('view', 'read')))

                # now actually do the ingest w/chunking
                argv = base + ['--chunksize', '10', '--view', newview, mpkfp]
                self.eq(await s_feed.main(argv, outp=outp), 0)
                nodes = await core.nodes('test:int', opts={'view': newview})
                self.len(20, nodes)

                # sad path
                outp = self.getTestOutp()
                argv = base + ['--view', badview, mpkfp]
                with self.raises(s_exc.NoSuchView):
                    await s_feed.main(argv, outp=outp)

            nodes = await core.nodes('test:int', opts={'view': newview})
            self.len(20, nodes)

            nodes = await core.nodes('test:int', opts={'view': oldview})
            self.len(0, nodes)

    async def test_synnodes_metadata(self):

        async with self.getTestCore() as core:

            await self.addCreatorDeleterRoles(core)

            host, port = await core.dmon.listen('tcp://127.0.0.1:0/')
            curl = f'tcp://icanadd:secret@{host}:{port}/'

            meta = {
                'count': 1,
                'created': 1747831406876525,
                'creatorname': 'root',
                'creatoriden': core.auth.rootuser.iden,
                'edges': {},
                'vers': 1,
                'forms': {'_baz:haha': 1},
                'query': '_baz:haha',
                'synapse_ver': '3.0.0',
                'type': 'meta'
            }

            with self.getTestDir() as dirn:

                mpkfp = s_common.genpath(dirn, 'syn.nodes')
                with s_common.genfile(mpkfp) as fd:
                    fd.write(s_msgpack.en(meta))
                    fd.write(s_msgpack.en((('_baz:haha', 'newp'), {})))

                argv = ['--cortex', curl,
                        '--summary',
                        mpkfp]

                outp = self.getTestOutp()
                self.eq(await s_feed.main(argv, outp=outp), 0)
                outp.expect('Summary for [syn.nodes]:')
                outp.expect('Count: 1')
