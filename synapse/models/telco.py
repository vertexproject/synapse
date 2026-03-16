import logging

logger = logging.getLogger(__name__)

modeldefs = (
    ('tel', {
        'ctors': (

            ('tel:mob:imei', 'synapse.lib.types.Imei', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IMEI'}}),
                ),
                'ex': '490154203237518',
                'doc': 'An International Mobile Equipment Id.'}),

            ('tel:mob:imsi', 'synapse.lib.types.Imsi', {}, {
                'interfaces': (
                    ('meta:observable', {'template': {'title': 'IMSI'}}),
                ),
                'ex': '310150123456789',
                'doc': 'An International Mobile Subscriber Id.'}),

            ('tel:phone', 'synapse.lib.types.Phone', {}, {
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

                ('time', ('time', {}), {
                    'doc': 'The time that the telemetry sample was taken.'}),

                ('http:request', ('inet:http:request', {}), {
                    'doc': 'The HTTP request that the telemetry was extracted from.'}),

                ('host', ('it:host', {}), {
                    'doc': 'The host that generated the mobile telemetry data.'}),

                # telco specific data
                ('cell', ('tel:mob:cell', {}), {
                    'doc': 'The mobile cell site where the telemetry sample was taken.'}),

                ('imsi', ('tel:mob:imsi', {}), {
                    'doc': 'The IMSI of the device associated with the mobile telemetry sample.'}),

                ('imei', ('tel:mob:imei', {}), {
                    'doc': 'The IMEI of the device associated with the mobile telemetry sample.'}),

                ('phone', ('tel:phone', {}), {
                    'doc': 'The phone number of the device associated with the mobile telemetry sample.'}),

                # inet protocol addresses
                ('mac', ('inet:mac', {}), {
                    'doc': 'The MAC address of the device associated with the mobile telemetry sample.'}),

                ('ip', ('inet:ip', {}), {
                    'doc': 'The IP address of the device associated with the mobile telemetry sample.',
                    'prevnames': ('ipv4', 'ipv6')}),

                ('wifi:ap', ('inet:wifi:ap', {}), {
                    'doc': 'The Wi-Fi AP associated with the mobile telemetry sample.',
                    'prevnames': ('wifi',)}),

                # host specific data
                ('adid', ('it:adid', {}), {
                    'doc': 'The advertising ID of the mobile telemetry sample.'}),

                # FIXME contact prop or interface?
                # User related data
                ('name', ('entity:name', {}), {
                    'doc': 'The user name associated with the mobile telemetry sample.'}),

                ('email', ('inet:email', {}), {
                    'doc': 'The email address associated with the mobile telemetry sample.'}),

                ('account', ('inet:service:account', {}), {
                    'doc': 'The service account which is associated with the tracked device.'}),

                # reporting related data
                ('app', ('it:software', {}), {
                    'doc': 'The app used to report the mobile telemetry sample.'}),

                ('data', ('data', {}), {
                    'doc': 'Data from the mobile telemetry sample.'}),
                # any other fields may be refs...
            )),
        )
    }),
)
