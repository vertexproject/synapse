import os
import copy
import json
import pprint
import contextlib

import regex

from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.stormhttp as s_stormhttp

import synapse.cmds.cortex as s_cmds_cortex

import synapse.tools.genpkg as s_genpkg

re_directive = regex.compile(r'^\.\.\s(storm.*|[^:])::(?:\s(.*)$|$)')

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

    async def runCmdLine(self, line):
        opts = self.getCmdOpts(f'storm {line}')
        return await self.runCmdOpts(opts)

    async def _mockHttp(self, *args, **kwargs):
        info = {
            'code': 200,
            'body': '{}',
        }

        resp = self.ctx.get('mock-http')
        if resp:
            body = resp.get('body')

            if isinstance(body, dict):
                body = json.dumps(body)

            info = {
                'code': resp.get('code', 200),
                'body': body.encode(),
            }

        return s_stormhttp.HttpResp(info)

    def printf(self, mesg, addnl=True, color=None):
        line = f'    {mesg}'
        self.lines.append(line)
        return line

    def _silence(self, mesg, opts):
        pass

    def _onErr(self, mesg, opts):
        # raise on err for rst
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
        with mock.patch('synapse.lib.stormhttp.LibHttp._httpRequest', new=self._mockHttp):
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

@contextlib.asynccontextmanager
async def getCell(ctor, conf):
    with s_common.getTempDir() as dirn:
        loc = s_dyndeps.getDynLocal(ctor)
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

        self.core = None

        self.handlers = {
            'storm': self._handleStorm,
            'storm-pkg': self._handleStormPkg,
            'storm-pre': self._handleStormPre,
            'storm-svc': self._handleStormSvc,
            'storm-opts': self._handleStormOpts,
            'storm-cortex': self._handleStormCortex,
            'storm-expect': self._handleStormExpect,
            'storm-mock-http': self._handleStormMockHttp,
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

        self._printf('::\n')
        self._printf('\n')

        soutp = StormOutput(core, self.context, stormopts=self.context.get('storm-opts'))
        self._printf(await soutp.runCmdLine(text))

        self._printf('\n\n')

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
        soutp = StormOutput(core, self.context, stormopts=self.context.get('storm-opts'))
        await soutp.runCmdLine(text)

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

    async def _handleStormOpts(self, text):
        '''
        Opts to use in subsequent Storm queries.

        Args:
            text (str): JSON string, e.g. {"vars": {"foo": "bar"}}
        '''
        item = json.loads(text)
        self.context['storm-opts'] = item

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
        if not os.path.isfile(text):
            raise s_exc.NoSuchFile(mesg='Storm HTTP mock filepath does not exist', path=text)

        self.context['mock-http'] = s_common.jsload(text)

    async def _readline(self, line):

        match = re_directive.match(line)

        if match is not None:
            directive, text = match.groups()
            text = text.strip()

            handler = self._getHandler(directive)
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
