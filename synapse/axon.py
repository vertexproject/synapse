import asyncio
import hashlib
import logging
import tempfile

import aiohttp
import aiohttp_socks

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.base as s_base
import synapse.lib.const as s_const
import synapse.lib.share as s_share
import synapse.lib.hashset as s_hashset
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab
import synapse.lib.slabseqn as s_slabseqn

logger = logging.getLogger(__name__)

CHUNK_SIZE = 16 * s_const.mebibyte
MAX_SPOOL_SIZE = CHUNK_SIZE * 32  # 512 mebibytes
MAX_HTTP_UPLOAD_SIZE = 4 * s_const.tebibyte

class AxonHttpUploadV1(s_httpapi.StreamHandler):

    async def prepare(self):
        self.upfd = None

        if not await self.reqAuthAllowed(('axon', 'upload')):
            await self.finish()

        # max_body_size defaults to 100MB and requires a value
        self.request.connection.set_max_body_size(MAX_HTTP_UPLOAD_SIZE)

        self.upfd = await self.cell.upload()
        self.hashset = s_hashset.HashSet()

    async def data_received(self, chunk):
        if chunk is not None:
            await self.upfd.write(chunk)
            self.hashset.update(chunk)
            await asyncio.sleep(0)

    def on_finish(self):
        if self.upfd is not None and not self.upfd.isfini:
            self.cell.schedCoroSafe(self.upfd.fini())

    def on_connection_close(self):
        self.on_finish()

    async def _save(self):
        size, sha256b = await self.upfd.save()

        fhashes = {htyp: hasher.hexdigest() for htyp, hasher in self.hashset.hashes}

        assert sha256b == s_common.uhex(fhashes.get('sha256'))
        assert size == self.hashset.size

        fhashes['size'] = size

        return self.sendRestRetn(fhashes)

    async def post(self):
        '''
        Called after all data has been read.
        '''
        await self._save()
        return

    async def put(self):
        await self._save()
        return

class AxonHttpHasV1(s_httpapi.Handler):

    async def get(self, sha256):
        if not await self.reqAuthAllowed(('axon', 'has')):
            return
        resp = await self.cell.has(s_common.uhex(sha256))
        return self.sendRestRetn(resp)

class AxonHttpDownloadV1(s_httpapi.Handler):

    async def get(self, sha256):

        if not await self.reqAuthAllowed(('axon', 'get')):
            return

        sha256b = s_common.uhex(sha256)

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment')

        try:
            async for byts in self.cell.get(sha256b):
                self.write(byts)
                await self.flush()
                await asyncio.sleep(0)

        except s_exc.NoSuchFile as e:
            self.set_status(404)
            self.sendRestErr('NoSuchFile', e.get('mesg'))

        return

class UpLoad(s_base.Base):

    async def __anit__(self, axon):  # type: ignore

        await s_base.Base.__anit__(self)

        self.axon = axon
        self.fd = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE)
        self.size = 0
        self.sha256 = hashlib.sha256()
        self.onfini(self._uploadFini)

    def _uploadFini(self):
        self.fd.close()

    def _reset(self):
        if self.fd._rolled or self.fd.closed:
            self.fd.close()
            self.fd = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE)
        else:
            # If we haven't rolled over, this skips allocating new objects
            self.fd.truncate(0)
            self.fd.seek(0)
        self.size = 0
        self.sha256 = hashlib.sha256()

    async def write(self, byts):
        self.size += len(byts)
        self.sha256.update(byts)
        self.fd.write(byts)

    async def save(self):

        sha256 = self.sha256.digest()
        rsize = self.size

        if await self.axon.has(sha256):
            self._reset()
            return rsize, sha256

        def genr():

            self.fd.seek(0)

            while True:

                if self.isfini:
                    raise s_exc.IsFini()

                byts = self.fd.read(CHUNK_SIZE)
                if not byts:
                    return

                yield byts

        await self.axon.save(sha256, genr())

        self._reset()
        return rsize, sha256

class UpLoadShare(UpLoad, s_share.Share):  # type: ignore
    typename = 'upload'

    async def __anit__(self, axon, link):
        await UpLoad.__anit__(self, axon)
        await s_share.Share.__anit__(self, link, None)

