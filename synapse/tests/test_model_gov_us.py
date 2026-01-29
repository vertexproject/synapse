import synapse.tests.utils as s_t_utils

class UsGovTest(s_t_utils.SynTest):

    async def test_models_usgov_cage(self):

        async with self.getTestCore() as core:
            valu = '7qe71'
            props = {
                'street': '123 Main St',
                'city': 'Smallville',
                'state': 'Kansas',
                'zip': 12345,
                'cc': 'US',
                'country': 'United States of America',
                'phone0': '17035551212',
                'phone1': 17035551213,
                'name0': 'Kent Labs',
            }
            q = '''[(gov:us:cage=$valu
                 :street=$p.street :city=$p.city :state=$p.state :zip=$p.zip
                 :cc=$p.cc :country=$p.country
                 :phone0=$p.phone0 :phone1=$p.phone1 :name0=$p.name0
            )]'''
            opts = {'vars': {'valu': valu, 'p': props}}
            nodes = await core.nodes(q, opts=opts)
            self.len(1, nodes)
            node = nodes[0]

            self.eq(node.ndef, ('gov:us:cage', '7qe71'))
            self.eq(node.get('street'), '123 main st')
            self.eq(node.get('city'), 'smallville')
            self.eq(node.get('state'), 'kansas')
            self.eq(node.get('zip'), 12345)
            self.eq(node.get('cc'), 'us')
            self.eq(node.get('country'), 'united states of america')
            self.eq(node.get('phone0'), '17035551212')
            self.eq(node.get('phone1'), '17035551213')
            self.eq(node.get('name0'), 'kent labs')
