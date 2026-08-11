import os
import hashlib

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.httpapi as s_httpapi
import synapse.lib.schemas as s_schemas
import synapse.lib.crypto.tinfoil as s_tinfoil

import synapse.tests.utils as s_t_utils

# a minimal package definition served by the mock hub
TESTPKG = {'name': 'testpkg', 'version': '1.0.0'}

class HubRegister(s_httpapi.Handler):

    async def post(self):
        body = self.getJsonBody()
        if body is None:  # pragma: no cover
            return

        # record what the deployment sent so the test can assert on it
        self.cell._vtxtest['register'] = body
        self.cell._vtxtest['register:headers'] = dict(self.request.headers)

        # emails with no hub account are rejected (the client turns this into a null)
        if body.get('email') == 'nobody@vertex.link':
            self.set_status(404)
            return self.sendRestErr('NoSuchUser', 'no such account')

        # the hub returns just the new deployment iden
        return self.sendRestRetn(s_common.guid())

class HubPackages(s_httpapi.Handler):

    async def get(self, iden):
        self.cell._vtxtest['pkglist:iden'] = iden
        self.cell._vtxtest['pkglist:headers'] = dict(self.request.headers)
        return self.sendRestRetn([{
            'name': 'testpkg', 'latest': '1.1.0', 'description': 'A test package.',
            'builds': {'available': [{'version': '1.0.0', 'created': 1600000000000000},
                                     {'version': '1.1.0', 'created': 1700000000000000}],
                       'compatible': ['1.1.0', '1.0.0']},
        }])

class HubVersions(s_httpapi.Handler):

    async def get(self, iden, name):
        self.cell._vtxtest['versions:name'] = name
        self.cell._vtxtest['versions:headers'] = dict(self.request.headers)
        vers = [{'version': v, 'created': c} for (v, c) in
                (('1.0.0', 1500000000000000), ('1.1.0', 1600000000000000), ('2.0.0', 1700000000000000))]
        match = self.get_argument('match', None)
        if match is not None:
            vers = [v for v in vers if v['version'].startswith(match)]

        return self.sendRestRetn(vers)

class HubPkgdef(s_httpapi.Handler):

    async def get(self, iden, name, version):
        self.cell._vtxtest['pkgdef:version'] = version
        return self.sendRestRetn(dict(TESTPKG))

class HubError(s_httpapi.Handler):

    async def get(self, iden, name, version):
        return self.sendRestErr('BadArg', 'no such package')

class HubFilesPkgdef(s_httpapi.Handler):
    '''
    Serve a pkgdef whose files section is built from the cell's _vtxtest state.
    '''
    async def get(self, iden, name, version):
        pkgdef = dict(TESTPKG)
        pkgdef['files'] = self.cell._vtxtest['files']
        return self.sendRestRetn(pkgdef)

class HubFile(s_httpapi.Handler):
    '''
    Serve a package file as raw bytes, like the real hub file endpoint.
    '''
    async def get(self, iden, name, version, sha256):
        self.cell._vtxtest.setdefault('fileurls', []).append(sha256)
        self.cell._vtxtest['file:version'] = version

        byts = self.cell._vtxtest['filebytes'].get(sha256)
        if byts is None:
            self.set_status(404)
            return self.sendRestErr('NoSuchFile', f'no file {sha256}')

        self.set_header('Content-Type', 'application/octet-stream')
        self.write(byts)
        return self.finish()

class HubBadJson(s_httpapi.Handler):

    async def get(self, iden):
        self.set_header('Content-Type', 'application/json')
        return self.write(b'this is not json')

