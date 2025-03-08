import asyncio
import logging
import urllib.parse

logger = logging.getLogger(__name__)

import aiohttp
import aiohttp_socks

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.json as s_json
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version
import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerType
class WebSocket(s_base.Base, s_stormtypes.StormType):
    '''
    Implements the Storm API for a Websocket.
    '''
    _storm_typename = 'inet:http:socket'

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
            await self.resp.send_bytes(s_json.dumps(mesg))
            return (True, None)

        except asyncio.CancelledError:  # pragma: no cover
            raise

        except Exception as e:  # pragma: no cover
            return s_common.retnexc(e)

    async def rx(self, timeout=None):

        try:
            _type, data, extra = await s_common.wait_for(self.resp.receive(), timeout=timeout)
            if _type in (aiohttp.WSMsgType.BINARY, aiohttp.WSMsgType.TEXT):
                return (True, s_json.loads(data))
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

    For APIs that accept an ssl_opts argument, the dictionary may contain the following values::

        ({
            'verify': <bool> - Perform SSL/TLS verification. Is overridden by the ssl_verify argument.
            'client_cert': <str> - PEM encoded full chain certificate for use in mTLS.
            'client_key': <str> - PEM encoded key for use in mTLS. Alternatively, can be included in client_cert.
            'ca_cert': <str> - A PEM encoded full chain CA certificate for use when verifying the request.
        })

    For APIs that accept a proxy argument, the following values are supported::

        (null): Deprecated - Use the proxy defined by the http:proxy configuration option if set.
        (true): Use the proxy defined by the http:proxy configuration option if set.
        (false): Do not use the proxy defined by the http:proxy configuration option if set.
        <str>: A proxy URL string.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get the contents of a given URL.',
         'type': {'type': 'function', '_funcname': '_httpEasyGet',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to retrieve.', },
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None},
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True},
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the request.',
                       'default': None},
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300},
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to false, do not follow redirects.',
                       'default': True},
                      {'name': 'proxy', 'type': ['bool', 'str'],
                       'desc': 'Configure proxy usage. See $lib.inet.http help for additional details.', 'default': True},
                      {'name': 'ssl_opts', 'type': 'dict',
                       'desc': 'Optional SSL/TLS options. See $lib.inet.http help for additional details.',
                       'default': None},
                  ),
                  'returns': {'type': 'inet:http:resp', 'desc': 'The response object.'}}},
        {'name': 'post', 'desc': 'Post data to a given URL.',
         'type': {'type': 'function', '_funcname': '_httpPost',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to post to.', },
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None},
                      {'name': 'json', 'type': 'prim', 'desc': 'The data to post, as JSON object.',
                       'default': None},
                      {'name': 'body', 'type': 'bytes', 'desc': 'The data to post, as binary object.',
                       'default': None},
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True},
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the request.',
                       'default': None},
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300},
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to false, do not follow redirects.',
                       'default': True},
                      {'name': 'fields', 'type': 'list',
                       'desc': 'A list of info dictionaries containing the name, value or sha256, '
                               'and additional parameters for fields to post, as multipart/form-data. '
                               'If a sha256 is specified, the request will be sent from the axon '
                               'and the corresponding file will be uploaded as the value for '
                               'the field.',
                       'default': None},
                      {'name': 'proxy', 'type': ['bool', 'str'],
                       'desc': 'Configure proxy usage. See $lib.inet.http help for additional details.', 'default': True},
                      {'name': 'ssl_opts', 'type': 'dict',
                       'desc': 'Optional SSL/TLS options. See $lib.inet.http help for additional details.',
                       'default': None},
                  ),
                  'returns': {'type': 'inet:http:resp', 'desc': 'The response object.'}}},
        {'name': 'head', 'desc': 'Get the HEAD response for a URL.',
         'type': {'type': 'function', '_funcname': '_httpEasyHead',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to retrieve.'},
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None},
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True},
                      {'name': 'params', 'type': 'dict',
                       'desc': 'Optional parameters which may be passed to the request.',
                       'default': None},
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300, },
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to true, follow redirects.',
                       'default': False},
                      {'name': 'proxy', 'type': ['bool', 'str'],
                       'desc': 'Configure proxy usage. See $lib.inet.http help for additional details.', 'default': True},
                      {'name': 'ssl_opts', 'type': 'dict',
                       'desc': 'Optional SSL/TLS options. See $lib.inet.http help for additional details.',
                       'default': None},
                  ),
                  'returns': {'type': 'inet:http:resp', 'desc': 'The response object.'}}},
        {'name': 'request', 'desc': 'Make an HTTP request using the given HTTP method to the url.',
         'type': {'type': 'function', '_funcname': '_httpRequest',
                   'args': (
                      {'name': 'meth', 'type': 'str', 'desc': 'The HTTP method. (ex. PUT)'},
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to send the request to.'},
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None},
                      {'name': 'json', 'type': 'prim', 'desc': 'The data to include in the body, as JSON object.',
                       'default': None},
                      {'name': 'body', 'type': 'bytes', 'desc': 'The data to include in the body, as binary object.',
                       'default': None},
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True},
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the request.',
                       'default': None},
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300},
                      {'name': 'allow_redirects', 'type': 'bool', 'desc': 'If set to false, do not follow redirects.',
                       'default': True},
                      {'name': 'fields', 'type': 'list',
                       'desc': 'A list of info dictionaries containing the name, value or sha256, '
                               'and additional parameters for fields to post, as multipart/form-data. '
                               'If a sha256 is specified, the request will be sent from the axon '
                               'and the corresponding file will be uploaded as the value for '
                               'the field.',
                       'default': None},
                      {'name': 'proxy', 'type': ['bool', 'str'],
                       'desc': 'Configure proxy usage. See $lib.inet.http help for additional details.', 'default': True},
                      {'name': 'ssl_opts', 'type': 'dict',
                       'desc': 'Optional SSL/TLS options. See $lib.inet.http help for additional details.',
                       'default': None},
                   ),
                  'returns': {'type': 'inet:http:resp', 'desc': 'The response object.'}
                  }
         },
        {'name': 'connect', 'desc': 'Connect a web socket to tx/rx JSON messages.',
         'type': {'type': 'function', '_funcname': 'inetHttpConnect',
                  'args': (
                      {'name': 'url', 'type': 'str', 'desc': 'The URL to retrieve.'},
                      {'name': 'headers', 'type': 'dict', 'desc': 'HTTP headers to send with the request.',
                       'default': None},
                      {'name': 'ssl_verify', 'type': 'boolean', 'desc': 'Perform SSL/TLS verification.',
                       'default': True},
                      {'name': 'timeout', 'type': 'int', 'desc': 'Total timeout for the request in seconds.',
                       'default': 300},
                      {'name': 'params', 'type': 'dict', 'desc': 'Optional parameters which may be passed to the connection request.',
                       'default': None},
                      {'name': 'proxy', 'type': ['bool', 'str'],
                       'desc': 'Configure proxy usage. See $lib.inet.http help for additional details.', 'default': True},
                      {'name': 'ssl_opts', 'type': 'dict',
                       'desc': 'Optional SSL/TLS options. See $lib.inet.http help for additional details.',
                       'default': None},
                  ),
                  'returns': {'type': 'inet:http:socket', 'desc': 'A websocket object.'}}},
        {'name': 'urlencode', 'desc': '''
            Urlencode a text string.

            This will replace special characters in a string using the %xx escape and
            replace spaces with plus signs.

            Examples:
                Urlencode a string::

                    $str=$lib.inet.http.urlencode("http://google.com")
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
        {'name': 'codereason', 'desc': '''
            Get the reason phrase for an HTTP status code.

            Examples:
                Get the reason for a 404 status code::

                    $str=$lib.inet.http.codereason(404)
         ''',
         'type': {'type': 'function', '_funcname': 'codereason',
                  'args': (
                      {'name': 'code', 'type': 'int', 'desc': 'The HTTP status code.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The reason phrase for the status code.', }}},
    )
    _storm_lib_path = ('inet', 'http')
    _storm_lib_perms = (
        {'perm': ('storm', 'lib', 'inet', 'http', 'proxy'), 'gate': 'cortex',
         'desc': 'Permits a user to specify the proxy used with `$lib.inet.http` APIs.'},
    )

    def getObjLocals(self):
        return {
            'get': self._httpEasyGet,
            'post': self._httpPost,
            'head': self._httpEasyHead,
            'request': self._httpRequest,
            'connect': self.inetHttpConnect,
            'urlencode': self.urlencode,
            'urldecode': self.urldecode,
            'codereason': self.codereason,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def urlencode(self, text):
        text = await s_stormtypes.tostr(text)
        return urllib.parse.quote_plus(text)

    @s_stormtypes.stormfunc(readonly=True)
    async def urldecode(self, text):
        text = await s_stormtypes.tostr(text)
        return urllib.parse.unquote_plus(text)

    @s_stormtypes.stormfunc(readonly=True)
    async def codereason(self, code):
        code = await s_stormtypes.toint(code)
        return s_common.httpcodereason(code)

    async def _httpEasyHead(self, url, headers=None, ssl_verify=True, params=None, timeout=300,
                            allow_redirects=False, proxy=True, ssl_opts=None):
        return await self._httpRequest('HEAD', url, headers=headers, ssl_verify=ssl_verify, params=params,
                                       timeout=timeout, allow_redirects=allow_redirects, proxy=proxy, ssl_opts=ssl_opts)

    async def _httpEasyGet(self, url, headers=None, ssl_verify=True, params=None, timeout=300,
                           allow_redirects=True, proxy=True, ssl_opts=None):
        return await self._httpRequest('GET', url, headers=headers, ssl_verify=ssl_verify, params=params,
                                       timeout=timeout, allow_redirects=allow_redirects, proxy=proxy, ssl_opts=ssl_opts)

    async def _httpPost(self, url, headers=None, json=None, body=None, ssl_verify=True,
                        params=None, timeout=300, allow_redirects=True, fields=None, proxy=True, ssl_opts=None):
        return await self._httpRequest('POST', url, headers=headers, json=json, body=body,
                                       ssl_verify=ssl_verify, params=params, timeout=timeout,
                                       allow_redirects=allow_redirects, fields=fields, proxy=proxy, ssl_opts=ssl_opts)

    async def inetHttpConnect(self, url, headers=None, ssl_verify=True, timeout=300,
                              params=None, proxy=True, ssl_opts=None):

        url = await s_stormtypes.tostr(url)
        headers = await s_stormtypes.toprim(headers)
        timeout = await s_stormtypes.toint(timeout, noneok=True)
        params = await s_stormtypes.toprim(params)
        proxy = await s_stormtypes.toprim(proxy)
        ssl_verify = await s_stormtypes.tobool(ssl_verify, noneok=True)
        ssl_opts = await s_stormtypes.toprim(ssl_opts)

        headers = s_stormtypes.strifyHttpArg(headers)

        sock = await WebSocket.anit()

        connector = None
        if proxyurl := await s_stormtypes.resolveCoreProxyUrl(proxy):
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        timeout = aiohttp.ClientTimeout(total=timeout)
        kwargs = {'timeout': timeout}
        if params:
            kwargs['params'] = params

        kwargs['ssl'] = self.runt.snap.core.getCachedSslCtx(opts=ssl_opts, verify=ssl_verify)

        try:
            sess = await sock.enter_context(aiohttp.ClientSession(connector=connector, timeout=timeout))
            sock.resp = await sock.enter_context(sess.ws_connect(url, headers=headers, **kwargs))

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
            name = field.get('name')
            data.add_field(name,
                           field.get('value'),
                           content_type=field.get('content_type'),
                           filename=field.get('filename'),
                           content_transfer_encoding=field.get('content_transfer_encoding'))
            if data.is_multipart and not isinstance(name, str):
                mesg = f'Each field requires a "name" key with a string value when multipart fields are enabled: {name}'
                raise s_exc.BadArg(mesg=mesg, name=name)
        return data

    async def _httpRequest(self, meth, url, headers=None, json=None, body=None,
                           ssl_verify=True, params=None, timeout=300, allow_redirects=True,
                           fields=None, proxy=True, ssl_opts=None):
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
        proxy = await s_stormtypes.toprim(proxy)
        ssl_opts = await s_stormtypes.toprim(ssl_opts)

        kwargs = {'allow_redirects': allow_redirects}
        if params:
            kwargs['params'] = s_stormtypes.strifyHttpArg(params, multi=True)

        headers = s_stormtypes.strifyHttpArg(headers)

        if fields:
            if any(['sha256' in field for field in fields]):
                self.runt.confirm(('storm', 'lib', 'axon', 'wput'))

                kwargs = {}

                ok, proxy = await s_stormtypes.resolveAxonProxyArg(proxy)
                if ok:
                    kwargs['proxy'] = proxy

                if ssl_opts is not None:
                    axonvers = self.runt.snap.core.axoninfo['synapse']['version']
                    mesg = f'The ssl_opts argument requires an Axon Synapse version {s_stormtypes.AXON_MINVERS_SSLOPTS}, ' \
                           f'but the Axon is running {axonvers}'
                    s_version.reqVersion(axonvers, s_stormtypes.AXON_MINVERS_SSLOPTS, mesg=mesg)
                    kwargs['ssl_opts'] = ssl_opts

                axon = self.runt.snap.core.axon
                info = await axon.postfiles(fields, url, headers=headers, params=params, method=meth,
                                            ssl=ssl_verify, timeout=timeout, **kwargs)
                return HttpResp(info)

        kwargs['ssl'] = self.runt.snap.core.getCachedSslCtx(opts=ssl_opts, verify=ssl_verify)

        connector = None
        if proxyurl := await s_stormtypes.resolveCoreProxyUrl(proxy):
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        timeout = aiohttp.ClientTimeout(total=timeout)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as sess:
            try:
                if fields:
                    data = self._buildFormData(fields)
                else:
                    data = body

                # `data` and `json` are passed in kwargs only if they are not
                # None because of a weird interaction with aiohttp and vcrpy.
                if data is not None:
                    kwargs['data'] = data

                if json is not None:
                    kwargs['json'] = json

                async with sess.request(meth, url, headers=headers, **kwargs) as resp:
                    history = []
                    for hist in resp.history:
                        hnfo = {
                            'code': hist.status,
                            'reason': await self.codereason(hist.status),
                            'headers': dict(hist.headers),
                            'url': str(hist.url),
                            # aiohttp has already closed the connection by this point
                            # so there is no connection to read a body from.
                            'body': b'',
                            'history': [],
                            'request_headers': dict(hist.request_info.headers)
                        }
                        history.append(hnfo)
                    info = {
                        'code': resp.status,
                        'reason': await self.codereason(resp.status),
                        'headers': dict(resp.headers),
                        'url': str(resp.url),
                        'body': await resp.read(),
                        'history': history,
                        'request_headers': dict(resp.request_info.headers)
                    }
                    return HttpResp(info)

            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                logger.exception(f'Error during http {meth} @ {url}')
                err = s_common.err(e)
                errmsg = err[1].get('mesg')
                if errmsg:
                    reason = f'Exception occurred during request: {err[0]}: {errmsg}'
                else:
                    reason = f'Exception occurred during request: {err[0]}'

                info = {
                    'err': err,
                    'code': -1,
                    'reason': reason,
                    'headers': dict(),
                    'url': url,
                    'body': b'',
                    'history': [],
                    'request_headers': dict(),
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
        {'name': 'reason', 'desc': 'The reason phrase for the HTTP status code.', 'type': 'str'},
        {'name': 'body', 'desc': 'The raw HTTP response body as bytes.', 'type': 'bytes', },
        {'name': 'headers', 'type': 'dict', 'desc': 'The HTTP Response headers.'},
        {'name': 'request_headers', 'type': 'dict', 'desc': 'The HTTP Request headers.'},
        {'name': 'url', 'type': 'str',
         'desc': 'The response URL. If the request was redirected, this would be the final URL in the redirection chain. If the status code is -1, then this is the request URL.'},
        {'name': 'err', 'type': 'list', 'desc': 'Tuple of the error type and information if an exception occurred.'},
        {'name': 'history', 'desc': 'A list of response objects representing the history of the response. This is populated when responses are redirected.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorHistory',
                  'returns': {'type': 'list', 'desc': 'A list of ``inet:http:resp`` objects.', }}},
        {'name': 'json', 'desc': 'Get the JSON deserialized response.',
         'type': {'type': 'function', '_funcname': '_httpRespJson',
                  'args': (
                      {'name': 'encoding', 'type': 'str', 'desc': 'Specify an encoding to use.', 'default': None, },
                      {'name': 'errors', 'type': 'str', 'desc': 'Specify an error handling scheme to use.', 'default': 'surrogatepass', },
                   ),
                   'returns': {'type': 'prim'}
                 }
        },
        {'name': 'msgpack', 'desc': 'Yield the msgpack deserialized objects.',
            'type': {'type': 'function', '_funcname': '_httpRespMsgpack',
                     'returns': {'name': 'Yields', 'type': 'prim', 'desc': 'Unpacked values.'}
                     }
        },
    )
    _storm_typename = 'inet:http:resp'
    def __init__(self, valu, path=None):
        super().__init__(valu, path=path)
        self.locls.update(self.getObjLocals())
        self.locls['url'] = self.valu.get('url')
        self.locls['code'] = self.valu.get('code')
        self.locls['reason'] = self.valu.get('reason')
        self.locls['body'] = self.valu.get('body')
        self.locls['headers'] = self.valu.get('headers')
        self.locls['request_headers'] = self.valu.get('request_headers')
        self.locls['err'] = self.valu.get('err', ())

        self.gtors.update({
            'history': self._gtorHistory,
        })

    def getObjLocals(self):
        return {
            'json': self._httpRespJson,
            'msgpack': self._httpRespMsgpack,
        }

    async def _httpRespJson(self, encoding=None, errors='surrogatepass'):
        try:
            valu = self.valu.get('body')
            errors = await s_stormtypes.tostr(errors)

            if encoding is None:
                encoding = s_json.detect_encoding(valu)
            else:
                encoding = await s_stormtypes.tostr(encoding)

            return s_json.loads(valu.decode(encoding, errors))

        except UnicodeDecodeError as e:
            raise s_exc.StormRuntimeError(mesg=f'{e}: {s_common.trimText(repr(valu))}') from None

        except s_exc.BadJsonText as e:
            mesg = f'Unable to decode HTTP response as json: {e.get("mesg")}'
            raise s_exc.BadJsonText(mesg=mesg)

    async def _httpRespMsgpack(self):
        byts = self.valu.get('body')
        unpk = s_msgpack.Unpk()
        for _, item in unpk.feed(byts):
            yield item

    async def _gtorHistory(self):
        return [HttpResp(hnfo) for hnfo in self.valu.get('history')]
