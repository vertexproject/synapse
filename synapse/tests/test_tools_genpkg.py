import os
import stat

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.tests.utils as s_test
import synapse.tests.files as s_files

import synapse.tools.genpkg as s_genpkg

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
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'nosuchfile.yaml')
            await s_genpkg.main((ymlpath,))

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
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'notitle.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.BadPkgDef):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'nocontent.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.SchemaViolation):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badcmdname.yaml')
            await s_genpkg.main((ymlpath,))

        with self.raises(s_exc.BadArg):
            ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'badjsonpkg.yaml')
            await s_genpkg.main((ymlpath,))

        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'testpkg.yaml')
        async with self.getTestCore() as core:

            savepath = s_common.genpath(core.dirn, 'testpkg.json')
            yamlpath = s_common.genpath(core.dirn, 'testpkg.yaml')
            newppath = s_common.genpath(core.dirn, 'newp.yaml')

            url = core.getLocalUrl()
            argv = ('--push', url, '--save', savepath, ymlpath)

            await s_genpkg.main(argv)

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
            self.eq(pdef['modules'][0]['storm'], 'inet:ipv4\n')
            self.eq(pdef['modules'][1]['name'], 'testpkg.testext')
            self.eq(pdef['modules'][1]['storm'], 'inet:fqdn\n')
            self.eq(pdef['modules'][2]['name'], 'testpkg.testextfile')
            self.eq(pdef['modules'][2]['storm'], 'inet:fqdn\n')
            self.eq(pdef['commands'][0]['name'], 'testpkgcmd')
            self.eq(pdef['commands'][0]['storm'], 'inet:ipv6\n')

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

            self.eq(pdef['optic']['files']['index.html']['file'], 'aGkK')

            self.eq(pdef['docs'][0]['title'], 'Foo Bar')
            self.eq(pdef['docs'][0]['content'], 'Hello!\n')

            self.eq(pdef['logo']['mime'], 'image/svg')
            self.eq(pdef['logo']['file'], 'c3R1ZmYK')

            self.len(3, pdef['optic']['workflows'])

            wflow = pdef['optic']['workflows']['testpkg-foo']
            self.eq(wflow, {'name': 'foo', 'desc': 'a foo workflow'})

            wflow = pdef['optic']['workflows']['testpkg-bar']
            self.eq(wflow, {'name': 'bar', 'desc': 'this is an inline workflow'})

            wflow = pdef['optic']['workflows']['testpkg-baz']
            self.eq(wflow, {'name': 'real-baz', 'desc': 'this is the real baz desc'})

            # nodocs
            nodocspath = s_common.genpath(core.dirn, 'testpkg_nodocs.json')
            argv = ('--no-docs', '--save', nodocspath, ymlpath)

            await s_genpkg.main(argv)

            noddocs_pdef = s_common.yamlload(nodocspath)

            self.eq(noddocs_pdef['name'], 'testpkg')
            self.eq(noddocs_pdef['docs'][0]['title'], 'Foo Bar')
            self.eq(noddocs_pdef['docs'][0]['content'], '')

            # No push, no save:  nothing to do
            argv = (ymlpath,)
            retn = await s_genpkg.main(argv)
            self.eq(1, retn)

            # Invalid:  save with pre-made file
            argv = ('--no-build', '--save', savepath, savepath)
            retn = await s_genpkg.main(argv)
            self.eq(1, retn)

            # Push a premade yaml
            argv = ('--push', url, '--no-build', yamlpath)
            retn = await s_genpkg.main(argv)
            self.eq(0, retn)

            # Push a premade json
            argv = ('--no-build', '--push', url, savepath)
            retn = await s_genpkg.main(argv)
            self.eq(0, retn)

            # Cannot push a file that does not exist
            argv = ('--push', url, '--no-build', newppath)
            retn = await s_genpkg.main(argv)
            self.eq(1, retn)

    def test_tools_tryloadpkg(self):
        ymlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'nosuchfile.yaml')
        pkg = s_genpkg.tryLoadPkgProto(ymlpath)
        # Ensure it ran the fallback to do_docs=False
        self.eq(pkg.get('docs'), [{'title': 'newp', 'path': 'docs/newp.md', 'content': ''}])

    def test_tools_loadpkgproto_readonly(self):
        self.thisHostMustNot(platform='windows')
        readonly_mode = stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH
        srcpath = s_common.genpath(dirname, 'files', 'stormpkg')

        with self.getTestDir(copyfrom=srcpath) as dirn:
            ymlpath = s_common.genpath(dirn, 'testpkg.yaml')
            self.setDirFileModes(dirn=dirn, mode=readonly_mode)
            self.skipIfWriteableFiles(dirn)
            with self.raises(PermissionError):
                s_genpkg.tryLoadPkgProto(ymlpath)
            pkg = s_genpkg.tryLoadPkgProto(ymlpath, readonly=True)

            self.eq(pkg.get('name'), 'testpkg')
            self.eq(pkg.get('modules')[0].get('storm'), 'inet:ipv4\n')
            self.eq(pkg.get('commands')[0].get('storm'), 'inet:ipv6\n')

        # Missing files are still a problem
        with self.getTestDir(copyfrom=srcpath) as dirn:
            ymlpath = s_common.genpath(dirn, 'testpkg.yaml')
            os.unlink(os.path.join(dirn, 'storm', 'modules', 'testmod'))
            self.setDirFileModes(dirn=dirn, mode=readonly_mode)
            with self.raises(s_exc.NoSuchFile) as cm:
                s_genpkg.tryLoadPkgProto(ymlpath, readonly=True)
            self.isin('storm/modules/testmod', cm.exception.get('path'))

        with self.getTestDir(copyfrom=srcpath) as dirn:
            ymlpath = s_common.genpath(dirn, 'testpkg.yaml')
            os.remove(os.path.join(dirn, 'storm', 'commands', 'testpkgcmd'))
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

    async def test_genpkg_dotstorm(self):

        yamlpath = s_common.genpath(dirname, 'files', 'stormpkg', 'dotstorm', 'dotstorm.yaml')

        async with self.getTestCore() as core:
            url = core.getLocalUrl()
            argv = ('--push', url, yamlpath)
            await s_genpkg.main(argv)
            msgs = await core.stormlist('$lib.import(dotstorm.foo)')
            self.stormIsInPrint('hello foo', msgs)
            msgs = await core.stormlist('dotstorm.bar')
            self.stormIsInPrint('hello bar', msgs)

class TestStormPkgTest(s_test.StormPkgTest):
    assetdir = s_common.genpath(dirname, 'files', 'stormpkg', 'dotstorm', 'testassets')
    pkgprotos = (s_common.genpath(dirname, 'files', 'stormpkg', 'dotstorm', 'dotstorm.yaml'),)

    async def test_stormpkg_base(self):
        async with self.getTestCore() as core:
            msgs = await core.stormlist('dotstorm.bar')
            self.stormHasNoWarnErr(msgs)
