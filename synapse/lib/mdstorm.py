import os
import shlex
import logging
import argparse
import contextlib
import subprocess
import collections

import vcr
import regex
import markdown_it

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.json as s_json
import synapse.lib.output as s_output
import synapse.lib.autodoc as s_autodoc
import synapse.lib.cluster as s_cluster
import synapse.lib.dyndeps as s_dyndeps

import synapse.tools.storm._cli as s_storm
import synapse.tools.storm.pkg.gen as s_genpkg

logger = logging.getLogger(__name__)

ONLOAD_TIMEOUT = int(os.getenv('SYNDEV_PKG_LOAD_TIMEOUT', 30))  # seconds

# A fenced code block's info string is a directive iff its first
# whitespace-separated token is one of these names -- any other fenced code
# block (```python, ```json, a plain ```storm example left for future syntax
# highlighting, an unrecognized ```mdstorm-* typo, etc.) is passed through
# untouched as ordinary Markdown. The "mdstorm" prefix (rather than bare
# "storm") keeps the "storm" info string free for syntax-highlighting use,
# since mdstorm's own directives never need it ("mdshell" is a deliberate
# exception -- see its flags parser below). Kept as a regex over the
# markdown-it "fence" token's info string, rather than folded into
# _md_parser.handlers, so that a typo'd mdstorm-* name is still recognized
# as an *attempted* directive and raises NoSuchName instead of silently
# rendering as an unstyled code block. Anything after the directive name on
# the opening fence line is the directive's fence-line flags -- see
# _splitDirectiveFlags.
re_directive_name = regex.compile(r'^(?:mdstorm(?:-[a-z0-9]+)*|mdshell|mdautodoc)$')

_md_parser = markdown_it.MarkdownIt('commonmark')

# mdstorm's flags: hide-* control CLI echo/display; --vars/--opts replace the
# old storm-opts directive on a per-call basis; --fail replaces the old
# storm-fail directive on a per-call basis; --hide-output runs the query (to
# validate it) but only displays the "storm> ..." line, not its output;
# --hide replaces the old standalone storm-pre directive on a per-call basis,
# running the query silently (no output at all, not even the query line)
# (see "Key findings" #8, #10, #12, #14).
mdstorm_flags = argparse.ArgumentParser(add_help=False)
mdstorm_flags.add_argument('--hide-query', default=False, action='store_true',
                         help='Suppress the echoed "storm> ..." query line in the rendered doc.')
mdstorm_flags.add_argument('--hide-tags', default=False, action='store_true',
                         help='Suppress tag output in the rendered doc.')
mdstorm_flags.add_argument('--hide-props', default=False, action='store_true',
                         help='Suppress prop output in the rendered doc.')
mdstorm_flags.add_argument('--vars', default=None, help='JSON object merged into the Storm opts "vars" key.')
mdstorm_flags.add_argument('--opts', default=None, help='A full JSON Storm opts dict (mutually exclusive with --vars).')
mdstorm_flags.add_argument('--fail', default=False, action='store_true',
                         help='Expect this query to raise; show the error in the docs instead of crashing the '
                              'build. Errors if the query unexpectedly succeeds.')
mdstorm_flags.add_argument('--hide-output', default=False, action='store_true',
                         help='Execute the query (to validate it) but only display the query line, not its output.')
mdstorm_flags.add_argument('--hide', default=False, action='store_true',
                         help='Run the query to prep the Cortex; nothing is printed into the document, not even '
                              'the query line. Folds the old standalone storm-pre directive into storm itself.')
mdstorm_flags.add_argument('--mock-http', dest='mock_http', default=None, metavar='PATH',
                         help='A VCR cassette YAML file to record/replay HTTP calls made by this query only, '
                              'overriding the document-wide --mock-http cassette (if any) for this one call.')

# mdstorm-setup's flags: one-time, whole-document configuration, consolidating
# what used to be three separate directives (mdstorm-cortex, mdstorm-envvar,
# mdstorm-vcr-opts) into a single flag-based directive. --load-pkg/--load-svc
# are repeatable since a document may need more than one package/service.
mdstormsetup_flags = argparse.ArgumentParser(add_help=False)
mdstormsetup_flags.add_argument('--cortex', default='default', metavar='CTOR',
                                help='Module path to the Cortex cell ctor to use for this document '
                                     '(default: the open-source Cortex).')
mdstormsetup_flags.add_argument('--vcr-opts', dest='vcr_opts', default=None, metavar='JSON',
                                help='A JSON dict passed to the VCR() instantiation used by --mock-http.')
mdstormsetup_flags.add_argument('--envvar', action='append', default=[], metavar='KEY=VALUE',
                                help='Set KEY=VALUE into the environment if KEY is not already set (repeatable).')
mdstormsetup_flags.add_argument('--load-pkg', dest='load_pkg', action='append', default=[], metavar='PATH',
                                help='Load a Storm package from this path (repeatable).')
