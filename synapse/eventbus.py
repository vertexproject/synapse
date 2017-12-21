import gc
import atexit
import signal
import logging
import threading
import contextlib
import collections

import synapse.common as s_common

import synapse.lib.reflect as s_reflect
import synapse.lib.thishost as s_thishost

logger = logging.getLogger(__name__)
finlock = threading.RLock()

def _fini_atexit(): # pragma: no cover

    for item in gc.get_objects():

        if not isinstance(item, EventBus):
            continue

        if not item._fini_atexit:
            continue

        try:

            item.fini()

        except Exception as e:
            logger.exception('atexit fini fail: %r' % (item,))

atexit.register(_fini_atexit)

class EventBus(object):
    '''
    A synapse EventBus provides an easy way manage callbacks.
    '''
    def __init__(self):
        self.isfini = False
        self.finievt = None
        self.finlock = finlock

        self._syn_funcs = collections.defaultdict(list)

        self._syn_refs = 1  # one ref for the ctor
        self._syn_links = []
        self._fini_funcs = []
        self._fini_atexit = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.fini()

    def incref(self):
        '''
        Increment the reference count for this event bus.
        This API may be optionally used to control fini().
        '''
        with self.finlock:
            self._syn_refs += 1
            return self._syn_refs

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

        Examples:

            Add a callback function and fire it:

                def baz(event):
                    x = event[1].get('x')
                    y = event[1].get('y')
                    return x + y

                d.on('foo', baz, x=10)

                # this fire triggers baz...
                d.fire('foo', x=10, y=20)

                # this fire does not ( due to filt )
                d.fire('foo', x=30, y=20)

        Returns:
            None:
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
        if self.isfini:
            return event

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
        if self.isfini:
            return ()

        ret = []
        for func, filt in self._syn_funcs.get(mesg[0], ()):

            try:

                if any(True for k, v in filt if mesg[1].get(k) != v):
                    continue

                ret.append(func(mesg))

            except Exception as e:
                logger.exception('Ebus %s error with mesg %s', self, mesg)

        for func in self._syn_links:
            try:
                ret.append(func(mesg))
            except Exception as e:
                logger.exception('Ebus %s error with mesg %s', self, mesg)

        return ret

    def fini(self):
        '''
        Fire the 'fini' handlers and set self.isfini.

        Example:

            d.fini()

        '''
        with finlock:

            if self.isfini:
                return 0

            self._syn_refs -= 1
            if self._syn_refs > 0:
                return self._syn_refs

            self.isfini = True
            fevt = self.finievt

        for func in self._fini_funcs:
            try:
                func()
            except Exception as e:
                logger.exception('Ebus %s error during fini function', self)

        # explicitly release the handlers
        self._syn_funcs.clear()
        del self._fini_funcs[:]

        if fevt is not None:
            fevt.set()

        return 0

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
        with self.finlock:

            if self.isfini:
                return True

            if self.finievt is None:
                self.finievt = threading.Event()

        return self.finievt.wait(timeout=timeout)

    def main(self):
        '''
        Helper function to block until shutdown ( and handle ctrl-c and SIGTERM).

        Examples:
            Run a event bus, wait until main() has returned, then do other stuff::

                foo = EventBus()
                foo.main()
                dostuff()

        Notes:
            This does fire a 'ebus:main' event prior to entering the
            waitfini() loop.

        Returns:
            None
        '''
        def sighandler(signum, frame):
            print('Caught signal {}, shutting down'.format(signum))
            self.fini()

        try:
            signal.signal(signal.SIGTERM, sighandler)
        except Exception as e:  # pragma: no cover
            logger.exception('Unable to register SIGTERM handler in eventbus.')

        try:
            self.fire('ebus:main')
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

    @contextlib.contextmanager
    def onWith(self, evnt, func, **filts):
        '''
        A context manager which can be used to add a callback and remove it when
        using a ``with`` statement.

        Args:
            evnt (str):         An event name
            func (function):    A callback function to receive event tufo
            **filts:            Optional positive filter values for the event tuple.

        Examples:

            Temporarily add the baz callback function and use it.

                def baz(event):
                    x = event[1].get('x')
                    y = event[1].get('y')
                    return x + y

                with d.onWith('foo', baz, x=10):
                    # this fire triggers baz...
                    d.fire('foo', x=10, y=20)

                # this does NOT fire triggers baz since it is outside
                # of the context manager.
                d.fire('foo', x=10, y=30)

        '''
        self.on(evnt, func, **filts)
        # Allow exceptions to propagate during the context manager
        # but ensure we cleanup our temporary callback
        try:
            yield self
        finally:
            self.off(evnt, func)

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

class BusRef(EventBus):
    '''
    An object for managing multiple EventBus instances.
    '''
    def __init__(self, ctor=None):
        EventBus.__init__(self)
        self.ctor = ctor
        self.lock = threading.Lock()
        self.ebus_by_name = {}
        self.onfini(self._onBusRefFini)

    def _onBusRefFini(self):
        [ebus.fini() for ebus in self.vals()]

    def put(self, name, ebus):
        '''
        Add an EventBus (or sub-class) to the BusRef by name.

        Args:
            name (str): The name/iden of the EventBus
            ebus (EventBus): The EventBus instance

        Returns:
            (None)
        '''
        def fini():
            self.ebus_by_name.pop(name, None)

        ebus.onfini(fini)
        self.ebus_by_name[name] = ebus

    def pop(self, name):
        '''
        Remove and return an EventBus from the BusRef.

        Args:
            name (str): The name/iden of the EventBus instance

        Returns:
            (EventBus): The named event bus ( or None )
        '''
        return self.ebus_by_name.pop(name, None)

    def get(self, name):
        '''
        Retrieve an EventBus instance by name.

        Args:
            name (str): The name/iden of the EventBus

        Returns:
            (EventBus): The EventBus instance (or None)
        '''
        return self.ebus_by_name.get(name)

    def gen(self, name):
        '''
        Atomically get/gen an EventBus and incref.
        (requires ctor during BusRef init)

        Args:
            name (str): The name/iden of the EventBus instance.
        '''
        if self.ctor is None:
            raise s_common.NoSuchCtor(name=name, mesg='BusRef.gen() requires ctor')

        with self.lock:

            ebus = self.ebus_by_name.get(name)

            if ebus is None:
                ebus = self.ctor(name)

                if ebus is not None:

                    def fini():
                        self.ebus_by_name.pop(name, None)

                    ebus.onfini(fini)
                    self.ebus_by_name[name] = ebus

            else:
                ebus.incref()

            return ebus

    def vals(self):
        return list(self.ebus_by_name.values())

    def __iter__(self):
        # make a copy during iteration to prevent dict
        # change during iteration exceptions
        return iter(list(self.ebus_by_name.values()))
