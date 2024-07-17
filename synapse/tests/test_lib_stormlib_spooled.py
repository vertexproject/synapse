from unittest import mock

import synapse.exc as s_exc
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.utils as s_test

class StormlibSpooledTest(s_test.SynTest):
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
                [ tel:mob:telem="*" ] +tel:mob:telem [ :data=$set.list() ]
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
                $set = $lib.spooled.set(1, 2, 3, 4 ,5)
                $set.add(1, 2, 3, 4)
                return($set.list())
            '''
            valu = await core.callStorm(q)
            self.isinstance(valu, tuple)
            self.len(5, valu)
            self.isin('1', valu)
            self.isin('2', valu)
            self.isin('3', valu)
            self.isin('4', valu)
            self.isin('5', valu)

            q = '''
                $set = $lib.spooled.set()
                $set.add($lib.true)
                $set.add($lib.false)
                $set.add($lib.true)
                $set.add($lib.false)
                $set.add('more stuff')

                $dict = ({
                    "foo": "bar",
                    "biz": "baz",
                })
                $set.adds($dict)
                return($set)
            '''
            valu = await core.callStorm(q)
            self.len(5, valu)
            self.isin(False, valu)
            self.isin(True, valu)
            self.isin('more stuff', valu)
            self.isin(('biz', 'baz'), valu)
            self.isin(('foo', 'bar'), valu)

            q = '''
                $set = $lib.spooled.set()
                $set.adds($items)
                for $x in $set {
                    $lib.print(`{$x} exists in the set`)
                }
                return()
            '''
            msgs = await core.stormlist(q, opts={'vars': {'items': [True, 'neato', False, 9001]}})
            self.len(7, msgs)
            self.stormIsInPrint('false exists in the set', msgs)
            self.stormIsInPrint('true exists in the set', msgs)
            self.stormIsInPrint('neato exists in the set', msgs)
            self.stormIsInPrint('9001 exists in the set', msgs)

            q = '''
                $set = $lib.spooled.set(neato, neato, neato, neato)
                $lib.print(`The set is {$set}`)
            '''
            msgs = await core.stormlist(q, opts={'vars': {'items': [True, 'neato', False, 9001]}})
            self.stormIsInPrint("The set is {'neato'}", msgs)

            # force a fallback
            q = '''
                $set = $lib.spooled.set()
                $set.adds($lib.range(1500))
                return($set.size())
            '''
            valu = await core.callStorm(q)
            self.eq(1500, valu)

            # sad paths
            # too complex
            q = '''
                $set = $lib.spooled.set()
                $set.add($stormnode)
                return($set)
            '''
            stormnode = s_stormtypes.Node(nodes[0])
            await self.asyncraises(s_exc.StormRuntimeError, core.callStorm(q, {'vars': {'stormnode': stormnode}}))

            # mutable failures
            q = '''
                $set = $lib.spooled.set()
                $set.add(({'neato': 'burrito'}))
                return($set)
            '''
            await self.asyncraises(s_exc.StormRuntimeError, core.callStorm(q))

            q = '''
                $set = $lib.spooled.set()
                $dict = ({'neato': 'burrito'})
                $set.adds(($dict, $dict))
                return($set)
            '''
            await self.asyncraises(s_exc.StormRuntimeError, core.callStorm(q))

            q = '''
                $set = $lib.spooled.set()
                $form = $lib.model.form('inet:ipv4')
                $set.adds(($stormnode, $form, $form))
                return($set)
            '''
            # it'll blow up on the first
            await self.asyncraises(s_exc.StormRuntimeError, core.callStorm(q, {'vars': {'stormnode': stormnode}}))

            q = '''
                $dict = ({'foo': 'bar'})
                $set = $lib.spooled.set($dict)
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

            q = '''
                $set = $lib.spooled.set($stormnode)
                return($set)
            '''
            await self.asyncraises(s_exc.StormRuntimeError, core.callStorm(q, {'vars': {'stormnode': stormnode}}))

    async def test_lib_spooled_dict(self):
        for size in (1000, 5):
            with mock.patch('synapse.lib.stormlib.spooled.LIB_SPOOLED_INMEMORY_OBJECTS', size):
                async with self.getTestCore() as core:
                    # Basic set key=val
                    q = '''
                        $d = $lib.spooled.dict()
                        $d.foo = bar
                        return($d)
                    '''

                    out = await core.callStorm(q)
                    self.eq({'foo': 'bar'}, out)

                    # Basic get key
                    q = '''
                        $d = $lib.spooled.dict()
                        $d.foo = bar
                        return($d.foo)
                    '''
                    out = await core.callStorm(q)
                    self.eq('bar', out)

                    # $lib.dict.* helpers should all work on a spooled dict
                    q = '''
                        $d = $lib.spooled.dict()
                        $d.kfoo = vfoo
                        $d.kbar = vbar
                        $d.kbaz = vbaz
                        $d.kquux = vquux
                        $d.kfive = vfive
                        $d.ksix = vsix
                        $d.kseven = vseven
                        $d.keight = veight
                        $d.knine = vnine
                        $d.kten = vten
                        $ret = ({
                            "haspos": $lib.dict.has($d, kfoo),
                            "hasneg": $lib.dict.has($d, newp),
                            "keys": $lib.dict.keys($d),
                            "poppos": $lib.dict.pop($d, kfoo),
                            "popneg": $lib.dict.pop($d, newp, $lib.null),
                        })

                        $lib.dict.update($d, ({"kfoo": "updated"}))

                        $ret.vals = $lib.dict.values($d)
                        return($ret)
                    '''
                    out = await core.callStorm(q)
                    self.true(out.get('haspos'))
                    self.false(out.get('hasneg'))
                    self.eq(out.get('poppos'), 'vfoo')
                    self.none(out.get('popneg'))
                    self.sorteq(out.get('keys'), ('kfoo', 'kbar', 'kbaz', 'kquux', 'kfive', 'ksix', 'kseven', 'keight', 'knine', 'kten'))
                    self.sorteq(out.get('vals'), ('vbar', 'vbaz', 'vquux', 'vfive', 'vsix', 'vseven', 'veight', 'vnine', 'vten', 'updated'))

        async with self.getTestCore() as core:
            q = '''
                $key = ({})
                $d = $lib.spooled.dict()
                $d.$key = foo
            '''
            with self.raises(s_exc.BadArg) as exc:
                await core.callStorm(q)
            self.eq(exc.exception.get('mesg'), 'Mutable values are not allowed as dictionary keys')

            q = '''
                [ inet:ipv4=1.2.3.4 ]
                $d = $lib.spooled.dict()
                $key = $node.edges()
                $d.$key = foo
            '''
            with self.raises(s_exc.BadArg) as exc:
                await core.callStorm(q)
            mesg = exc.exception.get('mesg')
            self.isin('<async_generator object Node._methNodeEdges', mesg)
            self.isin('is not safe to be used in a SpooledDict key.', mesg)

            q = '''
                [ inet:ipv4=1.2.3.4 ]
                $d = $lib.spooled.dict()
                $key = $node.edges()
                $d.foo = $key
            '''
            with self.raises(s_exc.BadArg) as exc:
                await core.callStorm(q)
            mesg = exc.exception.get('mesg')
            self.isin('<async_generator object Node._methNodeEdges', mesg)
            self.isin('is not safe to be used in a SpooledDict value.', mesg)
