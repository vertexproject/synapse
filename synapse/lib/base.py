import gc
import atexit
import signal
import inspect
import asyncio
import logging
import threading
import collections

import synapse.exc as s_exc

import synapse.lib.coro as s_coro
import synapse.lib.threads as s_threads

logger = logging.getLogger(__name__)

def _fini_atexit(): # pragma: no cover

    for item in gc.get_objects():

        if not isinstance(item, Base):
            continue

        if item.isfini:
            continue

        if not item._fini_atexit:
            if __debug__:
                logger.debug(f'At exit: Missing fini for %r', item)
            continue

        try:
            if __debug__:
                logger.debug('At exit: Calling fini for %r', item)
            rv = item.fini()
            if s_coro.iscoro(rv):
                # Try to run the fini on its loop
                loop = item.loop
                if not loop.is_running():
                    continue
                loop.create_task(rv)

        except Exception as e:
            logger.exception('atexit fini fail: %r' % (item,))

atexit.register(_fini_atexit)

class Base:
    '''
    Base class for Synapse objects.

    Acts as an observable, enables async init and fini.

    Example:

        class Foo(Base):

            async def __anit__(self, x, y):

                await Base.__anit__(self)

                await stuff(x, y)

        foo = await Foo.anit(10)

    Note:
        One should not create instances directly via its initializer, i.e. Base().  One shall always use the class
        method anit.
    '''
    def __init__(self):
        assert inspect.stack()[1].function == 'anit', 'Objects from Base must be constructed solely via "anit"'

    @classmethod
    async def anit(cls, *args, **kwargs):
        self = cls()
        await self.__anit__(*args, **kwargs)
        return self

    async def __anit__(self):

        self.loop = asyncio.get_running_loop()
        if __debug__:
            self.tid = s_threads.iden()
        self.isfini = False
        self.anitted = True  # For assertion purposes
        self.entered = False
        self.exitinfo = None
        self.finievt = None

        self.exitok = None
        self.entered = False
        self.exitinfo = None

        self._syn_funcs = collections.defaultdict(list)

        self._syn_refs = 1  # one ref for the ctor
        self._syn_links = []
        self._fini_funcs = []
        self._fini_atexit = False
        self._active_tasks = set()  # the free running tasks associated with me

    def onfini(self, func):
        '''
        Add a function or coroutine function to be called on fini().
        '''
        assert self.anitted
        self._fini_funcs.append(func)

    async def __aenter__(self):
        assert asyncio.get_running_loop() == self.loop
        self.entered = True
        return self

    async def __aexit__(self, exc, cls, tb):
        assert asyncio.get_running_loop() == self.loop

        self.exitok = cls is None
        self.exitinfo = (exc, cls, tb)
        await self.fini()

    def _isExitExc(self):
        # if entered but not exited *or* exitinfo has exc
        if not self.entered:
            return False

        if self.exitinfo is None:
            return True

        return self.exitinfo[0] is not None

    def incref(self):
        '''
        Increment the reference count for this base.  This API may be optionally used to control fini().
        '''
        self._syn_refs += 1
        return self._syn_refs

    def link(self, func):
        '''
        Add a callback function to receive *all* events.

        Example:

            base1 = Base()
            base2 = Base()

            base1.link( base2.dist )

            # all events on base1 are also propagated on base2

        '''
        self._syn_links.append(func)

    def unlink(self, func):
        '''
        Remove a callback function previously added with link()

        Example:

            base.unlink( callback )

        '''
        if func in self._syn_links:
            self._syn_links.remove(func)

    def on(self, evnt, func, **filts):
        '''
        Add an base function callback for a specific event with optional filtering.  If the function returns a
        coroutine, it will be awaited.

        Args:
            evnt (str):         An event name
            func (function):    A callback function to receive event tufo
            **filts:            Optional positive filter values for the event tuple.

        Examples:

            Add a callback function and fire it:

                async def baz(event):
                    x = event[1].get('x')
                    y = event[1].get('y')
                    return x + y

                d.on('foo', baz, x=10)

                # this fire triggers baz...
                await d.fire('foo', x=10, y=20)

                # this fire does not ( due to filt )
                await d.fire('foo', x=30, y=20)

        Returns:
            None:
        '''
        self._syn_funcs[evnt].append((func, tuple(filts.items())))

    def off(self, evnt, func):
        '''
        Remove a previously registered event handler function.

        Example:

            base.off( 'foo', onFooFunc )

        '''
        funcs = self._syn_funcs.get(evnt)
        if funcs is not None:

            for i in range(len(funcs)):

                if funcs[i][0] == func:
                    funcs.pop(i)
                    break

            if not funcs:
                self._syn_funcs.pop(evnt, None)

    async def fire(self, evtname, **info):
        '''
        Fire the given event name on the Base.
        Returns a list of the return values of each callback.

        Example:

            for ret in d.fire('woot',foo='asdf'):
                print('got: %r' % (ret,))

        '''
        event = (evtname, info)
        if self.isfini:
            return event

        await self.dist(event)
        return event

    async def dist(self, mesg):
        '''
        Distribute an existing event tuple.

        Args:
            mesg ((str,dict)):  An event tuple.

        Example:

            await base.dist( ('foo',{'bar':'baz'}) )

        '''
        if self.isfini:
            return ()

        ret = []
        for func, filt in self._syn_funcs.get(mesg[0], ()):

            try:

                if any(True for k, v in filt if mesg[1].get(k) != v):
                    continue

                retn = await s_coro.ornot(func, mesg)
                ret.append(retn)

            except Exception as e:
                logger.exception('base %s error with mesg %s', self, mesg)

        for func in self._syn_links:
            try:
                ret.append(await func(mesg))
            except Exception as e:
                logger.exception('base %s error with mesg %s', self, mesg)

        return ret

    def _iAmLoop(self):
        '''
        Return True if the current thread is same loop anit was called on

        Returns:
            (bool)

        '''
        return threading.get_ident() == self.ident

    async def _kill_active_tasks(self):
        for task in self._active_tasks.copy():
            task.cancel()
            try:
                await task
            except Exception:
                # The taskDone callback will emit the exception.  No need to repeat
                pass

    async def fini(self):
        '''
        Shut down the object and notify any onfini() coroutines.

        Returns:
            Remaining ref count
        '''
        assert self.anitted, 'Base object initialized improperly.  Must use Base.anit class method.'

        if self.isfini:
            return

        assert s_threads.iden() == self.tid

        self._syn_refs -= 1
        if self._syn_refs > 0:
            return self._syn_refs

        self.isfini = True

        fevt = self.finievt

        if fevt is not None:
            fevt.set()

        await self._kill_active_tasks()

        for fini in self._fini_funcs:
            try:
                await s_coro.ornot(fini)
            except Exception as e:
                logger.exception('fini failed')

        self._syn_funcs.clear()
        self._fini_funcs.clear()
        return 0

    async def waitfini(self, timeout=None):
        '''
        Wait for the base to fini()

        Returns:
            None if timed out, True if fini happened

        Example:

            base.waitfini(timeout=30)

        '''

        if self.isfini:
            return True

        if self.finievt is None:
            self.finievt = asyncio.Event(loop=self.loop)

        return await s_coro.event_wait(self.finievt, timeout)

    def schedCoro(self, coro):
        '''
        Schedules a free-running coroutine to run on this base's event loop.  Kills the coroutine if Base is fini'd.
        It does not pend on coroutine completion.

        Precondition:
            This function is *not* threadsafe and must be run on the Base's event loop

        Returns:
            An asyncio.Task

        '''
        assert asyncio.get_running_loop() == self.loop

        task = self.loop.create_task(coro)

        def taskDone(task):
            self._active_tasks.remove(task)
            try:
                task.result()
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception('Task scheduled through Base.schedCoro raised exception')

        task.add_done_callback(taskDone)
        self._active_tasks.add(task)

        return task

    def schedCoroSafe(self, coro):
        '''
        Schedules a coroutine to run as soon as possible on the same event loop that this Base is running on

        This function does *not* pend on coroutine completion.

        Note:
            This method may be run outside the event loop on a different thread.
        '''
        self.loop.call_soon_threadsafe(self.schedCoro, coro)

    def main(self):
        '''
        Helper function to block until shutdown ( and handle ctrl-c and SIGTERM).

        Examples:
            Run a base, wait until main() has returned, then do other stuff::

                foo = Base()
                foo.main()
                dostuff()

        Notes:
            This does fire a 'ebus:main' event prior to entering the
            waitfini() loop.

        Returns:
            None
        '''
        doneevent = threading.Event()
        self.onfini(doneevent.set)

        async def sighandler():
            print('Caught SIGTERM, shutting down')
            await self.fini()

        def handler():
            asyncio.run_coroutine_threadsafe(sighandler(), loop=self.loop)

        try:
            self.loop.add_signal_handler(signal.SIGTERM, handler)
        except Exception as e:  # pragma: no cover
            logger.exception('Unable to register SIGTERM handler.')

        async def asyncmain():
            await self.fire('ebus:main')

        asyncio.run_coroutine_threadsafe(asyncmain(), loop=self.loop)

        try:
            doneevent.wait()

        except KeyboardInterrupt as e:
            print('ctrl-c caught: shutting down')

        finally:
            # Avoid https://bugs.python.org/issue34680 by removing handler before closing down
            self.loop.remove_signal_handler(signal.SIGTERM)

    def waiter(self, count, *names):
        '''
        Construct and return a new Waiter for events on this base.

        Example:

            # wait up to 3 seconds for 10 foo:bar events...

            waiter = base.waiter(10,'foo:bar')

            # .. fire thread that will cause foo:bar events

            events = waiter.wait(timeout=3)

            if events == None:
                # handle the timout case...

            for event in events:
                # parse the events if you need...

        NOTE: use with caution... it's easy to accidentally construct
              race conditions with this mechanism ;)

        '''
        return Waiter(self, count, self.loop, *names)

    # async def log(self, level, mesg, **info):
    #     '''
    #     Implements the log event convention for a Base.

    #     Args:
    #         level (int):  A python logger level for the event
    #         mesg (str):   A log message
    #         **info:       Additional log metadata

    #     '''
    #     info['time'] = s_common.now()
    #     info['host'] = s_thishost.get('hostname')

    #     info['level'] = level
    #     info['class'] = self.__class__.__name__

    #     await self.fire('log', mesg=mesg, **info)

    # async def exc(self, exc, **info):
    #     '''
    #     Implements the exception log convention for Base.
    #     A caller is expected to be within the except frame.

    #     Args:
    #         exc (Exception):    The exception to log

    #     Returns:
    #         None
    #     '''
    #     info.update(s_common.excinfo(exc))
    #     await self.log(logging.ERROR, str(exc), **info)

