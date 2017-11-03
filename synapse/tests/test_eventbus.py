import signal
import threading

import synapse.common as s_common
import synapse.eventbus as s_eventbus
import synapse.lib.threads as s_threads

from synapse.tests.common import *

@firethread
def send_sig(pid, sig):
    time.sleep(0.1)
    # This test is insanity wolf
    os.kill(pid, sig)

class Foo(object):
    def __init__(self):
        self.bus = None  # type: s_eventbus.EventBus
        self.btreadid = None
        self.bthr = self.fireBus()

    @firethread
    def fireBus(self):
        self.btreadid = threading.get_ident()
        self.bus = s_eventbus.EventBus()
        self.bus.main()

class EventBusTest(SynTest):

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
                raise s_common.NoSuchObj(name='hehe')
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
            self.raises(NoSuchCtor, refs.gen, 'woot')

        def ctor(name):
            return s_eventbus.EventBus()

        with s_eventbus.BusRef(ctor=ctor) as refs:

            self.none(refs.get('woot'))

            woot = refs.gen('woot')

            self.nn(woot)
            self.true(refs.gen('woot') is woot)

            woot.fini()
            self.false(woot.isfini)
            self.true(refs.get('woot') is woot)

            woot.fini()
            self.true(woot.isfini)
            self.false(refs.get('woot') is woot)

    def test_eventbus_main_sigterm(self):
        self.thisHostMustNot(platform='windows')
        # We have no reliable way to test this on windows

        bus = s_eventbus.EventBus()
        pid = os.getpid()

        self.false(bus.isfini)
        foo = send_sig(pid, signal.SIGTERM)
        # block mainthread
        bus.main()
        # Signal should fire from our thread and unblock us to continue :)
        self.true(bus.isfini)
        foo.join()

    def test_eventbus_main_sigint(self):
        self.thisHostMustNot(platform='windows')
        # We have no reliable way to test this on windows

        bus = s_eventbus.EventBus()
        pid = os.getpid()

        self.false(bus.isfini)
        foo = send_sig(pid, signal.SIGINT)
        # block mainthread
        bus.main()
        # Signal should fire from our thread and unblock us to continue :)
        self.true(bus.isfini)
        foo.join()
