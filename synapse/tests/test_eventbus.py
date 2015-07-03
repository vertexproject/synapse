import unittest

import synapse.eventbus as s_eventbus

class EventBusTest(unittest.TestCase):

    def test_eventbus_basics(self):
        bus = s_eventbus.EventBus()

        def foo(event):
            x = event[1].get('x')
            y = event[1].get('y')
            return x + y

        def bar(event):
            x = event[1].get('x')
            y = event[1].get('y')
            return x * y

        bus.on('woot',foo)
        bus.on('woot',bar,weak=True)

        ret = bus.fire('woot',x=3,y=5)
        self.assertEqual( tuple(ret), (8,15) )
