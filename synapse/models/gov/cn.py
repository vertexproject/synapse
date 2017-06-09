from synapse.common import guid

def getDataModel():
    return {
        'prefix':'gov:cn',
        'version':201703301924,

        'types':(
            ('gov:cn:icp',     {'subof':'int','doc':'A Chinese Internet Content Provider ID'}),
            ('gov:cn:mucd',     {'subof':'int','doc':'A Chinese PLA MUCD'}),
            ('gov:cn:orgicp',   {'subof':'sepr','sep':'/','fields':'org,ou:org|icp,gov:cn:icp'}),
        ),

        'forms':(
            ('gov:cn:icp',{},()),
            ('gov:cn:mucd',{},()),
        ),
    }

def addCoreOns(core):

    def onTufoAddMucd(mesg):
        node = mesg[1].get('tufo')
        mucd = node[1].get('gov:cn:mucd')
        name = 'Chinese PLA Unit %d' % (mucd,)
        iden = guid( ('gov:cn:mucd',mucd) )
        core.formTufoByProp('ou:org', iden, name=name, alias='pla%d' % mucd)

    core.on('tufo:add:gov:cn:mucd', onTufoAddMucd)
