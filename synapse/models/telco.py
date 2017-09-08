import logging

import synapse.compat as s_compat
import synapse.lookup.phonenum as s_l_phone
from synapse.lib.types import DataType
from synapse.lib.module import CoreModule, modelrev

logger = logging.getLogger(__name__)

intls = (
    ('us', '1', '011', 10),
)

def genTelLocCast(iso2, cc, idd, size):
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

            if idd not in ('00', '011') and valu.startswith(idd):
                return int(valu[ilen:])

            if valu.startswith(cc):
                return int(valu)

            if len(valu) == size:
                return int(cc + valu)

            return int(valu)

        except Exception as e:
            logger.exception('cast tel:loc:%s' % iso2)
            return None

    return castTelLocal

def digits(text):
    return ''.join([c for c in text if c.isdigit()])

class PhoneType(DataType):
    def norm(self, valu, oldval=None):

        if s_compat.isstr(valu):
            valu = int(digits(valu))

        subs = {}
        try:
            valu = int(valu)
            info = s_l_phone.getPhoneInfo(valu)

            cc = info.get('cc')
            if cc is not None:
                subs['cc'] = cc

            # TODO prefix based validation?
            return valu, subs

        except TypeError as e:
            self._raiseBadValu(valu)

    def repr(self, valu):
        text = str(valu)

        # FIXME implement more geo aware reprs
        if text[0] == '1':
            area = text[1:4]
            pref = text[4:7]
            numb = text[7:11]
            return '+1 (%s) %s-%s' % (area, pref, numb)

        return '+' + text

class TelMod(CoreModule):

    def initCoreModule(self):
        # TODO
        # event handlers which cache and resolve prefixes to tag phone numbers
        for iso2, cc, idd, size in intls:
            self.core.addTypeCast('tel:loc:%s' % iso2, genTelLocCast(iso2, cc, idd, size))

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                ('tel:phone', {'ctor': 'synapse.models.telco.PhoneType'}),
            ),
            'forms': (
                ('tel:phone', {'ptype': 'tel:phone'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??'}),
                ]),
                ('tel:prefix', {'ptype': 'tel:phone'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??'}),
                    ('tag', {'ptype': 'syn:tag'}),
                ]),
            ),
        }
        name = 'tel'
        return ((name, modl), )
