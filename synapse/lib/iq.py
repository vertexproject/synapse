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
import sys
import time
import types
import shutil
import logging
import tempfile
import unittest
import threading
import contextlib
import collections

import synapse.axon as s_axon
import synapse.link as s_link
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.neuron as s_neuron
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.cores.common as s_cores_common

import synapse.data as s_data

import synapse.lib.cell as s_cell
import synapse.lib.const as s_const
import synapse.lib.scope as s_scope
import synapse.lib.output as s_output
import synapse.lib.msgpack as s_msgpack
import synapse.lib.thishost as s_thishost

logger = logging.getLogger(__name__)

# Default LMDB map size for tests
TEST_MAP_SIZE = s_const.gibibyte


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


def writeCerts(dirn):
    '''
    Copy test SSL certs from synapse.data to a directory.

    Args:
        dirn (str): Path to write files too.

    Notes:
        Writes the following files to disk:
        . ca.crt
        . ca.key
        . ca.pem
        . server.crt
        . server.key
        . server.pem
        . root.crt
        . root.key
        . user.crt
        . user.key

        The ca has signed all three certs.  The ``server.crt`` is for
        a server running on localhost. The ``root.crt`` and ``user.crt``
        certs are both are user certs which can connect. They have the
        common names "root@localhost" and "user@localhost", respectively.

    Returns:
        None
    '''
    fns = ('ca.crt', 'ca.key', 'ca.pem',
           'server.crt', 'server.key', 'server.pem',
           'root.crt', 'root.key', 'user.crt', 'user.key')
    for fn in fns:
        byts = s_data.get(fn)
        dst = os.path.join(dirn, fn)
        if not os.path.exists(dst):
            with s_common.genfile(dst) as fd:
                fd.write(byts)


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
            raise s_common.StepTimeout(mesg='timeout waiting for step',
                                       step=step)
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
                ('compfqdn', {'subof': 'comp', 'fields': 'guid=guid,fqdn=inet:fqdn'}),
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
                        ('faz', {'ptype': 'int', 'ro': 1}),
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
                (
                    'compfqdn', {'ptype': 'compfqdn'},
                    (
                        ('guid', {'ptype': 'guid', 'ro': 1}),
                        ('fqdn', {'ptype': 'inet:fqdn', 'ro': 1}),
                        ('seen:min', {'ptype': 'time:min'}),
                        ('seen:max', {'ptype': 'time:max'}),
                    )
                ),

            )
        }
        core.addDataModel('tst', modl)
        core.addTufoProp('inet:fqdn', 'inctest', ptype='int', defval=0)

    @contextlib.contextmanager
    def getAxonCore(self, cortex_conf=None):
        '''
        Get a TstEnv instance which is preconfigured with a Neuron, Blob, Axon, Daemon and Cortex.

        Notes:
            The following items are available in the TstEnv:

            * dirn: Temporary test directory.
            * axon_client: A Axon client object.
            * core_url: The Telepath URL to the Cortex so a connection can be made to the Cortex
              shared by the Daemon.
            * dmon_port: Port the Daemon is listening on.
            * dmon: A Daemon which is listening on 127.0.0.1:0. It is preconfigured to share the Cortex.
            * core: A Cortex.
            * axon_sess: The client session for the Axon.
            * axon: The AxonCell.
            * blob: The BlobCell backing the Axon.
            * neuron: The Neuron.

        Args:
            cortex_conf (dict): Optional cortex config

        Yields:
            TstEnv: A TstEnv instance.
        '''
        with self.getTestDir() as dirn:
            neurconf = {'host': 'localhost', 'bind': '127.0.0.1', 'port': 0}
            neurpath = s_common.gendir(dirn, 'neuron')
            neur = s_neuron.Neuron(neurpath, neurconf)
            neurhost, neurport = neur.getCellAddr()

            blobpath = s_common.gendir(dirn, 'blob')
            blobconf = {'host': 'localhost', 'bind': '127.0.0.1', 'port': 0, 'blob:mapsize': TEST_MAP_SIZE}
            blobauth = neur.genCellAuth('blob')
            s_msgpack.dumpfile(blobauth, os.path.join(blobpath, 'cell.auth'))
            blob = s_axon.BlobCell(blobpath, blobconf)
            self.true(blob.cellpool.neurwait(timeout=3))

            axonpath = s_common.gendir(dirn, 'axon')
            axonauth = neur.genCellAuth('axon')
            s_msgpack.dumpfile(axonauth, os.path.join(axonpath, 'cell.auth'))
            axonconf = {'host': 'localhost', 'bind': '127.0.0.1', 'port': 0, 'axon:blobs': ('blob@localhost',),
                        'axon:mapsize': TEST_MAP_SIZE}
            axon = s_axon.AxonCell(axonpath, axonconf)
            self.true(axon.cellpool.neurwait(timeout=3))
            axonhost, axonport = axon.getCellAddr()

            # wait for the axon to have blob
            ready = False
            for i in range(30):
                if axon.blobs.items():
                    ready = True
                    break
                time.sleep(0.1)
            self.true(ready)

            axon_user = s_cell.CellUser(axonauth)
            axon_sess = axon_user.open((axonhost, axonport))
            axon_client = s_axon.AxonClient(axon_sess)

            core = s_cortex.openurl('ram:///', conf=cortex_conf)
            self.addTstForms(core)

            cellpoolconf = {'host': neurhost, 'port': neurport, 'auth': s_common.enbase64(s_msgpack.en(axonauth))}
            core.setConfOpt('cellpool:conf', cellpoolconf)
            core.setConfOpt('axon:name', 'axon@localhost')

            dmon = s_daemon.Daemon()
            dmonlink = dmon.listen('tcp://127.0.0.1:0/')
            dmonport = dmonlink[1].get('port')
            dmon.share('core', core)
            coreurl = 'tcp://127.0.0.1:%d/core' % dmonport

            env = TstEnv()
            env.add('dirn', dirn)
            env.add('axon_client', axon_client)
            env.add('core_url', coreurl)
            env.add('dmon_port', dmonport)
            # Order matter for clean fini
            env.add('dmon', dmon, True)
            env.add('core', core, True)
            env.add('axon_sess', axon_sess, True)
            env.add('axon', axon, True)
            env.add('blob', blob, True)
            env.add('neuron', neur, True)
            try:
                yield env
            finally:
                env.fini()

    @contextlib.contextmanager
    def getRamCore(self, conf=None):
        '''
        Context manager to make a ram:/// cortex which has test models
        loaded into it.

        Args:
            conf (dict): Optional config

        Yields:
            s_cores_common.Cortex: Ram backed cortex with test models.
        '''
        with s_cortex.openurl('ram:///', conf=conf) as core:
            self.addTstForms(core)
            try:
                yield core
            finally:
                core.fini()

    @contextlib.contextmanager
    def getDirCore(self, conf=None):
        '''
        Context manager to make a dir:/// cortex which has test models
        loaded into it.

        Args:
            conf (dict): Optional cortex config

        Yields:
            s_cores_common.Cortex: Dir backed Cortex
        '''
        with self.getTestDir() as dirn:
            s_scope.set('dirn', dirn)
            with s_cortex.fromdir(dirn, conf=conf) as core:
                self.addTstForms(core)
                yield core

    @contextlib.contextmanager
    def getDmonCore(self, conf=None):
        '''
        Context manager to make a ram:/// cortex which has test models
        loaded into it and shared via daemon.

        Args:
            conf (dict): Optional cortex config

        Yields:
            s_cores_common.Cortex: A proxy object to the Ram backed cortex with test models.
        '''
        dmon = s_daemon.Daemon()
        core = s_cortex.openurl('ram:///', conf=conf)
        self.addTstForms(core)

        link = dmon.listen('tcp://127.0.0.1:0/')
        dmon.share('core00', core)
        port = link[1].get('port')
        prox = s_telepath.openurl('tcp://127.0.0.1/core00', port=port)

        s_scope.set('syn:test:link', link)
        s_scope.set('syn:cmd:core', prox)
        s_scope.set('syn:core', core)
        s_scope.set('syn:dmon', dmon)

        try:
            yield prox
        except:  # pragma: no cover
            raise
        finally:
            prox.fini()
            core.fini()
            dmon.fini()
            s_scope.pop('syn:dmon')
            s_scope.pop('syn:core')
            s_scope.pop('syn:cmd:core')
            s_scope.pop('syn:test:link')

    @contextlib.contextmanager
    def getSslCore(self, conf=None, configure_roles=False):
        dconf = {'auth:admin': 'root@localhost',
                 'auth:en': 1, }
        if conf:
            conf.update(dconf)
        conf = dconf

        amesgs = (
            ('auth:add:user', {'user': 'user@localhost'}),
            ('auth:add:role', {'role': 'creator'}),
            ('auth:add:rrule', {'role': 'creator',
                                'rule': ('node:add',
                                         {'form': '*'})
                                }),
            ('auth:add:rrule', {'role': 'creator',
                                'rule': ('node:tag:add',
                                         {'tag': '*'})
                                }),
            ('auth:add:rrule', {'role': 'creator',
                                'rule': ('node:prop:set',
                                         {'form': '*', 'prop': '*'})
                                }),
            ('auth:add:role', {'role': 'deleter'}),
            ('auth:add:rrule', {'role': 'deleter',
                                'rule': ('node:del',
                                         {'form': '*'})
                                }),
            ('auth:add:rrule', {'role': 'deleter',
                                'rule': ('node:del',
                                         {'form': '*'})
                                }),
            ('auth:add:rrule', {'role': 'deleter',
                                'rule': ('node:tag:del',
                                         {'tag': '*'})
                                }),
            ('auth:add:rrule', {'role': 'deleter',
                                'rule': ('node:prop:set',
                                         {'form': '*', 'prop': '*'})
                                }),
            ('auth:add:urole', {'user': 'user@localhost', 'role': 'creator'}),
            ('auth:add:urole', {'user': 'user@localhost', 'role': 'deleter'}),
        )

        with self.getDirCore(conf=conf) as core:
            s_scope.set('syn:core', core)
            dirn = s_scope.get('dirn')
            writeCerts(dirn)
            cafile = os.path.join(dirn, 'ca.crt')
            keyfile = os.path.join(dirn, 'server.key')
            certfile = os.path.join(dirn, 'server.crt')
            userkey = os.path.join(dirn, 'user.key')
            usercrt = os.path.join(dirn, 'user.crt')
            rootkey = os.path.join(dirn, 'root.key')
            rootcrt = os.path.join(dirn, 'root.crt')
            with s_daemon.Daemon() as dmon:
                s_scope.set('syn:dmon', dmon)
                dmon.share('core', core)
                link = dmon.listen('ssl://localhost:0/',
                                   cafile=cafile,
                                   keyfile=keyfile,
                                   certfile=certfile,
                                   )
                s_scope.set('syn:test:link', link)
                port = link[1].get('port')
                url = 'ssl://user@localhost/core'
                user_prox = s_telepath.openurl(url,
                                               port=port,
                                               cafile=cafile,
                                               keyfile=userkey,
                                               certfile=usercrt
                                               )  # type: s_cores_common.CoreApi
                root_prox = s_telepath.openurl(url,
                                               port=port,
                                               cafile=cafile,
                                               keyfile=rootkey,
                                               certfile=rootcrt
                                               )  # type: s_cores_common.CoreApi

                if configure_roles:
                    for mesg in amesgs:
                        isok, retn = root_prox.authReact(mesg)
                        s_common.reqok(isok, retn)

                try:
                    yield user_prox, root_prox
                finally:
                    user_prox.fini()
                    root_prox.fini()

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

    def eqish(self, x, y, places=6):
        '''
        Assert X is equal to Y within places decimal places
        '''
        self.assertAlmostEqual(x, y, places)

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
