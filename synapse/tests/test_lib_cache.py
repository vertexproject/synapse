import regex

import synapse.tests.utils as s_t_utils

import synapse.lib.base as s_base
import synapse.lib.cache as s_cache

class CacheTest(s_t_utils.SynTest):

    def test_lib_cache_fixed(self):

        def callback(name):
            return name.lower()

        cache = s_cache.FixedCache(callback, size=2)

        self.eq('foo', cache.get('FOO'))
        self.eq('bar', cache.get('BAR'))

        self.len(2, cache.fifo)
        self.len(2, cache.cache)

        self.nn(cache.cache.get('FOO'))
        self.nn(cache.cache.get('BAR'))

        self.eq('baz', cache.get('BAZ'))

        self.len(2, cache.fifo)
        self.len(2, cache.cache)

        self.nn(cache.cache.get('BAR'))
        self.nn(cache.cache.get('BAZ'))

        cache.clear()

        self.len(0, cache.fifo)
        self.len(0, cache.cache)

    def test_regexize(self):
        restr = s_cache.regexizeTagGlob('foo*')
        self.eq(restr, r'foo([^.]+?)')
        re = regex.compile(restr)
        self.nn(re.fullmatch('foot'))
        self.none(re.fullmatch('foo'))
        self.none(re.fullmatch('foo.bar'))

        restr = s_cache.regexizeTagGlob('foo**')
        self.eq(restr, r'foo(.+)')
        re = regex.compile(restr)
        self.nn(re.fullmatch('foot'))
        self.none(re.fullmatch('foo'))
        self.nn(re.fullmatch('foo.bar'))

        restr = s_cache.regexizeTagGlob('foo.b*.b**z')
        self.eq(restr, r'foo\.b([^.]+?)\.b(.+)z')
        re = regex.compile(restr)
        self.none(re.fullmatch('foot'))
        self.none(re.fullmatch('foo'))
        self.nn(re.fullmatch('foo.bar.baz'))
        self.none(re.fullmatch('foo.bar.bz'))
        self.nn(re.fullmatch('foo.bar.burliz'))
        self.nn(re.fullmatch('foo.bar.boof.zuz'))
        self.none(re.fullmatch('foo.car.boof.zuz'))
        self.nn(re.fullmatch('foo.bar.burma.shave.workz'))

        restr = s_cache.regexizeTagGlob('*.bar')
        self.eq(restr, r'([^.]+?)\.bar')
        re = regex.compile(restr)
        self.none(re.fullmatch('foo'))
        self.none(re.fullmatch('.bar'))
        self.nn(re.fullmatch('foo.bar'))
        self.none(re.fullmatch('foo.bart'))
        self.none(re.fullmatch('foo.bar.blah'))

        restr = s_cache.regexizeTagGlob('*bar')
        self.eq(restr, r'([^.]+?)bar')
        re = regex.compile(restr)
        self.nn(re.fullmatch('bbar'))
        self.none(re.fullmatch('foo'))
        self.none(re.fullmatch('.bar'))
        self.nn(re.fullmatch('foobar'))
        self.none(re.fullmatch('foo.bar'))
        self.none(re.fullmatch('foo.bart'))

        restr = s_cache.regexizeTagGlob('**.bar')
        self.eq(restr, r'(.+)\.bar')
        re = regex.compile(restr)
        self.none(re.fullmatch('foo'))
        self.none(re.fullmatch('.bar'))
        self.nn(re.fullmatch('foo.bar'))
        self.none(re.fullmatch('foo.bart'))
        self.nn(re.fullmatch('foo.duck.bar'))
        self.none(re.fullmatch('foo.duck.zanzibar'))

        restr = s_cache.regexizeTagGlob('**bar')
        self.eq(restr, r'(.+)bar')
        re = regex.compile(restr)
        self.nn(re.fullmatch('.bar'))
        self.none(re.fullmatch('foo'))
        self.nn(re.fullmatch('foo.bar'))
        self.none(re.fullmatch('foo.bart'))
        self.nn(re.fullmatch('foo.duck.bar'))
        self.nn(re.fullmatch('foo.duck.zanzibar'))

        restr = s_cache.regexizeTagGlob('foo.b*b')
        self.eq(restr, r'foo\.b([^.]+?)b')
        re = regex.compile(restr)
        self.none(re.fullmatch('foo.bb'))
        self.none(re.fullmatch('foo.bar'))
        self.nn(re.fullmatch('foo.baaaaab'))
        self.none(re.fullmatch('foo.bar.rab'))

        restr = s_cache.regexizeTagGlob('foo.b**b')
        self.eq(restr, r'foo\.b(.+)b')
        re = regex.compile(restr)
        self.none(re.fullmatch('foo.bb'))
        self.none(re.fullmatch('foo.bar'))
        self.nn(re.fullmatch('foo.bar.rab'))
        self.nn(re.fullmatch('foo.baaaaab'))
        self.nn(re.fullmatch('foo.baaaaab.baaab'))
        self.none(re.fullmatch('foo.baaaaab.baaad'))

        restr = s_cache.regexizeTagGlob('foo.**.bar')
        self.eq(restr, r'foo\.(.+)\.bar')
        re = regex.compile(restr)
        self.none(re.fullmatch('foo.bar'))
        self.nn(re.fullmatch('foo.a.bar'))
        self.nn(re.fullmatch('foo.aa.bar'))
        self.none(re.fullmatch('foo.a.barr'))
        self.nn(re.fullmatch('foo.a.a.a.bar'))

    async def test_tag_globs(self):

        base = await s_base.Base.anit()

        glob = s_cache.TagGlobs()

        glob.add('zip.*', 1)
        glob.add('zip.*si', 11)
        glob.add('foo.*.baz', 2)
        glob.add('a.*.*.c', 3, base=base)

        vals = tuple(sorted(v[1] for v in glob.get('foo.bar.baz')))
        self.eq(vals, (2,))

        vals = tuple(sorted(v[1] for v in glob.get('zip.visi')))
        self.eq(vals, (1, 11))

        vals = tuple(sorted(v[1] for v in glob.get('zip.visi.newp')))
        self.eq(vals, ())

        vals = tuple(sorted(v[1] for v in glob.get('a.b.b.c')))
        self.eq(vals, (3,))

        await base.fini()

        vals = tuple(sorted(v[1] for v in glob.get('a.b.b.c')))
        self.eq(vals, ())

        self.len(1, glob.get('zip.hehe'))
        glob.rem('zip.*', 1)
        self.len(0, glob.get('zip.hehe'))

    async def test_lrudict(self):
        lru = s_cache.LruDict(3)
        del lru['foo']
        lru['foo'] = 42
        self.eq(lru['foo'], 42)
        self.len(1, lru)
        self.eq(list(lru), ['foo'])
        del lru['foo']
        self.none(lru.get('foo', None))
        self.none(lru.get('newp', None))
        lru['foo2'] = 'yar'
        lru['foo3'] = 100
        lru['foo4'] = 'yop'
        self.notin('foo', lru)

        # Validate this is a LRU and not least-recently-added
        self.eq(lru['foo3'], 100)
        lru['foo5'] = 1
        lru['foo6'] = True
        self.isin('foo3', lru)

        self.eq(list(lru.items()), (('foo3', 100), ('foo5', 1), ('foo6', True)))
        self.eq(list(lru.keys()), ('foo3', 'foo5', 'foo6'))
        self.eq(list(lru.values()), (100, 1, True))

        # Make sure that disabled dict still work
        lru = s_cache.LruDict(0)
        lru['nope'] = 42
        self.none(lru.get('nope', None))
