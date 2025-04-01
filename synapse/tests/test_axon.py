import io
import os
import csv
import http
import base64
import shutil
import struct
import asyncio
import hashlib
import logging
import unittest.mock as mock
import tornado.httputil as t_httputil

import aiohttp.client_exceptions as a_exc

import synapse.exc as s_exc
import synapse.axon as s_axon
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.coro as s_coro
import synapse.lib.certdir as s_certdir
import synapse.lib.httpapi as s_httpapi
import synapse.lib.msgpack as s_msgpack

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

# This causes blocks which are not homogeneous when sliced in kibibyte lengths
bbuf = b'0123456' * 4793491
abuf = b'asdfasdf'
pbuf = b'pennywise'
rbuf = b'robert gray'
bin_buf = b'\xbb/$\xc0A\xf1\xbf\xbc\x00_\x82v4\xf6\xbd\x1b'

# sample of a real world csv with a extended ascii character encoding in
# one row which causes decoding errors.
csv_badenc_b64 = 'Zm9vLTAxNjIsMSwiVGhlICIiYmFyIiIga2V5d29yZCBkb2VzIGEgdGhpb' \
                 'mcuIiwiIiwiIgpmb28tMDE2MywyLCJtYWlsIGdvZXMgYnJycnJycnIiLG' \
                 'JlZXAsImJvb3AiLCJh/GIiCmZvby0wMTY0LDEsImJpZyB3b3JkcyBzbWF' \
                 'sbCB3b3JkcyIsIiIsIiIK'
csv_badenc_buf = base64.b64decode(csv_badenc_b64)

bbufhash = hashlib.sha256(bbuf).digest()
asdfhash = hashlib.sha256(abuf).digest()
emptyhash = hashlib.sha256(b'').digest()
pennhash = hashlib.sha256(pbuf).digest()
rgryhash = hashlib.sha256(rbuf).digest()
newphash = s_common.buid('newp')
csv_badenc_hash = hashlib.sha256(csv_badenc_buf).digest()

fields = [
    {'name': 'file', 'sha256': s_common.ehex(asdfhash), 'filename': 'file'},
    {'name': 'zip_password', 'value': 'test'},
    {'name': 'dict', 'value': {'foo': 'bar'}},
    {'name': 'bytes', 'value': b'coolbytes'},
]

asdfretn = (8, asdfhash)
emptyretn = (0, emptyhash)
pennretn = (9, pennhash)
rgryretn = (11, rgryhash)
bbufretn = (len(bbuf), bbufhash)

linesbuf = b'''asdf

qwer
'''

jsonsbuf = b'''
{"foo": "bar"}
{"baz": "faz"}
'''

class HttpPushFile(s_httpapi.StreamHandler):

    async def prepare(self):
        self.gotsize = 0
        self.byts = b''

    async def data_received(self, byts):
        self.gotsize += len(byts)
        self.byts += byts

    async def put(self):
        assert self.gotsize == 8
        self.sendRestRetn(self.gotsize)

    async def post(self):
        args = {}
        files = {}
        t_httputil.parse_body_arguments(self.request.headers["Content-Type"],
                                        self.byts, args, files)
        item = files.get('file')[0]

        assert item['body'] == b'asdfasdf'
        assert item['filename'] == 'file'

        item = files.get('bytes')[0]

        assert item['body'] == b'coolbytes'
        assert item['filename'] == 'bytes'

        assert args.get('zip_password') == [b'test']
        assert args.get('dict') == [b'{"foo":"bar"}']
        self.sendRestRetn(self.gotsize)

