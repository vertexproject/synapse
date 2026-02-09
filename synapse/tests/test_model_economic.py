import synapse.exc as s_exc
import synapse.tests.utils as s_utils

import synapse.common as s_common

class EconTest(s_utils.SynTest):

    async def test_model_econ(self):

        async with self.getTestCore() as core:

            # test card number 4024007150779444
            card = (await core.nodes('[ econ:pay:card="*" :expr=201802 :name="Bob Smith" :cvv=123 :pin=1234 :pan=4024007150779444 ]'))[0]
            self.propeq(card, 'name', 'bob smith')
            self.propeq(card, 'expr', 1517443200000000)
            self.propeq(card, 'pan', '4024007150779444')
            self.propeq(card, 'pan:mii', 4)
            self.propeq(card, 'pan:iin', 402400)

            text = '''[
                econ:purchase="*"

                    :price=13.37
                    :currency=USD
                    :buyer={[ entity:contact=* ]}
                    :seller={[ entity:contact=* ]}

                    :time=20180202

                    :place=*
                    :place:loc=us.ny.brooklyn

                    :paid=true
                    :paid:time=20180202
            ]'''

            perc = (await core.nodes(text))[0]

            self.propeq(perc, 'price', '13.37')
            self.propeq(perc, 'currency', 'usd')

            self.len(1, await core.nodes('econ:purchase :buyer -> entity:contact'))
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

            self.propeq(perc, 'paid', True)
            self.propeq(perc, 'paid:time', 1517529600000000)

            self.propeq(perc, 'place:loc', 'us.ny.brooklyn')

            self.len(1, await core.nodes('econ:purchase -> geo:place'))
            self.len(2, await core.nodes('econ:purchase -> entity:contact | uniq'))

            text = '''[
                econ:payment=*

                    :payee={[ entity:contact=* :name=payee ]}
                    :payer={[ entity:contact=* :name=payer ]}

                    :status=settled
                    :amount = 20.30
                    :currency = usd

                    :time=20180202

                    :place=*
                    :place:loc=us.ny.brooklyn
                    :place:name=myhouse
                    :place:address="123 main street, brooklyn, ny, 11223"
                    :place:latlong=(90,80)
            ]'''
            nodes = await core.nodes(text)

            self.propeq(nodes[0], 'status', 'settled')
            self.propeq(nodes[0], 'place:name', 'myhouse')
            self.eq((90, 80), nodes[0].get('place:latlong'))
            self.propeq(nodes[0], 'place:loc', 'us.ny.brooklyn')
            self.propeq(nodes[0], 'place:address', '123 main street, brooklyn, ny, 11223')

            self.len(1, await core.nodes('econ:payment -> geo:place'))
            self.len(2, await core.nodes('econ:payment -> entity:contact | uniq'))

            nodes = await core.nodes('''
                [ econ:fin:exchange=(us,nasdaq) :name=nasdaq :currency=usd :org=* ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].ndef[1])
            self.nn(nodes[0].get('org'))
            self.propeq(nodes[0], 'currency', 'usd')
            self.propeq(nodes[0], 'name', 'nasdaq')

            nodes = await core.nodes('''
                [
                    econ:fin:security=(us, nasdaq, tsla)
                        :exchange=(us, nasdaq)
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

            self.len(1, await core.nodes('econ:fin:security -> econ:fin:exchange +:name=nasdaq'))

            nodes = await core.nodes('''
                [
                    econ:fin:tick=*
                        :time=20200202
                        :security=(us, nasdaq, tsla)
                        :price=9999.00
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'time', 1580601600000000)
            self.propeq(nodes[0], 'security', '947183947f2e2c7bdc55264c20670f19')
            self.propeq(nodes[0], 'price', '9999')

            nodes = await core.nodes('''
                [
                    econ:fin:bar=*
                        :period=(20200202, 20200203)
                        :security=(us, nasdaq, tsla)
                        :price:open=9999.00
                        :price:close=9999.01
                        :price:high=999999999999.00
                        :price:low=0.00001
                ]
            ''')
            self.len(1, nodes)
            self.eq((1580601600000000, 1580688000000000, 86400000000), nodes[0].get('period'))
            self.propeq(nodes[0], 'security', '947183947f2e2c7bdc55264c20670f19')
            self.propeq(nodes[0], 'price:open', '9999')
            self.propeq(nodes[0], 'price:close', '9999.01')
            self.propeq(nodes[0], 'price:high', '999999999999')
            self.propeq(nodes[0], 'price:low', '0.00001')

            nodes = await core.nodes('''
                [ econ:balance=*
                    :time = 20211031
                    :account={[ econ:fin:account=* ]}
                    :amount = 123.45
                    :currency = usd
                ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('account'))
            self.propeq(nodes[0], 'time', 1635638400000000)
            self.propeq(nodes[0], 'amount', '123.45')
            self.propeq(nodes[0], 'currency', 'usd')

            self.eq('usd', await core.callStorm('econ:balance return($node.protocol(econ:adjustable, propname=amount).vars.currency)'))

            self.len(1, await core.nodes('econ:balance :account -> econ:fin:account'))

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

            nodes = await core.nodes('''
                [ econ:bank:aba:account=*
                    :type=checking
                    :number=1234
                    :routing=123456789
                    :issuer={ gen.ou.org "bank of visi" }
                    :issuer:name="bank of visi"
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('issuer'))
            self.propeq(nodes[0], 'number', '1234')
            self.propeq(nodes[0], 'type', 'checking.')
            self.propeq(nodes[0], 'issuer:name', 'bank of visi')
            self.len(1, await core.nodes('econ:bank:aba:account -> ou:org'))
            self.len(1, await core.nodes('econ:bank:aba:account -> entity:name'))
            self.len(1, await core.nodes('econ:bank:aba:account -> econ:bank:aba:rtn'))
            self.len(1, await core.nodes('econ:bank:aba:account -> econ:bank:aba:account:type:taxonomy'))

            nodes = await core.nodes('''[
                econ:bank:swift:bic=DEUTDEFFXXX
                    :business={ gen.ou.org "Deutsche Bank" }
                    :office=*
            ]''')
            self.len(1, nodes)
            self.len(1, await core.nodes('econ:bank:swift:bic -> ou:org +:name="deutsche bank"'))
            self.len(1, await core.nodes('econ:bank:swift:bic -> geo:place'))

            nodes = await core.nodes('''[
                econ:statement=*
                    :period=202403*
                    :account={econ:fin:account | limit 1}
                    :currency=usd
                    :starting:balance=99
                    :ending:balance=999
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('account'))
            self.propeq(nodes[0], 'currency', 'usd')
            self.propeq(nodes[0], 'starting:balance', '99')
            self.propeq(nodes[0], 'ending:balance', '999')
            self.eq((1709251200000000, 1709251200000001, 1), nodes[0].get('period'))

            self.len(2, nodes[0].protocols())
            self.len(0, nodes[0].protocols(name='newp:newp'))
            self.len(2, nodes[0].protocols(name='econ:adjustable'))

            proto = nodes[0].protocol('econ:adjustable', propname='starting:balance')
            self.eq(proto['vars']['currency'], 'usd')

            nodes = await core.nodes('''[
                econ:bank:aba:rtn=123456789
                    :bank={ gen.ou.org "deutsche bank" }
                    :bank:name="deutsche bank"
            ]''')
            self.len(1, nodes)
            self.len(1, await core.nodes('econ:bank:aba:rtn=123456789 -> entity:name'))
            self.len(1, await core.nodes('econ:bank:aba:rtn=123456789 -> ou:org +:name="deutsche bank"'))

            nodes = await core.nodes('''[
                econ:receipt=*
                    :amount=99
                    :currency=usd
                    :purchase=*
                    :issued=2024-03-19
                    :issuer={[ entity:contact=({"name": "visi"}) ]}
                    :recipient={[ entity:contact=({"name": "visi"}) ]}
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'amount', '99')
            self.propeq(nodes[0], 'currency', 'usd')
            self.propeq(nodes[0], 'issued', 1710806400000000)
            self.len(1, await core.nodes('econ:receipt -> econ:purchase'))
            self.len(1, await core.nodes('econ:receipt :issuer -> entity:contact'))
            self.len(1, await core.nodes('econ:receipt :recipient -> entity:contact'))

            nodes = await core.nodes('''[
                econ:invoice=*
                    :paid=(false)
                    :amount=99
                    :currency=usd
                    :purchase=*
                    :due=2024-03-19
                    :issued=2024-03-19
                    :issuer={ entity:contact:name=visi }
                    :recipient={ entity:contact:name=visi }
            ]''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'amount', '99')
            self.propeq(nodes[0], 'currency', 'usd')
            self.propeq(nodes[0], 'paid', 0)
            self.propeq(nodes[0], 'due', 1710806400000000)
            self.propeq(nodes[0], 'issued', 1710806400000000)
            self.len(1, await core.nodes('econ:invoice -> econ:purchase'))
            self.len(1, await core.nodes('econ:invoice :issuer -> entity:contact'))
            self.len(1, await core.nodes('econ:invoice :recipient -> entity:contact'))
