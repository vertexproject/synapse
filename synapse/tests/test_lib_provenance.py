import hashlib

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

            await core.addTrigger('node:add', '[ testint=1 ]', info={'form': 'teststr'})
            await s_common.aspin(await core.eval('[ teststr=foo ]'))
            await self.agenlen(1, await core.eval('testint'))

            await self.agenlen(0, await core.eval('testint | delnode'))

            splices = await alist(await core.splices(0, 1000))

            self.len(9, splices)
            idens = [splice[1]['prov'] for splice in splices]
            self.eq(idens[0], idens[1])
            self.eq(idens[0], idens[2])
            self.eq(idens[3], idens[4])
            self.eq(idens[7], idens[8])

            # node:add and prop:set
            self.eq(idens[5], idens[6])

            # The source splices
            prov1 = await core.getProvStack(idens[0])
            self.eq(({}, ()), prov1)

            # The teststr splices
            prov2 = await core.getProvStack(idens[3])
            s2 = ('storm', {'q': '[ teststr=foo ]', 'user': 'root'})
            self.eq((s2, ), prov2[1])

            # Validate that the iden calc itself is correct
            rawprov = ({}, [('storm', (('q', '[ teststr=foo ]'), ('user', 'root')))])
            hash = hashlib.md5(s_msgpack.en(rawprov)).hexdigest()
            self.eq(hash, idens[3])

            # The trigger splices
            prov3 = await core.getProvStack(idens[5])
            s3 = ('trig', {'cond': 'node:add', 'form': 'teststr', 'tag': None, 'prop': None})
            s4 = ('storm', {'q': '[ testint=1 ]', 'user': 'root'})
            self.eq((s2, s3, s4), prov3[1])

            # prop:del/node:del
            prov4 = await core.getProvStack(idens[7])

            ds2 = ('storm', {'q': 'testint | delnode', 'user': 'root'})
            ds3 = ('stormcmd', {'name': 'delnode', 'argv': ()})
            self.eq((ds2, ds3), prov4[1])

            # Test the streaming API
            provstacks = await alist(await core.provStacks(0, 1000))
            correct = [(idens[0], prov1), (idens[3], prov2), (idens[5], prov3), (idens[7], prov4)]
            self.eq(provstacks, correct)
