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

modeldefs = (
    ('tel', {
        'ctors': (

            ('tel:mob:imei', 'synapse.models.telco.Imei', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IMEI'}}),
                ),
                'ex': '490154203237518',
                'doc': 'An International Mobile Equipment Id.'}),

            ('tel:mob:imsi', 'synapse.models.telco.Imsi', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IMSI'}}),
                ),
                'ex': '310150123456789',
                'doc': 'An International Mobile Subscriber Id.'}),

            ('tel:phone', 'synapse.models.telco.Phone', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'phone number'}}),
                ),
                'ex': '+15558675309',
                'doc': 'A phone number.'}),

        ),

        'types': (

            ('tel:call', ('guid', {}), {
                'interfaces': (
                    ('lang:transcript', {}),
                ),
                'doc': 'A telephone call.'}),

            ('tel:phone:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of phone number types.'}),

            ('tel:mob:tac', ('int', {}), {
                'ex': '49015420',
                'doc': 'A mobile Type Allocation Code.'}),

            ('tel:mob:imid', ('comp', {'fields': (('imei', 'tel:mob:imei'), ('imsi', 'tel:mob:imsi'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IMEI and IMSI'}}),
                ),
                'ex': '(490154203237518, 310150123456789)',
                'doc': 'Fused knowledge of an IMEI/IMSI used together.'}),

            ('tel:mob:imsiphone', ('comp', {'fields': (('imsi', 'tel:mob:imsi'), ('phone', 'tel:phone'))}), {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IMSI and phone number'}}),
                ),
                'ex': '(310150123456789, "+7(495) 124-59-83")',
                'doc': 'Fused knowledge of an IMSI assigned phone number.'}),

            ('tel:mob:telem', ('guid', {}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'title': 'telemetry sample'}}),
                ),
                'doc': 'A single mobile telemetry measurement.'}),

            ('tel:mob:mcc', ('str', {'regex': '^[0-9]{3}$'}), {
                'doc': 'ITU Mobile Country Code.'}),

            ('tel:mob:mnc', ('str', {'regex': '^[0-9]{2,3}$'}), {
                'doc': 'ITU Mobile Network Code.'}),

            ('tel:mob:carrier', ('guid', {}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'The fusion of a MCC/MNC.'}),

            ('tel:mob:cell:radio:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of cell radio types.'}),

            ('tel:mob:cell', ('guid', {}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'title': 'cell tower'}}),
                ),
                'doc': 'A mobile cell site which a phone may connect to.'}),

            # TODO - eventually break out ISO-3 country code into a sub
            # https://en.wikipedia.org/wiki/TADIG_code
            ('tel:mob:tadig', ('str', {'regex': '^[A-Z0-9]{5}$'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
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

                ('caller', ('entity:actor', {}), {
                    'doc': 'The entity which placed the call.'}),

                ('caller:phone', ('tel:phone', {}), {
                    'prevnames': ('src',),
                    'doc': 'The phone number the caller placed the call from.'}),

                ('recipient', ('entity:actor', {}), {
                    'doc': 'The entity which received the call.'}),

                ('recipient:phone', ('tel:phone', {}), {
                    'prevnames': ('dst',),
                    'doc': 'The phone number the caller placed the call to.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the call took place.'}),

                ('connected', ('bool', {}), {
                    'doc': 'Indicator of whether the call was connected.'}),
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
                    'computed': True,
                    'doc': 'The Type Allocate Code within the IMEI.'}),

                ('serial', ('int', {}), {
                    'computed': True,
                    'doc': 'The serial number within the IMEI.'})

            )),
            ('tel:mob:imsi', {}, (
                ('mcc', ('tel:mob:mcc', {}), {
                    'computed': True,
                    'doc': 'The Mobile Country Code.',
                }),
            )),
            ('tel:mob:imid', {}, (

                ('imei', ('tel:mob:imei', {}), {
                    'computed': True,
                    'doc': 'The IMEI for the phone hardware.'}),

                ('imsi', ('tel:mob:imsi', {}), {
                    'computed': True,
                    'doc': 'The IMSI for the phone subscriber.'}),
            )),
            ('tel:mob:imsiphone', {}, (

                ('phone', ('tel:phone', {}), {
                    'computed': True,
                    'doc': 'The phone number assigned to the IMSI.'}),

                ('imsi', ('tel:mob:imsi', {}), {
                    'computed': True,
                    'doc': 'The IMSI with the assigned phone number.'}),
            )),
            ('tel:mob:mcc', {}, (
                ('place:country:code', ('iso:3166:alpha2', {}), {
                    'doc': 'The country code which the MCC is assigned to.'}),
            )),
            ('tel:mob:carrier', {}, (

                ('mcc', ('tel:mob:mcc', {}), {
                    'doc': 'The Mobile Country Code.'}),

                ('mnc', ('tel:mob:mnc', {}), {
                    'doc': 'The Mobile Network Code.'}),
            )),
            ('tel:mob:cell:radio:type:taxonomy', {}, ()),
            ('tel:mob:cell', {}, (

                ('carrier', ('tel:mob:carrier', {}), {
                    'doc': 'Mobile carrier which registered the cell tower.'}),

                ('lac', ('int', {}), {
                    'doc': 'Location Area Code. LTE networks may call this a TAC.'}),

                ('cid', ('int', {}), {
                    'doc': 'The Cell ID.'}),

                ('radio', ('tel:mob:cell:radio:type:taxonomy', {}), {
                    'doc': 'Cell radio type.'}),
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
                ('imsi', ('tel:mob:imsi', {}), {}),
                ('imei', ('tel:mob:imei', {}), {}),
                ('phone', ('tel:phone', {}), {}),

                # inet protocol addresses
                ('mac', ('inet:mac', {}), {}),
                ('ip', ('inet:ip', {}), {
                    'prevnames': ('ipv4', 'ipv6')}),

                ('wifi:ap', ('inet:wifi:ap', {}), {
                    'prevnames': ('wifi',)}),

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
