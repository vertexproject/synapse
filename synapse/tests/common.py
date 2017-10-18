import os
import ssl
import sys
import shutil
import socket
import logging
import tempfile
import unittest
import threading
import contextlib

import unittest.mock as mock


loglevel = int(os.getenv('SYN_TEST_LOG_LEVEL', logging.WARNING))
logging.basicConfig(level=loglevel,
                    format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')

import synapse.link as s_link
import synapse.cortex as s_cortex
import synapse.daemon as s_daemon
import synapse.eventbus as s_eventbus
import synapse.telepath as s_telepath

import synapse.cores.common as s_cores_common

import synapse.lib.scope as s_scope
import synapse.lib.ingest as s_ingest
import synapse.lib.output as s_output
import synapse.lib.thishost as s_thishost

from synapse.common import *

# create the global multi-plexor *not* within a test
# to avoid "leaked resource" when a test triggers creation
s_scope.get('plex')

class TooFewEvents(Exception): pass

TstSSLInvalidClientCertErr = socket.error
TstSSLConnectionResetErr = socket.error

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

    def expect(self, substr):
        outs = str(self)
        if outs.find(substr) == -1:
            raise Exception('TestOutPut.expect(%s) not in %s' % (substr, outs))

class SynTest(unittest.TestCase):

    def getTestWait(self, bus, size, *evts):
        return s_eventbus.Waiter(bus, size, *evts)

    def skipIfNoInternet(self):
        if bool(int(os.getenv('SYN_TEST_SKIP_INTERNET', 0))):
            raise unittest.SkipTest('SYN_TEST_SKIP_INTERNET envar set')

    def skipLongTest(self):
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
        if not db:
            raise unittest.SkipTest('no SYN_TEST_PG_DB envar')
        try:
            import psycopg2
        except ImportError:
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
            A PSQL backed cortex.

        Raises:
            unittest.SkipTest: if there is no SYN_TEST_PG_DB envar set.
        '''
        db = os.getenv('SYN_TEST_PG_DB')
        if not db:
            raise unittest.SkipTest('no SYN_TEST_PG_DB envar')

        if not table:
            table = 'syn_test_%s' % guid()
        core = s_cortex.openurl('postgres://%s/%s' % (db, table), **opts)

        def droptable():
            with core.getCoreXact() as xact:
                xact.cursor.execute('DROP TABLE %s' % (table,))
                xact.cursor.execute('DROP TABLE IF EXISTS %s' % (table + '_blob',))

        if not persist:
            core.onfini(droptable)
        return core

    def getTestOutp(self):
        return TstOutPut()

    def thisHostMust(self, **props):
        for k, v in props.items():
            if s_thishost.get(k) != v:
                raise unittest.SkipTest('skip thishost: %s!=%r' % (k, v))

    def thisHostMustNot(self, **props):
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

        yield prox

        prox.fini()
        core.fini()
        dmon.fini()

    @contextlib.contextmanager
    def getTestDir(self):
        tempdir = tempfile.mkdtemp()
        yield tempdir
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
        yield stream
        slogger.removeHandler(handler)

    def eq(self, x, y):
        self.assertEqual(x, y)

    def ne(self, x, y):
        self.assertNotEqual(x, y)

    def true(self, x):
        self.assertTrue(x)

    def false(self, x):
        self.assertFalse(x)

    def nn(self, x):
        self.assertIsNotNone(x)

    def none(self, x):
        self.assertIsNone(x)

    def noprop(self, info, prop):
        valu = info.get(prop, novalu)
        self.eq(valu, novalu)

    def raises(self, *args, **kwargs):
        return self.assertRaises(*args, **kwargs)

    def sorteq(self, x, y):
        return self.eq(sorted(x), sorted(y))

    def isinstance(self, obj, cls):
        self.assertIsInstance(obj, cls)

    def isin(self, member, container):
        self.assertIn(member, container)

    def notin(self, member, container):
        self.assertNotIn(member, container)

    def gt(self, x, y):
        self.assertGreater(x, y)

    def ge(self, x, y):
        self.assertGreaterEqual(x, y)

    def lt(self, x, y):
        self.assertLess(x, y)

    def le(self, x, y):
        self.assertLessEqual(x, y)

    def len(self, x, obj):
        self.eq(x, len(obj))

testdir = os.path.dirname(__file__)
def getTestPath(*paths):
    return os.path.join(testdir, *paths)

def getIngestCore(path, core=None):
    if core is None:
        core = s_cortex.openurl('ram:///')

    gest = s_ingest.loadfile(path)
    with core.getCoreXact() as xact:
        gest.ingest(core)

    return core
