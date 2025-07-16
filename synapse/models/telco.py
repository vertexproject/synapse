import logging

import synapse.exc as s_exc

import synapse.lib.types as s_types

import synapse.lookup.phonenum as s_l_phone

logger = logging.getLogger(__name__)


def digits(text):
    return ''.join([c for c in text if c.isdigit()])

def chop_imei(imei):
    valu = int(imei)
    tac = int(imei[0:8])
    snr = int(imei[8:14])
    cd = int(imei[14:15])
    return valu, {'subs': {'tac': tac, 'serial': snr, 'cd': cd}}

class Phone(s_types.Str):

    def postTypeInit(self):
        s_types.Str.postTypeInit(self)
        self.opts['globsuffix'] = True
        self.setNormFunc(str, self._normPyStr)
        self.setNormFunc(int, self._normPyInt)

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
            subs['loc'] = cc
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
        return s_types.Int.postTypeInit(self)

    async def _normPyInt(self, valu, view=None):
        imsi = str(valu)
        ilen = len(imsi)
        if ilen > 15:
            raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                    mesg='invalid imsi len: %d' % (ilen,))

        mcc = imsi[0:3]
        # TODO full imsi analysis tree
        return valu, {'subs': {'mcc': mcc}}

# TODO: support pre 2004 "old" imei format
class Imei(s_types.Int):

    def postTypeInit(self):
        self.opts['size'] = 8
        self.opts['signed'] = False
        return s_types.Int.postTypeInit(self)

    async def _normPyInt(self, valu, view=None):
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
                raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                        mesg='invalid imei checksum byte')
            return chop_imei(imei)

        raise s_exc.BadTypeValu(valu=valu, name=self.name,
                                mesg='Failed to norm IMEI')

