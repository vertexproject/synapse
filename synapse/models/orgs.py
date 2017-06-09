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
            ('ou:naics',{'subof':'int','doc':'North American Industry Classification System'}),

            ('ou:suborg', {'subof':'comp','fields':'org,ou:org|sub,ou:org','doc':'An org which owns a sub org'}),

            ('ou:hasfile',{'subof':'comp','fields':'org,ou:org|file,file:bytes'}),
            ('ou:hasfqdn',{'subof':'comp','fields':'org,ou:org|fqdn,inet:fqdn'}),
            ('ou:hasipv4',{'subof':'comp','fields':'org,ou:org|ipv4,inet:ipv4'}),
            ('ou:hashost',{'subof':'comp','fields':'org,ou:org|host,it:host'}),
            ('ou:hasemail',{'subof':'comp','fields':'org,ou:org|email,inet:email'}),
            ('ou:hasphone',{'subof':'comp','fields':'org,ou:org|phone,tel:phone'}),
            ('ou:hasnetuser',{'subof':'comp','fields':'org,ou:org|netuser,inet:netuser'}),

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
                ('url',{'ptype':'inet:url'}),
            ]),

            ('ou:suborg',{},[
                ('org',{'ptype':'ou:org','doc':'The org which owns sub'}),
                ('sub',{'ptype':'ou:org','doc':'The the sub which is owned by org'}),
                ('perc',{'ptype':'int','doc':'The optional percentage of sub which is owned by org'}),
                ('current',{'ptype':'bool','defval':1,'doc':'Is the suborg relationship still current'}),
                ('seen:min',{'ptype':'time:min','doc':'The optional time the suborg relationship began'}),
                ('seen:max',{'ptype':'time:max','doc':'The optional time the suborg relationship ended'}),
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

            ('ou:hasfile',{},[
                ('org',     {'ptype':'ou:org','ro':1}),
                ('file',    {'ptype':'file:bytes','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('ou:hasfqdn',{},[
                ('org',     {'ptype':'ou:org','ro':1}),
                ('fqdn',    {'ptype':'inet:fqdn','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('ou:hasipv4',{},[
                ('org',     {'ptype':'ou:org','ro':1}),
                ('ipv4',    {'ptype':'inet:ipv4','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('ou:hashost',{},[
                ('org',     {'ptype':'ou:org','ro':1}),
                ('host',    {'ptype':'it:host','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('ou:hasemail',{},[
                ('org',     {'ptype':'ou:org','ro':1}),
                ('email',   {'ptype':'inet:email','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('ou:hasphone',{},[
                ('org',     {'ptype':'ou:org','ro':1}),
                ('phone',   {'ptype':'tel:phone','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
            ]),
            ('ou:hasnetuser',{},[
                ('org',     {'ptype':'ou:org','ro':1}),
                ('netuser', {'ptype':'inet:netuser','ro':1}),
                ('seen:min',{'ptype':'time:min'}),
                ('seen:max',{'ptype':'time:max'}),
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