mdstormsetup_flags.add_argument('--load-svc', dest='load_svc', action='append', default=[], metavar='"CTOR NAME CONF"',
                                help='Start a Storm service, one shlex-quoted "ctor name conf" string per flag '
                                     '(repeatable).')

# mdshell's flags: recognized here (rather than built inline per-call in
# _handleShell) so the parser can be inspected via MdStorm.handlers without
# executing anything -- see tools.utils.mdstorm's --help directive listing.
mdshell_flags = argparse.ArgumentParser(add_help=False)
mdshell_flags.add_argument('--include-stderr', action='store_true',
                           help='Merge stderr into the captured/displayed output.')
mdshell_flags.add_argument('--hide-query', action='store_true',
                           help='Suppress the echoed command line, showing only its output.')
mdshell_flags.add_argument('--fail-ok', action='store_true',
                           help="Don't fail the mdstorm run if the command exits non-zero.")

# mdautodoc's flags: generate Markdown and splice it into the document at
# the point of use, replacing synapse.tools.utils.autodoc's old "generate a
# file, then splice it in by hand" flow. Exactly one target kind is
# recognized per fence; --level lets a fence nest its generated headings
# under an author-written heading instead of leaving them as page-level
# siblings (see _shiftHeadingLevel). Like mdstorm-setup there is no "--"
# body terminator -- every flag value here is a single token, so fence-line
# and body text are simply concatenated and shlex-split together.
mdautodoc_flags = argparse.ArgumentParser(add_help=False)
_mdautodoc_kind = mdautodoc_flags.add_mutually_exclusive_group(required=True)
_mdautodoc_kind.add_argument('--conf', metavar='CTOR',
                             help="A Cell subclass's confdefs, e.g. synmods.backup.service.Backup.")
_mdautodoc_kind.add_argument('--api', metavar='CTOR',
                             help="A class's own public methods (cls.__dict__, not its full MRO), "
                                  'e.g. synmods.enterprise.axon.AxonApi.')
_mdautodoc_kind.add_argument('--stormpkg', metavar='PATH',
                             help="A Storm package's command/module/dependency/endpoint reference, given the "
                                  'package prototype .yaml path (relative to this document unless absolute).')
_mdautodoc_kind.add_argument('--model-types', dest='model_types', default=False, action='store_true',
                             help="Synapse's data model: base types, ctors, and interfaces.")
_mdautodoc_kind.add_argument('--model-forms', dest='model_forms', default=False, action='store_true',
                             help="Synapse's data model: forms and their properties.")
_mdautodoc_kind.add_argument('--stormtypes-libs', dest='stormtypes_libs', default=False, action='store_true',
                             help='Every registered Storm library.')
_mdautodoc_kind.add_argument('--stormtypes-prims', dest='stormtypes_prims', default=False, action='store_true',
                             help='Every registered Storm primitive type.')
mdautodoc_flags.add_argument('--level', type=int, default=0, metavar='N',
                             help='Shift every heading in the generated block down by N levels, so it renders '
                                  'as a section under an author-written heading rather than a whole page.')

re_flag_token = regex.compile(r'--[a-zA-Z][a-zA-Z0-9-]*')
re_body_terminator = regex.compile(r'^--\s*$')
re_heading_line = regex.compile(r'^(#{1,6})( .*)$', flags=regex.MULTILINE)

def _shiftHeadingLevel(text, level):
    '''
    Shift every ATX heading ("# ...", "## ...", etc) in text down by level,
    capped at h6. Used by mdautodoc's --level: rather than threading a base
    level through every autodoc generator's internals (several of which emit
    a nested heading as literal Markdown, not through a level-aware helper),
    the generated block's rendered text is shifted uniformly after the fact.

    Args:
        text (str): The rendered Markdown block.
        level (int): The number of levels to shift by. 0 is a no-op.

    Returns:
        str: The shifted text.
    '''
    if not level:
        return text

    def _shift(match):
        return ('#' * min(6, len(match.group(1)) + level)) + match.group(2)

    return re_heading_line.sub(_shift, text)

