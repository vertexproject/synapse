import os
import shutil
import logging
import tempfile

import regex
import markdown_it

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.mdstorm as s_mdstorm
import synapse.lib.autodoc as s_autodoc

logger = logging.getLogger(__name__)

# markdown_it logs an "entering <rule>" DEBUG message per block/inline rule
# tried on every line of every doc -- deafening under DEBUG-level logging and
# never useful for diagnosing a doc build.
logging.getLogger('markdown_it').setLevel(logging.INFO)

# vcrpy logs every cassette request/response body ( INFO ) and playback detail
# ( DEBUG ) for each ``mdstorm`` doc that mocks HTTP via a cassette -- matches
# the same suppression synapse.tests.utils applies for test runs.
logging.getLogger('vcr').setLevel(logging.ERROR)

TOC_MAX_DEPTH = 3

# Ported from the old Sphinx-era docs/conf.py's convert_rstorm -- warning
# messages emitted while processing a doc's mdstorm fences that are safe to
# ignore, vs. ones that must always fail the build even though they are
# merely logged at WARNING (not raised) by the underlying code.
WARNINGS_IGNORE = [
    r'Detected \d+ deprecated properties unlocked and not in use',
    r'Sysctl values different than expected',
    r'The form edge:refs is deprecated or using a deprecated type',
    r'The form edge:has is deprecated or using a deprecated type',
    r'The property media:news:author is deprecated or using a deprecated type',
    r'The type [a-z:]+ field [a-z:]+ uses a deprecated type [a-z:]+.',
    r'Caught SIGTERM, shutting down\.',
    # Benign: a default (aha-less) temp Cortex's built-in mirror-service
    # lookups (axon/jsonstor) always miss aha during a ```mdstorm-setup
    # fence's teardown; harmless in every doc build, not just tests.
    r"No aha servers registered to lookup \w+",
    # Benign: a ```mdstorm --fail fence deliberately runs a query expected
    # to raise (mdstorm.py's own check -- did it actually fail? -- already
    # covers "unexpectedly succeeded"; this ignore only covers the
    # expected-and-actually-failed case). The Cortex logs the failure via
    # Python logging regardless of whether the caller (mdstorm) expected
    # it. A failing fence produces exactly this one record, logged
    # synchronously by view.runStorm() and therefore inside the per-file
    # log-capture window (see runMdstorm).
    r'Error during storm execution for \{.*\}',
    # Benign: a ```mdstorm-setup --load-svc fence's Telepath clientv2 makes
    # its first connect attempt to the just-registered service's dmon
    # before that dmon's listener has fully finished coming up (a normal
    # startup race under load) -- clientv2 logs the failed attempt at
    # ERROR and retries automatically, so the service.add/service.wait
    # storm calls succeed regardless. Ported from packages whose docs
    # provision more than one --load-svc across their doc set (e.g.
    # synmods.backup's adminguide.md and userguide.md each provisioning
    # their own service instance).
    r"telepath clientv2 \(tcp://.*\) encountered an error: \[Errno 111\] Connect call failed",
    # Benign: a doc-only Cortex fixture that boots its own ephemeral AHA
    # network (rather than the simple no-AHA getCell() most docs use) logs
    # this on teardown if the AHA cell itself finishes finishing before the
    # last "set service offline" call it issues for itself -- an ordering
    # artifact of tearing down a self-hosted AHA network, not a real error.
    r'AhaCell is fini\. Unable to set \S+ as down\.',
    # Benign: same self-hosted-AHA teardown race as above, seen instead as a
    # failed aha:// service lookup (NoSuchName) rather than a NotReady from
    # a mirror-peer connect attempt.
    r'telepath clientv2 \(aha://.*\) encountered an error: NoSuchName: mesg=.aha lookup failed',
    # Benign: a mirror/service peer's edits-listen loop logs this when its
    # remote end (the doc's own ephemeral Cortex/service, already torn
    # down) disconnects first -- an expected teardown-ordering artifact,
    # not a real link failure.
    r"error in edits listen loop LinkShutDown: mesg='Remote peer disconnected'",
    # Benign: synapse.lib.autodoc's model-processing functions
    # (processTypesMd/processFormsPropsMd) log this for a synthetic/runt
    # type or edge whose model info includes a key this doc generator
    # doesn't specifically render (e.g. a runt type's "liftfunc", or a
    # deprecated light edge's own model metadata) -- faithful to the real
    # data model, not a build defect. Only ever surfaced once a
    # ```mdautodoc --model-types/--model-forms fence started resolving
    # inside mdstorm's own log-capture window (SYN-11304); the same
    # warning existed before, just outside runMdstorm's per-file capture.
    r'(Base t|T)ype [\w:]+ has unhandled info: .*',
    r'.* Light edge \w+ has unhandled info: .*',
]

