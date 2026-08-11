import logging
import urllib.parse

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.coro as s_coro
import synapse.lib.json as s_json
import synapse.lib.httpapi as s_httpapi
import synapse.lib.version as s_version
import synapse.lib.stormhttp as s_stormhttp
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

# RSA key size for the per-deployment keypair (NIST 128-bit strength, valid past 2030).
DEPLOY_KEY_BITS = 3072

stormcmds = (
    {
        'name': 'vertex.register',
        'desc': 'Register this deployment with the Vertex Hub.',
        'cmdargs': (
            ('email', {'help': 'The email address to register the deployment under.'}),
            ('--name', {'help': 'An optional name for the deployment.', 'default': None}),
            ('--reset', {'help': 'Re-register even if already registered. This creates a NEW '
                                 'deployment which may have different available power-ups.',
                         'default': False, 'action': 'store_true'}),
        ),
        'storm': '''
            $deploy = $lib.vertex.register($cmdopts.email, name=$cmdopts.name, reset=$cmdopts.reset)
            if ($deploy = (null)) {
                $lib.print(`No Vertex Hub account was found for {$cmdopts.email}.`)
                $lib.print(`Create an account at https://hub.vertex.link/hub using this email address, then run vertex.register again.`)
            } else {
                $lib.print(`Registered deployment {$deploy} for {$cmdopts.email}.`)
                $lib.print(`Manage this deployment at https://hub.vertex.link/hub/support/deployments/{$deploy}`)
            }
        ''',
    },
    {
        'name': 'vertex.packages.list',
        'desc': 'List the packages available to this deployment from the Vertex Hub.',
        'cmdargs': (),
        'storm': '''
            $pkgs = $lib.vertex.packages.list()
            if (not $pkgs) {
                $lib.print('No packages are available to this deployment.')
            } else {
                $printer = $lib.tabular.printer(({
                    "columns": [
                        {"name": "Name", "width": 40},
                        {"name": "Version", "width": 12},
                        {"name": "Published", "width": 12},
                        {"name": "Description", "width": 60},
                    ],
                }))
                $lib.print($printer.header())
                for $pkg in $pkgs {
                    // the published date of the latest build (builds are oldest-first)
                    $published = ''
                    for $build in $pkg.builds.available {
                        if ($build.version = $pkg.latest) {
                            $published = $lib.time.format($build.created, '%Y-%m-%d')
                        }
                    }
                    $desc = $pkg.description
                    if ($desc = (null)) { $desc = '' }
                    $lib.print($printer.row(($pkg.name, $pkg.latest, $published, $desc)))
                }
            }
        ''',
    },
    {
        'name': 'vertex.packages.versions',
        'desc': 'List the available versions of a package from the Vertex Hub.',
        'cmdargs': (
            ('name', {'help': 'The name of the package.'}),
            ('--match', {'help': 'An optional version prefix used to filter the results.',
                         'default': None}),
        ),
        'storm': '''
            $vers = $lib.vertex.packages.versions($cmdopts.name, match=$cmdopts.match)
            if (not $vers) {
                $lib.print(`No versions are available for {$cmdopts.name}.`)
            } else {
                $printer = $lib.tabular.printer(({
                    "columns": [
                        {"name": "Version", "width": 20},
                        {"name": "Published", "width": 12},
                    ],
                }))
                $lib.print($printer.header())
                for $ver in $vers {
                    $row = ($ver.version, $lib.time.format($ver.created, '%Y-%m-%d'))
                    $lib.print($printer.row($row))
                }
            }
        ''',
    },
    {
        'name': 'vertex.packages.install',
        'desc': 'Install a package from the Vertex Hub.',
        'cmdargs': (
            ('name', {'help': 'The name of the package to install.'}),
            ('--version', {'help': 'The version to install. Defaults to the latest version.',
                           'default': None}),
        ),
        'storm': '''
            $pkg = $lib.vertex.packages.install($cmdopts.name, version=$cmdopts.version)
            $lib.print(`Installed {$pkg.name} at version {$pkg.version}.`)
        ''',
    },
)

