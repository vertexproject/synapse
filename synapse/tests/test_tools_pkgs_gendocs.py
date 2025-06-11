import io
import os
import sys
import json

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.pkgs.gendocs as s_t_gendocs
import synapse.tools.pkgs.pandoc_filter as s_t_pandoc_filter

class TestPkgBuildDocs(s_t_utils.SynTest):

    def setUp(self):
        if not s_t_gendocs.hasPandoc():
            self.skip('pandoc is not available')
        super().setUp()

    async def test_pkg_builddocs(self):

        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')
            self.true(os.path.isfile(testpkgfp))
            argv = [testpkgfp, ]
            r = await s_t_gendocs.main(argv)
            self.eq(r, 0)

            pkgdef = s_common.yamlload(testpkgfp)
            efiles = set()
            for dnfo in pkgdef.get('docs'):
                bname = os.path.basename(dnfo.get('path'))
                efiles.add(bname)
                efiles.add(bname.rsplit('.', 1)[0] + '.rst')
            builddir = os.path.join(dirn, 'docs', '_build')
            self.eq(efiles, set(os.listdir(builddir)))

            text = s_common.getbytes(os.path.join(builddir, 'bar.md')).decode()
            self.isin('storm> [inet:asn=1]', text)
            self.isin('inet:asn=1\n', text)
            self.notin(':orphan:', text)
            self.notin(':tocdepth:', text)

            text = s_common.getbytes(os.path.join(builddir, 'stormpackage.md')).decode()
            self.isin(':   baz (str): The baz.', text)
            self.isin(':   Baz the bam:\n\n        yield $lib.import(apimod).search(bam)', text)

        with self.getTestDir(mirror='testpkg_build_docs') as dirn:
            testpkgfp = os.path.join(dirn, 'testpkg.yaml')
            self.true(os.path.isfile(testpkgfp))
            argv = [testpkgfp, '--rst-only']
            r = await s_t_gendocs.main(argv)
            self.eq(r, 0)

            pkgdef = s_common.yamlload(testpkgfp)
            efiles = set()
            for dnfo in pkgdef.get('docs'):
                bname = os.path.basename(dnfo.get('path'))
                efiles.add(bname)
                efiles.add(bname.rsplit('.', 1)[0] + '.rst')
            builddir = os.path.join(dirn, 'docs', '_build')
            self.eq(efiles, set(os.listdir(builddir)))

            text = s_common.getbytes(os.path.join(builddir, 'bar.md')).decode()
            self.eq('', text)
            text = s_common.getbytes(os.path.join(builddir, 'stormpackage.md')).decode()
            self.eq('', text)

        with self.getTestDir(mirror='testpkg_build_docs') as dirn:

            # Missing input files
            testpkgfp = os.path.join(dirn, 'newp.yaml')
            self.false(os.path.isfile(testpkgfp))
            argv = [testpkgfp, ]
            with self.raises(s_exc.BadArg) as cm:
                await s_t_gendocs.main(argv)
            self.isin('Package does not exist or does not contain yaml', cm.exception.get('mesg'))

            # pandoc api version check coverage
            old_stdin = sys.stdin
            try:
                sys.stdin = io.StringIO(json.dumps({'pandoc-api-version': [2, 0, 0]}))
                with self.raises(Exception) as cm:
                    s_t_pandoc_filter.main()
                self.isin('does not match required version', str(cm.exception))
            finally:
                sys.stdin = old_stdin

            # pandoc failure
            outp = self.getTestOutp()
            oldv = s_t_gendocs.PANDOC_FILTER
            try:
                s_t_gendocs.PANDOC_FILTER = os.path.join(dirn, 'newp.py')
                with self.raises(s_exc.SynErr) as cm:
                    await s_t_gendocs.main([os.path.join(dirn, 'testpkg.yaml'),], outp=outp)
                self.isin('Error converting', cm.exception.get('mesg'))
                outp.expect('ERR: Error running filter')
            finally:
                s_t_gendocs.PANDOC_FILTER = oldv
