
import bz2
import gzip
import json

import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.tests.utils as s_test

from synapse.tests.utils import alist
from synapse.lib.httpapi import Handler

class StormTypesTest(s_test.SynTest):

    async def test_storm_node_tags(self):
        async with self.getTestCore() as core:
            await core.eval('[ test:comp=(20, haha) +#foo +#bar test:comp=(30, hoho) ]').list()

            q = '''
            test:comp
            for $tag in $node.tags() {
                -> test:int [ +#$tag ]
            }
            '''

            await core.eval(q).list()

            self.len(1, await core.eval('test:int#foo').list())
            self.len(1, await core.eval('test:int#bar').list())

            q = '''
            test:comp
            for $tag in $node.tags(fo*) {
                -> test:int [ -#$tag ]
            }
            '''
            await core.eval(q).list()

            self.len(0, await core.eval('test:int#foo').list())
            self.len(1, await core.eval('test:int#bar').list())

    async def test_node_globtags(self):

        def check_fire_mesgs(storm_mesgs, expected_data):
            tmesgs = [m[1] for m in storm_mesgs if m[0] == 'storm:fire']
            self.len(1, tmesgs)
            test_data = set(tmesgs[0].get('data', {}).get('globs'))
            self.eq(test_data, expected_data)

        async with self.getTestCore() as core:
            q = '''[test:str=woot
                    +#foo.bar.baz.faz
                    +#foo.bar.jaz.faz
                    +#foo.knight.day.faz]'''
            nodes = await core.eval(q).list()
            self.len(1, nodes)

            # explicit behavior tests
            q = 'test:str=woot $globs=$node.globtags("foo.*.*.faz") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.streamstorm(q).list()
            e = {('bar', 'baz'), ('bar', 'jaz'), ('knight', 'day')}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.*") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.streamstorm(q).list()
            e = {'baz', 'jaz'}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.*.*") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.streamstorm(q).list()
            e = {('baz', 'faz'), ('jaz', 'faz')}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.**") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.streamstorm(q).list()
            e = {'baz', 'baz.faz', 'jaz', 'jaz.faz'}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.*.*.*") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.streamstorm(q).list()
            e = set()
            check_fire_mesgs(mesgs, e)

            # For loop example for a single-match case
            q = '''test:str=woot
            for $part in $node.globtags("foo.bar.*") {
                [test:str=$part]
            }'''
            mesgs = await core.streamstorm(q).list()
            self.len(1, await core.nodes('test:str=baz'))
            self.len(1, await core.nodes('test:str=jaz'))

            # For loop example for a multi-match case
            q = '''test:str=woot
                for ($part1, $part2, $part3) in $node.globtags("foo.*.*.*") {
                    [test:str=$part1] -test:str=woot [+#$part3]
                }'''
            mesgs = await core.streamstorm(q).list()
            self.len(1, await core.nodes('test:str=bar'))
            self.len(1, await core.nodes('test:str=knight'))
            self.len(2, await core.nodes('#faz'))

    async def test_storm_lib_base(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ inet:asn=$lib.min(20, 0x30) ]')
            self.len(1, nodes)
            self.eq(20, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.min(20, (10, 30)) ]')
            self.len(1, nodes)
            self.eq(10, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.max(20, 0x30) ]')
            self.len(1, nodes)
            self.eq(0x30, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.max(20, (10, 30)) ]')
            self.len(1, nodes)
            self.eq(30, nodes[0].ndef[1])

            nodes = await core.nodes('[ inet:asn=$lib.len(asdf) ]')
            self.len(1, nodes)
            self.eq(4, nodes[0].ndef[1])

            nodes = await core.nodes('[ test:str=$lib.guid() test:str=$lib.guid() ]')
            self.len(2, nodes)
            self.true(s_common.isguid(nodes[0].ndef[1]))
            self.true(s_common.isguid(nodes[1].ndef[1]))
            self.ne(nodes[0].ndef[1], nodes[1].ndef[1])

            nodes = await core.nodes('[ test:str=$lib.guid(hehe,haha) test:str=$lib.guid(hehe,haha) ]')
            self.len(2, nodes)
            self.true(s_common.isguid(nodes[0].ndef[1]))
            self.true(s_common.isguid(nodes[1].ndef[1]))
            self.eq(nodes[0].ndef[1], nodes[1].ndef[1])

            async with core.getLocalProxy() as prox:
                mesgs = [m async for m in prox.storm('$lib.print("hi there")') if m[0] == 'print']
                self.len(1, mesgs)
                self.stormIsInPrint('hi there', mesgs)

                mesgs = [m async for m in prox.storm('[ inet:fqdn=vertex.link inet:fqdn=woot.com ] $lib.print(:zone)')]
                mesgs = [m for m in mesgs if m[0] == 'print']
                self.len(2, mesgs)
                self.eq('vertex.link', mesgs[0][1]['mesg'])
                self.eq('woot.com', mesgs[1][1]['mesg'])

                mesgs = [m async for m in prox.storm("$lib.print('woot at: {s} {num}', s=hello, num=$(42+43))")]
                self.stormIsInPrint('woot at: hello 85', mesgs)

    async def test_storm_lib_dict(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('$blah = $lib.dict(foo=vertex.link) [ inet:fqdn=$blah.foo ]')
            self.len(1, nodes)
            self.eq('vertex.link', nodes[0].ndef[1])

    async def test_storm_lib_str(self):
        async with self.getTestCore() as core:
            q = '$v=vertex $l=link $fqdn=$lib.str.concat($v, ".", $l)' \
                ' [ inet:email=$lib.str.format("visi@{domain}", domain=$fqdn) ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq('visi@vertex.link', nodes[0].ndef[1])

    async def test_storm_lib_bytes_gzip(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                hstr = b'ohhai'
                ghstr = gzip.compress(hstr)
                mstr = b'ohgood'
                ggstr = gzip.compress(mstr)
                n2 = s_common.guid()
                n3 = s_common.guid()

                node1 = await snap.addNode('graph:node', '*', {'data': ghstr})
                node2 = await snap.addNode('graph:node', '*', {'data': mstr})

                text = f'''
                    graph:node={node1.ndef[1]}
                    $gzthing = :data
                    $foo = $gzthing.gunzip()
                    $lib.print($foo)

                    [ graph:node={n2} :data=$foo ]
                '''

                msgs = await core.streamstorm(text).list()

                # make sure we gunzip correctly
                nodes = await alist(snap.getNodesBy('graph:node', n2))
                self.eq(hstr, nodes[0].get('data'))

                # gzip
                text = f'''
                    graph:node={node2.ndef[1]}
                    $bar = :data
                    [ graph:node={n3} :data=$bar.gzip() ]
                '''
                msgs = await core.streamstorm(text).list()

                # make sure we gzip correctly
                nodes = await alist(snap.getNodesBy('graph:node', n3))
                self.eq(gzip.decompress(ggstr),
                        gzip.decompress(nodes[0].get('data')))

    async def test_storm_lib_bytes_bzip(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                hstr = b'ohhai'
                ghstr = bz2.compress(hstr)
                mstr = b'ohgood'
                ggstr = bz2.compress(mstr)
                n2 = s_common.guid()
                n3 = s_common.guid()

                node1 = await snap.addNode('graph:node', '*', {'data': ghstr})
                node2 = await snap.addNode('graph:node', '*', {'data': mstr})

                text = '''
                    graph:node={valu}
                    $bzthing = :data
                    $foo = $bzthing.bunzip()
                    $lib.print($foo)

                    [ graph:node={n2} :data=$foo ]
                '''
                text = text.format(valu=node1.ndef[1], n2=n2)
                msgs = await core.streamstorm(text).list()

                # make sure we bunzip correctly
                nodes = await alist(snap.getNodesBy('graph:node', n2))
                self.eq(hstr, nodes[0].props['data'])

                # bzip
                text = '''
                    graph:node={valu}
                    $bar = :data
                    [ graph:node={n3} :data=$bar.bzip() ]
                '''
                text = text.format(valu=node2.ndef[1], n3=n3)
                msgs = await core.streamstorm(text).list()

                # make sure we bzip correctly
                nodes = await alist(snap.getNodesBy('graph:node', n3))
                self.eq(ggstr, nodes[0].props['data'])

    async def test_storm_lib_bytes_json(self):
        async with self.getTestCore() as core:
            async with await core.snap() as snap:
                foo = {'a': 'ohhai'}
                ghstr = bytes(json.dumps(foo), 'utf8')
                n2 = s_common.guid()

                node1 = await snap.addNode('graph:node', '*', {'data': ghstr})

                text = '''
                    graph:node={valu}
                    $jzthing = :data
                    $foo = $jzthing.json()

                    [ graph:node={n2} :data=$foo ]
                '''
                text = text.format(valu=node1.ndef[1], n2=n2)
                msgs = await core.streamstorm(text).list()

                # make sure we json loaded correctly
                nodes = await alist(snap.getNodesBy('graph:node', n2))
                self.eq(foo, nodes[0].props['data'])

    async def test_storm_lib_list(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('$v=(foo,bar,baz) [ test:str=$v.index(1) test:int=$v.length() ]')
            self.eq(nodes[0].ndef, ('test:str', 'bar'))
            self.eq(nodes[1].ndef, ('test:int', 3))

            nodes = await core.nodes('[ test:comp=(10,lol) ] $x=$node.ndef().index(1).index(1) [ test:str=$x ]')
            self.eq(nodes[1].ndef, ('test:str', 'lol'))

            # sad case - index out of bounds.
            mesgs = await core.streamstorm('test:comp=(10,lol) $x=$node.ndef().index(2)').list()
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][0], 'StormRuntimeError')

    async def test_storm_lib_fire(self):
        async with self.getTestCore() as core:
            text = '$lib.fire(foo:bar, baz=faz)'

            gotn = [mesg async for mesg in core.streamstorm(text) if mesg[0] == 'storm:fire']

            self.len(1, gotn)

            self.eq(gotn[0][1]['type'], 'foo:bar')
            self.eq(gotn[0][1]['data']['baz'], 'faz')

    async def test_storm_node_repr(self):
        text = '''
            [ inet:ipv4=1.2.3.4 :loc=us]
            $ipv4 = $node.repr()
            $loc = $node.repr(loc)
            $valu = $lib.str.format("{ipv4} in {loc}", ipv4=$ipv4, loc=$loc)
            [ test:str=$valu ]
            +test:str
        '''

        async with self.getTestCore() as core:
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], '1.2.3.4 in us')

    async def test_storm_csv(self):
        async with self.getTestCore() as core:
            nodes = await core.eval('[test:str=1234 :tick=2001]').list()
            nodes = await core.eval('[test:str=9876 :tick=3001]').list()

            q = "test:str " \
                "$tick=$node.repr(tick) " \
                "$lib.csv.emit($node.form(), $node.value(), $tick, table=mytable)"

            mesgs = await core.streamstorm(q, {'show': ('err', 'csv:row')}).list()
            csv_rows = [m for m in mesgs if m[0] == 'csv:row']
            self.len(2, csv_rows)
            csv_rows.sort(key=lambda x: x[1].get('row')[1])
            self.eq(csv_rows[0],
                    ('csv:row', {'row': ['test:str', '1234', '2001/01/01 00:00:00.000'],
                                 'table': 'mytable'}))
            self.eq(csv_rows[1],
                    ('csv:row', {'row': ['test:str', '9876', '3001/01/01 00:00:00.000'],
                                 'table': 'mytable'}))

    async def test_storm_node_iden(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:int=10 test:str=$node.iden() ] +test:str')
            iden = s_common.ehex(s_common.buid(('test:int', 10)))
            self.eq(nodes[0].ndef, ('test:str', iden))
            self.len(1, nodes)

    async def test_storm_text_add(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes(
                '[ test:int=10 ] $text=$lib.text(hehe) { +test:int>=10 $text.add(haha) } [ test:str=$text.str() ] +test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'hehehaha'))

    async def test_storm_set(self):
        async with self.getTestCore() as core:
            await core.nodes('[inet:ipv4=1.2.3.4 :asn=20]')
            await core.nodes('[inet:ipv4=5.6.7.8 :asn=30]')

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.add(:asn)
                [ graph:node="*" ] +graph:node [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), (20, 30))

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.adds((:asn,:asn))
                [ graph:node="*" ] +graph:node [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), (20, 30))

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.adds((:asn,:asn))
                { +:asn=20 $set.rem(:asn) }
                [ graph:node="*" ] +graph:node [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), (30,))

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.add(:asn)
                $set.rems((:asn,:asn))
                [ graph:node="*" ] +graph:node [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), ())

    async def test_storm_path(self):
        async with self.getTestCore() as core:
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            q = '''
                inet:fqdn=vertex.link -> inet:dns:a -> inet:ipv4
                $idens = $path.idens()
                [ graph:node="*" ] +graph:node [ :data=$idens ]
            '''

            idens = (
                '02488bc284ffd0f60f474d5af66a8c0cf89789f766b51fde1d3da9b227005f47',
                '20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                '3ecd51e142a5acfcde42c02ff5c68378bfaf1eaf49fe9721550b6e7d6013b699',
            )

            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), idens)

    async def test_storm_trace(self):
        async with self.getTestCore() as core:
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')

            q = '''
                inet:fqdn=vertex.link

                $trace=$path.trace()

                -> inet:dns:a -> inet:ipv4

                /* Make a trace object from a path which already has nodes */
                $trace2=$path.trace()

                [ graph:node="*" ] +graph:node [ :data=$trace.idens() ]

                /* Print the contents of the second trace */
                $lib.print($trace2.idens())
                '''
            mesgs = await core.streamstorm(q).list()
            podes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(1, podes)
            pode = podes[0]

            idens = (
                '02488bc284ffd0f60f474d5af66a8c0cf89789f766b51fde1d3da9b227005f47',
                '20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
                '3ecd51e142a5acfcde42c02ff5c68378bfaf1eaf49fe9721550b6e7d6013b699',
            )

            self.eq(tuple(sorted(pode[1]['props'].get('data'))), idens)

            for iden in idens:
                self.stormIsInPrint(iden, mesgs)

    async def test_stormuser(self):
        # Do not include persistent vars support in this test see
        # test_persistent_vars for that behavior.
        async with self.getTestCore() as core:
            q = '$lib.print($lib.user.name())'
            mesgs = await s_test.alist(core.streamstorm(q))
            self.stormIsInPrint('root', mesgs)

    async def test_persistent_vars(self):
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                async with core.getLocalProxy() as prox:  # type: s_cortex.CoreApi
                    # User setup for $lib.user.vars() tests
                    ret1 = await prox.addAuthUser('user1')
                    iden1 = ret1.get('iden')
                    await prox.setUserPasswd('user1', 'secret')
                    await prox.addAuthRule('user1', (True, ('node:add',)))
                    await prox.addAuthRule('user1', (True, ('prop:set',)))
                    await prox.addAuthRule('user1', (True,
                                                     ('storm:globals:get', 'userkey',)))

                    # Basic tests as root for $lib.globals

                    q = '''$lib.globals.set(adminkey, sekrit)
                    $lib.globals.set(userkey, lessThanSekrit)
                    $lib.globals.set(throwaway, beep)
                    $valu=$lib.globals.get(adminkey)
                    $lib.print($valu)
                    '''
                    mesgs = await s_test.alist(prox.storm(q))
                    self.stormIsInPrint('sekrit', mesgs)

                    popq = '''$valu = $lib.globals.pop(throwaway)
                    $lib.print("pop valu is {valu}", valu=$valu)
                    '''
                    mesgs = await s_test.alist(prox.storm(popq))
                    self.stormIsInPrint('pop valu is beep', mesgs)

                    # get and pop take a secondary default value which may be returned
                    q = '''$valu = $lib.globals.get(throwaway, $(0))
                    $lib.print("get valu is {valu}", valu=$valu)
                    '''
                    mesgs = await s_test.alist(prox.storm(q))
                    self.stormIsInPrint('get valu is 0', mesgs)

                    q = '''$valu = $lib.globals.pop(throwaway, $(0))
                    $lib.print("pop valu is {valu}", valu=$valu)
                    '''
                    mesgs = await s_test.alist(prox.storm(q))
                    self.stormIsInPrint('pop valu is 0', mesgs)

                    listq = '''for ($key, $valu) in $lib.globals.list() {
                    $string = $lib.str.format("{key} is {valu}", key=$key, valu=$valu)
                    $lib.print($string)
                    }
                    '''
                    mesgs = await s_test.alist(prox.storm(listq))
                    self.len(2, [m for m in mesgs if m[0] == 'print'])
                    self.stormIsInPrint('adminkey is sekrit', mesgs)
                    self.stormIsInPrint('userkey is lessThanSekrit', mesgs)

                    # Sadpath - storing a valu into the hive that can't be
                    # msgpacked will fail
                    q = '[test:str=test] $lib.user.vars.set(mynode, $node)'
                    mesgs = await s_test.alist(prox.storm(q))
                    err = "can not serialize 'Node' object"
                    errs = [m for m in mesgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][1][1].get('mesg'), err)

                    # Sad path - names must be strings.
                    q = '$lib.user.vars.set((my, nested, valu), haha)'
                    mesgs = await s_test.alist(prox.storm(q))
                    err = 'The name of a persistent variable must be a string.'
                    errs = [m for m in mesgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][1][1].get('mesg'), err)

                    # Sad path - names must be strings.
                    q = '$lib.globals.set((my, nested, valu), haha)'
                    mesgs = await s_test.alist(prox.storm(q))
                    err = 'The name of a persistent variable must be a string.'
                    errs = [m for m in mesgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][1][1].get('mesg'), err)

                async with core.getLocalProxy() as uprox:  # type: s_cortex.CoreApi
                    self.true(await uprox.setCellUser(iden1))

                    q = '''$lib.user.vars.set(somekey, hehe)
                    $valu=$lib.user.vars.get(somekey)
                    $lib.print($valu)
                    '''
                    mesgs = await s_test.alist(uprox.storm(q))
                    self.stormIsInPrint('hehe', mesgs)

                    q = '''$lib.user.vars.set(somekey, hehe)
                    $lib.user.vars.set(anotherkey, weee)
                    [test:str=$lib.user.vars.get(somekey)]
                    '''
                    mesgs = await s_test.alist(uprox.storm(q))
                    self.len(1, await core.nodes('test:str=hehe'))

                    listq = '''for ($key, $valu) in $lib.user.vars.list() {
                        $string = $lib.str.format("{key} is {valu}", key=$key, valu=$valu)
                        $lib.print($string)
                    }
                    '''
                    mesgs = await s_test.alist(uprox.storm(listq))
                    self.stormIsInPrint('somekey is hehe', mesgs)
                    self.stormIsInPrint('anotherkey is weee', mesgs)

                    popq = '''$valu = $lib.user.vars.pop(anotherkey)
                    $lib.print("pop valu is {valu}", valu=$valu)
                    '''
                    mesgs = await s_test.alist(uprox.storm(popq))
                    self.stormIsInPrint('pop valu is weee', mesgs)

                    mesgs = await s_test.alist(uprox.storm(listq))
                    self.len(1, [m for m in mesgs if m[0] == 'print'])
                    self.stormIsInPrint('somekey is hehe', mesgs)

                    # get and pop take a secondary default value which may be returned
                    q = '''$valu = $lib.user.vars.get(newp, $(0))
                    $lib.print("get valu is {valu}", valu=$valu)
                    '''
                    mesgs = await s_test.alist(prox.storm(q))
                    self.stormIsInPrint('get valu is 0', mesgs)

                    q = '''$valu = $lib.user.vars.pop(newp, $(0))
                    $lib.print("pop valu is {valu}", valu=$valu)
                    '''
                    mesgs = await s_test.alist(prox.storm(q))
                    self.stormIsInPrint('pop valu is 0', mesgs)

                    # the user can access the specific core.vars key
                    # that they have access too but not the admin key
                    q = '''$valu=$lib.globals.get(userkey)
                        $lib.print($valu)
                        '''
                    mesgs = await s_test.alist(uprox.storm(q))
                    self.stormIsInPrint('lessThanSekrit', mesgs)

                    # While the user has get perm, they do not have set or pop
                    # permission
                    q = '''$valu=$lib.globals.pop(userkey)
                    $lib.print($valu)
                    '''
                    mesgs = await s_test.alist(uprox.storm(q))
                    self.len(0, [m for m in mesgs if m[0] == 'print'])
                    errs = [m for m in mesgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][1][0], 'AuthDeny')

                    q = '''$valu=$lib.globals.set(userkey, newSekritValu)
                    $lib.print($valu)
                    '''
                    mesgs = await s_test.alist(uprox.storm(q))
                    self.len(0, [m for m in mesgs if m[0] == 'print'])
                    errs = [m for m in mesgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][1][0], 'AuthDeny')

                    # Attempting to access the adminkey fails
                    q = '''$valu=$lib.globals.get(adminkey)
                    $lib.print($valu)
                    '''
                    mesgs = await s_test.alist(uprox.storm(q))
                    self.len(0, [m for m in mesgs if m[0] == 'print'])
                    errs = [m for m in mesgs if m[0] == 'err']
                    self.len(1, errs)
                    self.eq(errs[0][1][0], 'AuthDeny')

                    # if the user attempts to list the values in
                    # core.vars, they only get the values they can read.
                    corelistq = '''
                    for ($key, $valu) in $lib.globals.list() {
                        $string = $lib.str.format("{key} is {valu}", key=$key, valu=$valu)
                        $lib.print($string)
                    }
                    '''
                    mesgs = await s_test.alist(uprox.storm(corelistq))
                    self.len(1, [m for m in mesgs if m[0] == 'print'])
                    self.stormIsInPrint('userkey is lessThanSekrit', mesgs)

            async with self.getTestCore(dirn=dirn) as core:
                # And our variables do persist AFTER restarting the cortex,
                # so they are persistent via the hive.
                async with core.getLocalProxy() as uprox:  # type: s_cortex.CoreApi
                    self.true(await uprox.setCellUser(iden1))

                    mesgs = await s_test.alist(uprox.storm(listq))
                    self.len(1, [m for m in mesgs if m[0] == 'print'])
                    self.stormIsInPrint('somekey is hehe', mesgs)

                    q = '''$valu=$lib.globals.get(userkey)
                    $lib.print($valu)
                    '''
                    mesgs = await s_test.alist(uprox.storm(q))
                    self.stormIsInPrint('lessThanSekrit', mesgs)

                    # The StormHiveDict is safe when computing things
                    q = '''[test:int=1234]
                    $lib.user.vars.set(someint, $node.value())
                    [test:str=$lib.user.vars.get(someint)]
                    '''
                    podes = await s_test.alist(uprox.eval(q))
                    self.len(2, podes)
                    self.eq({('test:str', '1234'), ('test:int', 1234)},
                            {pode[0] for pode in podes})
