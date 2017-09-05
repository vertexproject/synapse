import logging
import threading
import traceback
import collections

import synapse.common as s_common

import synapse.lib.reflect as s_reflect
import synapse.lib.thishost as s_thishost

logger = logging.getLogger(__name__)
finlock = threading.RLock()

def on(evnt, **filt):
    '''
    A decorator to register a method for EventBus.on() callbacks.

    Example:

        class FooBar(EventBus):

            @on('hehe')
            def _onHehe(self, mesg):
                doHeheStuff(mesg)

            # only fires if mesg[1].get('woot') == True
            @on('haha', woot=True)
            def _onHahaWoot(self, mesg):
                doHahaStuff(mesg)

    See: EventBus.on()

    '''
    def wrap(f):
        ons = getattr(f, '_ebus_ons', None)
        if ons is None:
            ons = f._ebus_ons = []
        ons.append((evnt, filt))
        return f
    return wrap

def onfini(f):
    '''
    A decorator to register a method for EventBus.onfini() callbacks.

    Example:

        class FooBar(EventBus):

            @onfini
            def _onFooBarFini(self):
                doFiniStuff()

    See: EventBus.onfini()

    '''
    f._ebus_onfini = True
    return f

class EventBus(object):
    '''
    A synapse EventBus provides an easy way manage callbacks.
    '''
    def __init__(self):
        self.isfini = False
        self.finlock = finlock
        self.finievt = threading.Event()

        self._syn_funcs = collections.defaultdict(list)

        self._syn_links = []

        self._syn_queues = {}

        self._fini_funcs = []

        for name, valu in s_reflect.getItemLocals(self):

            if not callable(valu):
                continue

            # check for onfini() decorator
            if getattr(valu, '_ebus_onfini', None):
                self.onfini(valu)
                continue

            # check for on() decorators
            for name, filt in getattr(valu, '_ebus_ons', ()):
                self.on(name, valu, **filt)

        self.fire('ebus:init')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.fini()

    def link(self, func):
        '''
        Add a callback function to receive *all* events.

        Example:

            bus1 = EventBus()
            bus2 = EventBus()

            bus1.link( bus2.dist )

            # all events on bus1 are also propigated on bus2

        '''
        self._syn_links.append(func)

    def unlink(self, func):
        '''
        Remove a callback function previously added with link()

        Example:

            bus.unlink( callback )

        '''
        if func in self._syn_links:
            self._syn_links.remove(func)

    def on(self, evnt, func, **filts):
        '''
        Add an event bus callback for a specific event with optional filtering.

        Args:
            evnt (str):         An event name
            func (function):    A callback function to receive event tufo
            **filts:            Optional positive filter values for the event tuple.

        Returns:
            (None)

        Example:

            def baz(event):
                x = event[1].get('x')
                y = event[1].get('y')
                return x + y

            d.on('foo', baz, x=10)

            # this fire triggers baz...
            d.fire('foo', x=10, y=20)

            # this fire does not ( due to filt )
            d.fire('foo', x=30, y=20)

        '''
        self._syn_funcs[evnt].append((func, tuple(filts.items())))

    def off(self, evnt, func):
        '''
        Remove a previously registered event handler function.

        Example:

            bus.off( 'foo', onFooFunc )

        '''
        funcs = self._syn_funcs.get(evnt)
        if funcs is not None:

            for i in range(len(funcs)):

                if funcs[i][0] == func:
                    funcs.pop(i)
                    break

            if not funcs:
                self._syn_funcs.pop(evnt, None)

    def fire(self, evtname, **info):
        '''
        Fire the given event name on the EventBus.
        Returns a list of the return values of each callback.

        Example:

            for ret in d.fire('woot',foo='asdf'):
                print('got: %r' % (ret,))

        '''
        event = (evtname, info)
        self.dist(event)
        return event

    def dist(self, mesg):
        '''
        Distribute an existing event tuple.

        Args:
            mesg ((str,dict)):  An event tuple.

        Example:

            ebus.dist( ('foo',{'bar':'baz'}) )

        '''
        ret = []

        for func, filt in self._syn_funcs.get(mesg[0], ()):

            try:

                if any(True for k, v in filt if mesg[1].get(k) != v):
                    continue

                ret.append(func(mesg))

            except Exception as e:
                logger.exception(e)

        for func in self._syn_links:
            try:
                ret.append(func(mesg))
            except Exception as e:
                logger.exception(e)

        return ret

    def fini(self):
        '''
        Fire the 'fini' handlers and set self.isfini.

        Example:

            d.fini()

        '''
        with finlock:

            if self.isfini:
                return

            self.isfini = True

        for func in self._fini_funcs:
            try:
                func()
            except Exception as e:
                traceback.print_exc()

        # explicitly release the handlers
        self._syn_funcs.clear()
        del self._fini_funcs[:]

        self.finievt.set()

    def onfini(self, func):
        '''
        Register a handler to fire when this EventBus shuts down.
        '''
        self._fini_funcs.append(func)

    def waitfini(self, timeout=None):
        '''
        Wait for the event bus to fini()

        Example:

            bus.waitfini(timeout=30)

        '''
        return self.finievt.wait(timeout=timeout)

    def main(self):
        '''
        Helper function to block until shutdown ( and handle ctrl-c etc ).

        Example:

            dmon.main()
            # we have now fini()d

        '''
        try:
            self.waitfini()
        except KeyboardInterrupt as e:
            print('ctrl-c caught: shutting down')
            self.fini()

    def distall(self, events):
        '''
        Distribute multiple events on the event bus.
        '''
        [self.dist(evt) for evt in events]

    @s_common.firethread
    def consume(self, gtor):
        '''
        Feed the event bus from a generator.

        Example:

            bus.consume( getAllEvents() )

        '''
        for e in gtor:
            if e is None:
                break

            self.dist(e)

    def waiter(self, count, *names):
        '''
        Construct and return a new Waiter for events on this bus.

        Example:

            # wait up to 3 seconds for 10 foo:bar events...

            waiter = bus.waiter(10,'foo:bar')

            # .. fire thread that will cause foo:bar events

            events = waiter.wait(timeout=3)

            if events == None:
                # handle the timout case...

            for event in events:
                # parse the events if you need...

        NOTE: use with caution... it's easy to accidentally construct
              race conditions with this mechanism ;)

        '''
        return Waiter(self, count, *names)

    def log(self, level, mesg, **info):
        '''
        Implements the log event convention for an EventBus.

        Args:
            level (int):  A python logger level for the event
            mesg (str):   A log message
            **info:       Additional log metadata

        '''
        info['time'] = s_common.now()
        info['host'] = s_thishost.get('hostname')

        info['level'] = level
        info['class'] = self.__class__.__name__

        self.fire('log', mesg=mesg, **info)

    def exc(self, exc, **info):
        '''
        Implements the exception log convention for EventBus.
        A caller is expected to be within the except frame.

        Args:
            exc (Exception):    The exception to log

        Returns:
            None
        '''
        info.update(s_common.excinfo(exc))
        self.log(logging.ERROR, str(exc), **info)

class Waiter:
    '''
    A helper to wait for a given number of events on an EventBus.
    '''
    def __init__(self, bus, count, *names):
        self.bus = bus
        self.names = names
        self.count = count
        self.event = threading.Event()

        self.events = []

        for name in names:
            bus.on(name, self._onWaitEvent)

        if not names:
            bus.link(self._onWaitEvent)

    def _onWaitEvent(self, mesg):
        self.events.append(mesg)
        if len(self.events) >= self.count:
            self.event.set()

    def wait(self, timeout=None):
        '''
        Wait for the required number of events and return them
        or None on timeout.

        Example:

            evnts = waiter.wait(timeout=30)

            if evnts == None:
                handleTimedOut()
                return

            for evnt in evnts:
                doStuff(evnt)

        '''
        try:

            self.event.wait(timeout=timeout)
            if not self.event.is_set():
                return None

            return self.events

        finally:
            self.fini()

    def fini(self):

        for name in self.names:
            self.bus.off(name, self._onWaitEvent)

        if not self.names:
            self.bus.unlink(self._onWaitEvent)
