import os

import synapse.common as s_common

import synapse.tests.utils as s_test
import synapse.lib.mddocs as s_mddocs
import synapse.tools.utils.docmanifest as s_docmanifest

def _write(dirn, relpath, text):
    path = s_common.genpath(dirn, relpath)
    s_common.gendir(os.path.dirname(path))
    with open(path, 'w') as fd:
        fd.write(text)
    return path

class DocManifestTest(s_test.SynTest):

    async def test_docmanifest_writes_one_bundle(self):

        with self.getTestDir() as workdir:

            srcdir = s_common.gendir(workdir, 'docs')
            outdir = s_common.gendir(workdir, 'files', 'docs')

            src = '# Index\n\n```mdtoc\npage1.md\n```\n'
            _write(srcdir, 'index.md', src)
            _write(srcdir, 'page1.md', '# Page One\n')
            _write(outdir, 'index.md', '# Index\n\n- [Page One](page1.md)\n')
            _write(outdir, 'page1.md', '# Page One\n')

            outp = self.getTestOutp()
            self.eq(0, await s_docmanifest.main([srcdir, outdir], outp=outp))

            path = s_mddocs.getManifestPath(srcdir)
            entries = dict(s_mddocs.loadManifest(path))

            # index.md carries a directive so both sides are tracked; page1.md does not
            self.eq({'docs/index.md', 'files/docs/index.md'}, set(entries))
            self.eq(s_mddocs.hashFile(s_common.genpath(outdir, 'index.md')), entries['files/docs/index.md'])
            self.true(outp.expect('2 entries'))

    async def test_docmanifest_touches_only_its_own_bundle(self):

        with self.getTestDir() as workdir:

            for name in ('pkgA', 'pkgB'):
                srcdir = s_common.gendir(workdir, name, 'docs')
                outdir = s_common.gendir(workdir, name, 'files', 'docs')
                _write(srcdir, 'index.md', f'# {name}\n\n```mdtoc\npage1.md\n```\n')
                _write(srcdir, 'page1.md', '# Page One\n')
                _write(outdir, 'index.md', f'# {name}\n')
                _write(outdir, 'page1.md', '# Page One\n')

            pathA = s_mddocs.getManifestPath(s_common.genpath(workdir, 'pkgA', 'docs'))
            pathB = s_mddocs.getManifestPath(s_common.genpath(workdir, 'pkgB', 'docs'))

            argv = [s_common.genpath(workdir, 'pkgA', 'docs'), s_common.genpath(workdir, 'pkgA', 'files', 'docs')]
            self.eq(0, await s_docmanifest.main(argv, outp=self.getTestOutp()))

            self.true(os.path.isfile(pathA))
            self.false(os.path.isfile(pathB))

    async def test_docmanifest_resolves_a_relative_srcdir(self):

        # docs/Makefile passes absolute paths, but a relative one has to resolve
        # against the caller's cwd rather than somewhere else
        with self.getTestDir() as workdir:

            srcdir = s_common.gendir(workdir, 'pkg', 'docs')
            outdir = s_common.gendir(workdir, 'pkg', 'files', 'docs')
            _write(srcdir, 'index.md', '# Index\n\n```mdtoc\npage1.md\n```\n')
            _write(outdir, 'index.md', '# Index\n')

            cwd = os.getcwd()
            os.chdir(workdir)
            try:
                argv = [os.path.join('pkg', 'docs'), os.path.join('pkg', 'files', 'docs')]
                self.eq(0, await s_docmanifest.main(argv, outp=self.getTestOutp()))
            finally:
                os.chdir(cwd)

            entries = s_mddocs.loadManifest(s_common.genpath(workdir, 'pkg', 'docs.sha256'))
            self.eq({'docs/index.md', 'files/docs/index.md'}, {relpath for relpath, _ in entries})
