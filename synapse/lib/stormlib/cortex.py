import copy
import json
import logging

import synapse.exc as s_exc

import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)


stormcds = [
    {
        'name': 'cortex.httpapi.list',
        'descr': 'List Extended HTTP API endpoints',
        'cmdargs': (),
        'storm': '''
        $apis = $lib.cortex.httpapi.list()
        if $apis {
            $header = 'order iden                             owner                auth  runas  path'
            $lib.print($header)
            for ($n, $api) in $lib.iters.enum($apis) {
                try {
                    $user = $api.owner.name
                } catch NoSuchUser as err {
                    $user = `No user found ({$err.info.user})`
                }
                $auth = `{$api.authenticated}`
                $order = `{$n}`
                $mesg=`{$order.ljust(5)} {$api.iden} {$user.ljust(20)} {$auth.ljust(5)} {$api.runas.ljust(6)} {$api.path}`
                $lib.print($mesg)
            }
        } else {
            $lib.print('No Extended HTTP API endpoints are registered.')
        }
        '''
    },
    {
        'name': 'cortex.httpapi.stat',
        'descr': 'Get details for a Extended HTTP API endpoint.',
        'cmdargs': (
            ('iden', {'help': 'The iden of the endpoint to inspect', 'type': 'str'}),
        ),
        'storm': '''
        // TODO Resolve the $api by a partial iden
        $api = $lib.cortex.httpapi.get($cmdopts.iden)

        $lib.print(`Iden: {$api.iden}`)
        $lib.print(`Path: {$api.path}`)
        try {
            $lib.print(`Owner: {$api.owner.name} ({$api.owner.iden})`)
        } catch NoSuchUser as err {
            $lib.print(`Owner: No user found ({$err.info.user})`)
        }
        $lib.print(`Runas: {$api.runas}`)
        try {
            $lib.print(`View: {$api.view.get(name)} ({$api.view.iden})`)
        } catch NoSuchView as err {
            $lib.print(`View: No view found ({$err.info.iden})`)
        }
        $lib.print(`Readonly: {$api.readonly}`)
        $lib.print(`Authenticated: {$api.authenticated}`)
        $lib.print(`Name: {$api.name}`)
        $lib.print(`Description: {$api.desc}`)
        $lib.print('')
        $perms = $api.perms
        if $perms {
            $lib.print('The following user permissions are required to run this HTTP API endpoint:')
            for $pdef in $perms {
                $perm = $pdef.perm
                $default = $pdef.default
                $valu = $lib.str.join('.', $perm)
                if $default {
                    $valu = `{$valu}, default: true`
                }
                $lib.print($valu)
            }
            $lib.print('')
        } else {
            $lib.print('No user permissions are required to run this HTTP API endpoint.')
        }
        $methods = $api.methods
        if $methods {
            $lib.print('The handler defines the following HTTP methods:')
            for ($meth, $storm) in $methods {
                $lib.print(`Method: {$meth.upper()}`)
                $lib.print($storm)
            }
            $lib.print('')
        } else {
            $lib.print('No HTTP Methods are set for the handler.')
        }
        $vars = $api.vars
        if $vars {
            $lib.print('The handler has the following runtime variables set:')
            for ($key, $valu) in $vars {
                $lib.print(`{$key.ljust(16)} => {$valu}`)
            }
            $lib.print('')
        } else {
            $lib.print('No vars are set for the handler.')
        }
        '''
    },
    {
        'name': 'cortex.httpapi.index',
        # TODO Give detailed example
        'desc': 'Set the index of a Extended HTTP API endpoint.',
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

def _normPermString(perm):
    if perm.startswith('!'):
        raise s_exc.BadArg(mesg=f'Permission assignment must not start with a !, got {perm}')
    parts = perm.split('.')
    pdef = {'perm': parts, 'default': False}
    return pdef

@s_stormtypes.registry.registerType
class HttpApi(s_stormtypes.StormType):
    '''
    Extended HTTPApi object
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
        # Perms comes in as a tuple - convert it to a list to we can have a mutable object
        self.info['perms'] = list(self.info.get('perms'))

        self.stors.update({
            # General helpers
            'name': self._storName,
            'desc': self._storDesc,
            'path': self._storPath,
            'vars': self._storVars,
            'view': self._storView,
            'runas': self._storRunas,
            'owner': self._storOwner,
            'perms': self._storPerms,
            'readonly': self._storReadonly,
            'authenticated': self._storAuthenticated,
        })

        self.gtors.update({
            'name': self._gtorName,
            'desc': self._gtorDesc,
            'path': self._gtorPath,
            'view': self._gtorView,
            'runas': self._gtorRunas,
            'owner': self._gtorOwner,
            # 'perms': self._gtorPerms,
            'readonly': self._gtorReadonly,
            'authenticated': self._gtorAuthenticated,
        })

        self.ctors.update({
            'vars': self._ctorVars,
            'perms': self._ctorPerms,
            'methods': self._ctorMethods
        })

        # constants
        self.locls.update(self.getObjLocals())
        self.locls.update({
            'iden': self.iden,
        })

    def getObjLocals(self):
        return {
            'pack': self._methPack,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPack(self):
        return copy.deepcopy(self.info)

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorMethods(self, path=None):
        return HttpApiMethods(self)

    async def _storPath(self, path):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        path = await s_stormtypes.tostr(path)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'path', path)
        self.info['path'] = path

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorPath(self):
        return self.info.get('path')

    async def _storName(self, name):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        name = await s_stormtypes.tostr(name)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'name', name)
        self.info['name'] = name

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorView(self):
        iden = self.info.get('view')
        vdef = await self.runt.snap.core.getViewDef(iden)
        if vdef is None:
            raise s_exc.NoSuchView(mesg=f'No view with {iden=}', iden=iden)
        return s_stormtypes.View(self.runt, vdef, path=self.path)

    async def _storVars(self, varz):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        varz = await s_stormtypes.toprim(varz)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'vars', varz)
        _varz = self.info.get('vars')
        _varz.clear()
        _varz.update(**adef.get('vars'))

    async def _storView(self, iden):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        if isinstance(iden, s_stormtypes.View):
            view = iden.value().get('iden')
        else:
            view = await s_stormtypes.tostr(iden)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'view', view)
        self.info['view'] = view

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorName(self):
        return self.info.get('name')

    async def _storDesc(self, desc):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        desc = await s_stormtypes.tostr(desc)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'desc', desc)
        self.info['desc'] = desc

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorDesc(self):
        return self.info.get('desc')

    async def _storRunas(self, runas):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        runas = await s_stormtypes.tostr(runas)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'runas', runas)
        self.info['runas'] = runas

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorRunas(self):
        return self.info.get('runas')

    async def _storReadonly(self, readonly):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        readonly = await s_stormtypes.tobool(readonly)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'readonly', readonly)
        self.info['readonly'] = readonly

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorVars(self, path=None):
        return HttpApiVars(self, path=path)

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorReadonly(self):
        return self.info.get('readonly')

    async def _storOwner(self, owner):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        if isinstance(owner, s_stormtypes.User):
            info = await owner.value()
            owner = info.get('iden')
        else:
            owner = await s_stormtypes.tostr(owner)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'owner', owner)
        self.info['owner'] = owner

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorOwner(self):
        iden = self.info.get('owner')
        udef = await self.runt.snap.core.getUserDef(iden)
        if udef is None:
            raise s_exc.NoSuchUser(mesg=f'HTTP API owner does not exist {iden}', user=iden)
        return s_stormtypes.User(self.runt, udef['iden'])

    async def _storPerms(self, perms):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        perms = await s_stormtypes.toprim(perms)
        pdefs = []
        for pdef in perms:
            if isinstance(pdef, str):
                pdef = _normPermString(pdef)
            pdefs.append(pdef)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'perms', pdefs)
        self.info['perms'].clear()
        self.info['perms'].extend(pdefs)

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorPerms(self, path):
        return HttpPermsList(self, path)

    async def _storAuthenticated(self, authenticated):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        authenticated = await s_stormtypes.tobool(authenticated)
        await self.runt.snap.core.modHttpExtApi(self.iden, 'authenticated', authenticated)
        self.info['authenticated'] = authenticated

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorAuthenticated(self):
        return self.info.get('authenticated')

@s_stormtypes.registry.registerType
class HttpApiMethods(s_stormtypes.Prim):
    '''
    Accessor dictionary for getting and setting http:api methods.
    '''
    _storm_typename = 'http:api:methods'
    _storm_locals = ()

    def __init__(self, httpapi: HttpApi):
        s_stormtypes.Prim.__init__(self, httpapi.info.get('methods'))
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

    async def iter(self):
        for k, v in list(self.valu.items()):
            yield (k, v)

    async def _storMethFunc(self, meth, query):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        meth = await s_stormtypes.tostr(meth)
        methods = self.valu.copy()

        if query is s_stormtypes.undef:
            methods.pop(meth, None)
            await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'methods', methods)
            self.valu.pop(meth, None)
        else:
            query = await s_stormtypes.tostr(query)
            query = query.strip()

            # Ensure our query can be parsed.
            await self.httpapi.runt.snap.core.getStormQuery(query)

            methods[meth] = query
            await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'methods', methods)
            self.valu[meth] = query

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

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorMethGet(self):
        return self.valu.get('get')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorMethHead(self):
        return self.valu.get('head')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorMethPost(self):
        return self.valu.get('post')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorMethPut(self):
        return self.valu.get('put')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorMethDelete(self):
        return self.valu.get('delete')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorMethPatch(self):
        return self.valu.get('patch')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorMethOptions(self):
        return self.valu.get('options')

@s_stormtypes.registry.registerType
class HttpHeaderDict(s_stormtypes.Dict):
    '''
    Immutable lowercase key access dictionary for HTTP request headers.
    '''
    _storm_typename = 'http:request:headers'
    _storm_locals = ()

    _ismutable = False

    # TODO DOCSTRING

    async def setitem(self, name, valu):
        mesg = f'{self._storm_typename} may not be modified by the runtime'
        raise s_exc.StormRuntimeError(mesg=mesg, name=name)

    async def deref(self, name):
        name = await s_stormtypes.tostr(name)
        name = name.lower()
        return self.valu.get(name)

@s_stormtypes.registry.registerType
class HttpPermsList(s_stormtypes.List):
    _storm_typename = 'http:api:perms'
    _storm_locals = ()

    _ismutable = False

    def __init__(self, httpapi, path=None):
        s_stormtypes.Prim.__init__(self, httpapi.info.get('perms'))
        self.httpapi = httpapi
        self.locls.update(self.getObjLocals())

    async def setitem(self, name, valu):
        indx = await s_stormtypes.toint(name)
        pdefs = self.valu.copy()
        if valu is s_stormtypes.undef:
            try:
                pdefs.pop(indx)
            except IndexError:
                pass
            else:
                await self.httpapi._storPerms(pdefs)
        else:
            pdef = await s_stormtypes.toprim(valu)
            if isinstance(pdef, str):
                pdef = _normPermString(pdef)
            pdefs[indx] = pdef
            await self.httpapi._storPerms(pdefs)

    async def _methListAppend(self, valu):
        pdef = await s_stormtypes.toprim(valu)
        if isinstance(pdef, str):
            pdef = _normPermString(pdef)
        pdefs = self.valu.copy()
        pdefs.append(pdef)
        await self.httpapi._storPerms(pdefs)

    async def _methListHas(self, valu):
        pdef = await s_stormtypes.toprim(valu)
        if isinstance(pdef, str):
            pdef = _normPermString(pdef)
        return await s_stormtypes.List._methListHas(self, pdef)

    async def _methListReverse(self):
        pdefs = self.valu.copy()
        pdefs.reverse()
        await self.httpapi._storPerms(pdefs)

    async def _methListPop(self):
        pdefs = self.valu.copy()
        try:
            valu = pdefs.pop()
        except IndexError:
            mesg = 'The permissions list is empty. Nothing to pop.'
            raise s_exc.StormRuntimeError(mesg=mesg)
        else:
            await self.httpapi._storPerms(pdefs)
            return valu

    async def _methListSort(self, reverse=False):
        raise s_exc.StormRuntimeError(mesg=f'{self._storm_typename} does not support sorting.')

    async def _methListExtend(self, valu):
        pdefs = self.valu.copy()
        async for pdef in s_stormtypes.toiter(valu):
            pdef = await s_stormtypes.toprim(pdef)
            if isinstance(pdef, str):
                pdef = _normPermString(pdef)
            pdefs.append(pdef)
        await self.httpapi._storPerms(pdefs)


@s_stormtypes.registry.registerType
class HttpApiVars(s_stormtypes.Dict):
    '''
    Accessor dictionary for getting and setting http:api vars.
    '''
    _storm_typename = 'http:api:vars'
    _storm_locals = ()

    _ismutable = False

    # TODO DOCSTRING
    def __init__(self, httpapi, path=None):
        s_stormtypes.Dict.__init__(self, httpapi.info.get('vars'), path=path)
        self.httpapi = httpapi

    async def setitem(self, name, valu):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        name = await s_stormtypes.tostr(name)

        varz = self.valu.copy()
        if valu is s_stormtypes.undef:
            varz.pop(name, None)
            await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'vars', varz)
            self.valu.pop(name, None)
        else:
            valu = await s_stormtypes.toprim(valu)
            varz[name] = valu
            await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'vars', varz)
            self.valu[name] = valu

@s_stormtypes.registry.registerType
class HttpReq(s_stormtypes.StormType):
    '''
    Extended HTTP API Request object.
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
            'params': self.rnfo.get('params'),
            'remote_ip': self.rnfo.get('remote_ip'),
            'uri': self.rnfo.get('uri'),
            'path': self.rnfo.get('path'),
            'user': self.rnfo.get('user'),
        })

        self.gtors.update({
            'api': self._gtorApi,  # Not a ctor since the adef retrieval is an async process
            'json': self._gtorJson,
        })

        self.ctors.update({
            'headers': self._ctorHeaders,
        })

    def getObjLocals(self):
        return {
            'sendcode': self._methSendCode,
            'sendheaders': self._methSendHeaders,
            'sendbody': self._methSendBody,
            'reply': self._methReply,
        }

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorHeaders(self, path=None):
        headers = self.rnfo.get('headers')
        return HttpHeaderDict(valu=headers, path=path)

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorApi(self):
        # FIXME: Permissions checks in gtors do not work.
        # s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        adef = await self.runt.snap.core.getHttpExtApi(self.rnfo.get('iden'))
        return HttpApi(self.runt, adef)

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorJson(self):
        try:
            return json.loads(self.rnfo.get('body'))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise s_exc.StormRuntimeError(mesg='Failed to decode request body as JSON: {e}') from None

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSendCode(self, code):
        code = await s_stormtypes.toint(code)
        await self.runt.snap.fire('http:resp:code', code=code)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSendHeaders(self, headers):
        headers = await s_stormtypes.toprim(headers)
        if not isinstance(headers, dict):
            typ = await s_stormtypes.totype(headers)
            raise s_exc.BadArg(mesg=f'HTTP Response headers must be a dictionary, got {typ}.')
        await self.runt.snap.fire('http:resp:headers', headers=headers)

    @s_stormtypes.stormfunc(readonly=True)
    async def _methSendBody(self, body):
        body = await s_stormtypes.toprim(body)
        if not isinstance(body, bytes):
            typ = await s_stormtypes.totype(body)
            raise s_exc.BadArg(mesg=f'HTTP Response body must be bytes, got {typ}.')
        await self.runt.snap.fire('http:resp:body', body=body)

    # Convenience method
    @s_stormtypes.stormfunc(readonly=True)
    async def _methReply(self, code, headers=None, body=s_stormtypes.undef):
        if self.replied:
            raise s_exc.BadArg(mesg='Response.reply() has already been call ed.')

        headers = await s_stormtypes.toprim(headers)
        if headers is None:
            headers = {}

        if body is not s_stormtypes.undef:
            if not isinstance(body, bytes):
                body = await s_stormtypes.toprim(body)
                body = json.dumps(body).encode('utf-8', 'surrogatepass')
                headers['Content-Type'] = 'application/json'
                headers['Content-Length'] = len(body)

        await self._methSendCode(code)

        if headers:
            await self._methSendHeaders(headers)

        if body is not s_stormtypes.undef:
            await self._methSendBody(body)

        self.replied = True
        return True

