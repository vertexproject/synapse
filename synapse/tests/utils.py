'''
This contains the core test helper code used in Synapse.

This gives the opportunity for third-party users of Synapse to test their
code using some of the same of the same helpers used to test Synapse.

The core class, synapse.tests.utils.SynTest is a subclass of unittest.TestCase,
with several wrapper functions to allow for easier calls to assert* functions,
with less typing.  There are also Synapse specific helpers, to load Cortexes and
whole both multi-component environments into memory.

Since SynTest is built from unittest.TestCase, the use of SynTest is
compatible with the unittest, nose and pytest frameworks.  This does not lock
users into a particular test framework; while at the same time allowing base
use to be invoked via the built-in Unittest library, with one important exception:
due to an unfortunate design approach, you cannot use the unittest module command
line to run a *single* async unit test.  pytest works fine though.

'''
import io
import os
import sys
import copy
import types
import shutil
import asyncio
import inspect
import logging
import tempfile
import unittest
import threading
import contextlib
import collections

import unittest.mock as mock

import aiohttp

from prompt_toolkit.formatted_text import FormattedText

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.cryotank as s_cryotank
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.cmdr as s_cmdr
import synapse.lib.hive as s_hive
import synapse.lib.const as s_const
import synapse.lib.storm as s_storm
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.output as s_output
import synapse.lib.lmdbslab as s_slab
import synapse.lib.thishost as s_thishost
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

# Default LMDB map size for tests
TEST_MAP_SIZE = s_const.gibibyte

async def alist(coro):
    return [x async for x in coro]

class LibTst(s_stormtypes.Lib):

    def addLibFuncs(self):
        self.locls.update({
            'beep': self.beep,
        })

    async def beep(self, valu):
        '''
        Example storm func
        '''
        ret = f'A {valu} beep!'
        return ret

class TestType(s_types.Type):

    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)

    def _normPyStr(self, valu):
        return valu.lower(), {}

    def indx(self, norm):
        # make this purposely fragile...
        return norm.encode('utf8')

class ThreeType(s_types.Type):

    def norm(self, valu):
        return 3, {'subs': {'three': 3}}

    def repr(self, valu):
        return '3'

    def indx(self, norm):
        return '3'.encode('utf8')

class TestSubType(s_types.Type):

    def norm(self, valu):
        valu = int(valu)
        return valu, {'subs': {'isbig': valu >= 1000}}

    def repr(self, norm):
        return str(norm)

    def indx(self, norm):
        return norm.to_bytes(4, 'big')

testmodel = {

    'ctors': (
        ('test:sub', 'synapse.tests.utils.TestSubType', {}, {}),
        ('test:type', 'synapse.tests.utils.TestType', {}, {}),
        ('test:threetype', 'synapse.tests.utils.ThreeType', {}, {}),
    ),

    'types': (
        ('test:type10', ('test:type', {'foo': 10}), {
            'doc': 'A fake type.'}),

        ('test:lower', ('str', {'lower': True}), {}),

        ('test:time', ('time', {}), {}),

        ('test:ival', ('ival', {}), {}),

        ('test:int', ('int', {}), {}),
        ('test:str', ('str', {}), {}),
        ('test:migr', ('str', {}), {}),
        ('test:auto', ('str', {}), {}),
        ('test:edge', ('edge', {}), {}),
        ('test:guid', ('guid', {}), {}),

        ('test:arrayprop', ('guid', {}), {}),

        ('test:comp', ('comp', {'fields': (
            ('hehe', 'test:int'),
            ('haha', 'test:lower'))
        }), {'doc': 'A fake comp type.'}),
        ('test:complexcomp', ('comp', {'fields': (
            ('foo', 'test:int'),
            ('bar', ('str', {'lower': True}),),
        )}), {'doc': 'A complex comp type.'}),
        ('test:hexa', ('hex', {}), {'doc': 'anysize test hex type'}),
        ('test:hex4', ('hex', {'size': 4}), {'doc': 'size 4 test hex type'}),

        ('test:pivtarg', ('str', {}), {}),
        ('test:pivcomp', ('comp', {'fields': (('targ', 'test:pivtarg'), ('lulz', 'test:str'))}), {}),
        ('test:haspivcomp', ('int', {}), {}),

        ('test:cycle0', ('str', {}), {}),
        ('test:cycle1', ('str', {}), {}),

        ('test:ndef', ('ndef', {}), {}),
        ('test:runt', ('str', {'lower': True, 'strip': True}), {'doc': 'A Test runt node'}),

    ),

    'univs': (
        ('test:univ', ('int', {'min': -1, 'max': 10}), {'doc': 'A test universal property.'}),
        ('univarray', ('array', {'type': 'int'}), {'doc': 'A test array universal property.'}),
    ),

    'forms': (

        ('test:arrayprop', {}, (
            ('ints', ('array', {'type': 'test:int'}), {}),
        )),
        ('test:type10', {}, (

            ('intprop', ('int', {'min': 20, 'max': 30}), {
                'defval': 20}),

            ('strprop', ('str', {'lower': 1}), {
                'defval': 'asdf'}),

            ('guidprop', ('guid', {'lower': 1}), {
                'defval': '*'}),

            ('locprop', ('loc', {}), {
                'defval': '??'}),
        )),

        ('test:cycle0', {}, (
            ('cycle1', ('test:cycle1', {}), {}),
        )),

        ('test:cycle1', {}, (
            ('cycle0', ('test:cycle0', {}), {}),
        )),

        ('test:type', {}, ()),

        ('test:comp', {}, (
            ('hehe', ('test:int', {}), {'ro': 1}),
            ('haha', ('test:lower', {}), {'ro': 1}),
        )),

        ('test:complexcomp', {}, (
            ('foo', ('test:int', {}), {'ro': 1}),
            ('bar', ('str', {'lower': 1}), {'ro': 1})
        )),

        ('test:int', {}, (
            ('loc', ('loc', {}), {}),
        )),

        ('test:edge', {}, (
            ('n1', ('ndef', {}), {'ro': 1}),
            ('n1:form', ('str', {}), {'ro': 1}),
            ('n2', ('ndef', {}), {'ro': 1}),
            ('n2:form', ('str', {}), {'ro': 1}),
        )),

        ('test:guid', {}, (
            ('size', ('test:int', {}), {}),
            ('tick', ('test:time', {}), {}),
            ('posneg', ('test:sub', {}), {}),
            ('posneg:isbig', ('bool', {}), {}),
        )),

        ('test:str', {}, (
            ('bar', ('ndef', {}), {}),
            ('baz', ('nodeprop', {}), {}),
            ('tick', ('test:time', {}), {}),
            ('hehe', ('str', {}), {}),
        )),

        ('test:migr', {}, (
            ('bar', ('ndef', {}), {}),
            ('baz', ('nodeprop', {}), {}),
            ('tick', ('test:time', {}), {}),
        )),

        ('test:threetype', {}, (
            ('three', ('int', {}), {}),
        )),
        ('test:auto', {}, ()),
        ('test:hexa', {}, ()),
        ('test:hex4', {}, ()),
        ('test:ival', {}, (
            ('interval', ('ival', {}), {}),
        )),

        ('test:pivtarg', {}, (
            ('name', ('str', {}), {}),
        )),

        ('test:pivcomp', {}, (
            ('targ', ('test:pivtarg', {}), {}),
            ('lulz', ('test:str', {}), {}),
            ('tick', ('time', {}), {}),
            ('size', ('test:int', {}), {}),
            ('width', ('test:int', {}), {}),
        )),

        ('test:haspivcomp', {}, (
            ('have', ('test:pivcomp', {}), {}),
        )),

        ('test:ndef', {}, (
            ('form', ('str', {}), {'ro': 1}),
        )),

        ('test:runt', {'runt': True}, (
            ('tick', ('time', {}), {'ro': True}),
            ('lulz', ('str', {}), {}),
            ('newp', ('str', {}), {'doc': 'A stray property we never use in nodes.'}),
        )),
    ),
}

