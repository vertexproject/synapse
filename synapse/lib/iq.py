# -*- coding: utf-8 -*-
"""
synapse - iq.py
Created on 10/21/17.

The IQ module contains the core test helper code used in Synapse.

This gives the opportunity for third-party users of Synapse to test their
code using some of the same of the same helpers used to test Synapse.

The core class, synapse.lib.iq.SynTest is a subclass of unittest.TestCase,
with several wrapper functions to allow for easier calls to assert* functions,
with less typing.  There are also Synapse specific helpers, to load both Ram
and PSQL Cortexes.

Since SynTest is built from unittest.TestCase, the use of SynTest is
compatible with the unittest, nose and pytest frameworks.  This does not lock
users into a particular test framework; while at the same time allowing base
use to be invoked via the built-in Unittest library.
"""
import io
import os
import types
import shutil
import logging
import tempfile
import unittest
import threading
import contextlib
import collections

import synapse.link as s_link
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.cores.common as s_cores_common

import synapse.lib.scope as s_scope
import synapse.lib.output as s_output
import synapse.lib.thishost as s_thishost

logger = logging.getLogger(__name__)

def objhierarchy(obj):
    '''
    Return the type hierarchy of an an object.
    Dictionary objects have their key values preserved.

    This function exists for debugging purposes.
    '''
    # Known objects we want to return fast on
    if isinstance(obj, (str, int, float, bytes, types.GeneratorType)):
        return type(obj)
    # Iterables we care about
    if isinstance(obj, collections.Iterable):
        if isinstance(obj, dict):
            return {k: objhierarchy(v) for k, v in obj.items()}
        if isinstance(obj, set):
            return {objhierarchy(o) for o in obj}
        if isinstance(obj, tuple):
            return tuple([objhierarchy(o) for o in obj])
        return [objhierarchy(o) for o in obj]
    # Default case
    return type(obj)

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

