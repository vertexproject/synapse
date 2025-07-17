modeldefs = (
    ('econ', {

        'types': (

            ('biz:sellable', ('ndef', {'forms': ('biz:product', 'biz:service')}), {
                'doc': 'A product or service which may be sold.'}),

            ('econ:pay:cvv', ('str', {'regex': '^[0-9]{1,6}$'}), {
                'doc': 'A Card Verification Value (CVV).'}),

            ('econ:pay:pin', ('str', {'regex': '^[0-9]{3,6}$'}), {
                'doc': 'A Personal Identification Number (PIN).'}),

            ('econ:pay:mii', ('int', {'min': 0, 'max': 9}), {
                'doc': 'A Major Industry Identifier (MII).'}),

            ('econ:pay:pan', ('str', {'regex': '^(?<iin>(?<mii>[0-9]{1})[0-9]{5})[0-9]{1,13}$'}), {
                'doc': 'A Primary Account Number (PAN) or card number.'}),

            ('econ:pay:iin', ('int', {'min': 0, 'max': 999999}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'An Issuer Id Number (IIN).'}),

            ('econ:pay:card', ('guid', {}), {
                'interfaces': (
                    ('econ:pay:instrument', {'template': {'instrument': 'payment card'}}),
                ),
                'doc': 'A single payment card.'}),

            ('econ:bank:check', ('guid', {}), {
                'interfaces': (
                    ('econ:pay:instrument', {'template': {'instrument': 'check'}}),
                ),
                'doc': 'A check written out to a recipient.'}),

            # TODO...
            # ('econ:bank:wire', ('guid', {}), {}),

            ('econ:purchase', ('guid', {}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'geo:locatable': 'purchase event'}}),
                ),
                'doc': 'A purchase event.'}),

            ('econ:lineitem', ('guid', {}), {
                'prevnames': ('econ:receipt:item',),
                'doc': 'A line item included as part of a purchase.'}),

            ('econ:payment', ('guid', {}), {
                'interfaces': (
                    ('geo:locatable', {'template': {'geo:locatable': 'payment event'}}),
                ),
                'doc': 'A payment, crypto currency transaction, or account withdrawal.'}),

            ('econ:balance', ('guid', {}), {
                'doc': 'The balance of funds available to a financial instrument at a specific time.'}),

            ('econ:statement', ('guid', {}), {
                'doc': 'A statement of starting/ending balance and payments for a financial instrument over a time period.'}),

            ('econ:receipt', ('guid', {}), {
                'doc': 'A receipt issued as proof of payment.'}),

            ('econ:invoice', ('guid', {}), {
                'doc': 'An invoice issued requesting payment.'}),

            ('econ:price', ('hugenum', {'norm': False}), {
                'doc': 'The amount of money expected, required, or given in payment for something.',
                'ex': '2.20'}),

            ('econ:currency', ('str', {'lower': True, 'strip': False}), {
                'doc': 'The name of a system of money in general use.',
                'ex': 'usd'}),

            ('econ:fin:exchange', ('guid', {}), {
                'doc': 'A financial exchange where securities are traded.'}),

            ('econ:fin:security:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of financial security types.'}),

            ('econ:fin:security', ('guid', {}), {
                'doc': 'A financial security which is typically traded on an exchange.'}),

            ('econ:fin:bar', ('guid', {}), {
                'doc': 'A sample of the open, close, high, low prices of a security in a specific time window.'}),

            ('econ:fin:tick', ('guid', {}), {
                'doc': 'A sample of the price of a security at a single moment in time.'}),

            ('econ:fin:account:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A financial account type taxonomy.'}),

            ('econ:fin:account', ('guid', {}), {
                'doc': 'A financial account which contains a balance of funds.'}),

            ('econ:bank:aba:account:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (('meta:taxonomy', {}),),
                'doc': 'A type taxonomy for ABA bank account numbers.'}),

            ('econ:bank:aba:account', ('guid', {}), {
                'doc': 'An ABA routing number and bank account number.'}),

            # TODO: econ:pay:cash (for an individual grip of cash. could reference bills/coins with numbers)
            ('econ:cash:deposit', ('guid', {}), {
                'doc': 'A cash deposit event to a financial account.'}),

            ('econ:cash:withdrawal', ('guid', {}), {
                'doc': 'A cash withdrawal event from a financial account.'}),

            ('econ:bank:aba:rtn', ('str', {'regex': '[0-9]{9}'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'An American Bank Association (ABA) routing transit number (RTN).'}),

            ('econ:bank:iban', ('str', {'regex': '[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{1,30}'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'An International Bank Account Number.'}),

            ('econ:bank:swift:bic', ('str', {'regex': '[A-Z]{6}[A-Z0-9]{5}'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'doc': 'A Society for Worldwide Interbank Financial Telecommunication (SWIFT) Business Identifier Code (BIC).'}),

            ('econ:pay:instrument', ('ndef', {'interface': 'econ:pay:instrument'}), {
                'doc': 'A node which may act as a payment instrument.'}),
        ),

        'interfaces': (
            ('econ:pay:instrument', {

                'doc': 'An interface for forms which may act as a payment instrument.',
                'template': {'instrument': 'instrument'},

                'props': (
                    ('account', ('econ:fin:account', {}), {
                        'doc': 'The account contains the funds used by the {instrument}.'}),
                ),
            }),
        ),

        'edges': (

            # (('econ:purchase', 'acquired', 'entity:havable'), {
                # 'doc': 'The purchase was used to acquire the target node.'}),

            (('econ:purchase', 'has', 'econ:lineitem'), {
                'doc': 'The purchase included the line item.'}),

            (('econ:receipt', 'has', 'econ:lineitem'), {
                'doc': 'The receipt included the line item.'}),

            (('econ:statement', 'has', 'econ:payment'), {
                'doc': 'The financial statement includes the payment.'}),
        ),

        'forms': (

            ('econ:currency', {}, ()),
            ('econ:pay:iin', {}, (

                ('issuer', ('ou:org', {}), {
                    'prevnames': ('org',),
                    'doc': 'The issuer organization.'}),

                ('issuer:name', ('meta:name', {}), {
                    'prevnames': ('name',),
                    'doc': 'The registered name of the issuer.'}),
            )),

            ('econ:pay:card', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name as it appears on the card.'}),

                ('pan', ('econ:pay:pan', {}), {
                    'doc': 'The payment card number.'}),

                ('pan:mii', ('econ:pay:mii', {}), {
                    'doc': 'The payment card MII.'}),

                ('pan:iin', ('econ:pay:iin', {}), {
                    'doc': 'The payment card IIN.'}),

                ('expr', ('time', {}), {
                    'doc': 'The expiration date for the card.'}),

                ('cvv', ('econ:pay:cvv', {}), {
                    'doc': 'The Card Verification Value on the card.'}),

                ('pin', ('econ:pay:pin', {}), {
                    'doc': 'The Personal Identification Number on the card.'}),
            )),

            ('econ:bank:check', {}, (

                ('payto', ('meta:name', {}), {
                    'doc': 'The name of the intended recipient.'}),

                ('amount', ('econ:price', {}), {
                    'doc': 'The amount the check is written for.'}),

                ('routing', ('econ:bank:aba:rtn', {}), {
                    'doc': 'The ABA routing number on the check.'}),

                ('account:number', ('str', {'regex': '[0-9]{1, 12}'}), {
                    'doc': 'The bank account number.'}),
            )),

            ('econ:purchase', {}, (

                ('buyer', ('entity:actor', {}), {
                    'prevnames': ('by:contact',),
                    'doc': 'The buyer which purchased the items.'}),

                ('seller', ('entity:actor', {}), {
                    'prevnames': ('from:contact',),
                    'doc': 'The seller which sold the items.'}),

                ('time', ('time', {}), {
                    'doc': 'The time of the purchase.'}),

                ('paid', ('bool', {}), {
                    'doc': 'Set to True if the purchase has been paid in full.'}),

                ('paid:time', ('time', {}), {
                    'doc': 'The point in time where the purchase was paid in full.'}),

                # FIXME overfit...
                # ('campaign', ('ou:campaign', {}), {
                #   'doc': 'The campaign that the purchase was in support of.'}),

                ('price', ('econ:price', {}), {
                    'protocols': {
                        'econ:adjustable': {'vars': {
                            'time': {'type': 'prop', 'name': 'time'},
                            'currency': {'type': 'prop', 'name': 'currency'}}},
                    },
                    'doc': 'The econ:price of the purchase.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The econ:price of the purchase.'}),

                # FIXME biz discussion
                # ('listing', ('biz:listing', {}), {
                #   'doc': 'The purchase was made based on the given listing.'}),
            )),

            ('econ:lineitem', {}, (

                ('count', ('int', {'min': 1}), {
                    'doc': 'The number of items included in this line item.'}),

                ('price', ('econ:price', {}), {
                    'doc': 'The total cost of this receipt line item.'}),

                ('item', ('biz:sellable', {}), {
                    'prevnames': ('product',),
                    'doc': 'The product or service.'}),
            )),

            ('econ:cash:deposit', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time the cash was deposited.'}),

                ('actor', ('entity:actor', {}), {
                    'doc': 'The entity which deposited the cash.'}),

                ('amount', ('econ:price', {}), {
                    'doc': 'The amount of cash deposited.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of the deposited cash.'}),

                ('account', ('econ:fin:account', {}), {
                    'doc': 'The account the cash was deposited to.'}),
            )),

            ('econ:cash:withdrawal', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time the cash was withdrawn.'}),

                ('actor', ('entity:actor', {}), {
                    'doc': 'The entity which withdrew the cash.'}),

                ('amount', ('econ:price', {}), {
                    'doc': 'The amount of cash withdrawn.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of the withdrawn cash.'}),

                ('account', ('econ:fin:account', {}), {
                    'doc': 'The account the cash was withdrawn from.'}),
            )),

            ('econ:payment', {}, (

                ('id', ('base:id', {}), {
                    'prevnames': ('txnid',),
                    'doc': 'A payment processor specific transaction ID.'}),

                ('time', ('time', {}), {
                    'doc': 'The time the payment was made.'}),

                ('fee', ('econ:price', {}), {
                    'doc': 'The transaction fee paid by the recipient to the payment processor.'}),

                ('cash', ('bool', {}), {
                    'doc': 'The payment was made with physical currency.'}),

                ('payee', ('entity:actor', {}), {
                    'doc': 'The entity which received the payment.'}),

                ('payee:instrument', ('econ:pay:instrument', {}), {
                    'doc': 'The payment instrument used by the payee to receive payment.'}),

                ('payer', ('entity:actor', {}), {
                    'doc': 'The entity which made the payment.'}),

                ('payer:instrument', ('econ:pay:instrument', {}), {
                    'doc': 'The payment instrument used by the payer to make the payment.'}),

                # FIXME one to many?
                # ('purchases', ('array', {'type': 'econ:purchase', 'uniq': True, 'sorted': True}), {
                #    'doc': 'The payment was made in exchange for the given purchases.'}),

                ('amount', ('econ:price', {}), {
                    'protocols': {
                        'econ:adjustable': {'vars': {
                            'time': {'type': 'prop', 'name': 'time'},
                            'currency': {'type': 'prop', 'name': 'currency'}}},
                    },
                    'doc': 'The amount of money transferred in the payment.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of the payment.'}),

                ('crypto:transaction', ('crypto:currency:transaction', {}), {
                    'doc': 'A crypto currency transaction that initiated the payment.'}),

                # FIXME one to many?
                # ('invoice', ('array', {'type': 'econ:invoice', 'uniq': True, 'sorted': True}), {
                #   doc': 'The invoices that the payment applies to.'}),

                # FIXME one to many?
                # ('receipt', ('econ:receipt', {}),
                    # 'doc': 'The receipts that was issued for the payment.'}),

                # FIXME geo:locatable
                # ('place', ('geo:place', {}), {
                    # 'doc': 'The place where the payment occurred.'}),

                # ('place:name', ('meta:name', {}), {
                    # 'doc': 'The name of the place where the payment occurred.'}),

                # ('place:address', ('geo:address', {}), {
                    # 'doc': 'The address of the place where the payment occurred.'}),

                # ('place:loc', ('loc', {}), {
                    # 'doc': 'The loc of the place where the payment occurred.'}),

                # ('place:latlong', ('geo:latlong', {}), {
                    # 'doc': 'The latlong where the payment occurred.'}),
            )),

            ('econ:balance', {}, (

                ('time', ('time', {}), {
                    'doc': 'The time the balance was recorded.'}),

                ('account', ('econ:fin:account', {}), {
                    'doc': 'The financial account holding the balance.'}),

                ('amount', ('econ:price', {}), {
                    'protocols': {
                        'econ:adjustable': {'vars': {
                            'time': {'type': 'prop', 'name': 'time'},
                            'currency': {'type': 'prop', 'name': 'currency'}}},
                    },
                    'doc': 'The available funds at the time.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of the available funds.'}),
            )),

            ('econ:statement', {}, (

                # TODO: total volume of changes etc...

                ('account', ('econ:fin:account', {}), {
                    'doc': 'The financial account described by the statement.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period that the statement includes.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency used to store the balances.'}),

                ('starting:balance', ('econ:price', {}), {
                    'protocols': {
                        'econ:adjustable': {'vars': {
                            'time': {'type': 'prop', 'name': 'period.min'},
                            'currency': {'type': 'prop', 'name': 'currency'}}},
                    },
                    'doc': 'The balance at the beginning of the statement period.'}),

                ('ending:balance', ('econ:price', {}), {
                    'protocols': {
                        'econ:adjustable': {'vars': {
                            'time': {'type': 'prop', 'name': 'period.max'},
                            'currency': {'type': 'prop', 'name': 'currency'}}},
                    },
                    'doc': 'The balance at the end of the statement period.'}),
            )),

            ('econ:fin:exchange', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'A simple name for the exchange.',
                    'ex': 'nasdaq'}),

                ('org', ('ou:org', {}), {
                    'doc': 'The organization that operates the exchange.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency used for all transactions in the exchange.',
                    'ex': 'usd'}),
            )),

            ('econ:fin:security:type:taxonomy', {}, ()),
            ('econ:fin:security', {}, (

                ('exchange', ('econ:fin:exchange', {}), {
                    'doc': 'The exchange on which the security is traded.'}),

                ('ticker', ('str', {'lower': True, 'strip': True}), {
                    'doc': 'The identifier for this security within the exchange.'}),

                ('type', ('econ:fin:security:type:taxonomy', {}), {
                    'doc': 'The type of security.'}),

                # FIXME valuable
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

                ('period', ('ival', {}), {
                    'prevnames': ('ival',),
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

            ('econ:invoice', {}, (

                ('issued', ('time', {}), {
                    'doc': 'The time that the invoice was issued to the recipient.'}),

                ('issuer', ('entity:actor', {}), {
                    'doc': 'The contact information for the entity which issued the invoice.'}),

                ('purchase', ('econ:purchase', {}), {
                    'doc': 'The purchase that the invoice is requesting payment for.'}),

                ('recipient', ('entity:actor', {}), {
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

            ('econ:receipt', {}, (

                ('issued', ('time', {}), {
                    'doc': 'The time the receipt was issued.'}),

                ('purchase', ('econ:purchase', {}), {
                    'doc': 'The purchase that the receipt confirms payment for.'}),

                # FIXME entity:contact?
                ('issuer', ('entity:actor', {}), {
                    'doc': 'The contact information for the entity which issued the receipt.'}),

                ('recipient', ('entity:actor', {}), {
                    'doc': 'The contact information for the entity which received the receipt.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency that the receipt uses to specify the price.'}),

                ('amount', ('econ:price', {}), {
                    'doc': 'The price that the receipt confirms was paid.'}),
            )),

            ('econ:bank:aba:rtn', {}, (

                ('bank', ('ou:org', {}), {
                    'doc': 'The bank which was issued the ABA RTN.'}),

                ('bank:name', ('meta:name', {}), {
                    'doc': 'The name which is registered for this ABA RTN.'}),

            )),

            ('econ:bank:iban', {}, ()),

            ('econ:bank:swift:bic', {}, (

                ('business', ('ou:org', {}), {
                    'doc': 'The business which is the registered owner of the SWIFT BIC.'}),

                # FIXME ou:office?
                ('office', ('entity:actor', {}), {
                    'doc': 'The branch or office which is specified in the last 3 digits of the SWIFT BIC.'}),
            )),

            ('econ:fin:account:type:taxonomy', {}, ()),
            ('econ:fin:account', {}, (

                ('type', ('econ:fin:account:type:taxonomy', {}), {
                    'doc': 'The type of financial account.'}),

                ('holder', ('entity:contactable', {}), {
                    'doc': 'The contact information of the account holder.'}),

                ('balance', ('econ:price', {}), {
                    'doc': 'The most recently known balance of the account.'}),

                ('balance:time', ('time', {}), {
                    'prevnames': ('balance:asof',),
                    'doc': 'The time the balance was most recently updated.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of the account balance.'}),
            )),


            ('econ:bank:aba:account:type:taxonomy', {}, ()),
            ('econ:bank:aba:account', {}, (

                ('type', ('econ:bank:aba:account:type:taxonomy', {}), {
                    'ex': 'checking',
                    'doc': 'The type of ABA account.'}),

                ('issuer', ('entity:actor', {}), {
                    'doc': 'The bank which issued the account number.'}),

                ('issuer:name', ('meta:name', {}), {
                    'doc': 'The name of the bank which issued the account number.'}),

                ('account', ('econ:fin:account', {}), {
                    'doc': 'The financial account which stores currency for this ABA account number.'}),

                ('routing', ('econ:bank:aba:rtn', {}), {
                    'doc': 'The routing number.'}),

                ('number', ('str', {'regex': '[0-9]+'}), {
                    'doc': 'The account number.'}),
            )),
        ),
    }),
)
