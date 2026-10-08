import os

import synapse.tests.utils as s_test
import synapse.lib.mddocs as s_mddocs
import synapse.tools.storm.pkg.doc as s_doc
import synapse.tools.storm.pkg.gen as s_genpkg

dirname = os.path.abspath(os.path.dirname(__file__))

class AcmeHelloTest(s_test.StormPkgTest):

    assetdir = os.path.join(dirname, 'testassets')
    pkgprotos = (os.path.join(dirname, 'acme-hello.yaml'),)

    async def test_acme_hello(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('acme.hello.sayhi')
            self.stormIsInPrint('hello storm!', msgs)
            self.stormHasNoWarnErr(msgs)

    async def test_acme_hello_mayyield(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('[ inet:fqdn=vertex.link ] | acme.hello.mayyield')
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('inet:fqdn', 'vertex.link'), nodes[0][0])

            msgs = await core.stormlist('[ inet:fqdn=vertex.link ] | acme.hello.mayyield --yield')
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(2, nodes)
            self.eq(('inet:dns:a', (('inet:fqdn', 'vertex.link'), ('inet:ipv4', (4, 0x01020304)))), nodes[0][0])
            self.eq(('inet:dns:a', (('inet:fqdn', 'vertex.link'), ('inet:ipv4', (4, 0x7b7b7b7b)))), nodes[1][0])

    async def test_acme_hello_docs(self):

        pkgdef = s_genpkg.loadPkgProto(self.pkgprotos[0], readonly=True)
        filedefs = pkgdef.get('files')

        # the built docs ship as ordinary package files under a docs/ prefix. only
        # the sha256 the Axon stores them by is carried in the package definition.
        pages = [name for name in os.listdir(os.path.join(dirname, 'docs')) if name.endswith('.md')]
        self.gt(len(pages), 0)

        for name in pages:
            filedef = filedefs.get(f'docs/{name}')
            self.nn(filedef)
            self.len(64, filedef.get('sha256'))

        self.nn(filedefs.get('docs/metadata.json'))

    async def test_acme_hello_docs_current(self):

        docsdir = os.path.join(dirname, 'docs')

        manifest = s_mddocs.getManifestPath(docsdir)
        entries = s_mddocs.loadManifest(manifest)
        self.gt(len(entries), 0)

        # every page the last build recorded still hashes to what it recorded, so
        # editing docs/ without rebuilding files/docs fails here rather than shipping
        hint = 'python -m synapse.tools.storm.pkg.doc acme-hello.yaml'
        self.eq([], s_mddocs.checkManifest('acme-hello', entries, os.path.dirname(manifest), hint=hint))

    async def test_acme_hello_docs_no_drift(self):

        # the manifest check above catches a page edited without a rebuild. This
        # catches the other direction: a page whose text never changed but whose
        # rendered output would come out differently now, because the pkgdef or the
        # Storm behind it moved. Rebuild into a throwaway directory and compare.
        with self.getTestDir() as savedir:

            await s_doc.buildPkgDocs(self.pkgprotos[0], save=savedir, force=True)

            builtdir = os.path.join(dirname, 'files', 'docs')
            names = sorted(name for name in os.listdir(builtdir) if name.endswith('.md'))
            self.gt(len(names), 0)

            for name in names:

                with open(os.path.join(builtdir, name)) as fd:
                    committed = self.normDrift(fd.read())

                with open(os.path.join(savedir, name)) as fd:
                    rebuilt = self.normDrift(fd.read())

                self.eq(committed, rebuilt, msg=f'{name} drifted from a rebuild')
