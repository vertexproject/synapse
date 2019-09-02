import synapse.tests.utils as s_test

class StormHttpTest(s_test.SynTest):

    async def test_storm_http_get(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpPort(0)
            core.insecure = True
            text = '''
                $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
                )
                $url = $lib.str.format("http://127.0.0.1:{port}/api/v1/model", port=$port)

                for $name in $lib.inet.http.get($url, headers=$hdr).json().result.forms {
                    [ test:str=$name ]
                }
            '''
            opts = {'vars': {'port': port}}
            nodes = await core.nodes(text, opts=opts)
            self.len(1, await core.nodes('test:str=inet:ipv4'))

    async def test_storm_http_post_api(self):

        async with self.getTestCore() as core:
            core.insecure = True
            addr, port = await core.addHttpPort(0)
            user, passwd = 'foo', 'bar'

            adduser = '''
                $url = $lib.str.format("http://127.0.0.1:{port}/api/v1/auth/adduser", port=$port)
                $user = $lib.str.format('{"name": "{name}", "passwd": "{passwd}"}', name=$name, passwd=$passwd)

                $user = $lib.inet.http.post($url, body=$user).json().result.name
                $lib.print($user)
                [ test:str=$user ]
            '''
            opts = {'vars': {'port': port, 'name': user, 'passwd': passwd}}
            nodes = await core.storm(adduser, opts=opts).list()
            self.len(1, nodes)
            self.assertIn(user, [u.name for u in core.auth.users()])

    async def test_storm_http_post_file(self):

        async with self.getTestCore() as core:

            core.insecure = True
            addr, port = await core.addHttpPort(0)
            json = '{"query": "{query}"}'
            text = '''
            $url = $lib.str.format("http://127.0.0.1:{port}/api/v1/storm", port=$port)
            $stormq = "($size, $sha2) = $lib.bytes.put($lib.b64.decode('dmVydGV4')) [ test:str = $sha2 ] [ test:int = $size ]"
            $query = $lib.str.format($json, query=$stormq)
            $bytez = $lib.inet.http.post($url, body=$query)
            '''
            opts = {'vars': {'port': port, 'json': json}}
            nodes = await core.storm(text, opts=opts).list()
            nodes = await core.nodes('test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'e1b683e26a3aad218df6aa63afe9cf57fdb5dfaf5eb20cddac14305d67f48a02'))

            nodes = await core.nodes('test:int')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 6))
