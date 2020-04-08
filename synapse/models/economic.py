import synapse.lib.module as s_module

class EconModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('econ', {

            'types': (

                ('econ:pay:cvv', ('str', {'regex': '^[0-9]{1,6}$'}), {
                    'doc': 'A Card Verification Value (CVV).'}),

                ('econ:pay:pin', ('str', {'regex': '^[0-9]{3,6}$'}), {
                    'doc': 'A Personal Identification Number.'}),

                ('econ:pay:mii', ('int', {'min': 0, 'max': 9}), {
                    'doc': 'A Major Industry Identifier (MII).'}),

                ('econ:pay:pan', ('str', {'regex': '^(?<iin>(?<mii>[0-9]{1})[0-9]{5})[0-9]{1,13}$'}), {
                    'doc': 'A Primary Account Number (PAN) or card number.'}),

                ('econ:pay:iin', ('int', {'min': 0, 'max': 999999}), {
                    'doc': 'An Issuer Id Number (IIN).'}),

                ('econ:pay:card', ('guid', {}), {
                    'doc': 'A single payment card.'}),

                ('econ:purchase', ('guid', {}), {
                    'doc': 'A purchase event.'}),

                ('econ:acquired', ('comp', {'fields': (('purchase', 'econ:purchase'), ('item', 'ndef'))}), {
                    'doc': 'A relationship between a purchase event and a purchased item.'}),

                ('econ:acct:payment', ('guid', {}), {
                    'doc': 'A payment moving currency from one monetary instrument to another.'}),

                # TODO currency / monetary units / crypto currency
                # econ:acct:bill
                # econ:goods econ:services

                # econ:bank:us:aba:rtn ( ABA Routing Number )
                # econ:bank:us:account = (econ:bank:us:aba:rtn, acct)
                # econ:bank:swift:...
            ),

            'forms': (

                ('econ:pay:iin', {}, (

                    ('org', ('ou:org', {}), {
                        'doc': 'The issuer organization.'}),

                    ('name', ('str', {'lower': True}), {
                        'doc': 'The registered name of the issuer.'}),
                )),

                ('econ:pay:card', {}, (

                    ('pan', ('econ:pay:pan', {}), {
                        'doc': 'The payment card number.'}),

                    ('pan:mii', ('econ:pay:mii', {}), {
                        'doc': 'The payment card MII.'}),

                    ('pan:iin', ('econ:pay:iin', {}), {
                        'doc': 'The payment card IIN.'}),

                    ('name', ('ps:name', {}), {
                        'doc': 'The name as it appears on the card.'}),

                    ('expr', ('time', {}), {
                        'doc': 'The expiration date for the card.'}),

                    ('cvv', ('econ:pay:cvv', {}), {
                        'doc': 'The Card Verification Value on the card.'}),

                    ('pin', ('econ:pay:pin', {}), {
                        'doc': 'The Personal Identification Number on the card.'}),
                )),

                ('econ:purchase', {}, (

                    ('by:contact', ('ps:contact', {}), {
                        'doc': 'The contact information used to make the purchase.'}),

                    ('from:contact', ('ps:contact', {}), {
                        'doc': 'The contact information used to sell the item.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time of the purchase.'}),

                    ('place', ('geo:place', {}), {
                        'doc': 'The place where the purchase took place.'}),

                    ('paid', ('bool', {}), {
                        'doc': 'Set to True if the purchase has been paid in full.'}),

                    ('paid:time', ('time', {}), {
                        'doc': 'The point in time where the purchase was paid in full.'}),

                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'The campaign that the purchase was in support of'}),
                    # TODO price
                )),

                ('econ:acquired', {}, (
                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase event which acquired an item.'}),
                    ('item', ('ndef', {}), {
                        'doc': 'A reference to the item that was acquired.'}),
                    ('item:form', ('str', {}), {
                        'doc': 'The form of item purchased.'}),
                )),

                ('econ:acct:payment', {}, (

                    ('from:pay:card', ('econ:pay:card', {}), {
                        'doc': 'The payment card making the payment.'}),

                    ('from:coinaddr', ('crypto:currency:address', {}), {
                        'doc': 'The crypto currency address making the payment.'}),

                    ('from:contact', ('ps:contact', {}), {
                        'doc': 'Contact information for the person/org being paid.'}),

                    ('to:coinaddr', ('crypto:currency:address', {}), {
                        'doc': 'The crypto currency address receiving the payment.'}),

                    ('to:contact', ('ps:contact', {}), {
                        'doc': 'Contact information for the person/org being paid.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the payment was processed.'}),

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase which the payment was paying for.'}),
                )),
            ),
        }),)
