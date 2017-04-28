from synapse.common import guid

def getDataModel():
    return {
        'prefix':'ou',
        'version':201611301215,

        'types':(
            ('ou:org',{'subof':'guid','alias':'ou:org:alias','doc':'A GUID for a human organization such as a company or military unit'}),
            ('ou:user',{'subof':'sepr','sep':'/','fields':'org,ou:org|user,inet:user','doc':'A user name within an organization'}),
            ('ou:alias',{'subof':'str:lwr','regex':'^[0-9a-z]+$','doc':'An alias for the org GUID','ex':'vertexproj'}),

            ('ou:name',{'subof':'str:lwr'}),
            ('ou:sic',{'subof':'int','doc':'Standard Industrial Classification Code'}),
            ('ou:naics',{'subof':'int','doc':'North American Industry Classification System'})
        ),

        'forms':(

            ('ou:org',{'ptype':'ou:org'},[
                ('cc',{'ptype':'pol:iso2'}),
                ('name',{'ptype':'ou:name'}),
                ('name:en',{'ptype':'ou:name'}),
                ('alias',{'ptype':'ou:alias'}),
                ('phone',{'ptype':'tel:phone','doc':'The primary phone number for the organization'}),
                ('sic',{'ptype':'ou:sic'}),
                ('naics',{'ptype':'ou:naics'}),
                ('us:cage',{'ptype':'gov:us:cage'}),
                ('url',{'ptype':'inet:url'})
            ]),

            ('ou:user',{},[
                ('org',{'ptype':'ou:org'}),
                ('user',{'ptype':'inet:user'}),
            ]),

            ('ou:member',{'ptype':'sepr','sep':'/','fields':'org,ou:org|person,ou:person'},[
                ('start',{'ptype':'time:min'}),
                ('title',{'ptype':'str:lwr','defval':'??'}),
            ]),

            ('ou:owns',{'ptype':'sepr','sep':'/','fields':'owner,ou:org|owned,ou:org'},[
            ]),
        ),

    }

def addCoreOns(core):

    def seedOrgAlias(prop,valu,**props):
        node = core.getTufoByProp('ou:org:alias',valu)
        if node == None:
            node = core.formTufoByProp('ou:org',guid(),alias=valu,**props)
        return node

    def seedOrgName(prop,valu,**props):
        node = core.getTufoByProp('ou:org:name',valu)
        if node == None:
            node = core.formTufoByProp('ou:org',guid(),name=valu,**props)
        return node

    core.addSeedCtor('ou:org:name', seedOrgName)
    core.addSeedCtor('ou:org:alias', seedOrgAlias)