WARNINGS_ERROR = [
    r'.* is deprecated or using a deprecated type',
]

_md_parser = markdown_it.MarkdownIt('commonmark')

_re_heading = regex.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
_re_explicit_anchor = regex.compile(r'<a\s+id="([^"]+)">\s*</a>')
_re_md_link = regex.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
# A cross-bundle link into the Vertex Hub docs viewer, e.g.
# /docs/synapse-enterprise-optic/latest/user_interface/userguide.md -- the
# hub route is r'/docs/([\w.-]+)/([\w.-]+)/(.+)', so this mirrors that shape.
# A bare /docs/<name>/<version>(/) reference (no path) is also valid -- only
# the project name matters, e.g. linking to a whole Power-Up's docs bundle.
_re_abs_doclink = regex.compile(r'^/docs/[\w.-]+/[\w.-]+(/.+\.md)?/?$')
_re_inline_code = regex.compile(r'`[^`]*`')

class _WarningCollector(logging.Handler):
    '''A logging.Handler that only collects WARNING+ records, for classifying against WARNINGS_IGNORE/ERROR.'''

    def __init__(self):
        logging.Handler.__init__(self, level=logging.WARNING)
        self.records = []

    def emit(self, record):
        # record.getMessage() only, not self.format(record) -- a WARNING
        # logged with exc_info (e.g. a background Telepath reconnect
        # failure) would otherwise pull a multi-line traceback into the
        # message classified against WARNINGS_IGNORE/ERROR below.
        self.records.append(record.getMessage())

def _classifyWarnings(messages):
    '''
    Classify captured log messages against WARNINGS_IGNORE/WARNINGS_ERROR,
    the same policy the old Sphinx-era docs/conf.py's convert_rstorm applied
    to rstorm's subprocess output: a message matching WARNINGS_IGNORE is
    dropped; a message matching WARNINGS_ERROR is a build-breaking issue,
    reported as-is; anything else is *also* build-breaking (there is no
    "warn and continue" outcome once a message is not on the ignore list),
    but flagged as "unhandled" so it stands out as a pattern nobody has
    triaged yet, rather than a known, expected failure mode.

    Args:
        messages (list): Captured log message strings.

    Returns:
        list: The subset of messages that are not ignorable, as issue strings.
    '''
    issues = []
    for mesg in messages:
        if any(regex.search(pattern, mesg) for pattern in WARNINGS_IGNORE):
            continue
        if any(regex.search(pattern, mesg) for pattern in WARNINGS_ERROR):
            issues.append(mesg)
        else:
            issues.append(f'unhandled warning: {mesg}')
    return issues

