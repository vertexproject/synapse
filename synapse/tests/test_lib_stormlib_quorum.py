import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_test

class StormLibQuorumTest(s_test.SynTest):

    async def test_stormlib_quorum(self):

        async with self.getTestCore() as core:

            # for coverage...
            self.none(core.view.getParentQuorum())

            visi = await core.auth.addUser('visi')
            whippit = await core.auth.addUser('whippit')

            await core.auth.allrole.addRule((True, ('view', 'add')))
            await core.auth.allrole.addRule((True, ('view', 'read')))

            vertex = await core.auth.addRole('vertex')

            await visi.grant(vertex.iden)
            await whippit.grant(vertex.iden)

            msgs = await core.stormlist('quorum.merge.list', opts={'user': whippit.iden})
            self.stormIsInPrint('No pending merge requests.', msgs)

            msgs = await core.stormlist('quorum.merge.list --todo', opts={'user': whippit.iden})
            self.stormIsInPrint('Nothing to do. Go grab some coffee!', msgs)

            await core.callStorm('''
                $lib.view.get().set(quorum, ({
                    "roles": [$vertex],
                    "count": 2,
                }))
            ''', opts={'vars': {'vertex': vertex.iden}})

            opts = {'user': visi.iden}

            fork00 = await core.callStorm('return($lib.view.get().fork(foo).iden)', opts=opts)
            fork01 = await core.callStorm('return($lib.view.get().fork(bar).iden)', opts=opts)
            fork02 = await core.callStorm('return($lib.view.get().fork(baz).iden)', opts=opts)

            await core.callStorm('''
                $lib.view.get($iden).setMergeRequest(({}))
            ''', opts={'user': visi.iden, 'vars': {'iden': fork00}})

            await core.callStorm('''
                $lib.view.get($iden).setMergeRequest(({}))
            ''', opts={'user': visi.iden, 'vars': {'iden': fork01}})

            await core.callStorm('''
                $lib.view.get($iden).setMergeVote()
            ''', opts={'user': whippit.iden, 'vars': {'iden': fork01}})

            # ensure we skip our own requests with --todo
            msgs = await core.stormlist('quorum.merge.list --todo', opts={'user': visi.iden})
            self.stormIsInPrint('Nothing to do. Go grab some coffee!', msgs)

            msgs = await core.stormlist('quorum.merge.list', opts={'user': whippit.iden})
            self.stormIsInPrint('foo visi', msgs, whitespace=False)
            self.stormIsInPrint('bar visi', msgs, whitespace=False)
            self.stormNotInPrint('baz', msgs)

            msgs = await core.stormlist('quorum.merge.list --todo', opts={'user': whippit.iden})
            self.stormIsInPrint('foo visi', msgs, whitespace=False)
            self.stormNotInPrint('bar', msgs)
            self.stormNotInPrint('baz', msgs)
