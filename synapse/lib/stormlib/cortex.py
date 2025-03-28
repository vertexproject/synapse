import copy
import logging

import synapse.exc as s_exc
import synapse.telepath as s_telepath

import synapse.lib.json as s_json
import synapse.lib.storm as s_storm
import synapse.lib.stormtypes as s_stormtypes
import synapse.lib.stormlib.auth as slib_auth

logger = logging.getLogger(__name__)


stormcmds = [
    {
        'name': 'cortex.httpapi.list',
        'descr': 'List Extended HTTP API endpoints',
        'cmdargs': (),
        'storm': '''
        $apis = $lib.cortex.httpapi.list()
        if $apis {
            $config = (({
                "separators": {
                    'data:row': ''
                },
                "columns": [
                    {'name': 'order', 'width': 5},
                    {'name': 'iden', 'width': 32},
                    {'name': 'owner', 'width': 20},
                    {'name': 'auth', 'width': 5},
                    {'name': 'runas', 'width': 6},
                    {'name': 'path'},
                ]
            }))
            $printer = $lib.tabular.printer($config)
            $lib.print($printer.header())
            for ($n, $api) in $lib.iters.enum($apis) {
                try {
                    $user = $api.owner.name
                } catch NoSuchUser as err {
                    $user = `No user found ({$err.info.user})`
                }
                $auth = `{$api.authenticated}`
                $lib.print($printer.row(($n, $api.iden, $user, $auth, $api.runas, $api.path)))
            }
        } else {
            $lib.print('No Extended HTTP API endpoints are registered.')
        }
        '''
    },
    {
        'name': 'cortex.httpapi.stat',
        'descr': 'Get details for an Extended HTTP API endpoint.',
        'cmdargs': (
            ('iden', {'help': 'The iden of the endpoint to inspect. This will also match iden prefixes or name prefixes.',
                      'type': 'str'}),
        ),
        'storm': '''
        $iden = $lib.null
        for $api in $lib.cortex.httpapi.list() {
            if $api.iden.startswith($cmdopts.iden) {
                if $iden {
                    $lib.raise(StormRuntimeError, 'Already matched one Extended HTTP API!')
                }
                $iden = $api.iden
            }
            if $api.name.startswith($cmdopts.iden) {
                if $iden {
                    $lib.raise(StormRuntimeError, 'Already matched one Extended HTTP API!')
                }
                $iden = $api.iden
            }
        }
        if (not $iden) {
            $lib.raise(StormRuntimeError, 'Failed to match Extended HTTP API by iden or name!')
        }
        $time = $lib.model.type(time)
        $api = $lib.cortex.httpapi.get($iden)
        $lib.print(`Iden: {$api.iden}`)
        try {
            $lib.print(`Creator: {$api.creator.name} ({$api.creator.iden})`)
        } catch NoSuchUser as err {
            $lib.print(`!Creator: No user found ({$err.info.user})`)
        }
        $lib.print(`Created: {$time.repr($api.created)}`)
        $lib.print(`Updated: {$time.repr($api.updated)}`)
        $lib.print(`Path: {$api.path}`)
        try {
            $lib.print(`Owner: {$api.owner.name} ({$api.owner.iden})`)
        } catch NoSuchUser as err {
            $lib.print(`!Owner: No user found ({$err.info.user})`)
        }
        $lib.print(`Runas: {$api.runas}`)
        try {
            $lib.print(`View: {$api.view.get(name)} ({$api.view.iden})`)
        } catch NoSuchView as err {
            $lib.print(`!View: No view found ({$err.info.iden})`)
        }
        $lib.print(`Readonly: {$api.readonly}`)
        $lib.print(`Pool enabled: {$api.pool}`)
        $lib.print(`Authenticated: {$api.authenticated}`)
        $lib.print(`Name: {$api.name}`)
        $lib.print(`Description: {$api.desc}`)
        $lib.print('')
        $perms = $api.perms
        if $perms {
            $lib.print('The following user permissions are required to run this HTTP API endpoint:')
            for $pdef in $perms {
                $perm = $lib.str.join(".", $pdef.perm)
                $lib.print($perm)
                $lib.print(`    default: {$pdef.default}`)
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
                $lib.print('')
            }
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
        'descr': '''Set the index of an Extended HTTP API endpoint.

Examples:

    // Move an endpoint to the first index.
    cortex.httpapi.index 60e5ba38e90958fd8e2ddd9e4730f16b 0

    // Move an endpoint to the third index.
    cortex.httpapi.index dd9e4730f16b60e5ba58fd8e2d38e909 2
''',
        'cmdargs': (
            ('iden', {'help': 'The iden of the endpoint to move. This will also match iden prefixes or name prefixes.',
                      'type': 'str'}),
            ('index', {'help': 'Specify the endpoint location as a 0 based index.', 'type': 'int'}),
        ),
        'storm': '''
        $iden = $lib.null
        for $api in $lib.cortex.httpapi.list() {
            if $api.iden.startswith($cmdopts.iden) {
                if $iden {
                    $lib.raise(StormRuntimeError, 'Already matched one Extended HTTP API!')
                }
                $iden = $api.iden
            }
            if $api.name.startswith($cmdopts.iden) {
                if $iden {
                    $lib.raise(StormRuntimeError, 'Already matched one Extended HTTP API!')
                }
                $iden = $api.iden
            }
        }
        if (not $iden) {
            $lib.raise(StormRuntimeError, 'Failed to match Extended HTTP API by iden or name!')
        }
        $api = $lib.cortex.httpapi.get($iden)
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
    Extended HTTP API object.

    This object represents an extended HTTP API that has been configured on the Cortex.
    '''
    _storm_typename = 'http:api'
    _storm_locals = (
        {'name': 'iden', 'desc': 'The iden of the Extended HTTP API.', 'type': 'str'},
        {'name': 'created', 'desc': 'The time the Extended HTTP API was created.', 'type': 'int'},
        {'name': 'updated', 'desc': 'The time the Extended HTTP API was last modified.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorUpdated', 'returns': {'type': 'int'}}},
        {'name': 'creator', 'desc': 'The user that created the Extended HTTP API.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorCreator', 'returns': {'type': 'auth:user'}}},
        {'name': 'owner', 'desc': 'The user that runs the endpoint query logic when runas="owner".',
         'type': {'type': ['gtor', 'stor'], '_gtorfunc': '_gtorOwner', '_storfunc': '_storOwner',
                  'returns': {'type': 'auth:user'}}},
        {'name': 'pack', 'desc': 'Get a packed copy of the HTTP API object.',
         'type': {'type': 'function', '_funcname': '_methPack', 'args': (),
                  'returns': {'type': 'dict'}}},
        {'name': 'name', 'desc': 'The name of the API instance.',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storName', '_gtorfunc': '_gtorName',
                  'returns': {'type': 'str'}}},
        {'name': 'desc', 'desc': 'The description of the API instance.',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storDesc', '_gtorfunc': '_gtorDesc',
                  'returns': {'type': 'str'}}},
        {'name': 'path', 'desc': '''
        The path of the API instance.

        This path may contain regular expression capture groups, which are used to populate
        request arguments.

        Note:
            The Cortex does not inspect paths in order to identify duplicates or overlapping paths.
            It is the responsibility of the Cortex administrator to configure their Extended HTTP API
            paths so that they are correct for their use cases.

        Example:
            Update an API path to contain a single wildcard argument::

                $api.path = 'foo/bar/(.*)/baz'

            Update an API path to contain a two wildcard arguments with restricted character sets::

                $api.path = 'hehe/([a-z]*)/([0-9]{1-4})'
        ''',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storPath', '_gtorfunc': '_gtorPath',
                  'returns': {'type': 'str'}}},
        {'name': 'pool', 'desc': 'Boolean value indicating if the handler responses may be executed as part of a Storm pool.',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storPool', '_gtorfunc': '_gtorPool',
                  'returns': {'type': 'boolean'}}},
        {'name': 'vars', 'desc': 'The Storm runtime variables specific for the API instance.',
         'type': {'type': ['stor', 'ctor'], '_storfunc': '_storVars', '_ctorfunc': '_ctorVars',
                  'returns': {'type': 'http:api:vars'}}},
        {'name': 'view', 'desc': 'The View of the API instance. This is the view that Storm methods are executed in.',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storView', '_gtorfunc': '_gtorView',
                  'returns': {'type': 'view'}}},
        {'name': 'runas', 'desc': 'String indicating whether the requests run as the owner or the authenticated user.',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storRunas', '_gtorfunc': '_gtorRunas',
                  'returns': {'type': 'str'}}},
        {'name': 'perms', 'desc': 'The permissions an authenticated user must have in order to access the HTTP API.',
         'type': {'type': ['stor', 'ctor'], '_storfunc': '_storPerms', '_ctorfunc': '_ctorPerms',
                  'returns': {'type': 'http:api:perms'}}},
        {'name': 'readonly', 'desc': 'Boolean value indicating if the Storm methods are executed in a readonly Storm runtime.',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storReadonly', '_gtorfunc': '_gtorReadonly',
                  'returns': {'type': 'boolean'}}},
        {'name': 'authenticated', 'desc': 'Boolean value indicating if the Extended HTTP API requires an authenticated user or session.',
         'type': {'type': ['stor', 'gtor'], '_storfunc': '_storAuthenticated', '_gtorfunc': '_gtorAuthenticated',
                  'returns': {'type': 'boolean'}}},
        {'name': 'methods', 'desc': 'The dictionary containing the Storm code used to implement the HTTP methods.',
         'type': {'type': ['ctor'], '_ctorfunc': '_ctorMethods', 'returns': {'type': 'http:api:methods'}}}
    )

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
            'pool': self._storPool,
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
            'pool': self._gtorPool,
            'view': self._gtorView,
            'runas': self._gtorRunas,
            'owner': self._gtorOwner,
            'creator': self._gtorCreator,
            'updated': self._gtorUpdated,
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
            'created': self.info.get('created'),
        })

    async def stormrepr(self):
        name = await self._gtorName()
        if not name:
            name = '<no name>'
        path = await self._gtorPath()
        return f'{self._storm_typename}: {name} ({self.iden}), path={path}'

    def getObjLocals(self):
        return {
            'pack': self._methPack,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _methPack(self):
        # TODO: Remove this when we've migrated the HTTPAPI data to set this value.
        ret = copy.deepcopy(self.info)
        ret.setdefault('pool', False)
        return ret

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorMethods(self, path=None):
        return HttpApiMethods(self)

    async def _storPath(self, path):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        path = await s_stormtypes.tostr(path)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'path', path)
        self.info['path'] = path
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorPath(self):
        return self.info.get('path')

    async def _storPool(self, pool):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        pool = await s_stormtypes.tobool(pool)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'pool', pool)
        self.info['pool'] = pool
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorPool(self):
        return self.info.get('pool')

    async def _storName(self, name):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        name = await s_stormtypes.tostr(name)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'name', name)
        self.info['name'] = name
        self.info['updated'] = adef.get('updated')

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
        self.info['updated'] = adef.get('updated')

    async def _storView(self, iden):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        if isinstance(iden, s_stormtypes.View):
            view = iden.value().get('iden')
        else:
            view = await s_stormtypes.tostr(iden)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'view', view)
        self.info['view'] = view
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorName(self):
        return self.info.get('name')

    async def _storDesc(self, desc):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        desc = await s_stormtypes.tostr(desc)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'desc', desc)
        self.info['desc'] = desc
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorDesc(self):
        return self.info.get('desc')

    async def _storRunas(self, runas):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        runas = await s_stormtypes.tostr(runas)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'runas', runas)
        self.info['runas'] = runas
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorRunas(self):
        return self.info.get('runas')

    async def _storReadonly(self, readonly):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        readonly = await s_stormtypes.tobool(readonly)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'readonly', readonly)
        self.info['readonly'] = readonly
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorVars(self, path=None):
        return HttpApiVars(self, path=path)

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorReadonly(self):
        return self.info.get('readonly')

    async def _storOwner(self, owner):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        if isinstance(owner, slib_auth.User):
            info = await owner.value()
            owner = info.get('iden')
        else:
            owner = await s_stormtypes.tostr(owner)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'owner', owner)
        self.info['owner'] = owner
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorOwner(self):
        iden = self.info.get('owner')
        udef = await self.runt.snap.core.getUserDef(iden)
        if udef is None:
            raise s_exc.NoSuchUser(mesg=f'HTTP API owner does not exist {iden}', user=iden)
        return slib_auth.User(self.runt, udef['iden'])

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorCreator(self):
        iden = self.info.get('creator')
        udef = await self.runt.snap.core.getUserDef(iden)
        if udef is None:
            raise s_exc.NoSuchUser(mesg=f'HTTP API creator does not exist {iden}', user=iden)
        return slib_auth.User(self.runt, udef['iden'])

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorUpdated(self):
        return self.info.get('updated')

    async def _storPerms(self, perms):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        perms = await s_stormtypes.toprim(perms)
        pdefs = []
        for pdef in perms:
            if isinstance(pdef, str):
                pdef = _normPermString(pdef)
            pdefs.append(pdef)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'perms', pdefs)
        self.info['perms'].clear()
        self.info['perms'].extend(pdefs)
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorPerms(self, path):
        return HttpPermsList(self, path)

    async def _storAuthenticated(self, authenticated):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        authenticated = await s_stormtypes.tobool(authenticated)
        adef = await self.runt.snap.core.modHttpExtApi(self.iden, 'authenticated', authenticated)
        self.info['authenticated'] = authenticated
        self.info['updated'] = adef.get('updated')

    @s_stormtypes.stormfunc(readonly=True)
    async def _gtorAuthenticated(self):
        return self.info.get('authenticated')

@s_stormtypes.registry.registerType
class HttpApiMethods(s_stormtypes.Prim):
    '''
    Accessor dictionary for getting and setting Extended HTTP API methods.

    Notes:
        The Storm code used to run these methods will have a $request object
        injected into them. This allows the method to send data back to the
        caller when it is run.

    Examples:
        Setting a simple GET method::

            $api.methods.get = ${
                $data = ({"someKey": "someValue})
                $headers = ({"someHeader": "someOtherValue"})
                $request.reply(200, headers=$headers, body=$data)
            }

        Removing a PUT method::

            $api.methods.put = $lib.undef

        Crafting a custom text response::

            $api.methods.get = ${
                // Create the body
                $data = 'some value'
                // Encode the response as bytes
                $data = $data.encode()
                // Set the headers
                $headers = ({"Content-Type": "text/plain", "Content-Length": $lib.len($data})
                $request.reply(200, headers=$headers, body=$data)
            }

        Streaming multiple chunks of data as JSON lines. This sends the code, headers and body separately::

            $api.methods.get = ${
                $request.sendcode(200)
                $request.sendheaders(({"Content-Type": "text/plain; charset=utf8"}))
                $values = ((1), (2), (3))
                for $i in $values {
                    $body=`{$lib.json.save(({"value": $i}))}\n`
                    $request.sendbody($body.encode())
                }
            }

    '''
    _storm_typename = 'http:api:methods'
    _storm_locals = (
        {'name': 'get', 'desc': 'The GET request Storm code.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storMethGet', '_gtorfunc': '_gtorMethGet',
                  'returns': {'type': ['str', 'null']}}},
        {'name': 'put', 'desc': 'The PUT request Storm code.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storMethPut', '_gtorfunc': '_gtorMethPut',
                  'returns': {'type': ['str', 'null']}}},
        {'name': 'head', 'desc': 'The HEAD request Storm code',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storMethHead', '_gtorfunc': '_gtorMethHead',
                  'returns': {'type': ['str', 'null']}}},
        {'name': 'post', 'desc': 'The POST request Storm code.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storMethPost', '_gtorfunc': '_gtorMethPost',
                  'returns': {'type': ['str', 'null']}}},
        {'name': 'delete', 'desc': 'The DELETE request Storm code.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storMethDelete', '_gtorfunc': '_gtorMethDelete',
                  'returns': {'type': ['str', 'null']}}},
        {'name': 'patch', 'desc': 'The PATCH request Storm code.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storMethPatch', '_gtorfunc': '_gtorMethPatch',
                  'returns': {'type': ['str', 'null']}}},
        {'name': 'options', 'desc': 'The OPTIONS request Storm code.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_storMethOptions', '_gtorfunc': '_gtorMethOptions',
                  'returns': {'type': ['str', 'null']}}},
    )
    _ismutable = True

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
            adef = await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'methods', methods)
            self.valu.pop(meth, None)
            self.httpapi.info['updated'] = adef.get('updated')
        else:
            query = await s_stormtypes.tostr(query)
            query = query.strip()

            # Ensure our query can be parsed.
            await self.httpapi.runt.snap.core.getStormQuery(query)

            methods[meth] = query
            adef = await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'methods', methods)
            self.valu[meth] = query
            self.httpapi.info['updated'] = adef.get('updated')

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

    Example:
        Request headers can be accessed in a case insensitive manner::

            $valu = $request.headers.Cookie
            // or the lower case value
            $valu = $request.headers.cookie
    '''
    _storm_typename = 'http:api:request:headers'
    _storm_locals = ()
    _ismutable = True

    async def setitem(self, name, valu):
        mesg = f'{self._storm_typename} may not be modified by the runtime.'
        raise s_exc.StormRuntimeError(mesg=mesg, name=name)

    async def deref(self, name):
        name = await s_stormtypes.tostr(name)
        name = name.lower()
        return self.valu.get(name)

@s_stormtypes.registry.registerType
class HttpPermsList(s_stormtypes.List):
    '''
    Accessor list for getting and setting http:api permissions.
    '''
    _storm_typename = 'http:api:perms'
    _storm_locals = (
        {'name': 'has', 'desc': 'Check it a permission is in the list.',
         'type': {'type': 'function', '_funcname': '_methListHas',
                  'args': (
                      {'name': 'valu', 'type': 'any', 'desc': 'The permission to check.', },
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the permission is in the list, false otherwise.', }}},
        {'name': 'pop', 'desc': 'Pop and return the last permission in the list.',
         'type': {'type': 'function', '_funcname': '_methListPop',
                  'returns': {'type': 'any', 'desc': 'The last permission from the list.', }}},
        {'name': 'size', 'desc': 'Return the length of the list.',
         'type': {'type': 'function', '_funcname': '_methListSize',
                  'returns': {'type': 'int', 'desc': 'The size of the list.', }}},
        {'name': 'index', 'desc': 'Return a single permission from the list by index.',
         'type': {'type': 'function', '_funcname': '_methListIndex',
                  'args': (
                      {'name': 'valu', 'type': 'int', 'desc': 'The list index value.', },
                  ),
                  'returns': {'type': 'any', 'desc': 'The permission present in the list at the index position.', }}},
        {'name': 'length', 'desc': 'Get the length of the list. This is deprecated; please use ``.size()`` instead.',
         'deprecated': {'eolvers': 'v3.0.0'},
         'type': {'type': 'function', '_funcname': '_methListLength',
                  'returns': {'type': 'int', 'desc': 'The size of the list.', }}},
        {'name': 'append', 'desc': 'Append a permission to the list.',
         'type': {'type': 'function', '_funcname': '_methListAppend',
                  'args': (
                      {'name': 'valu', 'type': 'any', 'desc': 'The permission to append to the list.', },
                  ),
                  'returns': {'type': 'null', }}},
        {'name': 'reverse', 'desc': 'Reverse the order of the list in place',
         'type': {'type': 'function', '_funcname': '_methListReverse',
                  'returns': {'type': 'null', }}},
        {'name': 'slice', 'desc': 'Get a slice of the list.',
         'type': {'type': 'function', '_funcname': '_methListSlice',
                  'args': (
                      {'name': 'start', 'type': 'int', 'desc': 'The starting index.'},
                      {'name': 'end', 'type': 'int', 'default': None,
                       'desc': 'The ending index. If not specified, slice to the end of the list.'},
                  ),
                  'returns': {'type': 'list', 'desc': 'The slice of the list.'}}},

        {'name': 'extend', 'desc': 'Extend a list using another iterable.',
         'type': {'type': 'function', '_funcname': '_methListExtend',
                  'args': (
                      {'name': 'valu', 'type': 'list', 'desc': 'A list or other iterable.'},
                  ),
                  'returns': {'type': 'null'}}},
    )
    _ismutable = True

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
        # This is not a documented method. Attempting to sort a list of permissions has no meaning.
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
    Accessor dictionary for getting and setting Extended HTTP API variables.

    This can be used to set, unset or iterate over the runtime variables that are
    set for an Extended HTTP API endpoint. These variables are set in the Storm
    runtime for all of the HTTP methods configured to be executed by the endpoint.

    Example:
        Set a few variables on a given API::

            $api.vars.foo = 'the foo string'
            $api.vars.bar = (1234)

        Remove a variable::

            $api.vars.foo = $lib.undef

        Iterate over the variables set for the endpoint::

            for ($key, $valu) in $api.vars {
                $lib.print(`{$key) -> {$valu}`)
            }

        Overwrite all of the variables for a given API with a new dictionary::

            $api.vars = ({"foo": "a new string", "bar": (137)})
    '''
    _storm_typename = 'http:api:vars'
    _storm_locals = ()
    _ismutable = True

    def __init__(self, httpapi, path=None):
        s_stormtypes.Dict.__init__(self, httpapi.info.get('vars'), path=path)
        self.httpapi = httpapi

    async def setitem(self, name, valu):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'set'))
        name = await s_stormtypes.tostr(name)

        varz = self.valu.copy()
        if valu is s_stormtypes.undef:
            varz.pop(name, None)
            adef = await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'vars', varz)
            self.valu.pop(name, None)
            self.httpapi.info['updated'] = adef.get('updated')
        else:
            valu = await s_stormtypes.toprim(valu)
            varz[name] = valu
            adef = await self.httpapi.runt.snap.core.modHttpExtApi(self.httpapi.iden, 'vars', varz)
            self.valu[name] = valu
            self.httpapi.info['updated'] = adef.get('updated')

@s_stormtypes.registry.registerType
class HttpReq(s_stormtypes.StormType):
    '''
    Extended HTTP API Request object.
    '''
    _storm_typename = 'http:api:request'
    _storm_locals = (
        {'name': 'args', 'desc': '''
        A list of path arguments made as part of the HTTP API request.
        These are the results of any capture groups defined in the Extended HTTP API path regular expression.''',
         'type': 'list'},
        {'name': 'body', 'desc': 'The raw request body.', 'type': 'bytes'},
        {'name': 'method', 'desc': 'The request method', 'type': 'str'},
        {'name': 'params', 'desc': 'Request parameters.', 'type': 'dict'},
        {'name': 'client', 'desc': 'The remote IP of the requester.', 'type': 'str'},
        {'name': 'uri', 'desc': 'The full request URI.', 'type': 'str'},
        {'name': 'path', 'desc': 'The path which was matched against the Extended HTTPAPI endpoint.', 'type': 'str'},
        {'name': 'user',
         'desc': 'The user iden who made the HTTP API request.', 'type': 'str'},
        {'name': 'api', 'desc': 'The http:api object for the request.',
         'type': {'type': 'gtor', '_gtorfunc': '_gtorApi',
                  'returns': {'type': 'http:api'}}},
        {'name': 'headers', 'desc': 'The request headers.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorJson',
                  'returns': {'type': 'http:api:request:headers'}}},
        {'name': 'json', 'desc': 'The request body as json.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorJson',
                  'returns': {'type': 'dict'}}},
        {'name': 'sendcode', 'desc': 'Send the HTTP response code.',
         'type': {'type': 'function', '_funcname': '_methSendCode',
                  'args': (
                      {'name': 'code', 'type': 'int',
                       'desc': 'The response code.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'sendheaders', 'desc': 'Send the HTTP response headers.',
         'type': {'type': 'function', '_funcname': '_methSendHeaders',
                  'args': (
                      {'name': 'headers', 'type': 'dict',
                       'desc': 'The response headers.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'sendbody', 'desc': 'Send the HTTP response body.',
         'type': {'type': 'function', '_funcname': '_methSendBody',
                  'args': (
                      {'name': 'body', 'type': 'bytes',
                       'desc': 'The response body.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'reply', 'desc': '''
        Convenience method to send the response code, headers and body together.

        Notes:
            This can only be called once.

            If the response body is not bytes, this method will serialize the body as JSON
            and set the ``Content-Type`` and ``Content-Length`` response headers.
        ''',
         'type': {'type': 'function', '_funcname': '_methReply',
                  'args': (
                      {'name': 'code', 'type': 'int',
                       'desc': 'The response code.'},
                      {'name': 'headers', 'type': 'dict',
                       'desc': 'The response headers.', 'default': None},
                      {'name': 'body', 'type': 'any',
                       'desc': 'The response body.', 'default': '$lib.undef'},
                  ),
                  'returns': {'type': 'null'}}},
    )

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
            'client': self.rnfo.get('client'),
            'uri': self.rnfo.get('uri'),
            'path': self.rnfo.get('path'),
            'user': self.rnfo.get('user'),
        })

        self.gtors.update({
            'api': self._gtorApi,  # Not a ctor since the adef retrieval is an async process
        })

        self.ctors.update({
            'json': self._ctorJson,
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
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        adef = await self.runt.snap.core.getHttpExtApi(self.rnfo.get('iden'))
        return HttpApi(self.runt, adef)

    @s_stormtypes.stormfunc(readonly=True)
    def _ctorJson(self, path=None):
        try:
            return s_json.loads(self.rnfo.get('body'))
        except (UnicodeDecodeError, s_exc.BadJsonText) as e:
            raise s_exc.StormRuntimeError(mesg=f'Failed to decode request body as JSON: {e}') from None

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
            raise s_exc.BadArg(mesg='Response.reply() has already been called.')

        headers = await s_stormtypes.toprim(headers)
        if headers is None:
            headers = {}

        if body is not s_stormtypes.undef:
            if not isinstance(body, bytes):
                body = await s_stormtypes.toprim(body)
                body = s_json.dumps(body)
                headers['Content-Type'] = 'application/json; charset=utf8"'
                headers['Content-Length'] = len(body)

        await self._methSendCode(code)

        if headers:
            await self._methSendHeaders(headers)

        if body is not s_stormtypes.undef:
            await self._methSendBody(body)

        self.replied = True

@s_stormtypes.registry.registerLib
class CortexHttpApi(s_stormtypes.Lib):
    '''
    Library for interacting with the Extended HTTP API.
    '''
    _storm_locals = (
        {'name': 'add', 'desc': '''
        Add an Extended HTTP API endpoint to the Cortex.

        This can be used to add an API endpoint which will be resolved under
        the API path "/api/ext/". New API endpoint objects are appended to
        a list of APIs to resolve in order.

        Notes:
            The Cortex does not make any attempt to do any inspection of path values which may conflict between one
            another. This is because the paths for a given endpoint may be changed, they can contain regular
            expressions, and they may have their resolution order changed. Cortex administrators are responsible for
            configuring their Extended HTTP API endpoints with correct paths and order to meet their use cases.

        Example:
            Add a simple API handler::

                // Create an endpoint for /api/ext/foo/bar
                $api = $lib.cortex.httpapi.add('foo/bar')

                // Define a GET response handler via storm that makes a simple reply.
                $api.methods.get = ${ $request.reply(200, body=({"some": "data}) }

            Add a wildcard handler::

                // Create a wildcard endpoint for /api/ext/some/thing([a-zA-Z0-9]*)/([a-zA-Z0-9]*)
                $api = $lib.cortex.httpapi.add('some/thing([a-zA-Z0-9]*)/([a-zA-Z0-9]*)')

                // The capture groups are exposed as request arguments.
                // Echo them back to the caller.
                $api.methods.get = ${
                    $request.reply(200, body=({"args": $request.args})
                }
        ''',
         'type': {'type': 'function', '_funcname': 'addHttpApi',
                  'args': (
                      {'name': 'path', 'type': 'string',
                       'desc': 'The extended HTTP API path.'},
                      {'name': 'name', 'type': 'string',
                       'desc': 'Friendly name for the Extended HTTP API.', 'default': ''},
                      {'name': 'desc', 'type': 'string',
                       'desc': 'Description for the Extended HTTP API.', 'default': ''},
                      {'name': 'runas', 'type': 'string',
                       'desc': 'Run the storm query as the API "owner" or as the authenticated "user".',
                       'default': 'owner'},
                      {'name': 'authenticated', 'type': 'boolean',
                       'desc': 'Require the API endpoint to be authenticated.', 'default': True},
                      {'name': 'readonly', 'type': 'boolean',
                       'desc': 'Run the Extended HTTP Storm methods in readonly mode.', 'default': False},
                      {'name': 'iden', 'type': 'str',
                       'desc': 'An iden for the new Extended HTTP API.', 'default': None},
                  ),
                  'returns': {'type': 'http:api', 'desc': 'A new ``http:api`` object.'}}},
        {'name': 'del', 'desc': 'Delete an Extended HTTP API endpoint.',
         'type': {'type': 'function', '_funcname': 'delHttpApi',
                  'args': (
                      {'name': 'iden', 'type': 'string',
                       'desc': 'The iden of the API to delete.'},
                  ),
                  'returns': {'type': 'null'}}},
        {'name': 'get', 'desc': 'Get an Extended ``http:api`` object.',
         'type': {'type': 'function', '_funcname': 'getHttpApi',
                  'args': (
                      {'name': 'iden', 'type': 'string',
                       'desc': 'The iden of the API to retrieve.'},
                  ),
                  'returns': {'type': 'http:api', 'desc': 'The ``http:api`` object.'}}},
        {'name': 'getByPath', 'desc': '''
        Get an Extended ``http:api`` object by path.

        Notes:
            The path argument is evaluated as a regular expression input, and will be
            used to get the first HTTP API handler whose path value has a match.
        ''',
         'type': {'type': 'function', '_funcname': 'getHttpApiByPath',
                  'args': (
                      {'name': 'path', 'type': 'string',
                       'desc': 'Path to use to retrieve an object.'},
                  ),
                  'returns': {'type': ['http:api', 'null'], 'desc': 'The ``http:api`` object or ``(null)`` if there is no match.'}}},
        {'name': 'list', 'desc': 'Get all the Extended HTTP APIs on the Cortex',
         'type': {'type': 'function', '_funcname': 'listHttpApis', 'args': (),
                 'returns': {'type': 'list', 'desc': 'A list of ``http:api`` objects'}}},
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
         'desc': 'Controls the ability to delete an Extended HTTP API on the Cortex.'},
        {'perm': ('storm', 'lib', 'cortex', 'httpapi', 'set'), 'gate': 'cortex',
         'desc': 'Controls the ability to modify an Extended HTTP API on the Cortex.'},
    )

    def getObjLocals(self):
        return {
            'add': self.addHttpApi,
            'del': self.delHttpApi,
            'get': self.getHttpApi,
            'list': self.listHttpApis,
            'index': self.setHttpApiIndx,
            'response': self.makeHttpResponse,
            'getByPath': self.getHttpApiByPath,
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
    async def getHttpApiByPath(self, path):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        path = await s_stormtypes.tostr(path)
        adef, _ = await self.runt.snap.core.getHttpExtApiByPath(path)
        if adef is None:
            return None
        return HttpApi(self.runt, adef)

    @s_stormtypes.stormfunc(readonly=True)
    async def listHttpApis(self):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'get'))
        adefs = await self.runt.snap.core.getHttpExtApis()
        apis = [HttpApi(self.runt, adef) for adef in adefs]
        return apis

    async def addHttpApi(self, path, name='', desc='', runas='owner', authenticated=True, readonly=False, iden=None):
        s_stormtypes.confirm(('storm', 'lib', 'cortex', 'httpapi', 'add'))

        path = await s_stormtypes.tostr(path)
        name = await s_stormtypes.tostr(name)
        desc = await s_stormtypes.tostr(desc)
        runas = await s_stormtypes.tostr(runas)
        readonly = await s_stormtypes.tobool(readonly)
        authenticated = await s_stormtypes.tobool(authenticated)

        adef = {
            'iden': iden,
            'path': path,
            'view': self.runt.snap.view.iden,
            'runas': runas,
            'creator': self.runt.user.iden,
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

class StormPoolSetCmd(s_storm.Cmd):
    '''
    Setup a Storm query offload mirror pool for the Cortex.
    '''
    name = 'cortex.storm.pool.set'
    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        pars.add_argument('--connection-timeout', type='int', default=2,
            help='The maximum amount of time to wait for a connection from the pool to become available.')
        pars.add_argument('--sync-timeout', type='int', default=2,
            help='The maximum amount of time to wait for the mirror to be in sync with the leader')
        pars.add_argument('url', type='str', required=True, help='The telepath URL for the AHA service pool.')
        return pars

    async def execStormCmd(self, runt, genr):

        if not self.runtsafe: # pragma: no cover
            mesg = 'cortex.storm.pool.set arguments must be runtsafe.'
            raise s_exc.StormRuntimeError(mesg=mesg)

        mesg = 'cortex.storm.pool.set command requires global admin permissions.'
        self.runt.reqAdmin(mesg=mesg)

        async for node, path in genr: # pragma: no cover
            yield node, path

        try:
            s_telepath.chopurl(self.opts.url)
        except s_exc.BadUrl as e:
            raise s_exc.BadArg(mesg=f'Unable to set Storm pool URL from url={self.opts.url} : {e.get("mesg")}') from None

        opts = {
            'timeout:sync': self.opts.sync_timeout,
            'timeout:connection': self.opts.connection_timeout,
        }

        await self.runt.snap.core.setStormPool(self.opts.url, opts)
        await self.runt.printf('Storm pool configuration set.')

class StormPoolDelCmd(s_storm.Cmd):
    '''
    Remove a Storm query offload mirror pool configuration.

    Notes:
        This will result in tearing down any Storm queries currently being serviced by the Storm pool.
        This may result in this command raising an exception if it was offloaded to a pool member. That would be an expected behavior.
    '''
    name = 'cortex.storm.pool.del'

    async def execStormCmd(self, runt, genr):

        mesg = 'cortex.storm.pool.del command requires global admin permissions.'
        self.runt.reqAdmin(mesg=mesg)

        async for node, path in genr: # pragma: no cover
            yield node, path

        await self.runt.snap.core.delStormPool()
        await self.runt.printf('Storm pool configuration removed.')

class StormPoolGetCmd(s_storm.Cmd):
    '''
    Display the current Storm query offload mirror pool configuration.
    '''
    name = 'cortex.storm.pool.get'

    async def execStormCmd(self, runt, genr):

        mesg = 'cortex.storm.pool.get command requires global admin permissions.'
        self.runt.reqAdmin(mesg=mesg)

        async for node, path in genr: # pragma: no cover
            yield node, path

        item = await self.runt.snap.core.getStormPool()
        if item is None:
            await self.runt.printf('No Storm pool configuration found.')
            return

        url, opts = item

        await self.runt.printf(f'Storm Pool URL: {url}')
        await self.runt.printf(f'Sync Timeout (secs): {opts.get("timeout:sync")}')
        await self.runt.printf(f'Connection Timeout (secs): {opts.get("timeout:connection")}')