def stageTree(srcdir, outdir):
    '''
    Copy a doc bundle's sources into outdir 1:1: every non-Markdown file is
    copied verbatim (runMdstorm() below then processes the .md files in
    place), except for any pre-existing build output and any "mocks"
    directory. A mocks/ dir holds VCR cassettes that are build inputs only
    (see MdStorm.srcbasedir / _resolveMockHttp) -- they are resolved
    straight from srcdir, never staged, so a package's built docs never
    carry recorded HTTP traffic (and any auth headers within it) as
    published files.

    Args:
        srcdir (str): The doc source directory.
        outdir (str): The (fresh) staging/output directory.
    '''
    def _ignore(dirn, names):
        ignored = {'_build', '.git', 'mocks'}
        return ignored & set(names)

    shutil.copytree(srcdir, outdir, ignore=_ignore, dirs_exist_ok=True)

def _iterMdFiles(outdir):
    for dirn, _dirs, fns in os.walk(outdir):
        for fn in fns:
            if fn.endswith('.md'):
                yield s_common.genpath(dirn, fn)

def _collapseBlankLines(lines):
    '''
    Strip fully-leading blank lines and collapse any run of 2+ consecutive
    blank lines down to one. A hidden ```mdstorm-setup/```mdstorm --hide
    fence produces zero output lines of its own, but the blank lines
    separating/following them in the source -- never part of any fence's
    own span -- are ordinary content and get printed as-is. Since nearly
    every page opens with exactly this shape (a ```mdstorm-setup fence,
    then one or more --hide auth-setup fences), the built output is
    otherwise left with several blank lines before the page's real
    content -- invisible in a rendered HTML page, but a real eyesore in
    the raw Markdown this build now commits directly.

    Args:
        lines (list): Lines as produced by MdStorm.run() (each ending in \\n).

    Returns:
        list: The same lines with leading/collapsed blank runs removed.
    '''
    out = []
    prevblank = False
    for line in lines:
        if line.strip() == '':
            if not out or prevblank:
                continue
            prevblank = True
        else:
            prevblank = False
        out.append(line)
    return out

async def runMdstorm(outdir, srcdir=None):
    '''
    Run mdstorm over every staged .md file in place, collecting any
    non-ignorable warnings emitted along the way (see _classifyWarnings).

    Args:
        outdir (str): The staged output directory.
        srcdir (str): The original doc source directory this bundle was
            staged from, threaded through to MdStorm so a ```mdautodoc
            --stormpkg fence can resolve a pkgdef path that lives outside
            the docroot (see MdStorm.srcbasedir). May be None (a file's
            mdautodoc fences then resolve relative to its own staged
            location).

    Returns:
        dict: {relpath: [warning-message, ...]} for any file with issues.
    '''
    issues = {}

    for path in sorted(_iterMdFiles(outdir)):
        collector = _WarningCollector()
        logging.getLogger().addHandler(collector)
        try:
            async with await s_mdstorm.MdStorm.anit(path, srcdir=srcdir, outdir=outdir) as mdstorm:
                lines = await mdstorm.run()
        finally:
            logging.getLogger().removeHandler(collector)

        with open(path, 'w') as fd:
            fd.writelines(_collapseBlankLines(lines))

        relpath = os.path.relpath(path, outdir)
        badmsgs = _classifyWarnings(collector.records)
        if badmsgs:
            issues[relpath] = badmsgs

    return issues

def _fenceDirectives(text, name):
    '''
    Find every top-level fenced code block in text whose info string is
    exactly (or starts with, for flags) the given directive name.

    Args:
        text (str): The full file text.
        name (str): The directive name to match (e.g. "mdtoc").

    Returns:
        list: (start, end, fenceargs, body) tuples, start/end being the
            [start, end) line-index range (open fence through close fence).
    '''
    lines = text.splitlines(keepends=True)
    fences = []

    for token in _md_parser.parse(text):
        if token.type != 'fence' or token.level != 0:
            continue

        info = token.info.strip()
        directive, _sep, fenceargs = info.partition(' ')
        if directive != name:
            continue

        start, end = token.map
        body = ''.join(lines[start + 1:end - 1]).strip('\n')
        fences.append((start, end, fenceargs.strip(), body))

    return fences

