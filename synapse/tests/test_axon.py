import io
import hashlib
import logging
import unittest.mock as mock

import aiohttp.client_exceptions as a_exc

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.telepath as s_telepath

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

asdfretn = (8, asdfhash)
emptyretn = (0, emptyhash)
pennretn = (9, pennhash)
rgryretn = (11, rgryhash)
bbufretn = (len(bbuf), bbufhash)

class AxonTest(s_t_utils.SynTest):

    async def check_blob(self, axon, fhash):
        chunks = []
        async for chunk in axon.get(fhash):
            chunks.append(chunk)
        buf = b''.join(chunks)
        ahash = hashlib.sha256(buf).digest()
        self.eq(fhash, ahash)

    async def runAxonTestBase(self, axon):

        tick = s_common.now()

        logger.info('asdfhash test')

        self.false(await axon.has(asdfhash))

        with self.raises(s_exc.NoSuchFile):
            async for _ in axon.get(asdfhash):
                pass

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

        logger.info('bbufhash test')

        self.false(await axon.has(bbufhash))

        self.eq((bbufhash,), await axon.wants((bbufhash, asdfhash)))

        async with await axon.upload() as fd:
            await fd.write(bbuf)
            self.eq(bbufretn, await fd.save())

        self.true(await axon.has(asdfhash))
        self.true(await axon.has(bbufhash))
        await self.check_blob(axon, bbufhash)

        self.eq((), await axon.wants((bbufhash, asdfhash)))

        logger.info('put() / puts() tests')
        # These don't add new data; but exercise apis to load data
        retn = await axon.put(abuf)
        self.eq(retn, asdfretn)

        retn = await axon.puts([abuf, bbuf])
        self.eq(retn, (asdfretn, bbufretn))

        logger.info('History and metrics')

        items = [x async for x in axon.hashes(0)]
        self.eq(((0, (asdfhash, 8)), (1, (bbufhash, 33554437))), items)

        items = [x[1] async for x in axon.history(tick)]
        self.eq(((asdfhash, 8), (bbufhash, 33554437)), items)

        items = [x[1] async for x in axon.history(0, tock=1)]
        self.eq((), items)

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(2, info.get('file:count'))

        logger.info('Empty file test')

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

        logger.info('Healthcheck test')
        snfo = await axon.getHealthCheck()
        self.eq(snfo.get('status'), 'nominal')
        axfo = [comp for comp in snfo.get('components') if comp.get('name') == 'axon'][0]
        self.eq(axfo.get('data'), await axon.metrics())

        logger.info('Upload context reuse')
        with mock.patch('synapse.axon.MAX_SPOOL_SIZE', s_axon.CHUNK_SIZE * 2):

            very_bigbuf = (s_axon.MAX_SPOOL_SIZE + 2) * b'V'
            vbighash = hashlib.sha256(very_bigbuf).digest()
            vbigretn = (len(very_bigbuf), vbighash)

            async with await axon.upload() as fd:
                # We can reuse the FD _after_ we have called save() on it.
                await fd.write(abuf)
                retn = await fd.save()
                self.eq(retn, asdfretn)

                logger.info('Reuse after uploading an existing file')
                # Now write a new file
                await fd.write(pbuf)
                retn = await fd.save()
                self.eq(retn, pennretn)
                await self.check_blob(axon, pennhash)

                logger.info('Reuse test with large file causing a rollover')
                for chunk in s_common.chunks(very_bigbuf, s_axon.CHUNK_SIZE):
                    await fd.write(chunk)
                retn = await fd.save()
                self.eq(retn, vbigretn)
                await self.check_blob(axon, vbighash)

                logger.info('Reuse test with small file post rollover')
                await fd.write(rbuf)
                retn = await fd.save()
                self.eq(retn, rgryretn)
                await self.check_blob(axon, rgryhash)

        info = await axon.metrics()
        self.eq(67108899, info.get('size:bytes'))
        self.eq(6, info.get('file:count'))

        # When testing a local axon, we want to ensure that the FD was in fact fini'd
        if isinstance(fd, s_axon.UpLoad):
            self.true(fd.fd.closed)

    async def test_axon_base(self):
        async with self.getTestAxon() as axon:
            self.isin('axon', axon.dmon.shared)
            await self.runAxonTestBase(axon)

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

            async with sess.get(f'{url_hs}/{asdfhash_h}') as resp:
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
                await self.agenraises(s_exc.AuthDeny, prox.hashes(0))
                await self.agenraises(s_exc.AuthDeny, prox.history(0))
                await self.asyncraises(s_exc.AuthDeny, prox.wants((asdfhash,)))
                await self.asyncraises(s_exc.AuthDeny, prox.put(abuf))
                await self.asyncraises(s_exc.AuthDeny, prox.puts((abuf,)))
                await self.asyncraises(s_exc.AuthDeny, prox.upload())
                await self.asyncraises(s_exc.AuthDeny, prox.metrics())
                # now add rules and run the test suite
                await user.addRule((True, ('health',)))
                await user.addRule((True, ('axon', 'get',)))
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