async def _hubResp(runt, meth, path, json=None, params=None):
    '''
    Make a request to the Vertex Hub and return an ``(code, data)`` tuple where
    data is the parsed JSON body (or None). Every request is tagged with the
    running Synapse version.
    '''
    core = runt.view.core

    url = core._vertex_hub_url + path
    ssl = {'verify': core._vertex_hub_ssl_verify}

    headers = {'X-Synapse-Version': s_version.version}

    libhttp = s_stormhttp.LibHttp(runt)
    resp = await libhttp._httpRequest(meth, url, headers=headers, json=json, params=params, ssl=ssl)

    body = resp.valu.get('body')

    data = None
    if body:
        try:
            data = s_json.loads(body)
        except s_exc.BadJsonText:
            data = None

    return resp.valu.get('code'), data

async def _hubReq(runt, meth, path, json=None, params=None):
    '''
    Make a request to the Vertex Hub and return the ``result`` of a REST response.
    '''
    code, data = await _hubResp(runt, meth, path, json=json, params=params)
    return s_httpapi.result(code, data)

def _rsaPubPem(privbyts):
    # load the RSA private key + derive its PEM public key; pure crypto (no slab
    # access) so it is safe to run in an executor thread
    return s_rsa.PriKey.load(privbyts).public().dump(fmt='pem').decode()