def _mdtocTargets(text):
    '''Return the list of relative paths named by a file's (single) mdtoc fence body, one per non-blank line.'''
    fences = _fenceDirectives(text, 'mdtoc')
    if not fences:
        return []
    _start, _end, _fenceargs, body = fences[0]
    return [line.strip() for line in body.splitlines() if line.strip()]

def _fileHeadings(text):
    '''Extract this file's headings (level, title, slug), slugged in encounter order for GFM-style dedup.'''
    seen = {}
    headings = []
    for line in text.splitlines():
        match = _re_heading.match(line)
        if match is None:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        slug = s_autodoc.mdSlugify(title, seen=seen)
        headings.append((level, title, slug))
    return headings

def _fileAnchors(text):
    '''All anchor ids resolvable within one file: explicit <a id="..."> tags plus every heading's GFM slug.'''
    anchors = set(_re_explicit_anchor.findall(text))
    anchors.update(slug for _lvl, _title, slug in _fileHeadings(text))
    return anchors

def _fileTitle(text):
    '''
    A file's title is its first H1 ("# ...") heading, wherever it falls
    among the file's headings. None means the file has no H1 heading at
    all, so a caller building a nav entry from it falls back to its
    relative path, and validate() below flags the file as an issue.
    '''
    for level, title, _slug in _fileHeadings(text):
        if level == 1:
            return title
    return None

def _headingChildren(headings, minlvl, maxdepth):
    '''
    Build a nested outline from a flat (level, title, slug) heading list,
    starting at minlvl (the level directly under the page's own title) and
    descending at most maxdepth levels -- the Markdown analog of
    docs/conf.py's _get_toc_subsections, which walked nested docutils
    section nodes instead of a flat heading list.

    Args:
        headings (list): (level, title, slug) tuples, in document order.
        minlvl (int): The heading level to treat as this outline's top level.
        maxdepth (int): How many nested levels below minlvl to include.

    Returns:
        list: {'title', 'anchor', 'children'} dicts (children omitted at the leaves).
    '''
    relevant = [h for h in headings if h[0] >= minlvl]
    return _headingChildrenAt(relevant, 0, minlvl, maxdepth)

def _headingChildrenAt(headings, idx, lvl, depthleft):
    children = []
    i = idx
    while i < len(headings):
        hlvl, title, slug = headings[i]
        if hlvl < lvl:
            break
        if hlvl > lvl:
            i += 1
            continue
        entry = {'title': title, 'anchor': slug}
        j = i + 1
        if depthleft > 1:
            sub, j = _headingChildrenAtCount(headings, j, lvl + 1, depthleft - 1)
            if sub:
                entry['children'] = sub
        else:
            while j < len(headings) and headings[j][0] > lvl:
                j += 1
        children.append(entry)
        i = j
    return children

def _headingChildrenAtCount(headings, idx, lvl, depthleft):
    children = _headingChildrenAt(headings, idx, lvl, depthleft)
    i = idx
    while i < len(headings) and headings[i][0] >= lvl:
        i += 1
    return children, i

def _stampAnchorHrefs(entry, href):
    for child in entry.get('children', ()):
        child['href'] = f"{href}#{child.pop('anchor')}"
        _stampAnchorHrefs(child, href)

def headingsToc(text, href, depth=1):
    '''
    Build a page's own toc children from its in-page headings -- the same
    heading-outline branch TocBuilder._childrenFor() falls back to for a
    page with no ```mdtoc fence of its own. Extracted so any caller that
    already has a page's title entry (e.g. pkg.gen building a package's
    docsmeta toc from its `docs:` list) can fill in that entry's
    `children` the same way the site build does, with the same slugs
    (s_autodoc.mdSlugify) -- so a `page.md#anchor` href always resolves
    the same way whether it came from a docs site build or a published
    package.

    Args:
        text (str): The page's full Markdown text.
        href (str): This page's own toc href (its path, e.g. "userguide.md").
        depth (int): This page's own depth in the surrounding toc (1 for a
            top-level entry); the returned children go at most
            TOC_MAX_DEPTH - depth levels below the page's own title.

    Returns:
        list: {'title', 'href', 'children'?} dicts.
    '''
    headings = _fileHeadings(text)
    if not headings:
        return []
    toplvl = headings[0][0] + 1
    children = _headingChildren(headings, toplvl, TOC_MAX_DEPTH - depth)
    for child in children:
        child['href'] = f"{href}#{child.pop('anchor')}"
        _stampAnchorHrefs(child, href)
    return children

