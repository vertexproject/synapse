import synapse.tests.utils as s_test

count_prop_00 = '''
 Count        | Layer Iden                       | Layer Name
==============|==================================|============
 16           | 5cc56afbb22fad9b96c51110812af8f7 |
 16           | 2371390b1fd0162ba6820f85a863e7b2 | default
Total: 32
'''

count_prop_01 = '''
 Count        | Layer Iden                       | Layer Name
==============|==================================|============
 16           | 9782c920718d3059b8806fddaf917bd8 |
 0            | 511122a9b2d576c5be2cdfcaef541bb9 | default
Total: 16
'''

class StormIndexTest(s_test.SynTest):

    async def test_lib_stormlib_index(self):

        async with self.getTestCore() as core:
            viewiden = await core.callStorm('return($lib.view.get().fork().iden)')
            viewopts = {'view': viewiden}
            await core.nodes('[ inet:ipv4=1.2.3.0/28 :asn=19 ]')
            await core.nodes('[ inet:ipv4=1.2.4.0/28 :asn=42 ]', opts=viewopts)

            msgs = await core.stormlist('index.count.prop inet:ipv4', opts=viewopts)
            self.stormIsInPrint(count_prop_00, msgs, deguid=True, whitespace=False)

            msgs = await core.stormlist('index.count.prop inet:ipv4:asn', opts=viewopts)
            self.stormIsInPrint(count_prop_00, msgs, deguid=True, whitespace=False)

            msgs = await core.stormlist('index.count.prop inet:ipv4:asn --value 42', opts=viewopts)
            self.stormIsInPrint(count_prop_01, msgs, deguid=True, whitespace=False)

            msgs = await core.stormlist('index.count.prop inet:ipv4:newp', opts=viewopts)
            self.stormIsInErr('No property named inet:ipv4:newp', msgs)
