import logging

import synapse.exc as s_exc

import synapse.lib.types as s_types
import synapse.lib.module as s_module

import synapse.lookup.phonenum as s_l_phone

logger = logging.getLogger(__name__)

intls = (
    ('us', '1', '011', 10),
)

# Fixme What do we want to do with these typecasters?
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

def chop_imei(imei):
    valu = int(imei)
    tac = int(imei[0:8])
    snr = int(imei[8:14])
    cd = int(imei[14:15])
    return valu, {'subs': {'tac': tac, 'serial': snr, 'cd': cd}}

class Phone(s_types.Type):
    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    def _normPyStr(self, valu):
        digs = digits(valu)
        if not digs:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='requires a digit string')
        subs = {}
        try:
            info = s_l_phone.getPhoneInfo(int(digs))
        except Exception as e:  # pragma: no cover
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='Failed to get phone info')
        cc = info.get('cc')
        if cc is not None:
            subs['loc'] = cc
        # TODO prefix based validation?
        return digs, {'subs': subs}

    def _normPyInt(self, valu):
        if valu < 1:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='phone int must be greater than 0')
        return self._normPyStr(str(valu))

    def indx(self, valu):
        '''

        Args:
            valu (str): Value to encode

        Returns:
            bytes: Encoded value
        '''
        return valu.encode('utf8')

    def indxByEq(self, valu):
        if isinstance(valu, str) and valu.endswith('*'):
            norm, _ = self._normPyStr(valu)
            return (
                ('pref', self.indx(norm)),
            )
        return s_types.Type.indxByEq(self, valu)

    def repr(self, valu, defval=None):
        # FIXME implement more geo aware reprs
        # XXX geo-aware reprs are practically a function of cc which
        # XXX the raw value may only have after doing a s_l_phone lookup
        if valu[0] == '1':  # FIXME Length check
            area = valu[1:4]
            pref = valu[4:7]
            numb = valu[7:11]
            return '+1 (%s) %s-%s' % (area, pref, numb)

        return '+' + valu

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

class Imsi(s_types.Type):
    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    def _normPyStr(self, valu):
        digs = digits(valu)
        if not digs:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='requires a digit string')
        return self._normPyInt(int(digs))

    def _normPyInt(self, valu):
        imsi = str(valu)
        ilen = len(imsi)
        if ilen > 15:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='invalid imsi len: %d' % (ilen,))

        mcc = int(imsi[0:3])
        # TODO full imsi analysis tree
        return valu, {'subs': {'mcc': mcc}}

    def indx(self, valu):
        '''

        Args:
            valu (int):

        Returns:
            bytes:
        '''
        return valu.to_bytes(8, byteorder='big')

# TODO: support pre 2004 "old" imei format
class Imei(s_types.Type):
    def postTypeInit(self):
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

    def _normPyStr(self, valu):
        digs = digits(valu)
        if not digs:
            raise s_exc.BadTypeValu(valu=valu,
                                    mesg='requires a digit string')
        return self._normPyInt(int(digs))

    def _normPyInt(self, valu):
        imei = str(valu)
        ilen = len(imei)

        # we are missing our optional check digit
        # lets add it for consistency...
        if ilen == 14:
            imei += imeicsum(imei)
            return chop_imei(imei)

        # if we *have* our check digit, lets check it
        elif ilen == 15:
            if imeicsum(imei) != imei[-1]:
                raise s_exc.BadTypeValu(valu=valu,
                                        mesg='invalid imei checksum byte')
            return chop_imei(imei)

        raise s_exc.BadTypeValu(valu=valu,
                                mesg='Failed to norm IMEI')

    def indx(self, valu):
        '''

        Args:
            valu (int):

        Returns:
            bytes:
        '''
        return valu.to_bytes(7, byteorder='big')

class TelcoModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'ctors': (

                ('tel:mob:imei', 'synapse.models.telco.Imei', {}, {
                    'ex': '490154203237518',
                    'doc': 'An International Mobile Equipment Id'}),

                ('tel:mob:imsi', 'synapse.models.telco.Imsi', {}, {
                    'ex': '310150123456789',
                    'doc': 'An International Mobile Subscriber Id'}),

                ('tel:phone', 'synapse.models.telco.Phone', {}, {
                    'ex': '+15558675309',
                    'doc': 'A phone number.'}),

            ),

            'types': (

                ('tel:mob:tac', ('int', {}), {
                    'ex': '49015420',
                    'doc': 'A mobile Type Allocation Code'}),

                ('tel:mob:imid', ('comp', {'fields': (('imei', 'tel:mob:imei'), ('imsi', 'tel:mob:imsi'))}), {
                    'ex': '(490154203237518, 310150123456789)',
                    'doc': 'Fused knowledge of an IMEI/IMSI used together.'}),

                ('tel:mob:imsiphone', ('comp', {'fields': (('imsi', 'tel:mob:imsi'), ('phone', 'tel:phone'))}), {
                    'ex': '(310150123456789, "+7(495) 124-59-83")',
                    'doc': 'Fused knowledge of an IMSI assigned phone number.'}),

                ('tel:mob:telem', ('guid', {}), {
                    'doc': 'A single mobile telemetry measurement.'}),
            ),

            'forms': (
                ('tel:phone', {}, (
                    ('loc', ('loc', {}), {
                        'doc': 'The location associated with the number.',
                        'defval': '??',
                    }),
                )),
                ('tel:mob:tac', {}, (
                    ('org', ('ou:org', {}), {
                        'doc': 'The org guid for the manufacturer',
                    }),
                    ('manu', ('str', {'lower': 1}), {
                        'doc': 'The TAC manufacturer name',
                        'defval': '??',
                    }),
                    ('model', ('str', {'lower': 1}), {
                        'doc': 'The TAC model name',
                        'defval': '??',
                    }),
                    ('internal', ('str', {'lower': 1}), {
                        'doc': 'The TAC internal model name',
                        'defval': '??',
                    }),
                )),
                ('tel:mob:imei', {}, (
                    ('tac', ('tel:mob:tac', {}), {
                        'ro': 1,
                        'doc': 'The Type Allocate Code within the IMEI'
                    }),
                    ('serial', ('int', {}), {
                        'ro': 1,
                        'doc': 'The serial number within the IMEI',
                    })
                )),
                ('tel:mob:imsi', {}, (
                    ('mcc', ('int', {}), {
                        'ro': 1,
                        'doc': 'The Mobile Country Code.',
                    }),
                )),
                ('tel:mob:imid', {}, (
                    ('imei', ('tel:mob:imei', {}), {'ro': 1,
                        'doc': 'The IMEI for the phone hardware.'
                    }),
                    ('imsi', ('tel:mob:imsi', {}), {
                        'ro': 1,
                        'doc': 'The IMSI for the phone subscriber.'
                    }),
                )),
                ('tel:mob:imsiphone', {}, (
                    ('phone', ('tel:phone', {}), {
                        'ro': 1,
                        'doc': 'The phone number assigned to the IMSI.'
                    }),
                    ('imsi', ('tel:mob:imsi', {}), {
                        'ro': 1,
                        'doc': 'The IMSI with the assigned phone number.'
                    }),
                )),

                ('tel:mob:telem', {}, (

                    ('time', ('time', {}), {}),
                    ('latlong', ('geo:latlong', {}), {}),

                    # telco specific data
                    ('imsi', ('tel:mob:imsi', {}), {}),
                    ('imei', ('tel:mob:imei', {}), {}),
                    ('phone', ('tel:phone', {}), {}),

                    # inet protocol addresses
                    ('mac', ('inet:mac', {}), {}),
                    ('ipv4', ('inet:ipv4', {}), {}),
                    ('ipv6', ('inet:ipv6', {}), {}),

                    ('wifi:ssid', ('inet:wifi:ssid', {}), {}),
                    ('wifi:bssid', ('inet:mac', {}), {}),

                    ('data', ('data', {}), {}),
                    # any other fields may be refs...
                )),

            )
        }
        name = 'tel'
        return ((name, modl),)

class TelMod(s_module.CoreModule):

    def initCoreModule(self):
        # TODO
        # event handlers which cache and resolve prefixes to tag phone numbers
        for iso2, cc, idd, size in intls:
            self.core.addTypeCast('tel:loc:%s' % iso2, genTelLocCast(iso2, cc, idd, size))

    @staticmethod
    def getBaseModels():
        modl = {
            'types': (
                # TODO: mcc, meid
            ),

            'forms': (

                ('tel:prefix', {'ptype': 'tel:phone'}, [
                    ('cc', {'ptype': 'pol:iso2', 'defval': '??'}),
                    ('tag', {'ptype': 'syn:tag'}),
                ]),
            ),
        }
        name = 'tel'
        return ((name, modl), )
