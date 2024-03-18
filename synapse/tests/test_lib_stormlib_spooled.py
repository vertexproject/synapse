import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.utils as s_test

class StormlibCompressionTest(s_test.SynTest):
    async def test_lib_spooled_set(self):
        async with self.getTestCore() as core:
            await core.nodes('[inet:ipv4=1.2.3.4 :asn=20]')
            await core.nodes('[inet:ipv4=5.6.7.8 :asn=30]')

            q = '''
                $set = $lib.spooled.set()
                $set.add(1, 2, 3, 4)
                return($set)
            '''
            valu = await core.callStorm(q)
            self.eq({'1', '2', '3', '4'}, valu)

            q = '''
                $set = $lib.spooled.set()
                $set.adds($lib.list(1, 2, 3, 4))
                return($set)
            '''
            valu = await core.callStorm(q)
            self.eq({'1', '2', '3', '4'}, valu)

            q = '''
                $set = $lib.spooled.set()
                inet:ipv4 $set.add(:asn)
                $set.rems((:asn,:asn))
                [ graph:node="*" ] +graph:node [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].get('data'), ())

            q = '''
                $set = $lib.spooled.set()
                $set.add($foo)
                $set.add($bar)
                $set.add($biz)
                return(($set.has($foo), $set.has(lolnop)))
            '''
            valu = await core.callStorm(q, opts={'vars': {'foo': b'foo', 'bar': b'bar', 'biz': b'biz'}})
            self.eq(True, valu[0])
            self.eq(False, valu[1])

            q = '''
                $set = $lib.spooled.set()
                $set.adds(('foo', 'bar', 'baz', 'biz', 'biz', 'biz', 'beep', 'boop'))
                return($set.size())
            '''
            valu = await core.callStorm(q)
            self.eq(6, valu)

            q = '''
                $set = $lib.spooled.set()
                $set.adds(('foo', 'bar', 'baz', 'biz', 'biz', 'biz', 'beep', 'boop'))

                $set.rems(('baz', 'beep', 'bar'))
                return($set)

            '''
            valu = await core.callStorm(q)
            self.eq({'foo', 'boop', 'biz'}, valu)

            q = '''
                $set = $lib.spooled.set()
                $set.add(1, 2, 3, 4)
                return($set.list())
            '''
            valu = await core.callStorm(q)
            self.isinstance(valu, tuple)
            self.isin('1', valu)
            self.isin('2', valu)
            self.isin('3', valu)
            self.isin('4', valu)

            # sad paths
            # too complex
            q = '''
                $set = $lib.spooled.set()
                $set.add($stormnode)
                return($set)
            '''
            stormnode = s_stormtypes.Node(nodes[0])
            await self.asyncraises(await core.callStorm(q, {'vars': {'stormnode': stormnode}}))

            # mutable failure
            q = '''
                $set = $lib.spooled.set()
                $set.add(({'neato': 'burrito'}))
                return($set)
            '''
            await self.asyncraises(s_exc.StormRuntimeError, core.callStorm(q))

            # type not msgpack-able
            q = '''
                $set = $lib.spooled.set()
                $set.add($lib.model.form("inet:ipv4"))
                return($set)
            '''
            await self.asyncraises(s_exc.StormRuntimeError, core.callStorm(q))
