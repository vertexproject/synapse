
import gzip
import json

import synapse.tests.utils as s_test

from synapse.lib.httpapi import Handler

class gzipper(Handler):
    async def get(self):
        ret = {
            'a': 1,
            'b': 2,
            'c': 3,
        }
        ret = gzip.compress(bytes(json.dumps(ret), 'utf8'))

        self.set_header('Content-Type', 'application/x-gzip')
        self.set_header('Accept-Ranges', 'bytes')
        self.set_status(200)
        return self.write(ret)

class StormHttpTest(s_test.SynTest):

    async def test_storm_http_get(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpPort(0)
            core.insecure = True
            text = '''
                $url = $lib.str.format("http://127.0.0.1:{port}/api/v1/model", port=$port)

                for $name in $lib.inet.http.get($url).json().result.forms {
                    [ test:str=$name ]
                }
            '''
            opts = {'vars': {'port': port}}
            nodes = await core.nodes(text, opts=opts)
            self.len(1, await core.nodes('test:str=inet:ipv4'))

            core.addHttpApi('/tests/lib/stormhttp/gzip', gzipper, {'cell': core})

            text = '''
                $url = $lib.str.format("http://127.0.0.1:{port}/tests/lib/stormhttp/gzip", port=$port)

                for $foo in $lib.inet.http.get($url).gunzip().json() {
                    [ test:str=$foo ]
                }
            '''
            nodes = [n async for n in core.eval(text, opts=opts)]
            self.len(3, nodes)