class AxonTest(s_t_utils.SynTest):

    async def check_blob(self, axon, fhash):
        chunks = [chunk async for chunk in axon.get(fhash)]
        buf = b''.join(chunks)
        ahash = hashlib.sha256(buf).digest()
        self.eq(fhash, ahash)

    async def runAxonTestBase(self, axon):

        tick = s_common.now()

        # asdfhash test

        self.false(await axon.has(asdfhash))

        with self.raises(s_exc.NoSuchFile):
            async for _ in axon.get(asdfhash):
                pass

        with self.raises(s_exc.NoSuchFile):
            await axon.hashset(asdfhash)

        self.len(0, [item async for item in axon.hashes(0)])

        async with await axon.upload() as fd:
            await fd.write(abuf)
            self.eq(asdfretn, await fd.save())

        # do it again to test the short circuit
        async with await axon.upload() as fd:
            await fd.write(abuf)
            self.eq(asdfretn, await fd.save())

        bytz = []
        async for byts in axon.get(asdfhash):
            bytz.append(byts)

        self.eq(b'asdfasdf', b''.join(bytz))

        self.true(await axon.has(asdfhash))
        self.eq(8, await axon.size(asdfhash))

        # bbufhash test

        self.false(await axon.has(bbufhash))

        self.eq((bbufhash,), await axon.wants((bbufhash, asdfhash)))

        async with await axon.upload() as fd:
            await fd.write(bbuf)
            self.eq(bbufretn, await fd.save())

        self.true(await axon.has(asdfhash))
        self.true(await axon.has(bbufhash))
        await self.check_blob(axon, bbufhash)

        self.eq((), await axon.wants((bbufhash, asdfhash)))

        # put() / puts() tests
        # These don't add new data; but exercise apis to load data
        retn = await axon.put(abuf)
        self.eq(retn, asdfretn)

        retn = await axon.puts([abuf, bbuf])
        self.eq(retn, (asdfretn, bbufretn))

        # History and metrics

        items = [x async for x in axon.hashes(0)]
        self.eq(((0, (asdfhash, 8)), (1, (bbufhash, 33554437))), items)

        items = [x[1] async for x in axon.history(tick)]
        self.eq(((asdfhash, 8), (bbufhash, 33554437)), items)

        items = [x[1] async for x in axon.history(0, tock=1)]
        self.eq((), items)

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(2, info.get('file:count'))

        # Empty file test

        async with await axon.upload() as fd:
            await fd.write(b'')
            self.eq(emptyretn, await fd.save())
        self.true(await axon.has(emptyhash))
        self.eq(0, await axon.size(emptyhash))

        info = await axon.metrics()
        self.eq(33554445, info.get('size:bytes'))
        self.eq(3, info.get('file:count'))

        bytz = []
        async for byts in axon.get(emptyhash):
            bytz.append(byts)

        self.eq(b'', b''.join(bytz))

        # Healthcheck test
        snfo = await axon.getHealthCheck()
        self.eq(snfo.get('status'), 'nominal')
        axfo = [comp for comp in snfo.get('components') if comp.get('name') == 'axon'][0]
        self.eq(axfo.get('data'), await axon.metrics())

        # Upload context reuse
        with mock.patch('synapse.axon.MAX_SPOOL_SIZE', s_axon.CHUNK_SIZE * 2):

            very_bigbuf = (s_axon.MAX_SPOOL_SIZE + 2) * b'V'
            vbighash = hashlib.sha256(very_bigbuf).digest()
            vbigretn = (len(very_bigbuf), vbighash)

            async with await axon.upload() as fd:
                # We can reuse the FD _after_ we have called save() on it.
                await fd.write(abuf)
                retn = await fd.save()
                self.eq(retn, asdfretn)

                # Reuse after uploading an existing file
                # Now write a new file
                await fd.write(pbuf)
                retn = await fd.save()
                self.eq(retn, pennretn)
                await self.check_blob(axon, pennhash)

                # Reuse test with large file causing a rollover
                for chunk in s_common.chunks(very_bigbuf, s_axon.CHUNK_SIZE):
                    await fd.write(chunk)
                retn = await fd.save()
                self.eq(retn, vbigretn)
                await self.check_blob(axon, vbighash)

                # Reuse test with small file post rollover
                await fd.write(rbuf)
                retn = await fd.save()
                self.eq(retn, rgryretn)
                await self.check_blob(axon, rgryhash)

        info = await axon.metrics()
        self.eq(67108899, info.get('size:bytes'))
        self.eq(6, info.get('file:count'))

        byts = b''.join([s_msgpack.en('foo'), s_msgpack.en('bar'), s_msgpack.en('baz')])
        size, sha256b = await axon.put(byts)
        sha256 = s_common.ehex(sha256b)
        self.eq(('foo', 'bar', 'baz'), [item async for item in axon.iterMpkFile(sha256)])

        # When testing a local axon, we want to ensure that the FD was in fact fini'd
        if isinstance(fd, s_axon.UpLoad):
            self.true(fd.fd.closed)

        self.true(await axon.del_(bbufhash))
        self.eq((False,), await axon.dels((bbufhash,)))

        info = await axon.metrics()
        self.eq(33554474, info.get('size:bytes'))
        self.eq(6, info.get('file:count'))

        self.notin(bbufretn[::-1], [item[1] async for item in axon.hashes(0)])

        self.false(await axon.del_(bbufhash))

        # deleted file re-added gets returned twice by hashes
        retn = await axon.put(bbuf)
        self.eq(retn, bbufretn)
        self.len(2, [item[1] async for item in axon.hashes(0) if item[1][0] == bbufhash])
        self.len(1, [item[1] async for item in axon.hashes(2) if item[1][0] == bbufhash])

        # readlines / jsonlines
        (lsize, l256) = await axon.put(linesbuf)
        (jsize, j256) = await axon.put(jsonsbuf)
        (bsize, b256) = await axon.put(b'\n'.join((jsonsbuf, linesbuf)))
        (binsize, bin256) = await axon.put(bin_buf)

        lines = [item async for item in axon.readlines(s_common.ehex(l256))]
        self.eq(('asdf', '', 'qwer'), lines)
        lines = [item async for item in axon.readlines(s_common.ehex(bin256))]  # Default is errors=ignore
        self.eq(lines, ['/$A\x00_v4\x1b'])
        lines = [item async for item in axon.readlines(s_common.ehex(bin256), errors='replace')]
        self.eq(lines, ['�/$�A�\x00_�v4��\x1b'])
        jsons = [item async for item in axon.jsonlines(s_common.ehex(j256))]
        self.eq(({'foo': 'bar'}, {'baz': 'faz'}), jsons)
        jsons = []
        with self.raises(s_exc.BadJsonText):
            async for item in axon.jsonlines(s_common.ehex(b256)):
                jsons.append(item)
        self.eq(({'foo': 'bar'}, {'baz': 'faz'}), jsons)

        with self.raises(s_exc.BadDataValu):
            lines = [item async for item in axon.readlines(s_common.ehex(bin256), errors=None)]

        with self.raises(s_exc.NoSuchFile):
            lines = [item async for item in axon.readlines(s_common.ehex(newphash))]

        with self.raises(s_exc.NoSuchFile):
            lines = [item async for item in axon.jsonlines(s_common.ehex(newphash))]

        # readlines byte alignment test
        csize = s_axon.CHUNK_SIZE
        stuff = (csize - 3) * 'v'
        lines = [stuff, '.ॐwords']
        buf = '\n'.join(lines)
        size, sha256 = await axon.put(buf.encode())
        lines = [item async for item in axon.readlines(s_common.ehex(sha256))]
        self.len(2, lines)
        self.eq(lines[1], '.ॐwords')

        # regular csv
        data = '''John,Doe,120 jefferson st.,Riverside, NJ, 08075
Jack,McGinnis,220 hobo Av.,Phila, PA,09119
"John ""Da Man""",Repici,120 Jefferson St.,Riverside, NJ,08075
"Stephen, aka the dude",Tyler,"7452 Terrace ""At the Plaza"" road",SomeTown,SD, 91234
,Blankman,,SomeTown, SD, 00298
"Joan ""the bone"", Anne",Jet,"9th, at Terrace plc",Desert City,CO,00123
Bob,Smith,Little House at the end of Main Street,Gomorra,CA,12345'''
        data = '\n'.join([data for _ in range(10)])
        size, sha256 = await axon.put(data.encode())
        rows = [row async for row in axon.csvrows(sha256)]
        self.len(70, rows)
        for row in rows:
            self.len(6, row)
        names = {row[0] for row in rows}
        self.len(7, names)
        enames = {'John', 'Jack', 'John "Da Man"', 'Stephen, aka the dude', '',
                  'Joan "the bone", Anne', 'Bob'}
        self.eq(names, enames)

        evt = asyncio.Event()
        origlink = s_axon.Axon._sha256ToLink
        async def fakelink(self, sha256_, link):
            link.onfini(evt.set)
            if sha256_ == pennhash:
                sha256_ = b'newp'
            await origlink(self, sha256_, link)

        newdata = '\n'.join([data for i in range(500)])
        size, sha256 = await axon.put(newdata.encode())

        with mock.patch('synapse.axon.Axon._sha256ToLink', fakelink):
            async for row in axon.csvrows(sha256):
                break
            self.true(await s_coro.event_wait(evt, 5))

            evt.clear()
            async for row in axon.readlines(s_common.ehex(sha256)):
                break
            self.true(await s_coro.event_wait(evt, 5))

            # make sure exceptions within sha256tolink get re-raised
            await self.asyncraises(s_exc.NoSuchFile, s_t_utils.alist(axon.csvrows(pennhash)))
            await self.asyncraises(s_exc.NoSuchFile, s_t_utils.alist(axon.readlines(s_common.ehex(pennhash))))

        # CSV with alternative delimiter
        data = '''foo|bar|baz
words|word|wrd'''
        size, sha256 = await axon.put(data.encode())
        rows = [row async for row in axon.csvrows(sha256, delimiter='|')]
        self.len(2, rows)
        for row in rows:
            self.len(3, row)

        # CSV With embedded newlines
        data = '''i,s,nonce
0,"foo
bar baz",
1,"foo
bar baz",v
2,"foo
bar baz",vv
'''
        size, sha256 = await axon.put(data.encode())
        rows = [row async for row in axon.csvrows(sha256)]
        self.len(4, rows)
        nlchunk = 'foo\nbar baz'
        erows = [['i', 's', 'nonce'], ['0', nlchunk, ''], ['1', nlchunk, 'v'], ['2', nlchunk, 'vv'], ]
        self.eq(rows, erows)

        # CSV with bad dialect
        with self.raises(s_exc.BadArg):
            rows = [row async for row in axon.csvrows(sha256, dialect='newp')]

        # Bad fmtparams
        with self.raises(s_exc.BadArg) as cm:
            rows = [row async for row in axon.csvrows(sha256, newp='newp')]

        # From CPython Test_Csv.test_read_eof
        eofbuf = '"a,'.encode()
        size, eofsha256 = await axon.put(eofbuf)
        with self.raises(s_exc.BadDataValu) as cm:
            rows = [row async for row in axon.csvrows(eofsha256, strict=True)]
        self.isin('unexpected end of data', cm.exception.get('mesg'))

        # Python 3.11+ - csv handles null bytes in an acceptable fashion.
        # See https://github.com/python/cpython/issues/71767 for discussion
        rows = [row async for row in axon.csvrows(bin256)]
        self.eq(rows, (('/$A\x00_v4\x1b',),))

        with self.raises(s_exc.NoSuchFile):
            lines = [item async for item in axon.csvrows(newphash)]

        # Single column csv blob with byte alignment issues
        fslm = csv.field_size_limit()
        csize = s_axon.CHUNK_SIZE
        buf = b''
        while True:
            buf = buf + (b'v' * fslm) + b'\n'
            if csize - len(buf) < fslm:
                break
        rem = csize - len(buf)
        buf = buf + b'v' * (rem - 3) + b'\n' + '.ॐwords'.encode()
        size, sha256 = await axon.put(buf)
        rows = [item async for item in axon.csvrows(sha256)]
        self.len(129, rows)
        for row in rows:
            self.len(1, row)
        self.eq(rows[-1], ['.ॐwords'])

        # This is pulled from CPython's csv test suite to throw a CSV error.
        size, sha256 = await axon.put('"a'.encode())
        with self.raises(s_exc.BadDataValu) as cm:
            rows = [row async for row in axon.csvrows(sha256, strict=True)]

        # A csvfile with an extended ascii character in it
        size, sha256 = await axon.put(csv_badenc_buf)
        self.eq(sha256, csv_badenc_hash)
        rows = [item async for item in axon.csvrows(sha256)]
        self.len(3, rows)

        erows = (('foo-0162', '1', 'The "bar" keyword does a thing.', '', ''),
                 ('foo-0163', '2', 'mail goes brrrrrrr', 'beep', 'boop', 'ab'),
                 ('foo-0164', '1', 'big words small words', '', ''),
                 )
        self.eq(rows, erows)

        info = await axon.getCellInfo()
        if info.get('features', {}).get('byterange') and not isinstance(axon, (s_telepath.Proxy, s_telepath.Client)):
            logger.info(f'Running range test for {axon}')
            # hand insert a genr to control offset sizes
            def genr():
                yield b'asdf'
                yield b'qwer'
                yield b'zxcv'

            asdfbyts = b'asdfqwerzxcv'
            sha256 = hashlib.sha256(asdfbyts).digest()
            await axon.save(sha256, genr(), size=len(asdfbyts))

            bytslist = [b async for b in axon.get(sha256, 0, size=2)]
            self.eq(b'as', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 0, size=12)]
            self.eq(b'asdfqwerzxcv', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 0, size=13)]
            self.eq(b'asdfqwerzxcv', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 0, size=4)]
            self.eq(b'asdf', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 2, size=4)]
            self.eq(b'dfqw', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 2, size=6)]
            self.eq(b'dfqwer', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 11, size=6)]
            self.eq(b'v', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 12, size=6)]
            self.eq(b'', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 13, size=6)]
            self.eq(b'', b''.join(bytslist))

            with self.raises(s_exc.BadArg):
                bytslist = [b async for b in axon.get(sha256, 1, size=-1)]

            with self.raises(s_exc.BadArg):
                bytslist = [b async for b in axon.get(sha256, -1, size=1)]

            with self.raises(s_exc.BadArg):
                bytslist = [b async for b in axon.get(sha256, 0, size=0)]

        # test unpack
        intdata = struct.pack('>QQQ', 1, 2, 3)
        size, sha256 = await axon.put(intdata)
        self.eq((1,), await axon.unpack(sha256, '>Q'))
        self.eq((2,), await axon.unpack(sha256, '>Q', offs=8))
        self.eq((3,), await axon.unpack(sha256, '>Q', offs=16))
        self.eq((2, 3), await axon.unpack(sha256, '>QQ', offs=8))

        fmt = 'Q' * 150_000
        with self.raises(s_exc.BadArg) as cm:
            await axon.unpack(sha256, '>' + fmt)
        self.isin('Struct format would read too much data', cm.exception.get('mesg'))

        with self.raises(s_exc.BadArg):
            await axon.unpack(sha256, 'not a valid format')

        with self.raises(s_exc.BadArg):
            await axon.unpack(sha256, 123)

        with self.raises(s_exc.BadDataValu):
            await axon.unpack(sha256, '>Q', offs=24)

    async def test_axon_base(self):
        async with self.getTestAxon() as axon:
            self.isin('axon', axon.dmon.shared)
            await self.runAxonTestBase(axon)

            # test behavior for two concurrent uploads where the file exists once the lock is released
            self.eq(bbufretn, await axon.put(bbuf))
            self.true(await axon.has(bbufhash))

            with self.raises(ValueError) as cm:
                async with axon.holdHashLock(bbufhash):
                    raise ValueError('oops')
            self.none(axon.hashlocks.get(bbufhash))

            def emptygen():
                if False:
                    yield None
                return

            self.eq(bbufretn[0], await axon.save(bbufhash, emptygen(), size=bbufretn[0]))

    async def test_axon_proxy(self):
        async with self.getTestAxon() as axon:
            async with axon.getLocalProxy() as prox:
                await self.runAxonTestBase(prox)

    async def test_axon_http(self):

        # HTTP handlers on a standalone Axon
        async with self.getTestAxon() as axon:
            await self.runAxonTestHttp(axon)

    async def runAxonTestHttp(self, axon, realaxon=None):
        '''
        Test Axon HTTP APIs.

        Args:
            axon: A cell that implements the axon http apis
            realaxon: The actual axon cell; if None defaults to the axon arg
        '''

        if realaxon is None:
            realaxon = axon

        host, port = await axon.addHttpsPort(0, host='127.0.0.1')

        newb = await axon.auth.addUser('newb')
        await newb.setPasswd('secret')

        url_de = f'https://localhost:{port}/api/v1/axon/files/del'
        url_ul = f'https://localhost:{port}/api/v1/axon/files/put'
        url_hs = f'https://localhost:{port}/api/v1/axon/files/has/sha256'
        url_dl = f'https://localhost:{port}/api/v1/axon/files/by/sha256'

        asdfhash_h = s_common.ehex(asdfhash)
        bbufhash_h = s_common.ehex(bbufhash)
        emptyhash_h = s_common.ehex(emptyhash)

        # No auth - coverage
        async with self.getHttpSess() as sess:
            async with sess.get(f'{url_dl}/foobar') as resp:
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                info = await resp.json()
                self.eq('NotAuthenticated', info.get('code'))
            async with sess.head(f'{url_dl}/foobar') as resp:
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                # aiohttp ignores HEAD bodies
            async with sess.delete(f'{url_dl}/foobar') as resp:
                self.eq(resp.status, http.HTTPStatus.UNAUTHORIZED)
                info = await resp.json()
                self.eq('NotAuthenticated', info.get('code'))

        # Perms
        async with self.getHttpSess(auth=('newb', 'secret'), port=port) as sess:

            async with sess.get(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.delete(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.get(f'{url_hs}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.head(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                item = await resp.json()

            async with sess.post(url_de) as resp:
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                item = await resp.json()
                self.eq('err', item.get('status'))

            async with sess.post(url_ul, data=abuf) as resp:
                self.eq(resp.status, http.HTTPStatus.FORBIDDEN)
                item = await resp.json()
                self.eq('err', item.get('status'))

            # Stream file
            byts = io.BytesIO(bbuf)
            with self.raises((a_exc.ServerDisconnectedError,
                              a_exc.ClientOSError)):
                async with sess.post(url_ul, data=byts) as resp:
                    pass

        await newb.addRule((True, ('axon', 'get')))
        await newb.addRule((True, ('axon', 'has')))
        await newb.addRule((True, ('axon', 'del')))
        await newb.addRule((True, ('axon', 'upload')))

        # Basic
        async with self.getHttpSess(auth=('newb', 'secret'), port=port) as sess:
            async with sess.get(f'{url_dl}/foobar') as resp:
                self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                info = await resp.json()
                self.eq('err', info.get('status'))
                self.eq('BadArg', info.get('code'))
                self.eq('Hash is not a SHA-256: foobar', info.get('mesg'))

            async with sess.get(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                info = await resp.json()
                self.eq('err', info.get('status'))
                self.eq('NoSuchFile', info.get('code'))
                self.eq(f'SHA-256 not found: {asdfhash_h}', info.get('mesg'))

            async with sess.get(f'{url_hs}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.false(item.get('result'))

            async with sess.post(url_ul, data=abuf) as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(set(result.keys()), {'size', 'md5', 'sha1', 'sha256', 'sha512'})
                self.eq(result.get('size'), asdfretn[0])
                self.eq(result.get('sha256'), asdfhash_h)
                self.true(await realaxon.has(asdfhash))

            async with sess.get(f'{url_hs}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.true(item.get('result'))

            async with sess.put(url_ul, data=abuf) as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), asdfretn[0])
                self.eq(result.get('sha256'), asdfhash_h)
                self.true(await realaxon.has(asdfhash))

            async with sess.get(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                self.eq(abuf, await resp.read())

            # Streaming upload
            byts = io.BytesIO(bbuf)

            async with sess.post(url_ul, data=byts) as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), bbufretn[0])
                self.eq(result.get('sha256'), bbufhash_h)
                self.true(await realaxon.has(bbufhash))

            byts = io.BytesIO(bbuf)

            async with sess.put(url_ul, data=byts) as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), bbufretn[0])
                self.eq(result.get('sha256'), bbufhash_h)
                self.true(await realaxon.has(bbufhash))

            byts = io.BytesIO(b'')

            async with sess.post(url_ul, data=byts) as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                result = item.get('result')
                self.eq(result.get('size'), emptyretn[0])
                self.eq(result.get('sha256'), emptyhash_h)
                self.true(await realaxon.has(emptyhash))

            # Streaming download
            async with sess.get(f'{url_dl}/{bbufhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.OK)

                byts = []
                async for bytz in resp.content.iter_chunked(1024):
                    byts.append(bytz)

                self.gt(len(byts), 1)
                self.eq(bbuf, b''.join(byts))

            # HEAD
            async with sess.head(f'{url_dl}/{bbufhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                self.eq('33554437', resp.headers.get('content-length'))
                self.none(resp.headers.get('content-range'))

            async with sess.head(f'{url_dl}/foobar') as resp:
                self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                self.eq('0', resp.headers.get('content-length'))

            # DELETE method by sha256
            async with sess.delete(f'{url_dl}/foobar') as resp:
                self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                info = await resp.json()
                self.eq('err', info.get('status'))
                self.eq('BadArg', info.get('code'))
                self.eq('Hash is not a SHA-256: foobar', info.get('mesg'))

            async with sess.delete(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.true(item.get('result'))

            async with sess.delete(f'{url_dl}/{asdfhash_h}') as resp:
                self.eq(resp.status, http.HTTPStatus.NOT_FOUND)
                item = await resp.json()
                self.eq('err', item.get('status'))

            # test /api/v1/axon/file/del API
            data = {'sha256s': (asdfhash_h, asdfhash_h)}
            async with sess.post(url_de, json=data) as resp:
                self.eq(resp.status, http.HTTPStatus.OK)
                item = await resp.json()
                self.eq('ok', item.get('status'))
                self.eq(((asdfhash_h, False), (asdfhash_h, False)), item.get('result'))

            data = {'newp': 'newp'}
            async with sess.post(url_de, json=data) as resp:
                self.eq(resp.status, http.HTTPStatus.BAD_REQUEST)
                item = await resp.json()
                self.eq('err', item.get('status'))
                self.eq('SchemaViolation', item.get('code'))

            info = await axon.getCellInfo()
            if info.get('features', {}).get('byterange'):
                # hand insert a genr to control offset sizes
                def genr():
                    yield b'asdf'
                    yield b'qwer'
                    yield b'zxcv'

                asdfbyts = b'asdfqwerzxcv'
                sha256 = hashlib.sha256(asdfbyts).digest()
                await axon.save(sha256, genr(), size=len(asdfbyts))
                shatext = s_common.ehex(sha256)

                headers = {'range': 'bytes=2-4'}
                async with sess.get(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('3', resp.headers.get('content-length'))
                    self.eq('bytes 2-4/12', resp.headers.get('content-range'))
                    buf = b''
                    async for byts in resp.content.iter_chunked(1024):
                        buf = buf + byts
                    self.eq(buf, b'dfq')

                headers = {'range': 'bytes=,2-'}
                async with sess.get(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('10', resp.headers.get('content-length'))
                    self.eq('bytes 2-11/12', resp.headers.get('content-range'))
                    buf = b''
                    async for byts in resp.content.iter_chunked(1024):
                        buf = buf + byts
                    self.eq(buf, b'dfqwerzxcv')

                headers = {'range': 'bytes=0-11'}
                async with sess.get(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('12', resp.headers.get('content-length'))
                    self.eq('bytes 0-11/12', resp.headers.get('content-range'))
                    buf = b''
                    async for byts in resp.content.iter_chunked(1024):
                        buf = buf + byts
                    self.eq(buf, b'asdfqwerzxcv')

                headers = {'range': 'bytes=10-11'}
                async with sess.get(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('2', resp.headers.get('content-length'))
                    self.eq('bytes 10-11/12', resp.headers.get('content-range'))
                    buf = b''
                    async for byts in resp.content.iter_chunked(1024):
                        buf = buf + byts
                    self.eq(buf, b'cv')

                headers = {'range': 'bytes=11-11'}
                async with sess.get(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('1', resp.headers.get('content-length'))
                    self.eq('bytes 11-11/12', resp.headers.get('content-range'))
                    buf = b''
                    async for byts in resp.content.iter_chunked(1024):
                        buf = buf + byts
                    self.eq(buf, b'v')

                headers = {'range': 'bytes=2-4,8-11'}
                async with sess.get(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('3', resp.headers.get('content-length'))
                    self.eq('bytes 2-4/12', resp.headers.get('content-range'))
                    buf = b''
                    async for byts in resp.content.iter_chunked(1024):
                        buf = buf + byts
                    self.eq(buf, b'dfq')

                # HEAD tests
                headers = {'range': 'bytes=2-4'}
                async with sess.head(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('3', resp.headers.get('content-length'))
                    self.eq('bytes 2-4/12', resp.headers.get('content-range'))

                headers = {'range': 'bytes=10-11'}
                async with sess.head(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('2', resp.headers.get('content-length'))
                    self.eq('bytes 10-11/12', resp.headers.get('content-range'))

                headers = {'range': 'bytes=11-11'}
                async with sess.head(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.PARTIAL_CONTENT)
                    self.eq('1', resp.headers.get('content-length'))
                    self.eq('bytes 11-11/12', resp.headers.get('content-range'))

                # TODO - In python 3.13+ this can be HTTPStatus.RANGE_NOT_SATISFIABLE
                # Reading past blobsize isn't valid HTTP
                headers = {'range': 'bytes=10-20'}
                async with sess.head(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)

                headers = {'range': 'bytes=11-12'}
                async with sess.head(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)

                headers = {'range': 'bytes=20-40'}
                async with sess.head(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)

                # Negative size
                headers = {'range': 'bytes=20-4'}
                async with sess.head(f'{url_dl}/{shatext}', headers=headers) as resp:
                    self.eq(resp.status, http.HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)

    async def test_axon_perms(self):
        async with self.getTestAxon() as axon:
            user = await axon.auth.addUser('user')
            await user.setPasswd('test')
            _, port = await axon.dmon.listen('tcp://127.0.0.1:0')
            aurl = f'tcp://user:test@127.0.0.1:{port}/axon'
            async with await s_telepath.openurl(aurl) as prox:  # type: s_axon.AxonApi
                # Ensure the user can't do things with bytes they don't have permissions too.
                await self.agenraises(s_exc.AuthDeny, prox.get(asdfhash))
                await self.asyncraises(s_exc.AuthDeny, prox.has(asdfhash))
                await self.asyncraises(s_exc.AuthDeny, prox.hashset(asdfhash))
                await self.agenraises(s_exc.AuthDeny, prox.hashes(0))
                await self.agenraises(s_exc.AuthDeny, prox.history(0))
                await self.asyncraises(s_exc.AuthDeny, prox.del_(asdfhash))
                await self.asyncraises(s_exc.AuthDeny, prox.dels((asdfhash,)))
                await self.asyncraises(s_exc.AuthDeny, prox.wants((asdfhash,)))
                await self.asyncraises(s_exc.AuthDeny, prox.put(abuf))
                await self.asyncraises(s_exc.AuthDeny, prox.puts((abuf,)))
                await self.asyncraises(s_exc.AuthDeny, prox.upload())
                await self.asyncraises(s_exc.AuthDeny, prox.metrics())
                # now add rules and run the test suite
                await user.addRule((True, ('health',)))
                await user.addRule((True, ('axon', 'get',)))
                await user.addRule((True, ('axon', 'del',)))
                await user.addRule((True, ('axon', 'has',)))
                await user.addRule((True, ('axon', 'upload',)))
                await self.runAxonTestBase(prox)

    async def test_axon_limits(self):

        async with self.getTestAxon(conf={'max:count': 10}) as axon:
            for i in range(10):
                await axon.put(s_common.buid())

            with self.raises(s_exc.HitLimit):
                await axon.put(s_common.buid())

        async with self.getTestAxon(conf={'max:bytes': 320}) as axon:
            for i in range(10):
                await axon.put(s_common.buid())

            with self.raises(s_exc.HitLimit):
                await axon.put(s_common.buid())

    async def test_axon_wget(self):

        async with self.getTestAxon() as axon:

            visi = await axon.auth.addUser('visi')
            await visi.setAdmin(True)
            await visi.setPasswd('secret')

            async with await axon.upload() as fd:
                await fd.write(b'asdfasdf')
                size, sha256 = await fd.save()

            host, port = await axon.addHttpsPort(0, host='127.0.0.1')

            sha2 = s_common.ehex(sha256)
            async with axon.getLocalProxy() as proxy:

                resp = await proxy.wget(f'https://visi:secret@127.0.0.1:{port}/api/v1/axon/files/by/sha256/{sha2}',
                                        ssl=False)
                self.eq(True, resp['ok'])
                self.eq(200, resp['code'])
                self.eq(8, resp['size'])
                self.eq('OK', resp['reason'])
                self.eq('application/octet-stream', resp['headers']['Content-Type'])

                resp = await proxy.wget(f'http://visi:secret@127.0.0.1:{port}/api/v1/axon/files/by/sha256/{sha2}')
                self.false(resp['ok'])
                self.eq(-1, resp['code'])
                self.isin('Exception occurred during request: ClientOSError: [Errno 104]', resp['reason'])
                self.isinstance(resp['err'], tuple)

                async def timeout(self):
                    await asyncio.sleep(2)
                with mock.patch.object(s_httpapi.ActiveV1, 'get', timeout):
                    resp = await proxy.wget(f'https://visi:secret@127.0.0.1:{port}/api/v1/active', timeout=1,
                                            ssl=False)
                    self.eq(False, resp['ok'])
                    self.eq('TimeoutError', resp['mesg'])

        conf = {'http:proxy': 'socks5://user:pass@127.0.0.1:1'}
        async with self.getTestAxon(conf=conf) as axon:
            async with axon.getLocalProxy() as proxy:
                resp = await proxy.wget('http://vertex.link/')
                self.false(resp.get('ok'))
                self.isin('connect to proxy 127.0.0.1:1', resp.get('mesg', ''))

                resp = await proxy.wget('http://vertex.link/', proxy=None)
                self.false(resp.get('ok'))
                self.isin('connect to proxy 127.0.0.1:1', resp.get('mesg', ''))

            resp = await proxy.wget('vertex.link')
            self.false(resp.get('ok'))
            self.isin('InvalidUrlClientError: vertex.link', resp.get('mesg', ''))

            await self.asyncraises(s_exc.BadArg, proxy.wget('http://vertex.link', proxy=1.1))

    async def test_axon_wput(self):

        async with self.getTestCore() as core:

            axon = core.axon
            axon.addHttpApi('/api/v1/pushfile', HttpPushFile, {'cell': axon})

            async with await axon.upload() as fd:
                await fd.write(b'asdfasdf')
                size, sha256 = await fd.save()

            host, port = await axon.addHttpsPort(0, host='127.0.0.1')

            async with axon.getLocalProxy() as proxy:

                resp = await proxy.wput(sha256, f'https://127.0.0.1:{port}/api/v1/pushfile', method='PUT', ssl=False)
                self.eq(True, resp['ok'])
                self.eq(200, resp['code'])
                self.eq('OK', resp['reason'])

            opts = {'vars': {'sha256': s_common.ehex(sha256)}}
            q = f'return($lib.axon.wput($sha256, "https://127.0.0.1:{port}/api/v1/pushfile", ssl=(0)))'
            resp = await core.callStorm(q, opts=opts)
            self.eq(True, resp['ok'])
            self.eq(200, resp['code'])

            opts = {'vars': {'sha256': s_common.ehex(s_common.buid())}}
            resp = await core.callStorm(q, opts=opts)
            self.eq(False, resp['ok'])
            self.eq(-1, resp['code'])
            self.isin('Axon does not contain the requested file.', resp.get('mesg'))
            self.isin('Exception occurred during request: NoSuchFile', resp.get('reason'))
            self.isinstance(resp.get('err'), tuple)

            q = f'''
            $fields = ([
                {{'name':'file', 'sha256':$sha256, 'filename':'file'}},
                {{'name':'zip_password', 'value':'test'}},
                {{'name':'dict', 'value':{{'foo':'bar'}} }},
                {{'name':'bytes', 'value':$bytes}}
            ])
            $resp = $lib.inet.http.post("https://127.0.0.1:{port}/api/v1/pushfile",
                                        fields=$fields, ssl_verify=(0))
            return($resp)
            '''
            opts = {'vars': {'sha256': s_common.ehex(sha256), 'bytes': b'coolbytes'}}
            resp = await core.callStorm(q, opts=opts)
            self.true(resp['ok'])
            self.eq(200, resp['code'])

            opts = {'vars': {'sha256': s_common.ehex(s_common.buid()), 'bytes': ''}}
            resp = await core.callStorm(q, opts=opts)
            self.false(resp['ok'])
            self.isin('Axon does not contain the requested file.', resp.get('reason'))

            async with axon.getLocalProxy() as proxy:
                resp = await proxy.postfiles(fields, f'https://127.0.0.1:{port}/api/v1/pushfile', ssl=False)
                self.true(resp['ok'])
                self.eq(200, resp['code'])

        conf = {'http:proxy': 'socks5://user:pass@127.0.0.1:1'}
        async with self.getTestAxon(conf=conf) as axon:

            axon.addHttpApi('/api/v1/pushfile', HttpPushFile, {'cell': axon})

            async with await axon.upload() as fd:
                await fd.write(b'asdfasdf')
                size, sha256 = await fd.save()

            host, port = await axon.addHttpsPort(0, host='127.0.0.1')

            async with axon.getLocalProxy() as proxy:
                resp = await proxy.postfiles(fields, f'https://127.0.0.1:{port}/api/v1/pushfile', ssl=False)
                self.false(resp.get('ok'))
                self.isin('connect to proxy 127.0.0.1:1', resp.get('reason'))

                resp = await proxy.postfiles(fields, f'https://127.0.0.1:{port}/api/v1/pushfile', ssl=False, proxy=None)
                self.false(resp.get('ok'))
                self.isin('connect to proxy 127.0.0.1:1', resp.get('reason'))

            resp = await proxy.wput(sha256, 'vertex.link')
            self.false(resp.get('ok'))
            self.isin('InvalidUrlClientError: vertex.link', resp.get('mesg', ''))

            resp = await proxy.postfiles(fields, 'vertex.link')
            self.false(resp.get('ok'))
            self.isin('InvalidUrlClientError: vertex.link', resp.get('reason'))

            # Bypass the Axon proxy configuration from Storm
            url = axon.getLocalUrl()
            async with self.getTestCore(conf={'axon': url}) as core:
                q = f'''
                $resp = $lib.inet.http.post("https://127.0.0.1:{port}/api/v1/pushfile",
                                            fields=$fields, ssl_verify=(0))
                return($resp)
                '''
                resp = await core.callStorm(q, opts={'vars': {'fields': fields}})
                self.false(resp.get('ok'))
                self.isin('connect to proxy 127.0.0.1:1', resp.get('reason'))

                q = f'''
                $resp = $lib.inet.http.post("https://127.0.0.1:{port}/api/v1/pushfile",
                                            fields=$fields, ssl_verify=(0), proxy=$lib.false)
                return($resp)
                '''
                resp = await core.callStorm(q, opts={'vars': {'fields': fields}})
                self.true(resp.get('ok'))
                self.eq(resp.get('code'), 200)

    async def test_axon_tlscapath(self):

        with self.getTestDir() as dirn:
            cdir = s_common.gendir(dirn, 'certs')
            cadir = s_common.gendir(cdir, 'cas')
            tdir = s_certdir.CertDir(cdir)
            tdir.genCaCert('somelocalca')
            tdir.genHostCert('localhost', signas='somelocalca')

            localkeyfp = tdir.getHostKeyPath('localhost')
            localcertfp = tdir.getHostCertPath('localhost')
            shutil.copyfile(localkeyfp, s_common.genpath(dirn, 'sslkey.pem'))
            shutil.copyfile(localcertfp, s_common.genpath(dirn, 'sslcert.pem'))

            tlscadir = s_common.gendir(dirn, 'cadir')
            for fn in os.listdir(cadir):
                if fn.endswith('.crt'):
                    shutil.copyfile(os.path.join(cadir, fn), os.path.join(tlscadir, fn))

            conf = {'auth:passwd': 'root'}
            async with self.getTestAxon(dirn=dirn, conf=conf) as axon:
                host, port = await axon.addHttpsPort(0, host='127.0.0.1')
                url = f'https://root:root@127.0.0.1:{port}/api/v1/active'
                resp = await axon.wget(url)
                self.false(resp.get('ok'))
                self.isin('unable to get local issuer certificate', resp.get('mesg'))

                retn = await axon.put(abuf)
                self.eq(retn, asdfretn)
                axon.addHttpApi('/api/v1/pushfile', HttpPushFile, {'cell': axon})
                url = f'https://root:root@127.0.0.1:{port}/api/v1/pushfile'
                resp = await axon.wput(asdfhash, url)
                self.false(resp.get('ok'))
                self.isin('unable to get local issuer certificate', resp.get('mesg'))

                resp = await axon.postfiles(fields, url)
                self.false(resp.get('ok'))
                self.isin('unable to get local issuer certificate', resp.get('reason'))

            conf = {'auth:passwd': 'root', 'tls:ca:dir': tlscadir}
            async with self.getTestAxon(dirn=dirn, conf=conf) as axon:
                host, port = await axon.addHttpsPort(0, host='127.0.0.1')
                url = f'https://root:root@localhost:{port}/api/v1/active'
                resp = await axon.wget(url)
                self.true(resp.get('ok'))

                retn = await axon.put(abuf)
                self.eq(retn, asdfretn)
                axon.addHttpApi('/api/v1/pushfile', HttpPushFile, {'cell': axon})
                url = f'https://root:root@localhost:{port}/api/v1/pushfile'
                resp = await axon.wput(asdfhash, url)
                self.true(resp.get('ok'))

                resp = await axon.postfiles(fields, url)
                self.true(resp.get('ok'))

    async def test_axon_blob_v00_v01(self):

        async with self.getRegrAxon('blobv00-blobv01') as axon:

            sha256 = hashlib.sha256(b'asdfqwerzxcv').digest()
            offsitems = list(axon.blobslab.scanByFull(db=axon.offsets))
            self.eq(offsitems, (
                (sha256 + (4).to_bytes(8, 'big'), (0).to_bytes(8, 'big')),
                (sha256 + (8).to_bytes(8, 'big'), (1).to_bytes(8, 'big')),
                (sha256 + (12).to_bytes(8, 'big'), (2).to_bytes(8, 'big')),
            ))

            bytslist = [b async for b in axon.get(sha256, 0, size=4)]
            self.eq(b'asdf', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 2, size=4)]
            self.eq(b'dfqw', b''.join(bytslist))

            bytslist = [b async for b in axon.get(sha256, 2, size=6)]
            self.eq(b'dfqwer', b''.join(bytslist))

            metrics = await axon.metrics()
            self.eq(metrics, {'size:bytes': 12, 'file:count': 1})

    async def test_axon_mirror(self):

        async with self.getTestAha() as aha:

            axon00dirn = s_common.gendir(aha.dirn, 'tmp', 'axon00')
            axon01dirn = s_common.gendir(aha.dirn, 'tmp', 'axon01')

            waiter = aha.waiter(2, 'aha:svcadd')

            axon00url = await aha.addAhaSvcProv('00.axon', {'https:port': None})
            axon01url = await aha.addAhaSvcProv('01.axon', {'https:port': None, 'mirror': '00.axon'})

            axon00 = await aha.enter_context(await s_axon.Axon.anit(axon00dirn, conf={'aha:provision': axon00url}))
            (size, sha256) = await axon00.put(b'visi')
            self.false(await axon00._axonFileAdd(sha256, size, {}))

            self.len(2, await waiter.wait(timeout=6))

            axon01 = await aha.enter_context(await s_axon.Axon.anit(axon01dirn, conf={'aha:provision': axon01url}))
            self.eq(4, await axon01.size(sha256))

            (size, sha256) = await axon01.put(b'vertex')
            self.eq(await axon00.size(sha256), await axon01.size(sha256))
