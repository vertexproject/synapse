import synapse.common as s_common

from synapse.tests.common import *

class BaseTest(SynTest):

    def test_model_base_source(self):

        with self.getRamCore() as core:

            props = {
                'name': 'foo bar',
                'type': 'osint',
            }

            sorc = core.formTufoByProp('source', '*', **props)

            self.eq(sorc[1].get('source:name'), 'foo bar')
            self.eq(sorc[1].get('source:type'), 'osint')

            iden = sorc[1].get('source')

            valu = (iden, ('inet:fqdn', 'woot.com'))
            props = {
                'time:min': '2016',
                'time:max': '2017',
            }

            ndef = s_common.guid(('inet:fqdn', 'woot.com'))
            seen = core.formTufoByProp('seen', valu, **props)

            self.eq(seen[1].get('seen:source'), iden)
            self.eq(seen[1].get('seen:time:min'), 1451606400000)
            self.eq(seen[1].get('seen:time:max'), 1483228800000)
            self.eq(seen[1].get('seen:node'), ndef)
            self.eq(seen[1].get('seen:node:form'), 'inet:fqdn')

    def test_model_base_record(self):

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
