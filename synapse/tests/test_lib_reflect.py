import synapse.tests.utils as s_t_utils

import synapse.lib.reflect as s_reflect

from synapse.eventbus import EventBus

class Foo(EventBus): pass

class Bar:
    def __init__(self):
        self.foo = Foo()

    def _syn_reflect(self):
        return s_reflect.getItemInfo(self.foo)

class ReflectTest(s_t_utils.SynTest):

    def test_reflect_getClsNames(self):
        foo = Foo()
        names = s_reflect.getClsNames(foo)
        self.isin('synapse.eventbus.EventBus', names)
        self.isin('synapse.tests.test_lib_reflect.Foo', names)

    def test_reflect_getItemInfo(self):
        foo = Foo()
        info = s_reflect.getItemInfo(foo)
        names = info.get('inherits', ())
        self.isin('synapse.eventbus.EventBus', names)
        self.isin('synapse.tests.test_lib_reflect.Foo', names)

    def test_reflect_syn_reflect(self):
        bar = Bar()
        info = s_reflect.getItemInfo(bar)
        names = info.get('inherits', ())
        self.isin('synapse.eventbus.EventBus', names)
        self.isin('synapse.tests.test_lib_reflect.Foo', names)
