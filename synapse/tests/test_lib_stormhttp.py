import os
import json
import shutil

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.certdir as s_certdir
import synapse.lib.httpapi as s_httpapi

import synapse.tests.utils as s_test

class TstWebSock(s_httpapi.WebSocket):

    def initialize(self):
        pass

    async def open(self):
        await self.sendJsonMesg({'hi': 'woot', 'headers': dict(self.request.headers)})

    async def on_message(self, byts):
        mesg = json.loads(byts)
        await self.sendJsonMesg(('echo', mesg), binary=True)

    async def sendJsonMesg(self, item, binary=False):
        byts = json.dumps(item)
        await self.write_message(byts, binary=binary)

class HttpNotJson(s_httpapi.Handler):
    async def get(self):
        self.write(b"{'not':'json!'}")

class StormHttpTest(s_test.SynTest):

    async def test_storm_http_get(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')

            core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
            core.addHttpApi('/api/v0/notjson', HttpNotJson, {'cell': core})
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            opts = {'vars': {'url': url}}

            # Header and params as dict
            q = '''
            $params=$lib.dict(key=valu, foo=bar, baz=$lib.false)
            $hdr = $lib.dict(true=$lib.true)
            $hdr."User-Agent"="Storm HTTP Stuff"
            $k = (0)
            $hdr.$k="Why"
            $resp = $lib.inet.http.get($url, headers=$hdr, params=$params, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',), 'baz': ('False',)})
            self.eq(data.get('headers').get('User-Agent'), 'Storm HTTP Stuff')
            self.eq(data.get('headers').get('0'), 'Why')
            self.eq(data.get('headers').get('True'), 'True')

            # headers / params as list of key/value pairs
            q = '''
            $params=((foo, bar), (key, valu), (baz, $lib.false))
            $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
                    ((0), "Why"),
                    ("true", $lib.true),
            )
            $resp = $lib.inet.http.get($url, headers=$hdr, params=$params, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',), 'baz': ('False',)})
            self.eq(data.get('headers').get('User-Agent'), 'Storm HTTP Stuff')
            self.eq(data.get('headers').get('0'), 'Why')
            self.eq(data.get('headers').get('True'), 'True')

            # headers
            q = '''
            $resp = $lib.inet.http.get($url, ssl_verify=$lib.false)
            return ( $resp.headers."Content-Type" )
            '''
            resp = await core.callStorm(q, opts=opts)
            self.eq(resp, 'application/json; charset=UTF-8')

            badurl = f'https://root:root@127.0.0.1:{port}/api/v0/notjson'
            badopts = {'vars': {'url': badurl}}
            q = '''
            $resp = $lib.inet.http.get($url, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            with self.raises(s_exc.BadJsonText) as cm:
                resp = await core.callStorm(q, opts=badopts)

            # params as a urlencoded string
            q = '''
            $params="foo=bar&key=valu&foo=baz"
            $resp = $lib.inet.http.get($url, params=$params, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar', 'baz')})

            # Bad param
            q = '''
            $params=(1138)
            $resp = $lib.inet.http.get($url, params=$params, ssl_verify=$lib.false)
            return ( ($resp.code, $resp.err) )
            '''
            code, (errname, _) = await core.callStorm(q, opts=opts)
            self.eq(code, -1)
            self.eq('TypeError', errname)

            # SSL Verify enabled results in a aiohttp.ClientConnectorCertificateError
            q = '''
            $params=((foo, bar), (key, valu))
            $resp = $lib.inet.http.get($url, params=$params)
            return ( ($resp.code, $resp.err) )
            '''
            code, (errname, _) = await core.callStorm(q, opts=opts)
            self.eq(code, -1)
            self.eq('ClientConnectorCertificateError', errname)

    async def test_storm_http_inject_ca(self):

        with self.getTestDir() as dirn:
            cdir = s_common.gendir(dirn, 'certs')
            cadir = s_common.gendir(cdir, 'cas')
            tdir = s_certdir.CertDir(cdir)
            tdir.genCaCert('somelocalca')
            tdir.genHostCert('localhost', signas='somelocalca')

            localkeyfp = tdir.getHostKeyPath('localhost')
            localcertfp = tdir.getHostCertPath('localhost')
            shutil.copyfile(localkeyfp, s_common.genpath(dirn, 'sslkey.pem'))
            shutil.copyfile(localcertfp, s_common.genpath(dirn, 'sslcert.pem'))

            tlscadir = s_common.gendir(dirn, 'cadir')
            for fn in os.listdir(cadir):
                if fn.endswith('.crt'):
                    shutil.copyfile(os.path.join(cadir, fn), os.path.join(tlscadir, fn))

            async with self.getTestCore(dirn=dirn) as core:

                root = await core.auth.getUserByName('root')
                await root.setPasswd('root')

                addr, port = await core.addHttpsPort(0)
                core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
                url = f'https://root:root@localhost:{port}/api/v0/test'
                opts = {'vars': {'url': url}}
                q = '''
                $params=((foo, bar), (key, valu))
                $resp = $lib.inet.http.get($url, params=$params)
                return ( ($resp.code, $resp.err) )
                '''
                code, (errname, _) = await core.callStorm(q, opts=opts)
                self.eq(code, -1)
                self.eq('ClientConnectorCertificateError', errname)

            conf = {'tls:ca:dir': tlscadir}
            async with self.getTestCore(dirn=dirn, conf=conf) as core:
                addr, port = await core.addHttpsPort(0)
                core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
                url = f'https://root:root@localhost:{port}/api/v0/test'
                opts = {'vars': {'url': url}}
                q = '''
                $params=((foo, bar), (key, valu))
                $resp = $lib.inet.http.get($url, params=$params)
                return ( $resp.json() )
                '''
                resp = await core.callStorm(q, opts=opts)
                data = resp.get('result')
                self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',)})

    async def test_storm_http_head(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')
            core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})

            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            noauth_url = f'https://127.0.0.1:{port}/api/v0/test'
            newp_url = noauth_url + 'newpnewp'
            opts = {'vars': {'url': url, 'noauth_url': noauth_url, 'newp_url': newp_url}}

            q = '''
            $params=$lib.dict(key=valu, foo=bar)
            $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.head($url, headers=$hdr, params=$params, ssl_verify=$lib.false)
            return ( ($resp.code, $resp.headers, $resp.body) )
            '''
            resp = await core.callStorm(q, opts=opts)
            code, headers, body = resp
            self.eq(code, 200)
            self.eq(b'', body)
            self.eq('0', headers.get('Content-Length'))
            self.eq('1', headers.get('Head'))

            q = '''
            $params=$lib.dict(key=valu, redirect='http://test.newp/')
            $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.head($url, headers=$hdr, params=$params, ssl_verify=$lib.false)
            return ( ($resp.code, $resp.headers, $resp.body) )
            '''
            resp = await core.callStorm(q, opts=opts)
            code, headers, body = resp
            self.eq(code, 302)
            self.eq(b'', body)
            self.eq('0', headers.get('Content-Length'))
            self.eq('1', headers.get('Head'))
            self.eq('1', headers.get('Redirected'))
            self.eq('http://test.newp/', headers.get('Location'))

            q = '''
            $params=$lib.dict(key=valu, redirect=$noauth_url)
            $hdr = (
                ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.head($url, headers=$hdr, params=$params, ssl_verify=$lib.false, allow_redirects=$lib.true)
            return ( ($resp.code, $resp.headers, $resp.body) )
            '''
            resp = await core.callStorm(q, opts=opts)
            code, headers, body = resp
            self.eq(code, 200)
            self.eq(b'', body)

            q = '''
            $params=$lib.dict(key=valu, redirect=$newp_url)
            $hdr = (
                ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.head($url, headers=$hdr, params=$params, ssl_verify=$lib.false, allow_redirects=$lib.true)
            return ( ($resp.code, $resp.headers, $resp.body) )
            '''
            resp = await core.callStorm(q, opts=opts)
            code, headers, body = resp
            self.eq(code, 404)
            self.eq(b'', body)

            q = '''
            $params=$lib.dict(key=valu, redirect="http://127.0.0.1/newp")
            $hdr = (
                ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.head($url, headers=$hdr, params=$params, ssl_verify=$lib.false, allow_redirects=$lib.true)
            return ( ($resp.code, $resp.headers, $resp.body) )
            '''
            resp = await core.callStorm(q, opts=opts)
            code, headers, body = resp
            self.eq(code, -1)
            self.eq(b'', body)

    async def test_storm_http_request(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')
            core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            opts = {'vars': {'url': url}}
            q = '''
            $params=$lib.dict(key=valu, foo=bar)
            $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.request(GET, $url, headers=$hdr, params=$params, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',)})
            self.eq(data.get('headers').get('User-Agent'), 'Storm HTTP Stuff')

            # Timeout
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            opts = {'vars': {'url': url, 'sleep': 1, 'timeout': 2}}
            q = '''
            $params=$lib.dict(key=valu, foo=bar, sleep=$sleep)
            $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.request(GET, $url, headers=$hdr, params=$params, ssl_verify=$lib.false, timeout=$timeout)
            $code = $resp.code
            return ($code)
            '''
            code = await core.callStorm(q, opts=opts)
            self.eq(200, code)

            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            opts = {'vars': {'url': url, 'sleep': 10, 'timeout': 1}}
            q = '''
            $params=$lib.dict(key=valu, foo=bar, sleep=$sleep)
            $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.request(GET, $url, headers=$hdr, params=$params, ssl_verify=$lib.false, timeout=$timeout)
            $code = $resp.code
            return (($code, $resp.err))
            '''
            code, (errname, errinfo) = await core.callStorm(q, opts=opts)
            self.eq(code, -1)
            self.eq('TimeoutError', errname)
            self.isin('mesg', errinfo)
            self.eq('', errinfo.get('mesg'))  # timeouterror has no mesg

    async def test_storm_http_post(self):

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

            core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            opts = {'vars': {'url': url, 'buf': b'1234'}}
            q = '''
            $params=$lib.dict(key=valu, foo=bar)
            $resp = $lib.inet.http.post($url, params=$params, body=$buf, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',)})
            self.eq(data.get('body'), 'MTIzNA==')

            q = '''
            $fields=$lib.list(
                $lib.dict(name=foo, value=bar),
                $lib.dict(name=foo, value=bar2),
                $lib.dict(name=baz, value=cool)
            )
            $resp = $lib.inet.http.post($url, fields=$fields, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'foo': ('bar', 'bar2'), 'baz': ('cool',)})

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
            $resp=$lib.inet.http.post($url, json=$json, body=$body, ssl_verify=$(0))
            return ( ($resp.code, $resp.err) )
            '''
            code, (errname, _) = await core.callStorm(text, opts=opts)
            self.eq(code, -1)
            self.eq('ValueError', errname)

    async def test_storm_http_proxy(self):
        conf = {'http:proxy': 'socks5://user:pass@127.0.0.1:1'}
        async with self.getTestCore(conf=conf) as core:
            resp = await core.callStorm('return($lib.axon.wget("http://vertex.link"))')
            self.ne(-1, resp['mesg'].find('Can not connect to proxy 127.0.0.1:1'))

            q = '$resp=$lib.inet.http.get("http://vertex.link") return(($resp.code, $resp.err))'
            code, (errname, _) = await core.callStorm(q)
            self.eq(code, -1)
            self.eq('ProxyConnectionError', errname)

    async def test_storm_http_connect(self):

        async with self.getTestCore() as core:

            core.addHttpApi('/test/ws', TstWebSock, {})
            addr, port = await core.addHttpsPort(0)

            mesg = await core.callStorm('''
                $hdr=$lib.dict(key=$lib.false)
                $url = $lib.str.format('https://127.0.0.1:{port}/test/ws', port=$port)

                ($ok, $sock) = $lib.inet.http.connect($url, headers=$hdr)
                if (not $ok) { $lib.exit($sock) }

                ($ok, $mesg) = $sock.rx()
                if (not $ok) { $lib.exit($mesg) }
                return($mesg)
            ''', opts={'vars': {'port': port}})
            self.eq(mesg.get('hi'), 'woot')
            self.eq(mesg.get('headers').get('Key'), 'False')

            mesg = await core.callStorm('''
                $hdr=( (key, $lib.false), )
                $url = $lib.str.format('https://127.0.0.1:{port}/test/ws', port=$port)

                ($ok, $sock) = $lib.inet.http.connect($url, headers=$hdr)
                if (not $ok) { $lib.exit($sock) }

                ($ok, $mesg) = $sock.rx()
                if (not $ok) { $lib.exit($mesg) }
                return($mesg)
            ''', opts={'vars': {'port': port}})
            self.eq(mesg.get('hi'), 'woot')
            self.eq(mesg.get('headers').get('Key'), 'False')

            self.eq((True, ('echo', 'lololol')), await core.callStorm('''
                $url = $lib.str.format('https://127.0.0.1:{port}/test/ws', port=$port)

                ($ok, $sock) = $lib.inet.http.connect($url)
                if (not $ok) { $lib.exit($sock) }

                ($ok, $mesg) = $sock.rx()
                if (not $ok) { $lib.exit($mesg) }

                ($ok, $valu) = $sock.tx(lololol)
                return($sock.rx())
            ''', opts={'vars': {'port': port}}))
