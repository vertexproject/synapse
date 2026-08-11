import os
import stat
import shutil
import hashlib
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.certdir as s_certdir
import synapse.lib.schemas as s_schemas
import synapse.lib.version as s_version
import synapse.lib.crypto.rsa as s_rsa
import synapse.lib.crypto.tinfoil as s_tinfoil

import synapse.tests.utils as s_test
import synapse.tests.files as s_files

import synapse.tools.storm.pkg.gen as s_genpkg

dirname = os.path.dirname(__file__)

class GenPkgTest(s_test.SynTest):

    @staticmethod
    def setDirFileModes(dirn, mode):
        '''
        Set all files in a directory to a new mode.
        '''
        for root, dirs, files in os.walk(dirn):
            for fn in files:
                fp = os.path.join(root, fn)
                os.chmod(fp, mode=mode)

    def skipIfWriteableFiles(self, dirn):
        '''
        If any files in dirn are not readonly, skip the test.
        '''
        for root, dirs, files in os.walk(dirn):
            for fn in files:
                fp = os.path.join(root, fn)
                try:
                    with open(fp, 'w+b') as fd:  # pragma: no cover
                        self.skipTest('Writable files found in directory, test likely run as root.')
                except PermissionError:
                    continue

    async def test_tools_genpkg(self):

        with self.raises(s_exc.NoSuchFile):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'newpfile.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.BadPkgDef):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'nopath.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.BadPkgDef):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'nomime.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.BadPkgDef):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'nosuchfile.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.SchemaViolation):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badcmdname.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.MustBeJsonSafe):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badjsonpkg.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.SchemaViolation):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badapidef.yaml')
            await s_genpkg.main((ymlpath,))

        # loadPkgProto materializes command storm files before schema
        # validation runs, so load this invalid proto from a mirrored copy of
        # the fixtures to avoid creating command files in the source tree.
        with self.getTestDir(mirror='stormpkg') as tdir:
            ymlpath = s_common.genpath(tdir, 'badendpoints.yaml')
            with self.raises(s_exc.SchemaViolation):
                await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.BadPkgDef):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badinits.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.SchemaViolation):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badvaultskeys.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.BadArg):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badvaultsschema.yaml')
            await s_genpkg.main((ymlpath,))

        datapath = s_common.genpath(dirname, 'files', 'stormpkg', 'files', 'data.dat')
        with open(datapath, 'rb') as fd:
            datasha256 = hashlib.sha256(fd.read()).hexdigest()

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml')

        # the package declares a file, so --push needs a Cortex with a real Axon
        async with self.getTestCluster() as clus:
            core = clus.cortex

            savepath = s_common.genpath(core.dirn, 'testpkg.json')
            yamlpath = s_common.genpath(core.dirn, 'testpkg.yaml')
            newppath = s_common.genpath(core.dirn, 'newp.yaml')

            url = core.getLocalUrl()
            argv = ('--encrypt', '--push', url, '--save', savepath, ymlpath)

            outp = self.getTestOutp()
            await s_genpkg.main(argv, outp=outp)

            # pushing to a Cortex uploads the declared files into its Axon
            outp.expect(f'Uploading file: {datapath} ({datasha256})')
            self.true(await core.callStorm('return($lib.axon.has($s))', opts={'vars': {'s': datasha256}}))

            msgs = await core.stormlist('testpkgcmd')
            self.stormIsInErr('argument <foo> is required', msgs)
            msgs = await core.stormlist('$mod=$lib.import(testmod) $lib.print($mod)')
            self.stormIsInPrint('Imported Module testmod', msgs)

            gdefs = await core.callStorm('return($lib.graph.list())')
            self.len(1, gdefs)
            self.eq(gdefs[0]['name'], 'testgraph')
            self.eq(gdefs[0]['power-up'], 'testpkg')

            pdef = s_common.yamlload(savepath)
            s_common.yamlsave(pdef, yamlpath)

            self.eq(pdef['name'], 'testpkg')
            self.eq(pdef['version'], '0.0.1')
            self.eq(pdef['modules'][0]['name'], 'testmod')
            self.eq(pdef['modules'][1]['name'], 'apimod')
            self.eq(pdef['modules'][2]['name'], 'testpkg.testext')
            self.eq(pdef['modules'][3]['name'], 'testpkg.testextfile')
            self.eq(pdef['commands'][0]['name'], 'testpkgcmd')

            # storm queries are encrypted by default; the seed/salt/pbkdf live under metadata
            encryption = pdef['metadata']['encryption']
            seed = encryption['seed']
            salt = encryption['salt']
            self.len(64, seed)
            self.len(64, salt)

            # the pbkdf params used are captured in the encryption metadata
            self.eq(encryption['pbkdf2'], {
                'iters': s_tinfoil.STORM_PKG_PBKDF2_ITERS,
                'hash': s_tinfoil.STORM_PKG_PBKDF2_HASH,
            })
            hashname = encryption['pbkdf2']['hash']
            iters = encryption['pbkdf2']['iters']

            # the stored storm must not be the plaintext
            self.ne(pdef['modules'][0]['storm'], 'inet:ip\n')

            # ...and must decrypt back to the original queries
            self.eq(s_tinfoil.decStorm(seed, salt, hashname, iters, pdef['modules'][0]['storm']), 'inet:ip\n')
            self.isin('function search', s_tinfoil.decStorm(seed, salt, hashname, iters, pdef['modules'][1]['storm']))
            self.eq(s_tinfoil.decStorm(seed, salt, hashname, iters, pdef['modules'][2]['storm']), 'inet:fqdn\n')
            self.eq(s_tinfoil.decStorm(seed, salt, hashname, iters, pdef['modules'][3]['storm']), 'inet:fqdn\n')
            self.eq(s_tinfoil.decStorm(seed, salt, hashname, iters, pdef['commands'][0]['storm']), 'inet:ip\n')

            self.eq(pdef['commands'][0]['endpoints'], [
                {'path': '/v1/test/one'},
                {'path': '/v1/test/two', 'url': 'https://vertex.link'},
                {'path': '/v1/test/three', 'desc': 'endpoint three'},
            ])

            self.eq(pdef['perms'][0]['perm'], ['power-ups', 'testpkg', 'user'])
            self.eq(pdef['perms'][0]['gate'], 'cortex')
            self.eq(pdef['perms'][0]['desc'], 'Controls user access to testpkg.')
            self.eq(pdef['perms'][0]['workflowconfig'], True)

            self.eq(pdef['configvars'][0]['name'], 'API key')
            self.eq(pdef['configvars'][0]['varname'], 'testpkg:apikey')
            self.eq(pdef['configvars'][0]['desc'], 'API key to use for querying the testpkg API.')
            self.eq(pdef['configvars'][0]['scopes'], ['global', 'self'])
            self.eq(pdef['configvars'][0]['workflowconfig'], True)
            self.eq(pdef['configvars'][0]['type'], 'hugenum')
            self.eq(pdef['configvars'][1]['name'], 'Tag Prefix')
            self.eq(pdef['configvars'][1]['varname'], 'testpkg:tag:prefix')
            self.eq(pdef['configvars'][1]['desc'], 'Tag prefix to use when recording tags.')
            self.eq(pdef['configvars'][1]['scopes'], ['global', 'self'])
            self.eq(pdef['configvars'][1]['default'], 'rep.testpkg')
            self.eq(pdef['configvars'][1]['workflowconfig'], True)
            self.eq(pdef['configvars'][1]['type'], ['inet:fqdn', ['str', 'inet:url']])

            pconfigs = pdef['vaults']['testpkg']['schema']['properties']['configs']
            psecrets = pdef['vaults']['testpkg']['schema']['properties']['secrets']
            self.eq(pconfigs['properties']['foo']['type'], 'string')
            self.eq(pconfigs['properties']['foo']['default'], 'hehe haha')
            self.eq(pconfigs['properties']['bar']['oneOf'][0]['type'], 'boolean')
            self.eq(pconfigs['properties']['bar']['oneOf'][1]['type'], 'string')
            self.eq(pconfigs['properties']['baz']['type'], 'boolean')
            self.eq(pconfigs['additionalProperties'], False)
            self.eq(psecrets['properties']['quux']['type'], 'string')
            self.eq(psecrets['properties']['quux']['minLength'], 2)
            self.eq(psecrets['required'], ('quux',))

            self.eq(pdef['logo']['mime'], 'image/svg')
            self.eq(pdef['logo']['file'], 'c3R1ZmYK')

            # everything under the files directory ships, keyed by the path relative
            # to that directory; the contents are never embedded in the package
            datapath = s_common.genpath(dirname, 'files', 'stormpkg', 'files', 'data.dat')
            with open(datapath, 'rb') as fd:
                datasha256 = hashlib.sha256(fd.read()).hexdigest()

            nestpath = s_common.genpath(dirname, 'files', 'stormpkg', 'files', 'sub', 'nested.dat')
            with open(nestpath, 'rb') as fd:
                nestsha256 = hashlib.sha256(fd.read()).hexdigest()

            self.eq(pdef['files'], {
                'data.dat': {'sha256': datasha256},
                'sub/nested.dat': {'sha256': nestsha256},
            })

            # the walk is recursive and ordered, so a rebuild is deterministic
            self.eq(['data.dat', 'sub/nested.dat'], list(pdef['files']))

            self.len(3, pdef['optic']['workflows'])

            wflow = pdef['optic']['workflows']['testpkg-foo']
            self.eq(wflow, {'name': 'foo', 'desc': 'a foo workflow'})

            wflow = pdef['optic']['workflows']['testpkg-bar']
            self.eq(wflow, {'name': 'bar', 'desc': 'this is an inline workflow'})

            wflow = pdef['optic']['workflows']['testpkg-baz']
            self.eq(wflow, {'name': 'real-baz', 'desc': 'this is the real baz desc'})

            build = pdef.get('build')
            self.nn(build)
            self.nn(build.get('time'))
            self.eq(build.get('synapse:version'), s_version.version)
            self.eq(build.get('synapse:commit'), s_version.commit)

            ret = await core.callStorm('''
                $s = $lib.pkg.get(testpkg).vaults.testpkg.schema.properties.configs
                return($lib.json.schema($s).validate(({"bar": true, "baz": true})))
            ''')
            self.eq([True, {
                'foo': 'hehe haha',
                'bar': True,
                'baz': True,
            }], ret)

            ret = await core.callStorm('''
                $s = $lib.pkg.get(testpkg).vaults.testpkg.schema.properties.secrets
                return($lib.json.schema($s).validate(({"quux": "foo"})))
            ''')
            self.eq([True, {'quux': 'foo'}], ret)

            # encryption is opt-in; without --encrypt the storm queries are plaintext
            noencpath = s_common.genpath(core.dirn, 'testpkg_noenc.json')
            argv = ('--save', noencpath, ymlpath)

            await s_genpkg.main(argv)

            noenc_pdef = s_common.yamlload(noencpath)

            self.none(noenc_pdef.get('metadata'))
            self.eq(noenc_pdef['modules'][0]['storm'], 'inet:ip\n')
            self.isin('function search', noenc_pdef['modules'][1]['storm'])
            self.eq(noenc_pdef['modules'][2]['storm'], 'inet:fqdn\n')
            self.eq(noenc_pdef['modules'][3]['storm'], 'inet:fqdn\n')
            self.eq(noenc_pdef['commands'][0]['storm'], 'inet:ip\n')

            # No push, no save:  nothing to do
            argv = (ymlpath,)
            retn = await s_genpkg.main(argv)
            self.eq(1, retn)

            # An already built package may be saved back out
            rebuiltpath = s_common.genpath(core.dirn, 'testpkg_rebuilt.json')
            argv = ('--no-build', '--save', rebuiltpath, savepath)
            retn = await s_genpkg.main(argv)
            self.eq(0, retn)
            self.eq(s_common.yamlload(savepath), s_common.yamlload(rebuiltpath))

            # ...including in place over the input file
            argv = ('--no-build', '--save', rebuiltpath, rebuiltpath)
            retn = await s_genpkg.main(argv)
            self.eq(0, retn)
            self.eq(s_common.yamlload(savepath), s_common.yamlload(rebuiltpath))

            # Re-pushing the proto finds the file already in the Axon
            outp = self.getTestOutp()
            argv = ('--push', url, ymlpath)
            self.eq(0, await s_genpkg.main(argv, outp=outp))
            outp.expect(f'Skipping existing file: {datapath} ({datasha256})')

            # Push a premade yaml. An already built package has no files directory
            # beside it, so they cannot be uploaded -- warn, but still push the package.
            outp = self.getTestOutp()
            argv = ('--push', url, '--no-build', yamlpath)
            retn = await s_genpkg.main(argv, outp=outp)
            self.eq(0, retn)
            outp.expect('No local file for data.dat')

            # Push a premade json
            argv = ('--no-build', '--push', url, savepath)
            retn = await s_genpkg.main(argv)
            self.eq(0, retn)

            # Cannot push a file that does not exist
            argv = ('--push', url, '--no-build', newppath)
            retn = await s_genpkg.main(argv)
            self.eq(1, retn)

            # A file which changes between being hashed and being uploaded would leave
            # the pushed package definition referencing bytes the Axon does not have
            with self.getTestDir() as tdir:

                datafile = s_common.genpath(s_common.gendir(tdir, 'files'), 'data.dat')
                with open(datafile, 'wb') as fd:
                    fd.write(b'fresh package file bytes')

                otherfile = s_common.genpath(tdir, 'other.dat')
                with open(otherfile, 'wb') as fd:
                    fd.write(b'these are not those bytes')

                protopath = s_common.genpath(tdir, 'filespkg.yaml')
                s_common.yamlsave({'name': 'filespkg', 'version': '0.0.1'}, protopath)

                newsha256 = s_genpkg.getFileSha256(datafile)

                # stand in for the file changing after loadPkgProto hashed it. the
                # push resolves the contents through getPkgProtoFiles, so only that
                # lookup is replaced -- the built package keeps the real sha256.
                with mock.patch.object(s_genpkg, 'getPkgProtoFiles',
                                       lambda path: {'data.dat': otherfile}):
                    with self.raises(s_exc.BadPkgDef) as cm:
                        await s_genpkg.main(('--push', url, protopath))

                self.eq(newsha256, cm.exception.get('sha256'))
                self.ne(newsha256, cm.exception.get('gotsha256'))

                # ...and the package was not added
                self.none(await core.getStormPkg('filespkg'))

            # a package which declares no files never reaches for the Axon, so a null
            # proxy here is enough to prove it is not used
            await s_genpkg.pushPkgFiles(outp, None, {'name': 'nofiles', 'version': '0.0.1'}, newppath)

    def test_tools_genpkg_files(self):

        protodir = s_common.genpath(dirname, 'files', 'stormpkg')
        datapath = s_common.genpath(protodir, 'files', 'data.dat')

        with open(datapath, 'rb') as fd:
            datasha256 = hashlib.sha256(fd.read()).hexdigest()

        self.eq(datasha256, s_genpkg.getFileSha256(datapath))

        with self.raises(s_exc.NoSuchFile) as cm:
            s_genpkg.getFileSha256(s_common.genpath(protodir, 'files', 'newp.dat'))
        self.isin('files/newp.dat', cm.exception.get('path'))

        nestpath = s_common.genpath(protodir, 'files', 'sub', 'nested.dat')

        # a package ships everything under its files directory, recursively, keyed
        # by the path relative to that directory
        ymlpath = s_common.genpath(protodir, 'testpkg.yaml')
        self.eq([('data.dat', datapath), ('sub/nested.dat', nestpath)],
                list(s_genpkg.iterPkgProtoFiles(ymlpath)))

        # a storm service serves its package files from the same mapping
        self.eq({'data.dat': datapath, 'sub/nested.dat': nestpath},
                s_genpkg.getPkgProtoFiles(ymlpath))

        # a prototype with no files directory ships none
        with self.getTestDir() as tdir:
            nofiles = s_common.genpath(tdir, 'nofiles.yaml')
            s_common.yamlsave({'name': 'nofiles', 'version': '0.0.1'}, nofiles)
            self.eq({}, s_genpkg.getPkgProtoFiles(nofiles))
            self.notin('files', s_genpkg.loadPkgProto(nofiles))

        with self.raises(s_exc.NoSuchFile):
            list(s_genpkg.iterPkgProtoFiles(s_common.genpath(protodir, 'newp.yaml')))

        # an entry may be authored to carry additional fields for the file it names,
        # but the walk still decides which files ship and fills in their sha256
        declared = s_genpkg.loadPkgProto(s_common.genpath(protodir, 'declaredfiles.yaml'))
        self.eq(declared['files'], {
            'data.dat': {'sha256': datasha256},
            'sub/nested.dat': {'sha256': s_genpkg.getFileSha256(nestpath)},
        })

        # ...and one naming a file the package does not ship is an error
        with self.raises(s_exc.BadPkgDef) as cm:
            s_genpkg.loadPkgProto(s_common.genpath(protodir, 'nosuchfile.yaml'))

        self.eq('newp.dat', cm.exception.get('path'))

        # a sha256 is lower case hex, so nothing downstream has to normalize it
        pkgdef = {'name': 'foopkg', 'version': '0.0.1', 'files': {'data.dat': {'sha256': datasha256}}}
        s_schemas.reqValidPkgdef(pkgdef)

        pkgdef['files'] = {'data.dat': {'sha256': datasha256.upper()}}
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidPkgdef(pkgdef)

        # ...and a files entry is keyed by path and carries exactly a sha256
        pkgdef['files'] = {'data.dat': {}}
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidPkgdef(pkgdef)

        pkgdef['files'] = {'data.dat': {'sha256': datasha256, 'path': 'data.dat'}}
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidPkgdef(pkgdef)

        pkgdef['files'] = {'data.dat': datasha256}
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidPkgdef(pkgdef)

    def test_tools_genpkg_advanced(self):

        # a package which is delivered by a deployed storm service declares advanced: true,
        # which reqSvcPkgProto() -- what such a service loads its own package with --
        # requires, so a service cannot ship a package the Vertex Hub would present as an
        # installable rapid power-up
        with self.getTestDir() as tdir:

            protopath = s_common.genpath(tdir, 'advpkg.yaml')
            s_common.yamlsave({'name': 'advpkg', 'version': '0.0.1', 'advanced': True}, protopath)

            pkgdef = s_genpkg.reqSvcPkgProto(protopath)
            self.true(pkgdef['advanced'])
            s_schemas.reqValidPkgdef(pkgdef)

            # the key is optional and nothing fills it in, so a package which does not
            # declare it does not carry it at all
            s_common.yamlsave({'name': 'advpkg', 'version': '0.0.1'}, protopath)

            pkgdef = s_genpkg.tryLoadPkgProto(protopath, readonly=True)
            self.notin('advanced', pkgdef)
            s_schemas.reqValidPkgdef(pkgdef)

            with self.raises(s_exc.BadPkgDef) as exc:
                s_genpkg.reqSvcPkgProto(protopath)
            self.eq('advpkg', exc.exception.get('name'))

            # ...and declaring it false is not declaring it
            s_common.yamlsave({'name': 'advpkg', 'version': '0.0.1', 'advanced': False}, protopath)
            with self.raises(s_exc.BadPkgDef):
                s_genpkg.reqSvcPkgProto(protopath)

            # it is a boolean, so anything else is a schema violation
            s_common.yamlsave({'name': 'advpkg', 'version': '0.0.1', 'advanced': 'yes'}, protopath)
            with self.raises(s_exc.SchemaViolation):
                s_genpkg.loadPkgProto(protopath)

    async def test_tools_genpkg_signas(self):

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml')

        with self.getTestDir() as dirn:

            cdir = s_certdir.CertDir(path=dirn)
            cdir.genCaCert('testca')
            cdir.genCodeCert('coder@vertex.link', signas='testca')

            savepath = s_common.genpath(dirn, 'testpkg.json')
            argv = ('--certdir', dirn, '--signas', 'coder@vertex.link', '--save', savepath, ymlpath)
            self.eq(0, await s_genpkg.main(argv))

            pdef = s_common.yamlload(savepath)
            codesign = pdef['metadata']['codesign']
            self.nn(codesign.get('cert'))
            self.nn(codesign.get('sign'))

            # the signed body excludes the whole metadata block, but covers the rest
            pkgcopy = dict(pdef)
            pkgcopy.pop('metadata')

            cert = cdir.loadCertByts(codesign['cert'].encode())
            pubk = s_rsa.PubKey(cert.public_key())
            self.true(pubk.verifyitem(pkgcopy, s_common.uhex(codesign['sign'])))

            pkgcopy['name'] = 'newp'
            self.false(pubk.verifyitem(pkgcopy, s_common.uhex(codesign['sign'])))

    async def test_pkg_encryption_runtime(self):

        async with self.getTestCore() as core:

            # defs that do not resolve to an encrypted package skip decryption
            self.none(core._getStormPkgEncryption(None))
            self.none(core._getStormPkgEncryption('newp.no.such.pkg'))

            query = await core.getStormQueryForDef({'storm': 'inet:ipv4'})
            self.nn(query)

            seed = s_common.ehex(os.urandom(32))
            salt = s_common.ehex(os.urandom(32))

            # use non-default pbkdf params to prove decryption reads them from
            # the encryption metadata rather than the module-level constants
            hashname = 'sha512'
            iters = 1000

            encmod = s_tinfoil.encStorm(seed, salt, hashname, iters, 'function foo() { return((42)) }')
            enccmd = s_tinfoil.encStorm(seed, salt, hashname, iters, '$lib.print(enccmdran)')

            pkgdef = {
                'name': 'encpkg',
                'version': '0.0.1',
                'metadata': {'encryption': {'seed': seed, 'salt': salt, 'pbkdf2': {'iters': iters, 'hash': hashname}}},
                'modules': [{'name': 'encmod', 'storm': encmod}],
                'commands': [{'name': 'enccmd', 'storm': enccmd}],
            }

            # addStormPkg validates (decrypts) the module/command storm on add
            await core.addStormPkg(pkgdef)

            # the loaded package exposes its encryption seed/salt
            self.eq(seed, core._getStormPkgEncryption('encpkg').get('seed'))

            # importing the module and running the command decrypt at runtime
            self.eq(42, await core.callStorm('return($lib.import(encmod).foo())'))

            msgs = await core.stormlist('enccmd')
            self.stormIsInPrint('enccmdran', msgs)

    async def test_pkg_encrypt_pubkey(self):

        # a deployment RSA keypair; the admin obtains the PEM from $lib.vertex.deployment
        prikey = s_rsa.PriKey.generate()

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml')

        with self.getTestDir() as dirn:
            pempath = s_common.genpath(dirn, 'deploy.pem')
            with open(pempath, 'wb') as fd:
                fd.write(prikey.public().dump(fmt='pem'))

            savepath = s_common.genpath(dirn, 'testpkg.json')
            # --encrypt-pubkey implies --encrypt; the built pkgdef still passes reqValidPkgdef
            self.eq(0, await s_genpkg.main(('--encrypt-pubkey', pempath, '--save', savepath, ymlpath)))

            pdef = s_common.yamlload(savepath)
            encryption = pdef['metadata']['encryption']

            # per-deployment: seed is RSA-encrypted (not the 64-hex plaintext) + flagged
            self.true(encryption['deploy'])
            self.len(512, encryption['seed'])
            self.len(64, encryption['salt'])

            # only the deployment private key recovers the real 64-hex seed
            seed = prikey.decrypt(s_common.uhex(encryption['seed'])).decode()
            self.len(64, seed)

            # ...and that seed decrypts the (still encrypted) module storm
            salt = encryption['salt']
            hashname = encryption['pbkdf2']['hash']
            iters = encryption['pbkdf2']['iters']
            self.ne('inet:ip\n', pdef['modules'][0]['storm'])
            self.eq('inet:ip\n', s_tinfoil.decStorm(seed, salt, hashname, iters, pdef['modules'][0]['storm']))

    def test_tools_loadpkgproto_readonly(self):
        self.thisHostMustNot(platform='windows')
        readonly_mode = stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH
        srcpath = s_common.genpath(dirname, 'files', 'stormpkg')
        stormmod_src = s_common.genpath(dirname, 'files', 'stormmod')

        with self.getTestDir(copyfrom=srcpath) as dirn:
            shutil.copytree(stormmod_src, s_common.genpath(os.path.dirname(dirn), 'stormmod'))
            ymlpath = s_common.genpath(dirn, 'testpkg.yaml')
            self.setDirFileModes(dirn=dirn, mode=readonly_mode)
            self.skipIfWriteableFiles(dirn)
            with self.raises(PermissionError):
                s_genpkg.tryLoadPkgProto(ymlpath)
            pkg = s_genpkg.tryLoadPkgProto(ymlpath, readonly=True)

            self.eq(pkg.get('name'), 'testpkg')
            self.eq(pkg.get('modules')[0].get('storm'), 'inet:ip\n')
            self.eq(pkg.get('commands')[0].get('storm'), 'inet:ip\n')

        # Missing files are still a problem
        with self.getTestDir(copyfrom=srcpath) as dirn:
            ymlpath = s_common.genpath(dirn, 'testpkg.yaml')
            os.unlink(os.path.join(dirn, 'storm', 'modules', 'testmod.storm'))
            self.setDirFileModes(dirn=dirn, mode=readonly_mode)
            with self.raises(s_exc.NoSuchFile) as cm:
                s_genpkg.tryLoadPkgProto(ymlpath, readonly=True)
            self.isin('storm/modules/testmod', cm.exception.get('path'))

        with self.getTestDir(copyfrom=srcpath) as dirn:
            shutil.copytree(stormmod_src, s_common.genpath(os.path.dirname(dirn), 'stormmod'))  # pragma: no cover
            ymlpath = s_common.genpath(dirn, 'testpkg.yaml')
            os.remove(os.path.join(dirn, 'storm', 'commands', 'testpkgcmd.storm'))
            self.setDirFileModes(dirn=dirn, mode=readonly_mode)
            with self.raises(s_exc.NoSuchFile) as cm:
                s_genpkg.tryLoadPkgProto(ymlpath, readonly=True)
            self.isin('storm/commands/testpkgcmd', cm.exception.get('path'))

    def test_files(self):
        assets = s_files.getAssets()
        self.isin('test.dat', assets)

        s = s_files.getAssetStr('stormmod/common')
        self.isinstance(s, str)

        self.raises(ValueError, s_files.getAssetPath, 'newp.bin')
        self.raises(ValueError, s_files.getAssetPath,
                    '../../../../../../../../../etc/passwd')

