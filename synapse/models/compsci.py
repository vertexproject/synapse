
def getDataModel():
    return {
        'prefix':'csci',
        'version':201611301306,

        'types':(
            ('csci:host',{'subof':'guid'}),
            ('csci:hostfile',{'subof':'guid'}),
            ('csci:hostfile',{'subof':'guid'}),
        ),

        'forms':(
            ('csci:hostfile',{'ptype':'csci:hostfile'},[
            ]),
        ),
    }
