import json
import asyncio
import logging

logger = logging.getLogger(__name__)

import aiohttp
import aiohttp_socks

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.msgpack as s_msgpack
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerType
class WebSocket(s_base.Base, s_stormtypes.StormType):
    '''
    Implements the Storm API for a Websocket.
    '''
    _storm_typename = 'storm:http:socket'

    _storm_locals = (

        {'name': 'tx', 'desc': 'Transmit a message over the web socket.',
         'type': {'type': 'function', '_funcname': 'tx',
                  'args': (
                      {'name': 'mesg', 'type': 'dict', 'desc': 'A JSON compatible message.', },
                  ),
                  'returns': {'type': 'list', 'desc': 'An ($ok, $valu) tuple.'}}},

        {'name': 'rx', 'desc': 'Receive a message from the web socket.',
         'type': {'type': 'function', '_funcname': 'rx',
                  'args': (
                      {'name': 'timeout', 'type': 'int', 'desc': 'The timeout to wait for',
                       'default': None, },
                  ),
                  'returns': {'type': 'list', 'desc': 'An ($ok, $valu) tuple.'}}},
    )

    async def __anit__(self):
        await s_base.Base.__anit__(self)
        s_stormtypes.StormType.__init__(self)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'tx': self.tx,
            'rx': self.rx,
        }

    async def tx(self, mesg):
        try:

            mesg = await s_stormtypes.toprim(mesg)
            await self.resp.send_bytes(json.dumps(mesg).encode())
            return (True, None)

        except asyncio.CancelledError: # pragma: no cover
            raise

        except Exception as e: # pragma: no cover
            return s_common.retnexc(e)

    async def rx(self, timeout=None):

        try:
            _type, data, extra = await asyncio.wait_for(self.resp.receive(), timeout=timeout)
            if _type == aiohttp.WSMsgType.BINARY:
                return (True, json.loads(data))
            if _type == aiohttp.WSMsgType.TEXT:
                return (True, json.loads(data.encode()))
            if _type == aiohttp.WSMsgType.CLOSED: # pragma: no cover
                return (True, None)
            return (False, ('BadMesgFormat', {'mesg': f'WebSocket RX unhandled type: {_type.name}'})) # pragma: no cover

        except asyncio.CancelledError: # pragma: no cover
            raise

        except Exception as e: # pragma: no cover
            return s_common.retnexc(e)


