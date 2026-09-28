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
            self.propeq(node, 'md5', '91112d75297841c12ca655baafc05104')
            self.propeq(node, 'sha1', '2984ab44774294be9f7a369bbd73b52021bf0bb4')
            self.propeq(node, 'sha256', '62c7174a99ff0afd4c828fc779d2572abc2438415e3ca9769033d4a36479b14f')

            nodes = await core.nodes('[ auth:passwd=" Woot " ]')
            self.eq(nodes[0].ndef, ('auth:passwd', ' Woot '))

            opts = {'vars': {'valu': ' sk_Live_AbC123/+= '}}
            nodes = await core.nodes('''
                [ auth:apikey=*
                    :issuer={[ ou:org=* :name=vertex ]}
                    :period=(2024, 2025)
                    :value=$valu
                    :seen=2024
                ]
            ''', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.ndef[0], 'auth:apikey')
            self.propeq(node, 'period', (1704067200000000, 1735689600000000, 31622400000000))
            self.propeq(node, 'value', ' sk_Live_AbC123/+= ')
            self.nn(node.get('seen'))

            self.len(1, await core.nodes('auth:apikey -> ou:org +:name=vertex'))
            self.len(1, await core.nodes('auth:apikey:value=$valu', opts=opts))
            self.len(0, await core.nodes('auth:apikey:value="sk_Live_AbC123/+="'))

            nodes = await core.nodes('auth:apikey -> it:dev:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('it:dev:str', ' sk_Live_AbC123/+= '))

            form = core.model.form('auth:apikey')
            self.true(form.implements('auth:credential'))
            self.true(form.implements('meta:observable'))

            nodes = await core.nodes('''
                auth:apikey
                [ :issuer={[ inet:service:account=(acct0,) ]} ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('issuer'), ('inet:service:account', s_common.guid(('acct0',))))

            nodes = await core.nodes('''
                [ inet:service:account=(acct1,) :creds={ auth:apikey } ]
                -> auth:credential
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'auth:apikey')
