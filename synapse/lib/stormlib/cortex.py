import json
import asyncio
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)


stormcds = [
    {
        'name': 'httpapi.ext.list',
        'descr': 'List Custom HTTP API endpoints',
        'cmdargs': (),
        'storm': '''
        $apis = $lib.cortex.httpapi.list()
        if $apis {
            $header = 'order iden                             owner                auth  runas  path'
            $lib.print($header)
            for ($n, $api) in $lib.iters.enum($apis) {
                // $lib.print($api)
                $user = $lib.auth.users.get($api.owner)
                $user = $user.name
                $auth = `{$api.authenticated}`
                $order = `{$n}`
                $mesg=`{$order.ljust(5)} {$api.iden} {$user.ljust(20)} {$auth.ljust(5)} {$api.runas.ljust(6)} {$api.path}`
                $lib.print($mesg)
            }
        } else {
            $lib.print('No Custom HTTP API endpoints are registered.')
        }
        '''
    },
    {
        'name': 'httpapi.ext.stat',
        'descr': 'Get details for a Custom HTTP API endpoint.',
        'cmdargs': (
            ('iden', {'help': 'The iden of the endpoint to inspect', 'type': 'str'}),
        ),
        'storm': '''
        // TODO Resolve the $api by a partial iden
        $api = $lib.cortex.httpapi.get($cmdopts.iden)
        $lib.print(`Iden: {$api.iden}`)
        $lib.print(`Path: {$api.path}`)
        $user = $lib.auth.users.get($api.owner)
        $lib.print(`Owner: {$user.name} ({$api.owner})`)
        $lib.print(`Runas: {$api.runas}`)
        $lib.print(`Authenticated: {$api.authenticated}`)
        $lib.print(`Name: {$api.name}`)
        $lib.print(`Description: {$api.desc}`)

        $perms = $api.perms
        if $perms {
            for $pdef in $perms {
                $perm = $pdef.perm
                $default = $pdef.default
            }
            // pass
        } else {
            $lib.print('No user permissions are required to run this handler.')
        }
        $methods = $api.methods
        if $methods {
            for ($meth, $storm) in $methods {
                $lib.print(`Method: {$meth.upper()}`)
                $lib.print($storm)
            }
        } else {
            $lib.print('No HTTP Methods are set for the handler.')
        }
        '''
    },
    {
        'name': 'httpapi.ext.index',
        # TODO Give detailed example
        'desc': 'Set the index of a Custom HTTP API endpoint.',
        'cmdargs': (
            ('iden', {'help': 'The iden of the endpoint to move.', 'type': 'str'}),
            ('index', {'help': 'The order value to move the endpoint too.', 'type': 'int'}),
        ),
        'storm': '''// TODO Resolve the $api by a partial iden
        $api = $lib.cortex.httpapi.get($cmdopts.iden)
        $index = $lib.cortex.httpapi.index($api.iden, $cmdopts.index)
        $lib.print(`Set HTTP API {$api.iden} to index {$index}`)
        '''
    }
]

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
            # 'view': self._storView,  # TODO -> Implement .view
            'runas': self._storRunas,
            'owner': self._storOwner,
            'perms': self._storPerms,
            'authenticated': self._storAuthenticated,
        })

        self.gtors.update({
            'name': self._gtorName,
            'desc': self._gtorDesc,
            'path': self._gtorPath,
            # 'view': self._gtorView,  # TODO -> Implement .view
            'runas': self._gtorRunas,
            'owner': self._gtorOwner,
            'perms': self._gtorPerms,
            'authenticated': self._gtorAuthenticated,
        })

        self.ctors.update({
            'methods': self._ctorMethods
        })

        self.locls.update({
            'iden': self.iden,
        })

    # def getObjLocals(self):
    #     return {
    #         'pack': self._methPack,
    #     }

    def value(self):
        return self.info

    # async def _methPack(self):
    #     # TODO Return a copy of the data from the cortex!
    #     return self.info

    def _ctorMethods(self, path):
        return HttpApiMethods(self)

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
        return self.info.get('runas')

    async def _storOwner(self, owner):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        owner = await s_stormtypes.tostr(owner)
        # TODO - Confirm the owner is a user
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'owner', owner)
        return True

    async def _gtorOwner(self):
        # TODO Return a s_stormtypes.User object!
        return self.info.get('owner')

    async def _storPerms(self, perms):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        perms = await s_stormtypes.toprim(perms)
        pdefs = []
        for pdef in perms:
            if isinstance(pdef, str):
                if pdef.startswith('!'):
                    raise s_exc.BadArg(mesg=f'Permission assignment must not start with a !, got {perm}')
                parts = pdef.split('.')
                pdef = {'perm': parts, 'default': False}

            pdefs.append(pdef)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'perms', pdefs)
        return True

    async def _gtorPerms(self):
        return self.info.get('perms')

    async def _storAuthenticated(self, authenticated):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        authenticated = await s_stormtypes.tobool(authenticated)
        self.info = await self.runt.snap.core.modHttpExtApi(self.iden, 'authenticated', authenticated)
        return True

    async def _gtorAuthenticated(self):
        return self.info.get('authenticated')

