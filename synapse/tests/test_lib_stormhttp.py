
import synapse.tests.utils as s_test

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
