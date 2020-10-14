import os
import copy
import json
import logging
import pathlib
import contextlib

import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.base as s_base
import synapse.lib.cmdr as s_cmdr
import synapse.lib.msgpack as s_msgpack

loggers_to_supress = (
    'synapse.lib.view',
)

def getDocPath(fn, root=None):
    '''
    Helper for getting a documentation data file paths.

    Args:
        fn (str): Name of the file to retrieve the full path for.
        root (str): Optional root path to look for a docdata in.

    Notes:
        Defaults to looking for the ``docdata`` directory in the current
        working directory. This behavior works fine for notebooks nested
        in the docs directory of synapse; but this root directory that
        is looked for may be overridden by providing an alternative root.

    Returns:
        str: A file path.

    Raises:
        ValueError if the file does not exist or directory traversal attempted..
    '''
    cwd = pathlib.Path(os.getcwd())
    if root:
        cwd = pathlib.Path(root)
    # Walk up a directory until you find '...d./data'
    while True:
        dpath = cwd.joinpath('docdata')
        if dpath.is_dir():
            break
        parent = cwd.parent
        if parent == cwd:
            raise ValueError(f'Unable to find data directory from {os.getcwd()}.')
        cwd = parent

    # Protect against traversal
    fpath = os.path.abspath(os.path.join(dpath.as_posix(), fn))
    if not fpath.startswith(dpath.as_posix()):
        raise ValueError(f'Path escaping detected: {fn}')

    # Existence
    if not os.path.isfile(fpath):
        raise ValueError(f'File does not exist: {fn}')

    return fpath

def getDocData(fp, root=None):
    '''

    Args:
        fn (str): Name of the file to retrieve the data of.
        root (str): Optional root path to look for a docdata directory in.

    Notes:
        Will detect json/jsonl/yaml/mpk extensions and automatically
        decode that data if found; otherwise it returns bytes.

        Defaults to looking for the ``docdata`` directory in the current
        working directory. This behavior works fine for notebooks nested
        in the docs directory of synapse; but this root directory that
        is looked for may be overridden by providing an alternative root.

    Returns:
        data: May be deserialized data or bytes.

    Raises:
        ValueError if the file does not exist or directory traversal attempted..
    '''
    fpath = getDocPath(fp, root)
    if fpath.endswith('.yaml'):
        return s_common.yamlload(fpath)
    if fpath.endswith('.json'):
        return s_common.jsload(fpath)
    with s_common.genfile(fpath) as fd:
        if fpath.endswith('.mpk'):
            return s_msgpack.un(fd.read())
        if fpath.endswith('.jsonl'):
            recs = []
            for line in fd.readlines():
                recs.append(json.loads(line.decode()))
            return recs
        return fd.read()


@contextlib.asynccontextmanager
async def genTempCoreProxy(mods=None):
    '''Get a temporary cortex proxy.'''
    with s_common.getTempDir() as dirn:
        async with await s_cortex.Cortex.anit(dirn) as core:
            if mods:
                for mod in mods:
                    await core.loadCoreModule(mod)
            async with core.getLocalProxy() as prox:
                # Use object.__setattr__ to hulk smash and avoid proxy getattr magick
                object.__setattr__(prox, '_core', core)
                yield prox

@contextlib.asynccontextmanager
async def genTempStormsvcProxy(cmdrcore, svcname, svcctor, conf=None):
    if conf is None:
        conf = {}

    conf = copy.deepcopy(conf)

    with s_common.getTempDir() as dirn:

        async with await svcctor(dirn, conf=conf) as svc:
            svc.dmon.share(svcname, svc)

            root = await svc.auth.getUserByName('root')
            await root.setPasswd('secret')

            info = await svc.dmon.listen('tcp://127.0.0.1:0/')
            svc.dmon.test_addr = info
            host, port = info
            surl = f'tcp://root:secret@127.0.0.1:{port}/{svcname}'

            await cmdrcore.storm(f'service.add {svcname} {surl}')
            await cmdrcore.storm(f'$lib.service.wait({svcname})')

            async with svc.getLocalProxy() as prox:
                # Use object.__setattr__ to hulk smash and avoid proxy getattr magick
                object.__setattr__(prox, '_svc', svc)
                yield prox

async def getItemCmdr(prox, outp=None, locs=None):
    '''Get a Cmdr instance with prepopulated locs'''
    cmdr = await s_cmdr.getItemCmdr(prox, outp=outp)
    cmdr.echoline = True
    if locs:
        cmdr.locs.update(locs)
    return cmdr

