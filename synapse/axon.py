import csv
import json
import asyncio
import hashlib
import logging
import tempfile
import contextlib

import aiohttp
import aiohttp_socks

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.coro as s_coro
import synapse.lib.base as s_base
import synapse.lib.link as s_link
import synapse.lib.const as s_const
import synapse.lib.nexus as s_nexus
import synapse.lib.share as s_share
import synapse.lib.config as s_config
import synapse.lib.hashset as s_hashset
import synapse.lib.httpapi as s_httpapi
import synapse.lib.urlhelp as s_urlhelp
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

        if not await self.allowed(('axon', 'upload')):
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
        if not await self.allowed(('axon', 'has')):
            return
        resp = await self.cell.has(s_common.uhex(sha256))
        return self.sendRestRetn(resp)

reqValidAxonDel = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'sha256s': {
            'type': 'array',
            'items': {'type': 'string', 'pattern': '(?i)^[0-9a-f]{64}$'}
        },
    },
    'additionalProperties': False,
    'required': ['sha256s'],
})

class AxonHttpDelV1(s_httpapi.Handler):

    async def post(self):

        if not await self.allowed(('axon', 'del')):
            return

        body = self.getJsonBody(validator=reqValidAxonDel)
        if body is None:
            return

        sha256s = body.get('sha256s')
        hashes = [s_common.uhex(s) for s in sha256s]
        resp = await self.cell.dels(hashes)
        return self.sendRestRetn(tuple(zip(sha256s, resp)))

class AxonFileHandler(s_httpapi.Handler):

    def axon(self):
        return self.cell

    async def getAxonInfo(self):
        return await self.axon().getCellInfo()

    async def _setSha256Headers(self, sha256b):

        self.ranges = []

        self.blobsize = await self.axon().size(sha256b)
        if self.blobsize is None:
            self.set_status(404)
            self.sendRestErr('NoSuchFile', f'SHA-256 not found: {s_common.ehex(sha256b)}')
            return False

        status = 200
        info = await self.getAxonInfo()
        if info.get('features', {}).get('byterange'):
            self.set_header('Accept-Ranges', 'bytes')
            self._chopRangeHeader()

        if len(self.ranges):
            status = 206
            soff, eoff = self.ranges[0]

            # Negative lengths are invalid
            cont_len = eoff - soff
            if cont_len < 1:
                self.set_status(416)
                return False

            # Reading past the blobsize is invalid
            if soff >= self.blobsize:
                self.set_status(416)
                return False

            if soff + cont_len > self.blobsize:
                self.set_status(416)
                return False

            # ranges are *inclusive*...
            self.set_header('Content-Range', f'bytes {soff}-{eoff-1}/{self.blobsize}')
            self.set_header('Content-Length', str(cont_len))
            # TODO eventually support multi-range returns
        else:
            self.set_header('Content-Length', str(self.blobsize))

        self.set_status(status)
        return True

    def _chopRangeHeader(self):

        header = self.request.headers.get('range', '').strip().lower()
        if not header.startswith('bytes='):
            return

        for part in header.split('=', 1)[1].split(','):

            part = part.strip()
            if not part:
                continue

            soff, eoff = part.split('-', 1)

            soff = int(soff.strip())
            eoff = eoff.strip()

            if not eoff:
                eoff = self.blobsize
            else:
                eoff = int(eoff) + 1

            self.ranges.append((soff, eoff))

    async def _sendSha256Byts(self, sha256b):

        # a single range is simple...
        if self.ranges:
            # TODO eventually support multi-range returns
            soff, eoff = self.ranges[0]
            size = eoff - soff
            async for byts in self.axon().get(sha256b, soff, size):
                self.write(byts)
                await self.flush()
                await asyncio.sleep(0)
            return

        # standard file return
        async for byts in self.axon().get(sha256b):
            self.write(byts)
            await self.flush()
            await asyncio.sleep(0)

class AxonHttpBySha256V1(AxonFileHandler):

    async def head(self, sha256):

        if not await self.allowed(('axon', 'get')):
            return

        sha256b = s_common.uhex(sha256)

        if not await self._setSha256Headers(sha256b):
            return

        self.set_header('Content-Disposition', 'attachment')
        self.set_header('Content-Type', 'application/octet-stream')

        return self.finish()

    async def get(self, sha256):

        if not await self.allowed(('axon', 'get')):
            return

        sha256b = s_common.uhex(sha256)
        if not await self._setSha256Headers(sha256b):
            return

        self.set_header('Content-Disposition', 'attachment')
        self.set_header('Content-Type', 'application/octet-stream')

        await self._sendSha256Byts(sha256b)

        return self.finish()

    async def delete(self, sha256):

        if not await self.allowed(('axon', 'del')):
            return

        sha256b = s_common.uhex(sha256)
        if not await self.cell.has(sha256b):
            self.set_status(404)
            self.sendRestErr('NoSuchFile', f'SHA-256 not found: {sha256}')
            return

        resp = await self.cell.del_(sha256b)
        return self.sendRestRetn(resp)

class AxonHttpBySha256InvalidV1(AxonFileHandler):

    async def _handle_err(self, sha256, send_err=True):
        if not await self.reqAuthUser():
            return

        self.set_status(404)
        if send_err:
            self.sendRestErr('BadArg', f'Hash is not a SHA-256: {sha256}')

    async def delete(self, sha256):
        return await self._handle_err(sha256)

    async def get(self, sha256):
        return await self._handle_err(sha256)

    async def head(self, sha256):
        return await self._handle_err(sha256, send_err=False)

