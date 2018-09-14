import os
import sys
import signal
import asyncio
<<<<<<< HEAD
=======
import unittest
>>>>>>> 010
import multiprocessing

import synapse.exc as s_exc
import synapse.glob as s_glob

import synapse.lib.base as s_base
import synapse.tests.utils as s_t_utils

def block_processing(evt1, evt2):
    '''
    Function to make a base and call main().  Used as a Process target.

    Args:
        evt1 (multiprocessing.Event): event to twiddle
        evt2 (multiprocessing.Event): event to twiddle
    '''

<<<<<<< HEAD
    bus = s_glob.plex.coroToSync(s_base.Base.anit())

    def onMain(mesg):
        evt1.set()
=======
    base = s_glob.plex.coroToSync(s_base.Base.anit())

    async def onMain(mesg):
        evt1.set()
        await base.fini()
>>>>>>> 010

    def onFini():
        evt2.set()

<<<<<<< HEAD
    bus.on('ebus:main', onMain)
    bus.onfini(onFini)

    bus.main()
    sys.exit(137)

class BaseTest(s_t_utils.ASynTest):
=======
    base.on('ebus:main', onMain)
    base.onfini(onFini)

    base.main()

    sys.exit(137)

class BaseTest(s_t_utils.SynTest):

    @s_glob.synchelp
>>>>>>> 010
    async def test_base_basics(self):
        base = await s_base.Base.anit()

        def foo(event):
            x = event[1].get('x')
            y = event[1].get('y')
            event[1]['ret'] = x + y

        base.on('woot', foo)

        event = await base.fire('woot', x=3, y=5, ret=[])
        self.eq(event[1]['ret'], 8)

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
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

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
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

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
    async def test_base_withfini(self):

        data = {'count': 0}

        def onfini():
            data['count'] += 1

        async with s_base.Base() as base:
            base.onfini(onfini)

        self.eq(data['count'], 1)

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
    async def test_base_finionce(self):

        data = {'count': 0}

        async def onfini():
            data['count'] += 1

        base = await s_base.Base.anit()
        base.onfini(onfini)

        await base.fini()
        await base.fini()

        self.eq(data['count'], 1)

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
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

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
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

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
    async def test_base_filt(self):

        base = await s_base.Base.anit()

        def wootfunc(mesg):
            mesg[1]['woot'] = True

        base.on('lol', wootfunc)

        base.on('rofl', wootfunc, foo=10)

        mesg = await base.fire('lol')
        self.true(mesg[1].get('woot'))

        mesg = await base.fire('rofl')
        self.false(mesg[1].get('woot'))

        mesg = await base.fire('rofl', foo=20)
        self.false(mesg[1].get('woot'))

        mesg = await base.fire('rofl', foo=10)
        self.true(mesg[1].get('woot'))

<<<<<<< HEAD
=======
    @s_glob.synchelp
    @unittest.skip('Remove me when base.log confirmed unused')
>>>>>>> 010
    async def test_base_log(self):

        logs = []
        async with await s_base.Base.anit() as base:
            base.on('log', logs.append)

            await base.log(100, 'omg woot', foo=10)

        mesg = logs[0]
        self.eq(mesg[0], 'log')
        self.eq(mesg[1].get('foo'), 10)
        self.eq(mesg[1].get('mesg'), 'omg woot')
        self.eq(mesg[1].get('level'), 100)

<<<<<<< HEAD
=======
    @s_glob.synchelp
    @unittest.skip('Remove me when exc confirmed unused')
>>>>>>> 010
    async def test_base_exc(self):

        logs = []
        async with await s_base.Base.anit() as base:
            base.on('log', logs.append)

            try:
                raise s_exc.NoSuchObj(name='hehe')
            except Exception as e:
                await base.exc(e)

        mesg = logs[0]
        self.eq(mesg[1].get('err'), 'NoSuchObj')

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
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

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
    async def test_base_waitfini(self):

        base = await s_base.Base.anit()

        self.false(await base.waitfini(timeout=0.1))

        async def callfini():
            await asyncio.sleep(0.1, loop=asyncio.get_event_loop())
            await base.fini()

        asyncio.get_event_loop().create_task(callfini())
        # actually wait...
        self.true(await base.waitfini(timeout=0.3))

        # bounce off the isfini block
        self.true(await base.waitfini(timeout=0.3))

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
    async def test_base_refcount(self):
        base = await s_base.Base.anit()

        self.eq(base.incref(), 2)

        self.eq(await base.fini(), 1)
        self.false(base.isfini)

        self.eq(await base.fini(), 0)
        self.true(base.isfini)

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
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

<<<<<<< HEAD
=======
    @s_glob.synchelp
>>>>>>> 010
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

        ctx = multiprocessing.get_context('spawn')

        evt1 = ctx.Event()
        evt2 = ctx.Event()

        proc = ctx.Process(target=block_processing, args=(evt1, evt2))
        proc.start()

        self.true(evt1.wait(timeout=10))
        os.kill(proc.pid, signal.SIGTERM)
        self.true(evt2.wait(timeout=10))
        proc.join(timeout=10)
        self.eq(proc.exitcode, 137)

    def test_base_main_sigint(self):
        self.thisHostMustNot(platform='windows')
        # We have no reliable way to test this on windows

        ctx = multiprocessing.get_context('spawn')

        evt1 = ctx.Event()
        evt2 = ctx.Event()

        proc = ctx.Process(target=block_processing, args=(evt1, evt2))
        proc.start()

        self.true(evt1.wait(timeout=10))
        os.kill(proc.pid, signal.SIGINT)

        self.true(evt2.wait(timeout=10))
        proc.join(timeout=10)
        self.eq(proc.exitcode, 137)
