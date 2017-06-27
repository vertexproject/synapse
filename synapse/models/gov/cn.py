from synapse.common import guid
from synapse.eventbus import on

from synapse.eventbus import on, onfini
from synapse.lib.module import CoreModule, modelrev

class GovCnMod(CoreModule):

    @modelrev('gov:cn',201703301924)
    def _revCnGov0(self):
        self.core.addDataModel('gov:cn',{

            'types':(
                ('gov:cn:icp',     {'subof':'int','doc':'A Chinese Internet Content Provider ID'}),
                ('gov:cn:mucd',     {'subof':'int','doc':'A Chinese PLA MUCD'}),
                ('gov:cn:orgicp',   {'subof':'sepr','sep':'/','fields':'org,ou:org|icp,gov:cn:icp'}),
            ),

            'forms':(
                ('gov:cn:icp',{},()),
                ('gov:cn:mucd',{},()),
            ),

        })

    @on('node:add', form='gov:cn:mucd')
    def _onFormMucd(self, mesg):

        mucd = mesg[1].get('valu')
        name = 'Chinese PLA Unit %d' % (mucd,)

        iden = guid( ('gov:cn:mucd',mucd) )
        self.form('ou:org', iden, name=name, alias='pla%d' % mucd)
