from synapse.tests.common import SynTest

class UsGovTest(SynTest):

    def test_models_usgov_cage(self):
        with self.getTestCore() as core:
            input_props = {
                'street': '123 Main St',
                'city': 'Smallville',
                'state': 'Kansas',
                'zip': 12345,
                'cc': 'US',
                'country': 'United States of America',
            }
            expected_props = {
                'street': '123 main st',
                'city': 'smallville',
                'state': 'kansas',
                'zip': 12345,
                'cc': 'us',
                'country': 'united states of america',
            }
            formname = 'gov:us:cage'
            valu = '7qe71'
            expected_ndef = (formname, valu)
            with core.xact(write=True) as xact:
                # FIXME  - 010 need phones
                # n0 = xact.addNode('gov:us:cage', '7QE71', {'phone0': 17035551212})
                n0 = xact.addNode(formname, valu.upper(), input_props)

            self.eq(n0.ndef, expected_ndef)
            self.eq(n0.props, expected_props)