class AxonApi(s_cell.CellApi, s_share.Share):  # type: ignore

    async def __anit__(self, cell, link, user):
        await s_cell.CellApi.__anit__(self, cell, link, user)
        await s_share.Share.__anit__(self, link, None)

    async def get(self, sha256):
        await self._reqUserAllowed(('axon', 'get'))
        async for byts in self.cell.get(sha256):
            yield byts

    async def has(self, sha256):
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.has(sha256)

    async def size(self, sha256):
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.size(sha256)

    async def hashes(self, offs):
        await self._reqUserAllowed(('axon', 'has'))
        async for item in self.cell.hashes(offs):
            yield item

    async def history(self, tick, tock=None):
        await self._reqUserAllowed(('axon', 'has'))
        async for item in self.cell.history(tick, tock=tock):
            yield item

    async def wants(self, sha256s):
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.wants(sha256s)

    async def put(self, byts):
        await self._reqUserAllowed(('axon', 'upload'))
        return await self.cell.put(byts)

    async def puts(self, files):
        await self._reqUserAllowed(('axon', 'upload'))
        return await self.cell.puts(files)

    async def upload(self):
        await self._reqUserAllowed(('axon', 'upload'))
        return await UpLoadShare.anit(self.cell, self.link)

    async def wget(self, url, params=None, headers=None, json=None, body=None, method='GET', ssl=True, timeout=None):
        await self._reqUserAllowed(('axon', 'wget'))
        return await self.cell.wget(url, params=params, headers=headers, json=json, body=body, method=method, ssl=ssl, timeout=timeout)

    async def metrics(self):
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.metrics()

    async def iterMpkFile(self, sha256):
        await self._reqUserAllowed(('axon', 'get'))
        async for item in self.cell.iterMpkFile(sha256):
            yield item