class Waiter:
    '''
    A helper to wait for a given number of events on a Base.
    '''
    def __init__(self, base, count, *names):
        self.base = base
        self.names = names
        self.count = count
        self.event = asyncio.Event(loop=base.loop)

        self.events = []

        for name in names:
            base.on(name, self._onWaitEvent)

        if not names:
            base.link(self._onWaitEvent)

    def _onWaitEvent(self, mesg):
        self.events.append(mesg)
        if len(self.events) >= self.count:
            self.event.set()

    async def wait(self, timeout=None):
        '''
        Wait for the required number of events and return them or None on timeout.

        Example:

            evnts = waiter.wait(timeout=30)

            if evnts == None:
                handleTimedOut()
                return

            for evnt in evnts:
                doStuff(evnt)

        '''
        try:

            retn = await s_coro.event_wait(self.event, timeout)
            if not retn:
                return None

            return self.events

        finally:
            self.fini()

    def fini(self):

        for name in self.names:
            self.base.off(name, self._onWaitEvent)

        if not self.names:
            self.base.unlink(self._onWaitEvent)
        del self.event

class BaseRef(Base):
    '''
    An object for managing multiple Base instances by name.
    '''
    async def __anit__(self, ctor=None):
        await Base.__anit__(self)
        self.ctor = ctor
        self.base_by_name = {}
        self.onfini(self._onBaseRefFini)

    async def _onBaseRefFini(self):
        await asyncio.gather(*[base.fini() for base in self.vals()], loop=self.loop)

    def put(self, name, base):
        '''
        Add a Base (or sub-class) to the BaseRef by name.

        Args:
            name (str): The name/iden of the Base
            base (Base): The Base instance

        Returns:
            (None)
        '''
        async def fini():
            if self.base_by_name.get(name) is base:
                self.base_by_name.pop(name, None)

        # Remove myself from BaseRef when I fini
        base.onfini(fini)
        self.base_by_name[name] = base

    def pop(self, name):
        '''
        Remove and return a Base from the BaseRef.

        Args:
            name (str): The name/iden of the Base instance

        Returns:
            (Base): The named base ( or None )
        '''
        return self.base_by_name.pop(name, None)

    def get(self, name):
        '''
        Retrieve a Base instance by name.

        Args:
            name (str): The name/iden of the Base

        Returns:
            (Base): The Base instance (or None)
        '''
        return self.base_by_name.get(name)

    async def gen(self, name):
        '''
        Atomically get/gen a Base and incref.
        (requires ctor during BaseRef init)

        Args:
            name (str): The name/iden of the Base instance.
        '''
        if self.ctor is None:
            raise s_exc.NoSuchCtor(name=name, mesg='BaseRef.gen() requires ctor')

        base = self.base_by_name.get(name)

        if base is None:
            base = await self.ctor(name)
            self.put(name, base)
        else:
            base.incref()

        return base

    def vals(self):
        return list(self.base_by_name.values())

    def items(self):
        return list(self.base_by_name.items())

    def __iter__(self):
        # make a copy during iteration to prevent dict
        # change during iteration exceptions
        return iter(list(self.base_by_name.values()))
