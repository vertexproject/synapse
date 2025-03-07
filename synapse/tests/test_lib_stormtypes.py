import re
import bz2
import gzip
import base64
import struct
import asyncio
import hashlib
import binascii
import datetime
import contextlib

from datetime import timezone as tz
from unittest import mock

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.json as s_json
import synapse.lib.time as s_time
import synapse.lib.storm as s_storm
import synapse.lib.hashset as s_hashset
import synapse.lib.httpapi as s_httpapi
import synapse.lib.modelrev as s_modelrev
import synapse.lib.stormtypes as s_stormtypes

import synapse.tests.utils as s_test
import synapse.tests.files as s_test_files

from synapse.tests.utils import alist

MINSECS = 60
HOURSECS = 60 * MINSECS
DAYSECS = 24 * HOURSECS

class Newp:
    def __bool__(self):
        raise s_exc.SynErr(mesg='newp')

    def __int__(self):
        raise s_exc.SynErr(mesg='newp')

    def __str__(self):
        raise s_exc.SynErr(mesg='newp')

    def __repr__(self):
        return 'Newp'

linesbuf = b'''
vertex.link
woot.com
'''.strip(b'\n')

jsonsbuf = b'''
{"fqdn": "vertex.link"}
{"fqdn": "woot.com"}
'''.strip(b'\n')

