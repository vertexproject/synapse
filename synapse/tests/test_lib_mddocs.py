import os
import shutil
import hashlib
import logging
import tempfile
from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.mddocs as s_mddocs

import synapse.tests.utils as s_test

def _write(dirn, relpath, text):
    path = s_common.genpath(dirn, relpath)
    s_common.gendir(os.path.dirname(path))
    with open(path, 'w') as fd:
        fd.write(text)
    return path

def _writemanifest(path, entries):
    '''
    Write a docs.sha256-shaped manifest at path from (relpath, sha256hex)
    entries -- the same shape gen_docs_manifest.saveManifest/loadManifest
    read and write, built by hand here so a test can pin an entry to
    whatever hash it wants (a real hashFile() call for a "matches" case, or
    a deliberately wrong hex string for a "drifted" one) without needing the
    enterprise-only gen_docs_manifest.py.
    '''
    with open(path, 'w') as fd:
        fd.write('# test manifest\n')
        for relpath, hexdigest in entries:
            fd.write(f'{hexdigest}  {relpath}\n')

class _FakeMdStorm:
    '''A fake MdStorm that emits two log.warning() calls instead of processing directives, for testing runMdstorm's warning capture/classification without needing a real Cortex-triggered warning.'''

    def __init__(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def run(self):
        logger = logging.getLogger('synapse.tests.test_lib_mddocs._FakeMdStorm')
        logger.warning('Sysctl values different than expected: vm.foo')  # on WARNINGS_IGNORE
        logger.warning('A totally new, never-seen-before problem.')  # not on any list
        return ['# Page One\n']

    @classmethod
    async def anit(cls, path, mockhttp=None, srcdir=None, outdir=None):
        return cls()

class MdDocsTest(s_test.SynTest):

    def test_stagetree_copies_verbatim_and_skips_mocks(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n')
            _write(srcdir, 'sub/image.svg', '<svg></svg>')
            _write(srcdir, 'mocks/cassette.yaml', 'interactions: []\n')

            s_mddocs.stageTree(srcdir, outdir)

            with open(s_common.genpath(outdir, 'sub', 'image.svg')) as fd:
                self.eq('<svg></svg>', fd.read())
            self.false(os.path.isdir(s_common.genpath(outdir, 'mocks')))

    async def test_builddocs_basic_toc_and_mdtoc_rendering(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                'Some content.',
                '',
            )))

            metadata = await s_mddocs.buildDocs(srcdir, outdir)

            # category is no longer part of a built bundle's own metadata --
            # see synmods.hub.app.HubCell.getDocsManifest / vtxtools.docsmanifest
            self.notin('category', metadata)
            self.eq(1, len(metadata['toc']))
            self.eq('Page One', metadata['toc'][0]['title'])
            self.eq('page1.md', metadata['toc'][0]['href'])

            with open(s_common.genpath(outdir, 'index.md')) as fd:
                text = fd.read()
            self.isin('- [Page One](page1.md)', text)
            self.notin('```mdtoc', text)

            self.true(os.path.isfile(s_common.genpath(outdir, 'metadata.json')))
            onfile = s_json.jsload(outdir, 'metadata.json')
            self.eq(metadata, onfile)

    async def test_builddocs_staticdir_fallback_for_toc_and_links(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir, self.getTestDir() as staticdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                'changelog.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                'See the [changelog](changelog.md).',
                '',
            )))
            # changelog.md lives only in staticdir -- it simulates a plain
            # page that was git mv'd out of docs/ into files/docs and is
            # never staged/rebuilt, per the docs/-vs-files/docs split.
            _write(staticdir, 'changelog.md', '\n'.join((
                '# Changelog',
                '',
                'Initial release.',
                '',
            )))

            metadata = await s_mddocs.buildDocs(srcdir, outdir, staticdir=staticdir)

            self.eq(2, len(metadata['toc']))
            self.eq('Page One', metadata['toc'][0]['title'])
            self.eq('Changelog', metadata['toc'][1]['title'])

            # changelog.md was never staged/copied into outdir -- staticdir
            # is read-only fallback, never written to.
            self.false(os.path.isfile(s_common.genpath(outdir, 'changelog.md')))

    async def test_builddocs_staticdir_missing_target_still_raises(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir, self.getTestDir() as staticdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'changelog.md',
                '```',
                '',
            )))
            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir, staticdir=staticdir)
            self.isin('mdtoc target does not exist: changelog.md', cm.exception.get('issues'))
            # the issue text must also be in mesg -- reprexc() (what a CLI's
            # wrapmain prints) only ever shows mesg, never the issues= field
            self.isin('mdtoc target does not exist: changelog.md', cm.exception.get('mesg'))

    async def test_builddocs_mdstorm_fence_executes(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '```mdstorm-setup',
                '```',
                '',
                '```mdstorm',
                '$lib.print(hello)',
                '```',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                text = fd.read()
            self.isin('storm> $lib.print(hello)', text)

    async def test_builddocs_strips_leading_blank_lines_from_hidden_fences(self):
        # a hidden ```mdstorm-setup/```mdstorm --hide fence produces zero
        # output lines of its own, but the blank lines separating/following
        # them in the source (never part of any fence's own span) are
        # ordinary content and get printed as-is -- leaving a page that
        # opens with several blank lines before its real content. Invisible
        # in a rendered HTML page, but a real eyesore in the raw Markdown
        # this build now commits directly. Every page's own first fence is
        # exactly this shape (mdstorm-setup, then one or more --hide auth
        # setup fences), so this is the common case, not an edge case.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '```mdstorm-setup',
                '```',
                '',
                '```mdstorm --hide',
                'auth.user.add visi',
                '```',
                '',
                '# Page One',
                '',
                'Some content.',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                text = fd.read()
            self.eq('# Page One\n\nSome content.\n', text)

    async def test_builddocs_collapses_blank_run_after_explicit_anchor(self):
        # a page opening with an explicit <a id="..."> anchor tag (real
        # content, not blank) followed by the same hidden-fence pattern
        # still ends up with a run of several blank lines before its H1 --
        # collapsed to exactly one, not stripped entirely, since the
        # anchor tag itself is real leading content.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '<a id="page1"></a>',
                '',
                '```mdstorm-setup',
                '```',
                '',
                '```mdstorm --hide',
                'auth.user.add visi',
                '```',
                '',
                '```mdstorm --hide',
                'auth.role.add ninjas',
                '```',
                '',
                '# Page One',
                '',
                'Some content.',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                text = fd.read()
            self.eq('<a id="page1"></a>\n\n# Page One\n\nSome content.\n', text)

    async def test_builddocs_mockhttp_resolves_from_srcdir_not_staged(self):
        # a bundle's mocks/ directory is never staged (see stageTree); a
        # ```mdstorm --mock-http fence must still resolve its cassette
        # against the ORIGINAL source tree (MdStorm.srcbasedir), the same
        # way ```mdautodoc --stormpkg does (see
        # test_builddocs_mdautodoc_stormpkg_via_srcbasedir below).
        cassette = self.getTestFilePath('mdstorm', 'httprespmulti.yaml')
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            s_common.gendir(srcdir, 'mocks')
            shutil.copy(cassette, s_common.genpath(srcdir, 'mocks', 'cassette.yaml'))
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '```mdstorm-setup',
                '--vcr-opts \'{"record_mode": "none"}\'',
                '```',
                '',
                '```mdstorm --mock-http mocks/cassette.yaml',
                '$resp=$lib.inet.http.get("http://example.com") '
                '[ it:dev:str=$resp.body.decode() ]',
                '```',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

            self.false(os.path.isdir(s_common.genpath(outdir, 'mocks')))
            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                text = fd.read()
            self.isin('<ANSI STANDARD PIZZA>', text)

    async def test_builddocs_nested_headings_as_children(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '## Section A',
                '',
                'text',
                '',
                '### Subsection A1',
                '',
                'text',
                '',
                '## Section B',
                '',
                'text',
                '',
            )))

            metadata = await s_mddocs.buildDocs(srcdir, outdir)

            page1 = metadata['toc'][0]
            self.eq('Page One', page1['title'])
            children = page1['children']
            self.eq(['Section A', 'Section B'], [c['title'] for c in children])
            self.eq('page1.md#section-a', children[0]['href'])

            # depth 3 (Subsection A1) is present since it is within TOC_MAX_DEPTH
            self.isin('children', children[0])
            self.eq(['Subsection A1'], [c['title'] for c in children[0]['children']])
            self.eq('page1.md#subsection-a1', children[0]['children'][0]['href'])

    async def test_builddocs_child_page_with_own_mdtoc_recurses(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'guide.md',
                '```',
                '',
            )))
            _write(srcdir, 'guide.md', '\n'.join((
                '# Guide',
                '',
                '```mdtoc',
                'sub/one.md',
                '```',
                '',
            )))
            _write(srcdir, 'sub/one.md', '# Sub One\n\ntext\n')

            metadata = await s_mddocs.buildDocs(srcdir, outdir)

            guide = metadata['toc'][0]
            self.eq('Guide', guide['title'])
            self.eq([{'title': 'Sub One', 'href': 'sub/one.md'}], guide['children'])

    async def test_builddocs_missing_mdtoc_target_raises(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'doesnotexist.md',
                '```',
                '',
            )))

            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir)
            self.isin('doesnotexist.md', str(cm.exception.get('issues')))

    async def test_builddocs_orphan_page_raises(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n\nno toc here\n')
            _write(srcdir, 'orphan.md', '# Orphan\n')

            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir)
            issues = cm.exception.get('issues')
            self.true(any('orphan.md' in i for i in issues))

    async def test_builddocs_page_reachable_via_plain_link_not_orphan(self):
        # a page reached only through an ordinary in-page Markdown link
        # (a curated bullet list, say) rather than a ```mdtoc fence is
        # still reachable, and must not be flagged as an orphan
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                'See also:',
                '',
                '- [Curated Page](curated.md)',
                '',
            )))
            _write(srcdir, 'curated.md', '# Curated Page\n')

            # must not raise
            await s_mddocs.buildDocs(srcdir, outdir)

    async def test_builddocs_page_reachable_only_transitively_not_orphan(self):
        # reachability is transitive: a page linked from a page that is
        # itself only reachable via mdtoc still counts as reachable
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'section.md',
                '```',
                '',
            )))
            _write(srcdir, 'section.md', '\n'.join((
                '# Section',
                '',
                '- [Leaf Page](leaf.md)',
                '',
            )))
            _write(srcdir, 'leaf.md', '# Leaf Page\n')

            # must not raise
            await s_mddocs.buildDocs(srcdir, outdir)

    async def test_builddocs_broken_link_target_raises(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '# Page One\n\n[bad link](nope.md)\n')

            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir)
            issues = cm.exception.get('issues')
            self.true(any('nope.md' in i for i in issues))

    async def test_builddocs_broken_anchor_raises(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '# Page One\n\n[bad anchor](page2.md#nosuchanchor)\n')
            _write(srcdir, 'page2.md', '# Page Two\n\n## Real Section\n')

            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir)
            issues = cm.exception.get('issues')
            self.true(any('nosuchanchor' in i for i in issues))

    async def test_builddocs_good_anchor_link_does_not_raise(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '# Page One\n\n[good anchor](page2.md#real-section)\n')
            _write(srcdir, 'page2.md', '# Page Two\n\n## Real Section\n')

            await s_mddocs.buildDocs(srcdir, outdir)

    async def test_builddocs_same_file_anchor_link(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '[jump down](#down-here)',
                '',
                '## Down Here',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

    async def test_builddocs_explicit_anchor_tag_resolves(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '# Page One\n\n[to conf](page2.md#conf-somevar)\n')
            _write(srcdir, 'page2.md', '# Page Two\n\n<a id="conf-somevar"></a>\n\n### somevar\n')

            await s_mddocs.buildDocs(srcdir, outdir)

    async def test_builddocs_no_h1_heading_raises(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                'page2.md',
                '```',
                '',
            )))
            # no headings at all
            _write(srcdir, 'page1.md', 'Just prose, no heading.\n')
            # a heading, but never an H1
            _write(srcdir, 'page2.md', '## Not An H1\n\ntext\n')

            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir)
            issues = cm.exception.get('issues')
            self.true(any('no H1 heading in page1.md' in i for i in issues))
            self.true(any('no H1 heading in page2.md' in i for i in issues))

    async def test_builddocs_h1_need_not_be_the_first_heading(self):
        # the title is the first H1 heading *anywhere* in the file, not
        # necessarily the file's first heading overall
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '## Preamble',
                '',
                '# The Real Title',
                '',
                'text',
                '',
            )))

            metadata = await s_mddocs.buildDocs(srcdir, outdir)
            self.eq('The Real Title', metadata['toc'][0]['title'])

    async def test_builddocs_ci_mode_writes_warn_file(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n\nno toc here\n')
            _write(srcdir, 'orphan.md', '# Orphan\n')

            # must not raise in ci mode
            metadata = await s_mddocs.buildDocs(srcdir, outdir, ci=True)
            self.notin('category', metadata)

            with open(s_common.genpath(outdir, 'docbuild.warn')) as fd:
                warntext = fd.read()
            self.isin('orphan.md', warntext)

    async def test_builddocs_ci_mode_writes_empty_warn_file_when_clean(self):
        # gen_docs_junit.py distinguishes a missing file (package not built
        # this run -- skipped) from an empty one (built cleanly -- passed),
        # so a clean ci-mode build must still write the file, just empty.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n\nno issues here\n')

            await s_mddocs.buildDocs(srcdir, outdir, ci=True)

            with open(s_common.genpath(outdir, 'docbuild.warn')) as fd:
                warntext = fd.read()
            self.eq('', warntext)

    async def test_builddocs_absolute_doclink_does_not_raise(self):
        # a cross-bundle Vertex Hub link (/docs/<name>/<version>/<path>.md)
        # cannot be resolved against this single bundle -- it is shape-checked
        # only, and does not count as a broken link or an orphan-reachability
        # link.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '[other bundle](/docs/synapse-enterprise-optic/latest/user_interface/userguide.md#foo)',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

    async def test_builddocs_bare_bundle_root_doclink_does_not_raise(self):
        # a bare /docs/<name>/<version>(/) reference (no path) links to a whole
        # bundle's docs, not a specific page -- valid with or without the
        # trailing slash.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '[with slash](/docs/synapse-enterprise-optic/latest/)',
                '[without slash](/docs/synapse-enterprise-search/latest)',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

    async def test_builddocs_malformed_absolute_doclink_raises(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '[bad shape](/docs/synapse-enterprise-optic/latest/userguide.html)',
                '',
            )))

            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir)
            issues = cm.exception.get('issues')
            self.true(any('malformed cross-bundle doc link' in i for i in issues))

    async def test_builddocs_mdautodoc_conf_integration(self):
        # a ```mdautodoc --conf fence resolves at the point of use, as part
        # of the same mdstorm pass as every other directive -- no separate
        # autodoc pre-pass or savedir is involved.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdautodoc --conf synapse.lib.aha.AhaCell',
                '```',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

            with open(s_common.genpath(outdir, 'index.md')) as fd:
                text = fd.read()
            self.notin('```mdautodoc', text)
            self.isin('### aha:name', text)

    async def test_builddocs_srcdir_unmodified(self):
        # the build must never mutate srcdir -- only outdir
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

            await s_mddocs.buildDocs(srcdir, outdir)

            with open(s_common.genpath(srcdir, 'index.md')) as fd:
                srctext = fd.read()
            self.isin('```mdtoc', srctext)

    def test_classifywarnings_ignore_error_and_unhandled(self):
        msgs = [
            'Sysctl values different than expected: foo',  # WARNINGS_IGNORE
            'Prop foo:bar is deprecated or using a deprecated type baz.',  # WARNINGS_ERROR
            'A totally new, never-seen-before problem.',  # neither list
        ]
        issues = s_mddocs._classifyWarnings(msgs)
        self.eq(['Prop foo:bar is deprecated or using a deprecated type baz.',
                  'unhandled warning: A totally new, never-seen-before problem.'], issues)

    def test_classifywarnings_ignores_expected_storm_fail_errors(self):
        # a ```mdstorm --fail fence's query is *expected* to raise; the
        # Cortex logs the failure regardless (unaware of --fail's
        # semantics), so that log line must be ignored
        msgs = [
            "Error during storm execution for { [ inet:ip=woot.com inet:ip=22.22.22.22 ] }",
        ]
        self.eq([], s_mddocs._classifyWarnings(msgs))

    def test_classifywarnings_reports_schedcoro_task_errors(self):
        # a task raising out through Base.schedCoro() is a real error worth
        # failing a doc build over, and is never one of the records an
        # expected ```mdstorm --fail failure produces: a failing query's
        # exception is raised to whoever is running the query.
        mesg = ("Task <Task finished name='Task-1755' coro=<schedGenr.<locals>.genrtask() done, "
                "defined at synapse/lib/base.py:835> exception=BadTypeValu(...)> "
                "scheduled through Base.schedCoro raised exception")
        self.eq([f'unhandled warning: {mesg}'], s_mddocs._classifyWarnings([mesg]))

    def test_classifywarnings_ignores_load_svc_connect_race(self):
        # A ```mdstorm-setup --load-svc fence's Telepath clientv2 may log
        # one failed connect attempt against the just-registered service's
        # dmon before its listener finishes coming up -- benign, since
        # clientv2 retries automatically and the storm calls still succeed.
        msgs = [
            "telepath clientv2 (tcp://root:****@127.0.0.1:41611/svc) encountered an error: "
            "[Errno 111] Connect call failed ('127.0.0.1', 41611)",
        ]
        self.eq([], s_mddocs._classifyWarnings(msgs))

    def test_classifywarnings_ignores_ahacell_teardown_race(self):
        # A doc fixture that boots its own ephemeral AHA network (e.g.
        # synmods.fixtures.search.MdstormCortex) logs this benign ordering
        # artifact on teardown.
        msgs = ['AhaCell is fini. Unable to set 000.aha.synapse as down.']
        self.eq([], s_mddocs._classifyWarnings(msgs))

    async def test_runmdstorm_captures_and_classifies_warnings(self):
        with self.getTestDir() as outdir:
            _write(outdir, 'page1.md', '# Page One\n')

            origcls = s_mddocs.s_mdstorm.MdStorm
            s_mddocs.s_mdstorm.MdStorm = _FakeMdStorm
            try:
                issues = await s_mddocs.runMdstorm(outdir)
            finally:
                s_mddocs.s_mdstorm.MdStorm = origcls

            self.isin('page1.md', issues)
            self.eq(['unhandled warning: A totally new, never-seen-before problem.'], issues['page1.md'])

    async def test_builddocs_surfaces_unhandled_mdstorm_warning(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '# Page One\n')

            origcls = s_mddocs.s_mdstorm.MdStorm
            s_mddocs.s_mdstorm.MdStorm = _FakeMdStorm
            try:
                with self.raises(s_exc.SynErr) as cm:
                    await s_mddocs.buildDocs(srcdir, outdir)
            finally:
                s_mddocs.s_mdstorm.MdStorm = origcls

            issues = cm.exception.get('issues')
            self.true(any('A totally new, never-seen-before problem.' in i for i in issues))

    async def test_builddocs_child_page_with_no_headings_has_no_children(self):
        # a page WITH an H1 title but no sub-headings simply has no toc children
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'plain.md',
                '```',
                '',
            )))
            _write(srcdir, 'plain.md', '# Plain Page\n\nJust prose, no sub-headings.\n')

            metadata = await s_mddocs.buildDocs(srcdir, outdir)
            entry = metadata['toc'][0]
            self.notin('children', entry)

    async def test_builddocs_link_to_external_url_is_not_validated(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '- [Page One](page1.md)',
                '',
            )))
            _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '[external](https://vertex.link/)',
                '[mail](mailto:info@vertex.link)',
                '',
            )))

            # must not raise -- external links are out of scope for link validation
            await s_mddocs.buildDocs(srcdir, outdir)

    def test_headingchildren_orphaned_deep_heading_is_dropped(self):
        # a heading deeper than the expected level with no intervening
        # parent heading (e.g. "# Title" directly followed by "### Deep")
        # is dropped rather than mis-nested
        headings = [(1, 'Title', 'title'), (3, 'Deep', 'deep')]
        children = s_mddocs._headingChildren(headings, minlvl=2, maxdepth=2)
        self.eq([], children)

    def test_headingchildren_extra_depth_beyond_limit_is_skipped(self):
        # a heading nested deeper than maxdepth allows is skipped over
        # entirely, rather than appearing as a sibling of its ancestor
        headings = [
            (1, 'Title', 'title'),
            (2, 'Section', 'section'),
            (3, 'Sub', 'sub'),
            (4, 'Too Deep', 'too-deep'),
            (2, 'Next Section', 'next-section'),
        ]
        children = s_mddocs._headingChildren(headings, minlvl=2, maxdepth=1)
        self.eq(['Section', 'Next Section'], [c['title'] for c in children])
        self.notin('children', children[0])

    async def test_builddocs_mdautodoc_stormpkg_via_srcbasedir(self):
        # A Storm package's own yaml commonly lives as a sibling of the doc
        # bundle's srcdir (e.g. packages/<pkg>/docs next to
        # packages/<pkg>/<pkg>.yaml, or synmods/<mod>/assets/docs next to
        # synmods/<mod>/assets/<pkg>.yaml) -- --stormpkg resolves against
        # the ORIGINAL srcdir (MdStorm.srcbasedir), not the staged outdir,
        # so no source outside srcdir needs to be staged to reach it.
        with self.getTestDir() as workdir, self.getTestDir() as outdir:
            srcdir = s_common.genpath(workdir, 'docs')
            s_common.yamlsave({'name': 'srcbasedirpkg', 'version': '0.0.1'},
                              s_common.genpath(workdir, 'srcbasedirpkg.yaml'))
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdautodoc --stormpkg ../srcbasedirpkg.yaml',
                '```',
                '',
            )))

            await s_mddocs.buildDocs(srcdir, outdir)

            with open(s_common.genpath(outdir, 'index.md')) as fd:
                text = fd.read()
            self.isin('# Storm Package: srcbasedirpkg', text)

    async def test_buildbundle_merges_into_outdir_without_touching_static_content(self):
        # buildBundle stages into a private tempdir (sibling of outdir) and
        # merges the result in -- outdir may already hold static content
        # (e.g. changelog.md, moved out of docs/ per the docs/-vs-committed
        # split) that this build never staged and must leave untouched.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                'changelog.md',
                '```',
                '',
            )))
            _write(srcdir, 'page1.md', '# Page One\n')
            _write(outdir, 'changelog.md', '# Changelog\n\nstatic, never staged\n')

            metadata = await s_mddocs.buildBundle(srcdir, outdir)

            self.eq(2, len(metadata['toc']))
            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                self.isin('Page One', fd.read())
            with open(s_common.genpath(outdir, 'changelog.md')) as fd:
                self.isin('static, never staged', fd.read())

            # the staging tempdir is cleaned up -- nothing but the build's
            # own output (and the pre-existing static content) is left
            self.eq({'index.md', 'page1.md', 'changelog.md', 'metadata.json'}, set(os.listdir(outdir)))

    async def test_buildbundle_defaults_staticdir_to_outdir(self):
        # with no explicit staticdir, a mdtoc target that resolves only to
        # pre-existing content in outdir itself still resolves.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'changelog.md',
                '```',
                '',
            )))
            _write(outdir, 'changelog.md', '# Changelog\n')

            metadata = await s_mddocs.buildBundle(srcdir, outdir)
            self.eq(['changelog.md'], [e['href'] for e in metadata['toc']])

    async def test_buildbundle_ci_warnfile_excluded_from_merge(self):
        # docbuild.warn is build-time-only -- it must never be merged into
        # outdir alongside the pages it built (SYN-11365).
        with self.getTestDir() as srcdir, self.getTestDir() as outdir, self.getTestDir() as otherdir:
            _write(srcdir, 'index.md', '# Index\n\nno toc here\n')
            _write(srcdir, 'orphan.md', '# Orphan\n')
            warnfile = s_common.genpath(otherdir, 'synapse.warn')

            await s_mddocs.buildBundle(srcdir, outdir, ci=True, warnfile=warnfile)

            with open(warnfile) as fd:
                self.isin('orphan.md', fd.read())
            self.false(os.path.isfile(s_common.genpath(outdir, 'docbuild.warn')))

    async def test_buildbundle_ci_without_warnfile_drops_issues(self):
        # --ci with no warnfile still builds (never raises) -- the issues
        # are simply not persisted anywhere.
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n\nno toc here\n')
            _write(srcdir, 'orphan.md', '# Orphan\n')

            await s_mddocs.buildBundle(srcdir, outdir, ci=True)

            self.false(os.path.isfile(s_common.genpath(outdir, 'docbuild.warn')))

    async def test_buildbundle_non_ci_raises_and_never_merges(self):
        with self.getTestDir() as srcdir, self.getTestDir() as outdir:
            _write(srcdir, 'index.md', '# Index\n\nno toc here\n')
            _write(srcdir, 'orphan.md', '# Orphan\n')

            with self.raises(s_exc.SynErr):
                await s_mddocs.buildBundle(srcdir, outdir)

            # a failed build leaves outdir untouched -- nothing was merged
            self.eq([], os.listdir(outdir))

    async def test_buildbundle_stagedir_parent_override(self):
        # A Storm package's outdir (files/docs) is nested one level inside
        # its declared files/ tree -- staging a sibling of outdir alone
        # (files/.docsbuild-xxx) would still leave the tempdir inside
        # files/, where a live, self-referential ```mdstorm-setup
        # --load-svc``` fence declares and serves its files straight off
        # disk. That fence would then see the half-built staging dir as
        # one of its own declared files and fail its sha256 check
        # mid-build (this actually happened -- a real regression caught in
        # CI, not a hypothetical). stagedir_parent lets a caller (see
        # buildPkgDocs) name the tree's real root -- files/'s parent --
        # instead of outdir's immediate parent.
        with self.getTestDir() as workdir:
            pkgdir = s_common.gendir(workdir, 'pkgdir')
            srcdir = s_common.genpath(workdir, 'docs')
            outdir = s_common.genpath(pkgdir, 'files', 'docs')
            _write(srcdir, 'index.md', '# Index\n')

            seen = []
            realmkdtemp = tempfile.mkdtemp

            def spy(*args, **kwargs):
                path = realmkdtemp(*args, **kwargs)
                seen.append(kwargs.get('dir'))
                return path

            with mock.patch('tempfile.mkdtemp', spy):
                await s_mddocs.buildBundle(srcdir, outdir, stagedir_parent=pkgdir)

            self.len(1, seen)
            # the staging dir's parent is pkgdir (a sibling of files/),
            # never files/ itself or files/docs
            self.eq(s_common.genpath(pkgdir), seen[0])
            self.notin('files', os.path.relpath(seen[0], pkgdir).split(os.sep))

    async def test_buildbundle_stagedir_parent_defaults_to_outdir_parent(self):
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            outdir = s_common.genpath(workdir, 'built')
            _write(srcdir, 'index.md', '# Index\n')

            seen = []
            realmkdtemp = tempfile.mkdtemp

            def spy(*args, **kwargs):
                path = realmkdtemp(*args, **kwargs)
                seen.append(kwargs.get('dir'))
                return path

            with mock.patch('tempfile.mkdtemp', spy):
                await s_mddocs.buildBundle(srcdir, outdir)

            self.len(1, seen)
            self.eq(s_common.genpath(workdir), seen[0])

    def test_hashfile_returns_sha256_hex(self):
        with self.getTestDir() as dirn:
            path = _write(dirn, 'a.md', 'hello world')
            self.eq(hashlib.sha256(b'hello world').hexdigest(), s_mddocs.hashFile(path))

    def test_loadmanifest_roundtrips_and_rejects_malformed_line(self):
        with self.getTestDir() as dirn:
            path = _write(dirn, 'docs.sha256', '\n'.join((
                '# a comment line, skipped',
                '',
                f'{"a" * 64}  page1.md',
                f'{"b" * 64} *page2.md',
            )) + '\n')
            self.eq([('page1.md', 'a' * 64), ('page2.md', 'b' * 64)], s_mddocs.loadManifest(path))

            badpath = _write(dirn, 'bad.sha256', 'not-a-valid-manifest-line\n')
            with self.raises(ValueError) as cm:
                s_mddocs.loadManifest(badpath)
            self.isin('malformed manifest line', str(cm.exception))

    def test_walkmdfiles_skips_stage_ignore_dirs_and_non_md(self):
        with self.getTestDir() as dirn:
            _write(dirn, 'index.md', '# Index\n')
            _write(dirn, 'sub/page.md', '# Page\n')
            _write(dirn, 'sub/image.svg', '<svg></svg>')
            _write(dirn, 'mocks/cassette.yaml', 'interactions: []\n')
            _write(dirn, '_build/stale.md', '# Stale\n')

            got = set(s_mddocs._walkMdFiles(dirn))
            self.eq({'index.md', os.path.join('sub', 'page.md')}, got)

    def test_getmanifestpath_derives_from_srcdir(self):
        # every real bundle shape (rapid/synmod: docs.sha256 next to docs/
        # and files/docs/; synapse: docs.sha256 in synsrc/docs, sibling of
        # the docs/synapse srcdir) -- see the doc.manifest fixtures in
        # vtxtools.pkginfo -- has its manifest exactly at
        # dirname(srcdir)/docs.sha256.
        with self.getTestDir() as workdir:
            rapidsrc = s_common.gendir(workdir, 'rapid', 'docs')
            self.eq(s_common.genpath(workdir, 'rapid', 'docs.sha256'),
                    s_mddocs.getManifestPath(rapidsrc))

            synmodsrc = s_common.gendir(workdir, 'synmod', 'assets', 'docs')
            self.eq(s_common.genpath(workdir, 'synmod', 'assets', 'docs.sha256'),
                    s_mddocs.getManifestPath(synmodsrc))

            synsrc = s_common.gendir(workdir, 'synsrc', 'docs', 'synapse')
            self.eq(s_common.genpath(workdir, 'synsrc', 'docs', 'docs.sha256'),
                    s_mddocs.getManifestPath(synsrc))

            # a trailing slash on srcdir must not shift the result up a level
            self.eq(s_common.genpath(workdir, 'rapid', 'docs.sha256'),
                    s_mddocs.getManifestPath(rapidsrc + os.sep))

    def test_reusefiles_returns_empty_without_manifest_or_dirs(self):
        with self.getTestDir() as workdir:
            srcdir = s_common.gendir(workdir, 'docs')
            builtdir = s_common.gendir(workdir, 'built')
            manifest = s_common.genpath(workdir, 'docs.sha256')

            # no manifest at all
            self.eq(set(), s_mddocs.reuseFiles(srcdir, builtdir, None))
            # a manifest path that doesn't exist yet (bundle never built before)
            self.eq(set(), s_mddocs.reuseFiles(srcdir, builtdir, manifest))

            _writemanifest(manifest, [])
            # srcdir/builtdir must each exist too
            self.eq(set(), s_mddocs.reuseFiles(s_common.genpath(workdir, 'nosrc'), builtdir, manifest))
            self.eq(set(), s_mddocs.reuseFiles(srcdir, s_common.genpath(workdir, 'nobuilt'), manifest))

    def test_reusefiles_excludes_various_disqualifying_cases(self):
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            builtdir = s_common.genpath(workdir, 'built')
            manifest = s_common.genpath(workdir, 'docs.sha256')

            oksrc = _write(srcdir, 'ok.md', '# OK\n')
            okbuilt = _write(builtdir, 'ok.md', '# OK (built)\n')

            # no built counterpart at all -- os.path.isfile(builtpath) fails
            nobuiltsrc = _write(srcdir, 'nobuilt.md', '# No Built Copy\n')

            # both files exist, but the manifest names only the SOURCE side
            nodstsrc = _write(srcdir, 'nodstentrysrc.md', '# No Dst Entry\n')
            _write(builtdir, 'nodstentrysrc.md', '# No Dst Entry (built)\n')

            # both files exist, but the manifest names only the DEST side
            _write(srcdir, 'nosrcentrysrc.md', '# No Src Entry\n')
            nosrcbuilt = _write(builtdir, 'nosrcentrysrc.md', '# No Src Entry (built)\n')

            # an mdtoc-bearing page is never reused, even with matching hashes
            tocsrc = _write(srcdir, 'toc.md', '\n'.join((
                '# TOC Page', '', '```mdtoc', 'ok.md', '```', '',
            )))
            tocbuilt = _write(builtdir, 'toc.md', '# TOC Page\n\n- [OK](ok.md)\n')

            entries = [
                (os.path.relpath(oksrc, workdir), s_mddocs.hashFile(oksrc)),
                (os.path.relpath(okbuilt, workdir), s_mddocs.hashFile(okbuilt)),
                (os.path.relpath(nobuiltsrc, workdir), s_mddocs.hashFile(nobuiltsrc)),
                (os.path.relpath(nodstsrc, workdir), s_mddocs.hashFile(nodstsrc)),
                (os.path.relpath(nosrcbuilt, workdir), s_mddocs.hashFile(nosrcbuilt)),
                (os.path.relpath(tocsrc, workdir), s_mddocs.hashFile(tocsrc)),
                (os.path.relpath(tocbuilt, workdir), s_mddocs.hashFile(tocbuilt)),
            ]
            _writemanifest(manifest, entries)

            self.eq({'ok.md'}, s_mddocs.reuseFiles(srcdir, builtdir, manifest))

    def test_reusefiles_excludes_hash_mismatch_on_either_side(self):
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            builtdir = s_common.genpath(workdir, 'built')
            manifest = s_common.genpath(workdir, 'docs.sha256')

            badsrcsrc = _write(srcdir, 'badsrc.md', '# Bad Src\n')
            badsrcbuilt = _write(builtdir, 'badsrc.md', '# Bad Src (built)\n')

            baddstsrc = _write(srcdir, 'baddst.md', '# Bad Dst\n')
            baddstbuilt = _write(builtdir, 'baddst.md', '# Bad Dst (built)\n')

            entries = [
                (os.path.relpath(badsrcsrc, workdir), s_mddocs.hashFile(badsrcsrc)),
                (os.path.relpath(badsrcbuilt, workdir), s_mddocs.hashFile(badsrcbuilt)),
                (os.path.relpath(baddstsrc, workdir), s_mddocs.hashFile(baddstsrc)),
                (os.path.relpath(baddstbuilt, workdir), s_mddocs.hashFile(baddstbuilt)),
            ]
            _writemanifest(manifest, entries)

            # the source drifted from what the manifest recorded after the fact
            with open(badsrcsrc, 'w') as fd:
                fd.write('# Bad Src (edited after the manifest was written)\n')
            # the built output was hand-edited after the fact
            with open(baddstbuilt, 'w') as fd:
                fd.write('# Bad Dst (edited after the manifest was written)\n')

            self.eq(set(), s_mddocs.reuseFiles(srcdir, builtdir, manifest))

    def test_reusefiles_key_inversion_across_bundle_layouts(self):
        # a bundle's manifest relpaths are recorded relative to the
        # manifest's OWN directory (see gen_docs_manifest.buildBundleEntries),
        # which sits in a different place relative to docsdir/outdir for
        # each bundle kind -- a rapid/synmod's docs.sha256 sits next to both
        # docs/ and files/docs, while synapse's sits one level below
        # synapse/assets/docs (its manifest lives in synsrc/docs, its built
        # bundle in synsrc/synapse/assets/docs). reuseFiles must key off the
        # manifest's basedir correctly in either shape.
        with self.getTestDir() as workdir:
            # rapid/synmod shape: docs.sha256 next to docs/ and files/docs/
            rapidmanifest = s_common.genpath(workdir, 'rapid', 'docs.sha256')
            rapidsrc = s_common.genpath(workdir, 'rapid', 'docs')
            rapidbuilt = s_common.genpath(workdir, 'rapid', 'files', 'docs')
            rapidsrcfp = _write(rapidsrc, 'page1.md', '# Page One\n')
            rapidbuiltfp = _write(rapidbuilt, 'page1.md', '# Page One (built)\n')
            _writemanifest(rapidmanifest, [
                (os.path.relpath(rapidsrcfp, os.path.dirname(rapidmanifest)), s_mddocs.hashFile(rapidsrcfp)),
                (os.path.relpath(rapidbuiltfp, os.path.dirname(rapidmanifest)), s_mddocs.hashFile(rapidbuiltfp)),
            ])
            self.eq({'page1.md'}, s_mddocs.reuseFiles(rapidsrc, rapidbuilt, rapidmanifest))

            # synapse shape: the manifest's own dir (synsrc/docs) is a SIBLING
            # of the built bundle's parent (synsrc/synapse), so built entries
            # climb out with a leading "../"
            synmanifestdir = s_common.gendir(workdir, 'synsrc', 'docs')
            synmanifest = s_common.genpath(synmanifestdir, 'docs.sha256')
            synsrc = s_common.genpath(synmanifestdir, 'synapse')
            synbuilt = s_common.genpath(workdir, 'synsrc', 'synapse', 'assets', 'docs')
            synsrcfp = _write(synsrc, 'page1.md', '# Page One\n')
            synbuiltfp = _write(synbuilt, 'page1.md', '# Page One (built)\n')
            _writemanifest(synmanifest, [
                (os.path.relpath(synsrcfp, synmanifestdir), s_mddocs.hashFile(synsrcfp)),
                (os.path.relpath(synbuiltfp, synmanifestdir), s_mddocs.hashFile(synbuiltfp)),
            ])
            self.eq({'page1.md'}, s_mddocs.reuseFiles(synsrc, synbuilt, synmanifest))

    def test_stagereuse_overwrites_staged_copy_with_built_content(self):
        with self.getTestDir() as workdir:
            builtdir = s_common.genpath(workdir, 'built')
            outdir = s_common.genpath(workdir, 'stage')
            _write(builtdir, 'page1.md', '# Page One (built)\n')
            _write(outdir, 'page1.md', '# Page One (staged from source)\n')
            _write(outdir, 'page2.md', '# Page Two (untouched)\n')

            s_mddocs.stageReuse(builtdir, outdir, {'page1.md'})

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                self.eq('# Page One (built)\n', fd.read())
            with open(s_common.genpath(outdir, 'page2.md')) as fd:
                self.eq('# Page Two (untouched)\n', fd.read())

    async def test_runmdstorm_skip_leaves_file_untouched(self):
        with self.getTestDir() as outdir:
            _write(outdir, 'page1.md', '# Page One\n')
            _write(outdir, 'page2.md', '# Page Two\n')

            origcls = s_mddocs.s_mdstorm.MdStorm
            s_mddocs.s_mdstorm.MdStorm = _FakeMdStorm
            try:
                issues = await s_mddocs.runMdstorm(outdir, skip={'page1.md'})
            finally:
                s_mddocs.s_mdstorm.MdStorm = origcls

            # page1.md was skipped entirely -- untouched, no warnings captured
            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                self.eq('# Page One\n', fd.read())
            self.notin('page1.md', issues)

            # page2.md was not skipped -- ran through the fake, which always
            # emits an unhandled warning and a fixed page of its own
            with open(s_common.genpath(outdir, 'page2.md')) as fd:
                self.eq('# Page One\n', fd.read())
            self.isin('page2.md', issues)

    async def test_builddocs_manifest_reuse_skips_unchanged_page(self):
        # page1.md's SOURCE carries a live ```mdstorm fence -- if reuseFiles/
        # stageReuse work, its staticdir content (which never went through
        # that fence at all) survives untouched; if it were rebuilt instead,
        # a real Cortex would execute the fence and a "storm>" echo line
        # would appear (see test_builddocs_mdstorm_fence_executes). The
        # manifest lives wherever getManifestPath derives it from srcdir --
        # no path is passed to buildDocs.
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            staticdir = s_common.genpath(workdir, 'built')
            outdir = s_common.genpath(workdir, 'stage')
            manifest = s_mddocs.getManifestPath(srcdir)

            _write(srcdir, 'index.md', '# Index\n\n- [Page One](page1.md)\n')
            page1src = _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '```mdstorm-setup',
                '```',
                '',
                '```mdstorm',
                '$lib.print(freshlyrendered)',
                '```',
                '',
            )))
            page1built = _write(staticdir, 'page1.md', '# Page One\n\nAlready built, never touched again.\n')

            basedir = os.path.dirname(manifest)
            entries = [
                (os.path.relpath(page1src, basedir), s_mddocs.hashFile(page1src)),
                (os.path.relpath(page1built, basedir), s_mddocs.hashFile(page1built)),
            ]
            _writemanifest(manifest, entries)

            await s_mddocs.buildDocs(srcdir, outdir, staticdir=staticdir)

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                text = fd.read()
            self.eq('# Page One\n\nAlready built, never touched again.\n', text)
            self.notin('storm>', text)

    async def test_builddocs_force_rebuilds_matching_page(self):
        # identical setup to the reuse test above, but force=True skips the
        # docs.sha256 check entirely -- the live ```mdstorm fence really
        # executes even though source and built output both still match.
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            staticdir = s_common.genpath(workdir, 'built')
            outdir = s_common.genpath(workdir, 'stage')
            manifest = s_mddocs.getManifestPath(srcdir)

            _write(srcdir, 'index.md', '# Index\n\n- [Page One](page1.md)\n')
            page1src = _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '```mdstorm-setup',
                '```',
                '',
                '```mdstorm',
                '$lib.print(freshlyrendered)',
                '```',
                '',
            )))
            page1built = _write(staticdir, 'page1.md', '# Page One\n\nAlready built, never touched again.\n')

            basedir = os.path.dirname(manifest)
            entries = [
                (os.path.relpath(page1src, basedir), s_mddocs.hashFile(page1src)),
                (os.path.relpath(page1built, basedir), s_mddocs.hashFile(page1built)),
            ]
            _writemanifest(manifest, entries)

            await s_mddocs.buildDocs(srcdir, outdir, staticdir=staticdir, force=True)

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                text = fd.read()
            self.isin('storm> $lib.print(freshlyrendered)', text)

    async def test_builddocs_manifest_reuse_rebuilds_when_source_changed(self):
        # a deliberately wrong recorded source hash simulates a page edited
        # after its manifest entry was last regenerated -- the mismatch
        # forces a real rebuild, which for a ```mdstorm fence means a real
        # Cortex actually executes it.
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            staticdir = s_common.genpath(workdir, 'built')
            outdir = s_common.genpath(workdir, 'stage')
            manifest = s_mddocs.getManifestPath(srcdir)

            _write(srcdir, 'index.md', '# Index\n\n- [Page One](page1.md)\n')
            page1src = _write(srcdir, 'page1.md', '\n'.join((
                '# Page One',
                '',
                '```mdstorm-setup',
                '```',
                '',
                '```mdstorm',
                '$lib.print(freshlyrendered)',
                '```',
                '',
            )))
            page1built = _write(staticdir, 'page1.md', '# Page One\n\nAlready built, never touched again.\n')

            basedir = os.path.dirname(manifest)
            entries = [
                (os.path.relpath(page1src, basedir), '0' * 64),  # deliberately wrong
                (os.path.relpath(page1built, basedir), s_mddocs.hashFile(page1built)),
            ]
            _writemanifest(manifest, entries)

            await s_mddocs.buildDocs(srcdir, outdir, staticdir=staticdir)

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                text = fd.read()
            self.isin('storm> $lib.print(freshlyrendered)', text)

    async def test_builddocs_mdtoc_page_never_reused_reflects_reused_sibling_title(self):
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            staticdir = s_common.genpath(workdir, 'built')
            outdir = s_common.genpath(workdir, 'stage')
            manifest = s_mddocs.getManifestPath(srcdir)

            indextext = '\n'.join((
                '# Index',
                '',
                '```mdtoc',
                'page1.md',
                '```',
                '',
            ))
            indexsrc = _write(srcdir, 'index.md', indextext)
            page1src = _write(srcdir, 'page1.md', '# Page One\n')
            # matching manifest entries for BOTH pages, to prove index.md is
            # excluded despite an (artificially) matching hash pair of its
            # own -- only its own ```mdtoc fence disqualifies it.
            indexbuilt = _write(staticdir, 'index.md', indextext)
            page1built = _write(staticdir, 'page1.md', '# Page One (Already Built Title)\n')

            basedir = os.path.dirname(manifest)
            entries = [
                (os.path.relpath(indexsrc, basedir), s_mddocs.hashFile(indexsrc)),
                (os.path.relpath(indexbuilt, basedir), s_mddocs.hashFile(indexbuilt)),
                (os.path.relpath(page1src, basedir), s_mddocs.hashFile(page1src)),
                (os.path.relpath(page1built, basedir), s_mddocs.hashFile(page1built)),
            ]
            _writemanifest(manifest, entries)

            metadata = await s_mddocs.buildDocs(srcdir, outdir, staticdir=staticdir)

            # page1.md was reused: its H1 is the BUILT title, not the source's
            self.eq('Page One (Already Built Title)', metadata['toc'][0]['title'])

            with open(s_common.genpath(outdir, 'index.md')) as fd:
                text = fd.read()
            # index.md's own ```mdtoc fence was still resolved (never reused,
            # despite a manifest entry matching it too), naming page1's
            # reused title in the rendered bullet list.
            self.notin('```mdtoc', text)
            self.isin('[Page One (Already Built Title)](page1.md)', text)

    async def test_builddocs_reused_page_broken_link_still_reported(self):
        # a reused page's committed built content is still scanned by
        # validate() the same as a rebuilt one -- reuse skips mdstorm, not
        # validation.
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            staticdir = s_common.genpath(workdir, 'built')
            outdir = s_common.genpath(workdir, 'stage')
            manifest = s_mddocs.getManifestPath(srcdir)

            _write(srcdir, 'index.md', '# Index\n\n- [Page One](page1.md)\n')
            page1src = _write(srcdir, 'page1.md', '# Page One\n')
            # the reused BUILT content links to a page that no longer exists
            # anywhere in this build -- a stale link a prior build left behind.
            page1built = _write(staticdir, 'page1.md', '# Page One\n\n[gone](goneaway.md)\n')

            basedir = os.path.dirname(manifest)
            entries = [
                (os.path.relpath(page1src, basedir), s_mddocs.hashFile(page1src)),
                (os.path.relpath(page1built, basedir), s_mddocs.hashFile(page1built)),
            ]
            _writemanifest(manifest, entries)

            with self.raises(s_exc.SynErr) as cm:
                await s_mddocs.buildDocs(srcdir, outdir, staticdir=staticdir)
            issues = cm.exception.get('issues')
            self.true(any('goneaway.md' in i for i in issues))

    async def test_builddocs_manifest_without_staticdir_is_inert(self):
        # a bundle's own docs.sha256, sitting right where getManifestPath
        # derives it, has nothing to reuse a page's built output FROM
        # without staticdir -- a no-op, same as force=True.
        with self.getTestDir() as parentdir:
            srcdir = s_common.genpath(parentdir, 'docs')
            outdir = s_common.genpath(parentdir, 'stage')
            manifest = s_mddocs.getManifestPath(srcdir)

            _write(srcdir, 'index.md', '\n'.join((
                '# Index', '', '```mdtoc', 'page1.md', '```', '',
            )))
            page1src = _write(srcdir, 'page1.md', '# Page One\n')
            basedir = os.path.dirname(manifest)
            _writemanifest(manifest, [(os.path.relpath(page1src, basedir), s_mddocs.hashFile(page1src))])

            metadata = await s_mddocs.buildDocs(srcdir, outdir)
            self.eq('Page One', metadata['toc'][0]['title'])

    async def test_buildbundle_manifest_reuse_thread_through(self):
        # buildBundle must thread force= through to buildDocs the same way
        # it already threads ci=/warnfile= -- reuse works end-to-end through
        # the stage-then-merge pipeline, not just via a direct buildDocs
        # call, and with staticdir defaulting to outdir (the common case --
        # no explicit staticdir override).
        with self.getTestDir() as workdir:
            srcdir = s_common.genpath(workdir, 'docs')
            outdir = s_common.genpath(workdir, 'built')
            manifest = s_mddocs.getManifestPath(srcdir)

            _write(srcdir, 'index.md', '# Index\n\n- [Page One](page1.md)\n')
            page1src = _write(srcdir, 'page1.md', '# Page One\n')
            _write(outdir, 'index.md', '# Index\n\n- [Page One](page1.md)\n')
            page1built = _write(outdir, 'page1.md', '# Page One\n\nAlready built, never touched again.\n')

            basedir = os.path.dirname(manifest)
            entries = [
                (os.path.relpath(page1src, basedir), s_mddocs.hashFile(page1src)),
                (os.path.relpath(page1built, basedir), s_mddocs.hashFile(page1built)),
            ]
            _writemanifest(manifest, entries)

            await s_mddocs.buildBundle(srcdir, outdir)

            with open(s_common.genpath(outdir, 'page1.md')) as fd:
                self.eq('# Page One\n\nAlready built, never touched again.\n', fd.read())
