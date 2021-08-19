import os
import asyncio

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.multislabseqn as s_multislabseqn

import synapse.tests.utils as s_t_utils

class SlabSeqn(s_t_utils.SynTest):

    async def test_slab_seqn(self):

        with self.getTestDir() as dirn, self.setTstEnvars(SYN_MULTISLAB_MAX_INDEX='10'):

            msqn = await s_multislabseqn.MultiSlabSeqn(dirn)
            self.eq(0, msqn.index())

            retn = list(msqn.iter(0))
            self.eq([], retn)

            retn = msqn.last()
            self.eq(None, retn)
