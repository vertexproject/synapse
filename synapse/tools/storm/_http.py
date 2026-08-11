import os
import ssl
import asyncio
import logging

import aiohttp
import aiohttp_socks

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.json as s_json
import synapse.lib.const as s_const
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack
import synapse.lib.urlhelp as s_urlhelp
import synapse.lib.crypto.passwd as s_passwd

logger = logging.getLogger(__name__)

CHUNK_SIZE = s_const.mebibyte

# The keepalive period ( in seconds ) used for streaming Storm queries. This causes the
# Cortex to emit periodic ping messages which keep an HTTP proxy or load balancer from
# terminating the connection while a long running query produces no output.
KEEPALIVE = 6

# The total request timeout ( in seconds ) used for Storm exports. The export API does
# not emit keepalive messages and performs a complete lift before yielding the first
# node, so the request is bounded rather than allowed to hang forever.
EXPORT_TIMEOUT = 3600

# The number of chunks buffered while streaming bytes into an Axon HTTP upload.
UPLOAD_QSIZE = 4

apikeymesg = 'A user API key is required to connect to a Cortex over HTTP. ' \
             'Provide it in the URL as https://<apikey>@host:port/.'

def isHttpsUrl(url):
    '''
    Check if a URL should be handled by the Cortex HTTP API client.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL uses the https scheme.
    '''
    return url.lower().startswith('https://')

async def openurl(url, cadir=None, proxy=None, verify=True):
    '''
    Open a Cortex HTTP API client which duck types the Telepath CoreApi.

    Args:
        url (str): The https:// URL of the Cortex, including the user API key.
        cadir (str): A directory of CAs to add to the TLS CA chain.
        proxy (str): An aiohttp-socks compatible proxy URL.
        verify (bool): Verify the TLS certificate of the Cortex.

    Returns:
        HttpCortex: The Cortex HTTP API client.
    '''
    return await HttpCortex.anit(url, cadir=cadir, proxy=proxy, verify=verify)

def getBaseUrl(info):
    '''
    Build the Cortex HTTP API base URL from a s_urlhelp.chopurl() info dict.

    Args:
        info (dict): The parsed URL info.

    Returns:
        str: The base URL with no userinfo and no trailing slash.
    '''
    host = info.get('host')
    if ':' in host:
        host = f'[{host}]'

    port = info.get('port')
    if port is None:
        port = 443

    return f'https://{host}:{port}{info.get("path", "").rstrip("/")}'

async def iterJsonLines(genr):
    '''
    Yield JSON messages from an async generator of newline delimited byte chunks.

    Args:
        genr: An async generator which yields bytes.

    Yields:
        The deserialized JSON messages.
    '''
    buf = b''

    async for byts in genr:

        buf += byts

        while (indx := buf.find(b'\n')) != -1:
            yield s_json.loads(buf[:indx])
            buf = buf[indx + 1:]

class HttpUpload(s_base.Base):
    '''
    An Axon UpLoad workalike which streams bytes to the Cortex HTTP API.
    '''

    async def __anit__(self, core):

        await s_base.Base.__anit__(self)

        self.core = core

        self.task = None
        self.queue = None

    async def _genrBytes(self):

        while True:

            byts = await self.queue.get()
            if byts is None:
                return

            yield byts

    async def _runUpload(self):

        url = self.core._getUrl('/api/v3/axon/files/put')

        async with self.core.sess.put(url, data=self._genrBytes(), **self.core.reqinfo) as resp:
            return await self.core._getRestRetn(resp)

    def _initUpload(self):
        self.queue = asyncio.Queue(maxsize=UPLOAD_QSIZE)
        self.task = self.schedCoro(self._runUpload())

    async def _putUpload(self, item):
        '''
        Put an item on the upload queue while watching for an early request failure.

        Note:
            A bare queue put would deadlock if the request task died while the queue
            was full, which is what happens when the user is denied axon.upload.
        '''
        putt = self.schedCoro(self.queue.put(item))

        await asyncio.wait((putt, self.task), return_when=asyncio.FIRST_COMPLETED)

        if putt.done():
            return await putt

        putt.cancel()

        # this raises if the upload request failed
        await self.task

        mesg = 'The Cortex HTTP API upload ended before all bytes were sent.'
        raise s_exc.BadDataValu(mesg=mesg)

    async def write(self, byts):

        if self.task is None:
            self._initUpload()

        if not byts:
            return

        await self._putUpload(byts)

    async def save(self):

        if self.task is None:
            self._initUpload()

        await self._putUpload(None)

        info = await self.task

        self.task = None
        self.queue = None

        return info.get('size'), s_common.uhex(info.get('sha256'))