class TocBuilder:
    '''
    Resolves ```mdtoc fences into rendered link lists and builds the
    metadata.json nav tree, mirroring the shape docs/conf.py's
    _extract_toc_entries/_get_toc_children produced from a Sphinx doctree.
    '''

    def __init__(self, outdir, staticdir=None):
        self.outdir = outdir
        # staticdir is the real files/docs directory (as opposed to
        # outdir, a build's staging copy) -- a fallback read location for
        # a page that lives only there, never staged (e.g. changelog.md,
        # git mv'd out of docs/ per the docs/-vs-files/docs split). None
        # for any caller that doesn't merge into pre-existing static
        # content (e.g. a fresh/isolated build).
        self.staticdir = staticdir
        self._cache = {}
        self.visited = set()
        self.missing = []

    def _read(self, relpath):
        if relpath not in self._cache:
            path = s_common.genpath(self.outdir, relpath)
            if not os.path.isfile(path) and self.staticdir is not None:
                path = s_common.genpath(self.staticdir, relpath)
            if not os.path.isfile(path):
                self._cache[relpath] = None
            else:
                with open(path, 'r') as fd:
                    self._cache[relpath] = fd.read()
        return self._cache[relpath]

    def resolveFences(self):
        '''Replace every ```mdtoc fence (in every staged file) with a rendered Markdown bullet list of links.'''
        for path in list(_iterMdFiles(self.outdir)):
            with open(path, 'r') as fd:
                text = fd.read()

            fences = _fenceDirectives(text, 'mdtoc')
            if not fences:
                continue

            lines = text.splitlines(keepends=True)
            reldir = os.path.dirname(os.path.relpath(path, self.outdir))

            out = []
            idx = 0
            fenceiter = iter(fences)
            nextfence = next(fenceiter, None)
            while idx < len(lines):
                if nextfence is not None and idx == nextfence[0]:
                    start, end, _fenceargs, body = nextfence
                    targets = [line.strip() for line in body.splitlines() if line.strip()]
                    for target in targets:
                        relpath = os.path.normpath(os.path.join(reldir, target)) if reldir else target
                        title = self._titleFor(relpath) or target
                        out.append(f'- [{title}]({target})\n')
                    out.append('\n')
                    idx = end
                    nextfence = next(fenceiter, None)
                    continue
                out.append(lines[idx])
                idx += 1

            with open(path, 'w') as fd:
                fd.writelines(out)

            # invalidate the cache entry for this file, since its content just changed
            relpath = os.path.relpath(path, self.outdir)
            self._cache.pop(relpath, None)

    def _titleFor(self, relpath):
        text = self._read(relpath)
        if text is None:
            return None
        return _fileTitle(text)

    def buildToc(self, indexpath='index.md'):
        '''
        Build the full nav tree from index.md's mdtoc entries, recording
        every reachable file (self.visited) and any target that does not
        exist (self.missing) along the way.

        Returns:
            list: TOC entries, TOC_MAX_DEPTH deep, in the docs/conf.py shape.
        '''
        self.visited.add(os.path.normpath(indexpath))
        text = self._read(indexpath)
        targets = _mdtocTargets(text) if text is not None else []
        return self._entriesFor(targets, os.path.dirname(indexpath), depth=1)

    def _entriesFor(self, targets, reldir, depth):
        entries = []
        for target in targets:
            relpath = os.path.normpath(os.path.join(reldir, target)) if reldir else target
            text = self._read(relpath)
            if text is None:
                self.missing.append(relpath)
                continue

            self.visited.add(relpath)
            title = _fileTitle(text) or relpath
            entry = {'title': title, 'href': relpath}

            if depth < TOC_MAX_DEPTH:
                children = self._childrenFor(relpath, text, depth)
                if children:
                    entry['children'] = children

            entries.append(entry)
        return entries

    def _childrenFor(self, relpath, text, depth):
        subtargets = _mdtocTargets(text)
        if subtargets:
            return self._entriesFor(subtargets, os.path.dirname(relpath), depth + 1)

        return headingsToc(text, relpath, depth)