def _splitDirectiveFlags(fenceargs, text, parser):
    '''
    A directive's flags may appear on the opening fence line (the text after
    the directive name, e.g. "```mdstorm --hide-query"), in the fence body,
    or both. Body flags occupy one or more lines at the top of the body --
    the flags themselves need not each be on their own line, or line up with
    the eventual terminator at all -- but that flags region as a whole must
    be terminated by a line containing exactly "--" and nothing else (the
    terminator itself *does* need its own line, so it is never confused with
    a flag's value); everything after that line is returned untouched as the
    literal query/command text -- this avoids ever reconstructing it from
    re-joined/re-quoted tokens, so a multi-line Storm query or shell command
    renders in docs exactly as authored. If the body has no such terminator
    line, the whole body is query text and only the fence-line flags (if
    any) apply -- so a query that happens to start with a single-dash Storm
    token, e.g. an edge like "-(sees)>", is never misread as a flag line.

    Flag values are taken verbatim as the text between one recognized flag
    and the next (rather than shlex-tokenized), so a --vars/--opts JSON blob
    may contain unquoted whitespace (e.g. --vars {"targ": "vertex.link"}).

    Args:
        fenceargs (str): The text following the directive name on the
            opening fence line, if any.
        text (str): The full fence body.
        parser (argparse.ArgumentParser): Parser for the recognized flags.

    Returns:
        (argparse.Namespace, str): Parsed flags (unset ones at their
            defaults) and the raw query/command text.
    '''
    lines = text.split('\n')

    termidx = None
    for idx, line in enumerate(lines):
        if re_body_terminator.match(line):
            termidx = idx
            break

    if termidx is None:
        bodyflags = ''
        query = text
    else:
        bodyflags = '\n'.join(lines[:termidx])
        query = '\n'.join(lines[termidx + 1:])

    flagtext = ' '.join(part.strip() for part in (fenceargs, bodyflags) if part.strip())

    matches = list(re_flag_token.finditer(flagtext))

    argv = []
    for i, match in enumerate(matches):
        flag = match.group(0)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(flagtext)
        value = flagtext[start:end].strip()

        argv.append(flag)
        if value:
            argv.append(value)

    opts = parser.parse_args(argv)
    return opts, query

class MdStormCli(s_storm.StormCli):
    '''
    mdstorm's query-execution entry point. Wraps the Storm CLI's own output
    formatting/error handling for use inside a rendered doc, and applies
    mdstorm's HTTP mocking: a single VCR cassette (mdstorm's --mock-http)
    applied to the call, with mdstorm-vcr-opts forwarded to the VCR recorder.
    '''

    async def __anit__(self, item, outp=s_output.stdout, opts=None):
        await s_storm.StormCli.__anit__(self, item, outp, opts)
        self.ctx = {}
        self.echoline = True
        self._print_skips.append('init')
        self._print_skips.append('fini')
        self._print_skips.append('edits')

    async def runCmdLine(self, text, opts=None):
        if text and text[0] == '!':
            if self.echoline:
                self.printf(f'{self.cmdprompt}{text}')
            save = self.echoline
            self.echoline = False
            try:
                ret = await s_storm.StormCli.runCmdLine(self, text, opts=opts)
            finally:
                self.echoline = save
            return ret
        return await s_storm.StormCli.runCmdLine(self, text, opts=opts)

    async def handleErr(self, mesg):
        #  raise on err for doc rendering
        if self.ctx.pop('storm-fail', None):
            await s_storm.StormCli.handleErr(self, mesg)
            return
        (errname, errinfo) = mesg[1]
        errinfo.setdefault('_errname', errname)
        raise s_exc.StormRuntimeError(**errinfo)

    def _printNodeProp(self, name, valu):
        base = f'        {name} = '
        if '\n' in valu:
            parts = collections.deque(valu.split('\n'))
            ws = ' ' * len(base)
            self.printf(f'{base}{parts.popleft()}')
            while parts:
                part = parts.popleft()
                self.printf(f'{ws}{part}')

        else:
            self.printf(f'{base}{valu}')

    async def runDocCmdLine(self, text, ctx, stormopts=None, mockhttp=None):
        self.ctx = ctx

        if mockhttp:
            vcr_kwargs = ctx.get('mdstorm-vcr-opts') or {}
            recorder = vcr.VCR(**vcr_kwargs)
            with recorder.use_cassette(mockhttp):
                await self.runCmdLine(text, opts=stormopts)
        else:
            await self.runCmdLine(text, opts=stormopts)

        return str(self.outp)

@contextlib.asynccontextmanager
async def getDocsCell(ctor, conf):
    loc = s_dyndeps.getDynLocal(ctor)
    if loc is None:
        raise s_exc.NoSuchCtor(mesg=f'Unable to resolve ctor [{ctor}]', ctor=ctor)

    # Build the cell config explicitly (rather than handing anit() a bare dict) so
    # that SYN_<CELL>_* environment variables are honored, matching production boot
    # behavior. The caller-provided conf takes precedence over the environment. Not
    # every doc-rendering ctor is a real Cell (some doc-only ctors are lightweight
    # test doubles with a custom anit()) -- fall back to the bare conf dict for
    # those, since they never supported env-var overrides in the first place.
    if issubclass(loc, s_cell.Cell):
        cellconf = loc.initCellConf()
        for name, valu in conf.items():
            cellconf.setdefault(name, valu)

        cellconf.setConfFromEnvs()
    else:
        cellconf = conf

    with s_common.getTempDir() as dirn:
        async with await loc.anit(dirn, conf=cellconf) as cell:
            yield cell

