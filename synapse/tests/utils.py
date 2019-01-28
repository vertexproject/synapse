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
import types
import shutil
import asyncio
import inspect
import logging
import pathlib
import tempfile
import unittest
import threading
import contextlib

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.const as s_const
import synapse.lib.scope as s_scope
import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.output as s_output
import synapse.lib.certdir as s_certdir
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
        ('testsub', 'synapse.tests.utils.TestSubType', {}, {}),
        ('testtype', 'synapse.tests.utils.TestType', {}, {}),
        ('testthreetype', 'synapse.tests.utils.ThreeType', {}, {}),
    ),

    'types': (
        ('testtype10', ('testtype', {'foo': 10}), {
            'doc': 'A fake type.'}),

        ('testlower', ('str', {'lower': True}), {}),

        ('testtime', ('time', {}), {}),

        ('testint', ('int', {}), {}),
        ('teststr', ('str', {}), {}),
        ('testauto', ('str', {}), {}),
        ('testguid', ('guid', {}), {}),

        ('testcomp', ('comp', {'fields': (
            ('hehe', 'testint'),
            ('haha', 'testlower'))
        }), {'doc': 'A fake comp type.'}),
        ('testcomplexcomp', ('comp', {'fields': (
            ('foo', 'testint'),
            ('bar', ('str', {'lower': True}),),
        )}), {'doc': 'A complex comp type.'}),
        ('testhexa', ('hex', {}), {'doc': 'anysize test hex type'}),
        ('testhex4', ('hex', {'size': 4}), {'doc': 'size 4 test hex type'}),

        ('pivtarg', ('str', {}), {}),
        ('pivcomp', ('comp', {'fields': (('targ', 'pivtarg'), ('lulz', 'teststr'))}), {}),

        ('cycle0', ('str', {}), {}),
        ('cycle1', ('str', {}), {}),

        ('test:ndef', ('ndef', {}), {}),
    ),

    'forms': (

        ('testtype10', {}, (

            ('intprop', ('int', {'min': 20, 'max': 30}), {
                'defval': 20}),

            ('strprop', ('str', {'lower': 1}), {
                'defval': 'asdf'}),

            ('guidprop', ('guid', {'lower': 1}), {
                'defval': '*'}),

            ('locprop', ('loc', {}), {
                'defval': '??'}),
        )),

        ('cycle0', {}, (
            ('cycle1', ('cycle1', {}), {}),
        )),

        ('cycle1', {}, (
            ('cycle0', ('cycle0', {}), {}),
        )),

        ('testcomp', {}, (
            ('hehe', ('testint', {}), {'ro': 1}),
            ('haha', ('testlower', {}), {'ro': 1}),
        )),

        ('testcomplexcomp', {}, (
            ('foo', ('testint', {}), {'ro': 1}),
            ('bar', ('str', {'lower': 1}), {'ro': 1})
        )),

        ('testint', {}, (
            ('loc', ('loc', {}), {}),
        )),

        ('testguid', {}, (
            ('size', ('testint', {}), {}),
            ('tick', ('testtime', {}), {}),
            ('posneg', ('testsub', {}), {}),
            ('posneg:isbig', ('bool', {}), {}),
        )),

        ('teststr', {}, (
            ('bar', ('ndef', {}), {}),
            ('baz', ('nodeprop', {}), {}),
            ('tick', ('testtime', {}), {}),
        )),

        ('testthreetype', {}, (
            ('three', ('int', {}), {}),
        )),
        ('testauto', {}, ()),
        ('testhexa', {}, ()),
        ('testhex4', {}, ()),

        ('pivtarg', {}, (
            ('name', ('str', {}), {}),
        )),

        ('pivcomp', {}, (
            ('targ', ('pivtarg', {}), {}),
            ('lulz', ('teststr', {}), {}),
            ('tick', ('time', {}), {}),
            ('size', ('testint', {}), {}),
            ('width', ('testint', {}), {}),
        )),

        ('test:ndef', {}, (
            ('form', ('str', {}), {'ro': 1}),
        )),
    ),
}

