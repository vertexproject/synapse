import os
import sys
import signal
import asyncio
import contextlib
import multiprocessing

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.scope as s_scope

import synapse.tests.utils as s_t_utils

def block_processing(evt1):
    '''
    Function to make a base and call main().  Used as a Process target.

    Args:
        evt1 (multiprocessing.Event): event to twiddle
    '''
    async def main():

        base = await s_base.Base.anit()
        await base.addSignalHandlers()

        evt1.set()

        await base.waitfini()

    asyncio.run(main())
    sys.exit(137)

class Hehe(s_base.Base):

    async def __anit__(self, foo):
        await s_base.Base.__anit__(self)
        self.foo = foo
        self.bar = self.foo + 10
        self.posted = False

    async def postAnit(self):
        self.posted = True
        if self.foo == -1:
            raise s_exc.BadArg(mesg='boom')

class BaseTest(s_t_utils.SynTest):

    async def test_base_basics(self):
        base = await s_base.Base.anit()

        def foo(event):
            x = event[1].get('x')
            y = event[1].get('y')
            event[1]['ret'] = x + y

        base.on('woot', foo)

        event = await base.fire('woot', x=3, y=5, ret=[])
        self.eq(event[1]['ret'], 8)

        base00 = await s_base.Base.anit()
        base01 = await s_base.Base.anit()
        data = {}
        async def onfini():
            data['woot'] = True

        await base00.fini()
        base00.onfini(onfini)
        await asyncio.sleep(0)
        self.true(data.get('woot'))

        base00.onfini(base01)
        await asyncio.sleep(0)
        self.true(base01.isfini)

    async def test_base_anit(self):

        afoo = await Hehe.anit(20)
        self.eq(afoo.foo, 20)
        self.eq(afoo.bar, 30)
        self.true(afoo.posted)

        with self.raises(s_exc.BadArg) as cm:
            await Hehe.anit(-1)
        self.eq(cm.exception.get('mesg'), 'boom')

    async def test_coro_fini(self):

        event = asyncio.Event()

        async def setit():
            event.set()

        f = await s_base.Base.anit()
        async with f as f:
            f.onfini(setit)

        self.true(f.isfini)
        self.true(event.is_set())

    async def test_enter_context(self):
        state = None

        @contextlib.contextmanager
        def ctxtest():
            nonlocal state
            state = "before"
            yield state
            state = "after"

        @contextlib.asynccontextmanager
        async def actxtest():
            nonlocal state
            state = "before2"
            yield state
            state = "after2"

        async with await s_base.Base.anit() as base:
            await base.enter_context(ctxtest())
            self.eq("before", state)

        self.eq("after", state)

        async with await s_base.Base.anit() as base:
            await base.enter_context(actxtest())
            self.eq("before2", state)

        self.eq("after2", state)

    async def test_base_link(self):

        base1 = await s_base.Base.anit()
        base2 = await s_base.Base.anit()

        base1.link(base2.dist)

        data = {}

        async def woot(event):
            data['woot'] = True

        base2.on('woot', woot)

        await base1.fire('woot')

        self.true(data.get('woot'))

    async def test_base_unlink(self):

        base = await s_base.Base.anit()

        mesgs = []

        async def woot(mesg):
            mesgs.append(mesg)

        base.link(woot)

        await base.fire('haha')
        self.eq(len(mesgs), 1)

        base.unlink(woot)

        await base.fire('haha')
        self.eq(len(mesgs), 1)

        await base.fini()

    async def test_base_withfini(self):

        data = {'count': 0}

        def onfini():
            data['count'] += 1

        async with await s_base.Base.anit() as base:
            base.onfini(onfini)

        self.eq(data['count'], 1)

    async def test_base_finionce(self):

        data = {'count': 0}

        async def onfini():
            data['count'] += 1

        base = await s_base.Base.anit()
        base.onfini(onfini)

        await base.fini()
        await base.fini()

        self.eq(data['count'], 1)

    async def test_base_off(self):
        base = await s_base.Base.anit()

        data = {'count': 0}

        async def woot(mesg):
            data['count'] += 1

        base.on('hehe', woot)

        await base.fire('hehe')

        base.off('hehe', woot)

        await base.fire('hehe')

        await base.fini()

        self.eq(data['count'], 1)

    async def test_base_waiter(self):

        base0 = await s_base.Base.anit()

        wait0 = base0.waiter(3, 'foo:bar')

        await base0.fire('foo:bar')
        await base0.fire('foo:bar')
        await base0.fire('foo:bar')

        evts = await wait0.wait(timeout=3)
        self.eq(len(evts), 3)

        wait1 = base0.waiter(3, 'foo:baz')
        evts = await wait1.wait(timeout=0.1)
        self.none(evts)

        # Bare waiter test - uses the link() method on the Base
        # to receive all of the events from the Base.
        wait2 = s_base.Waiter(base0, 2)
        await base0.fire('hehe')
        await base0.fire('haha')
        evts = await wait2.wait(1)
        self.len(2, evts)

        with self.raises(s_exc.TimeOut):
            async with base0.waiter(1, 'newp', 'nuuh', timeout=0.01):
                pass

    async def test_baseref(self):

        bref = await s_base.BaseRef.anit()

        base0 = await s_base.Base.anit()
        base1 = await s_base.Base.anit()
        base2 = await s_base.Base.anit()

        bref.put('foo', base0)
        bref.put('bar', base1)
        bref.put('baz', base2)

        await base1.fini()
        self.nn(bref.get('foo'))
        self.none(bref.get('bar'))

        self.len(2, list(bref))

        self.true(bref.pop('baz') is base2)
        self.len(1, list(bref))

        await bref.fini()
        self.true(base0.isfini)

        await base2.fini()

    async def test_base_waitfini(self):
        loop = asyncio.get_running_loop()

        base = await s_base.Base.anit()

        self.false(await base.waitfini(timeout=0.1))

        async def callfini():
            await asyncio.sleep(0.1)
            await base.fini()

        loop.create_task(callfini())
        # actually wait...
        self.true(await base.waitfini(timeout=0.3))
        self.true(base.isfini)

        # bounce off the isfini block
        self.true(await base.waitfini(timeout=0.3))

    async def test_base_refcount(self):
        base = await s_base.Base.anit()

        self.eq(base.incref(), 2)

        self.eq(await base.fini(), 1)
        self.false(base.isfini)

        self.eq(await base.fini(), 0)
        self.true(base.isfini)

    async def test_baseref_gen(self):

        async with await s_base.BaseRef.anit() as refs:
            await self.asyncraises(s_exc.NoSuchCtor, refs.gen('woot'))

        async def ctor(name):
            return await s_base.Base.anit()

        async with await s_base.BaseRef.anit(ctor=ctor) as refs:

            self.none(refs.get('woot'))

            woot = await refs.gen('woot')
            self.eq(1, woot._syn_refs)

            self.nn(woot)
            self.true(await refs.gen('woot') is woot)
            self.eq(2, woot._syn_refs)

            await woot.fini()
            self.false(woot.isfini)
            self.true(refs.get('woot') is woot)
            self.eq(1, woot._syn_refs)

            await woot.fini()
            self.eq(0, woot._syn_refs)

            self.true(woot.isfini)
            self.false(refs.get('woot') is woot)
            self.eq(0, woot._syn_refs)

    async def test_baseref_items(self):

        bref = await s_base.BaseRef.anit()

        base0 = await s_base.Base.anit()
        base1 = await s_base.Base.anit()
        base2 = await s_base.Base.anit()

        bref.put('foo', base0)
        bref.put('bar', base1)
        bref.put('baz', base2)

        items = bref.items()
        self.isin(('foo', base0), items)
        self.isin(('bar', base1), items)
        self.isin(('baz', base2), items)

        await base1.fini()
        items = bref.items()
        self.isin(('foo', base0), items)
        self.isin(('baz', base2), items)

        await base2.fini()
        items = bref.items()
        self.isin(('foo', base0), items)

        await base0.fini()
        items = bref.items()
        self.eq(items, [])

        await bref.fini()
        items = bref.items()
        self.eq(items, [])

    def test_base_main_sigterm(self):
        self.thisHostMustNot(platform='windows')
        # We have no reliable way to test this on windows
        self.thisHostMustNot(platform='darwin')
        # This test fails on darwin in circleci

        ctx = multiprocessing.get_context('spawn')

        evt1 = ctx.Event()

        proc = ctx.Process(target=block_processing, args=(evt1,))
        proc.start()

        self.true(evt1.wait(timeout=30))
        os.kill(proc.pid, signal.SIGTERM)
        proc.join(timeout=10)
        self.eq(proc.exitcode, 137)

    def test_base_main_sigint(self):
        self.thisHostMustNot(platform='windows')
        # We have no reliable way to test this on windows
        self.thisHostMustNot(platform='darwin')
        # This test fails on darwin in circleci

        ctx = multiprocessing.get_context('spawn')

        evt1 = ctx.Event()

        proc = ctx.Process(target=block_processing, args=(evt1,))
        proc.start()

        self.true(evt1.wait(timeout=30))
        os.kill(proc.pid, signal.SIGINT)

        proc.join(timeout=10)
        self.eq(proc.exitcode, 137)

    async def test_onwith(self):
        base = await s_base.Base.anit()
        l0 = []
        l1 = []

        def onHehe0(mesg):
            l0.append(mesg)

        def onHehe1(mesg):
            l1.append(mesg)

        base.on('hehe', onHehe0)

        # Temporarily set the 'hehe' callback
        with base.onWith('hehe', onHehe1) as e:
            self.true(e is base)
            await base.fire('hehe')
            self.len(1, l0)
            self.len(1, l1)

        # subsequent fires do not call onHehe1
        await base.fire('hehe')
        self.len(2, l0)
        self.len(1, l1)

    async def test_base_mixin(self):

        data = []

        class M1(s_base.Base):
            async def __anit__(self):
                await s_base.Base.__anit__(self)
                self.m1fini = asyncio.Event()
                self.onfini(self.m1fini.set)
                self.on('event', self._M1OnEvent)

            def _M1OnEvent(self, event):
                data.append(event)

        class M2(s_base.Base):
            async def __anit__(self):
                await s_base.Base.__anit__(self)
                self.m2fini = asyncio.Event()
                self.onfini(self.m2fini.set)
                self.on('event', self._M2OnEvent)

            def _M2OnEvent(self, event):
                data.append(event)

        class MixedBases(M1, M2):

            async def __anit__(self):
                # Initialize our mixins
                await M1.__anit__(self)
                await M2.__anit__(self)

        mixed = await MixedBases.anit()
        self.false(mixed.m1fini.is_set())
        self.false(mixed.m2fini.is_set())
        self.len(2, mixed._fini_funcs)
        self.len(2, mixed._syn_funcs.get('event'))
        self.eq(mixed._syn_refs, 1)

        await mixed.fire('event', key=1)
        self.len(2, data)

        await mixed.fini()

        self.true(mixed.m1fini.is_set())
        self.true(mixed.m2fini.is_set())

    async def test_base_schedgenr(self):
        async def goodgenr():
            yield 'foo'
            await asyncio.sleep(0)
            yield 'bar'
            await asyncio.sleep(0)

        async def badgenr():
            yield 'foo'
            await asyncio.sleep(0)
            raise s_exc.SynErr(mesg='rando')

        async def slowgenr():
            yield 'foo'
            await asyncio.sleep(5)
            yield 'bar'

        event = asyncio.Event()

        async def slowtask():
            g = s_base.schedGenr(slowgenr())
            item = await g.__anext__()
            self.eq('foo', item)
            event.set()
            item = await g.__anext__()

        items = [item async for item in s_base.schedGenr(goodgenr())]
        self.eq(items, ['foo', 'bar'])
        await self.agenraises(s_exc.SynErr, s_base.schedGenr(badgenr()))

        async with await s_base.Base.anit() as base:
            task = base.schedCoro(slowtask())
            self.true(await s_coro.event_wait(event, 3.0))

        await self.asyncraises(asyncio.CancelledError, task)

    async def test_lib_base_scope(self):

        # Simple test with a single scope stack.

        data = {}

        async def func1(key):
            valu = s_scope.get(key, defval=None)
            data[key] = valu
            # Get / set in our scope works fine
            s_scope.set('hehe', 'newp')
            self.eq(s_scope.get('hehe'), 'newp')

        async with await s_base.Base.anit() as base:
            vals = {'foo': 'bar'}
            with s_scope.enter(vals=vals):  # Ensure we have a known value in the scope
                task = base.schedCoro(func1('foo'))
                await task

        # The scoped data was accessible in the task
        self.eq(data.get('foo'), 'bar')

        # The scope data set in the task is not present outside of it.
        self.none(s_scope.get('hehe'))

        # Nested scopes across multiple tasks
        data = {}

        async def func2(key):
            valu = s_scope.get(key, defval=None)
            data[key] = valu
            # Get / set in our scope works fine
            s_scope.set('hehe', 'newp')
            self.eq(s_scope.get('hehe'), 'newp')

        async def func3(bobj, key, valu):
            s_scope.set(key, valu)
            task = bobj.schedCoro(func2(key))
            await task
            self.none(s_scope.get('hehe'))

        async with await s_base.Base.anit() as base:
            vals = {'foo': 'bar'}
            with s_scope.enter(vals=vals):  # Ensure we have a known value in the scope
                task = base.schedCoro(func3(base, 'beep', 'boop'))
                await task

        # The scoped data was accessible in the task
        self.eq(data.get('beep'), 'boop')

        # The scope data set in the task is not present outside of it.
        self.none(s_scope.get('hehe'))
