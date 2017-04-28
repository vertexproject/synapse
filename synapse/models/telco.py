import logging

import synapse.compat as s_compat
from synapse.lib.types import DataType

import synapse.lookup.phonenum as s_l_phone

logger = logging.getLogger(__name__)

def getDataModel():
    return {
        'prefix':'tel',
        'version':201703302055,
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

def genTelLocCast(iso2,cc,idd,size):
    '''
    Generate a generic phone canonicalizer for numbers which
    may reside within an arbitrary country's local exchange.
    '''
    clen = len(cc)
    ilen = len(idd)

    def castTelLocal(valu):
        try:

            rawp = str(valu).strip()
            valu = digits(rawp)
            if not valu:
                return None

            if rawp[0] == '+':
                return int(valu)

            # since 00 and 011 are so common
            # (and generally incompatible with local)
            if valu.startswith('00'):
                return int(valu[2:])

            if valu.startswith('011'):
                return int(valu[3:])

            if idd not in ('00','011') and valu.startswith(idd):
                return int(valu[ilen:])

            if valu.startswith(cc):
                return int(valu)

            if len(valu) == size:
                return int( cc + valu )

            return int(valu)

        except Exception as e:
            logger.exception('cast tel:loc:%s' % iso2)
            return None

    return castTelLocal

intls = (
    ('us','1','011',10),
)

def addCoreOns(core):
    for iso2,cc,idd,size in intls:
        core.addTypeCast('tel:loc:%s' % iso2, genTelLocCast(iso2,cc,idd,size))

    #prefs = {}
    #for tufo in core.getTufosByProp('tel:prefix'):

    #def onTufoAddPrefix(mesg):
        #tufo = mesg[1].get('tufo')
        #pref = tufo[1].get('tel:pref')

    #def onTufoDelPrefix(mesg):
        #tufo = mesg[1].get('tufo')

    #def onTufoFormPhone(mesg):

def digits(text):
    return ''.join([ c for c in text if c.isdigit() ])

class PhoneType(DataType):

    def norm(self, valu, oldval=None):

        if s_compat.isstr(valu):
            valu = int(digits(valu))

        subs = {}
        try:
            valu = int(valu)
            info = s_l_phone.getPhoneInfo(valu)

            cc = info.get('cc')
            if cc != None:
                subs['cc'] = cc

            # TODO prefix based validation?
            return valu,subs

        except TypeError as e:
            self._raiseBadValu(valu)

    def repr(self, valu):
        text = str(valu)

        # FIXME implement more geo aware reprs
        if text[0] == '1':
            area = text[1:4]
            pref = text[4:7]
            numb = text[7:11]
            return '+1 (%s) %s-%s' % (area,pref,numb)

        return '+' + text