def _stripCode(text):
    '''
    Strip fenced code blocks and inline code spans before link scanning.
    Storm/regex content routinely contains a "[...]" list literal or
    character class immediately followed by a "(...)" call/group -- e.g.
    ``[0-9]{2}[0-9]{0,2}`` -- which otherwise false-positives as a Markdown
    link target.

    Args:
        text (str): The full file text.

    Returns:
        str: text with fenced/inline code content blanked out (same line
            count, so this is safe to use for anything that doesn't need
            exact character offsets).
    '''
    lines = text.splitlines(keepends=True)
    infence = False
    out = []
    for line in lines:
        if line.lstrip().startswith('```'):
            infence = not infence
            out.append('\n')
            continue
        if infence:
            out.append('\n')
            continue
        out.append(_re_inline_code.sub('', line))
    return ''.join(out)

def _internalLinkTargets(text):
    '''Every local (non-http) markdown link target in text, split into (file-part, anchor-part-or-None).'''
    targets = []
    for target in _re_md_link.findall(_stripCode(text)):
        if target.startswith(('http://', 'https://', 'mailto:')):
            continue
        fpart, _sep, apart = target.partition('#')
        targets.append((fpart, apart or None))
    return targets

def validate(outdir, tocbuilder, staticdir=None):
    '''
    Validate a built doc bundle: every page must have an H1 heading (its
    title -- see _fileTitle), every ```mdtoc target must exist, every
    staged .md file must be reachable from index.md -- via the mdtoc nav
    tree *or* an ordinary in-page Markdown link from some other reachable
    page, since not every page organizes its children with mdtoc (e.g. a
    curated bullet list of links is just as real a path to a page) --
    every internal Markdown link's target file and #anchor must resolve.
    A link into another bundle (an absolute
    ``/docs/<name>/<version>/<path>.md`` Vertex Hub link -- see
    _re_abs_doclink) is only shape-checked here: the target lives in a
    different bundle's docroot (possibly a different repo entirely), which
    this single-bundle build cannot resolve. It does not count toward
    orphan-page reachability either, for the same reason.

    Args:
        outdir (str): The staged output directory.
        tocbuilder (TocBuilder): Already used to build the TOC (so
            .visited/.missing are populated).
        staticdir (str): Fallback read location for a link target that
            lives only there (see TocBuilder.staticdir). Only affects
            target-existence/anchor checks -- outdir's own .md files are
            still the only ones scanned for orphan/H1/link-source issues.

    Returns:
        list: Human-readable issue strings (empty if the bundle is clean).
    '''
    issues = []

    for relpath in tocbuilder.missing:
        issues.append(f'mdtoc target does not exist: {relpath}')

    allfiles = {os.path.relpath(p, outdir) for p in _iterMdFiles(outdir)}

    linked = set()

    for relpath in sorted(allfiles):
        path = s_common.genpath(outdir, relpath)
        with open(path, 'r') as fd:
            text = fd.read()

        if _fileTitle(text) is None:
            issues.append(f'no H1 heading in {relpath}')

        reldir = os.path.dirname(relpath)
        for fpart, apart in _internalLinkTargets(text):
            if fpart.startswith('/'):
                if not _re_abs_doclink.match(fpart):
                    issues.append(f'malformed cross-bundle doc link in {relpath}: {fpart}')
                continue

            if not fpart:
                targetrel = relpath
            else:
                targetrel = os.path.normpath(os.path.join(reldir, fpart)) if reldir else fpart
                linked.add(targetrel)

            targetpath = s_common.genpath(outdir, targetrel)
            if not os.path.isfile(targetpath) and staticdir is not None:
                targetpath = s_common.genpath(staticdir, targetrel)
            if not os.path.isfile(targetpath):
                issues.append(f'broken link in {relpath}: target file does not exist: {fpart}')
                continue

            if apart:
                with open(targetpath, 'r') as fd:
                    targettext = fd.read()
                if apart not in _fileAnchors(targettext):
                    issues.append(f'broken link in {relpath}: anchor #{apart} not found in {fpart or relpath}')

    orphans = allfiles - tocbuilder.visited - linked
    for relpath in sorted(orphans):
        issues.append(f'orphan page (not reachable from index.md): {relpath}')

    return issues

