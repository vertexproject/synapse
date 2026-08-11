import os
import shutil
import hashlib
import contextlib
import unittest.mock as mock

import aiohttp

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.httpapi as s_httpapi
import synapse.lib.certdir as s_certdir
import synapse.lib.crypto.rsa as s_rsa

import synapse.tests.utils as s_test

import synapse.tools.storm.pkg.doc as s_gendocs
import synapse.tools.storm.pkg.publish as s_pkgpublish

dirname = os.path.dirname(__file__)

class HubPackages(s_httpapi.Handler):
    '''
    Stand in for the Vertex Hub package publish endpoint.
    '''
    async def post(self):
        self.cell._pubtest['pkgdef'] = self.getJsonBody()
        self.cell._pubtest['pkgdef:apikey'] = self.request.headers.get('X-API-KEY')

        if self.cell._pubtest.get('pkgfail'):
            return self.sendRestErr('AuthDeny', 'Publishing requires the builder role.')

        return self.sendRestRetn({'iden': self.cell._pubtest['iden']})

class HubPackageFile(s_httpapi.Handler):
    '''
    Stand in for the Vertex Hub package file endpoint.
    '''
    async def head(self, name, version, sha256):

        self.cell._pubtest.setdefault('heads', []).append((name, version, sha256))
        self.cell._pubtest['file:apikey'] = self.request.headers.get('X-API-KEY')

        if sha256 not in self.cell._pubtest['files']:
            self.set_status(404)
            return self.sendRestErr('NoSuchFile', f'no file {sha256}')

        return self.sendRestRetn(True)

    async def put(self, name, version, sha256):

        self.cell._pubtest.setdefault('puts', []).append((name, version, sha256))
        self.cell._pubtest['files'][sha256] = self.request.body

        if self.cell._pubtest.get('putfail'):
            self.set_status(403)
            return self.sendRestErr('AuthDeny', 'Package files require the builder role.')

        self.set_status(201)
        return self.sendRestRetn(True)

class HubBadBody(s_httpapi.Handler):

    async def post(self):
        return self.write(b'this is not json')

