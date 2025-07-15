import logging

import synapse.common as s_common
import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class AuthModelTest(s_t_utils.SynTest):

    async def test_model_auth(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[auth:passwd=2Cool4u]')
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef, ('auth:passwd', '2Cool4u'))
            self.eq(node.get('md5'), '91112d75297841c12ca655baafc05104')
            self.eq(node.get('sha1'), '2984ab44774294be9f7a369bbd73b52021bf0bb4')
            self.eq(node.get('sha256'), '62c7174a99ff0afd4c828fc779d2572abc2438415e3ca9769033d4a36479b14f')
