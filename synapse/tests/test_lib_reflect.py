import synapse.lib.base as s_base
import synapse.lib.cell as s_cell
import synapse.lib.reflect as s_reflect
import synapse.lib.version as s_version

import synapse.tests.utils as s_t_utils

class Lol:
    def lol(self):
        return 'lol'

class Foo(Lol):
    def foo(self):
        return 'foo'

class Echo(s_base.Base):
    def echo(self, args):
        return args

    async def mygenr(self, n):
        for i in range(n):
            yield i

class TstCellApi(s_cell.CellApi):
    async def giggles(self):
        yield 'giggles'

    @s_cell.adminapi(log=False)
    async def wrapped_giggles(self):
        yield 'giggles'

class TstCell(s_cell.Cell):
    cellapi = TstCellApi

class ReflectTest(s_t_utils.SynTest):

    def test_reflect_getClsNames(self):
        foo = Foo()
        names = s_reflect.getClsNames(foo)
        self.isin('synapse.tests.test_lib_reflect.Lol', names)
        self.isin('synapse.tests.test_lib_reflect.Foo', names)

    def test_reflect_getMethName(self):
        foo = Foo()
        name = s_reflect.getMethName(foo.foo)
        self.eq('synapse.tests.test_lib_reflect.Foo.foo', name)

    def test_reflect_getItemLocals(self):
        foo = Foo()
        locls = s_reflect.getItemLocals(foo)
        self.isin(('foo', foo.foo), locls)
        self.isin(('lol', foo.lol), locls)

    async def test_telemeth(self):
        self.none(getattr(Echo, '_syn_sharinfo_synapse.tests.test_lib_reflect_Echo', None))
        async with self.getTestDmon() as dmon:
            echo = await Echo.anit()
            dmon.share('echo', echo)
            self.none(getattr(echo, '_syn_sharinfo_synapse.tests.test_lib_reflect_Echo', None))
            self.none(getattr(Echo, '_syn_sharinfo_synapse.tests.test_lib_reflect_Echo', None))
            async with await self.getTestProxy(dmon, 'echo') as proxy:
                pass
            self.isinstance(getattr(echo, '_syn_sharinfo_synapse.tests.test_lib_reflect_Echo', None), dict)
            self.isinstance(getattr(Echo, '_syn_sharinfo_synapse.tests.test_lib_reflect_Echo', None), dict)

            sharinfo = getattr(echo, '_syn_sharinfo_synapse.tests.test_lib_reflect_Echo')
            self.eq(sharinfo.get('syn:version'), s_version.version)
            self.eq(sharinfo.get('classes'),
                    ['synapse.tests.test_lib_reflect.Echo', 'synapse.lib.base.Base'])

        # Check attribute information for a Cell / CellApi wrapper which sets
        # the __syn_wrapped__ attribute on a few functions of the CellApi
        # class. This also tests unwrapped async generator detection.
        with self.getTestDir() as dirn:
            async with await TstCell.anit(dirn) as cell:
                async with cell.getLocalProxy() as prox:
                    key = '_syn_sharinfo_synapse.tests.test_lib_reflect_TstCellApi'
                    valu = getattr(TstCellApi, key)
                    self.nn(valu)

                    meths = valu.get('meths')
                    self.isin('giggles', meths)
                    self.isin('wrapped_giggles', meths)
                    self.isin('dyniter', meths)
