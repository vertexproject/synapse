import hashlib
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.msgpack as s_msgpack
import synapse.lib.provenance as s_provenance

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ProvenanceTest(s_t_utils.SynTest):

    async def test_prov(self):

        s_provenance.reset()

        async with self.getTestCore() as real, real.getLocalProxy() as core:

            # Non-existent iden
            self.none(await core.getProvStack('abcd'))

            await real.view.addTrigger({
                'cond': 'node:add',
                'form': 'test:str',
                'storm': '[ test:int=1 ]',
            })
            self.eq(1, await core.count('[ test:str=foo ]'))
            self.eq(1, await core.count('test:int'))

            self.eq(0, await core.count('test:int | delnode'))

            splices = await alist(core.splices(None, 1000))

            self.len(9, splices)
            idens = [splice[1][1].get('prov') for splice in splices]

            # source splices
            self.eq(idens[0], idens[1])
            self.eq(idens[0], idens[2])

            # test:str add
            self.eq(idens[3], idens[4])

            # trigger
            self.eq(idens[5], idens[6])

            # test:int delnode
            self.eq(idens[7], idens[8])

            provs = [await core.getProvStack(iden) for iden in idens]

            # The meta:source splices
            self.eq(({}, (('init', {'meth': '_initCoreMods'}),)), provs[0])

            # The test:str splices
            prov = provs[3][1]
            rootiden = prov[0][1]['user']
            s2 = ('storm', {'q': '[ test:str=foo ]', 'user': rootiden})
            self.eq((s2, ), prov)

            # Validate that the iden calc itself is correct
            rawprov = ({}, [('storm', (('q', '[ test:str=foo ]'), ('user', rootiden)))])
            hash = hashlib.md5(s_msgpack.en(rawprov)).hexdigest()
            self.eq(hash, idens[3])

            # The trigger splices
            prov = provs[5][1]
            s3 = ('trig', {'cond': 'node:add', 'form': 'test:str', 'tag': None, 'prop': None})
            s4 = ('storm', {'q': '[ test:int=1 ]', 'user': rootiden})
            self.eq((s2, s3, s4), prov)

            # prop:del/node:del
            prov = provs[7][1]
            ds2 = ('storm', {'q': 'test:int | delnode', 'user': rootiden})
            ds3 = ('stormcmd', {'name': 'delnode'})
            self.eq((ds2, ds3), prov)

            # Test the streaming API
            provstacks = await alist(core.provStacks(0, 1000))
            correct = [(idens[0], provs[0]), (idens[5], provs[5]), (idens[3], provs[3]), (idens[7], provs[7])]
            self.eq(provstacks, correct)

            # Force recursion exception to be thrown

            with mock.patch.object(s_provenance, 'ProvenanceStackLimit', 10):
                q = '.created ' + '| uniq' * 20
                with self.raises(s_exc.RecursionLimitHit) as cm:
                    await real.nodes(q)

            self.eq(cm.exception.get('type'), 'stormcmd')
            self.eq(cm.exception.get('info'), {'name': 'uniq'})
            baseframe = cm.exception.get('baseframe')
            name, args = baseframe
            self.eq(name, 'storm')
            self.eq(args[0], ('q', q))
            recent_frames = cm.exception.get('recent_frames')
            self.len(6, recent_frames)
            for frame in recent_frames:
                self.eq(frame, ('stormcmd', (('name', 'uniq'),)))

            # Run a feed function and validate the user is recorded.
            await core.addFeedData('syn.nodes', [(('test:int', 1138), {})])
            # We have to brute force the last prov stack to get the data
            # Since we don't have splices to track
            stacks = await alist(core.provStacks(0, 1000))
            feed_stack = stacks[-1]
            frame = feed_stack[1][1][0]
            self.eq(frame[0], 'feed:data')
            self.eq(frame[1].get('name'), 'syn.nodes')
            self.isin('user', frame[1])

    async def test_prov_no_extra(self):
        '''
        No more than 1 prov:new event with the same data shall be fired for the same query
        '''
        self.skip('Pending provenance cache')
        async with self.getTestCore() as core:
            mesgs = await core.stormlist('[test:str=foo :hehe=bar]', opts={'editformat': 'nodeedits'})
            provs = [m for m in mesgs if m[0] == 'prov:new']

            # No duplicate prov:new
            self.len(1, provs)

    async def test_prov_disabled(self):
        '''
        Test that things still work with provenance disabled
        '''
        async with self.getTestCoreAndProxy(conf={}) as (core, prox):
            await prox.storm('[ test:str=foo ]').list()

            await alist(prox.provStacks(0, 1000))

            self.none(await prox.getProvStack('abcd'))

            self.none(core.provstor.precommit())

            retn = core.provstor.stor()
            self.eq((None, None), retn)