class StormTypesTest(s_test.SynTest):

    async def test_stormtypes_copy(self):

        async with self.getTestCore() as core:
            item = await core.callStorm('''
            $item = ({"foo": {"bar": "baz"}, "hehe": []})
            $copy = $lib.copy($item)
            $item.foo.bar = hehe
            $copy.hehe.append(lolz)
            return($copy)
            ''')
            self.eq('baz', item['foo']['bar'])
            self.eq(['lolz'], item['hehe'])

            item = await core.callStorm('''
            $item = ([1, 2, 3])
            $copy = $lib.copy($item)
            $item.append((4))
            return($copy)
            ''')
            self.eq((1, 2, 3), item)

            self.eq('woot', await core.callStorm('return($lib.copy(woot))'))
            self.eq(10, await core.callStorm('return($lib.copy((10)))'))
            self.eq(None, await core.callStorm('return($lib.copy($lib.null))'))
            self.eq(True, await core.callStorm('return($lib.copy($lib.true))'))
            self.eq(False, await core.callStorm('return($lib.copy($lib.false))'))
            self.eq(b'V', await core.callStorm('return($lib.copy($x))', opts={'vars': {'x': b'V'}}))

            # is not a Prim
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.copy($lib))')

            # is not a Prim
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.copy($lib.print))')

            # does not support copy()
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.copy($lib.auth.users.byname(root)))')

            # nested type which contains a object that does not support copy()
            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.copy(({"lib": $lib})))')

    async def test_stormtypes_notify(self):

        async def testUserNotif(core):
            visi = await core.auth.addUser('visi')

            asvisi = {'user': visi.iden}
            mesgindx = await core.callStorm('return($lib.auth.users.byname(root).tell(heya))', opts=asvisi)

            msgs = await core.stormlist('''
                for ($indx, $mesg) in $lib.notifications.list() {
                    ($useriden, $mesgtime, $mesgtype, $mesgdata) = $mesg
                    if ($mesgtype = "tell") {
                        $lib.print("{user} says {text}", user=$mesgdata.from, text=$mesgdata.text)
                    }
                }
            ''')
            self.stormIsInPrint(f'{visi.iden} says heya', msgs)

            opts = {'user': visi.iden, 'vars': {'indx': mesgindx}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.notifications.del($indx)', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.notifications.get($indx))', opts=opts)

            opts = {'vars': {'indx': mesgindx}}
            await core.callStorm('$lib.notifications.del($indx)', opts=opts)

            msgs = await core.stormlist('''
                for ($indx, $mesg) in $lib.notifications.list() {
                    ($useriden, $mesgtime, $mesgtype, $mesgdata) = $mesg
                    if ($mesgtype = "tell") {
                        $lib.print("{user} says {text}", user=$mesgdata.from, text=$mesgdata.text)
                    }
                }
            ''')
            self.stormNotInPrint(f'{visi.iden} says heya', msgs)

            indx = await core.callStorm('return($lib.auth.users.byname(root).notify(hehe, ({"haha": "hoho"})))')
            opts = {'vars': {'indx': indx}}
            mesg = await core.callStorm('return($lib.notifications.get($indx))', opts=opts)
            self.eq(mesg[0], core.auth.rootuser.iden)
            self.eq(mesg[2], 'hehe')
            self.eq(mesg[3], {'haha': 'hoho'})

            opts = {'user': visi.iden}
            q = 'return($lib.auth.users.byname(root).notify(newp, ({"key": "valu"})))'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=opts)

            q = 'return($lib.auth.users.byname(root).notify(newp, ({"key": "valu"})))'
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(q, opts=opts)

            # Push a handful of notifications and list a subset of them
            q = '''$m=$lib.str.format('hello {i}', i=$i) return($lib.auth.users.byname(root).tell($m))'''
            for i in range(5):
                opts = {'user': visi.iden, 'vars': {'i': i}}
                await core.callStorm(q, opts=opts)

            q = '''for ($indx, $mesg) in $lib.notifications.list(size=$size) {
                ($useriden, $mesgtime, $mesgtype, $mesgdata) = $mesg
                $lib.print("{user} says {text}", user=$mesgdata.from, text=$mesgdata.text)
            }'''
            opts = {'vars': {'size': 3}}
            msgs = await core.stormlist(q, opts=opts)
            # We have a valid message that is the first item yielded
            # but it is not a "tell" format.
            self.stormIsInPrint('$lib.null says $lib.null', msgs)
            self.stormIsInPrint('hello 4', msgs)
            self.stormIsInPrint('hello 3', msgs)
            self.stormNotInPrint('hello 2', msgs)

        async with self.getTestCore() as core:
            await testUserNotif(core)

        # test with a remote jsonstor
        async with self.getTestJsonStor() as jsonstor:
            conf = {'jsonstor': jsonstor.getLocalUrl()}
            async with self.getTestCore(conf=conf) as core:
                await testUserNotif(core)

    async def test_stormtypes_jsonstor(self):

        async with self.getTestCore() as core:
            self.none(await core.callStorm('return($lib.jsonstor.get(foo))'))
            self.false(await core.callStorm('return($lib.jsonstor.has(foo))'))
            self.none(await core.callStorm('return($lib.jsonstor.get(foo, prop=bar))'))
            self.true(await core.callStorm('return($lib.jsonstor.set(hi, ({"foo": "bar", "baz": "faz"})))'))
            self.true(await core.callStorm('return($lib.jsonstor.set(bye/bye, ({"zip": "zop", "bip": "bop"})))'))
            self.true(await core.callStorm('return($lib.jsonstor.has(bye/bye))'))
            self.eq('bar', await core.callStorm('return($lib.jsonstor.get(hi, prop=foo))'))
            self.eq({'foo': 'bar', 'baz': 'faz'}, await core.callStorm('return($lib.jsonstor.get(hi))'))

            await core.callStorm('$lib.jsonstor.set(hi, hehe, prop=foo)')
            items = await core.callStorm('''
            $list = ()
            for $item in $lib.jsonstor.iter(bye) { $list.append($item) }
            return($list)
            ''')
            self.eq(items, (
                (('bye', ), {'zip': 'zop', 'bip': 'bop'}),
            ))
            self.true(await core.callStorm('return($lib.jsonstor.del(bye/bye, prop=zip))'))
            self.none(await core.callStorm('return($lib.jsonstor.get(bye/bye, prop=zip))'))
            self.true(await core.callStorm('return($lib.jsonstor.del(bye/bye))'))
            self.none(await core.callStorm('return($lib.jsonstor.get(bye/bye))'))

            visi = await core.auth.addUser('visi')
            asvisi = {'user': visi.iden}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.jsonstor.get(foo))', opts=asvisi)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.jsonstor.has(foo))', opts=asvisi)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.jsonstor.set(foo, bar))', opts=asvisi)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.jsonstor.del(foo))', opts=asvisi)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('for $item in $lib.jsonstor.iter() {}', opts=asvisi)

            # cache helpers

            self.none(await core.callStorm('return($lib.jsonstor.cacheget(foo/bar, baz))'))

            ret = await core.callStorm('return($lib.jsonstor.cacheset(foo/bar, baz, ({"bam": 1})))')
            asof = ret.get('asof')

            self.eq({
                'asof': asof,
                'data': {'bam': 1},
                'key': 'baz',
            }, await core.callStorm('return($lib.jsonstor.get($path))', opts={'vars': ret}))

            await asyncio.sleep(0.1)

            self.none(await core.callStorm('return($lib.jsonstor.cacheget(foo/bar, baz))'))
            self.eq({'bam': 1}, await core.callStorm('return($lib.jsonstor.cacheget(foo/bar, baz, asof="-1day"))'))
            self.eq({'bam': 1}, await core.callStorm('return($lib.jsonstor.cacheget((foo, bar), baz, asof="-1day"))'))

            self.eq({
                'asof': asof,
                'data': {'bam': 1},
                'key': 'baz',
            }, await core.callStorm('return($lib.jsonstor.cacheget(foo/bar, baz, asof="-1day", envl=$lib.true))'))

            self.none(await core.callStorm('return($lib.jsonstor.cacheget(foo/bar, (baz, $lib.true), asof="-1day"))'))

            self.nn(await core.callStorm('return($lib.jsonstor.cacheset(foo/bar, (baz, $lib.true), ({"bam": 2})))'))
            await asyncio.sleep(0.1)

            scmd = 'return($lib.jsonstor.cacheget(foo/bar, (baz, $lib.true), asof="-1day"))'
            self.eq({'bam': 2}, await core.callStorm(scmd))

            self.nn(await core.callStorm('return($lib.jsonstor.cacheset((foo, bar), baz, ({"bam": 3})))'))
            await asyncio.sleep(0.1)

            self.eq({'bam': 3}, await core.callStorm('return($lib.jsonstor.cacheget(foo/bar, baz, asof="-1day"))'))

            path = ('cells', core.iden, 'foo', 'bar')
            items = sorted(await alist(core.jsonstor.getPathObjs(path)), key=lambda x: x[1]['asof'])
            self.len(2, items)
            self.true(all(len(item[0]) == 1 and s_common.isguid(item[0][0]) for item in items))
            [item[1].pop('asof') for item in items]
            self.eq({'key': ('baz', True), 'data': {'bam': 2}}, items[0][1])
            self.eq({'key': 'baz', 'data': {'bam': 3}}, items[1][1])

            self.true(await core.callStorm('return($lib.jsonstor.cachedel(newp/newp, nah))'))
            self.true(await core.callStorm('return($lib.jsonstor.cachedel(foo/bar, baz))'))
            self.true(await core.callStorm('return($lib.jsonstor.cachedel((foo, bar), (baz, $lib.true)))'))
            await self.agenlen(0, core.jsonstor.getPathObjs(path))

            with self.raises(s_exc.NoSuchType):
                await core.callStorm('return($lib.jsonstor.cacheset(foo/bar, $lib.queue, (1)))')

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.jsonstor.cacheget(foo, bar))', opts=asvisi)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.jsonstor.cacheset(foo, bar, baz))', opts=asvisi)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.jsonstor.cachedel(foo, bar))', opts=asvisi)

    async def test_stormtypes_registry(self):

        class NewpType(s_stormtypes.StormType):
            _storm_locals = ()
            _storm_typename = 'storm:type:newp'

        self.notin('storm:type:newp', s_stormtypes.registry.known_types)
        self.notin('storm:type:newp', s_stormtypes.registry.undefined_types)
        s_stormtypes.registry.registerType(NewpType)
        self.isin('storm:type:newp', s_stormtypes.registry.known_types)
        self.notin('storm:type:newp', s_stormtypes.registry.undefined_types)
        s_stormtypes.registry.delStormType(NewpType.__name__)

        self.notin('storm:type:newp', s_stormtypes.registry.known_types)
        self.isin('storm:type:newp', s_stormtypes.registry.undefined_types)

        # Remove the modification from the global
        s_stormtypes.registry.undefined_types.discard('storm:type:newp')

    async def test_storm_debug(self):

        async with self.getTestCore() as core:
            self.true(await core.callStorm('return($lib.debug)', opts={'debug': True}))
            await core.addStormPkg({
                'name': 'hehe',
                'version': '1.1.1',
                'modules': [
                    {'name': 'hehe', 'storm': 'function getDebug() { return($lib.debug) }'},
                ],
                'commands': [
                    {'name': 'hehe.haha', 'storm': 'if $lib.debug { $lib.print(hehe.haha) }'},
                ],
            })

            self.false(await core.callStorm('return($lib.import(hehe).getDebug())'))
            self.true(await core.callStorm('return($lib.import(hehe, debug=(1)).getDebug())'))
            self.true(await core.callStorm('$lib.debug = (1) return($lib.import(hehe).getDebug())'))
            msgs = await core.stormlist('$lib.debug = (1) hehe.haha')
            self.stormIsInPrint('hehe.haha', msgs)

    async def test_storm_doubleadd_pkg(self):
        async with self.getTestCore() as core:
            async with core.beholder() as wind:
                pkg = {
                    'name': 'hehe',
                    'version': '1.1.1',
                    'modules': [
                        {'name': 'hehe', 'storm': 'function getDebug() { return($lib.debug) }'},
                    ],
                    'commands': [
                        {'name': 'hehe.haha', 'storm': 'if $lib.debug { $lib.print(hehe.haha) }'},
                    ],
                }

                # all but the first of these should bounce
                for i in range(5):
                    await core.addStormPkg(pkg)

                pkg['version'] = '1.2.3'

                # all but the first of these should bounce
                for i in range(5):
                    await core.addStormPkg(pkg)

            events = []
            async for m in wind:
                events.append(m)
            self.len(2, events)
            self.eq('pkg:add', events[0]['event'])
            self.eq('hehe', events[0]['info']['name'])
            self.eq('1.1.1', events[0]['info']['version'])

            self.eq('pkg:add', events[1]['event'])
            self.eq('hehe', events[1]['info']['name'])
            self.eq('1.2.3', events[1]['info']['version'])

    async def test_storm_private(self):
        async with self.getTestCore() as core:
            await core.addStormPkg({
                'name': 'hehe',
                'version': '1.1.1',
                'modules': [
                    {'name': 'hehe',
                     'storm': '''
                        $pub = 'foo'
                        $_pub = 'bar'
                        $__priv = 'baz'
                        $___priv = 'baz'
                        function pubFunc() { return($__priv) }
                        function __privFunc() { return($__priv) }
                        function _pubFunc() { return($__privFunc()) }
                     '''},
                ]
            })

            self.eq('foo', await core.callStorm('return($lib.import(hehe).pub)'))
            self.eq('bar', await core.callStorm('return($lib.import(hehe)._pub)'))
            self.eq('baz', await core.callStorm('return($lib.import(hehe).pubFunc())'))
            self.eq('baz', await core.callStorm('return($lib.import(hehe)._pubFunc())'))

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('return($lib.import(hehe).__priv)')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('return($lib.import(hehe).___priv)')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('return($lib.import(hehe).__privFunc())')

    async def test_storm_node_tags(self):
        async with self.getTestCore() as core:
            await core.nodes('[ test:comp=(20, haha) +#foo +#bar test:comp=(30, hoho) ]')

            q = '''
            test:comp
            for $tag in $node.tags() {
                -> test:int [ +#$tag ]
            }
            '''

            await core.nodes(q)

            self.len(1, await core.nodes('test:int#foo'))
            self.len(1, await core.nodes('test:int#bar'))

            q = '''
            test:comp
            for $tag in $node.tags(fo*) {
                -> test:int [ -#$tag ]
            }
            '''
            await core.nodes(q)

            self.len(0, await core.nodes('test:int#foo'))
            self.len(1, await core.nodes('test:int#bar'))

            await core.nodes('test:comp [+#foo.thing1.cool +#bar.thing2.cool +#bar.thing3.notcool.newp +#bar.thing3.notcool.yup]')
            ret = await core.callStorm('test:comp return ( $node.tags(leaf=$lib.true) )')
            self.eq(set(ret), {'foo.thing1.cool', 'bar.thing2.cool', 'bar.thing3.notcool.newp', 'bar.thing3.notcool.yup'})

            ret = await core.callStorm('test:comp return ( $node.tags(glob="*.*.cool", leaf=$lib.true) )')
            self.eq(set(ret), {'foo.thing1.cool', 'bar.thing2.cool'})

            ret = await core.callStorm('test:comp return ( $node.tags(glob="*.*.notcool.*", leaf=$lib.false) )')
            self.eq(set(ret), {'bar.thing3.notcool.yup', 'bar.thing3.notcool.newp'})

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
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # explicit behavior tests
            q = 'test:str=woot $globs=$node.globtags("foo.*.*.faz") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.stormlist(q)
            e = {('bar', 'baz'), ('bar', 'jaz'), ('knight', 'day')}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.*") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.stormlist(q)
            e = {'baz', 'jaz'}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.*.*") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.stormlist(q)
            e = {('baz', 'faz'), ('jaz', 'faz')}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.**") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.stormlist(q)
            e = {'baz', 'baz.faz', 'jaz', 'jaz.faz'}
            check_fire_mesgs(mesgs, e)

            q = 'test:str=woot $globs=$node.globtags("foo.bar.*.*.*") $lib.fire(test, globs=$globs) -test:str'
            mesgs = await core.stormlist(q)
            e = set()
            check_fire_mesgs(mesgs, e)

            # For loop example for a single-match case
            q = '''test:str=woot
            for $part in $node.globtags("foo.bar.*") {
                [test:str=$part]
            }'''
            mesgs = await core.stormlist(q)
            self.len(1, await core.nodes('test:str=baz'))
            self.len(1, await core.nodes('test:str=jaz'))

            # For loop example for a multi-match case
            q = '''test:str=woot
                for ($part1, $part2, $part3) in $node.globtags("foo.*.*.*") {
                    [test:str=$part1] -test:str=woot [+#$part3]
                }'''
            mesgs = await core.stormlist(q)
            self.len(1, await core.nodes('test:str=bar'))
            self.len(1, await core.nodes('test:str=knight'))
            self.len(2, await core.nodes('#faz'))

    async def test_storm_node_difftags(self):
        async with self.getTestCore() as core:

            retn = await core.callStorm('[ test:str=foo ] return($node.difftags((["foo", "bar"])))')
            self.sorteq(retn['adds'], ['foo', 'bar'])
            self.eq(retn['dels'], [])

            nodes = await core.nodes('test:str=foo $node.difftags((["foo", "bar"]), apply=$lib.true)')
            self.sorteq(nodes[0].tags, ['foo', 'bar'])

            retn = await core.callStorm('[ test:str=foo ] return($node.difftags((["foo", "bar"])))')
            self.eq(retn['adds'], [])
            self.eq(retn['dels'], [])

            retn = await core.callStorm('test:str=foo return($node.difftags((["foo", "baz"])))')
            self.eq(retn['adds'], ['baz'])
            self.eq(retn['dels'], ['bar'])

            nodes = await core.nodes('test:str=foo $node.difftags((["foo", "baz.bar"]), apply=$lib.true)')
            self.sorteq(nodes[0].tags, ['foo', 'baz', 'baz.bar'])

            nodes = await core.nodes('test:str=foo [-#$node.tags()]')
            self.eq(nodes[0].tags, {})

            nodes = await core.nodes('test:str=foo $node.difftags((["foo", "baz.bar"]), prefix=test, apply=$lib.true)')
            self.sorteq(nodes[0].tags, ['test', 'test.foo', 'test.baz', 'test.baz.bar'])

            nodes = await core.nodes('test:str=foo $node.difftags((["foo", "baz"]), prefix=test, apply=$lib.true)')
            self.sorteq(nodes[0].tags, ['test', 'test.foo', 'test.baz'])

            nodes = await core.nodes('test:str=foo $node.difftags((["foo", "baz"]), prefix=baz, apply=$lib.true)')
            self.sorteq(nodes[0].tags, ['test', 'test.foo', 'test.baz', 'baz', 'baz.foo', 'baz.baz'])

            nodes = await core.nodes('test:str=foo $node.difftags((["foo", "baz", ""]), apply=$lib.true)')
            self.sorteq(nodes[0].tags, ['foo', 'baz'])

            nodes = await core.nodes('test:str=foo $node.difftags((["foo-bar", ""]), apply=$lib.true, norm=$lib.true)')
            self.sorteq(nodes[0].tags, ['foo_bar'])

            nodes = await core.nodes('test:str=foo $node.difftags((["foo-bar", "foo", "baz"]), apply=$lib.true)')
            self.sorteq(nodes[0].tags, ['foo', 'baz'])

            await core.setTagModel("foo", "regex", (None, "[a-zA-Z]{3}"))
            async with await core.snap() as snap:
                snap.strict = False
                nodes = await snap.nodes('test:str=foo $tags=(["foo", "foo.a"]) [ -#$tags ]')
                self.eq(list(nodes[0].tags.keys()), ['baz'])

    async def test_storm_lib_base(self):
        pdef = {
            'name': 'foo',
            'desc': 'test',
            'version': (0, 0, 1),
            'synapse_version': '>=2.8.0,<3.0.0',
            'modules': [
                {
                    'name': 'test',
                    'storm': '$valu=$modconf.valu function getvalu() { return($valu) }',
                    'modconf': {'valu': 'foo'},
                },
                {
                    'name': 'test.danger',
                    'storm': '''
                        init { $src=$lib.null }
                        function genSrc() { if $src { return ($src) } [meta:source=(s1,)] $src=$node return ($node) }
                        $genSrc()
                        '''
                }
            ],
            'commands': [
            ],
        }
        async with self.getTestCore() as core:

            with self.raises(s_exc.NoSuchType):
                await core.nodes('$lib.cast(newp, asdf)')

            with self.raises(s_exc.NoSuchType):
                await core.nodes('$lib.trycast(newp, asdf)')

            self.eq(4, await core.callStorm('$x = asdf return($x.size())'))
            self.eq(2, await core.callStorm('$x = asdf return($x.find(d))'))
            self.eq(None, await core.callStorm('$x = asdf return($x.find(v))'))

            self.eq(('f', 'o', 'o'), await core.callStorm('$x = () $x.extend((f, o, o)) return($x)'))
            self.eq(('o', 'o', 'b', 'a'), await core.callStorm('$x = (f, o, o, b, a, r) return($x.slice(1, 5))'))
            self.eq(('o', 'o', 'b', 'a', 'r'), await core.callStorm('$x = (f, o, o, b, a, r) return($x.slice(1))'))

            self.true(await core.callStorm('return($lib.trycast(inet:ipv4, 1.2.3.4).0)'))
            self.false(await core.callStorm('return($lib.trycast(inet:ipv4, asdf).0)'))

            self.eq(None, await core.callStorm('return($lib.trycast(inet:ipv4, asdf).1)'))
            self.eq(0x01020304, await core.callStorm('return($lib.trycast(inet:ipv4, 1.2.3.4).1)'))

            # trycast/cast a property instead of a form/type
            flow = s_json.loads(s_test_files.getAssetStr('attack_flow/CISA AA22-138B VMWare Workspace (Alt).json'))
            opts = {'vars': {'flow': flow}}
            self.true(await core.callStorm('return($lib.trycast(it:mitre:attack:flow:data, $flow).0)', opts=opts))
            self.false(await core.callStorm('return($lib.trycast(it:mitre:attack:flow:data, {}).0)'))
            self.eq(flow, await core.callStorm('return($lib.cast(it:mitre:attack:flow:data, $flow))', opts=opts))

            self.true(await core.callStorm('$x=(foo,bar) return($x.has(foo))'))
            self.false(await core.callStorm('$x=(foo,bar) return($x.has(newp))'))
            self.false(await core.callStorm('$x=(foo,bar) return($x.has((foo,bar)))'))

            await core.addStormPkg(pdef)
            nodes = await core.nodes('[ inet:asn=$lib.min(20, (0x30)) ]')
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

            # $lib.min / $lib.max behavior with 1 item
            ret = await core.callStorm('$x = ([(1234)]) return ( $lib.min($x) )')
            self.eq(ret, 1234)

            ret = await core.callStorm('return ( $lib.min(1234) )')
            self.eq(ret, 1234)

            ret = await core.callStorm('$x = ([(1234)]) return ( $lib.max($x) )')
            self.eq(ret, 1234)

            ret = await core.callStorm('return ( $lib.max(1234) )')
            self.eq(ret, 1234)

            # $lib.min / $lib.max behavior with 0 items
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$lib.max()')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$l=() $lib.max($l)')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$lib.min()')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$l=() $lib.min($l)')

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

            self.ne(s_common.guid('foo'), await core.callStorm('return($lib.guid(foo))'))
            self.eq(s_common.guid('foo'), await core.callStorm('return($lib.guid(valu=foo))'))

            with self.raises(s_exc.BadArg) as ectx:
                await core.callStorm('return($lib.guid(foo, valu=bar))')
            self.eq('Valu cannot be specified if positional arguments are provided', ectx.exception.errinfo['mesg'])

            await self.asyncraises(s_exc.NoSuchType, core.callStorm('return($lib.guid(valu=$lib))'))

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

            q = '''
                $set = $lib.set(c, b, a)
                for $x in $lib.sorted($set, reverse=$lib.true) {
                    [ test:str=$x ]
                }
            '''
            nodes = await core.nodes(q)
            self.len(3, nodes)
            self.eq(nodes[0].ndef[1], 'c')
            self.eq(nodes[1].ndef[1], 'b')
            self.eq(nodes[2].ndef[1], 'a')

            # $lib.import
            q = '$test = $lib.import(test) $lib.print($test)'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('Imported Module test', msgs)
            q = '$test = $lib.import(newp)'
            msgs = await core.stormlist(q)
            erfo = [m for m in msgs if m[0] == 'err'][0]
            self.eq(erfo[1][0], 'NoSuchName')
            self.eq(erfo[1][1].get('name'), 'newp')

            await core.callStorm('$test = $lib.import(test) $test.modconf.valu=bar')
            self.eq('foo', await core.callStorm('return($lib.import(test).getvalu())'))
            self.eq('foo', await core.callStorm('return($lib.import(test).getvalu())', opts={'readonly': True}))

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('return($lib.import(test.danger).src)', opts={'readonly': True})

            mods = await core.getStormMods()
            self.len(2, mods)
            mods['test']['modconf']['valu'] = 'bar'
            mods = await core.getStormMods()
            self.eq('foo', mods['test']['modconf']['valu'])

            # lib.len()
            opts = {
                'vars': {
                    'true': True,
                    'list': [1, 2, 3],
                    'dict': {'k1': 'v1', 'k2': 'v2'},
                    'str': '1138',
                    'bytes': b'o'
                }
            }

            self.eq(4, await core.callStorm('return($lib.len($str))', opts=opts))
            self.eq(3, await core.callStorm('return($lib.len($list))', opts=opts))
            self.eq(2, await core.callStorm('return($lib.len($dict))', opts=opts))
            self.eq(1, await core.callStorm('return($lib.len($bytes))', opts=opts))

            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.nodes('$lib.print($lib.len($true))', opts=opts)
            self.eq(cm.exception.get('mesg'), 'Object builtins.bool does not have a length.')

            mesgs = await core.stormlist('$lib.print((1,(2),3))')
            self.stormIsInPrint("['1', 2, '3']", mesgs)

            mesgs = await core.stormlist('$lib.print(${ $foo=bar })')
            self.stormIsInPrint('storm:query: " $foo=bar "', mesgs)

            mesgs = await core.stormlist('$lib.print($lib.set(1,2,3))')
            self.stormIsInPrint("'1'", mesgs)
            self.stormIsInPrint("'2'", mesgs)
            self.stormIsInPrint("'3'", mesgs)

            mesgs = await core.stormlist('$lib.print(({"foo": "1", "bar": "2"}))')
            self.stormIsInPrint("'foo': '1'", mesgs)
            self.stormIsInPrint("'bar': '2'", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.dict)')
            self.stormIsInPrint("Library $lib.dict", mesgs)

            mesgs = await core.stormlist('$lib.print($lib)')
            self.stormIsInPrint("Library $lib", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.queue.add(testq))')
            self.stormIsInPrint("queue: testq", mesgs)

            mesgs = await core.stormlist('$lib.pprint((1,2,3))')
            self.stormIsInPrint("('1', '2', '3')", mesgs)

            mesgs = await core.stormlist('$lib.pprint(({"foo": "1", "bar": "2"}))')
            self.stormIsInPrint("'foo': '1'", mesgs)
            self.stormIsInPrint("'bar': '2'", mesgs)

            mesgs = await core.stormlist('$lib.pprint($lib)')
            self.stormIsInPrint("LibBase object", mesgs)

            mesgs = await core.stormlist('$lib.pprint(newp, clamp=2)')
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('Invalid clamp length.', err[1].get('mesg'))

            # lib.guid()
            opts = {'vars': {'x': {'foo': 'bar'}, 'y': ['foo']}}
            guid00 = await core.callStorm('return($lib.guid($x, $y))', opts=opts)
            guid01 = await core.callStorm('$x=({"foo": "bar"}) $y=(foo,) return($lib.guid($x, $y))')
            self.eq(guid00, guid01)

            guid00 = await core.callStorm('return($lib.guid(foo))')
            guid01 = await core.callStorm('[test:str=foo] return($lib.guid($node))')
            self.eq(guid00, guid01)

            guid = await core.callStorm('return($lib.guid($lib.undef))')
            self.eq(s_common.guid(()), guid)

            guid = await core.callStorm('return($lib.guid(($lib.undef,)))')
            self.eq(s_common.guid(((),)), guid)

            guid = await core.callStorm('$foo = ($lib.undef,) return($lib.guid(({"foo": $foo})))')
            self.eq(s_common.guid(({'foo': ()},)), guid)

            mesgs = await core.stormlist('function foo() { test:str } $lib.guid($foo())')
            self.stormIsInErr('can not serialize \'async_generator\'', mesgs)

            # lib.range()
            q = 'for $v in $lib.range($stop, start=$start, step=$step) { $lib.fire(range, v=$v) }'

            async def getseqn(genr, name, key):
                seqn = []
                async for mtyp, info in genr:
                    if mtyp != 'storm:fire':
                        continue
                    self.eq(info.get('type'), name)
                    seqn.append(info.get('data', {}).get(key))
                return seqn

            opts = {'vars': {'stop': 3, 'start': None, 'step': None}}
            items = await getseqn(core.storm(q, opts), 'range', 'v')
            self.eq(items, [0, 1, 2])

            opts = {'vars': {'stop': 3, 'start': 1, 'step': None}}
            items = await getseqn(core.storm(q, opts), 'range', 'v')
            self.eq(items, [1, 2])

            opts = {'vars': {'stop': 5, 'start': 0, 'step': 2}}
            items = await getseqn(core.storm(q, opts), 'range', 'v')
            self.eq(items, [0, 2, 4])

            opts = {'vars': {'stop': 0, 'start': 4, 'step': None}}
            items = await getseqn(core.storm(q, opts), 'range', 'v')
            self.eq(items, [])

            opts = {'vars': {'stop': 0, 'start': 4, 'step': -1}}
            items = await getseqn(core.storm(q, opts), 'range', 'v')
            self.eq(items, [4, 3, 2, 1])

            tags = await core.callStorm('return($lib.tags.prefix((foo, bar, "foo.baz", "."), visi))')
            self.eq(tags, ('visi.foo', 'visi.bar', 'visi.foo_baz'))

            tags = await core.callStorm('return($lib.tags.prefix((foo, bar, "foo.baz"), visi, ispart=$lib.true))')
            self.eq(tags, ('visi.foo', 'visi.bar', 'visi.foo.baz'))

            self.none(await core.callStorm('[inet:user=visi] return($node.data.cacheget(foo))'))

            await core.callStorm('inet:user=visi $node.data.cacheset(foo, bar)')
            envl = await core.callStorm('inet:user=visi return($node.data.get(foo))')
            self.nn(envl.get('asof'))
            self.eq('bar', envl.get('data'))

            self.none(await core.callStorm('inet:user=visi return($node.data.cacheget(foo))'))
            self.eq('bar', await core.callStorm('inet:user=visi return($node.data.cacheget(foo, asof="-30days"))'))

            lowuser = await core.auth.addUser('lowuser')

            aslow = {'user': lowuser.iden}
            await lowuser.addRule((False, ('auth', 'self', 'set')))
            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.auth.users.byname(lowuser).setPasswd(hehehaha)', opts=aslow)
            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.auth.users.byname(lowuser).setEmail(v@vtx.lk)', opts=aslow)
            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.auth.users.byname(lowuser).name = derpuser', opts=aslow)
            with self.raises(s_exc.AuthDeny):
                async with core.getLocalProxy(user='lowuser') as proxy:
                    await proxy.setUserPasswd(lowuser.iden, 'hehehaha')

            self.none(await s_stormtypes.tobuidhex(None, noneok=True))

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')
            self.eq(nodes[0].iden(), await s_stormtypes.tobuidhex(nodes[0]))
            stormnode = s_stormtypes.Node(nodes[0])
            self.eq(nodes[0].iden(), await s_stormtypes.tobuidhex(stormnode))

            iden = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': iden}
            await core.nodes('[ ou:org=* ou:org=* ]', opts=opts)
            self.eq(2, await core.callStorm('return($lib.len($lib.layer.get().getStorNodes()))', opts=opts))

            await core.nodes('[ media:news=c0dc5dc1f7c3d27b725ef3015422f8e2 +(refs)> { inet:ipv4=1.2.3.4 } ]')
            edges = await core.callStorm('''
                $edges = ([])
                media:news=c0dc5dc1f7c3d27b725ef3015422f8e2
                for $i in $lib.layer.get().getEdgesByN1($node.iden()) { $edges.append($i) }
                fini { return($edges) }
            ''')
            self.eq([('refs', '20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f')], edges)

            edges = await core.callStorm('''
                $edges = ([])
                inet:ipv4=1.2.3.4
                for $i in $lib.layer.get().getEdgesByN2($node.iden()) { $edges.append($i) }
                fini { return($edges) }
            ''')
            self.eq([('refs', 'ddf7f87c0164d760e8e1e5cd2cae2fee96868a3cf184f6dab9154e31ad689528')], edges)

            edges = await core.callStorm('''
                $edges = ([])
                for $i in $lib.layer.get().getEdges() { $edges.append($i) }
                return($edges)
            ''')
            self.isin(('ddf7f87c0164d760e8e1e5cd2cae2fee96868a3cf184f6dab9154e31ad689528',
                       'refs',
                       '20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f'), edges)

            data = await core.callStorm('''
                $data = ({})
                inet:user=visi
                for ($name, $valu) in $lib.layer.get().getNodeData($node.iden()) { $data.$name = $valu }
                return($data)
            ''')
            foo = data.get('foo')
            self.nn(foo)
            self.nn(foo.get('asof'))
            self.eq('bar', foo.get('data'))

            msgs = await core.stormlist('$lib.print($lib.null)')
            self.stormIsInPrint('$lib.null', msgs)
            self.stormNotInPrint('None', msgs)

            msgs = await core.stormlist('$lib.print($lib.true)')
            self.stormIsInPrint('true', msgs)
            self.stormNotInPrint('True', msgs)

            msgs = await core.stormlist('$lib.print($lib.false)')
            self.stormIsInPrint('false', msgs)
            self.stormNotInPrint('False', msgs)

            msgs = await core.stormlist('$lib.print($lib.undef)')
            self.stormIsInPrint('$lib.undef', msgs)

            msgs = await core.stormlist('auth.user.add visi')
            self.stormHasNoWarnErr(msgs)
            msgs = await core.stormlist('auth.user.addrule visi view.read')
            self.stormHasNoWarnErr(msgs)

            fork00 = await core.callStorm('return($lib.view.get().fork())')
            iden = fork00.get('iden')

            visi = await core.auth.getUserByName('visi')
            with self.raises(s_exc.AuthDeny):
                await core.nodes('$lib.view.get().detach()', opts={'user': visi.iden, 'view': iden})

            await core.stormlist('$lib.view.get().detach()', opts={'view': iden})

            with self.raises(s_exc.BadArg):
                await core.nodes('$lib.view.get().detach()', opts={'view': iden})

            view = core.reqView(iden)

            self.none(view.parent)
            self.none(view.info.get('parent'))

    async def test_storm_lib_ps(self):

        async with self.getTestCore() as core:

            evnt = asyncio.Event()
            iden = s_common.guid()

            async def runLongStorm():
                q = f'[ test:str=foo test:str={"x"*100} ] | sleep 10 | [ test:str=endofquery ]'
                async for mesg in core.storm(q, opts={'task': iden}):
                    if mesg[0] == 'init':
                        self.true(mesg[1]['task'] == iden)
                    evnt.set()

            task = core.schedCoro(runLongStorm())

            self.true(await asyncio.wait_for(evnt.wait(), timeout=6))

            with self.raises(s_exc.BadArg):
                await core.schedCoro(core.stormlist('inet:ipv4', opts={'task': iden}))

            # Verify that the long query got truncated
            msgs = await core.stormlist('ps.list')

            for msg in msgs:
                if msg[0] == 'print' and 'xxx...' in msg[1]['mesg']:
                    self.eq(120, len(msg[1]['mesg']))

            self.stormIsInPrint('xxx...', msgs)
            self.stormIsInPrint('name: storm', msgs)
            self.stormIsInPrint('user: root', msgs)
            self.stormIsInPrint('status: $lib.null', msgs)
            self.stormIsInPrint('2 tasks found.', msgs)
            self.stormIsInPrint('start time: 2', msgs)

            self.stormIsInPrint(f'task iden: {iden}', msgs)

            # Verify we see the whole query
            msgs = await core.stormlist('ps.list --verbose')
            self.stormIsInPrint('endofquery', msgs)

            msgs = await core.stormlist(f'ps.kill {iden}')
            self.stormIsInPrint('kill status: true', msgs)
            self.true(task.done())

            msgs = await core.stormlist('ps.list')
            self.stormIsInPrint('1 tasks found.', msgs)

            bond = await core.auth.addUser('bond')

            async with core.getLocalProxy(user='bond') as prox:

                evnt = asyncio.Event()
                iden = None

                async def runLongStorm():
                    async for mesg in core.storm('[ test:str=foo test:str=bar ] | sleep 10'):
                        nonlocal iden
                        if mesg[0] == 'init':
                            iden = mesg[1]['task']
                        evnt.set()

                task = core.schedCoro(runLongStorm())
                self.true(await asyncio.wait_for(evnt.wait(), timeout=6))

                msgs = await core.stormlist('ps.list')
                self.stormIsInPrint('2 tasks found.', msgs)
                self.stormIsInPrint(f'task iden: {iden}', msgs)

                msgs = await alist(prox.storm('ps.list'))
                self.stormIsInPrint('1 tasks found.', msgs)

                # Try killing from the unprivileged user
                msgs = await alist(prox.storm(f'ps.kill {iden}'))
                self.stormIsInErr('Provided iden does not match any processes.', msgs)

                # Try a kill with a numeric identifier - this won't match
                msgs = await alist(prox.storm(f'ps.kill 123412341234'))
                self.stormIsInErr('Provided iden does not match any processes.', msgs)

                # Give user explicit permissions to list
                await core.addUserRule(bond.iden, (True, ('task', 'get')))

                # Match all tasks
                msgs = await alist(prox.storm(f"ps.kill ''"))
                self.stormIsInErr('Provided iden matches more than one process.', msgs)

                msgs = await alist(prox.storm('ps.list'))
                self.stormIsInPrint(f'task iden: {iden}', msgs)

                # Give user explicit license to kill
                await core.addUserRule(bond.iden, (True, ('task', 'del')))

                # Kill the task as the user
                msgs = await alist(prox.storm(f'ps.kill {iden}'))
                self.stormIsInPrint('kill status: true', msgs)
                self.true(task.done())

                # Kill a task that doesn't exist
                self.false(await core.kill(bond, 'newp'))

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

            # exec vars do not populate upwards
            q = '''
            $foo = "that is one neato burrito"
            $baz = ${ $bar=$lib.str.concat(wompwomp, $lib.guid()) $lib.print("in exec") }
            $baz.exec()
            $lib.print("post exec {bar}", bar=$bar)
            [ test:str=$foo ]
            '''
            with self.raises(s_exc.NoSuchVar):
                await core.nodes(q)

            # make sure returns work
            q = '''
            $foo = $(10)
            $bar = ${ return ( $($foo+1) ) }
            [test:int=$bar.exec()]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 11))

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
            msgs = await core.stormlist(q)
            self.stormIsInPrint('look ma, my runt', msgs)
            self.stormIsInPrint('bing is now 99', msgs)

            # vars may be captured for each node flowing through them
            q = '''[(test:int=100 :loc=us.va) (test:int=200 :loc=us.ca)] $foo=:loc
            $q = ${ $lib.print($foo) } $q.exec()'''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('us.va', msgs)
            self.stormIsInPrint('us.ca', msgs)

            # Yield/iterator behavior
            nodes = await core.nodes('''
                function foo(x) {
                    return(${
                        [ inet:ipv4=$x ]
                    })
                }

                [it:dev:str=1.2.3.4]

                $genr = $foo($node.repr())

                -> { yield $genr }
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            nodes = await core.nodes('''
                function foo(x) {
                    return( ${ [ inet:ipv4=$x ] } )
                }

                [it:dev:str=5.5.5.5]

                $genr = $foo($node.repr())

                $genr.exec()
            ''')
            self.len(1, await core.nodes('inet:ipv4=5.5.5.5'))

            msgs = await core.stormlist('''
                $embed = ${[inet:ipv4=1.2.3.4]}
                for $xnode in $embed {
                    $lib.print($xnode.repr())
                }
            ''')
            self.stormIsInPrint('1.2.3.4', msgs)

            q = '''[test:int=1 test:int=2]
            $currentNode = $node
            $q=${ [test:str=$currentNode.value()] }
            yield $q
            '''
            nodes = await core.nodes(q)
            self.len(4, nodes)
            self.eq({n.ndef for n in nodes},
                    {('test:int', 1), ('test:int', 2), ('test:str', '1'), ('test:str', '2')})

            # You can toprim() as Query object.
            q = '''$q=${ $lib.print('fire in the hole') } $lib.fire('test', q=$q)
            '''
            msgs = await core.stormlist(q)
            fires = [m for m in msgs if m[0] == 'storm:fire']
            self.len(1, fires)
            self.eq(fires[0][1].get('data').get('q'),
                    " $lib.print('fire in the hole') ")

            q = '''
            $q=${ [test:int=1 test:int=2] }
            return($q.size())
            '''
            self.eq(2, await core.callStorm(q))

            q = '''
            $q=${ [test:int=1 test:int=2] return($node.value()) }
            return($q.size())
            '''
            self.eq(0, await core.callStorm(q))

            q = '''
            $q=${ [test:int=1 test:int=2] fini { return($lib.null) } }
            return($q.size())
            '''
            self.eq(2, await core.callStorm(q))

            q = '''
            $q=${ [test:int=1 test:int=2 test:int=3] }
            return($q.size(limit=2))
            '''
            self.eq(2, await core.callStorm(q))

            q = '''
            $q=${ return( $lib.auth.users.byname(root).name ) }
            return ( $q.exec() )
            '''
            self.eq('root', await core.callStorm(q, opts={'readonly': True}))

            q = '''
            $q=${ test:int=1 }
            return ( $q.size() )
            '''
            self.eq(1, await core.callStorm(q, opts={'readonly': True}))

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('$foo=${ [test:str=readonly] } return ( $foo.exec() )', opts={'readonly': True})

            with self.raises(s_exc.IsReadOnly):
                await core.callStorm('$foo=${ [test:str=readonly] } return( $foo.size() )', opts={'readonly': True})

    async def test_storm_lib_node(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('[ test:str=woot :tick=2001] [ test:int=$node.isform(test:str) ] +test:int')
            self.eq(1, nodes[0].ndef[1])

            q = 'test:str=woot $lib.fire(name=pode, pode=$node.pack(dorepr=True))'
            msgs = await core.stormlist(q, opts={'repr': True})
            pode = [m[1] for m in msgs if m[0] == 'node'][0]
            apode = [m[1].get('data').get('pode') for m in msgs if m[0] == 'storm:fire'][0]
            self.eq(pode[0], ('test:str', 'woot'))
            pode[1].pop('path')
            self.eq(pode, apode)

    async def test_storm_lib_dict(self):
        async with self.getTestCore() as core:
            nodes = await core.nodes('$blah = ({"foo": "vertex.link"}) [ inet:fqdn=$blah.foo ]')
            self.len(1, nodes)
            self.eq('vertex.link', nodes[0].ndef[1])

            self.eq(2, await core.callStorm('$d=({"k1": "1", "k2": "2"}) return($lib.len($d))'))

            d = {'key1': 'val1', 'key2': None}
            opts = {'vars': {'d': d}}
            has = await core.callStorm('return($lib.dict.has($d, "key1"))', opts=opts)
            self.true(has)

            has = await core.callStorm('return($lib.dict.has($d, "key2"))', opts=opts)
            self.true(has)

            has = await core.callStorm('return($lib.dict.has($d, "key3"))', opts=opts)
            self.false(has)

            d = {'key1': 'val1', 'key2': 'val2'}
            opts = {'vars': {'d': d}}
            keys = await core.callStorm('return($lib.dict.keys($d))', opts=opts)
            self.eq(keys, ['key1', 'key2'])

            vals = await core.callStorm('return($lib.dict.values($d))', opts=opts)
            self.eq(vals, ['val1', 'val2'])

            val = await core.callStorm('return($lib.dict.pop($d, "key2"))', opts=opts)
            self.eq(val, 'val2')
            self.eq(d, {'key1': 'val1'})

            val = await core.callStorm('return($lib.dict.pop($d, "newp", "w00t"))', opts=opts)
            self.eq(val, 'w00t')
            self.eq(d, {'key1': 'val1'})

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.dict.pop($d, "newp"))', opts=opts)

            await core.callStorm('$lib.dict.update($d, ({"foo": "bar"}))', opts=opts)
            self.eq(d, {'key1': 'val1', 'foo': 'bar'})

            msgs = await core.stormlist('$d = $lib.dict(foo=bar, baz=woot)')
            self.stormIsInWarn('$lib.dict() is deprecated. Use ({}) instead.', msgs)

            msgs = await core.stormlist('$lib.dict.keys(([]))')
            self.stormIsInErr('valu argument must be a dict, not list.', msgs)

            msgs = await core.stormlist('$lib.dict.keys(1)')
            self.stormIsInErr('valu argument must be a dict, not str.', msgs)

            msgs = await core.stormlist('$lib.dict.keys((1))')
            self.stormIsInErr('valu argument must be a dict, not int.', msgs)

            msgs = await core.stormlist('$lib.dict.keys($lib.undef)')
            self.stormIsInErr('valu argument must be a dict, not undef.', msgs)

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

            nodes = await core.nodes('$s = woot [ test:str=$s.rjust(10, x) ]')
            self.eq('xxxxxxwoot', nodes[0].ndef[1])

            nodes = await core.nodes('$s = woot [ test:str=$s.ljust(10) ]')
            self.eq('woot      ', nodes[0].ndef[1])

            nodes = await core.nodes('$s = woot [ test:str=$s.ljust(10, x) ]')
            self.eq('wootxxxxxx', nodes[0].ndef[1])

            sobj = s_stormtypes.Str('beepbeep')
            self.len(8, sobj)

            nodes = await core.nodes('$s = (foo, bar, baz) [ test:str=$lib.str.join(".", $s) ]')
            self.eq('foo.bar.baz', nodes[0].ndef[1])

            nodes = await core.nodes('$s = foo-bar-baz [ test:str=$s.replace("-", ".") ]')
            self.eq('foo.bar.baz', nodes[0].ndef[1])

            nodes = await core.nodes('$s = foo-bar-baz [ test:str=$s.replace("-", ".", 1) ]')
            self.eq('foo.bar-baz', nodes[0].ndef[1])

            q = '$foo=" foo " return ( $foo.strip() )'
            self.eq('foo', await core.callStorm(q))

            q = '$foo=" foo " return ( $foo.lstrip() )'
            self.eq('foo ', await core.callStorm(q))

            q = '$foo=" foo " return ( $foo.rstrip() )'
            self.eq(' foo', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.strip(quxk) )'
            self.eq('ickbrownfo', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.lstrip(quxk) )'
            self.eq('ickbrownfox', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.rstrip(quxk) )'
            self.eq('quickbrownfo', await core.callStorm(q))

            q = '$foo="QuickBrownFox" return ( $foo.lower() )'
            self.eq('quickbrownfox', await core.callStorm(q))

            q = '$foo="QuickBrownFox" return ( $foo.upper() )'
            self.eq('QUICKBROWNFOX', await core.callStorm(q))

            q = '$foo="hello world" return ( $foo.title() )'
            self.eq('Hello World', await core.callStorm(q))

            q = '$foo="hello World" return ( $foo.title() )'
            self.eq('Hello World', await core.callStorm(q))

            q = '$foo="HELLO WORLD!" return ( $foo.title() )'
            self.eq('Hello World!', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.slice(5) )'
            self.eq('brownfox', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.slice(5, 10) )'
            self.eq('brown', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.slice((-8)) )'
            self.eq('brownfox', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.slice(0, (-3)) )'
            self.eq('quickbrown', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.slice(55, 42) )'
            self.eq('', await core.callStorm(q))

            q = '$foo="quickbrownfox" return ( $foo.slice("newp") )'
            await self.asyncraises(s_exc.BadCast, core.callStorm(q))

            q = '$foo="foobar" return ( $foo.reverse() )'
            self.eq('raboof', await core.callStorm(q))

            q = '$foo="hehe {haha} {newp}" return ( $foo.format(haha=yup, baz=faz) )'
            self.eq('hehe yup {newp}', await core.callStorm(q))

            # tuck the regx tests in with str
            self.true(await core.callStorm(r'''return($lib.regex.matches('^foo', foobar))'''))
            self.true(await core.callStorm(r'''return($lib.regex.matches('foo', FOOBAR, $lib.regex.flags.i))'''))
            self.false(await core.callStorm(r'''return($lib.regex.matches('^foo$', foobar))'''))
            self.false(await core.callStorm(f'return($lib.regex.matches(foo, " foobar"))'))

            self.eq(('oo',), await core.callStorm(r'''return($lib.regex.search('([aeiou]+)', foobar))'''))
            self.eq(('foo', 'baz'), await core.callStorm('return($lib.regex.search("(foo)bar(baz)", foobarbaz))'))
            self.eq((), await core.callStorm('return($lib.regex.search(foo, foobar))'))
            self.none(await core.callStorm('return($lib.regex.search(foo, bat))'))

            self.eq(('G0006',), await core.callStorm('return($lib.regex.findall("(G[0-9]{4}) and", "G0006 and G0001"))'))
            self.eq(('G0006', 'G0001'), await core.callStorm('return($lib.regex.findall("G[0-9]{4}", "G0006 and G0001"))'))
            self.eq(('G0006', 'G0001'), await core.callStorm('return($lib.regex.findall("(G[0-9]{4})", "G0006 and G0001"))'))
            valu = await core.callStorm('return($lib.regex.findall("(G[0-9]{4}) (hehe)", "G0006 hehe and G0001 hehe G0009 hoho"))')
            self.eq((('G0006', 'hehe'), ('G0001', 'hehe')), valu)
            self.eq([], await core.callStorm('return($lib.regex.findall("(G[0-9]{4})", "newp G000 newp"))'))

            self.eq(('foo', 'bar', 'baz'), await core.callStorm('$x = "foo,bar,baz" return($x.split(","))'))
            self.eq(('foo', 'bar', 'baz'), await core.callStorm('$x = "foo,bar,baz" return($x.rsplit(","))'))
            self.eq(('foo', 'bar,baz'), await core.callStorm('$x = "foo,bar,baz" return($x.split(",", maxsplit=1))'))
            self.eq(('foo,bar', 'baz'), await core.callStorm('$x = "foo,bar,baz" return($x.rsplit(",", maxsplit=1))'))

            self.eq('foo bar baz faz', await core.callStorm('return($lib.regex.replace("[ ]{2,}", " ", "foo  bar   baz faz"))'))

            self.eq(r'foo\.bar\.baz', await core.callStorm('return($lib.regex.escape("foo.bar.baz"))'))
            self.eq(r'foo\ bar\ baz', await core.callStorm('return($lib.regex.escape("foo bar baz"))'))

            self.eq(((1, 2, 3)), await core.callStorm('return(("[1, 2, 3]").json())'))

            with self.raises(s_exc.BadJsonText):
                await core.callStorm('return(("foo").json())')

            with self.raises(s_exc.BadArg):
                await core.nodes("$lib.regex.search('?id=([0-9]+)', 'foo')")

            with self.raises(s_exc.BadArg):
                await core.nodes("$lib.regex.search('(?au)\\w', 'foo')")

            with self.raises(s_exc.BadArg):
                await core.nodes("$lib.regex.replace('(?P<a>x)', '\\g<ab>', 'xx')")

            with self.raises(s_exc.BadArg):
                await core.nodes("$lib.regex.replace('(?P<a>x)', '(?au)\\w', 'xx')")

    async def test_storm_lib_bytes_gzip(self):
        async with self.getTestCore() as core:
            hstr = 'ohhai'
            ghstr = base64.urlsafe_b64encode((gzip.compress(hstr.encode()))).decode()
            mstr = 'ohgood'
            n2 = s_common.guid()
            n3 = s_common.guid()

            nodes = await core.nodes('[tel:mob:telem="*" :data=$data]', opts={'vars': {'data': ghstr}})
            self.len(1, nodes)
            node1 = nodes[0]

            nodes = await core.nodes('[tel:mob:telem="*" :data=$data]', opts={'vars': {'data': mstr}})
            self.len(1, nodes)
            node2 = nodes[0]
            q = '''tel:mob:telem=$n1 $gzthing = :data
                $foo = $lib.base64.decode($gzthing).gunzip()
                $lib.print($foo)
                [( tel:mob:telem=$n2 :data=$foo.decode() )]'''

            msgs = await core.stormlist(q, opts={'vars': {'n1': node1.ndef[1], 'n2': n2}})
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('ohhai', msgs)

            # make sure we gunzip correctly
            nodes = await core.nodes('tel:mob:telem=$valu', opts={'vars': {'valu': n2}})
            self.len(1, nodes)
            self.eq(hstr, nodes[0].get('data'))

            text = f'''tel:mob:telem=$n2 $bar = :data
                    [( tel:mob:telem=$n3 :data=$lib.base64.encode($bar.encode().gzip()) )]'''
            msgs = await core.stormlist(text, opts={'vars': {'n2': node2.ndef[1], 'n3': n3}})
            self.stormHasNoWarnErr(msgs)

            # make sure we gzip correctly
            nodes = await core.nodes('tel:mob:telem=$valu', opts={'vars': {'valu': n3}})
            self.len(1, nodes)
            self.eq(mstr.encode(), gzip.decompress(base64.urlsafe_b64decode(nodes[0].props['data'])))

    async def test_storm_lib_bytes_bzip(self):
        async with self.getTestCore() as core:
            hstr = 'ohhai'
            ghstr = base64.urlsafe_b64encode((bz2.compress(hstr.encode()))).decode()
            mstr = 'ohgood'
            ggstr = base64.urlsafe_b64encode((bz2.compress(mstr.encode()))).decode()
            n2 = s_common.guid()
            n3 = s_common.guid()

            nodes = await core.nodes('[tel:mob:telem="*" :data=$data]', opts={'vars': {'data': ghstr}})
            self.len(1, nodes)
            node1 = nodes[0]
            nodes = await core.nodes('[tel:mob:telem="*" :data=$data]', opts={'vars': {'data': mstr}})
            self.len(1, nodes)
            node2 = nodes[0]

            q = '''tel:mob:telem=$valu $bzthing = :data $foo = $lib.base64.decode($bzthing).bunzip()
            $lib.print($foo)
            [( tel:mob:telem=$n2 :data=$foo.decode() )] -tel:mob:telem=$valu'''
            msgs = await core.stormlist(q, opts={'vars': {'valu': node1.ndef[1], 'n2': n2}})
            self.stormHasNoWarnErr(msgs)
            self.stormIsInPrint('ohhai', msgs)

            # make sure we bunzip correctly
            opts = {'vars': {'iden': n2}}
            nodes = await core.nodes('tel:mob:telem=$iden', opts=opts)
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('data'), hstr)

            # bzip
            q = '''tel:mob:telem=$valu $bar = :data
                [( tel:mob:telem=$n3 :data=$lib.base64.encode($bar.encode().bzip()) )] -tel:mob:telem=$valu'''
            nodes = await core.nodes(q, opts={'vars': {'valu': node2.ndef[1], 'n3': n3}})
            self.len(1, nodes)
            node = nodes[0]
            self.eq(node.get('data'), ggstr)

    async def test_storm_lib_bytes_json(self):
        async with self.getTestCore() as core:

            foo = {'a': 'ohhai'}
            ghstr = s_json.dumps(foo).decode()
            valu = s_common.guid()
            n2 = s_common.guid()

            nodes = await core.nodes('[tel:mob:telem=$valu :data=$data]', opts={'vars': {'valu': valu, 'data': ghstr}})
            self.len(1, nodes)
            node1 = nodes[0]
            self.eq(node1.get('data'), ghstr)

            q = '''tel:mob:telem=$valu $jzthing=:data $foo=$jzthing.encode().json() [(tel:mob:telem=$n2 :data=$foo)]
                  -tel:mob:telem=$valu'''
            nodes = await core.nodes(q, opts={'vars': {'valu': valu, 'n2': n2}})
            self.len(1, nodes)
            node2 = nodes[0]
            self.eq(node2.get('data'), foo)

            buf = b'\xff\xfe{\x00"\x00k\x00"\x00:\x00 \x00"\x00v\x00"\x00}\x00'
            q = '''return( $buf.json(encoding=$encoding) )'''
            resp = await core.callStorm(q, opts={'vars': {'buf': buf, 'encoding': 'utf-16'}})
            self.eq(resp, {'k': 'v'})

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm(q, opts={'vars': {'buf': buf, 'encoding': 'utf-32'}})

            with self.raises(s_exc.BadJsonText):
                await core.callStorm(q, opts={'vars': {'buf': b'lol{newp,', 'encoding': None}})

    async def test_storm_lib_list(self):
        async with self.getTestCore() as core:
            # Base List object behavior
            q = '''
            $list=(1,2,3)
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
            $elst=()
            $lib.print('elst size is {len}', len=$lib.len($elst))
            '''
            msgs = await core.stormlist(q)
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
            msgs = await core.stormlist(q)
            self.stormIsInWarn('StormType List.length() is deprecated', msgs)

            # Reverse a list
            q = '$v=(foo,bar,baz) $v.reverse() return ($v)'
            ret = await core.callStorm(q)
            self.eq(ret, ('baz', 'bar', 'foo',))

            # sort a list
            q = '$v=(foo,bar,baz) $v.sort() return ($v)'
            ret = await core.callStorm(q)
            self.eq(ret, ('bar', 'baz', 'foo',))

            # incompatible sort types
            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('$v=(foo,bar,(1)) $v.sort() return ($v)')

            q = '$l = (1, 2, (3), 4, 1, (3), 3, asdf) return ( $l.unique() )'
            self.eq(['1', '2', 3, '4', '3', 'asdf'], await core.callStorm(q))

            await core.addUser('lowuser1')
            await core.addUser('lowuser2')
            q = '''
            $a=$lib.auth.users.byname(lowuser1) $b=$lib.auth.users.byname(lowuser2) $r=$lib.auth.users.byname(root)
            $l = ($a, $r, $b, $b, $a ) $l2 = $l.unique() $l3 = ()
            for $user in $l2 {
                $l3.append($user.name)
            }
            return ( $l3 )'''
            self.eq(['lowuser1', 'root', 'lowuser2'], await core.callStorm(q))

            q = '$l=(1, 2, 3, 3, $lib.queue) return ( $lib.len($l.unique()) )'
            self.eq(4, await core.callStorm(q))

            # funcs are different class instances here
            q = '$l = (1, 2, 2, $lib.inet.http.get, $lib.inet.http.get) return ($lib.len($l.unique()))'
            self.eq(4, await core.callStorm(q))

            # funcs are the same class instance
            q = '$hehe = $lib.inet.http $l = (1, 2, 2, $hehe.get, $hehe.get) return ($lib.len($l.unique()))'
            self.eq(3, await core.callStorm(q))

            q = '''
            function foo() {}
            function bar() {}
            $l = ($foo, $bar)
            return ($lib.len($l.unique()))
            '''
            self.eq(2, await core.callStorm(q))

            q = '''
            function foo() {}
            function bar() {}
            $l = ($bar, $foo, $bar)
            return ($lib.len($l.unique()))
            '''
            self.eq(2, await core.callStorm(q))

            q = '''
            $q1 = $lib.queue.gen(hehe)
            $q2 = $lib.queue.get(hehe)
            $l = ($q1, $q2)
            return ( $lib.len($l.unique()) ) '''
            self.eq(1, await core.callStorm(q))

            q = '''
            $q1 = $lib.queue.gen(hehe)
            $q2 = $lib.queue.get(hehe)
            $l = ($q1, $q2, $q2)
            return ( $lib.len($l.unique()) ) '''
            self.eq(1, await core.callStorm(q))

            q = '''
            $q1 = $lib.queue.gen(hehe)
            $q2 = $lib.queue.get(hehe)
            $q3 = $lib.queue.get(hehe)
            $l = ($q1, $q2, $q3)
            return ( $lib.len($l.unique()) ) '''
            self.eq(1, await core.callStorm(q))

            # Python Tuples can be treated like a List object for accessing via data inside of.
            q = '[ test:comp=(10,lol) ] $x=$node.ndef().index(1).index(1) [ test:str=$x ]'
            nodes = await core.nodes(q)
            self.eq(nodes[0].ndef, ('test:str', 'lol'))

            # sad case - index out of bounds.
            q = 'test:comp=(10,lol) $x=$node.ndef().index(2)'
            mesgs = await core.stormlist(q)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][0], 'StormRuntimeError')

            self.eq('bar', await core.callStorm('$foo = (foo, bar) return($foo.1)'))
            self.eq('foo', await core.callStorm('$foo = (foo, bar) return($foo."-2")'))
            self.eq('bar', await core.callStorm('$foo = (foo, bar) return($foo.pop())'))

            self.eq(3, await core.callStorm('$list = ([1, 2, 3, 4]) return($list.pop(2))'))
            self.eq(2, await core.callStorm('$list = ([1, 2, 3, 4]) return($list.pop(-3))'))
            self.eq(4, await core.callStorm('$list = ([1, 2, 3, 4]) $list.pop(2) return($list.pop(2))'))
            self.eq([1, 3, 4], await core.callStorm('$list = ([1, 2, 3, 4]) $list.pop(1) return($list)'))

            with self.raises(s_exc.StormRuntimeError) as exc:
                await core.callStorm('$foo=() $foo.pop()')
            self.eq(exc.exception.get('mesg'), 'pop from empty list')

            with self.raises(s_exc.StormRuntimeError) as exc:
                await core.callStorm('$list = ([1, 2, 3, 4]) return($list.pop(13))')
            self.eq(exc.exception.get('mesg'), 'pop index out of range')

            with self.raises(s_exc.StormRuntimeError) as exc:
                await core.callStorm('$list = ([1, 2, 3, 4]) return($list.pop(-5))')
            self.eq(exc.exception.get('mesg'), 'pop index out of range')

            somelist = ["foo", "bar", "baz", "bar"]
            q = '''
                $l.rem("bar")
                $l.rem("newp")
                return($l)
            '''
            opts = {'vars': {'l': somelist.copy()}}
            out = await core.callStorm(q, opts=opts)
            self.eq(out, ["foo", "baz", "bar"])

            somelist = ["foo", "bar", "baz", "bar"]
            q = '''
                $l.rem("bar", all=$lib.true)
                return($l)
            '''
            opts = {'vars': {'l': somelist.copy()}}
            out = await core.callStorm(q, opts=opts)
            self.eq(out, ["foo", "baz"])

            msgs = await core.stormlist('$list = $lib.list(foo, bar)')
            self.stormIsInWarn('$lib.list() is deprecated. Use ([]) instead.', msgs)

    async def test_storm_layer_getstornode(self):

        async with self.getTestCore() as core:
            visi = await core.auth.addUser('visi')
            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ]')
            opts = {'user': visi.iden, 'vars': {'iden': nodes[0].iden()}}
            sode = await core.callStorm('return($lib.layer.get().getStorNode($iden))', opts=opts)
            self.eq(sode['form'], 'inet:ipv4')
            self.eq(sode['valu'], (0x01020304, 4))

            # check auth deny...
            layriden = await core.callStorm('return($lib.view.get().fork().layers.0.iden)')

            opts = {'user': visi.iden, 'vars': {'layriden': layriden, 'iden': nodes[0].iden()}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.layer.get($layriden).getStorNode($iden))', opts=opts)

            # check perms the old way...
            await visi.addRule((True, ('layer', 'read')), gateiden=layriden)
            await core.callStorm('return($lib.layer.get($layriden).getStorNode($iden))', opts=opts)

    async def test_storm_lib_fire(self):
        async with self.getTestCore() as core:
            text = '$lib.fire(foo:bar, baz=faz)'

            gotn = [mesg for mesg in await core.stormlist(text) if mesg[0] == 'storm:fire']

            self.len(1, gotn)

            self.eq(gotn[0][1]['type'], 'foo:bar')
            self.eq(gotn[0][1]['data']['baz'], 'faz')

            await core.addTagProp('score', ('int', {}), {})

            await core.callStorm('[inet:ipv4=1.2.3.4 +#foo=2021 +#foo:score=9001]')
            q = 'inet:ipv4 $lib.fire(msg:pack, sode=$node.getStorNodes())'
            gotn = [mesg async for mesg in core.storm(q) if mesg[0] == 'storm:fire']
            self.len(1, gotn)
            self.eq(gotn[0][1]['data']['sode'][0]['tagprops'], {'foo': {'score': (9001, 9)}})
            self.eq(gotn[0][1]['type'], 'msg:pack')

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

            mesgs = await core.stormlist('inet:ipv4 $repr=$node.repr(newp)')

            err = mesgs[-2][1]
            self.eq(err[0], 'NoSuchProp')
            self.eq(err[1].get('prop'), 'newp')
            self.eq(err[1].get('form'), 'inet:ipv4')

    async def test_storm_csv(self):
        async with self.getTestCore() as core:
            await core.nodes('[test:str=1234 :tick=2001]')
            await core.nodes('[test:str=9876 :tick=3001]')

            q = "test:str " \
                "$tick=$node.repr(tick) " \
                "$lib.csv.emit($node.form(), $node.value(), $tick, table=mytable)"

            mesgs = await core.stormlist(q, {'show': ('err', 'csv:row')})
            csv_rows = [m for m in mesgs if m[0] == 'csv:row']
            self.len(2, csv_rows)
            csv_rows.sort(key=lambda x: x[1].get('row')[1])
            self.eq(csv_rows[0],
                    ('csv:row', {'row': ['test:str', '1234', '2001/01/01 00:00:00.000'],
                                 'table': 'mytable'}))
            self.eq(csv_rows[1],
                    ('csv:row', {'row': ['test:str', '9876', '3001/01/01 00:00:00.000'],
                                 'table': 'mytable'}))

            q = 'test:str $hehe=$node.props.hehe $lib.csv.emit(:tick, $hehe)'
            mesgs = await core.stormlist(q, {'show': ('err', 'csv:row')})
            csv_rows = [m for m in mesgs if m[0] == 'csv:row']
            self.len(2, csv_rows)
            self.eq(csv_rows[0], ('csv:row', {'row': [978307200000, None], 'table': None}))
            self.eq(csv_rows[1], ('csv:row', {'row': [32535216000000, None], 'table': None}))

            # Sad path case...
            q = '''
                [ test:str=woot ]
                $lib.csv.emit($path)
            '''
            mesgs = await core.stormlist(q, {'show': ('err', 'csv:row')})
            err = mesgs[-2]
            self.eq(err[1][0], 'NoSuchType')

    async def test_storm_text(self):
        async with self.getTestCore() as core:
            # $lib.text() is deprecated (SYN-8482); test ensures the object works as expected until removed
            nodes = await core.nodes('''
                [ test:int=10 ] $text=$lib.text(hehe) { +test:int>=10 $text.add(haha) }
                [ test:str=$text.str() ] +test:str''')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'hehehaha'))

            q = '''$t=$lib.text(beepboop) $lib.print($lib.len($t))
            $t.add("more!") $lib.print($lib.len($t))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('8', msgs)
            self.stormIsInPrint('13', msgs)

            msgs = await core.stormlist('help --verbose $lib.text')
            self.stormIsInPrint('Warning', msgs)
            self.stormIsInPrint('$lib.text`` has been deprecated and will be removed in version 3.0.0', msgs)

    async def test_storm_set(self):

        async with self.getTestCore() as core:

            await core.nodes('[inet:ipv4=1.2.3.4 :asn=20]')
            await core.nodes('[inet:ipv4=5.6.7.8 :asn=30]')

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.add(:asn)
                [ tel:mob:telem="*" ] +tel:mob:telem [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), (20, 30))

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.adds((:asn,:asn))
                [ tel:mob:telem="*" ] +tel:mob:telem [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), (20, 30))

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.adds((:asn,:asn))
                { +:asn=20 $set.rem(:asn) }
                [ tel:mob:telem="*" ] +tel:mob:telem [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), (30,))

            q = '''
                $set = $lib.set()
                inet:ipv4 $set.add(:asn)
                $set.rems((:asn,:asn))
                [ tel:mob:telem="*" ] +tel:mob:telem [ :data=$set.list() ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(tuple(sorted(nodes[0].get('data'))), ())

            q = '$set = $lib.set(a, b, c, b, a) [test:int=$set.size()]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:int', 3))

            q = '''$set = $lib.set(a, b, c)
            for $v in $set {
                $lib.print('set valu: {v}', v=$v)
            }
            '''
            mesgs = await core.stormlist(q)
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

            # test that some of the more complex objects we've got uniq down properly
            # Bool
            q = '''
                $set = $lib.set()
                $set.add($true)
                $set.add($true)
                $set.add($true)
                $set.add($false)
                $set.add($false)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            trueprim = s_stormtypes.Bool(True)
            falsprim = s_stormtypes.Bool(False)
            msgs = await core.stormlist(q, opts={'vars': {'true': trueprim, 'false': falsprim}})
            self.stormIsInPrint('There are 2 items in the set', msgs)

            # bytes
            q = '''
                $set = $lib.set()
                $set.add($norun)
                $set.add($norun)
                $set.add($section)
                $set.add($section)
                $set.add($section)
                $set.add($copy)
                $set.add($bare)
                $set.add($bare)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            norun = s_stormtypes.Bytes(b'This program cannot be run')
            section = s_stormtypes.Bytes(b'.text')
            copy = s_stormtypes.Bytes(b'.text')
            bare = b'.text'
            msgs = await core.stormlist(q, opts={'vars': {'norun': norun, 'section': section, 'copy': copy, 'bare': bare}})
            self.stormIsInPrint('There are 3 items in the set', msgs)

            # cmdopts
            q = '''
                $set = $lib.set()
                $set.add($opts)
                $set.add($othr)
                $set.add($diff)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''

            class OptWrapper:
                def __init__(self, argv):
                    self.pars = s_storm.Parser(prog='test', descr='for set testing')
                    self.pars.add_argument('--foo', action='store_true')
                    self.pars.add_argument('--bar', action='store_false')
                    self.pars.add_argument('--lol', action='store_true')
                    self.pars.add_argument('--nope', action='store_true')

                    self.opts = self.pars.parse_args(argv)

                def __eq__(self, othr):
                    return self.opts == othr.opts

            opts = s_stormtypes.CmdOpts(OptWrapper(['--foo', '--bar']))
            othr = s_stormtypes.CmdOpts(OptWrapper(['--foo', '--bar']))
            diff = s_stormtypes.CmdOpts(OptWrapper(['--lol', '--nope']))
            msgs = await core.stormlist(q, opts={'vars': {'opts': opts, 'othr': othr, 'diff': diff}})
            self.stormIsInPrint('There are 2 items in the set', msgs)
            self.ne(diff, copy)
            self.ne(copy, diff)

            # cron and others uniq by iden
            q = '''
                $set = $lib.set()
                $jobA = $lib.cron.add(query=${[test:int=1]}, hourly=10)
                $jobB = $lib.cron.add(query=${[test:int=1]}, hourly=10)

                $set.add($jobA)
                $set.add($jobB)

                $set.add($jobA)
                $set.add($jobB)

                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 2 items in the set', msgs)

            # gate
            q = '''
                $set = $lib.set()
                $gate = $lib.auth.gates.get($lib.view.get().iden)
                $set.add($gate)
                $set.add($gate)
                $set.add($lib.auth.gates.get($lib.view.get().iden))
                $set.add($lib.auth.gates.get($lib.view.get().iden))

                $layr = $lib.layer.add().iden
                $newview = $lib.view.add(($layr,))
                $set.add($lib.auth.gates.get($newview.iden))
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 2 items in the set', msgs)

            # layer
            q = '''
                init {
                    $extra = $lib.layer.add()
                    $fake = $lib.layer.add()
                }
                $layr = $lib.layer.get()
                $set = $lib.set()
                $set.add($lib.layer.get())
                $set.add($lib.layer.get())
                $set.add($extra)
                $set.add($fake)
                $set.add($fake)
                $set.add($extra)
                $set.add($layr)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 3 items in the set', msgs)

            # node
            q = '''
                init {
                    $set = $lib.set()
                }
                inet:ipv4

                $set.add($node)
                $set.add($node)
                fini {
                    $lib.print('There are {count} items in the set', count=$lib.len($set))
                }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 2 items in the set', msgs)

            # queue
            q = '''
                $orig = $lib.queue.add(testq)
                $set = $lib.set()
                $set.add($orig)
                $set.add($lib.queue.get(testq))
                $set.add($lib.queue.get(testq))
                $set.add($lib.queue.get(testq))
                $lib.print('There is {count} item in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There is 1 item in the set', msgs)

            # role
            q = '''
                $role = $lib.auth.roles.add(muffin)
                $set = $lib.set()
                $set.add($role)
                $set.add($lib.auth.roles.byname(muffin))
                $set.add($role)
                $lib.print('There is {count} item in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There is 1 item in the set', msgs)

            # str
            q = '''
                $set = $lib.set()
                $set.add(23)
                $set.add("alpha")
                $set.add("alpha")
                $set.add($alpha)

                $set.add($beta)
                $set.add("beta")

                $set.add("delta")
                $set.add($delta)

                $set.add($copy)
                $set.add($copy)
                $set.add(47)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            alpha = s_stormtypes.Str('alpha')
            beta = s_stormtypes.Str('beta')
            delta = s_stormtypes.Str('delta')
            copy = s_stormtypes.Str('delta')
            msgs = await core.stormlist(q, opts={'vars': {'alpha': alpha, 'beta': beta, 'delta': delta, 'copy': copy}})
            self.stormIsInPrint('There are 8 items in the set', msgs)
            self.ne(alpha, section)

            # trigger
            q = '''
                $trig = $lib.trigger.add($tdef)
                $set = $lib.set()
                $set.adds(($trig, $trig, $trig, $trig))
                $lib.print('There is {count} item in the set', count=$lib.len($set))
            '''
            iden = s_common.guid()
            tdef = {'iden': iden, 'cond': 'node:add', 'storm': '[ test:str=foo ]', 'form': 'test:str'}
            msgs = await core.stormlist(q, opts={'vars': {'tdef': tdef}})
            self.stormIsInPrint('There is 1 item in the set', msgs)
            self.nn(await core.view.getTrigger(iden))

            # user
            q = '''
                $u = $lib.auth.users.add(bar)
                $lib.set($u)
                $set = $lib.set($u)
                $set.add($lib.auth.users.byname(bar))
                $set.add($lib.auth.users.byname(bar))
                $lib.print('There is {count} item in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There is 1 item in the set', msgs)

            # view
            q = '''
                $view = $lib.view.get()
                $set = $lib.set($view)
                $set.add($lib.view.get())
                $set.add($lib.view.get())

                $layr = $lib.layer.add().iden
                $newview = $lib.view.add(($layr,))
                $set.add($newview)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 2 items in the set', msgs)

            # Dict
            q = '''
                $dict = ({
                    "foo": "bar",
                    "biz": "baz",
                })
                $set = $lib.set($dict)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            q = '''
                $dict = ({
                    "foo": "bar",
                    "biz": "baz",
                })
                $set = $lib.set()
                $set.adds($dict)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 2 items in the set', msgs)

            # List
            q = '''
                $list = (1, 2, 3)
                $set = $lib.set($list)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            q = '''
                $list = (1, 2, 3, 1, 2, 3, 1, 2, 3)
                $set = $lib.set()
                $set.adds($list)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 3 items in the set', msgs)

            q = '''
                $list = ((4, 5, 6, 7), (1, 2, 3, 4))
                $set = $lib.set()
                $set.adds($list)
                $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            # Set
            q = '''
                $setA = $lib.set(1, 1, 2, 2, 3)
                $setB = $lib.set($setA)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            q = '''
                $setA = $lib.set(1, 1, 2, 2, 3)
                $setB = $lib.set()

                $setB.adds($setA)
                $lib.print('There are {count} items in the set', count=$lib.len($setB))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 3 items in the set', msgs)

            # path
            q = '''
                inet:ipv4
                $set = $lib.set()
                $set.add($path)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            # PathMeta
            q = '''
                inet:ipv4
                $set = $lib.set()
                $meta = $path.meta
                $set.add($meta)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            # pathvars
            q = '''
                inet:ipv4
                $set = $lib.set()
                $vars = $path.vars
                $set.add($vars)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            # text
            q = '''
                $text = () $text.append(beepboopgetthejedi)
                $set = $lib.set($text)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            # stattally
            q = '''
                $tally = $lib.stats.tally()
                $tally.inc(foo)
                $set = $lib.set($tally)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInErr('is mutable and cannot be used in a set', msgs)

            # mix
            q = '''
            $user = $lib.auth.users.add(foo)
            $list = (1, 1, 'a', $user, $user, $lib.view.get(), $lib.view.get(), $lib.queue.add(neatq), $lib.queue.get(neatq), $lib.false)
            $set = $lib.set()
            $set.adds($list)
            $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 6 items in the set', msgs)

            q = '''
            $list = (
                1, 2, 3, 4,
                (2), (3), (4), (5),
                (3.0), (4.0), (5.0), (6.0),
                $lib.cast(float, 4), $lib.cast(float, 5), $lib.cast(float, 6), $lib.cast(float, 7)
            )
            $set = $lib.set()
            $set.adds($list)
            $lib.print('There are {count} items in the set', count=$lib.len($set))
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint('There are 13 items in the set', msgs)

    async def test_storm_path(self):
        async with self.getTestCore() as core:
            await core.nodes('[ inet:dns:a=(vertex.link, 1.2.3.4) ]')
            q = '''
                inet:fqdn=vertex.link -> inet:dns:a -> inet:ipv4
                $idens = $path.idens()
                [ tel:mob:telem="*" ] +tel:mob:telem [ :data=$idens ]
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
            mesgs = await core.stormlist(text)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('No var with name: testkey', err[1].get('mesg'))

            opts = {'vars': {'testkey': 'testvar'}}
            text = "[ test:str='123' ] $path.vars.$testkey = test [ test:str=$path.vars.testvar ]"
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
            msgs = await core.stormlist(text, opts=opts)

            self.stormIsInPrint('testvar=test', msgs)
            self.stormIsInPrint('testkey=testvar', msgs)

            async with core.getLocalProxy() as proxy:
                msgs = await proxy.storm('''
                    [ ps:contact=* ]
                    $path.meta.foo = bar
                    $path.meta.baz = faz
                    $path.meta.baz = $lib.undef
                    $path.meta.biz = ('neato', 'burrito')
                    {
                        for ($name, $valu) in $path.meta {
                            $lib.print('meta: {name}={valu}', name=$name, valu=$valu)
                        }
                    }
                    if $path.meta.foo { $lib.print(foofoofoo) }
                ''').list()
                self.stormIsInPrint('foofoofoo', msgs)
                self.stormIsInPrint('meta: foo=bar', msgs)
                self.stormIsInPrint("meta: biz=['neato', 'burrito']", msgs)
                pode = [m[1] for m in msgs if m[0] == 'node'][0]
                self.len(2, pode[1]['path'])
                self.eq('bar', pode[1]['path']['foo'])

                q = '''
                inet:fqdn=vertex.link
                $path.meta.foobar = ('neato', 'burrito')
                '''
                msgs = [mesg async for mesg in proxy.storm(q)]
                pode = [m[1] for m in msgs if m[0] == 'node'][0]
                self.eq(pode[1]['path'], {'foobar': ('neato', 'burrito')})

                q = '''
                inet:fqdn=vertex.link
                $path.meta.wat = ({"foo": "bar", "biz": "baz", "thing": ({"1": "2", "2": ["a", "b", "c"], "five": "nine"}) })
                $path.meta.neato = (awesome, burrito)
                '''
                msgs = [mesg async for mesg in proxy.storm(q)]
                pode = [m[1] for m in msgs if m[0] == 'node'][0]
                path = pode[1]['path']
                self.eq(('awesome', 'burrito'), path['neato'])
                self.eq('bar', path['wat']['foo'])
                self.eq('baz', path['wat']['biz'])
                self.eq('nine', path['wat']['thing']['five'])
                self.eq('2', path['wat']['thing']['1'])
                self.eq(('a', 'b', 'c'), path['wat']['thing']['2'])

                q = '''
                inet:fqdn=vertex.link
                $path.meta.$node = ('foo', 'bar')
                '''
                msgs = [mesg async for mesg in proxy.storm(q)]
                pode = [m[1] for m in msgs if m[0] == 'node'][0]
                path = pode[1]['path']
                self.len(1, path)
                key = list(path.keys())[0]
                self.true(key.startswith('vertex.link'))
                self.eq(('foo', 'bar'), path[key])

                q = '''
                inet:fqdn=vertex.link
                $test = ({"foo": "bar"})
                $path.meta.data = $test
                $test.biz = baz
                '''
                msgs = [mesg async for mesg in proxy.storm(q)]
                pode = [m[1] for m in msgs if m[0] == 'node'][0]
                path = pode[1]['path']
                self.len(1, path)
                self.len(2, path['data'])
                self.eq('bar', path['data']['foo'])
                self.eq('baz', path['data']['biz'])

    async def test_stormuser(self):
        # Do not include persistent vars support in this test see
        # test_persistent_vars for that behavior.
        async with self.getTestCore() as core:
            q = '$lib.print($lib.user.name())'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('root', mesgs)
            self.eq(core.auth.rootuser.iden, await core.callStorm('return($lib.user.iden)'))

            msgs = await core.stormlist('$lib.print($lib.auth.users.list().0)')
            self.stormIsInPrint('auth:user', msgs)
            self.stormIsInPrint("'name': 'root'", msgs)

            await core.stormlist('auth.user.add visi')

            visi = await core.auth.getUserByName('visi')
            opts = {'user': visi.iden}
            self.true(await core.callStorm('return($lib.user.allowed(foo.bar, default=$lib.true))', opts=opts))
            self.false(await core.callStorm('return($lib.user.allowed(foo.bar, default=$lib.false))', opts=opts))

    async def test_persistent_vars(self):
        with self.getTestDir() as dirn:
            async with self.getTestCore(dirn=dirn) as core:
                async with core.getLocalProxy() as prox:
                    # User setup for $lib.user.vars() tests

                    ret1 = await prox.addUser('user1', passwd='secret')
                    iden1 = ret1.get('iden')

                    await prox.addUserRule(iden1, (True, ('node', 'add')))
                    await prox.addUserRule(iden1, (True, ('node', 'prop', 'set')))
                    await prox.addUserRule(iden1, (True, ('globals', 'get', 'userkey',)))

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

                    q = '''$x=({"foo": "1"})
                    $lib.globals.set(bar, $x)
                    $y=$lib.globals.get(bar)
                    $lib.print("valu={v}", v=$y.foo)
                    '''
                    mesgs = await s_test.alist(prox.storm(q))
                    self.stormIsInPrint('valu=1', mesgs)

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
                    self.len(3 + 1, [m for m in mesgs if m[0] == 'print'])
                    self.stormIsInPrint('adminkey is sekrit', mesgs)
                    self.stormIsInPrint('userkey is lessThanSekrit', mesgs)

                    # Storing a valu into the hive gets toprim()'d
                    q = '[test:str=test] $lib.user.vars.set(mynode, $node) return($lib.user.vars.get(mynode))'
                    data = await prox.callStorm(q)
                    self.eq(data, 'test')

                    # Sad path - names must be strings.
                    q = '$lib.globals.set((my, nested, valu), haha)'
                    mesgs = await prox.storm(q).list()
                    err = 'The name of a persistent variable must be a string.'
                    self.stormIsInErr(err, mesgs)

                    # Sad path - names must be strings.
                    q = '$lib.globals.set((my, nested, valu), haha)'
                    mesgs = await prox.storm(q).list()
                    err = 'The name of a persistent variable must be a string.'
                    self.stormIsInErr(err, mesgs)

                async with core.getLocalProxy() as uprox:
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
                    # that they have access to but not the admin key
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
                async with core.getLocalProxy() as uprox:
                    self.true(await uprox.setCellUser(iden1))

                    mesgs = await uprox.storm(listq).list()
                    self.len(1, [m for m in mesgs if m[0] == 'print'])
                    self.stormIsInPrint('somekey is hehe', mesgs)

                    q = '''$valu=$lib.globals.get(userkey)
                    $lib.print($valu)
                    '''
                    mesgs = await uprox.storm(q).list()
                    self.stormIsInPrint('lessThanSekrit', mesgs)

                    # The StormHiveDict is safe when computing things
                    q = '''[test:int=1234]
                    $lib.user.vars.set(someint, $node.value())
                    [test:str=$lib.user.vars.get(someint)]
                    '''
                    mesgs = await uprox.storm(q).list()
                    podes = [m[1] for m in mesgs if m[0] == 'node']
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

            query = '''$valu="10/1/2017 1:22-01:30"
            $parsed=$lib.time.parse($valu, "%m/%d/%Y %H:%M%z")
            [test:int=$parsed]
            '''
            nodes = await core.nodes(query)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[1], 1506826320000)

            query = '''$valu="10/1/2017 3:52+01:00"
            $parsed=$lib.time.parse($valu, "%m/%d/%Y %H:%M%z")
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
            mesgs = await core.stormlist(query)
            ernfos = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, ernfos)
            self.isin('Error during time parsing', ernfos[0][1].get('mesg'))

            # We can optionally suppress that if error we want to do so and then
            # we can compare the return value against $lib.null if we wanted to
            # do any flow control based on that information.
            query = '''$valu="10/1/2017 2:52"
            $parsed=$lib.time.parse($valu, "%m/%d/%Y--%H:%MTZ", errok=$lib.true)
            return ($parsed)'''
            ret = await core.callStorm(query)
            self.none(ret)

            self.none(await core.callStorm('return($lib.time.parse($lib.true, "%m/%d/%Y", errok=$lib.true))'))

            query = '''[test:str=1234 :tick=20190917]
            $lib.print($lib.time.format(:tick, "%Y-%d-%m"))
            '''
            mesgs = await core.stormlist(query)
            self.stormIsInPrint('2019-17-09', mesgs)

            # Strs can be parsed using time norm routine.
            query = '''$valu=$lib.time.format('200103040516', '%Y %m %d')
            $lib.print($valu)
            '''
            mesgs = await core.stormlist(query)
            self.stormIsInPrint('2001 03 04', mesgs)

            # Out of bounds case for datetime
            query = '''[test:int=253402300800000]
            $valu=$lib.time.format($node.value(), '%Y')'''
            mesgs = await core.stormlist(query)
            ernfos = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, ernfos)
            self.isin('Failed to norm a time value prior to formatting', ernfos[0][1].get('mesg'))

            # Cant format ? times
            query = '$valu=$lib.time.format("?", "%Y")'
            mesgs = await core.stormlist(query)
            ernfos = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, ernfos)
            self.isin('Cannot format a timestamp for ongoing/future time.', ernfos[0][1].get('mesg'))

            # strftime fail - taken from
            # https://github.com/python/cpython/blob/3.7/Lib/test/datetimetester.py#L1404
            query = r'''[test:str=1234 :tick=20190917]
            $lib.print($lib.time.format(:tick, "%y\ud800%m"))
            '''
            mesgs = await core.stormlist(query)
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

            # Get time parts
            self.eq(2021, await core.callStorm('return($lib.time.year(20211031020304))'))
            self.eq(10, await core.callStorm('return($lib.time.month(20211031020304))'))
            self.eq(31, await core.callStorm('return($lib.time.day(20211031020304))'))
            self.eq(2, await core.callStorm('return($lib.time.hour(20211031020304))'))
            self.eq(3, await core.callStorm('return($lib.time.minute(20211031020304))'))
            self.eq(4, await core.callStorm('return($lib.time.second(20211031020304))'))
            self.eq(6, await core.callStorm('return($lib.time.dayofweek(20211031020304))'))
            self.eq(303, await core.callStorm('return($lib.time.dayofyear(20211031020304))'))
            self.eq(30, await core.callStorm('return($lib.time.dayofmonth(20211031020304))'))
            self.eq(9, await core.callStorm('return($lib.time.monthofyear(20211031020304))'))

            tick = s_time.parse('2020-02-11 14:08:00.123')
            valu = await core.callStorm('return($lib.time.toUTC(2020-02-11@14:08:00.123, EST))')
            self.eq(valu, (True, tick + (s_time.onehour * 5)))

            valu = await core.callStorm('return($lib.time.toUTC(2020, VISI))')
            self.false(valu[0])
            self.eq(valu[1]['err'], 'BadArg')

    async def test_storm_lib_time_ticker(self):

        async with self.getTestCore() as core:
            iden = s_common.guid()
            await core.nodes('''
                $lib.queue.add(visi)
                $lib.dmon.add(${
                    $visi=$lib.queue.get(visi)
                    for $tick in $lib.time.ticker(0.01) {
                        $visi.put($tick)
                    }
                }, ddef=({"iden": $iden}))
            ''', opts={'vars': {'iden': iden}})
            nodes = await core.nodes('for ($offs, $tick) in $lib.queue.get(visi).gets(size=3) { [test:int=$tick] } ')
            self.len(3, nodes)
            self.eq({0, 1, 2}, {node.ndef[1] for node in nodes})
            self.nn(await core.getStormDmon(iden))

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

    async def test_stormtypes_telepath(self):

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

            varz = {'url': lurl}
            opts = {'vars': varz}

            q = '[ inet:ipv4=1.2.3.4 :asn=20 ] $asn = $lib.telepath.open($url).doit(:asn) [ :asn=$asn ]'
            nodes = await core.nodes(q, opts=opts)
            self.eq(40, nodes[0].props['asn'])

            nodes = await core.nodes('for $fqdn in $lib.telepath.open($url).fqdns() { [ inet:fqdn=$fqdn ] }', opts=opts)
            self.len(2, nodes)

            nodes = await core.nodes('for $ipv4 in $lib.telepath.open($url).ipv4s() { [ inet:ipv4=$ipv4 ] }', opts=opts)
            self.len(2, nodes)

            with self.raises(s_exc.NoSuchName):
                await core.nodes('$lib.telepath.open($url)._newp()', opts=opts)

            mesgs = await core.stormlist('$lib.print($lib.telepath.open($url))', opts=opts)
            self.stormIsInPrint("telepath:proxy: <synapse.telepath.Proxy object", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.telepath.open($url).doit)', opts=opts)
            self.stormIsInPrint("telepath:proxy:method: <synapse.telepath.Method", mesgs)

            mesgs = await core.stormlist('$lib.print($lib.telepath.open($url).fqdns)', opts=opts)
            self.stormIsInPrint("telepath:proxy:genrmethod: <synapse.telepath.GenrMethod", mesgs)

            unfo = await core.addUser('lowuesr')
            user = unfo.get('iden')

            opts = {'user': user, 'vars': varz}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return ( $lib.telepath.open($url).ipv4s() )', opts=opts)
            await core.addUserRule(user, (True, ('storm', 'lib', 'telepath', 'open', 'cell')))
            self.len(2, await core.callStorm('return ( $lib.telepath.open($url).ipv4s() )', opts=opts))

            # SynErr exceptions are allowed through. They can be caught by storm.
            with self.raises(s_exc.BadUrl):
                await core.callStorm('$prox=$lib.telepath.open("weeeeeeeeeeeeee")')

            # Python exceptions are caught and raised as StormRuntimeError exceptions.
            with self.raises(s_exc.StormRuntimeError) as cm:
                await core.callStorm('$prox=$lib.telepath.open("tcp://0.0.0.0:60000")')
            emsg = cm.exception.get('mesg')
            self.isin('Failed to connect to Telepath service: "tcp://0.0.0.0:60000" error:', emsg)
            self.isin('Connect call failed', emsg)

    async def test_storm_lib_queue(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('queue.add visi')
            self.stormIsInPrint('queue added: visi', msgs)

            with self.raises(s_exc.DupName):
                await core.nodes('queue.add visi')

            msgs = await core.stormlist('queue.list')
            self.stormIsInPrint('Storm queue list:', msgs)
            self.stormIsInPrint('visi', msgs)

            name = await core.callStorm('$q = $lib.queue.get(visi) return ($q.name)')
            self.eq(name, 'visi')

            nodes = await core.nodes('$q = $lib.queue.get(visi) [ inet:ipv4=1.2.3.4 ] $q.put( $node.repr() )')
            nodes = await core.nodes('$q = $lib.queue.get(visi) ($offs, $ipv4) = $q.get(0) inet:ipv4=$ipv4')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('inet:ipv4', 0x01020304))

            # test iter use case
            q = '$q = $lib.queue.add(blah) [ inet:ipv4=1.2.3.4 inet:ipv4=5.5.5.5 ] $q.put( $node.repr() )'
            nodes = await core.nodes(q)
            self.len(2, nodes)

            # Put a value into the queue that doesn't exist in the cortex so the lift can nop
            await core.nodes('$q = $lib.queue.get(blah) $q.put("8.8.8.8")')

            nodes = await core.nodes('''
                $q = $lib.queue.get(blah)
                for ($offs, $ipv4) in $q.gets(0, wait=0) {
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

            q = '$q = $lib.queue.get(blah) for ($offs, $ipv4) in $q.gets(wait=0) { inet:ipv4=$ipv4 }'
            nodes = await core.nodes(q)
            self.len(0, nodes)

            msgs = await core.stormlist('queue.del visi')
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

            q = '$item = $lib.queue.get(doit).get(offs=1) [test:str=$item.0]'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            q = 'for ($offs, $name) in $lib.queue.get(doit).gets(size=1, offs=1) { [test:str=$name] }'
            nodes = await core.nodes(q)
            self.len(1, nodes)

            # test other users who have access to this queue can do things to it
            async with core.getLocalProxy() as root:
                # add users
                await root.addUser('synapse')
                await root.addUser('wootuser')

                synu = await core.auth.getUserByName('synapse')
                woot = await core.auth.getUserByName('wootuser')

                # make a queue
                with self.raises(s_exc.AuthDeny):
                    opts = {'user': synu.iden}
                    await core.nodes('queue.add synq', opts=opts)

                rule = (True, ('queue', 'add'))
                await root.addUserRule(synu.iden, rule, indx=None)
                opts = {'user': synu.iden}
                msgs = await core.stormlist('queue.add synq', opts=opts)
                self.stormIsInPrint('queue added: synq', msgs)

                rule = (True, ('queue', 'synq', 'put'))
                await root.addUserRule(synu.iden, rule, indx=None)

                opts = {'user': synu.iden}
                await core.nodes('$q = $lib.queue.get(synq) $q.puts((bar, baz))', opts=opts)

                # now let's see our other user fail to add things
                with self.raises(s_exc.AuthDeny):
                    opts = {'user': woot.iden}
                    await core.nodes('$lib.queue.get(synq).get()', opts=opts)

                rule = (True, ('queue', 'synq', 'get'))
                await root.addUserRule(woot.iden, rule, indx=None)

                msgs = await core.stormlist('$lib.print($lib.queue.get(synq).get(wait=0))')
                self.stormIsInPrint("(0, 'bar')", msgs)

                with self.raises(s_exc.AuthDeny):
                    opts = {'user': woot.iden}
                    await core.nodes('$lib.queue.del(synq)', opts=opts)

                rule = (True, ('queue', 'del'))
                await root.addUserRule(woot.iden, rule, indx=None, gateiden='queue:synq')

                opts = {'user': woot.iden}
                await core.nodes('$lib.queue.del(synq)', opts=opts)

                with self.raises(s_exc.NoSuchName):
                    await core.nodes('$lib.queue.get(synq)')

                await core.callStorm('$lib.queue.gen(poptest).puts((foo, bar, baz))')
                self.eq('poptest', await core.callStorm('return($lib.queue.get(poptest).name)'))
                self.eq((0, 'foo'), await core.callStorm('return($lib.queue.get(poptest).pop(0))'))
                self.eq((1, 'bar'), await core.callStorm('return($lib.queue.get(poptest).pop(1))'))
                self.eq((2, 'baz'), await core.callStorm('return($lib.queue.get(poptest).pop(2))'))
                self.none(await core.callStorm('return($lib.queue.get(poptest).pop(2))'))
                self.none(await core.callStorm('return($lib.queue.get(poptest).pop())'))
                # Repopulate the queue, we now have data in index 3, 4, and 5
                await core.callStorm('$lib.queue.gen(poptest).puts((foo, bar, baz))')
                # Out of order pop() with a index does not cull.
                self.eq((4, 'bar'), await core.callStorm('return($lib.queue.get(poptest).pop(4))'))
                self.eq((3, 'foo'), await core.callStorm('return($lib.queue.get(poptest).pop())'))
                self.eq((5, 'baz'), await core.callStorm('return($lib.queue.get(poptest).pop())'))
                self.none(await core.callStorm('return($lib.queue.get(poptest).pop())'))

    async def test_storm_node_data(self):

        async with self.getTestCore() as core:
            stormpkg = {
                'name': 'nodedatatest',
                'version': (0, 0, 1),
                'commands': (
                    {
                     'name': 'nd.permtest',
                     'storm': '$node.data.get(foo:bar)',
                    },
                ),
            }

            await core.addStormPkg(stormpkg)

            nodes = await core.nodes('[test:int=10] $node.data.set(foo, hehe)')

            self.len(1, nodes)
            self.eq(await nodes[0].getData('foo'), 'hehe')

            nodes = await core.nodes('test:int $foo=$node.data.get(foo) [ test:str=$foo ] +test:str')
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'hehe'))

            q = 'test:int for ($name, $valu) in $node.data.list() { [ test:str=$name ] } +test:str'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'foo'))

            # list() exposes data from all layers from top-down
            fork = await core.callStorm('return ( $lib.view.get().fork().iden )')
            await core.nodes('test:int=10 $node.data.set(bar, newp)')
            await core.nodes('test:int=10 $node.data.set(bar, baz)', opts={'view': fork})
            data = await core.callStorm('test:int=10 return( $node.data.list() )', opts={'view': fork})
            self.eq(data, (('bar', 'baz'), ('foo', 'hehe')))

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

            visi = await core.auth.addUser('visi')
            async with core.getLocalProxy(user='visi') as asvisi:
                self.eq(None, await asvisi.callStorm('test:int return($node.data.get(foo))'))

            await visi.addRule((True, ('view', 'add')))

            asvisi = {'user': visi.iden}
            view = await core.callStorm('return($lib.view.get().fork().iden)', opts=asvisi)

            asvisi['view'] = view
            layr = core.getView(view).layers[0]
            await visi.addRule((True, ('node',)), gateiden=layr.iden)
            await core.nodes('[ inet:ipv4=1.2.3.4 ] $node.data.set(woot, (10))', opts=asvisi)

            # test interaction between LibLift and setting node data
            q = '''
            for $i in $lib.range((10)) {
                [test:int=$i]
                $node.data.set(laststatus, "start")
            }
            '''
            await core.callStorm(q)
            q = '''
            for $work in $lib.lift.byNodeData(laststatus) {
                if ($work.value() > 5) {
                    $work.data.set(laststatus, "running")
                } else {
                    $work.data.set(laststatus, "done")
                }
                $status = $work.data.get(laststatus)
                $lib.print("#{valu} status is {status}", valu=$work.value(), status=$status)
            }
            '''
            msgs = await core.stormlist(q)
            for i in range(10):
                if i > 5:
                    self.stormIsInPrint(f'#{i} status is running', msgs)
                else:
                    self.stormIsInPrint(f'#{i} status is done', msgs)

            q = '''
            for $work in $lib.lift.byNodeData(laststatus) {
                if ($work.value() = 5) {
                    $work.data.pop(laststatus)
                    $status = $work.data.get(laststatus)
                    $lib.print("#{value} work status is {status}", value=$work.value(), status=$status)
                } else {
                    $status = $work.data.get(laststatus)
                    $lib.print("#{value} is still {status}", value=$work.value(), status=$status)
                }
            }
            '''
            msgs = await core.stormlist(q)
            prints = [x for x in msgs if x[0] == 'print']
            self.len(10, prints)
            self.stormIsInPrint("#5 work status is $lib.null", msgs)

            # has
            q = '''
            [ test:int=10 ]
            $node.data.set(data:key, $lib.false)
            if $node.data.has(lol:nope) {
                $lib.print("But How?")
            } else {
                $lib.print("Working")
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("Working", msgs)

            q = '''
            [ test:int=27 ]
            $node.data.set(data:key, $lib.null)
            if $node.data.has(data:key) {
                $lib.print("Working")
            } else {
                $lib.print("Failure")
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("Working", msgs)

            q = '''
            test:int=27
            if ($node.data.has(data:key) = $lib.true) {
                $lib.print("Working")
            } else {
                $lib.print("Failure")
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("Working", msgs)

            q = '''
            test:int=10
            if ($node.data.has(lol:nope) = $lib.false) {
                $lib.print("Working")
            } else {
                $lib.print("Failure")
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("Working", msgs)

            q = '''
            $count = (0)
            for $int in $lib.lift.byNodeData(lol:nope) {
                $count = ($count + 1)
            }
            $lib.print("Count: {c}", c=$count)
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("Count: 0", msgs)

            q = '[test:int=127] $node.data.set(neato:key, $lib.false)'
            await core.nodes(q)
            q = '''
            test:int=127
            if ($node.data.has(neato:key) = $lib.true) {
                $lib.print("Working")
            } else {
                $lib.print("Failure")
            }
            '''
            msgs = await core.stormlist(q)
            self.stormIsInPrint("Working", msgs)

    async def test_storm_lib_bytes(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'bytes': 10}}

            with self.raises(s_exc.BadArg):
                text = '($size, $sha2) = $lib.bytes.put($bytes)'
                nodes = await core.nodes(text, opts=opts)

            with self.raises(s_exc.BadArg):
                text = '($size, $sha2) = $lib.axon.put($bytes)'
                nodes = await core.nodes(text, opts=opts)

            asdf = b'asdfasdf'
            asdfset = s_hashset.HashSet()
            asdfset.update(asdf)
            hashes = dict([(n, s_common.ehex(h)) for (n, h) in asdfset.digests()])

            asdfhash_h = '2413fb3709b05939f04cf2e92f7d0897fc2596f9ad0b8a9ea855c7bfebaae892'
            self.eq(asdfhash_h, hashes['sha256'])

            ret = await core.callStorm('return($lib.bytes.has($hash))', {'vars': {'hash': asdfhash_h}})
            self.false(ret)
            self.false(await core.callStorm('return($lib.bytes.has($lib.null))'))
            self.false(await core.callStorm('return($lib.axon.has($lib.null))'))

            opts = {'vars': {'bytes': asdf}}
            text = '($size, $sha2) = $lib.bytes.put($bytes) [ test:int=$size test:str=$sha2 ]'

            nodes = await core.nodes(text, opts=opts)
            self.len(2, nodes)

            opts = {'vars': {'sha256': asdfhash_h}}
            self.eq(8, await core.callStorm('return($lib.bytes.size($sha256))', opts=opts))
            self.eq(8, await core.callStorm('return($lib.axon.size($sha256))', opts=opts))

            hashset = await core.callStorm('return($lib.bytes.hashset($sha256))', opts=opts)
            self.eq(hashset, hashes)

            hashset = await core.callStorm('return($lib.axon.hashset($sha256))', opts=opts)
            self.eq(hashset, hashes)

            self.eq(nodes[0].ndef, ('test:int', 8))
            self.eq(nodes[1].ndef, ('test:str', asdfhash_h))

            bkey = s_common.uhex(asdfhash_h)
            byts = b''.join([b async for b in core.axon.get(bkey)])
            self.eq(b'asdfasdf', byts)

            ret = await core.callStorm('return($lib.bytes.has($hash))', {'vars': {'hash': asdfhash_h}})
            self.true(ret)

            ret = await core.callStorm('return($lib.axon.has($hash))', {'vars': {'hash': asdfhash_h}})
            self.true(ret)

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

            # Mismatch surrogates from real world data
            surrogate_data = "FOO\ufffd\ufffd\ufffd\udfab\ufffd\ufffdBAR"
            resp = await core.callStorm('$buf=$s.encode() return ( ($buf, $buf.decode() ) )',
                                        opts={'vars': {'s': surrogate_data}})
            self.eq(resp[0], surrogate_data.encode('utf-8', 'surrogatepass'))
            self.eq(resp[1], surrogate_data)

            # Encoding/decoding errors are caught
            q = '$valu="valu" $valu.encode("utf16").decode()'
            msgs = await core.stormlist(q)
            errs = [m for m in msgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][1][0], 'StormRuntimeError')

            q = '$lib.print($byts.decode(errors=ignore))'
            msgs = await core.stormlist(q, opts={'vars': {'byts': b'foo\x80'}})
            self.stormHasNoErr(msgs)
            self.stormIsInPrint('foo', msgs)

            q = '$valu="str.ॐ.valu" $buf=$valu.encode(ascii)'
            msgs = await core.stormlist(q)
            errs = [m for m in msgs if m[0] == 'err']
            self.len(1, errs)
            self.eq(errs[0][1][0], 'StormRuntimeError')

            bobj = s_stormtypes.Bytes(b'beepbeep')
            self.len(8, bobj)

            opts = {'vars': {'chunks': (b'visi', b'kewl')}}
            retn = await core.callStorm('return($lib.bytes.upload($chunks))', opts=opts)
            self.eq((8, '9ed8ffd0a11e337e6e461358195ebf8ea2e12a82db44561ae5d9e638f6f922c4'), retn)

            retn = await core.callStorm('return($lib.axon.upload($chunks))', opts=opts)
            self.eq((8, '9ed8ffd0a11e337e6e461358195ebf8ea2e12a82db44561ae5d9e638f6f922c4'), retn)

            visi = await core.auth.addUser('visi')
            await visi.addRule((False, ('axon', 'has')))

            opts = {'user': visi.iden, 'vars': {'hash': asdfhash_h}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.bytes.has($hash))', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.bytes.size($hash))', opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.bytes.hashset($hash))', opts=opts)

            await visi.addRule((False, ('axon', 'upload')))

            opts = {'user': visi.iden, 'vars': {'byts': b'foo'}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.bytes.put($byts))', opts=opts)

            opts = {'user': visi.iden, 'vars': {'chunks': (b'visi', b'kewl')}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.bytes.upload($chunks))', opts=opts)

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
            text = '$lib.axon.put($lib.base64.decode($bytes))'
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
            text = '$lib.axon.put($lib.base64.decode($bytes, $(0)))'
            nodes = await core.nodes(text, opts)
            key = binascii.unhexlify(hashlib.sha256(base64.urlsafe_b64decode(opts['vars']['bytes'])).hexdigest())
            byts = b''.join([b async for b in core.axon.get(key)])
            self.eq(byts, b'fooba?')

            # unhappy cases
            opts = {'vars': {'bytes': 'not bytes'}}
            text = '[ test:str=$lib.base64.encode($bytes) ]'
            mesgs = await core.stormlist(text, opts=opts)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('Error during base64 encoding - a bytes-like object is required', err[1].get('mesg'))

            opts = {'vars': {'bytes': 'foobar'}}
            text = '[test:str=$lib.base64.decode($bytes)]'
            mesgs = await core.stormlist(text, opts=opts)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            self.isin('Error during base64 decoding - Incorrect padding', err[1].get('mesg'))

            opts = {'vars': {'bytes': None}}
            text = '[test:str=$lib.base64.decode($bytes)]'
            mesgs = await core.stormlist(text, opts=opts)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'StormRuntimeError')
            emsg = "Error during base64 decoding - argument should be a bytes-like object or ASCII string, not 'NoneType'"
            self.isin(emsg, err[1].get('mesg'))

    async def test_storm_lib_vars(self):

        async with self.getTestCore() as core:

            opts = {'vars': {'testvar': 'test'}}
            text = '$testkey=testvar [ test:str=$lib.vars.get($testkey) ]'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test'))

            text = '$testkey=testvar [ test:str=$lib.vars.get($testkey) ]'
            mesgs = await core.stormlist(text)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'BadTypeValu')
            self.isin('no norm for type', err[1].get('mesg'))

            opts = {'vars': {'testkey': 'testvar'}}
            text = '$lib.vars.set($testkey, test) [ test:str=$lib.vars.get(testvar) ]'
            nodes = await core.nodes(text, opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('test:str', 'test'))

            opts = {'vars': {'testvar': 'test', 'testkey': 'testvar'}}
            text = '$lib.vars.del(testvar) [ test:str=$lib.vars.get($testkey) ]'
            mesgs = await core.stormlist(text, opts=opts)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'BadTypeValu')
            self.isin('no norm for type', err[1].get('mesg'))

            opts = {'vars': {'testvar': 'test', 'testkey': 'testvar'}}
            text = '$lib.vars.del(testvar) [ test:str=$lib.vars.get($testkey) ]'
            mesgs = await core.stormlist(text, opts=opts)
            errs = [m[1] for m in mesgs if m[0] == 'err']
            self.len(1, errs)
            err = errs[0]
            self.eq(err[0], 'BadTypeValu')
            self.isin('no norm for type', err[1].get('mesg'))

            opts = {'vars': {'testvar': 'test', 'testkey': 'testvar'}}
            text = '$lib.print($lib.vars.list())'
            mesgs = await core.stormlist(text, opts=opts)
            mesgs = [m for m in mesgs if m[0] == 'print']
            self.len(1, mesgs)
            self.stormIsInPrint("('testvar', 'test'), ('testkey', 'testvar')", mesgs)

    async def test_storm_lib_vars_type(self):

        async with self.getTestCore() as core:

            # $lib.vars.type() results
            self.eq('undef', await core.callStorm('return ($lib.vars.type($lib.undef))'))
            self.eq('null', await core.callStorm('return ($lib.vars.type($lib.null))'))
            self.eq('null', await core.callStorm('$foo=({}) return ($lib.vars.type($foo.key))'))
            self.eq('boolean', await core.callStorm('return ($lib.vars.type($lib.true))'))
            self.eq('boolean', await core.callStorm('return ($lib.vars.type($lib.false))'))
            self.eq('str', await core.callStorm('return ($lib.vars.type(1))'))
            self.eq('int', await core.callStorm('return ($lib.vars.type( (1) ))'))
            self.eq('bytes', await core.callStorm('return ($lib.vars.type( $foo ))', {'vars': {'foo': b'hehe'}}))
            self.eq('dict', await core.callStorm('return ( $lib.vars.type(({"hehe": "haha"})) )'))
            self.eq('list', await core.callStorm('return ( $lib.vars.type((1, 2)) )'))
            self.eq('list', await core.callStorm('return ( $lib.vars.type(()) )'))
            self.eq('list', await core.callStorm('return ( $lib.vars.type(([])) )'))
            self.eq('list', await core.callStorm('return ( $lib.vars.type(([1, 2])) )'))
            self.eq('set', await core.callStorm('return ( $lib.vars.type($lib.set(hehe, haha)) )'))
            self.eq('number', await core.callStorm('return ($lib.vars.type( $foo ))', {'vars': {'foo': 1.2345}}))
            self.eq('number', await core.callStorm('return ( $lib.vars.type($lib.math.number(42.0)) )'))

            self.eq('function', await core.callStorm('return ( $lib.vars.type($lib.print) )'))
            self.eq('function', await core.callStorm('function foo() {} return ( $lib.vars.type($foo) )'))
            self.eq('function', await core.callStorm('function foo() { emit bar }  return ( $lib.vars.type($foo  ) )'))
            self.eq('generator', await core.callStorm('function foo() { emit bar } return ( $lib.vars.type($foo()) )'))

            self.eq('auth:role', await core.callStorm('return( $lib.vars.type($lib.auth.roles.byname(all)) )'))
            self.eq('auth:user', await core.callStorm('return( $lib.vars.type($lib.auth.users.byname(root)) )'))
            self.eq('auth:user:json', await core.callStorm('return( $lib.vars.type($lib.auth.users.byname(root).json) )'))
            self.eq('auth:user:profile', await core.callStorm('return( $lib.vars.type($lib.auth.users.byname(root).profile) )'))
            self.eq('auth:user:vars', await core.callStorm('return( $lib.vars.type($lib.auth.users.byname(root).vars) )'))
            self.eq('auth:gate',
                    await core.callStorm('return ( $lib.vars.type($lib.auth.gates.get($lib.view.get().iden)) )'))

            self.eq('view', await core.callStorm('return( $lib.vars.type($lib.view.get()) )'))
            self.eq('layer', await core.callStorm('return( $lib.vars.type($lib.layer.get()) )'))

            self.eq('storm:query', await core.callStorm('return( $lib.vars.type( ${test:str} ) )'))

            url = core.getLocalUrl()
            opts = {'vars': {'url': url}}
            self.eq('telepath:proxy', await core.callStorm('return( $lib.vars.type($lib.telepath.open($url)) )', opts))
            self.eq('telepath:proxy:method', await core.callStorm('return( $lib.vars.type($lib.telepath.open($url).getCellInfo) )', opts))
            self.eq('telepath:proxy:genrmethod', await core.callStorm('return( $lib.vars.type($lib.telepath.open($url).storm) )', opts))

            self.eq('node', await core.callStorm('[test:str=foo] return ($lib.vars.type($node))'))
            self.eq('node:props', await core.callStorm('[test:str=foo] return ($lib.vars.type($node.props))'))
            self.eq('node:data', await core.callStorm('[test:str=foo] return ($lib.vars.type($node.data))'))
            self.eq('node:path', await core.callStorm('[test:str=foo] return ($lib.vars.type($path))'))

            # Coverage
            def foo():
                for i in range(1):
                    yield i
            genr = foo()
            self.eq('generator', await s_stormtypes.totype(genr))

            self.eq('NoValu', await s_stormtypes.totype(s_common.novalu, basetypes=True))
            with self.raises(s_exc.NoSuchType) as cm:
                await s_stormtypes.totype(s_common.novalu)

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

            q = 'feed.list'
            mesgs = await core.stormlist(q)
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
            msgs = await core.stormlist(q, opts)
            self.stormIsInWarn("BadTypeValu", msgs)
            errs = [m for m in msgs if m[0] == 'err']
            self.len(0, errs)

    async def test_storm_lib_layer(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            mainlayr = core.view.layers[0].iden

            forkview = await core.callStorm('return($lib.view.get().fork().iden)')
            forklayr = await core.callStorm('return($lib.layer.get().iden)', opts={'view': forkview})
            self.eq(forklayr, core.views.get(forkview).layers[0].iden)

            q = '$lib.print($lib.layer.get().iden)'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint(mainlayr, mesgs)

            q = f'$lib.print($lib.layer.get({mainlayr}).iden)'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint(mainlayr, mesgs)

            info = await core.callStorm('return ($lib.layer.get().pack())')
            size = info.get('totalsize')

            self.gt(size, 1)
            self.nn(info.get('created'))
            # Verify we're showing actual disk usage and not just apparent
            self.lt(size, 1000000000)

            # Try to create an invalid layer
            msgs = await core.stormlist('$lib.layer.add(ldef=({"lockmemory": (42)}))')
            self.stormIsInErr('lockmemory must be boolean', msgs)
            msgs = await core.stormlist('$lib.layer.add(ldef=({"readonly": "False"}))')
            self.stormIsInErr('readonly must be boolean', msgs)

            # Create a new layer
            newlayr = await core.callStorm('return($lib.layer.add().iden)')
            self.isin(newlayr, core.layers)

            # Ensure new layer is set to current model revision
            newrev = await core.layers[newlayr].getModelVers()
            self.eq(s_modelrev.maxvers, newrev)

            # List the layers in the cortex
            q = '''
                for $layer in $lib.layer.list() {
                    $lib.print($layer.iden)
                }
            '''
            idens = []
            mesgs = await core.stormlist(q)
            for mesg in mesgs:
                if mesg[0] == 'print':
                    idens.append(mesg[1]['mesg'])

            self.sorteq(idens, core.layers)

            # Create a new layer with a name
            q = f'$lib.print($lib.layer.add(({{"name": "foo"}})).iden)'
            for mesg in await core.stormlist(q):
                if mesg[0] == 'print':
                    namedlayer = mesg[1]['mesg']

            self.eq(core.layers.get(namedlayer).layrinfo.get('name'), 'foo')

            # Delete a layer
            q = f'$lib.print($lib.layer.del({newlayr}))'
            mesgs = await core.stormlist(q)

            self.notin(newlayr, core.layers)

            # Sad paths

            q = f'$lib.layer.get(foo)'
            with self.raises(s_exc.NoSuchIden):
                await core.nodes(q)

            q = f'$lib.layer.del(foo)'
            with self.raises(s_exc.NoSuchIden):
                await core.nodes(q)

            q = f'$lib.layer.del({mainlayr})'
            with self.raises(s_exc.LayerInUse):
                await core.nodes(q)

            # Test permissions

            visi = await prox.addUser('visi')
            await prox.setUserPasswd(visi['iden'], 'secret')

            async with core.getLocalProxy(user='visi') as asvisi:

                q = 'layer.get'
                mesgs = await asvisi.storm(q).list()
                self.stormIsInPrint(mainlayr, mesgs)

                q = f'layer.get {mainlayr}'
                mesgs = await asvisi.storm(q).list()
                self.stormIsInPrint(mainlayr, mesgs)

                q = 'layer.list'
                idens = []
                mesgs = await asvisi.storm(q).list()

                for layr in core.layers.keys():
                    self.stormIsInPrint(layr, mesgs)

                # Add requires 'add' permission
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm('$lib.layer.add()')

                await prox.addUserRule(visi['iden'], (True, ('layer', 'add')))

                layers = set(core.layers.keys())
                q = 'layer.add --name "hehe haha"'
                mesgs = await core.stormlist(q)
                visilayr = list(set(core.layers.keys()) - layers)[0]
                self.stormIsInPrint('(name: hehe haha)', mesgs)
                self.isin(visilayr, core.layers)

                # Del requires 'del' permission
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'$lib.layer.del({visilayr})')

                await prox.addUserRule(visi['iden'], (True, ('layer', 'del')))

                q = f'layer.del {visilayr}'
                mesgs = await asvisi.storm(q).list()

                self.notin(visilayr, core.layers)

                # Test add layer opts
                layers = set(core.layers.keys())
                q = f'layer.add --lockmemory --growsize 5000'
                mesgs = await core.stormlist(q)
                locklayr = list(set(core.layers.keys()) - layers)[0]

                layr = core.getLayer(locklayr)
                self.true(layr.lockmemory)

                q = '''
                for ($buid, $sode) in $lib.layer.get().getStorNodes() {
                    $lib.fire(layrdiff, sode=$sode)
                }
                '''
                await core.addTagProp('risk', ('int', {}), {})
                await core.nodes('[ it:dev:str=foo +#test:risk=50 ]')
                gotn = [mesg[1] async for mesg in asvisi.storm(q) if mesg[0] == 'storm:fire']
                fire = [mesg for mesg in gotn if mesg['data']['sode']['form'] == 'it:dev:str']
                self.len(1, fire)
                self.eq(fire[0]['data']['sode']['tagprops'], {'test': {'risk': (50, 9)}})

                q = '''
                $lib.print($lib.layer.get().pack())
                $lib.fire(layrfire, layr=$lib.layer.get().pack())
                '''
                gotn = [mesg[1] async for mesg in asvisi.storm(q)]
                fire = [mesg for mesg in gotn if mesg.get('type') == 'layrfire']
                self.len(1, fire)
                self.nn(fire[0]['data'].get('layr', None))

            # formcounts for layers are exposed on the View object
            await core.nodes('[(test:guid=(test,) :size=1138) (test:int=8675309)]')
            counts = await core.callStorm('return( $lib.layer.get().getFormCounts() )')
            self.eq(counts.get('test:int'), 2)
            self.eq(counts.get('test:guid'), 1)

    async def test_storm_lib_layer_sodebyform(self):
        async with self.getTestCore() as core:

            await core.nodes('$lib.model.ext.addTagProp(score, (int, ({})), ({}))')

            view_prop = await core.callStorm('return($lib.view.get().fork().iden)')
            view_tags = await core.callStorm('return($lib.view.get().fork().iden)')
            view_tagp = await core.callStorm('return($lib.view.get().fork().iden)')
            view_n1eg = await core.callStorm('return($lib.view.get().fork().iden)')
            view_n2eg = await core.callStorm('return($lib.view.get().fork().iden)')
            view_data = await core.callStorm('return($lib.view.get().fork().iden)')
            view_noop = await core.callStorm('return($lib.view.get().fork().iden)')

            self.len(1, await core.nodes('[ test:str=foo +#base ]'))
            self.len(1, await core.nodes('test:str=foo [ :hehe=haha ]', opts={'view': view_prop}))
            self.len(1, await core.nodes('test:str=foo [ +#bar ]', opts={'view': view_tags}))
            self.len(1, await core.nodes('test:str=foo [ +#base:score=10 ]', opts={'view': view_tagp}))
            self.len(1, await core.nodes('test:str=foo [ +(bam)> {[ test:int=2 ]} ]', opts={'view': view_n1eg}))
            self.len(1, await core.nodes('test:str=foo [ <(bam)+ {[ test:int=1 ]} ]', opts={'view': view_n2eg}))
            self.len(1, await core.nodes('test:str=foo $node.data.set(hehe, haha)', opts={'view': view_data}))

            scmd = '''
                $sodes = ([])
                for $sode in $lib.layer.get().getStorNodesByForm($form) {
                    $sodes.append($sode)
                }
                return($sodes)
            '''
            opts = {'vars': {'form': 'test:str'}}

            self.len(1, await core.callStorm(scmd, opts=opts))
            self.len(1, await core.callStorm(scmd, opts={**opts, 'view': view_prop}))
            self.len(1, await core.callStorm(scmd, opts={**opts, 'view': view_tags}))
            self.len(1, await core.callStorm(scmd, opts={**opts, 'view': view_tagp}))
            self.len(1, await core.callStorm(scmd, opts={**opts, 'view': view_n1eg}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_n2eg})) # n2-only sode not added
            self.len(1, await core.callStorm(scmd, opts={**opts, 'view': view_data}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_noop}))

            self.len(1, await core.nodes('test:str=foo [ -:hehe ]', opts={'view': view_prop}))
            self.len(1, await core.nodes('test:str=foo [ -#bar ]', opts={'view': view_tags}))
            self.len(1, await core.nodes('test:str=foo [ -#base:score ]', opts={'view': view_tagp}))
            self.len(1, await core.nodes('test:str=foo [ -(bam)> {[ test:int=2 ]} ]', opts={'view': view_n1eg}))
            self.len(1, await core.nodes('test:str=foo [ <(bam)- {[ test:int=1 ]} ]', opts={'view': view_n2eg}))
            self.len(1, await core.nodes('test:str=foo $node.data.pop(hehe)', opts={'view': view_data}))

            self.len(1, await core.callStorm(scmd, opts=opts))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_prop}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_tags}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_tagp}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_n1eg}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_n2eg}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_data}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_noop}))

            self.len(1, await core.nodes('''
                test:str=foo [
                    :hehe=lol
                    +#baz
                    +#base:score=11
                    +(bar)> {[ test:int=2 ]}
                    <(bar)+ {[ test:int=1 ]}
                ]
                $node.data.set(haha, lol)
            '''))
            self.len(1, await core.nodes('test:str=foo [ :hehe=lol ]', opts={'view': view_prop}))
            self.len(1, await core.nodes('test:str=foo [ +#baz ]', opts={'view': view_tags}))
            self.len(1, await core.nodes('test:str=foo [ +#base:score=11 ]', opts={'view': view_tagp}))
            self.len(1, await core.nodes('test:str=foo [ +(bar)> {[ test:int=2 ]} ]', opts={'view': view_n1eg}))
            self.len(1, await core.nodes('test:str=foo [ <(bar)+ {[ test:int=1 ]} ]', opts={'view': view_n2eg}))
            self.len(1, await core.nodes('test:str=foo $node.data.set(haha, lol)', opts={'view': view_data}))

            self.len(1, await core.callStorm(scmd, opts=opts))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_prop}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_tags}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_tagp}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_n1eg}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_n2eg}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_data}))
            self.len(0, await core.callStorm(scmd, opts={**opts, 'view': view_noop}))

            self.len(1, await core.nodes('''
                test:str=foo [
                    -:hehe
                    -#baz
                    -#base:score -#base
                    -(bar)> { test:int=2 }
                    <(bar)- { test:int=1 }
                ]
                $node.data.pop(haha)
            '''))
            self.len(1, await core.callStorm(scmd, opts=opts))

            await core.nodes('test:str=foo delnode')
            self.len(0, await core.callStorm(scmd, opts=opts))

            # sad

            await self.asyncraises(s_exc.NoSuchForm, core.callStorm(scmd, opts={'vars': {'form': 'newp:newp'}}))

            lowuser = await core.auth.addUser('low')
            lowopts = opts | {'user': lowuser.iden, 'view': view_prop}

            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=lowopts))

            await lowuser.addRule((True, ('view', 'read')), gateiden=view_prop)
            await core.callStorm(scmd, opts=lowopts)

    async def test_storm_lib_layer_upstream(self):
        async with self.getTestCore() as core:
            async with self.getTestCore() as core2:

                await core2.nodes('[ inet:ipv4=1.2.3.4 ]')
                url = core2.getLocalUrl('*/layer')

                layriden = core2.view.layers[0].iden
                offs = await core2.view.layers[0].getEditIndx()

                layers = set(core.layers.keys())
                q = f'layer.add --upstream {url}'
                mesgs = await core.stormlist(q)
                uplayr = list(set(core.layers.keys()) - layers)[0]

                q = f'layer.set {uplayr} name "woot woot"'
                mesgs = await core.stormlist(q)
                self.stormIsInPrint('(name: woot woot)', mesgs)

                layr = core.getLayer(uplayr)

                evnt = await layr.waitUpstreamOffs(layriden, offs)
                self.true(await asyncio.wait_for(evnt.wait(), timeout=6))

    async def test_storm_lib_view(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.addRule((True, ('layer', 'read')))

            layr0 = core.getLayer()
            ldef1 = await core.addLayer()

            layrs0 = (layr0.iden, ldef1.get('iden'))
            layrs1 = (ldef1.get('iden'), layr0.iden)

            # fork the default view to test editing the root view layers
            fork00 = await core.callStorm('return($lib.view.get().fork().iden)')
            self.eq(2, await core.callStorm('return($lib.view.get().layers.size())', opts={'view': fork00}))

            await core.callStorm('$lib.view.get().set(layers, $layers)', opts={'vars': {'layers': layrs0}})
            ldefs = await core.callStorm('return($lib.view.get().get(layers))')
            self.eq(layrs0, [x.get('iden') for x in ldefs])

            layers = await core.callStorm('return($lib.view.get().layers)', opts={'view': fork00})
            self.eq(layrs0, [layr['iden'] for layr in layers][-2:])
            self.len(3, layers)

            await core.callStorm('$lib.view.get().set(layers, $layers)', opts={'vars': {'layers': layrs1}})
            ldefs = await core.callStorm('return($lib.view.get().get(layers))')
            self.eq(layrs1, [x.get('iden') for x in ldefs])

            with self.raises(s_exc.NoSuchLayer):
                await core.nodes('$lib.view.get().set(layers, $layers)', opts={'vars': {'layers': ('asdf',)}})

            with self.raises(s_exc.AuthDeny):
                opts = {'user': visi.iden, 'vars': {'layers': layrs0}}
                await core.callStorm('$lib.view.get().set(layers, $layers)', opts=opts)

        async with self.getTestCoreAndProxy() as (core, prox):

            derp = await core.auth.addUser('derp')
            root = await core.auth.getUserByName('root')

            await derp.addRule((True, ('view', 'add')))

            await core.addTagProp('risk', ('int', {'min': 0, 'max': 100}), {'doc': 'risk score'})
            await core.nodes('[test:int=12 +#tag.test +#tag.proptest:risk=20]')

            # Get the main view
            mainiden = await core.callStorm('return($lib.view.get().iden)')
            altview = await core.callStorm('''
                $layers = ()
                for $layer in $lib.view.get().layers {
                    $layers.append($layer.iden)
                }
                return($lib.view.add($layers).iden)
            ''')

            altlayr = await core.callStorm('return($lib.layer.add().iden)')

            asderp = {'user': derp.iden, 'vars': {'altlayr': altlayr}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(f'return($lib.view.add(($altlayr,)))', opts=asderp)

            asderp = {'user': derp.iden, 'vars': {'altview': altview}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(f'return($lib.view.get($altview).fork())', opts=asderp)

            # Fork the main view
            q = f'''
                $view=$lib.view.get().fork()
                return(($view.iden, $view.layers.index(0).iden))
            '''
            forkiden, forklayr = await core.callStorm(q)

            # Parent is populated on the fork and not the default view
            q = '''$dp=$lib.view.get().parent $fp=$lib.view.get($iden).parent return (($dp, $fp))'''
            self.eq((None, mainiden), await core.callStorm(q, opts={'vars': {'iden': forkiden}}))

            self.isin(forkiden, core.views)
            self.isin(forklayr, core.layers)

            msgs = await core.stormlist(f'$v=$lib.view.get({forkiden}) $lib.print($lib.len($v))')
            self.stormIsInErr('View does not have a length', msgs)

            # Add a view
            ldef = await core.addLayer()
            newlayer = core.getLayer(ldef.get('iden'))

            newiden = await core.callStorm(f'return($lib.view.add(({newlayer.iden},)).iden)')
            self.nn(newiden)

            self.isin(newiden, core.views)

            # List the views in the cortex
            q = '''
                $views = ()
                for $view in $lib.view.list() {
                    $views.append($view.iden)
                }
                return($views)
            '''
            idens = await core.callStorm(q)
            self.sorteq(idens, core.views.keys())

            # Delete the added view
            q = f'$lib.view.del({newiden})'
            await core.nodes(q)

            self.notin(newiden, core.views)

            # Fork the forked view
            q = f'''
                $forkview=$lib.view.get({forkiden}).fork()
                return($forkview.pack().iden)
            '''
            childiden = await core.callStorm(q)
            self.nn(childiden)

            # Can't merge the first forked view if it has children
            q = f'$lib.view.get({forkiden}).merge()'
            await self.asyncraises(s_exc.CantMergeView, core.callStorm(q))

            # Can't merge the child forked view if the parent is read only
            core.views[childiden].parent.layers[0].readonly = True
            q = f'$lib.view.get({childiden}).merge()'
            await self.asyncraises(s_exc.ReadOnlyLayer, core.callStorm(q))

            core.views[childiden].parent.layers[0].readonly = False
            await core.nodes(q)

            # Merge the forked view
            q = f'$lib.view.get({childiden}).merge()'
            await core.nodes(q)

            # Remove the forked view
            q = f'$lib.view.del({childiden})'
            await core.nodes(q)

            self.notin(childiden, core.views)

            # Sad paths
            await self.asyncraises(s_exc.NoSuchView, core.nodes('$lib.view.del(foo)'))
            await self.asyncraises(s_exc.NoSuchView, core.nodes('$lib.view.get(foo)'))
            await self.asyncraises(s_exc.CantMergeView, core.nodes(f'$lib.view.get().merge()'))
            await self.asyncraises(s_exc.NoSuchLayer, core.nodes(f'view.add --layers {s_common.guid()}'))
            await self.asyncraises(s_exc.SynErr, core.nodes('$lib.view.del($lib.view.get().iden)'))
            await self.asyncraises(s_exc.SchemaViolation, core.nodes('$lib.view.add(([]))'))

            q = '$iden = $lib.layer.get().iden $lib.view.add(([$iden, $iden]))'
            await self.asyncraises(s_exc.SchemaViolation, core.nodes(q))

            # Check helper commands
            # Get the main view
            mesgs = await core.stormlist('view.get')
            self.stormIsInPrint(mainiden, mesgs)

            await core.stormlist('$lib.view.get().set(name, "test view")')
            await core.stormlist('$lib.view.get().set(desc, "test view desc")')

            await core.stormlist('$lib.layer.get().set(name, "test layer")')
            await core.stormlist('$lib.layer.get().set(desc, "test layer desc")')

            self.eq(await core.callStorm('return( $lib.view.get().get(name))'), 'test view')
            self.eq(await core.callStorm('return( $lib.view.get().get(desc))'), 'test view desc')

            self.eq(await core.callStorm('return( $lib.layer.get().get(name))'), 'test layer')
            self.eq(await core.callStorm('return( $lib.layer.get().get(desc))'), 'test layer desc')

            await core.stormlist('$lib.view.get().set(name, $lib.null)')
            vdef = await core.callStorm('return($lib.view.get())')
            self.notin('name', vdef)
            await core.stormlist('$lib.view.get().set(name, "test view")')
            await core.stormlist('$lib.view.get().set(name, $lib.undef)')
            vdef = await core.callStorm('return($lib.view.get())')
            self.notin('name', vdef)
            self.nn(vdef.get('created'))

            await core.stormlist('$lib.layer.get().set(name, $lib.null)')
            ldef = await core.callStorm('return($lib.layer.get())')
            self.notin('name', ldef)
            await core.stormlist('$lib.layer.get().set(name, "test layer")')
            await core.stormlist('$lib.layer.get().set(name, $lib.undef)')
            ldef = await core.callStorm('return($lib.layer.get())')
            self.notin('name', ldef)

            with self.raises(s_exc.BadOptValu):
                await core.nodes('$lib.view.get().set(hehe, haha)')

            with self.raises(s_exc.BadOptValu):
                await core.nodes('$lib.layer.get().set(hehe, haha)')

            async with core.getLocalProxy() as prox:
                self.eq(core.view.iden, await prox.callStorm('return ($lib.view.get().get(iden))'))
                q = 'return ($lib.view.get().layers.index(0).get(iden))'
                self.eq(core.view.layers[0].iden, await prox.callStorm(q))

            q = f'view.get {mainiden}'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint(mainiden, mesgs)
            self.stormIsInPrint('readonly: False', mesgs)
            self.stormIsInPrint(core.view.layers[0].iden, mesgs)

            # Fork the main view
            views = set(core.views.keys())
            q = f'view.fork {mainiden} --name lulz'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('(name: lulz)', mesgs)
            helperfork = list(set(core.views.keys()) - views)[0]
            self.isin(helperfork, core.views)

            # Add a view
            ldef = await core.addLayer()
            newlayer2 = core.getLayer(ldef.get('iden'))

            views = set(core.views.keys())

            q = f'view.add --name "foo bar" --layers {newlayer.iden} {newlayer2.iden}'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('(name: foo bar)', mesgs)

            helperadd = list(set(core.views.keys()) - views)[0]

            # List the views in the cortex
            q = 'view.list'
            mesgs = await core.stormlist(q)

            self.stormIsInPrint(f'Creator: {root.iden}', mesgs)
            self.stormIsInPrint(f'readonly: False', mesgs)

            for viden, v in core.views.items():
                self.stormIsInPrint(viden, mesgs)
                for layer in v.layers:
                    self.stormIsInPrint(layer.iden, mesgs)

            # Delete the added view
            q = f'view.del {helperadd}'
            await core.nodes(q)

            self.notin(helperadd, core.views)

            # Merge the forked view
            q = f'view.merge --delete {helperfork}'
            await core.nodes(q)

            self.notin(helperfork, core.views)

            # Test permissions

            visi = await prox.addUser('visi', passwd='secret')

            async with core.getLocalProxy(user='visi') as asvisi:

                await asvisi.storm('$lib.view.list()').list()
                await asvisi.storm('$lib.view.get()').list()

                # Add and Fork require 'add' permission
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'$lib.view.add(({newlayer.iden},))')
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'$lib.view.get({mainiden}).fork()')

                await prox.addUserRule(visi['iden'], (True, ('view', 'add')))
                await prox.addUserRule(visi['iden'], (True, ('layer', 'read')), gateiden=newlayer.iden)

                q = f'''
                    $newview=$lib.view.add(({newlayer.iden},))
                    return($newview.pack().iden)
                '''
                addiden = await asvisi.callStorm(q)
                self.isin(addiden, core.views)

                q = f'''
                    $forkview=$lib.view.get({mainiden}).fork()
                    $lib.print($forkview.pack().iden)
                '''
                mesgs = await asvisi.storm(q).list()
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        forkediden = mesg[1]['mesg']

                self.isin(forkediden, core.views)

                # Owner can 'get' the forked view
                q = f'$lib.view.get({forkediden})'
                vals = await asvisi.storm(q).list()
                self.len(2, vals)

                # Del and Merge require 'del' permission unless performed by the owner
                # Delete a view the user owns

                q = f'$lib.view.del({addiden})'
                await asvisi.storm(q).list()

                self.notin(addiden, core.views)

                forkview = core.getView(forkediden)
                await alist(forkview.eval('[test:int=34 +#tag.test +#tag.proptest:risk=40]'))
                await alist(forkview.eval('test:int=12 [-#tag.proptest:risk]'))
                await alist(forkview.eval('test:int=12 | delnode'))

                # Make a bunch of nodes so we chunk the permission check
                for i in range(1000):
                    opts = {'vars': {'val': i + 1000}}
                    await self.agenlen(1, forkview.eval('[test:int=$val]', opts=opts))

                # Merge the view forked by the user
                # Will need perms for all the ops required to merge

                q = f'$lib.view.get({forkediden}).merge()'
                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(q)

                await prox.addUserRule(visi['iden'], (True, ('node', 'add',)))
                await prox.addUserRule(visi['iden'], (True, ('node', 'del',)))
                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'set',)))
                await prox.addUserRule(visi['iden'], (True, ('node', 'prop', 'del',)))
                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'add',)))
                await prox.addUserRule(visi['iden'], (True, ('node', 'tag', 'del',)))

                q = f'''
                    $view = $lib.view.get({forkediden})

                    $view.merge()

                    $lib.view.del($view.iden)
                    $lib.layer.del($view.layers.index(0).iden)
                '''
                await asvisi.callStorm(q)

                self.notin(forkediden, core.views)

                # Make some views not owned by the user
                views = set(core.views.keys())
                q = f'view.add --layers {newlayer.iden}'
                mesgs = await core.stormlist(q)
                self.stormIsInPrint('(name: unnamed)', mesgs)
                rootadd = list(set(core.views.keys()) - views)[0]
                self.isin(rootadd, core.views)

                q = f'view.set {rootadd} name "lol lol"'
                mesgs = await core.stormlist(q)
                self.stormIsInPrint('(name: lol lol)', mesgs)

                q = f'view.fork {mainiden}'
                mesgs = await core.stormlist(q)
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        rootfork = mesg[1]['mesg'].split(' ')[-1]
                self.isin(rootfork, core.views)

                with self.raises(s_exc.AuthDeny):
                    await asvisi.callStorm(f'$lib.view.del({rootadd})')

                await prox.addUserRule(visi['iden'], (True, ('view', 'del')))

                # Delete a view not owned by the user
                q = f'$lib.view.del({rootadd})'
                await asvisi.storm(q).list()

                self.notin(rootadd, core.views)

                # Merge a view not owned by the user
                q = f'view.merge --delete {rootfork}'
                await core.nodes(q)

                self.notin(rootfork, core.views)

                # Test getting the view's triggers
                tdef = await core.view.addTrigger({
                    'cond': 'node:add',
                    'form': 'test:str',
                    'storm': '[ test:int=1 ]',
                })

                triggers = await core.callStorm('return($lib.view.get().triggers)')
                self.len(1, triggers)
                self.eq(triggers[0]['iden'], tdef['iden'])

            # Test formcounts
            nodes = await core.nodes('[(test:guid=(test,) :size=1138) (test:int=8675309)]')
            counts = await core.callStorm('return( $lib.view.get().getFormCounts() )')
            self.eq(counts.get('test:int'), 1003)
            self.eq(counts.get('test:guid'), 1)

            opts = {'vars': {'props': {'asn': 'asdf'}}}
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('yield $lib.view.get().addNode(inet:ipv4, 1.2.3.4, props=$props)', opts=opts)
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4'))
            opts = {'vars': {'props': {'asn': '1234'}}}
            nodes = await core.nodes('yield $lib.view.get().addNode(inet:ipv4, 1.2.3.4, props=$props)', opts=opts)
            self.eq(1234, nodes[0].get('asn'))

        # view.addNode() behavior
        async with self.getTestCore() as core:

            fork = await core.callStorm('return($lib.view.get().fork().iden)')
            visi = await core.auth.addUser('visi')

            opts = {'user': visi.iden, 'vars': {'fork': fork}}
            msgs = await core.stormlist('$lib.view.get($fork).addNode(inet:fqdn, vertex.link)', opts=opts)
            self.stormIsInErr('must have permission view.read', msgs)

            await visi.addRule((True, ('view', 'read')), gateiden=fork)

            opts = {'user': visi.iden, 'vars': {'fork': fork}}
            msgs = await core.stormlist('$lib.view.get($fork).addNode(inet:fqdn, vertex.link)', opts=opts)
            self.stormIsInErr('must have permission node.add.inet:fqdn', msgs)

            layr = core.getView(fork).layers[0].iden
            await visi.addRule((True, ('node', 'add', 'inet:fqdn')), gateiden=layr)

            opts = {'user': visi.iden, 'vars': {'fork': fork}}
            msgs = await core.stormlist('$lib.view.get($fork).addNode(inet:fqdn, vertex.link, props=({"issuffix": true}))', opts=opts)
            self.stormIsInErr('must have permission node.prop.set.inet:fqdn:issuffix', msgs)

            # return none since the node is made in a different view
            await visi.addRule((True, ('node', 'prop', 'set', 'inet:fqdn:issuffix')), gateiden=layr)
            query = '$node=$lib.view.get($fork).addNode(inet:fqdn, vertex.link, props=({"issuffix": true})) ' \
                    'return ( $node )'
            node = await core.callStorm(query, opts=opts)
            self.none(node)

            # return the node from the current view
            opts = {'user': visi.iden, 'view': fork}
            query = '$node=$lib.view.get().addNode(inet:fqdn, vertex.link, props=({"issuffix": true})) ' \
                    'return ( $node )'
            node = await core.callStorm(query, opts=opts)
            self.eq(node, 'vertex.link')  # prim version of the storm:node

            self.len(0, await core.nodes('inet:fqdn=vertex.link'))
            self.len(1, await core.nodes('inet:fqdn=vertex.link +:issuffix=1', opts={'view': fork}))

            # retun the node edits for an updated node in the current view
            guid = 'c7e4640767de30a5ac4ff192a9d56dfa'
            opts = {'user': visi.iden, 'view': fork, 'vars': {'fork': fork, 'guid': guid}}
            await visi.addRule((True, ('node', 'add', 'media:news')), gateiden=layr)
            msgs = await core.stormlist('$lib.view.get($fork).addNode(media:news, $guid)', opts=opts)
            edits = [ne for ne in msgs if ne[0] == 'node:edits']
            self.len(1, edits)
            opts['vars']['props'] = {
                'title': 'foobar',
                'summary': 'bizbaz',
            }
            await visi.addRule((True, ('node', 'prop', 'set', 'media:news:title')), gateiden=layr)
            await visi.addRule((True, ('node', 'prop', 'set', 'media:news:summary')), gateiden=layr)
            msgs = await core.stormlist('$lib.view.get($fork).addNode(media:news, $guid, $props)', opts=opts)
            edits = [ne for ne in msgs if ne[0] == 'node:edits']
            self.len(1, edits)
            self.len(2, edits[0][1]['edits'][0][2])

            # don't get any node edits for a different view
            opts = {'user': visi.iden, 'vars': {'fork': fork}}
            msgs = await core.stormlist('$lib.view.get($fork).addNode(media:news, *)', opts=opts)
            edits = [ne for ne in msgs if ne[0] == 'node:edits']
            self.len(0, edits)

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            # Add a layer
            ldef = await core.addLayer()
            layer = core.getLayer(ldef.get('iden'))

            # Add a view via stormlib, worldreadable=False (default)
            iden = await core.callStorm(f'return($lib.view.add(({layer.iden},)).iden)')
            self.nn(iden)
            self.false(visi.allowed(('view', 'read'), gateiden=iden))

            # Add a view via stormlib, worldreadable=True (default)
            iden = await core.callStorm(f'return($lib.view.add(({layer.iden},), worldreadable=$lib.true).iden)')
            self.nn(newiden)
            self.true(visi.allowed(('view', 'read'), gateiden=iden))

            # Add a view via storm cmd, worldreadable=False (default)
            msgs = await core.stormlist(f'view.add --name view1 --layers {layer.iden}')
            self.stormIsInPrint('View added.', msgs)

            views = core.listViews()
            views = {view.info.get('name'): view.iden for view in views}

            iden = views.get('view1')
            self.nn(iden)
            self.false(visi.allowed(('view', 'read'), gateiden=iden))

            # Add a view via storm cmd, worldreadable=True
            msgs = await core.stormlist(f'view.add --name view1 --worldreadable $lib.true --layers {layer.iden}')
            self.stormIsInPrint('View added.', msgs)

            views = core.listViews()
            views = {view.info.get('name'): view.iden for view in views}

            iden = views.get('view1')
            self.nn(iden)
            self.true(visi.allowed(('view', 'read'), gateiden=iden))

            await visi.addRule((True, ('view', 'add')))

            msgs = await core.stormlist('$lib.view.get().fork()', opts={'user': visi.iden})
            self.stormHasNoWarnErr(msgs)

            await visi.addRule((False, ('view', 'fork')), gateiden=core.view.iden)
            msgs = await core.stormlist('$lib.view.get().fork()', opts={'user': visi.iden})
            self.stormIsInErr('must have permission view.fork', msgs)

    async def test_storm_view_deporder(self):

        async with self.getTestCore() as core:
            view1 = await core.view.fork()
            view2 = await core.view.fork()
            layr1 = await core.addLayer()
            layr2 = await core.addLayer()
            view3 = await core.addView({'layers': (layr1['iden'], layr2['iden'])})
            expect = (
                core.view.iden,
                view3['iden'],
                view1['iden'],
                view2['iden'],
            )
            self.eq(expect, await core.callStorm('''
                $views = ()
                for $view in $lib.view.list(deporder=$lib.true) {
                    $views.append($view.iden)
                }
                return($views)
            '''))

    async def test_storm_lib_trigger_async_regression(self):
        async with self.getRegrCore('2.112.0-trigger-noasyncdef') as core:

            # Old trigger - created in v2.70.0 with no async flag set
            view = await core.callStorm('return($lib.view.get().iden)')
            tdef = await core.callStorm('return ( $lib.trigger.get(bc1cbf350d151bba5936e6654dd13ff5) )')
            self.notin('async', tdef)

            msgs = await core.stormlist('trigger.list')
            self.stormHasNoWarnErr(msgs)
            trgs = ('iden                             view                             en?    async? cond      object',
                    f'8af9a5b134d08fded3edb667f8d8bbc2 {view} true   true   tag:add   inet:ipv4',
                    f'99b637036016dadd6db513552a1174b8 {view} true   false  tag:add            ',
                    f'bc1cbf350d151bba5936e6654dd13ff5 {view} true   false  node:add  inet:ipv4',
                    )
            for m in trgs:
                self.stormIsInPrint(m, msgs)

    async def test_storm_lib_trigger(self):

        async with self.getTestCoreAndProxy() as (core, prox):

            self.len(0, await core.nodes('syn:trigger'))

            q = 'trigger.list'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('No triggers found', mesgs)

            q = 'trigger.add node:add --form test:str --query {[ test:int=1 ]} --name trigger_test_str'
            mesgs = await core.stormlist(q)

            await core.nodes('[ test:str=foo ]')
            self.len(1, await core.nodes('test:int'))
            nodes = await core.nodes('syn:trigger')
            self.len(1, nodes)
            self.eq('trigger_test_str', nodes[0].get('name'))

            await core.nodes('trigger.add tag:add --form test:str --tag footag.* --query {[ +#count test:str=$tag ]}')

            await core.nodes('[ test:str=bar +#footag.bar ]')
            await core.nodes('[ test:str=bar +#footag.bar ]')
            nodes = await core.nodes('syn:trigger:tag^=footag')
            self.len(1, nodes)
            self.eq('', nodes[0].get('name'))
            self.len(1, await core.nodes('#count'))
            self.len(1, await core.nodes('test:str=footag.bar'))

            await core.nodes('trigger.add prop:set --disabled --prop test:type10:intprop --query {[ test:int=6 ]}')

            q = 'trigger.list'
            mesgs = await core.stormlist(q)
            self.stormIsInPrint('user', mesgs)
            self.stormIsInPrint('node:add', mesgs)
            self.stormIsInPrint('root', mesgs)

            nodes = await core.nodes('syn:trigger')
            self.len(3, nodes)

            rootiden = await core.auth.getUserIdenByName('root')

            for node in nodes:
                self.eq(node.props.get('user'), rootiden)

            goodbuid = nodes[1].ndef[1][:6]
            goodbuid2 = nodes[2].ndef[1][:6]

            # Trigger is created disabled, so no nodes yet
            self.len(0, await core.nodes('test:int=6'))

            await core.nodes(f'trigger.enable {goodbuid2}')

            # Trigger is enabled, so it should fire
            await core.nodes('[ test:type10=1 :intprop=25 ]')
            self.len(1, await core.nodes('test:int=6'))

            mesgs = await core.stormlist(f'trigger.del {goodbuid}')
            self.stormIsInPrint(f'Deleted trigger: {goodbuid}', mesgs)

            q = 'trigger.del deadbeef12341234'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            q = 'trigger.enable deadbeef12341234'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            q = 'trigger.disable deadbeef12341234'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            mesgs = await core.stormlist(f'trigger.disable {goodbuid2}')
            self.stormIsInPrint('Disabled trigger', mesgs)

            mesgs = await core.stormlist(f'trigger.enable {goodbuid2}')
            self.stormIsInPrint('Enabled trigger', mesgs)

            mesgs = await core.stormlist(f'trigger.mod {goodbuid2} {{[ test:str=different ]}}')
            self.stormIsInPrint('Modified trigger', mesgs)

            q = 'trigger.mod deadbeef12341234 {#foo}'
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes(q))

            await core.nodes('trigger.add tag:add --tag another --query {[ +#count2 ]}')

            # Syntax mistakes
            mesgs = await core.stormlist('trigger.mod "" {#foo}')
            self.stormIsInErr('matches more than one', mesgs)

            mesgs = await core.stormlist('trigger.add tag:add --prop another:thing --query {[ +#count2 ]}')
            self.stormIsInErr("data must contain ['tag'] properties", mesgs)

            mesgs = await core.stormlist('trigger.add tag:add --tag hehe.haha --prop another --query {[ +#count2 ]}')
            self.stormIsInErr("data.prop must match pattern", mesgs)

            mesgs = await core.stormlist('trigger.add tug:udd --prop another:newp --query {[ +#count2 ]}')
            self.stormIsInErr('data.cond must be one of', mesgs)

            mesgs = await core.stormlist('trigger.add tag:add --form inet:ipv4 --tag test')
            self.stormIsInErr('Missing a required option: --query', mesgs)

            mesgs = await core.stormlist('trigger.add node:add --form test:str --tag foo --query {test:str}')
            self.stormIsInErr('tag must not be present for node:add or node:del', mesgs)

            mesgs = await core.stormlist('trigger.add prop:set --tag foo --query {test:str}')
            self.stormIsInErr("data must contain ['prop']", mesgs)

            q = 'trigger.add prop:set --prop test:type10.intprop --tag foo --query {test:str}'
            mesgs = await core.stormlist(q)
            self.stormIsInErr('form and tag must not be present for prop:set', mesgs)

            mesgs = await core.stormlist('trigger.add node:add --tag tag1 --query {test:str}')
            self.stormIsInErr("data must contain ['form']", mesgs)

            # Bad storm syntax
            mesgs = await core.stormlist('trigger.add node:add --form test:str --query {[ | | test:int=1 ] }')
            self.stormIsInErr("Unexpected token '|' at line 1, column 49", mesgs)

            # (Regression) Just a command as the storm query
            q = 'trigger.add node:add --form test:str --query {[ test:int=99 ] | spin }'
            mesgs = await core.stormlist(q)
            await core.nodes('[ test:str=foo4 ]')
            self.len(1, await core.nodes('test:int=99'))

            for mesg in mesgs:
                if mesg[0] != 'print':
                    continue
                match = re.match(r'Added trigger: ([0-9a-f]+)', mesg[1]['mesg'])
                if match:
                    trigiden = match.groups()[0]
                    break
            else:
                raise Exception("Didn't find 'Added trigger' mesg")

            # Trigger pack
            q = f'return ($lib.trigger.get({trigiden}).pack())'
            trigdef = await core.callStorm(q)
            self.notin('disabled', trigdef)
            self.true(trigdef.get('enabled'))
            self.nn(trigdef.get('user'))
            self.nn(trigdef.get('view'))
            self.nn(trigdef.get('created'))
            self.eq(trigdef.get('storm'), '[ test:int=99 ] | spin')
            self.eq(trigdef.get('cond'), 'node:add')
            self.eq(trigdef.get('form'), 'test:str')
            self.eq(trigdef.get('iden'), trigiden)
            self.eq(trigdef.get('startcount'), 1)
            self.eq(trigdef.get('errcount'), 0)
            self.eq(trigdef.get('lasterrs'), ())

            mesgs = await core.stormlist(f'trigger.mod {trigiden} {{$lib.newp}}')
            self.stormIsInPrint('Modified trigger', mesgs)

            await core.nodes('[ test:str=foo5 ]')

            q = f'return ($lib.trigger.get({trigiden}).pack())'
            trigdef = await core.callStorm(q)
            self.eq(trigdef.get('startcount'), 2)
            self.eq(trigdef.get('errcount'), 1)
            lasterrs = trigdef.get('lasterrs', [])
            self.len(1, lasterrs)
            self.isin('NoSuchName', lasterrs[0])

            # Move a trigger to a different view
            q = '''
                $tdef = ({
                    "condition": 'node:add',
                    "form": 'test:str',
                    "storm": '{[ +#tagged ]}',
                    "doc": 'some trigger'
                })
                $trig = $lib.trigger.add($tdef)
                return($trig.pack())
            '''
            tdef = await core.callStorm(q)
            self.eq(tdef.get('doc'), 'some trigger')
            trig = tdef.get('iden')
            q = '''$t = $lib.trigger.get($trig) $t.set("doc", "awesome trigger") return ( $t.pack() )'''
            tdef = await core.callStorm(q, opts={'vars': {'trig': trig}})
            self.eq(tdef.get('doc'), 'awesome trigger')

            with self.raises(s_exc.BadArg):
                q = '$t = $lib.trigger.get($trig) $t.set("created", "woot") return ( $t.pack() )'
                await core.callStorm(q, opts={'vars': {'trig': trig}})

            with self.raises(s_exc.BadArg):
                q = '$t = $lib.trigger.get($trig) $t.set("foo", "bar")'
                await core.callStorm(q, opts={'vars': {'trig': trig}})

            nodes = await core.nodes('[ test:str=test1 ]')
            self.nn(nodes[0].tags.get('tagged'))

            mainview = await core.callStorm('return($lib.view.get().iden)')
            forkview = await core.callStorm('return($lib.view.get().fork().iden)')

            forkopts = {'view': forkview}
            await core.nodes('trigger.add tag:add --view $view --tag neato.* --query {[ +#awesome ]}', opts={'vars': forkopts})
            mesgs = await core.stormlist('trigger.list', opts=forkopts)
            nodes = await core.nodes('syn:trigger', opts=forkopts)
            self.stormNotInPrint(mainview, mesgs)
            self.stormIsInPrint(forkview, mesgs)
            self.len(1, nodes)
            othr = nodes[0].ndef[1]
            self.nn(nodes[0].props.get('.created'))

            # fetch a trigger from another view
            self.nn(await core.callStorm(f'return($lib.trigger.get({othr}))'))

            # mess with things to make a bad trigger and make sure move doesn't delete it
            core.views[forkview].triggers.triggers[othr].tdef.pop('storm')
            mesgs = await core.stormlist(f'$lib.trigger.get({othr}).move({mainview})')
            self.stormIsInErr('Cannot move invalid trigger', mesgs)

            mesgs = await core.stormlist('trigger.list')
            self.stormNotInPrint(othr, mesgs)
            mesgs = await core.stormlist('trigger.list', opts=forkopts)
            self.stormIsInPrint(othr, mesgs)
            mesgs = await core.stormlist('trigger.list --all')
            self.stormIsInPrint(othr, mesgs)

            core.views[forkview].triggers.triggers[othr].tdef['storm'] = '[ +#naughty.trigger'
            mesgs = await core.stormlist(f'$lib.trigger.get({othr}).move({mainview})')
            self.stormIsInErr('Cannot move invalid trigger', mesgs)

            mesgs = await core.stormlist('trigger.list')
            self.stormNotInPrint(othr, mesgs)
            mesgs = await core.stormlist('trigger.list', opts=forkopts)
            self.stormIsInPrint(othr, mesgs)
            mesgs = await core.stormlist('trigger.list --all')
            self.stormIsInPrint(othr, mesgs)

            # fix that trigger in another view
            await core.stormlist(f'trigger.mod {othr} {{ [ +#neato.trigger ] }}')
            othrtrig = await core.callStorm(f'return($lib.trigger.get({othr}))')
            self.eq('[ +#neato.trigger ]', othrtrig['storm'])

            # now we can move it while being in a different view
            await core.nodes(f'$lib.trigger.get({othr}).move({mainview})')
            # but still retrieve it from the other view
            self.nn(await core.callStorm(f'return($lib.trigger.get({othr}))', opts=forkopts))

            await core.nodes(f'$lib.trigger.get({trig}).move({forkview})')

            nodes = await core.nodes('[ test:str=test2 ]')
            self.none(nodes[0].tags.get('tagged'))

            nodes = await core.nodes('[ test:str=test3 ]', opts=forkopts)
            self.nn(nodes[0].tags.get('tagged'))

            await core.nodes(f'$lib.trigger.get({trig}).move({mainview})', opts=forkopts)
            nodes = await core.nodes('[ test:str=test4 ]')
            self.nn(nodes[0].tags.get('tagged'))

            with self.raises(s_exc.NoSuchView):
                await core.nodes(f'$lib.trigger.get({trig}).move(newp)')

            q = '''
                $tdef = ({
                    "condition": 'node:add',
                    "form": 'test:str',
                    "storm": '{[ +#tagged ]}',
                    "iden": $trig
                })
                $trig = $lib.trigger.add($tdef)
                return($trig.iden)
            '''
            with self.raises(s_exc.DupIden):
                await core.callStorm(q, opts={'view': forkview, 'vars': {'trig': trig}})

            # toggle trigger in other view
            mesgs = await core.stormlist(f'trigger.disable {othr}')
            self.stormIsInPrint(f'Disabled trigger: {othr}', mesgs)

            mesgs = await core.stormlist(f'trigger.enable {othr}')
            self.stormIsInPrint(f'Enabled trigger: {othr}', mesgs)

            mesgs = await core.stormlist(f'trigger.mod {othr} {{ [ +#burrito ] }}')
            self.stormIsInPrint(f'Modified trigger: {othr}', mesgs)

            await core.stormlist(f'trigger.del {othr}')
            await self.asyncraises(s_exc.NoSuchIden, core.callStorm(f'return($lib.trigger.get({othr}))'))

            # Test manipulating triggers as another user
            bond = await core.auth.addUser('bond')

            async with core.getLocalProxy(user='bond') as asbond:

                q = 'trigger.list'
                mesgs = await asbond.storm(q).list()
                self.stormIsInPrint('No triggers found', mesgs)

                q = f'trigger.mod {goodbuid2} {{[ test:str=yep ]}}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('iden does not match any', mesgs)

                q = f'trigger.disable {goodbuid2}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('iden does not match any', mesgs)

                q = f'trigger.enable {goodbuid2}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('iden does not match any', mesgs)

                q = f'trigger.del {goodbuid2}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('iden does not match any', mesgs)

                q = 'trigger.add node:add --form test:str --query {[ test:int=1 ]}'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('must have permission trigger.add', mesgs)

                # Give explicit perm

                await prox.addUserRule(bond.iden, (True, ('trigger', 'add')))
                mesgs = await asbond.storm(q).list()

                q = 'trigger.list'
                mesgs = await asbond.storm(q).list()
                self.stormIsInPrint('bond', mesgs)

                await prox.addUserRule(bond.iden, (True, ('trigger', 'get')))

                mesgs = await asbond.storm('trigger.list').list()
                self.stormIsInPrint('user', mesgs)
                self.stormIsInPrint('root', mesgs)

                await prox.addUserRule(bond.iden, (True, ('trigger', 'set')))

                mesgs = await asbond.storm(f'trigger.mod {goodbuid2} {{[ test:str=yep ]}}').list()
                self.stormIsInPrint('Modified trigger', mesgs)

                mesgs = await asbond.storm(f'trigger.disable {goodbuid2}').list()
                self.stormIsInPrint('Disabled trigger', mesgs)

                mesgs = await asbond.storm(f'trigger.enable {goodbuid2}').list()
                self.stormIsInPrint('Enabled trigger', mesgs)

                await prox.addUserRule(bond.iden, (True, ('trigger', 'del')))

                mesgs = await asbond.storm(f'trigger.del {goodbuid2}').list()
                self.stormIsInPrint('Deleted trigger', mesgs)

                # Move trigger perms

                await prox.delUserRule(bond.iden, (True, ('trigger', 'add')))
                await prox.delUserRule(bond.iden, (True, ('trigger', 'del')))

                q = f'$lib.trigger.get({trig}).move({forkview})'
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('must have permission view.read', mesgs)

                await prox.addUserRule(bond.iden, (True, ('view', 'read')), gateiden=forkview)
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('must have permission trigger.add', mesgs)

                await prox.addUserRule(bond.iden, (True, ('trigger', 'add')), gateiden=forkview)
                mesgs = await asbond.storm(q).list()
                self.stormIsInErr('must have permission trigger.del', mesgs)

                await prox.addUserRule(bond.iden, (True, ('trigger', 'del')), gateiden=trig)
                mesgs = await asbond.storm(q).list()

                await prox.addUserRule(bond.iden, (True, ('node',)))

                msgs = await asbond.storm('[ test:str=test5 ]', opts={'view': forkview}).list()
                pode = [m[1] for m in msgs if m[0] == 'node'][0]
                self.nn(pode[1]["tags"].get('tagged'))

                msgs = await asbond.storm('[ test:str=test6 ]').list()
                pode = [m[1] for m in msgs if m[0] == 'node'][0]
                self.none(pode[1]["tags"].get('tagged'))

    async def test_storm_lib_cron_notime(self):
        # test cron APIs that don't require time stepping

        async with self.getTestCore() as core:

            cdef = await core.callStorm('return($lib.cron.add(query="{[tel:mob:telem=*]}", hourly=30).pack())')
            self.eq('', cdef.get('doc'))
            self.eq('', cdef.get('name'))

            iden = cdef.get('iden')
            opts = {'vars': {'iden': iden}}

            cdef = await core.callStorm('return($lib.cron.get($iden).set(name, foobar))', opts=opts)
            self.eq('foobar', cdef.get('name'))

            cdef = await core.callStorm('return($lib.cron.get($iden).set(doc, foodoc))', opts=opts)
            self.eq('foodoc', cdef.get('doc'))

            with self.raises(s_exc.BadArg):
                await core.callStorm('return($lib.cron.get($iden).set(hehe, haha))', opts=opts)

            mesgs = await core.stormlist('cron.add --hour +1 {[tel:mob:telem=*]} --name myname --doc mydoc')
            for mesg in mesgs:
                if mesg[0] == 'print':
                    iden0 = mesg[1]['mesg'].split(' ')[-1]

            opts = {'vars': {'iden': iden0}}

            # for coverage...
            self.false(await core.killCronTask('newp'))
            self.false(await core._killCronTask('newp'))
            self.false(await core.callStorm(f'return($lib.cron.get({iden0}).kill())'))

            cdef = await core.callStorm('return($lib.cron.get($iden).pack())', opts=opts)
            self.eq('mydoc', cdef.get('doc'))
            self.eq('myname', cdef.get('name'))

            cdef = await core.callStorm('$cron=$lib.cron.get($iden) return ( $cron.set(name, lolz) )', opts=opts)
            self.eq('lolz', cdef.get('name'))

            cdef = await core.callStorm('$cron=$lib.cron.get($iden) return ( $cron.set(doc, zoinks) )', opts=opts)
            self.eq('zoinks', cdef.get('doc'))

    async def test_storm_lib_cron(self):

        MONO_DELT = 1543827303.0
        unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=0, tzinfo=tz.utc).timestamp()

        def timetime():
            return unixtime

        def looptime():
            return unixtime - MONO_DELT

        loop = asyncio.get_running_loop()

        with mock.patch.object(loop, 'time', looptime), mock.patch('time.time', timetime):

            async with self.getTestCoreAndProxy() as (core, prox):

                mesgs = await core.stormlist('cron.list')
                self.stormIsInPrint('No cron jobs found', mesgs)

                q = '$lib.cron.add()'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Query parameter is required', mesgs)

                q = 'cron.add foo'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Must provide at least one optional argument', mesgs)

                q = "cron.add --month nosuchmonth --day=-2 {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Failed to parse fixed parameter "nosuchmonth"', mesgs)

                q = "cron.add --month 8nosuchmonth --day=-2 {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Failed to parse fixed parameter "8nosuchmonth"', mesgs)

                mesgs = await core.stormlist('cron.add --day="," {#foo}')
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = "cron.add --day Mon --month +3 {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('provide a recurrence value with day of week', mesgs)

                q = "cron.add --day Mon --month June {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('fix month or year with day of week', mesgs)

                q = "cron.add --day Mon --month +3 --year +2 {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('more than 1 recurrence', mesgs)

                q = "cron.add --year=2019 {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Year may not be a fixed value', mesgs)

                q = "cron.add {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Must provide at least one optional', mesgs)

                q = "cron.add --hour 3 --minute +4 {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Fixed unit may not be larger', mesgs)

                q = 'cron.add --day Tuesday,1 {#foo}'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = 'cron.add --day 1,Tuesday {#foo}'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = 'cron.add --day Fri,3 {#foo}'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Failed to parse day value', mesgs)

                q = "cron.add --minute +4x {#foo}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Failed to parse parameter', mesgs)

                q = 'cron.add }'
                mesgs = await core.stormlist(q)
                self.stormIsInErr("Unexpected token '}' at line 1, column 10", mesgs)

                ##################
                layr = core.getLayer()
                nextlayroffs = await layr.getEditOffs() + 1

                # Start simple: add a cron job that creates a node every minute
                q = "cron.add --minute +1 {[meta:note='*' :type=m1]}"
                mesgs = await core.stormlist(q)
                self.stormIsInPrint('Created cron job', mesgs)
                for mesg in mesgs:
                    if mesg[0] == 'print':
                        guid = mesg[1]['mesg'].split(' ')[-1]

                await core.nodes('$lib.queue.add(foo)')

                async def getNextFoo():
                    return await core.callStorm('''
                        $foo = $lib.queue.get(foo)
                        ($offs, $valu) = $foo.get()
                        $foo.cull($offs)
                        return($valu)
                    ''')

                async def getFooSize():
                    return await core.callStorm('''
                        return($lib.queue.get(foo).size())
                    ''')

                async def getCronIden():
                    return await core.callStorm('''
                        $jobs=$lib.cron.list() $job=$jobs.index(0) return ($job.iden)
                    ''')

                @contextlib.asynccontextmanager
                async def getCronJob(text):
                    msgs = await core.stormlist(text)
                    self.stormIsInPrint('Created cron job', msgs)
                    guid = await getCronIden()
                    yield guid
                    msgs = await core.stormlist(f'cron.del {guid}')
                    self.stormIsInPrint(f'Deleted cron job: {guid}', msgs)

                unixtime += 60
                mesgs = await core.stormlist('cron.list')
                self.stormIsInPrint(':type=m1', mesgs)

                # Make sure it ran
                await layr.waitEditOffs(nextlayroffs, timeout=5)
                self.eq(1, await prox.count('meta:note:type=m1'))

                q = "cron.mod $guid { [meta:note='*' :type=m2] }"
                mesgs = await core.stormlist(q, opts={'vars': {'guid': guid[:6]}})
                self.stormIsInPrint(f'Modified cron job: {guid}', mesgs)

                q = "cron.mod xxx { [meta:note='*' :type=m2] }"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('does not match', mesgs)

                # Make sure the old one didn't run and the new query ran
                nextlayroffs = await layr.getEditOffs() + 1
                unixtime += 60
                await layr.waitEditOffs(nextlayroffs, timeout=5)
                self.eq(1, await prox.count('meta:note:type=m1'))
                self.eq(1, await prox.count('meta:note:type=m2'))

                # Delete the job
                q = f"cron.del {guid}"
                mesgs = await core.stormlist(q)
                self.stormIsInPrint('Deleted cron job', mesgs)

                q = f"cron.del xxx"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('does not match', mesgs)

                # Make sure deleted job didn't run
                unixtime += 60
                self.eq(1, await prox.count('meta:note:type=m1'))
                self.eq(1, await prox.count('meta:note:type=m2'))

                # Test fixed minute, i.e. every hour at 17 past
                unixtime = datetime.datetime(year=2018, month=12, day=5, hour=7, minute=10,
                                             tzinfo=tz.utc).timestamp()

                q = '{$lib.queue.get(foo).put(m3) $s=$lib.str.format("m3 {t} {i}", t=$auto.type, i=$auto.iden) $lib.log.info($s, ({"iden": $auto.iden})) }'
                text = f'cron.add --minute 17 {q}'
                async with getCronJob(text) as guid:
                    with self.getStructuredAsyncLoggerStream('synapse.storm.log', 'm3 cron') as stream:
                        unixtime += 7 * MINSECS
                        self.eq('m3', await getNextFoo())
                        self.true(await stream.wait(6))
                    mesg = stream.jsonlines()[0]
                    self.eq(mesg['message'], f'm3 cron {guid}')
                    self.eq(mesg['iden'], guid)

                ##################

                # Test day increment
                async with getCronJob("cron.add --day +2 {$lib.queue.get(foo).put(d1)}") as guid:

                    unixtime += DAYSECS

                    # Make sure it *didn't* run
                    self.eq(0, await getFooSize())

                    unixtime += DAYSECS

                    # Make sure it runs.  We add the cron.list to give the cron scheduler a chance to run
                    self.eq('d1', await getNextFoo())

                    unixtime += DAYSECS * 2

                    self.eq('d1', await getNextFoo())

                ##################

                # Test fixed day of week: every Monday and Thursday at 3am
                unixtime = datetime.datetime(year=2018, month=12, day=11, hour=7, minute=10,
                                             tzinfo=tz.utc).timestamp()  # A Tuesday

                async with getCronJob("cron.add --hour 3 --day Mon,Thursday {$lib.queue.get(foo).put(d2)}") as guid:

                    unixtime = datetime.datetime(year=2018, month=12, day=13, hour=3, minute=10,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    self.eq('d2', await getNextFoo())

                ##################

                q = "cron.add --hour 3 --day Noday {}"
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Failed to parse day value "Noday"', mesgs)

                ##################

                # Test fixed day of month: second-to-last day of month
                async with getCronJob("cron.add --day -2 --month Dec {$lib.queue.get(foo).put(d3)}") as guid:

                    unixtime = datetime.datetime(year=2018, month=12, day=29, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    # self.eq('d3', await getNextFoo())
                    self.eq(0, await getFooSize())

                    unixtime += DAYSECS

                    self.eq('d3', await getNextFoo())

                ##################

                # Test month increment

                async with getCronJob("cron.add --month +2 --day=4 {$lib.queue.get(foo).put(month1)}") as guid:

                    unixtime = datetime.datetime(year=2019, month=2, day=4, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    self.eq('month1', await getNextFoo())

                ##################

                # Test year increment

                async with getCronJob("cron.add --year +2 {$lib.queue.get(foo).put(year1)}") as guid:

                    unixtime = datetime.datetime(year=2021, month=1, day=1, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp() + 1  # Now Thursday

                    self.eq('year1', await getNextFoo())

                # Make sure second-to-last day works for February
                async with getCronJob("cron.add --month February --day=-2 {$lib.queue.get(foo).put(year2)}") as guid:

                    unixtime = datetime.datetime(year=2021, month=2, day=27, hour=0, minute=0,
                                                 tzinfo=tz.utc).timestamp() + 1  # Now Thursday

                    self.eq('year2', await getNextFoo())

                ##################

                # Test 'at' command
                q = 'cron.at {#foo}'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('At least', mesgs)

                q = 'cron.at --minute +1p3arsec {#foo}'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Trouble parsing', mesgs)

                q = 'cron.at --day +1'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('The argument <query> is required', mesgs)

                q = 'cron.at --dt nope {#foo}'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Trouble parsing', mesgs)

                q = '$lib.cron.at(day="+1")'
                mesgs = await core.stormlist(q)
                self.stormIsInErr('Query parameter is required', mesgs)

                q = "cron.at --minute +5,+10 {$lib.queue.get(foo).put(at1)}"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('Created cron job', msgs)

                q = "cron.cleanup"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('0 cron/at jobs deleted.', msgs)

                unixtime += 5 * MINSECS
                core.agenda._wake_event.set()

                self.eq('at1', await getNextFoo())

                # Shouldn't delete yet, still one more run scheduled
                q = "cron.cleanup"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('0 cron/at jobs deleted.', msgs)

                unixtime += 5 * MINSECS
                core.agenda._wake_event.set()

                self.eq('at1', await getNextFoo())

                q = "cron.cleanup"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('1 cron/at jobs deleted.', msgs)

                async with getCronJob("cron.at --day +1,+7 {$lib.queue.get(foo).put(at2)}"):

                    unixtime += DAYSECS
                    core.agenda._wake_event.set()

                    self.eq('at2', await getNextFoo())

                    unixtime += 6 * DAYSECS + 1

                    self.eq('at2', await getNextFoo())

                ##################

                async with getCronJob("cron.at --dt 202104170415 {$lib.queue.get(foo).put(at3)}") as guid:

                    unixtime = datetime.datetime(year=2021, month=4, day=17, hour=4, minute=15,
                                                 tzinfo=tz.utc).timestamp()  # Now Thursday

                    core.agenda._wake_event.set()
                    self.eq('at3', await getNextFoo())

                    mesgs = await core.stormlist(f'cron.stat {guid[:6]}')

                    self.stormIsInPrint('last result:     finished successfully with 0 nodes', mesgs)
                    self.stormIsInPrint('entries:         <None>', mesgs)
                    self.stormIsInPrint('pool:            false', mesgs)

                    # Test 'stat' command
                    mesgs = await core.stormlist('cron.stat xxx')
                    self.stormIsInErr('Provided iden does not match any', mesgs)

                    # Test 'enable' 'disable' commands
                    mesgs = await core.stormlist(f'cron.enable xxx')
                    self.stormIsInErr('Provided iden does not match any', mesgs)

                    mesgs = await core.stormlist(f'cron.disable xxx')
                    self.stormIsInErr('Provided iden does not match any', mesgs)

                    mesgs = await core.stormlist(f'cron.disable {guid[:6]}')
                    self.stormIsInPrint(f'Disabled cron job: {guid}', mesgs)

                    mesgs = await core.stormlist(f'cron.stat {guid[:6]}')
                    self.stormIsInPrint('enabled:         N', mesgs)

                    mesgs = await core.stormlist(f'cron.enable {guid[:6]}')
                    self.stormIsInPrint(f'Enabled cron job: {guid}', mesgs)

                    mesgs = await core.stormlist(f'cron.stat {guid[:6]}')
                    self.stormIsInPrint('enabled:         Y', mesgs)

                ##################

                # Test --now
                q = "cron.at --now {$lib.queue.get(foo).put(atnow)}"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('Created cron job', msgs)

                self.eq('atnow', await getNextFoo())

                q = "cron.cleanup"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('1 cron/at jobs deleted.', msgs)

                q = "cron.at --now --minute +5 {$lib.queue.get(foo).put(atnow)}"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('Created cron job', msgs)

                self.eq('atnow', await getNextFoo())

                # Shouldn't delete yet, still one more run scheduled
                q = "cron.cleanup"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('0 cron/at jobs deleted.', msgs)

                unixtime += 5 * MINSECS
                core.agenda._wake_event.set()

                self.eq('atnow', await getNextFoo())

                q = "cron.cleanup"
                msgs = await core.stormlist(q)
                self.stormIsInPrint('1 cron/at jobs deleted.', msgs)

                opts = {'vars': {'iden': '21d87b933f43ca3b192d2579d3a6a08e'}}
                q = "cron.at --iden $iden --hour 4 {[test:guid=$lib.guid()]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Created cron job: 21d87b933f43ca3b192d2579d3a6a08e', msgs)

                q = "cron.del $iden"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Deleted cron job: 21d87b933f43ca3b192d2579d3a6a08e', msgs)

                ##################
                # Test --iden
                q = "cron.add --iden invalididen --hour +7 {[test:guid=$lib.guid()]}"
                msgs = await core.stormlist(q)
                self.stormIsInErr('data.iden must match pattern', msgs)

                opts = {'vars': {'iden': 'cd263bd133a5dafa1e1c5e9a01d9d486'}}
                q = "cron.add --pool --iden $iden --day +1 --minute 14 {[test:guid=$lib.guid()]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Created cron job: cd263bd133a5dafa1e1c5e9a01d9d486', msgs)

                q = "cron.add --iden $iden --minute +86400 {[test:guid=$lib.guid()]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (cd263bd133a5dafa1e1c5e9a01d9d486)', msgs)

                q = "cron.del $iden"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Deleted cron job: cd263bd133a5dafa1e1c5e9a01d9d486', msgs)

                opts = {'vars': {'iden': 'b5f74c417dd67aa38142f2be9567cc12'}}
                q = "cron.add --iden $iden --month +2 --hour 4 {[test:guid=$lib.guid()]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Created cron job: b5f74c417dd67aa38142f2be9567cc12', msgs)

                q = "cron.add --iden $iden --day +62 --hour 4 {[test:guid=$lib.guid()]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (b5f74c417dd67aa38142f2be9567cc12)', msgs)

                q = "cron.add --iden $iden --month +4 --hour 4 {[test:guid=$lib.guid()]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (b5f74c417dd67aa38142f2be9567cc12)', msgs)

                q = "cron.del $iden"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Deleted cron job: ', msgs)

                opts = {'vars': {'iden': '9d893f731df9777b2937cb5a7895970b'}}
                q = "cron.add --iden $iden --hour 0,2 --day Sat {[test:int=5]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Created cron job: 9d893f731df9777b2937cb5a7895970b', msgs)

                q = "cron.add --iden $iden --hour 2,0 --day Mon {[test:int=5]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (9d893f731df9777b2937cb5a7895970b)', msgs)

                q = "cron.add --iden $iden --hour 2,0 --month 3 {[test:int=5]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (9d893f731df9777b2937cb5a7895970b)', msgs)

                q = "cron.add --iden $iden --month +3 --hour 2,3 --minute 10,30 {[test:int=5]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (9d893f731df9777b2937cb5a7895970b)', msgs)

                q = "cron.add --iden $iden --hour 2,3 --day Sat {[test:int=5]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (9d893f731df9777b2937cb5a7895970b)', msgs)

                q = "cron.add --iden $iden --month 2 --day +2 {[test:int=5]}"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInErr('Duplicate cron iden (9d893f731df9777b2937cb5a7895970b)', msgs)

                q = "cron.del $iden"
                msgs = await core.stormlist(q, opts=opts)
                self.stormIsInPrint('Deleted cron job: ', msgs)

                # Test that stating a failed cron prints failures
                async with getCronJob("cron.at --now {$lib.queue.get(foo).put(atnow) $lib.newp}") as guid:
                    self.eq('atnow', await getNextFoo())
                    mesgs = await core.stormlist(f'cron.stat {guid[:6]}')
                    print_str = '\n'.join([m[1].get('mesg') for m in mesgs if m[0] == 'print'])
                    self.nn(re.search("# errors:.+1", print_str))
                    self.nn(re.search("most recent errors:\n[^\n]+Cannot find name", print_str))

                ##################
                # Test the aliases
                async with getCronJob('cron.add --hourly 15 {#foo}') as guid:
                    mesgs = await core.stormlist(f'cron.stat {guid[:6]}')
                    self.stormIsInPrint("{'minute': 15}", mesgs)

                async with getCronJob('cron.add --daily 05:47 {#bar}') as guid:
                    mesgs = await core.stormlist(f'cron.stat {guid[:6]}')
                    self.stormIsInPrint("{'hour': 5, 'minute': 47", mesgs)

                async with getCronJob('cron.add --monthly=-1:12:30 {#bar}') as guid:
                    mesgs = await core.stormlist(f'cron.stat {guid[:6]}')
                    self.stormIsInPrint("{'hour': 12, 'minute': 30, 'dayofmonth': -1}", mesgs)

                # leave this job around for the subsequent tests
                mesgs = await core.stormlist('cron.add --yearly 04:17:12:30 {#bar}')
                self.stormIsInPrint('Created cron job', mesgs)
                guid = await getCronIden()

                mesgs = await core.stormlist(f'cron.stat {guid[:6]}')
                self.stormIsInPrint("{'month': 4, 'hour': 12, 'minute': 30, 'dayofmonth': 17}", mesgs)

                mesgs = await core.stormlist('cron.add --yearly 04:17:12 {#bar}')
                self.stormIsInErr('Failed to parse parameter', mesgs)

                mesgs = await core.stormlist('cron.add --daily xx:xx {#bar}')
                self.stormIsInErr('Failed to parse ..ly parameter', mesgs)

                mesgs = await core.stormlist('cron.add --hourly 1 --minute 17 {#bar}')
                self.stormIsInErr('May not use both', mesgs)

                # Test manipulating cron jobs as another user
                bond = await core.auth.addUser('bond')

                async with core.getLocalProxy(user='bond') as asbond:

                    mesgs = await asbond.storm('cron.list').list()
                    self.isin('err', (m[0] for m in mesgs))

                    mesgs = await asbond.storm(f'cron.disable {guid[:6]}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    mesgs = await asbond.storm(f'cron.enable {guid[:6]}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    mesgs = await asbond.storm(f'cron.mod {guid[:6]} {{#foo}}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    mesgs = await asbond.storm(f'cron.del {guid[:6]}').list()
                    self.stormIsInErr('iden does not match any', mesgs)

                    mesgs = await asbond.storm('cron.add --hourly 15 {#bar}').list()
                    self.stormIsInErr('must have permission cron.add', mesgs)

                    # Give explicit perm

                    await prox.addUserRule(bond.iden, (True, ('cron', 'add')))
                    await prox.addUserRule(bond.iden, (True, ('cron', 'get')))

                    await asbond.storm('cron.add --hourly 15 {#bar}').list()

                    mesgs = await asbond.storm('cron.list').list()
                    self.stormIsInPrint('bond', mesgs)

                    mesgs = await asbond.storm('cron.list').list()
                    self.stormIsInPrint('user', mesgs)
                    self.stormIsInPrint('root', mesgs)

                    await prox.addUserRule(bond.iden, (True, ('cron', 'set')))

                    mesgs = await asbond.storm(f'cron.disable {guid[:6]}').list()
                    self.stormIsInPrint('Disabled cron job', mesgs)

                    mesgs = await asbond.storm(f'cron.enable {guid[:6]}').list()
                    self.stormIsInPrint('Enabled cron job', mesgs)

                    mesgs = await asbond.storm(f'cron.mod {guid[:6]} {{#foo}}').list()
                    self.stormIsInPrint('Modified cron job', mesgs)

                    await prox.addUserRule(bond.iden, (True, ('cron', 'del')))

                    mesgs = await asbond.storm(f'cron.del {guid[:6]}').list()
                    self.stormIsInPrint('Deleted cron job', mesgs)

    async def test_storm_lib_userview(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.setAdmin(True)

            opts = {'user': visi.iden}
            await core.nodes('$lib.user.profile.set(cortex:view, $lib.view.get().fork().iden)', opts=opts)

            self.nn(visi.profile.get('cortex:view'))

            self.len(1, await core.nodes('[ inet:ipv4=1.2.3.4 ]', opts=opts))

            self.len(0, await core.nodes('inet:ipv4=1.2.3.4'))

            self.len(1, await core.nodes('inet:ipv4=1.2.3.4', opts=opts))
            self.len(0, await core.nodes('inet:ipv4=1.2.3.4', opts={'user': visi.iden, 'view': core.view.iden}))

            async with core.getLocalProxy(user='visi') as prox:
                self.eq(1, await prox.count('inet:ipv4=1.2.3.4'))
                self.eq(0, await prox.count('inet:ipv4=1.2.3.4', opts={'view': core.view.iden}))

            async with core.getLocalProxy(user='root') as prox:
                self.eq(0, await prox.count('inet:ipv4=1.2.3.4'))

    async def test_storm_lib_lift(self):

        async with self.getTestCore() as core:

            await core.nodes('[ inet:ipv4=5.5.5.5 ]')
            await core.nodes('[ inet:ipv4=1.2.3.4 ] $node.data.set(hehe, haha) $node.data.set(lulz, rofl)')

            nodes = await core.nodes('yield $lib.lift.byNodeData(newp) $node.data.load(lulz)')
            self.len(0, nodes)

            nodes = await core.nodes('yield $lib.lift.byNodeData(hehe) $node.data.load(lulz)')
            self.len(1, nodes)
            self.eq(('inet:ipv4', 0x01020304), nodes[0].ndef)
            self.eq('haha', nodes[0].nodedata['hehe'])
            self.eq('haha', nodes[0].pack()[1]['nodedata']['hehe'])
            self.eq('rofl', nodes[0].nodedata['lulz'])
            self.eq('rofl', nodes[0].pack()[1]['nodedata']['lulz'])

            # Since the nodedata is loaded right away, getting the data shortcuts the layer
            q = 'yield $lib.lift.byNodeData(hehe) $lib.print($node.data.get(hehe))'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('haha', msgs)

            nodes = await core.nodes('inet:ipv4=1.2.3.4 $node.data.pop(hehe)')
            self.len(0, await core.nodes('yield $lib.lift.byNodeData(hehe)'))

    async def test_stormtypes_node(self):

        async with self.getTestCore() as core:

            nodes = await core.nodes('[ test:int=10 test:str=$node.iden() ] +test:str')
            iden = s_common.ehex(s_common.buid(('test:int', 10)))
            self.eq(nodes[0].ndef, ('test:str', iden))
            self.len(1, nodes)

            await core.nodes('[ inet:ipv4=1.2.3.4 :asn=20 ]')
            self.eq(20, await core.callStorm('inet:ipv4=1.2.3.4 return($node.props.get(asn))'))
            self.isin(('asn', 20), await core.callStorm('inet:ipv4=1.2.3.4 return($node.props.list())'))

            fakeuser = await core.auth.addUser('fakeuser')
            opts = {'user': fakeuser.iden}
            with self.raises(s_exc.NoSuchProp):
                await core.callStorm('inet:ipv4=1.2.3.4 return($node.props.set(lolnope, 42))')
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('inet:ipv4=1.2.3.4 return($node.props.set(dns:rev, "vertex.link"))', opts=opts)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('inet:ipv4=1.2.3.4 $node.props."dns:rev" = "vertex.link"', opts=opts)

            await fakeuser.addRule((True, ('node', 'prop', 'set')))
            retn = await core.callStorm('inet:ipv4=1.2.3.4 return($node.props.set(dns:rev, "vertex.link"))', opts=opts)
            self.true(retn)
            node = await core.nodes('inet:ipv4=1.2.3.4')
            self.eq(node[0].props['dns:rev'], 'vertex.link')

            retn = await core.callStorm('inet:ipv4=1.2.3.4 return($node.props.set(dns:rev, "foo.bar.com"))', opts=opts)
            self.true(retn)
            node = await core.nodes('inet:ipv4=1.2.3.4')
            self.eq(node[0].props['dns:rev'], 'foo.bar.com')

            props = await core.callStorm('inet:ipv4=1.2.3.4 return($node.props)')
            self.eq(20, props['asn'])

            self.eq(0x01020304, await core.callStorm('inet:ipv4=1.2.3.4 return($node)'))

            with self.raises(s_exc.StormRuntimeError) as cm:
                _ = await core.nodes('inet:ipv4=1.2.3.4 $lib.print($lib.len($node))')
            self.eq(cm.exception.get('mesg'), 'Object synapse.lib.node.Node does not have a length.')

            nodes = await core.nodes('[test:guid=(beep,)] $node.props.size="12"')
            self.eq(12, nodes[0].get('size'))
            nodes = await core.nodes('[test:guid=(beep,)] $node.props.".seen"=2020')
            self.eq((1577836800000, 1577836800001), nodes[0].get('.seen'))

            text = '$d=({}) test:guid=(beep,) { for ($name, $valu) in $node.props { $d.$name=$valu } } return ($d)'
            props = await core.callStorm(text)
            self.eq(12, props.get('size'))
            self.eq((1577836800000, 1577836800001), props.get('.seen'))
            self.isin('.created', props)

            with self.raises(s_exc.NoSuchProp):
                self.true(await core.callStorm('[test:guid=(beep,)] $node.props.newp="noSuchProp"'))
            with self.raises(s_exc.BadTypeValu):
                self.true(await core.callStorm('[test:guid=(beep,)] $node.props.size=(foo, bar)'))

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('inet:ipv4=1.2.3.4 $node.props."dns:rev" = $lib.undef', opts=opts)

            nodes = await core.nodes('inet:ipv4=1.2.3.4')
            self.nn(nodes[0].props.get('dns:rev'))

            await fakeuser.addRule((True, ('node', 'prop', 'del')))
            nodes = await core.nodes('inet:ipv4=1.2.3.4 $node.props."dns:rev" = $lib.undef', opts=opts)
            self.none(nodes[0].props.get('dns:rev'))

            await core.nodes('$n=$lib.null inet:ipv4=1.2.3.4 $n=$node spin | $n.props."dns:rev" = "vertex.link"')
            nodes = await core.nodes('inet:ipv4=1.2.3.4')
            self.eq(nodes[0].props.get('dns:rev'), 'vertex.link')

            with self.raises(s_exc.NoSuchProp):
                self.true(await core.callStorm('[test:guid=(beep,)] $node.props.newp = $lib.undef'))

    async def test_stormtypes_toprim(self):

        async with self.getTestCore() as core:

            orig = {'hehe': 20, 'haha': (1, 2, 3), 'none': None, 'bool': True}
            valu = await core.callStorm('return($valu)', opts={'vars': {'valu': orig}})

            self.eq(valu['hehe'], 20)
            self.eq(valu['haha'], (1, 2, 3))
            self.eq(valu['none'], None)
            self.eq(valu['bool'], True)

            q = '$list = () $list.append(foo) $list.append(bar) return($list)'
            self.eq(('foo', 'bar'), await core.callStorm(q))
            self.eq({'foo': 'bar'}, await core.callStorm('$dict = ({}) $dict.foo = bar return($dict)'))
            q = '$tally = $lib.stats.tally() $tally.inc(foo) $tally.inc(foo) return($tally)'
            self.eq({'foo': 2}, await core.callStorm(q))

    async def test_print_warn(self):
        async with self.getTestCore() as core:
            q = '$lib.print(hello)'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('hello', msgs)

            q = '$name="moto" $lib.print("hello {name}", name=$name)'
            msgs = await core.stormlist(q)
            self.stormIsInPrint('hello moto', msgs)

            q = '$name="moto" $lib.warn("hello {name}", name=$name)'
            msgs = await core.stormlist(q)
            self.stormIsInWarn('hello moto', msgs)

    async def test_stormtypes_tofoo(self):

        boolprim = s_stormtypes.Bool(True)

        self.eq(20, await s_stormtypes.toint(20))
        self.eq(20, await s_stormtypes.toint('20'))
        self.eq(20, await s_stormtypes.toint(s_stormtypes.Str('20')))
        self.eq(20, await s_stormtypes.toint(s_stormtypes.Number('20')))

        self.eq('asdf', await s_stormtypes.tostr('asdf'))
        self.eq('asdf', await s_stormtypes.tostr(s_stormtypes.Str('asdf')))
        self.eq('asdf', await s_stormtypes.tostr(s_stormtypes.Bytes(b'asdf')))
        self.eq(True, await s_stormtypes.tobool(s_stormtypes.Bytes(b'asdf')))

        self.eq((1, 3), await s_stormtypes.toprim([1, s_exc.SynErr, 3]))
        self.eq({'foo': 'bar'}, (await s_stormtypes.toprim({'foo': 'bar', 'exc': s_exc.SynErr})))

        self.eq(1, await s_stormtypes.toint(s_stormtypes.Bool(True)))
        self.eq('true', await s_stormtypes.tostr(s_stormtypes.Bool(True)))
        self.eq(True, await s_stormtypes.tobool(s_stormtypes.Bool(True)))

        self.true(await s_stormtypes.tobool(boolprim))
        self.true(await s_stormtypes.tobool(1))
        self.false(await s_stormtypes.tobool(0))
        self.true(await s_stormtypes.tobool(s_stormtypes.Number('1')))
        self.false(await s_stormtypes.tobool(s_stormtypes.Number('0')))
        # no bool <- int <- str
        self.true(await s_stormtypes.tobool('1'))
        self.true(await s_stormtypes.tobool(s_stormtypes.Str('0')))
        self.true(await s_stormtypes.tobool(s_stormtypes.Str('asdf')))
        self.false(await s_stormtypes.tobool(s_stormtypes.Str('')))

        numb = s_stormtypes.Number('20.1')

        self.eq(20, await s_stormtypes.tonumber('20'))
        self.eq(20.1, await s_stormtypes.tonumber(20.1))
        self.eq(20.1, await s_stormtypes.tonumber('20.1'))
        self.eq(20.1, await s_stormtypes.tonumber(numb))

        self.eq('20.1', await s_stormtypes.tostor(numb))
        self.eq(['20.1', '20.1'], await s_stormtypes.tostor([numb, numb]))
        self.eq({'foo': '20.1'}, await s_stormtypes.tostor({'foo': numb}))
        self.eq((1, 3), await s_stormtypes.tostor([1, s_exc.SynErr, 3]))
        self.eq({'foo': 'bar'}, (await s_stormtypes.tostor({'foo': 'bar', 'exc': s_exc.SynErr})))

        self.eq(True, await s_stormtypes.tocmprvalu(boolprim))
        self.eq((1, s_exc.SynErr), await s_stormtypes.tocmprvalu([1, s_exc.SynErr]))
        self.eq({'exc': s_exc.SynErr}, await s_stormtypes.tocmprvalu({'exc': s_exc.SynErr}))

        with self.raises(s_exc.BadCast):
            await s_stormtypes.toint(s_stormtypes.Prim(()))

        with self.raises(s_exc.BadCast):
            self.eq(20, await s_stormtypes.toint(s_stormtypes.Str('asdf')))

        with self.raises(s_exc.BadCast):
            await s_stormtypes.tobool(Newp())

        with self.raises(s_exc.BadCast):
            await s_stormtypes.tostr(Newp())

        with self.raises(s_exc.BadCast):
            await s_stormtypes.toint(Newp())

        self.none(await s_stormtypes.tostr(None, noneok=True))
        self.none(await s_stormtypes.toint(None, noneok=True))
        self.none(await s_stormtypes.tobool(None, noneok=True))
        self.none(await s_stormtypes.tonumber(None, noneok=True))

    async def test_stormtypes_layer_edits(self):

        async with self.getTestCore() as core:

            await core.nodes('[inet:ipv4=1.2.3.4]')

            # TODO: should we asciify the buid here so it is json compatible?
            q = '''$list = ()
            for ($offs, $edit) in $lib.layer.get().edits(wait=$lib.false) {
                $list.append($edit)
            }
            return($list)'''
            nodeedits = await core.callStorm(q)

            retn = []
            for edits in nodeedits:
                for edit in edits:
                    if edit[1] == 'inet:ipv4':
                        retn.append(edit)

            self.len(1, retn)

    async def test_stormtypes_layer_counts(self):
        async with self.getTestCore() as core:

            self.eq(0, await core.callStorm('return($lib.layer.get().getTagCount(foo.bar))'))
            await core.nodes('[ inet:ipv4=1.2.3.4 inet:ipv4=5.6.7.8 :asn=20 inet:asn=20 +#foo.bar ]')
            self.eq(0, await core.callStorm('return($lib.layer.get().getPropCount(ps:person))'))
            self.eq(2, await core.callStorm('return($lib.layer.get().getPropCount(inet:ipv4))'))
            self.eq(2, await core.callStorm('return($lib.layer.get().getPropCount(inet:ipv4:asn))'))
            self.eq(3, await core.callStorm('return($lib.layer.get().getTagCount(foo.bar))'))
            self.eq(2, await core.callStorm('return($lib.layer.get().getTagCount(foo.bar, formname=inet:ipv4))'))

            self.eq(6, await core.callStorm("return($lib.layer.get().getPropCount('.created'))"))
            self.eq(2, await core.callStorm("return($lib.layer.get().getPropCount(inet:ipv4.created))"))
            self.eq(0, await core.callStorm("return($lib.layer.get().getPropCount('.seen'))"))

            with self.raises(s_exc.NoSuchProp):
                await core.callStorm('return($lib.layer.get().getPropCount(newp:newp))')

            with self.raises(s_exc.NoSuchProp):
                await core.callStorm("return($lib.layer.get().getPropCount('.newp'))")

            await core.nodes('.created | delnode --force')

            await core.addTagProp('score', ('int', {}), {})

            q = '''[
                inet:ipv4=1
                inet:ipv4=2
                inet:ipv4=3
                :asn=4

                (ou:org=*
                 ou:org=*
                 :names=(foo, bar))

                .seen=2020
                .univarray=(1, 2)
                +#foo:score=2

                test:arrayform=(1,2,3)
                test:arrayform=(2,3,4)
            ]'''
            await core.nodes(q)

            q = 'return($lib.layer.get().getPropCount(inet:ipv4:asn, valu=1))'
            self.eq(0, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(inet:ipv4:loc, valu=1))'
            self.eq(0, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(inet:ipv4:asn, valu=4))'
            self.eq(3, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(inet:ipv4.seen, valu=2020))'
            self.eq(3, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(".seen", valu=2020))'
            self.eq(5, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(".test:univ", valu=1))'
            self.eq(0, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(inet:ipv4, valu=1))'
            self.eq(1, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(ou:org:names, valu=(foo, bar)))'
            self.eq(2, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropCount(".univarray", valu=(1, 2)))'
            self.eq(5, await core.callStorm(q))

            with self.raises(s_exc.NoSuchProp):
                q = 'return($lib.layer.get().getPropCount(newp, valu=1))'
                await core.callStorm(q)

            q = 'return($lib.layer.get().getPropArrayCount(ou:org:names))'
            self.eq(4, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropArrayCount(ou:org:names, valu=foo))'
            self.eq(2, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropArrayCount(".univarray"))'
            self.eq(10, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropArrayCount(".univarray", valu=2))'
            self.eq(5, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropArrayCount(test:arrayform))'
            self.eq(6, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropArrayCount(test:arrayform, valu=2))'
            self.eq(2, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropArrayCount(ou:org:subs))'
            self.eq(0, await core.callStorm(q))

            q = 'return($lib.layer.get().getPropArrayCount(ou:org:subs, valu=*))'
            self.eq(0, await core.callStorm(q))

            with self.raises(s_exc.NoSuchProp):
                q = 'return($lib.layer.get().getPropArrayCount(newp, valu=1))'
                await core.callStorm(q)

            with self.raises(s_exc.BadTypeValu):
                q = 'return($lib.layer.get().getPropArrayCount(inet:ipv4, valu=1))'
                await core.callStorm(q)

            q = 'return($lib.layer.get().getTagPropCount(foo, score))'
            self.eq(5, await core.callStorm(q))

            q = 'return($lib.layer.get().getTagPropCount(foo, score, valu=2))'
            self.eq(5, await core.callStorm(q))

            q = 'return($lib.layer.get().getTagPropCount(foo, score, form=ou:org, valu=2))'
            self.eq(2, await core.callStorm(q))

            q = 'return($lib.layer.get().getTagPropCount(bar, score))'
            self.eq(0, await core.callStorm(q))

            q = 'return($lib.layer.get().getTagPropCount(bar, score, valu=2))'
            self.eq(0, await core.callStorm(q))

            with self.raises(s_exc.NoSuchTagProp):
                q = 'return($lib.layer.get().getTagPropCount(foo, newp, valu=2))'
                await core.callStorm(q)

    async def test_stormtypes_prop_uniq_values(self):
        async with self.getTestCore() as core:

            layr1vals = [
                'a' * 512 + 'a',
                'a' * 512 + 'a',
                'a' * 512 + 'c',
                'a' * 512 + 'c',
                'c' * 512,
                'c' * 512,
                'c',
                'c'
            ]
            opts = {'vars': {'vals': layr1vals}}
            await core.nodes('for $val in $vals {[ it:dev:str=$val .seen=2020 ]}', opts=opts)
            await core.nodes('for $val in $vals {[ ou:org=* :name=$val .seen=2021]}', opts=opts)

            layr2vals = [
                'a' * 512 + 'a',
                'a' * 512 + 'a',
                'a' * 512 + 'b',
                'a' * 512 + 'b',
                'b' * 512,
                'b' * 512,
                'b',
                'b'
            ]
            forkview = await core.callStorm('return($lib.view.get().fork().iden)')
            opts = {'view': forkview, 'vars': {'vals': layr2vals}}
            await core.nodes('for $val in $vals {[ it:dev:str=$val .seen=2020]}', opts=opts)
            await core.nodes('for $val in $vals {[ ou:org=* :name=$val .seen=2023]}', opts=opts)

            viewq = '''
            $vals = ([])
            for $valu in $lib.view.get().getPropValues($prop) {
                $vals.append($valu)
            }
            return($vals)
            '''

            layrq = '''
            $vals = ([])
            for $valu in $lib.layer.get().getPropValues($prop) {
                $vals.append($valu)
            }
            return($vals)
            '''

            # Values come out in index order which is not necessarily value order
            opts = {'vars': {'prop': 'it:dev:str'}}
            uniqvals = list(set(layr1vals))
            self.sorteq(uniqvals, await core.callStorm(viewq, opts=opts))
            self.sorteq(uniqvals, await core.callStorm(layrq, opts=opts))

            opts['view'] = forkview
            uniqvals = list(set(layr2vals) - set(layr1vals))
            self.sorteq(uniqvals, await core.callStorm(layrq, opts=opts))

            uniqvals = list(set(layr1vals) | set(layr2vals))
            self.sorteq(uniqvals, await core.callStorm(viewq, opts=opts))

            opts = {'vars': {'prop': 'ou:org:name'}}
            uniqvals = list(set(layr1vals))
            self.sorteq(uniqvals, await core.callStorm(viewq, opts=opts))
            self.sorteq(uniqvals, await core.callStorm(layrq, opts=opts))

            opts['view'] = forkview
            uniqvals = list(set(layr2vals))
            self.sorteq(uniqvals, await core.callStorm(layrq, opts=opts))

            uniqvals = list(set(layr1vals) | set(layr2vals))
            self.sorteq(uniqvals, await core.callStorm(viewq, opts=opts))

            opts = {'vars': {'prop': '.seen'}}

            ival = core.model.type('ival')
            uniqvals = [ival.norm('2020')[0], ival.norm('2021')[0]]
            self.sorteq(uniqvals, await core.callStorm(viewq, opts=opts))
            self.sorteq(uniqvals, await core.callStorm(layrq, opts=opts))

            opts['view'] = forkview
            uniqvals = [ival.norm('2020')[0], ival.norm('2023')[0]]
            self.sorteq(uniqvals, await core.callStorm(layrq, opts=opts))

            uniqvals = [ival.norm('2020')[0], ival.norm('2021')[0], ival.norm('2023')[0]]
            self.sorteq(uniqvals, await core.callStorm(viewq, opts=opts))

            opts['vars']['prop'] = 'ps:contact:name'
            self.eq([], await core.callStorm(viewq, opts=opts))

            opts['vars']['prop'] = 'newp:newp'
            with self.raises(s_exc.NoSuchProp):
                await core.callStorm(layrq, opts=opts)

            with self.raises(s_exc.NoSuchProp):
                await core.callStorm(viewq, opts=opts)

            arryvals = [
                ('foo', 'bar'),
                ('foo', 'bar'),
                ('foo', 'baz'),
                ('bar', 'baz'),
                ('bar', 'foo')
            ]
            opts = {'vars': {'vals': arryvals}}
            await core.nodes('for $val in $vals {[ transport:air:flight=* :stops=$val ]}', opts=opts)

            opts = {'vars': {'prop': 'transport:air:flight:stops'}}
            uniqvals = list(set(arryvals))
            self.sorteq(uniqvals, await core.callStorm(viewq, opts=opts))
            self.sorteq(uniqvals, await core.callStorm(layrq, opts=opts))

            await core.nodes('[ media:news=(bar,) :title=foo ]')
            await core.nodes('[ media:news=(baz,) :title=bar ]')
            await core.nodes('[ media:news=(faz,) :title=faz ]')

            forkopts = {'view': forkview}
            await core.nodes('[ media:news=(baz,) :title=faz ]', opts=forkopts)

            opts = {'vars': {'prop': 'media:news:title'}}
            self.eq(['bar', 'faz', 'foo'], await core.callStorm(viewq, opts=opts))

            opts = {'view': forkview, 'vars': {'prop': 'media:news:title'}}
            self.eq(['faz', 'foo'], await core.callStorm(viewq, opts=opts))

            forkview2 = await core.callStorm('return($lib.view.get().fork().iden)', opts=forkopts)
            forkopts2 = {'view': forkview2}

            await core.nodes('[ ps:contact=(foo,) :name=foo ]', opts=forkopts2)
            await core.nodes('[ ps:contact=(foo,) :name=bar ]', opts=forkopts)
            await core.nodes('[ ps:contact=(bar,) :name=bar ]')

            opts = {'view': forkview2, 'vars': {'prop': 'ps:contact:name'}}
            self.eq(['bar', 'foo'], await core.callStorm(viewq, opts=opts))

            self.eq([], await alist(core.getLayer().iterPropIndxBuids('newp', 'newp', 'newp')))

    async def test_lib_stormtypes_cmdopts(self):
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
                {
                    'name': 'test.cmdopts',
                    'cmdargs': (
                        ('foo', {}),
                        ('--bar', {'default': False, 'action': 'store_true'}),
                        ('--footime', {'default': False, 'type': 'time'}),
                        ('--choice', {'choices': ['choice00', 'choice01']}),
                    ),
                    'storm': '''
                        $lib.print($lib.len($cmdopts))
                        if ($lib.len($cmdopts) = 5) { $lib.print(foo) }

                        $set = $lib.set()
                        for ($name, $valu) in $cmdopts { $set.add($valu) }

                        if ($lib.len($set) = 5) { $lib.print(bar) }

                        if $cmdopts.bar { $lib.print(baz) }

                        if $cmdopts.footime { $lib.print($cmdopts.footime) }

                        if $cmdopts.choice { $lib.print($cmdopts.choice) }
                    '''
                },
                {
                    'name': 'test.setboom',
                    'cmdargs': [
                        ('foo', {}),
                        ('--bar', {'default': False, 'action': 'store_true'}),
                    ],
                    'storm': '''
                        $cmdopts.foo = hehe
                    '''
                },
                {
                    'name': 'test.runtsafety',
                    'cmdargs': [
                        ('foo', {}),
                    ],
                    'storm': '''
                        test:str=$cmdopts.foo
                    '''
                },
            ],
        }
        sadt = {
            'name': 'bar',
            'desc': 'test',
            'version': (0, 0, 1),
            'commands': [
                {
                    'name': 'test.badtype',
                    'cmdargs': [
                        ('--bar', {'type': 'notatype'}),
                    ],
                    'storm': '''
                        $cmdopts.foo = hehe
                    '''
                },
            ],
        }
        sadchoice = {
            'name': 'baz',
            'desc': 'test',
            'version': (0, 0, 1),
            'commands': [
                {
                    'name': 'test.badchoice',
                    'cmdargs': [
                        ('--baz', {'choices': 'newp'}),
                    ],
                    'storm': '''
                        $cmdopts.baz = hehe
                    '''
                },
            ],
        }
        async with self.getTestCore() as core:
            await core.addStormPkg(pdef)
            msgs = await core.stormlist('test.cmdopts hehe --bar --footime 20200101 --choice choice00')
            self.stormIsInPrint('foo', msgs)
            self.stormIsInPrint('bar', msgs)
            self.stormIsInPrint('baz', msgs)
            self.stormIsInPrint('choice00', msgs)
            self.stormIsInPrint('1577836800000', msgs)

            with self.raises(s_exc.BadArg):
                await core.nodes('test.cmdopts hehe --choice newp')

            with self.raises(s_exc.StormRuntimeError):
                await core.nodes('test.setboom hehe --bar')

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(sadt)

            with self.raises(s_exc.SchemaViolation):
                await core.addStormPkg(sadchoice)

            nodes = await core.nodes('[ test:str=foo test:str=bar ] | test.runtsafety $node.repr()')
            self.len(4, nodes)
            ndefs = [n.ndef for n in nodes]
            exp = [('test:str', 'bar'),
                   ('test:str', 'bar'),
                   ('test:str', 'foo'),
                   ('test:str', 'foo')]
            self.sorteq(ndefs, exp)

    async def test_exit(self):
        async with self.getTestCore() as core:
            q = '[test:str=beep.sys] $lib.exit()'
            msgs = await core.stormlist(q)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(0, nodes)

            q = '[test:str=beep.sys] $lib.exit(foo)'
            msgs = await core.stormlist(q)
            self.stormIsInWarn('foo', msgs)

            # Local callstorm behavior keeps the local exception
            import synapse.lib.stormctrl as s_ctrl
            with self.raises(s_ctrl.StormExit) as cm:
                q = '[test:str=beep.sys] $lib.exit(foo)'
                _ = await core.callStorm(q)
            self.eq(cm.exception.get('mesg'), 'foo')

            # Remote tests
            async with core.getLocalProxy() as prox:
                # No message is emitted
                q = '[test:str=beep.sys] $lib.exit()'
                msgs = await prox.storm(q).list()
                self.eq(('init', 'fini'), [m[0] for m in msgs])

                # A exception is raised but no message; this is
                # treated as a generic SynErr by the telepath client.
                q = '[test:str=beep.sys] $lib.exit()'
                with self.raises(s_exc.SynErr) as cm:
                    _ = await prox.callStorm(q)
                self.eq(cm.exception.get('mesg'), 'StormExit: ')
                self.eq(cm.exception.get('errx'), 'StormExit')

                # A warn is emitted
                q = '[test:str=beep.sys] $lib.exit(foo)'
                msgs = await prox.storm(q).list()
                self.stormIsInWarn('foo', msgs)

                # A exception is raised with the message
                q = '[test:str=beep.sys] $lib.exit("foo {bar}", bar=baz)'
                with self.raises(s_exc.SynErr) as cm:
                    _ = await prox.callStorm(q)
                self.eq(cm.exception.get('mesg'), "StormExit: mesg='foo baz'")
                self.eq(cm.exception.get('errx'), 'StormExit')

    async def test_iter(self):
        async with self.getTestCore() as core:
            await self.agenlen(0, s_stormtypes.toiter(None, noneok=True))

            await core.nodes('[inet:ipv4=0] [inet:ipv4=1]')

            # explicit test for a pattern in some stormsvcs
            scmd = '''
            function add() {
                $x=$lib.set()
                inet:ipv4
                $x.add($node)
                fini { return($x) }
            }
            $y=$lib.set() $x=$add() for $n in $x { yield $n }
            '''
            nodes = await core.nodes(scmd)
            self.len(2, nodes)

            # set adds
            ret = await core.callStorm('$x=$lib.set() $y=(1,2,3) $x.adds($y) return($x)')
            self.eq({'1', '2', '3'}, ret)

            ret = await core.callStorm('$x=$lib.set() $y=({"foo": "1", "bar": "2"}) $x.adds($y) return($x)')
            self.eq({('foo', '1'), ('bar', '2')}, ret)

            ret = await core.nodes('$x=$lib.set() $x.adds(${inet:ipv4}) for $n in $x { yield $n.iden() }')
            self.len(2, ret)

            ret = await core.callStorm('$x=$lib.set() $x.adds((1,2,3)) return($x)')
            self.eq({'1', '2', '3'}, ret)

            ret = await core.callStorm('$x=$lib.set() $y=abcd $x.adds($y) return($x)')
            self.eq({'a', 'b', 'c', 'd'}, ret)

            # set rems
            ret = await core.callStorm('$x=$lib.set(1,2,3) $y=(1,2) $x.rems($y) return($x)')
            self.eq({'3'}, ret)

            scmd = '''
                $x=$lib.set()
                $y=({"foo": "1", "bar": "2"})
                $x.adds($y)
                $z=({"foo": "1"})
                $x.rems($z)
                return($x)
            '''
            ret = await core.callStorm(scmd)
            self.eq({('bar', '2')}, ret)

            ret = await core.callStorm('$x=$lib.set() $y=({"foo": "1", "bar": "2"}) $x.adds($y) return($x)')
            self.eq({('foo', '1'), ('bar', '2')}, ret)

            ret = await core.callStorm('$x=$lib.set(1,2,3) $x.rems((1,2)) return($x)')
            self.eq({'3'}, ret)

            ret = await core.callStorm('$x=$lib.set(a,b,c,d) $y=ab $x.rems($y) return($x)')
            self.eq({'d', 'c'}, ret)

            # str join
            ret = await core.callStorm('$x=(foo,bar,baz) $y=$lib.str.join("-", $x) return($y)')
            self.eq('foo-bar-baz', ret)

            ret = await core.callStorm('$y=$lib.str.join("-", (foo, bar, baz)) return($y)')
            self.eq('foo-bar-baz', ret)

            ret = await core.callStorm('$x=abcd $y=$lib.str.join("-", $x) return($y)')
            self.eq('a-b-c-d', ret)

    async def test_storm_lib_axon(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')
            # test out the stormlib axon API
            host, port = await core.addHttpsPort(0, host='127.0.0.1')

            opts = {'user': visi.iden, 'vars': {'port': port}}
            wget = '''
               $url = $lib.str.format("https://visi:secret@127.0.0.1:{port}/api/v1/healthcheck", port=$port)
               return($lib.axon.wget($url, ssl=$lib.false))
           '''
            with self.raises(s_exc.AuthDeny):
                await core.callStorm(wget, opts=opts)

            with self.raises(s_exc.AuthDeny):
                await core.nodes('for $x in $lib.axon.list() { $lib.print($x) }', opts=opts)

            # test wget runtsafe / per-node / per-node with cmdopt
            nodes = await core.nodes(f'wget --no-ssl-verify https://127.0.0.1:{port}/api/v1/active')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:urlfile')

            nodes = await core.nodes(f'inet:url=https://127.0.0.1:{port}/api/v1/active | wget --no-ssl-verify')
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:urlfile')

            q = f'inet:urlfile:url=https://127.0.0.1:{port}/api/v1/active | wget --no-ssl-verify :url'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'inet:urlfile')

            # check that the file name got set...
            q = f'wget --no-ssl-verify https://127.0.0.1:{port}/api/v1/active | -> file:bytes +:name=active'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'file:bytes')
            sha256, size, created = nodes[0].get('sha256'), nodes[0].get('size'), nodes[0].get('.created')

            items = await core.callStorm('$x=() for $i in $lib.axon.list() { $x.append($i) } return($x)')
            self.eq([(0, sha256, size)], items)

            # test $lib.axon.del()
            delopts = {'user': visi.iden, 'vars': {'sha256': sha256}}
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.axon.del($sha256)', opts=delopts)
            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.axon.dels(($sha256,))', opts=delopts)
            with self.raises(s_exc.BadArg):
                await core.callStorm('$lib.axon.dels(newp)')
            delopts = {'vars': {'sha256': sha256}}
            self.eq((True, False), await core.callStorm('return($lib.axon.dels(($sha256, $sha256)))', opts=delopts))
            self.false(await core.callStorm('return($lib.axon.del($sha256))', opts=delopts))

            items = await core.callStorm('$x=() for $i in $lib.axon.list() { $x.append($i) } return($x)')
            self.len(0, items)

            msgs = await core.stormlist(f'wget --no-ssl-verify https://127.0.0.1:{port}/api/v1/newp')
            self.stormIsInWarn('HTTP code 404', msgs)

            self.len(1, await core.callStorm('$x=() for $i in $lib.axon.list() { $x.append($i) } return($x)'))

            size, sha256 = await core.callStorm('return($lib.axon.put($buf))', opts={'vars': {'buf': b'foo'}})

            items = await core.callStorm('$x=() for $i in $lib.axon.list() { $x.append($i) } return($x)')
            self.len(2, items)
            self.eq((2, sha256, size), items[1])

            items = await core.callStorm('$x=() for $i in $lib.axon.list(2) { $x.append($i) } return($x)')
            self.eq([(2, sha256, size)], items)

            # test request timeout
            async def timeout(self):
                await asyncio.sleep(2)

            with mock.patch.object(s_httpapi.ActiveV1, 'get', timeout):
                msgs = await core.stormlist(f'wget --no-ssl-verify https://127.0.0.1:{port}/api/v1/active --timeout 1')
                self.stormIsInWarn('TimeoutError', msgs)

            await visi.addRule((True, ('storm', 'lib', 'axon', 'wget')))
            resp = await core.callStorm(wget, opts=opts)
            self.true(resp['ok'])

            opts = {'vars': {'linesbuf': linesbuf, 'jsonsbuf': jsonsbuf, 'asdfbuf': b'asdf'}}
            asdfitem = await core.callStorm('return($lib.axon.put($asdfbuf))', opts=opts)
            linesitem = await core.callStorm('return($lib.axon.put($linesbuf))', opts=opts)
            jsonsitem = await core.callStorm('return($lib.axon.put($jsonsbuf))', opts=opts)

            opts = {'vars': {'sha256': asdfitem[1]}}
            self.eq(('asdf',), await core.callStorm('''
                $items = ()
                for $item in $lib.axon.readlines($sha256) { $items.append($item) }
                return($items)
            ''', opts=opts))

            opts = {'vars': {'sha256': linesitem[1]}}
            self.eq(('vertex.link', 'woot.com'), await core.callStorm('''
                $items = ()
                for $item in $lib.axon.readlines($sha256) { $items.append($item) }
                return($items)
            ''', opts=opts))

            opts = {'vars': {'sha256': jsonsitem[1]}}
            self.eq(({'fqdn': 'vertex.link'}, {'fqdn': 'woot.com'}), await core.callStorm('''
                $items = ()
                for $item in $lib.axon.jsonlines($sha256) { $items.append($item) }
                return($items)
            ''', opts=opts))

            async def waitlist():
                items = await core.callStorm('''
                    $x=()
                    for $i in $lib.axon.list(2, wait=$lib.true, timeout=1) {
                        $x.append($i)
                    }
                    return($x)
                ''')
                return items
            task = core.schedCoro(waitlist())
            await asyncio.sleep(0.1)
            await core.axon.put(b'visi')
            items = await task
            self.len(6, items)
            self.eq(items[5][1], 'e45bbb7e03acacf4d1cca4c16af1ec0c51d777d10e53ed3155bd3d8deb398f3f')

            data = '''John,Doe,120 jefferson st.,Riverside, NJ, 08075
Jack,McGinnis,220 hobo Av.,Phila, PA,09119
"John ""Da Man""",Repici,120 Jefferson St.,Riverside, NJ,08075
Stephen,Tyler,"7452 Terrace ""At the Plaza"" road",SomeTown,SD, 91234
,Blankman,,SomeTown, SD, 00298
"Joan ""the bone"", Anne",Jet,"9th, at Terrace plc",Desert City,CO,00123
Bob,Smith,Little House at the end of Main Street,Gomorra,CA,12345'''
            size, sha256 = await core.axon.put(data.encode())
            sha256 = s_common.ehex(sha256)
            q = '''
            $genr = $lib.axon.csvrows($sha256)
            for $row in $genr {
                $lib.fire(csvrow, row=$row)
            }
            '''
            msgs = await core.stormlist(q, opts={'vars': {'sha256': sha256}})
            rows = [m[1].get('data').get('row') for m in msgs if m[0] == 'storm:fire']
            self.len(7, rows)
            for row in rows:
                self.len(6, row)
            names = [row[0] for row in rows]
            self.len(7, names)
            self.isin('', names)
            self.isin('Bob', names)
            self.isin('John "Da Man"', names)

            data = '''foo\tbar\tbaz
words\tword\twrd'''
            size, sha256 = await core.axon.put(data.encode())
            sha256 = s_common.ehex(sha256)
            # Note: The tab delimiter in the query here is double quoted
            # so that we decode it in the Storm parser.
            q = '''
            $genr = $lib.axon.csvrows($sha256, delimiter="\\t")
            for $row in $genr {
                $lib.fire(csvrow, row=$row)
            }
            '''
            msgs = await core.stormlist(q, opts={'vars': {'sha256': sha256}})
            rows = [m[1].get('data').get('row') for m in msgs if m[0] == 'storm:fire']
            self.eq(rows, [['foo', 'bar', 'baz'], ['words', 'word', 'wrd']])

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('return($lib.axon.metrics())', opts={'user': visi.iden})

            self.eq({
                'file:count': 9,
                'size:bytes': 646,
            }, await core.callStorm('return($lib.axon.metrics())'))

            bin_buf = b'\xbb/$\xc0A\xf1\xbf\xbc\x00_\x82v4\xf6\xbd\x1b'
            binsize, bin256 = await core.axon.put(bin_buf)

            opts = {'vars': {'sha256': s_common.ehex(bin256)}}
            with self.raises(s_exc.BadDataValu):
                self.eq('', await core.callStorm('''
                    $items = ()
                    for $item in $lib.axon.readlines($sha256, errors=$lib.null) {
                        $items.append($item)
                    }
                    return($items)
                ''', opts=opts))

            self.eq(('/$A\x00_v4\x1b',), await core.callStorm('''
                $items = ()
                for $item in $lib.axon.readlines($sha256, errors=ignore) { $items.append($item) }
                return($items)
            ''', opts=opts))

    async def test_storm_lib_axon_perms(self):

        async with self.getTestCore() as core:

            mainview = await core.callStorm('return($lib.view.get().iden)')
            forkview = await core.callStorm('return($lib.view.get().fork().iden)')

            mainlayr = core.getView(mainview).layers[0].iden

            visi = await core.auth.addUser('visi')
            await visi.setPasswd('secret')

            host, port = await core.addHttpsPort(0, host='127.0.0.1')
            core.addHttpApi('/api/v0/test', s_test.HttpReflector, {'cell': core})
            url = f'https://visi:secret@127.0.0.1:{port}/api/v0/test'

            async def _addfile():
                async with await core.axon.upload() as fd:
                    await fd.write(b'{"foo": "bar"}')
                    return await fd.save()

            size, sha256 = await _addfile()

            opts = {'user': visi.iden, 'vars': {'url': url, 'sha256': s_common.ehex(sha256)}}

            # wget

            scmd = 'return($lib.axon.wget($url, ssl=$lib.false).code)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'wget')))
            self.eq(200, await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'wget')))

            await visi.addRule((True, ('axon', 'wget')))
            self.eq(200, await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'wget')))

            # wput

            scmd = 'return($lib.axon.wput($sha256, $url, method=post, ssl=$lib.false).code)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'wput')))
            self.eq(200, await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'wput')))

            await visi.addRule((True, ('axon', 'wput')))
            self.eq(200, await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'wput')))

            # urlfile

            opts['view'] = mainview
            scmd = 'yield $lib.axon.urlfile($url, ssl=$lib.false) return($node)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'wget')))
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('node', 'add', 'file:bytes')), gateiden=mainlayr)
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('node', 'add', 'inet:urlfile')), gateiden=mainlayr)
            self.nn(await core.callStorm(scmd, opts=opts))

            # won't work in another view
            opts['view'] = forkview
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))
            opts.pop('view')

            await visi.delRule((True, ('storm', 'lib', 'axon', 'wget')))

            await visi.addRule((True, ('axon', 'wget')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'wget')))

            # del

            scmd = 'return($lib.axon.del($sha256))'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'del')))
            self.true(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'del')))
            await _addfile()

            await visi.addRule((True, ('axon', 'del')))
            self.true(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'del')))
            await _addfile()

            # dels

            scmd = 'return($lib.axon.dels(($sha256,)))'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'del')))
            self.eq([True], await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'del')))
            await _addfile()

            await visi.addRule((True, ('axon', 'del')))
            self.eq([True], await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'del')))
            await _addfile()

            # list

            scmd = '$x=$lib.null for $x in $lib.axon.list() { } return($x)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'has')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'has')))

            await visi.addRule((True, ('axon', 'has')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'has')))

            # readlines

            scmd = '$x=$lib.null for $x in $lib.axon.readlines($sha256) { } return($x)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'get')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'get')))

            await visi.addRule((True, ('axon', 'get')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'get')))

            # jsonlines

            scmd = '$x=$lib.null for $x in $lib.axon.jsonlines($sha256) { } return($x)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'get')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'get')))

            await visi.addRule((True, ('axon', 'get')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'get')))

            # csvrows

            scmd = '$x=$lib.null for $x in $lib.axon.csvrows($sha256) { } return($x)'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'get')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'get')))

            await visi.addRule((True, ('axon', 'get')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'get')))

            # metrics

            scmd = 'return($lib.axon.metrics())'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(scmd, opts=opts))

            await visi.addRule((True, ('storm', 'lib', 'axon', 'has')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('storm', 'lib', 'axon', 'has')))

            await visi.addRule((True, ('axon', 'has')))
            self.nn(await core.callStorm(scmd, opts=opts))
            await visi.delRule((True, ('axon', 'has')))

    async def test_storm_lib_export(self):

        async with self.getTestCore() as core:
            await core.nodes('[inet:dns:a=(vertex.link, 1.2.3.4)]')
            size, sha256 = await core.callStorm('return( $lib.export.toaxon(${.created}) )')
            byts = b''.join([b async for b in core.axon.get(s_common.uhex(sha256))])
            self.isin(b'vertex.link', byts)

            with self.raises(s_exc.BadArg):
                await core.callStorm('return( $lib.export.toaxon(${.created}, (bad, opts,)) )')

    async def test_storm_nodes_edges(self):

        async with self.getTestCore() as core:

            iden = await core.callStorm('[ ou:industry=* ] return($node.iden())')

            opts = {'vars': {'iden': iden}}

            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ] $node.addEdge(foo, $iden) -(foo)> ou:industry', opts=opts)
            self.eq(nodes[0].iden(), iden)

            nodes = await core.nodes('ou:industry for ($verb, $n2iden) in $node.edges(reverse=(1)) { -> { yield $n2iden } }')
            self.len(1, nodes)

            nodes = await core.nodes('ou:industry for ($verb, $n2iden) in $node.edges(reverse=(0)) { -> { yield $n2iden } }')
            self.len(0, nodes)

            nodes = await core.nodes('inet:ipv4=1.2.3.4 for ($verb, $n2iden) in $node.edges(reverse=(1)) { -> { yield $n2iden } }')
            self.len(0, nodes)

            nodes = await core.nodes('inet:ipv4=1.2.3.4 for ($verb, $n2iden) in $node.edges() { -> { yield $n2iden } }')
            self.len(1, nodes)
            self.eq('ou:industry', nodes[0].ndef[0])

            nodes = await core.nodes('ou:industry for ($verb, $n1iden) in $node.edges(reverse=(1)) { -> { yield $n1iden } }')
            self.len(1, nodes)
            self.eq('inet:ipv4', nodes[0].ndef[0])

            iden = await core.callStorm('ou:industry=* return($node.iden())')
            nodes = await core.nodes('[ inet:ipv4=1.2.3.4 ] $node.delEdge(foo, $iden) -(foo)> ou:industry', opts=opts)
            self.len(0, nodes)

            with self.raises(s_exc.BadCast):
                await core.nodes('ou:industry $node.addEdge(foo, bar)')

            with self.raises(s_exc.BadCast):
                await core.nodes('ou:industry $node.delEdge(foo, bar)')

    async def test_storm_layer_lift(self):

        async with self.getTestCore() as core:

            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            q = '[ ou:org=* :name=foobar +#hehe ] $node.data.set(foo, bar) return($node.iden())'
            basenode = await core.callStorm(q)

            opts = {'view': viewiden}
            nodeiden = await core.callStorm('''
                [ ou:org=* :name=foobar +#hehe ]
                $node.data.set(foo, bar)
                return($node.iden())
            ''', opts=opts)

            nodeiden2 = await core.callStorm('[test:str=yup] $node.data.set(foo, yup) return ($node.iden())',
                                             opts=opts)

            self.len(2, await core.nodes('ou:org +:name=foobar +#hehe', opts=opts))

            nodes = await core.nodes('yield $lib.layer.get().liftByNodeData(foo)', opts=opts)
            self.len(2, nodes)
            self.eq(set((nodeiden, nodeiden2)), {node.iden() for node in nodes})

            nodes = await core.nodes('yield $lib.layer.get().liftByNodeData(foo)')
            self.len(1, nodes)
            self.eq(nodes[0].iden(), basenode)

            nodes = await core.nodes('yield $lib.layer.get().liftByProp(ou:org)', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].iden(), nodeiden)

            nodes = await core.nodes('yield $lib.layer.get().liftByProp(ou:org:name, foobar)', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].iden(), nodeiden)

            nodes = await core.nodes('yield $lib.layer.get().liftByProp(ou:org:name, foo, "^=")', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].iden(), nodeiden)

            nodes = await core.nodes('yield $lib.layer.get().liftByProp(".created")', opts=opts)
            self.len(2, nodes)
            self.eq(nodes[0].iden(), nodeiden)

            nodes = await core.nodes('yield $lib.layer.get().liftByTag(hehe)', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].iden(), nodeiden)

            nodes = await core.nodes('yield $lib.layer.get().liftByTag(hehe, ou:org)', opts=opts)
            self.len(1, nodes)
            self.eq(nodes[0].iden(), nodeiden)

            with self.raises(s_exc.NoSuchProp):
                await core.nodes('yield $lib.layer.get().liftByProp(newp)', opts=opts)

            with self.raises(s_exc.NoSuchForm):
                await core.nodes('yield $lib.layer.get().liftByTag(newp, newp)', opts=opts)

            # Comparators are validated
            with self.raises(s_exc.NoSuchCmpr):
                await core.nodes('yield $lib.layer.get().liftByProp(ou:org:name, foo, "^#$%@")', opts=opts)

            # Type safety still matters
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('yield $lib.layer.get().liftByProp(ou:org, not_a_guid)', opts=opts)

    async def test_stormtypes_number(self):

        async with self.getTestCore() as core:

            with self.raises(s_exc.BadCast):
                s_stormtypes.Number('beepbeep')

            huge = s_stormtypes.Number(1.23)

            self.eq(huge, 1.23)
            self.ne(huge, 'foo')
            self.lt(huge, 2.34)
            self.eq(huge + 2.34, 3.57)
            self.eq(huge - 0.23, 1.0)
            self.eq(huge * 1.0, 1.23)
            self.eq(huge / 1.0, 1.23)
            self.eq(huge % 1.0, 0.23)
            self.eq(huge ** 2, 1.5129)
            self.eq(huge ** 2.0, 1.5129)
            self.eq(huge ** s_stormtypes.Number(2), 1.5129)
            self.eq(huge, float(huge))

            with self.assertRaises(TypeError):
                self.lt(huge, 'foo')

            with self.assertRaises(TypeError):
                huge + 'foo'

            with self.assertRaises(TypeError):
                huge - 'foo'

            with self.assertRaises(TypeError):
                huge * 'foo'

            with self.assertRaises(TypeError):
                huge / 'foo'

            with self.assertRaises(TypeError):
                huge ** 'foo'

            with self.assertRaises(TypeError):
                huge % 'foo'

            self.eq(15.0, await core.callStorm('return($lib.math.number(0xf))'))
            self.eq(15.0, await core.callStorm('return($lib.math.number($lib.math.number(0xf)))'))
            self.eq(1.23, await core.callStorm('return($lib.math.number(1.23).tofloat())'))
            self.eq('1.23', await core.callStorm('return($lib.math.number(1.23).tostr())'))
            self.eq(1, await core.callStorm('return($lib.math.number(1.23).toint())'))
            self.eq(2, await core.callStorm('return($lib.math.number(1.23).toint(rounding=ROUND_UP))'))

            with self.raises(s_exc.BadCast):
                await core.callStorm('return($lib.math.number((null)))')
            with self.raises(s_exc.BadCast):
                await core.callStorm('return($lib.math.number(newp))')

            with self.raises(s_exc.StormRuntimeError):
                await core.callStorm('return($lib.math.number(1.23).toint(rounding=NEWP))')

            self.eq(0.0123, await core.callStorm('return($lib.math.number(1.23).scaleb(-2))'))

            msgs = await core.stormlist('$lib.print((1.23))')
            self.eq(msgs[1][1]['mesg'], '1.23')

            q = '''
            [ inet:fqdn=foo.com ]
            $foo = (1.23)
            $bar = $node
            [ ps:contact=(test, $foo, $bar) ]
            '''
            self.len(2, await core.nodes(q))

            valu = '1.000000000000000000001'

            await core.addTagProp('huge', ('hugenum', {}), {})
            await core.addFormProp('test:str', '_hugearray', ('array', {'type': 'hugenum'}), {})

            nodes = await core.nodes(f'[econ:acct:balance=* :amount=({valu})]')
            self.eq(nodes[0].props.get('amount'), valu)

            nodes = await core.nodes(f'econ:acct:balance:amount=({valu})')
            self.len(1, nodes)

            nodes = await core.nodes(f'[test:hugenum=({valu})]')
            self.eq(nodes[0].ndef[1], valu)

            nodes = await core.nodes(f'test:hugenum=({valu})')
            self.len(1, nodes)

            nodes = await core.nodes(f'econ:acct:balance:amount +:amount=({valu})')
            self.len(1, nodes)

            nodes = await core.nodes(f'[test:str=foo +#foo:huge=({valu})]')
            self.len(1, nodes)
            self.eq(nodes[0].tagprops['foo']['huge'], valu)

            nodes = await core.nodes(f'#foo:huge=({valu})')
            self.len(1, nodes)

            nodes = await core.nodes(f'test:str#foo:huge=({valu})')
            self.len(1, nodes)

            nodes = await core.nodes(f'[test:str=bar :_hugearray=(({valu}), ({valu}))]')
            self.len(1, nodes)
            self.eq(nodes[0].props.get('_hugearray'), [valu, valu])

            nodes = await core.nodes(f'test:str:_hugearray*[=({valu})]')
            self.len(1, nodes)

    async def test_storm_stor_readonly(self):
        async with self.getTestCore() as core:
            udef = await core.addUser('user')
            user = udef.get('iden')

            q = '$user=$lib.auth.users.get($iden) $user.name = $newname'
            msgs = await core.stormlist(q, opts={'readonly': True,
                                                 'vars': {
                                                     'iden': user,
                                                     'newname': 'oops'
                                                 }})

            self.stormIsInErr('Setting name on auth:user is not marked readonly safe.', msgs)

            mesg = 'Storm runtime is in readonly mode, cannot create or edit nodes and other graph data.'

            q = '$user=$lib.auth.users.get($iden) $user.profile.foo = bar'
            msgs = await core.stormlist(q, opts={'readonly': True,
                                                 'vars': {'iden': user}})

            self.stormIsInErr(mesg, msgs)

            q = '$user=$lib.auth.users.get($iden) $user.vars.foo = bar'
            msgs = await core.stormlist(q, opts={'readonly': True,
                                                 'vars': {'iden': user}})

            self.stormIsInErr(mesg, msgs)

            q = '$lib.debug=$lib.true return($lib.debug)'
            debug = await core.callStorm(q, opts={'readonly': True,
                                                  'vars': {'iden': user}})
            self.true(debug)

            await core.callStorm('[inet:fqdn=foo]')

            q = '''
                $user=$lib.auth.users.get($iden)
                inet:fqdn=foo
                $user.vars.foo = bar
            '''
            msgs = await core.stormlist(q, opts={'readonly': True, 'vars': {'iden': user}})
            self.stormIsInErr(mesg, msgs)

            q = '$lib.pkg.add(({}))'
            msgs = await core.stormlist(q, opts={'readonly': True, 'vars': {'iden': user}})
            self.stormIsInErr('$lib.pkg.add() is not marked readonly safe.', msgs)

    async def test_storm_view_counts(self):

        async with self.getTestCore() as core:

            await core.addTagProp('score', ('int', {}), {})

            view2 = await core.view.fork()
            forkopts = {'view': view2['iden']}

            q = '''[
                inet:ipv4=1
                inet:ipv4=2
                inet:ipv4=3
                :asn=4

                (ou:org=*
                 ou:org=*
                 :names=(foo, bar))

                .seen=2020
                .univarray=(1, 2)
                +#foo:score=2

                test:arrayform=(1,2,3)
                test:arrayform=(2,3,4)
            ]'''
            await core.nodes(q)

            q = '''[
                inet:ipv4=4
                inet:ipv4=5
                inet:ipv4=6
                :asn=4

                (ou:org=*
                 ou:org=*
                 :names=(foo, bar))

                .seen=2020
                .univarray=(1, 2)
                +#foo:score=2

                test:arrayform=(3,4,5)
                test:arrayform=(4,5,6)
            ]'''
            await core.nodes(q, opts=forkopts)

            q = 'return($lib.view.get().getPropCount(inet:ipv4:asn))'
            self.eq(6, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(inet:ipv4:asn, valu=1))'
            self.eq(0, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(inet:ipv4:loc, valu=1))'
            self.eq(0, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(inet:ipv4:asn, valu=4))'
            self.eq(6, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(inet:ipv4.seen, valu=2020))'
            self.eq(6, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(".seen", valu=2020))'
            self.eq(10, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(inet:ipv4, valu=1))'
            self.eq(1, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(ou:org:names, valu=(foo, bar)))'
            self.eq(4, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropCount(".univarray", valu=(1, 2)))'
            self.eq(10, await core.callStorm(q, opts=forkopts))

            with self.raises(s_exc.NoSuchProp):
                q = 'return($lib.view.get().getPropCount(newp, valu=1))'
                await core.callStorm(q, opts=forkopts)

            q = 'return($lib.view.get().getPropArrayCount(ou:org:names))'
            self.eq(8, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropArrayCount(ou:org:names, valu=foo))'
            self.eq(4, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropArrayCount(".univarray", valu=2))'
            self.eq(10, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getPropArrayCount(test:arrayform, valu=3))'
            self.eq(3, await core.callStorm(q, opts=forkopts))

            with self.raises(s_exc.NoSuchProp):
                q = 'return($lib.view.get().getPropArrayCount(newp, valu=1))'
                await core.callStorm(q, opts=forkopts)

            with self.raises(s_exc.BadTypeValu):
                q = 'return($lib.view.get().getPropArrayCount(inet:ipv4, valu=1))'
                await core.callStorm(q, opts=forkopts)

            q = 'return($lib.view.get().getTagPropCount(foo, score))'
            self.eq(10, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getTagPropCount(foo, score, valu=2))'
            self.eq(10, await core.callStorm(q, opts=forkopts))

            q = 'return($lib.view.get().getTagPropCount(foo, score, form=ou:org, valu=2))'
            self.eq(4, await core.callStorm(q, opts=forkopts))

            with self.raises(s_exc.NoSuchTagProp):
                q = 'return($lib.view.get().getTagPropCount(foo, newp, valu=2))'
                await core.callStorm(q, opts=forkopts)

    async def test_view_quorum(self):

        async with self.getTestCore() as core:

            root = core.auth.rootuser
            visi = await core.auth.addUser('visi')
            newp = await core.auth.addUser('newp')

            await visi.addRule((True, ('view', 'add')))
            await visi.addRule((True, ('view', 'read')))

            await newp.addRule((True, ('view', 'add')))
            await newp.addRule((True, ('view', 'read')))

            ninjas = await core.auth.addRole('ninjas')

            with self.raises(s_exc.BadState):
                core.getView().reqParentQuorum()

            vdef = await core.getView().fork()
            with self.raises(s_exc.BadState):
                core.getView(vdef['iden']).reqParentQuorum()

            with self.raises(s_exc.AuthDeny):
                opts = {'user': visi.iden, 'vars': {'role': ninjas.iden}}
                await core.callStorm('return($lib.view.get().set(quorum, ({"count": 1, "roles": [$role]})))', opts=opts)

            opts = {'vars': {'role': ninjas.iden}}
            quorum = await core.callStorm('return($lib.view.get().set(quorum, ({"count": 1, "roles": [$role]})))', opts=opts)

            # coverage mop up for edge cases...
            with self.raises(s_exc.CantMergeView):
                await core.getView(vdef['iden']).mergeAllowed()

            await core.getView(vdef['iden']).detach()

            fork00 = await core.callStorm('return($lib.view.get().fork().iden)')

            with self.raises(s_exc.BadState):
                await core.callStorm('$lib.view.get().setMergeComment("that doesnt exist")', opts={'user': root.iden, 'view': fork00})

            msgs = await core.stormlist('[ inet:fqdn=vertex.link ]', opts={'view': fork00})
            self.stormHasNoWarnErr(msgs)

            nodes = await core.nodes('inet:fqdn')
            self.len(0, nodes)

            with self.raises(s_exc.SynErr):
                await core.callStorm('$lib.view.get().merge()', opts={'view': fork00})

            with self.raises(s_exc.BadState):
                core.getView(fork00).reqValidVoter(visi.iden)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.get().setMergeRequest()', opts={'user': visi.iden, 'view': fork00})

            merge = await core.callStorm('return($lib.view.get().setMergeRequest(comment=woot))', opts={'view': fork00})
            self.nn(merge['iden'])
            self.nn(merge['created'])
            self.eq(merge['comment'], 'woot')
            self.eq(merge['creator'], core.auth.rootuser.iden)
            self.none(merge.get('updated'))

            merging = 'return($lib.view.get().getMergingViews()) '

            self.eq([fork00], await core.callStorm(merging))

            with self.raises(s_exc.AuthDeny):
                core.getView(fork00).reqValidVoter(root.iden)

            await core.callStorm('$lib.view.get().setMergeComment("mergin some dataaz")', opts={'view': fork00})

            merge = await core.callStorm('return($lib.view.get().getMergeRequest())', opts={'view': fork00})
            self.nn(merge['iden'])
            self.nn(merge['created'])
            self.nn(merge['updated'])
            self.gt(merge['updated'], merge['created'])
            self.eq(merge['comment'], 'mergin some dataaz')
            self.eq(merge['creator'], core.auth.rootuser.iden)

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.get().setMergeVote()', opts={'view': fork00})

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.get().setMergeVote()', opts={'user': visi.iden, 'view': fork00})

            await visi.grant(ninjas.iden)
            await newp.grant(ninjas.iden)

            opts = {'user': visi.iden, 'view': fork00}
            vote = await core.callStorm('return($lib.view.get().setMergeVote(approved=(false), comment=fixyourstuff))', opts=opts)
            self.nn(vote['offset'])
            self.nn(vote['created'])
            self.false(vote['approved'])
            self.eq(vote['user'], visi.iden)
            self.eq(vote['comment'], 'fixyourstuff')

            forkview = core.getView(fork00)

            with self.raises(s_exc.BadState):
                await core.callStorm('$lib.view.get().setMergeVoteComment("wait that doesnt exist")', opts={'view': fork00, 'user': newp.iden})

            with self.raises(s_exc.AuthDeny):
                await core.callStorm('$lib.view.get().setMergeComment("no wait you cant do that")', opts={'view': fork00, 'user': newp.iden})

            await core.callStorm('$lib.view.get().setMergeVoteComment("no really, fix your stuff")', opts=opts)
            votes = [vote async for vote in forkview.getMergeVotes()]
            self.len(1, votes)
            self.eq(votes[0]['comment'], 'no really, fix your stuff')
            self.nn(votes[0]['updated'])
            self.gt(votes[0]['updated'], votes[0]['created'])

            opts = {'user': newp.iden, 'view': fork00}
            vote = await core.callStorm('return($lib.view.get().setMergeVote())', opts=opts)
            self.nn(vote['offset'])
            self.nn(vote['created'])
            self.true(vote['approved'])
            self.eq(vote['user'], newp.iden)

            summary = await core.callStorm('return($lib.view.get().getMergeRequestSummary())', opts={'view': fork00})
            self.nn(summary['merge'])
            self.nn(summary['quorum'])
            self.nn(summary['offset'])
            self.len(2, summary['votes'])
            self.false(summary['merging'])

            with self.raises(s_exc.AuthDeny):
                opts = {'user': newp.iden, 'view': fork00, 'vars': {'visi': visi.iden}}
                await core.callStorm('return($lib.view.get().delMergeVote(useriden=$visi))', opts=opts)

            # removing the last veto triggers the merge
            opts = {'user': visi.iden, 'view': fork00}
            await core.callStorm('return($lib.view.get().delMergeVote())', opts=opts)

            self.true(forkview.merging)
            self.true(forkview.layers[0].readonly)

            self.true(await forkview.waitfini(timeout=12))

            self.none(core.getView(fork00))
            nodes = await core.nodes('inet:fqdn')
            self.len(2, nodes)

            # previously successful merges
            self.len(1, await core.callStorm('$list = ([]) for $merge in $lib.view.get().getMerges() { $list.append($merge) } fini { return($list) }'))

            # current open merge requests
            self.eq([], await core.callStorm(merging))

            # test out the delMergeRequest logic / cleanup
            forkdef = await core.getView().fork()

            fork = core.getView(forkdef.get('iden'))

            opts = {'view': fork.iden}
            self.nn(await core.callStorm('return($lib.view.get().setMergeRequest())', opts=opts))
            self.eq([fork.iden], await core.callStorm(merging))

            # confirm that you may re-parent to a view with a merge request
            layr = await core.addLayer()
            vdef = await core.addView({'layers': (layr['iden'],)})
            await core.getView(vdef['iden']).setViewInfo('parent', fork.iden)

            opts = {'view': fork.iden, 'user': visi.iden}
            self.nn(await core.callStorm('return($lib.view.get().setMergeVote(approved=(false)))', opts=opts))
            self.len(1, [vote async for vote in fork.getMergeVotes()])

            opts = {'view': fork.iden}
            self.nn(await core.callStorm('return($lib.view.get().delMergeRequest())', opts=opts))
            self.len(0, [vote async for vote in fork.getMergeVotes()])

            self.eq([], await core.callStorm(merging))

            # test coverage for beholder progress events...
            forkdef = await core.getView().fork()
            fork = core.getView(forkdef.get('iden'))

            opts = {'view': fork.iden}
            await core.stormlist('[ inet:ipv4=1.2.3.0/20 ]', opts=opts)
            await core.callStorm('return($lib.view.get().setMergeRequest())', opts=opts)

            self.eq([fork.iden], await core.callStorm(merging))

            nevents = 8
            if s_common.envbool('SYNDEV_NEXUS_REPLAY'):
                # view:merge:vote:set fires twice
                nevents += 1
            waiter = core.waiter(nevents, 'cell:beholder')

            opts = {'view': fork.iden, 'user': visi.iden}
            await core.callStorm('return($lib.view.get().setMergeVote())', opts=opts)

            msgs = await waiter.wait(timeout=12)
            self.eq(msgs[0][1]['event'], 'view:merge:vote:set')
            self.eq(msgs[0][1]['info']['vote']['user'], visi.iden)

            self.eq(msgs[1][1]['event'], 'view:merge:init')
            self.eq(msgs[1][1]['info']['merge']['creator'], core.auth.rootuser.iden)
            self.eq(msgs[1][1]['info']['votes'][0]['user'], visi.iden)

            self.eq(msgs[-2][1]['info']['merge']['creator'], core.auth.rootuser.iden)
            self.eq(msgs[-2][1]['event'], 'view:merge:prog')
            self.eq(msgs[-2][1]['info']['merge']['creator'], core.auth.rootuser.iden)
            self.eq(msgs[-2][1]['info']['votes'][0]['user'], visi.iden)

            self.eq(msgs[-1][1]['event'], 'view:merge:fini')
            self.eq(msgs[-1][1]['info']['merge']['creator'], core.auth.rootuser.iden)
            self.eq(msgs[-1][1]['info']['votes'][0]['user'], visi.iden)

            self.eq([], await core.callStorm(merging))

            # merge a view with a fork
            mainview = core.getView()
            fork00 = await mainview.fork()
            midfork = core.getView(fork00['iden'])

            fork01 = await midfork.fork()
            fork01_iden = fork01['iden']
            self.true(midfork.hasKids())

            opts = {'view': midfork.iden}
            await core.callStorm('return($lib.view.get().setMergeRequest())', opts=opts)

            self.eq([midfork.iden], await core.callStorm(merging))

            layridens = [lyr['iden'] for lyr in fork01['layers'] if lyr['iden'] != midfork.layers[0].iden]
            events = [
                {'event': 'view:setlayers', 'info': {'iden': fork01_iden, 'layers': layridens}},
                {'event': 'view:set', 'info': {'iden': fork01_iden, 'name': 'parent', 'valu': mainview.iden}}
            ]
            task = core.schedCoro(s_test.waitForBehold(core, events))

            opts = {'view': midfork.iden, 'user': visi.iden}
            await core.callStorm('return($lib.view.get().setMergeVote())', opts=opts)

            self.true(await midfork.waitfini(timeout=12))

            await asyncio.wait_for(task, timeout=5)

            self.eq([], await core.callStorm(merging))

            leaffork = core.getView(fork01['iden'])
            self.false(leaffork.hasKids())

            self.len(2, leaffork.layers)
            self.eq(leaffork.parent, core.getView())

            # test coverage for bad state for merge request
            opts = {'view': fork01['iden']}
            await core.callStorm('return($lib.view.get().setMergeRequest())', opts=opts)
            self.eq([fork01['iden']], await core.callStorm(merging))

            core.getView().layers[0].readonly = True
            with self.raises(s_exc.BadState):
                await core.callStorm('return($lib.view.get().setMergeRequest())', opts=opts)

            core.getView().layers[0].readonly = False
            await core.callStorm('return($lib.view.get().fork())', opts=opts)

            # setup a new merge and make a mirror...
            forkdef = await core.getView().fork()
            fork = core.getView(forkdef.get('iden'))

            opts = {'view': fork.iden}
            await core.stormlist('[ inet:ipv4=5.5.5.5 ]', opts=opts)
            await core.callStorm('return($lib.view.get().setMergeRequest())', opts=opts)

            self.eq(set([fork.iden, fork01['iden']]), set(await core.callStorm(merging)))

            # hamstring the runViewMerge method on the new view
            async def fake():
                return
            fork.runViewMerge = fake

            # vote to merge and set it off....
            opts = {'view': fork.iden, 'user': visi.iden}
            await core.callStorm('return($lib.view.get().setMergeVote())', opts=opts)

            await core.sync()

            await core.runBackup(name='lead00', wait=True)
            await core.runBackup(name='mirror00', wait=True)

            # test that when a leader restarts it fires and completes the merge
            dirn = s_common.genpath(core.dirn, 'backups', 'lead00')
            async with self.getTestCore(dirn=dirn) as lead:
                while lead.getView(fork.iden) is not None:
                    await asyncio.sleep(0.1)
                self.len(1, await lead.nodes('inet:ipv4=5.5.5.5'))

            # test that a mirror starts without firing the merge and then fires it on promotion
            dirn = s_common.genpath(core.dirn, 'backups', 'mirror00')
            async with self.getTestCore(conf={'mirror': core.getLocalUrl()}, dirn=dirn) as mirror:
                await mirror.sync()
                view = mirror.getView(fork.iden)
                layr = view.layers[0]
                await mirror.promote(graceful=False)
                self.true(await view.waitfini(6))
                self.true(await layr.waitfini(6))
                self.len(1, await mirror.nodes('inet:ipv4=5.5.5.5'))

            msgs = await core.stormlist('$lib.view.get().set(quorum, $lib.null)')
            self.stormHasNoWarnErr(msgs)

            with self.raises(s_exc.BadState):
                await core.callStorm(merging)

    async def test_storm_lib_axon_read_unpack(self):

        async with self.getTestCore() as core:

            visi = await core.auth.addUser('visi')

            orig_axoninfo = core.axoninfo
            core.axoninfo = {'features': {}}
            data = struct.pack('>Q', 1)
            size, sha256 = await core.axon.put(data)
            sha256_s = s_common.ehex(sha256)
            q = 'return($lib.axon.unpack($sha256, fmt=">Q"))'
            await self.asyncraises(s_exc.FeatureNotSupported,
                                   core.callStorm(q, opts={'vars': {'sha256': sha256_s}}))
            core.axoninfo = orig_axoninfo

            data = b'vertex.link'
            size, sha256 = await core.axon.put(data)
            sha256_s = s_common.ehex(sha256)

            _, emptyhash = await core.axon.put(b'')
            emptyhash = s_common.ehex(emptyhash)

            opts = {'user': visi.iden, 'vars': {'sha256': sha256_s, 'emptyhash': emptyhash}}
            await self.asyncraises(s_exc.AuthDeny,
                core.callStorm('return($lib.axon.read($sha256, offs=3, size=3))', opts=opts))
            await visi.addRule((True, ('storm', 'lib', 'axon', 'get')))

            q = 'return($lib.axon.read($sha256, offs=3, size=3))'
            self.eq(b'tex', await core.callStorm(q, opts=opts))
            q = 'return($lib.axon.read($sha256, offs=7, size=4))'
            self.eq(b'link', await core.callStorm(q, opts=opts))
            q = 'return($lib.axon.read($sha256, offs=11, size=1))'
            self.eq(b'', await core.callStorm(q, opts=opts))

            q = 'return($lib.axon.read($emptyhash))'
            self.eq(b'', await core.callStorm(q, opts=opts))

            q = 'return($lib.axon.read($sha256, size=0))'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q, opts=opts))
            q = 'return($lib.axon.read($sha256, offs=-1, size=1))'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q, opts=opts))
            q = 'return($lib.axon.read($sha256, size=2097152))'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q, opts=opts))

            intdata = struct.pack('>QQQ', 1, 2, 3)
            size, sha256 = await core.axon.put(intdata)
            sha256_s = s_common.ehex(sha256)
            opts = {'user': visi.iden, 'vars': {'sha256': sha256_s}}

            await visi.delRule((True, ('storm', 'lib', 'axon', 'get')))
            q = 'return($lib.axon.unpack($sha256, fmt=">Q"))'
            await self.asyncraises(s_exc.AuthDeny, core.callStorm(q, opts=opts))
            await visi.addRule((True, ('storm', 'lib', 'axon', 'get')))

            q = 'return($lib.axon.unpack($sha256, fmt=">Q"))'
            self.eq((1,), await core.callStorm(q, opts=opts))
            q = 'return($lib.axon.unpack($sha256, fmt=">Q", offs=8))'
            self.eq((2,), await core.callStorm(q, opts=opts))
            q = 'return($lib.axon.unpack($sha256, fmt=">Q", offs=16))'
            self.eq((3,), await core.callStorm(q, opts=opts))
            q = 'return($lib.axon.unpack($sha256, fmt=">QQ", offs=8))'
            self.eq((2, 3), await core.callStorm(q, opts=opts))

            q = 'return($lib.axon.unpack($sha256, fmt="not a valid format"))'
            await self.asyncraises(s_exc.BadArg, core.callStorm(q, opts=opts))

            q = 'return($lib.axon.unpack($sha256, fmt=">Q", offs=24))'
            await self.asyncraises(s_exc.BadDataValu, core.callStorm(q, opts=opts))