@s_stormtypes.registry.registerType
class HttpApiMethods(s_stormtypes.StormType):
    '''
    '''
    _storm_typename = 'http:api:methods'
    _storm_locals = ()

    def __init__(self, httpapi: HttpApi):
        s_stormtypes.StormType.__init__(self)
        self.httpapi = httpapi

        self.gtors.update({
            'get': self._gtorMethGet,
            'head': self._gtorMethHead,
            'post': self._gtorMethPost,
            'put': self._gtorMethPut,
            'delete': self._gtorMethDelete,
            'patch': self._gtorMethPatch,
            'options': self._gtorMethOptions,
        })

        self.stors.update({
            'get': self._storMethGet,
            'head': self._storMethHead,
            'post': self._storMethPost,
            'put': self._storMethPut,
            'delete': self._storMethDelete,
            'patch': self._storMethPatch,
            'options': self._storMethOptions,
        })

    async def _storMethFunc(self, meth, query):
        query = await s_stormtypes.tostr(query)
        query = query.strip()
        methods = self.httpapi.info.get('methods')
        methods[meth] = query
        self.httpapi.info = await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'methods', methods)
        return True

    async def _storMethGet(self, query):
        return await self._storMethFunc('get', query)

    async def _storMethHead(self, query):
        return await self._storMethFunc('head', query)

    async def _storMethPost(self, query):
        return await self._storMethFunc('post', query)

    async def _storMethPut(self, query):
        return await self._storMethFunc('put', query)

    async def _storMethPatch(self, query):
        return await self._storMethFunc('patch', query)

    async def _storMethOptions(self, query):
        return await self._storMethFunc('options', query)

    async def _storMethDelete(self, query):
        return await self._storMethFunc('delete', query)

    async def _gtorMethGet(self):
        return self.httpapi.info.get('methods').get('get')

    async def _gtorMethHead(self):
        return self.httpapi.info.get('methods').get('head')

    async def _gtorMethPost(self):
        return self.httpapi.info.get('methods').get('post')

    async def _gtorMethPut(self):
        return self.httpapi.info.get('methods').get('put')

    async def _gtorMethDelete(self):
        return self.httpapi.info.get('methods').get('delete')

    async def _gtorMethPatch(self):
        return self.httpapi.info.get('methods').get('patch')

    async def _gtorMethOptions(self):
        return self.httpapi.info.get('methods').get('options')

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

    def __init__(self, runt, rnfo):
        s_stormtypes.StormType.__init__(self)

        self.replied = False

        self.runt = runt
        self.rnfo = rnfo
        self.rcode = None
        self.rbody = None
        self.rheaders = None
        self.locls.update(self.getObjLocals())

        # Constants for a given instance
        self.locls.update({
            'args': self.rnfo.get('args'),
            'body': self.rnfo.get('body'),
            'method': self.rnfo.get('method'),
            'headers': self.rnfo.get('headers'),
            'params': self.rnfo.get('params'),
            'remote_ip': self.rnfo.get('remote_ip'),
            'uri': self.rnfo.get('uri'),
            'path': self.rnfo.get('path'),
        })

        self.gtors.update({
            'api': self._gtorApi,  # Not a ctor since the adef retrieval is an async process
            'json': self._gtorJson,
        })

    def getObjLocals(self):
        return {
            'sendcode': self._methSendCode,
            'sendheaders': self._methSendHeaders,
            'sendbody': self._methSendBody,
            'reply': self._methReply,
        }

    async def _gtorApi(self):
        adef = self.runt.snap.core.getHttpExtApiByIden(self.rnfo.get('iden'))
        return HttpApi(self.runt, adef)

    async def _gtorJson(self):
        try:
            return json.loads(self.rnfo.get('body'))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise s_exc.StormRuntimeError(mesg='Failed to decode request body as JSON: {e}') from None

    async def _methSendCode(self, code):
        code = await s_stormtypes.toint(code)
        await self.runt.snap.fire('http:resp:code', code=code)

    async def _methSendHeaders(self, headers):
        headers = await s_stormtypes.toprim(headers)
        if not isinstance(headers, dict):
            typ = await s_stormtypes.totype(headers)
            raise s_exc.BadArg(mesg=f'HTTP Response headers must be a dictionary, got {typ}')
        await self.runt.snap.fire('http:resp:headers', headers=headers)

    async def _methSendBody(self, body):
        body = await s_stormtypes.toprim(body)
        if not isinstance(body, bytes):
            typ = await s_stormtypes.totype(body)
            raise s_exc.BadArg(mesg=f'HTTP Response body must be bytes, got {typ}.')
        await self.runt.snap.fire('http:resp:body', body=body)

    # Convenience method
    async def _methReply(self, code, headers=None, body=None):
        if self.replied:
            raise s_exc.BadArg(mesg='Response.reply() has already been called.')

        headers = await s_stormtypes.toprim(headers)
        if headers is None:
            headers = {}

        body = await s_stormtypes.toprim(body)
        if body is not None and not isinstance(body, bytes):
            # TODO - discuss strict use
            # s_common.reqJsonSafeStrict(body)
            body = json.dumps(body, sort_keys=True).encode('utf-8', 'surrogatepass')
            headers['Content-Type'] = 'application/json'
            headers['Content-Length'] = len(body)

        await self._methSendCode(code)

        if headers:
            await self._methSendHeaders(headers)

        if body is not None:
            await self._methSendBody(body)

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
            'get': self.getHttpApi,
            'list': self.listHttpApis,
            'index': self.setHttpApiIndx,
            'response': self.makeHttpResponse,
        }

    async def makeHttpResponse(self, requestinfo):
        requestinfo = await s_stormtypes.toprim(requestinfo)
        return HttpReq(self.runt, requestinfo)

    async def getHttpApi(self, iden):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.core.getHttpExtApiByIden(iden)

    async def listHttpApis(self):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        adefs = await self.runt.snap.core.getHttpExtApis()
        apis = [HttpApi(self.runt, adef) for adef in adefs]
        return apis

    async def addHttpApi(self, path, name='', desc='', runas='owner', authenticated=True):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'add'))

        path = await s_stormtypes.tostr(path)
        name = await s_stormtypes.tostr(name)
        desc = await s_stormtypes.tostr(desc)
        runas = await s_stormtypes.tostr(runas)
        authenticated = await s_stormtypes.tobool(authenticated)

        # TODO: Discuss to confirm the following behavior:
        # Since the path value may be a regular expression, and a user can easily
        # re-order the endpoints values, we just accept whatever path is provided.
        # This removes the burden of resolving path conflicts from Synapse and onto
        # the Cortex administrator which are performing the management of their
        # custom HTTP API endpoints.

        adef = {
            'path': path,
            'view': self.runt.snap.view.iden,
            'runas': runas,
            'owner': self.runt.user.iden,
            'methods': {},
            'authenticated': authenticated,
            'name': name,
            'desc': desc,
        }

        adef = await self.runt.snap.core.addHttpExtApi(adef)
        return HttpApi(self.runt, adef)

    async def delHttpApi(self, iden):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'del'))
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.view.core.delHttpExtApi(iden)

    async def setHttpApiIndx(self, iden, index=0):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'mod'))
        iden = await s_stormtypes.tostr(iden)
        index = await s_stormtypes.toint(index)
        if index < 0:
            raise s_exc.BadArg(mesg=f'indx must be greater than or equal to 0; got {index}')
        return await self.runt.snap.view.core.setHttpApiIndx(iden, index)
