import synapse.exc as s_exc
import synapse.reactor as s_reactor
import synapse.tests.utils as s_t_utils

class ReactorTest(s_t_utils.SynTest):

    def test_reactor(self):
        reac = s_reactor.Reactor()

        def actfoo(mesg):
            x = mesg[1].get('x')
            y = mesg[1].get('y')
            return x + y

        reac.act('foo', actfoo)

        data = ('foo', {'x': 10, 'y': 20})
        self.eq(reac.react(data), 30)

        self.raises(s_exc.NoSuchAct, reac.react, ('wat', {}))
