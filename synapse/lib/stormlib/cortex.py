import asyncio
import logging

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

class HttpApi(s_stormtypes.StormType):
    _storm_typename = 'http:api'
    _storm_locals = ()

    def __init__(self, runt, info):
        s_stormtypes.StormType.__init__(self)
        self.runt = runt
        self.info = info

    # mostly exists for getter / setter plumbing...
    # handle dynamically updating ( require admin )
    # * path
    # * runas
    # * owner
    # * methods ($hapi.methods.get = ${})

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

    def __init__(self, runt, info, hreq):
        s_stormtypes.StormType.__init__(self)
        self.replied = False
        self.runt = runt
        self.info = info
        self.hreq = hreq

    def getObjLocals(self):
        return {
            # 'api': <http:api>,
            'argv': (), # any wild globs from the endpoint parsing
        }

    async def _derefGet(self, name):
        # TODO
        # headers
        # params ( dynamically parse / cache URL params and form params )
        # json ( dynamically deserialize / cache JSON body )
        # session (not MVP can delay) - $request.session.get() / set()

    async def reply(self, code, body, headers=None):

        if self.replied:
            raise s_exc.BadArg()

        self.replied = True

        code = s_stormtypes.toint(code)
        body = s_stormtypes.toprim(body)

        headers = s_stormtypes.toprim(headers)
        if headers is None:
            headers = {}

        if not isinstance(headers, dict):
            raise s_exc.BadArg()

        for name, valu in headers.items():
            self.hreq.set_header(name, valu)

        if isinstance(body, bytes):
            self.hreq.set_status(code)
            self.hreq.write(body)
            await self.hreq.flush()
            return

        if isinstance(body, str):
            self.hreq.set_status(code)
            self.hreq.write(body.encode())
            await self.hreq.flush()
            return

        self.hreq.set_status(code)
        self.hreq.set_header('Content-Type', 'application/json')
        self.hreq.write(json.dumps(body))
        await self.hreq.flush()

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
            'get': self.getHttpApi,
            'list': self.listHttpApis,
        }

    async def addHttpApi(self, path):
        # check for admin perms ( for add/del and list )
        adef = {
            'path': path,
            'view': self.runt.snap.view.iden,
            'runas': 'owner',
            'owner': self.runt.user.iden,
            'methods': {},
            'authenticated': True,
        }

        adef = await self.runt.snap.view.core.addHttpExtApi(adef)
        return HttpApi(self.runt, adef)
