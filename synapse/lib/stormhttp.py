import json
import asyncio
import logging
import urllib.parse

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

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:  # pragma: no cover
            return s_common.retnexc(e)

    async def rx(self, timeout=None):

        try:
            _type, data, extra = await asyncio.wait_for(self.resp.receive(), timeout=timeout)
            if _type == aiohttp.WSMsgType.BINARY:
                return (True, json.loads(data))
            if _type == aiohttp.WSMsgType.TEXT:
                return (True, json.loads(data.encode()))
            if _type == aiohttp.WSMsgType.CLOSED:  # pragma: no cover
                return (True, None)
            return (False, ('BadMesgFormat', {'mesg': f'WebSocket RX unhandled type: {_type.name}'}))  # pragma: no cover

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:  # pragma: no cover
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
                      {'name': 'fields', 'type': 'list',
                       'desc': 'A list of info dictionaries containing the name, value or sha256, '
                               'and additional parameters for fields to post, as multipart/form-data. '
                               'If a sha256 is specified, the request will be sent from the axon '
                               'and the corresponding file will be uploaded as the value for '
                               'the field.',
                       'default': None, },
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
                      {'name': 'fields', 'type': 'list',
                       'desc': 'A list of info dictionaries containing the name, value or sha256, '
                               'and additional parameters for fields to post, as multipart/form-data. '
                               'If a sha256 is specified, the request will be sent from the axon '
                               'and the corresponding file will be uploaded as the value for '
                               'the field.',
                       'default': None, },
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
                       'default': 300, },
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the connection request.',
                       'default': None, },
                  ),
                  'returns': {'type': 'storm:http:socket', 'desc': 'A websocket object.'}}},
        {'name': 'urlencode', 'desc': '''
            Urlencode a text string.

            This will replace special characters in a string using the %xx escape and
            replace spaces with plus signs.

            Examples:
                Urlencode a string::

                    $str=$lib.inet.http.urlencode("http://go ogle.com")
         ''',
         'type': {'type': 'function', '_funcname': 'urlencode',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text string.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The urlencoded string.', }}},
        {'name': 'urldecode', 'desc': '''
            Urldecode a text string.

            This will replace %xx escape characters with the special characters they represent
            and replace plus signs with spaces.

            Examples:
                Urlencode a string::

                    $str=$lib.inet.http.urldecode("http%3A%2F%2Fgo+ogle.com")
         ''',
         'type': {'type': 'function', '_funcname': 'urldecode',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text string.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The urldecoded string.', }}},
    )
    _storm_lib_path = ('inet', 'http')

    def getObjLocals(self):
        return {
            'get': self._httpEasyGet,
            'post': self._httpPost,
            'head': self._httpEasyHead,
            'request': self._httpRequest,
            'connect': self.inetHttpConnect,
            'urlencode': self.urlencode,
            'urldecode': self.urldecode,
        }

    def strify(self, item):
        if isinstance(item, (list, tuple)):
            return [(str(k), str(v)) for (k, v) in item]
        elif isinstance(item, dict):
            return {str(k): str(v) for k, v in item.items()}
        return item

    async def urlencode(self, text):
        text = await s_stormtypes.tostr(text)
        return urllib.parse.quote_plus(text)

    async def urldecode(self, text):
        text = await s_stormtypes.tostr(text)
        return urllib.parse.unquote_plus(text)

    async def _httpEasyHead(self, url, headers=None, ssl_verify=True, params=None, timeout=300,
                            allow_redirects=False):
        return await self._httpRequest('HEAD', url, headers=headers, ssl_verify=ssl_verify, params=params,
                                       timeout=timeout, allow_redirects=allow_redirects, )

    async def _httpEasyGet(self, url, headers=None, ssl_verify=True, params=None, timeout=300,
                           allow_redirects=True):
        return await self._httpRequest('GET', url, headers=headers, ssl_verify=ssl_verify, params=params,
                                       timeout=timeout, allow_redirects=allow_redirects, )

    async def _httpPost(self, url, headers=None, json=None, body=None, ssl_verify=True,
                        params=None, timeout=300, allow_redirects=True, fields=None):
        return await self._httpRequest('POST', url, headers=headers, json=json, body=body,
                                       ssl_verify=ssl_verify, params=params, timeout=timeout,
                                       allow_redirects=allow_redirects, fields=fields, )

    async def inetHttpConnect(self, url, headers=None, ssl_verify=True, timeout=300, params=None):

        url = await s_stormtypes.tostr(url)
        headers = await s_stormtypes.toprim(headers)
        timeout = await s_stormtypes.toint(timeout, noneok=True)
        params = await s_stormtypes.toprim(params)

        headers = self.strify(headers)

        sock = await WebSocket.anit()

        proxyurl = await self.runt.snap.core.getConfOpt('http:proxy')
        connector = None
        if proxyurl is not None:
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            sess = await sock.enter_context(aiohttp.ClientSession(connector=connector, timeout=timeout))
            sock.resp = await sock.enter_context(sess.ws_connect(url, headers=headers, ssl=ssl_verify, timeout=timeout,
                                                                 params=params, ))

            sock._syn_refs = 0
            self.runt.onfini(sock)

            return (True, sock)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:  # pragma: no cover
            await sock.fini()
            return s_common.retnexc(e)

    def _buildFormData(self, fields):
        data = aiohttp.FormData()
        for field in fields:
            data.add_field(field.get('name'),
                           field.get('value'),
                           content_type=field.get('content_type'),
                           filename=field.get('filename'),
                           content_transfer_encoding=field.get('content_transfer_encoding'))
        return data

    async def _httpRequest(self, meth, url, headers=None, json=None, body=None,
                           ssl_verify=True, params=None, timeout=300, allow_redirects=True,
                           fields=None, ):
        meth = await s_stormtypes.tostr(meth)
        url = await s_stormtypes.tostr(url)
        json = await s_stormtypes.toprim(json)
        body = await s_stormtypes.toprim(body)
        fields = await s_stormtypes.toprim(fields)
        headers = await s_stormtypes.toprim(headers)
        params = await s_stormtypes.toprim(params)
        timeout = await s_stormtypes.toint(timeout, noneok=True)
        ssl_verify = await s_stormtypes.tobool(ssl_verify, noneok=True)
        allow_redirects = await s_stormtypes.tobool(allow_redirects)

        kwargs = {'allow_redirects': allow_redirects}
        if params:
            kwargs['params'] = self.strify(params)

        headers = self.strify(headers)

        if fields:
            if any(['sha256' in field for field in fields]):
                self.runt.confirm(('storm', 'lib', 'axon', 'wput'))
                axon = self.runt.snap.core.axon
                info = await axon.postfiles(fields, url, headers=headers, params=params,
                                            method=meth, ssl=ssl_verify, timeout=timeout)
                return HttpResp(info)
            else:
                data = self._buildFormData(fields)
        else:
            data = body

        proxyurl = self.runt.snap.core.conf.get('http:proxy')
        cadir = self.runt.snap.core.conf.get('tls:ca:dir')

        connector = None
        if proxyurl is not None:
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        if ssl_verify is False:
            kwargs['ssl'] = False
        elif cadir:
            kwargs['ssl'] = s_common.getSslCtx(cadir)
        else:
            # default aiohttp behavior
            kwargs['ssl'] = None

        timeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
            try:
                async with sess.request(meth, url, headers=headers, json=json, data=data, **kwargs) as resp:
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
        try:
            return json.loads(self.valu.get('body'))
        except json.JSONDecodeError as e:
            mesg = f'Unable to decode HTTP response as json: {e.args[0]}'
            raise s_exc.BadJsonText(mesg=mesg)

    async def _httpRespMsgpack(self):
        byts = self.valu.get('body')
        unpk = s_msgpack.Unpk()
        for _, item in unpk.feed(byts):
            yield item
