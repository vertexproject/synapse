import synapse.tests.utils as s_test

class StormHttpTest(s_test.SynTest):

    async def test_storm_http_get(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')
            text = '''
                $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
                )
                $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/model", port=$port)

                for ($name, $fdef) in $lib.inet.http.get($url, headers=$hdr, ssl_verify=$(0)).json().result.forms {
                    [ test:str=$name ]
                }
            '''
            opts = {'vars': {'port': port}}
            nodes = await core.nodes(text, opts=opts)
            self.len(1, await core.nodes('test:str=inet:ipv4'))

    async def test_storm_http_request(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')
            text = '''
                $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
                )
                $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/model", port=$port)

                for ($name, $fdef) in $lib.inet.http.request(GET, $url, headers=$hdr, ssl_verify=$(0)).json().result.forms {
                    [ test:str=$name ]
                }
            '''
            opts = {'vars': {'port': port}}
            nodes = await core.nodes(text, opts=opts)
            self.len(1, await core.nodes('test:str=inet:ipv4'))

    async def test_storm_http_post_api(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')

            adduser = '''
                $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/auth/adduser", port=$port)
                $user = $lib.dict(name=$name, passwd=$passwd)
                $post = $lib.inet.http.post($url, json=$user, ssl_verify=$(0)).json().result.name
                $lib.print($post)
                [ test:str=$post ]
            '''
            opts = {'vars': {'port': port, 'name': 'foo', 'passwd': 'bar'}}
            nodes = await core.nodes(adduser, opts=opts)
            self.len(1, nodes)
            self.assertIn('foo', [u.name for u in core.auth.users()])

            adduser = '''
                $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/auth/adduser", port=$port)
                $user = $lib.str.format('{"name": "{name}", "passwd": "{passwd}"}', name=$name, passwd=$passwd)
                $header = $lib.dict("Content-Type"="application/json")
                $post = $lib.inet.http.post($url, headers=$header, body=$user,  ssl_verify=$(0)).json().result.name
                [ test:str=$post ]
            '''
            opts = {'vars': {'port': port, 'name': 'vertex', 'passwd': 'project'}}
            nodes = await core.nodes(adduser, opts=opts)
            self.len(1, nodes)
            self.assertIn('vertex', [u.name for u in core.auth.users()])

    async def test_storm_http_post_file(self):

        async with self.getTestCore() as core:

            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')
            text = '''
            $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/storm", port=$port)
            $stormq = "($size, $sha2) = $lib.bytes.put($lib.base64.decode('dmVydGV4')) [ test:str = $sha2 ] [ test:int = $size ]"
            $json = $lib.dict(query=$stormq)
            $bytez = $lib.inet.http.post($url, json=$json, ssl_verify=$(0))
            '''
            opts = {'vars': {'port': port}}
            nodes = await core.nodes(text, opts=opts)
            nodes = await core.nodes('test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'e1b683e26a3aad218df6aa63afe9cf57fdb5dfaf5eb20cddac14305d67f48a02'))

            nodes = await core.nodes('test:int')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 6))

            text = '''
            $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/storm", port=$port)
            $json = $lib.dict(query="test:str")
            $body = $json
            $json=$lib.inet.http.post($url, json=$json, body=$body, ssl_verify=$(0))
            '''
            mesgs = await core.stormlist(text, opts=opts)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('Error during http post - data and json parameters can not be used at the same time', err[1].get('mesg'))
