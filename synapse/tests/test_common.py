import os
import http
import asyncio
import logging
import subprocess

import yaml
import aiohttp

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.httpapi as s_httpapi

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class CommonTest(s_t_utils.SynTest):

    async def test_waitgenr(self):

        async def genr():
            yield 10
            raise Exception('omg')

        rets = [retn async for retn in s_common.waitgenr(genr(), 10)]

        self.true(rets[0][0])
        self.false(rets[1][0])

        async def one():
            yield 'item'

        rets = [retn async for retn in s_common.waitgenr(one(), timeout=1.0)]
        self.eq(rets, [(True, 'item')])

        async def genr():
            yield 1
            await asyncio.sleep(60)
            yield 2

        rets = [retn async for retn in s_common.waitgenr(genr(), timeout=0.1)]
        self.eq(rets[0], (True, 1))
        self.false(rets[1][0])
        self.eq(rets[1][1]['err'], 'TimeoutError')

    def test_tuplify(self):
        tv = ['node', [['test:str', 'test'],
                       {'tags': {
                           'beep': [None, None],
                           'beep.boop': [0x01020304, 0x01020305]
                       },
                       'props': {
                           'tick': 0x01020304,
                           'tock': ['hehe', ['haha', 1]]
                       }}]]
        ev = ('node', (('test:str', 'test'),
                       {'tags': {
                           'beep': (None, None),
                           'beep.boop': (0x01020304, 0x01020305)
                       },
                       'props': {
                           'tick': 0x01020304,
                           'tock': ('hehe', ('haha', 1))
                       }}))

        self.eq(ev, s_common.tuplify(tv))
        tv = ('foo', ['bar', 'bat'])
        ev = ('foo', ('bar', 'bat'))
        self.eq(ev, s_common.tuplify(tv))

    def test_common_flatten(self):
        item = {'foo': 'bar', 'baz': 10, 'gronk': True, 'hehe': ['ha', 'ha'], 'tupl': (1, 'two'), 'newp': None}
        self.ne('15c8a3727942fa01e04d6a7a525666a2', s_common.guid(item))
        self.eq('15c8a3727942fa01e04d6a7a525666a2', s_common.guid(s_common.flatten(item)))

    def test_common_vertup(self):
        self.eq(s_common.vertup('1.3.30'), (1, 3, 30))
        self.true(s_common.vertup('30.40.50') > (9, 0))

    def test_common_file_helpers(self):

        # genfile
        with self.getTestDir() as testdir:
            fd = s_common.genfile(testdir, 'woot', 'foo.bin')
            fd.write(b'genfile_test')
            fd.close()

            with open(os.path.join(testdir, 'woot', 'foo.bin'), 'rb') as fd:
                buf = fd.read()
            self.eq(buf, b'genfile_test')

        # reqpath
        with self.getTestDir() as testdir:
            with s_common.genfile(testdir, 'test.txt') as fd:
                fd.write(b'')
            self.eq(os.path.join(testdir, 'test.txt'), s_common.reqpath(testdir, 'test.txt'))
            self.raises(s_exc.NoSuchFile, s_common.reqpath, testdir, 'newp')

        # reqfile
        with self.getTestDir() as testdir:
            with s_common.genfile(testdir, 'test.txt') as fd:
                fd.write(b'reqfile_test')
            fd = s_common.reqfile(testdir, 'test.txt')
            buf = fd.read()
            self.eq(buf, b'reqfile_test')
            fd.close()
            self.raises(s_exc.NoSuchFile, s_common.reqfile, testdir, 'newp')

        # getfile
        with self.getTestDir() as testdir:
            with s_common.genfile(testdir, 'test.txt') as fd:
                fd.write(b'getfile_test')
            fd = s_common.getfile(testdir, 'test.txt')
            buf = fd.read()
            self.eq(buf, b'getfile_test')
            fd.close()
            self.none(s_common.getfile(testdir, 'newp'))

        # getbytes
        with self.getTestDir() as testdir:
            with s_common.genfile(testdir, 'test.txt') as fd:
                fd.write(b'getbytes_test')
            buf = s_common.getbytes(testdir, 'test.txt')
            self.eq(buf, b'getbytes_test')
            self.none(s_common.getbytes(testdir, 'newp'))

        # reqbytes
        with self.getTestDir() as testdir:
            with s_common.genfile(testdir, 'test.txt') as fd:
                fd.write(b'reqbytes_test')
            buf = s_common.reqbytes(testdir, 'test.txt')
            self.eq(buf, b'reqbytes_test')
            self.raises(s_exc.NoSuchFile, s_common.reqbytes, testdir, 'newp')

        # listdir
        with self.getTestDir() as dirn:
            path = os.path.join(dirn, 'woot.txt')
            with open(path, 'wb') as fd:
                fd.write(b'woot')

            os.makedirs(os.path.join(dirn, 'nest'))
            with open(os.path.join(dirn, 'nest', 'nope.txt'), 'wb') as fd:
                fd.write(b'nope')

            retn = tuple(s_common.listdir(dirn))
            self.len(2, retn)

            retn = tuple(s_common.listdir(dirn, glob='*.txt'))
            self.eq(retn, ((path,)))

            real, appr = s_common.getDirSize(dirn)
            self.eq(real % 512, 0)
            self.gt(real, appr)
            self.ge(appr, len(b'woot') + len(b'nope'))

    def test_common_intify(self):
        self.eq(s_common.intify(20), 20)
        self.eq(s_common.intify("20"), 20)
        self.none(s_common.intify(None))
        self.none(s_common.intify("woot"))

    def test_common_guid(self):
        iden0 = s_common.guid()
        iden1 = s_common.guid('foo bar baz')
        iden2 = s_common.guid('foo bar baz')
        self.ne(iden0, iden1)
        self.eq(iden1, iden2)

    def test_common_isguid(self):
        self.true(s_common.isguid('98db59098e385f0bfdec8a6a0a6118b3'))
        self.false(s_common.isguid('visi'))

    def test_common_chunks(self):
        s = '123456789'
        parts = [chunk for chunk in s_common.chunks(s, 2)]
        self.eq(parts, ['12', '34', '56', '78', '9'])

        parts = [chunk for chunk in s_common.chunks(s, 100000)]
        self.eq(parts, [s])

        parts = [chunk for chunk in s_common.chunks(b'', 10000)]
        self.eq(parts, [b''])

        parts = [chunk for chunk in s_common.chunks([], 10000)]
        self.eq(parts, [[]])

        parts = [chunk for chunk in s_common.chunks('', 10000)]
        self.eq(parts, [''])

        parts = [chunk for chunk in s_common.chunks([1, 2, 3, 4, 5], 2)]
        self.eq(parts, [[1, 2], [3, 4], [5]])

        # set is unslicable
        with self.assertRaises(TypeError) as cm:
            parts = [chunk for chunk in s_common.chunks({1, 2, 3}, 10000)]

        # dict is unslicable
        with self.assertRaises((TypeError, KeyError)) as cm:
            parts = [chunk for chunk in s_common.chunks({1: 2}, 10000)]

        # empty dict is caught during the [0:0] slice
        with self.assertRaises((TypeError, KeyError)) as cm:
            parts = [chunk for chunk in s_common.chunks({}, 10000)]

    def test_common_ehex_uhex(self):
        byts = b'deadb33f00010203'
        s = s_common.ehex(byts)
        self.isinstance(s, str)
        self.eq(s, '64656164623333663030303130323033')
        # uhex is a linear transform back
        obyts = s_common.uhex(s)
        self.isinstance(obyts, bytes)
        self.eq(byts, obyts)

    def test_common_buid(self):
        byts = b'deadb33f00010203'

        iden = s_common.buid()
        self.isinstance(iden, bytes)
        self.len(32, iden)
        # Buids are random by default
        iden2 = s_common.buid()
        self.ne(iden, iden2)

        # buids may be derived from any msgpackable valu which is stable
        iden3 = s_common.buid(byts)
        evalu = b'\xde\x8a\x8a\x88\xbc \xd4\xc1\x81J\xf5\xc7\xbf\xbc\xd2T6\xba\xd0\xf1\x10\xaa\x07<\xfa\xe5\xfc\x8c\x93\xeb\xb4 '
        self.len(32, iden3)
        self.eq(iden3, evalu)

    def test_common_spin(self):
        s = '1234'
        gen = iter(s)
        s_common.spin(gen)
        # Ensure we consumed everything from the generator
        self.raises(StopIteration, next, gen)

        # Consuming a generator could have effects!
        data = []
        def hehe():
            for c in s:
                data.append(c)
                yield c
        gen = hehe()
        s_common.spin(gen)
        self.eq(data, [c for c in s])

    def test_common_config(self):

        confdefs = (
            ('foo', {'defval': 20}),
            ('bar', {'defval': 30}),
        )

        conf = s_common.config({'foo': 80}, confdefs)

        self.eq(80, conf.get('foo'))
        self.eq(30, conf.get('bar'))

    def test_common_yaml(self):
        obj = [{'key': 1,
                'key2': [1, 2, 3],
                'key3': True,
                'key4': 'some str',
                'key5': {
                    'oh': 'my',
                    'we all': 'float down here'
                }, },
               'duck',
               False,
               'zero',
               0.1,
               ]
        with self.getTestDir() as dirn:
            s_common.yamlsave(obj, dirn, 'test.yaml')
            robj = s_common.yamlload(dirn, 'test.yaml')

            self.eq(obj, robj)

            obj = {'foo': 'bar', 'zap': [3, 4, 'f']}
            s_common.yamlsave(obj, dirn, 'test.yaml')
            s_common.yamlmod({'bar': 42}, dirn, 'test.yaml')
            robj = s_common.yamlload(dirn, 'test.yaml')
            obj['bar'] = 42
            self.eq(obj, robj)

            s_common.yamlmod({'bar': 42}, dirn, 'nomod.yaml')
            robj = s_common.yamlload(dirn, 'nomod.yaml')
            self.eq(robj, {'bar': 42})

            s_common.yamlpop('zap', dirn, 'test.yaml')
            robj = s_common.yamlload(dirn, 'test.yaml')
            self.eq(robj, {'foo': 'bar', 'bar': 42})
            # And its replayable
            s_common.yamlpop('zap', dirn, 'test.yaml')
            # And won't blow up if the file doesn't exist
            s_common.yamlpop('zap', dirn, 'newp.yaml')

            # Test yaml helper safety
            s = '!!python/object/apply:os.system ["pwd"]'
            with s_common.genfile(dirn, 'explode.yaml') as fd:
                fd.write(s.encode())
            self.raises(yaml.YAMLError, s_common.yamlload, dirn, 'explode.yaml')

            # Make sure we're testing the CSafeLoader and not the python native
            # implementation
            self.eq(s_common.Loader, yaml.CSafeLoader)

            data = '{"foo":"bar", "unicode": "✊"}'
            obj = s_common.yamlloads(data)
            self.eq(obj, {'foo': 'bar', 'unicode': '✊'})

            obj = s_common.yamlloads(data.encode('utf8'))
            self.eq(obj, {'foo': 'bar', 'unicode': '✊'})

            obj = s_common.yamlloads('{"foo": "bar", "unicode": "\u270A"}')
            self.eq(obj, {'foo': 'bar', 'unicode': '✊'})

    def test_switchext(self):
        retn = s_common.switchext('foo.txt', ext='.rdf')
        self.eq(retn, s_common.genpath('foo.rdf'))

        retn = s_common.switchext('.vim', ext='.rdf')
        self.eq(retn, s_common.genpath('.vim.rdf'))

    def test_envbool(self):
        with self.setTstEnvars(SYN_FOO='true', SYN_BAR='1', SYN_BAZ='foobar'):
            self.true(s_common.envbool('SYN_FOO'))
            self.true(s_common.envbool('SYN_BAR'))
            self.true(s_common.envbool('SYN_BAZ'))
            # non-existent and default behaviors
            self.false(s_common.envbool('SYN_NEWP'))
            self.true(s_common.envbool('SYN_NEWP', '1'))

        with self.setTstEnvars(SYN_FOO='false', SYN_BAR='0'):
            self.false(s_common.envbool('SYN_FOO'))
            self.false(s_common.envbool('SYN_BAR'))

    def test_normlog(self):
        self.eq(10, s_common.normLogLevel(' 10 '))
        self.eq(10, s_common.normLogLevel(10))
        self.eq(20, s_common.normLogLevel(' inFo\n'))
        with self.raises(s_exc.BadArg):
            s_common.normLogLevel(100)
        with self.raises(s_exc.BadArg):
            s_common.normLogLevel('BEEP')
        with self.raises(s_exc.BadArg):
            s_common.normLogLevel('12')
        with self.raises(s_exc.BadArg):
            s_common.normLogLevel({'key': 'newp'})

    async def test_merggenr(self):
        async def asyncl(data):
            for item in data:
                yield item

        async def alist(coro):
            return [x async for x in coro]

        l1 = (1, 2, 3)
        l2 = (4, 5, 6)
        l3 = (7, 8, 9)

        retn = s_common.merggenr([asyncl(lt) for lt in (l1, l2, l3)], lambda x, y: x < y)
        self.eq((1, 2, 3, 4, 5, 6, 7, 8, 9), await alist(retn))

        retn = s_common.merggenr([asyncl(lt) for lt in (l1, l1, l1)], lambda x, y: x < y)
        self.eq((1, 1, 1, 2, 2, 2, 3, 3, 3), await alist(retn))

        retn = s_common.merggenr([asyncl(lt) for lt in (l3, l2, l1)], lambda x, y: x < y)
        self.eq((1, 2, 3, 4, 5, 6, 7, 8, 9), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l2, l3, ())], lambda x: x)
        self.eq((1, 2, 3, 4, 5, 6, 7, 8, 9), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l1, l1)], lambda x: x)
        self.eq((1, 1, 1, 2, 2, 2, 3, 3, 3), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l3, l2, l1)], lambda x: x)
        self.eq((1, 2, 3, 4, 5, 6, 7, 8, 9), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l2, l3, ())])
        self.eq((1, 2, 3, 4, 5, 6, 7, 8, 9), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l1, l1)])
        self.eq((1, 1, 1, 2, 2, 2, 3, 3, 3), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l3, l2, l1)])
        self.eq((1, 2, 3, 4, 5, 6, 7, 8, 9), await alist(retn))

        l1 = (3, 2, 1)
        l2 = (6, 5, 4)
        l3 = (9, 8, 7)

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l2, l3)], lambda x: x, True)
        self.eq((9, 8, 7, 6, 5, 4, 3, 2, 1), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l1, l1)], lambda x: x, True)
        self.eq((3, 3, 3, 2, 2, 2, 1, 1, 1), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l3, l2, l1)], lambda x: x, True)
        self.eq((9, 8, 7, 6, 5, 4, 3, 2, 1), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l2, l3)], reverse=True)
        self.eq((9, 8, 7, 6, 5, 4, 3, 2, 1), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l1, l1, l1)], reverse=True)
        self.eq((3, 3, 3, 2, 2, 2, 1, 1, 1), await alist(retn))

        retn = s_common.merggenr2([asyncl(lt) for lt in (l3, l2, l1)], reverse=True)
        self.eq((9, 8, 7, 6, 5, 4, 3, 2, 1), await alist(retn))

    def test_sslctx(self):
        with self.getTestDir(mirror='certdir') as dirn:
            cadir = s_common.genpath(dirn, 'cas')
            os.makedirs(s_common.genpath(cadir, 'newp'))
            with self.getLoggerStream('synapse.common', f'Error loading {cadir}/ca.key') as stream:
                ctx = s_common.getSslCtx(cadir)
                self.true(stream.wait(10))
            ca_subjects = {cert.get('subject') for cert in ctx.get_ca_certs()}
            self.isin(((('commonName', 'test'),),), ca_subjects)

    async def test_wait_for(self):

        async def foo():
            return 123

        loop = asyncio.get_running_loop()
        footask = loop.create_task(foo())

        await footask

        self.eq(123, await s_common.wait_for(footask, timeout=-1))

    def test_trim_text(self):
        tvs = (
            ('Hello world!', 'Hello world!'),
            ('Hello world 123', 'Hello world 123'),
            ('Hello world 1234', 'Hello world 1234'),
            ('Hello world 12345', 'Hello world 1...'),
            ('Hello world 1234 5678', 'Hello world 1...'),
            ('HelloXworldY1234Z5678', 'HelloXworldY1...'),
        )
        n = 16
        for iv, ev in tvs:
            v = s_common.trimText(iv, n=n)
            self.le(len(v), n)
            self.eq(v, ev)

    async def test_tornado_monkeypatch(self):
        class JsonHandler(s_httpapi.Handler):
            async def get(self):
                resp = {
                    'foo': 'bar',
                    'html': '<html></html>'
                }
                self.write(resp)

        async with self.getTestCore() as core:
            core.addHttpApi('/api/v1/test_tornado/', JsonHandler, {'cell': core})
            _, port = await core.addHttpsPort(0)
            url = f'https://127.0.0.1:{port}/api/v1/test_tornado/'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, ssl=False) as resp:
                    self.eq(resp.status, http.HTTPStatus.OK)

                    text = await resp.text()
                    self.eq(text, '{"foo":"bar","html":"<html><\\/html>"}')

                    json = await resp.json()
                    self.eq(json, {'foo': 'bar', 'html': '<html></html>'})
