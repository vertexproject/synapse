
import os
import sys
import time
import signal
import multiprocessing


import synapse.exc as s_exc
import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.tests.common as s_test
import synapse.lib.threads as s_threads

@s_common.firethread
def send_sig(pid, sig):
    '''
    Sent a signal to a process.

    Args:
        pid (int): Process id to send the signal too.
        sig (int): Signal to send.

    Returns:
        None
    '''
    os.kill(pid, sig)

def block_processing(evt1, evt2):
    '''
    Function to make an eventbus and call main().  Used as a Process target.

    Args:
        evt1 (multiprocessing.Event): event to twiddle
        evt2 (multiprocessing.Event): event to twiddle
    '''
    bus = s_eventbus.EventBus()

    def onMain(mesg):
        evt1.set()

    def onFini():
        evt2.set()

    bus.on('ebus:main', onMain)
    bus.onfini(onFini)

    bus.main()
    sys.exit(137)

class EventBusTest(s_test.SynTest):

    def test_eventbus_basics(self):
        bus = s_eventbus.EventBus()

        def foo(event):
            x = event[1].get('x')
            y = event[1].get('y')
            event[1]['ret'] = x + y

        bus.on('woot', foo)

        event = bus.fire('woot', x=3, y=5, ret=[])
        self.eq(event[1]['ret'], 8)

    def test_eventbus_link(self):

        bus1 = s_eventbus.EventBus()
        bus2 = s_eventbus.EventBus()

        bus1.link(bus2.dist)

        data = {}
        def woot(event):
            data['woot'] = True

        bus2.on('woot', woot)

        bus1.fire('woot')

        self.true(data.get('woot'))

    def test_evenbus_unlink(self):

        bus = s_eventbus.EventBus()

        mesgs = []
        def woot(mesg):
            mesgs.append(mesg)

        bus.link(woot)

        bus.fire('haha')
        self.eq(len(mesgs), 1)

        bus.unlink(woot)

        bus.fire('haha')
        self.eq(len(mesgs), 1)

        bus.fini()

    def test_eventbus_withfini(self):

        data = {'count': 0}
        def onfini():
            data['count'] += 1

        with s_eventbus.EventBus() as bus:
            bus.onfini(onfini)

        self.eq(data['count'], 1)

    def test_eventbus_finionce(self):

        data = {'count': 0}
        def onfini():
            data['count'] += 1

        bus = s_eventbus.EventBus()
        bus.onfini(onfini)

        bus.fini()
        bus.fini()

        self.eq(data['count'], 1)

    def test_eventbus_consume(self):
        bus = s_eventbus.EventBus()
        wait = self.getTestWait(bus, 2, 'woot')

        bus.consume([('haha', {}), ('hehe', {}), ('woot', {}), ('woot', {})])

        wait.wait()

        bus.fini()

    def test_eventbus_off(self):
        bus = s_eventbus.EventBus()

        data = {'count': 0}

        def woot(mesg):
            data['count'] += 1

        bus.on('hehe', woot)

        bus.fire('hehe')

        bus.off('hehe', woot)

        bus.fire('hehe')

        bus.fini()

        self.eq(data['count'], 1)

    def test_eventbus_waiter(self):
        bus0 = s_eventbus.EventBus()

        wait0 = bus0.waiter(3, 'foo:bar')

        bus0.fire('foo:bar')
        bus0.fire('foo:bar')
        bus0.fire('foo:bar')

        evts = wait0.wait(timeout=3)
        self.eq(len(evts), 3)

        wait1 = bus0.waiter(3, 'foo:baz')
        evts = wait1.wait(timeout=0.1)
        self.none(evts)

    def test_eventbus_filt(self):

        bus = s_eventbus.EventBus()

        def wootfunc(mesg):
            mesg[1]['woot'] = True

        bus.on('lol', wootfunc)

        bus.on('rofl', wootfunc, foo=10)

        mesg = bus.fire('lol')
        self.true(mesg[1].get('woot'))

        mesg = bus.fire('rofl')
        self.false(mesg[1].get('woot'))

        mesg = bus.fire('rofl', foo=20)
        self.false(mesg[1].get('woot'))

        mesg = bus.fire('rofl', foo=10)
        self.true(mesg[1].get('woot'))

    def test_eventbus_log(self):

        logs = []
        with s_eventbus.EventBus() as ebus:
            ebus.on('log', logs.append)

            ebus.log(100, 'omg woot', foo=10)

        mesg = logs[0]
        self.eq(mesg[0], 'log')
        self.eq(mesg[1].get('foo'), 10)
        self.eq(mesg[1].get('mesg'), 'omg woot')
        self.eq(mesg[1].get('level'), 100)

    def test_eventbus_exc(self):

        logs = []
        with s_eventbus.EventBus() as ebus:
            ebus.on('log', logs.append)

            try:
                raise s_exc.NoSuchObj(name='hehe')
            except Exception as e:
                ebus.exc(e)

        mesg = logs[0]
        self.eq(mesg[1].get('err'), 'NoSuchObj')

    def test_eventbus_busref(self):

        bref = s_eventbus.BusRef()

        bus0 = s_eventbus.EventBus()
        bus1 = s_eventbus.EventBus()
        bus2 = s_eventbus.EventBus()

        bref.put('foo', bus0)
        bref.put('bar', bus1)
        bref.put('baz', bus2)

        bus1.fini()
        self.nn(bref.get('foo'))
        self.none(bref.get('bar'))

        self.len(2, list(bref))

        self.true(bref.pop('baz') is bus2)
        self.len(1, list(bref))

        bref.fini()
        self.true(bus0.isfini)

    def test_eventbus_waitfini(self):

        ebus = s_eventbus.EventBus()

        self.false(ebus.waitfini(timeout=0.1))

        def callfini():
            time.sleep(0.1)
            ebus.fini()

        thr = s_threads.worker(callfini)
        # actually wait...
        self.true(ebus.waitfini(timeout=0.3))

        # bounce off the isfini block
        self.true(ebus.waitfini(timeout=0.3))

    def test_eventbus_refcount(self):
        ebus = s_eventbus.EventBus()

        self.eq(ebus.incref(), 2)

        self.eq(ebus.fini(), 1)
        self.false(ebus.isfini)

        self.eq(ebus.fini(), 0)
        self.true(ebus.isfini)

    def test_eventbus_busref_gen(self):

        with s_eventbus.BusRef() as refs:
            self.raises(s_exc.NoSuchCtor, refs.gen, 'woot')

        def ctor(name):
            return s_eventbus.EventBus()

        with s_eventbus.BusRef(ctor=ctor) as refs:

            self.none(refs.get('woot'))

            woot = refs.gen('woot')
            self.eq(1, woot._syn_refs)

            self.nn(woot)
            self.true(refs.gen('woot') is woot)
            self.eq(2, woot._syn_refs)

            woot.fini()
            self.false(woot.isfini)
            self.true(refs.get('woot') is woot)
            self.eq(1, woot._syn_refs)

            woot.fini()
            self.eq(0, woot._syn_refs)

            self.true(woot.isfini)
            self.false(refs.get('woot') is woot)
            self.eq(0, woot._syn_refs)

    def test_eventbus_main_sigterm(self):
        self.thisHostMustNot(platform='windows')
        # We have no reliable way to test this on windows

        evt1 = multiprocessing.Event()
        evt1.clear()
        evt2 = multiprocessing.Event()
        evt2.clear()

        proc = multiprocessing.Process(target=block_processing, args=(evt1, evt2))
        proc.start()

        self.true(evt1.wait(timeout=10))
        foo = send_sig(proc.pid, signal.SIGTERM)
        self.true(evt2.wait(timeout=10))
        proc.join(timeout=10)
        foo.join()
        self.eq(proc.exitcode, 137)

    def test_eventbus_main_sigint(self):
        self.thisHostMustNot(platform='windows')
        # We have no reliable way to test this on windows

        evt1 = multiprocessing.Event()
        evt1.clear()
        evt2 = multiprocessing.Event()
        evt2.clear()

        proc = multiprocessing.Process(target=block_processing, args=(evt1, evt2))
        proc.start()

        self.true(evt1.wait(timeout=10))
        foo = send_sig(proc.pid, signal.SIGINT)
        self.true(evt2.wait(timeout=10))
        proc.join(timeout=10)
        foo.join()
        self.eq(proc.exitcode, 137)

    def test_eventbus_onwith(self):
        ebus = s_eventbus.EventBus()
        l0 = []
        l1 = []

        def onHehe0(mesg):
            l0.append(mesg)

        def onHehe1(mesg):
            l1.append(mesg)

        ebus.on('hehe', onHehe0)

        # Temporarily set the 'hehe' callback
        with ebus.onWith('hehe', onHehe1) as e:
            self.true(e is ebus)
            ebus.fire('hehe')
            self.len(1, l0)
            self.len(1, l1)

        # subsequent fires do not call onHehe1
        ebus.fire('hehe')
        self.len(2, l0)
        self.len(1, l1)

    def test_eventbus_busref_items(self):

        bref = s_eventbus.BusRef()

        bus0 = s_eventbus.EventBus()
        bus1 = s_eventbus.EventBus()
        bus2 = s_eventbus.EventBus()

        bref.put('foo', bus0)
        bref.put('bar', bus1)
        bref.put('baz', bus2)

        items = bref.items()
        self.isin(('foo', bus0), items)
        self.isin(('bar', bus1), items)
        self.isin(('baz', bus2), items)

        bus1.fini()
        items = bref.items()
        self.isin(('foo', bus0), items)
        self.isin(('baz', bus2), items)

        bus2.fini()
        items = bref.items()
        self.isin(('foo', bus0), items)

        bus0.fini()
        items = bref.items()
        self.eq(items, [])

        bref.fini()
        items = bref.items()
        self.eq(items, [])
