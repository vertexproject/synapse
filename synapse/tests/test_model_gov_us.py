import synapse.tests.utils as s_t_utils

class UsGovTest(s_t_utils.SynTest):

    async def test_models_usgov_cage(self):

        async with self.getTestCore() as core:
            input_props = {
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
            expected_props = {
                'street': '123 main st',
                'city': 'smallville',
                'state': 'kansas',
                'zip': 12345,
                'cc': 'us',
                'country': 'united states of america',
                'phone0': '17035551212',
                'phone1': '17035551213',
                'name0': 'kent labs',
            }
            formname = 'gov:us:cage'
            valu = '7qe71'
            expected_ndef = (formname, valu)
            async with await core.snap() as snap:
                n0 = await snap.addNode(formname, valu.upper(), input_props)

            self.eq(n0.ndef, expected_ndef)
            for prop, valu in expected_props.items():
                self.eq(n0.get(prop), valu)
