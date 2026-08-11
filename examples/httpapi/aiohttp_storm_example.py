import sys
import json
import pprint
import asyncio

import aiohttp

# Examples for using the Cortex HTTP API to call Storm queries.
# For more information about these APIs, refer to the following documentation.
# https://synapse.docs.vertex.link/en/latest/synapse/httpapi.html#

# Fill in your url and API key. The Storm and model HTTP endpoints accept
# X-API-KEY authentication only. Generate an API key for your user with the
# Storm $lib.auth.users.byname($name).genApiKey() API.

base_url = 'https://yourcortex.yourdomain.com'
apikey = 'XXXX'

async def main(argv):

    # The X-API-KEY header authenticates every request.
    headers = {'X-API-KEY': apikey}
    async with aiohttp.ClientSession(headers=headers) as sess:

        # api/v3/storm - This streams Storm messages back to the user,
        # much like the telepath storm() API. The example shows some
        # node and print messages being sent back. The messages are
        # newline delimited JSON, so each line is one message.

        query = '.created $lib.print($node.repr(".created")) | limit 3'
        data = {'query': query, 'opts': {'node:opts': {'repr': True}}}
        url = f'{base_url}/api/v3/storm'

        async with sess.get(url, json=data) as resp:
            async for line in resp.content:
                mesg = json.loads(line)
                pprint.pprint(mesg)

        # storm/call - this is intended for use with the Storm return() syntax
        # as they return a singular value, instead of a stream of messages.

        query = '$valu="world" $foo=`hello {$valu}` return ($foo)'
        data = {'query': query}
        url = f'{base_url}/api/v3/storm/call'

        async with sess.get(url, json=data) as resp:
            info = await resp.json()
            pprint.pprint(info)

if __name__ == '__main__':
    sys.exit(asyncio.run(main(sys.argv[1:])))