class UpLoad(s_base.Base):
    '''
    An object used to manage uploads to the Axon.
    '''
    async def __anit__(self, axon):  # type: ignore

        await s_base.Base.__anit__(self)

        self.axon = axon
        dirn = s_common.gendir(axon.dirn, 'tmp')
        self.fd = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE, dir=dirn)
        self.size = 0
        self.sha256 = hashlib.sha256()
        self.onfini(self._uploadFini)

    def _uploadFini(self):
        self.fd.close()

    def _reset(self):
        if self.fd._rolled or self.fd.closed:
            self.fd.close()
            dirn = s_common.gendir(self.axon.dirn, 'tmp')
            self.fd = tempfile.SpooledTemporaryFile(max_size=MAX_SPOOL_SIZE, dir=dirn)
        else:
            # If we haven't rolled over, this skips allocating new objects
            self.fd.truncate(0)
            self.fd.seek(0)
        self.size = 0
        self.sha256 = hashlib.sha256()

    async def write(self, byts):
        '''
        Write bytes to the Upload object.

        Args:
            byts (bytes): Bytes to write to the current Upload object.

        Returns:
            (None): Returns None.
        '''
        self.size += len(byts)
        self.sha256.update(byts)
        self.fd.write(byts)

    async def save(self):
        '''
        Save the currently uploaded bytes to the Axon.

        Notes:
            This resets the Upload object, so it can be reused.

        Returns:
            tuple(int, bytes): A tuple of sizes in bytes and the sha256 hash of the saved files.
        '''

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

class UpLoadProxy(s_share.Share):

    async def __anit__(self, link, upload):
        await s_share.Share.__anit__(self, link, upload)
        self.onfini(upload)

    async def write(self, byts):
        return await self.item.write(byts)

    async def save(self):
        return await self.item.save()

