import os
import stat
import shutil
import hashlib
import unittest.mock as mock

import aiohttp_socks

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.certdir as s_certdir
import synapse.lib.msgpack as s_msgpack
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

    def getTestCourse(self):
        return {
            'iden': 'a' * 32,
            'title': 'A Course',
            'body': 'course material',
            'modules': [
                {
                    'iden': 'c' * 32,
                    'type': 'module',
                    'title': 'Module One',
                    'body': 'module material',
                },
                {
                    'iden': 'd' * 32,
                    'type': 'quiz',
                    'title': 'Quiz Two',
                    'body': 'quiz body',
                    'sections': [
                        {
                            'title': 'Section One',
                            'questions': [
                                {
                                    'iden': 'f' * 32,
                                    'type': 'basic',
                                    'body': 'what is it?',
                                    'points': 10,
                                    'answer': {'value': 'vertex.link', 'type': 'inet:fqdn'},
                                },
                            ],
                        },
                    ],
                },
            ],
        }

    def setTestQuestion(self, cdef, **edits):
        '''
        Return a copy of the test course whose one question is replaced, since which fields
        a question carries depends on its type.
        '''
        ques = {'iden': 'f' * 32, 'body': 'what is it?', 'points': 10}
        ques.update(edits)

        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'][0]['questions'][0] = ques

        return newp

    def test_tools_genpkg_courses(self):

        protodir = s_common.genpath(dirname, 'files', 'stormpkg')
        ymlpath = s_common.genpath(protodir, 'testpkg.yaml')

        # the courses directory beside the package yaml file is loaded automatically
        pkgdef = s_genpkg.loadPkgProto(ymlpath)

        self.len(1, pkgdef['courses'])

        cdef = pkgdef['courses'][0]
        self.eq('09f6c8bd3e4a41d5b7e2c0a91f8d6b34', cdef['iden'])
        self.eq('Test Course', cdef['title'])
        self.eq(('Introduction', 'FQDN Quiz'),
                tuple([mdef['title'] for mdef in cdef['modules']]))

        # a module is either course material or a quiz, and each names itself
        self.eq(('module', 'quiz'), tuple([mdef['type'] for mdef in cdef['modules']]))
        self.notin('sections', cdef['modules'][0])

        quiz = cdef['modules'][1]
        self.eq('FQDN Quiz', quiz['title'])
        self.eq(('The Basics', 'Storm Questions'), tuple([sdef['title'] for sdef in quiz['sections']]))

        # every question type is covered
        quesdefs = [qdef for sdef in quiz['sections'] for qdef in sdef['questions']]
        self.len(5, quesdefs)
        self.eq(('basic', 'yesorno', 'multi', 'choice', 'storm'),
                tuple([qdef['type'] for qdef in quesdefs]))

        # a hint is carried by the answer, so it is withheld with everything else the
        # learner may not see
        self.len(1, quesdefs[0]['answer']['hints'])

        with self.getTestDir() as dirn:

            newppath = s_common.genpath(dirn, 'coursepkg.yaml')
            coursedir = s_common.genpath(dirn, 'courses')

            s_common.yamlsave({'name': 'coursepkg', 'version': '0.0.1'}, newppath)

            # with no courses directory at all, the section is absent
            self.notin('courses', s_genpkg.loadPkgProto(newppath))

            def loadproto(courses, **files):
                shutil.rmtree(coursedir, ignore_errors=True)
                for name, cdef in files.items():
                    s_common.yamlsave(cdef, coursedir, name)

                proto = {'name': 'coursepkg', 'version': '0.0.1'}
                if courses is not None:
                    proto['courses'] = courses

                s_common.yamlsave(proto, newppath)
                return s_genpkg.loadPkgProto(newppath)

            # every .yaml file in the directory becomes a course, in sorted order so a
            # rebuild produces the same package
            twodef = self.getTestCourse()
            twodef['iden'] = 'e' * 32
            twodef['title'] = 'Zeroth Course'

            newdef = loadproto(None, **{'one.yaml': self.getTestCourse(), 'two.yaml': twodef})
            self.eq(['a' * 32, 'e' * 32], [cdef['iden'] for cdef in newdef['courses']])

            # ...and anything which is not a .yaml file is skipped
            with self.getLoggerStream('synapse.tools.storm.pkg.gen') as stream:
                newdef = loadproto(None, **{'one.yaml': self.getTestCourse(), 'two.newp': twodef})
            self.len(1, newdef['courses'])
            stream.seek(0)
            mesg = stream.read()
            self.isin('Skipping course file', mesg)
            self.isin('two.newp', mesg)

            # an empty course file is an authoring mistake
            s_common.yamlsave(None, coursedir, 'empty.yaml')
            with self.raises(s_exc.BadPkgDef) as cm:
                s_genpkg.loadPkgProto(newppath)
            self.isin('is empty', cm.exception.get('mesg'))

            # the section is generated, so it may not also be declared
            with self.raises(s_exc.BadPkgDef) as cm:
                loadproto([self.getTestCourse()], **{'one.yaml': self.getTestCourse()})
            self.isin('may not be specified', cm.exception.get('mesg'))

            # a course must be distinguishable from the others by iden
            with self.raises(s_exc.BadPkgDef) as cm:
                loadproto(None, **{'one.yaml': self.getTestCourse(), 'two.yaml': self.getTestCourse()})
            self.eq('a' * 32, cm.exception.get('iden'))

            # a module iden is what a run is recorded against, so it must be unique
            # within the course even when the modules are named differently
            cdef = self.getTestCourse()
            cdef['modules'][0]['iden'] = cdef['modules'][1]['iden']
            with self.raises(s_exc.BadArg) as cm:
                loadproto(None, **{'one.yaml': cdef})
            self.eq('d' * 32, cm.exception.get('module'))

            # ...and for a question iden, which must be unique across the whole quiz
            # rather than within its section, since a run keys answers on it
            cdef = self.getTestCourse()
            quiz = cdef['modules'][1]
            sect = s_msgpack.deepcopy(quiz['sections'][0], use_list=True)
            sect['title'] = 'Section Two'
            quiz['sections'].append(sect)
            with self.raises(s_exc.BadArg) as cm:
                loadproto(None, **{'one.yaml': cdef})
            self.eq('f' * 32, cm.exception.get('question'))

            # a title is only a label, so any two elements may share one as long as
            # their idens are distinct
            cdef = self.getTestCourse()
            cdef['modules'][0]['title'] = 'Module Two'

            quiz = s_msgpack.deepcopy(cdef['modules'][1], use_list=True)
            quiz['iden'] = 'e' * 32
            quiz['sections'].append(s_msgpack.deepcopy(quiz['sections'][0], use_list=True))
            quiz['sections'][1]['questions'][0]['iden'] = '0' * 32
            cdef['modules'].append(quiz)

            self.nn(loadproto(None, **{'one.yaml': cdef}))

    def test_tools_genpkg_course_schema(self):

        cdef = self.getTestCourse()
        self.eq(cdef, s_schemas.reqValidCourse(s_msgpack.deepcopy(cdef, use_list=True)))

        # a question type must be implemented by both the editor and the runner
        for valu in ('edits', 'newp'):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][1]['sections'][0]['questions'][0]['type'] = valu
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # the answer value of a basic question may be a bool, an int or a string, and an
        # empty string is a legitimate answer
        for valu in ('vertex.link', True, False, 0, 42, ''):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][1]['sections'][0]['questions'][0]['answer']['value'] = valu
            s_schemas.reqValidCourse(newp)

        # ...but not a float or an object
        for valu in (1.5, {'newp': 'newp'}):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][1]['sections'][0]['questions'][0]['answer']['value'] = valu
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # an empty array is a legitimate answer to a question which is answered with one
        # -- "none of these are FQDNs" is a question worth asking -- and an empty value may
        # equally be offered as one of the choices
        newp = self.setTestQuestion(cdef, type='choice',
                                    choices=[{'value': 'a'}, {'value': ''}, {'value': ()}],
                                    answer={'type': 'str', 'value': ()})
        s_schemas.reqValidCourse(newp)

        # a choice must have a value
        newp['modules'][1]['sections'][0]['questions'][0]['choices'] = [{'type': 'str'}]
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

        # a title is free text, but it is bounded and may not be empty
        for valu in ('', 'x' * 81, 42):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][0]['title'] = valu
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # the answer of a basic question is graded by norming the attempt as type and
        # comparing it to value, since a storm question is the only one a query grades
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'][0]['questions'][0]['answer'] = {'type': 'inet:fqdn',
                                                                       'value': 'vertex.link'}
        s_schemas.reqValidCourse(newp)

        for answer in ({'checker': 'inet:fqdn=vertex.link'},
                       {'checker': 'inet:fqdn', 'type': 'inet:fqdn', 'value': 'vertex.link'}):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][1]['sections'][0]['questions'][0]['answer'] = answer
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # a value with no type has nothing to norm against, and a type with no value has
        # nothing to compare
        for answer in ({}, {'value': 'vertex.link'}, {'type': 'inet:fqdn'}, {'hints': ()}):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][1]['sections'][0]['questions'][0]['answer'] = answer
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # a hint carries both the text it shows and the deduction it charges, so a partial
        # entry is rejected rather than silently costing nothing
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'][0]['questions'][0]['answer']['hints'] = [{'body': 'text',
                                                                                 'deduction': 1}]
        s_schemas.reqValidCourse(newp)

        for entry in ({}, {'body': 'text'}, {'deduction': 1}):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][1]['sections'][0]['questions'][0]['answer']['hints'] = [entry]
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # ...and it belongs to the answer, so it is withheld along with it
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'][0]['questions'][0]['hints'] = [{'body': 'text',
                                                                      'deduction': 1}]
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

        # what a wrong attempt costs is one number on the question
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'][0]['questions'][0]['deduct'] = 3
        s_schemas.reqValidCourse(newp)

        for valu in (-1, 'newp'):
            newp = s_msgpack.deepcopy(cdef, use_list=True)
            newp['modules'][1]['sections'][0]['questions'][0]['deduct'] = valu
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # a question is identified by its iden and its body is the question itself, so it
        # carries no title to label it with
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'][0]['questions'][0]['title'] = 'A Question'
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

        # a course may carry no modules at all, since one is authored before it has any
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'] = []
        s_schemas.reqValidCourse(newp)

        # ...but a quiz with no sections is not content
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'] = []
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

        # a basic question is a labelled input with a button to submit it, so its ui takes
        # all three of the presentation options
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        ques = newp['modules'][1]['sections'][0]['questions'][0]
        ques['ui'] = {'label': 'FQDN', 'placeholder': 'some.fqdn', 'buttontext': 'Go'}
        s_schemas.reqValidCourse(newp)

        # ...and the ui is closed rather than an open bag, so a key no widget takes is
        # refused instead of carried along
        ques['ui'] = {'label': 'FQDN', 'newp': 'newp'}
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

        # ...but an answer carries no type options, since the answer type is the type of
        # one value and never the array type
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['sections'][0]['questions'][0]['answer']['typeopts'] = {'type': 'str'}
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

        # a hook is a Storm query rather than an open bag, and only a quiz carries any
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['hooks'] = {'viewinit': 'return($view)',
                                       'completed': '$lib.print(hi)'}
        s_schemas.reqValidCourse(newp)

        for hooks in ({'viewinit': {'newp': 'newp'}}, {'viewinit': ''}, {'newp': 'newp'}):
            newp['modules'][1]['hooks'] = hooks
            with self.raises(s_exc.SchemaViolation):
                s_schemas.reqValidCourse(newp)

        # a view to work in belongs to the quiz which needs it, so a course declares none
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['viewinit'] = 'return($view)'
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

        # ...and course material has nothing to run, so it carries no hooks either
        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][0]['hooks'] = {'completed': '$lib.print(hi)'}
        with self.raises(s_exc.SchemaViolation):
            s_schemas.reqValidCourse(newp)

    def test_tools_genpkg_course_question_types(self):
        '''
        The question type is the widget the attempt was collected with, so it decides which
        answer fields the question carries.
        '''
        cdef = self.getTestCourse()

        # a query run on the participant's behalf needs a view to run in
        quesargs = {'type': 'storm', 'answer': {'checker': 'inet:fqdn=vertex.link'}}
        with self.raises(s_exc.BadArg) as cm:
            s_schemas.reqValidCourse(self.setTestQuestion(cdef, **quesargs))

        self.isin('has a checker hook, but no viewinit hook', cm.exception.get('mesg'))

        for hook in ('correct', 'incorrect', 'validate'):
            quesargs = {'type': 'basic',
                        'answer': {'type': 'inet:fqdn', 'value': 'vertex.link',
                                   'hooks': {hook: '$lib.print(hi)'}}}
            with self.raises(s_exc.BadArg) as cm:
                s_schemas.reqValidCourse(self.setTestQuestion(cdef, **quesargs))

            self.isin(f'has a {hook} hook, but no viewinit hook', cm.exception.get('mesg'))

        newp = s_msgpack.deepcopy(cdef, use_list=True)
        newp['modules'][1]['hooks'] = {'completed': '$lib.print(hi)'}
        with self.raises(s_exc.BadArg) as cm:
            s_schemas.reqValidCourse(newp)

        self.isin('has a completed hook but no viewinit hook', cm.exception.get('mesg'))

        # a wrong attempt reveals a hint, so there may not be more hints than retries
        quesargs = {'type': 'basic', 'retries': 1,
                    'answer': {'type': 'inet:fqdn', 'value': 'vertex.link',
                               'hints': [{'body': 'one', 'deduction': 1},
                                         {'body': 'two', 'deduction': 1}]}}
        with self.raises(s_exc.BadArg) as cm:
            s_schemas.reqValidCourse(self.setTestQuestion(cdef, **quesargs))

        self.isin('more hints available than retries allowed', cm.exception.get('mesg'))

        cdef['modules'][1]['hooks'] = {'viewinit': 'return($lib.view.get().iden)'}

        def reqValid(**edits):
            return s_schemas.reqValidCourse(self.setTestQuestion(cdef, **edits))

        # a question which does not match the branch its type names fails the whole choice,
        # and a module is itself one branch of a choice, so the failure surfaces at the
        # module rather than naming the field which is actually wrong
        def reqInvalid(mesg='data.modules[1] cannot be validated by any definition', **edits):
            with self.raises(s_exc.SchemaViolation) as cm:
                s_schemas.reqValidCourse(self.setTestQuestion(cdef, **edits))

            self.isin(mesg, cm.exception.get('mesg'))

        # a storm question is the only type graded by a query, which is a field of the answer
        # and is handed the type along with the attempt
        reqValid(type='storm', answer={'checker': 'return(({"correct": (true)}))',
                                       'type': 'inet:fqdn'})

        # ...so no other type carries one, whether or not it has a value to compare as well
        for qtype in ('basic', 'yesorno', 'multi', 'choice'):
            edits = {'type': qtype, 'answer': {'checker': 'return(({"correct": (true)}))',
                                               'type': 'inet:fqdn'}}
            if qtype == 'choice':
                edits['choices'] = [{'value': 'vertex.link'}]

            reqInvalid(**edits)

            edits['answer'] = {'checker': 'return(({"correct": (true)}))',
                               'type': 'inet:fqdn',
                               'value': ['vertex.link'] if qtype in ('multi', 'choice') else 'vertex.link'}
            reqInvalid(**edits)

        # the answers each type does carry, which is what the rest of these check
        answers = {
            'basic': {'type': 'inet:fqdn', 'value': 'vertex.link'},
            'yesorno': {'value': True},
            'storm': {'checker': 'inet:fqdn=vertex.link'},
            'multi': {'type': 'inet:fqdn', 'value': ['vertex.link']},
            'choice': {'type': 'inet:fqdn', 'value': ['vertex.link']},
        }

        # the hooks which run once an attempt has been graded belong to every type, since
        # any question may show the participant something on the way it went
        for (qtype, answer) in answers.items():
            edits = {'type': qtype,
                     'answer': {**answer, 'hooks': {'correct': '$lib.print(yup)',
                                                    'incorrect': '$lib.print(newp)',
                                                    'validate': 'inet:fqdn=vertex.link'}}}
            if qtype == 'choice':
                edits['choices'] = [{'value': 'vertex.link'}]

            reqValid(**edits)

        # the fields which do not depend on the widget are carried by every type, and each
        # type is closed, so a field which is neither one of those nor one of its own is
        # rejected whichever type it is
        for (qtype, answer) in answers.items():
            edits = {'type': qtype, 'retries': 2, 'deduct': 1,
                     'answer': {**answer, 'hints': [{'body': 'a hint', 'deduction': 1}]}}
            if qtype == 'choice':
                edits['choices'] = [{'value': 'vertex.link'}]

            reqValid(**edits)
            reqInvalid(newp='newp', **edits)

        # a ui, by contrast, does depend on the widget: each type declares its own and
        # closes it, so an option belonging to another type's widget is refused rather than
        # carried along and ignored
        uiopts = {
            'basic': ('label', 'placeholder', 'buttontext'),
            'multi': ('label', 'placeholder', 'buttontext'),
            'choice': ('buttontext',),
            'storm': ('buttontext',),
            'yesorno': (),
        }

        for (qtype, answer) in answers.items():
            edits = {'type': qtype, 'answer': answer}
            if qtype == 'choice':
                edits['choices'] = [{'value': 'vertex.link'}]

            takes = uiopts.get(qtype)

            if takes:
                reqValid(ui={key: 'valu' for key in takes}, **edits)
            else:
                # a yesorno is two fixed buttons, with nothing to label and no button of its
                # own to name, so it declares no ui and an empty one is as invalid as an
                # option in one
                reqInvalid(ui={}, **edits)

            for key in ('label', 'placeholder', 'buttontext', 'newp'):

                if key in takes:
                    continue

                reqInvalid(ui={key: 'valu'}, **edits)

        # a basic question is one text input, so it is answered with one value of one type
        reqValid(type='basic', answer={'type': 'inet:fqdn', 'value': 'vertex.link'})

        # ...never with a list of them, and it offers nothing to choose from
        reqInvalid(type='basic', answer={'type': 'inet:fqdn', 'value': ['vertex.link']})
        reqInvalid(type='basic', answer={'type': 'array', 'value': ['vertex.link']})
        reqInvalid(type='basic', choices=[{'value': 'vertex.link'}],
                   answer={'type': 'inet:fqdn', 'value': 'vertex.link'})

        # a yes or no question is two buttons, so the attempt is normed as a bool. The
        # buttons are the type, so the answer declares none of its own.
        for valu in (True, False):
            reqValid(type='yesorno', answer={'value': valu})

        reqInvalid(type='yesorno', answer={'type': 'bool', 'value': True})
        reqInvalid(type='yesorno', answer={'type': 'inet:fqdn', 'value': 'vertex.link'})
        reqInvalid(type='yesorno', choices=[{'value': 'yup'}], answer={'value': True})

        # ...and the value is the bool itself rather than one of the values the bool type
        # norms as one
        for valu in ('false', 'true', 0, 1):
            reqInvalid(type='yesorno', answer={'value': valu})

        # a storm question is answered by the work the participant does in the view, so
        # there is no attempt to compare and only its checker can grade it
        reqValid(type='storm', answer={'checker': 'inet:fqdn=vertex.link'})

        reqInvalid(type='storm', answer={'type': 'inet:fqdn', 'value': 'vertex.link'})
        reqInvalid(type='storm', choices=[{'value': 'vertex.link'}],
                   answer={'checker': 'inet:fqdn=vertex.link'})

        # ...and the checker sits alongside the hooks on the answer rather than among them,
        # which only run once an attempt has been graded
        reqInvalid(type='storm', answer={'hooks': {'attempt': 'inet:fqdn=vertex.link'}})

        # the hooks are the answer's, so a question carries none of its own
        reqInvalid(type='storm', answer={'checker': 'inet:fqdn=vertex.link'},
                   hooks={'correct': '$lib.print(yup)'})

        # ...and they are closed, so the author query is only reachable by its own name
        reqInvalid(type='storm', answer={'checker': 'inet:fqdn=vertex.link',
                                        'hooks': {'authorcheck': 'inet:fqdn=vertex.link'}})

        # a multi question is a list editor the participant fills in themselves, so the
        # answer is a list of values and the type is the type of one of them
        reqValid(type='multi', answer={'type': 'inet:fqdn',
                                      'value': ['vertex.link', 'synapse.vertex.link']})

        reqInvalid(type='multi', answer={'type': 'array', 'value': ['vertex.link']})
        reqInvalid(type='multi', answer={'type': 'inet:fqdn', 'value': ['vertex.link'],
                                        'typeopts': {'type': 'inet:fqdn'}})
        reqInvalid(type='multi', answer={'value': ['vertex.link']})
        reqInvalid(type='multi', answer={'type': 'inet:fqdn', 'value': 'vertex.link'})
        reqInvalid(type='multi', choices=[{'value': 'vertex.link'}],
                   answer={'type': 'inet:fqdn', 'value': ['vertex.link']})

        # a choice question offers the choices it declares, one of which is correct when
        # the answer is a single value and more than one when it is an array
        reqValid(type='choice', choices=[{'value': 'vertex.link'}, {'value': 'newp.link'}],
                 answer={'type': 'inet:fqdn', 'value': ['vertex.link']})

        reqValid(type='choice', choices=[{'value': 'vertex.link'}, {'value': 'newp.link'}],
                 answer={'type': 'inet:fqdn', 'value': ['vertex.link', 'newp.link']})

        # ...so a choice question with nothing to choose from is not a question
        reqInvalid(type='choice', answer={'type': 'inet:fqdn', 'value': ['vertex.link']})
        reqInvalid(type='choice', choices=[],
                   answer={'type': 'inet:fqdn', 'value': ['vertex.link']})

        # ...and the participant picks from a list either way, so a single correct choice is
        # a list of one rather than the value itself
        reqInvalid(type='choice', choices=[{'value': 'vertex.link'}],
                   answer={'type': 'inet:fqdn', 'value': 'vertex.link'})

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

    async def test_tools_genpkg_https_args(self):

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml')

        # the https only options require an https:// --push URL
        for argv in (('--https-proxy', 'socks5://127.0.0.1:9050'),
                     ('--https-ca-dir', '/path/to/cas'),
                     ('--https-noverify',)):

            with self.raises(s_exc.BadArg) as cm:
                await s_genpkg.main((*argv, '--push', 'cell://newp', ymlpath), outp=self.getTestOutp())
            self.isin('may only be used with an https:// Cortex URL', cm.exception.get('mesg'))

            # ...and are not silently ignored by a --save only run
            with self.raises(s_exc.BadArg):
                await s_genpkg.main((*argv, '--save', '/newp/newp.json', ymlpath), outp=self.getTestOutp())

    async def test_tools_genpkg_https(self):

        datapath = s_common.genpath(dirname, 'files', 'stormpkg', 'files', 'data.dat')
        datasha256 = s_genpkg.getFileSha256(datapath)

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml')

        # the package declares a file, so --push needs a Cortex with a real Axon
        async with self.getTestCluster() as clus:
            core = clus.cortex

            port, apikey = await self.getHttpsApiInfo(core, name='pkg-gen')
            url = f'https://{apikey}@127.0.0.1:{port}'

            base = ('--push', url, '--https-noverify')
            argv = (*base, ymlpath)

            outp = self.getTestOutp()
            self.eq(0, await s_genpkg.main(argv, outp=outp))

            # the declared files are uploaded into the Axon over the HTTP API
            outp.expect(f'Uploading file: {datapath} ({datasha256})')
            self.true(await core.callStorm('return($lib.axon.has($s))', opts={'vars': {'s': datasha256}}))

            # ...and the package itself is installed
            self.nn(await core.getStormPkg('testpkg'))
            msgs = await core.stormlist('$mod=$lib.import(testmod) $lib.print($mod)')
            self.stormIsInPrint('Imported Module testmod', msgs)

            # a re-push finds the content addressed file already in the Axon
            outp = self.getTestOutp()
            self.eq(0, await s_genpkg.main(argv, outp=outp))
            outp.expect(f'Skipping existing file: {datapath} ({datasha256})')

            # the Cortex verifies a code signature against its own certdir, which reads
            # the CA back off disk per call, so seeding it after boot is enough
            core.certdir.genCaCert('testca')
            core.certdir.genCodeCert('coder@vertex.link', signas='testca')

            # the Cortex is told to verify, and the package is not signed
            with self.raises(s_exc.BadPkgDef) as cm:
                await s_genpkg.main((*base, '--push-verify', ymlpath), outp=self.getTestOutp())
            self.isin('not signed', cm.exception.get('mesg'))

            # a signed package verifies, so the signature survives the JSON round trip
            # the HTTP API puts the package definition through
            signas = ('--push-verify', '--certdir', core.certpath, '--signas', 'coder@vertex.link')
            self.eq(0, await s_genpkg.main((*base, *signas, ymlpath), outp=self.getTestOutp()))

            pkgdef = await core.getStormPkg('testpkg')
            self.nn(pkgdef['metadata']['codesign']['sign'])

            # an API key whose user cannot add packages is denied
            lowuser = await core.auth.addUser('lowuser')
            lowkey, _ = await core.addUserApiKey(lowuser.iden, 'lowuser')

            lowurl = f'https://{lowkey}@127.0.0.1:{port}'
            with self.raises(s_exc.AuthDeny):
                await s_genpkg.main(('--push', lowurl, '--https-noverify', ymlpath), outp=self.getTestOutp())

    async def test_tools_genpkg_https_proxy(self):

        datapath = s_common.genpath(dirname, 'files', 'stormpkg', 'files', 'data.dat')
        datasha256 = s_genpkg.getFileSha256(datapath)

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml')

        # the package declares a file, so the push needs a Cortex with a real Axon
        async with self.getTestCluster() as clus:
            core = clus.cortex

            port, apikey = await self.getHttpsApiInfo(core, name='pkg-gen')
            url = f'https://{apikey}@127.0.0.1:{port}'

            base = ('--push', url, '--https-noverify', '--https-proxy')

            # a real proxy, so a push which quietly went direct fails rather than passing
            for ctor in s_test.PROXIES:
                with self.subTest(scheme=ctor.scheme):

                    # drop the file so every scheme uploads rather than skipping
                    await core.callStorm('$lib.axon.del($sha256)', opts={'vars': {'sha256': datasha256}})

                    async with await ctor.anit() as proxy:

                        outp = self.getTestOutp()
                        self.eq(0, await s_genpkg.main((*base, proxy.url, ymlpath), outp=outp))

                        # the streamed Axon upload rides the tunnel, not just the pkgdef
                        outp.expect(f'Uploading file: {datapath} ({datasha256})')
                        self.true(await core.callStorm('return($lib.axon.has($s))',
                                                       opts={'vars': {'s': datasha256}}))
                        self.nn(await core.getStormPkg('testpkg'))

                        # every tunnel named the Cortex, and there was at least one
                        self.lt(0, len(proxy.connects))
                        self.eq({('127.0.0.1', port)}, set(proxy.connects))

                    # credentials in the proxy URL reach a proxy which demands them
                    async with await ctor.anit(auth='visi:secret') as proxy:

                        proxyurl = proxy.url.replace('://', '://visi:secret@')

                        outp = self.getTestOutp()
                        self.eq(0, await s_genpkg.main((*base, proxyurl, ymlpath), outp=outp))

                        outp.expect(f'Skipping existing file: {datapath} ({datasha256})')
                        self.eq(0, proxy.refused)
                        self.eq({('127.0.0.1', port)}, set(proxy.connects))

                    # and the wrong ones fail rather than connecting directly
                    async with await ctor.anit(auth='visi:secret') as proxy:

                        proxyurl = proxy.url.replace('://', '://visi:newp@')

                        with self.raises(aiohttp_socks.ProxyError):
                            await s_genpkg.main((*base, proxyurl, ymlpath), outp=self.getTestOutp())

                        self.eq([], proxy.connects)
                        self.lt(0, proxy.refused)

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

            # a failing inits query is caught and logged rather than raised, so without
            # asserting what it set, a broken one goes unnoticed on every package load
            self.true(await core.callStorm('return($lib.globals."testpkg-first")'))

            # 'second' is version 2 with no inaugural flag, so a fresh install records
            # its version and skips the query (see Cortex._runStormPkgOnload)
            self.none(await core.callStorm('return($lib.globals."testpkg-second")'))

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