@s_stormtypes.registry.registerLib
class CortexHttpApi(s_stormtypes.Lib):
    '''
    Library for interacting with the Extended HTTP API.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': '''
        Add an Extended HTTP API endpoint to the Cortex.

        This can be used to add an API endpoint which will be resolved under
        the API path "/api/ext/".  New API endpoints objects are appended to
        a list of APIs to resolve in order.

        Notes:
            The Cortex does not make any attempt to do any inspection of path values which may conflict between one
            another. This is because the paths for a given endpoint may be changed, they can contain regular
            expressions, and they have their resolution order changed. Cortex administrators are responsible for
            configuring their Extended HTTP API endpoints with correct paths and order to meet their use cases.

        Example:

            Add a simple API handler::

                // Create a endpoint for /api/ext/foo/bar
                $api = $lib.cortex.httpapi.add('foo/bar')

                // Define a GET response handler via storm that makes a simple reply.
                $api.methods.get = ${ $request.replay(200, body=({"some": "data}) }

            Add a wildcard handler::

                // Create a wildcard endpoint for /api/ext/some/thing([a-zA-Z0-9]*)/([a-zA-Z0-9]*)
                $api = $lib.cortex.httpapi.add('some/thing([a-zA-Z0-9]*)/([a-zA-Z0-9]*)')

                // The capture groups are exposed as request arguments.
                // Echo them back to the caller.
                $api.methods.get = ${
                    $request.replay(200, body=({"args": $request.args})
                }
        ''',
         'type': {'type': 'function', '_funcname': 'addHttpApi',
                  'args': (
                      {'name': 'path', 'type': 'string',
                       'desc': 'The extended HTTP API path.'},
                      {'name': 'name', 'type': 'string',
                       'desc': 'Friendly name for the Extended HTTP API', 'default': ''},
                      {'name': 'desc', 'type': 'string',
                       'desc': 'Description for the Extended HTTP API.', 'default': ''},
                      {'name': 'runas', 'type': 'string',
                       'desc': 'Run the storm query as the API "owner" or as the authenticated "user".',
                       'default': 'owner'},
                      {'name': 'authenticated', 'type': 'boolean',
                       'desc': 'Require the API endpoint to be authenticated.', 'default': True},
                      {'name': 'readonly', 'type': 'booilean',
                       'desc': 'Run the Extended HTTP Storm methods in readonly mode', 'default': False},
                      # {'name': '', 'type': '',
                      #  'desc': '', 'default': ''},
                      # {'name': '', 'type': '',
                      #  'desc': '', 'default': ''},
                      # {'name': '', 'type': '',
                      #  'desc': '', 'default': ''},
                      # {'name': '', 'type': '',
                      #  'desc': '', 'default': ''},
                      # {'name': '', 'type': '',
                      #  'desc': '', 'default': ''},
                  ),
                  'returns': {'type': 'http:api', 'desc': 'A new http:api object.'}}},
        {'name': 'del', 'desc': 'Delete an Extended HTTPI API endpoint.',
         'type': {'type': 'function', '_funcname': 'delHttpApi',
                  'args': (
                      {'name': 'iden', 'type': 'string',
                       'desc': 'The iden of the API to delete.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'get', 'desc': 'Get an Extended HTTP API object.',
         'type': {'type': 'function', '_funcname': 'getHttpApi',
                  'args': (
                      {'name': 'iden', 'type': 'string',
                       'desc': 'The iden of the API to retreive.'},
                  ),
                  'returns': {'type': 'http:api', 'desc': 'The http:api object.'}}},
        {'name': 'list', 'desc': 'Get all the Extneded HTTP APIs on the Cortex',
         'type': {'type': 'function', '_funcname': 'listHttpApis', 'args': (),
                  'returns': {'type': 'list', 'desc': 'A list of http:api objects'}}},
        {'name': 'index', 'desc': 'Set the index for a given Extended HTTP API.',
         'type': {'type': 'function', '_funcname': 'setHttpApiIndx',
                  'args': (
                      {'name': 'iden', 'type': 'string',
                       'desc': 'The iden of the API to modify.'},
                      {'name': 'index', 'type': 'int', 'default': 0,
                      'desc': 'The new index of the API. Uses zero based indexing.'},
                  ),
                  'returns': {'type': 'int', 'desc': 'The new index location of the API.'}}},
        {'name': 'response', 'desc': 'Make a response object. Used by API handlers automatically.',
         'type': {'type': 'function', '_funcname': 'makeHttpResponse',
                  'args': (
                      {'name': 'requestinfo', 'type': 'dict',
                       'desc': 'Request info dictionary. This is an opaque data structure which may change.'},
                  ),
                  'returns': {'type': 'http:api:request'}}},
    )
    _storm_lib_path = ('cortex', 'httpapi')

    _storm_lib_perms = (
        {'perm': ('storm', 'lib', 'cortex', 'httpapi', 'add'), 'gate': 'cortex',
         'desc': 'Controls the ability to add a new Extended HTTP API on the Cortex.'},
        {'perm': ('storm', 'lib', 'cortex', 'httpapi', 'get'), 'gate': 'cortex',
         'desc': 'Controls the ability to get or list Extended HTTP APIs on the Cortex.'},
        {'perm': ('storm', 'lib', 'cortex', 'httpapi', 'del'), 'gate': 'cortex',
         'desc': 'Controls the ability to delete a Extended HTTP API on the Cortex.'},
        {'perm': ('storm', 'lib', 'cortex', 'httpapi', 'set'), 'gate': 'cortex',
         'desc': 'Controls the ability to modify a Extended HTTP API on the Cortex.'},
    )

    def getObjLocals(self):
        return {
            'add': self.addHttpApi,
            'del': self.delHttpApi,
            'get': self.getHttpApi,
            'list': self.listHttpApis,
            'index': self.setHttpApiIndx,
            'response': self.makeHttpResponse,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def makeHttpResponse(self, requestinfo):
        requestinfo = await s_stormtypes.toprim(requestinfo)
        return HttpReq(self.runt, requestinfo)

    @s_stormtypes.stormfunc(readonly=True)
    async def getHttpApi(self, iden):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        iden = await s_stormtypes.tostr(iden)
        adef = await self.runt.snap.core.getHttpExtApi(iden)
        return HttpApi(self.runt, adef)

    @s_stormtypes.stormfunc(readonly=True)
    async def listHttpApis(self):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        adefs = await self.runt.snap.core.getHttpExtApis()
        apis = [HttpApi(self.runt, adef) for adef in adefs]
        return apis

    async def addHttpApi(self, path, name='', desc='', runas='owner', authenticated=True, readonly=False):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'add'))

        path = await s_stormtypes.tostr(path)
        name = await s_stormtypes.tostr(name)
        desc = await s_stormtypes.tostr(desc)
        runas = await s_stormtypes.tostr(runas)
        readonly = await s_stormtypes.tobool(readonly)
        authenticated = await s_stormtypes.tobool(authenticated)

        adef = {
            'path': path,
            'view': self.runt.snap.view.iden,
            'runas': runas,
            'owner': self.runt.user.iden,
            'methods': {},
            'authenticated': authenticated,
            'name': name,
            'desc': desc,
            'readonly': readonly,
        }

        adef = await self.runt.snap.core.addHttpExtApi(adef)
        return HttpApi(self.runt, adef)

    async def delHttpApi(self, iden):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'del'))
        iden = await s_stormtypes.tostr(iden)
        return await self.runt.snap.view.core.delHttpExtApi(iden)

    async def setHttpApiIndx(self, iden, index=0):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        iden = await s_stormtypes.tostr(iden)
        index = await s_stormtypes.toint(index)
        return await self.runt.snap.view.core.setHttpApiIndx(iden, index)
