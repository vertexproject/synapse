import asyncio
import datetime
import unittest.mock as mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.coro as s_coro
import synapse.lib.storm as s_storm
import synapse.lib.version as s_version
import synapse.lib.httpapi as s_httpapi

import synapse.tests.utils as s_t_utils
from synapse.tests.utils import alist

class StormTest(s_t_utils.SynTest):

    async def test_lib_storm_basics(self):
        # a catch-all bucket for simple tests to avoid cortex construction
        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchVar):
                await core.nodes('inet:ipv4=$ipv4')

            # test that runtsafe vars stay runtsafe
            msgs = await core.stormlist('$foo=bar $lib.print($foo) if $node { $foo=$node.value() }')
            self.stormIsInPrint('bar', msgs)

            # test storm background command
            await core.nodes('''
                $lib.queue.add(foo)
                [inet:ipv4=1.2.3.4]
                background {
                    [it:dev:str=haha]
                    fini{
                        $lib.queue.get(foo).put(hehe)
                    }
                }''')
            self.eq((0, 'hehe'), await core.callStorm('return($lib.queue.get(foo).get())'))

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('[ ou:org=*] $text = $node.repr() | background $text')

            with self.raises(s_exc.NoSuchVar):
                await core.nodes('background { $lib.print($foo) }')

            # test the parallel command
            nodes = await core.nodes('parallel --size 4 { [ ou:org=* ] }')
            self.len(4, nodes)

            # check that subquery validation happens
            with self.raises(s_exc.NoSuchVar):
                await core.nodes('parallel --size 4 { [ ou:org=$foo ] }')

            # check that an exception on inbound percolates correctly
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ ou:org=* ou:org=foo ] | parallel { [:name=bar] }')

            # check that an exception in the parallel pipeline percolates correctly
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('parallel { [ou:org=foo] }')

            nodes = await core.nodes('ou:org | parallel {[ :name=foo ]}')
            self.true(all([n.get('name') == 'foo' for n in nodes]))

            # test $lib.exit() and the StormExit handlers
            msgs = [m async for m in core.view.storm('$lib.exit()')]
            self.eq(msgs[-1][0], 'fini')

            # test that the view command functions correctly
            iden = s_common.guid()
            view0 = await core.callStorm('return($lib.view.get().fork().iden)')
            with self.raises(s_exc.NoSuchVar):
                opts = {'vars': {'view': view0}}
                await core.nodes('view.exec $view { [ ou:org=$iden] }', opts=opts)

            opts = {'vars': {'view': view0, 'iden': iden}}
            self.len(0, await core.nodes('view.exec $view { [ ou:org=$iden] }', opts=opts))

            opts = {'view': view0, 'vars': {'iden': iden}}
            self.len(1, await core.nodes('ou:org=$iden', opts=opts))

            # check safe per-node execution of view.exec
            view1 = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'vars': {'view': view1}}
            # lol...
            self.len(1, await core.nodes('''
                [ ou:org=$view :name="[ inet:ipv4=1.2.3.4 ]" ]
                $foo=$node.repr() $bar=:name
                | view.exec $foo $bar
            ''', opts=opts))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4', opts={'view': view1}))

            self.len(0, await core.nodes('$x = $lib.null if ($x and $x > 20) { [ ps:contact=* ] }'))
            self.len(1, await core.nodes('$x = $lib.null if ($lib.true or $x > 20) { [ ps:contact=* ] }'))

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            cmd0 = {
                'name': 'asroot.not',
                'storm': '[ ou:org=* ]',
            }
            cmd1 = {
                'name': 'asroot.yep',
                'storm': '[ it:dev:str=$lib.user.allowed(node.add.it:dev:str) ]',
                'asroot': True,
            }
            await core.setStormCmd(cmd0)
            await core.setStormCmd(cmd1)

            opts = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.nodes('asroot.not', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('asroot.yep', opts=opts)

            await visi.addRule((True, ('storm', 'asroot', 'cmd', 'asroot', 'yep')))

            nodes = await core.nodes('asroot.yep', opts=opts)
            self.len(1, nodes)
            self.eq('false', nodes[0].ndef[1])

            await visi.addRule((True, ('storm', 'asroot', 'cmd', 'asroot')))
            self.len(1, await core.nodes('asroot.not', opts=opts))

            pkg0 = {
                'name': 'foopkg',
                'version': (0, 0, 1),
                'modules': (
                    {
                        'name': 'foo.bar',
                        'storm': '''
                            function lol() {
                                [ ou:org=* ]
                                return($node.iden())
                            }
                            function dyncall() {
                                return($lib.feed.list())
                            }
                            function dyniter() {
                                for $item in $lib.queue.add(dyniter).gets(wait=$lib.false) {}
                                return(woot)
                            }
                        ''',
                        'asroot': True,
                    },
                    {
                        'name': 'foo.baz',
                        'storm': 'function lol() { [ ou:org=* ] return($node.iden()) }',
                    },
                )
            }

            await core.loadStormPkg(pkg0)

            await core.nodes('$lib.import(foo.baz)', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.import(foo.bar)', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.import(foo.baz).lol()', opts=opts)

            await visi.addRule((True, ('storm', 'asroot', 'mod', 'foo', 'bar')))
            self.len(1, await core.nodes('yield $lib.import(foo.bar).lol()', opts=opts))

            await visi.addRule((True, ('storm', 'asroot', 'mod', 'foo')))
            self.len(1, await core.nodes('yield $lib.import(foo.baz).lol()', opts=opts))

            # coverage for dyncall/dyniter with asroot...
            await core.nodes('$lib.import(foo.bar).dyncall()', opts=opts)
            await core.nodes('$lib.import(foo.bar).dyniter()', opts=opts)

            self.eq(s_version.version, await core.callStorm('return($lib.version.synapse())'))
            self.true(await core.callStorm('return($lib.version.matches($lib.version.synapse(), ">=2.9.0"))'))
            self.false(await core.callStorm('return($lib.version.matches($lib.version.synapse(), ">0.0.1,<2.0"))'))

            # test out the stormlib axon API
            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            opts = {'user': visi.iden, 'vars': {'port': port}}
            wget = '''
                $url = $lib.str.format("https://visi:secret@127.0.0.1:{port}/api/v1/healthcheck", port=$port)
                return($lib.axon.wget($url, ssl=$lib.false))
            '''
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(wget, opts=opts)

            # test wget runtsafe / per-node / per-node with cmdopt
            nodes = await core.nodes(f'wget https://127.0.0.1:{port}/api/v1/active')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:urlfile')

            nodes = await core.nodes(f'inet:url=https://127.0.0.1:{port}/api/v1/active | wget')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:urlfile')

            nodes = await core.nodes(f'inet:urlfile:url=https://127.0.0.1:{port}/api/v1/active | wget :url')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:urlfile')

            # check that the file name got set...
            nodes = await core.nodes(f'wget https://127.0.0.1:{port}/api/v1/active | -> file:bytes +:name=active')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'file:bytes')

            msgs = await core.stormlist(f'wget https://127.0.0.1:{port}/api/v1/newp')
            self.stormIsInWarn('HTTP code 404', msgs)

            # test request timeout
            async def timeout(self):
                await asyncio.sleep(2)

            with mock.patch.object(s_httpapi.ActiveV1, 'get', timeout):
                msgs = await core.stormlist(f'wget https://127.0.0.1:{port}/api/v1/active --timeout 1')
                self.stormIsInWarn('TimeoutError', msgs)

            await visi.addRule((True, ('storm', 'lib', 'axon', 'wget')))
            resp = await core.callStorm(wget, opts=opts)
            self.true(resp['ok'])

            # check that the feed API uses toprim
            email = await core.callStorm('''
                $iden = $lib.guid()
                $props = $lib.dict(email=visi@vertex.link)
                $lib.feed.ingest(syn.nodes, (
                    ( (ps:contact, $iden), $lib.dict(props=$props)),
                ))
                ps:contact=$iden
                return(:email)
            ''')
            self.eq(email, 'visi@vertex.link')

            email = await core.callStorm('''
                $iden = $lib.guid()
                $props = $lib.dict(email=visi@vertex.link)
                yield $lib.feed.genr(syn.nodes, (
                    ( (ps:contact, $iden), $lib.dict(props=$props)),
                ))
                return(:email)
            ''')
            self.eq(email, 'visi@vertex.link')

            pkg0 = {'name': 'hehe', 'version': '1.2.3'}
            await core.addStormPkg(pkg0)
            self.eq('1.2.3', await core.callStorm('return($lib.pkg.get(hehe).version)'))

            self.eq(None, await core.callStorm('return($lib.pkg.get(nopkg))'))

            # test for $lib.queue.gen()
            self.eq(0, await core.callStorm('return($lib.queue.gen(woot).size())'))
            # and again to test *not* creating it...
            self.eq(0, await core.callStorm('return($lib.queue.gen(woot).size())'))

            self.eq({'foo': 'bar'}, await core.callStorm('return($lib.dict(    foo    =    bar   ))'))

            ddef0 = await core.callStorm('return($lib.dmon.add(${ $lib.queue.gen(hehedmon).put(lolz) $lib.time.sleep(10) }, name=hehedmon))')
            ddef1 = await core.callStorm('return($lib.dmon.get($iden))', opts={'vars': {'iden': ddef0.get('iden')}})
            self.none(await core.callStorm('return($lib.dmon.get(newp))'))

            self.eq(ddef0['iden'], ddef1['iden'])

            self.eq((0, 'lolz'), await core.callStorm('return($lib.queue.gen(hehedmon).get(0))'))

            task = core.stormdmons.getDmon(ddef0['iden']).task
            self.true(await core.callStorm(f'return($lib.dmon.bump($iden))', opts={'vars': {'iden': ddef0['iden']}}))
            self.ne(task, core.stormdmons.getDmon(ddef0['iden']).task)

            self.true(await core.callStorm(f'return($lib.dmon.stop($iden))', opts={'vars': {'iden': ddef0['iden']}}))
            self.none(core.stormdmons.getDmon(ddef0['iden']).task)

            self.true(await core.callStorm(f'return($lib.dmon.start($iden))', opts={'vars': {'iden': ddef0['iden']}}))
            self.nn(core.stormdmons.getDmon(ddef0['iden']).task)

            self.false(await core.callStorm(f'return($lib.dmon.bump(newp))'))
            self.false(await core.callStorm(f'return($lib.dmon.stop(newp))'))
            self.false(await core.callStorm(f'return($lib.dmon.start(newp))'))

            self.eq((1, 'lolz'), await core.callStorm('return($lib.queue.gen(hehedmon).get(1))'))

            async with core.getLocalProxy() as proxy:
                self.nn(await proxy.getStormDmon(ddef0['iden']))
                self.true(await proxy.bumpStormDmon(ddef0['iden']))
                self.true(await proxy.disableStormDmon(ddef0['iden']))
                self.true(await proxy.enableStormDmon(ddef0['iden']))
                self.false(await proxy.bumpStormDmon('newp'))
                self.false(await proxy.disableStormDmon('newp'))
                self.false(await proxy.enableStormDmon('newp'))

            await core.callStorm('[ inet:ipv4=11.22.33.44 :asn=56 inet:asn=99]')
            await core.callStorm('[ ps:person=* +#foo ]')

            view, layr = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')

            opts = {'view': view}
            self.len(0, await core.callStorm('''
                $list = $lib.list()
                $layr = $lib.view.get().layers.0
                for $item in $layr.getStorNodes() {
                    $list.append($item)
                }
                return($list)''', opts=opts))

            await core.addTagProp('score', ('int', {}), {})
            await core.callStorm('[ inet:ipv4=11.22.33.44 :asn=99 inet:fqdn=55667788.link +#foo=2020 +#foo:score=100]', opts=opts)
            await core.callStorm('inet:ipv4=11.22.33.44 $node.data.set(foo, bar)', opts=opts)
            await core.callStorm('inet:ipv4=11.22.33.44 [ +(blahverb)> { inet:asn=99 } ]', opts=opts)

            sodes = await core.callStorm('''
                $list = $lib.list()
                $layr = $lib.view.get().layers.0
                for $item in $layr.getStorNodes() {
                    $list.append($item)
                }
                return($list)''', opts=opts)
            self.len(2, sodes)

            ipv4 = await core.callStorm('''
                $list = $lib.list()
                $layr = $lib.view.get().layers.0
                for ($buid, $sode) in $layr.getStorNodes() {
                    yield $buid
                }
                +inet:ipv4
                return($node.repr())''', opts=opts)
            self.eq('11.22.33.44', ipv4)

            sodes = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getStorNodes())', opts=opts)
            self.eq((1577836800000, 1577836800001), sodes[0]['tags']['foo'])
            self.eq((99, 9), sodes[0]['props']['asn'])
            self.eq((185999660, 4), sodes[1]['valu'])
            self.eq(('unicast', 1), sodes[1]['props']['type'])
            self.eq((56, 9), sodes[1]['props']['asn'])

            bylayer = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getByLayer())', opts=opts)
            self.ne(bylayer['ndef'], layr)
            self.eq(bylayer['props']['asn'], layr)
            self.eq(bylayer['tags']['foo'], layr)
            self.ne(bylayer['props']['type'], layr)

            msgs = await core.stormlist('inet:ipv4=11.22.33.44 | merge', opts=opts)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4:asn = 99', msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo = ('2020/01/01 00:00:00.000', '2020/01/01 00:00:00.001')", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo:score = 100", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 DATA foo = 'bar'", msgs)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 +(blahverb)> a0df14eab785847912993519f5606bbe741ad81afb51b81455ac6982a5686436', msgs)

            msgs = await core.stormlist('ps:person | merge --diff', opts=opts)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4:asn = 99', msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo = ('2020/01/01 00:00:00.000', '2020/01/01 00:00:00.001')", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4#foo:score = 100", msgs)
            self.stormIsInPrint("aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 DATA foo = 'bar'", msgs)
            self.stormIsInPrint('aade791ea3263edd78e27d0351e7eed8372471a0434a6f0ba77101b5acf4f9bc inet:ipv4 +(blahverb)> a0df14eab785847912993519f5606bbe741ad81afb51b81455ac6982a5686436', msgs)

            await core.callStorm('inet:ipv4=11.22.33.44 | merge --apply', opts=opts)
            nodes = await core.nodes('inet:ipv4=11.22.33.44')
            self.len(1, nodes)
            self.nn(nodes[0].getTag('foo'))
            self.eq(99, nodes[0].get('asn'))

            bylayer = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getByLayer())', opts=opts)
            self.ne(bylayer['ndef'], layr)
            self.ne(bylayer['props']['asn'], layr)
            self.ne(bylayer['tags']['foo'], layr)

            # confirm that we moved node data and light edges
            self.eq('bar', await core.callStorm('inet:ipv4=11.22.33.44 return($node.data.get(foo))'))
            self.eq(99, await core.callStorm('inet:ipv4=11.22.33.44 -(blahverb)> inet:asn return($node.value())'))
            self.eq(100, await core.callStorm('inet:ipv4=11.22.33.44 return(#foo:score)'))

            sodes = await core.callStorm('inet:ipv4=11.22.33.44 return($node.getStorNodes())', opts=opts)
            self.eq(sodes[0], {})

            with self.raises(s_exc.CantMergeView):
                await core.callStorm('inet:ipv4=11.22.33.44 | merge')

            # test printing a merge that the node was created in the top layer
            msgs = await core.stormlist('[ inet:fqdn=mvmnasde.com ] | merge', opts=opts)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn = mvmnasde.com', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:host = mvmnasde', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:domain = com', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:issuffix = False', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:iszone = True', msgs)
            self.stormIsInPrint('3496c02183961db4fbc179f0ceb5526347b37d8ff278279917b6eb6d39e1e272 inet:fqdn:zone = mvmnasde.com', msgs)

            # merge all the nodes with anything stored in the top layer...
            await core.callStorm('''
                for ($buid, $sode) in $lib.view.get().layers.0.getStorNodes() {
                    yield $buid
                }
                | merge --apply
            ''', opts=opts)

            self.len(0, await core.callStorm('''
                $list = $lib.list()
                for ($buid, $sode) in $lib.view.get().layers.0.getStorNodes() {
                    $list.append($buid)
                }
                return($list)
            ''', opts=opts))

            self.eq('c8af8cfbcc36ba5dec9858124f8f014d', await core.callStorm('''
                $iden = c8af8cfbcc36ba5dec9858124f8f014d
                [ inet:fqdn=vertex.link <(woots)+ {[ meta:source=$iden ]} ]
                <(woots)- meta:source
                return($node.value())
            '''))

            with self.raises(s_exc.BadArg):
                await core.callStorm('inet:fqdn=vertex.link $tags = $node.globtags(foo.***)')

            nodes = await core.nodes('$form=inet:fqdn [ *$form=visi.com ]')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:fqdn', 'visi.com'))

            # test non-runtsafe invalid form deref node add
            with self.raises(s_exc.NoSuchForm):
                await core.callStorm('[ it:dev:str=hehe:haha ] $form=$node.value() [*$form=lol]')

            async def sleeper():
                await asyncio.sleep(2)
            task = core.schedCoro(sleeper())
            self.false(await s_coro.waittask(task, timeout=0.1))

    async def test_storm_pipe(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                $crap = (foo, bar, baz)

                $pipe = $lib.pipe.gen(${
                    $pipe.puts($crap)
                    $pipe.put(hehe)
                    $pipe.put(haha)

                    // cause the generator to tick once for coverage...
                    [ ou:org=* ]
                })

                for $items in $pipe.slices(size=2) {
                    for $devstr in $items {
                        [ it:dev:str=$devstr ]
                    }
                }
            ''')
            self.len(5, nodes)
            nvals = [n.ndef[1] for n in nodes]
            self.eq(('foo', 'bar', 'baz', 'hehe', 'haha'), nvals)

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.pipe.gen(${}, size=999999)')

            with self.raises(s_exc.BadArg):
                await core.nodes('$pipe = $lib.pipe.gen(${}) for $item in $pipe.slices(size=999999) {}')

            with self.raises(s_exc.BadArg):
                await core.nodes('$pipe = $lib.pipe.gen(${}) for $item in $pipe.slice(size=999999) {}')

            msgs = await core.stormlist('''
                $pipe = $lib.pipe.gen(${ $pipe.put((0 + "woot")) })
                for $items in $pipe.slices() { $lib.print($items) }
            ''')

            self.stormIsInWarn('pipe filler error: BadCast', msgs)
            self.false(any([m for m in msgs if m[0] == 'err']))

            self.eq(0, await core.callStorm('return($lib.pipe.gen(${}).size())'))

            with self.raises(s_exc.BadArg):
                await core.nodes('''
                    $pipe = $lib.pipe.gen(${ $pipe.put(woot) })

                    for $items in $pipe.slices() { $lib.print($items) }

                    $pipe.put(hehe)
                ''')

            with self.raises(s_exc.BadArg):
                await core.nodes('''
                    $pipe = $lib.pipe.gen(${ $pipe.put(woot) })

                    for $items in $pipe.slices() { $lib.print($items) }

                    $pipe.puts((hehe, haha))
                ''')

            nodes = await core.nodes('''
                $crap = (foo, bar, baz)

                $pipe = $lib.pipe.gen(${ $pipe.puts((foo, bar, baz)) })

                for $devstr in $pipe.slice(size=2) {
                    [ it:dev:str=$devstr ]
                }
            ''')
            self.len(2, nodes)
            nvals = [n.ndef[1] for n in nodes]
            self.eq(('foo', 'bar'), nvals)

    async def test_storm_undef(self):

        async with self.getTestCore() as core:

            # pernode variants
            self.none(await core.callStorm('''
                [ ps:contact = * ]
                if $node {
                    $foo = $lib.dict()
                    $foo.bar = $lib.undef
                    return($foo.bar)
                }
            '''))
            with self.raises(s_exc.NoSuchVar):
                await core.callStorm('[ps:contact=*] $foo = $node.repr() $foo = $lib.undef return($foo)')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('''
                    [ps:contact=*]
                    $path.vars.foo = lol
                    $path.vars.foo = $lib.undef
                    return($path.vars.foo)
                ''')

            # runtsafe variants
            self.eq(('foo', 'baz'), await core.callStorm('$foo = (foo, bar, baz) $foo.1 = $lib.undef return($foo)'))
            self.eq(('foo', 'bar'), await core.callStorm('$foo = (foo, bar, baz) $foo."-1" = $lib.undef return($foo)'))
            self.none(await core.callStorm('$foo = $lib.dict() $foo.bar = 10 $foo.bar = $lib.undef return($foo.bar)'))
            self.eq(('woot',), await core.callStorm('''
                $foo = (foo, bar, baz)
                $foo.0 = $lib.undef
                $foo.0 = $lib.undef
                $foo.0 = $lib.undef
                // one extra to test the exc handler
                $foo.0 = $lib.undef
                $foo.append(hehe)
                $foo.0 = woot
                return($foo)
            '''))
            with self.raises(s_exc.NoSuchVar):
                await core.callStorm('$foo = 10 $foo = $lib.undef return($foo)')

    async def test_storm_pkg_load(self):
        cont = s_common.guid()
        pkg = {
            'name': 'testload',
            'version': '0.3.0',
            'modules': (
                {
                    'name': 'testload',
                    'storm': 'function x() { return((0)) }',
                },
            ),
            'onload': f'[ ps:contact={cont} ] $lib.print(teststring) return($path.vars.newp)'
        }
        class PkgHandler(s_httpapi.Handler):

            async def get(self, name):

                if name == 'notok':
                    self.sendRestErr('FooBar', 'baz faz')
                    return

                self.sendRestRetn(pkg)

        async with self.getTestCore() as core:
            core.addHttpApi('/api/v1/pkgtest/(.*)', PkgHandler, {'cell': core})
            port = (await core.addHttpsPort(0, host='127.0.0.1'))[1]

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/newp/newp')
            self.stormIsInWarn('pkg.load got HTTP code: 404', msgs)

            msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/pkgtest/notok')
            self.stormIsInWarn('pkg.load got JSON error: FooBar', msgs)

            with self.getAsyncLoggerStream('synapse.cortex',
                                      "{'mesg': 'teststring'}") as stream:
                msgs = await core.stormlist(f'pkg.load --ssl-noverify https://127.0.0.1:{port}/api/v1/pkgtest/yep')
                self.stormIsInPrint('testload @0.3.0', msgs)
                self.true(await stream.wait(6))

            self.len(1, await core.nodes(f'ps:contact={cont}'))

    async def test_storm_tree(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:fqdn=www.vertex.link ] | tree { :domain -> inet:fqdn }')
            vals = [n.ndef[1] for n in nodes]
            self.eq(('www.vertex.link', 'vertex.link', 'link'), vals)

            # Max recursion fail
            q = '[ inet:fqdn=www.vertex.link ] | tree { inet:fqdn=www.vertex.link }'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

    async def test_storm_movetag(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('hehe.haha', valu=(20, 30))

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe.haha'))

                await tagnode.set('doc', 'haha doc')
                await tagnode.set('title', 'haha title')

            await core.nodes('movetag hehe woot')

            self.len(0, await core.nodes('#hehe'))
            self.len(0, await core.nodes('#hehe.haha'))

            self.len(1, await core.nodes('#woot'))
            self.len(1, await core.nodes('#woot.haha'))

            async with await core.snap() as snap:

                newt = await core.getNodeByNdef(('syn:tag', 'woot.haha'))

                self.eq(newt.get('doc'), 'haha doc')
                self.eq(newt.get('title'), 'haha title')

                node = await snap.getNodeByNdef(('test:str', 'foo'))
                self.eq((20, 30), node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe'))
                self.eq('woot', node.get('isnow'))

                node = await snap.getNodeByNdef(('syn:tag', 'hehe.haha'))
                self.eq('woot.haha', node.get('isnow'))

                node = await snap.addNode('test:str', 'bar')

                # test isnow plumbing
                await node.addTag('hehe.haha')

                self.nn(node.tags.get('woot'))
                self.nn(node.tags.get('woot.haha'))

                self.none(node.tags.get('hehe'))
                self.none(node.tags.get('hehe.haha'))

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'foo')
                await node.addTag('hehe', valu=(20, 30))

                tagnode = await snap.getNodeByNdef(('syn:tag', 'hehe'))

                await tagnode.set('doc', 'haha doc')

            await core.nodes('movetag hehe woot')

            self.len(0, await core.nodes('#hehe'))
            self.len(1, await core.nodes('#woot'))

            async with await core.snap() as snap:
                newt = await core.getNodeByNdef(('syn:tag', 'woot'))

                self.eq(newt.get('doc'), 'haha doc')

        # Test moving a tag which has tags on it.
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'V')
                await node.addTag('a.b.c', (None, None))
                tnode = await snap.getNodeByNdef(('syn:tag', 'a.b'))
                await tnode.addTag('foo', (None, None))

            await core.nodes('movetag a.b a.m')
            self.len(2, await core.nodes('#foo'))
            self.len(1, await core.nodes('syn:tag=a.b +#foo'))
            self.len(1, await core.nodes('syn:tag=a.m +#foo'))

        # Test moving a tag to another tag which is a string prefix of the source
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                node = await snap.addNode('test:str', 'V')
                await node.addTag('aaa.b.ccc', (None, None))
                await node.addTag('aaa.b.ddd', (None, None))
                node = await snap.addNode('test:str', 'Q')
                await node.addTag('aaa.barbarella.ccc', (None, None))

            await core.nodes('movetag aaa.b aaa.barbarella')

            self.len(7, await core.nodes('syn:tag'))
            self.len(1, await core.nodes('syn:tag=aaa.barbarella.ccc'))
            self.len(1, await core.nodes('syn:tag=aaa.barbarella.ddd'))

        # Move a tag with tagprops
        async def seed_tagprops(core):
            await core.addTagProp('test', ('int', {}), {})
            await core.addTagProp('note', ('str', {}), {})
            q = '[test:int=1 +#hehe.haha +#hehe:test=1138 +#hehe.beep:test=8080 +#hehe.beep:note="oh my"]'
            nodes = await core.nodes(q)
            self.eq(nodes[0].tagprops.get(('hehe', 'test')), 1138)
            self.eq(nodes[0].tagprops.get(('hehe.beep', 'test')), 8080)
            self.eq(nodes[0].tagprops.get(('hehe.beep', 'note')), 'oh my')

        async with self.getTestCore() as core:
            await seed_tagprops(core)
            await core.nodes('movetag hehe woah')

            self.len(0, await core.nodes('#hehe'))
            nodes = await core.nodes('#woah')
            self.len(1, nodes)
            self.eq(nodes[0].tagprops, {('woah', 'test'): 1138,
                                        ('woah.beep', 'test'): 8080,
                                        ('woah.beep', 'note'): 'oh my',
                                        })

        async with self.getTestCore() as core:
            await seed_tagprops(core)
            await core.nodes('movetag hehe.beep woah.beep')

            self.len(1, await core.nodes('#hehe'))
            nodes = await core.nodes('#woah')
            self.len(1, nodes)
            self.eq(nodes[0].tagprops, {('hehe', 'test'): 1138,
                                        ('woah.beep', 'test'): 8080,
                                        ('woah.beep', 'note'): 'oh my',
                                        })

        # Sad path
        async with self.getTestCore() as core:
            # Test moving a tag to itself
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag foo.bar foo.bar')
            # Test moving a tag which does not exist
            with self.raises(s_exc.BadOperArg):
                await core.nodes('movetag foo.bar duck.knight')

    async def test_storm_spin(self):

        async with self.getTestCore() as core:

            await self.agenlen(0, core.eval('[ test:str=foo test:str=bar ] | spin'))
            await self.agenlen(2, core.eval('test:str=foo test:str=bar'))

    async def test_storm_reindex_sudo(self):

        async with self.getTestCore() as core:

            mesgs = await core.stormlist('reindex')
            self.stormIsInWarn('reindex currently does nothing', mesgs)

            msgs = await core.stormlist('.created | sudo')
            self.stormIsInWarn('Sudo is deprecated and does nothing', msgs)

    async def test_storm_count(self):

        async with self.getTestCoreAndProxy() as (realcore, core):
            await self.agenlen(2, core.eval('[ test:str=foo test:str=bar ]'))

            mesgs = await alist(core.storm('test:str=foo test:str=bar | count |  [+#test.tag]'))
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(2, nodes)
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 2 nodes.')

            mesgs = await alist(core.storm('test:str=newp | count'))
            prints = [mesg for mesg in mesgs if mesg[0] == 'print']
            self.len(1, prints)
            self.eq(prints[0][1].get('mesg'), 'Counted 0 nodes.')
            nodes = [mesg for mesg in mesgs if mesg[0] == 'node']
            self.len(0, nodes)

    async def test_storm_uniq(self):
        async with self.getTestCore() as core:
            q = "[test:comp=(123, test) test:comp=(123, duck) test:comp=(123, mode)]"
            await self.agenlen(3, core.eval(q))
            nodes = await alist(core.eval('test:comp -> *'))
            self.len(3, nodes)
            nodes = await alist(core.eval('test:comp -> * | uniq | count'))
            self.len(1, nodes)

    async def test_storm_iden(self):
        async with self.getTestCore() as core:
            q = "[test:str=beep test:str=boop]"
            nodes = await alist(core.eval(q))
            self.len(2, nodes)
            idens = [node.iden() for node in nodes]

            iq = ' '.join(idens)
            # Demonstrate the iden lift does pass through previous nodes in the pipeline
            mesgs = await core.nodes(f'[test:str=hehe] | iden {iq} | count')
            self.len(3, mesgs)

            q = 'iden newp'
            with self.getLoggerStream('synapse.lib.snap', 'Failed to decode iden') as stream:
                await self.agenlen(0, core.eval(q))
                self.true(stream.wait(1))

            q = 'iden deadb33f'
            with self.getLoggerStream('synapse.lib.snap', 'iden must be 32 bytes') as stream:
                await self.agenlen(0, core.eval(q))
                self.true(stream.wait(1))

    async def test_minmax(self):

        async with self.getTestCore() as core:

            minval = core.model.type('time').norm('2015')[0]
            midval = core.model.type('time').norm('2016')[0]
            maxval = core.model.type('time').norm('2017')[0]

            async with await core.snap() as snap:
                # Ensure each node we make has its own discrete created time.
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2015',
                                                             '.seen': '2015'})
                minc = node.get('.created')
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2016',
                                                             '.seen': '2016'})
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:guid', '*', {'tick': '2017',
                                                             '.seen': '2017'})
                await asyncio.sleep(0.01)
                node = await snap.addNode('test:str', '1', {'tick': '2016'})

            # Relative paths
            nodes = await core.nodes('test:guid | max :tick')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), maxval)

            nodes = await core.nodes('test:guid | min :tick')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            # Universal prop for relative path
            nodes = await core.nodes('.created>=$minc | max .created',
                                     {'vars': {'minc': minc}})
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), midval)

            nodes = await core.nodes('.created>=$minc | min .created',
                                     {'vars': {'minc': minc}})
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            # Variables nodesuated
            nodes = await core.nodes('test:guid ($tick, $tock) = .seen | min $tick')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), minval)

            nodes = await core.nodes('test:guid ($tick, $tock) = .seen | max $tock')
            self.len(1, nodes)
            self.eq(nodes[0].get('tick'), maxval)

            text = '''[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 ]
                      { +inet:ipv4=1.2.3.4 [ :asn=10 ] }
                      { +inet:ipv4=5.6.7.8 [ :asn=20 ] }
                      $asn = :asn | min $asn'''

            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(0x01020304, nodes[0].ndef[1])

            text = '''[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 ]
                      { +inet:ipv4=1.2.3.4 [ :asn=10 ] }
                      { +inet:ipv4=5.6.7.8 [ :asn=20 ] }
                      $asn = :asn | max $asn'''

            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(0x05060708, nodes[0].ndef[1])

            # Sad paths where the specify an invalid property name
            with self.raises(s_exc.NoSuchProp):
                self.len(0, await core.nodes('test:guid | max :newp'))

            with self.raises(s_exc.NoSuchProp):
                self.len(0, await core.nodes('test:guid | min :newp'))

            # test that intervals work
            maxnodes = await core.nodes('[ ou:org=* ]')
            maxnodes = await core.nodes('[ ou:org=* +#minmax ]')
            minnodes = await core.nodes('[ ou:org=* +#minmax=(1981, 2010) ]')
            await core.nodes('[ ou:org=* +#minmax=(1982, 2018) ]')
            maxnodes = await core.nodes('[ ou:org=* +#minmax=(1997, 2020) ]')

            testmin = await core.nodes('ou:org | min #minmax')
            self.eq(testmin[0].ndef, minnodes[0].ndef)

            testmax = await core.nodes('ou:org | max #minmax')
            self.eq(testmax[0].ndef, maxnodes[0].ndef)

    async def test_scrape(self):

        async with self.getTestCore() as core:

            # runtsafe tests
            nodes = await core.nodes('$foo=6.5.4.3 | scrape $foo')
            self.len(0, nodes)

            self.len(1, await core.nodes('inet:ipv4=6.5.4.3'))

            nodes = await core.nodes('$foo=6.5.4.3 | scrape $foo --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x06050403))

            nodes = await core.nodes('[inet:ipv4=9.9.9.9 ] $foo=6.5.4.3 | scrape $foo')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x09090909))

            nodes = await core.nodes('[inet:ipv4=9.9.9.9 ] $foo=6.5.4.3 | scrape $foo --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x06050403))

            nodes = await core.nodes('$foo="6[.]5[.]4[.]3" | scrape $foo --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x06050403))

            nodes = await core.nodes('$foo="6[.]5[.]4[.]3" | scrape $foo --yield --skiprefang')
            self.len(0, nodes)

            # per-node tests

            guid = s_common.guid()

            await core.nodes(f'[ inet:search:query={guid} :text="hi there 5.5.5.5" ]')
            # test the special runtsafe but still per-node invocation
            nodes = await core.nodes('inet:search:query | scrape')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:search:query')

            self.len(1, await core.nodes('inet:ipv4=5.5.5.5'))

            nodes = await core.nodes('inet:search:query | scrape :text --yield')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

            nodes = await core.nodes('inet:search:query | scrape :text --refs | -(refs)> *')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x05050505))

            # test runtsafe and non-runtsafe failure to create node
            msgs = await core.stormlist('scrape "https://t.c…"')
            self.stormIsInWarn('BadTypeValue', msgs)
            msgs = await core.stormlist('[ media:news=* :title="https://t.c…" ] | scrape :title')
            self.stormIsInWarn('BadTypeValue', msgs)

    async def test_storm_tee(self):

        async with self.getTestCore() as core:

            async with await core.snap() as snap:
                guid = s_common.guid()
                await snap.addNode('edge:refs', (('media:news', guid), ('inet:ipv4', '1.2.3.4')))
                await snap.addNode('inet:dns:a', ('woot.com', '1.2.3.4'))

            await core.nodes('[ inet:ipv4=1.2.3.4 :asn=0 ]')

            nodes = await core.nodes('inet:ipv4=1.2.3.4 | tee { -> * }')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))

            nodes = await core.nodes('inet:ipv4=1.2.3.4 | tee --join { -> * }')
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef, ('inet:ipv4', 0x01020304))

            q = 'inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * }'
            nodes = await core.nodes(q)
            self.len(3, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef, ('inet:ipv4', 0x01020304))

            q = 'inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * } { -> edge:refs:n2 :n1 -> * }'
            nodes = await core.nodes(q)
            self.len(4, nodes)
            self.eq(nodes[0].ndef, ('inet:asn', 0))
            self.eq(nodes[1].ndef[0], ('inet:dns:a'))
            self.eq(nodes[2].ndef[0], ('media:news'))
            self.eq(nodes[3].ndef, ('inet:ipv4', 0x01020304))

            # Empty queries are okay - they will just return the input node
            q = 'inet:ipv4=1.2.3.4 | tee {}'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # Subqueries are okay too but will just yield the input back out
            q = 'inet:ipv4=1.2.3.4 | tee {{ -> * }}'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # Sad path
            q = 'inet:ipv4=1.2.3.4 | tee'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            # Runtsafe tee
            q = 'tee { inet:ipv4=1.2.3.4 } { inet:ipv4 -> * }'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            exp = {
                ('inet:asn', 0),
                ('inet:ipv4', 0x01020304),
            }
            self.eq(exp, {x.ndef for x in nodes})

            q = '$foo=woot.com tee { inet:ipv4=1.2.3.4 } { inet:fqdn=$foo <- * }'
            nodes = await core.nodes(q)
            self.len(3, nodes)
            exp = {
                ('inet:ipv4', 0x01020304),
                ('inet:fqdn', 'woot.com'),
                ('inet:dns:a', ('woot.com', 0x01020304)),
            }
            self.eq(exp, {n.ndef for n in nodes})

            # Variables are scoped down into the sub runtime
            q = (
                f'$foo=5 tee '
                f'{{ [ inet:asn=3 ] }} '
                f'{{ [ inet:asn=4 ] $lib.print("made asn node: {{node}}", node=$node) }} '
                f'{{ [ inet:asn=$foo ] }}'
            )
            msgs = await core.stormlist(q)
            self.stormIsInPrint("made asn node: Node{(('inet:asn', 4)", msgs)
            podes = [m[1] for m in msgs if m[0] == 'node']
            self.eq({('inet:asn', 3), ('inet:asn', 4), ('inet:asn', 5)},
                    {p[0] for p in podes})

            # lift a non-existent node and feed to tee.
            q = 'inet:fqdn=newp.com tee { inet:ipv4=1.2.3.4 } { inet:ipv4 -> * }'
            nodes = await core.nodes(q)
            self.len(2, nodes)
            exp = {
                ('inet:asn', 0),
                ('inet:ipv4', 0x01020304),
            }
            self.eq(exp, {x.ndef for x in nodes})

            q = 'tee'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

    async def test_storm_yieldvalu(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')

            buid0 = nodes[0].buid
            iden0 = s_common.ehex(buid0)

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': (iden0,)}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            def genr():
                yield iden0

            async def agenr():
                yield iden0

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': (iden0,)}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': buid0}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': genr()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': agenr()}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': nodes[0]}})
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('yield $foo', opts={'vars': {'foo': None}})
            self.len(0, nodes)

            with self.raises(s_exc.BadLiftValu):
                await core.nodes('yield $foo', opts={'vars': {'foo': 'asdf'}})

    async def test_storm_splicelist(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            mesgs = await core.stormlist('[ test:str=foo ]')
            await asyncio.sleep(0.01)

            mesgs = await core.stormlist('[ test:str=bar ]')

            tick = mesgs[0][1]['tick']
            tickdt = datetime.datetime.utcfromtimestamp(tick / 1000.0)
            tickstr = tickdt.strftime('%Y/%m/%d %H:%M:%S.%f')

            tock = mesgs[-1][1]['tock']
            tockdt = datetime.datetime.utcfromtimestamp(tock / 1000.0)
            tockstr = tockdt.strftime('%Y/%m/%d %H:%M:%S.%f')

            await asyncio.sleep(0.01)
            mesgs = await core.stormlist('[ test:str=baz ]')

            nodes = await core.nodes(f'splice.list')
            self.len(9, nodes)

            nodes = await core.nodes(f'splice.list --mintimestamp {tick}')
            self.len(4, nodes)

            nodes = await core.nodes(f'splice.list --mintime "{tickstr}"')
            self.len(4, nodes)

            nodes = await core.nodes(f'splice.list --maxtimestamp {tock}')
            self.len(7, nodes)

            nodes = await core.nodes(f'splice.list --maxtime "{tockstr}"')
            self.len(7, nodes)

            nodes = await core.nodes(f'splice.list --mintimestamp {tick} --maxtimestamp {tock}')
            self.len(2, nodes)

            nodes = await core.nodes(f'splice.list --mintime "{tickstr}" --maxtime "{tockstr}"')
            self.len(2, nodes)

            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('splice.list --mintime badtime'))
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('splice.list --maxtime nope'))

            visi = await prox.addUser('visi', passwd='secret')

            await prox.addUserRule(visi['iden'], (True, ('node', 'add')))
            await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set')))

            async with core.getLocalProxy(user='visi') as asvisi:

                # make sure a normal user only gets their own splices
                nodes = await alist(asvisi.eval("[ test:str=hehe ]"))

                nodes = await alist(asvisi.eval("splice.list"))
                self.len(2, nodes)

                # should get all splices now as an admin
                await prox.setUserAdmin(visi['iden'], True)

                nodes = await alist(asvisi.eval("splice.list"))
                self.len(11, nodes)

    async def test_storm_spliceundo(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            await core.addTagProp('risk', ('int', {'min': 0, 'max': 100}), {'doc': 'risk score'})

            visi = await prox.addUser('visi', passwd='secret')

            await prox.addUserRule(visi['iden'], (True, ('node', 'add')))
            await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set')))
            await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

            async with core.getLocalProxy(user='visi') as asvisi:

                nodes = await alist(asvisi.eval("[ test:str=foo ]"))
                await asyncio.sleep(0.01)

                mesgs = await alist(asvisi.storm("[ test:str=bar ]"))
                tick = mesgs[0][1]['tick']
                tock = mesgs[-1][1]['tock']

                mesgs = await alist(asvisi.storm("test:str=bar [ +#test.tag ]"))

                # undo a node add

                nodes = await alist(asvisi.eval("test:str=bar"))
                self.len(1, nodes)

                # undo adding a node fails without tag:del perms if is it tagged
                q = f'splice.list --mintimestamp {tick} --maxtimestamp {tock} | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'del')))

                # undo adding a node fails without node:del perms
                q = f'splice.list --mintimestamp {tick} --maxtimestamp {tock} | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'del')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=bar"))
                self.len(0, nodes)

                # undo a node delete

                # undo deleting a node fails without node:add perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'add')))

                q = 'splice.list | limit 2 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=bar"))
                self.len(1, nodes)

                # undo adding a prop

                nodes = await alist(asvisi.eval("test:str=foo [ :tick=2000 ]"))
                self.nn(nodes[0][1]['props'].get('tick'))

                # undo adding a prop fails without prop:del perms
                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'del',)))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.none(nodes[0][1]['props'].get('tick'))

                # undo updating a prop

                nodes = await alist(asvisi.eval("test:str=foo [ :tick=2000 ]"))
                oldv = nodes[0][1]['props']['tick']
                self.nn(oldv)

                nodes = await alist(asvisi.eval("test:str=foo [ :tick=3000 ]"))
                self.ne(oldv, nodes[0][1]['props']['tick'])

                # undo updating a prop fails without prop:set perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'prop', 'set')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set',)))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(oldv, nodes[0][1]['props']['tick'])

                # undo deleting a prop

                nodes = await alist(asvisi.eval("test:str=foo [ -:tick ]"))
                self.none(nodes[0][1]['props'].get('tick'))

                # undo deleting a prop fails without prop:set perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'prop', 'set')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(oldv, nodes[0][1]['props']['tick'])

                # undo adding a tag

                nodes = await alist(asvisi.eval("test:str=foo [ +#rep=2000 ]"))
                tagv = nodes[0][1]['tags'].get('rep')
                self.nn(tagv)

                # undo adding a tag fails without tag:del perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'del',)))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'del',)))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.none(nodes[0][1]['tags'].get('rep'))

                # undo deleting a tag

                # undo deleting a tag fails without tag:add perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(tagv, nodes[0][1]['tags'].get('rep'))

                # undo updating a tag
                nodes = await alist(asvisi.eval("test:str=foo [ +#rep=2000 ]"))
                oldv = nodes[0][1]['tags'].get('rep')
                nodes = await alist(asvisi.eval("test:str=foo [ +#rep=3000 ]"))
                self.ne(oldv, nodes[0][1]['tags'].get('rep'))

                q = 'splice.list | limit 1 | splice.undo'
                await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(oldv, nodes[0][1]['tags'].get('rep'))

                # undo adding a tagprop

                nodes = await alist(asvisi.eval("test:str=foo [ +#rep:risk=50 ]"))
                tagv = nodes[0][1]['tagprops']['rep'].get('risk')
                self.nn(tagv)

                # undo adding a tagprop fails without tag:del perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'del')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'del')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.none(nodes[0][1]['tagprops'].get('rep'))

                # undo deleting a tagprop

                # undo deleting a tagprop fails without tag:add perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(tagv, nodes[0][1]['tagprops']['rep'].get('risk'))

                # undo updating a tagprop

                nodes = await alist(asvisi.eval("test:str=foo [ +#rep:risk=0 ]"))
                self.ne(tagv, nodes[0][1]['tagprops']['rep'].get('risk'))

                # undo updating a tagprop fails without prop:set perms
                await prox.delUserRule(visi['iden'], (True, ('node', 'tag', 'add')))

                q = 'splice.list | limit 1 | splice.undo'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add')))
                nodes = await alist(asvisi.eval(q))

                nodes = await alist(asvisi.eval("test:str=foo"))
                self.eq(tagv, nodes[0][1]['tagprops']['rep'].get('risk'))

                # sending nodes of form other than syn:splice doesn't work
                q = 'test:str | limit 1 | splice.undo'
                await self.agenraises(s_exc.StormRuntimeError, asvisi.eval(q))

                # must be admin to use --force for node deletion
                await alist(asvisi.eval('[ test:cycle0=foo :cycle1=bar ]'))
                await alist(asvisi.eval('[ test:cycle1=bar :cycle0=foo ]'))

                nodes = await alist(asvisi.eval("test:cycle0"))
                self.len(1, nodes)

                q = 'splice.list | +:type="node:add" +:form="test:cycle0" | limit 1 | splice.undo'
                await self.agenraises(s_exc.CantDelNode, asvisi.eval(q))

                q = 'splice.list | +:type="node:add" +:form="test:cycle0" | limit 1 | splice.undo --force'
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.setUserAdmin(visi['iden'], True)

                nodes = await alist(asvisi.eval(q))
                nodes = await alist(asvisi.eval("test:cycle0"))
                self.len(0, nodes)

    async def test_storm_argv_parser(self):

        pars = s_storm.Parser(prog='hehe')
        pars.add_argument('--hehe')
        self.none(pars.parse_args(['--lol']))
        self.isin("ERROR: Expected 0 positional arguments. Got 1: ['--lol']", pars.mesgs)

        pars = s_storm.Parser(prog='hehe')
        pars.add_argument('hehe')
        opts = pars.parse_args(['-h'])
        self.notin("ERROR: The argument <hehe> is required.", pars.mesgs)
        self.isin('Usage: hehe [options] <hehe>', pars.mesgs)
        self.isin('Options:', pars.mesgs)
        self.isin('  --help                      : Display the command usage.', pars.mesgs)
        self.isin('Arguments:', pars.mesgs)
        self.isin('  <hehe>                      : No help available', pars.mesgs)

        pars = s_storm.Parser()
        pars.add_argument('--no-foo', default=True, action='store_false')
        opts = pars.parse_args(['--no-foo'])
        self.false(opts.no_foo)

        pars = s_storm.Parser()
        pars.add_argument('--yada')
        self.none(pars.parse_args(['--yada']))
        self.true(pars.exited)

        pars = s_storm.Parser()
        pars.add_argument('--yada', action='append')
        self.none(pars.parse_args(['--yada']))
        self.true(pars.exited)

        pars = s_storm.Parser()
        pars.add_argument('--yada', nargs='?')
        opts = pars.parse_args(['--yada'])
        self.none(opts.yada)

        pars = s_storm.Parser()
        pars.add_argument('--yada', nargs='+')
        self.none(pars.parse_args(['--yada']))
        self.true(pars.exited)

        pars = s_storm.Parser()
        pars.add_argument('--yada', type='int')
        self.none(pars.parse_args(['--yada', 'hehe']))
        self.true(pars.exited)

        # check help output formatting of optargs
        pars = s_storm.Parser()
        pars.add_argument('--star', nargs='*')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--star [<star> ...]', helptext)

        pars = s_storm.Parser()
        pars.add_argument('--plus', nargs='+')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--plus <plus> [<plus> ...]', helptext)

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='?')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--ques [ques]', helptext)

        # Check formatting for store_true / store_false optargs
        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs=2, type='int')
        pars.add_argument('--beep', action='store_true', help='beep beep')
        pars.add_argument('--boop', action='store_false', help='boop boop')
        pars.help()
        helptext = '\n'.join(pars.mesgs)
        self.isin('--ques <ques>               : No help available', helptext)
        self.isin('--beep                      : beep beep', helptext)
        self.isin('--boop                      : boop boop', helptext)

        # test some nargs type intersections
        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='?', type='int')
        self.none(pars.parse_args(['--ques', 'asdf']))
        helptext = '\n'.join(pars.mesgs)
        self.isin("Invalid value for type (int): asdf", helptext)

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='*', type='int')
        self.none(pars.parse_args(['--ques', 'asdf']))
        helptext = '\n'.join(pars.mesgs)
        self.isin("Invalid value for type (int): asdf", helptext)

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs='+', type='int')
        self.none(pars.parse_args(['--ques', 'asdf']))
        helptext = '\n'.join(pars.mesgs)
        self.isin("Invalid value for type (int): asdf", helptext)

        pars = s_storm.Parser()
        pars.add_argument('foo', type='int')
        self.none(pars.parse_args(['asdf']))
        helptext = '\n'.join(pars.mesgs)
        self.isin("Invalid value for type (int): asdf", helptext)

        # argument count mismatch
        pars = s_storm.Parser()
        pars.add_argument('--ques')
        self.none(pars.parse_args(['--ques']))
        helptext = '\n'.join(pars.mesgs)
        self.isin("An argument is required for --ques", helptext)

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs=2)
        self.none(pars.parse_args(['--ques', 'lolz']))
        helptext = '\n'.join(pars.mesgs)
        self.isin("2 arguments are required for --ques", helptext)

        pars = s_storm.Parser()
        pars.add_argument('--ques', nargs=2, type='int')
        self.none(pars.parse_args(['--ques', 'lolz', 'hehe']))
        helptext = '\n'.join(pars.mesgs)
        self.isin("Invalid value for type (int): lolz", helptext)

        # test time argtype
        ttyp = s_datamodel.Model().type('time')

        pars = s_storm.Parser()
        pars.add_argument('--yada', type='time')
        args = pars.parse_args(['--yada', '20201021-1day'])
        self.nn(args)
        self.eq(ttyp.norm('20201021-1day')[0], args.yada)

        args = pars.parse_args(['--yada', 1603229675444])
        self.nn(args)
        self.eq(ttyp.norm(1603229675444)[0], args.yada)

        self.none(pars.parse_args(['--yada', 'hehe']))
        self.true(pars.exited)
        helptext = '\n'.join(pars.mesgs)
        self.isin("Invalid value for type (time): hehe", helptext)

        # test ival argtype
        ityp = s_datamodel.Model().type('ival')

        pars = s_storm.Parser()
        pars.add_argument('--yada', type='ival')
        args = pars.parse_args(['--yada', '20201021-1day'])
        self.nn(args)
        self.eq(ityp.norm('20201021-1day')[0], args.yada)

        args = pars.parse_args(['--yada', 1603229675444])
        self.nn(args)
        self.eq(ityp.norm(1603229675444)[0], args.yada)

        args = pars.parse_args(['--yada', ('20201021', '20201023')])
        self.nn(args)
        self.eq(ityp.norm(('20201021', '20201023'))[0], args.yada)

        args = pars.parse_args(['--yada', (1603229675444, '20201021')])
        self.nn(args)
        self.eq(ityp.norm((1603229675444, '20201021'))[0], args.yada)

        self.none(pars.parse_args(['--yada', 'hehe']))
        self.true(pars.exited)
        helptext = '\n'.join(pars.mesgs)
        self.isin("Invalid value for type (ival): hehe", helptext)

        # check adding argument with invalid type
        with self.raises(s_exc.BadArg):
            pars = s_storm.Parser()
            pars.add_argument('--yada', type=int)

    async def test_liftby_edge(self):
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=test1 +(refs)> { [test:int=7] } ]')
            await core.nodes('[ test:str=test1 +(refs)> { [test:int=8] } ]')
            await core.nodes('[ test:str=test2 +(refs)> { [test:int=8] } ]')

            nodes = await core.nodes('lift.byverb refs')
            self.eq(sorted([n.ndef[1] for n in nodes]), ['test1', 'test2'])

            nodes = await core.nodes('lift.byverb --n2 refs ')
            self.eq(sorted([n.ndef[1] for n in nodes]), [7, 8])

            nodes = await core.nodes('lift.byverb $v', {'vars': {'v': 'refs'}})
            self.eq(sorted([n.ndef[1] for n in nodes]), ['test1', 'test2'])

            q = '[(test:str=refs) (test:str=foo)] $v=$node.value() | lift.byverb $v'
            nodes = await core.nodes(q)
            self.len(4, nodes)
            self.eq({n.ndef[1] for n in nodes},
                    {'test1', 'test2', 'refs', 'foo'})

    async def test_storm_nested_root(self):
        async with self.getTestCore() as core:
            self.eq(20, await core.callStorm('''
            $foo = (100)
            function x() {
                function y() {
                    function z() {
                        $foo = (20)
                    }
                    $z()
                }
                $y()
            }
            $x()
            return ($foo)
            '''))

    async def test_edges_del(self):
        async with self.getTestCore() as core:

            await core.nodes('[ test:str=test1 +(refs)> { [test:int=7 test:int=8] } ]')
            await core.nodes('[ test:str=test1 +(seen)> { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 -(*)> *'))

            await core.nodes('test:str=test1 | edges.del refs')
            self.len(0, await core.nodes('test:str=test1 -(refs)> *'))
            self.len(2, await core.nodes('test:str=test1 -(seen)> *'))

            await core.nodes('test:str=test1 [ +(refs)> { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 -(*)> *'))

            await core.nodes('test:str=test1 | edges.del *')
            self.len(0, await core.nodes('test:str=test1 -(*)> *'))

            # Test --n2
            await core.nodes('test:str=test1 [ <(refs)+ { [test:int=7 test:int=8] } ]')
            await core.nodes('test:str=test1 [ <(seen)+ { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 <(*)- *'))

            await core.nodes('test:str=test1 | edges.del refs --n2')
            self.len(0, await core.nodes('test:str=test1 <(refs)- *'))
            self.len(2, await core.nodes('test:str=test1 <(seen)- *'))

            await core.nodes('test:str=test1 [ <(refs)+ { [test:int=7 test:int=8] } ]')

            self.len(4, await core.nodes('test:str=test1 <(*)- *'))

            await core.nodes('test:str=test1 | edges.del * --n2')
            self.len(0, await core.nodes('test:str=test1 <(*)- *'))

            # Test non-runtsafe usage
            await core.nodes('[ test:str=refs +(refs)> { [test:int=7 test:int=8] } ]')
            await core.nodes('[ test:str=seen +(seen)> { [test:int=7 test:int=8] } ]')

            self.len(2, await core.nodes('test:str=refs -(refs)> *'))
            self.len(2, await core.nodes('test:str=seen -(seen)> *'))

            await core.nodes('test:str=refs test:str=seen $v=$node.value() | edges.del $v')

            self.len(0, await core.nodes('test:str=refs -(refs)> *'))
            self.len(0, await core.nodes('test:str=seen -(seen)> *'))

            await core.nodes('test:str=refs [ <(refs)+ { [test:int=7 test:int=8] } ]')
            await core.nodes('test:str=seen [ <(seen)+ { [test:int=7 test:int=8] } ]')

            self.len(2, await core.nodes('test:str=refs <(refs)- *'))
            self.len(2, await core.nodes('test:str=seen <(seen)- *'))

            await core.nodes('test:str=refs test:str=seen $v=$node.value() | edges.del $v --n2')

            self.len(0, await core.nodes('test:str=refs <(refs)- *'))
            self.len(0, await core.nodes('test:str=seen <(seen)- *'))

            await core.nodes('test:str=refs [ <(refs)+ { [test:int=7 test:int=8] } ]')
            await core.nodes('[ test:str=* <(seen)+ { [test:int=7 test:int=8] } ]')

            self.len(2, await core.nodes('test:str=refs <(refs)- *'))
            self.len(2, await core.nodes('test:str=* <(seen)- *'))

            await core.nodes('test:str=refs test:str=* $v=$node.value() | edges.del $v --n2')

            self.len(0, await core.nodes('test:str=refs <(refs)- *'))
            self.len(0, await core.nodes('test:str=* <(seen)- *'))

    async def test_storm_pushpull(self):

        with self.getTestDir() as dirn:

            async with self.getTestCore(dirn=dirn) as core:

                visi = await core.auth.addUser('visi')
                await visi.setPasswd('secret')

                await core.auth.rootuser.setPasswd('secret')
                host, port = await core.dmon.listen('tcp://127.0.0.1:0/')

                # setup a trigger so we know when the nodes move...
                view0, layr0 = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')
                view1, layr1 = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')
                view2, layr2 = await core.callStorm('$view = $lib.view.get().fork() return(($view.iden, $view.layers.0.iden))')

                opts = {'vars': {
                    'view0': view0,
                    'view1': view1,
                    'view2': view2,
                    'layr0': layr0,
                    'layr1': layr1,
                    'layr2': layr2,
                }}

                # lets get some auth denies...
                async with core.getLocalProxy(user='visi') as asvisi:

                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr0).addPush(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr0).delPush(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).addPull(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).delPull(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).addPull(hehe)', opts=opts)
                    with self.raises(s_exc.AuthDeny):
                        await asvisi.callStorm(f'$lib.layer.get($layr2).delPull(hehe)', opts=opts)

                actv = len(core.activecoros)
                # view0 -push-> view1 <-pull- view2
                await core.callStorm(f'$lib.layer.get($layr0).addPush("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)
                await core.callStorm(f'$lib.layer.get($layr2).addPull("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)

                purl = await core.callStorm('for ($iden, $pdef) in $lib.layer.get($layr2).get(pulls) { return($pdef.url) }', opts=opts)
                self.true(purl.startswith('tcp://root:****@127.0.0.1'))
                purl = await core.callStorm('for ($iden, $pdef) in $lib.layer.get($layr0).get(pushs) { return($pdef.url) }', opts=opts)
                self.true(purl.startswith('tcp://root:****@127.0.0.1'))

                self.eq(2, len(core.activecoros) - actv)
                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(1, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(1, [t for t in tasks if t.get('name').startswith('layer push:')])

                await core.nodes('[ ps:contact=* ]', opts={'view': view0})

                # wait for first write so we can get the correct offset
                await core.layers.get(layr2).waitEditOffs(0, timeout=3)
                offs = await core.layers.get(layr2).getEditOffs()

                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.layers.get(layr2).waitEditOffs(offs + 10, timeout=3)

                self.len(3, await core.nodes('ps:contact', opts={'view': view1}))
                self.len(3, await core.nodes('ps:contact', opts={'view': view2}))

                # remove and ensure no replay on restart
                await core.nodes('ps:contact | delnode', opts={'view': view2})
                self.len(0, await core.nodes('ps:contact', opts={'view': view2}))

            conf = {'dmon:listen': f'tcp://127.0.0.1:{port}'}
            async with self.getTestCore(dirn=dirn, conf=conf) as core:

                await asyncio.sleep(0)

                offs = await core.layers.get(layr2).getEditOffs()
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.nodes('[ ps:contact=* ]', opts={'view': view0})
                await core.layers.get(layr2).waitEditOffs(offs + 6, timeout=3)

                # confirm we dont replay and get the old one back...
                self.len(3, await core.nodes('ps:contact', opts={'view': view2}))

                actv = len(core.activecoros)
                # remove all pushes / pulls
                await core.callStorm('''
                    for $layr in $lib.layer.list() {
                        $pushs = $layr.get(pushs)
                        if $pushs {
                            for ($iden, $pdef) in $pushs { $layr.delPush($iden) }
                        }
                        $pulls = $layr.get(pulls)
                        if $pulls {
                            for ($iden, $pdef) in $pulls { $layr.delPull($iden) }
                        }
                    }
                ''')
                self.eq(actv - 2, len(core.activecoros))
                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(0, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(0, [t for t in tasks if t.get('name').startswith('layer push:')])

                # code coverage for push/pull dict exists but has no entries
                self.none(await core.callStorm('return($lib.layer.get($layr2).delPull($lib.guid()))', opts=opts))
                self.none(await core.callStorm('return($lib.layer.get($layr0).delPush($lib.guid()))', opts=opts))

                # add a push/pull and remove the layer to cancel it...
                await core.callStorm(f'$lib.layer.get($layr0).addPush("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)
                await core.callStorm(f'$lib.layer.get($layr2).addPull("tcp://root:secret@127.0.0.1:{port}/*/layer/{layr1}")', opts=opts)

                await asyncio.sleep(0)

                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(1, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(1, [t for t in tasks if t.get('name').startswith('layer push:')])
                self.eq(actv, len(core.activecoros))

                tasks = [cdef.get('task') for cdef in core.activecoros.values()]

                await core.callStorm('$lib.view.del($view0)', opts=opts)
                await core.callStorm('$lib.view.del($view1)', opts=opts)
                await core.callStorm('$lib.view.del($view2)', opts=opts)
                await core.callStorm('$lib.layer.del($layr0)', opts=opts)
                await core.callStorm('$lib.layer.del($layr1)', opts=opts)
                await core.callStorm('$lib.layer.del($layr2)', opts=opts)

                # Wait for the active coros to die
                for task in [t for t in tasks if t is not None]:
                    self.true(await s_coro.waittask(task, timeout=5))

                tasks = await core.callStorm('return($lib.ps.list())')
                self.len(0, [t for t in tasks if t.get('name').startswith('layer pull:')])
                self.len(0, [t for t in tasks if t.get('name').startswith('layer push:')])
                self.eq(actv - 2, len(core.activecoros))

                with self.raises(s_exc.SchemaViolation):
                    await core.addLayrPush('newp', {})
                with self.raises(s_exc.SchemaViolation):
                    await core.addLayrPull('newp', {})

                # sneak a bit of coverage for the raw library in here...
                fake = {
                    'time': s_common.now(),
                    'iden': s_common.guid(),
                    'user': s_common.guid(),
                    'url': 'tcp://localhost',
                }
                self.none(await core.addLayrPush('newp', fake))
                self.none(await core.addLayrPull('newp', fake))

                self.none(await core.delLayrPull('newp', 'newp'))
                self.none(await core.delLayrPull(layr0, 'newp'))
                self.none(await core.delLayrPush('newp', 'newp'))
                self.none(await core.delLayrPush(layr0, 'newp'))

                # main view/layer have None for pulls/pushs
                self.none(await core.delLayrPull(core.getView().layers[0].iden, 'newp'))
                self.none(await core.delLayrPush(core.getView().layers[0].iden, 'newp'))

                async with await s_telepath.openurl(f'tcp://visi:secret@127.0.0.1:{port}/*/view') as proxy:
                    self.eq(core.getView().iden, await proxy.getCellIden())
                    with self.raises(s_exc.AuthDeny):
                        await proxy.storNodeEdits((), {})

                with self.raises(s_exc.NoSuchPath):
                    async with await s_telepath.openurl(f'tcp://root:secret@127.0.0.1:{port}/*/newp'):
                        pass

                class LayrBork:
                    async def syncNodeEdits(self, offs, wait=True):
                        if False: yield None
                        raise s_exc.SynErr()

                fake = {'iden': s_common.guid(), 'user': s_common.guid()}
                # this should fire the reader and exit cleanly when he explodes
                await core._pushBulkEdits(LayrBork(), LayrBork(), fake)

                class FastPull:
                    async def syncNodeEdits(self, offs, wait=True):
                        yield (0, range(2000))

                class FastPush:
                    def __init__(self):
                        self.edits = []
                    async def storNodeEdits(self, edits, meta):
                        self.edits.extend(edits)

                pull = FastPull()
                push = FastPush()

                await core._pushBulkEdits(pull, push, fake)
                self.eq(push.edits, tuple(range(2000)))

                # a quick/ghetto test for coverage...
                layr = core.getView().layers[0]
                layr.logedits = False
                with self.raises(s_exc.BadArg):
                    await layr.waitEditOffs(200)
