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

    def test_eventbus_fini_weak(self):
        '''
        Ensure that weak ref'd fini functions are fire as well.
        '''
        data = {'count': 0}

        def onfini():
            data['count'] += 1

        bus = s_eventbus.EventBus()
        bus.onfini(onfini, weak=True)

        bus.fini()
        bus.fini()

        self.assertEqual(data['count'], 1)

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

    def test_eventbus_bad_callback(self):
        '''
        Ensure that registering non-callables fails.
        '''
        bus = s_eventbus.EventBus()
        non_callable = 1
        with self.raises(Exception) as cm:
            bus.on('woot', non_callable)
        self.assertIn('func not callable', str(cm.exception))

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
