import synapse.common as s_common

import synapse.tests.common as s_test

class BaseTest(s_test.SynTest):

    def test_model_base_source(self):

        with self.getTestCore() as core:

            with core.snap() as snap:

                props = {
                    'name': 'FOO BAR',
                    'type': 'osint',
                }

                sorc = snap.addNode('source', '*', props=props)

                self.eq(sorc.get('type'), 'osint')
                self.eq(sorc.get('name'), 'foo bar')

                valu = (sorc.ndef[1], ('inet:fqdn', 'woot.com'))

                seen = snap.addNode('seen', valu)

                self.eq(seen.get('source'), sorc.ndef[1])
                self.eq(seen.get('node'), ('inet:fqdn', 'woot.com'))
                #self.eq(seen.get('node:form'), 'inet:fqdn')

    def test_model_base_record(self):

        self.skip('BASE MODEL RECORD QUESTION')

        with self.getRamCore() as core:

            props = {
                'name': 'foo bar',
                'type': 'osint',
            }

            sorc = core.formTufoByProp('record', '*', **props)

            self.eq(sorc[1].get('record:name'), 'foo bar')
            self.eq(sorc[1].get('record:type'), 'osint')

            iden = sorc[1].get('record')

            valu = (iden, ('inet:fqdn', 'woot.com'))
            props = {
                'time:min': '2016',
                'time:max': '2017',
            }

            ndef = s_common.guid(('inet:fqdn', 'woot.com'))
            rref = core.formTufoByProp('recref', valu, **props)

            self.eq(rref[1].get('recref:record'), iden)
            self.eq(rref[1].get('recref:node'), ndef)
            self.eq(rref[1].get('recref:node:form'), 'inet:fqdn')
