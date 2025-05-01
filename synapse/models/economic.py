import synapse.lib.module as s_module

class EconModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('econ', {

            'types': (

                ('econ:pay:cvv', ('str', {'regex': '^[0-9]{1,6}$'}), {
                    'doc': 'A Card Verification Value (CVV).'}),

                ('econ:pay:pin', ('str', {'regex': '^[0-9]{3,6}$'}), {
                    'doc': 'A Personal Identification Number (PIN).'}),

                ('econ:pay:mii', ('int', {'min': 0, 'max': 9}), {
                    'doc': 'A Major Industry Identifier (MII).'}),

                ('econ:pay:pan', ('str', {'regex': '^(?<iin>(?<mii>[0-9]{1})[0-9]{5})[0-9]{1,13}$'}), {
                    'doc': 'A Primary Account Number (PAN) or card number.'}),

                ('econ:pay:iin', ('int', {'min': 0, 'max': 999999}), {
                    'doc': 'An Issuer Id Number (IIN).'}),

                ('econ:pay:card', ('guid', {}), {

                    'interfaces': ('econ:pay:instrument',),
                    'template': {
                        'instrument': 'payment card'},

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

                ('econ:acct:receipt', ('guid', {}), {
                    'doc': 'A receipt issued as proof of payment.'}),

                ('econ:acct:invoice', ('guid', {}), {
                    'doc': 'An invoice issued requesting payment.'}),

                ('econ:price', ('hugenum', {'norm': False}), {
                    'doc': 'The amount of money expected, required, or given in payment for something.',
                    'ex': '2.20'}),

                ('econ:currency', ('str', {'lower': True, 'strip': False}), {
                    'doc': 'The name of a system of money in general use.',
                    'ex': 'usd'}),

                ('econ:fin:exchange', ('guid', {}), {
                    'doc': 'A financial exchange where securities are traded.'}),

                ('econ:fin:security', ('guid', {}), {
                    'doc': 'A financial security which is typically traded on an exchange.'}),

                ('econ:fin:bar', ('guid', {}), {
                    'doc': 'A sample of the open, close, high, low prices of a security in a specific time window.'}),

                ('econ:fin:tick', ('guid', {}), {
                    'doc': 'A sample of the price of a security at a single moment in time.'}),

                ('econ:bank:account:type:taxonomy', ('taxonomy', {}), {
                    'doc': 'A bank account type taxonomy.'}),

                ('econ:bank:account', ('guid', {}), {

                    'interfaces': ('econ:pay:instrument',),
                    'template': {
                        'instrument': 'bank account'},

                    'doc': 'A bank account.'}),

                ('econ:bank:balance', ('guid', {}), {
                    'doc': 'A balance contained by a bank account at a point in time.'}),

                ('econ:bank:statement', ('guid', {}), {
                    'doc': 'A statement of bank account payment activity over a period of time.'}),

                ('econ:bank:aba:rtn', ('str', {'regex': '[0-9]{9}'}), {
                    'doc': 'An American Bank Association (ABA) routing transit number (RTN).'}),

                ('econ:bank:iban', ('str', {'regex': '[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{1,30}'}), {
                    'doc': 'An International Bank Account Number.'}),

                ('econ:bank:swift:bic', ('str', {'regex': '[A-Z]{6}[A-Z0-9]{5}'}), {
                    'doc': 'A Society for Worldwide Interbank Financial Telecommunication (SWIFT) Business Identifier Code (BIC).'}),

                ('econ:pay:instrument', ('ndef', {'interface': 'econ:pay:instrument'}), {
                    'doc': 'A node which may act as a payment instrument.'}),
            ),

            'interfaces': (
                ('econ:pay:instrument', {

                    'doc': 'An interface for forms which may act as a payment instrument.',
                    'template': {
                        'instrument': 'instrument',
                    },

                    'props': (

                        ('contact', ('ps:contact', {}), {
                            'doc': 'The primary contact for the {instrument}.'}),
                    ),
                }),
            ),

            'edges': (
                (('econ:purchase', 'acquired', None), {
                    'doc': 'The purchase was used to acquire the target node.'}),

                (('econ:bank:statement', 'has', 'econ:acct:payment'), {
                    'doc': 'The bank statement includes the payment.'}),
            ),

            'forms': (

                ('econ:currency', {}, ()),
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

                    ('account', ('econ:bank:account', {}), {
                        'doc': 'A bank account associated with the payment card.'}),
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
                        'doc': 'The econ:price of the purchase.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The econ:price of the purchase.'}),

                    ('listing', ('biz:listing', {}), {
                        'doc': 'The purchase was made based on the given listing.'}),
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

                    ('from:cash', ('bool', {}), {
                        'doc': 'Set to true if the payment input was in cash.'}),

                    ('to:instrument', ('econ:pay:instrument', {}), {
                        'doc': 'The payment instrument which received funds from the payment.'}),

                    ('from:instrument', ('econ:pay:instrument', {}), {
                        'doc': 'The payment instrument used to make the payment.'}),

                    ('from:account', ('econ:bank:account', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :from:instrument.'}),

                    ('from:pay:card', ('econ:pay:card', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :from:instrument.'}),

                    ('from:contract', ('ou:contract', {}), {
                        'doc': 'A contract used as an aggregate payment source.'}),

                    ('from:coinaddr', ('crypto:currency:address', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :from:instrument.'}),

                    ('from:contact', ('ps:contact', {}), {
                        'doc': 'Contact information for the entity making the payment.'}),

                    ('to:cash', ('bool', {}), {
                        'doc': 'Set to true if the payment output was in cash.'}),

                    ('to:account', ('econ:bank:account', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :to:instrument.'}),

                    ('to:coinaddr', ('crypto:currency:address', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :to:instrument.'}),

                    ('to:contact', ('ps:contact', {}), {
                        'doc': 'Contact information for the person/org being paid.'}),

                    ('to:contract', ('ou:contract', {}), {
                        'doc': 'A contract used as an aggregate payment destination.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the payment was processed.'}),

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase which the payment was paying for.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The amount of money transferred in the payment.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency of the payment.'}),

                    ('memo', ('str', {}), {
                        'doc': 'A small note specified by the payer common in financial transactions.'}),

                    ('crypto:transaction', ('crypto:currency:transaction', {}), {
                        'doc': 'A crypto currency transaction that initiated the payment.'}),

                    ('invoice', ('econ:acct:invoice', {}), {
                        'doc': 'The invoice that the payment applies to.'}),

                    ('receipt', ('econ:acct:receipt', {}), {
                        'doc': 'The receipt that was issued for the payment.'}),

                    ('place', ('geo:place', {}), {
                        'doc': 'The place where the payment occurred.'}),

                    ('place:name', ('geo:name', {}), {
                        'doc': 'The name of the place where the payment occurred.'}),

                    ('place:address', ('geo:address', {}), {
                        'doc': 'The address of the place where the payment occurred.'}),

                    ('place:loc', ('loc', {}), {
                        'doc': 'The loc of the place where the payment occurred.'}),

                    ('place:latlong', ('geo:latlong', {}), {
                        'doc': 'The latlong where the payment occurred.'}),
                )),

                ('econ:acct:balance', {}, (

                    ('time', ('time', {}), {
                        'doc': 'The time the balance was recorded.'}),

                    ('instrument', ('econ:pay:instrument', {}), {
                        'doc': 'The financial instrument holding the balance.'}),

                    ('pay:card', ('econ:pay:card', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :instrument.'}),

                    ('crypto:address', ('crypto:currency:address', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use :instrument.'}),

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
                        'doc': 'A simple name for the exchange.',
                        'ex': 'nasdaq'}),

                    ('org', ('ou:org', {}), {
                        'doc': 'The organization that operates the exchange.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency used for all transactions in the exchange.',
                        'ex': 'usd'}),
                )),

                ('econ:fin:security', {}, (

                    ('exchange', ('econ:fin:exchange', {}), {
                        'doc': 'The exchange on which the security is traded.'}),

                    ('ticker', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'The identifier for this security within the exchange.'}),

                    ('type', ('str', {'lower': True, 'strip': True}), {
                        'doc': 'A user defined type such as stock, bond, option, future, or forex.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The last known/available price of the security.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time of the last know price sample.'}),
                )),

                ('econ:fin:tick', {}, (

                    ('security', ('econ:fin:security', {}), {
                        'doc': 'The security measured by the tick.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the price was sampled.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The price of the security at the time.'}),
                )),

                ('econ:fin:bar', {}, (

                    ('security', ('econ:fin:security', {}), {
                        'doc': 'The security measured by the bar.'}),

                    ('ival', ('ival', {}), {
                        'doc': 'The interval of measurement.'}),

                    ('price:open', ('econ:price', {}), {
                        'doc': 'The opening price of the security.'}),

                    ('price:close', ('econ:price', {}), {
                        'doc': 'The closing price of the security.'}),

                    ('price:low', ('econ:price', {}), {
                        'doc': 'The low price of the security.'}),

                    ('price:high', ('econ:price', {}), {
                        'doc': 'The high price of the security.'}),
                )),

                ('econ:acct:invoice', {}, (

                    ('issued', ('time', {}), {
                        'doc': 'The time that the invoice was issued to the recipient.'}),

                    ('issuer', ('ps:contact', {}), {
                        'doc': 'The contact information for the entity who issued the invoice.'}),

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase that the invoice is requesting payment for.'}),

                    ('recipient', ('ps:contact', {}), {
                        'doc': 'The contact information for the intended recipient of the invoice.'}),

                    ('due', ('time', {}), {
                        'doc': 'The time by which the payment is due.'}),

                    ('paid', ('bool', {}), {
                        'doc': 'Set to true if the invoice has been paid in full.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The balance due.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency that the invoice specifies for payment.'}),
                )),

                ('econ:acct:receipt', {}, (

                    ('issued', ('time', {}), {
                        'doc': 'The time the receipt was issued.'}),

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase that the receipt confirms payment for.'}),

                    ('issuer', ('ps:contact', {}), {
                        'doc': 'The contact information for the entity who issued the receipt.'}),

                    ('recipient', ('ps:contact', {}), {
                        'doc': 'The contact information for the entity who received the receipt.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency that the receipt uses to specify the price.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The price that the receipt confirms was paid.'}),
                )),

                ('econ:bank:aba:rtn', {}, (

                    ('bank', ('ou:org', {}), {
                        'doc': 'The bank which was issued the ABA RTN.'}),

                    ('bank:name', ('ou:name', {}), {
                        'doc': 'The name which is registered for this ABA RTN.'}),

                )),

                ('econ:bank:iban', {}, ()),

                ('econ:bank:swift:bic', {}, (

                    ('business', ('ou:org', {}), {
                        'doc': 'The business which is the registered owner of the SWIFT BIC.'}),

                    ('office', ('ps:contact', {}), {
                        'doc': 'The branch or office which is specified in the last 3 digits of the SWIFT BIC.'}),
                )),

                ('econ:bank:account:type:taxonomy', {}, ()),
                ('econ:bank:account', {}, (

                    ('type', ('econ:bank:account:type:taxonomy', {}), {
                        'doc': 'The type of bank account.'}),

                    ('aba:rtn', ('econ:bank:aba:rtn', {}), {
                        'doc': 'The ABA routing transit number for the bank which issued the account.'}),

                    ('number', ('str', {'regex': '[0-9]+'}), {
                        'doc': 'The account number.'}),

                    ('iban', ('econ:bank:iban', {}), {
                        'doc': 'The IBAN for the account.'}),

                    ('issuer', ('ou:org', {}), {
                        'doc': 'The bank which issued the account.'}),

                    ('issuer:name', ('ou:name', {}), {
                        'doc': 'The name of the bank which issued the account.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency of the account balance.'}),

                    ('balance', ('econ:bank:balance', {}), {
                        'doc': 'The most recently known bank balance information.'}),
                )),

                ('econ:bank:balance', {}, (

                    ('time', ('time', {}), {
                        'doc': 'The time that the account balance was observed.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The amount of currency available at the time.'}),

                    ('account', ('econ:bank:account', {}), {
                        'doc': 'The bank account which contained the balance amount.'}),
                )),
                ('econ:bank:statement', {}, (

                    ('account', ('econ:bank:account', {}), {
                        'doc': 'The bank account used to compute the statement.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period that the statement includes.'}),

                    ('starting:balance', ('econ:price', {}), {
                        'doc': 'The account balance at the beginning of the statement period.'}),

                    ('ending:balance', ('econ:price', {}), {
                        'doc': 'The account balance at the end of the statement period.'}),
                )),
            ),
        }),)
