import os
import copy
import json
import pprint
import logging
import contextlib
import collections

import vcr
import regex

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.stormhttp as s_stormhttp

import synapse.cmds.cortex as s_cmds_cortex

import synapse.tools.storm as s_storm
import synapse.tools.genpkg as s_genpkg


re_directive = regex.compile(r'^\.\.\s(storm.*|[^:])::(?:\s(.*)$|$)')

logger = logging.getLogger(__name__)


class OutPutRst(s_output.OutPutStr):
    '''
    Rst specific helper for output intended to be indented
    in RST text as a literal block.
    '''
    prefix = '    '

    def printf(self, mesg, addnl=True):

        if '\n' in mesg:
            logger.debug(f'Newline found in [{mesg}]')
            parts = mesg.split('\n')
            mesg0 = '\n'.join([self.prefix + part for part in parts[1:]])
            mesg = '\n'.join((parts[0], mesg0))

        return s_output.OutPutStr.printf(self, mesg, addnl)


class StormOutput(s_cmds_cortex.StormCmd):
    '''
    Produce standard output from a stream of storm runtime messages.
    Must be instantiated for a single query with a rstorm context.
    '''

    _cmd_syntax = (
        ('--hide-query', {}),
    ) + s_cmds_cortex.StormCmd._cmd_syntax

    def __init__(self, core, ctx, stormopts=None, opts=None):
        if opts is None:
            opts = {}

        s_cmds_cortex.StormCmd.__init__(self, None, **opts)

        self.stormopts = stormopts or {}

        # hide a few mesg types by default
        for mtype in ('init', 'fini', 'node:edits', 'node:edits:count', 'prov:new'):
            self.cmdmeths[mtype] = self._silence

        self.core = core
        self.ctx = ctx
        self.lines = []
        self.prefix = '    '

    async def runCmdLine(self, line):
        opts = self.getCmdOpts(f'storm {line}')
        return await self.runCmdOpts(opts)

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

    async def _mockHttp(self, *args, **kwargs):
        info = {
            'code': 200,
            'body': '{}',
        }

        resp = self.ctx.get('mock-http')
        if resp:
            body = resp.get('body')

            if isinstance(body, (dict, list)):
                body = json.dumps(body)

            info = {
                'code': resp.get('code', 200),
                'body': body.encode(),
            }

        return s_stormhttp.HttpResp(info)

    @contextlib.contextmanager
    def _shimHttpCalls(self, vcr_kwargs):
        path = self.ctx.get('mock-http-path')
        if not vcr_kwargs:
            vcr_kwargs = {}

        if path:
            path = os.path.abspath(path)
            # try it as json first (since yaml can load json...). if it parses, we're old school
            # if it doesn't, either it doesn't exist/we can't read it/we can't parse it.
            # in any of those cases, default to using vcr
            try:
                with open(path, 'r') as fd:
                    byts = json.load(fd)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                byts = None

            if not byts:
                recorder = vcr.VCR(**vcr_kwargs)
                vcrcb = self.ctx.get('storm-vcr-callback', None)
                if vcrcb:
                    vcrcb(recorder)
                with recorder.use_cassette(os.path.abspath(path)) as cass:
                    yield cass
                    self.ctx.pop('mock-http-path', None)
            else:  # backwards compat
                if not os.path.isfile(path):
                    raise s_exc.NoSuchFile(mesg='Storm HTTP mock filepath does not exist', path=path)
                self.ctx['mock-http'] = byts
                with mock.patch('synapse.lib.stormhttp.LibHttp._httpRequest', new=self._mockHttp):
                    yield
        else:
            yield

    def printf(self, mesg, addnl=True, color=None):
        line = f'{self.prefix}{mesg}'
        if '\n' in line:
            logger.debug(f'Newline found in [{mesg}]')
            parts = line.split('\n')
            mesg0 = '\n'.join([self.prefix + part for part in parts[1:]])
            line = '\n'.join((parts[0], mesg0))

        self.lines.append(line)
        return line

    def _silence(self, mesg, opts):
        pass

    def _onErr(self, mesg, opts):
        # raise on err for rst
        if self.ctx.pop('storm-fail', None):
            s_cmds_cortex.StormCmd._onErr(self, mesg, opts)
            return
        raise s_exc.StormRuntimeError(mesg=mesg)

    async def runCmdOpts(self, opts):

        text = opts.get('query')

        if not opts.get('hide-query'):
            self.printf(f'> {text}')

        stormopts = copy.deepcopy(self.stormopts)

        stormopts.setdefault('repr', True)
        stormopts.setdefault('path', opts.get('path', False))

        hide_unknown = True

        # Let this raise on any errors
        with self._shimHttpCalls(self.ctx.get('storm-vcr-opts')):
            async for mesg in self.core.storm(text, opts=stormopts):

                if opts.get('debug'):
                    self.printf(pprint.pformat(mesg))
                    continue

                try:
                    func = self.cmdmeths[mesg[0]]
                except KeyError:  # pragma: no cover
                    if hide_unknown:
                        continue
                    self.printf(repr(mesg), color=s_cmds_cortex.UNKNOWN_COLOR)
                else:
                    func(mesg, opts)

        return '\n'.join(self.lines)