modeldefs = (
    ('tel', {
        'ctors': (

            ('tel:mob:imei', 'synapse.models.telco.Imei', {}, {
                'ex': '490154203237518',
                'doc': 'An International Mobile Equipment Id.'}),

            ('tel:mob:imsi', 'synapse.models.telco.Imsi', {}, {
                'ex': '310150123456789',
                'doc': 'An International Mobile Subscriber Id.'}),

            ('tel:phone', 'synapse.models.telco.Phone', {}, {
                'ex': '+15558675309',
                'doc': 'A phone number.'}),

        ),

        'types': (

            ('tel:call', ('guid', {}), {
                'interfaces': (
                    ('lang:transcript', {}),
                ),
                'doc': 'A guid for a telephone call record.'}),

            ('tel:phone:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of phone number types.'}),

            ('tel:txtmesg', ('guid', {}), {
                'doc': 'A guid for an individual text message.'}),

            ('tel:mob:tac', ('int', {}), {
                'ex': '49015420',
                'doc': 'A mobile Type Allocation Code.'}),

            ('tel:mob:imid', ('comp', {'fields': (('imei', 'tel:mob:imei'), ('imsi', 'tel:mob:imsi'))}), {
                'ex': '(490154203237518, 310150123456789)',
                'doc': 'Fused knowledge of an IMEI/IMSI used together.'}),

            ('tel:mob:imsiphone', ('comp', {'fields': (('imsi', 'tel:mob:imsi'), ('phone', 'tel:phone'))}), {
                'ex': '(310150123456789, "+7(495) 124-59-83")',
                'doc': 'Fused knowledge of an IMSI assigned phone number.'}),

            ('tel:mob:telem', ('guid', {}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'geo:locatable': 'telemetry sample'}}),
                ),
                'doc': 'A single mobile telemetry measurement.'}),

            ('tel:mob:mcc', ('str', {'regex': '^[0-9]{3}$', 'strip': True}), {
                'doc': 'ITU Mobile Country Code.'}),

            ('tel:mob:mnc', ('str', {'regex': '^[0-9]{2,3}$', 'strip': True}), {
                'doc': 'ITU Mobile Network Code.'}),

            ('tel:mob:carrier', ('comp', {'fields': (('mcc', 'tel:mob:mcc'), ('mnc', 'tel:mob:mnc'))}), {
                'doc': 'The fusion of a MCC/MNC.'}),

            ('tel:mob:cell:radio:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of cell radio types.'}),

            ('tel:mob:cell', ('comp', {'fields': (('carrier', 'tel:mob:carrier'),
                                                  ('lac', ('int', {})),
                                                  ('cid', ('int', {})))}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'geo:locatable': 'cell tower'}}),
                ),
                'doc': 'A mobile cell site which a phone may connect to.'}),

            # TODO - eventually break out ISO-3 country code into a sub
            # https://en.wikipedia.org/wiki/TADIG_code
            ('tel:mob:tadig', ('str', {'regex': '^[A-Z0-9]{5}$', 'strip': True}), {
                'doc': 'A Transferred Account Data Interchange Group number issued to a GSM carrier.'}),

        ),

        'forms': (
            ('tel:phone:type:taxonomy', {}, ()),
            ('tel:phone', {}, (

                ('type', ('tel:phone:type:taxonomy', {}), {
                    'doc': 'The type of phone number.'}),

                ('loc', ('loc', {}), {
                    'doc': 'The location associated with the number.'}),

            )),

            ('tel:call', {}, (

                ('src', ('tel:phone', {}), {
                    'doc': 'The source phone number for a call.'}),

                ('dst', ('tel:phone', {}), {
                    'doc': 'The destination phone number for a call.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the call took place.'}),

                ('connected', ('bool', {}), {
                    'doc': 'Indicator of whether the call was connected.'}),

                ('recording', ('file:bytes', {}), {
                    'doc': 'An audio file which recorded the call.'}),
            )),
            ('tel:txtmesg', {}, (

                ('from', ('tel:phone', {}), {
                    'doc': 'The phone number assigned to the sender.'}),

                ('to', ('tel:phone', {}), {
                    'doc': 'The phone number assigned to the primary recipient.'}),

                ('recipients', ('array', {'type': 'tel:phone', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of phone numbers for additional recipients of the message.'}),

                ('svctype', ('str', {'enums': 'sms,mms,rcs', 'strip': True, 'lower': True}), {
                    'doc': 'The message service type (sms, mms, rcs).'}),

                ('time', ('time', {}), {
                    'doc': 'The time the message was sent.'}),

                ('text', ('text', {}), {
                    'doc': 'The text of the message.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'A file containing related media.'}),
            )),
            ('tel:mob:tac', {}, (

                ('org', ('ou:org', {}), {
                    'doc': 'The org guid for the manufacturer.'}),

                ('manu', ('str', {'lower': True}), {
                    'doc': 'The TAC manufacturer name.'}),
                # FIXME manufactured

                ('model', ('meta:name', {}), {
                    'doc': 'The TAC model name.'}),

                ('internal', ('meta:name', {}), {
                    'doc': 'The TAC internal model name.'}),

            )),
            ('tel:mob:imei', {}, (

                ('tac', ('tel:mob:tac', {}), {
                    'ro': True,
                    'doc': 'The Type Allocate Code within the IMEI.'}),

                ('serial', ('int', {}), {
                    'ro': True,
                    'doc': 'The serial number within the IMEI.'})

            )),
            ('tel:mob:imsi', {}, (
                ('mcc', ('tel:mob:mcc', {}), {
                    'ro': True,
                    'doc': 'The Mobile Country Code.',
                }),
            )),
            ('tel:mob:imid', {}, (

                ('imei', ('tel:mob:imei', {}), {
                    'ro': True,
                    'doc': 'The IMEI for the phone hardware.'}),

                ('imsi', ('tel:mob:imsi', {}), {
                    'ro': True,
                    'doc': 'The IMSI for the phone subscriber.'}),
            )),
            ('tel:mob:imsiphone', {}, (

                ('phone', ('tel:phone', {}), {
                    'ro': True,
                    'doc': 'The phone number assigned to the IMSI.'}),

                ('imsi', ('tel:mob:imsi', {}), {
                    'ro': True,
                    'doc': 'The IMSI with the assigned phone number.'}),
            )),
            ('tel:mob:mcc', {}, (
                ('loc', ('loc', {}), {'doc': 'Location assigned to the MCC.'}),
            )),
            ('tel:mob:carrier', {}, (

                ('mcc', ('tel:mob:mcc', {}), {
                    'ro': True}),

                ('mnc', ('tel:mob:mnc', {}), {
                    'ro': True}),

                ('org', ('ou:org', {}), {
                    'doc': 'Organization operating the carrier.'}),

                ('loc', ('loc', {}), {
                    'doc': 'Location the carrier operates from.'}),

                ('tadig', ('tel:mob:tadig', {}), {
                    'doc': 'The TADIG code issued to the carrier.'}),
            )),
            ('tel:mob:cell:radio:type:taxonomy', {}, ()),
            ('tel:mob:cell', {}, (
                ('carrier', ('tel:mob:carrier', {}), {'doc': 'Mobile carrier.', 'ro': True, }),
                ('carrier:mcc', ('tel:mob:mcc', {}), {'doc': 'Mobile Country Code.', 'ro': True, }),
                ('carrier:mnc', ('tel:mob:mnc', {}), {'doc': 'Mobile Network Code.', 'ro': True, }),
                ('lac', ('int', {}), {'doc': 'Location Area Code. LTE networks may call this a TAC.',
                                      'ro': True, }),
                ('cid', ('int', {}), {'doc': 'The Cell ID.', 'ro': True, }),
                ('radio', ('tel:mob:cell:radio:type:taxonomy', {}), {'doc': 'Cell radio type.'}),
            )),

            ('tel:mob:tadig', {}, ()),

            ('tel:mob:telem', {}, (

                ('time', ('time', {}), {}),

                ('http:request', ('inet:http:request', {}), {
                    'doc': 'The HTTP request that the telemetry was extracted from.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host that generated the mobile telemetry data.'}),

                # telco specific data
                ('cell', ('tel:mob:cell', {}), {}),
                ('cell:carrier', ('tel:mob:carrier', {}), {}),
                ('imsi', ('tel:mob:imsi', {}), {}),
                ('imei', ('tel:mob:imei', {}), {}),
                ('phone', ('tel:phone', {}), {}),

                # inet protocol addresses
                ('mac', ('inet:mac', {}), {}),
                ('ip', ('inet:ip', {}), {
                    'prevnames': ('ipv4', 'ipv6')}),

                ('wifi:ap', ('inet:wifi:ap', {}), {
                    'prevnames': ('wifi',)}),

                ('wifi:ap:ssid', ('inet:wifi:ssid', {}), {
                    'prevnames': ('wifi:ssid',)}),

                ('wifi:ap:bssid', ('inet:mac', {}), {
                    'prevnames': ('wifi:bssid',)}),

                # host specific data
                ('adid', ('it:adid', {}), {
                    'doc': 'The advertising ID of the mobile telemetry sample.'}),

                # FIXME contact prop or interface?
                # User related data
                ('name', ('meta:name', {}), {}),
                ('email', ('inet:email', {}), {}),

                ('account', ('inet:service:account', {}), {
                    'doc': 'The service account which is associated with the tracked device.'}),

                # reporting related data
                ('app', ('it:software', {}), {}),

                ('data', ('data', {}), {}),
                # any other fields may be refs...
            )),

        )
    }),
)