@s_stormtypes.registry.registerLib
class LibVertex(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with the Vertex Hub.
    '''
    _storm_locals = (
        {'name': 'register', 'desc': '''
            Register this deployment with the Vertex Hub.

            Each registration generates and stores a fresh RSA keypair as this
            deployment's cryptographic identity. The returned deployment iden is
            used to authenticate subsequent Vertex Hub requests. The email address
            must belong to an existing Vertex Hub account.

            If this deployment is already registered, this raises unless ``reset``
            is set. Passing ``reset`` creates a NEW deployment which may have
            different available power-ups.''',
         'type': {'type': 'function', '_funcname': '_register',
                  'args': (
                      {'name': 'email', 'type': 'str',
                       'desc': 'The email address of the Vertex Hub account to register under.'},
                      {'name': 'name', 'type': 'str', 'default': None,
                       'desc': 'An optional name for the deployment. The Vertex Hub generates a default if not provided.'},
                      {'name': 'reset', 'type': 'boolean', 'default': False,
                       'desc': 'Re-register even if already registered, creating a new deployment.'},
                  ),
                  'returns': {'type': 'str',
                              'desc': 'The new deployment iden, or null if no Vertex Hub account exists for the email.'}}},
        {'name': 'deployment', 'desc': '''
            This deployment's Vertex Hub registration info.

            Requires admin privileges.''',
         'type': {'type': 'gtor', '_gtorfunc': '_deployment',
                  'returns': {'type': 'dict',
                              'desc': 'A dict with the deployment ``iden`` and ``pubkey``, or null if not registered.'}}},
    )
    _storm_lib_path = ('vertex',)
    _storm_lib_perms = (
        {'perm': ('vertex', 'register'), 'gate': 'cortex',
         'desc': 'Permits a user to register the deployment with the Vertex Hub.'},
    )

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name=name)
        self.gtors['deployment'] = self._deployment

    def getObjLocals(self):
        return {
            'register': self._register,
        }

    async def _deployment(self):
        self.runt.reqAdmin()

        core = self.runt.view.core

        depl = core.getMeta('vertex:deployment')
        if depl is None:
            return None

        pubkey = await s_coro.executor(_rsaPubPem, depl.get('rsakey'))
        return {'iden': depl.get('iden'), 'pubkey': pubkey}

    async def _register(self, email, name=None, reset=False):
        self.runt.confirm(('vertex', 'register'))

        email = await s_stormtypes.tostr(email)
        name = await s_stormtypes.tostr(name, noneok=True)
        reset = await s_stormtypes.tobool(reset)

        core = self.runt.view.core

        # guard against accidentally re-registering an already-registered deployment
        if not reset and core.getMeta('vertex:deployment') is not None:
            mesg = 'Deployment already registered; use reset to create a new deployment.'
            raise s_exc.BadState(mesg=mesg)

        # generate a fresh keypair for this (re-)registration as the deployment's
        # cryptographic identity. RSA key generation is CPU bound, so run it in the
        # executor pool to keep the ioloop responsive.
        prikey = await s_coro.executor(s_rsa.PriKey.generate, DEPLOY_KEY_BITS)

        body = {
            'email': email,
            'pubkey': s_common.ehex(prikey.public().dump()),
        }
        if name is not None:
            body['name'] = name

        code, data = await _hubResp(self.runt, 'POST', '/api/v3/hub/deployments/register', json=body)

        # the hub requires a pre-existing account for the email; report the miss as
        # None so the vertex.register command can guide the user rather than error
        if code == 404 and isinstance(data, dict) and data.get('code') == 'NoSuchUser':
            return None

        iden = s_httpapi.result(code, data)

        # store the deployment iden + keypair as one nexus-replicated value (the
        # public key is derived from the private key on demand). The vertex:deployment
        # meta hook re-keys any per-deployment Storm packages when the key rotates.
        await core.setMeta('vertex:deployment', {'iden': iden, 'rsakey': prikey.dump()})

        return iden


@s_stormtypes.registry.registerLib
class LibVertexPackages(s_stormtypes.Lib):
    '''
    A Storm Library for retrieving packages from the Vertex Hub.
    '''
    _storm_locals = (
        {'name': 'list', 'desc': 'List the packages available to this deployment.',
         'type': {'type': 'function', '_funcname': '_list',
                  'returns': {'type': 'list', 'desc': 'A list of available package info dictionaries.'}}},
        {'name': 'versions', 'desc': 'List the available versions of a package.',
         'type': {'type': 'function', '_funcname': '_versions',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the package.'},
                      {'name': 'match', 'type': 'str', 'default': None,
                       'desc': 'An optional version prefix used to filter the results.'},
                  ),
                  'returns': {'type': 'list', 'desc': 'A list of available version strings.'}}},
        {'name': 'get', 'desc': '''
            Retrieve a package definition from the Vertex Hub without installing it.''',
         'type': {'type': 'function', '_funcname': '_get',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the package.'},
                      {'name': 'version', 'type': 'str', 'default': None,
                       'desc': 'The version to retrieve. Defaults to the latest version.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The package definition.'}}},
        {'name': 'install', 'desc': '''
            Install a package from the Vertex Hub.

            Any files the package declares are downloaded into the Cortex Axon before the
            package is added, so a package is never installed without its files.''',
         'type': {'type': 'function', '_funcname': '_install',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the package to install.'},
                      {'name': 'version', 'type': 'str', 'default': None,
                       'desc': 'The version to install. Defaults to the latest version.'},
                  ),
                  'returns': {'type': 'dict', 'desc': 'The installed package definition.'}}},
    )
    _storm_lib_path = ('vertex', 'packages')
    _storm_lib_perms = (
        {'perm': ('vertex', 'packages', 'list'), 'gate': 'cortex',
         'desc': 'Permits a user to list packages available from the Vertex Hub.'},
        {'perm': ('vertex', 'packages', 'install'), 'gate': 'cortex',
         'desc': 'Permits a user to install packages from the Vertex Hub.'},
    )

    def getObjLocals(self):
        return {
            'get': self._get,
            'list': self._list,
            'versions': self._versions,
            'install': self._install,
        }

    def _deployIden(self):
        depl = self.runt.view.core.getMeta('vertex:deployment')
        if depl is None:
            mesg = 'Deployment not registered; run vertex.register first.'
            raise s_exc.BadState(mesg=mesg)

        return depl.get('iden')

    @s_stormtypes.stormfunc(readonly=True)
    async def _list(self):
        self.runt.confirm(('vertex', 'packages', 'list'))
        iden = self._deployIden()
        return await _hubReq(self.runt, 'GET', f'/api/v3/hub/deployments/{iden}/packages')

    @s_stormtypes.stormfunc(readonly=True)
    async def _versions(self, name, match=None):
        self.runt.confirm(('vertex', 'packages', 'list'))

        name = await s_stormtypes.tostr(name)
        match = await s_stormtypes.tostr(match, noneok=True)

        params = {}
        if match is not None:
            params['match'] = match

        iden = self._deployIden()
        name = urllib.parse.quote(name, safe='')
        return await _hubReq(self.runt, 'GET', f'/api/v3/hub/deployments/{iden}/packages/{name}',
                             params=params)

    async def _pkgPath(self, name, version):
        name = await s_stormtypes.tostr(name)
        version = await s_stormtypes.tostr(version, noneok=True)
        if version is None:
            version = 'latest'

        iden = self._deployIden()
        name = urllib.parse.quote(name, safe='')
        version = urllib.parse.quote(version, safe='')
        return f'/api/v3/hub/deployments/{iden}/packages/{name}/{version}'

    @s_stormtypes.stormfunc(readonly=True)
    async def _get(self, name, version=None):
        # the full pkgdef is what install would add, so it requires the same perm
        self.runt.confirm(('vertex', 'packages', 'install'))
        path = await self._pkgPath(name, version)
        return await _hubReq(self.runt, 'GET', path)

    async def _downloadPkgFiles(self, pkgdef):
        '''
        Download the files declared by a package into the Cortex Axon, by sha256.

        A download failure raises, and runs before the package is added, so a package is
        never installed without the files it declares. The Vertex Hub requires the files
        to be uploaded before a package may be published, so a miss here means a problem
        reaching the hub rather than an incomplete package.
        '''
        files = pkgdef.get('files')
        if not files:
            return

        core = self.runt.view.core

        # resolve the concrete version rather than the caller's (possibly latest)
        path = await self._pkgPath(pkgdef.get('name'), pkgdef.get('version'))

        ssl = {'verify': core._vertex_hub_ssl_verify}
        headers = {'X-Synapse-Version': s_version.version}

        axon = await core.getAxon()

        for filedef in files.values():

            sha256 = filedef.get('sha256')
            if await axon.has(s_common.uhex(sha256)):
                continue

            url = f'{core._vertex_hub_url}{path}/files/{sha256}'

            resp = await axon.wget(url, headers=headers, ssl=ssl)

            if not resp.get('ok') or resp.get('code') != 200:
                mesg = resp.get('mesg', resp.get('reason'))
                mesg = f'Failed to download package file {sha256}: {mesg}'
                raise s_exc.StormRuntimeError(mesg=mesg, sha256=sha256)

            # the Axon stores the response body regardless of what it contains, so a
            # mismatch means the file we asked for is still missing (no cleanup needed,
            # the bytes we did get live under their own hash)
            if (gotsha256 := resp['hashes']['sha256']) != sha256:
                mesg = f'Package file {sha256} downloaded as {gotsha256}.'
                raise s_exc.StormRuntimeError(mesg=mesg, sha256=sha256, gotsha256=gotsha256)

    async def _install(self, name, version=None):
        self.runt.confirm(('vertex', 'packages', 'install'))

        path = await self._pkgPath(name, version)
        pkgdef = await _hubReq(self.runt, 'GET', path)

        # the files must be in the Axon before an onload query may read them
        await self._downloadPkgFiles(pkgdef)

        await self.runt.view.core.addStormPkg(pkgdef)
        return pkgdef
