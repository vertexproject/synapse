import unittest
import threading

import synapse.session as s_session

from synapse.common import *

class TooFewEvents(Exception):pass

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

    def getTestSess(self):
        cura = s_session.Curator()
        return cura.getNewSess()

    def eq(self, x, y):
        self.assertEqual(x,y)

    def nn(self, x):
        self.assertIsNotNone(x)
