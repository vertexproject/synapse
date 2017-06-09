from synapse.tests.common import *

import synapse.lookup.iso3166 as s_l_country


class CountryLookTest(SynTest):

    def test_lookup_countries(self):
        self.eq(s_l_country.country2iso.get('united states of america'), 'us')
        self.eq(s_l_country.country2iso.get('mexico'), 'mx')
        self.eq(s_l_country.country2iso.get('vertexLandia'), None)
