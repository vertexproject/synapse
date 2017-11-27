import logging

import synapse.common as s_common

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

        if isinstance(valu, str):
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

def imeicsum(text):
    '''
    Calculate the imei check byte.
    '''
    digs = []
    for i in range(14):

        v = int(text[i])
        if i % 2:
            v *= 2

        [digs.append(int(x)) for x in str(v)]

    chek = 0
    valu = sum(digs)
    remd = valu % 10
    if remd != 0:
        chek = 10 - remd

    return str(chek)

class ImeiType(DataType):
    '''
    https://en.wikipedia.org/wiki/International_Mobile_Equipment_Identity
    '''

    def norm(self, valu, oldval=None):

        # TODO: support pre 2004 "old" imei format
        if isinstance(valu, str):
            digs = digits(valu)
            if not digs:
                self._raiseBadValu(valu, mesg='requires a digit string')
            valu = int(digs)

        imei = str(valu)
        ilen = len(imei)

        # we are missing our optional check digit
        # lets add it for consistency...
        if ilen == 14:
            imei += imeicsum(imei)
            return self._norm_imei(imei)

        # if we *have* our check digit, lets check it
        elif ilen == 15:
            if imeicsum(imei) != imei[-1]:
                self._raiseBadValu(valu, mesg='invalid imei checksum byte')
            return self._norm_imei(imei)

        self._raiseBadValu(valu)

    def _norm_imei(self, imei):
        valu = int(imei)
        tac = int(imei[0:8])
        snr = int(imei[8:14])
        cd = int(imei[14:15])
        return valu, {'tac': tac, 'serial': snr, 'cd': cd}

class ImsiType(DataType):

    def norm(self, valu, oldval=None):

        if isinstance(valu, str):
            digs = digits(valu)
            if not digs:
                self._raiseBadValu(valu, mesg='requires a digit string')
            valu = int(digs)

        imsi = str(valu)
        ilen = len(imsi)
        if ilen > 15:
            self._raiseBadValu(valu, mesg='invalid imsi len: %d' % (ilen,))

        mcc = int(imsi[0:3])
        # TODO full imsi analysis tree
        return valu, {'mcc': mcc}

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

                ('tel:mob:tac', {'subof': 'int',
                                 'doc': 'A mobile Type Allocation Code'}),

                ('tel:mob:imei', {'ctor': 'synapse.models.telco.ImeiType',
                                  'doc': 'An International Mobile Equipment Id'}),

                ('tel:mob:imsi', {'ctor': 'synapse.models.telco.ImsiType',
                                  'doc': 'An International Mobile Subscriber Id'}),

                ('tel:mob:imid', {
                    'subof': 'comp',
                    'fields': 'imei=tel:mob:imei,imsi=tel:mob:imsi',
                    'doc': 'Fused knowledge of an IMEI/IMSI used together.'}),

                ('tel:mob:imsiphone', {
                    'subof': 'comp',
                    'fields': 'imsi=tel:mob:imsi,phone=tel:phone',
                    'doc': 'Fused knowledge of an IMSI assigned phone number.'}),

                # TODO: mcc, meid

            ),

            'forms': (

                ('tel:phone', {'ptype': 'tel:phone'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??'}),
                ]),

                ('tel:prefix', {'ptype': 'tel:phone'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??'}),
                    ('tag', {'ptype': 'syn:tag'}),
                ]),

                ('tel:mob:tac', {}, [

                    ('org', {'ptype': 'ou:org',
                             'doc': 'The org guid for the manufacturer'}),

                    ('manu', {'ptype': 'str:lwr', 'defval': '??',
                              'doc': 'The TAC manufacturer name'}),

                    ('model', {'ptype': 'str:lwr', 'defval': '??',
                               'doc': 'The TAC model name'}),

                    ('internal', {'ptype': 'str:lwr', 'defval': '??',
                                  'doc': 'The TAC internal model name'}),
                ]),

                ('tel:mob:imei', {}, [
                    ('tac', {'ptype': 'tel:mob:tac', 'doc': 'The Type Allocate Code within the IMEI'}),
                    ('serial', {'ptype': 'int', 'doc': 'The serial number within the IMEI'}),
                ]),

                ('tel:mob:imsi', {}, [
                    ('mcc', {'ptype': 'int', 'doc': 'The Mobile Country Code'}),
                ]),

                ('tel:mob:imid', {}, [
                    ('imei', {'ptype': 'tel:mob:imei',
                        'doc': 'The IMEI for the phone hardware.'}),
                    ('imsi', {'ptype': 'tel:mob:imsi',
                        'doc': 'The IMSI for the phone subscriber.'}),
                ]),

                ('tel:mob:imsiphone', {}, (

                    ('imsi', {'ptype': 'tel:mob:imsi',
                        'doc': 'The IMSI with the assigned phone number.'}),

                    ('phone', {'ptype': 'tel:phone',
                        'doc': 'The phone number assigned to the IMSI.'}),
                )),

            ),
        }
        name = 'tel'
        return ((name, modl), )
