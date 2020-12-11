import gc
import os
import atexit
import signal
import asyncio
import inspect
import logging
import weakref
import contextlib
import collections

if __debug__:
    import traceback

import synapse.exc as s_exc
import synapse.glob as s_glob

import synapse.lib.coro as s_coro

logger = logging.getLogger(__name__)

OMIT_FINI_WARNS = os.environ.get('SYNDEV_OMIT_FINI_WARNS', False)

def _fini_atexit(): # pragma: no cover

    for item in gc.get_objects():

        if not isinstance(item, Base):
            continue

        if not item.anitted:
            continue

        if item.isfini:
            continue

        if not item._fini_atexit and not OMIT_FINI_WARNS:
            if __debug__:
                logger.debug(f'At exit: Missing fini for {item}')
                for depth, call in enumerate(item.call_stack[:-2]):
                    logger.debug(f'{depth+1:3}: {call.strip()}')
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

        except Exception:
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
        self.anitted = False
        assert inspect.stack()[1].function == 'anit', 'Objects from Base must be constructed solely via "anit"'

    @classmethod
    async def anit(cls, *args, **kwargs):

        # sneak in a quick loop check here for convenience
        if s_glob._glob_loop is None:
            s_glob.initloop()

        self = cls()

        try:

            await self.__anit__(*args, **kwargs)

        except (asyncio.CancelledError, Exception):
            if self.anitted:
                await self.fini()

            raise

        try:
            await self.postAnit()
        except (asyncio.CancelledError, Exception):
            logger.exception('Error during postAnit callback.')
            await self.fini()
            raise

        return self

    async def __anit__(self):

        self.loop = asyncio.get_running_loop()
        if __debug__:
            import synapse.lib.threads as s_threads  # avoid import cycle
            self.tid = s_threads.iden()
            self.call_stack = traceback.format_stack()  # For cleanup debugging

        if object.__getattribute__(self, 'anitted') is True:
            # The Base has already been anitted. This allows a class to treat
            # multiple Base objects as a mixin and __anit__ themselves without
            # smashing fini or event handlers from the others.
            return

        self.isfini = False
        self.anitted = True  # For assertion purposes
        self.finievt = None
        self.entered = False

        # hold a weak ref to other bases we should fini if they
        # are still around when we go down...
        self.tofini = weakref.WeakSet()

        self._syn_funcs = collections.defaultdict(list)

        self._syn_refs = 1  # one ref for the ctor
        self._syn_links = []
        self._fini_funcs = []
        self._fini_atexit = False
        self._active_tasks = set()  # the free running tasks associated with me

    async def postAnit(self):
        '''
        Method called after self.__anit__() has completed, but before anit() returns the object to the caller.
        '''
        pass

    async def enter_context(self, item):
        '''
        Modeled on Python's contextlib.ExitStack.enter_context.  Enters a new context manager and adds its __exit__()
        and __aexit__ method to its onfini handlers.

        Returns:
            The result of item’s own __aenter__ or __enter__() method.
        '''
        async def fini():
            meth = getattr(item, '__aexit__', None)
            if meth is not None:
                return await meth(None, None, None)

            meth = getattr(item, '__exit__', None)
            if meth is not None:
                return meth(None, None, None)

        self.onfini(fini)

        entr = getattr(item, '__aenter__', None)
        if entr is not None:
            async def fini():
                await item.__aexit__(None, None, None)
            self.onfini(fini)
            return await entr()

        entr = getattr(item, '__enter__', None)
        assert entr is not None

        async def fini():
            item.__exit__(None, None, None)
        self.onfini(fini)
        return entr()

    def onfini(self, func):
        '''
        Add a function/coroutine/Base to be called on fini().
        '''
        if isinstance(func, Base):
            self.tofini.add(func)
            return

        assert self.anitted
        self._fini_funcs.append(func)

    async def __aenter__(self):
        assert asyncio.get_running_loop() == self.loop
        self.entered = True
        return self

    async def __aexit__(self, exc, cls, tb):
        # Either there should be no running loop or we shall be on the right one
        try:
            assert asyncio.get_running_loop() == self.loop
        except RuntimeError:
            pass

        await self.fini()

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

    def on(self, evnt, func, base=None):
        '''
        Add an base function callback for a specific event with optional filtering.  If the function returns a
        coroutine, it will be awaited.

        Args:
            evnt (str):         An event name
            func (function):    A callback function to receive event tufo

        Examples:

            Add a callback function and fire it:

                async def baz(event):
                    x = event[1].get('x')
                    y = event[1].get('y')
                    return x + y

                d.on('foo', baz)

                # this fire triggers baz...
                await d.fire('foo', x=10, y=20)

        Returns:
            None:
        '''
        funcs = self._syn_funcs[evnt]
        if func in funcs:
            return

        funcs.append(func)

        if base is not None:

            def fini():
                self.off(evnt, func)

            base.onfini(fini)

    def off(self, evnt, func):
        '''
        Remove a previously registered event handler function.

        Example:

            base.off( 'foo', onFooFunc )

        '''
        funcs = self._syn_funcs.get(evnt)
        if funcs is None:
            return

        try:
            funcs.remove(func)
        except ValueError:
            pass

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
        for func in self._syn_funcs.get(mesg[0], ()):

            try:
                ret.append(await s_coro.ornot(func, mesg))
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception:
                logger.exception('base %s error with mesg %s', self, mesg)

        for func in self._syn_links:
            try:
                ret.append(await s_coro.ornot(func, mesg))
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception:
                logger.exception('base %s error with mesg %s', self, mesg)

        return ret

    async def _kill_active_tasks(self):

        if not self._active_tasks:
            return

        for task in self._active_tasks.copy():

            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                # The taskDone callback will emit the exception.  No need to repeat
                pass

    async def fini(self):
        '''
        Shut down the object and notify any onfini() coroutines.

        Returns:
            Remaining ref count
        '''
        assert self.anitted, f'{self.__class__.__name__} initialized improperly.  Must use Base.anit class method.'

        if self.isfini:
            return

        if __debug__:
            import synapse.lib.threads as s_threads  # avoid import cycle
            assert s_threads.iden() == self.tid

        self._syn_refs -= 1
        if self._syn_refs > 0:
            return self._syn_refs

        self.isfini = True

        for base in list(self.tofini):
            await base.fini()

        await self._kill_active_tasks()

        for fini in self._fini_funcs:
            try:
                await s_coro.ornot(fini)
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                raise
            except Exception:
                logger.exception(f'{self} - fini function failed: {fini}')

        self._syn_funcs.clear()
        self._fini_funcs.clear()

        fevt = self.finievt

        if fevt is not None:
            fevt.set()

        return 0

    @contextlib.contextmanager
    def onWith(self, evnt, func):
        '''
        A context manager which can be used to add a callback and remove it when
        using a ``with`` statement.

        Args:
            evnt (str):         An event name
            func (function):    A callback function to receive event tufo
        '''
        self.on(evnt, func)
        # Allow exceptions to propagate during the context manager
        # but ensure we cleanup our temporary callback
        try:
            yield self
        finally:
            self.off(evnt, func)

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
            self.finievt = asyncio.Event()

        return await s_coro.event_wait(self.finievt, timeout)

    def schedCoro(self, coro):
        '''
        Schedules a free-running coroutine to run on this base's event loop.  Kills the coroutine if Base is fini'd.
        It does not pend on coroutine completion.

        Precondition:
            This function is *not* threadsafe and must be run on the Base's event loop

        Returns:
            asyncio.Task: An asyncio.Task object.

        '''
        import synapse.lib.provenance as s_provenance  # avoid import cycle

        if __debug__:
            assert inspect.isawaitable(coro)
            import synapse.lib.threads as s_threads  # avoid import cycle
            assert s_threads.iden() == self.tid

        task = self.loop.create_task(coro)

        # In rare cases, (Like this function being triggered from call_soon_threadsafe), there's no task context
        if asyncio.current_task():
            s_provenance.dupstack(task)

        def taskDone(task):
            self._active_tasks.remove(task)
            try:
                if not task.done():
                    task.result()
            except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
                pass
            except Exception:
                logger.exception('Task %s scheduled through Base.schedCoro raised exception', task)

        self._active_tasks.add(task)
        task.add_done_callback(taskDone)

        return task

    def schedCallSafe(self, func, *args, **kwargs):
        '''
        Schedule a function to run as soon as possible on the same event loop that this Base is running on.

        This function does *not* pend on the function completion.

        Args:
            func:
            *args:
            **kwargs:

        Notes:
            This method may be called from outside of the event loop on a different thread.

        Returns:
            concurrent.futures.Future: A Future representing the eventual function execution.
        '''
        def real():
            return func(*args, **kwargs)
        return self.loop.call_soon_threadsafe(real)

    def schedCoroSafe(self, coro):
        '''
        Schedules a coroutine to run as soon as possible on the same event loop that this Base is running on.

        This function does *not* pend on coroutine completion.

        Notes:
            This method may be run outside the event loop on a different thread.

        Returns:
            concurrent.futures.Future: A Future representing the eventual coroutine execution.
        '''
        return self.loop.call_soon_threadsafe(self.schedCoro, coro)

    def schedCoroSafePend(self, coro):
        '''
        Schedules a coroutine to run as soon as possible on the same event loop that this Base is running on

        Note:
            This method may *not* be run inside an event loop
        '''
        if __debug__:
            import synapse.lib.threads as s_threads  # avoid import cycle
            assert s_threads.iden() != self.tid

        task = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return task.result()

    async def addSignalHandlers(self):
        '''
        Register SIGTERM/SIGINT signal handlers with the ioloop to fini this object.
        '''

        def sigterm():
            print('Caught SIGTERM, shutting down.')
            asyncio.create_task(self.fini())

        def sigint():
            print('Caught SIGINT, shutting down.')
            asyncio.create_task(self.fini())

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, sigint)
        loop.add_signal_handler(signal.SIGTERM, sigterm)

    async def main(self):
        '''
        Helper function to setup signal handlers for this base as the main object.
        ( use base.waitfini() to block )

        NOTE: This API may only be used when the ioloop is *also* the main thread.
        '''
        await self.addSignalHandlers()
        return await self.waitfini()

    def waiter(self, count, *names):
        '''
        Construct and return a new Waiter for events on this base.

        Example:

            # wait up to 3 seconds for 10 foo:bar events...

            waiter = base.waiter(10,'foo:bar')

            # .. fire thread that will cause foo:bar events

            events = await waiter.wait(timeout=3)

            if events == None:
                # handle the timeout case...

            for event in events:
                # parse the events if you need...

        NOTE: use with caution... it's easy to accidentally construct
              race conditions with this mechanism ;)

        '''
        return Waiter(self, count, self.loop, *names)

class Waiter:
    '''
    A helper to wait for a given number of events on a Base.
    '''
    def __init__(self, base, count, *names):
        self.base = base
        self.names = names
        self.count = count
        self.event = asyncio.Event()

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
        await asyncio.gather(*[base.fini() for base in self.vals()])

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

async def schedGenr(genr, maxsize=100):
    '''
    Schedule a generator to run on a separate task and yield results to this task (pipelined generator).
    '''
    q = asyncio.Queue(maxsize=maxsize)

    async def genrtask(base):
        try:
            async for item in genr:
                await q.put((True, item))

            await q.put((False, None))

        except asyncio.CancelledError:  # pragma: no cover  TODO:  remove once >= py 3.8 only
            raise

        except Exception:
            if not base.isfini:
                await q.put((False, None))
            raise

    async with await Base.anit() as base:

        task = base.schedCoro(genrtask(base))

        while not base.isfini:

            ok, retn = await q.get()

            if ok:
                yield retn
                # since we are a pipeline, yield every time...
                await asyncio.sleep(0)
                continue

            await task
            return

async def main(coro): # pragma: no cover
    base = await coro
    if isinstance(base, Base):
        async with base:
            await base.main()