class HttpCortex(s_base.Base):
    '''
    A Cortex client which uses the HTTP API rather than Telepath.

    This implements the subset of the Telepath CoreApi which is used by the Storm CLI.

    Note:
        Messages are deserialized from JSON, so nested sequences are lists where the
        Telepath APIs would return tuples.
    '''

    async def __anit__(self, url, cadir=None, proxy=None, verify=True):

        await s_base.Base.__anit__(self)

        info = s_urlhelp.chopurl(url)

        scheme = info.get('scheme')
        if scheme != 'https':
            mesg = f'The Cortex HTTP API client requires an https:// URL, got {scheme}://.'
            raise s_exc.BadUrl(mesg=mesg)

        apikey = info.get('user')
        if apikey is None:
            raise s_exc.BadArg(mesg=apikeymesg, arg='apikey')

        isok, _ = s_passwd.parseApiKey(apikey)
        if not isok:
            mesg = f'The value is not a valid Synapse user API key. {apikeymesg}'
            raise s_exc.BadArg(mesg=mesg, arg='apikey')

        # NOTE: the API key may be embedded in the userinfo of the caller's URL, so the
        # URL must never be logged. The s_urlhelp.sanitizeUrl() helper only masks a passwd.
        self.baseurl = getBaseUrl(info)

        self.sslctx = self._initSslCtx(cadir, verify)

        # NOTE: the kwargs used by every request. aiohttp only strips Authorization,
        # Cookie, and Proxy-Authorization from a cross origin redirect, so the X-API-KEY
        # header would otherwise be replayed to the redirect target ( over cleartext, if
        # the redirect is to http:// ). None of the API endpoints redirect.
        self.reqinfo = {'ssl': self.sslctx, 'allow_redirects': False}

        connector = None
        if proxy is not None:
            connector = aiohttp_socks.ProxyConnector.from_url(proxy)

        # NOTE: aiohttp defaults to a 300 second total timeout which would abort long
        # running Storm queries.
        timeout = aiohttp.ClientTimeout(total=None)

        sess = aiohttp.ClientSession(connector=connector,
                                     timeout=timeout,
                                     headers={'X-API-KEY': apikey},
                                     max_line_size=s_const.MAX_LINE_SIZE,
                                     max_field_size=s_const.MAX_FIELD_SIZE)

        self.sess = await self.enter_context(sess)

        await self._reqCortexApi()

    async def _reqCortexApi(self):
        '''
        Confirm the URL, TLS configuration, and API key before we return.

        Note:
            The model norm API is API key only and normalizing a value neither executes
            Storm nor writes to the nexus, so this leaves nothing behind in the Storm
            log of a production Cortex.
        '''
        body = {'prop': 'meta:source:name', 'value': 'stormcli'}

        async with self.sess.post(self._getUrl('/api/v3/model/norm'), json=body, **self.reqinfo) as resp:
            await self._getRestRetn(resp)

    def _initSslCtx(self, cadir, verify):

        if cadir is None:
            sslctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)

        else:

            if not os.path.isdir(cadir):
                mesg = f'The TLS CA directory does not exist: {cadir}'
                raise s_exc.BadArg(mesg=mesg, arg='tls-ca-dir')

            sslctx = s_common.getSslCtx(cadir, purpose=ssl.Purpose.SERVER_AUTH)

        sslctx.verify_flags &= ~ssl.VERIFY_X509_STRICT

        if not verify:
            sslctx.check_hostname = False
            sslctx.verify_mode = ssl.CERT_NONE

        return sslctx

    def _getUrl(self, path):
        return f'{self.baseurl}{path}'

    async def _getRestBody(self, resp):
        '''
        Return the parsed JSON body of a response, or None if it is not JSON.
        '''
        try:
            return s_json.loads(await resp.read())
        except s_exc.BadJsonText:
            return None

    async def _getRestRetn(self, resp):
        '''
        Return the result from a REST response envelope.

        Note:
            The envelope only carries the exception name and message, so the errinfo
            of the original exception cannot be recovered.
        '''
        return s_httpapi.result(resp.status, await self._getRestBody(resp))

    async def _reqRestOk(self, resp):
        '''
        Raise a SynErr if a streaming response did not start successfully.
        '''
        if resp.status == 200:
            return

        s_httpapi.result(resp.status, await self._getRestBody(resp))

    async def storm(self, text, *, opts=None):

        if opts is None:
            opts = {}

        opts = dict(opts)
        opts.setdefault('keepalive', KEEPALIVE)

        body = {'query': text, 'opts': opts}

        async with self.sess.post(self._getUrl('/api/v3/storm'), json=body, **self.reqinfo) as resp:

            await self._reqRestOk(resp)

            fini = False

            async for mesg in iterJsonLines(resp.content.iter_any()):

                if mesg[0] == 'fini':
                    fini = True

                yield mesg

            # the server swallows exceptions raised after the first flush, so a
            # truncated stream is only detectable by the missing fini message.
            if not fini:
                errm = 'The Cortex HTTP API storm stream ended without a fini message.'
                yield ('err', ('LinkShutDown', {'mesg': errm}))

    async def callStorm(self, text, *, opts=None):

        body = {'query': text}
        if opts is not None:
            body['opts'] = opts

        async with self.sess.post(self._getUrl('/api/v3/storm/call'), json=body, **self.reqinfo) as resp:
            return await self._getRestRetn(resp)

    async def exportStorm(self, text, *, opts=None):

        body = {'query': text}
        if opts is not None:
            body['opts'] = opts

        url = self._getUrl('/api/v3/storm/export')
        timeout = aiohttp.ClientTimeout(total=EXPORT_TIMEOUT)

        async with self.sess.post(url, json=body, timeout=timeout, **self.reqinfo) as resp:

            await self._reqRestOk(resp)

            size = 0
            unpk = s_msgpack.Unpk()

            async for byts in resp.content.iter_any():

                size += len(byts)

                for _, pode in unpk.feed(byts):
                    yield pode

            if size != unpk.size:
                mesg = 'The Cortex HTTP API export stream ended with a partial node.'
                raise s_exc.BadDataValu(mesg=mesg)

    async def getCoreInfoV2(self):

        async with self.sess.get(self._getUrl('/api/v3/core/info'), **self.reqinfo) as resp:
            return await self._getRestRetn(resp)

    async def getAxonBytes(self, sha256):

        url = self._getUrl(f'/api/v3/axon/files/by/sha256/{sha256}')

        async with self.sess.get(url, **self.reqinfo) as resp:

            if resp.status != 200:

                item = await self._getRestBody(resp)

                # normalize the HTTP message to match the Telepath API
                if isinstance(item, dict) and item.get('code') == 'NoSuchFile':
                    mesg = 'Axon does not contain the requested file.'
                    raise s_exc.NoSuchFile(mesg=mesg, sha256=sha256)

                s_httpapi.result(resp.status, item)

            async for byts in resp.content.iter_chunked(CHUNK_SIZE):
                yield byts

    async def getAxonUpload(self):
        upload = await HttpUpload.anit(self)
        self.onfini(upload)
        return upload