class CmdrCore(s_base.Base):
    '''
    A helper for jupyter/storm CLI interaction
    '''
    async def __anit__(self, core, outp=None):
        await s_base.Base.__anit__(self)
        self.prefix = 'storm'  # Eventually we may remove or change this
        self.core = core
        locs = {'storm:hide-unknown': True}
        self.cmdr = await getItemCmdr(self.core, outp=outp, locs=locs)
        self.onfini(self._onCmdrCoreFini)
        self.acm = None  # A placeholder for the context manager

    async def addFeedData(self, name, items, *, viewiden=None):
        '''
        Add feed data to the cortex.
        '''
        return await self.core.addFeedData(name, items, viewiden=viewiden)

    async def runCmdLine(self, text):
        '''
        Run a line of text directly via cmdr.
        '''
        await self.cmdr.runCmdLine(text)

    @contextlib.contextmanager
    def suppress_logging(self, suppress):
        '''
        Context manager to suppress specific loggers.
        '''
        logs = {}
        if not suppress:
            yield None
        else:
            try:
                for logname in loggers_to_supress:
                    logger = logging.getLogger(logname)
                    if logger is not None:
                        logs[logname] = (logger, logger.level)
                        logger.setLevel(logger.level + 100)
                yield None
            finally:
                for (logger, level) in logs.values():
                    logger.setLevel(level)

    async def _runStorm(self, text, opts=None, cmdr=False, suppress_logging=False):
        mesgs = []
        with self.suppress_logging(suppress_logging):
            if cmdr:
                if self.prefix:
                    text = ' '.join((self.prefix, text))

                def onEvent(event):
                    mesg = event[1].get('mesg')
                    mesgs.append(mesg)

                with self.cmdr.onWith('storm:mesg', onEvent):
                    await self.runCmdLine(text)

            else:
                async for mesg in self.core.storm(text, opts=opts):
                    mesgs.append(mesg)

        return mesgs

    async def storm(self, text, opts=None, num=None, cmdr=False, suppress_logging=False):
        '''
        A helper for executing a storm command and getting a list of storm messages.

        Args:
            text (str): Storm command to execute.
            opts (dict): Opt to pass to the cortex during execution.
            num (int): Number of nodes to expect in the output query. Checks that with an assert statement.
            cmdr (bool): If True, executes the line via the Cmdr CLI and will send output to outp.
            suppress_logging (bool): If True, suppresses some logging related to Storm runtime exceptions.

        Notes:
            The opts dictionary will not be used if cmdr=True.

        Returns:
            list: A list of storm messages.
        '''
        mesgs = await self._runStorm(text, opts, cmdr, suppress_logging)
        if num is not None:
            nodes = [m for m in mesgs if m[0] == 'node']
            if len(nodes) != num:
                raise AssertionError(f'Expected {num} nodes, got {len(nodes)}')

        return mesgs

    async def eval(self, text, opts=None, num=None, cmdr=False):
        '''
        A helper for executing a storm command and getting a list of packed nodes.

        Args:
            text (str): Storm command to execute.
            opts (dict): Opt to pass to the cortex during execution.
            num (int): Number of nodes to expect in the output query. Checks that with an assert statement.
            cmdr (bool): If True, executes the line via the Cmdr CLI and will send output to outp.

        Notes:
            The opts dictionary will not be used if cmdr=True.

        Returns:
            list: A list of packed nodes.
        '''
        mesgs = await self._runStorm(text, opts, cmdr)
        for mesg in mesgs:
            if mesg[0] == 'err': # pragma: no cover
                raise AssertionError(f'Query { {text} } got err: {mesg!r}')

        nodes = [m[1] for m in mesgs if m[0] == 'node']

        if num is not None:
            if len(nodes) != num: # pragma: no cover
                raise AssertionError(f'Query { {text} } expected {num} nodes, got {len(nodes)}')

        return nodes

    async def _onCmdrCoreFini(self):
        await self.cmdr.fini()
        # await self.core.fini()
        # If self.acm is set, acm.__aexit should handle the self.core fini.
        if self.acm:
            await self.acm.__aexit__(None, None, None)

async def getTempCoreProx(mods=None):
    '''
    Get a Telepath Proxt to a Cortex instance which is backed by a temporary Cortex.

    Args:
        mods (list): A list of additional CoreModules to load in the Cortex.

    Notes:
        The Proxy returned by this should be fini()'d to tear down the temporary Cortex.

    Returns:
        s_telepath.Proxy
    '''
    acm = genTempCoreProxy(mods)
    prox = await acm.__aenter__()
    # Use object.__setattr__ to hulk smash and avoid proxy getattr magick
    object.__setattr__(prox, '_acm', acm)

    async def onfini():
        await prox._acm.__aexit__(None, None, None)
    prox.onfini(onfini)
    return prox

async def getTempCoreCmdr(mods=None, outp=None):
    '''
    Get a CmdrCore instance which is backed by a temporary Cortex.

    Args:
        mods (list): A list of additional CoreModules to load in the Cortex.
        outp: A output helper.  Will be used for the Cmdr instance.

    Notes:
        The CmdrCore returned by this should be fini()'d to tear down the temporary Cortex.

    Returns:
        CmdrCore: A CmdrCore instance.
    '''
    acm = genTempCoreProxy(mods)
    prox = await acm.__aenter__()
    cmdrcore = await CmdrCore.anit(prox, outp=outp)
    cmdrcore.acm = acm
    return cmdrcore

async def getTempCoreCmdrStormsvc(svcname, svcctor, svcconf=None, outp=None):
    '''
    Get a proxy to a Storm service and a CmdrCore instance backed by a temporary Cortex with the service added.

    Args:
        svcname (str): Storm service name
        svcctor: Storm service constructor (e.g. Example.anit)
        svcconf: Optional conf for the Storm service
        outp: A output helper for the Cmdr instance

    Notes:
        Both the CmdrCore and Storm service proxy should be fini()'d for proper teardown

    Returns:
        (CmdrCore, Proxy): A CmdrCore instance and proxy to the Storm service
    '''
    cmdrcore = await getTempCoreCmdr(outp=outp)

    acm = genTempStormsvcProxy(cmdrcore, svcname, svcctor, svcconf)
    svcprox = await acm.__aenter__()
    # Use object.__setattr__ to hulk smash and avoid proxy getattr magick
    object.__setattr__(svcprox, '_acm', acm)

    async def onfini():
        await svcprox._acm.__aexit__(None, None, None)
    svcprox.onfini(onfini)

    return cmdrcore, svcprox