class PkgPublishTest(s_test.SynTest):

    def setUp(self):
        super().setUp()

        # the tool has no TLS opt out ( it only ever talks to the real Vertex Hub ), so give
        # its session an unverified connector to reach the test cell's self signed port. The
        # real ctor is captured before patching, otherwise sess() re-enters itself.
        ctor = aiohttp.ClientSession

        def sess(*args, **kwargs):
            kwargs['connector'] = aiohttp.TCPConnector(ssl=False)
            return ctor(*args, **kwargs)

        patcher = mock.patch.object(aiohttp, 'ClientSession', sess)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def _addHubApis(self, core):
        core.addHttpApi('/api/v3/hub/packages', HubPackages, {'cell': core})
        core.addHttpApi(r'/api/v3/hub/packages/([\w.-]+)/([\w.-]+)/files/([0-9a-fA-F]{64})',
                        HubPackageFile, {'cell': core})

    @contextlib.contextmanager
    def getPkgProto(self):
        '''
        Mirror the package prototype, since publishing builds its docs into files/docs
        and must not write into the source tree. The proto loads a module from
        ../stormmod, resolved relative to the yaml, so that is copied alongside.
        '''
        srcpath = s_common.genpath(dirname, 'files', 'stormpkg')
        stormmod = s_common.genpath(dirname, 'files', 'stormmod')

        with self.getTestDir(copyfrom=srcpath) as dirn:
            shutil.copytree(stormmod, s_common.genpath(os.path.dirname(dirn), 'stormmod'))
            yield dirn

    async def test_tools_pkg_publish(self):

        with self.getPkgProto() as pkgdirn:

            ymlpath = s_common.genpath(pkgdirn, 'testpkg.yaml')
            datapath = s_common.genpath(pkgdirn, 'files', 'data.dat')

            with open(datapath, 'rb') as fd:
                databyts = fd.read()

            datasha256 = hashlib.sha256(databyts).hexdigest()

            nestpath = s_common.genpath(pkgdirn, 'files', 'sub', 'nested.dat')
            with open(nestpath, 'rb') as fd:
                nestbyts = fd.read()

            nestsha256 = hashlib.sha256(nestbyts).hexdigest()

            # publishing builds the package's docs/ into files/docs first (see
            # synapse.tools.storm.pkg.publish), so those built files are
            # declared/published right alongside data.dat/nested.dat. Build
            # once here (idempotent -- s_pkgpublish.main() below rebuilds the
            # same content) to compute their sha256s the same way data.dat's
            # is computed above, rather than hardcoding hashes that would go
            # stale the moment the doc build's own output changes.
            await s_gendocs.buildPkgDocs(ymlpath)

            docsdir = s_common.genpath(pkgdirn, 'files', 'docs')
            docfiles = []
            for root, dirs, names in os.walk(docsdir):
                dirs.sort()
                for name in sorted(names):
                    fp = os.path.join(root, name)
                    with open(fp, 'rb') as fd:
                        filesha256 = hashlib.sha256(fd.read()).hexdigest()
                    docfiles.append((os.path.relpath(fp, s_common.genpath(pkgdirn, 'files')), filesha256))

            # the mock hub is served by a test Cortex so the tool talks real HTTP
            async with self.getTestCore() as core:

                core._pubtest = {'files': {}, 'iden': s_common.guid()}

                addr, port = await core.addHttpsPort(0)
                await self._addHubApis(core)

                url = f'https://127.0.0.1:{port}'
                base = ('--url', url, '--apikey', 'hehe')

                outp = self.getTestOutp()
                self.eq(0, await s_pkgpublish.main(base + (ymlpath,), outp=outp))

                # the missing files are uploaded before the package is published --
                # data.dat, then the built docs/ files (walked in the same order
                # iterPkgProtoFiles declares them), then sub/nested.dat
                expected = ([('testpkg', '0.0.1', datasha256)]
                            + [('testpkg', '0.0.1', filesha256) for _relpath, filesha256 in docfiles]
                            + [('testpkg', '0.0.1', nestsha256)])
                self.eq(expected, core._pubtest['heads'])
                self.eq(expected, core._pubtest['puts'])
                self.eq(databyts, core._pubtest['files'][datasha256])
                self.eq(nestbyts, core._pubtest['files'][nestsha256])

                outp.expect(f'Uploading file: {datapath} ({datasha256})')
                outp.expect(f'Published package iden {core._pubtest["iden"]}')

                # the api key is sent with the file requests as well as the publish
                self.eq('hehe', core._pubtest['pkgdef:apikey'])
                self.eq('hehe', core._pubtest['file:apikey'])

                # the published pkgdef carries the sha256, never the file contents
                pkgdef = core._pubtest['pkgdef']
                self.eq('testpkg', pkgdef['name'])
                expectedfiles = {'data.dat': {'sha256': datasha256}}
                expectedfiles.update({relpath: {'sha256': filesha256} for relpath, filesha256 in docfiles})
                expectedfiles['sub/nested.dat'] = {'sha256': nestsha256}
                self.eq(expectedfiles, pkgdef['files'])

                # the walk order is the key order, so a rebuild is deterministic
                self.eq(list(expectedfiles), list(pkgdef['files']))

                # a published package always has its storm encrypted; there is no opt out
                encryption = pkgdef['metadata']['encryption']
                self.len(64, encryption['seed'])
                self.len(64, encryption['salt'])
                self.notin('deploy', encryption)
                self.ne('inet:ip\n', pkgdef['modules'][0]['storm'])

                # a second publish finds the file already present and skips the upload
                core._pubtest['heads'] = []
                core._pubtest['puts'] = []

                outp = self.getTestOutp()
                self.eq(0, await s_pkgpublish.main(base + (ymlpath,), outp=outp))

                self.eq(expected, core._pubtest['heads'])
                self.eq([], core._pubtest['puts'])
                outp.expect(f'Skipping existing file: {datapath} ({datasha256})')

                # a file upload failure stops the publish, re-raised as the SynErr the
                # Vertex Hub named in its REST envelope
                core._pubtest['files'] = {}
                core._pubtest['pkgdef'] = None
                core._pubtest['putfail'] = True

                outp = self.getTestOutp()
                with self.raises(s_exc.AuthDeny) as cm:
                    await s_pkgpublish.main(base + (ymlpath,), outp=outp)

                self.isin('Package files require the builder role', cm.exception.get('mesg'))
                outp.expect(f'Uploading file: {datapath}')
                self.none(core._pubtest['pkgdef'])

                core._pubtest['putfail'] = False

                # ...as does a publish failure, which the hub reports inside a 200
                core._pubtest['pkgfail'] = True

                with self.raises(s_exc.AuthDeny) as cm:
                    await s_pkgpublish.main(base + (ymlpath,))

                self.isin('Publishing requires the builder role', cm.exception.get('mesg'))

                core._pubtest['pkgfail'] = False

                # a code signature may be applied on the way out
                with self.getTestDir() as certdirn:

                    cdir = s_certdir.CertDir(path=certdirn)
                    cdir.genCaCert('testca')
                    cdir.genCodeCert('coder@vertex.link', signas='testca')

                    core._pubtest['files'] = {}

                    argv = base + ('--certdir', certdirn, '--signas', 'coder@vertex.link', ymlpath)
                    self.eq(0, await s_pkgpublish.main(argv))

                    codesign = core._pubtest['pkgdef']['metadata']['codesign']
                    self.nn(codesign.get('cert'))
                    self.nn(codesign.get('sign'))

                    # the signature covers the files section, so the file digests a
                    # package ships cannot be tampered with independently of it
                    pkgcopy = dict(core._pubtest['pkgdef'])
                    pkgcopy.pop('metadata')

                    cert = cdir.loadCertByts(codesign['cert'].encode())
                    pubk = s_rsa.PubKey(cert.public_key())
                    self.true(pubk.verifyitem(pkgcopy, s_common.uhex(codesign['sign'])))

                    pkgcopy['files'] = {'data.dat': {'sha256': 'ff' * 32}}
                    self.false(pubk.verifyitem(pkgcopy, s_common.uhex(codesign['sign'])))

    async def test_tools_pkg_publish_no_docs(self):
        '''
        Documentation is optional: publishing a package which ships no docs
        directory builds nothing (synapse.tools.storm.pkg.doc.buildPkgDocs) and
        publishes the package's other files as usual. Files are optional too:
        a package which ships none declares no files section and uploads nothing.
        '''
        with self.getPkgProto() as pkgdirn:

            ymlpath = s_common.genpath(pkgdirn, 'testpkg.yaml')

            # this fixture's logo lives under docs/, so relocate it (and repoint
            # the proto at it) before removing the directory -- what is under
            # test is a package with no docs/ tree at all
            shutil.move(s_common.genpath(pkgdirn, 'docs', 'foobar.svg'),
                        s_common.genpath(pkgdirn, 'foobar.svg'))
            shutil.rmtree(s_common.genpath(pkgdirn, 'docs'))

            pkgproto = s_common.yamlload(ymlpath)
            pkgproto['logo']['path'] = 'foobar.svg'
            s_common.yamlsave(pkgproto, ymlpath)

            async with self.getTestCore() as core:

                core._pubtest = {'files': {}, 'iden': s_common.guid()}

                addr, port = await core.addHttpsPort(0)
                await self._addHubApis(core)

                url = f'https://127.0.0.1:{port}'

                outp = self.getTestOutp()
                self.eq(0, await s_pkgpublish.main(('--url', url, '--apikey', 'hehe', ymlpath), outp=outp))

                # only the package's own files are declared -- no docs/ entries,
                # and the doc build left no files/docs behind
                pkgdef = core._pubtest['pkgdef']
                self.eq(['data.dat', 'sub/nested.dat'], list(pkgdef['files']))
                self.false(os.path.isdir(s_common.genpath(pkgdirn, 'files', 'docs')))

                # ...and with the files directory gone the package declares no
                # files section at all, so there is nothing to upload
                shutil.rmtree(s_common.genpath(pkgdirn, 'files'))

                core._pubtest['heads'] = []
                core._pubtest['puts'] = []

                outp = self.getTestOutp()
                self.eq(0, await s_pkgpublish.main(('--url', url, '--apikey', 'hehe', ymlpath), outp=outp))

                self.eq([], core._pubtest['heads'])
                self.eq([], core._pubtest['puts'])
                self.notin('files', core._pubtest['pkgdef'])

    async def test_tools_pkg_publish_apikey(self):

        with self.getPkgProto() as pkgdirn:

            ymlpath = s_common.genpath(pkgdirn, 'testpkg.yaml')

            async with self.getTestCore() as core:

                core._pubtest = {'files': {}, 'iden': s_common.guid()}

                addr, port = await core.addHttpsPort(0)
                await self._addHubApis(core)

                url = f'https://127.0.0.1:{port}'

                # an api key is required
                with self.setTstEnvars(VERTEX_HUB_APIKEY=None):
                    outp = self.getTestOutp()
                    self.eq(1, await s_pkgpublish.main(('--url', url, ymlpath), outp=outp))
                    outp.expect('An api key is required')

                # ...and may come from the environment instead of the command line
                with self.setTstEnvars(VERTEX_HUB_APIKEY='envkey'):
                    argv = ('--url', url, ymlpath)
                    self.eq(0, await s_pkgpublish.main(argv))

                self.eq('envkey', core._pubtest['pkgdef:apikey'])

    async def test_tools_pkg_publish_defurl(self):

        with self.getPkgProto() as pkgdirn:

            ymlpath = s_common.genpath(pkgdirn, 'testpkg.yaml')

            # --url defaults to the Vertex Hub, so a publish with no --url must target it.
            # Stop at the upload so nothing reaches the real hub.
            boom = mock.AsyncMock(side_effect=s_exc.SynErr(mesg='nope'))
            with mock.patch.object(s_pkgpublish, 'uploadPkgFiles', boom) as mok:
                with self.raises(s_exc.SynErr):
                    await s_pkgpublish.main(('--apikey', 'hehe', ymlpath))

            self.eq(s_pkgpublish.HUB_URL, mok.await_args.args[2])
            self.eq('https://hub.vertex.link', s_pkgpublish.HUB_URL)

    async def test_tools_pkg_publish_badbody(self):

        with self.getPkgProto() as pkgdirn:

            ymlpath = s_common.genpath(pkgdirn, 'testpkg.yaml')

            async with self.getTestCore() as core:

                core._pubtest = {'files': {}, 'iden': s_common.guid()}

                addr, port = await core.addHttpsPort(0)
                core.addHttpApi('/api/v3/hub/packages', HubBadBody, {'cell': core})
                core.addHttpApi(r'/api/v3/hub/packages/([\w.-]+)/([\w.-]+)/files/([0-9a-fA-F]{64})',
                                HubPackageFile, {'cell': core})

                url = f'https://127.0.0.1:{port}'
                argv = ('--url', url, '--apikey', 'hehe', ymlpath)

                # a response which is not a REST envelope at all still raises, as the
                # generic SynErr s_httpapi.result falls back to
                with self.raises(s_exc.SynErr) as cm:
                    await s_pkgpublish.main(argv)

                self.eq(s_exc.SynErr, type(cm.exception))
                self.isin('REST API request failed', cm.exception.get('mesg'))
