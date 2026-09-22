import unittest.mock as mock

import synapse.exc as s_exc

import synapse.lib.cmd as s_cmd
import synapse.lib._http as s_http
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.httpclient as s_httpclient
import synapse.lib.crypto.passwd as s_passwd

import synapse.tests.utils as s_test

class FakeContent:
    '''
    Stand in for the content of an aiohttp response.
    '''
    def __init__(self, chunks):
        self.chunks = chunks

    async def iter_any(self):
        for byts in self.chunks:
            yield byts

class FakeResp:
    '''
    Stand in for an aiohttp response context manager.
    '''
    def __init__(self, chunks, status=200):
        self.status = status
        self.content = FakeContent(chunks)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

class HttpCortexTest(s_test.SynTest):

    async def test_lib_http_urls(self):

        # only https:// URLs are handled by the HTTP API client
        self.true(s_http.isHttpsUrl('https://foo.bar.com:4443/'))
        self.true(s_http.isHttpsUrl('HTTPS://foo.bar.com/'))
        self.false(s_http.isHttpsUrl('http://foo.bar.com/'))
        self.false(s_http.isHttpsUrl('cell:///vertex/storage'))

        # the base URL is built without userinfo and with a default port
        self.eq('https://foo.bar.com:443', s_http.getBaseUrl({'host': 'foo.bar.com', 'path': '/'}))
        self.eq('https://foo.bar.com:443', s_http.getBaseUrl({'host': 'foo.bar.com', 'path': ''}))
        self.eq('https://[::1]:4443/optic', s_http.getBaseUrl({'host': '::1', 'port': 4443, 'path': '/optic/'}))

    async def test_lib_http_args(self):

        pars = s_cmd.Parser(prog='test', outp=self.getTestOutp())
        s_http.addHttpsArgs(pars)

        opts = pars.parse_args(())
        self.none(opts.https_proxy)
        self.none(opts.https_ca_dir)
        self.false(opts.https_noverify)

        # the shared options are a no-op with a telepath URL
        s_http.reqTeleOpts(opts)

        argv = ('--https-proxy', 'socks5://127.0.0.1:9050',
                '--https-ca-dir', '/path/to/cas', '--https-noverify')
        opts = pars.parse_args(argv)
        self.eq('socks5://127.0.0.1:9050', opts.https_proxy)
        self.eq('/path/to/cas', opts.https_ca_dir)
        self.true(opts.https_noverify)

        # ...and each is rejected on its own with one
        for argv in (('--https-proxy', 'socks5://127.0.0.1:9050'),
                     ('--https-ca-dir', '/path/to/cas'),
                     ('--https-noverify',)):

            with self.raises(s_exc.BadArg) as cm:
                s_http.reqTeleOpts(pars.parse_args(argv))
            self.isin('may only be used with an https:// Cortex URL', cm.exception.get('mesg'))

    async def test_lib_http_apikey(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getHttpsApiInfo(core)

            # an API key is required in the URL
            with self.raises(s_exc.BadArg) as cm:
                await s_http.HttpCortex.anit(f'https://127.0.0.1:{port}', verify=False)
            self.isin('https://<apikey>@host:port/', cm.exception.get('mesg'))

            # a malformed API key is rejected before any network activity
            with self.raises(s_exc.BadArg) as cm:
                await s_http.HttpCortex.anit(f'https://not+a+key@127.0.0.1:{port}', verify=False)
            self.isin('not a valid Synapse user API key', cm.exception.get('mesg'))

            # a well formed but unknown API key is rejected by the Cortex
            _, badkey, _ = await s_passwd.generateApiKey()
            with self.raises(s_exc.AuthDeny) as cm:
                await s_http.HttpCortex.anit(f'https://{badkey}@127.0.0.1:{port}', verify=False)
            self.isin('The session is not logged in.', cm.exception.get('mesg'))

            # only https is supported by the HTTP client
            for badurl in (f'cell://{apikey}@newp', f'http://{apikey}@127.0.0.1:{port}'):
                with self.raises(s_exc.BadUrl) as cm:
                    await s_http.HttpCortex.anit(badurl)
                self.isin('requires an https:// URL', cm.exception.get('mesg'))

            # the TLS CA directory must exist
            with self.raises(s_exc.BadArg) as cm:
                await s_http.HttpCortex.anit(f'https://{apikey}@127.0.0.1:{port}', cadir='/newp')
            self.isin('TLS CA directory does not exist', cm.exception.get('mesg'))

            # a base path which does not host the API has no JSON envelope to report
            with self.raises(s_exc.SynErr) as cm:
                await s_http.HttpCortex.anit(f'https://{apikey}@127.0.0.1:{port}/newp', verify=False)
            self.isin('REST API request failed (HTTP 404)', cm.exception.get('mesg'))

    async def test_lib_http_useragent(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getHttpsApiInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            useragent = s_httpclient.getUserAgent(s_http.USER_AGENT_PROD, s_version.version)
            self.eq(f'Synapse-Client/{s_version.version} (Synapse/{s_version.version}; https://vertex.link)',
                    useragent)

            core.addHttpApi('/api/v0/reflect', s_test.HttpReflector, {'cell': core})

            async with await s_http.HttpCortex.anit(url, verify=False) as prox:

                # the client identifies itself rather than sending the aiohttp default
                self.eq(useragent, prox.sess.headers.get('User-Agent'))

                async with prox.sess.get(prox._getUrl('/api/v0/reflect'), **prox.reqinfo) as resp:
                    item = await resp.json()

                headers = {name.lower(): valu for (name, valu) in item['result']['headers'].items()}
                self.eq(useragent, headers.get('user-agent'))

    async def test_lib_http_keepalive(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getHttpsApiInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_http.HttpCortex.anit(url, verify=False) as prox:

                self.none(prox.sess.timeout.total)

                calls = []
                realpost = prox.sess.post

                def post(url, **kwargs):
                    calls.append((url, kwargs.get('json'), kwargs.get('timeout')))
                    return realpost(url, **kwargs)

                with mock.patch.object(prox.sess, 'post', post):

                    await s_test.alist(prox.storm('$lib.print(woot)'))
                    await prox.callStorm('return((0))')
                    await s_test.alist(prox.exportStorm('inet:ip'))
                    await s_test.alist(prox.storm('$lib.print(woot)', opts={'keepalive': 30}))

                stormurl, body, timeout = calls[0]
                self.eq(f'{url.split("@")[1]}/api/v3/storm', stormurl.split('//')[1])
                self.eq(6, body['opts']['keepalive'])
                self.notin('stream', body)
                self.none(timeout)

                # callStorm and exportStorm do not emit keepalive messages
                self.notin('keepalive', calls[1][1].get('opts', {}))
                self.notin('keepalive', calls[2][1].get('opts', {}))
                self.none(calls[1][2])

                # the export request is bounded rather than allowed to hang forever
                self.eq(s_http.EXPORT_TIMEOUT, calls[2][2].total)

                # an explicit keepalive wins over the default
                self.eq(30, calls[3][1]['opts']['keepalive'])

                # the Cortex really does emit ping messages
                msgs = await s_test.alist(prox.storm('$lib.time.sleep(0.35)', opts={'keepalive': 0.1}))
                pings = [m for m in msgs if m[0] == 'ping']
                self.gt(len(pings), 0)
                self.eq({}, pings[0][1])

    async def test_lib_http_bigmesg(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getHttpsApiInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            # a single storm message larger than the aiohttp StreamReader high water mark
            # ( 524288 bytes ) must survive the jsonlines reassembly. reading the stream
            # with readline() raises LineTooLong for a message this size, which is why
            # iterJsonLines() buffers over iter_any() instead.
            size = 1000000
            q = f'$valu = $lib.cast(str, A) $lib.fire(bigmesg, data=$valu.ljust({size}, A))'

            async with await s_http.HttpCortex.anit(url, verify=False) as prox:

                msgs = await s_test.alist(prox.storm(q))

                fired = [m for m in msgs if m[0] == 'storm:fire']
                self.len(1, fired)
                self.eq('bigmesg', fired[0][1].get('type'))
                self.eq('A' * size, fired[0][1]['data'].get('data'))

                # the stream still terminated cleanly
                self.eq('fini', msgs[-1][0])

    async def test_lib_http_redirect(self):

        async with self.getTestCore() as core:

            port, apikey = await self.getHttpsApiInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            core.addHttpApi('/api/v0/reflect', s_test.HttpReflector, {'cell': core})

            async with await s_http.HttpCortex.anit(url, verify=False) as prox:

                reflect = prox._getUrl('/api/v0/reflect')

                # the X-API-KEY header is a session default, and aiohttp only strips
                # Authorization / Cookie / Proxy-Authorization from a redirect. without
                # allow_redirects=False the key would be replayed to the redirect target.
                async with prox.sess.get(f'{reflect}?redirect={reflect}', **prox.reqinfo) as resp:
                    self.eq(302, resp.status)

                # the same request which follows the redirect does carry the key onward
                info = dict(prox.reqinfo)
                info['allow_redirects'] = True

                async with prox.sess.get(f'{reflect}?redirect={reflect}', **info) as resp:
                    self.eq(200, resp.status)
                    item = await resp.json()

                self.isin('x-api-key', [k.lower() for k in item['result']['headers']])

    async def test_lib_http_jsonlines(self):

        async def genr(chunks):
            for byts in chunks:
                yield byts

        # a message split across chunks is reassembled
        chunks = (b'["pri', b'nt",{"mesg":"woot"}]\n["fini",{}]\n')
        msgs = await s_test.alist(s_http.iterJsonLines(genr(chunks)))
        self.eq([['print', {'mesg': 'woot'}], ['fini', {}]], msgs)

        # empty chunks and multiple messages per chunk are handled
        chunks = (b'', b'["init",{}]\n["print",{"mesg":"a"}]\n', b'', b'["fini",{}]\n')
        msgs = await s_test.alist(s_http.iterJsonLines(genr(chunks)))
        self.len(3, msgs)
        self.eq('init', msgs[0][0])

        # a trailing partial message is not yielded
        msgs = await s_test.alist(s_http.iterJsonLines(genr((b'["init",{}]\n["pri',))))
        self.eq([['init', {}]], msgs)

    async def test_lib_http_addstormpkg(self):

        pkgdef = {'name': 'httppkg', 'version': '1.2.3'}

        async with self.getTestCore() as core:

            port, apikey = await self.getHttpsApiInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_http.HttpCortex.anit(url, verify=False) as prox:

                self.none(await prox.addStormPkg(pkgdef))

                gotdef = await core.getStormPkg('httppkg')
                self.eq('1.2.3', gotdef.get('version'))

                # an unsigned package is rejected when the Cortex is told to verify
                with self.raises(s_exc.BadPkgDef) as cm:
                    await prox.addStormPkg(pkgdef, verify=True)
                self.isin('not signed', cm.exception.get('mesg'))

            # the same pkg.add permission the telepath CoreApi method confirms
            lowuser = await core.auth.addUser('lowuser')
            lowkey, _ = await core.addUserApiKey(lowuser.iden, 'lowuser')

            async with await s_http.HttpCortex.anit(f'https://{lowkey}@127.0.0.1:{port}', verify=False) as prox:

                with self.raises(s_exc.AuthDeny) as cm:
                    await prox.addStormPkg({'name': 'newppkg', 'version': '1.2.3'})
                self.isin('pkg.add', cm.exception.get('mesg'))

    async def test_lib_http_errors(self):

        async with self.getTestCluster() as clus:
            core = clus.cortex

            port, apikey = await self.getHttpsApiInfo(core)
            url = f'https://{apikey}@127.0.0.1:{port}'

            async with await s_http.HttpCortex.anit(url, verify=False) as prox:

                # error envelopes are converted back into synapse exceptions
                with self.raises(s_exc.NoSuchView):
                    await prox.callStorm('return((0))', opts={'view': 'a' * 32})

                with self.raises(s_exc.NoSuchView):
                    await s_test.alist(prox.storm('inet:ip', opts={'view': 'a' * 32}))

                with self.raises(s_exc.NoSuchView):
                    await s_test.alist(prox.exportStorm('inet:ip', opts={'view': 'a' * 32}))

                # a missing file is normalized to match the telepath API
                with self.raises(s_exc.NoSuchFile) as cm:
                    await s_test.alist(prox.getAxonBytes('00' * 32))
                self.eq('Axon does not contain the requested file.', cm.exception.get('mesg'))
                self.eq('00' * 32, cm.exception.get('sha256'))

                # a truncated storm stream is reported rather than silently accepted
                async def truncated(genr):
                    yield ['init', {}]

                with mock.patch.object(s_http, 'iterJsonLines', truncated):
                    msgs = await s_test.alist(prox.storm('inet:ip'))

                self.eq('err', msgs[-1][0])
                self.eq('LinkShutDown', msgs[-1][1][0])

                # a truncated export stream raises rather than returning a short result
                pode = (('inet:ip', (4, 0x01020304)), {})
                byts = s_msgpack.en(pode)

                def post(url, **kwargs):
                    return FakeResp((byts, byts[:-3]))

                with mock.patch.object(prox.sess, 'post', post):
                    with self.raises(s_exc.BadDataValu) as cm:
                        await s_test.alist(prox.exportStorm('inet:ip'))
                self.isin('partial node', cm.exception.get('mesg'))

            # a user without the axon permissions gets a useful error rather than a hang
            lowuser = await core.auth.addUser('lowuser')
            lowkey, _ = await core.addUserApiKey(lowuser.iden, 'lowuser')

            async with await s_http.HttpCortex.anit(f'https://{lowkey}@127.0.0.1:{port}', verify=False) as prox:

                with self.raises(s_exc.AuthDeny):
                    await s_test.alist(prox.getAxonBytes('00' * 32))

                # the upload queue must not deadlock when the request fails early
                with self.raises(s_exc.AuthDeny):
                    async with await prox.getAxonUpload() as upload:
                        for _ in range(s_http.UPLOAD_QSIZE + 1):
                            await upload.write(b'A' * 10000000)
                        await upload.save()

            async with await s_http.HttpCortex.anit(url, verify=False) as prox:

                # an upload which ends before all the bytes are sent is an error
                async def _runUpload(self):
                    return {'size': 0, 'sha256': '00' * 32}

                with mock.patch.object(s_http.HttpUpload, '_runUpload', _runUpload):

                    async with await prox.getAxonUpload() as upload:

                        upload._initUpload()
                        for _ in range(s_http.UPLOAD_QSIZE):
                            upload.queue.put_nowait(b'A')

                        await upload.task

                        with self.raises(s_exc.BadDataValu) as cm:
                            await upload.write(b'A')

                self.isin('ended before all bytes were sent', cm.exception.get('mesg'))
