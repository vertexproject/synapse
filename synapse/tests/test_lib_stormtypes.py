import bz2
import gzip
import json
import base64
import asyncio
import hashlib
import binascii
import datetime

from datetime import timezone as tz
from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.provenance as s_provenance

import synapse.tests.utils as s_test

from synapse.tests.utils import alist

MINSECS = 60
HOURSECS = 60 * MINSECS
DAYSECS = 24 * HOURSECS

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
        pdef = {
            'name': 'foo',
            'desc': 'test',
            'version': (0, 0, 1),
            'modules': [
                {
                    'name': 'test',
                    'storm': 'function f(a) { return ($a) }',
                }
            ],
            'commands': [
            ],
        }
        async with self.getTestCore() as core:

            await core.addStormPkg(pdef)
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

            # lib.sorted()
            q = '''
                $set = $lib.set(c, b, a)
                for $x in $lib.sorted($set) {
                    [ test:str=$x ]
                }
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)
            self.eq(nodes[0].ndef[1], 'a')
            self.eq(nodes[1].ndef[1], 'b')
            self.eq(nodes[2].ndef[1], 'c')

            # $lib.import
            q = '$test = $lib.import(test) $lib.print($test)'
            msgs = await core.streamstorm(q).list()
            self.stormIsInPrint('stormtypes.Lib object', msgs)
            q = '$test = $lib.import(newp)'
            msgs = await core.streamstorm(q).list()
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'NoSuchName')
            self.eq(erfo[1][1].get('name'), 'newp')

    async def test_storm_lib_query(self):
        async with self.getTestCore() as core:
            # basic
            q = '''
            $foo = ${ [test:str=theevalthatmendo] }
            $foo.exec()
            '''
            await core.nodes(q)
            nodes = await core.nodes('test:str=theevalthatmendo')
            self.len(1, nodes)

            # make sure our scope goes down
            q = '''
            $bar = ${ [test:str=$foo] }

            $foo = "this little node went to market"
            $bar.exec()
            $foo = "this little node stayed home"
            $bar.exec()
            $foo = "this little node had roast beef"
            $bar.exec()
            '''
            msgs = await core.streamstorm(q).list()
            nodes = [m for m in msgs if m[0] == 'node:add']
            self.len(3, nodes)
            self.eq(nodes[0][1]['ndef'], ('test:str', 'this little node went to market'))
            self.eq(nodes[1][1]['ndef'], ('test:str', 'this little node stayed home'))
            self.eq(nodes[2][1]['ndef'], ('test:str', 'this little node had roast beef'))

            # but that it doesn't come back up
            q = '''
            $foo = "that is one neato burrito"
            $baz = ${ $bar=$lib.str.concat(wompwomp, $lib.guid()) }
            $baz.exec()
            $lib.print($bar)
            [ test:str=$foo ]
            '''

            msgs = await core.streamstorm(q).list()
            prints = [m for m in msgs if m[0] == 'print']
            self.len(0, prints)

            # make sure returns work
            q = '''
            $foo = $(10)
            $bar = ${ return ( $($foo+1) ) }
            [test:int=$bar.exec()]
            '''
            msgs = await core.streamstorm(q).list()
            nodes = [m for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(nodes[0][1][0], ('test:int', 11))

            # make sure it inherits the runt it's created in, not exec'd in
            q = '''
            $foo = ${$lib.print("look ma, my runt") $bing = $(0) }

            function foofunc() {
                $bing = $(99)
                yield $foo.exec()
                $lib.print("bing is now {bing}", bing=$bing)
                return ($(0))
            }

            $foofunc()
            '''
            msgs = await core.streamstorm(q).list()
            self.stormIsInPrint('look ma, my runt', msgs)
            self.stormIsInPrint('bing is now 99', msgs)

    async def test_storm_lib_node(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:str=woot :tick=2001] [ test:int=$node.isform(test:str) ] +test:int')
            self.eq(1, nodes[0].ndef[1])

            q = 'test:str=woot $lib.fire(name=pode, pode=$node.pack(dorepr=True))'
            msgs = await core.streamstorm(q, opts={'repr': True}).list()
            pode = [m[1] for m in msgs if m[0] == 'node'][0]
            apode = [m[1].get('data').get('pode') for m in msgs if m[0] == 'storm:fire'][0]
            self.eq(pode[0], ('test:str', 'woot'))
            pode[1].pop('path')
            self.eq(pode, apode)

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

            nodes = await core.nodes('$s = woot [ test:int=$s.startswith(w) ]')
            self.eq(1, nodes[0].ndef[1])

            nodes = await core.nodes('$s = woot [ test:int=$s.endswith(visi) ]')
            self.eq(0, nodes[0].ndef[1])

            nodes = await core.nodes('$s = woot [ test:str=$s.rjust(10) ]')
            self.eq('      woot', nodes[0].ndef[1])

            nodes = await core.nodes('$s = woot [ test:str=$s.ljust(10) ]')
            self.eq('woot      ', nodes[0].ndef[1])

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
            # Base List object behavior
            q = '''// $lib.list ctor
            $list=$lib.list(1,2,3)
            // __len__
            $lib.print('List size is {len}', len=$lib.len($list))
            // aiter/iter method
            $sum = $(0)
            for $valu in $list {
                $sum = $( $sum + $valu)
            }
            $lib.print('Sum is {sum}', sum=$sum)
            // Append method
            $list.append(4)
            // size method
            $lib.print('List size is now {len}', len=$list.size())
            // Access the values by index
            $lib.print('List[0]={zero}, List[-1]={neg1}', zero=$list.index(0), neg1=$list.index(-1))
            $sum = $(0)
            for $valu in $list {
                $sum = $( $sum + $valu)
            }
            $lib.print('Sum is now {sum}', sum=$sum)
            // Empty lists may also be made
            $elst=$lib.list()
            $lib.print('elst size is {len}', len=$lib.len($elst))
            '''
            msgs = await core.streamstorm(q).list()
            self.stormIsInPrint('List size is 3', msgs)
            self.stormIsInPrint('Sum is 6', msgs)
            self.stormIsInPrint('List[0]=1, List[-1]=4', msgs)
            self.stormIsInPrint('List size is now 4', msgs)
            self.stormIsInPrint('Sum is now 10', msgs)
            self.stormIsInPrint('elst size is 0', msgs)

            # Convert primitive python objects to List objects
            q = '$v=(foo,bar,baz) [ test:str=$v.index(1) test:int=$v.length() ]'
            nodes = await core.nodes(q)
            self.eq(nodes[0].ndef, ('test:str', 'bar'))
            self.eq(nodes[1].ndef, ('test:int', 3))

            # Python Tuples can be treated like a List object for accessing via data inside of.
            q = '[ test:comp=(10,lol) ] $x=$node.ndef().index(1).index(1) [ test:str=$x ]'
            nodes = await core.nodes(q)
            self.eq(nodes[0].ndef, ('test:str', 'lol'))

            # sad case - index out of bounds.
            q = 'test:comp=(10,lol) $x=$node.ndef().index(2)'
            mesgs = await core.streamstorm(q).list()
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
            $latlong = $node.repr(latlong, defv="??")
            $valu = $lib.str.format("{ipv4} in {loc} at {latlong}", ipv4=$ipv4, loc=$loc, latlong=$latlong)
            [ test:str=$valu ]
            +test:str
        '''

        async with self.getTestCore() as core:
            nodes = await core.nodes(text)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], '1.2.3.4 in us at ??')

            mesgs = await alist(core.streamstorm('inet:ipv4 $repr=$node.repr(newp)'))

            err = mesgs[-2][1]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('mesg', err[1])
            self.eq(err[1].get('prop'), 'newp')
            self.eq(err[1].get('form'), 'inet:ipv4')

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

            q = 'test:str $lib.csv.emit(:tick, :hehe)'
            mesgs = await core.streamstorm(q, {'show': ('err', 'csv:row')}).list()
            csv_rows = [m for m in mesgs if m[0] == 'csv:row']
            self.len(2, csv_rows)
            self.eq(csv_rows[0],
                    ('csv:row', {'row': [978307200000, None], 'table': None}))
            self.eq(csv_rows[1],
                    ('csv:row', {'row': [32535216000000, None], 'table': None}))

            # Sad path case...
            q = '''$data=() $genr=$lib.feed.genr(syn.node, $data)
            $lib.csv.emit($genr)
            '''
            mesgs = await core.streamstorm(q, {'show': ('err', 'csv:row')}).list()
            err = mesgs[-2]
            self.eq(err[1][0], 'NoSuchType')

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

            q = '$set = $lib.set(a, b, c) [test:int=$set.size()]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 3))

            q = '''$set = $lib.set(a, b, c)
            for $v in $set {
                $lib.print('set valu: {v}', v=$v)
            }
            '''
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('set valu: a', mesgs)
            self.stormIsInPrint('set valu: b', mesgs)
            self.stormIsInPrint('set valu: c', mesgs)

            q = '''
                $set = $lib.set()
                $set.add(foo)
                if $set.has(foo) { [ test:str=asdf ] }
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'asdf'))

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

            opts = {'vars': {'testvar': 'test'}}
            text = "[ test:str='123' ] $testkey=testvar [ test:str=$path.vars.$testkey ]"
            nodes = await core.nodes(text, opts=opts)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test'))

            text = "[ test:str='123' ] [ test:str=$path.vars.testkey ]"
            mesgs = await alist(core.streamstorm(text))
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('No var with name: testkey', err[1].get('mesg'))

            opts = {'vars': {'testkey': 'testvar'}}
            text = "[ test:str='123' ] $path.vars.$testkey = test [ test:str=$testvar ]"
            nodes = await core.nodes(text, opts=opts)
            self.len(2, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test'))
            self.eq(nodes[1].ndef, ('test:str', '123'))

            opts = {'vars': {'testvar': 'test', 'testkey': 'testvar'}}
            text = '''
                [ test:str='123' ]
                for ($name, $valu) in $path.vars {
                    $lib.print('{name}={valu}', name=$name, valu=$valu)
                }
            '''
            msgs = await alist(core.streamstorm(text, opts=opts))

            self.stormIsInPrint('testvar=test', msgs)
            self.stormIsInPrint('testkey=testvar', msgs)

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

    async def test_storm_lib_time(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('[ ps:person="*" :dob = $lib.time.fromunix(20) ]')
            self.len(1, nodes)
            self.eq(20000, nodes[0].get('dob'))

            query = '''$valu="10/1/2017 2:52"
            $parsed=$lib.time.parse($valu, "%m/%d/%Y %H:%M")
            [test:int=$parsed]
            '''
            nodes = await core.nodes(query)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 1506826320000)

            # Sad case for parse
            query = '''$valu="10/1/2017 2:52"
            $parsed=$lib.time.parse($valu, "%m/%d/%Y--%H:%MTZ")
            [test:int=$parsed]
            '''
            mesgs = await alist(core.streamstorm(query))
            ernfos = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, ernfos)
            self.isin('Error during time parsing', ernfos[0][1].get('mesg'))

            query = '''[test:str=1234 :tick=20190917]
            $lib.print($lib.time.format(:tick, "%Y-%d-%m"))
            '''
            mesgs = await alist(core.streamstorm(query))
            self.stormIsInPrint('2019-17-09', mesgs)

            # Strs can be parsed using time norm routine.
            query = '''$valu=$lib.time.format('200103040516', '%Y %m %d')
            $lib.print($valu)
            '''
            mesgs = await alist(core.streamstorm(query))
            self.stormIsInPrint('2001 03 04', mesgs)

            # Out of bounds case for datetime
            query = '''[test:int=253402300800000]
            $valu=$lib.time.format($node.value(), '%Y')'''
            mesgs = await alist(core.streamstorm(query))
            ernfos = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, ernfos)
            self.isin('Failed to norm a time value prior to formatting', ernfos[0][1].get('mesg'))

            # Cant format ? times
            query = '$valu=$lib.time.format("?", "%Y")'
            mesgs = await alist(core.streamstorm(query))
            ernfos = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, ernfos)
            self.isin('Cannot format a timestamp for ongoing/future time.', ernfos[0][1].get('mesg'))

            # strftime fail - taken from
            # https://github.com/python/cpython/blob/3.7/Lib/test/datetimetester.py#L1404
            query = r'''[test:str=1234 :tick=20190917]
            $lib.print($lib.time.format(:tick, "%y\ud800%m"))
            '''
            mesgs = await alist(core.streamstorm(query))
            ernfos = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, ernfos)
            self.isin('Error during time format', ernfos[0][1].get('mesg'))

            # $lib.time.sleep causes cache flushes on the snap
            async with await core.snap() as snap:
                # lift a node into the cache
                data0 = await alist(snap.storm('test:str=1234'))
                self.len(1, snap.buidcache)
                # use $lib.time.sleep
                data1 = await alist(snap.storm('$lib.time.sleep(0) fini { test:str=1234 } '))
                self.ne(id(data0[0][0]), id(data1[0][0]))
                self.eq(data0[0][0].ndef, data1[0][0].ndef)

    async def test_storm_lib_time_ticker(self):

        async with self.getTestCore() as core:
            await core.nodes('''
                $lib.queue.add(visi)
                $lib.dmon.add(${
                    $visi=$lib.queue.get(visi)
                    for $tick in $lib.time.ticker(0.01) {
                        $visi.put($tick)
                    }
                })
            ''')
            nodes = await core.nodes('for ($offs, $tick) in $lib.queue.get(visi).gets(size=3) { [test:int=$tick] } ')
            self.len(3, nodes)
            self.eq({0, 1, 2}, {node.ndef[1] for node in nodes})

            # lib.time.ticker also clears the snap cache
            async with await core.snap() as snap:
                # lift a node into the cache
                _ = await alist(snap.storm('test:int=0'))
                self.len(1, snap.buidcache)
                q = '''
                $visi=$lib.queue.get(visi)
                for $tick in $lib.time.ticker(0.01, count=3) {
                    $visi.put($tick)
                }
                '''
                _ = await alist(snap.storm(q))
                self.len(0, snap.buidcache)

    async def test_storm_lib_telepath(self):

        class FakeService:

            async def doit(self, x):
                return x + 20

            async def fqdns(self):
                yield 'woot.com'
                yield 'vertex.link'

            async def ipv4s(self):
                return ('1.2.3.4', '5.6.7.8')

        async with self.getTestCore() as core:

            fake = FakeService()
            core.dmon.share('fake', fake)
            lurl = core.getLocalUrl(share='fake')

            await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 ]')

            opts = {'vars': {'url': lurl}}

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 ] $asn = $lib.telepath.open($url).doit(:asn) [ :asn=$asn ]', opts=opts)
            self.eq(40, nodes[0].props['asn'])

            nodes = await core.nodes('for $fqdn in $lib.telepath.open($url).fqdns() { [ inet:fqdn=$fqdn ] }', opts=opts)
            self.len(2, nodes)

            nodes = await core.nodes('for $ipv4 in $lib.telepath.open($url).ipv4s() { [ inet:ipv4=$ipv4 ] }', opts=opts)
            self.len(2, nodes)

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.telepath.open($url)._newp()', opts=opts)

    async def test_storm_lib_queue(self):

        async with self.getTestCore() as core:

            msgs = await core.streamstorm('queue.add visi').list()
            self.stormIsInPrint('queue added: visi', msgs)

            with self.raises(s_exc.DupName):
                await core.nodes('queue.add visi')

            msgs = await core.streamstorm('queue.list').list()
            self.stormIsInPrint('Storm queue list:', msgs)
            self.stormIsInPrint('visi', msgs)

            nodes = await core.nodes('$q = $lib.queue.get(visi) [ inet:ipv4=1.2.3.4 ] $q.put( $node.repr() )')
            nodes = await core.nodes('$q = $lib.queue.get(visi) ($offs, $ipv4) = $q.get(0) inet:ipv4=$ipv4')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # test iter use case
            nodes = await core.nodes('$q = $lib.queue.add(blah) [ inet:ipv4=1.2.3.4 inet:ipv4=5.5.5.5 ] $q.put( $node.repr() )')
            self.len(2, nodes)

            # Put a value into the queue that doesn't exist in the cortex so the lift can nop
            await core.nodes('$q = $lib.queue.get(blah) $q.put("8.8.8.8")')

            nodes = await core.nodes('''
                $q = $lib.queue.get(blah)
                for ($offs, $ipv4) in $q.gets(0, cull=0, wait=0) {
                    inet:ipv4=$ipv4
                }
            ''')
            self.len(2, nodes)

            nodes = await core.nodes('''
                $q = $lib.queue.get(blah)
                for ($offs, $ipv4) in $q.gets(wait=0) {
                    inet:ipv4=$ipv4
                    $q.cull($offs)
                }
            ''')
            self.len(2, nodes)

            nodes = await core.nodes('$q = $lib.queue.get(blah) for ($offs, $ipv4) in $q.gets(wait=0) { inet:ipv4=$ipv4 }')
            self.len(0, nodes)

            msgs = await core.streamstorm('queue.del visi').list()
            self.stormIsInPrint('queue removed: visi', msgs)

            with self.raises(s_exc.NoSuchName):
                await core.nodes('queue.del visi')

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.queue.get(newp).get()')

            await core.nodes('''
                $doit = $lib.queue.add(doit)
                $doit.puts((foo,bar))
            ''')
            nodes = await core.nodes('for ($offs, $name) in $lib.queue.get(doit).gets(size=2) { [test:str=$name] }')
            self.len(2, nodes)

            # test other users who have access to this queue can do things to it
            async with core.getLocalProxy() as root:
                # add users
                await root.addAuthUser('synapse')
                await root.addAuthUser('wootuser')

                synu = core.auth.getUserByName('synapse')
                woot = core.auth.getUserByName('wootuser')

                # make a queue
                with self.raises(s_exc.AuthDeny):
                    await core.nodes('queue.add synq', user=synu)

                rule = (True, ('storm', 'queue', 'add'))
                await root.addAuthRule('synapse', rule, indx=None)
                msgs = await alist(core.streamstorm('queue.add synq', user=synu))
                self.stormIsInPrint('queue added: synq', msgs)

                rule = (True, ('storm', 'queue', 'synq', 'put'))
                await root.addAuthRule('synapse', rule, indx=None)

                await core.nodes('$q = $lib.queue.get(synq) $q.puts((bar, baz))', user=synu)

                # now let's see our other user fail to add things
                with self.raises(s_exc.AuthDeny):
                    await core.nodes('$lib.queue.get(synq).get()', user=woot)

                rule = (True, ('storm', 'queue', 'synq', 'get'))
                await root.addAuthRule('wootuser', rule, indx=None)

                msgs = await alist(core.streamstorm('$lib.print($lib.queue.get(synq).get(wait=False))'))
                self.stormIsInPrint("(0, 'bar')", msgs)

                with self.raises(s_exc.AuthDeny):
                    await core.nodes('$lib.queue.del(synq)', user=woot)

                rule = (True, ('storm', 'queue', 'del', 'synq'))
                await root.addAuthRule('wootuser', rule, indx=None)
                await core.nodes('$lib.queue.del(synq)', user=woot)
                with self.raises(s_exc.NoSuchName):
                    await core.nodes('$lib.queue.get(synq)')

    async def test_storm_node_data(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[test:int=10] $node.data.set(foo, hehe)')

            self.len(1, nodes)
            self.eq(await nodes[0].getData('foo'), 'hehe')

            nodes = await core.nodes('test:int $foo=$node.data.get(foo) [ test:str=$foo ] +test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'hehe'))

            nodes = await core.nodes('test:int for ($name, $valu) in $node.data.list() { [ test:str=$name ] } +test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo'))

            # delete and remake the node to confirm data wipe
            nodes = await core.nodes('test:int=10 | delnode')
            nodes = await core.nodes('test:int=10')
            self.len(0, nodes)

            nodes = await core.nodes('[test:int=10]')

            self.none(await nodes[0].getData('foo'))

            nodes = await core.nodes('[ test:int=20 ] $node.data.set(woot, woot)')
            self.eq('woot', await nodes[0].getData('woot'))

            nodes = await core.nodes('test:int=20 [ test:str=$node.data.pop(woot) ]')

            self.none(await nodes[1].getData('woot'))
            self.eq(nodes[0].ndef, ('test:str', 'woot'))

    async def test_storm_lib_bytes(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadArg):
                opts = {'vars': {'bytes': 10}}
                text = '($size, $sha2) = $lib.bytes.put($bytes)'
                nodes = await core.nodes(text, opts=opts)

            opts = {'vars': {'bytes': b'asdfasdf'}}
            text = '($size, $sha2) = $lib.bytes.put($bytes) [ test:int=$size test:str=$sha2 ]'

            nodes = await core.nodes(text, opts=opts)
            self.len(2, nodes)

            self.eq(nodes[0].ndef, ('test:int', 8))
            self.eq(nodes[1].ndef, ('test:str', '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892'))

            bkey = s_common.uhex('2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892')
            byts = b''.join([b async for b in core.axon.get(bkey)])
            self.eq(b'asdfasdf', byts)

            # Allow bytes to be directly decoded as a string
            opts = {'vars': {'buf': 'hehe'.encode()}}
            nodes = await core.nodes('$valu=$buf.decode() [test:str=$valu]', opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'hehe'))

            # Allow strings to be encoded as bytes
            text = '''$valu="visi"  $buf1=$valu.encode() $buf2=$valu.encode("utf-16")
            [(file:bytes=$buf1) (file:bytes=$buf2)]
            '''
            nodes = await core.nodes(text)
            self.len(2, nodes)
            self.eq({'sha256:e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f',
                     'sha256:1263d0f4125831df93a82a08ab955d1176306953c9f0c44d366969295c7b57db',
                     },
                    {n.ndef[1] for n in nodes})

            # Encoding/decoding errors are caught
            q = '$valu="valu" $valu.encode("utf16").decode()'
            msgs = await core.streamstorm(q).list()
            errs = [m for m in msgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][1][0], 'StormRuntimeError')

            q = '$valu="str.ॐ.valu" $buf=$valu.encode(ascii)'
            msgs = await core.streamstorm(q).list()
            errs = [m for m in msgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][1][0], 'StormRuntimeError')

    async def test_storm_lib_base64(self):

        async with self.getTestCore() as core:

            await core.axready.wait()

            # urlsafe
            opts = {'vars': {'bytes': b'fooba?'}}
            text = '$valu = $lib.base64.encode($bytes) [ test:str=$valu ]'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'Zm9vYmE_'))

            opts = {'vars': {'bytes': nodes[0].ndef[1]}}
            text = '$lib.bytes.put($lib.base64.decode($bytes))'
            nodes = await core.nodes(text, opts)
            key = binascii.unhexlify(hashlib.sha256(base64.urlsafe_b64decode(opts['vars']['bytes'])).hexdigest())
            byts = b''.join([b async for b in core.axon.get(key)])
            self.eq(byts, b'fooba?')

            # normal
            opts = {'vars': {'bytes': b'fooba?'}}
            text = '$valu = $lib.base64.encode($bytes, $(0)) [ test:str=$valu ]'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'Zm9vYmE/'))

            opts = {'vars': {'bytes': nodes[0].ndef[1]}}
            text = '$lib.bytes.put($lib.base64.decode($bytes, $(0)))'
            nodes = await core.nodes(text, opts)
            key = binascii.unhexlify(hashlib.sha256(base64.urlsafe_b64decode(opts['vars']['bytes'])).hexdigest())
            byts = b''.join([b async for b in core.axon.get(key)])
            self.eq(byts, b'fooba?')

            # unhappy cases
            opts = {'vars': {'bytes': 'not bytes'}}
            text = '[ test:str=$lib.base64.encode($bytes) ]'
            mesgs = await alist(core.streamstorm(text, opts=opts))
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('Error during base64 encoding - a bytes-like object is required', err[1].get('mesg'))

            opts = {'vars': {'bytes': 'foobar'}}
            text = '[test:str=$lib.base64.decode($bytes)]'
            mesgs = await alist(core.streamstorm(text, opts=opts))
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('Error during base64 decoding - Incorrect padding', err[1].get('mesg'))

    async def test_storm_lib_vars(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'testvar': 'test'}}
            text = '$testkey=testvar [ test:str=$lib.vars.get($testkey) ]'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test'))

            text = '$testkey=testvar [ test:str=$lib.vars.get($testkey) ]'
            mesgs = await alist(core.streamstorm(text))
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'BadPropValu')
            self.isin('Error adding node', err[1].get('mesg'))

            opts = {'vars': {'testkey': 'testvar'}}
            text = '$lib.vars.set($testkey, test) [ test:str=$lib.vars.get(testvar) ]'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test'))

            opts = {'vars': {'testvar': 'test', 'testkey': 'testvar'}}
            text = '$lib.vars.del(testvar) [ test:str=$lib.vars.get($testkey) ]'
            mesgs = await alist(core.streamstorm(text, opts=opts))
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'BadPropValu')
            self.isin('Error adding node', err[1].get('mesg'))

            opts = {'vars': {'testvar': 'test', 'testkey': 'testvar'}}
            text = '$lib.vars.del(testvar) [ test:str=$lib.vars.get($testkey) ]'
            mesgs = await alist(core.streamstorm(text, opts=opts))
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'BadPropValu')
            self.isin('Error adding node', err[1].get('mesg'))

            opts = {'vars': {'testvar': 'test', 'testkey': 'testvar'}}
            text = '$lib.print($lib.vars.list())'
            mesgs = await alist(core.streamstorm(text, opts=opts))
            mesgs = [m for m in mesgs if m[0] == 'print']
            self.len(1, mesgs)
            self.stormIsInPrint("('testvar', 'test'), ('testkey', 'testvar')", mesgs)

    async def test_feed(self):

        async with self.getTestCore() as core:
            data = [
                (('test:str', 'hello'), {'props': {'tick': '2001'},
                                         'tags': {'test': (None, None)}}),
                (('test:str', 'stars'), {'props': {'tick': '3001'},
                                         'tags': {}}),
            ]
            svars = {'data': data}
            opts = {'vars': svars}
            q = '$lib.feed.ingest("syn.nodes", $data)'
            nodes = await core.nodes(q, opts)
            self.eq(nodes, [])
            self.len(2, await core.nodes('test:str'))
            self.len(1, await core.nodes('test:str#test'))
            self.len(1, await core.nodes('test:str:tick=3001'))

            # Try seqn combo
            guid = s_common.guid()
            svars['guid'] = guid
            svars['offs'] = 0
            q = '''$seqn=$lib.feed.ingest("syn.nodes", $data, ($guid, $offs))
            $lib.print("New offset: {seqn}", seqn=$seqn)
            '''
            mesgs = await alist(core.streamstorm(q, opts))
            self.stormIsInPrint('New offset: 2', mesgs)
            self.eq(2, await core.getFeedOffs(guid))

            q = 'feed.list'
            mesgs = await alist(core.streamstorm(q))
            self.stormIsInPrint('Storm feed list', mesgs)
            self.stormIsInPrint('com.test.record', mesgs)
            self.stormIsInPrint('No feed docstring', mesgs)
            self.stormIsInPrint('syn.nodes', mesgs)
            self.stormIsInPrint('Add nodes to the Cortex via the packed node format', mesgs)

            data = [
                (('test:str', 'sup!'), {'props': {'tick': '2001'},
                                         'tags': {'test': (None, None)}}),
                (('test:str', 'dawg'), {'props': {'tick': '3001'},
                                         'tags': {}}),
            ]
            svars['data'] = data
            q = '$genr=$lib.feed.genr("syn.nodes", $data) $lib.print($genr) yield $genr'
            nodes = await core.nodes(q, opts=opts)
            self.len(2, nodes)
            self.eq({'sup!', 'dawg'},
                    {n.ndef[1] for n in nodes})

            # Ingest bad data
            data = [
                (('test:int', 'newp'), {}),
            ]
            svars['data'] = data
            q = '$lib.feed.ingest("syn.nodes", $data)'
            msgs = await core.streamstorm(q, opts).list()
            self.stormIsInWarn("BadPropValu: Error adding node: test:int 'newp'", msgs)
            errs = [m for m in msgs if m[0] == 'err']
            self.len(0, errs)

    async def test_lib_stormtypes_stats(self):

        async with self.getTestCore() as core:

            q = '''
                $tally = $lib.stats.tally()

                $tally.inc(foo)
                $tally.inc(foo)

                $tally.inc(bar)
                $tally.inc(bar, 3)

                for ($name, $valu) in $tally {
                    [ test:comp=($valu, $name) ]
                }

                $lib.print('tally: foo={foo} baz={baz}', foo=$tally.get(foo), baz=$tally.get(baz))
            '''
            mesgs = await core.streamstorm(q).list()
            nodes = [m[1] for m in mesgs if m[0] == 'node']
            self.len(2, nodes)
            self.eq(nodes[0][0], ('test:comp', (2, 'foo')))
            self.eq(nodes[1][0], ('test:comp', (4, 'bar')))
            self.stormIsInPrint('tally: foo=2 baz=0', mesgs)

    async def test_storm_lib_view(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            await core.addTagProp('risk', ('int', {'minval': 0, 'maxval': 100}), {'doc': 'risk score'})
            await core.nodes('[test:int=12 +#tag.test +#tag.proptest:risk=20]')

            # Get the main view
            q = '$lib.print($lib.view.get().pack().iden)'
            mesgs = await core.streamstorm(q).list()
            for mesg in mesgs:
                if mesg[0] == 'print':
                    mainiden = mesg[1]['mesg']

            self.isin(mainiden, core.views)

            q = f'$lib.print($lib.view.get({mainiden}).pack().iden)'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint(mainiden, mesgs)

            # Fork the main view
            q = f'''
                $forkview=$lib.view.fork({mainiden})
                $forkvalu=$forkview.pack()
                $lib.print("{{iden}},{{layr}}", iden=$forkvalu.iden, layr=$forkvalu.layers.index(0).iden)
            '''
            mesgs = await core.streamstorm(q).list()
            for mesg in mesgs:
                if mesg[0] == 'print':
                    forkiden, forklayr = mesg[1]['mesg'].split(',')

            self.isin(forkiden, core.views)
            self.isin(forklayr, core.layers)

            # Add a view
            newlayer = await core.addLayer()

            q = f'''
                $newview=$lib.view.add(({newlayer.iden},))
                $lib.print($newview.pack().iden)
            '''
            mesgs = await core.streamstorm(q).list()
            for mesg in mesgs:
                if mesg[0] == 'print':
                    newiden = mesg[1]['mesg']

            self.isin(newiden, core.views)

            # List the views in the cortex
            q = '''
                for $view in $lib.view.list() {
                    $lib.print($view.pack().iden)
                }
            '''
            idens = []
            mesgs = await core.streamstorm(q).list()
            for mesg in mesgs:
                if mesg[0] == 'print':
                    idens.append(mesg[1]['mesg'])

            self.sorteq(idens, core.views.keys())

            # Delete the added view
            q = f'$lib.view.del({newiden})'
            await core.nodes(q)

            self.notin(newiden, core.views)

            # Fork the forked view
            q = f'''
                $forkview=$lib.view.fork({forkiden})
                $lib.print($forkview.pack().iden)
            '''
            mesgs = await core.streamstorm(q).list()
            for mesg in mesgs:
                if mesg[0] == 'print':
                    childiden = mesg[1]['mesg']

            # Can't merge the first forked view if it has children
            q = f'$lib.view.merge({forkiden})'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            # Can't merge the child forked view if the parent is read only
            core.views[childiden].parent.layers[0].readonly = True
            q = f'$lib.view.merge({childiden})'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            core.views[childiden].parent.layers[0].readonly = False
            await core.nodes(q)

            # Merge the forked view
            q = f'$lib.view.merge({forkiden})'
            await core.nodes(q)

            self.notin(forkiden, core.views)
            self.notin(forklayr, core.layers)

            # Sad paths
            await self.asyncraises(s_exc.NoSuchIden, core.nodes('$lib.view.del(foo)'))
            await self.asyncraises(s_exc.NoSuchIden, core.nodes('$lib.view.fork(foo)'))
            await self.asyncraises(s_exc.NoSuchIden, core.nodes('$lib.view.get(foo)'))
            await self.asyncraises(s_exc.NoSuchIden, core.nodes('$lib.view.merge(foo)'))
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(f'$lib.view.merge({mainiden})'))

            q = f'$lib.view.del({mainiden})'
            mesgs = await core.streamstorm(q).list()
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][0], 'StormRuntimeError')
            self.eq(errs[0][1]['mesg'], 'Deleting the main view is not permitted.')

            # Check helper commands
            # Get the main view
            q = 'view.get'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint(mainiden, mesgs)

            q = f'view.get {mainiden}'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint(mainiden, mesgs)

            # Fork the main view
            q = f'view.fork {mainiden}'
            mesgs = await core.streamstorm(q).list()
            for mesg in mesgs:
                if mesg[0] == 'print':
                    helperfork = mesg[1]['mesg'].split(' ')[-1]

            self.isin(helperfork, core.views)

            # Add a view
            newlayer2 = await core.addLayer()

            q = f'view.add --layers {newlayer.iden} {newlayer2.iden}'
            mesgs = await core.streamstorm(q).list()
            for mesg in mesgs:
                if mesg[0] == 'print':
                    helperadd = mesg[1]['mesg'].split(' ')[-1]

            self.isin(helperadd, core.views)

            # List the views in the cortex
            q = 'view.list'
            mesgs = await core.streamstorm(q).list()

            for viden, v in core.views.items():
                self.stormIsInPrint(viden, mesgs)
                for layer in v.layers:
                    self.stormIsInPrint(layer.iden, mesgs)

            # Delete the added view
            q = f'view.del {helperadd}'
            nodes = await core.nodes(q)

            self.notin(helperadd, core.views)

            # Merge the forked view
            q = f'view.merge {helperfork}'
            nodes = await core.nodes(q)

            self.notin(helperfork, core.views)

            # Test permissions

            await prox.addAuthUser('visi')
            await prox.setUserPasswd('visi', 'secret')

            async with core.getLocalProxy(user='visi') as asvisi:

                # List and Get require 'read' permission
                await self.agenraises(s_exc.AuthDeny, asvisi.eval('$lib.view.list()'))
                await self.agenraises(s_exc.AuthDeny, asvisi.eval('$lib.view.get()'))

                await prox.addAuthRule('visi', (True, ('view', 'read')))

                await asvisi.eval('$lib.view.list()').list()
                await asvisi.eval('$lib.view.get()').list()

                # Add and Fork require 'add' permission
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(f'$lib.view.add(({newlayer.iden},))'))
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(f'$lib.view.fork({mainiden})'))

                await prox.addAuthRule('visi', (True, ('view', 'add')))

                q = f'''
                    $newview=$lib.view.add(({newlayer.iden},))
                    $lib.print($newview.pack().iden)
                '''
                mesgs = await asvisi.storm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        addiden = mesg[1]['mesg']

                self.isin(addiden, core.views)

                q = f'''
                    $forkview=$lib.view.fork({mainiden})
                    $lib.print($forkview.pack().iden)
                '''
                mesgs = await asvisi.storm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        forkediden = mesg[1]['mesg']

                self.isin(forkediden, core.views)

                # Del and Merge require 'del' permission unless performed by the owner
                # Delete a view the user owns

                q = f'$lib.view.del({addiden})'
                nodes = await asvisi.storm(q).list()

                self.notin(addiden, core.views)

                forkview = core.getView(forkediden)
                await alist(forkview.eval('[test:int=34 +#tag.test +#tag.proptest:risk=40]'))
                await alist(forkview.eval('test:int=12 [-#tag.proptest:risk]'))
                await alist(forkview.eval('test:int=12 | delnode'))

                # Merge the view forked by the user
                # Will need perms for all the ops required to merge

                q = f'$lib.view.merge({forkediden})'
                mesgs = await asvisi.storm(q).list()
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(q))

                await prox.addAuthRule('visi', (True, ('node:add',)))
                await prox.addAuthRule('visi', (True, ('node:del',)))
                await prox.addAuthRule('visi', (True, ('prop:set',)))
                await prox.addAuthRule('visi', (True, ('prop:del',)))
                await prox.addAuthRule('visi', (True, ('tag:add',)))
                await prox.addAuthRule('visi', (True, ('tag:del',)))

                q = f'$lib.view.merge({forkediden})'
                nodes = await asvisi.storm(q).list()

                self.notin(forkediden, core.views)

                # Make some views not owned by the user
                q = f'view.add --layers {newlayer.iden}'
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        rootadd = mesg[1]['mesg'].split(' ')[-1]
                self.isin(rootadd, core.views)

                q = f'view.fork {mainiden}'
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        rootfork = mesg[1]['mesg'].split(' ')[-1]
                self.isin(rootfork, core.views)

                await self.agenraises(s_exc.AuthDeny, asvisi.eval(f'$lib.view.del({rootadd})'))
                await self.agenraises(s_exc.AuthDeny, asvisi.eval(f'$lib.view.merge({rootfork})'))

                await prox.addAuthRule('visi', (True, ('view', 'del')))

                # Delete a view not owned by the user
                q = f'$lib.view.del({rootadd})'
                nodes = await asvisi.storm(q).list()

                self.notin(rootadd, core.views)

                # Merge a view not owned by the user
                q = f'view.merge {rootfork}'
                nodes = await core.nodes(q)

                self.notin(rootfork, core.views)

    async def test_storm_lib_trigger(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            await self.agenlen(0, core.eval('syn:trigger'))

            q = 'trigger.list'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('No triggers found', mesgs)

            q = 'trigger.add node:add --form test:str --query {[ test:int=1 ]}'
            mesgs = await core.streamstorm(q).list()

            await core.storm('[ test:str=foo ]').list()
            await self.agenlen(1, core.eval('test:int'))

            q = 'trigger.add tag:add --form test:str --tag #footag.* --query {[ +#count test:str=$tag ]}'
            mesgs = await core.streamstorm(q).list()

            await core.storm('[ test:str=bar +#footag.bar ]').list()
            await core.storm('[ test:str=bar +#footag.bar ]').list()
            await self.agenlen(1, core.eval('#count'))
            await self.agenlen(1, core.eval('test:str=footag.bar'))

            q = 'trigger.add prop:set --disabled --prop test:type10:intprop --query {[ test:int=6 ]}'
            mesgs = await core.streamstorm(q).list()

            q = 'trigger.list'
            mesgs = await core.streamstorm(q).list()
            self.stormIsInPrint('user', mesgs)
            self.stormIsInPrint('root', mesgs)

            nodes = await core.nodes('syn:trigger')
            self.len(3, nodes)

            for node in nodes:
                self.eq(node.props.get('user'), 'root')

            goodbuid = nodes[1].ndef[1][:6]
            goodbuid2 = nodes[2].ndef[1][:6]

            # Trigger is created disabled, so no nodes yet
            await self.agenlen(0, core.eval('test:int=6'))
            waiter = core.waiter(1, 'core:trigger:action')

            await core.storm(f'trigger.enable {goodbuid2}').list()
            evnts = await waiter.wait(1)

            self.eq(evnts[0][1].get('action'), 'enable')

            # Trigger is enabled, so it should fire
            await core.storm('[ test:type10=1 :intprop=25 ]').list()
            await self.agenlen(1, core.eval('test:int=6'))

            mesgs = await core.streamstorm(f'trigger.del {goodbuid}').list()
            self.stormIsInPrint('Deleted trigger', mesgs)

            q = f'trigger.del deadbeef12341234'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            q = f'trigger.enable deadbeef12341234'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            q = f'trigger.disable deadbeef12341234'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            waiter = core.waiter(1, 'core:trigger:action')
            mesgs = await core.streamstorm(f'trigger.disable {goodbuid2}').list()
            self.stormIsInPrint('Disabled trigger', mesgs)

            evnts = await waiter.wait(1)
            self.eq(evnts[0][1].get('action'), 'disable')

            mesgs = await core.streamstorm(f'trigger.enable {goodbuid2}').list()
            self.stormIsInPrint('Enabled trigger', mesgs)

            mesgs = await core.streamstorm(f'trigger.mod {goodbuid2} {{[ test:str=different ]}}').list()
            self.stormIsInPrint('Modified trigger', mesgs)

            q = 'trigger.mod deadbeef12341234 {#foo}'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            await core.storm('trigger.add tag:add --tag #another --query {[ +#count2 ]}').list()

            # Syntax mistakes
            mesgs = await core.streamstorm('trigger.mod "" {#foo}').list()
            self.stormIsInErr('matches more than one', mesgs)

            mesgs = await core.streamstorm('trigger.add tag:add --prop another --query {[ +#count2 ]}').list()
            self.stormIsInErr('Missing tag parameter', mesgs)

            mesgs = await core.streamstorm('trigger.add tug:udd --prop another --query {[ +#count2 ]}').list()
            self.stormIsInErr('Invalid trigger condition', mesgs)

            mesgs = await core.streamstorm('trigger.add tag:add --form inet:ipv4').list()
            self.stormIsInErr('Missing query parameter', mesgs)

            mesgs = await core.streamstorm('trigger.add node:add --form test:str --tag #foo --query {test:str}').list()
            self.stormIsInErr('node:* does not support', mesgs)

            mesgs = await core.streamstorm('trigger.add prop:set --tag #foo --query {test:str}').list()
            self.stormIsInErr('Missing prop parameter', mesgs)

            mesgs = await core.streamstorm('trigger.add prop:set --prop test:type10.intprop --tag #foo --query {test:str}').list()
            self.stormIsInErr('prop:set does not support a tag', mesgs)

            mesgs = await core.streamstorm('trigger.add tag:add --tag #tag --form test:int').list()
            self.stormIsInErr('Missing query', mesgs)

            mesgs = await core.streamstorm('trigger.add node:add --tag #tag1 --query {test:str}').list()
            self.stormIsInErr('Missing form', mesgs)

            mesgs = await core.streamstorm(f'trigger.mod {goodbuid2} test:str').list()
            self.stormIsInErr('start with {', mesgs)

            # Bad storm syntax
            mesgs = await core.streamstorm('trigger.add node:add --form test:str --query {[ | | test:int=1 ] }').list()
            self.stormIsInErr('No terminal defined', mesgs)

            # (Regression) Just a command as the storm query
            mesgs = await core.streamstorm('trigger.add node:add --form test:str --query {[ test:int=99 ] | spin }').list()
            await core.storm('[ test:str=foo4 ]').list()
            await self.agenlen(1, core.eval('test:int=99'))

            # Test manipulating triggers as another user
            await core.auth.addUser('bond')

            async with core.getLocalProxy(user='bond') as asbond:

                q = 'trigger.list'
                mesgs = await asbond.storm(q).list()
                self.stormIsInPrint('No triggers found', mesgs)

                q = f'trigger.mod {goodbuid2} {{[ test:str=yep ]}}'

                q = f'trigger.disable {goodbuid2}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('iden does not match any', mesgs)

                q = f'trigger.enable {goodbuid2}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('iden does not match any', mesgs)

                q = f'trigger.del {goodbuid2}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('iden does not match any', mesgs)

                # Give explicit perm
                await prox.addAuthRule('bond', (True, ('trigger', 'get')))

                mesgs = await asbond.storm('trigger.list').list()
                self.stormIsInPrint('user', mesgs)
                self.stormIsInPrint('root', mesgs)

                await prox.addAuthRule('bond', (True, ('trigger', 'set')))

                mesgs = await asbond.storm(f'trigger.mod {goodbuid2} {{[ test:str=yep ]}}').list()
                self.stormIsInPrint('Modified trigger', mesgs)

                mesgs = await asbond.storm(f'trigger.disable {goodbuid2}').list()
                self.stormIsInPrint('Disabled trigger', mesgs)

                mesgs = await asbond.storm(f'trigger.enable {goodbuid2}').list()
                self.stormIsInPrint('Enabled trigger', mesgs)

                await prox.addAuthRule('bond', (True, ('trigger', 'del')))

                mesgs = await asbond.storm(f'trigger.del {goodbuid2}').list()
                self.stormIsInPrint('Deleted trigger', mesgs)

    async def test_storm_lib_cron(self):

        MONO_DELT = 1543827303.0
        unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=0, tzinfo=tz.utc).timestamp()
        sync = asyncio.Event()
        lastquery = None
        s_provenance.reset()

        def timetime():
            return unixtime

        def looptime():
            return unixtime - MONO_DELT

        async def myeval(query, user=None):
            nonlocal lastquery
            lastquery = query
            sync.set()
            return
            yield None

        loop = asyncio.get_running_loop()

        with mock.patch.object(loop, 'time', looptime), mock.patch('time.time', timetime):

            async with self.getTestCoreAndProxy() as (core, prox):

                mesgs = await core.streamstorm('cron.list').list()
                self.stormIsInPrint('No cron jobs found', mesgs)

                q = '$lib.cron.add()'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Query parameter is required', mesgs)

                q = 'cron.add #foo'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('must start with {', mesgs)

                q = "cron.add --month nosuchmonth --day=-2 {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse fixed parameter "nosuchmonth"', mesgs)

                q = "cron.add --month 8nosuchmonth --day=-2 {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse fixed parameter "8nosuchmonth"', mesgs)

                q = "cron.add --day=, {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = "cron.add --day Mon --month +3 {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('provide a recurrence value with day of week', mesgs)

                q = "cron.add --day Mon --month June {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('fix month or year with day of week', mesgs)

                q = "cron.add --day Mon --month +3 --year +2 {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('more than 1 recurrence', mesgs)

                q = "cron.add --year=2019 {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Year may not be a fixed value', mesgs)

                q = "cron.add {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Must provide at least one optional', mesgs)

                q = "cron.add --hour 3 --minute +4 {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Fixed unit may not be larger', mesgs)

                q = 'cron.add --day Tuesday,1 {#foo}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = 'cron.add --day 1,Tuesday {#foo}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = 'cron.add --day Fri,3 {#foo}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = "cron.add --minute +4x {#foo}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse parameter', mesgs)

                q = 'cron.add }'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('No terminal defined', mesgs)

                ##################
                oldsplices = len(await alist(prox.splices(0, 1000)))

                # Start simple: add a cron job that creates a node every minute
                q = "cron.add --minute +1 {[graph:node='*' :type=m1]}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint('Created cron job', mesgs)
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                unixtime += 60
                mesgs = await core.streamstorm('cron.list').list()
                self.stormIsInPrint(':type=m1', mesgs)

                # Make sure it ran
                await self.agenlen(1, prox.eval('graph:node:type=m1'))

                # Make sure the provenance of the new splices looks right
                splices = await alist(prox.splices(oldsplices, 1000))
                self.gt(len(splices), 1)

                aliases = [splice[1]['prov'] for splice in splices]
                self.true(all(a == aliases[0] for a in aliases))
                prov = await prox.getProvStack(aliases[0])
                rootiden = prov[1][1][1]['user']
                correct = ({}, (
                           ('cron', {'iden': guid}),
                           ('storm', {'q': "[graph:node='*' :type=m1]", 'user': rootiden})))
                self.eq(prov, correct)

                q = f"cron.mod {guid[:6]} {{[graph:node='*' :type=m2]}}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint('Modified cron job', mesgs)

                q = f"cron.mod xxx {{[graph:node='*' :type=m2]}}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('does not match', mesgs)

                q = f"cron.mod xxx yyy"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Expected second argument to start with {', mesgs)

                # Make sure the old one didn't run and the new query ran
                unixtime += 60
                await self.agenlen(1, prox.eval('graph:node:type=m1'))
                await self.agenlen(1, prox.eval('graph:node:type=m2'))

                # Delete the job
                q = f"cron.del {guid}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint('Deleted cron job', mesgs)

                q = f"cron.del xxx"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('does not match', mesgs)

                q = f"cron.del xxx"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('does not match', mesgs)

                # Make sure deleted job didn't run
                unixtime += 60
                await self.agenlen(1, prox.eval('graph:node:type=m1'))
                await self.agenlen(1, prox.eval('graph:node:type=m2'))

                # Test fixed minute, i.e. every hour at 17 past
                unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=10,
                                             tzinfo=tz.utc).timestamp()
                q = "cron.add --minute 17 {[graph:node='*' :type=m3]}"
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                unixtime += 7 * MINSECS

                # Make sure it runs.  We add the cron.list to give the cron scheduler a chance to run
                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=m3'))
                await core.nodes(f"cron.del {guid}")

                ##################

                # Test day increment
                q = "cron.add --day +2 {[graph:node='*' :type=d1]}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint('Created cron job', mesgs)
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid1 = mesg[1]['mesg'].split(' ')[-1]

                unixtime += DAYSECS

                # Make sure it *didn't* run
                await self.agenlen(0, prox.eval('graph:node:type=d1'))

                unixtime += DAYSECS

                # Make sure it runs.  We add the cron.list to give the cron scheduler a chance to run
                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=d1'))

                unixtime += DAYSECS * 2
                await prox.eval('cron.list').list()
                await self.agenlen(2, prox.eval('graph:node:type=d1'))

                ##################

                # Test fixed day of week: every Monday and Thursday at 3am
                unixtime = datetime.datetime(year=2018, month=12, day=11, hour=7, minute=10,
                                             tzinfo=tz.utc).timestamp()  # A Tuesday

                q = "cron.add --hour 3 --day Mon,Thursday {[graph:node='*' :type=d2]}"
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid2 = mesg[1]['mesg'].split(' ')[-1]

                unixtime = datetime.datetime(year=2018, month=12, day=13, hour=3, minute=10,
                                             tzinfo=tz.utc).timestamp()  # Now Thursday
                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=d2'))

                q = f'cron.del ""'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('matches more than one', mesgs)

                await core.nodes(f"cron.del {guid1}")
                await core.nodes(f"cron.del {guid2}")

                q = "cron.add --hour 3 --day Noday {[graph:node='*' :type=d2]}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse day value "Noday"', mesgs)

                ##################

                # Test fixed day of month: second-to-last day of month
                q = "cron.add --day -2 --month Dec {[graph:node='*' :type=d3]}"
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                unixtime = datetime.datetime(year=2018, month=12, day=29, hour=0, minute=0,
                                             tzinfo=tz.utc).timestamp()  # Now Thursday
                await prox.eval('cron.list').list()
                await self.agenlen(0, prox.eval('graph:node:type=d3'))  # Not yet

                unixtime += DAYSECS
                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=d3'))

                await core.nodes(f"cron.del {guid}")

                ##################

                # Test month increment

                q = "cron.add --month +2 --day=4 {[graph:node='*' :type=month1]}"
                mesgs = await core.streamstorm(q).list()
                unixtime = datetime.datetime(year=2019, month=2, day=4, hour=0, minute=0,
                                             tzinfo=tz.utc).timestamp()  # Now Thursday

                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=month1'))

                ##################

                # Test year increment

                q = "cron.add --year +2 {[graph:node='*' :type=year1]}"
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid2 = mesg[1]['mesg'].split(' ')[-1]

                unixtime = datetime.datetime(year=2021, month=1, day=1, hour=0, minute=0,
                                             tzinfo=tz.utc).timestamp()  # Now Thursday

                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=year1'))

                # Make sure second-to-last day works for February
                q = "cron.add --month February --day=-2 {[graph:node='*' :type=year2]}"
                mesgs = await core.streamstorm(q).list()
                unixtime = datetime.datetime(year=2021, month=2, day=27, hour=0, minute=0,
                                             tzinfo=tz.utc).timestamp()  # Now Thursday

                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=year2'))

                ##################

                # Test 'at' command

                q = 'cron.at #foo'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('must start with {', mesgs)

                q = 'cron.at {#foo}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('At least', mesgs)

                q = 'cron.at --minute +1p3arsec {#foo}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Trouble parsing', mesgs)

                q = 'cron.at --day +1'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint('the following arguments are required: query', mesgs)

                q = 'cron.at --dt nope {#foo}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Trouble parsing', mesgs)

                q = '$lib.cron.at(day="+1")'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Query parameter is required', mesgs)

                q = "cron.at --minute +5 {[graph:node='*' :type=at1]}"
                mesgs = await core.streamstorm(q).list()
                unixtime += 5 * MINSECS

                await prox.eval('cron.list').list()
                await self.agenlen(1, core.eval('graph:node:type=at1'))

                q = "cron.at --day +1,+7 {[graph:node='*' :type=at2]}"
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                unixtime += DAYSECS
                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=at2'))

                unixtime += 6 * DAYSECS + 1
                await prox.eval('cron.list').list()
                await self.agenlen(2, prox.eval('graph:node:type=at2'))

                q = "cron.at --dt 202104170415 {[graph:node='*' :type=at3]}"
                mesgs = await core.streamstorm(q).list()

                unixtime = datetime.datetime(year=2021, month=4, day=17, hour=4, minute=15,
                                             tzinfo=tz.utc).timestamp()  # Now Thursday

                await prox.eval('cron.list').list()
                await self.agenlen(1, prox.eval('graph:node:type=at3'))

                ##################

                # Test 'stat' command
                mesgs = await core.streamstorm('cron.stat xxx').list()
                self.stormIsInErr('Provided iden does not match any', mesgs)

                mesgs = await core.streamstorm(f'cron.stat ""').list()
                self.stormIsInErr('matches more than one', mesgs)

                mesgs = await core.streamstorm(f'cron.stat {guid[:6]}').list()
                self.stormIsInPrint('last result:     finished successfully with 1 nodes', mesgs)
                self.stormIsInPrint('entries:         <None>', mesgs)

                mesgs = await core.streamstorm(f'cron.stat {guid2[:6]}').list()
                self.stormIsInPrint("{'month': 1, 'hour': 0, 'minute': 0, 'dayofmonth': 1}", mesgs)

                ##################

                # Test 'enable' 'disable' commands
                q = f'cron.enable xxx'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Provided iden does not match any', mesgs)

                q = f'cron.disable xxx'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Provided iden does not match any', mesgs)

                q = f'cron.disable {guid[:6]}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint(f'Disabled cron job: {guid}', mesgs)

                mesgs = await core.streamstorm(f'cron.stat {guid[:6]}').list()
                self.stormIsInPrint('enabled:         N', mesgs)

                q = f'cron.enable {guid[:6]}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint(f'Enabled cron job: {guid}', mesgs)

                mesgs = await core.streamstorm(f'cron.stat {guid[:6]}').list()
                self.stormIsInPrint('enabled:         Y', mesgs)

                ###################

                # Delete an expired at job
                q = f"cron.del {guid}"
                mesgs = await core.streamstorm(q).list()
                self.stormIsInPrint(f'Deleted cron job: {guid}', mesgs)

                ##################

                # Test the aliases
                q = 'cron.add --hourly 15 {#bar}'
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                mesgs = await core.streamstorm(f'cron.stat {guid[:6]}').list()
                self.stormIsInPrint("{'minute': 15}", mesgs)

                q = 'cron.add --daily 05:47 {#bar}'
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                mesgs = await core.streamstorm(f'cron.stat {guid[:6]}').list()
                self.stormIsInPrint("{'hour': 5, 'minute': 47", mesgs)

                q = 'cron.add --monthly=-1:12:30 {#bar}'
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                mesgs = await core.streamstorm(f'cron.stat {guid[:6]}').list()
                self.stormIsInPrint("{'hour': 12, 'minute': 30, 'dayofmonth': -1}", mesgs)

                q = 'cron.add --yearly 04:17:12:30 {#bar}'
                mesgs = await core.streamstorm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                mesgs = await core.streamstorm(f'cron.stat {guid[:6]}').list()
                self.stormIsInPrint("{'month': 4, 'hour': 12, 'minute': 30, 'dayofmonth': 17}", mesgs)

                q = 'cron.add --yearly 04:17:12 {#bar}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse parameter', mesgs)

                q = 'cron.add --daily xx:xx {#bar}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('Failed to parse ..ly parameter', mesgs)

                q = 'cron.add --hourly 1 --minute 17 {#bar}'
                mesgs = await core.streamstorm(q).list()
                self.stormIsInErr('May not use both', mesgs)

                # Test manipulating cron jobs as another user
                await core.auth.addUser('bond')

                async with core.getLocalProxy(user='bond') as asbond:

                    mesgs = await asbond.storm('cron.list').list()
                    self.stormIsInPrint('No cron jobs found', mesgs)

                    mesgs = await asbond.storm(f'cron.disable {guid[:6]}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    mesgs = await asbond.storm(f'cron.enable {guid[:6]}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    mesgs = await asbond.storm(f'cron.mod {guid[:6]} {{#foo}}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    mesgs = await asbond.storm(f'cron.del {guid[:6]}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    # Give explicit perm

                    await prox.addAuthRule('bond', (True, ('cron', 'get')))

                    mesgs = await asbond.storm('cron.list').list()
                    self.stormIsInPrint('user', mesgs)
                    self.stormIsInPrint('root', mesgs)

                    await prox.addAuthRule('bond', (True, ('cron', 'set')))

                    mesgs = await asbond.storm(f'cron.disable {guid[:6]}').list()
                    self.stormIsInPrint('Disabled cron job', mesgs)

                    mesgs = await asbond.storm(f'cron.enable {guid[:6]}').list()
                    self.stormIsInPrint('Enabled cron job', mesgs)

                    mesgs = await asbond.storm(f'cron.mod {guid[:6]} {{#foo}}').list()
                    self.stormIsInPrint('Modified cron job', mesgs)

                    await prox.addAuthRule('bond', (True, ('cron', 'del')))

                    mesgs = await asbond.storm(f'cron.del {guid[:6]}').list()
                    self.stormIsInPrint('Deleted cron job', mesgs)

    async def test_storm_lib_userview(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.setAdmin(True)

            await core.nodes('$lib.user.profile.set(cortex:view, $lib.view.get().fork().iden)', user=visi)

            self.nn(visi.profile.get('cortex:view'))

            self.len(1, await core.nodes('[ inet:ipv4=1.2.3.4 ]', user=visi))

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4'))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4', user=visi))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4', user=visi, opts={'view': core.view.iden}))

            async with core.getLocalProxy(user='visi') as prox:
                self.len(1, await prox.eval('inet:ipv4=1.2.3.4').list())
                self.len(0, await prox.eval('inet:ipv4=1.2.3.4', opts={'view': None}).list())
                self.len(0, await prox.eval('inet:ipv4=1.2.3.4', opts={'view': core.view.iden}).list())

            async with core.getLocalProxy(user='root') as prox:
                self.len(0, await prox.eval('inet:ipv4=1.2.3.4').list())
