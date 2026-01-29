import bz2
import gzip
import zlib
import base64

import synapse.exc as s_exc

import synapse.tests.utils as s_test

class StormlibCompressionTest(s_test.SynTest):

    async def test_storm_lib_bytes_bzip2(self):
        async with self.getTestCore() as core:
            text = 'ohhai'
            tenc = base64.urlsafe_b64encode((bz2.compress(text.encode()))).decode()

            await core.nodes(f'[ tel:mob:telem=(node1,) :data="{tenc}" ]')
            await core.nodes(f'[ tel:mob:telem=(node2,) :data="{text}" ]')

            q = 'tel:mob:telem=(node1,) return($lib.compression.bzip2.un($lib.base64.decode(:data)).decode())'
            self.eq(text, await core.callStorm(q))

            q = 'tel:mob:telem=(node2,) return($lib.base64.encode($lib.compression.bzip2.en((:data).encode())))'
            self.eq(tenc, await core.callStorm(q))

            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('$lib.compression.bzip2.en(foo)'))
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('$lib.compression.bzip2.un(foo)'))

    async def test_storm_lib_bytes_gzip(self):
        async with self.getTestCore() as core:
            text = 'ohhai'
            tenc = base64.urlsafe_b64encode((gzip.compress(text.encode()))).decode()

            await core.nodes(f'[ tel:mob:telem=(node1,) :data="{tenc}" ]')
            await core.nodes(f'[ tel:mob:telem=(node2,) :data="{text}" ]')

            q = 'tel:mob:telem=(node1,) return($lib.compression.gzip.un($lib.base64.decode(:data)).decode())'
            self.eq(text, await core.callStorm(q))

            q = 'tel:mob:telem=(node2,) return($lib.compression.gzip.en((:data).encode()))'
            self.eq(text.encode(), gzip.decompress(await core.callStorm(q)))

            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('$lib.compression.gzip.en(foo)'))
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('$lib.compression.gzip.un(foo)'))

    async def test_storm_lib_bytes_zlib(self):
        async with self.getTestCore() as core:
            text = 'ohhai'
            tenc = base64.urlsafe_b64encode((zlib.compress(text.encode()))).decode()

            await core.nodes(f'[ tel:mob:telem=(node1,) :data="{tenc}" ]')
            await core.nodes(f'[ tel:mob:telem=(node2,) :data="{text}" ]')

            q = 'tel:mob:telem=(node1,) return($lib.compression.zlib.un($lib.base64.decode(:data)).decode())'
            self.eq(text, await core.callStorm(q))

            q = 'tel:mob:telem=(node2,) return($lib.base64.encode($lib.compression.zlib.en((:data).encode())))'
            self.eq(tenc, await core.callStorm(q))

            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('$lib.compression.zlib.en(foo)'))
            await self.asyncraises(s_exc.StormRuntimeError, core.nodes('$lib.compression.zlib.un(foo)'))
