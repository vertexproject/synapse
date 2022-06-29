import io
import os
import shutil
import asyncio
import hashlib
import logging
import unittest.mock as mock
import tornado.httputil as t_httputil

import aiohttp.client_exceptions as a_exc

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.certdir as s_certdir
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

# This causes blocks which are not homogeneous when sliced in kibibyte lengths
bbuf = b'0123456' * 4793491
abuf = b'asdfasdf'
pbuf = b'pennywise'
rbuf = b'robert gray'

bbufhash = hashlib.sha256(bbuf).digest()
asdfhash = hashlib.sha256(abuf).digest()
emptyhash = hashlib.sha256(b'').digest()
pennhash = hashlib.sha256(pbuf).digest()
rgryhash = hashlib.sha256(rbuf).digest()

fields = [
    {'name': 'file', 'sha256': s_common.ehex(asdfhash), 'filename': 'file'},
    {'name': 'zip_password', 'value': 'test'},
]

asdfretn = (8, asdfhash)
emptyretn = (0, emptyhash)
pennretn = (9, pennhash)
rgryretn = (11, rgryhash)
bbufretn = (len(bbuf), bbufhash)

linesbuf = b'''asdf

qwer
'''

jsonsbuf = b'''
{"foo": "bar"}
{"baz": "faz"}
'''

class HttpPushFile(s_httpapi.StreamHandler):

    async def prepare(self):
        self.gotsize = 0
        self.byts = b''

    async def data_received(self, byts):
        self.gotsize += len(byts)
        self.byts += byts

    async def put(self):
        assert self.gotsize == 8
        self.sendRestRetn(self.gotsize)

    async def post(self):
        args = {}
        files = {}
        t_httputil.parse_body_arguments(self.request.headers["Content-Type"],
                                        self.byts, args, files)
        item = files.get('file')[0]

        assert item['body'] == b'asdfasdf'
        assert item['filename'] == 'file'
        assert args.get('zip_password') == [b'test']
        self.sendRestRetn(self.gotsize)

