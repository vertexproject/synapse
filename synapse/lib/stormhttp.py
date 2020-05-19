import json

import aiohttp

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

class LibHttp(s_stormtypes.Lib):
    '''
    HTTP client API for STORM
    '''

    def addLibFuncs(self):
        self.locls.update({
            'get': self._httpEasyGet,
            'post': self._httpPost,
            # 'session':
        })

    async def _httpEasyGet(self, url, headers=None, ssl_verify=True):

        url = await s_stormtypes.toprim(url)
        headers = await s_stormtypes.toprim(headers)

        kwargs = {}
        if not ssl_verify:
            kwargs['ssl'] = False
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, headers=headers, **kwargs) as resp:
                info = {
                    'code': resp.status,
                    'body': await resp.content.read(),
                }
                return HttpResp(info)

    async def _httpPost(self, url, headers=None, json=None, body=None, ssl_verify=True):

        url = await s_stormtypes.toprim(url)
        json = await s_stormtypes.toprim(json)
        body = await s_stormtypes.toprim(body)
        headers = await s_stormtypes.toprim(headers)

        kwargs = {}
        if not ssl_verify:
            kwargs['ssl'] = False

        async with aiohttp.ClientSession() as sess:
            try:
                async with sess.post(url, headers=headers, json=json, data=body, **kwargs) as resp:
                    info = {
                        'code': resp.status,
                        'body': await resp.content.read()
                    }
                    return HttpResp(info)
            except ValueError as e:
                mesg = f'Error during http post - {str(e)}'
                raise s_exc.StormRuntimeError(mesg=mesg, headers=headers, json=json, body=body) from None

class HttpResp(s_stormtypes.StormType):

    def __init__(self, locls):
        s_stormtypes.StormType.__init__(self)
        self.locls.update(locls)
        self.locls.update({
            'json': self._httpRespJson,
        })

    async def _httpRespJson(self):
        body = self.locls.get('body')
        return json.loads(body)