@contextlib.asynccontextmanager
async def getDocsCluster(ctor=None, coreconf=None):
    '''
    Boot a Cluster ( see synapse.lib.cluster ) for documentation Storm: a
    Cortex with its axon and jsonstor peers resolved by cell type on an
    ephemeral AHA network. Yields the Cluster; a caller needing an additional
    power-up peer alongside the Cortex ( e.g. a doc fixture booting a
    FileParser ) should boot it with the yielded Cluster's addSvc(), which
    already awaits its discovery. The AHA network and every booted service
    tear down together when the yielded Cluster is fini()d.

    This is a thin conf-default helper over synapse.lib.cluster.getCluster():
    it exists only so we can set some default config values for the docs core.

    Args:
        ctor: The Cortex class to boot. Defaults to the base synapse Cortex.
        coreconf (dict): Conf overrides for the Cortex boot (this dict wins on
            key conflicts with the defaults below).

    Notes:
        The Cortex no longer boots embedded axon / jsonstor cells, so doc Storm
        that uses ``$lib.axon`` / ``$lib.bytes`` / ``$lib.jsonstor`` ( or a
        package onload that does ) needs real peers to resolve.
    '''
    if ctor is None:
        ctor = s_cortex.Cortex

    conf = {'health:sysctl:checks': False}

    # readpool:size is only a valid config key on a cell that opts into a read
    # pool (eg synmods.enterprise.cortex.Cortex) -- setting it on a ctor that
    # doesn't (eg the base synapse.cortex.Cortex) is a BadArg at boot, not a
    # silently-ignored no-op.
    if 'readpool:size' in getattr(ctor, 'confbase', {}):
        conf['readpool:size'] = 0

    conf.update(coreconf or {})

    async with s_cluster.getCluster({'cortex': {'ctor': ctor, 'conf': conf}}) as clus:
        yield clus