async def buildDocs(srcdir, outdir, ci=False, staticdir=None):
    '''
    Build one doc bundle from srcdir into outdir: stage sources, run mdstorm
    over every file (which resolves each page's own ```mdautodoc fences,
    e.g. confdefs, API docs, or the data model, at the point of use),
    resolve ```mdtoc fences into rendered nav + metadata.json, and validate
    the result.

    A bundle's category is intentionally not part of this build -- it is
    derived at the point a doc manifest is delivered (see
    synmods.hub.app.HubCell.getDocsManifest for the Hub's Product-based
    scheme), so metadata.json here carries only the nav tree.

    Args:
        srcdir (str): The doc source directory (containing index.md).
        outdir (str): Output directory for the built bundle (created fresh).
        ci (bool): If True, write any warnings/validation issues to
            outdir/docbuild.warn instead of raising -- so a `make -j` run
            finishes building every package (see docs/Makefile's
            mddocs_ciflag). If False (the default, for local/interactive
            use), raise on the first issue.
        staticdir (str): Fallback read location (the real files/docs) for
            a mdtoc target or internal link that resolves to a page living
            only there, never staged from srcdir. None for a caller with
            no pre-existing static content to merge into (e.g. a fully
            isolated/fresh build).

    Returns:
        dict: {'toc': [...]} -- the same shape written to metadata.json.
    '''
    s_common.gendir(outdir)
    stageTree(srcdir, outdir)

    mdstormissues = await runMdstorm(outdir, srcdir=srcdir)

    tocbuilder = TocBuilder(outdir, staticdir=staticdir)
    # buildToc() must run before resolveFences(): it reads the original
    # ```mdtoc fences to walk the nav tree, and resolveFences() replaces
    # those same fences with rendered bullet lists.
    toc = tocbuilder.buildToc()
    tocbuilder.resolveFences()

    issues = []
    for relpath, msgs in mdstormissues.items():
        issues.extend(f'{relpath}: {mesg}' for mesg in msgs)
    issues.extend(validate(outdir, tocbuilder, staticdir=staticdir))

    metadata = {'toc': toc}
    s_json.jssave(metadata, outdir, 'metadata.json')

    if ci:
        with open(s_common.genpath(outdir, 'docbuild.warn'), 'w') as fd:
            if issues:
                fd.write('\n'.join(issues) + '\n')
    elif issues:
        # fold the issues into mesg, not just the issues= field -- s_exc.reprexc
        # (what a CLI's wrapmain ultimately prints) only ever shows mesg, so a bare
        # 'mddocs build failed' with the actual issues sitting unprinted in the
        # exception's info dict is not actionable from a CI log
        mesg = 'mddocs build failed:\n' + '\n'.join(f'  - {issue}' for issue in issues)
        raise s_exc.SynErr(mesg=mesg, issues=issues)

    return metadata