class AxonApi(s_cell.CellApi, s_share.Share):  # type: ignore

    async def __anit__(self, cell, link, user):
        await s_cell.CellApi.__anit__(self, cell, link, user)
        await s_share.Share.__anit__(self, link, None)

    async def get(self, sha256, offs=None, size=None):
        '''
        Get bytes of a file.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.
            offs (int): The offset to start reading from.
            size (int): The total number of bytes to read.

        Examples:

            Get the bytes from an Axon and process them::

                buf = b''
                async for bytz in axon.get(sha256):
                    buf =+ bytz

                await dostuff(buf)

        Yields:
            bytes: Chunks of the file bytes.

        Raises:
            synapse.exc.NoSuchFile: If the file does not exist.
        '''
        await self._reqUserAllowed(('axon', 'get'))
        async for byts in self.cell.get(sha256, offs=offs, size=size):
            yield byts

    async def has(self, sha256):
        '''
        Check if the Axon has a file.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Returns:
            boolean: True if the Axon has the file; false otherwise.
        '''
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.has(sha256)

    async def size(self, sha256):
        '''
        Get the size of a file in the Axon.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Returns:
            int: The size of the file, in bytes. If not present, None is returned.
        '''
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.size(sha256)

    async def hashset(self, sha256):
        '''
        Calculate additional hashes for a file in the Axon.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Returns:
            dict: A dictionary containing hashes of the file.
        '''
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.hashset(sha256)

    async def hashes(self, offs, wait=False, timeout=None):
        '''
        Yield hash rows for files that exist in the Axon in added order starting at an offset.

        Args:
            offs (int): The index offset.
            wait (boolean): Wait for new results and yield them in realtime.
            timeout (int): Max time to wait for new results.

        Yields:
            (int, (bytes, int)): An index offset and the file SHA-256 and size.
        '''
        await self._reqUserAllowed(('axon', 'has'))
        async for item in self.cell.hashes(offs, wait=wait, timeout=timeout):
            yield item

    async def history(self, tick, tock=None):
        '''
        Yield hash rows for files that existing in the Axon after a given point in time.

        Args:
            tick (int): The starting time (in epoch milliseconds).
            tock (int): The ending time to stop iterating at (in epoch milliseconds).

        Yields:
            (int, (bytes, int)): A tuple containing time of the hash was added and the file SHA-256 and size.
        '''
        await self._reqUserAllowed(('axon', 'has'))
        async for item in self.cell.history(tick, tock=tock):
            yield item

    async def wants(self, sha256s):
        '''
        Get a list of sha256 values the axon does not have from a input list.

        Args:
            sha256s (list): A list of sha256 values as bytes.

        Returns:
            list: A list of bytes containing the sha256 hashes the Axon does not have.
        '''
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.wants(sha256s)

    async def put(self, byts):
        '''
        Store bytes in the Axon.

        Args:
            byts (bytes): The bytes to store in the Axon.

        Notes:
            This API should not be used for files greater than 128 MiB in size.

        Returns:
            tuple(int, bytes): A tuple with the file size and sha256 hash of the bytes.
        '''
        await self._reqUserAllowed(('axon', 'upload'))
        return await self.cell.put(byts)

    async def puts(self, files):
        '''
        Store a set of bytes in the Axon.

        Args:
            files (list): A list of bytes to store in the Axon.

        Notes:
            This API should not be used for storing more than 128 MiB of bytes at once.

        Returns:
            list(tuple(int, bytes)): A list containing tuples of file size and sha256 hash of the saved bytes.
        '''
        await self._reqUserAllowed(('axon', 'upload'))
        return await self.cell.puts(files)

    async def upload(self):
        '''
        Get an Upload object.

        Notes:
            The UpLoad object should be used to manage uploads greater than 128 MiB in size.

        Examples:
            Use an UpLoad object to upload a file to the Axon::

                async with axonProxy.upload() as upfd:
                    # Assumes bytesGenerator yields bytes
                    async for byts in bytsgenerator():
                        upfd.write(byts)
                    upfd.save()

            Use a single UpLoad object to save multiple files::

                async with axonProxy.upload() as upfd:
                    for fp in file_paths:
                        # Assumes bytesGenerator yields bytes
                        async for byts in bytsgenerator(fp):
                            upfd.write(byts)
                        upfd.save()

        Returns:
            UpLoadShare: An Upload manager object.
        '''
        await self._reqUserAllowed(('axon', 'upload'))
        return await UpLoadShare.anit(self.cell, self.link)

    async def del_(self, sha256):
        '''
        Remove the given bytes from the Axon by sha256.

        Args:
            sha256 (bytes): The sha256, in bytes, to remove from the Axon.

        Returns:
            boolean: True if the file is removed; false if the file is not present.
        '''
        await self._reqUserAllowed(('axon', 'del'))
        return await self.cell.del_(sha256)

    async def dels(self, sha256s):
        '''
        Given a list of sha256 hashes, delete the files from the Axon.

        Args:
            sha256s (list): A list of sha256 hashes in bytes form.

        Returns:
            list: A list of booleans, indicating if the file was deleted or not.
        '''
        await self._reqUserAllowed(('axon', 'del'))
        return await self.cell.dels(sha256s)

    async def wget(self, url, params=None, headers=None, json=None, body=None, method='GET', ssl=True, timeout=None, proxy=None):
        '''
        Stream a file download directly into the Axon.

        Args:
            url (str): The URL to retrieve.
            params (dict): Additional parameters to add to the URL.
            headers (dict): Additional HTTP headers to add in the request.
            json: A JSON body which is included with the request.
            body: The body to be included in the request.
            method (str): The HTTP method to use.
            ssl (bool): Perform SSL verification.
            timeout (int): The timeout of the request, in seconds.

        Notes:
            The response body will be stored, regardless of the response code. The ``ok`` value in the reponse does not
            reflect that a status code, such as a 404, was encountered when retrieving the URL.

            The dictionary returned by this may contain the following values::

                {
                    'ok': <boolean> - False if there were exceptions retrieving the URL.
                    'url': <str> - The URL retrieved (which could have been redirected)
                    'code': <int> - The response code.
                    'mesg': <str> - An error message if there was an exception when retrieving the URL.
                    'headers': <dict> - The response headers as a dictionary.
                    'size': <int> - The size in bytes of the response body.
                    'hashes': {
                        'md5': <str> - The MD5 hash of the response body.
                        'sha1': <str> - The SHA1 hash of the response body.
                        'sha256': <str> - The SHA256 hash of the response body.
                        'sha512': <str> - The SHA512 hash of the response body.
                    }
                }

        Returns:
            dict: An information dictionary containing the results of the request.
        '''
        await self._reqUserAllowed(('axon', 'wget'))
        return await self.cell.wget(url, params=params, headers=headers, json=json, body=body, method=method, ssl=ssl,
                                    timeout=timeout, proxy=proxy)

    async def postfiles(self, fields, url, params=None, headers=None, method='POST', ssl=True, timeout=None, proxy=None):
        await self._reqUserAllowed(('axon', 'wput'))
        return await self.cell.postfiles(fields, url, params=params, headers=headers,
                                         method=method, ssl=ssl, timeout=timeout, proxy=proxy)

    async def wput(self, sha256, url, params=None, headers=None, method='PUT', ssl=True, timeout=None, proxy=None):
        await self._reqUserAllowed(('axon', 'wput'))
        return await self.cell.wput(sha256, url, params=params, headers=headers, method=method, ssl=ssl,
                                    timeout=timeout, proxy=proxy)

    async def metrics(self):
        '''
        Get the runtime metrics of the Axon.

        Returns:
            dict: A dictionary of runtime data about the Axon.
        '''
        await self._reqUserAllowed(('axon', 'has'))
        return await self.cell.metrics()

    async def iterMpkFile(self, sha256):
        '''
        Yield items from a MsgPack (.mpk) file in the Axon.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Yields:
            Unpacked items from the bytes.
        '''
        await self._reqUserAllowed(('axon', 'get'))
        async for item in self.cell.iterMpkFile(sha256):
            yield item

    async def readlines(self, sha256):
        '''
        Yield lines from a multi-line text file in the axon.

        Args:
            sha256 (bytes): The sha256 hash of the file.

        Yields:
            str: Lines of text
        '''
        await self._reqUserAllowed(('axon', 'get'))
        async for item in self.cell.readlines(sha256):
            yield item

    async def csvrows(self, sha256, dialect='excel', **fmtparams):
        '''
        Yield CSV rows from a CSV file.

        Args:
            sha256 (bytes): The sha256 hash of the file.
            dialect (str): The CSV dialect to use.
            **fmtparams: The CSV dialect format parameters.

        Notes:
            The dialect and fmtparams expose the Python csv.reader() parameters.

        Examples:

            Get the rows from a CSV file and process them::

                async for row in axon.csvrows(sha256):
                    await dostuff(row)

            Get the rows from a tab separated file and process them::

                async for row in axon.csvrows(sha256, delimiter='\t'):
                    await dostuff(row)

        Yields:
            list: Decoded CSV rows.
        '''
        await self._reqUserAllowed(('axon', 'get'))
        async for item in self.cell.csvrows(sha256, dialect, **fmtparams):
            yield item

    async def jsonlines(self, sha256):
        '''
        Yield JSON objects from JSONL (JSON lines) file.

        Args:
            sha256 (bytes): The sha256 hash of the file.

        Yields:
            object: Decoded JSON objects.
        '''
        await self._reqUserAllowed(('axon', 'get'))
        async for item in self.cell.jsonlines(sha256):
            yield item


