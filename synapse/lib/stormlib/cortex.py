import json
import asyncio
import logging

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)


# HttpApi ctor for .method -> HttpApiMethods getter/ setter for methods
#
# class HttpApiMethods(s_stormtypes.StormType):
#     _storm_typename = 'http:api:methods'
#     _storm_locals = ()
#
#     def __init__(self, runt, iden):
#         s_stormtypes.StormType.__init__(self)
#         self.runt = runt
#         self.iden = iden
#
#

class HttpApi(s_stormtypes.StormType):
    '''
    HTTPApi object
    '''
    _storm_typename = 'http:api'
    _storm_locals = ()

    # TODO DOCSTRING
    # TODO LOCALS

    def __init__(self, runt, info):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self.info = info
        self.iden = self.info.get('iden')

        self.stors.update({
            # General helpers
            'name': self._storName,
            'desc': self._storDesc,
            'path': self._storPath,
            'runas': self._storRunas,
            'owner': self._storOwner,
            'perms': self._storPerms,

            # Meth setters
            'get': self._storMethGet,
            # 'head': self._storMethHead,
            # 'put': self._storMethPut,
            # 'post': self._storMethPost,
            # 'patch': self._storMethPatch,
        })

        self.gtors.update({
            'name': self._gtorName,
            'desc': self._gtorDesc,
            'path': self._gtorPath,
            'runas': self._gtorRunas,
            'owner': self._gtorOwner,
            'perms': self._gtorPerms,

            # Meth setters
            'get': self._gtorMethGet,
            # 'head': self._gtorMethHead,
            # 'put': self._gtorMethPut,
            # 'post': self._gtorMethPost,
            # 'patch': self._gtorMethPatch,
        })

    def getObjLocals(self):
        return {
            'pack': self._methPack,
        }

    def value(self):
        return self.info

    async def _methPack(self):
        # TODO Return a copy of the data from the cortex!
        return self.info

    async def _storPath(self, path):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        path = await s_stormtypes.tostr(path)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'path', path)
        return True

    async def _gtorPath(self):
        return self.info.get('path')

    async def _storName(self, name):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        name = await s_stormtypes.tostr(name)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'name', name)
        return True

    async def _gtorName(self):
        return self.info.get('name')

    async def _storDesc(self, desc):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        desc = await s_stormtypes.tostr(desc)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'desc', desc)
        return True

    async def _gtorDesc(self):
        return self.info.get('desc')

    async def _storRunas(self, runas):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        runas = await s_stormtypes.tostr(runas)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'runas', runas)
        return True

    async def _gtorRunas(self):
        return self.info.get('desc')

    async def _storOwner(self, owner):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        owner = await s_stormtypes.tostr(owner)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'owner', owner)
        return True

    async def _gtorOwner(self):
        return self.info.get('owner')

    async def _storPerms(self, perms):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        perms = await s_stormtypes.toprim(perms)
        _perms = []
        for perm in perms:
            # # TODO Convert perms string into a perm value using perm helper
            # if isinstance(perm, str):
            #     perm = ...
            _perms.append(perm)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'perms', _perms)
        return True

    async def _gtorPerms(self):
        return self.info.get('perms')

    async def _storMethGet(self, query):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        query = await s_stormtypes.tostr(query)
        query = query.strip()
        methods = self.info.get('methods')
        methods['get'] = query
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'methods', methods)
        return True

    async def _gtorMethGet(self):
        return self.info.get('methods').get('get')

    # * methods ($hapi.methods.get = ${})