class Axon(s_cell.Cell):

    cellapi = AxonApi

    confdefs = {
        'max:bytes': {
            'description': 'The maximum number of bytes that can be stored in the Axon.',
            'type': 'integer',
            'minimum': 1,
            'hidecmdl': True,
        },
        'max:count': {
            'description': 'The maximum number of files that can be stored in the Axon.',
            'type': 'integer',
            'minimum': 1,
            'hidecmdl': True,
        },
        'http:proxy': {
            'description': 'An aiohttp-socks compatible proxy URL to use in the wget API.',
            'type': 'string',
        },
    }

    async def __anit__(self, dirn, conf=None):  # type: ignore

        await s_cell.Cell.__anit__(self, dirn, conf=conf)

        # share ourself via the cell dmon as "axon"
        # for potential default remote use
        self.dmon.share('axon', self)

        path = s_common.gendir(self.dirn, 'axon.lmdb')
        self.axonslab = await s_lmdbslab.Slab.anit(path)
        self.sizes = self.axonslab.initdb('sizes')
        self.onfini(self.axonslab.fini)

        self.axonhist = s_lmdbslab.Hist(self.axonslab, 'history')
        self.axonseqn = s_slabseqn.SlabSeqn(self.axonslab, 'axonseqn')

        node = await self.hive.open(('axon', 'metrics'))
        self.axonmetrics = await node.dict()
        self.axonmetrics.setdefault('size:bytes', 0)
        self.axonmetrics.setdefault('file:count', 0)

        self.maxbytes = self.conf.get('max:bytes')
        self.maxcount = self.conf.get('max:count')

        self.addHealthFunc(self._axonHealth)

        # modularize blob storage
        await self._initBlobStor()

        self._initAxonHttpApi()

    def _reqBelowLimit(self):

        if (self.maxbytes is not None and
            self.maxbytes <= self.axonmetrics.get('size:bytes')):
            mesg = f'Axon is at size:bytes limit: {self.maxbytes}'
            raise s_exc.HitLimit(mesg=mesg)

        if (self.maxcount is not None and
            self.maxcount <= self.axonmetrics.get('file:count')):
            mesg = f'Axon is at file:count limit: {self.maxcount}'
            raise s_exc.HitLimit(mesg=mesg)

    async def _axonHealth(self, health):
        health.update('axon', 'nominal', '', data=await self.metrics())

    async def _initBlobStor(self):
        path = s_common.gendir(self.dirn, 'blob.lmdb')
        self.blobslab = await s_lmdbslab.Slab.anit(path)
        self.blobs = self.blobslab.initdb('blobs')
        self.onfini(self.blobslab.fini)

    def _initAxonHttpApi(self):
        self.addHttpApi('/api/v1/axon/files/put', AxonHttpUploadV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/has/sha256/([0-9a-fA-F]{64}$)', AxonHttpHasV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/by/sha256/([0-9a-fA-F]{64}$)', AxonHttpDownloadV1, {'cell': self})

    def _addSyncItem(self, item):
        self.axonhist.add(item)
        self.axonseqn.add(item)

    async def history(self, tick, tock=None):
        for item in self.axonhist.carve(tick, tock=tock):
            yield item

    async def hashes(self, offs):
        for item in self.axonseqn.iter(offs):
            yield item

    async def get(self, sha256):

        if not await self.has(sha256):
            raise s_exc.NoSuchFile(mesg='Axon does not contain the requested file.', sha256=s_common.ehex(sha256))

        async for byts in self._get(sha256):
            yield byts

    async def _get(self, sha256):

        for _, byts in self.blobslab.scanByPref(sha256, db=self.blobs):
            yield byts

    async def put(self, byts):
        # Use a UpLoad context manager so that we can
        # ensure that a one-shot set of bytes is chunked
        # in a consistent fashion.
        async with await self.upload() as fd:
            await fd.write(byts)
            return await fd.save()

    async def puts(self, files):
        return [await self.put(b) for b in files]

    async def upload(self):
        return await UpLoad.anit(self)

    async def has(self, sha256):
        return self.axonslab.get(sha256, db=self.sizes) is not None

    async def size(self, sha256):
        byts = self.axonslab.get(sha256, db=self.sizes)
        if byts is not None:
            return int.from_bytes(byts, 'big')

    async def metrics(self):
        return dict(self.axonmetrics.items())

    async def save(self, sha256, genr):

        self._reqBelowLimit()
        byts = self.axonslab.get(sha256, db=self.sizes)
        if byts is not None:
            return int.from_bytes(byts, 'big')

        size = await self._saveFileGenr(sha256, genr)

        self._addSyncItem((sha256, size))

        await self.axonmetrics.set('file:count', self.axonmetrics.get('file:count') + 1)
        await self.axonmetrics.set('size:bytes', self.axonmetrics.get('size:bytes') + size)

        self.axonslab.put(sha256, size.to_bytes(8, 'big'), db=self.sizes)

        return size

    async def _saveFileGenr(self, sha256, genr):
        size = 0
        for i, byts in enumerate(genr):
            size += len(byts)
            lkey = sha256 + i.to_bytes(8, 'big')
            self.blobslab.put(lkey, byts, db=self.blobs)
            await asyncio.sleep(0)
        return size

    async def wants(self, sha256s):
        '''
        Given a list of sha256 bytes, returns a list of the hashes we want bytes for.
        '''
        return [s for s in sha256s if not await self.has(s)]

    async def iterMpkFile(self, sha256):
        '''
        Yield items from a .mpk message pack stream file.
        '''
        unpk = s_msgpack.Unpk()
        async for byts in self.get(s_common.uhex(sha256)):
            for _, item in unpk.feed(byts):
                yield item

    async def wget(self, url, params=None, headers=None, json=None, body=None, method='GET', ssl=True, timeout=None):
        '''
        Stream a file download directly into the axon.
        '''
        connector = None
        proxyurl = self.conf.get('http:proxy')
        if proxyurl is not None:
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        atimeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=atimeout) as sess:

            try:

                async with sess.request(method, url, headers=headers, params=params, json=json, data=body, ssl=ssl) as resp:

                    info = {
                        'ok': True,
                        'url': str(resp.url),
                        'code': resp.status,
                        'headers': dict(resp.headers),
                    }

                    hashset = s_hashset.HashSet()

                    async with await self.upload() as upload:

                        async for byts in resp.content.iter_chunked(CHUNK_SIZE):
                            await upload.write(byts)
                            hashset.update(byts)

                        size, _ = await upload.save()

                    info['size'] = size
                    info['hashes'] = dict([(n, s_common.ehex(h)) for (n, h) in hashset.digests()])

                    return info

            except asyncio.CancelledError:
                raise

            except Exception as e:
                exc = s_common.excinfo(e)
                mesg = exc.get('errmsg')
                if not mesg:
                    mesg = exc.get('err')

                return {
                    'ok': False,
                    'mesg': mesg,
                }
