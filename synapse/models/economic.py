modeldefs = (
    {

        'types': (

            ('econ:price', (None, {'ctor': 'synapse.lib.types.Price'}), {
                'ex': '2.20',
                'virts': (

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency denomination of the price.'}),

                    ('adjusted', ('econ:price:adjusted', {}), {
                        'doc': 'The inflation or currency adjusted price.'}),
                ),
                'doc': 'The amount of money expected, required, or given in payment for something.'}),

            ('econ:price:adjusted', ('guid', {}), {
                'props': (

                    ('value', ('econ:price', {}), {
                        'doc': 'The adjusted price value.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time to which the price was adjusted.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency to which the price was adjusted.'}),
                ),
                'doc': 'An inflation or currency adjusted price.'}),

            ('econ:pricerange', (None, {'ctor': 'synapse.lib.types.PriceRange'}), {
                'ex': '1.50-2.20',
                'virts': (

                    ('min', ('econ:price', {}), {
                        'doc': 'The minimum (inclusive) price.'}),

                    ('max', ('econ:price', {}), {
                        'doc': 'The maximum (inclusive) price.'}),

                    ('delta', ('econ:price', {}), {
                        'doc': 'The size of the range (max - min).'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency denomination.'}),
                ),
                'doc': 'An inclusive range of prices.'}),

            ('econ:pricechange', (None, {'ctor': 'synapse.lib.types.PriceChange'}), {
                'virts': (

                    ('start', ('econ:price', {}), {
                        'doc': 'The starting (inclusive) price.'}),

                    ('end', ('econ:price', {}), {
                        'doc': 'The ending (inclusive) price.'}),

                    ('delta', ('econ:price', {}), {
                        'doc': 'The signed change in price (end - start).'}),

                    ('rate', ('ratio', {}), {
                        'doc': 'The change as a percent of the starting price.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency denomination.'}),
                ),
                'doc': 'A directional change of a price over an interval.'}),

            ('econ:pay:cvv', ('str', {'regex': '^[0-9]{1,6}$'}), {
                'doc': 'A Card Verification Value (CVV).'}),

            ('econ:pay:pin', ('str', {'regex': '^[0-9]{3,6}$'}), {
                'doc': 'A Personal Identification Number (PIN).'}),

            ('econ:pay:mii', ('int', {'min': 0, 'max': 9}), {
                'doc': 'A Major Industry Identifier (MII).'}),

            ('econ:pay:pan', ('str', {'regex': '^(?<iin>(?<mii>[0-9]{1})[0-9]{5})[0-9]{1,13}$'}), {
                'props': (

                    ('mii', ('econ:pay:mii', {}), {
                        'computed': True,
                        'doc': 'The Major Industry Identifier (MII) of the PAN.'}),

                    ('iin', ('econ:pay:iin', {}), {
                        'computed': True,
                        'doc': 'The Issuer Identification Number (IIN) of the PAN.'}),
                ),
                'doc': 'A Primary Account Number (PAN) or card number.'}),

            ('econ:pay:iin', ('base:id', {'regex': '^[0-9]{6,8}$'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                ),
                'props': (

                    ('issuer', ('ou:org', {}), {
                        'prevnames': ('org',),
                        'doc': 'The issuer organization.'}),

                    ('issuer:name', ('entity:name', {}), {
                        'prevnames': ('name',),
                        'doc': 'The registered name of the issuer.'}),
                ),
                'doc': 'An Issuer Id Number (IIN).'}),

            ('econ:pay:card', ('guid', {}), {
                'template': {'title': 'payment card'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('econ:pay:instrument', {}),
                ),
                'props': (

                    ('name', ('entity:name', {}), {
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
                ),
                'doc': 'A single payment card.'}),

            ('econ:bank:check', ('guid', {}), {
                'template': {'title': 'check'},
                'interfaces': (
                    ('meta:observable', {}),
                    ('econ:pay:instrument', {}),
                ),
                'props': (

                    ('payto', ('entity:name', {}), {
                        'doc': 'The name of the intended recipient.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The amount the check is written for.'}),

                    ('bank:account', ('econ:bank:account', {}), {
                        'doc': 'The bank account the check is drawn against.'}),
                ),
                'doc': 'A check written out to a recipient.'}),

            # TODO: entity:purchased?
            ('econ:purchase', ('guid', {}), {
                'template': {'title': 'purchase', 'verb': 'made'},
                'interfaces': (
                    ('entity:event', {}),
                    ('geo:locatable', {}),
                ),
                'props': (

                    ('seller', ('entity:actor', {}), {
                        'prevnames': ('from:contact',),
                        'doc': 'The actor who sold the items.'}),

                    ('seller:name', ('entity:name', {}), {
                        'doc': 'The name of the actor who sold the items.'}),

                    ('paid', ('time', {}), {
                        'doc': 'The time when the purchase was paid in full.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The price of the purchase.'}),
                ),
                'doc': 'An event where an actor made a purchase.'}),

            ('econ:lineitem', ('guid', {}), {
                'prevnames': ('econ:receipt:item',),
                'props': (

                    ('count', ('size', {}), {
                        'doc': 'The number of items included in this line item.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The total cost of this receipt line item.'}),

                    ('item', (
                            ('biz:service', {}),
                            ('meta:havable', {}),
                        ), {
                        'prevnames': ('product',),
                        'doc': 'The product or service.'}),
                ),
                'doc': 'A line item included as part of a purchase.'}),

            ('econ:payment', ('guid', {}), {
                'template': {'title': 'payment event'},
                'interfaces': (
                    ('entity:event', {}),
                    ('geo:locatable', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'prevnames': ('txnid',),
                        'doc': 'A payment processor specific transaction ID.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the payment was made.'}),

                    ('fee', ('econ:price', {}), {
                        'doc': 'The transaction fee paid by the recipient to the payment processor.'}),

                    ('cash', ('bool', {}), {
                        'doc': 'Set to true if the payment was made with physical currency.'}),

                    ('status', ('title', {}), {
                        'doc': 'The status of the payment.'}),

                    ('payee', ('entity:actor', {}), {
                        'doc': 'The entity which received the payment.'}),

                    ('payee:instrument', ('econ:pay:instrument', {}), {
                        'doc': 'The payment instrument used by the payee to receive payment.'}),

                    ('payee:account', ('econ:account', {}), {
                        'doc': 'The account the payment was received into.'}),

                    ('actor:instrument', ('econ:pay:instrument', {}), {
                        'doc': 'The payment instrument used by the actor to make the payment.'}),

                    ('actor:account', ('econ:account', {}), {
                        'doc': 'The account the payment was made from.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The amount of money transferred in the payment.'}),

                    ('crypto:transaction', ('crypto:currency:transaction', {}), {
                        'doc': 'A crypto currency transaction that initiated the payment.'}),
                ),
                'doc': 'A payment, crypto currency transaction, or account withdrawal.'}),

            ('econ:balance', ('guid', {}), {
                'props': (

                    ('time', ('time', {}), {
                        'doc': 'The time the balance was recorded.'}),

                    ('account', ('econ:account', {}), {
                        'doc': 'The financial account holding the balance.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The available funds at the time.'}),

                    ('change', ('econ:pricechange', {}), {
                        'doc': 'The change in the account balance since the previous balance sample.'}),

                    ('previous', ('econ:balance', {}), {
                        'doc': 'The previous balance sample for the account.'}),
                ),
                'doc': 'The balance of funds available in an account at specific time.'}),

            ('econ:statement', ('guid', {}), {
                'props': (

                    # TODO: total volume of changes etc...

                    ('account', ('econ:account', {}), {
                        'doc': 'The financial account described by the statement.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period that the statement includes.'}),

                    ('previous', ('econ:statement', {}), {
                        'doc': 'The statement for the previous period.'}),

                    ('balance', ('econ:price', {}), {
                        'doc': 'The balance at the end of the statement period.'}),
                ),
                'doc': 'A statement of starting/ending balance and payments for a financial instrument over a time period.'}),

            ('econ:receipt', ('guid', {}), {
                'props': (

                    ('issued', ('time', {}), {
                        'doc': 'The time the receipt was issued.'}),

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase that the receipt confirms payment for.'}),

                    ('issuer', ('entity:actor', {}), {
                        'doc': 'The entity which issued the receipt.'}),

                    ('recipient', ('entity:actor', {}), {
                        'doc': 'The entity which received the receipt.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The price that the receipt confirms was paid.'}),
                ),
                'doc': 'A receipt issued as proof of payment.'}),

            ('econ:invoice', ('guid', {}), {
                'props': (

                    ('issued', ('time', {}), {
                        'doc': 'The time that the invoice was issued to the recipient.'}),

                    ('issuer', ('entity:actor', {}), {
                        'doc': 'The entity which issued the invoice.'}),

                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase that the invoice is requesting payment for.'}),

                    ('recipient', ('entity:actor', {}), {
                        'doc': 'The entity which received the invoice.'}),

                    ('due', ('time', {}), {
                        'doc': 'The time by which the payment is due.'}),

                    ('paid', ('bool', {}), {
                        'doc': 'Set to true if the invoice has been paid in full.'}),

                    ('amount', ('econ:price', {}), {
                        'doc': 'The balance due.'}),
                ),
                'doc': 'An invoice issued requesting payment.'}),

            ('econ:allocation', ('econ:pricechange', {'names': {'start': 'allocated', 'end': 'spent', 'delta': 'variance'}}), {
                'doc': 'An allocation of funds and the amount spent against it, with the variance between them.'}),

            ('econ:budget', ('guid', {}), {
                'template': {'title': 'budget', 'verb': 'managed', 'activity': 'was in effect'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'doc': 'The ID of the budget.'}),

                    ('name', ('title', {}), {
                        'doc': 'The name of the budget.'}),

                    ('funds', ('econ:allocation', {}), {
                        'doc': 'The funds allocated and spent over the period.'}),

                    ('previous', ('econ:budget', {}), {
                        'doc': 'The budget for the previous period.'}),
                ),
                'doc': 'A budget of funds allocated and spent over a period.'}),

            # common currency symbols -> ISO 4217 codes. ('$' and the yen/yuan
            # sign are ambiguous and are mapped to their most common code.)
            ('econ:currency', ('str', {'upper': True, 'mapping': {
                                '$': 'USD',
                                '€': 'EUR',
                                '£': 'GBP',
                                '¥': 'JPY',
                                '₹': 'INR',
                                '₩': 'KRW',
                                '₽': 'RUB',
                                '₺': 'TRY',
                                '฿': 'THB',
                            }}), {
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The full name of the currency.'}),
                ),
                'doc': 'A currency. This should ideally be an ISO 4217 currency code when one is available.',
                'ex': 'USD'}),

            ('econ:exchange', ('guid', {}), {
                'props': (

                    ('operator', ('entity:actor', {}), {
                        'doc': 'The entity which operates the exchange.'}),

                    ('operator:name', ('entity:name', {}), {
                        'doc': 'The name of the entity which operates the exchange.'}),

                    ('currency', ('econ:currency', {}), {
                        'doc': 'The currency used for all transactions in the exchange.',
                        'ex': 'usd'}),
                ),
                'doc': 'A financial exchange where securities are traded.'}),

            ('econ:security:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of financial security types.'}),

            ('econ:security', ('guid', {}), {
                'props': (

                    ('exchange', ('econ:exchange', {}), {
                        'doc': 'The exchange on which the security is traded.'}),

                    ('ticker', ('title', {}), {
                        'doc': 'The identifier for this security within the exchange.'}),

                    ('type', ('econ:security:type:taxonomy', {}), {
                        'doc': 'The type of security.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The last known/available price of the security.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time of the last know price sample.'}),
                ),
                'doc': 'A financial security which is typically traded on an exchange.'}),

            ('econ:security:ochlv', ('guid', {}), {
                'props': (

                    ('security', ('econ:security', {}), {
                        'doc': 'The security measured by the sample.'}),

                    ('exchange', ('econ:exchange', {}), {
                        'doc': 'The exchange on which the security was traded during the period.'}),

                    ('period', ('ival', {}), {
                        'prevnames': ('ival',),
                        'doc': 'The interval of measurement.'}),

                    ('change', ('econ:pricechange', {}), {
                        'doc': 'The open to close price change of the security during the period.'}),

                    ('range', ('econ:pricerange', {}), {
                        'doc': 'The low to high price range of the security during the period.'}),

                    ('volume', ('hugenum', {}), {
                        'doc': 'The traded volume of the security during the period.'}),

                    ('volume:delta', ('hugenum', {}), {
                        'doc': 'The change in traded volume since the previous sample.'}),

                    ('volume:delta:rate', ('ratio', {}), {
                        'doc': 'The volume delta as a percent of the previous sample.'}),

                    ('previous', ('econ:security:ochlv', {}), {
                        'doc': 'The preceding OCHLV sample.'}),
                ),
                'doc': 'A sample of the open, close, high, low prices and volume of a security in a specific time window.'}),

            ('econ:security:telem', ('guid', {}), {
                'props': (

                    ('security', ('econ:security', {}), {
                        'doc': 'The security measured by the telemetry sample.'}),

                    ('exchange', ('econ:exchange', {}), {
                        'doc': 'The exchange on which the security was traded at the time.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time the price was sampled.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The price of the security at the time.'}),
                ),
                'doc': 'A sample of the price of a security at a single moment in time.'}),

            ('econ:account:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A financial account type taxonomy.'}),

            ('econ:account', ('guid', {}), {
                'template': {'title': 'financial account'},
                'interfaces': (
                    ('meta:observable', {}),
                ),
                'props': (

                    ('type', ('econ:account:type:taxonomy', {}), {
                        'doc': 'The type of financial account.'}),

                    ('holder', ('entity:contactable', {}), {
                        'doc': 'The contact information of the account holder.'}),

                    ('balance', ('econ:price', {}), {
                        'doc': 'The most recently known balance of the account.'}),

                    ('issuer', ('entity:actor', {}), {
                        'doc': 'The financial institution which issued the account.'}),

                    ('issuer:name', ('entity:name', {}), {
                        'doc': 'The name of the financial institution which issued the account.'}),

                    ('id', ('base:id', {}), {
                        'alts': ('ids',),
                        'doc': 'The ID or account number of the account.'}),

                    ('ids', ('base:id', {}), {
                        'array': {},
                        'doc': 'An array of IDs or account numbers for the account.'}),
                ),
                'doc': 'A financial account which contains a balance of funds.'}),

            # TODO: econ:pay:cash (for an individual grip of cash. could reference bills/coins with numbers)
            ('econ:bank:aba:rtn', ('base:id', {'regex': '^[0-9]{9}$'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                    ('econ:bank:routing:code', {}),
                ),
                'props': (),
                'doc': 'An American Bank Association (ABA) routing transit number (RTN).'}),

            ('econ:bank:iban', ('base:id', {'regex': '^[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{1,30}$'}), {
                'template': {'title': 'IBAN account'},
                'interfaces': (
                    ('entity:identifier', {}),
                    ('econ:pay:instrument', {}),
                ),
                'props': (),
                'doc': 'An International Bank Account Number.'}),

            ('econ:bank:swift:bic', ('base:id', {'regex': '^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$'}), {
                'interfaces': (
                    ('entity:identifier', {}),
                    ('econ:bank:routing:code', {}),
                ),
                'props': (

                    ('office', ('entity:contact', {}), {
                        'doc': 'The branch or office which is specified in the last 3 digits of the SWIFT BIC.'}),
                ),
                'doc': 'A Society for Worldwide Interbank Financial Telecommunication (SWIFT) Business Identifier Code (BIC).'}),

            ('econ:bank:routing:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (('meta:taxonomy', {}),),
                'props': (),
                'doc': 'A taxonomy of bank routing identifier systems.'}),

            ('econ:bank:routing:id', ('base:id', {}), {
                'interfaces': (
                    ('entity:identifier', {}),
                    ('econ:bank:routing:code', {}),
                ),
                'props': (
                    ('type', ('econ:bank:routing:type:taxonomy', {}), {
                        'doc': 'The kind of bank routing system this identifier belongs to.'}),
                ),
                'doc': 'A generic bank routing identifier for routing systems without a dedicated form.'}),

            ('econ:bank:account', ('comp', {
                    'sepr': ':',
                    'fields': (
                        ('routing', 'econ:bank:routing:code'),
                        ('id', 'base:id'),
                    ),
                }), {
                'template': {'title': 'bank account'},
                'interfaces': (
                    ('econ:pay:instrument', {}),
                ),
                'props': (
                    ('routing', ('econ:bank:routing:code', {}), {
                        'computed': True,
                        'doc': 'The bank routing identifier portion of the account identifier.'}),

                    ('id', ('base:id', {}), {
                        'computed': True,
                        'doc': 'The account identifier within the routing system.'}),
                ),
                'doc': 'A bank account paired with the routing identifier that addresses it.'}),
        ),

        'interfaces': (
            ('econ:budgetable', {

                'doc': 'An interface for forms which may have an associated budget.',
                'template': {'title': 'item'},

                'props': (
                    ('budget', ('econ:budget', {}), {
                        'doc': 'The budget for the {title}.'}),
                ),
            }),

            ('econ:pay:instrument', {

                'doc': 'An interface for forms which may act as a payment instrument.',
                'template': {'title': 'instrument'},

                'props': (
                    ('account', ('econ:account', {}), {
                        'doc': 'The account that contains the funds used by the {title}.'}),
                ),
            }),

            ('econ:bank:routing:code', {

                'doc': 'An interface for forms which identify a bank or branch for routing purposes.',

                'props': (
                    ('bank', ('ou:org', {}), {
                        'doc': 'The bank or branch which the routing identifier refers to.'}),

                    ('bank:name', ('entity:name', {}), {
                        'doc': 'The name of the bank or branch.'}),
                ),
            }),
        ),

        'edges': (

            (('econ:purchase', 'had', 'econ:lineitem'), {
                'doc': 'The purchase included the line item.'}),

            (('econ:purchase', 'purchased', 'meta:havable'), {
                'doc': 'The purchase was used to acquire the target node.'}),

            (('econ:receipt', 'has', 'econ:lineitem'), {
                'doc': 'The receipt included the line item.'}),

            (('econ:statement', 'has', 'econ:payment'), {
                'doc': 'The financial statement includes the payment.'}),

            (('econ:purchase', 'ledto', 'econ:payment'), {
                'doc': 'The purchase led to the payment.'}),

            (('econ:budget', 'had', 'econ:purchase'), {
                'doc': 'The purchase was included as spent during the budget period.'}),
        ),
    },
)