@s_stormtypes.registry.registerLib
class LibHttp(s_stormtypes.Lib):
    '''
    A Storm Library exposing an HTTP client API.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get the contents of a given URL.',
         'type': {'type': 'function', '_funcname': '_httpEasyGet',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to retrieve.', },
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None, },
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True, },
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the request.',
                       'default': None, },
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300, },
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to false, do not follow redirects.',
                       'default': True, },
                  ),
                  'returns': {'type': 'storm:http:resp', 'desc': 'The response object.', }}},
        {'name': 'post', 'desc': 'Post data to a given URL.',
         'type': {'type': 'function', '_funcname': '_httpPost',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to post to.', },
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None, },
                      {'name': 'json', 'type': 'prim', 'desc': 'The data to post, as JSON object.',
                       'default': None, },
                      {'name': 'body', 'type': 'bytes', 'desc': 'The data to post, as binary object.',
                       'default': None, },
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True, },
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the request.',
                       'default': None, },
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300, },
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to false, do not follow redirects.',
                       'default': True, },
                  ),
                  'returns': {'type': 'storm:http:resp', 'desc': 'The response object.', }}},
        {'name': 'head', 'desc': 'Get the HEAD response for a URL.',
         'type': {'type': 'function', '_funcname': '_httpEasyHead',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to retrieve.', },
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None, },
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True, },
                      {'name': 'params', 'type': 'dict',
                       'desc': 'Optional parameters which may be passed to the request.',
                       'default': None, },
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300, },
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to true, follow redirects.',
                       'default': False, },
                  ),
                  'returns': {'type': 'storm:http:resp', 'desc': 'The response object.', }}},
        {'name': 'request', 'desc': 'Make an HTTP request using the given HTTP method to the url.',
         'type': {'type': 'function', '_funcname': '_httpRequest',
                   'args': (
                      {'name': 'meth', 'type': 'str', 'desc': 'The HTTP method. (ex. PUT)', },
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to send the request to.', },
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None, },
                      {'name': 'json', 'type': 'prim', 'desc': 'The data to include in the body, as JSON object.',
                       'default': None, },
                      {'name': 'body', 'type': 'bytes', 'desc': 'The data to include in the body, as binary object.',
                       'default': None, },
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True, },
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the request.',
                       'default': None, },
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300, },
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to false, do not follow redirects.',
                       'default': True, },
                   ),
                  'returns': {'type': 'storm:http:resp', 'desc': 'The response object.', }
                  }
         },
        {'name': 'connect', 'desc': 'Connect a web socket to tx/rx JSON messages.',
         'type': {'type': 'function', '_funcname': 'inetHttpConnect',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to retrieve.', },
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None, },
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True, },
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300, }
                  ),
                  'returns': {'type': 'storm:http:socket', 'desc': 'A websocket object.'}}},
    )
    _storm_lib_path = ('inet', 'http')

    def getObjLocals(self):
        return {
            'get': self._httpEasyGet,
            'post': self._httpPost,
            'head': self._httpEasyHead,
            'request': self._httpRequest,
            'connect': self.inetHttpConnect,
        }

    async def _httpEasyHead(self, url, headers=None, ssl_verify=True, params=None, timeout=300,
                            allow_redirects=False):
        return await self._httpRequest('HEAD', url, headers=headers, ssl_verify=ssl_verify, params=params,
                                       timeout=timeout, allow_redirects=allow_redirects, )

    async def _httpEasyGet(self, url, headers=None, ssl_verify=True, params=None, timeout=300,
                           allow_redirects=True):
        return await self._httpRequest('GET', url, headers=headers, ssl_verify=ssl_verify, params=params,
                                       timeout=timeout, allow_redirects=allow_redirects, )

    async def _httpPost(self, url, headers=None, json=None, body=None, ssl_verify=True, params=None, timeout=300,
                        allow_redirects=True):
        return await self._httpRequest('POST', url, headers=headers, json=json, body=body,
                                       ssl_verify=ssl_verify, params=params, timeout=timeout,
                                       allow_redirects=allow_redirects, )

    async def inetHttpConnect(self, url, headers=None, ssl_verify=True, timeout=300):

        url = await s_stormtypes.tostr(url)
        headers = await s_stormtypes.toprim(headers)
        timeout = await s_stormtypes.toint(timeout, noneok=True)

        sock = await WebSocket.anit()

        proxyurl = await self.runt.snap.core.getConfOpt('http:proxy')
        connector = None
        if proxyurl is not None:
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            sess = await sock.enter_context(aiohttp.ClientSession(connector=connector, timeout=timeout))
            sock.resp = await sock.enter_context(sess.ws_connect(url, headers=headers, ssl=ssl_verify, timeout=timeout))

            sock._syn_refs = 0
            self.runt.onfini(sock)

            return (True, sock)

        except asyncio.CancelledError: # pragma: no cover
            raise

        except Exception as e: # pragma: no cover
            await sock.fini()
            return s_common.retnexc(e)

    async def _httpRequest(self, meth, url, headers=None, json=None, body=None, ssl_verify=True,
                           params=None, timeout=300, allow_redirects=True, ):
        meth = await s_stormtypes.tostr(meth)
        url = await s_stormtypes.tostr(url)
        json = await s_stormtypes.toprim(json)
        body = await s_stormtypes.toprim(body)
        headers = await s_stormtypes.toprim(headers)
        params = await s_stormtypes.toprim(params)
        timeout = await s_stormtypes.toint(timeout, noneok=True)
        allow_redirects = await s_stormtypes.tobool(allow_redirects)

        kwargs = {'allow_redirects': allow_redirects}
        if not ssl_verify:
            kwargs['ssl'] = False
        if params:
            kwargs['params'] = params

        todo = s_common.todo('getConfOpt', 'http:proxy')
        proxyurl = await self.runt.dyncall('cortex', todo)

        connector = None
        if proxyurl is not None:
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        timeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
            try:
                async with sess.request(meth, url, headers=headers, json=json, data=body, **kwargs) as resp:
                    info = {
                        'code': resp.status,
                        'headers': dict(resp.headers),
                        'url': str(resp.url),
                        'body': await resp.read(),
                    }
                    return HttpResp(info)

            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.exception(f'Error during http {meth} @ {url}')
                err = s_common.err(e)
                info = {
                    'code': -1,
                    'headers': dict(),
                    'url': url,
                    'body': b'',
                    'err': err,
                }
                return HttpResp(info)

@s_stormtypes.registry.registerType
class HttpResp(s_stormtypes.Prim):
    '''
    Implements the Storm API for a HTTP response.
    '''
    _storm_locals = (
        {'name': 'code', 'desc': 'The HTTP status code. It is -1 if an exception occurred.',
            'type': 'int', },
        {'name': 'body', 'desc': 'The raw HTTP response body as bytes.', 'type': 'bytes', },
        {'name': 'headers', 'type': 'dict', 'desc': 'The HTTP Response headers.'},
        {'name': 'err', 'type': 'list', 'desc': 'Tufo of the error type and information if an exception occurred.'},
        {'name': 'json', 'desc': 'Get the JSON deserialized response.',
            'type': {'type': 'function', '_funcname': '_httpRespJson',
                     'returns': {'type': 'prim'}
                     }
        },
        {'name': 'msgpack', 'desc': 'Yield the msgpack deserialized objects.',
            'type': {'type': 'function', '_funcname': '_httpRespMsgpack',
                     'returns': {'name': 'Yields', 'type': 'prim', 'desc': 'Unpacked values.'}
                     }
        },
    )
    _storm_typename = 'storm:http:resp'
    def __init__(self, valu, path=None):
        super().__init__(valu, path=path)
        self.locls.update(self.getObjLocals())
        self.locls['code'] = self.valu.get('code')
        self.locls['body'] = self.valu.get('body')
        self.locls['headers'] = self.valu.get('headers')
        self.locls['err'] = self.valu.get('err', ())

    def getObjLocals(self):
        return {
            'json': self._httpRespJson,
            'msgpack': self._httpRespMsgpack,
        }

    async def _httpRespJson(self):
        return json.loads(self.valu.get('body'))

    async def _httpRespMsgpack(self):
        byts = self.valu.get('body')
        unpk = s_msgpack.Unpk()
        for _, item in unpk.feed(byts):
            yield item
