import logging

import synapse.exc as s_exc

import synapse.lib.types as s_types

import synapse.lookup.phonenum as s_l_phone

logger = logging.getLogger(__name__)


def digits(text):
    return ''.join([c for c in text if c.isdigit()])

class Phone(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.opts['globsuffix'] = True
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

        self.loctype = self.modl.type('loc')

    async def _normPyStr(self, valu, view=None):
        digs = digits(valu)
        if not digs:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='requires a digit string')
        subs = {}
        try:
            info = s_l_phone.getPhoneInfo(int(digs))
        except Exception as e:  # pragma: no cover
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='Failed to get phone info') from None
        cc = info.get('cc')
        if cc is not None:
            subs['loc'] = (self.loctype.typehash, cc, {})
        # TODO prefix based validation?
        return digs, {'subs': subs}

    async def _normPyInt(self, valu, view=None):
        if valu < 1:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='phone int must be greater than 0')
        return await self._normPyStr(str(valu))

    def repr(self, valu):
        # XXX geo-aware reprs are practically a function of cc which
        # XXX the raw value may only have after doing a s_l_phone lookup
        if valu[0] == '1' and len(valu) == 11:
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

class Imsi(s_types.Int):

    def postTypeInit(self):
        self.opts['size'] = 8
        self.opts['signed'] = False

        self.mcctype = self.modl.type('tel:mob:mcc')

        return s_types.Int.postTypeInit(self)

    async def _normPyInt(self, valu, view=None):
        imsi = str(valu)
        ilen = len(imsi)
        if ilen > 15:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='invalid imsi len: %d' % (ilen,))

        mcc = imsi[0:3]
        # TODO full imsi analysis tree
        return valu, {'subs': {'mcc': (self.mcctype.typehash, mcc, {})}}

# TODO: support pre 2004 "old" imei format
class Imei(s_types.Int):

    def postTypeInit(self):
        self.opts['size'] = 8
        self.opts['signed'] = False

        self.inttype = self.modl.type('int')
        self.tactype = self.modl.type('tel:mob:tac')

        return s_types.Int.postTypeInit(self)

    def chop_imei(self, imei):
        valu = int(imei)
        tac = int(imei[0:8])
        snr = int(imei[8:14])
        return valu, {'subs': {'tac': (self.tactype.typehash, tac, {}),
                               'serial': (self.inttype.typehash, snr, {})}}

    async def _normPyInt(self, valu, view=None):
        imei = str(valu)
        ilen = len(imei)

        # we are missing our optional check digit
        # lets add it for consistency...
        if ilen == 14:
            imei += imeicsum(imei)
            return self.chop_imei(imei)

        # if we *have* our check digit, lets check it
        elif ilen == 15:
            if imeicsum(imei) != imei[-1]:
                raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                        mesg='invalid imei checksum byte')
            return self.chop_imei(imei)

        raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                mesg='Failed to norm IMEI')
