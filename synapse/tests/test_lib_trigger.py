import synapse.tests.utils as s_t_utils

import unittest
raise unittest.SkipTest('FIXME RE ENABLE TRIGGERS')

import synapse.lib.trigger as s_trigger

class TrigTest(s_t_utils.SynTest):

    def test_trigger_base(self):

        trig = s_trigger.Triggers()

        data = {}
        def foo():
            data['valu'] = 'foo'

        def bar():
            data['valu'] = 'bar'

        def baz():
            data['valu'] = 'baz'

        trig.add(foo, ('hehe:*', {}))
        trig.add(bar, ('haha:hoho', {'blah': 'woot*'}))
        trig.add(baz, ('rofl:lulz', {'gronk': 'boing'}))

        trig.trigger(('hehe:haha', {}))
        self.eq(data.pop('valu'), 'foo')

        trig.trigger(('haha:hoho', {'blah': 'lulz'}))
        self.none(data.get('valu'))

        trig.trigger(('haha:hoho', {'blah': 'wootwoot'}))
        self.eq(data.pop('valu'), 'bar')
