import unittest

import synapse.dispatch as s_dispatch

class DispatchTest(unittest.TestCase):

    def test_dispatch_basics(self):
        disp = s_dispatch.Dispatcher()

        def foo(x,y):
            return x + y

        def bar(x,y):
            return x * y

        disp.synOn('woot',foo)
        disp.synOn('woot',bar,weak=True)

        ret = disp.synFire('woot',3,5)
        self.assertEqual( tuple(ret), (8,15) )
