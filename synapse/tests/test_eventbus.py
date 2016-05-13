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
            return event[1]['ret'].append( x + y )

        def bar(event):
            x = event[1].get('x')
            y = event[1].get('y')
            return event[1]['ret'].append( x * y )

        bus.on('woot',foo)
        bus.on('woot',bar,weak=True)

        event = bus.fire('woot',x=3,y=5,ret=[])
        self.assertEqual( tuple(event[1]['ret']), (8,15) )

    def test_eventbus_link(self):

        bus1 = s_eventbus.EventBus()
        bus2 = s_eventbus.EventBus()
        bus3 = s_eventbus.EventBus()

        # gotta hold a reference
        bus3dist = bus3.dist

        bus1.link(bus2.dist)
        bus2.link(bus3dist, weak=True)

        data = {}
        def woot(event):
            data['woot'] = True

        def weakwoot(event):
            data['weak'] = True

        bus2.on('woot',woot)
        bus3.on('woot',weakwoot)

        bus1.fire('woot')

        self.assertTrue( data.get('woot') )
        self.assertTrue( data.get('weak') )

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

    def test_eventbus_off_weak(self):
        bus = s_eventbus.EventBus()

        data = {'count':0}

        def woot(mesg):
            data['count'] += 1

        bus.on('hehe', woot, weak=True)

        bus.fire('hehe')

        bus.off('hehe', woot)

        bus.fire('hehe')

        bus.fini()

        self.assertEqual( data['count'], 1 )
