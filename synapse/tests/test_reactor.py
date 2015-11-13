from synapse.tests.common import *

import synapse.reactor as s_reactor

class ReactorTest(SynTest):

    def test_reactor_base(self):
        reac = s_reactor.Reactor()

        def actfoo(mesg):
            x = mesg[1].get('x')
            y = mesg[1].get('y')
            return x + y
            
        reac.act('foo',actfoo)
        self.assertEqual( reac.react( tufo('foo', x=10, y=20)), 30 )
