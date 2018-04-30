
from synapse.tests.common import SynTest

class CnGovTest(SynTest):

    def test_models_cngov_mucd(self):
        with self.getTestCore() as core:
            formname = 'gov:cn:mucd'
            # guid = 32 * '0'
            #flag_valu = 64 * 'f'

            #input_props = {'flag': flag_valu, 'founded': 456, 'iso2': 'VI', 'iso3': 'VIS', 'isonum': 31337,
            #    'name': 'Republic of Visi', 'tld': 'visi', 'pop': 123}
            #expected_props = {'flag': flag_valu, 'founded': 456, 'iso2': 'vi', 'iso3': 'vis', 'isonum': 31337,
            #    'name': 'republic of visi', 'tld': 'visi', 'pop': 123}
            # expected_ndef = (formname, guid)

            with core.xact(write=True) as xact:

                node = xact.addNode(formname, 61786)
                print('node:', node)
                # self.eq(node.buid, func.args[0].buid)

                # node = core.formTufoByProp('gov:cn:mucd', 61786)

                self.nn(node)
                self.nn(xact.getNodesBy('ou:org:name', 'chinese pla unit 61786'))
                for n in xact.getNodesBy('ou:org:name', 'chinese pla unit 61786'):
                    print(n)