class TestCmd(s_storm.Cmd):
    '''
    A test command
    '''

    name = 'testcmd'

    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        return pars

    async def execStormCmd(self, runt, genr):
        async for node, path in genr:
            yield node, path

class TestEchoCmd(s_storm.Cmd):
    '''A command to echo a using getStormEval'''
    name = 'testechocmd'

    def getArgParser(self):
        pars = s_storm.Cmd.getArgParser(self)
        pars.add_argument('valu', help='valu to echo')
        return pars

    async def execStormCmd(self, runt, genr):
        func = self.getStormEval(runt, self.opts.valu)

        async for node, path in genr:
            ret = func(path)
            await runt.snap.printf(f'Echo: [{ret}]')
            yield node, path

class TestModule(s_module.CoreModule):
    testguid = '8f1401de15918358d5247e21ca29a814'

    async def initCoreModule(self):

        self.core.setFeedFunc('com.test.record', self.addTestRecords)

        async with await self.core.snap() as snap:
            await snap.addNode('meta:source', self.testguid, {'name': 'test'})

        self.core.addStormLib(('test',), LibTst)

        self.healthy = True
        self.core.addHealthFunc(self._testModHealth)

        self._runtsByBuid = {}
        self._runtsByPropValu = collections.defaultdict(list)
        await self._initTestRunts()

        # Add runt lift helpers
        for form in ('test:runt',):
            form = self.model.form(form)
            self.core.addRuntLift(form.full, self._testRuntLift)
            for name, prop in form.props.items():
                pfull = prop.full
                self.core.addRuntLift(pfull, self._testRuntLift)
        self.core.addRuntPropSet('test:runt:lulz', self._testRuntPropSetLulz)
        self.core.addRuntPropDel('test:runt:lulz', self._testRuntPropDelLulz)

    async def _testModHealth(self, health):
        if self.healthy:
            health.update(self.getModName(), 'nominal',
                          'Test module is healthy', data={'beep': 0})
        else:
            health.update(self.getModName(), 'failed',
                          'Test module is unhealthy', data={'beep': 1})

    async def addTestRecords(self, snap, items):
        for name in items:
            await snap.addNode('test:str', name)

    async def _testRuntLift(self, full, valu=None, cmpr=None):
        # runt lift helpers must decide what comparators they support
        if cmpr is not None and cmpr != '=':
            raise s_exc.BadCmprValu(mesg='Test runts do not support cmpr which is not equality',
                                    cmpr=cmpr)

        # Runt lift helpers must support their own normalization for data retrieval
        if valu is not None:
            prop = self.model.prop(full)
            valu, _ = prop.type.norm(valu)

        # runt lift helpers must then yield buid/rows pairs for Node object creation.
        if valu is None:
            buids = self._runtsByPropValu.get(full, ())
        else:
            buids = self._runtsByPropValu.get((full, valu), ())

        rowsets = [(buid, self._runtsByBuid.get(buid, ())) for buid in buids]
        for buid, rows in rowsets:
            yield buid, rows

    async def _testRuntPropSetLulz(self, node, prop, valu):
        curv = node.get(prop.name)
        valu, _ = prop.type.norm(valu)
        if curv == valu:
            return False
        if not valu.endswith('.sys'):
            raise s_exc.BadPropValu(mesg='test:runt:lulz must end with ".sys"',
                                    valu=valu, name=prop.full)
        node.props[prop.name] = valu
        # In this test helper, we do NOT persist the change to our in-memory
        # storage of row data, so a re-lift of the node would not reflect the
        # change that a user made here.
        return True

    async def _testRuntPropDelLulz(self, node, prop,):
        curv = node.props.pop(prop.name, s_common.novalu)
        if curv is s_common.novalu:
            return False

        # In this test helper, we do NOT persist the change to our in-memory
        # storage of row data, so a re-lift of the node would not reflect the
        # change that a user made here.
        return True

    async def _initTestRunts(self):
        modl = self.core.model
        fnme = 'test:runt'
        form = modl.form(fnme)
        now = s_common.now()
        data = [(' BEEP ', {'tick': modl.type('time').norm('2001')[0], 'lulz': 'beep.sys', '.created': now}),
                ('boop', {'tick': modl.type('time').norm('2010')[0], '.created': now}),
                ('blah', {'tick': modl.type('time').norm('2010')[0], 'lulz': 'blah.sys'}),
                ('woah', {}),
                ]
        for pprop, propd in data:
            props = {}
            pnorm, _ = form.type.norm(pprop)

            for k, v in propd.items():
                prop = form.props.get(k)
                if prop:
                    norm, _ = prop.type.norm(v)
                    props[k] = norm

            props.setdefault('.created', s_common.now())

            rows = [('*' + fnme, pnorm)]
            for k, v in props.items():
                rows.append((k, v))

            buid = s_common.buid((fnme, pnorm))
            self._runtsByBuid[buid] = rows

            # Allow for indirect lookup to a set of buids
            self._runtsByPropValu[fnme].append(buid)
            self._runtsByPropValu[(fnme, pnorm)].append(buid)
            for k, propvalu in props.items():
                prop = fnme + ':' + k
                if k.startswith('.'):
                    prop = fnme + k
                self._runtsByPropValu[prop].append(buid)
                if modl.prop(prop).type.indx(propvalu):
                    # Can the secondary property be indexed for lift?
                    self._runtsByPropValu[(prop, propvalu)].append(buid)

    def getModelDefs(self):
        return (
            ('test', testmodel),
        )

    def getStormCmds(self):
        return (TestCmd,
                TestEchoCmd,
                )

