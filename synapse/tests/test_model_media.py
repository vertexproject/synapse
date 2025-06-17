import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class MediaModelTest(s_t_utils.SynTest):

    async def test_hashtag(self):

        async with self.getTestCore() as core:

            self.len(1, await core.nodes('[ media:hashtag="#🫠" ]'))
            self.len(1, await core.nodes('[ media:hashtag="#🫠🫠" ]'))
            self.len(1, await core.nodes('[ media:hashtag="#·bar"]'))
            self.len(1, await core.nodes('[ media:hashtag="#foo·"]'))
            self.len(1, await core.nodes('[ media:hashtag="#foo〜"]'))
            self.len(1, await core.nodes('[ media:hashtag="#hehe" ]'))
            self.len(1, await core.nodes('[ media:hashtag="#foo·bar"]'))  # note the interpunct
            self.len(1, await core.nodes('[ media:hashtag="#foo〜bar"]'))  # note the wave dash
            self.len(1, await core.nodes('[ media:hashtag="#fo·o·······b·ar"]'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ media:hashtag="foo" ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ media:hashtag="#foo#bar" ]')

            # All unicode whitespace from:
            # https://www.compart.com/en/unicode/category/Zl
            # https://www.compart.com/en/unicode/category/Zp
            # https://www.compart.com/en/unicode/category/Zs
            whitespace = [
                '\u0020', '\u00a0', '\u1680', '\u2000', '\u2001', '\u2002', '\u2003', '\u2004',
                '\u2005', '\u2006', '\u2007', '\u2008', '\u2009', '\u200a', '\u202f', '\u205f',
                '\u3000', '\u2028', '\u2029',
            ]
            for char in whitespace:
                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ media:hashtag="#foo{char}bar" ]')

                with self.raises(s_exc.BadTypeValu):
                    await core.callStorm(f'[ media:hashtag="#{char}bar" ]')

                # These are allowed because strip=True
                await core.callStorm(f'[ media:hashtag="#foo{char}" ]')
                await core.callStorm(f'[ media:hashtag=" #foo{char}" ]')
