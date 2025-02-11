import sys
import pprint
import asyncio

import aiohttp

import synapse.lib.json as s_json

# Examples for using the Cortex HTTP API to call Storm queries.
# For more information about these APIs, refer to the following documentation.
# https://synapse.docs.vertex.link/en/latest/synapse/httpapi.html#

# Fill in your url, user, and password.

base_url = 'https://yourcortex.yourdomain.com'
username = 'XXXX'
password = 'XXXX'

async def main(argv):

    async with aiohttp.ClientSession() as sess:

        # Login to setup a session cookie with the UI. This sets the sess cookie.
        # aiohttp.ClientSession automatically handles the Set-Cookie header to
        # store and reuse the session cookie. Refer to the documentation for
        # other HTTPAPI clients and tools for how they handle cookies.

        url = f'{base_url}/api/v1/login'
        data = {'user': username, 'passwd': password}

        async with await sess.post(url, json=data) as resp:
            assert resp.status == 200, f'Failed to login resp.status={resp.status}'
            print(resp.headers)

        # api/v1/storm - This streams Storm messages back to the user,
        # much like the telepath storm() API. The example shows some
        # node and print messages being sent back.

        query = '.created $lib.print($node.repr(".created")) | limit 3'
        data = {'query': query, 'opts': {'repr': True}}
        url = f'{base_url}/api/v1/storm'

        async with sess.get(url, json=data) as resp:
            async for byts, x in resp.content.iter_chunks():

                if not byts:
                    break

                mesg = s_json.loads(byts)
                pprint.pprint(mesg)

        # storm/call - this is intended for use with the Storm return() syntax
        # as they return a singular value, instead of a stream of messages.

        query = '$foo = $lib.str.format("hello {valu}", valu="world") return ($foo)'
        data = {'query': query}
        url = f'{base_url}/api/v1/storm/call'

        async with sess.get(url, json=data) as resp:
            info = await resp.json()
            pprint.pprint(info)

if __name__ == '__main__':
    sys.exit(asyncio.run(main(sys.argv[1:])))