class StormCliOutput(s_storm.StormCli):

    async def __anit__(self, item, outp=s_output.stdout, opts=None):
        await s_storm.StormCli.__anit__(self, item, outp, opts)
        self.ctx = {}
        self._print_skips.append('init')
        self._print_skips.append('fini')
        self._print_skips.append('prov:new')
        self._print_skips.append('node:edits')
        self._print_skips.append('node:edits:count')

    def printf(self, mesg, addnl=True, color=None):
        mesg = f'    {mesg}'
        s_storm.StormCli.printf(self, mesg, addnl, color)

    async def handleErr(self, mesg):
        #  raise on err for rst
        if self.ctx.pop('storm-fail', None):
            await s_storm.StormCli.handleErr(self, mesg)
            return
        raise s_exc.StormRuntimeError(mesg=mesg)

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

    async def _mockHttp(self, *args, **kwargs):
        info = {
            'code': 200,
            'body': '{}',
        }

        resp = self.ctx.get('mock-http')
        if resp:
            body = resp.get('body')

            if isinstance(body, (dict, list)):
                body = json.dumps(body)

            info = {
                'code': resp.get('code', 200),
                'body': body.encode(),
            }

        return s_stormhttp.HttpResp(info)

    @contextlib.contextmanager
    def _shimHttpCalls(self, vcr_kwargs):
        path = self.ctx.get('mock-http-path')
        if not vcr_kwargs:
            vcr_kwargs = {}

        if path:
            path = os.path.abspath(path)
            # try it as json first (since yaml can load json...). if it parses, we're old school
            # if it doesn't, either it doesn't exist/we can't read it/we can't parse it.
            # in any of those cases, default to using vcr
            try:
                with open(path, 'r') as fd:
                    byts = json.load(fd)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                byts = None

            if not byts:
                with vcr.use_cassette(os.path.abspath(path), **vcr_kwargs) as cass:
                    yield cass
                    self.ctx.pop('mock-http-path', None)
            else:  # backwards compat
                if not os.path.isfile(path):
                    raise s_exc.NoSuchFile(mesg='Storm HTTP mock filepath does not exist', path=path)
                self.ctx['mock-http'] = byts
                with mock.patch('synapse.lib.stormhttp.LibHttp._httpRequest', new=self._mockHttp):
                    yield
        else:
            yield

    async def runRstCmdLine(self, text, ctx, stormopts=None):
        self.ctx = ctx

        self.printf(self.cmdprompt + text)

        with self._shimHttpCalls(self.ctx.get('storm-vcr-opts')):

            await self.runCmdLine(text, opts=stormopts)

        return str(self.outp)

@contextlib.asynccontextmanager
async def getCell(ctor, conf):
    loc = s_dyndeps.getDynLocal(ctor)
    if loc is None:
        raise s_exc.NoSuchCtor(mesg=f'Unable to resolve ctor [{ctor}]', ctor=ctor)
    with s_common.getTempDir() as dirn:
        async with await loc.anit(dirn, conf=conf) as cell:
            yield cell

