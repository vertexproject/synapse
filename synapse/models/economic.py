import synapse.lib.module as s_module

class EconModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('econ', {

            'types': (

                ('econ:pay:cvv', ('int', {}), {
                    'doc': 'A Card Verification Value (CVV).'}),

                ('econ:pay:mii', ('int', {}), {
                    'doc': 'A Major Industry Identifier (MII).'}),

                ('econ:pay:pan', ('str', {'regex': '^(?<iin>(?<mii>[0-9]{1})[0-9]{5})[0-9]{1,13}$'}), {
                    'doc': 'A Primary Account Number (PAN) or card number.'}),

                ('econ:pay:iin', ('int', {}), {
                    'doc': 'An Issuer Id Number (IIN).'}),

                ('econ:pay:card', ('guid', {}), {
                    'doc': 'A single payment card.'}),

                ('econ:purchase', ('guid', {}), {
                    'doc': 'A purchase event.'}),

                # TODO currency / monitary units / crypto currency
                # econ:acct:bill econ:acct:payment
                # econ:goods econ:services
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
                        'doc': 'The payment card MII.'}),

                    ('name', ('ps:name', {}), {
                        'doc': 'The name as it appears on the card.'}),

                    ('expr', ('time', {}), {
                        'doc': 'The expiration date for the card.'}),

                    ('cvv', ('econ:pay:cvv', {}), {
                        'doc': 'The Card Verification Value on the card.'}),
                )),

                ('econ:purchase', {}, (

                    ('by:org', ('ou:org', {}), {
                        'doc': 'The organization which made the purchase.'}),

                    ('by:person', ('ps:person', {}), {
                        'doc': 'The person who made the purchase.'}),

                    ('by:contact', ('ps:contact', {}), {
                        'doc': 'The contact information used to make the purchase.'}),

                    ('from:org', ('ou:org', {}), {
                        'doc': 'The organization which sold the item.'}),

                    ('from:person', ('ps:person', {}), {
                        'doc': 'The person who sold the item.'}),

                    ('from:contact', ('ps:contact', {}), {
                        'doc': 'The contact information used to sell the item.'}),

                    # TODO price
                    ('pay:card', ('econ:pay:card', {}), {
                        'doc': 'The payment card used for the purchase.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time of the purchase.'}),

                    ('place', ('geo:place', {}), {
                        'doc': 'The place where the purchase took place.'}),

                    ('item', ('ndef', {}), {
                        'doc': 'A node representing the purchased item.'}),
                )),
            ),
        }),)
