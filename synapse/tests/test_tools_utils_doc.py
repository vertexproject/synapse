import os

import synapse.common as s_common

import synapse.tests.utils as s_t_utils

import synapse.tools.utils.doc as s_t_doc

def _write(dirn, relpath, text):
    path = s_common.genpath(dirn, relpath)
    s_common.gendir(os.path.dirname(path))
    with open(path, 'w') as fd:
        fd.write(text)
    return path

class TestUtilsDoc(s_t_utils.SynTest):

    async def test_utils_doc_base(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '# Page One\n')

            self.eq(0, await s_t_doc.main([srcdir, outdir]))

            self.true(os.path.isfile(os.path.join(outdir, 'page1.md')))
            self.true(os.path.isfile(os.path.join(outdir, 'metadata.json')))

    async def test_utils_doc_staticdir(self):
        # a mdtoc target that lives only in a committed bundle dir --
        # never staged from srcdir -- resolves via --staticdir, the same
        # way it would for a Storm package's own files/docs.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir, self.getTestDir() as staticdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'changelog.md',
                '```',
                '',
            )))
            _write(staticdir, 'changelog.md', '# Changelog\n')

            self.eq(0, await s_t_doc.main([srcdir, outdir, '--staticdir', staticdir]))

            # resolved via staticdir for the toc/title, but never copied
            # into outdir -- staticdir is a read-only fallback
            self.false(os.path.isfile(os.path.join(outdir, 'changelog.md')))
            with open(os.path.join(outdir, 'index.md')) as fd:
                self.isin('[Changelog](changelog.md)', fd.read())

    async def test_utils_doc_ci_flag_writes_warn_file(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n\nno toc here\n')
            _write(srcdir, 'orphan.md', '# Orphan\n')
            warnfp = os.path.join(outdir, 'docbuild.warn')

            self.eq(0, await s_t_doc.main([srcdir, outdir, '--ci', '--warnfile', warnfp]))

            with open(warnfp) as fd:
                self.isin('orphan.md', fd.read())

    async def test_utils_doc_ci_flag_no_warnfile_drops_issues(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n\nno toc here\n')
            _write(srcdir, 'orphan.md', '# Orphan\n')

            self.eq(0, await s_t_doc.main([srcdir, outdir, '--ci']))

            self.false(os.path.isfile(os.path.join(outdir, 'docbuild.warn')))

    async def test_utils_doc_bad_srcdir_raises(self):
        with self.getTestDir() as outdir:
            srcdir = os.path.join(outdir, 'doesnotexist')
            with self.raises(FileNotFoundError):
                await s_t_doc.main([srcdir, os.path.join(outdir, 'built')])