class StormRst(s_base.Base):

    async def __anit__(self, rstfile):
        await s_base.Base.__anit__(self)

        self.rstfile = s_common.genpath(rstfile)

        if not os.path.isfile(rstfile):
            raise s_exc.BadConfValu(mesg='A valid rstfile must be specified', rstfile=self.rstfile)

        self.linesout = []
        self.context = {}
        self.stormvars = {}

        self.core = None

        self.handlers = {
            'storm': self._handleStorm,
            'storm-cli': self._handleStormCli,
            'storm-pkg': self._handleStormPkg,
            'storm-pre': self._handleStormPre,
            'storm-svc': self._handleStormSvc,
            'storm-fail': self._handleStormFail,
            'storm-opts': self._handleStormOpts,
            'storm-cortex': self._handleStormCortex,
            'storm-envvar': self._handleStormEnvVar,
            'storm-expect': self._handleStormExpect,
            'storm-multiline': self._handleStormMultiline,
            'storm-mock-http': self._handleStormMockHttp,
            'storm-vcr-opts': self._handleStormVcrOpts,
            'storm-clear-http': self._handleStormClearHttp,
            'storm-vcr-callback': self._handleStormVcrCallback,
        }

    async def _getCell(self, ctor, conf=None):
        if conf is None:
            conf = {}

        cell = await self.enter_context(getCell(ctor, conf))

        return cell

    def _printf(self, line):
        self.linesout.append(line)

    def _reqCore(self):
        if self.core is None:
            mesg = 'No cortex set.  Use .. storm-cortex::'
            raise s_exc.NoSuchVar(mesg=mesg)
        return self.core

    def _getHandler(self, directive):
        handler = self.handlers.get(directive)
        if handler is None:
            raise s_exc.NoSuchName(mesg=f'The {directive} directive is not supported', directive=directive)
        return handler

    async def _handleStorm(self, text):
        '''
        Run a Storm command and generate text from the output.

        Args:
            text (str): A valid Storm query.
        '''
        core = self._reqCore()
        text = self._getStormMultiline(text)

        self._printf('::\n')
        self._printf('\n')

        soutp = StormOutput(core, self.context, stormopts=self.context.get('storm-opts'))
        self._printf(await soutp.runCmdLine(text))

        if self.context.pop('storm-fail', None):
            raise s_exc.StormRuntimeError(mesg='Expected a failure, but none occurred.')

        self._printf('\n\n')

    async def _handleStormCli(self, text):
        core = self._reqCore()
        outp = OutPutRst()
        text = self._getStormMultiline(text)

        self._printf('::\n')
        self._printf('\n')

        cli = await StormCliOutput.anit(item=core, outp=outp)

        self._printf(await cli.runRstCmdLine(text, self.context, stormopts=self.context.get('storm-opts')))

        if self.context.pop('storm-fail', None):
            raise s_exc.StormRuntimeError(mesg='Expected a failure, but none occurred.')

        self._printf('\n')

    async def _handleStormPkg(self, text):
        '''
        Load a Storm package into the Cortex by path.

        Args:
            text (str): The path to a Storm package YAML file.
        '''
        if not os.path.isfile(text):
            raise s_exc.NoSuchFile(mesg='Storm Package filepath does not exist', path=text)

        core = self._reqCore()

        pkg = s_genpkg.loadPkgProto(text)
        await core.addStormPkg(pkg)

    async def _handleStormPre(self, text):
        '''
        Run a Storm query to prepare the Cortex without output.

        Args:
            text (str): A valid Storm query
        '''
        core = self._reqCore()

        self.context.setdefault('storm-opts', {})

        stormopts = self.context.get('storm-opts')
        stormopts.setdefault('vars', {})

        # only map env vars in for storm-pre
        stormopts = copy.deepcopy(stormopts)
        stormopts['vars'].update(self.stormvars)

        soutp = StormOutput(core, self.context, stormopts=stormopts)
        await soutp.runCmdLine(text)

        self.context.pop('storm-fail', None)

    async def _handleStormSvc(self, text):
        '''
        Load a Storm service by ctor and add to the Cortex.

        Args:
            text (str): <ctor> <svcname> <optional JSON string to use as svcconf>
        '''
        core = self._reqCore()

        splts = text.split(' ', 2)
        ctor, svcname = splts[:2]
        svcconf = json.loads(splts[2].strip()) if len(splts) == 3 else {}

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

    async def _handleStormFail(self, text):
        valu = json.loads(text)
        assert valu in (True, False), f'storm-fail must be a boolean: {text}'
        self.context['storm-fail'] = valu

    def _getStormMultiline(self, text):
        if '=' in text:
            sentinel, key = text.split('=', 1)
            if sentinel != 'MULTILINE':
                return text
            ret = self.context.get('multiline', {}).get(key)
            assert ret is not None, f'Invalid multiline text: {text}'
            return ret
        return text

    async def _handleStormMultiline(self, text):
        key, valu = text.split('=', 1)
        assert key.isupper()
        valu = json.loads(valu)
        assert isinstance(valu, str)
        multi = self.context.get('multiline', {})
        multi[key] = valu
        self.context['multiline'] = multi

    async def _handleStormOpts(self, text):
        '''
        Opts to use in subsequent Storm queries.

        Args:
            text (str): JSON string, e.g. {"vars": {"foo": "bar"}}
        '''
        item = json.loads(text)
        self.context['storm-opts'] = item

    async def _handleStormClearHttp(self, text):
        '''
        Reset the storm http context and any associated opts with it.

        Args:
            text (str): true if you also want to clear any storm/vcr opts as well
        '''
        if text == 'true':
            self.context.pop('storm-opts', None)
            self.context.pop('storm-vcr-opts', None)
            self.context.pop('storm-vcr-callback', None)
        self.context.pop('mock-http-path', None)
        self.context.pop('mock-http', None)

    async def _handleStormCortex(self, text):
        '''
        Spin up a default Cortex if ctor=default, else load the defined ctor.

        TODO: Handle providing conf in text

        Args:
            text (str): "default" or a ctor (e.g. synapse.cortex.Cortex)
        '''
        if self.core is not None:
            await self.core.fini()
            self.core = None

        ctor = 'synapse.cortex.Cortex' if text == 'default' else text

        self.core = await self._getCell(ctor)

    async def _handleStormEnvVar(self, text):
        name, valu = text.split('=', 1)
        name = name.strip()
        valu = valu.strip()
        self.stormvars[name] = os.getenv(name, valu)

    async def _handleStormExpect(self, text):
        # TODO handle some light weight output confirmation.
        return

    async def _handleStormMockHttp(self, text):
        '''
        Setup an HTTP mock file to be used with a later Storm command.

        Response file format:
        {
            "code": int,
            "body": {
                "data": json or a json str
            }
        }

        Args:
            text (str): Path to a json file with the response.
        '''
        self.context['mock-http-path'] = text

    async def _handleStormVcrOpts(self, text):
        '''
        Opts to pass to VCRPY for use in generating docs

        Args:
            text (str): JSON string, e.g. {"filter_query_args": true}
        '''
        item = json.loads(text)
        self.context['storm-vcr-opts'] = item

    async def _handleStormVcrCallback(self, text):
        '''
        Get a callback function as a dynlocal
        '''
        cb = s_dyndeps.getDynLocal(text)
        if cb is None:
            raise s_exc.NoSuchCtor(mesg=f'Failed to get callback "{text}"', ctor=text)
        self.context['storm-vcr-callback'] = cb

    async def _readline(self, line):

        match = re_directive.match(line)

        if match is not None:
            directive, text = match.groups()
            text = text.strip()

            handler = self._getHandler(directive)
            logger.debug(f'Executing {directive} -> {text}')
            await handler(text)

            return

        self._printf(line)

    async def run(self):
        '''
        Parses the specified RST file with Storm directive handling.

        Returns:
            list: List of line strings for the RST output
        '''
        with open(self.rstfile, 'r') as fd:
            lines = fd.readlines()

        for line in lines:
            await self._readline(line)

        return self.linesout