class VertexStormTest(s_t_utils.SynTest):

    async def _addHubApis(self, core):
        core.addHttpApi('/api/v3/hub/deployments/register', HubRegister, {'cell': core})
        core.addHttpApi(r'/api/v3/hub/deployments/([0-9a-f]{32})/packages', HubPackages, {'cell': core})
        # deliberately wider than the real hub routes ([\w.-]+) so a package name carrying
        # path separators still resolves here -- that is what proves the client escaped it
        # into a single segment rather than the request escaping to another route
        core.addHttpApi(r'/api/v3/hub/deployments/([0-9a-f]{32})/packages/([^/]+)', HubVersions, {'cell': core})
        core.addHttpApi(r'/api/v3/hub/deployments/([0-9a-f]{32})/packages/([^/]+)/([^/]+)', HubPkgdef, {'cell': core})

    async def test_stormlib_vertex(self):

        async with self.getTestCore() as core:

            core._vtxtest = {}

            addr, port = await core.addHttpsPort(0)
            await self._addHubApis(core)

            # point the deployment at our local mock hub (self signed cert)
            core._vertex_hub_url = f'https://127.0.0.1:{port}'
            core._vertex_hub_ssl_verify = False

            # not registered yet -> package APIs fail (BadState) + deployment() is null
            with self.raises(s_exc.BadState):
                await core.callStorm('return($lib.vertex.packages.list())')
            msgs = await core.stormlist('vertex.packages.list')
            self.stormIsInErr('not registered', msgs)
            self.none(await core.callStorm('return($lib.vertex.deployment)'))

            # register the deployment; the hub returns just the new deployment iden,
            # which is persisted in cell metadata
            deploy = await core.callStorm('return($lib.vertex.register(visi@vertex.link))')
            self.len(32, deploy)
            self.eq(deploy, core.getMeta('vertex:deployment').get('iden'))

            reg = core._vtxtest.get('register')
            self.eq(reg.get('email'), 'visi@vertex.link')
            # _hubResp tags every hub request, including register, with the version
            self.nn(core._vtxtest.get('register:headers').get('X-Synapse-Version'))
            self.notin('secret', reg)
            # no name sent by default -> the hub applies its own default
            self.notin('name', reg)
            self.nn(reg.get('pubkey'))

            # the deployment iden + keypair are persisted as one meta value; the
            # deployment key is 3072-bit and the pubkey sent to the hub derives from it
            depl = core.getMeta('vertex:deployment')
            self.eq(deploy, depl.get('iden'))
            prikey = s_rsa.PriKey.load(depl.get('rsakey'))
            self.eq(3072, prikey.priv.key_size)
            self.eq(s_common.ehex(prikey.public().dump()), reg.get('pubkey'))

            # $lib.vertex.deployment returns the iden + PEM-encoded pubkey (admin only)
            info = await core.callStorm('return($lib.vertex.deployment)')
            self.eq(deploy, info.get('iden'))
            self.isin('-----BEGIN PUBLIC KEY-----', info.get('pubkey'))
            self.eq(prikey.public().dump(fmt='pem').decode(), info.get('pubkey'))

            luser = await core.auth.addUser('lowuser')
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.vertex.deployment)', opts={'user': luser.iden})

            # re-registering an already-registered deployment is guarded; --reset is required
            with self.raises(s_exc.BadState) as exc:
                await core.callStorm('return($lib.vertex.register(visi@vertex.link))')
            self.isin('already registered', exc.exception.get('mesg'))
            msgs = await core.stormlist('vertex.register visi@vertex.link')
            self.stormIsInErr('already registered', msgs)
            # the guard left the stored deployment untouched
            self.eq(deploy, core.getMeta('vertex:deployment').get('iden'))

            # reset re-registers: name plumbs through, a fresh keypair is generated,
            # and a NEW deployment iden is minted
            oldrsakey = core.getMeta('vertex:deployment').get('rsakey')
            newiden = await core.callStorm(
                'return($lib.vertex.register(visi@vertex.link, name="My Deploy", reset=(true)))')
            self.eq('My Deploy', core._vtxtest.get('register').get('name'))
            self.ne(deploy, newiden)
            newdepl = core.getMeta('vertex:deployment')
            self.eq(newiden, newdepl.get('iden'))
            # a new keypair was minted and the new pubkey is what was sent to the hub
            self.ne(oldrsakey, newdepl.get('rsakey'))
            newpub = s_rsa.PriKey.load(newdepl.get('rsakey')).public()
            self.eq(s_common.ehex(newpub.dump()), core._vtxtest.get('register').get('pubkey'))

            # the --name + --reset command options both plumb through
            await core.stormlist('vertex.register visi@vertex.link --name "CLI Deploy" --reset')
            self.eq('CLI Deploy', core._vtxtest.get('register').get('name'))

            # the command (with --reset) confirms success and links directly to the editor
            msgs = await core.stormlist('vertex.register visi@vertex.link --reset')
            self.stormIsInPrint('Registered deployment', msgs)
            self.stormIsInPrint('Manage this deployment', msgs)
            regiden = core.getMeta('vertex:deployment').get('iden')
            self.stormIsInPrint(f'https://hub.vertex.link/hub/support/deployments/{regiden}', msgs)

            # an email with no hub account -> register returns null and the command
            # guides the user to create an account (--reset needed since already registered)
            self.none(await core.callStorm('return($lib.vertex.register(nobody@vertex.link, reset=(true)))'))
            msgs = await core.stormlist('vertex.register nobody@vertex.link --reset')
            self.stormIsInPrint('Create an account at https://hub.vertex.link/hub', msgs)

            # packages.list carries the deployment iden in the path + the synapse version
            # header and prints a name/version/published/description table (dates only)
            msgs = await core.stormlist('vertex.packages.list')
            self.stormIsInPrint('Name', msgs)
            self.stormIsInPrint('Published', msgs)
            self.stormIsInPrint('testpkg', msgs)
            self.stormIsInPrint('1.1.0', msgs)
            self.stormIsInPrint('2023-11-14', msgs)
            self.stormIsInPrint('A test package.', msgs)

            self.eq(core._vtxtest.get('pkglist:iden'), core.getMeta('vertex:deployment').get('iden'))
            headers = core._vtxtest.get('pkglist:headers')
            self.nn(headers.get('X-Synapse-Version'))

            # versions with and without a match filter (per-version metadata records)
            vers = await core.callStorm('return($lib.vertex.packages.versions(testpkg))')
            self.eq(['1.0.0', '1.1.0', '2.0.0'], [v['version'] for v in vers])
            self.eq(core._vtxtest.get('versions:name'), 'testpkg')
            # every _hubReq call carries the synapse version header, not just list
            self.nn(core._vtxtest.get('versions:headers').get('X-Synapse-Version'))

            # a package name carrying path separators is percent-escaped into a single
            # path segment, so it cannot traverse to a different hub endpoint
            await core.callStorm('return($lib.vertex.packages.versions("../../admin"))')
            self.eq('../../admin', core._vtxtest.get('versions:name'))

            vers = await core.callStorm('return($lib.vertex.packages.versions(testpkg, match="1."))')
            self.eq(['1.0.0', '1.1.0'], [v['version'] for v in vers])

            # the versions command prints a version/published table (dates only)
            msgs = await core.stormlist('vertex.packages.versions testpkg')
            self.stormIsInPrint('Version', msgs)
            self.stormIsInPrint('Published', msgs)
            self.stormIsInPrint('2.0.0', msgs)
            self.stormIsInPrint('2023-11-14', msgs)

            # --match plumbs through to the filtered rows
            msgs = await core.stormlist('vertex.packages.versions testpkg --match 1.')
            self.stormIsInPrint('1.0.0', msgs)
            self.stormIsInPrint('1.1.0', msgs)

            # get returns the pkgdef without adding it to the cortex
            pkgdef = await core.callStorm('return($lib.vertex.packages.get(testpkg, version="1.0.0"))')
            self.eq(TESTPKG, pkgdef)
            self.eq(core._vtxtest.get('pkgdef:version'), '1.0.0')
            self.none(await core.getStormPkg('testpkg'))

            # browsing the catalog is gated on the list perm, get on the install perm
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.vertex.packages.versions(testpkg))', opts={'user': luser.iden})
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.vertex.packages.get(testpkg))', opts={'user': luser.iden})

            # install adds the package to the cortex
            msgs = await core.stormlist('vertex.packages.install testpkg --version 1.0.0')
            self.stormIsInPrint('Installed testpkg at version 1.0.0', msgs)
            self.eq(core._vtxtest.get('pkgdef:version'), '1.0.0')
            self.nn(await core.getStormPkg('testpkg'))

            # install with no version defaults to 'latest' in the path
            await core.callStorm('return($lib.vertex.packages.install(testpkg))')
            self.eq(core._vtxtest.get('pkgdef:version'), 'latest')

    async def test_stormlib_vertex_pkg_files(self):

        # a real axon is required to store the downloaded package files
        async with self.getTestCluster() as clus:

            core = clus.cortex

            core._vtxtest = {}

            addr, port = await core.addHttpsPort(0)
            core.addHttpApi('/api/v3/hub/deployments/register', HubRegister, {'cell': core})
            core.addHttpApi(r'/api/v3/hub/deployments/([0-9a-f]{32})/packages/([\w.-]+)/([\w.-]+)',
                            HubFilesPkgdef, {'cell': core})
            core.addHttpApi(r'/api/v3/hub/deployments/([0-9a-f]{32})/packages/([\w.-]+)/([\w.-]+)/files/([0-9a-f]{64})',
                            HubFile, {'cell': core})

            core._vertex_hub_url = f'https://127.0.0.1:{port}'
            core._vertex_hub_ssl_verify = False

            await core.callStorm('$lib.vertex.register(visi@vertex.link)')

            axon = await core.getAxon()

            foobyts = b'package file foo'
            barbyts = b'package file bar'

            foosha256 = hashlib.sha256(foobyts).hexdigest()
            barsha256 = hashlib.sha256(barbyts).hexdigest()

            core._vtxtest['filebytes'] = {foosha256: foobyts, barsha256: barbyts}
            core._vtxtest['files'] = {'foo.dat': {'sha256': foosha256},
                                      'bar.dat': {'sha256': barsha256}}

            # a file already in the axon is not downloaded again
            await axon.put(barbyts)

            msgs = await core.stormlist('vertex.packages.install testpkg --version 1.0.0')
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('Installed testpkg at version 1.0.0', msgs)

            # both files are now in the cortex axon, but only the missing one was fetched
            self.true(await axon.has(s_common.uhex(foosha256)))
            self.true(await axon.has(s_common.uhex(barsha256)))
            self.eq([foosha256], core._vtxtest['fileurls'])

            # a package with no files does not reach for the axon at all
            core._vtxtest['files'] = {}
            core._vtxtest['fileurls'] = []
            msgs = await core.stormlist('vertex.packages.install testpkg --version 1.0.0')
            self.stormHasNoWarnErr(msgs)
            self.eq([], core._vtxtest['fileurls'])

            # an unavailable file fails the install, and the package is not added since
            # the files are downloaded before it
            await core.delStormPkg('testpkg')

            newpbyts = b'package file newp'
            newpsha256 = hashlib.sha256(newpbyts).hexdigest()
            core._vtxtest['files'] = {'newp.dat': {'sha256': newpsha256}}

            msgs = await core.stormlist('vertex.packages.install testpkg --version 1.0.0')
            self.stormIsInErr(f'Failed to download package file {newpsha256}', msgs)
            self.stormNotInPrint('Installed testpkg', msgs)
            self.false(await axon.has(s_common.uhex(newpsha256)))
            self.none(await core.getStormPkg('testpkg'))

            # ...as does a file whose contents do not match the declared sha256
            wrongsha256 = hashlib.sha256(b'these are not those bytes').hexdigest()
            core._vtxtest['filebytes'][wrongsha256] = newpbyts
            core._vtxtest['files'] = {'wrong.dat': {'sha256': wrongsha256}}

            msgs = await core.stormlist('vertex.packages.install testpkg --version 1.0.0')
            self.stormIsInErr(f'Package file {wrongsha256} downloaded as {newpsha256}', msgs)
            self.none(await core.getStormPkg('testpkg'))

            # installing 'latest' resolves the file urls with the pkgdef's concrete
            # version, since 'latest' would be ambiguous by the time it is fetched
            await axon.del_(s_common.uhex(foosha256))
            core._vtxtest['files'] = {'foo.dat': {'sha256': foosha256}}
            core._vtxtest['fileurls'] = []

            msgs = await core.stormlist('vertex.packages.install testpkg')
            self.stormHasNoWarnErr(msgs)
            self.eq([foosha256], core._vtxtest['fileurls'])
            self.eq('1.0.0', core._vtxtest['file:version'])

    async def test_stormlib_vertex_deploy_seed(self):

        async with self.getTestCore() as core:

            seed = s_common.ehex(os.urandom(32))
            salt = s_common.ehex(os.urandom(32))
            hashname = 'sha256'
            iters = 1000

            encmod = s_tinfoil.encStorm(seed, salt, hashname, iters, 'function foo() { return((42)) }')
            enccmd = s_tinfoil.encStorm(seed, salt, hashname, iters, '$lib.print(enccmdran)')

            def buildpkg(name, seedval):
                return {
                    'name': name,
                    'version': '0.0.1',
                    'metadata': {'encryption': {'seed': seedval, 'salt': salt,
                                                'pbkdf2': {'iters': iters, 'hash': hashname},
                                                'deploy': True}},
                    'modules': [{'name': f'{name}.mod', 'storm': encmod}],
                    'commands': [{'name': f'{name}cmd', 'storm': enccmd}],
                }

            # a deploy package added before registration (no private key): the package
            # is fine, this Cortex just is not registered -> BadState
            with self.raises(s_exc.BadState):
                await core.addStormPkg(buildpkg('deploypkg', seed))

            # store the deployment the way registration would
            prikey = s_rsa.PriKey.generate()
            await core.setMeta('vertex:deployment', {'iden': s_common.guid(), 'rsakey': prikey.dump()})

            # encrypt the seed to our public key, exactly as the hub does on serve
            encseed = s_common.ehex(prikey.public().encrypt(seed.encode()))

            await core.addStormPkg(buildpkg('deploypkg', encseed))

            # the persisted pkgdef keeps the seed RSA-encrypted to the deployment key
            # (the plaintext seed is never stored) and retains the deploy flag
            encryption = core._getStormPkgEncryption('deploypkg')
            self.eq(encseed, encryption.get('seed'))
            self.ne(seed, encryption.get('seed'))
            self.true(encryption.get('deploy'))

            # the module + command storm still decrypt + run at runtime
            self.eq(42, await core.callStorm('return($lib.import(deploypkg.mod).foo())'))
            msgs = await core.stormlist('deploypkgcmd')
            self.stormIsInPrint('enccmdran', msgs)

            # the long RSA-encrypted seed length is only allowed for a deploy package: a
            # plaintext seed is always exactly 32 bytes, so an over-long one without
            # deploy=True fails pkgdef validation
            plainpkg = buildpkg('plainpkg', s_common.ehex(os.urandom(384)))
            plainpkg['metadata']['encryption'].pop('deploy')
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidPkgdef(plainpkg)

            # the same over-long seed is valid once the package declares deploy=True,
            # and a plaintext 32 byte seed stays valid without it
            s_schemas.reqValidPkgdef(buildpkg('deploylen', s_common.ehex(os.urandom(384))))
            plainok = buildpkg('plainok', seed)
            plainok['metadata']['encryption'].pop('deploy')
            s_schemas.reqValidPkgdef(plainok)

            # a seed encrypted to a different key cannot be recovered -> CryptoErr
            other = s_rsa.PriKey.generate()
            badseed = s_common.ehex(other.public().encrypt(seed.encode()))
            with self.raises(s_exc.CryptoErr):
                await core.addStormPkg(buildpkg('deploypkg2', badseed))

            # a loaded deploy package whose seed cannot be decrypted with the old key
            # is logged and skipped, without stopping the good package from re-keying
            core.stormpkgs['badpkg'] = {
                'name': 'badpkg', 'version': '0.0.1',
                'metadata': {'encryption': {'seed': badseed, 'salt': salt,
                                            'pbkdf2': {'iters': iters, 'hash': hashname},
                                            'deploy': True}},
            }

            # rotating the deployment private key re-keys the deploy package: its seed
            # is re-encrypted to the new key (still never plaintext, deploy retained)
            newkey = s_rsa.PriKey.generate()
            with self.getLoggerStream('synapse.cortex') as stream:
                await core.setMeta('vertex:deployment', {'iden': s_common.guid(), 'rsakey': newkey.dump()})
                await stream.expect('Unable to re-key per-deployment Storm package badpkg', timeout=6)

            rekeyed = core._getStormPkgEncryption('deploypkg')
            self.ne(encseed, rekeyed.get('seed'))
            self.ne(seed, rekeyed.get('seed'))
            self.true(rekeyed.get('deploy'))
            # the re-keyed seed recovers the original seed under the new key
            self.eq(seed, (await core._reqDecEncryption(rekeyed)).get('seed'))

            # and the package still decrypts + runs under the new key
            self.eq(42, await core.callStorm('return($lib.import(deploypkg.mod).foo())'))
            msgs = await core.stormlist('deploypkgcmd')
            self.stormIsInPrint('enccmdran', msgs)

            # cellmeta commits after the hook, so a crash mid-rotation can leave a package
            # already re-keyed while the old deployment is still current. Re-running the
            # hook converges instead of failing, because the new key is tried first.
            # snapshot the ciphertext first: the hook mutates the encryption dict in place
            # and _getStormPkgEncryption hands back that same live dict
            prevseed = rekeyed.get('seed')

            olddepl = {'iden': s_common.guid(), 'rsakey': prikey.dump()}
            await core._onSetMetaVertexDeployment(core.getMeta('vertex:deployment'), olddepl)

            replayed = core._getStormPkgEncryption('deploypkg')
            self.true(replayed.get('deploy'))
            # RSA-OAEP is randomized, so a changed ciphertext proves the seed really was
            # recovered with the new key and re-encrypted, rather than the package being
            # skipped as undecryptable
            self.ne(prevseed, replayed.get('seed'))
            self.eq(seed, (await core._reqDecEncryption(replayed)).get('seed'))
            self.eq(42, await core.callStorm('return($lib.import(deploypkg.mod).foo())'))

    async def test_stormlib_vertex_devenvars(self):
        # undocumented dev-only overrides for the fixed hub location
        with self.setTstEnvars(SYNDEV_VERTEX_HUB_URL='https://hub.example.com',
                               SYNDEV_VERTEX_HUB_SSL_VERIFY='0'):
            async with self.getTestCore() as core:
                self.eq('https://hub.example.com', core._vertex_hub_url)
                self.false(core._vertex_hub_ssl_verify)

        # absent -> the fixed production defaults apply
        async with self.getTestCore() as core:
            self.eq('https://hub.vertex.link', core._vertex_hub_url)
            self.true(core._vertex_hub_ssl_verify)

    async def test_stormlib_vertex_reset_mirror(self):

        async with self.getTestCluster({'cortex': {'mirrors': 1}}) as clus:

            core00 = clus.cortex
            core01 = clus.svcs['001.cortex']

            # point $lib.vertex at a mock hub served by the leader
            core00._vtxtest = {}
            addr, port = await core00.addHttpsPort(0)
            core00.addHttpApi('/api/v3/hub/deployments/register', HubRegister, {'cell': core00})
            core00._vertex_hub_url = f'https://127.0.0.1:{port}'
            core00._vertex_hub_ssl_verify = False

            # register the deployment (mints the first RSA key)
            deploy = await core00.callStorm('return($lib.vertex.register(visi@vertex.link))')
            self.len(32, deploy)

            # install a per-deployment package encrypted to the current deployment key
            seed = s_common.ehex(os.urandom(32))
            salt = s_common.ehex(os.urandom(32))
            encmod = s_tinfoil.encStorm(seed, salt, 'sha256', 1000, 'function foo() { return((42)) }')
            pubkey = s_rsa.PriKey.load(core00.getMeta('vertex:deployment').get('rsakey')).public()
            pkgdef = {
                'name': 'deploypkg',
                'version': '0.0.1',
                'metadata': {'encryption': {'seed': s_common.ehex(pubkey.encrypt(seed.encode())),
                                            'salt': salt, 'pbkdf2': {'iters': 1000, 'hash': 'sha256'},
                                            'deploy': True}},
                'modules': [{'name': 'deploypkg.mod', 'storm': encmod}],
            }
            await core00.addStormPkg(pkgdef)

            # the package runs on the leader and (after replication) on the mirror
            await core01.sync()
            self.eq(42, await core00.callStorm('return($lib.import(deploypkg.mod).foo())'))
            self.eq(42, await core01.callStorm('return($lib.import(deploypkg.mod).foo())'))

            # both nodes store the same first-key ciphertext (replicated via pkg:add)
            firstseed = core00._getStormPkgEncryption('deploypkg').get('seed')
            self.eq(firstseed, core01._getStormPkgEncryption('deploypkg').get('seed'))

            # reset the registration: a new deployment iden + a fresh RSA key. The
            # vertex:deployment rotation re-keys the deploy package on the leader and,
            # via the replicated meta:set, on the mirror too.
            newdeploy = await core00.callStorm('return($lib.vertex.register(visi@vertex.link, reset=(true)))')
            self.ne(deploy, newdeploy)

            await core01.sync()

            # each node re-encrypted its package seed to the new key (still not plaintext)
            self.ne(firstseed, core00._getStormPkgEncryption('deploypkg').get('seed'))
            self.ne(firstseed, core01._getStormPkgEncryption('deploypkg').get('seed'))
            self.ne(seed, core00._getStormPkgEncryption('deploypkg').get('seed'))

            # and the package still functions on the leader AND the mirror
            self.eq(42, await core00.callStorm('return($lib.import(deploypkg.mod).foo())'))
            self.eq(42, await core01.callStorm('return($lib.import(deploypkg.mod).foo())'))

    async def test_stormlib_vertex_errors(self):

        async with self.getTestCore() as core:

            core._vtxtest = {}

            addr, port = await core.addHttpsPort(0)
            core.addHttpApi('/api/v3/hub/deployments/register', HubRegister, {'cell': core})
            core.addHttpApi(r'/api/v3/hub/deployments/([0-9a-f]{32})/packages/([\w.-]+)/([\w.-]+)', HubError, {'cell': core})
            core.addHttpApi(r'/api/v3/hub/deployments/([0-9a-f]{32})/packages', HubBadJson, {'cell': core})

            core._vertex_hub_url = f'https://127.0.0.1:{port}'
            core._vertex_hub_ssl_verify = False

            # a registered deployment
            await core.callStorm('$lib.vertex.register(visi@vertex.link)')

            # a hub REST error is re-raised as the SynErr named by its code (BadArg)
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.vertex.packages.install(newp)')
            msgs = await core.stormlist('vertex.packages.install newp')
            self.stormIsInErr('no such package', msgs)

            # a non-JSON response body -> generic failure defaulting to SynErr
            with self.raises(s_exc.SynErr) as exc:
                await core.callStorm('$lib.vertex.packages.list()')
            self.eq(s_exc.SynErr, type(exc.exception))
            self.isin('REST API request failed', exc.exception.get('mesg'))

            # a connection failure (nothing listening) -> generic failure mesg
            core._vertex_hub_url = f'https://127.0.0.1:{port + 1}'
            msgs = await core.stormlist('vertex.packages.list')
            self.stormIsInErr('REST API request failed', msgs)