class TstEnv:

    def __init__(self):
        self.items = {}
        self.tofini = []

    def __getattr__(self, prop):
        item = self.items.get(prop)
        if item is None:
            raise AttributeError(prop)
        return item

    def __enter__(self):
        return self

    def __exit__(self, cls, exc, tb):
        self.fini()

    def add(self, name, item, fini=False):
        self.items[name] = item
        if fini:
            self.tofini.append(item)

    def fini(self):
        for bus in self.tofini:
            bus.fini()

class TstOutPut(s_output.OutPutStr):

    def expect(self, substr, throw=True):
        '''
        Check if a string is present in the messages captured by the OutPutStr object.

        Args:
            substr (str): String to check for the existence of.
            throw (bool): If True, a missing substr results in a Exception being thrown.

        Returns:
            bool: True if the string is present; False if the string is not present and throw is False.
        '''
        outs = str(self)
        if outs.find(substr) == -1:
            if throw:
                raise Exception('TestOutPut.expect(%s) not in %s' % (substr, outs))
            return False
        return True

    def clear(self):
        self.mesgs.clear()

class TestSteps:
    '''
    A class to assist with interlocking for multi-thread tests.

    Args:
        names (list): A list of names of tests steps as strings.
    '''
    def __init__(self, names):
        self.steps = {}
        self.names = names

        for name in names:
            self.steps[name] = threading.Event()

    def done(self, step):
        '''
        Mark the step name as complete.

        Args:
            step (str): The step name to mark complete
        '''
        self.steps[step].set()

    def wait(self, step, timeout=None):
        '''
        Wait (up to timeout seconds) for a step to complete.

        Args:
            step (str): The step name to wait for.
            timeout (int): The timeout in seconds (or None)

        Returns:
            bool: True if the step is completed within the wait timeout.

        Raises:
            StepTimeout: on wait timeout
        '''
        if not self.steps[step].wait(timeout=timeout):
            raise s_exc.StepTimeout(mesg='timeout waiting for step', step=step)
        return True

    def step(self, done, wait, timeout=None):
        '''
        Complete a step and wait for another.

        Args:
            done (str): The step name to complete.
            wait (str): The step name to wait for.
            timeout (int): The wait timeout.
        '''
        self.done(done)
        return self.wait(wait, timeout=timeout)

    def waitall(self, timeout=None):
        '''
        Wait for all the steps to be complete.

        Args:
            timeout (int): The wait timeout (per step).

        Returns:
            bool: True when all steps have completed within the alloted time.

        Raises:
            StepTimeout: When the first step fails to complete in the given time.
        '''
        for name in self.names:
            self.wait(name, timeout=timeout)
        return True

    def clear(self, step):
        '''
        Clear the event for a given step.

        Args:
            step (str): The name of the step.
        '''
        self.steps[step].clear()

class CmdGenerator:

    def __init__(self, cmds):
        self.cmds = collections.deque(cmds)

    def addCmd(self, cmd):
        '''
        Add a command to the end of the list of commands returned by the CmdGenerator.

        Args:
            cmd (str): Command to add to the list of commands to return.
        '''
        self.cmds.append(cmd)

    def __call__(self, *args, **kwargs):
        return self._corocall(*args, **kwargs)

    async def _corocall(self, *args, **kwargs):

        if not self.cmds:
            raise Exception('No further actions.')

        retn = self.cmds.popleft()

        if isinstance(retn, (Exception, KeyboardInterrupt)):
            raise retn

        return retn

class StreamEvent(io.StringIO, threading.Event):
    '''
    A combination of a io.StringIO object and a threading.Event object.
    '''
    def __init__(self, *args, **kwargs):
        io.StringIO.__init__(self, *args, **kwargs)
        threading.Event.__init__(self)
        self.mesg = ''

    def setMesg(self, mesg):
        '''
        Clear the internal event and set a new message that is used to set the event.

        Args:
            mesg (str): The string to monitor for.

        Returns:
            None
        '''
        self.mesg = mesg
        self.clear()

    def write(self, s):
        io.StringIO.write(self, s)
        if self.mesg and self.mesg in s:
            self.set()

