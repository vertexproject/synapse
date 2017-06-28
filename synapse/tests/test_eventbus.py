import unittest
import threading

import synapse.eventbus as s_eventbus

from synapse.tests.common import *

class EventBusTest(SynTest):

    def test_eventbus_basics(self):
        bus = s_eventbus.EventBus()

        def foo(event):
            x = event[1].get('x')
            y = event[1].get('y')
            event[1]['ret'] = x + y

        bus.on('woot',foo)

        event = bus.fire('woot',x=3,y=5,ret=[])
        self.eq( event[1]['ret'], 8 )

    def test_eventbus_link(self):

        bus1 = s_eventbus.EventBus()
        bus2 = s_eventbus.EventBus()

        bus1.link(bus2.dist)

        data = {}
        def woot(event):
            data['woot'] = True

        bus2.on('woot',woot)

        bus1.fire('woot')

        self.true( data.get('woot') )

    def test_evenbus_unlink(self):

        bus = s_eventbus.EventBus()

        mesgs = []
        def woot(mesg):
            mesgs.append(mesg)

        bus.link(woot)

        bus.fire('haha')
        self.assertEqual( len(mesgs), 1 )

        bus.unlink(woot)

        bus.fire('haha')
        self.assertEqual( len(mesgs), 1 )

        bus.fini()

    def test_eventbus_withfini(self):

        data = {'count':0}
        def onfini():
            data['count'] += 1

        with s_eventbus.EventBus() as bus:
            bus.onfini(onfini)

        self.assertEqual( data['count'], 1 )

    def test_eventbus_finionce(self):

        data = {'count':0}
        def onfini():
            data['count'] += 1

        bus = s_eventbus.EventBus()
        bus.onfini(onfini)

        bus.fini()
        bus.fini()

        self.assertEqual( data['count'], 1 )

    def test_eventbus_consume(self):
        bus = s_eventbus.EventBus()
        wait = self.getTestWait(bus,2,'woot')

        bus.consume( [ ('haha',{}), ('hehe',{}), ('woot',{}), ('woot',{}) ] )

        wait.wait()

        bus.fini()


    def test_eventbus_off(self):
        bus = s_eventbus.EventBus()

        data = {'count':0}

        def woot(mesg):
            data['count'] += 1

        bus.on('hehe', woot)

        bus.fire('hehe')

        bus.off('hehe', woot)

        bus.fire('hehe')

        bus.fini()

        self.assertEqual( data['count'], 1 )

    def test_eventbus_waiter(self):
        bus0 = s_eventbus.EventBus()

        wait0 = bus0.waiter(3,'foo:bar')

        bus0.fire('foo:bar')
        bus0.fire('foo:bar')
        bus0.fire('foo:bar')

        evts = wait0.wait(timeout=3)
        self.eq( len(evts), 3 )

        wait1 = bus0.waiter(3,'foo:baz')
        evts = wait1.wait(timeout=0.1)
        self.assertIsNone( evts )

    def test_eventbus_filt(self):

        bus = s_eventbus.EventBus()

        def wootfunc(mesg):
            mesg[1]['woot'] = True

        bus.on('lol', wootfunc)

        bus.on('rofl', wootfunc, foo=10 )

        mesg = bus.fire('lol')
        self.true( mesg[1].get('woot') )

        mesg = bus.fire('rofl')
        self.false( mesg[1].get('woot') )

        mesg = bus.fire('rofl', foo=20)
        self.false( mesg[1].get('woot') )

        mesg = bus.fire('rofl', foo=10)
        self.true( mesg[1].get('woot') )

    def test_eventbus_decor(self):

        class Woot(s_eventbus.EventBus):

            @s_eventbus.on('ebus:init')
            def _onWootInit(self, mesg):
                self.hit = False
                self.finid = False

            @s_eventbus.on('hehe:hoho')
            @s_eventbus.on('hehe:haha', woot=1)
            def _onHeheHaHaWoot(self, mesg):
                self.hit = True

            @s_eventbus.onfini
            def _onWootFini(self):
                self.finid = True

        woot = Woot()
        self.false( woot.hit )

        woot.fire('hehe:haha')
        self.false( woot.hit )

        woot.fire('hehe:haha', woot=1)
        self.true( woot.hit )

        woot.hit = False
        woot.fire('hehe:hoho')
        self.true( woot.hit )

        woot.fini()
        self.true(woot.finid)

    def test_eventbus_log(self):

        logs = []
        with s_eventbus.EventBus() as ebus:
            ebus.on('log',logs.append)

            ebus.log(100,'omg woot', foo=10)

        mesg = logs[0]
        self.eq( mesg[0], 'log' )
        self.eq( mesg[1].get('foo'), 10)
        self.eq( mesg[1].get('mesg'), 'omg woot')
        self.eq( mesg[1].get('level'), 100)

    def test_eventbus_exc(self):

        logs = []
        with s_eventbus.EventBus() as ebus:
            ebus.on('log',logs.append)

            try:
                raise NoSuchObj(name='hehe')
            except Exception as e:
                ebus.exc(e)

        mesg = logs[0]
        self.eq(mesg[1].get('err'), 'NoSuchObj')