class TestSteps:
    '''
    A class to assist with interlocking for multi-thread tests.
    '''
    def __init__(self, names):
        self.steps = {}
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

        Raises:
            Exception: on wait timeout
        '''
        if not self.steps[step].wait(timeout=timeout):
            raise Exception('timeout waiting for step: %d' % (step,))

    def step(self, done, wait, timeout=None):
        '''
        Complete a step and wait for another.

        Args:
            done (str): The step name to complete.
            wait (str): The step name to wait for.
            timeout (int): The wait timeout.
        '''
        self.done(done)
        self.wait(wait, timeout=timeout)

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
                    cli.runCmdLoop()
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

class SynTest(unittest.TestCase):

    def getTestWait(self, bus, size, *evts):
        return s_eventbus.Waiter(bus, size, *evts)

    def getTestSteps(self, names):
        '''
        Return a TestSteps instance for the given step names.

        Args:
            names ([str]): The list of step names.
        '''
        return TestSteps(names)

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

    def getPgConn(self):
        '''
        Get a psycopg2 connection object.

        The PG database connected to is derived from the SYN_TEST_PG_DB
        environmental variable.

        Returns:
            psycopg2.connection: Raw psycopg2 connection object.

        '''
        db = os.getenv('SYN_TEST_PG_DB')
        if not db:  # pragma: no cover
            raise unittest.SkipTest('no SYN_TEST_PG_DB envar')
        try:
            import psycopg2
        except ImportError:  # pragma: no cover
            raise unittest.SkipTest('psycopg2 not installed.')

        url = 'postgres://%s' % db
        link = s_link.chopLinkUrl(url)

        def _initDbInfo(link):

            dbinfo = {}

            path = link[1].get('path')
            if path:
                parts = [p for p in path.split('/') if p]
                if parts:
                    dbinfo['database'] = parts[0]

            host = link[1].get('host')
            if host is not None:
                dbinfo['host'] = host

            port = link[1].get('port')
            if port is not None:
                dbinfo['port'] = port

            user = link[1].get('user')
            if user is not None:
                dbinfo['user'] = user

            passwd = link[1].get('passwd')
            if passwd is not None:
                dbinfo['password'] = passwd

            return dbinfo

        dbinfo = _initDbInfo(link)
        conn = psycopg2.connect(**dbinfo)
        return conn

    def getPgCore(self, table='', persist=False, **opts):
        '''
        Get a Postgresql backed Cortex.

        This will grab the SYN_TEST_PG_DB environmental variable, and use it to construct
        a string to connect to a PSQL server and create a Cortex. By default, the Cortex
        DB tables will be dropped when onfini() is called on the Cortex.

        Some example values for this envar are shown below::

            # From our .drone.yml file
            root@database:5432/syn_test
            # An example which may be used with a local docker image
            # after having created the syn_test database
            postgres:1234@localhost:5432/syn_test

        Args:
            table (str): The PSQL table name to use.  If the table name is not provided
                         by URL or argument; a random table name will be created.
            persist (bool): If set to True, keep the tables created by the Cortex creation.
            opts: Additional options passed to openlink call.

        Returns:
            s_cores_common.Cortex: A PSQL backed cortex.

        Raises:
            unittest.SkipTest: if there is no SYN_TEST_PG_DB envar set.
        '''
        db = os.getenv('SYN_TEST_PG_DB')
        if not db:  # pragma: no cover
            raise unittest.SkipTest('no SYN_TEST_PG_DB envar')

        if not table:
            table = 'syn_test_%s' % s_common.guid()
        core = s_cortex.openurl('postgres://%s/%s' % (db, table), **opts)

        def droptable():
            with core.getCoreXact() as xact:
                xact.cursor.execute('DROP TABLE %s' % (table,))
                xact.cursor.execute('DROP TABLE IF EXISTS %s' % (table + '_blob',))

        if not persist:
            core.onfini(droptable)
        return core

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

    @staticmethod
    def addTstForms(core):
        '''
        Add test forms to the cortex.

        Args:
            core (s_cores_common.Cortex): Core to prep.

        Returns:
            None
        '''
        # Some custom type machinations for later test use
        modl = {
            'types': (
                ('strform', {'subof': 'str'},),
                ('intform', {'subof': 'int'},),
                ('default_foo', {'subof': 'str'},),
                ('guidform', {'subof': 'guid'},),
                ('pvsub', {'subof': 'str'}),
            ),
            'forms': (
                (
                    'strform', {'ptype': 'strform', 'doc': 'A test str form'},
                    (
                        ('foo', {'ptype': 'str'}),
                        ('bar', {'ptype': 'str'}),
                        ('baz', {'ptype': 'int'}),
                    )
                ),
                (
                    'intform', {'ptype': 'intform'},  # purposely missing doc
                    (
                        ('foo', {'ptype': 'str'}),
                        ('baz', {'ptype': 'int'}),
                    )
                ),
                (
                    'default_foo', {'ptype': 'str'},
                    (
                        ('p0', {'ptype': 'int'}),
                    )
                ),
                (
                    'guidform', {'ptype': 'guidform'},
                    (
                        ('foo', {'ptype': 'str'}),
                        ('baz', {'ptype': 'int'}),
                    )
                ),
                (
                    'pvsub', {'ptype': 'pvsub'},
                    (
                        ('xref', {'ptype': 'propvalu', 'ro': 1, }),
                        ('xref:intval', {'ptype': 'int', 'ro': 1, }),
                        ('xref:strval', {'ptype': 'str', 'ro': 1}),
                        ('xref:prop', {'ptype': 'str', 'ro': 1}),
                    )
                ),
                (
                    'pvform', {'ptype': 'propvalu'},
                    (
                        ('intval', {'ptype': 'int', 'ro': 1, }),
                        ('strval', {'ptype': 'str', 'ro': 1}),
                        ('prop', {'ptype': 'str', 'ro': 1}),
                    )
                ),
            )
        }
        core.addDataModel('tst', modl)
        core.addTufoProp('inet:fqdn', 'inctest', ptype='int', defval=0)

    @contextlib.contextmanager
    def getRamCore(self):
        '''
        Context manager to make a ram:/// cortex which has test models
        loaded into it.

        Yields:
            s_cores_common.Cortex: Ram backed cortex with test models.
        '''
        with s_cortex.openurl('ram:///') as core:
            self.addTstForms(core)
            try:
                yield core
            finally:
                core.fini()

    @contextlib.contextmanager
    def getDirCore(self):
        '''
        Context manager to make a dir:/// cortex

        Yields:
            s_cores_common.Cortex: Dir backed Cortex
        '''
        with self.getTestDir() as dirn:
            with s_cortex.fromdir(dirn) as core:
                yield core

    @contextlib.contextmanager
    def getDmonCore(self):
        '''
        Context manager to make a ram:/// cortex which has test models loaded into it and shared via daemon.

        Yields:
            s_cores_common.Cortex: A proxy object to the Ram backed cortex with test models.
        '''
        dmon = s_daemon.Daemon()
        core = s_cortex.openurl('ram:///')
        self.addTstForms(core)

        link = dmon.listen('tcp://127.0.0.1:0/')
        dmon.share('core00', core)
        port = link[1].get('port')
        prox = s_telepath.openurl('tcp://127.0.0.1/core00', port=port)

        s_scope.set('syn:test:link', link)
        s_scope.set('syn:cmd:core', prox)

        try:
            yield prox
        except:  # pragma: no cover
            raise
        finally:
            prox.fini()
            core.fini()
            dmon.fini()

    @contextlib.contextmanager
    def getTestDir(self):
        '''
        Get a temporary directory for test purposes.
        This destroys the directory afterwards.

        Yields:
            str: The path to a temporary directory.
        '''
        tempdir = tempfile.mkdtemp()
        try:
            yield tempdir
        except:  # pragma: no cover
            raise
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)

    @contextlib.contextmanager
    def getLoggerStream(self, logname):
        '''
        Get a logger and attach a io.StringIO object to the logger to capture log messages.

        Args:
            logname (str): Name of the logger to get.

        Examples:
            Do an action and get the stream of log messages to check against::

                with self.getLoggerStream('synapse.foo.bar') as stream:
                    # Do something that triggers a log message
                    doSomthing()
                    stream.seek(0)
                    mesgs = stream.read()
                # Do something with messages

        Yields:
            io.StringIO: A io.StringIO object
        '''
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        slogger = logging.getLogger(logname)
        slogger.addHandler(handler)
        try:
            yield stream
        except:  # pragma: no cover
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
        except:  # pragma: no cover
            raise
        # Clean up any new envars we set and any old envars we need to reset.
        finally:
            for key in pop_data:
                del os.environ[key]
            for key, valu in old_data.items():
                os.environ[key] = valu

    def eq(self, x, y):
        '''
        Assert X is equal to Y
        '''
        self.assertEqual(x, y)

    def ne(self, x, y):
        '''
        Assert X is not equal to Y
        '''
        self.assertNotEqual(x, y)

    def true(self, x):
        '''
        Assert X is True
        '''
        self.assertTrue(x)

    def false(self, x):
        '''
        Assert X is False
        '''
        self.assertFalse(x)

    def nn(self, x):
        '''
        Assert X is not None
        '''
        self.assertIsNotNone(x)

    def none(self, x):
        '''
        Assert X is None
        '''
        self.assertIsNone(x)

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

    def sorteq(self, x, y):
        '''
        Assert two sorted sequences are the same.
        '''
        return self.eq(sorted(x), sorted(y))

    def isinstance(self, obj, cls):
        '''
        Assert a object is the instance of a given class or tuple of classes.
        '''
        self.assertIsInstance(obj, cls)

    def isin(self, member, container):
        '''
        Assert a member is inside of a container.
        '''
        self.assertIn(member, container)

    def notin(self, member, container):
        '''
        Assert a member is not inside of a container.
        '''
        self.assertNotIn(member, container)

    def gt(self, x, y):
        '''
        Assert that X is greater than Y
        '''
        self.assertGreater(x, y)

    def ge(self, x, y):
        '''
        Assert that X is greater than or equal to Y
        '''
        self.assertGreaterEqual(x, y)

    def lt(self, x, y):
        '''
        Assert that X is less than Y
        '''
        self.assertLess(x, y)

    def le(self, x, y):
        '''
        Assert that X is less than or equal to Y
        '''
        self.assertLessEqual(x, y)

    def len(self, x, obj):
        '''
        Assert that the length of an object is equal to X
        '''
        self.eq(x, len(obj))
