from synapse.common import guid
import synapse.lib.module as s_module

class GovCnModule(s_module.CoreModule):

    def getModelDefs(self):
        modl = {
            'types': (
                ('gov:cn:icp',
                    ('int', {}),
                    {'doc': 'A Chinese Internet Content Provider ID'},
                 ),
                ('gov:cn:mucd',
                    ('int', {}),
                    {'doc': 'A Chinese PLA MUCD'},
                 ),
              # FIXME 010 - needs orgs
              #  ('gov:cn:orgicp',
              #      ('comp', {'fields': (('org', 'ou:org'), ('icp', 'gov:cn:icp'))}),
              #      {},
              #   ),
            ),
            'forms': (
                ('gov:cn:icp', {}, ()),
                ('gov:cn:mucd', {}, ()),
            ),
        }
        name = 'gov:cn'
        return ((name, modl), )

    def initCoreModule(self):
        self.onNodeAdd(self.onAddMucd, form='gov:cn:mucd')

    def onAddMucd(self, node):
        mucd = node[1].get('gov:cn:mucd')

        name = f'Chinese PLA Unit {mucd}'

        iden = guid(('gov:cn:mucd', mucd))
        self.form('ou:org', iden, name=name, alias=f'pla{mucd}')