class TestStormPkgTest(s_test.StormPkgTest):
    pkgprotos = (s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml'),)

    async def initTestCore(self, core):
        await core.callStorm('$lib.globals.inittestcore = frob')

    async def test_stormpkg_base(self):
        async with self.getTestCore() as core:
            msgs = await core.stormlist('testpkgcmd foo')
            self.stormHasNoWarnErr(msgs)
            self.eq('frob', await core.callStorm('return($lib.globals.inittestcore)'))

    async def stormpkg_preppkghook(self, core):
        await core.callStorm('$lib.globals.stormpkg_preppkghook = boundmethod')

    async def test_stormpkg_preppkghook(self):

        # inline example
        async def hook(core):
            await core.callStorm('$lib.globals.inlinehook = haha')

        async with self.getTestCore(prepkghook=hook) as core:
            msgs = await core.stormlist('testpkgcmd foo')
            self.stormHasNoWarnErr(msgs)
            self.eq('haha', await core.callStorm('return($lib.globals.inlinehook)'))
            self.eq('frob', await core.callStorm('return($lib.globals.inittestcore)'))

        # bound method example
        async with self.getTestCore(prepkghook=self.stormpkg_preppkghook) as core:
            msgs = await core.stormlist('testpkgcmd foo')
            self.stormHasNoWarnErr(msgs)
            self.eq('boundmethod', await core.callStorm('return($lib.globals.stormpkg_preppkghook)'))
            self.eq('frob', await core.callStorm('return($lib.globals.inittestcore)'))

class TestStormPkgTestNoEvent(s_test.StormPkgTest):
    assetdir = s_common.genpath(dirname, 'files', 'stormpkg', 'dotstorm_noevents', 'testassets')
    pkgprotos = (s_common.genpath(dirname, 'files', 'stormpkg', 'dotstorm_noevents', 'dotstorm.yaml'),)

    events = []
    linkfunc = None
    core = None

    async def _stormpkghook(self, core):
        async def func(event):
            self.events.append(event)
        self.linkfunc = func
        self.core = core
        core.link(func)

    def doCleanups(self):
        self.core.unlink(self.linkfunc)
        self.core = None
        self.linkfunc = None
        self.events.clear()

    async def test_no_load_event(self):
        async with self.getTestCore(prepkghook=self._stormpkghook) as core:
            q = '$lib.time.sleep(0.5) return( $lib.pkg.get(dotstorm_noevents).name)'
            self.eq('dotstorm_noevents', await core.callStorm(q))
        self.len(3, self.events)
        self.eq(self.events[0][0], 'cell:beholder')
        self.eq(self.events[1], ('core:pkg:onload:start', {'pkg': 'dotstorm_noevents'}))
        self.eq(self.events[2], ('core:pkg:onload:complete', {'pkg': 'dotstorm_noevents', 'storvers': -1}))
