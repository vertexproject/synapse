import json

import aiohttp

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

@s_stormtypes.registry.registerLib
class LibHttp(s_stormtypes.Lib):
    '''
    A Storm Library exposing an HTTP client API.
    '''

    _storm_lib_path = ('inet', 'http')

    def getObjLocals(self):
        return {
            'get': self._httpEasyGet,
            'post': self._httpPost,
            'request': self._httpRequest,
        }

    async def _httpEasyGet(self, url, headers=None, ssl_verify=True, params=None):
        '''
        Get the contents of a given URL.

        Args:
            url (str): The URL to retrieve.

            headers (dict): HTTP headers to send with the request.

            ssl_verify (bool): Perform SSL/TLS verification. Defaults to true.

            params (dict): Optional parameters which may be passed to the request.

        Returns:
            HttpResp: A Storm HttpResp object.
        '''
        return await self._httpRequest('get', url, headers=headers, ssl_verify=ssl_verify, params=params)

    async def _httpPost(self, url, headers=None, json=None, body=None, ssl_verify=True, params=None):
        '''
        Post data to a given URL.

        Args:
            url (str): The URL to post to.

            headers (dict): HTTP headers to send with the request.

            json: The data to post, as JSON object.

            body: The data to post, as binary object.

            ssl_verify (bool): Perform SSL/TLS verification. Defaults to true.

            params (dict): Optional parameters which may be passed to the request.

        Returns:
            HttpResp: A Storm HttpResp object.
        '''
        return await self._httpRequest('POST', url, headers=headers, json=json,
                                       body=body, ssl_verify=ssl_verify, params=params)

    async def _httpRequest(self, meth, url, headers=None, json=None, body=None, ssl_verify=True,
                           params=None):
        '''
        Make an HTTP request using the given HTTP method to the url.

        Args:
            meth (str): The HTTP method. (ex. PUT)

            url (str): The URL to post to.

            headers (dict): HTTP headers to send with the request.

            json: The data to post, as JSON object.

            body: The data to post, as binary object.

            ssl_verify (bool): Perform SSL/TLS verification. Defaults to true.

            params (dict): Optional parameters which may be passed to the request.

        Returns:
            HttpResp: A Storm HttpResp object.
        '''

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

        async with aiohttp.ClientSession() as sess:
            try:
                async with sess.request(meth, url, headers=headers, json=json, data=body, **kwargs) as resp:
                    info = {
                        'code': resp.status,
                        'body': await resp.content.read()
                    }
                    return HttpResp(info)
            except (TypeError, ValueError) as e:
                mesg = f'Error during http {meth} - {str(e)}'
                raise s_exc.StormRuntimeError(mesg=mesg, headers=headers, json=json, body=body, params=params) from None

@s_stormtypes.registry.registerType
class HttpResp(s_stormtypes.StormType):

    def __init__(self, locls):
        s_stormtypes.StormType.__init__(self)
        self.locls.update(locls)
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'json': self._httpRespJson,
        }

    async def _httpRespJson(self):
        body = self.locls.get('body')
        return json.loads(body)