class MdStorm(s_base.Base):

    async def __anit__(self, mdpath, mockhttp=None, srcdir=None, outdir=None):
        await s_base.Base.__anit__(self)

        self.mdpath = s_common.genpath(mdpath)

        if not os.path.isfile(self.mdpath):
            raise s_exc.BadConfValu(mesg='A valid mdpath must be specified', mdpath=self.mdpath)

        self.basedir = os.path.dirname(self.mdpath)

        # When this file is a staged copy (buildDocs' stageTree mirrors srcdir's
        # structure 1:1 into outdir), self.srcbasedir is the ORIGINAL directory
        # this file was staged from -- used to resolve a relative path that
        # lives outside the docroot (e.g. "../foo.yaml"), since stageTree
        # never copies a package's own yaml/storm sources -- nor a bundle's
        # mocks/ directory -- into the staged tree: mdautodoc's --stormpkg,
        # mdstorm-setup's --load-pkg, and a relative --mock-http all resolve
        # against it.
        if srcdir is not None and outdir is not None:
            relpath = os.path.relpath(self.basedir, s_common.genpath(outdir))
            self.srcbasedir = s_common.genpath(srcdir, relpath)
        else:
            self.srcbasedir = self.basedir

        # A VCR cassette path applied to every mdstorm query in the document,
        # used as the default for any ```mdstorm fence that does not specify
        # its own --mock-http (see _handleStorm) -- in practice one cassette
        # recording/replaying the whole document's HTTP traffic is the common
        # case, but a document with more than one distinct cassette (e.g. one
        # per external service it demonstrates) overrides this per fence.
        self.mockhttp = self._resolveMockHttp(mockhttp)

        self.linesout = []
        self.context = {}
        self.stormvars = {}

        self.core = None
        self.clus = None  # the Cluster backing self.core, when booted via getDocsCluster()
        self._forkediden = None  # set by Task 3's SYN_DOCS_CORTEX path; None means no view-scoping to apply
        self._remote = False  # True when self.core is a Telepath proxy to a SYN_DOCS_CORTEX Cortex
        self._cortexinit = False  # flips True on the first mdstorm-setup fence; a second one is an error

        self.onfini(self._finiCore)

        # Each value is (argparser, callback) so the flags recognized by a
        # directive can be inspected (e.g. for --help output) without
        # invoking it -- see tools.utils.mdstorm.
        self.handlers = {
            'mdstorm': (mdstorm_flags, self._handleStorm),
            'mdshell': (mdshell_flags, self._handleShell),
            'mdstorm-setup': (mdstormsetup_flags, self._handleStormSetup),
            'mdautodoc': (mdautodoc_flags, self._handleAutodoc),
        }

    async def _getCell(self, ctor, conf=None):
        if conf is None:
            conf = {}
        cell = await self.enter_context(getDocsCell(ctor, conf))
        return cell

    def _printf(self, line):
        self.linesout.append(line)

    def _reqCore(self):
        if self.core is None:
            mesg = 'No cortex set. Use a ```mdstorm-setup fenced block.'
            raise s_exc.NoSuchVar(mesg=mesg)
        return self.core

    def _resolveMockHttp(self, mockhttp):
        '''
        Resolve a cassette path relative to self.srcbasedir, the same way
        the document-wide --mock-http (self.mockhttp, resolved in
        __anit__) is resolved. Used both for that document-wide default
        and for a per-fence --mock-http override on an individual
        ```mdstorm fence.

        self.srcbasedir (rather than self.basedir) matters for a staged
        build (buildDocs' stageTree does not copy a bundle's mocks/
        directory -- see mddocs.stageTree): a relative cassette path is
        authored relative to the doc's original location, not wherever it
        was staged to, so resolving here must reach back to the source
        tree the same way mdautodoc's --stormpkg already does.

        Args:
            mockhttp (str or None): A cassette path, absolute or relative.

        Returns:
            str or None: The resolved absolute path, or None if mockhttp is None.
        '''
        if mockhttp is None:
            return None
        if not os.path.isabs(mockhttp):
            return os.path.join(self.srcbasedir, mockhttp)
        return mockhttp

    def _getHandler(self, directive):
        entry = self.handlers.get(directive)
        if entry is None:
            raise s_exc.NoSuchName(mesg=f'The {directive} directive is not supported', directive=directive)
        return entry

    def _buildStormOpts(self, varsjson, optsjson):
        '''
        Build a per-call Storm opts dict from a directive's --vars/--opts
        flags. Replaces the old storm-opts directive, which set a JSON blob
        into shared context that silently applied to every later directive.

        Args:
            varsjson (str or None): JSON object to merge into opts['vars'].
            optsjson (str or None): A full JSON opts dict (exclusive with varsjson).

        Returns:
            dict: The Storm opts for this one call.
        '''
        if varsjson and optsjson:
            raise s_exc.BadArg(mesg='--vars and --opts are mutually exclusive on a single directive.')
        if optsjson:
            return s_json.loads(optsjson)
        if varsjson:
            return {'vars': s_json.loads(varsjson)}
        return {}

    def _mergeViewOpts(self, opts):
        '''
        Inject the forked-view iden (set by Task 3's SYN_DOCS_CORTEX path)
        into a per-call opts dict, if a fork is active. A no-op until Task 3
        ever sets self._forkediden to a non-None value.
        '''
        if self._forkediden is not None:
            opts.setdefault('view', self._forkediden)
        return opts

    async def _handleStorm(self, parser, fenceargs, text):
        core = self._reqCore()

        opts, query = _splitDirectiveFlags(fenceargs, text, parser)

        mockhttp = self._resolveMockHttp(opts.mock_http) if opts.mock_http else self.mockhttp

        if opts.hide:
            # Prep query: run it against the Cortex but print nothing into
            # the processed document -- not even the "storm> ..." line
            # (unlike --hide-output, which still shows the query). Folds the old
            # standalone storm-pre directive into storm itself ("Key
            # findings" #14), including that a leftover --fail is
            # intentionally not enforced here: there is no displayed output
            # for an "expected failure" to be shown in, matching rstorm's
            # storm-pre, which always silently discarded any pending
            # storm-fail state rather than acting on it. Unlike the rest of
            # mdstorm, --hide also merges self.stormvars (values set via
            # mdstorm-setup's --envvar) into the call's vars, exactly as the
            # old storm-pre directive did.
            if opts.fail:
                self.context['storm-fail'] = True

            callopts = self._buildStormOpts(opts.vars, opts.opts)
            callopts.setdefault('vars', {})
            callopts['vars'].update(self.stormvars)
            callopts = self._mergeViewOpts(callopts)

            cli = await MdStormCli.anit(item=core)
            await cli.runDocCmdLine(query.strip(), self.context, stormopts=callopts, mockhttp=mockhttp)

            self.context.pop('storm-fail', None)
            return

        outp = s_output.OutPutStr()

        cli = await MdStormCli.anit(item=core, outp=outp)

        if opts.hide_query:
            cli.echoline = False
        if opts.hide_tags:
            cli.hidetags = True
        if opts.hide_props:
            cli.hideprops = True
        if opts.fail:
            self.context['storm-fail'] = True

        callopts = self._mergeViewOpts(self._buildStormOpts(opts.vars, opts.opts))

        self._printf('```stormdoc\n')

        result = await cli.runDocCmdLine(query.strip(), self.context, stormopts=callopts, mockhttp=mockhttp)

        if opts.hide_output:
            # Execution already happened above (proving the query is valid);
            # keep only the echoed "storm> ..." line, drop everything the
            # query printed/returned.
            result = result.split('\n', 1)[0] + '\n'

        self._printf(result)

        if self.context.pop('storm-fail', None):
            raise s_exc.StormRuntimeError(mesg='Expected a failure, but none occurred.')

        self._printf('```\n')

    async def _handleStormSetup(self, parser, fenceargs, text):
        '''
        One-time, whole-document setup: which Cortex to run queries against
        (and any packages/services to provision on it), the VCR() kwargs
        used by --mock-http, and default envvars. Consolidates what used to
        be three separate directives (mdstorm-cortex, mdstorm-envvar,
        mdstorm-vcr-opts) into a single flag-based directive, since in
        practice all of them are one-time, document-wide configuration.

        Spins up a temp Cortex if --cortex=default and SYN_DOCS_CORTEX is
        unset, else loads the given ctor, else (if SYN_DOCS_CORTEX is set
        and --cortex=default) connects to that Cortex over Telepath and
        forks a fresh View for this run so directive-driven edits never leak
        into the shared Cortex or across directive runs. --load-pkg/
        --load-svc are rejected in the fork path since packages/services are
        Cortex-global, not scoped to a forked view ("Key findings" #9). Only
        one mdstorm-setup directive is allowed per document.

        This directive's whole body is arguments (there is no trailing query
        text), so unlike mdstorm/mdshell there is no "--" body terminator --
        fence-line and body flags are simply concatenated and shlex-split
        together.

        Args:
            fenceargs (str): The text following "mdstorm-setup" on the
                opening fence line, if any.
            text (str): '[--cortex CTOR] [--vcr-opts JSON] [--envvar KEY=VALUE ...]
                [--load-pkg PATH ...] [--load-svc "CTOR NAME CONF" ...]'
        '''
        if self._cortexinit:
            raise s_exc.BadArg(mesg='Only one mdstorm-setup directive is allowed per document.')
        self._cortexinit = True

        combined = ' '.join(part.strip() for part in (fenceargs, text) if part.strip())
        opts = parser.parse_args(shlex.split(combined))

        for envvar in opts.envvar:
            name, valu = envvar.split('=', 1)
            name = name.strip()
            valu = valu.strip()
            self.stormvars[name] = os.getenv(name, valu)

        if opts.vcr_opts is not None:
            self.context['mdstorm-vcr-opts'] = s_json.loads(opts.vcr_opts)

        docscortex = os.getenv('SYN_DOCS_CORTEX')
        useremote = bool(docscortex) and opts.cortex == 'default'

        if useremote and (opts.load_pkg or opts.load_svc):
            raise s_exc.BadArg(mesg='--load-pkg/--load-svc are not supported with SYN_DOCS_CORTEX: packages and '
                                     'services are Cortex-global, not scoped to the per-run forked view.')

        if useremote:
            # Not registered via self.enter_context(): Base.fini() closes
            # enter_context()-registered context managers *before* running
            # onfini callbacks, which would tear down the Telepath proxy
            # before _finiCore gets a chance to delView() through it. Instead
            # _finiCore (an onfini callback) owns both the delView() call and
            # closing this proxy, in that order.
            self.core = await s_telepath.openurl(docscortex)
            self.clus = None
            self._forkediden = await self.core.callStorm('return($lib.view.get().fork().iden)')
            self._remote = True
            return

        if opts.cortex == 'default':
            # the default doc Cortex needs axon/jsonstor peers (resolved via AHA) so
            # doc Storm using $lib.axon/$lib.jsonstor works -- a package's onload may
            # use them unconditionally (the vertex package's onload, for one, calls
            # $lib.jsonstor.has()).
            self.clus = await self.enter_context(getDocsCluster())
            self.core = self.clus.cortex
        else:
            loc = s_dyndeps.getDynLocal(opts.cortex)
            if loc is None:
                raise s_exc.NoSuchCtor(mesg=f'Unable to resolve ctor [{opts.cortex}]', ctor=opts.cortex)
            if isinstance(loc, type) and issubclass(loc, s_cortex.Cortex):
                # a real Cortex subclass needs its axon/jsonstor peers resolved via AHA,
                # same as the default doc Cortex.
                self.clus = await self.enter_context(getDocsCluster(ctor=loc))
                self.core = self.clus.cortex
            else:
                # a doc-only test double (not a real Cell/Cortex) -- eg one that
                # provisions its own self-contained test cluster via anit() -- must
                # not also be wrapped in a second, redundant AHA network.
                self.clus = None
                self.core = await self._getCell(opts.cortex)

        self._forkediden = None
        self._remote = False

        for pkgpath in opts.load_pkg:
            await self._loadStormPkg(pkgpath)

        for svcspec in opts.load_svc:
            await self._startStormSvc(svcspec)

    async def _finiCore(self):
        if self.core is None:
            return

        try:
            if self._remote and self._forkediden is not None:
                await self.core.callStorm('$lib.view.del($iden)', opts={'vars': {'iden': self._forkediden}})
        except Exception:
            # The proxy close below must be unconditional -- a failed view
            # delete (network blip, timeout, storm error) must never leave a
            # live Telepath connection open against a shared, production
            # SYN_DOCS_CORTEX. Log loudly rather than swallow silently, since
            # the forked view itself is now orphaned (undeleted) on that
            # Cortex and needs a human to notice and clean it up.
            logger.exception(f'Failed to delete forked view {self._forkediden}; it is now orphaned.')
        finally:
            await self.core.fini()

        self.core = None
        self._forkediden = None
        self._remote = False

    async def _loadStormPkg(self, pkgpath):
        '''
        Load a Storm package into the current Cortex by path. Ported
        verbatim from the old standalone storm-pkg directive's body.

        A relative pkgpath resolves against self.srcbasedir, not
        self.basedir: every doc's ```mdstorm-setup --load-pkg targets its
        own package's prototype yaml at "../<pkg>.yaml" -- a sibling of
        the doc bundle's srcdir, not something stageTree stages -- the
        same resolution ```mdautodoc --stormpkg and a relative
        --mock-http use.

        Args:
            pkgpath (str): The path to a Storm package YAML file.
        '''
        if not os.path.isabs(pkgpath):
            pkgpath = os.path.join(self.srcbasedir, pkgpath)
        if not os.path.isfile(pkgpath):
            raise s_exc.NoSuchFile(mesg='Storm Package filepath does not exist', path=pkgpath)

        core = self._reqCore()

        pkg = s_genpkg.loadPkgProto(pkgpath)

        if pkg.get('onload') is not None:
            waiter = core.waiter(1, 'core:pkg:onload:complete')
        else:
            waiter = None

        await core.addStormPkg(pkg)

        if waiter is not None and not await waiter.wait(timeout=ONLOAD_TIMEOUT):
            raise s_exc.SynErr(mesg=f'Package onload failed to run for {pkg.get("name")}')

    async def _startStormSvc(self, svcspec):
        '''
        Start a Storm service and register it against the current Cortex,
        unless a service by that name is already registered (idempotent on
        repeat --svc calls with the same name, e.g. from a repeated flag or
        the same package's service being provisioned by more than one
        document -- see "Key findings" #12). The old storm-svc directive had
        no such guard since Cortex.addStormSvc generates a fresh iden per
        call and never raises on a reused name, silently registering a
        second, duplicate entry instead.

        A ctor whose registration name matches its own getCellType() (true of
        every real power-up service today, since that name IS what a
        StormSvc's own storm commands use to look it up, and it is also
        what AHA auto-discovery would register it under) is booted onto the
        current Cortex's own AHA network, if it has one, rather than
        standalone -- required for a service ( e.g. FileParser resolving
        aha://axon..., Metrics resolving aha://cortex... ) whose
        initServiceRuntime() calls _reqAhaServers(). A mismatched name falls
        back to the old standalone boot, since AHA auto-discovery would
        register the peer under its cell type regardless of the name
        requested here, risking a second, diverging registration.

        Args:
            svcspec (str): "ctor svcname [json svcconf]", exactly as the old
                storm-svc directive's text argument was formatted.
        '''
        core = self._reqCore()

        splts = svcspec.split(' ', 2)
        ctor, svcname = splts[:2]
        svcconf = s_json.loads(splts[2].strip()) if len(splts) == 3 else {}

        if core.getStormSvc(svcname) is not None:
            logger.debug(f'Storm service {svcname} is already registered, skipping --svc.')
            return

        loc = s_dyndeps.getDynLocal(ctor)
        if loc is None: # pragma: no cover
            raise s_exc.NoSuchCtor(mesg=f'Unable to resolve ctor [{ctor}]', ctor=ctor)

        iscell = issubclass(loc, s_cell.Cell)

        # a storm service is registered under, and addressed by, its cell type, and the
        # Cortex refuses a link reporting any other type. Reject a mismatch here rather
        # than letting $lib.service.wait() below block on a service which can never
        # become ready.
        if iscell and svcname != loc.getCellType():
            mesg = f'Storm service {ctor} must be loaded under its cell type ' \
                   f'{loc.getCellType()}, not {svcname}.'
            raise s_exc.BadArg(mesg=mesg, name=svcname)

        joinable = self.clus is not None and iscell

        # a package always fires this on an active cortex, after its inits and its
        # onload, so wait on it whenever the service delivers one.
        svcpkg = loc.cellapi._storm_svc_pkg
        waiter = None
        if svcpkg is not None:
            waiter = core.waiter(1, 'core:pkg:onload:complete')

        if joinable:
            svc = await self.clus.addSvc(loc, conf=svcconf, timeout=ONLOAD_TIMEOUT)
        else:
            svc = await self._getCell(ctor, conf=svcconf)

            svc.dmon.share('svc', svc)
            root = await svc.auth.getUserByName('root')
            await root.setPasswd('root')
            info = await svc.dmon.listen('tcp://127.0.0.1:0/')
            svc.dmon.test_addr = info
            host, port = info
            surl = f'tcp://root:root@127.0.0.1:{port}/svc'
            await core.nodes(f'service.add {svcname} {surl}')
            await core.nodes(f'$lib.service.wait({svcname})')

        if waiter is not None and not await waiter.wait(timeout=ONLOAD_TIMEOUT):
            raise s_exc.SynErr(mesg=f'Package onload failed to run for service {svcname}')

    async def _handleShell(self, parser, fenceargs, text):
        opts, query = _splitDirectiveFlags(fenceargs, text, parser)
        query = query.strip()

        stderr = None
        if opts.include_stderr:
            stderr = subprocess.STDOUT

        proc = subprocess.run(shlex.split(query), stdout=subprocess.PIPE, stderr=stderr, text=True)
        if proc.returncode != 0 and not opts.fail_ok:
            mesg = f'Error when executing mdshell directive: {query} (rv: {proc.returncode})'
            raise s_exc.SynErr(mesg=mesg)

        self._printf('```text\n')

        if not opts.hide_query:
            self._printf(f'{query}\n')

        for line in proc.stdout.splitlines():
            self._printf(f'{line}\n')

        self._printf('```\n')

    async def _handleAutodoc(self, parser, fenceargs, text):
        '''
        Splice generated Markdown (a Cell's confdefs, a class's own API, a
        Storm package's command/module reference, the data model, or the
        Storm types reference) into the document, replacing the old
        "generate a file into an autodoc: savedir, then splice it in by
        hand" flow driven by mddocs.yaml. Like mdstorm-setup, there is no
        "--" body terminator -- every flag here is a single token, so
        fence-line and body text are simply concatenated and shlex-split
        together.

        Args:
            parser (argparse.ArgumentParser): mdautodoc_flags.
            fenceargs (str): Text following "mdautodoc" on the opening fence line.
            text (str): The fence body, normally empty.
        '''
        combined = ' '.join(part.strip() for part in (fenceargs, text) if part.strip())
        opts = parser.parse_args(shlex.split(combined))

        if opts.conf is not None:
            md = await s_autodoc.docConfdefsMd(opts.conf)
        elif opts.api is not None:
            md = await s_autodoc.docApiMd(opts.api)
        elif opts.stormpkg is not None:
            pkgpath = opts.stormpkg
            if not os.path.isabs(pkgpath):
                pkgpath = os.path.join(self.srcbasedir, pkgpath)
            if not os.path.isfile(pkgpath):
                raise s_exc.NoSuchFile(mesg='mdautodoc stormpkg path does not exist', path=pkgpath)
            md = await s_autodoc.docStormpkgMd(pkgpath)
        elif opts.model_types:
            async with s_cortex.getTempCortex() as core:
                md = await s_autodoc.docModelTypesMd(core)
        elif opts.model_forms:
            async with s_cortex.getTempCortex() as core:
                md = await s_autodoc.docModelFormsMd(core)
        elif opts.stormtypes_libs:
            md = await s_autodoc.docStormTypesLibsMd()
        else:
            md = await s_autodoc.docStormTypesPrimsMd()

        text = _shiftHeadingLevel(md.getMdText(), opts.level)

        self._printf(text)
        if not text.endswith('\n'):
            self._printf('\n')

    def _getDirectiveFences(self, lines):
        '''
        Use markdown-it to find this document's top-level fenced code blocks
        whose info string names a directive, in document order.

        markdown-it (rather than a hand-rolled line scan) correctly ignores
        fences nested inside a blockquote/list (token.level > 0) and fences
        that are really indented code blocks, and tolerates longer (````)
        fences -- cases the old bare regex scanner either mishandled or
        never supported. A fence is only ever consulted for its line range;
        its body text is always re-sliced from the original lines so
        directive text renders in docs exactly as authored.

        Args:
            lines (list): The full file's lines (with line endings).

        Returns:
            list: (start, end, directive, fenceargs, body) tuples, start/end
                being the [start, end) line-index range of the fence (open
                through close), sorted by start. fenceargs is any text after
                the directive name on the opening fence line.
        '''
        fences = []

        for token in _md_parser.parse(''.join(lines)):
            if token.type != 'fence' or token.level != 0:
                continue

            info = token.info.strip()
            directive, _, fenceargs = info.partition(' ')
            if re_directive_name.match(directive) is None:
                continue
            fenceargs = fenceargs.strip()

            start, end = token.map
            if lines[end - 1].strip() != token.markup:
                raise s_exc.BadSyntax(mesg=f'Unterminated ```{directive} fence', directive=directive)

            body = ''.join(lines[start + 1:end - 1]).strip('\n')
            fences.append((start, end, directive, fenceargs, body))

        return fences

    async def run(self):
        '''
        Parses the specified markdown file with fenced Storm directive handling.

        Returns:
            list: List of line strings for the processed markdown output
        '''
        with open(self.mdpath, 'r') as fd:
            lines = fd.readlines()

        fences = iter(self._getDirectiveFences(lines))
        nextfence = next(fences, None)

        idx = 0
        while idx < len(lines):
            if nextfence is not None and idx == nextfence[0]:
                start, end, directive, fenceargs, text = nextfence

                parser, handler = self._getHandler(directive)
                logger.debug(f'Executing {directive} -> {fenceargs!r} {text}')
                await handler(parser, fenceargs, text)

                idx = end
                nextfence = next(fences, None)
                continue

            self._printf(lines[idx])
            idx += 1

        return self.linesout
