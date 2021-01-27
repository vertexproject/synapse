import json
import asyncio

import aiohttp
import aiohttp_socks

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

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
                   ),
                  'returns': {'type': 'storm:http:resp', 'desc': 'The response object.', }
                  }
         },
    )
    _storm_lib_path = ('inet', 'http')

    def getObjLocals(self):
        return {
            'get': self._httpEasyGet,
            'post': self._httpPost,
            'request': self._httpRequest,
        }

    async def _httpEasyGet(self, url, headers=None, ssl_verify=True, params=None):
        return await self._httpRequest('get', url, headers=headers, ssl_verify=ssl_verify, params=params)

    async def _httpPost(self, url, headers=None, json=None, body=None, ssl_verify=True, params=None):
        return await self._httpRequest('POST', url, headers=headers, json=json,
                                       body=body, ssl_verify=ssl_verify, params=params)

    async def _httpRequest(self, meth, url, headers=None, json=None, body=None, ssl_verify=True,
                           params=None):
        meth = await s_stormtypes.tostr(meth)
        url = await s_stormtypes.tostr(url)
        json = await s_stormtypes.toprim(json)
        body = await s_stormtypes.toprim(body)
        headers = await s_stormtypes.toprim(headers)
        params = await s_stormtypes.toprim(params)

        kwargs = {}
        if not ssl_verify:
            kwargs['ssl'] = False
        if params:
            kwargs['params'] = params

        todo = s_common.todo('getConfOpt', 'http:proxy')
        proxyurl = await self.runt.dyncall('cortex', todo)

        connector = None
        if proxyurl is not None:
            connector = aiohttp_socks.ProxyConnector.from_url(proxyurl)

        async with aiohttp.ClientSession(connector=connector) as sess:
            try:
                async with sess.request(meth, url, headers=headers, json=json, data=body, **kwargs) as resp:
                    info = {
                        'code': resp.status,
                        'headers': dict(resp.headers),
                        'url': str(resp.url),
                        'body': await resp.read(),
                    }
                    return HttpResp(info)
                    # return HttpResp(code=resp.status, body=await resp.content.read())
            except asyncio.CancelledError:  # pragma: no cover
                raise
            except Exception as e:
                mesg = f'Error during http {meth} - {str(e)}'
                raise s_exc.StormRuntimeError(mesg=mesg, headers=headers, json=json, body=body, params=params) from None

@s_stormtypes.registry.registerType
class HttpResp(s_stormtypes.Prim):
    '''
    Implements the Storm API for a HTTP response.
    '''
    _storm_locals = (
        {'name': 'code', 'desc': 'The HTTP status code.', 'type': 'int', },
        {'name': 'body', 'desc': 'The raw HTTP response body as bytes.', 'type': 'bytes', },
        {'name': 'headers', 'type': 'dict', 'desc': 'The HTTP Response headers.'},
        {'name': 'json', 'desc': 'Get the JSON deserialized response.',
            'type': {'type': 'function', '_funcname': '_httpRespJson',
                     'returns': {'type': 'prim'}
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

    def getObjLocals(self):
        return {
            'json': self._httpRespJson,
        }

    async def _httpRespJson(self):
        return json.loads(self.valu.get('body'))
