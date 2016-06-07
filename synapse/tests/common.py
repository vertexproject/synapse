import os
import shutil
import logging
import tempfile
import unittest
import threading
import contextlib

logging.basicConfig(level=logging.WARNING)

import synapse.lib.thishost as s_thishost

from synapse.common import *

class TooFewEvents(Exception):pass

class TestEnv:

    def __init__(self):
        self.items = {}
        self.tofini = []

    def __getattr__(self, prop):
        item = self.items.get(prop)
        if item == None:
            raise AttributeError(prop)
        return item

    def add(self, name, item, fini=False):
        self.items[name] = item
        if fini:
            self.tofini.append(item)

    def fini(self):
        for bus in self.tofini:
            bus.fini()

class TestWaiter:

    def __init__(self, bus, size, *evts):
        self.evts = evts
        self.size = size
        self.events = []

        self.event = threading.Event()

        for evt in evts:
            bus.on(evt, self._onTestEvent)

        if not evts:
            bus.link(self._onTestEvent)

    def _onTestEvent(self, event):
        self.events.append(event)
        if len(self.events) >= self.size:
            self.event.set()

    def wait(self, timeout=3):
        self.event.wait(timeout=timeout)
        if len(self.events) < self.size:
            raise TooFewEvents('%r: %d/%d' % (self.evts, len(self.events), self.size))
        return self.events

class SynTest(unittest.TestCase):

    def getTestWait(self, bus, size, *evts):
        return TestWaiter(bus, size, *evts)

    def thisHostMust(self, **props):
        for k,v in props.items():
            if s_thishost.get(k) != v:
                raise unittest.SkipTest('skip thishost: %s!=%r' % (k,v))

    def thisHostMustNot(self, **props):
        for k,v in props.items():
            if s_thishost.get(k) == v:
                raise unittest.SkipTest('skip thishost: %s==%r' % (k,v))

    @contextlib.contextmanager
    def getTestDir(self):
        tempdir = tempfile.mkdtemp()
        yield tempdir
        shutil.rmtree(tempdir)

    def eq(self, x, y):
        self.assertEqual(x,y)

    def nn(self, x):
        self.assertIsNotNone(x)

testdir = os.path.dirname(__file__)
def getTestPath(*paths):
    return os.path.join(testdir,*paths)
