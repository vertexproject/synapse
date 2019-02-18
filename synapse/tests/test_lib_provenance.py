import synapse.common as s_common
import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class ProvenanceTest(s_t_utils.SynTest):

    async def test_prov(self):
        async with self.getTestCore() as real, real.getLocalProxy() as core:
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

            # FIXME: public API for retrieval?

            # The source splices
            prov = await real.layer.getProvStack(aliases[0])
            s1 = ('', {})
            self.eq((s1,), prov)

            # The teststr splices
            prov = await real.layer.getProvStack(aliases[3])
            s2 = ('storm', {'q': '[ teststr=foo ]', 'user': 'root'})
            self.eq((s1, s2), prov)

            # The trigger splices
            prov = await real.layer.getProvStack(aliases[5])
            s3 = ('trig', {'cond': 'node:add', 'form': 'teststr', 'tag': None, 'prop': None})
            s4 = ('storm', {'q': '[ testint=1 ]', 'user': 'root'})
            self.eq((s1, s2, s3, s4), prov)

            # prop:del/node:del
            prov = await real.layer.getProvStack(aliases[7])

            ds2 = ('storm', {'q': 'testint | delnode', 'user': 'root'})
            ds3 = ('stormcmd', {'name': 'delnode', 'argv': ()})
            self.eq((s1, ds2, ds3), prov)


