import logging

import synapse.common as s_common
import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class AuthModelTest(s_t_utils.SynTest):

    async def test_model_auth(self):

        async with self.getTestCore() as core:

            cred = s_common.guid()
            nodes = await core.nodes(f'''
                [ auth:creds={cred}
                    :email=visi@vertex.link
                    :user=lolz
                    :phone=12028675309
                    :passwd=secret
                    :passwdhash="*"
                    :website=https://www.vertex.link
                    :host="*"
                    :wifi:ssid=vertexproject
                    :web:acct=(vertex.link,visi)
                ]
            ''')

            self.len(1, nodes)
            self.nn(nodes[0].get('host'))
            self.nn(nodes[0].get('passwdhash'))

            self.eq('lolz', nodes[0].get('user'))
            self.eq('12028675309', nodes[0].get('phone'))
            self.eq('secret', nodes[0].get('passwd'))
            self.eq('visi@vertex.link', nodes[0].get('email'))
            self.eq('https://www.vertex.link', nodes[0].get('website'))
            self.eq('vertexproject', nodes[0].get('wifi:ssid'))
            self.eq(('vertex.link', 'visi'), nodes[0].get('web:acct'))

            accs = s_common.guid()
            nodes = await core.nodes(f'''
                [ auth:access={accs}
                    :person="*"
                    :creds={cred}
                    :time=20200202
                    :success=true
                ]
            ''')
            self.nn(nodes[0].get('creds'))
            self.nn(nodes[0].get('person'))

            self.eq(True, nodes[0].get('success'))
            self.eq(1580601600000, nodes[0].get('time'))
