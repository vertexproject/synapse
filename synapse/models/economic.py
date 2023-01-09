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

                ('econ:receipt:item', ('guid', {}), {
                    'doc': 'A line item included as part of a purchase.'}),

                ('econ:acquired', ('comp', {'fields': (('purchase', 'econ:purchase'), ('item', 'ndef'))}), {
                    'deprecated': True,
                    'doc': 'Deprecated. Please use econ:purchase -(acquired)> *.'}),

                ('econ:acct:payment', ('guid', {}), {
                    'doc': 'A payment or crypto currency transaction.'}),

                ('econ:acct:balance', ('guid', {}), {
                    'doc': 'A snapshot of the balance of an account at a point in time.'}),

                ('econ:price', ('hugenum', {'norm': False}), {
                    'doc': 'The amount of money expected, required, or given in payment for something',
                    'ex': '2.20'}),

                ('econ:currency', ('str', {'lower': True, 'strip': False}), {
                    'doc': 'The name of a system of money in general use',
                    'ex': 'usd'}),

                ('econ:fin:exchange', ('guid', {}), {
                    'doc': 'A financial exchange where securities are traded.'}),

                ('econ:fin:security', ('guid', {}), {
                    'doc': 'A financial security which is typically traded on an exchange.'}),

                ('econ:fin:bar', ('guid', {}), {
                    'doc': 'A sample of the open, close, high, low prices of a security in a specific time window'}),

                ('econ:fin:tick', ('guid', {}), {
                    'doc': 'A sample of the price of a security at a single moment in time'}),

                # econ:acct:bill
                # econ:bank:us:aba:rtn ( ABA Routing Number )
                # econ:bank:us:account = (econ:bank:us:aba:rtn, acct)
                # econ:bank:swift:...
            ),

            'edges': (
                (('econ:purchase', 'acquired', None), {
                    'doc': 'The purchase was used to acquire the target node.'}),
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

                    ('settled', ('time', {}), {
                        'doc': 'The point in time where the purchase was settled.'}),

                    ('campaign', ('ou:campaign', {}), {
                        'doc': 'The campaign that the purchase was in support of.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The econ:price of the purchase'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The econ:price of the purchase'}),
                )),

                ('econ:receipt:item', {}, (

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase that contains this line item.'}),

                    ('count', ('int', {'min': 1}), {
                        'doc': 'The number of items included in this line item.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The total cost of this receipt line item.'}),

                    ('product', ('biz:product', {}), {
                        'doc': 'The product being being purchased in this line item.'}),
                )),
                ('econ:acquired', {}, (
                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase event which acquired an item.', 'ro': True, }),
                    ('item', ('ndef', {}), {
                        'doc': 'A reference to the item that was acquired.', 'ro': True, }),
                    ('item:form', ('str', {}), {
                        'doc': 'The form of item purchased.'}),
                )),

                ('econ:acct:payment', {}, (

                    ('txnid', ('str', {'strip': True}), {
                        'doc': 'A payment processor specific transaction id.'}),

                    ('fee', ('econ:price', {}), {
                        'doc': 'The transaction fee paid by the recipient to the payment processor.'}),

                    ('from:pay:card', ('econ:pay:card', {}), {
                        'doc': 'The payment card making the payment.'}),

                    ('from:contract', ('ou:contract', {}), {
                        'doc': 'A contract used as an aggregate payment source.'}),

                    ('from:coinaddr', ('crypto:currency:address', {}), {
                        'doc': 'The crypto currency address making the payment.'}),

                    ('from:contact', ('ps:contact', {}), {
                        'doc': 'Contact information for the person/org being paid.'}),

                    ('to:coinaddr', ('crypto:currency:address', {}), {
                        'doc': 'The crypto currency address receiving the payment.'}),

                    ('to:contact', ('ps:contact', {}), {
                        'doc': 'Contact information for the person/org being paid.'}),

                    ('to:contract', ('ou:contract', {}), {
                        'doc': 'A contract used as an aggregate payment destination.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the payment was processed.'}),

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase which the payment was paying for.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The amount of money transferred in the payment'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency of the payment'}),

                    ('memo', ('str', {}), {
                        'doc': 'A small note specified by the payer common in financial transactions.'}),

                    ('crypto:transaction', ('crypto:currency:transaction', {}), {
                        'doc': 'A crypto currency transaction that initiated the payment.'}),

                )),

                ('econ:acct:balance', {}, (
                    ('time', ('time', {}), {
                        'doc': 'The time the balance was recorded.'}),
                    ('pay:card', ('econ:pay:card', {}), {
                        'doc': 'The payment card holding the balance.'}),
                    ('crypto:address', ('crypto:currency:address', {}), {
                        'doc': 'The crypto currency address holding the balance.'}),
                    ('amount', ('econ:price', {}), {
                        'doc': 'The account balance at the time.'}),
                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency of the balance amount.'}),
                    ('delta', ('econ:price', {}), {
                        'doc': 'The change since last regular sample.'}),
                    ('total:received', ('econ:price', {}), {
                        'doc': 'The total amount of currency received by the account.'}),
                    ('total:sent', ('econ:price', {}), {
                        'doc': 'The total amount of currency sent from the account.'}),
                )),


                ('econ:fin:exchange', {}, (

                    ('name', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'A simple name for the exchange',
                        'ex': 'nasdaq'}),

                    ('org', ('ou:org', {}), {
                        'doc': 'The organization that operates the exchange'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency used for all transactions in the exchange',
                        'ex': 'usd'}),
                )),

                ('econ:fin:security', {}, (

                    ('exchange', ('econ:fin:exchange', {}), {
                        'doc': 'The exchange on which the security is traded'}),

                    ('ticker', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The identifier for this security within the exchange'}),

                    ('type', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'A user defined type such as stock, bond, option, future, or forex'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The last known/available price of the security'}),

                    ('time', ('time', {}), {
                        'doc': 'The time of the last know price sample'}),
                )),

                ('econ:fin:tick', {}, (

                    ('security', ('econ:fin:security', {}), {
                        'doc': 'The security measured by the tick'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the price was sampled'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The price of the security at the time'}),
                )),

                ('econ:fin:bar', {}, (

                    ('security', ('econ:fin:security', {}), {
                        'doc': 'The security measured by the bar'}),

                    ('ival', ('ival', {}), {
                        'doc': 'The interval of measurement'}),

                    ('price:open', ('econ:price', {}), {
                        'doc': 'The opening price of the security'}),

                    ('price:close', ('econ:price', {}), {
                        'doc': 'The closing price of the security'}),

                    ('price:low', ('econ:price', {}), {
                        'doc': 'The low price of the security'}),

                    ('price:high', ('econ:price', {}), {
                        'doc': 'The high price of the security'}),
                )),
            ),
        }),)
