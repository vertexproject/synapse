import synapse.compat as s_compat
from synapse.lib.types import DataType

def getDataModel():
    return {
        'prefix':'tel',
        'version':201611301342,
        'types':(
            ('tel:phone',{'ctor':'synapse.models.telco.PhoneType'}),
        ),
        'forms':(
            ('tel:phone',{'ptype':'tel:phone'},[
                ('cc',{'ptype':'pol:iso2','defval':'??'}),
            ]),
            ('tel:prefix',{'ptype':'tel:phone'},[
                ('cc',{'ptype':'pol:iso2','defval':'??'}),
                ('tag',{'ptype':'syn:tag'}),
            ]),
        ),
    }

# TODO
# event handlers which cache and resolve prefixes to tag phone numbers

#def addCoreOns(core):

    #prefs = {}
    #for tufo in core.getTufosByProp('tel:prefix'):

    #def onTufoAddPrefix(mesg):
        #tufo = mesg[1].get('tufo')
        #pref = tufo[1].get('tel:pref')

    #def onTufoDelPrefix(mesg):
        #tufo = mesg[1].get('tufo')

    #def onTufoFormPhone(mesg):

class PhoneType(DataType):

    def parse(self, text, oldval=None):
        if not s_compat.isstr(text):
            self._raiseBadValu(text)
        return (''.join([ c for c in text if c.isdigit() ])),{}

    def norm(self, valu, oldval=None):
        if not s_compat.isstr(valu):
            self._raiseBadValu(valu)
        return ''.join([ c for c in valu if c.isdigit() ]),{}

    def repr(self, valu):
        return '+%s' % (valu,)
