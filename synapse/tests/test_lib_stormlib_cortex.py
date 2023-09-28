import asyncio

from unittest import mock

import aioimaplib

import synapse.common as s_common

import synapse.tests.utils as s_test

class CortexLibTest(s_test.SynTest):

    async def test_libcortex_httpapi(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            addr, port = await core.addHttpsPort(0)

            # Define our first handler!
            q = '''
            $obj = $lib.cortex.httpapi.add('hehe/haha')
            $obj.get = ${
                $response.reply(200, ({'oh': 'my'}), ({'Secret-Header': 'OhBoy!'}) )
                return ( $response )
            }
            '''
