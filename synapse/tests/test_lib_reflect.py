import synapse.eventbus as s_eventbus

import synapse.lib.base as s_base
import synapse.lib.reflect as s_reflect

import synapse.tests.utils as s_t_utils

class Foo(s_eventbus.EventBus): pass

class Bar:
    def __init__(self):
        self.foo = Foo()

    def _syn_reflect(self):
        return s_reflect.getItemInfo(self.foo)

class Echo(s_base.Base):
    def echo(self, args):
        return args

    async def mygenr(self, n):
        for i in range(n):
            yield i

class ReflectTest(s_t_utils.SynTest):

    def test_reflect_getClsNames(self):
        foo = Foo()
        names = s_reflect.getClsNames(foo)
        self.isin('synapse.eventbus.EventBus', names)
        self.isin('synapse.tests.test_lib_reflect.Foo', names)

    # def test_reflect_getItemInfo(self):
    #     foo = Foo()
    #     info = s_reflect.getItemInfo(foo)
    #     names = info.get('inherits', ())
    #     self.isin('synapse.eventbus.EventBus', names)
    #     self.isin('synapse.tests.test_lib_reflect.Foo', names)
    #
    # def test_reflect_syn_reflect(self):
    #     bar = Bar()
    #     info = s_reflect.getItemInfo(bar)
    #     names = info.get('inherits', ())
    #     self.isin('synapse.eventbus.EventBus', names)
    #     self.isin('synapse.tests.test_lib_reflect.Foo', names)

    async def test_telemeth(self):
        self.none(getattr(Echo, '_syn_sharinfo', None))
        async with self.getTestDmon() as dmon:
            echo = await Echo.anit()
            dmon.share('echo', echo)
            self.none(getattr(echo, '_syn_sharinfo', None))
            self.none(getattr(Echo, '_syn_sharinfo', None))
            async with await self.getTestProxy(dmon, 'echo') as proxy:
                pass
            self.isinstance(getattr(echo, '_syn_sharinfo', None), dict)
            self.isinstance(getattr(Echo, '_syn_sharinfo', None), dict)
