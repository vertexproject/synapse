
import threading


class TooFewEvents(Exception):
    pass


class EventWaiter:

    def __init__(self, bus, size, *evts):
        self.evts = evts
        self.size = size
        self.events = []
        self.event = threading.Event()

        for evt in evts:
            bus.on(evt, self._onTestEvent)

        if not evts:
            bus.link(self._onTestEvent)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.wait()

    def _onTestEvent(self, event):
        self.events.append(event)
        if len(self.events) >= self.size:
            self.event.set()

    def wait(self, timeout=3):
        self.event.wait(timeout=timeout)
        if len(self.events) < self.size:
            raise TooFewEvents('%r: %d/%d' % (self.evts, len(self.events), self.size))
        return self.events
