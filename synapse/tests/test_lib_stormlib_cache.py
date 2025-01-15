import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormlibCacheTest(s_test.SynTest):

    async def test_storm_lib_cache_fixed(self):

        async with self.getTestCore() as core:

            # basics

            rets = await core.callStorm('''
                $rets = ([])
                $cache = $lib.cache.fixed("return(`{$cache_key}-ret`)")

                $cache.clear()

                $rets.append($lib.len($cache))

                $rets.append($cache.get(key))
                $rets.append($lib.len($cache))

                $cache.put(key, key-put)
                $rets.append($cache.get(key))

                $cache.clear()
                $rets.append($cache.get(key))

                $cache.put(key, key-put)
                $rets.append($cache.get(key))
                $rets.append($cache.pop(key))
                $rets.append($cache.get(key))

                $rets.append($cache.pop(newp))

                $rets.append($cache.query)

                return($rets)
            ''')
            self.eq([
                0,
                'key-ret', 1,
                'key-put',
                'key-ret',
                'key-put', 'key-put', 'key-ret',
                None,
                'return(`{$cache_key}-ret`)'
            ], rets)

            # exhaust size

            rets = await core.callStorm('''
                $rets = ([])
                $cache = $lib.cache.fixed("return(`{$cache_key}-ret`)", size=2)

                $cache.put(one, one-put)
                $cache.put(two, two-put)
                $rets.append($cache.get(one))
                $rets.append($cache.get(two))

                $rets.append($cache.get(three))
                $rets.append($cache.get(one))

                return($rets)
            ''')
            self.eq(['one-put', 'two-put', 'three-ret', 'one-ret'], rets)

            # also accept a storm query object

            ret = await core.callStorm('''
                $cache = $lib.cache.fixed(${ $suf=ret return(`{$cache_key}-{$suf}`)})
                return($cache.get(foo))
            ''')
            self.eq('foo-ret', ret)

            # callback runtime scoping

            ## a function still has the outer scope as its root
            rets = await core.callStorm('''
                $val = zero
                $sent = $lib.null

                function cb(key) {
                    $sent = $val
                    return(`{$key}-{$val}`)
                }

                $cache = $lib.cache.fixed("return($cb($cache_key))")

                $rets = ([])

                $rets.append($cache.get(foo))
                $rets.append($sent)

                $val = one
                $rets.append($cache.get(bar))
                $rets.append($sent)

                return($rets)
            ''')
            self.eq([
                'foo-zero', 'zero',
                'bar-one', 'one'
            ], rets)

            ## runtime also can modify refs to the outer scope
            rets = await core.callStorm('''
                $val = zero
                $vals = ([])
                $sent = $lib.null

                $cache = $lib.cache.fixed(${
                    $sent = $val
                    $vals.append($cache_key)
                    return(`{$cache_key}-{$val}`)
                })

                $rets = ([])

                $rets.append($cache.get(foo))
                $rets.append($sent)
                $rets.append($lib.str.join(",", $vals))

                $val = one
                $rets.append($cache.get(bar))
                $rets.append($sent)
                $rets.append($lib.str.join(",", $vals))

                return($rets)
            ''')
            self.eq([
                'foo-zero', None, 'foo',
                'bar-one', None, 'foo,bar',
            ], rets)

            ## default to null w/o a return
            self.none(await core.callStorm('return($lib.cache.fixed("if (0) { return(yup) }").get(foo))'))

            ## control flow exceptions don't propagate up
            msgs = await core.stormlist('''
                $cache = $lib.cache.fixed( ${ if ($cache_key < (2)) { return (`key={$cache_key}`) } else { break } } )

                for $i in $lib.range(4) {
                    $lib.print(`{$cache.get($i)}`)
                }
            ''')
            self.stormIsInPrint('key=1', msgs)
            self.stormNotInPrint('key=2', msgs)
            self.stormIsInErr('Storm control flow "break" not allowed in cache callbacks.', msgs)

            msgs = await core.stormlist('''
                $cache = $lib.cache.fixed( ${ if ($cache_key < (2)) { return (`key={$cache_key}`) } else { continue } } )

                for $i in $lib.range(4) {
                    $lib.print(`{$cache.get($i)}`)
                }
            ''')
            self.stormIsInPrint('key=1', msgs)
            self.stormNotInPrint('key=2', msgs)
            self.stormIsInErr('Storm control flow "continue" not allowed in cache callbacks.', msgs)

            msgs = await core.stormlist('''
                $cache = $lib.cache.fixed( ${ if ($cache_key < (2)) { return (`key={$cache_key}`) } else { stop } } )

                for $i in $lib.range(4) {
                    $lib.print(`{$cache.get($i)}`)
                }
            ''')
            self.stormIsInPrint('key=1', msgs)
            self.stormNotInPrint('key=2', msgs)
            self.stormIsInErr('Storm control flow "stop" not allowed in cache callbacks.', msgs)

            msgs = await core.stormlist('''
                $cache = $lib.cache.fixed(
                    ${ if ($cache_key < (2)) { return (`key={$cache_key}`) } else { $lib.exit(mesg=newp) } }
                )

                for $i in $lib.range(4) {
                    $lib.print(`{$cache.get($i)}`)
                }
                ''')
            self.stormIsInPrint('key=1', msgs)
            self.stormNotInPrint('key=2', msgs)
            self.stormIsInErr('Storm control flow "StormExit" not allowed in cache callbacks.', msgs)

            ## control flow scoped inside the callback
            rets = await core.callStorm("""
                $cache = $lib.cache.fixed('''
                    $vals = ([])
                    for $i in $lib.range(3) {
                        $vals.append(`key={$cache_key} i={$i}`)
                        break
                    }
                    return($vals)
                ''')

                $rets = ([])

                for $k in (foo, bar, baz) {
                    $rets.append($cache.get($k))
                }

                return($rets)
            """)
            self.eq([('key=foo i=0',), ('key=bar i=0',), ('key=baz i=0',),], rets)

            ## coverage for the cb runtime emiting nodes
            rets = await core.callStorm('''
                $rets = ([])
                $cache = $lib.cache.fixed(${ if (0) { return(yup) } [ inet:ipv4=$cache_key ] })

                for $i in (0, 1) {
                    $rets.append($cache.get($i))
                }
                return($rets)
            ''')
            self.eq([None, None], rets)

            # stormrepr

            msgs = await core.stormlist('''
                $lib.print($lib.cache.fixed(${return(cool)}))
                $lib.print($lib.cache.fixed($longq))
            ''', opts={'vars': {'longq': f'return({"a" * 150})'}})
            self.stormIsInPrint('cache:fixed: size=10000 query="return(cool)"', msgs)
            self.stormIsInPrint('aaaaa...', msgs)

            # sad

            ## bad storm query

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.cache.fixed("function x -> newp")')
            self.isin('Invalid callback query', ectx.exception.errinfo.get('mesg'))

            ## no return

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.cache.fixed("$x=1")')
            self.eq('Callback query must return a value', ectx.exception.errinfo.get('mesg'))

            ## bad size

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.cache.fixed("return()", size=(-1))')
            self.eq('Cache size must be between 1-10000', ectx.exception.errinfo.get('mesg'))

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.cache.fixed("return()", size=(1000000))')
            self.eq('Cache size must be between 1-10000', ectx.exception.errinfo.get('mesg'))

            ## callback raises an exception

            rets = await core.callStorm('''
                function cb(key) {
                    if ($key = "sad") {
                        $lib.raise(Bad, Time)
                    }
                    return(`{$key}-happy`)
                }
                $cache = $lib.cache.fixed("return($cb($cache_key))")

                $rets = ([])

                try {
                    $rets.append($cache.get(sad))
                } catch Bad as e {
                    $rets.append(badtime)
                }

                $rets.append($cache.get(foo))

                return($rets)
            ''')
            self.eq(['badtime', 'foo-happy'], rets)

            with self.raises(s_exc.BadCast) as ectx:
                await core.nodes('$lib.cache.fixed(${ return(($cache_key * 3)) }).get(foo)')
            self.eq('Failed to make an integer from \'foo\'.', ectx.exception.errinfo.get('mesg'))

            ## mutable key

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.cache.fixed("return()").get((foo,))')
            self.eq('Mutable values are not allowed as cache keys', ectx.exception.errinfo.get('mesg'))

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.cache.fixed("return()").put((foo,), bar)')
            self.eq('Mutable values are not allowed as cache keys', ectx.exception.errinfo.get('mesg'))

            with self.raises(s_exc.BadArg) as ectx:
                await core.nodes('$lib.cache.fixed("return()").pop((foo,))')
            self.eq('Mutable values are not allowed as cache keys', ectx.exception.errinfo.get('mesg'))

            ## non-primable key

            with self.raises(s_exc.NoSuchType) as ectx:
                await core.nodes('$cache = $lib.cache.fixed("return()") $cache.get($cache)')
            self.eq('Unable to convert object to Storm primitive.', ectx.exception.errinfo.get('mesg'))

            ## missing use of $cache_key - no error

            self.eq('newp', await core.callStorm('return($lib.cache.fixed("return(newp)").get(foo))'))
