import os
import ssl
import shutil

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.certdir as s_certdir
import synapse.lib.httpapi as s_httpapi
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.utils as s_test

class TstWebSock(s_httpapi.WebSocket):

    def initialize(self):
        pass

    async def open(self):
        resp = {'hi': 'woot', 'headers': dict(self.request.headers)}

        params = {}
        for k, v in self.request.query_arguments.items():
            v = [_s.decode() for _s in v]
            params[k] = v

        if params:
            resp['params'] = params

        await self.sendJsonMesg(resp)

    async def on_message(self, byts):
        mesg = s_json.loads(byts)
        await self.sendJsonMesg(('echo', mesg), binary=True)

    async def sendJsonMesg(self, item, binary=False):
        byts = s_json.dumps(item)
        await self.write_message(byts, binary=binary)

class HttpNotJson(s_httpapi.Handler):
    async def get(self):
        self.write(b"{'not':'json!'}")

class HttpBadJson(s_httpapi.Handler):
    async def get(self):
        self.write(b'{"foo": "bar\x80"}')

class StormHttpTest(s_test.SynTest):

    async def test_storm_http_get(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            visi = await core.auth.addUser('visi')
            await root.setPasswd('root')

            core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
            core.addHttpApi('/api/v0/notjson', HttpNotJson, {'cell': core})
            core.addHttpApi('/api/v0/badjson', HttpBadJson, {'cell': core})
            url = f'https://root:root@127.0.0.1:{port}/api/v0/test'
            status_url = f'https://127.0.0.1:{port}/api/v1/status'
            opts = {'vars': {'url': url, 'port': port, 'status_url': status_url}}

            # Request URL is exposed
            q = '''
            $resp = $lib.inet.http.get($url, ssl_verify=$lib.false)
            return ( $resp.url )
            '''
            resp = await core.callStorm(q, opts=opts)
            # The password is omitted
            self.eq(resp, f'https://127.0.0.1:{port}/api/v0/test')

            # Redirects expose the final URL
            q = '''
            $params = ({'redirect': $status_url})
            $resp = $lib.inet.http.get($url, params=$params, ssl_verify=$lib.false)
            return ( $resp.url )
            '''
            resp = await core.callStorm(q, opts=opts)
            self.eq(resp, f'https://127.0.0.1:{port}/api/v1/status')

            q = '''
            $_url = `https://root:root@127.0.0.1:{($port + (1))}/api/v0/newp`
            $resp = $lib.inet.http.get($_url, ssl_verify=$lib.false)
            if ( $resp.code != (-1) ) { $lib.exit(mesg='Test fail!') }
            return ( $resp.url )
            '''
            resp = await core.callStorm(q, opts=opts)
            # The password is present
            self.eq(resp, f'https://root:root@127.0.0.1:{port + 1}/api/v0/newp')

            # Header and params as dict
            q = '''
            $params=({"key": "valu", "foo": "bar", "baz": $lib.false})
            $hdr = ({"true": $lib.true})
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

            # Request headers
            q = '''
            $headers = ({"Wow": "OhMy"})
            $resp = $lib.inet.http.get($url, headers=$headers, ssl_verify=$lib.false)
            return ( $resp.request_headers )
            '''
            resp = await core.callStorm(q, opts=opts)
            self.eq(resp.get('Wow'), 'OhMy')
            # Authorization header derived from the basic auth in $url
            self.isin('Authorization', resp)

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
            return ( ($resp.code, $resp.reason, $resp.err) )
            '''
            code, reason, (errname, _) = await core.callStorm(q, opts=opts)
            self.eq(code, -1)
            self.isin('Exception occurred during request: ', reason)
            self.isin('Invalid query type', reason)
            self.eq('TypeError', errname)

            # SSL Verify enabled results in an aiohttp.ClientConnectorCertificateError
            q = '''
            $params=((foo, bar), (key, valu))
            $resp = $lib.inet.http.get($url, params=$params)
            return ( ($resp.code, $resp.reason, $resp.err) )
            '''
            code, reason, (errname, _) = await core.callStorm(q, opts=opts)
            self.eq(code, -1)
            self.isin('certificate verify failed', reason)
            self.eq('ClientConnectorCertificateError', errname)

            retn = await core.callStorm('return($lib.inet.http.urlencode("http://go ogle.com"))')
            self.eq('http%3A%2F%2Fgo+ogle.com', retn)

            retn = await core.callStorm('return($lib.inet.http.urldecode("http%3A%2F%2Fgo+ogle.com"))')
            self.eq('http://go ogle.com', retn)

            badurl = f'https://root:root@127.0.0.1:{port}/api/v0/badjson'
            badopts = {'vars': {'url': badurl}}
            q = '''
            $resp = $lib.inet.http.get($url, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            with self.raises(s_exc.StormRuntimeError) as cm:
                resp = await core.callStorm(q, opts=badopts)

            q = '''
            $resp = $lib.inet.http.get($url, ssl_verify=$lib.false)
            return ( $resp.json(encoding=utf8, errors=ignore) )
            '''
            self.eq({"foo": "bar"}, await core.callStorm(q, opts=badopts))

            retn = await core.callStorm('return($lib.inet.http.codereason(404))')
            self.eq(retn, 'Not Found')

            retn = await core.callStorm('return($lib.inet.http.codereason(123))')
            self.eq(retn, 'Unknown HTTP status code 123')

            # Request history is preserved across multiple redirects.
            q = '''$api = $lib.cortex.httpapi.add(dyn00)
            $api.methods.get =  ${
                $api = $request.api
                if $n {
                    $part = `redir0{$n}`
                    $redir = `/api/ext/{$part}`
                    $headers = ({"Location": $redir})
                    $api.vars.n = ($n - (1) )
                    $api.path = $part
                    $request.reply(301, headers=$headers)
                } else {
                    $api.vars.n = $initial_n
                    $api.path = dyn00
                    $request.reply(200, body=({"end": "youMadeIt"}) )
                }
            }
            $api.authenticated = (false)
            $api.vars.initial_n = (3)
            $api.vars.n = (3)
            return ( ($api.iden) )'''
            iden00 = await core.callStorm(q)

            q = '''
            $url = `https://127.0.0.1:{$port}/api/ext/dyn00`
            $resp = $lib.inet.http.get($url, ssl_verify=$lib.false)
            return ( $resp )
            '''
            resp = await core.callStorm(q, opts=opts)
            self.eq(resp.get('url'), f'https://127.0.0.1:{port}/api/ext/redir01')
            self.eq([hnfo.get('url') for hnfo in resp.get('history')],
                    [f'https://127.0.0.1:{port}/api/ext/dyn00',
                     f'https://127.0.0.1:{port}/api/ext/redir03',
                     f'https://127.0.0.1:{port}/api/ext/redir02',
                     ])

            # The gtor returns a list of objects
            q = '''
            $url = `https://127.0.0.1:{$port}/api/ext/dyn00`
            $resp = $lib.inet.http.get($url, ssl_verify=$lib.false)
            return ( $resp.history.0 )
            '''
            resp = await core.callStorm(q, opts=opts)
            self.eq(resp.get('url'), f'https://127.0.0.1:{port}/api/ext/dyn00')

            # The history is not available if there is a fatal error when
            # following redirects.
            q = '''
            $_url = `https://127.0.0.1:{($port + (1))}/api/v0/newp`
            $params = ({'redirect': $_url})
            $resp = $lib.inet.http.get($url, params=$params, ssl_verify=$lib.false)
            if ( $resp.code != (-1) ) { $lib.exit(mesg='Test fail!') }
            return ( $resp.history )
            '''
            resp = await core.callStorm(q, opts=opts)
            self.isinstance(resp, tuple)
            self.len(0, resp)

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
            $params=({"key": "valu", "foo": "bar"})
            $hdr = (
                    ("User-Agent", "Storm HTTP Stuff"),
            )
            $resp = $lib.inet.http.head($url, headers=$hdr, params=$params, ssl_verify=$lib.false)
            return ( ($resp.code, $resp.reason, $resp.headers, $resp.body) )
            '''
            resp = await core.callStorm(q, opts=opts)
            code, reason, headers, body = resp
            self.eq(code, 200)
            self.eq(reason, 'OK')
            self.eq(b'', body)
            self.eq('0', headers.get('Content-Length'))
            self.eq('1', headers.get('Head'))

            q = '''
            $params=({"key": "valu", "redirect": 'http://test.newp/'})
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
            $params=({"key": "valu", "redirect": $noauth_url})
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
            $params=({"key": "valu", "redirect": $newp_url})
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
            $params=({"key": "valu", "redirect": "http://127.0.0.1/newp"})
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
            $params=({"key": "valu", "foo": "bar"})
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
            $params=({"key": "valu", "foo": "bar", "sleep": $sleep})
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
            $params=({"key": "valu", "foo": "bar", "sleep": $sleep})
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

            q = '''
            $params=({"foo": ["bar", "baz"], "key": [["valu"]]})
            $resp = $lib.inet.http.request(GET, $url, params=$params, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'foo': ['bar', 'baz'], 'key': ["('valu',)"]})

    async def test_storm_http_post(self):

        async with self.getTestCore() as core:
            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')

            adduser = '''
                $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/auth/adduser", port=$port)
                $user = ({"name": $name, "passwd": $passwd})
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
                $header = ({"Content-Type": "application/json"})
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
            $params=({"key": "valu", "foo": "bar"})
            $resp = $lib.inet.http.post($url, params=$params, body=$buf, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'key': ('valu',), 'foo': ('bar',)})
            self.eq(data.get('body'), 'MTIzNA==')

            q = '''
            $fields=([
                {"name": "foo", "value": "bar"},
                {"name": "foo", "value": "bar2"},
                {"name": "baz", "value": "cool"}
            ])
            $resp = $lib.inet.http.post($url, fields=$fields, ssl_verify=$lib.false)
            return ( $resp.json() )
            '''
            resp = await core.callStorm(q, opts=opts)
            data = resp.get('result')
            self.eq(data.get('params'), {'foo': ('bar', 'bar2'), 'baz': ('cool',)})

            # We can send multipart/form-data directly
            q = '''
            $buf = $lib.hex.decode(deadb33f)
            $fields = ([
                {"filename": 'deadb33f.exe', "value": $buf, "name": "word"},
            ])
            return($lib.inet.http.post($url, ssl_verify=$lib.false, fields=$fields))
            '''
            resp = await core.callStorm(q, opts=opts)
            request = s_json.loads(resp.get('body'))
            request_headers = request.get('result').get('headers')
            self.isin('multipart/form-data; boundary=', request_headers.get('Content-Type', ''))

            q = '''
            $fields = ([
                {"forgot": "name", "sha256": "newp"},
            ])
            return($lib.inet.http.post($url, ssl_verify=$lib.false, fields=$fields))
            '''
            resp = await core.callStorm(q, opts=opts)
            self.eq(resp.get('code'), -1)
            self.isin('BadArg: Each field requires a "name" key with a string value: None', resp.get('reason'))

            q = '''
            $buf = $lib.hex.decode(deadb33f)
            $fields = ([
                {"filename": 'deadbeef.exe', "value": $buf},
            ])
            return($lib.inet.http.post($url, ssl_verify=$lib.false, fields=$fields))
            '''
            resp = await core.callStorm(q, opts=opts)
            err = resp['err']
            experr = 'Each field requires a "name" key with a string value when multipart fields are enabled: None'
            self.eq(experr, err[1].get('mesg'))

    async def test_storm_http_post_file(self):

        async with self.getTestCore() as core:

            addr, port = await core.addHttpsPort(0)
            root = await core.auth.getUserByName('root')
            await root.setPasswd('root')
            text = '''
            $url = $lib.str.format("https://root:root@127.0.0.1:{port}/api/v1/storm", port=$port)
            $stormq = "($size, $sha2) = $lib.axon.put($lib.base64.decode('dmVydGV4')) [ test:str = $sha2 ] [ test:int = $size ]"
            $json = ({"query": $stormq})
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
            $json = ({"query": "test:str"})
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
            self.false(resp.get('ok'))
            self.ne(-1, resp['mesg'].find('connect to proxy 127.0.0.1:1'))

            msgs = await core.stormlist('$resp=$lib.axon.wget("http://vertex.link", proxy=(null)) $lib.print($resp.mesg)')
            self.stormIsInWarn('HTTP proxy argument to $lib.null is deprecated', msgs)
            self.stormIsInPrint('connect to proxy 127.0.0.1:1', msgs)

            await self.asyncraises(s_exc.BadArg, core.nodes('$lib.axon.wget("http://vertex.link", proxy=(1.1))'))

            # todo: setting the synapse version can be removed once proxy=true support is released
            try:
                oldv = core.axoninfo['synapse']['version']
                core.axoninfo['synapse']['version'] = (oldv[0], oldv[1] + 1, oldv[2])
                resp = await core.callStorm('return($lib.axon.wget("http://vertex.link", proxy=(null)))')
                self.false(resp.get('ok'))
                self.ne(-1, resp['mesg'].find('connect to proxy 127.0.0.1:1'))
            finally:
                core.axoninfo['synapse']['version'] = oldv

            size, sha256 = await core.axon.put(b'asdf')
            opts = {'vars': {'sha256': s_common.ehex(sha256)}}
            resp = await core.callStorm(f'return($lib.axon.wput($sha256, http://vertex.link))', opts=opts)
            self.false(resp.get('ok'))
            self.isin('connect to proxy 127.0.0.1:1', resp['mesg'])

            q = '$resp=$lib.inet.http.get("http://vertex.link") return(($resp.code, $resp.err))'
            code, (errname, _) = await core.callStorm(q)
            self.eq(code, -1)
            self.eq('ProxyConnectionError', errname)

            msgs = await core.stormlist('$resp=$lib.inet.http.get("http://vertex.link", proxy=(null)) $lib.print($resp.err)')
            self.stormIsInWarn('HTTP proxy argument to $lib.null is deprecated', msgs)
            self.stormIsInPrint('connect to proxy 127.0.0.1:1', msgs)

            await self.asyncraises(s_exc.BadArg, core.nodes('$lib.inet.http.get("http://vertex.link", proxy=(1.1))'))

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('storm', 'lib', 'axon', 'wget')))
            await visi.addRule((True, ('storm', 'lib', 'axon', 'wput')))

            errmsg = f'User {visi.name!r} ({visi.iden}) must have permission {{perm}}'

            asvisi = {'user': visi.iden}
            msgs = await core.stormlist('$lib.inet.http.get(http://vertex.link, proxy=$lib.false)', opts=asvisi)
            self.stormIsInErr(errmsg.format(perm='storm.lib.inet.http.proxy'), msgs)

            asvisi = {'user': visi.iden}
            msgs = await core.stormlist('$lib.inet.http.get(http://vertex.link, proxy=socks5://user:pass@127.0.0.1:1)', opts=asvisi)
            self.stormIsInErr(errmsg.format(perm='storm.lib.inet.http.proxy'), msgs)

            resp = await core.callStorm('return($lib.inet.http.get(http://vertex.link, proxy=socks5://user:pass@127.0.0.1:1))')
            self.eq('ProxyConnectionError', resp['err'][0])

            # test $lib.axon proxy API
            asvisi = {'user': visi.iden}
            msgs = await core.stormlist('$lib.axon.wget(http://vertex.link, proxy=$lib.false)', opts=asvisi)
            self.stormIsInErr(errmsg.format(perm='storm.lib.inet.http.proxy'), msgs)

            asvisi = {'user': visi.iden}
            msgs = await core.stormlist('$lib.axon.wget(http://vertex.link, proxy=socks5://user:pass@127.0.0.1:1)', opts=asvisi)
            self.stormIsInErr(errmsg.format(perm='storm.lib.inet.http.proxy'), msgs)

            asvisi = {'user': visi.iden}
            msgs = await core.stormlist('$lib.axon.wput(asdf, http://vertex.link, proxy=socks5://user:pass@127.0.0.1:1)', opts=asvisi)
            self.stormIsInErr(errmsg.format(perm='storm.lib.inet.http.proxy'), msgs)

            resp = await core.callStorm('return($lib.axon.wget(http://vertex.link, proxy=socks5://user:pass@127.0.0.1:1))')
            self.false(resp.get('ok'))
            self.isin('connect to proxy 127.0.0.1:1', resp['mesg'])

            size, sha256 = await core.axon.put(b'asdf')

            sha256 = s_common.ehex(sha256)
            resp = await core.callStorm(f'return($lib.axon.wput({sha256}, http://vertex.link, proxy=socks5://user:pass@127.0.0.1:1))')
            self.false(resp.get('ok'))
            self.isin('connect to proxy 127.0.0.1:1', resp['mesg'])

            host, port = await core.addHttpsPort(0)
            opts = {
                'vars': {
                    'url': f'https://loop.vertex.link:{port}',
                    'proxy': 'socks5://user:pass@127.0.0.1:1',
                }
            }
            try:
                oldv = core.axoninfo['synapse']['version']
                minver = s_stormtypes.AXON_MINVERS_PROXY
                core.axoninfo['synapse']['version'] = minver[2], minver[1] - 1, minver[0]
                q = '$resp=$lib.axon.wget($url, ssl=(false), proxy=$proxy) $lib.print(`code={$resp.code}`)'
                mesgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('code=404', mesgs)
                self.stormIsInWarn('Axon version does not support proxy argument', mesgs)
            finally:
                core.axoninfo['synapse']['version'] = oldv

        async with self.getTestCore(conf=conf) as core:
            # Proxy permission tests in this section

            visi = await core.auth.addUser('visi')

            await visi.addRule((True, ('storm', 'lib', 'axon', 'wget')))
            await visi.addRule((True, ('storm', 'lib', 'axon', 'wput')))

            _, sha256 = await core.axon.put(b'asdf')
            sha256 = s_common.ehex(sha256)

            host, port = await core.addHttpsPort(0)

            q1 = f'return($lib.inet.http.get(https://loop.vertex.link:{port}, ssl_verify=$lib.false, proxy=$proxy))'
            q2 = f'return($lib.axon.wget(https://loop.vertex.link:{port}, ssl=$lib.false, proxy=$proxy))'
            q3 = f'return($lib.axon.wput({sha256}, https://loop.vertex.link:{port}, ssl=$lib.false, proxy=$proxy))'

            for proxy in ('socks5://user:pass@127.0.0.1:1', False):
                opts = {'vars': {'proxy': proxy}, 'user': visi.iden}

                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(q1, opts=opts)

                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(q2, opts=opts)

                with self.raises(s_exc.AuthDeny):
                    await core.callStorm(q3, opts=opts)

            # Add permissions to use a proxy
            await visi.addRule((True, ('storm', 'lib', 'inet', 'http', 'proxy')))

            opts = {'vars': {'proxy': 'socks5://user:pass@127.0.0.1:1'}, 'user': visi.iden}

            resp = await core.callStorm(q1, opts=opts)
            self.eq('ProxyConnectionError', resp['err'][0])

            resp = await core.callStorm(q2, opts=opts)
            self.eq('ProxyConnectionError', resp['err'][0])

            resp = await core.callStorm(q3, opts=opts)
            self.eq('ProxyConnectionError', resp['err'][0])

            opts = {'vars': {'proxy': False}, 'user': visi.iden}

            resp = await core.callStorm(q1, opts=opts)
            self.eq(resp['code'], 404)
            self.eq(resp['reason'], 'Not Found')

            resp = await core.callStorm(q2, opts=opts)
            self.eq(resp['code'], 404)
            self.eq(resp['reason'], 'Not Found')

            resp = await core.callStorm(q3, opts=opts)
            self.eq(resp['code'], 404)
            self.eq(resp['reason'], 'Not Found')

    async def test_storm_http_connect(self):

        async with self.getTestCore() as core:

            core.addHttpApi('/test/ws', TstWebSock, {})
            addr, port = await core.addHttpsPort(0)

            mesg = await core.callStorm('''
                $params = ( { "param1": "somevalu" } )
                $hdr = ( { "key": $lib.false } )
                $url = $lib.str.format('https://127.0.0.1:{port}/test/ws', port=$port)

                ($ok, $sock) = $lib.inet.http.connect($url, headers=$hdr, params=$params, ssl_verify=$lib.false)
                if (not $ok) { $lib.exit($sock) }

                ($ok, $mesg) = $sock.rx()
                if (not $ok) { $lib.exit($mesg) }
                return($mesg)
            ''', opts={'vars': {'port': port}})
            self.eq(mesg.get('hi'), 'woot')
            self.eq(mesg.get('headers').get('Key'), 'False')
            # HTTP params are received as multidict's and returned in similar shape.
            self.eq(mesg.get('params').get('param1'), ['somevalu', ])

            mesg = await core.callStorm('''
                $hdr = ( { "key": $lib.false } )
                $url = $lib.str.format('https://127.0.0.1:{port}/test/ws', port=$port)

                ($ok, $sock) = $lib.inet.http.connect($url, headers=$hdr, ssl_verify=$lib.false)
                if (not $ok) { $lib.exit($sock) }

                ($ok, $mesg) = $sock.rx()
                if (not $ok) { $lib.exit($mesg) }
                return($mesg)
            ''', opts={'vars': {'port': port}})
            self.eq(mesg.get('hi'), 'woot')
            self.eq(mesg.get('headers').get('Key'), 'False')
            self.none(mesg.get('params'))

            query = '''
            $url = $lib.str.format('https://127.0.0.1:{port}/test/ws', port=$port)

            ($ok, $sock) = $lib.inet.http.connect($url, proxy=$proxy, ssl_verify=$lib.false)
            if (not $ok) { $lib.exit($sock) }

            ($ok, $mesg) = $sock.rx()
            if (not $ok) { $lib.exit($mesg) }

            ($ok, $valu) = $sock.tx(lololol)
            return($sock.rx())
            '''
            opts = {'vars': {'port': port, 'proxy': True}}
            self.eq((True, ('echo', 'lololol')),
                    await core.callStorm(query, opts=opts))

            opts = {'vars': {'port': port, 'proxy': None}}
            mesgs = await core.stormlist(query, opts=opts)
            self.stormIsInWarn('proxy argument to $lib.null is deprecated', mesgs)
            self.true(mesgs[-2][0] == 'err' and mesgs[-2][1][1]['mesg'] == "(True, ['echo', 'lololol'])")

            visi = await core.auth.addUser('visi')

            opts = {'user': visi.iden, 'vars': {'port': port, 'proxy': False}}
            with self.raises(s_exc.AuthDeny) as cm:
                await core.callStorm(query, opts=opts)
            self.eq(cm.exception.get('mesg'), f'User {visi.name!r} ({visi.iden}) must have permission storm.lib.inet.http.proxy')

            await visi.setAdmin(True)

            opts = {'user': visi.iden,
                    'vars': {'port': port, 'proxy': 'socks5://user:pass@127.0.0.1:1'}}
            with self.raises(s_stormctrl.StormExit) as cm:
                await core.callStorm(query, opts=opts)
            self.isin('connect to proxy 127.0.0.1:1', str(cm.exception))

    async def test_storm_http_mtls(self):

        with self.getTestDir() as dirn:

            cdir = s_common.gendir(dirn, 'certs')
            cadir = s_common.gendir(cdir, 'cas')
            tdir = s_certdir.CertDir(cdir)
            tdir.genCaCert('somelocalca')
            tdir.genHostCert('localhost', signas='somelocalca')

            localkeyfp = tdir.getHostKeyPath('localhost')
            localcertfp = tdir.getHostCertPath('localhost')
            pkeypath = shutil.copyfile(localkeyfp, s_common.genpath(dirn, 'sslkey.pem'))
            certpath = shutil.copyfile(localcertfp, s_common.genpath(dirn, 'sslcert.pem'))

            tlscadir = s_common.gendir(dirn, 'cadir')
            cacertpath = shutil.copyfile(os.path.join(cadir, 'somelocalca.crt'), os.path.join(tlscadir, 'somelocalca.crt'))

            with s_common.genfile(cacertpath) as fd:
                ca_cert = fd.read().decode()

            pkey, cert = tdir.genUserCert('someuser', signas='somelocalca')
            user_pkey = tdir._pkeyToByts(pkey).decode()
            user_cert = tdir._certToByts(cert).decode()

            user_fullchain = user_cert + s_common.getbytes(cacertpath).decode()
            user_fullchain_key = user_fullchain + user_pkey

            conf = {'tls:ca:dir': tlscadir}
            async with self.getTestCore(dirn=dirn, conf=conf) as core:

                sslctx = core.initSslCtx(certpath, pkeypath)
                sslctx.load_verify_locations(cafile=cacertpath)

                addr, port = await core.addHttpsPort(0, sslctx=sslctx)
                root = await core.auth.getUserByName('root')
                await root.setPasswd('root')

                core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
                core.addHttpApi('/test/ws', TstWebSock, {})

                sslopts = {}

                opts = {
                    'vars': {
                        'url': f'https://root:root@localhost:{port}/api/v0/test',
                        'ws': f'https://localhost:{port}/test/ws',
                        'verify': True,
                        'sslopts': sslopts,
                    },
                }

                q = 'return($lib.inet.http.get($url, ssl_verify=$verify, ssl_opts=$sslopts))'

                size, sha256 = await core.callStorm('return($lib.bytes.put($lib.base64.decode(Zm9v)))')
                opts['vars']['sha256'] = sha256

                # mtls required

                sslctx.verify_mode = ssl.CERT_REQUIRED

                ## no client cert provided
                resp = await core.callStorm(q, opts=opts)
                self.eq(-1, resp['code'])
                self.isin('tlsv13 alert certificate required', resp['reason'])

                ## full chain cert w/key
                sslopts['client_cert'] = user_fullchain_key
                resp = await core.callStorm(q, opts=opts)
                self.eq(200, resp['code'])

                ## separate cert and key
                sslopts['client_cert'] = user_fullchain
                sslopts['client_key'] = user_pkey
                resp = await core.callStorm(q, opts=opts)
                self.eq(200, resp['code'])

                ## sslctx's are cached
                self.len(3, core._sslctx_cache)
                resp = await core.callStorm(q, opts=opts)
                self.eq(200, resp['code'])
                self.len(3, core._sslctx_cache)

                ## remaining methods
                self.eq(200, await core.callStorm('return($lib.inet.http.post($url, ssl_opts=$sslopts).code)', opts=opts))
                self.eq(200, await core.callStorm('return($lib.inet.http.head($url, ssl_opts=$sslopts).code)', opts=opts))
                self.eq(200, await core.callStorm('return($lib.inet.http.request(get, $url, ssl_opts=$sslopts).code)', opts=opts))

                ## connect
                ret = await core.callStorm('''
                    ($ok, $sock) = $lib.inet.http.connect($ws, ssl_opts=$sslopts)
                    if (not $ok) { return(($ok, $sock)) }
                    ($ok, $mesg) = $sock.rx()
                    return(($ok, $mesg))
                ''', opts=opts)
                self.true(ret[0])
                self.eq('woot', ret[1]['hi'])

                # Axon APIs

                axon_queries = {
                    'postfile': '''
                        $fields = ([{"name": "file", "sha256": $sha256}])
                        return($lib.inet.http.post($url, fields=$fields, ssl_opts=$sslopts).code)
                    ''',
                    'wget': 'return($lib.axon.wget($url, ssl_opts=$sslopts).code)',
                    'wput': 'return($lib.axon.wput($sha256, $url, method=POST, ssl_opts=$sslopts).code)',
                    'urlfile': 'yield $lib.axon.urlfile($url, ssl_opts=$sslopts)',
                }

                ## version check fails
                try:
                    oldv = core.axoninfo['synapse']['version']
                    core.axoninfo['synapse']['version'] = (2, 161, 0)
                    await self.asyncraises(s_exc.BadVersion, core.callStorm(axon_queries['postfile'], opts=opts))
                    await self.asyncraises(s_exc.BadVersion, core.callStorm(axon_queries['wget'], opts=opts))
                    await self.asyncraises(s_exc.BadVersion, core.callStorm(axon_queries['wput'], opts=opts))
                    await self.asyncraises(s_exc.BadVersion, core.nodes(axon_queries['urlfile'], opts=opts))
                finally:
                    core.axoninfo['synapse']['version'] = oldv

                ## version check succeeds
                self.eq(200, await core.callStorm(axon_queries['postfile'], opts=opts))
                self.eq(200, await core.callStorm(axon_queries['wget'], opts=opts))
                self.eq(200, await core.callStorm(axon_queries['wput'], opts=opts))
                self.len(1, await core.nodes(axon_queries['urlfile'], opts=opts))

                # verify arg precedence

                core.conf.pop('tls:ca:dir')
                core._sslctx_cache.clear()

                ## fail w/o ca
                resp = await core.callStorm(q, opts=opts)
                self.eq(-1, resp['code'])
                self.isin('self-signed certificate', resp['reason'])

                ## verify arg wins
                opts['vars']['verify'] = False
                sslopts['verify'] = True
                resp = await core.callStorm(q, opts=opts)
                self.eq(200, resp['code'])

                # bad opts

                ## schema violation
                sslopts['newp'] = 'wut'
                await self.asyncraises(s_exc.SchemaViolation, core.callStorm(q, opts=opts))
                sslopts.pop('newp')

                ## missing key
                sslopts['client_cert'] = user_fullchain
                sslopts['client_key'] = None
                await self.asyncraises(s_exc.BadArg, core.callStorm(q, opts=opts))

                ## bad cert
                sslopts['client_cert'] = 'not-gonna-work'
                await self.asyncraises(s_exc.BadArg, core.callStorm(q, opts=opts))

            # Provide a CA certificate directly
            async with self.getTestCore(dirn=dirn) as core:

                sslctx = core.initSslCtx(certpath, pkeypath)
                sslctx.load_verify_locations(cafile=cacertpath)

                addr, port = await core.addHttpsPort(0, sslctx=sslctx)
                root = await core.auth.getUserByName('root')
                await root.setPasswd('root')

                core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})

                sslopts = {}

                opts = {
                    'vars': {
                        'url': f'https://root:root@localhost:{port}/api/v0/test',
                        'verify': True,
                        'sslopts': sslopts,
                    },
                }

                q = 'return($lib.inet.http.get($url, ssl_verify=$verify, ssl_opts=$sslopts))'

                size, sha256 = await core.callStorm('return($lib.bytes.put($lib.base64.decode(Zm9v)))')
                opts['vars']['sha256'] = sha256

                ## no cert provided
                resp = await core.callStorm(q, opts=opts)
                self.eq(-1, resp['code'])
                self.isin('certificate verify failed', resp['reason'])

                ## provide just the CA Certificate
                sslopts['ca_cert'] = ca_cert
                resp = await core.callStorm(q, opts=opts)
                self.eq(200, resp['code'])
