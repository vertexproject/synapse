import sys
import pprint

import requests

import synapse.lib.json as s_json

# Examples for using the Cortex HTTP API to call Storm queries.
# For more information about these APIs, refer to the following documentation.
# https://synapse.docs.vertex.link/en/latest/synapse/httpapi.html#

# Fill in your url, user, and password.

base_url = 'https://yourcortex.yourdomain.com'
username = 'XXXX'
password = 'XXXX'

def main(argv):

    sess = requests.session()

    # Login to setup a session cookie with the UI. This sets the sess cookie.
    # requests.session automatically handles the Set-Cookie header to
    # store and reuse the session cookie. Refer to the documentation for
    # other HTTPAPI clients and tools for how they handle cookies.

    url = f'{base_url}/api/v1/login'
    data = {'user': username, 'passwd': password}

    resp = sess.post(url, json=data)
    assert resp.status_code == 200, f'Failed to login resp.status={resp.status}'

    # api/v1/storm - This streams Storm messages back to the user,
    # much like the telepath storm() API. The example shows some
    # node and print messages being sent back.

    query = '.created $lib.print($node.repr(".created")) | limit 3'
    data = {'query': query, 'opts': {'repr': True}}
    url = f'{base_url}/api/v1/storm'

    resp = sess.get(url, json=data, stream=True)
    for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
        mesg = s_json.loads(chunk)
        pprint.pprint(mesg)

    # storm/call - this is intended for use with the Storm return() syntax
    # as they return a singular value, instead of a stream of messages.

    query = '$foo = $lib.str.format("hello {valu}", valu="world") return ($foo)'
    data = {'query': query}
    url = f'{base_url}/api/v1/storm/call'

    resp = sess.get(url, json=data)
    info = resp.json()
    pprint.pprint(info)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
