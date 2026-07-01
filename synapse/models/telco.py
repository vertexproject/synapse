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

modeldefs = (
    {
        'types': (

            ('tel:mob:imei', ('base:id', {'regex': '^(?<tac>[0-9]{8})(?<serial>[0-9]{6})[0-9]$'}), {
                'template': {'title': 'IMEI'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'ex': '490154203237518',
                'props': (

                    ('tac', ('tel:mob:tac', {}), {
                        'computed': True,
                        'doc': 'The Type Allocate Code within the IMEI.'}),

                    ('serial', ('int', {}), {
                        'computed': True,
                        'doc': 'The serial number within the IMEI.'})

                ),
                'doc': 'An International Mobile Equipment Id.'}),

            ('tel:mob:imsi', ('base:id', {'regex': '^(?<mcc>[0-9]{3})[0-9]{2,12}$'}), {
                'template': {'title': 'IMSI'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('entity:identifier', {}),
                ),
                'ex': '310150123456789',
                'props': (
                    ('mcc', ('tel:mob:mcc', {}), {
                        'computed': True,
                        'doc': 'The Mobile Country Code.',
                    }),
                ),
                'doc': 'An International Mobile Subscriber Id.'}),

            ('tel:phone', (None, {'ctor': 'synapse.models.telco.Phone'}), {
                'template': {'title': 'phone number'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'ex': '+15558675309',
                'props': (

                    ('type', ('tel:phone:type:taxonomy', {}), {
                        'doc': 'The type of phone number.'}),

                    ('loc', ('loc', {}), {
                        'doc': 'The location associated with the number.'}),

                ),
                'doc': 'A phone number.'}),

            ('tel:call', ('guid', {}), {
                'interfaces': (
                    ('base:activity', {}),
                    ('lang:transcript', {}),
                ),
                'props': (

                    ('caller', ('entity:actor', {}), {
                        'doc': 'The entity which placed the call.'}),

                    ('caller:phone', ('tel:phone', {}), {
                        'prevnames': ('src',),
                        'doc': 'The phone number the caller placed the call from.'}),

                    ('recipient', ('entity:actor', {}), {
                        'doc': 'The entity which received the call.'}),

                    ('recipient:phone', ('tel:phone', {}), {
                        'prevnames': ('dst',),
                        'doc': 'The phone number at which the recipient received the call.'}),

                    ('period', None, {
                        'doc': 'The time period when the call took place.'}),

                    ('connected', ('bool', {}), {
                        'doc': 'Specifies whether the call was successfully connected.'}),
                ),
                'doc': 'A telephone call.'}),

            ('tel:phone:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy of phone number types.'}),

            ('tel:mob:tac', ('int', {}), {
                'interfaces': (
                    ('meta:havable', {}),
                ),
                'props': (
                    ('model', ('biz:model', {}), {
                        'doc': 'The TAC model name.'}),
                ),
                'ex': '49015420',
                'doc': 'A mobile Type Allocation Code.'}),

            ('tel:mob:imid', ('comp', {'fields': (('imei', 'tel:mob:imei'), ('imsi', 'tel:mob:imsi'))}), {
                'template': {'title': 'IMEI and IMSI'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('entity:identifier', {}),
                ),
                'ex': '(490154203237518, 310150123456789)',
                'props': (

                    ('imei', ('tel:mob:imei', {}), {
                        'computed': True,
                        'doc': 'The IMEI for the phone hardware.'}),

                    ('imsi', ('tel:mob:imsi', {}), {
                        'computed': True,
                        'doc': 'The IMSI for the phone subscriber.'}),
                ),
                'doc': 'Fused knowledge of an IMEI/IMSI used together.'}),

            ('tel:mob:imsiphone', ('comp', {'fields': (('imsi', 'tel:mob:imsi'), ('phone', 'tel:phone'))}), {
                'template': {'title': 'IMSI and phone number'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'ex': '(310150123456789, "+7(495) 124-59-83")',
                'props': (

                    ('phone', ('tel:phone', {}), {
                        'computed': True,
                        'doc': 'The phone number assigned to the IMSI.'}),

                    ('imsi', ('tel:mob:imsi', {}), {
                        'computed': True,
                        'doc': 'The IMSI with the assigned phone number.'}),
                ),
                'doc': 'Fused knowledge of an IMSI assigned phone number.'}),

            ('tel:mob:mcc', ('base:id', {'regex': '^[0-9]{3}$'}), {
                'props': (
                    ('place:country:code', ('iso:3166:alpha2', {}), {
                        'doc': 'The country code which the MCC is assigned to.'}),
                ),
                'doc': 'ITU Mobile Country Code.'}),

            ('tel:mob:mnc', ('base:id', {'regex': '^[0-9]{2,3}$'}), {
                'doc': 'ITU Mobile Network Code.'}),

            ('tel:mob:carrier', ('comp', {'fields': (('mcc', 'tel:mob:mcc'), ('mnc', 'tel:mob:mnc'))}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'props': (

                    ('mcc', ('tel:mob:mcc', {}), {
                        'computed': True,
                        'doc': 'The Mobile Country Code.'}),

                    ('mnc', ('tel:mob:mnc', {}), {
                        'computed': True,
                        'doc': 'The Mobile Network Code.'}),
                ),
                'ex': '(310, 150)',
                'doc': 'The fusion of a MCC/MNC.'}),

            ('tel:mob:cell:radio:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of cell radio types.'}),

            ('tel:mob:cell', ('guid', {}), {
                'template': {'title': 'cell tower'},
                'interfaces': (
                    ('geo:locatable', {}),
                ),
                'props': (

                    ('carrier', ('tel:mob:carrier', {}), {
                        'doc': 'Mobile carrier which registered the cell tower.'}),

                    ('lac', ('int', {}), {
                        'doc': 'Location Area Code. LTE networks may call this a TAC.'}),

                    ('cid', ('int', {}), {
                        'doc': 'The Cell ID.'}),

                    ('radio', ('tel:mob:cell:radio:type:taxonomy', {}), {
                        'doc': 'Cell radio type.'}),
                ),
                'doc': 'A mobile cell site which a phone may connect to.'}),

            # TODO - eventually break out ISO-3 country code into a sub
            # https://en.wikipedia.org/wiki/TADIG_code
            ('tel:mob:tadig', ('base:id', {'regex': '^[A-Z0-9]{5}$'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'props': (),
                'doc': 'A Transferred Account Data Interchange Group number issued to a GSM carrier.'}),

        ),
    },
)