class Axon(s_cell.Cell):

    cellapi = AxonApi
    byterange = False

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
        'tls:ca:dir': {
            'description': 'An optional directory of CAs which are added to the TLS CA chain for wget and wput APIs.',
            'type': 'string',
        },
    }

    async def initServiceStorage(self):  # type: ignore

        path = s_common.gendir(self.dirn, 'axon.lmdb')
        self.axonslab = await s_lmdbslab.Slab.anit(path)
        self.sizes = self.axonslab.initdb('sizes')
        self.onfini(self.axonslab.fini)

        self.hashlocks = {}

        self.axonhist = s_lmdbslab.Hist(self.axonslab, 'history')
        self.axonseqn = s_slabseqn.SlabSeqn(self.axonslab, 'axonseqn')

        node = await self.hive.open(('axon', 'metrics'))
        self.axonmetrics = await node.dict()
        self.axonmetrics.setdefault('size:bytes', 0)
        self.axonmetrics.setdefault('file:count', 0)

        self.maxbytes = self.conf.get('max:bytes')
        self.maxcount = self.conf.get('max:count')

        # modularize blob storage
        await self._initBlobStor()

    async def initServiceRuntime(self):

        # share ourself via the cell dmon as "axon"
        # for potential default remote use
        self.dmon.share('axon', self)

        self._initAxonHttpApi()
        self.addHealthFunc(self._axonHealth)

    async def getCellInfo(self):
        info = await s_cell.Cell.getCellInfo(self)
        info['features']['byterange'] = self.byterange
        return info

    @contextlib.asynccontextmanager
    async def holdHashLock(self, hashbyts):
        '''
        A context manager that synchronizes edit access to a blob.

        Args:
            hashbyts (bytes): The blob to hold the lock for.
        '''

        item = self.hashlocks.get(hashbyts)
        if item is None:
            self.hashlocks[hashbyts] = item = [0, asyncio.Lock()]

        item[0] += 1
        async with item[1]:
            yield

        item[0] -= 1

        if item[0] == 0:
            self.hashlocks.pop(hashbyts, None)

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

        self.byterange = True

        path = s_common.gendir(self.dirn, 'blob.lmdb')

        self.blobslab = await s_lmdbslab.Slab.anit(path)
        self.blobs = self.blobslab.initdb('blobs')
        self.offsets = self.blobslab.initdb('offsets')
        self.metadata = self.blobslab.initdb('metadata')
        self.onfini(self.blobslab.fini)

        if self.inaugural:
            self._setStorVers(1)

        storvers = self._getStorVers()
        if storvers < 1:
            storvers = await self._setStorVers01()

    async def _setStorVers01(self):

        logger.warning('Updating Axon storage version (adding offset index). This may take a while.')

        offs = 0
        cursha = b''

        # TODO: need LMDB to support getting value size without getting value
        for lkey, byts in self.blobslab.scanByFull(db=self.blobs):

            await asyncio.sleep(0)

            blobsha = lkey[:32]

            if blobsha != cursha:
                offs = 0
                cursha = blobsha

            offs += len(byts)

            self.blobslab.put(cursha + offs.to_bytes(8, 'big'), lkey[32:], db=self.offsets)

        return self._setStorVers(1)

    def _getStorVers(self):
        byts = self.blobslab.get(b'version', db=self.metadata)
        if not byts:
            return 0
        return int.from_bytes(byts, 'big')

    def _setStorVers(self, version):
        self.blobslab.put(b'version', version.to_bytes(8, 'big'), db=self.metadata)
        return version

    def _initAxonHttpApi(self):
        self.addHttpApi('/api/v1/axon/files/del', AxonHttpDelV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/put', AxonHttpUploadV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/has/sha256/([0-9a-fA-F]{64}$)', AxonHttpHasV1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/by/sha256/([0-9a-fA-F]{64}$)', AxonHttpBySha256V1, {'cell': self})
        self.addHttpApi('/api/v1/axon/files/by/sha256/(.*)', AxonHttpBySha256InvalidV1, {'cell': self})

    def _addSyncItem(self, item, tick=None):
        self.axonhist.add(item, tick=tick)
        self.axonseqn.add(item)

    async def _reqHas(self, sha256):
        '''
        Ensure a file exists; and return its size if so.

        Args:
            sha256 (bytes): The sha256 to check.

        Returns:
            int: Size of the file in bytes.

        Raises:
            NoSuchFile: If the file does not exist.
        '''
        fsize = await self.size(sha256)
        if fsize is None:
            raise s_exc.NoSuchFile(mesg='Axon does not contain the requested file.', sha256=s_common.ehex(sha256))
        return fsize

    async def history(self, tick, tock=None):
        '''
        Yield hash rows for files that existing in the Axon after a given point in time.

        Args:
            tick (int): The starting time (in epoch milliseconds).
            tock (int): The ending time to stop iterating at (in epoch milliseconds).

        Yields:
            (int, (bytes, int)): A tuple containing time of the hash was added and the file SHA-256 and size.
        '''
        for item in self.axonhist.carve(tick, tock=tock):
            yield item

    async def hashes(self, offs, wait=False, timeout=None):
        '''
        Yield hash rows for files that exist in the Axon in added order starting at an offset.

        Args:
            offs (int): The index offset.
            wait (boolean): Wait for new results and yield them in realtime.
            timeout (int): Max time to wait for new results.

        Yields:
            (int, (bytes, int)): An index offset and the file SHA-256 and size.

        Note:
            If the same hash was deleted and then added back, the same hash will be yielded twice.
        '''
        async for item in self.axonseqn.aiter(offs, wait=wait, timeout=timeout):
            if self.axonslab.has(item[1][0], db=self.sizes):
                yield item
            await asyncio.sleep(0)

    async def get(self, sha256, offs=None, size=None):
        '''
        Get bytes of a file.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.
            offs (int): The offset to start reading from.
            size (int): The total number of bytes to read.

        Examples:

            Get the bytes from an Axon and process them::

                buf = b''
                async for bytz in axon.get(sha256):
                    buf =+ bytz

                await dostuff(buf)

        Yields:
            bytes: Chunks of the file bytes.

        Raises:
            synapse.exc.NoSuchFile: If the file does not exist.
        '''
        fsize = await self._reqHas(sha256)

        fhash = s_common.ehex(sha256)
        logger.debug(f'Getting blob [{fhash}].', extra=await self.getLogExtra(sha256=fhash))

        if offs is not None or size is not None:

            if not self.byterange:  # pragma: no cover
                mesg = 'This axon does not support byte ranges.'
                raise s_exc.FeatureNotSupported(mesg=mesg)

            if offs < 0:
                raise s_exc.BadArg(mesg='Offs must be >= 0', offs=offs)
            if size < 1:
                raise s_exc.BadArg(mesg='Size must be >= 1', size=size)

            if offs >= fsize:
                # If we try to read past the file, yield empty bytes and return.
                yield b''
                return

            async for byts in self._getBytsOffsSize(sha256, offs, size):
                yield byts

        else:
            async for byts in self._get(sha256):
                yield byts

    async def _get(self, sha256):

        for _, byts in self.blobslab.scanByPref(sha256, db=self.blobs):
            yield byts

    async def put(self, byts):
        '''
        Store bytes in the Axon.

        Args:
            byts (bytes): The bytes to store in the Axon.

        Notes:
            This API should not be used for files greater than 128 MiB in size.

        Returns:
            tuple(int, bytes): A tuple with the file size and sha256 hash of the bytes.
        '''
        # Use a UpLoad context manager so that we can
        # ensure that a one-shot set of bytes is chunked
        # in a consistent fashion.
        async with await self.upload() as fd:
            await fd.write(byts)
            return await fd.save()

    async def puts(self, files):
        '''
        Store a set of bytes in the Axon.

        Args:
            files (list): A list of bytes to store in the Axon.

        Notes:
            This API should not be used for storing more than 128 MiB of bytes at once.

        Returns:
            list(tuple(int, bytes)): A list containing tuples of file size and sha256 hash of the saved bytes.
        '''
        return [await self.put(b) for b in files]

    async def upload(self):
        '''
        Get an Upload object.

        Notes:
            The UpLoad object should be used to manage uploads greater than 128 MiB in size.

        Examples:
            Use an UpLoad object to upload a file to the Axon::

                async with await axon.upload() as upfd:
                    # Assumes bytesGenerator yields bytes
                    async for byts in bytsgenerator():
                        await upfd.write(byts)
                    await upfd.save()

            Use a single UpLoad object to save multiple files::

                async with await axon.upload() as upfd:
                    for fp in file_paths:
                        # Assumes bytesGenerator yields bytes
                        async for byts in bytsgenerator(fp):
                            await upfd.write(byts)
                        await upfd.save()

        Returns:
            UpLoad: An Upload manager object.
        '''
        return await UpLoad.anit(self)

    async def has(self, sha256):
        '''
        Check if the Axon has a file.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Returns:
            boolean: True if the Axon has the file; false otherwise.
        '''
        return self.axonslab.get(sha256, db=self.sizes) is not None

    async def size(self, sha256):
        '''
        Get the size of a file in the Axon.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Returns:
            int: The size of the file, in bytes. If not present, None is returned.
        '''
        byts = self.axonslab.get(sha256, db=self.sizes)
        if byts is not None:
            return int.from_bytes(byts, 'big')

    async def hashset(self, sha256):
        '''
        Calculate additional hashes for a file in the Axon.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.

        Returns:
            dict: A dictionary containing hashes of the file.
        '''
        await self._reqHas(sha256)

        fhash = s_common.ehex(sha256)
        logger.debug(f'Getting blob [{fhash}].', extra=await self.getLogExtra(sha256=fhash))

        hashset = s_hashset.HashSet()

        async for byts in self._get(sha256):
            hashset.update(byts)
            await asyncio.sleep(0)

        return dict([(n, s_common.ehex(h)) for (n, h) in hashset.digests()])

    async def metrics(self):
        '''
        Get the runtime metrics of the Axon.

        Returns:
            dict: A dictionary of runtime data about the Axon.
        '''
        return dict(self.axonmetrics.items())

    async def save(self, sha256, genr):
        '''
        Save a generator of bytes to the Axon.

        Args:
            sha256 (bytes): The sha256 hash of the file in bytes.
            genr: The bytes generator function.

        Returns:
            int: The size of the bytes saved.
        '''
        assert genr is not None
        return await self._populate(sha256, genr)

    async def _populate(self, sha256, genr, size=None):
        '''
        Populates the metadata and save the data itself if genr is not None
        '''
        assert genr is not None or size is not None

        self._reqBelowLimit()

        async with self.holdHashLock(sha256):

            byts = self.axonslab.get(sha256, db=self.sizes)
            if byts is not None:
                return int.from_bytes(byts, 'big')

            fhash = s_common.ehex(sha256)
            logger.debug(f'Saving blob [{fhash}].', extra=await self.getLogExtra(sha256=fhash))

            if genr is not None:
                size = await self._saveFileGenr(sha256, genr)

            await self._axonFileAdd(sha256, size, {'tick': s_common.now()})

            return size

    @s_nexus.Pusher.onPushAuto('axon:file:add')
    async def _axonFileAdd(self, sha256, size, info):

        byts = self.axonslab.get(sha256, db=self.sizes)
        if byts is not None:
            return False

        tick = info.get('tick')
        self._addSyncItem((sha256, size), tick=tick)

        await self.axonmetrics.set('file:count', self.axonmetrics.get('file:count') + 1)
        await self.axonmetrics.set('size:bytes', self.axonmetrics.get('size:bytes') + size)

        self.axonslab.put(sha256, size.to_bytes(8, 'big'), db=self.sizes)
        return True

    async def _saveFileGenr(self, sha256, genr):

        size = 0

        for i, byts in enumerate(genr):

            size += len(byts)
            await self._axonBytsSave(sha256, i, size, byts)

            await asyncio.sleep(0)

        return size

    # a nexusified way to save local bytes
    @s_nexus.Pusher.onPushAuto('axon:bytes:add')
    async def _axonBytsSave(self, sha256, indx, offs, byts):
        ikey = indx.to_bytes(8, 'big')
        okey = offs.to_bytes(8, 'big')

        self.blobslab.put(sha256 + ikey, byts, db=self.blobs)
        self.blobslab.put(sha256 + okey, ikey, db=self.offsets)

    def _offsToIndx(self, sha256, offs):
        lkey = sha256 + offs.to_bytes(8, 'big')
        for offskey, indxbyts in self.blobslab.scanByRange(lkey, db=self.offsets):
            return int.from_bytes(offskey[32:], 'big'), indxbyts

    async def _getBytsOffs(self, sha256, offs):

        first = True

        boff, indxbyts = self._offsToIndx(sha256, offs)

        for bkey, byts in self.blobslab.scanByRange(sha256 + indxbyts, db=self.blobs):

            await asyncio.sleep(0)

            if bkey[:32] != sha256:
                return

            if first:
                first = False
                delt = boff - offs
                yield byts[-delt:]
                continue

            yield byts

    async def _getBytsOffsSize(self, sha256, offs, size):
        '''
        Implementation dependent method to stream size # of bytes from the Axon,
        starting a given offset.
        '''
        # This implementation assumes that the offs provided is < the maximum
        # size of the sha256 value being asked for.
        remain = size
        async for byts in self._getBytsOffs(sha256, offs):

            blen = len(byts)
            if blen >= remain:
                yield byts[:remain]
                return

            remain -= blen

            yield byts

    async def dels(self, sha256s):
        '''
        Given a list of sha256 hashes, delete the files from the Axon.

        Args:
            sha256s (list): A list of sha256 hashes in bytes form.

        Returns:
            list: A list of booleans, indicating if the file was deleted or not.
        '''
        return [await self.del_(s) for s in sha256s]

    async def del_(self, sha256):
        '''
        Remove the given bytes from the Axon by sha256.

        Args:
            sha256 (bytes): The sha256, in bytes, to remove from the Axon.

        Returns:
            boolean: True if the file is removed; false if the file is not present.
        '''
        if not await self.has(sha256):
            return False

        return await self._axonFileDel(sha256)

    @s_nexus.Pusher.onPushAuto('axon:file:del')
    async def _axonFileDel(self, sha256):
        async with self.holdHashLock(sha256):

            byts = self.axonslab.pop(sha256, db=self.sizes)
            if not byts:
                return False

            fhash = s_common.ehex(sha256)
            logger.debug(f'Deleting blob [{fhash}].', extra=await self.getLogExtra(sha256=fhash))

            size = int.from_bytes(byts, 'big')
            await self.axonmetrics.set('file:count', self.axonmetrics.get('file:count') - 1)
            await self.axonmetrics.set('size:bytes', self.axonmetrics.get('size:bytes') - size)

            await self._delBlobByts(sha256)
            return True

    async def _delBlobByts(self, sha256):

        # remove the offset indexes...
        for lkey in self.blobslab.scanKeysByPref(sha256, db=self.blobs):
            self.blobslab.delete(lkey, db=self.offsets)
            await asyncio.sleep(0)

        # remove the actual blobs...
        for lkey in self.blobslab.scanKeysByPref(sha256, db=self.blobs):
            self.blobslab.delete(lkey, db=self.blobs)
            await asyncio.sleep(0)

    async def wants(self, sha256s):
        '''
        Get a list of sha256 values the axon does not have from a input list.

        Args:
            sha256s (list): A list of sha256 values as bytes.

        Returns:
            list: A list of bytes containing the sha256 hashes the Axon does not have.
        '''
        return [s for s in sha256s if not await self.has(s)]

    async def iterMpkFile(self, sha256):
        '''
        Yield items from a MsgPack (.mpk) file in the Axon.

        Args:
            sha256 (str): The sha256 hash of the file as a string.

        Yields:
            Unpacked items from the bytes.
        '''
        unpk = s_msgpack.Unpk()
        async for byts in self.get(s_common.uhex(sha256)):
            for _, item in unpk.feed(byts):
                yield item

    async def _sha256ToLink(self, sha256, link):
        try:
            async for byts in self.get(sha256):
                await link.send(byts)
                await asyncio.sleep(0)
        finally:
            link.txfini()

    async def readlines(self, sha256):

        sha256 = s_common.uhex(sha256)
        await self._reqHas(sha256)

        link00, sock00 = await s_link.linksock(forceclose=True)

        try:
            todo = s_common.todo(_spawn_readlines, sock00)
            async with await s_base.Base.anit() as scope:

                scope.schedCoro(s_coro.spawn(todo, log_conf=await self._getSpawnLogConf()))
                scope.schedCoro(self._sha256ToLink(sha256, link00))

                while not self.isfini:

                    mesg = await link00.rx()
                    if mesg is None:
                        return

                    line = s_common.result(mesg)
                    if line is None:
                        return

                    yield line.rstrip('\n')

        finally:
            sock00.close()
            await link00.fini()

    async def csvrows(self, sha256, dialect='excel', **fmtparams):
        await self._reqHas(sha256)
        if dialect not in csv.list_dialects():
            raise s_exc.BadArg(mesg=f'Invalid CSV dialect, use one of {csv.list_dialects()}')

        link00, sock00 = await s_link.linksock(forceclose=True)

        try:
            todo = s_common.todo(_spawn_readrows, sock00, dialect, fmtparams)
            async with await s_base.Base.anit() as scope:

                scope.schedCoro(s_coro.spawn(todo, log_conf=await self._getSpawnLogConf()))
                scope.schedCoro(self._sha256ToLink(sha256, link00))

                while not self.isfini:

                    mesg = await link00.rx()
                    if mesg is None:
                        return

                    row = s_common.result(mesg)
                    if row is None:
                        return

                    yield row

        finally:
            sock00.close()
            await link00.fini()

    async def jsonlines(self, sha256):
        async for line in self.readlines(sha256):
            line = line.strip()
            if not line:
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                logger.exception(f'Bad json line encountered for {sha256}')
                raise s_exc.BadJsonText(mesg=f'Bad json line encountered while processing {sha256}, ({e})',
                                        sha256=sha256) from None

    async def postfiles(self, fields, url, params=None, headers=None, method='POST', ssl=True, timeout=None, proxy=None):
        '''
        Send files from the axon as fields in a multipart/form-data HTTP request.

        Args:
            fields (list): List of dicts containing the fields to add to the request as form-data.
            url (str): The URL to retrieve.
            params (dict): Additional parameters to add to the URL.
            headers (dict): Additional HTTP headers to add in the request.
            method (str): The HTTP method to use.
            ssl (bool): Perform SSL verification.
            timeout (int): The timeout of the request, in seconds.
            proxy (bool|str|null): Use a specific proxy or disable proxy use.

        Notes:
            The dictionaries in the fields list may contain the following values::

                {
                    'name': <str> - Name of the field.
                    'sha256': <str> - SHA256 hash of the file to submit for this field.
                    'value': <str> - Value for the field. Ignored if a sha256 has been specified.
                    'filename': <str> - Optional filename for the field.
                    'content_type': <str> - Optional content type for the field.
                    'content_transfer_encoding': <str> - Optional content-transfer-encoding header for the field.
                }

            The dictionary returned by this may contain the following values::

                {
                    'ok': <boolean> - False if there were exceptions retrieving the URL.
                    'err': <str> - An error message if there was an exception when retrieving the URL.
                    'url': <str> - The URL retrieved (which could have been redirected)
                    'code': <int> - The response code.
                    'body': <bytes> - The response body.
                    'headers': <dict> - The response headers as a dictionary.
                }

        Returns:
            dict: An information dictionary containing the results of the request.
        '''
        if proxy is None:
            proxy = self.conf.get('http:proxy')

        cadir = self.conf.get('tls:ca:dir')

        connector = None
        if proxy:
            connector = aiohttp_socks.ProxyConnector.from_url(proxy)

        if ssl is False:
            pass
        elif cadir:
            ssl = s_common.getSslCtx(cadir)
        else:
            # default aiohttp behavior
            ssl = None

        atimeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=atimeout) as sess:

            try:
                data = aiohttp.FormData()
                data._is_multipart = True

                for field in fields:
                    sha256 = field.get('sha256')
                    if sha256:
                        valu = self.get(s_common.uhex(sha256))
                    else:
                        valu = field.get('value')
                        if not isinstance(valu, (bytes, str)):
                            valu = json.dumps(valu)

                    data.add_field(field.get('name'),
                                   valu,
                                   content_type=field.get('content_type'),
                                   filename=field.get('filename'),
                                   content_transfer_encoding=field.get('content_transfer_encoding'))

                async with sess.request(method, url, headers=headers, params=params,
                                        data=data, ssl=ssl) as resp:
                    info = {
                        'ok': True,
                        'url': str(resp.url),
                        'code': resp.status,
                        'body': await resp.read(),
                        'headers': dict(resp.headers),
                    }
                    return info

            except asyncio.CancelledError:  # pramga: no cover
                raise

            except Exception as e:
                logger.exception(f'Error POSTing files to [{s_urlhelp.sanitizeUrl(url)}]')
                exc = s_common.excinfo(e)
                mesg = exc.get('errmsg')
                if not mesg:
                    mesg = exc.get('err')

                return {
                    'ok': False,
                    'err': mesg,
                    'url': url,
                    'body': b'',
                    'code': -1,
                    'headers': dict(),
                }

    async def wput(self, sha256, url, params=None, headers=None, method='PUT', ssl=True, timeout=None,
                   filename=None, filemime=None, proxy=None):
        '''
        Stream a blob from the axon as the body of an HTTP request.
        '''
        if proxy is None:
            prox = self.conf.get('http:proxy')

        cadir = self.conf.get('tls:ca:dir')

        connector = None
        if proxy:
            connector = aiohttp_socks.ProxyConnector.from_url(proxy)

        if ssl is False:
            pass
        elif cadir:
            ssl = s_common.getSslCtx(cadir)
        else:
            # default aiohttp behavior
            ssl = None

        atimeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=atimeout) as sess:

            try:

                async with sess.request(method, url, headers=headers, params=params,
                                        data=self.get(sha256), ssl=ssl) as resp:

                    info = {
                        'ok': True,
                        'url': str(resp.url),
                        'code': resp.status,
                        'headers': dict(resp.headers),
                    }
                    return info

            except asyncio.CancelledError:  # pramga: no cover
                raise

            except Exception as e:
                logger.exception(f'Error streaming [{sha256}] to [{s_urlhelp.sanitizeUrl(url)}]')
                exc = s_common.excinfo(e)
                mesg = exc.get('errmsg')
                if not mesg:
                    mesg = exc.get('err')

                return {
                    'ok': False,
                    'mesg': mesg,
                }

    async def wget(self, url, params=None, headers=None, json=None, body=None, method='GET', ssl=True, timeout=None, proxy=None):
        '''
        Stream a file download directly into the Axon.

        Args:
            url (str): The URL to retrieve.
            params (dict): Additional parameters to add to the URL.
            headers (dict): Additional HTTP headers to add in the request.
            json: A JSON body which is included with the request.
            body: The body to be included in the request.
            method (str): The HTTP method to use.
            ssl (bool): Perform SSL verification.
            timeout (int): The timeout of the request, in seconds.
            proxy (bool|str|null): Use a specific proxy or disable proxy use.

        Notes:
            The response body will be stored, regardless of the response code. The ``ok`` value in the reponse does not
            reflect that a status code, such as a 404, was encountered when retrieving the URL.

            The dictionary returned by this may contain the following values::

                {
                    'ok': <boolean> - False if there were exceptions retrieving the URL.
                    'url': <str> - The URL retrieved (which could have been redirected)
                    'code': <int> - The response code.
                    'mesg': <str> - An error message if there was an exception when retrieving the URL.
                    'headers': <dict> - The response headers as a dictionary.
                    'size': <int> - The size in bytes of the response body.
                    'hashes': {
                        'md5': <str> - The MD5 hash of the response body.
                        'sha1': <str> - The SHA1 hash of the response body.
                        'sha256': <str> - The SHA256 hash of the response body.
                        'sha512': <str> - The SHA512 hash of the response body.
                    }
                }

        Returns:
            dict: An information dictionary containing the results of the request.
        '''
        logger.debug(f'Wget called for [{url}].', extra=await self.getLogExtra(url=s_urlhelp.sanitizeUrl(url)))

        if proxy is None:
            proxy = self.conf.get('http:proxy')

        cadir = self.conf.get('tls:ca:dir')

        connector = None
        if proxy:
            connector = aiohttp_socks.ProxyConnector.from_url(proxy)

        atimeout = aiohttp.ClientTimeout(total=timeout)

        if ssl is False:
            pass
        elif cadir:
            ssl = s_common.getSslCtx(cadir)
        else:
            # default aiohttp behavior
            ssl = None

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
                logger.exception(f'Failed to wget {s_urlhelp.sanitizeUrl(url)}')
                exc = s_common.excinfo(e)
                mesg = exc.get('errmsg')
                if not mesg:
                    mesg = exc.get('err')

                return {
                    'ok': False,
                    'mesg': mesg,
                }