@s_stormtypes.registry.registerType
class HttpReq(s_stormtypes.StormType):
    '''
    Examples:

        $hapi = $lib.cortex.httpapi.add('foo/bar/baz')
        $hapi.authenticated = (false)

        $hapi.methods.get = ${
            $request.reply(200, ({"ok": true, "value": 10}))
        }

        $resquest.params.<name> ( URL params / form params )
        $resquest.json.<stuff>  ( parse body as json (cache) and deref )

        // run the authenticated query as the owner

        $hapi = $lib.cortex.httpapi.add('foo/bar/baz')
        $hapi.methods.get = ${
            $request.reply(200, ({"ok": true, "value": 10}))
        }

        // run the query as the authenticated user

        $hapi = $lib.cortex.httpapi.add('foo/(.*)/blah')
        $hapi.runas = user
        $hapi.methods.get = ${
            $request.reply(200, $lib.user.jsonstor.get($request.argv.1))
        }

        // queue an item from an anonymous API request

        $hapi = $lib.cortex.httpapi.add(`foo/{$lib.guid}`)
        $hapi.

    '''
    _storm_typename = 'http:api:request'
    _storm_locals = ()

    def __init__(self, runt, info):
        s_stormtypes.StormType.__init__(self)

        self.replied = False

        # self._code_called = False
        # self._headers_called = False

        self.runt = runt
        self.info = info
        self.rcode = None
        self.rbody = None
        self.rheaders = None
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            # 'api': <http:api>,
            # 'argv': (), # any wild globs from the endpoint parsing
            'code': self._methCode,
            'headers': self._methHeaders,
            'body': self._methBody,
            'reply': self._methReply,
        }

    async def _derefGet(self, name):
        # TODO
        # headers
        # params ( dynamically parse / cache URL params and form params )
        # json ( dynamically deserialize / cache JSON body )
        # session (not MVP can delay) - $request.session.get() / set()

        pass

    async def _methCode(self, code):
        code = await s_stormtypes.toint(code)
        await self.runt.snap.fire('http:resp:code', code=code)

    async def _methHeaders(self, headers):
        headers = await s_stormtypes.toprim(headers)
        if not isinstance(headers, dict):
            # TODO include type
            raise s_exc.BadArg(mesg=f'HTTP Response headers must be a dictionary. {type(headers)=}')
        await self.runt.snap.fire('http:resp:headers', headers=headers)

    async def _methBody(self, body, flush=True):
        body = await s_stormtypes.toprim(body)
        if not isinstance(body, bytes):
            # TODO include type
            raise s_exc.BadArg(mesg='HTTP Response body must be bytes.')
        await self.runt.snap.fire('http:resp:body', body=body, flush=flush)

    # Convenience method
    async def _methReply(self, code, headers=None, body=None):
        if self.replied:
            raise s_exc.BadArg(mesg='Response.reply() has already been called.')

        await self._methCode(code)
        await self._methHeaders(headers)
        await self._methBody(body)

        self.replied = True
        return True


@s_stormtypes.registry.registerLib
class CortexHttpApi(s_stormtypes.Lib):
    '''
    '''
    _storm_locals = ()
    _storm_lib_path = ('cortex', 'httpapi')

    def getObjLocals(self):
        return {
            'add': self.addHttpApi,
            'del': self.delHttpApi,
            # 'get': self.getHttpApi,
            'list': self.listHttpApis,
            'response': self.makeHttpResponse,
        }

    async def makeHttpResponse(self, requestinfo):
        requestinfo = await s_stormtypes.toprim(requestinfo)
        return HttpReq(self.runt, requestinfo)

    # async def getHttpApi(self, iden):
    #     s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
    #     iden = await s_stormtypes.tostr(iden)
    #     adefs = await self.runt.snap.core.getHtp()
    #     apis = [HttpApi(self.runt, adef) for adef in adefs]
    #     return apis

    async def listHttpApis(self):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        adefs = await self.runt.snap.core.getHttpExtApis()
        apis = [HttpApi(self.runt, adef) for adef in adefs]
        return apis

    async def addHttpApi(self, path):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'add'))

        path = await s_stormtypes.tostr(path)

        # check for admin perms ( for add/del and list )
        adef = {
            'path': path,
            'view': self.runt.snap.view.iden,
            'runas': 'owner',
            'owner': self.runt.user.iden,
            'methods': {},
            'authenticated': True,
        }

        adef = await self.runt.snap.core.addHttpExtApi(adef)
        return HttpApi(self.runt, adef)

    async def delHttpApi(self, iden):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'del'))
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.view.core.delHttpExtApi(iden)