class TestModule(s_module.CoreModule):
    testguid = '8f1401de15918358d5247e21ca29a814'

    async def initCoreModule(self):
        self.core.setFeedFunc('com.test.record', self.addTestRecords)
        async with await self.core.snap() as snap:
            await snap.addNode('source', self.testguid, {'name': 'test'})

        self.core.addStormLib(('test',), LibTst)

    async def addTestRecords(self, snap, items):
        for name in items:
            await snap.addNode('teststr', name)

    def getModelDefs(self):
        return (
            ('test', testmodel),
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

    async def asyncwait(self, step, timeout=None):
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
        if not await s_glob.executor(self.steps[step].wait, timeout=timeout):
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

class CmdGenerator(s_eventbus.EventBus):
    '''
    Generates a callable object which can be used with unittest.mock.patch in
    order to do CLI driven testing.

    Args:
        cmds (list): List of commands to send to callers.
        on_end (str, Exception): Either a string or a exception class that is
        respectively returned or raised when all the provided commands have been consumed.

    Examples:
        Use the CmdGenerator to issue a series of commands to a Cli object during a test::

            outp = self.getTestOutp()  # self is a SynTest instance
            cmdg = CmdGenerator(['help', 'ask hehe:haha=1234', 'quit'])
            # Patch the get_input command to call our CmdGenerator instance
            with mock.patch('synapse.lib.cli.get_input', cmdg) as p:
                with s_cli.Cli(None, outp) as cli:
                    await cli.runCmdLoop()
                    self.eq(cli.isfini, True)

    Notes:
        This EventBus reacts to the event ``syn:cmdg:add`` to add additional
        command strings after initialization. The value of the ``cmd`` argument
        is appended to the list of commands returned by the CmdGenerator.
    '''

    def __init__(self, cmds, on_end='quit'):
        s_eventbus.EventBus.__init__(self)
        self.cmds = list(cmds)
        self.cur_command = 0
        self.end_action = on_end

        self.on('syn:cmdg:add', self._onCmdAdd)

    def _onCmdAdd(self, mesg):
        cmd = mesg[1].get('cmd')
        self.addCmd(cmd)

    def addCmd(self, cmd):
        '''
        Add a command to the end of the list of commands returned by the CmdGenerator.

        Args:
            cmd (str): Command to add to the list of commands to return.
        '''
        self.cmds.append(cmd)

    def __call__(self, *args, **kwargs):
        try:
            ret = self.cmds[self.cur_command]
        except IndexError:
            ret = self._on_end()
            return ret
        else:
            self.cur_command = self.cur_command + 1
            return ret

    def _on_end(self):
        if isinstance(self.end_action, str):
            return self.end_action
        if callable(self.end_action) and issubclass(self.end_action, BaseException):
            raise self.end_action('No further actions')
        raise Exception('Unhandled end action')

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

    def setUp(self):
        self.alt_write_layer = None  # Subclass hook to override the top layer

    def checkNode(self, node, expected):
        ex_ndef, ex_props = expected
        self.eq(node.ndef, ex_ndef)
        [self.eq(node.get(k), v, msg=f'Prop {k} does not match') for (k, v) in ex_props.items()]

        diff = {prop for prop in (set(node.props) - set(ex_props)) if not prop.startswith('.')}
        if diff:
            logger.warning('form(%s): untested properties: %s', node.form.name, diff)

    def getTestWait(self, bus, size, *evts):
        return s_eventbus.Waiter(bus, size, *evts)

    def printed(self, msgs, text):
        # a helper for testing storm print message output
        for mesg in msgs:
            if mesg[0] == 'print':
                if mesg[1].get('mesg') == text:
                    return

        raise Exception('print output not found: %r' % (text,))

    def getTestSteps(self, names):
        '''
        Return a TestSteps instance for the given step names.

        Args:
            names ([str]): The list of step names.
        '''
        return TestSteps(names)

    def skip(self, mesg):
        raise unittest.SkipTest(mesg)

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
    async def getTestCore(self, mirror='testcore', conf=None, extra_layers=None):
        '''
        Return a simple test Cortex.

        Args:
           conf:  additional configuration entries.  Combined with contents from mirror.
        '''
        with self.getTestDir(mirror=mirror) as dirn:
            s_cells.deploy('cortex', dirn)
            s_common.yamlmod(conf, dirn, 'cell.yaml')
            ldir = s_common.gendir(dirn, 'layers')
            layerdir = pathlib.Path(ldir, '000-default')
            if self.alt_write_layer:
                os.symlink(self.alt_write_layer, layerdir)
            else:
                layerdir.mkdir()
                s_cells.deploy('layer-lmdb', layerdir)
                s_common.yamlmod({'lmdb:mapsize': TEST_MAP_SIZE}, layerdir, 'cell.yaml')
            for i, fn in enumerate(extra_layers or []):
                src = pathlib.Path(fn).resolve()
                os.symlink(src, pathlib.Path(ldir, f'{i + 1:03}-testlayer'))

            async with await s_cortex.Cortex.anit(dirn) as core:
                yield core

    @contextlib.asynccontextmanager
    async def getTestDmon(self, mirror='dmontest'):

        with self.getTestDir(mirror=mirror) as dirn:

            # Copy test certs
            shutil.copytree(self.getTestFilePath('certdir'), os.path.join(dirn, 'certs'))

            coredir = pathlib.Path(dirn, 'cells', 'core')
            if coredir.is_dir():
                ldir = s_common.gendir(coredir, 'layers')
                if self.alt_write_layer:
                    os.symlink(self.alt_write_layer, pathlib.Path(ldir, '000-default'))

            certdir = s_certdir.defdir

            async with await s_daemon.Daemon.anit(dirn) as dmon:

                # act like synapse.tools.dmon...
                s_certdir.defdir = s_common.genpath(dirn, 'certs')

                yield dmon

                s_certdir.defdir = certdir

    def getTestUrl(self, dmon, name, **opts):

        host, port = dmon.addr
        netloc = '%s:%s' % (host, port)

        user = opts.get('user')
        passwd = opts.get('passwd')

        if user is not None and passwd is not None:
            netlock = '%s:%s@%s' % (user, passwd, netloc)

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
    def getTestDir(self, mirror=None):
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
        tempdir = tempfile.mkdtemp()

        try:

            if mirror is not None:
                srcpath = self.getTestFilePath(mirror)
                dstpath = os.path.join(tempdir, 'mirror')
                shutil.copytree(srcpath, dstpath)
                yield dstpath

            else:
                yield tempdir

        finally:
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
                    doSomthing()

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

            Do an action and wait for a specific log message to be written::

                with self.getLoggerStream('synapse.foo.bar', 'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    doSomthing()
                    stream.wait(timeout=10)  # Wait for the mesg to be written to the stream

                stream.seek(0)
                mesgs = stream.read()
                # Do something with messages

            You can also reset the message and wait for another message to occur::

                with self.getLoggerStream('synapse.foo.bar', 'big badda boom happened') as stream:
                    # Do something that triggers a log message
                    doSomthing()
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

    async def getTestCell(self, dirn, name, boot=None, conf=None):
        '''
        Get an instance of a Cell with specific boot and configuration data.

        Args:
            dirn (str): The directory the celldir is made in.
            name (str): The name of the cell to make. This must be a
            registered cell name in ``s_cells.ctors.``
            boot (dict): Optional boot data. This is saved to ``boot.yaml``
            for the cell to load.
            conf (dict): Optional configuration data. This is saved to
            ``cell.yaml`` for the Cell to load.

        Examples:

            Get a test Cortex cell:

                conf = {'key': 'value'}
                boot = {'cell:name': 'TestCell'}
                cell = getTestCell(someDirectory, 'cortex', conf, boot)

        Returns:
            s_cell.Cell: A Cell instance.
        '''
        cdir = os.path.join(dirn, name)
        s_common.makedirs(cdir)
        if boot:
            s_common.yamlsave(boot, cdir, 'boot.yaml')
        if conf:
            s_common.yamlsave(conf, cdir, 'cell.yaml')
        if name == 'cortex' and self.alt_write_layer:
            ldir = s_common.gendir(cdir, 'layers')
            layerdir = pathlib.Path(ldir, '000-default')
            try:
                shutil.copytree(self.alt_write_layer, layerdir)
            except FileExistsError:
                pass
        return await s_cells.init(name, cdir)

    def getIngestDef(self, guid, seen):
        gestdef = {
            'comment': 'ingest_test',
            'source': guid,
            'seen': '20180102',
            'forms': {
                'teststr': [
                    '1234',
                    'duck',
                    'knight',
                ],
                'testint': [
                    '1234'
                ],
                'pivcomp': [
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
                        'teststr',
                        'ohmy'
                    ],
                    {
                        'props': {
                            'bar': ('testint', 137),
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
                        'testint',
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
                        'teststr',
                        '1234'
                    ],
                    'refs',
                    [
                        [
                            'testint',
                            1234
                        ]
                    ]
                ]
            ],
            'time:edges': [
                [
                    [
                        'teststr',
                        '1234'
                    ],
                    'wentto',
                    [
                        [
                            [
                                'testint',
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
        await core.addAuthRole('creator')
        await core.addAuthRule('creator', (True, ('node:add',)))
        await core.addAuthRule('creator', (True, ('prop:set',)))
        await core.addAuthRule('creator', (True, ('tag:add',)))

        await core.addAuthRole('deleter')
        await core.addAuthRule('deleter', (True, ('node:del',)))
        await core.addAuthRule('deleter', (True, ('prop:del',)))
        await core.addAuthRule('deleter', (True, ('tag:del',)))

    @contextlib.asynccontextmanager
    async def getTestDmonCortexAxon(self, rootperms=True):
        '''
        Get a test Daemon with a Cortex and a Axon with a single BlobStor
        enabled. The Cortex is an auth enabled cortex with the root username
        and password as "root:root".

        This environment can be used to run tests which require having both
        an Cortex and a Axon readily available.

        Valid connection URLs for the Axon and Cortex are set in the local
        scope as "axonurl" and "coreurl" respectively.

        Args:
            perms (bool): If true, grant the root user * permissions on the Cortex.

        Returns:
            s_daemon.Daemon: A configured Daemon.
        '''
        async with self.getTestDmon('axoncortexdmon') as dmon:

            # Construct URLS for later use
            blobstorurl = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/blobstor00'
            axonurl = f'tcp://{dmon.addr[0]}:{dmon.addr[1]}/axon00'
            coreurl = f'tcp://root:root@{dmon.addr[0]}:{dmon.addr[1]}/core'

            # register the blob with the Axon.
            async with await self.agetTestProxy(dmon, 'axon00') as axon:
                await axon.addBlobStor(blobstorurl)

            # Add our helper URLs to scope so others don't
            # have to construct them.
            s_scope.set('axonurl', axonurl)
            s_scope.set('coreurl', coreurl)

            s_scope.set('blobstorurl', blobstorurl)

            # grant the root user permissions
            if rootperms:
                async with await self.getTestProxy(dmon, 'core', user='root', passwd='root') as core:
                    await self.addCreatorDeleterRoles(core)
                    await core.addUserRole('root', 'creator')
                    await core.addUserRole('root', 'deleter')

            yield dmon
