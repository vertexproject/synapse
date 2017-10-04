from synapse.common import guid
from synapse.lib.module import CoreModule, modelrev

class GovCnMod(CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('gov:cn:icp', {'subof': 'int', 'doc': 'A Chinese Internet Content Provider ID'}),
                ('gov:cn:mucd', {'subof': 'int', 'doc': 'A Chinese PLA MUCD'}),
                ('gov:cn:orgicp', {'subof': 'sepr', 'sep': '/', 'fields': 'org,ou:org|icp,gov:cn:icp'}),
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

        name = 'Chinese PLA Unit %d' % (mucd,)

        iden = guid(('gov:cn:mucd', mucd))
        self.form('ou:org', iden, name=name, alias='pla%d' % mucd)