def _spawn_readlines(sock): # pragma: no cover
    try:
        with sock.makefile('r') as fd:

            try:

                for line in fd:
                    sock.sendall(s_msgpack.en((True, line)))

                sock.sendall(s_msgpack.en((True, None)))

            except UnicodeDecodeError as e:
                raise s_exc.BadDataValu(mesg=str(e))

    except Exception as e:
        mesg = s_common.retnexc(e)
        sock.sendall(s_msgpack.en(mesg))

def _spawn_readrows(sock, dialect, fmtparams): # pragma: no cover
    try:

        # Assume utf8 encoding and ignore errors.
        with sock.makefile('r', errors='ignore') as fd:

            try:

                for row in csv.reader(fd, dialect, **fmtparams):
                    sock.sendall(s_msgpack.en((True, row)))

                sock.sendall(s_msgpack.en((True, None)))

            except TypeError as e:
                raise s_exc.BadArg(mesg=f'Invalid csv format parameter: {str(e)}')

            except UnicodeDecodeError as e:
                raise s_exc.BadDataValu(mesg=str(e))

            except csv.Error as e:
                mesg = f'CSV error: {str(e)}'
                raise s_exc.BadDataValu(mesg=mesg)

    except Exception as e:
        mesg = s_common.retnexc(e)
        sock.sendall(s_msgpack.en(mesg))
