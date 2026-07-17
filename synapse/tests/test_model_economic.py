import synapse.exc as s_exc
import synapse.tests.utils as s_utils

class EconTest(s_utils.SynTest):

    async def test_model_econ(self):

        async with self.getTestCore() as core:

            # test card number 4024007150779444
            card = (await core.nodes('[ econ:pay:card="*" :expr=201802 :name="Bob Smith" :cvv=123 :pin=1234 :pan=4024007150779444 ]'))[0]
            self.propeq(card, 'name', 'Bob Smith')
            self.propeq(card, 'expr', 1517443200000000)
            self.propeq(card, 'pan', '4024007150779444')
            self.propeq(card, 'pan:mii', 4)
            self.propeq(card, 'pan:iin', '402400')

            # Setting :pan auto-creates econ:pay:pan form node
            pans = await core.nodes('econ:pay:pan=4024007150779444')
            self.len(1, pans)
            pan = pans[0]
            self.eq('4024007150779444', pan.ndef[1])
            self.propeq(pan, 'mii', 4)
            self.propeq(pan, 'iin', '402400')

            # Pivot from card to pan works
            self.len(1, await core.nodes('econ:pay:card -> econ:pay:pan'))

            # econ:pay:pan can be created standalone
            nodes = await core.nodes('[ econ:pay:pan=5500005555555559 ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'mii', 5)
            self.propeq(nodes[0], 'iin', '550000')

            # econ:pay:pan:iin pivots to econ:pay:iin
            self.len(1, await core.nodes('econ:pay:pan=4024007150779444 -> econ:pay:iin'))
            self.len(1, await core.nodes('econ:pay:pan=4024007150779444 :iin -> econ:pay:iin'))

            # bad PAN rejected
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ econ:pay:pan=notapan ]')

            text = '''[
                econ:purchase="*"

                    :price=13.37
                    :actor={[ entity:contact=* ]}
                    :seller={[ entity:contact=* ]}

                    :time=20180202

                    :place=* as geo:place
                    :place:loc=us.ny.brooklyn

                    :paid=20180202
            ]'''

            perc = (await core.nodes(text))[0]

            self.propeq(perc, 'price', '13.37')

            self.len(1, await core.nodes('econ:purchase :actor -> entity:contact'))
            self.len(1, await core.nodes('econ:purchase :seller -> entity:contact'))

            self.len(1, await core.nodes('econ:purchase:price=13.37'))
            self.len(1, await core.nodes('econ:purchase:price=13.370'))
            self.len(0, await core.nodes('econ:purchase:price=13.372'))

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('econ:purchase [ :price=730750818665451459101843 ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('econ:purchase [ :price=-730750818665451459101843 ]')

            self.len(1, await core.nodes('econ:purchase:price*range=(13,14)'))

            self.len(1, await core.nodes('econ:purchase:price>10.00'))
            self.len(1, await core.nodes('econ:purchase:price<20.00'))
            self.len(1, await core.nodes('econ:purchase:price>=10.00'))
            self.len(1, await core.nodes('econ:purchase:price>=13.37'))
            self.len(1, await core.nodes('econ:purchase:price<=20.00'))
            self.len(1, await core.nodes('econ:purchase:price<=13.37'))

            self.len(0, await core.nodes('econ:purchase:price<10.00'))
            self.len(0, await core.nodes('econ:purchase:price>20.00'))
            self.len(0, await core.nodes('econ:purchase:price>=20.00'))
            self.len(0, await core.nodes('econ:purchase:price<=10.00'))

            # runtime filter/cmpr test for econ:price
            self.len(1, await core.nodes('econ:purchase:price +:price=13.37'))
            self.len(1, await core.nodes('econ:purchase:price +:price=13.370'))
            self.len(0, await core.nodes('econ:purchase:price +:price=13.372'))

            self.len(1, await core.nodes('econ:purchase:price +:price*range=(13,14)'))

            self.len(1, await core.nodes('econ:purchase:price +:price>10.00'))
            self.len(1, await core.nodes('econ:purchase:price +:price<20.00'))
            self.len(1, await core.nodes('econ:purchase:price +:price>=10.00'))
            self.len(1, await core.nodes('econ:purchase:price +:price>=13.37'))
            self.len(1, await core.nodes('econ:purchase:price +:price<=20.00'))
            self.len(1, await core.nodes('econ:purchase:price +:price<=13.37'))

            self.len(0, await core.nodes('econ:purchase:price +:price<10.00'))
            self.len(0, await core.nodes('econ:purchase:price +:price>20.00'))
            self.len(0, await core.nodes('econ:purchase:price +:price>=20.00'))
            self.len(0, await core.nodes('econ:purchase:price +:price<=10.00'))

            self.propeq(perc, 'paid', 1517529600000000)

            self.propeq(perc, 'place:loc', 'us.ny.brooklyn')

            self.len(1, await core.nodes('econ:purchase -> geo:place'))
            self.len(2, await core.nodes('econ:purchase -> entity:contact | uniq'))

            nodes = await core.nodes('''
                econ:purchase
                    [
                        +(had)> {[ econ:lineitem=* :item={[ biz:product=* :name=widget ]} ]}
                        +(purchased)> {[ biz:product=* :name=gadget ]}
                    ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('econ:purchase -(had)> econ:lineitem'))
            self.len(1, await core.nodes('econ:purchase -(purchased)> biz:product +:name=gadget'))
            self.len(1, await core.nodes('econ:purchase -(purchased)> *'))

            text = '''[
                econ:payment=*

                    :payee={[ entity:contact=* :name=payee ]}
                    :actor={[ entity:contact=* :name=payer ]}

                    :payee:account={[ econ:account=* :id=payeeacct ]}
                    :actor:account={[ econ:account=* :id=actoracct ]}

                    :status=settled
                    :amount = 20.30

                    :time=20180202

                    :place=* as geo:place
                    :place:loc=us.ny.brooklyn
                    :place:name=myhouse
                    :place:address="123 main street, brooklyn, ny, 11223"
                    :place:latlong=(90,80)
            ]'''
            nodes = await core.nodes(text)

            self.propeq(nodes[0], 'status', 'settled')
            self.propeq(nodes[0], 'place:name', 'myhouse')
            self.propeq(nodes[0], 'place:latlong', (90, 80))
            self.propeq(nodes[0], 'place:loc', 'us.ny.brooklyn')
            self.propeq(nodes[0], 'place:address', '123 main street, brooklyn, ny, 11223')

            self.len(1, await core.nodes('econ:payment -> geo:place'))
            self.len(2, await core.nodes('econ:payment -> entity:contact | uniq'))

            self.len(1, await core.nodes('econ:payment :payee:account -> econ:account +:id=payeeacct'))
            self.len(1, await core.nodes('econ:payment :actor:account -> econ:account +:id=actoracct'))

            nodes = await core.nodes('''
                [ econ:exchange=(us,nasdaq)
                    :operator={ gen.org "nasdaq inc" }
                    :operator:name="nasdaq inc"
                    :currency=usd
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].ndef[1])
            self.nn(nodes[0].get('operator'))
            self.propeq(nodes[0], 'currency', 'USD')
            self.propeq(nodes[0], 'operator:name', 'nasdaq inc')

            nodes = await core.nodes('''
                [
                    econ:security=(us, nasdaq, tsla)
                        :exchange=(us, nasdaq) as econ:exchange
                        :ticker=nasdaq/tsla
                        :type=STOCK
                        :price=9999.00
                        :time=202002
                ]
            ''')

            self.len(1, nodes)
            self.eq('947183947f2e2c7bdc55264c20670f19', nodes[0].ndef[1])
            self.propeq(nodes[0], 'type', 'stock.')
            self.propeq(nodes[0], 'ticker', 'nasdaq/tsla')
            self.propeq(nodes[0], 'price', '9999')
            self.propeq(nodes[0], 'time', 1580515200000000)

            self.len(1, await core.nodes('econ:security -> econ:exchange +:operator:name="nasdaq inc"'))

            nodes = await core.nodes('''
                [
                    econ:security:telem=*
                        :time=20200202
                        :security=(us, nasdaq, tsla) as econ:security
                        :price=9999.00
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'time', 1580601600000000)
            self.propeq(nodes[0], 'security', '947183947f2e2c7bdc55264c20670f19')
            self.propeq(nodes[0], 'price', '9999')

            nodes = await core.nodes('''
                [
                    econ:security:ochlv=*
                        :period=(20200202, 20200203)
                        :security=(us, nasdaq, tsla) as econ:security
                        :change=(9999.00, 9999.01)
                        :range=(0.00001, 999999999999.00)
                        :volume=123456
                        :volume:delta=-789
                        :volume:delta:rate=-0.64
                        :previous={[ econ:security:ochlv=* :volume=124245 ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'period', (1580601600000000, 1580688000000000, 86400000000))
            self.propeq(nodes[0], 'security', '947183947f2e2c7bdc55264c20670f19')
            self.eq('9999', nodes[0].get('change.start'))
            self.eq('9999.01', nodes[0].get('change.end'))
            self.eq('0.00001', nodes[0].get('range.min'))
            self.eq('999999999999', nodes[0].get('range.max'))
            self.propeq(nodes[0], 'volume', '123456')
            self.propeq(nodes[0], 'volume:delta', '-789')
            self.propeq(nodes[0], 'volume:delta:rate', '-0.64')
            self.nn(nodes[0].get('previous'))
            self.len(1, await core.nodes('econ:security:ochlv:volume=123456 :previous -> econ:security:ochlv'))

            nodes = await core.nodes('''
                [ econ:balance=*
                    :time = 20211031
                    :account={[ econ:account=* ]}
                    :amount = 123.45
                    :change = (100.00, 123.45)
                    :previous={[ econ:balance=* :amount=100.00 ]}
                ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('account'))
            self.nn(nodes[0].get('previous'))
            self.propeq(nodes[0], 'time', 1635638400000000)
            self.propeq(nodes[0], 'amount', '123.45')
            self.eq('100', nodes[0].get('change.start'))
            self.eq('123.45', nodes[0].get('change.end'))
            self.eq('23.45', nodes[0].get('change.delta'))

            self.len(1, await core.nodes('econ:balance :account -> econ:account'))
            self.len(1, await core.nodes('econ:balance:amount=123.45 :previous -> econ:balance'))

            nodes = await core.nodes('''
                [ econ:lineitem=*
                    :count=10
                    :price=100
                    :item={[ biz:product=* :name=bananna ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'count', 10)
            self.propeq(nodes[0], 'price', '100')
            self.len(1, await core.nodes('econ:lineitem -> biz:product +:name=bananna'))

            # US-style: an econ:account for the funds plus an econ:bank:account
            # instrument carrying the (ABA RTN, account id) pair.
            nodes = await core.nodes('''
                [ econ:account=*
                    :type=checking
                    :holder={[ entity:contact=({"name": "us bank holder"}) ]}
                    :balance=500
                    :issuer={ gen.org "bank of visi" }
                    :issuer:name="bank of visi"
                    :id=1234
                ]
            ''')
            self.len(1, nodes)
            acct = nodes[0]
            self.nn(acct.get('issuer'))
            self.propeq(acct, 'type', 'checking.')
            self.propeq(acct, 'issuer:name', 'bank of visi')
            self.propeq(acct, 'balance', '500')
            self.propeq(acct, 'id', '1234')
            self.len(1, await core.nodes('econ:account -> ou:org'))
            self.len(1, await core.nodes('econ:account -> entity:name'))
            self.len(1, await core.nodes('econ:account -> econ:account:type:taxonomy'))

            # Routing identifier for the comp must be passed as a node /
            # NodeRef: the comp's routing field is poly-typed by the
            # econ:bank:routing:code interface, so raw routing strings are
            # rejected (no safe precedence between regex forms and the
            # base:id catch-all).
            q = f'''
                $rtn = {{ [ econ:bank:aba:rtn=123456789 ] }}
                [ econ:bank:account=($rtn, 1234) :account={acct.ndef[1]} as econ:account ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('econ:bank:account', (('econ:bank:aba:rtn', '123456789'), '1234')))
            self.eq(nodes[0].repr(), '123456789:1234')
            self.nn(nodes[0].get('account'))
            self.len(1, await core.nodes('econ:bank:aba:rtn=123456789'))
            self.len(1, await core.nodes('econ:bank:account :account -> econ:account'))

            # Raw routing-code strings are rejected on the comp field.
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ econ:bank:account=(987654321, 5678) ]')

            # IBAN as an econ:pay:instrument: lifts to its econ:account
            # via the :account property the interface provides.
            iban_acct = (await core.nodes('[ econ:account=* :type=savings ]'))[0]
            q = f'[ econ:bank:iban=GB82WEST12345698765432 :account={iban_acct.ndef[1]} as econ:account ]'
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.nn(nodes[0].get('account'))
            self.len(1, await core.nodes('econ:bank:iban -> econ:account'))

            # SWIFT-style route: pass the BIC node via NodeRef.
            swift_acct = (await core.nodes('[ econ:account=* ]'))[0]
            q = f'''
                $bic = {{ [ econ:bank:swift:bic=DEUTDEFF ] }}
                [ econ:bank:account=($bic, 987654321) :account={swift_acct.ndef[1]} as econ:account ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef, ('econ:bank:account', (('econ:bank:swift:bic', 'DEUTDEFF'), '987654321')))
            self.eq(nodes[0].repr(), 'DEUTDEFF:987654321')

            # Paired (routing, number) alts via multiple instruments on one
            # account. Use case: account survives a bank acquisition and is
            # reachable by multiple (routing, number) pairs.
            survivor = (await core.nodes('[ econ:account=* :type=checking ]'))[0]
            q = f'''
                $rtn = {{ [ econ:bank:aba:rtn=111000025 ] }}
                $bic = {{ [ econ:bank:swift:bic=DEUBDEFF ] }}
                [ econ:bank:account=($rtn, A100) :account={survivor.ndef[1]} as econ:account ]
                [ econ:bank:account=($bic, A100) :account={survivor.ndef[1]} as econ:account ]
            '''
            await core.nodes(q)
            q = f'econ:bank:account:account={survivor.ndef[1]}'
            self.len(2, await core.nodes(q))

            # Generic routing form for routing systems without a dedicated
            # form. The form extends base:id so its primary value is the
            # routing code itself; :type annotates which system it belongs
            # to. Pre-create the node and pass a NodeRef into the
            # account:id comp.
            q = '''
                $rt = { [ econ:bank:routing:id=401234 :type=sortcode ] }
                [ econ:bank:account=($rt, 12345) ]
            '''
            nodes = await core.nodes(q)
            self.len(1, nodes)
            self.eq(nodes[0].ndef[0], 'econ:bank:account')
            self.eq(nodes[0].ndef[1][0], ('econ:bank:routing:id', '401234'))
            self.eq(nodes[0].ndef[1][1], '12345')
            routing = (await core.nodes('econ:bank:routing:id=401234'))[0]
            self.propeq(routing, 'type', 'sortcode.')
            self.true(core.model.form('econ:bank:routing:id').implements('entity:identifier'))

            nodes = await core.nodes('''[
                econ:bank:swift:bic=DEUTDEFFXXX
                    :bank={ gen.org "Deutsche Bank" }
                    :office=* as entity:contact
            ]''')
            self.len(1, nodes)
            self.len(1, await core.nodes('econ:bank:swift:bic -> ou:org +:name="deutsche bank"'))
            self.len(1, await core.nodes('econ:bank:swift:bic -> entity:contact'))

            # econ:bank:check references the bank account it is drawn against
            # via :bank:account, reusing the econ:bank:account comp that pairs a
            # routing identifier with an account id. The funds account is linked
            # via the econ:pay:instrument :account property.
            check_acct = (await core.nodes('[ econ:account=* :type=checking ]'))[0]
            nodes = await core.nodes(f'''
                $rtn = {{ [ econ:bank:aba:rtn=021000021 ] }}
                [ econ:bank:check=*
                    :payto="jane doe"
                    :amount=250
                    :bank:account=($rtn, 556677)
                    :account={check_acct.ndef[1]} as econ:account
                ]
            ''')
            self.len(1, nodes)
            chk = nodes[0]
            self.propeq(chk, 'payto', 'jane doe')
            self.propeq(chk, 'amount', '250')
            self.nn(chk.get('bank:account'))
            self.nn(chk.get('account'))
            self.len(1, await core.nodes('econ:bank:check :bank:account -> econ:bank:account'))
            self.len(1, await core.nodes('econ:bank:check :bank:account -> econ:bank:account :routing -> econ:bank:aba:rtn'))
            self.len(1, await core.nodes('econ:bank:check :account -> econ:account'))

            # Non-US check: the econ:bank:account comp accepts a SWIFT BIC (and,
            # via econ:bank:routing:id, sort codes / IFSC / etc.) that the old
            # econ:bank:aba:rtn routing typing on the check could not hold.
            nodes = await core.nodes('''
                $bic = { [ econ:bank:swift:bic=BARCGB22 ] }
                [ econ:bank:check=*
                    :payto="john smith"
                    :amount=80
                    :bank:account=($bic, 12345678)
                ]
            ''')
            self.len(1, nodes)
            self.len(1, await core.nodes('econ:bank:check :bank:account -> econ:bank:account :routing -> econ:bank:swift:bic'))

            nodes = await core.nodes('''[
                econ:statement=*
                    :period=202403*
                    :account={econ:account | limit 1}
                    :balance=999
                    :previous={[ econ:statement=* ]}
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('account'))
            self.nn(nodes[0].get('previous'))
            self.propeq(nodes[0], 'balance', '999')
            self.propeq(nodes[0], 'period', (1709251200000000, 1709251200000001, 1))
            self.len(1, await core.nodes('econ:statement:balance=999 :previous -> econ:statement'))

            nodes = await core.nodes('''[
                econ:bank:aba:rtn=123456789
                    :bank={ gen.org "deutsche bank" }
                    :bank:name="deutsche bank"
            ]''')
            self.len(1, nodes)
            self.len(1, await core.nodes('econ:bank:aba:rtn=123456789 -> entity:name'))
            self.len(1, await core.nodes('econ:bank:aba:rtn=123456789 -> ou:org +:name="deutsche bank"'))

            nodes = await core.nodes('''[
                econ:receipt=*
                    :amount=99
                    :purchase=* as econ:purchase
                    :issued=2024-03-19
                    :issuer={[ entity:contact=({"name": "visi"}) ]}
                    :recipient={[ entity:contact=({"name": "visi"}) ]}
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'amount', '99')
            self.propeq(nodes[0], 'issued', 1710806400000000)
            self.len(1, await core.nodes('econ:receipt -> econ:purchase'))
            self.len(1, await core.nodes('econ:receipt :issuer -> entity:contact'))
            self.len(1, await core.nodes('econ:receipt :recipient -> entity:contact'))

            nodes = await core.nodes('''[
                econ:invoice=*
                    :paid=(false)
                    :amount=99
                    :purchase=* as econ:purchase
                    :due=2024-03-19
                    :issued=2024-03-19
                    :issuer={ entity:contact:name=visi }
                    :recipient={ entity:contact:name=visi }
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'amount', '99')
            self.propeq(nodes[0], 'paid', 0)
            self.propeq(nodes[0], 'due', 1710806400000000)
            self.propeq(nodes[0], 'issued', 1710806400000000)
            self.len(1, await core.nodes('econ:invoice -> econ:purchase'))
            self.len(1, await core.nodes('econ:invoice :issuer -> entity:contact'))
            self.len(1, await core.nodes('econ:invoice :recipient -> entity:contact'))

            nodes = await core.nodes('''[
                econ:budget=*
                    :id=FY24-MKTG
                    :name="FY24 Marketing"
                    :period=(2024, 2025)
                    :actor={ gen.org "budget owner" }
                    :funds=(5000, 1000)
                    :previous={[ econ:budget=* :name="FY23 Marketing" ]}
            ]''')
            self.len(1, nodes)
            budget = nodes[0]
            self.propeq(budget, 'id', 'FY24-MKTG')
            self.propeq(budget, 'name', 'FY24 Marketing')
            self.propeq(budget, 'period', (1704067200000000, 1735689600000000, 31622400000000))
            self.eq('5000', budget.get('funds.allocated'))
            self.eq('1000', budget.get('funds.spent'))
            self.eq('-4000', budget.get('funds.variance'))
            self.eq('-80', budget.get('funds.rate'))
            self.nn(budget.get('actor'))
            self.nn(budget.get('previous'))
            self.len(1, await core.nodes('econ:budget:name="FY24 Marketing" :actor -> ou:org'))
            self.len(1, await core.nodes('econ:budget:name="FY24 Marketing" :previous -> econ:budget +:name="FY23 Marketing"'))

            props = budget.getProps(virts=True)
            self.eq(props.get('funds.type'), 'econ:allocation')
            self.eq(props.get('funds.allocated'), '5000')
            self.eq(props.get('funds.spent'), '1000')
            self.eq(props.get('funds.variance'), '-4000')
            self.eq(props.get('funds.rate'), '-80')

            # econ:allocation renamed virts (allocated/spent/variance) are liftable
            self.len(1, await core.nodes('econ:budget:funds.allocated=5000'))
            self.len(1, await core.nodes('econ:budget:funds.spent=1000'))
            self.len(1, await core.nodes('econ:budget:name="FY24 Marketing" +:funds.variance<0'))
            self.len(0, await core.nodes('econ:budget:name="FY24 Marketing" +:funds.variance>0'))

            # econ:budget -(had)> econ:purchase edge
            await core.nodes('''
                econ:budget:name="FY24 Marketing"
                [ +(had)> {[ econ:purchase=(fy24, spend) ]} ]
            ''')
            self.len(1, await core.nodes('econ:budget:name="FY24 Marketing" -(had)> econ:purchase'))

            # econ:budgetable interface: :budget on implementing forms
            for form in ('entity:campaign', 'ou:org', 'proj:project', 'ou:event', 'ou:conference', 'ou:contest'):
                nodes = await core.nodes(f'[ {form}=* :budget={{ econ:budget:name="FY24 Marketing" }} ]')
                self.len(1, nodes)
                self.nn(nodes[0].get('budget'))
                self.len(1, await core.nodes(f'{form} :budget -> econ:budget +:name="FY24 Marketing"'))

    async def test_model_econ_price_virts(self):

        async with self.getTestCore() as core:

            # the econ:price:adjusted form holds the adjusted outputs
            nodes = await core.nodes('''[
                econ:price:adjusted=*
                    :value=20.00
                    :time=2024
                    :currency=USD
            ]''')
            self.len(1, nodes)
            adj = nodes[0].ndef[1]
            self.propeq(nodes[0], 'value', '20')
            self.propeq(nodes[0], 'time', 1704067200000000)
            self.propeq(nodes[0], 'currency', 'USD')

            # set the adjusted virt on a price referencing the adjusted node
            opts = {'vars': {'adj': adj}}
            nodes = await core.nodes('[ econ:purchase=* :price=13.37 :price.adjusted=$adj ]', opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'price', '13.37')
            self.propeq(nodes[0], 'price.adjusted', adj)

            # pivot from the virt to the adjusted node
            self.len(1, await core.nodes('econ:purchase:price=13.37 :price.adjusted -> econ:price:adjusted'))

            # lift by the adjusted virt
            self.len(1, await core.nodes('econ:purchase:price.adjusted=$adj', opts=opts))

            # filter by the adjusted virt
            self.len(1, await core.nodes('econ:purchase +:price.adjusted=$adj', opts=opts))

            # backward compat: price without the virt still works
            nodes = await core.nodes('[ econ:purchase=* :price=99.99 ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'price', '99.99')
            self.none(nodes[0].get('price.adjusted'))

            # price comparisons still work with the virt set
            self.len(1, await core.nodes('econ:purchase:price=13.37 +:price>10'))
            self.len(1, await core.nodes('econ:purchase:price=13.37 +:price<20'))

            # the adjusted virt may be assigned via a gutor: the embedded dict
            # deconflicts/creates the econ:price:adjusted node and populates it.
            nodes = await core.nodes('''[
                econ:purchase=*
                    :price=88.00
                    :price.adjusted=({"value": "90.00", "time": "2025", "currency": "USD"})
            ]''')
            self.len(1, nodes)
            gutoradj = nodes[0].get('price.adjusted')
            self.nn(gutoradj)
            adjnodes = await core.nodes('econ:price:adjusted=$g', opts={'vars': {'g': gutoradj}})
            self.len(1, adjnodes)
            self.propeq(adjnodes[0], 'value', '90')
            self.propeq(adjnodes[0], 'time', 1735689600000000)
            self.propeq(adjnodes[0], 'currency', 'USD')

            # error: setting the virt on an unset price
            nodes = await core.nodes('[ econ:purchase=* ]')
            opts = {'vars': {'guid': nodes[0].ndef[1], 'adj': adj}}
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('econ:purchase=$guid [ :price.adjusted=$adj ]', opts=opts)

            # the restored currency virt works alongside the adjusted virt
            nodes = await core.nodes('[ econ:purchase=* :price=42.00 :price.currency=USD :price.adjusted=$adj ]', opts=opts)
            self.len(1, nodes)
            self.propeq(nodes[0], 'price.currency', 'USD')
            self.propeq(nodes[0], 'price.adjusted', adj)

            # the currency virt type is the econ:currency form, so setting it
            # automatically creates the econ:currency node.
            self.len(1, await core.nodes('econ:currency=usd'))

            # lift and filter by the currency virt
            self.len(1, await core.nodes('econ:purchase:price.currency=usd'))
            self.len(1, await core.nodes('econ:purchase:price=42.00 +:price.currency=usd'))

            # error: setting the currency virt on an unset price
            nodes = await core.nodes('[ econ:purchase=* ]')
            opts = {'vars': {'guid': nodes[0].ndef[1]}}
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('econ:purchase=$guid [ :price.currency=usd ]', opts=opts)

            # a trailing currency code on the price string is captured
            nodes = await core.nodes('[ econ:purchase=* :price=99USD ]')
            self.len(1, nodes)
            self.propeq(nodes[0], 'price', '99')
            self.propeq(nodes[0], 'price.currency', 'USD')
            self.eq('99USD', nodes[0].repr('price'))
            self.eq('99USD', nodes[0].pack(dorepr=True)[1]['reprs']['price'])

            # lower-case input is stored upper-case and reprs the same
            nodes = await core.nodes('[ econ:purchase=* :price=99usd ]')
            self.propeq(nodes[0], 'price.currency', 'USD')
            self.eq('99USD', nodes[0].repr('price'))

            # a bare number captures no currency and reprs the plain value
            nodes = await core.nodes('[ econ:purchase=* :price=99 ]')
            self.none(nodes[0].get('price.currency'))
            self.eq('99', nodes[0].repr('price'))
            self.notin('price', nodes[0].pack(dorepr=True)[1].get('reprs', {}))

            # common currency symbols are mapped to ISO 4217 codes
            curr = core.model.type('econ:currency')
            self.eq('USD', (await curr.norm('$'))[0])
            self.eq('EUR', (await curr.norm('€'))[0])
            self.eq('GBP', (await curr.norm('£'))[0])
            self.eq('USD', (await curr.norm('usd'))[0])

            nodes = await core.nodes("[ econ:purchase=* :price=5 :price.currency='$' ]")
            self.propeq(nodes[0], 'price.currency', 'USD')
            # lifting by the symbol maps to USD and matches the same nodes
            self.eq(
                len(await core.nodes("econ:purchase:price.currency='$'")),
                len(await core.nodes('econ:purchase:price.currency=usd')),
            )

            # a prefix (^=) storage LIFT on an econ:currency-typed prop maps the
            # symbol through the mapping option before the prefix match
            nodes = await core.nodes("[ crypto:currency:chain=(btc,) :symbol='$' ]")
            self.propeq(nodes[0], 'symbol', 'USD')
            self.len(1, await core.nodes("crypto:currency:chain:symbol^='$'"))
            self.len(1, await core.nodes("crypto:currency:chain:symbol^=usd"))

            # --- gutor-dict virtual prop keys ---
            # price.currency in the deconfliction dict.
            nodes_g0 = await core.nodes('[ biz:listing=({"name": "widget", "price": "10", "price.currency": "usd"}) ]')
            self.len(1, nodes_g0)
            self.propeq(nodes_g0[0], 'price', '10')
            self.propeq(nodes_g0[0], 'price.currency', 'USD')

            # Same dict deconflicts to the same node.
            nodes_g1 = await core.nodes('[ biz:listing=({"name": "widget", "price": "10", "price.currency": "usd"}) ]')
            self.len(1, nodes_g1)
            self.eq(nodes_g0[0].ndef, nodes_g1[0].ndef)

            # Different price produces a different node (base value participates in guid).
            nodes_g2 = await core.nodes('[ biz:listing=({"name": "widget", "price": "20", "price.currency": "usd"}) ]')
            self.len(1, nodes_g2)
            self.ne(nodes_g0[0].ndef, nodes_g2[0].ndef)

            # econ:price.currency is virt metadata, not the value itself, so it does
            # NOT affect the deconfliction guid; only the numeric value does.
            # Two dicts with the same numeric price but different currencies resolve to
            # the same node.  Because the node already exists, deconf props are NOT
            # re-applied (only $props are), so the currency stays as originally set.
            nodes_g3 = await core.nodes('[ biz:listing=({"name": "widget", "price": "10", "price.currency": "eur"}) ]')
            self.len(1, nodes_g3)
            self.eq(nodes_g0[0].ndef, nodes_g3[0].ndef)  # same node, deconf not re-applied
            self.propeq(nodes_g3[0], 'price.currency', 'USD')  # original value preserved

            # price.currency in $props: applied to the node, does not affect the guid.
            nodes_g4 = await core.nodes('[ biz:listing=({"name": "gtor-props", "price": "5"}) ]')
            nodes_g5 = await core.nodes('[ biz:listing=({"name": "gtor-props", "price": "5", "$props": {"price.currency": "USD"}}) ]')
            self.len(1, nodes_g4)
            self.len(1, nodes_g5)
            self.eq(nodes_g4[0].ndef, nodes_g5[0].ndef)
            self.propeq(nodes_g5[0], 'price.currency', 'USD')

            # econ:purchase with price.currency in the gutor deconf dict
            nodes_g6 = await core.nodes('[ econ:purchase=({"price": "25", "price.currency": "usd"}) ]')
            self.len(1, nodes_g6)
            self.propeq(nodes_g6[0], 'price', '25')
            self.propeq(nodes_g6[0], 'price.currency', 'USD')

    async def test_model_econ_pricerange(self):

        async with self.getTestCore() as core:

            # side-index lifts before any range is stored hit the NoSuchAbrv
            # guard in indxByProp and return nothing
            self.len(0, await core.nodes('econ:security:ochlv:range.max=5'))
            self.len(0, await core.nodes('econ:security:ochlv:range.delta>0'))
            self.len(0, await core.nodes('econ:security:ochlv:range=(1, 2)'))

            nodes = await core.nodes('''[
                econ:security:ochlv=*
                    :range=(1.50, 2.20)
                    :range.currency=usd
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'range', ('1.5', '2.2', '0.7'))
            self.eq('1.5', nodes[0].get('range.min'))
            self.eq('2.2', nodes[0].get('range.max'))
            self.eq('0.7', nodes[0].get('range.delta'))
            self.eq('USD', nodes[0].get('range.currency'))

            # set each virt independently and assert siblings recompute
            nodes = await core.nodes('econ:security:ochlv:range.min=1.5 [ :range.max=3.0 ]')
            self.eq('1.5', nodes[0].get('range.min'))
            self.eq('3', nodes[0].get('range.max'))
            self.eq('1.5', nodes[0].get('range.delta'))

            props = nodes[0].getProps(virts=True)
            self.eq(props.get('range.min'), '1.5')
            self.eq(props.get('range.max'), '3')
            self.eq(props.get('range.delta'), '1.5')

            # build a range from parts, then partial-capture with sentinel
            await core.nodes('''[
                (econ:security:ochlv=(p1,) :range=(10, 20))
                (econ:security:ochlv=(p2,) :range=(15, 35))
                (econ:security:ochlv=(p3,) :range=(40, 41))
            ]''')

            # ordered range lifts on .min (primary index prefix)
            self.len(2, await core.nodes('econ:security:ochlv:range.min>=15'))
            self.len(2, await core.nodes('econ:security:ochlv:range.min<15'))
            self.len(3, await core.nodes('econ:security:ochlv +:range.min<=15'))

            # ordered range lifts on derived/second fields (side index DBs)
            self.len(1, await core.nodes('econ:security:ochlv +:range.max>35'))
            self.len(2, await core.nodes('econ:security:ochlv +:range.delta>5'))
            self.len(1, await core.nodes('econ:security:ochlv +:range.delta=1'))
            self.len(4, await core.nodes('econ:security:ochlv +:range.delta>0'))

            # bare storage LIFTs (exercise the StorTypePriceRange lifters and
            # the max/delta side-index DBs, not the runtime cmpr). the four
            # ranges at this point are (1.5,3,1.5) (10,20,10) (15,35,20) (40,41,1)
            self.len(1, await core.nodes('econ:security:ochlv:range.max>=41'))
            self.len(1, await core.nodes('econ:security:ochlv:range.max>40'))
            self.len(1, await core.nodes('econ:security:ochlv:range.max<=3'))
            self.len(1, await core.nodes('econ:security:ochlv:range.max<20'))
            self.len(1, await core.nodes('econ:security:ochlv:range.max=20'))
            self.len(1, await core.nodes('econ:security:ochlv:range.delta=1'))
            self.len(2, await core.nodes('econ:security:ochlv:range.delta<2'))
            self.len(1, await core.nodes('econ:security:ochlv:range.delta>14'))
            self.len(2, await core.nodes('econ:security:ochlv:range.delta>=10'))
            self.len(2, await core.nodes('econ:security:ochlv:range.delta<=1.5'))

            # bare exact-range LIFT (StorTypePriceRange._liftEq)
            self.len(1, await core.nodes('econ:security:ochlv:range=(10, 20)'))
            self.len(1, await core.nodes('econ:security:ochlv:range=(1.5, 3.0)'))

            # bare min LIFTs incl. the > (Gt -> Ge) path
            self.len(2, await core.nodes('econ:security:ochlv:range.min>14'))
            self.len(1, await core.nodes('econ:security:ochlv:range.min=40'))

            # .currency lift and filter
            self.len(1, await core.nodes('econ:security:ochlv:range.currency=usd'))
            self.len(1, await core.nodes('econ:security:ochlv:range.min=1.5 +:range.currency=usd'))

            # a trailing currency code on the range string is captured
            nodes = await core.nodes('[ econ:security:ochlv=(cur,) :range=32-99USD ]')
            self.len(1, nodes)
            self.eq('32', nodes[0].get('range.min'))
            self.eq('99', nodes[0].get('range.max'))
            self.eq('USD', nodes[0].get('range.currency'))
            self.eq('32-99USD', nodes[0].repr('range'))
            self.eq('32-99USD', nodes[0].pack(dorepr=True)[1]['reprs']['range'])

            # sentinel round-trip then completion
            nodes = await core.nodes('[ econ:security:ochlv=(unk,) :range=(?, ?) :range.delta=5 ]')
            self.propeq(nodes[0], 'range', ('?', '?', '5'))
            self.none(nodes[0].get('range.min'))
            self.none(nodes[0].get('range.max'))
            self.eq('5', nodes[0].get('range.delta'))

            nodes = await core.nodes('econ:security:ochlv=(unk,) [ :range.min=10 ]')
            self.propeq(nodes[0], 'range', ('10', '15', '5'))

            # sentinel-bearing nodes are excluded from ordered .min lifts:
            # adding a fully-unknown range must not change the .min>=0 count.
            before = await core.count('econ:security:ochlv:range.min>=0')
            await core.nodes('[ econ:security:ochlv=(sentonly,) :range=(?, ?) ]')
            self.eq(before, await core.count('econ:security:ochlv:range.min>=0'))

            # repr includes the sentinel
            nodes = await core.nodes('[ econ:security:ochlv=(rep,) :range=(?, 9) ]')
            self.eq(('?', '9'), core.model.type('econ:pricerange').repr(nodes[0].get('range')[1]))

            # deleting the prop tears down the side-index DBs (max/delta); after
            # the delete a max lift no longer returns the node.
            await core.nodes('[ econ:security:ochlv=(del,) :range=(50, 60) ]')
            self.len(1, await core.nodes('econ:security:ochlv:range.max=60'))
            await core.nodes('econ:security:ochlv=(del,) [ -:range ]')
            self.len(0, await core.nodes('econ:security:ochlv:range.max=60'))
            self.none((await core.nodes('econ:security:ochlv=(del,)'))[0].get('range'))

            # errors
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ econ:security:ochlv=* :range=(5, 2) ]')

            with self.raises(s_exc.BadTypeValu):
                await core.nodes('econ:security:ochlv:range.min=1.5 [ :range.delta=2 ]')

    async def test_model_econ_pricechange(self):

        async with self.getTestCore() as core:

            # side-index lifts before any change is stored hit the NoSuchAbrv
            # guard in indxByProp and return nothing
            self.len(0, await core.nodes('econ:balance:change.end=5'))
            self.len(0, await core.nodes('econ:balance:change.rate>0'))

            nodes = await core.nodes('''[
                econ:balance=*
                    :amount=130.00
                    :change=(100.00, 130.00)
                    :change.currency=usd
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'amount', '130')
            self.propeq(nodes[0], 'change', ('100', '130', '30', '30'))
            self.eq('100', nodes[0].get('change.start'))
            self.eq('130', nodes[0].get('change.end'))
            self.eq('30', nodes[0].get('change.delta'))
            self.eq('30', nodes[0].get('change.rate'))
            self.eq('USD', nodes[0].get('change.currency'))

            # negative delta + rate
            nodes = await core.nodes('[ econ:balance=(neg,) :change=(100, 75) ]')
            self.propeq(nodes[0], 'change', ('100', '75', '-25', '-25'))

            # set start then end recomputes delta and rate
            nodes = await core.nodes('[ econ:balance=(parts,) :change.start=200 ]')
            self.eq('200', nodes[0].get('change.start'))
            self.none(nodes[0].get('change.end'))
            nodes = await core.nodes('econ:balance=(parts,) [ :change.end=250 ]')
            self.eq('250', nodes[0].get('change.end'))
            self.eq('50', nodes[0].get('change.delta'))
            self.eq('25', nodes[0].get('change.rate'))

            # settable rate derives the unknown endpoint
            nodes = await core.nodes('[ econ:balance=(rate,) :change.start=100 :change.rate=20 ]')
            self.propeq(nodes[0], 'change', ('100', '120', '20', '20'))

            # settable signed delta derives the unknown endpoint
            nodes = await core.nodes('[ econ:balance=(sd,) :change.start=100 :change.delta=-40 ]')
            self.propeq(nodes[0], 'change', ('100', '60', '-40', '-40'))

            await core.nodes('''[
                (econ:balance=(c1,) :change=(100, 110))
                (econ:balance=(c2,) :change=(100, 90))
                (econ:balance=(c3,) :change=(100, 100))
            ]''')

            # ordered range lifts incl. negative rate / delta
            self.len(3, await core.nodes('econ:balance +:change.rate<0'))
            self.len(4, await core.nodes('econ:balance +:change.rate>0'))
            self.len(3, await core.nodes('econ:balance:change.delta<0'))
            self.len(4, await core.nodes('econ:balance +:change.end>105'))
            self.len(7, await core.nodes('econ:balance:change.start>=100 +:change.start<=100'))

            # bare storage LIFTs (exercise StorTypePriceRange side-index DBs for
            # end/delta/rate and the rate lifter, not the runtime cmpr). the
            # eight changes are: (100,130,30,30) (100,75,-25,-25) (200,250,50,25)
            # (100,120,20,20) (100,60,-40,-40) (100,110,10,10) (100,90,-10,-10)
            # (100,100,0,0)
            self.len(1, await core.nodes('econ:balance:change.end>=250'))
            self.len(1, await core.nodes('econ:balance:change.end>130'))
            self.len(1, await core.nodes('econ:balance:change.end<=60'))
            self.len(1, await core.nodes('econ:balance:change.end<75'))
            self.len(1, await core.nodes('econ:balance:change.end=120'))
            self.len(1, await core.nodes('econ:balance:change.delta=30'))
            self.len(3, await core.nodes('econ:balance:change.delta<0'))
            self.len(1, await core.nodes('econ:balance:change.delta>40'))
            self.len(1, await core.nodes('econ:balance:change.delta>=50'))
            self.len(3, await core.nodes('econ:balance:change.delta<=-10'))
            self.len(3, await core.nodes('econ:balance:change.rate<0'))
            self.len(4, await core.nodes('econ:balance:change.rate>0'))
            self.len(1, await core.nodes('econ:balance:change.rate>=30'))
            self.len(1, await core.nodes('econ:balance:change.rate<=-40'))
            self.len(1, await core.nodes('econ:balance:change.rate<-39'))
            self.len(1, await core.nodes('econ:balance:change.rate=30'))

            # bare exact-range LIFT and start lifts
            self.len(1, await core.nodes('econ:balance:change=(200, 250)'))
            self.len(1, await core.nodes('econ:balance:change.start>=200'))
            self.len(1, await core.nodes('econ:balance:change.start>150'))
            self.len(7, await core.nodes('econ:balance:change.start<=100'))
            self.len(7, await core.nodes('econ:balance:change.start<150'))

            # .currency lift / filter
            self.len(1, await core.nodes('econ:balance:change.currency=usd'))
            self.len(1, await core.nodes('econ:balance:change.start=100 +:change.currency=usd'))

            # a trailing currency code on the change string is captured
            nodes = await core.nodes('[ econ:balance=(cur,) :change=99-32USD ]')
            self.len(1, nodes)
            self.eq('99', nodes[0].get('change.start'))
            self.eq('32', nodes[0].get('change.end'))
            self.eq('USD', nodes[0].get('change.currency'))
            self.eq('99-32USD', nodes[0].repr('change'))
            self.eq('99-32USD', nodes[0].pack(dorepr=True)[1]['reprs']['change'])

            # a negative endpoint still works via a (start, end) tuple
            nodes = await core.nodes('[ econ:balance=(negtup,) :change=(100, 75) ]')
            self.eq('-25', nodes[0].get('change.delta'))

            # sentinel round-trip
            nodes = await core.nodes('[ econ:balance=(unk,) :change=(?, ?) :change.delta=5 ]')
            self.propeq(nodes[0], 'change', ('?', '?', '5', '?'))
            self.none(nodes[0].get('change.start'))
            self.eq('5', nodes[0].get('change.delta'))

            # the "start-end" string form is accepted
            nodes = await core.nodes('[ econ:balance=(strform,) :change="100-130" ]')
            self.eq('100', nodes[0].get('change.start'))
            self.eq('130', nodes[0].get('change.end'))

            # deleting the prop tears down the side-index DBs (end/delta/rate);
            # after the delete an end lift no longer returns the node.
            await core.nodes('[ econ:balance=(del,) :change=(300, 360) ]')
            self.len(1, await core.nodes('econ:balance:change.end=360'))
            await core.nodes('econ:balance=(del,) [ -:change ]')
            self.len(0, await core.nodes('econ:balance:change.end=360'))
            self.none((await core.nodes('econ:balance=(del,)'))[0].get('change'))

            # a negative endpoint can not be expressed as a string
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('[ econ:balance=* :change="-25-100" ]')

            # over-constraint error
            with self.raises(s_exc.BadTypeValu):
                await core.nodes('econ:balance:change.start=200 [ :change.rate=5 ]')
