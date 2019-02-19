import synapse.common as s_common

import synapse.lib.provenance as s_provenance

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ProvenanceTest(s_t_utils.SynTest):

    async def test_prov(self):

        s_provenance.reset()

        async with self.getTestCore() as real, real.getLocalProxy() as core:

            # Non-existent alias
            self.none(await real.layer.getProvStack(b'abcd'))

            await core.addTrigger('node:add', '[ testint=1 ]', info={'form': 'teststr'})
            await s_common.aspin(await core.eval('[ teststr=foo ]'))
            await self.agenlen(1, await core.eval('testint'))

            await self.agenlen(0, await core.eval('testint | delnode'))

            splices = await alist(await core.splices(0, 1000))

            self.len(9, splices)
            aliases = [splice[1]['prov'] for splice in splices]
            self.eq(aliases[0], aliases[1])
            self.eq(aliases[0], aliases[2])
            self.eq(aliases[3], aliases[4])
            self.eq(aliases[7], aliases[8])

            # node:add and prop:set
            self.eq(aliases[5], aliases[6])

            # The source splices
            prov1 = await real.layer.getProvStack(aliases[0])
            s1 = ('', {})
            self.eq((s1,), prov1)

            # The teststr splices
            prov2 = await real.layer.getProvStack(aliases[3])
            s2 = ('storm', {'q': '[ teststr=foo ]', 'user': 'root'})
            self.eq((s1, s2), prov2)

            # The trigger splices
            prov3 = await real.layer.getProvStack(aliases[5])
            s3 = ('trig', {'cond': 'node:add', 'form': 'teststr', 'tag': None, 'prop': None})
            s4 = ('storm', {'q': '[ testint=1 ]', 'user': 'root'})
            self.eq((s1, s2, s3, s4), prov3)

            # prop:del/node:del
            prov4 = await core.getProvStack(aliases[7])

            ds2 = ('storm', {'q': 'testint | delnode', 'user': 'root'})
            ds3 = ('stormcmd', {'name': 'delnode', 'argv': ()})
            self.eq((s1, ds2, ds3), prov4)

            # Test the streaming API
            provstacks = await alist(await core.provStacks(0, 1000))
            correct = [(aliases[0], prov1), (aliases[3], prov2), (aliases[5], prov3), (aliases[7], prov4)]
            self.eq(provstacks, correct)
