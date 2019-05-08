import json
import asyncio

import aiohttp

import synapse.common as s_common
import synapse.lib.stormtypes as s_stormtypes

class LibHttp(s_stormtypes.Lib):
    '''
    HTTP client API for STORM
    '''

    def addLibFuncs(self):
        self.locls.update({
            'get': self._httpEasyGet,
            #'post':
            #'session':
        })

    async def _httpEasyGet(self, url):
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url) as resp:
                info = {
                    'code': resp.status,
                    'body': await resp.content.read(),
                }
                return HttpResp(info)

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