class AsyncStreamEvent(io.StringIO, asyncio.Event):
    '''
    A combination of a io.StringIO object and an asyncio.Event object.
    '''
    def __init__(self, *args, **kwargs):
        io.StringIO.__init__(self, *args, **kwargs)
        asyncio.Event.__init__(self, loop=asyncio.get_running_loop())
        self.mesg = ''

    def setMesg(self, mesg):
        '''
        Clear the internal event and set a new message that is used to set the event.

        Args:
            mesg (str): The string to monitor for.

        Returns:
            None
        '''
        self.mesg = mesg
        self.clear()

    def write(self, s):
        io.StringIO.write(self, s)
        if self.mesg and self.mesg in s:
            self.set()

    async def wait(self, timeout=None):
        if timeout is None:
            return await asyncio.Event.wait(self)
        return await s_coro.event_wait(self, timeout=timeout)

class SynTest(unittest.TestCase):
    '''
    Mark all async test methods as s_glob.synchelp decorated.

    Note:
        This precludes running a single unit test via path using the unittest module.
    '''
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        for s in dir(self):
            attr = getattr(self, s, None)
            # If s is an instance method and starts with 'test_', synchelp wrap it
            if inspect.iscoroutinefunction(attr) and s.startswith('test_') and inspect.ismethod(attr):
                setattr(self, s, s_glob.synchelp(attr))

    def checkNode(self, node, expected):
        ex_ndef, ex_props = expected
        self.eq(node.ndef, ex_ndef)
        [self.eq(node.get(k), v, msg=f'Prop {k} does not match') for (k, v) in ex_props.items()]

        diff = {prop for prop in (set(node.props) - set(ex_props)) if not prop.startswith('.')}
        if diff:
            logger.warning('form(%s): untested properties: %s', node.form.name, diff)

    def worker(func, *args, **kwargs):
        '''
        Fire a worker thread to run the given func(*args,**kwargs)
        '''
        def work():
            return func(*args, **kwargs)

        thr = threading.Thread(target=work)
        thr.start()
        return thr

    def printed(self, msgs, text):
        # a helper for testing storm print message output
        for mesg in msgs:
            if mesg[0] == 'print':
                if mesg[1].get('mesg') == text:
                    return

        raise Exception('print output not found: %r' % (text,))

    def skip(self, mesg):
        raise unittest.SkipTest(mesg)

    @contextlib.contextmanager
    def getRegrDir(self, *path):

        regr = os.getenv('SYN_REGRESSION_REPO')
        if regr is None: # pragma: no cover
            raise unittest.SkipTest('SYN_REGRESSION_REPO is not set')

        regr = s_common.genpath(regr)

        if not os.path.isdir(regr): # pragma: no cover
            raise Exception('SYN_REGREGSSION_REPO is not a dir')

        dirn = os.path.join(regr, *path)

        with self.getTestDir(copyfrom=dirn) as regrdir:
            yield regrdir

    @contextlib.asynccontextmanager
    async def getRegrCore(self, vers):
        with self.getRegrDir('cortexes', vers) as dirn:
            async with await s_cortex.Cortex.anit(dirn) as core:
                yield core

    def skipIfNoInternet(self):  # pragma: no cover
        '''
        Allow skipping a test if SYN_TEST_SKIP_INTERNET envar is set.

        Raises:
            unittest.SkipTest if SYN_TEST_SKIP_INTERNET envar is set to a integer greater than 1.
        '''
        if bool(int(os.getenv('SYN_TEST_SKIP_INTERNET', 0))):
            raise unittest.SkipTest('SYN_TEST_SKIP_INTERNET envar set')

    def skipLongTest(self):  # pragma: no cover
        '''
        Allow skipping a test if SYN_TEST_SKIP_LONG envar is set.

        Raises:
            unittest.SkipTest if SYN_TEST_SKIP_LONG envar is set to a integer greater than 1.
        '''
        if bool(int(os.getenv('SYN_TEST_SKIP_LONG', 0))):
            raise unittest.SkipTest('SYN_TEST_SKIP_LONG envar set')

    def getTestOutp(self):
        '''
        Get a Output instance with a expects() function.

        Returns:
            TstOutPut: A TstOutPut instance.
        '''
        return TstOutPut()

    def thisHostMust(self, **props):  # pragma: no cover
        '''
        Requires a host having a specific property.

        Args:
            **props:

        Raises:
            unittest.SkipTest if the required property is missing.
        '''
        for k, v in props.items():
            if s_thishost.get(k) != v:
                raise unittest.SkipTest('skip thishost: %s!=%r' % (k, v))

    def thisHostMustNot(self, **props):  # pragma: no cover
        '''
        Requires a host to not have a specific property.

        Args:
            **props:

        Raises:
            unittest.SkipTest if the required property is missing.
        '''

        for k, v in props.items():
            if s_thishost.get(k) == v:
                raise unittest.SkipTest('skip thishost: %s==%r' % (k, v))

    @contextlib.asynccontextmanager
    async def getTestAxon(self, dirn=None):
        '''
        Get a test Axon as an async context manager.

        Returns:
            s_axon.Axon: A Axon object.
        '''
        if dirn is not None:
            async with await s_axon.Axon.anit(dirn) as axon:
                yield axon

            return

        with self.getTestDir() as dirn:
            async with await s_axon.Axon.anit(dirn) as axon:
                yield axon

    @contextlib.contextmanager
    def withTestCmdr(self, cmdg):

        getItemCmdr = s_cmdr.getItemCmdr

        async def getTestCmdr(*a, **k):
            cli = await getItemCmdr(*a, **k)
            cli.prompt = cmdg
            return cli

        with mock.patch('synapse.lib.cmdr.getItemCmdr', getTestCmdr):
            yield

    @contextlib.contextmanager
    def withCliPromptMockExtendOutp(self, outp):
        '''
        Context manager to mock our use of Prompt Toolkit's print_formatted_text function and
        extend the lines to an an output object.

        Args:
            outp (TstOutPut): The outp to extend.

        Notes:
            This extends the outp with the lines AFTER the context manager has exited.

        Returns:
            mock.MagicMock: Yields a mock.MagicMock object.
        '''
        with self.withCliPromptMock() as patch:
            yield patch
        self.extendOutpFromPatch(outp, patch)

    @contextlib.contextmanager
    def withCliPromptMock(self):
        '''
        Context manager to mock our use of Prompt Toolkit's print_formatted_text function.

        Returns:
            mock.MagicMock: Yields a mock.MagikMock object.
        '''
        with mock.patch('synapse.lib.cli.print_formatted_text',
                        mock.MagicMock(return_value=None)) as patch:  # type: mock.MagicMock
            yield patch

    def getMagicPromptLines(self, patch):
        '''
        Get the text lines from a MagicMock object from withCliPromptMock.

        Args:
            patch (mock.MagicMock): The MagicMock object from withCliPromptMock.

        Returns:
            list: A list of lines.
        '''
        self.true(patch.called, 'Assert prompt was called')
        lines = []
        for args in patch.call_args_list:
            arg = args[0][0]
            if isinstance(arg, str):
                lines.append(arg)
                continue
            if isinstance(arg, FormattedText):
                color, text = arg[0]
                lines.append(text)
                continue
            raise ValueError(f'Unknown arg: {type(arg)}/{arg}')
        return lines

    def getMagicPromptColors(self, patch):
        '''
        Get the colored lines from a MagicMock object from withCliPromptMock.

        Args:
            patch (mock.MagicMock): The MagicMock object from withCliPromptMock.

        Returns:
            list: A list of tuples, containing color and line data.
        '''
        self.true(patch.called, 'Assert prompt was called')
        lines = []
        for args in patch.call_args_list:
            arg = args[0][0]
            if isinstance(arg, str):
                continue
            if isinstance(arg, FormattedText):
                color, text = arg[0]
                lines.append((color, text))
                continue
            raise ValueError(f'Unknown arg: {type(arg)}/{arg}')
        return lines

    def extendOutpFromPatch(self, outp, patch):
        '''
        Extend an Outp with lines from a magicMock object from withCliPromptMock.

        Args:
            outp (TstOutPut): The outp to extend.
            patch (mock.MagicMock): The patch object.

        Returns:
            None: Returns none.
        '''
        lines = self.getMagicPromptLines(patch)
        [outp.printf(line) for line in lines]

    @contextlib.asynccontextmanager
    async def getTestReadWriteCores(self, conf=None, dirn=None):
        '''
        Get a read/write core pair.

        Notes:
            By default, this returns the same cortex.  It is expected that
            a test which needs two distinct Cortexes implements the bridge
            themselves.

        Returns:
            (s_cortex.Cortex, s_cortex.Cortex): A tuple of Cortex objects.
        '''
        async with self.getTestCore(conf=conf, dirn=dirn) as core:
            yield core, core

    @contextlib.asynccontextmanager
    async def getTestCore(self, conf=None, dirn=None):
        '''
        Get a simple test Cortex as an async context manager.

        Returns:
            s_cortex.Cortex: A Cortex object.
        '''
        if conf is None:
            conf = {'layer:lmdb:map_async': True}

        conf = copy.deepcopy(conf)

        mods = conf.get('modules')

        if mods is None:
            mods = []
            conf['modules'] = mods

        mods.append(('synapse.tests.utils.TestModule', {'key': 'valu'}))

        if dirn is not None:

            async with await s_cortex.Cortex.anit(dirn, conf=conf) as core:
                yield core

            return

        with self.getTestDir() as dirn:
            async with await s_cortex.Cortex.anit(dirn, conf=conf) as core:
                yield core

    @contextlib.asynccontextmanager
    async def getTestCoreAndProxy(self, conf=None, dirn=None):
        '''
        Get a test Cortex and the Telepath Proxy to it.

        Returns:
            (s_cortex.Cortex, s_cortex.CoreApi): The Cortex and a Proxy representing a CoreApi object.
        '''
        async with self.getTestCore(conf=conf, dirn=dirn) as core:
            core.conf['storm:log'] = True
            async with core.getLocalProxy() as prox:
                yield core, prox

    @contextlib.asynccontextmanager
    async def getTestCryo(self, dirn=None):
        '''
        Get a simple test Cryocell as an async context manager.

        Returns:
            s_cryotank.CryoCell: Test cryocell.
        '''
        if dirn is not None:
            async with await s_cryotank.CryoCell.anit(dirn) as cryo:
                yield cryo

            return

        with self.getTestDir() as dirn:
            async with await s_cryotank.CryoCell.anit(dirn) as cryo:
                yield cryo

    @contextlib.asynccontextmanager
    async def getTestCryoAndProxy(self, dirn=None):
        '''
        Get a test Cryocell and the Telepath Proxy to it.

        Returns:
            (s_cryotank: CryoCell, s_cryotank.CryoApi): The CryoCell and a Proxy representing a CryoApi object.
        '''
        async with self.getTestCryo(dirn=dirn) as cryo:
            async with cryo.getLocalProxy() as prox:
                yield cryo, prox

    @contextlib.asynccontextmanager
    async def getTestDmon(self):
        with self.getTestDir(mirror='certdir') as certdir:
            async with await s_daemon.Daemon.anit(certdir=certdir) as dmon:
                await dmon.listen('tcp://127.0.0.1:0/')
                with mock.patch('synapse.lib.certdir.defdir', certdir):
                    yield dmon

    def getTestUrl(self, dmon, name, **opts):

        host, port = dmon.addr
        netloc = '%s:%s' % (host, port)

        user = opts.get('user')
        passwd = opts.get('passwd')

        if user is not None and passwd is not None:
            netloc = '%s:%s@%s' % (user, passwd, netloc)

        return 'tcp://%s/%s' % (netloc, name)

    def getTestProxy(self, dmon, name, **kwargs):
        host, port = dmon.addr
        kwargs.update({'host': host, 'port': port})
        return s_telepath.openurl(f'tcp:///{name}', **kwargs)

    async def agetTestProxy(self, dmon, name, **kwargs):
        host, port = dmon.addr
        kwargs.update({'host': host, 'port': port})
        return await s_telepath.openurl(f'tcp:///{name}', **kwargs)

    @contextlib.contextmanager
    def getTestDir(self, mirror=None, copyfrom=None, chdir=False):
        '''
        Get a temporary directory for test purposes.
        This destroys the directory afterwards.

        Args:
            mirror (str): A directory to mirror into the test directory.

        Notes:
            The mirror argument is normally used to mirror test directory
            under ``synapse/tests/files``.  This is accomplised by passing in
            the name of the directory (such as ``testcore``) as the mirror
            argument.

            If the ``mirror`` argument is an absolute directory, that directory
            will be copied to the test directory.

        Returns:
            str: The path to a temporary directory.
        '''
        curd = os.getcwd()
        tempdir = tempfile.mkdtemp()

        try:

            dstpath = tempdir

            if mirror is not None:
                srcpath = self.getTestFilePath(mirror)
                dstpath = os.path.join(dstpath, 'mirror')
                shutil.copytree(srcpath, dstpath)

            elif copyfrom is not None:
                dstpath = os.path.join(dstpath, 'mirror')
                shutil.copytree(copyfrom, dstpath)

            if chdir:
                os.chdir(dstpath)

            yield dstpath

        finally:

            if chdir:
                os.chdir(curd)

            shutil.rmtree(tempdir, ignore_errors=True)

    def getTestFilePath(self, *names):
        import synapse.tests.common
        path = os.path.dirname(synapse.tests.common.__file__)
        return os.path.join(path, 'files', *names)

    @contextlib.contextmanager
    def getLoggerStream(self, logname, mesg=''):
        '''
        Get a logger and attach a io.StringIO object to the logger to capture log messages.

        Args:
            logname (str): Name of the logger to get.
            mesg (str): A string which, if provided, sets the StreamEvent event if a message
            containing the string is written to the log.

        Examples:
            Do an action and get the stream of log messages to check against::

                with self.getLoggerStream('synapse.foo.bar') as stream:
                    # Do something that triggers a log message
                    doSomething()

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

            Do an action and wait for a specific log message to be written::

                with self.getLoggerStream('synapse.foo.bar', 'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    doSomething()
                    stream.wait(timeout=10)  # Wait for the mesg to be written to the stream

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

            You can also reset the message and wait for another message to occur::

                with self.getLoggerStream('synapse.foo.bar', 'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    doSomething()
                    stream.wait(timeout=10)
                    stream.setMesg('yo dawg')  # This will now wait for the 'yo dawg' string to be written.
                    stream.wait(timeout=10)

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

        Notes:
            This **only** captures logs for the current process.

        Yields:
            StreamEvent: A StreamEvent object
        '''
        stream = StreamEvent()
        stream.setMesg(mesg)
        handler = logging.StreamHandler(stream)
        slogger = logging.getLogger(logname)
        slogger.addHandler(handler)
        try:
            yield stream
        except Exception:  # pragma: no cover
            raise
        finally:
            slogger.removeHandler(handler)

    @contextlib.contextmanager
    def getAsyncLoggerStream(self, logname, mesg=''):
        '''
        Async version of getLoggerStream.

        Args:
            logname (str): Name of the logger to get.
            mesg (str): A string which, if provided, sets the StreamEvent event if a message
            containing the string is written to the log.

        Notes:
            The event object mixed in for the AsyncStreamEvent is a asyncio.Event object.
            This requires the user to await the Event specific calls as neccesary.

        Examples:
            Do an action and wait for a specific log message to be written::

                with self.getAsyncLoggerStream('synapse.foo.bar',
                                               'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    await doSomething()
                    # Wait for the mesg to be written to the stream
                    await stream.wait(timeout=10)

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

        Returns:
            AsyncStreamEvent: An AsyncStreamEvent object.
        '''
        stream = AsyncStreamEvent()
        stream.setMesg(mesg)
        handler = logging.StreamHandler(stream)
        slogger = logging.getLogger(logname)
        slogger.addHandler(handler)
        try:
            yield stream
        except Exception:  # pragma: no cover
            raise
        finally:
            slogger.removeHandler(handler)

    @contextlib.asynccontextmanager
    async def getHttpSess(self, auth=None, port=None):
        '''
        Get an aiohttp ClientSession with a CookieJar.

        Args:
            auth (str, str): A tuple of username and password information for http auth.
            port (int): Port number to connect to.

        Notes:
            If auth and port are provided, the session will login to a Synapse cell
            hosted at localhost:port.

        Returns:
            aiohttp.ClientSession: An aiohttp.ClientSession object.
        '''

        jar = aiohttp.CookieJar(unsafe=True)
        conn = aiohttp.TCPConnector(ssl=False)

        async with aiohttp.ClientSession(cookie_jar=jar, connector=conn) as sess:

            if auth is not None:

                if port is None: # pragma: no cover
                    raise Exception('getHttpSess requires port for auth')

                user, passwd = auth
                async with sess.post(f'https://localhost:{port}/api/v1/login',
                                     json={'user': user, 'passwd': passwd}) as resp:
                    retn = await resp.json()
                    self.eq('ok', retn.get('status'))
                    self.eq(user, retn['result']['name'])

            yield sess

    @contextlib.contextmanager
    def setTstEnvars(self, **props):
        '''
        Set Environmental variables for the purposes of running a specific test.

        Args:
            **props: A kwarg list of envars to set. The values set are run
            through str() to ensure we're setting strings.

        Examples:
            Run a test while a envar is set::

                with self.setEnvars(magic='haha') as nop:
                    ret = dostuff()
                    self.true(ret)

        Notes:
            This helper explicitly sets and unsets values in os.environ, as
            os.putenv does not automatically updates the os.environ object.

        Yields:
            None. This context manager yields None. Upon exiting, envars are
            either removed from os.environ or reset to their previous values.
        '''
        old_data = {}
        pop_data = set()
        for key, valu in props.items():
            v = str(valu)
            oldv = os.environ.get(key, None)
            if oldv:
                if oldv == v:
                    continue
                else:
                    old_data[key] = oldv
                    os.environ[key] = v
            else:
                pop_data.add(key)
                os.environ[key] = v

        # This context manager is a nop
        try:
            yield None
        except Exception:  # pragma: no cover
            raise
        # Clean up any new envars we set and any old envars we need to reset.
        finally:
            for key in pop_data:
                del os.environ[key]
            for key, valu in old_data.items():
                os.environ[key] = valu

    async def execToolMain(self, func, argv):
        outp = self.getTestOutp()
        def execmain():
            return func(argv, outp=outp)
        retn = await s_coro.executor(execmain)
        return retn, outp

    @contextlib.contextmanager
    def redirectStdin(self, new_stdin):
        '''
        Temporary replace stdin.

        Args:
            new_stdin(file-like object):  file-like object.

        Examples:
            inp = io.StringIO('stdin stuff\nanother line\n')
            with self.redirectStdin(inp):
                main()

            Here's a way to use this for code that's expecting the stdin buffer to have bytes.
            inp = Mock()
            inp.buffer = io.BytesIO(b'input data')
            with self.redirectStdin(inp):
                main()

        Returns:
            None
        '''
        old_stdin = sys.stdin
        sys.stdin = new_stdin
        yield
        sys.stdin = old_stdin

    def genraises(self, exc, gfunc, *args, **kwargs):
        '''
        Helper to validate that a generator function will throw an exception.

        Args:
            exc: Exception class to catch
            gfunc: Generator function to call.
            *args: Args passed to the generator function.
            **kwargs: Kwargs passed to the generator function.

        Notes:
            Wrap a generator function in a list() call and execute that in a
            bound local using ``self.raises(exc, boundlocal)``. The ``list()``
            will consume the generator until complete or an exception occurs.
        '''
        def testfunc():
            return list(gfunc(*args, **kwargs))

        self.raises(exc, testfunc)

    async def agenraises(self, exc, gfunc):
        '''
        Helper to validate that an async generator will throw an exception.

        Args:
            exc: Exception class to catch
            gfunc: async Generator
        '''
        await self.asyncraises(exc, alist(gfunc))

    @contextlib.contextmanager
    def setSynDir(self, dirn):
        '''
        Sets s_common.syndir to a specific directory and then unsets it afterwards.

        Args:
            dirn (str): Directory to set syndir to.

        Notes:
            This is to be used as a context manager.
        '''
        olddir = s_common.syndir
        try:
            s_common.syndir = dirn
            yield None
        finally:
            s_common.syndir = olddir

    @contextlib.contextmanager
    def getTestSynDir(self):
        '''
        Combines getTestDir() and setSynDir() into one.
        '''
        with self.getTestDir() as dirn:
            with self.setSynDir(dirn):
                yield dirn

    def eq(self, x, y, msg=None):
        '''
        Assert X is equal to Y
        '''
        if type(x) == list:
            x = tuple(x)

        if type(y) == list:
            y = tuple(y)

        self.assertEqual(x, y, msg=msg)

    def eqish(self, x, y, places=6, msg=None):
        '''
        Assert X is equal to Y within places decimal places
        '''
        self.assertAlmostEqual(x, y, places, msg=msg)

    def ne(self, x, y):
        '''
        Assert X is not equal to Y
        '''
        self.assertNotEqual(x, y)

    def true(self, x, msg=None):
        '''
        Assert X is True
        '''
        self.assertTrue(x, msg=msg)

    def false(self, x, msg=None):
        '''
        Assert X is False
        '''
        self.assertFalse(x, msg=msg)

    def nn(self, x, msg=None):
        '''
        Assert X is not None
        '''
        self.assertIsNotNone(x, msg=msg)

    def none(self, x, msg=None):
        '''
        Assert X is None
        '''
        self.assertIsNone(x, msg=msg)

    def noprop(self, info, prop):
        '''
        Assert a property is not present in a dictionary.
        '''
        valu = info.get(prop, s_common.novalu)
        self.eq(valu, s_common.novalu)

    def raises(self, *args, **kwargs):
        '''
        Assert a function raises an exception.
        '''
        return self.assertRaises(*args, **kwargs)

    async def asyncraises(self, exc, coro):
        with self.assertRaises(exc):
            await coro

    def sorteq(self, x, y, msg=None):
        '''
        Assert two sorted sequences are the same.
        '''
        return self.eq(sorted(x), sorted(y), msg=msg)

    def isinstance(self, obj, cls, msg=None):
        '''
        Assert a object is the instance of a given class or tuple of classes.
        '''
        self.assertIsInstance(obj, cls, msg=msg)

    def isin(self, member, container, msg=None):
        '''
        Assert a member is inside of a container.
        '''
        self.assertIn(member, container, msg=msg)

    def notin(self, member, container, msg=None):
        '''
        Assert a member is not inside of a container.
        '''
        self.assertNotIn(member, container, msg=msg)

    def gt(self, x, y, msg=None):
        '''
        Assert that X is greater than Y
        '''
        self.assertGreater(x, y, msg=msg)

    def ge(self, x, y, msg=None):
        '''
        Assert that X is greater than or equal to Y
        '''
        self.assertGreaterEqual(x, y, msg=msg)

    def lt(self, x, y, msg=None):
        '''
        Assert that X is less than Y
        '''
        self.assertLess(x, y, msg=msg)

    def le(self, x, y, msg=None):
        '''
        Assert that X is less than or equal to Y
        '''
        self.assertLessEqual(x, y, msg=msg)

    def len(self, x, obj, msg=None):
        '''
        Assert that the length of an object is equal to X
        '''
        gtyps = (
                 s_coro.GenrHelp,
                 s_telepath.Genr,
                 s_telepath.GenrIter,
                 types.GeneratorType,
                 )

        if isinstance(obj, gtyps):
            obj = list(obj)

        self.eq(x, len(obj), msg=msg)

    async def agenlen(self, x, obj, msg=None):
        '''
        Assert that the async generator produces x items
        '''
        count = 0
        async for _ in obj:
            count += 1
        self.eq(x, count, msg=msg)

    def stormIsInPrint(self, mesg, mesgs):
        '''
        Check if a string is present in all of the print messages from a stream of storm messages.

        Args:
            mesg (str): A string to check.
            mesgs (list): A list of storm messages.
        '''
        print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'print'])
        self.isin(mesg, print_str)

    def stormIsInWarn(self, mesg, mesgs):
        '''
        Check if a string is present in all of the warn messages from a stream of storm messages.

        Args:
            mesg (str): A string to check.
            mesgs (list): A list of storm messages.
        '''
        print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'warn'])
        self.isin(mesg, print_str)

    def istufo(self, obj):
        '''
        Check to see if an object is a tufo.

        Args:
            obj (object): Object being inspected. This is validated to be a
            tuple of length two, contiaing a str or None as the first value,
            and a dict as the second value.

        Notes:
            This does not make any assumptions about the contents of the dictionary.

        Returns:
            None
        '''
        self.isinstance(obj, tuple)
        self.len(2, obj)
        self.isinstance(obj[0], (type(None), str))
        self.isinstance(obj[1], dict)

    @contextlib.contextmanager
    def getTestConfDir(self, name, boot=None, conf=None):
        with self.getTestDir() as dirn:
            cdir = os.path.join(dirn, name)
            s_common.makedirs(cdir)
            if boot:
                s_common.yamlsave(boot, cdir, 'boot.yaml')
            if conf:
                s_common.yamlsave(conf, cdir, 'cell.yaml')
            yield dirn

    def getIngestDef(self, guid, seen):
        gestdef = {
            'comment': 'ingest_test',
            'source': guid,
            'seen': '20180102',
            'forms': {
                'test:str': [
                    '1234',
                    'duck',
                    'knight',
                ],
                'test:int': [
                    '1234'
                ],
                'test:pivcomp': [
                    ('hehe', 'haha')
                ]
            },
            'tags': {
                'test.foo': (None, None),
                'test.baz': ('2014', '2015'),
                'test.woah': (seen - 1, seen + 1),
            },
            'nodes': [
                [
                    [
                        'test:str',
                        'ohmy'
                    ],
                    {
                        'props': {
                            'bar': ('test:int', 137),
                            'tick': '2001',
                        },
                        'tags': {
                            'beep.beep': (None, None),
                            'beep.boop': (10, 20),
                        }
                    }
                ],
                [
                    [
                        'test:int',
                        '8675309'
                    ],
                    {
                        'tags': {
                            'beep.morp': (None, None)
                        }
                    }
                ]
            ],
            'edges': [
                [
                    [
                        'test:str',
                        '1234'
                    ],
                    'edge:refs',
                    [
                        [
                            'test:int',
                            1234
                        ]
                    ]
                ]
            ],
            'time:edges': [
                [
                    [
                        'test:str',
                        '1234'
                    ],
                    'edge:wentto',
                    [
                        [
                            [
                                'test:int',
                                8675309

                            ],
                            '20170102'
                        ]
                    ]
                ]
            ]
        }
        return gestdef

    async def addCreatorDeleterRoles(self, core):
        '''
        Add two roles to a Cortex *proxy*, the `creator` and `deleter` roles.
        Creator allows for node:add, prop:set and tag:add actions.
        Deleter allows for node:del, prop:del and tag:del actions.

        Args:
            core: Auth enabled cortex.
        '''
        creator = await core.auth.addRole('creator')

        await creator.setRules((
            (True, ('node:add',)),
            (True, ('prop:set',)),
            (True, ('tag:add',)),
            (True, ('feed:data',)),
        ))

        deleter = await core.auth.addRole('deleter')
        await deleter.setRules((
            (True, ('node:del',)),
            (True, ('prop:del',)),
            (True, ('tag:del',)),
        ))

        iadd = await core.auth.addUser('icanadd')
        await iadd.grant('creator')
        await iadd.setPasswd('secret')

        idel = await core.auth.addUser('icandel')
        await idel.grant('deleter')
        await idel.setPasswd('secret')

    @contextlib.asynccontextmanager
    async def getTestHive(self):
        with self.getTestDir() as dirn:
            async with self.getTestHiveFromDirn(dirn) as hive:
                yield hive

    @contextlib.asynccontextmanager
    async def getTestHiveFromDirn(self, dirn):

        import synapse.lib.const as s_const
        map_size = s_const.gibibyte

        async with await s_slab.Slab.anit(dirn, map_size=map_size) as slab:

            async with await s_hive.SlabHive.anit(slab) as hive:

                yield hive

    @contextlib.asynccontextmanager
    async def getTestHiveDmon(self):
        with self.getTestDir() as dirn:
            async with self.getTestHiveFromDirn(dirn) as hive:
                async with self.getTestDmon() as dmon:
                    dmon.share('hive', hive)
                    yield dmon

    @contextlib.asynccontextmanager
    async def getTestTeleHive(self):

        async with self.getTestHiveDmon() as dmon:

            turl = self.getTestUrl(dmon, 'hive')

            async with await s_hive.openurl(turl) as hive:

                yield hive
