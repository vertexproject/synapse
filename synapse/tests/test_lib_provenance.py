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