async def buildBundle(srcdir, outdir, staticdir=None, ci=False, warnfile=None, stagedir_parent=None):
    '''
    Build one doc bundle from srcdir and merge the result into outdir, the
    canonical bundle directory a caller has already committed (possibly
    holding static content -- see staticdir below -- that this build never
    staged and must leave untouched).

    Building happens in a private tempdir under stagedir_parent rather than
    into outdir directly: a doc that documents its own power-up by booting
    it as a live Storm service (```mdstorm-setup --load-svc``) has that
    service declare and serve its files by reading straight off disk, and
    for a self-referential Storm package build that disk location is
    outdir's own PARENT directory -- synapse.tools.storm.pkg.gen walks a
    package's entire files/ tree, of which files/docs (outdir) is only a
    part, so staging even one level up (a sibling of outdir, but still
    inside files/) would let that live service see a half-built bundle
    (pages already rewritten by earlier mdstorm passes, later ones still
    untouched) and fail its own sha256 check against the declared-files
    snapshot taken the moment its service module was first imported
    (mid-build). stagedir_parent lets a caller whose outdir nests inside a
    larger declared-files tree (buildPkgDocs) name that tree's real root
    instead of outdir's immediate parent. Only merged into outdir once the
    build has fully succeeded.

    docbuild.warn (buildDocs' own --ci output, written inside the staging
    dir) is never merged into outdir -- outdir is committed content, and a
    bundle's own build-time warning file has no business living permanently
    alongside it. If warnfile is given, it is copied there instead.

    Args:
        srcdir (str): The doc source directory (containing index.md).
        outdir (str): The canonical, committed bundle directory to merge
            built output into. Known limitation (inherited from the
            previous buildPkgDocs/files/docs behavior): if a docs/ source
            page is deleted, its stale built counterpart is not
            automatically removed from outdir.
        staticdir (str): Fallback read location (see buildDocs/TocBuilder)
            for a mdtoc target or internal link that resolves to a page
            living only in the committed bundle, never staged from srcdir
            (e.g. a plain page moved out of docs/ per the docs/-vs-
            committed split). Defaults to outdir itself.
        ci (bool): Passed through to buildDocs.
        warnfile (str): If given, buildDocs' docbuild.warn (only written
            when ci is True) is copied here instead of into outdir.
        stagedir_parent (str): Directory to create the private staging
            tempdir under. Defaults to outdir's own parent -- correct when
            outdir is not nested inside a larger tree a live service might
            declare as its own files (e.g. the synapse/synapse-enterprise
            bundles, which have no pkgdef at all). buildPkgDocs passes the
            package's own directory (files/'s parent) instead, since its
            outdir is files/docs, one level inside files/.

    Returns:
        dict: The built bundle's metadata (see buildDocs).
    '''
    if staticdir is None:
        staticdir = outdir

    if stagedir_parent is None:
        stagedir_parent = os.path.dirname(s_common.genpath(outdir))

    dirn = s_common.gendir(stagedir_parent)
    stagedir = tempfile.mkdtemp(prefix='.docsbuild-', dir=dirn)

    try:
        metadata = await buildDocs(srcdir, stagedir, ci=ci, staticdir=staticdir)

        for curdir, _dirs, fns in os.walk(stagedir):
            reldir = os.path.relpath(curdir, stagedir)
            for fn in fns:
                if reldir == '.' and fn == 'docbuild.warn':
                    if warnfile is not None:
                        s_common.gendir(os.path.dirname(s_common.genpath(warnfile)))
                        shutil.copy2(os.path.join(curdir, fn), warnfile)
                    continue

                srcpath = os.path.join(curdir, fn)
                dstdir = outdir if reldir == '.' else os.path.join(outdir, reldir)
                s_common.gendir(dstdir)
                shutil.copy2(srcpath, os.path.join(dstdir, fn))
    finally:
        shutil.rmtree(stagedir, ignore_errors=True)

    return metadata