class AxonTest(s_t_utils.SynTest):

    async def check_blob(self, axon, fhash):
        chunks = [chunk async for chunk in axon.get(fhash)]
        buf = b''.join(chunks)
        ahash = hashlib.sha256(buf).digest()
        self.eq(fhash, ahash)

    async def runAxonTestBase(self, axon):

        tick = s_common.now()

        # asdfhash test

        self.false(await axon.has(asdfhash))

        with self.raises(s_exc.NoSuchFile):
            async for _ in axon.get(asdfhash):
                pass

        with self.raises(s_exc.NoSuchFile):
            await axon.hashset(asdfhash)

        self.len(0, [item async for item in axon.hashes(0)])

        async with await axon.upload() as fd:
            await fd.write(abuf)
            self.eq(asdfretn, await fd.save())

        # do it again to test the short circuit
        async with await axon.upload() as fd:
            await fd.write(abuf)
            self.eq(asdfretn, await fd.save())

        bytz = []
        async for byts in axon.get(asdfhash):
            bytz.append(byts)

        self.eq(b'asdfasdf', b''.join(bytz))

        self.true(await axon.has(asdfhash))
        self.eq(8, await axon.size(asdfhash))

        # bbufhash test

        self.false(await axon.has(bbufhash))

        self.eq((bbufhash,), await axon.wants((bbufhash, asdfhash)))

        async with await axon.upload() as fd:
            await fd.write(bbuf)
            self.eq(bbufretn, await fd.save())

        self.true(await axon.has(asdfhash))
        self.true(await axon.has(bbufhash))
        await self.check_blob(axon, bbufhash)

        self.eq((), await axon.wants((bbufhash, asdfhash)))

        # put() / puts() tests
        # These don't add new data; but exercise apis to load data
        retn = await axon.put(abuf)
        self.eq(retn, asdfretn)

        retn = await axon.puts([abuf, bbuf])
        self.eq(retn, (asdfretn, bbufretn))

        # History and metrics

        items = [x async for x in axon.hashes(0)]
        self.eq(((0, (asdfhash, 8)), (1, (bbufhash, 33554437))), items)

        items = [x[1] async for x in axon.history(tick)]
        self.eq(((asdfhash, 8), (bbufhash, 33554437)), items)

        items = [x[1] async for x in axon.history(0, tock=1)]
        self.eq((), items)

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(2, info.get('file:count'))

        # Empty file test

        async with await axon.upload() as fd:
            await fd.write(b'')
            self.eq(emptyretn, await fd.save())

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(3, info.get('file:count'))

        bytz = []
        async for byts in axon.get(emptyhash):
            bytz.append(byts)

        self.eq(b'', b''.join(bytz))

        # Healthcheck test
        snfo = await axon.getHealthCheck()
        self.eq(snfo.get('status'), 'nominal')
        axfo = [comp for comp in snfo.get('components') if comp.get('name') == 'axon'][0]
        self.eq(axfo.get('data'), await axon.metrics())

        # Upload context reuse
        with mock.patch('synapse.axon.MAX_SPOOL_SIZE', s_axon.CHUNK_SIZE * 2):

            very_bigbuf = (s_axon.MAX_SPOOL_SIZE + 2) * b'V'
            vbighash = hashlib.sha256(very_bigbuf).digest()
            vbigretn = (len(very_bigbuf), vbighash)

            async with await axon.upload() as fd:
                # We can reuse the FD _after_ we have called save() on it.
                await fd.write(abuf)
                retn = await fd.save()
                self.eq(retn, asdfretn)

                # Reuse after uploading an existing file
                # Now write a new file
                await fd.write(pbuf)
                retn = await fd.save()
                self.eq(retn, pennretn)
                await self.check_blob(axon, pennhash)

                # Reuse test with large file causing a rollover
                for chunk in s_common.chunks(very_bigbuf, s_axon.CHUNK_SIZE):
                    await fd.write(chunk)
                retn = await fd.save()
                self.eq(retn, vbigretn)
                await self.check_blob(axon, vbighash)

                # Reuse test with small file post rollover
                await fd.write(rbuf)
                retn = await fd.save()
                self.eq(retn, rgryretn)
                await self.check_blob(axon, rgryhash)

        info = await axon.metrics()
        self.eq(67108899, info.get('size:bytes'))
        self.eq(6, info.get('file:count'))

        byts = b''.join([s_msgpack.en('foo'), s_msgpack.en('bar'), s_msgpack.en('baz')])
        size, sha256b = await axon.put(byts)
        sha256 = s_common.ehex(sha256b)
        self.eq(('foo', 'bar', 'baz'), [item async for item in axon.iterMpkFile(sha256)])

        # When testing a local axon, we want to ensure that the FD was in fact fini'd
        if isinstance(fd, s_axon.UpLoad):
            self.true(fd.fd.closed)

        self.true(await axon.del_(bbufhash))
        self.eq((False,), await axon.dels((bbufhash,)))

        info = await axon.metrics()
        self.eq(33554474, info.get('size:bytes'))
        self.eq(6, info.get('file:count'))

        self.notin(bbufretn[::-1], [item[1] async for item in axon.hashes(0)])

        self.false(await axon.del_(bbufhash))

        # deleted file re-added gets returned twice by hashes
        retn = await axon.put(bbuf)
        self.eq(retn, bbufretn)
        self.len(2, [item[1] async for item in axon.hashes(0) if item[1][0] == bbufhash])
        self.len(1, [item[1] async for item in axon.hashes(2) if item[1][0] == bbufhash])

        # readlines / jsonlines
        (lsize, l256) = await axon.put(linesbuf)
        (jsize, j256) = await axon.put(jsonsbuf)
        (bsize, b256) = await axon.put(b'\n'.join((jsonsbuf, linesbuf)))

        lines = [item async for item in axon.readlines(s_common.ehex(l256))]
        self.eq(('asdf', '', 'qwer'), lines)
        jsons = [item async for item in axon.jsonlines(s_common.ehex(j256))]
        self.eq(({'foo': 'bar'}, {'baz': 'faz'}), jsons)
        jsons = []
        with self.raises(s_exc.BadJsonText):
            async for item in axon.jsonlines(s_common.ehex(b256)):
                jsons.append(item)
        self.eq(({'foo': 'bar'}, {'baz': 'faz'}), jsons)

    async def test_axon_base(self):
        async with self.getTestAxon() as axon:
            self.isin('axon', axon.dmon.shared)
            await self.runAxonTestBase(axon)

            # test behavior for two concurrent uploads where the file exists once the lock is released
            self.eq(bbufretn, await axon.put(bbuf))
            self.true(await axon.has(bbufhash))

            def emptygen():
                if False:
                    yield None
                return

            self.eq(bbufretn[0], await axon.save(bbufhash, emptygen()))

    async def test_axon_proxy(self):
        async with self.getTestAxon() as axon:
            async with axon.getLocalProxy() as prox:
                await self.runAxonTestBase(prox)

    async def test_axon_http(self):

        # HTTP handlers on a standalone Axon
        async with self.getTestAxon() as axon:
            await self.runAxonTestHttp(axon)

    async def runAxonTestHttp(self, axon):
        host, port = await axon.addHttpsPort(0, host='127.0.0.1')

        newb = await axon.auth.addUser('newb')
        await newb.setPasswd('secret')

        url_de = f'https://localhost:{port}/api/v1/axon/files/del'
        url_ul = f'https://localhost:{port}/api/v1/axon/files/put'
        url_hs = f'https://localhost:{port}/api/v1/axon/files/has/sha256'
        url_dl = f'https://localhost:{port}/api/v1/axon/files/by/sha256'

        asdfhash_h = s_common.ehex(asdfhash)
        bbufhash_h = s_common.ehex(bbufhash)
        emptyhash_h = s_common.ehex(emptyhash)

        # Perms
        async with self.getHttpSess(auth=('newb', 'secret'), port=port) as sess:

            async with sess.get(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(403, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.delete(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(403, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.get(f'{url_hs}/{asdfhash_h}') as resp:
                self.eq(403, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.post(url_de) as resp:
                self.eq(403, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.post(url_ul, data=abuf) as resp:
                self.eq(403, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))

            # Stream file
            byts = io.BytesIO(bbuf)
            with self.raises((a_exc.ServerDisconnectedError,
                              a_exc.ClientOSError)):
                async with sess.post(url_ul, data=byts) as resp:
                    pass

        await newb.addRule((True, ('axon', 'get')))
        await newb.addRule((True, ('axon', 'has')))
        await newb.addRule((True, ('axon', 'del')))
        await newb.addRule((True, ('axon', 'upload')))

        # Basic
        async with self.getHttpSess(auth=('newb', 'secret'), port=port) as sess:
            async with sess.get(f'{url_dl}/foobar') as resp:
                self.eq(404, resp.status)

            async with sess.get(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(404, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.get(f'{url_hs}/{asdfhash_h}') as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.false(item.get('result'))

            async with sess.post(url_ul, data=abuf) as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(set(result.keys()), {'size', 'md5', 'sha1', 'sha256', 'sha512'})
                self.eq(result.get('size'), asdfretn[0])
                self.eq(result.get('sha256'), asdfhash_h)
                self.true(await axon.has(asdfhash))

            async with sess.get(f'{url_hs}/{asdfhash_h}') as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.true(item.get('result'))

            async with sess.put(url_ul, data=abuf) as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), asdfretn[0])
                self.eq(result.get('sha256'), asdfhash_h)
                self.true(await axon.has(asdfhash))

            async with sess.get(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(200, resp.status)
                self.eq(abuf, await resp.read())

            # Streaming upload
            byts = io.BytesIO(bbuf)

            async with sess.post(url_ul, data=byts) as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), bbufretn[0])
                self.eq(result.get('sha256'), bbufhash_h)
                self.true(await axon.has(bbufhash))

            byts = io.BytesIO(bbuf)

            async with sess.put(url_ul, data=byts) as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), bbufretn[0])
                self.eq(result.get('sha256'), bbufhash_h)
                self.true(await axon.has(bbufhash))

            byts = io.BytesIO(b'')

            async with sess.post(url_ul, data=byts) as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), emptyretn[0])
                self.eq(result.get('sha256'), emptyhash_h)
                self.true(await axon.has(emptyhash))

            # Streaming download
            async with sess.get(f'{url_dl}/{bbufhash_h}') as resp:
                self.eq(200, resp.status)

                byts = []
                async for bytz in resp.content.iter_chunked(1024):
                    byts.append(bytz)

                self.gt(len(byts), 1)
                self.eq(bbuf, b''.join(byts))

            # DELETE method by sha256
            async with sess.delete(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.true(item.get('result'))

            async with sess.delete(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(404, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))

            # test /api/v1/axon/file/del API
            data = {'sha256s': (asdfhash_h, asdfhash_h)}
            async with sess.post(url_de, json=data) as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.eq(((asdfhash_h, False), (asdfhash_h, False)), item.get('result'))

            data = {'newp': 'newp'}
            async with sess.post(url_de, json=data) as resp:
                self.eq(200, resp.status)
                item = await resp.json()
                self.eq('err', item.get('status'))
                self.eq('SchemaViolation', item.get('code'))

    async def test_axon_perms(self):
        async with self.getTestAxon() as axon:
            user = await axon.auth.addUser('user')
            await user.setPasswd('test')
            _, port = await axon.dmon.listen('tcp://127.0.0.1:0')
            aurl = f'tcp://user:test@127.0.0.1:{port}/axon'
            async with await s_telepath.openurl(aurl) as prox:  # type: s_axon.AxonApi
                # Ensure the user can't do things with bytes they don't have permissions too.
                await self.agenraises(s_exc.AuthDeny, prox.get(asdfhash))
                await self.asyncraises(s_exc.AuthDeny, prox.has(asdfhash))
                await self.asyncraises(s_exc.AuthDeny, prox.hashset(asdfhash))
                await self.agenraises(s_exc.AuthDeny, prox.hashes(0))
                await self.agenraises(s_exc.AuthDeny, prox.history(0))
                await self.asyncraises(s_exc.AuthDeny, prox.del_(asdfhash))
                await self.asyncraises(s_exc.AuthDeny, prox.dels((asdfhash,)))
                await self.asyncraises(s_exc.AuthDeny, prox.wants((asdfhash,)))
                await self.asyncraises(s_exc.AuthDeny, prox.put(abuf))
                await self.asyncraises(s_exc.AuthDeny, prox.puts((abuf,)))
                await self.asyncraises(s_exc.AuthDeny, prox.upload())
                await self.asyncraises(s_exc.AuthDeny, prox.metrics())
                # now add rules and run the test suite
                await user.addRule((True, ('health',)))
                await user.addRule((True, ('axon', 'get',)))
                await user.addRule((True, ('axon', 'del',)))
                await user.addRule((True, ('axon', 'has',)))
                await user.addRule((True, ('axon', 'upload',)))
                await self.runAxonTestBase(prox)

    async def test_axon_limits(self):

        async with self.getTestAxon(conf={'max:count': 10}) as axon:
            for i in range(10):
                await axon.put(s_common.buid())

            with self.raises(s_exc.HitLimit):
                await axon.put(s_common.buid())

        async with self.getTestAxon(conf={'max:bytes': 320}) as axon:
            for i in range(10):
                await axon.put(s_common.buid())

            with self.raises(s_exc.HitLimit):
                await axon.put(s_common.buid())

    async def test_axon_wget(self):

        async with self.getTestAxon() as axon:

            visi = await axon.auth.addUser('visi')
            await visi.setAdmin(True)
            await visi.setPasswd('secret')

            async with await axon.upload() as fd:
                await fd.write(b'asdfasdf')
                size, sha256 = await fd.save()

            host, port = await axon.addHttpsPort(0, host='127.0.0.1')

            sha2 = s_common.ehex(sha256)
            async with axon.getLocalProxy() as proxy:

                resp = await proxy.wget(f'https://visi:secret@127.0.0.1:{port}/api/v1/axon/files/by/sha256/{sha2}',
                                        ssl=False)
                self.eq(True, resp['ok'])
                self.eq(200, resp['code'])
                self.eq(8, resp['size'])
                self.eq('application/octet-stream', resp['headers']['Content-Type'])

                resp = await proxy.wget(f'http://visi:secret@127.0.0.1:{port}/api/v1/axon/files/by/sha256/{sha2}')
                self.false(resp['ok'])

                async def timeout(self):
                    await asyncio.sleep(2)
                with mock.patch.object(s_httpapi.ActiveV1, 'get', timeout):
                    resp = await proxy.wget(f'https://visi:secret@127.0.0.1:{port}/api/v1/active', timeout=1,
                                            ssl=False)
                    self.eq(False, resp['ok'])
                    self.eq('TimeoutError', resp['mesg'])

        conf = {'http:proxy': 'socks5://user:pass@127.0.0.1:1'}
        async with self.getTestAxon(conf=conf) as axon:
            async with axon.getLocalProxy() as proxy:
                resp = await proxy.wget('http://vertex.link')
                self.isin('Can not connect to proxy 127.0.0.1:1', resp.get('mesg', ''))

    async def test_axon_wput(self):

        async with self.getTestCore() as core:

            axon = core.axon
            axon.addHttpApi('/api/v1/pushfile', HttpPushFile, {'cell': axon})

            async with await axon.upload() as fd:
                await fd.write(b'asdfasdf')
                size, sha256 = await fd.save()

            host, port = await axon.addHttpsPort(0, host='127.0.0.1')

            async with axon.getLocalProxy() as proxy:

                resp = await proxy.wput(sha256, f'https://127.0.0.1:{port}/api/v1/pushfile', method='PUT', ssl=False)
                self.eq(True, resp['ok'])
                self.eq(200, resp['code'])

            opts = {'vars': {'sha256': s_common.ehex(sha256)}}
            q = f'return($lib.axon.wput($sha256, "https://127.0.0.1:{port}/api/v1/pushfile", ssl=(0)))'
            resp = await core.callStorm(q, opts=opts)
            self.eq(True, resp['ok'])
            self.eq(200, resp['code'])

            opts = {'vars': {'sha256': s_common.ehex(s_common.buid())}}
            resp = await core.callStorm(q, opts=opts)
            self.eq(False, resp['ok'])
            self.isin('Axon does not contain the requested file.', resp.get('mesg'))

            q = f'''
            $fields = $lib.list(
                $lib.dict(name=file, sha256=$sha256, filename=file),
                $lib.dict(name=zip_password, value=test)
            )
            $resp = $lib.inet.http.post("https://127.0.0.1:{port}/api/v1/pushfile",
                                        fields=$fields, ssl_verify=(0))
            return($resp)
            '''
            opts = {'vars': {'sha256': s_common.ehex(sha256)}}
            resp = await core.callStorm(q, opts=opts)
            self.true(resp['ok'])
            self.eq(200, resp['code'])

            opts = {'vars': {'sha256': s_common.ehex(s_common.buid())}}
            resp = await core.callStorm(q, opts=opts)
            self.false(resp['ok'])
            self.isin('Axon does not contain the requested file.', resp.get('err'))

            async with axon.getLocalProxy() as proxy:
                resp = await proxy.postfiles(fields, f'https://127.0.0.1:{port}/api/v1/pushfile', ssl=False)
                self.true(resp['ok'])
                self.eq(200, resp['code'])

        conf = {'http:proxy': 'socks5://user:pass@127.0.0.1:1'}
        async with self.getTestAxon(conf=conf) as axon:
            async with axon.getLocalProxy() as proxy:
                resp = await proxy.postfiles(fields, f'https://127.0.0.1:{port}/api/v1/pushfile', ssl=False)
                self.false(resp['ok'])
                self.isin('Can not connect to proxy 127.0.0.1:1', resp.get('err', ''))

    async def test_axon_tlscapath(self):

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

            conf = {'auth:passwd': 'root'}
            async with self.getTestAxon(dirn=dirn, conf=conf) as axon:
                host, port = await axon.addHttpsPort(0, host='127.0.0.1')
                url = f'https://root:root@127.0.0.1:{port}/api/v1/active'
                resp = await axon.wget(url)
                self.false(resp.get('ok'))
                self.isin('unable to get local issuer certificate', resp.get('mesg'))

                retn = await axon.put(abuf)
                self.eq(retn, asdfretn)
                axon.addHttpApi('/api/v1/pushfile', HttpPushFile, {'cell': axon})
                url = f'https://root:root@127.0.0.1:{port}/api/v1/pushfile'
                resp = await axon.wput(asdfhash, url)
                self.false(resp.get('ok'))
                self.isin('unable to get local issuer certificate', resp.get('mesg'))

                resp = await axon.postfiles(fields, url)
                self.false(resp.get('ok'))
                self.isin('unable to get local issuer certificate', resp.get('err'))

            conf = {'auth:passwd': 'root', 'tls:ca:dir': tlscadir}
            async with self.getTestAxon(dirn=dirn, conf=conf) as axon:
                host, port = await axon.addHttpsPort(0, host='127.0.0.1')
                url = f'https://root:root@localhost:{port}/api/v1/active'
                resp = await axon.wget(url)
                self.true(resp.get('ok'))

                retn = await axon.put(abuf)
                self.eq(retn, asdfretn)
                axon.addHttpApi('/api/v1/pushfile', HttpPushFile, {'cell': axon})
                url = f'https://root:root@localhost:{port}/api/v1/pushfile'
                resp = await axon.wput(asdfhash, url)
                self.true(resp.get('ok'))

                resp = await axon.postfiles(fields, url)
                self.true(resp.get('ok'))
