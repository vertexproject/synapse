import asyncio

from unittest import mock

import aioimaplib

import synapse.common as s_common

import synapse.tests.utils as s_test

from pprint import pprint

class CortexLibTest(s_test.SynTest):

    async def test_libcortex_httpapi(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('lowuser')
            lowuser = udef.get('iden')
            await core.setUserPasswd(core.auth.rootuser.iden, 'root')
            await core.setUserPasswd(lowuser, 'secret')
            addr, hport = await core.addHttpsPort(0)

            # Define our first handler!
            q = '''
            $obj = $lib.cortex.httpapi.add('hehe/haha')
            $obj.get = ${
$data = ({'oh': 'my'})
$body = $lib.json.save($data).encode()
$headers = ({'Secret-Header': 'OhBoy!'})
$headers."Content-Type" = "application/json"
$headers."Content-Length" = $lib.len($body)
$request.reply(200, headers=$headers, body=$body)
            }
            '''
            msgs = await core.stormlist(q)
            for m in msgs:
                print(m)

            async with self.getHttpSess(auth=('root', 'root'), port=hport) as sess:
                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha')
                print(resp)
                buf = await resp.read()
                print(buf)

                resp = await sess.get(f'https://localhost:{hport}/api/ext/hehe/haha?sup=dude')
                print(resp)
                buf = await resp.read()
                print(buf)
