from synapse.lib.types import DataType

def getDataModel():
    return {
        'prefix':'ps',
        'version':201703271415,

        'types':(
            ('ps:tokn',{'subof':'str:lwr','doc':'A single name element (potentially given or sur)','ex':'mike'}),
            ('ps:name',{'ctor':'synapse.models.person.Name','ex':'smith,bob', 'doc':'A last,first person full name'}),
            ('ps:person',{'subof':'guid','doc':'A GUID for a person or suspected person'}),


            ('ps:hasuser',{'subof':'sepr','sep':'/','fields':'person,ps:person|user,inet:user'}),
            ('ps:hasalias',{'subof':'sepr','sep':'/','fields':'person,ps:person|alias,ps:name'}),
            ('ps:hasphone',{'subof':'sepr','sep':'/','fields':'person,ps:person|phone,tel:phone'}),
            ('ps:hasemail',{'subof':'sepr','sep':'/','fields':'person,ps:person|email,inet:email'}),
            ('ps:hasnetuser',{'subof':'sepr','sep':'/','fields':'person,ps:person|netuser,inet:netuser'}),

            #('ps:hashost',{'subof','sepr','sep':'/','fields':'person,ps:person|host,it:host'}),
            # FIXME add wireless elemements like NMEI and IMEI once modeled
        ),

        'forms':(
            ('ps:tokn',{'ptype':'ps:tokn'},[]),
            ('ps:name',{'ptype':'ps:name'},[
                ('sur',{'ptype':'ps:tokn','doc':'The "surname" part of ps:name','ex':'stark'}),
                ('given',{'ptype':'ps:tokn','doc':'The "given name" part of ps:name','ex':'tony'}),
                ('middle',{'ptype':'ps:tokn','doc':'The "middle name" part of ps:name','ex':'alex'}),
            ]),
            ('ps:person',{'ptype':'ps:person'},[
                ('dob',{'ptype':'time','doc':'The Date of Birth (DOB) if known'}),
                ('name',{'ptype':'ps:name'}),
                ('name:sur',{'ptype':'ps:tokn'}),
                ('name:given',{'ptype':'ps:tokn'}),
            ]),
            ('ps:hasuser',{'ptype':'ps:hasuser'},[
                ('user',{'ptype':'inet:user'}),
                ('person',{'ptype':'ps:person'}),
            ]),
            ('ps:hasalias',{'ptype':'ps:hasalias'},[
                ('alias',{'ptype':'ps:name'}),
                ('person',{'ptype':'ps:person'}),
            ]),
            ('ps:hasphone',{'ptype':'ps:hasphone'},[
                ('phone',{'ptype':'tel:phone'}),
                ('person',{'ptype':'ps:person'}),
            ]),
            ('ps:hasemail',{'ptype':'ps:hasemail'},[
                ('email',{'ptype':'inet:email'}),
                ('person',{'ptype':'ps:person'}),
            ]),
            ('ps:hasnetuser',{'ptype':'ps:hasnetuser'},[
                ('netuser',{'ptype':'inet:netuser'}),
                ('person',{'ptype':'ps:person'}),
            ]),
        ),
    }

# FIXME identify/handle possibly as seeds
# tony stark
# tony logan stark
# stark,tony logan
# stark,tony l.

class Name(DataType):

    subprops = (
        ('sur', {'ptype':'ps:tokn'}),
        ('given', {'ptype':'ps:tokn'}),
        ('middle', {'ptype':'ps:tokn'}),
        ('parts', {'ptype':'int','doc':'Number of ps:tokn elements in ps:name'}),
    )

    def norm(self, valu, oldval=None):
        subs = {}

        valu = valu.lower().strip()
        if not valu:
            self._raiseBadValu(valu)

        parts = [ v.strip().strip('.').lower() for v in valu.split(',') ]
        if len(parts) >= 2:
            subs['sur'] = parts[0]
            subs['given'] = parts[1]
            if len(parts) >= 3:
                subs['middle'] = parts[2]

        subs['parts'] = len(parts)
        valu = ','.join(parts)
        return valu,subs
