import os
import shutil

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json

import synapse.tests.utils as s_t_utils

import synapse.tools.storm.pkg.doc as s_t_gendocs

class TestPkgBuildDocs(s_t_utils.SynTest):

    async def test_storm_pkg_doc_base(self):
        # testpkg_build_docs/docs/ mirrors the shape a real package uses:
        # index.md (mdtoc), a plain page, a nested subdirectory with a
        # non-.md asset (proves verbatim copy), a mocks/ cassette (proves
        # it is never staged/published), and the existing
        # mdautodoc --stormpkg page.
        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')
            self.true(os.path.isfile(testpkgfp))

            argv = [testpkgfp, ]
            r = await s_t_gendocs.main(argv)
            self.eq(r, 0)

            outdir = os.path.join(dirn, 'files', 'docs')

            for relpath in ('index.md', 'userguide.md', 'stormpackage.md',
                             os.path.join('sub', 'nested.md'), os.path.join('sub', 'image.svg')):
                self.true(os.path.isfile(os.path.join(outdir, relpath)), msg=relpath)

            # mocks/ is a build input only -- never staged, never published
            self.false(os.path.isdir(os.path.join(outdir, 'mocks')))

            with open(os.path.join(outdir, 'stormpackage.md')) as fd:
                self.isin('# Storm Package: testpkg', fd.read())

            with open(os.path.join(outdir, 'userguide.md')) as fd:
                self.isin('<ANSI STANDARD PIZZA>', fd.read())

            metadata = s_json.jsload(outdir, 'metadata.json')
            # category is derived at manifest-delivery time (the Hub /
            # vtxtools.docsmanifest), never written into a package's own
            # built bundle
            self.notin('category', metadata)
            hrefs = {e['href'] for e in metadata['toc']}
            self.eq({'userguide.md', os.path.join('sub', 'nested.md').replace(os.sep, '/'), 'stormpackage.md'},
                     hrefs)

    async def test_storm_pkg_doc_missing_pkg(self):
        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'newp.yaml')
            self.false(os.path.isfile(testpkgfp))
            argv = [testpkgfp, ]
            with self.raises(s_exc.BadArg) as cm:
                await s_t_gendocs.main(argv)
            self.isin('Package does not exist or does not contain yaml', cm.exception.get('mesg'))

    async def test_storm_pkg_doc_missing_docsdir(self):
        # documentation is optional -- a package which ships no docs directory
        # builds nothing rather than failing, so synapse.tools.storm.pkg.publish
        # can build docs unconditionally on the way out
        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            shutil.rmtree(os.path.join(dirn, 'docs'))
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')

            self.none(await s_t_gendocs.buildPkgDocs(testpkgfp))
            self.eq(0, await s_t_gendocs.main([testpkgfp, ]))

            # nothing was built, and no staging dir was left behind
            self.false(os.path.isdir(os.path.join(dirn, 'files')))
            self.eq([], [n for n in os.listdir(dirn) if n.startswith('.docsbuild-')])

    async def test_storm_pkg_doc_save_override(self):
        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')
            savedir = os.path.join(dirn, 'altbuild')

            self.eq(0, await s_t_gendocs.main([testpkgfp, '--save', savedir]))

            self.true(os.path.isfile(os.path.join(savedir, 'metadata.json')))
            # the default files/docs location is untouched when --save overrides it
            self.false(os.path.isdir(os.path.join(dirn, 'files')))

    async def test_storm_pkg_doc_merges_static_content(self):
        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')
            outdir = os.path.join(dirn, 'files', 'docs')

            # simulate a previously-committed static page living in
            # files/docs that is no longer authored under docs/ at all
            # (e.g. changelog.md, git mv'd out of docs/ per the
            # docs/-vs-files/docs split).
            s_common.gendir(outdir)
            with open(os.path.join(outdir, 'changelog.md'), 'w') as fd:
                fd.write('# Changelog\n\nInitial release.\n')

            self.eq(0, await s_t_gendocs.main([testpkgfp, ]))

            # the static file survived the rebuild -- merge, not replace
            with open(os.path.join(outdir, 'changelog.md')) as fd:
                self.isin('Initial release.', fd.read())

            # the build's own output still landed correctly
            self.true(os.path.isfile(os.path.join(outdir, 'userguide.md')))
            self.true(os.path.isfile(os.path.join(outdir, 'stormpackage.md')))
            self.true(os.path.isfile(os.path.join(outdir, 'metadata.json')))

    async def test_storm_pkg_doc_save_override_falls_back_to_real_files_docs(self):
        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')

            # seed the REAL files/docs with a static changelog.md, as if a
            # prior migration had already git mv'd it out of docs/
            realoutdir = os.path.join(dirn, 'files', 'docs')
            s_common.gendir(realoutdir)
            with open(os.path.join(realoutdir, 'changelog.md'), 'w') as fd:
                fd.write('# Changelog\n\nInitial release.\n')

            # wire index.md's mdtoc to reference it, like a real
            # post-migration bundle would
            indexfp = os.path.join(dirn, 'docs', 'index.md')
            with open(indexfp, 'w') as fd:
                fd.write('# testpkg\n\n```mdtoc\nuserguide.md\nsub/nested.md\nstormpackage.md\nchangelog.md\n```\n')

            savedir = os.path.join(dirn, 'altbuild')
            argv = [testpkgfp, '--save', savedir]
            self.eq(0, await s_t_gendocs.main(argv))

            # changelog.md's title resolved via the real files/docs, even
            # though this build's own output went to savedir instead
            metadata = s_json.jsload(savedir, 'metadata.json')
            hrefs = {e['href']: e['title'] for e in metadata['toc']}
            self.eq('Changelog', hrefs['changelog.md'])

            # changelog.md was never copied into savedir -- staticdir is
            # read-only fallback, and always the package's real
            # files/docs, independent of --save
            self.false(os.path.isfile(os.path.join(savedir, 'changelog.md')))

    async def test_storm_pkg_doc_stale_output_preserved(self):
        # With merge semantics, files in outdir that aren't part of the
        # staged build are preserved (not removed). This allows static
        # content (changelog.md, images, etc.) to persist across builds.
        # Stale pages must be manually `git rm`'d alongside source deletion.
        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')
            outdir = os.path.join(dirn, 'files', 'docs')
            stalefp = os.path.join(outdir, 'stale.txt')
            with s_common.genfile(stalefp) as fd:
                fd.write(b'stale')

            self.eq(0, await s_t_gendocs.main([testpkgfp, ]))

            # the static file survived the rebuild -- merge, not replace
            self.true(os.path.isfile(stalefp))

    async def test_storm_pkg_doc_ci_flag_writes_warn_file(self):
        with self.getTestDir(mirror='testpkg_build_docs_no_h1') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')
            warnfp = os.path.join(dirn, 'docbuild.warn')

            self.eq(0, await s_t_gendocs.main([testpkgfp, '--ci', '--warnfile', warnfp]))

            with open(warnfp) as fd:
                warntext = fd.read()
            self.isin('no H1 heading in noh1.md', warntext)

            # docbuild.warn is build-time-only -- it must never be merged
            # into the committed bundle alongside the pages it built.
            outdir = os.path.join(dirn, 'files', 'docs')
            self.false(os.path.isfile(os.path.join(outdir, 'docbuild.warn')))

    async def test_storm_pkg_doc_ci_flag_no_warnfile_drops_issues(self):
        # --ci without --warnfile still builds (never raises) -- the
        # issues are simply not persisted anywhere, same as a caller that
        # doesn't care to collect them.
        with self.getTestDir(mirror='testpkg_build_docs_no_h1') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')

            self.eq(0, await s_t_gendocs.main([testpkgfp, '--ci']))

            outdir = os.path.join(dirn, 'files', 'docs')
            self.false(os.path.isfile(os.path.join(outdir, 'docbuild.warn')))

    async def test_storm_pkg_doc_no_h1_raises(self):
        # SYN-11304: a doc's title (and metadata.json entry) is discovered
        # from its first H1 heading; a page with none fails the build.
        with self.getTestDir(mirror='testpkg_build_docs_no_h1') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')

            with self.raises(s_exc.SynErr) as cm:
                await s_t_gendocs.main([testpkgfp, ])
            issues = cm.exception.get('issues')
            self.true(any('no H1 heading in noh1.md' in i for i in issues))
