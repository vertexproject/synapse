import synapse.exc as s_exc
import synapse.tests.utils as s_utils

import synapse.common as s_common

class EconTest(s_utils.SynTest):

    async def test_model_econ(self):

        async with self.getTestCore() as core:

            # test card number 4024007150779444
            card = (await core.nodes('[ econ:pay:card="*" :expr=201802 :name="Bob Smith" :cvv=123 :pin=1234 :pan=4024007150779444 ]'))[0]
            self.eq('bob smith', card.get('name'))
            self.eq(1517443200000000, card.get('expr'))
            self.eq('4024007150779444', card.get('pan'))
            self.eq(4, card.get('pan:mii'))
            self.eq(402400, card.get('pan:iin'))

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

            self.eq('13.37', perc.get('price'))
            self.eq('usd', perc.get('currency'))

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

            self.eq(True, perc.get('paid'))
            self.eq(1517529600000000, perc.get('paid:time'))

            self.eq(perc.get('place:loc'), 'us.ny.brooklyn')

            self.len(1, await core.nodes('econ:purchase -> geo:place'))
            self.len(2, await core.nodes('econ:purchase -> entity:contact | uniq'))

            text = '''[
                econ:payment=*
                    :id=" 1234 "
                    :ids=(" 5678 ",)

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

            self.eq(nodes[0].get('status'), 'settled')
            self.eq('1234', nodes[0].get('id'))
            self.eq(('5678',), nodes[0].get('ids'))
            self.eq('myhouse', nodes[0].get('place:name'))
            self.eq((90, 80), nodes[0].get('place:latlong'))
            self.eq('us.ny.brooklyn', nodes[0].get('place:loc'))
            self.eq('123 main street, brooklyn, ny, 11223', nodes[0].get('place:address'))

            self.len(1, await core.nodes('econ:payment -> geo:place'))
            self.len(2, await core.nodes('econ:payment -> entity:contact | uniq'))

            self.eq(nodes[0].ndef[1], await core.callStorm('return({econ:payment=({"id": "5678"})})'))

            nodes = await core.nodes('''
                [ econ:fin:exchange=(us,nasdaq) :name=nasdaq :currency=usd :org=* ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].ndef[1])
            self.nn(nodes[0].get('org'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq('nasdaq', nodes[0].get('name'))

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
            self.eq('stock.', nodes[0].get('type'))
            self.eq('nasdaq/tsla', nodes[0].get('ticker'))
            self.eq('9999', nodes[0].get('price'))
            self.eq(1580515200000000, nodes[0].get('time'))

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
            self.eq(1580601600000000, nodes[0].get('time'))
            self.eq('947183947f2e2c7bdc55264c20670f19', nodes[0].get('security'))
            self.eq('9999', nodes[0].get('price'))

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
            self.eq('947183947f2e2c7bdc55264c20670f19', nodes[0].get('security'))
            self.eq('9999', nodes[0].get('price:open'))
            self.eq('9999.01', nodes[0].get('price:close'))
            self.eq('999999999999', nodes[0].get('price:high'))
            self.eq('0.00001', nodes[0].get('price:low'))

            nodes = await core.nodes('''
                [ econ:balance=*
                    :time = 20211031
                    :account={[ econ:fin:account=* ]}
                    :amount = 123.45
                    :currency = usd
                ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('account'))
            self.eq(nodes[0].get('time'), 1635638400000000)
            self.eq(nodes[0].get('amount'), '123.45')
            self.eq(nodes[0].get('currency'), 'usd')

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
            self.eq(nodes[0].get('count'), 10)
            self.eq(nodes[0].get('price'), '100')
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
            self.eq('1234', nodes[0].get('number'))
            self.eq('checking.', nodes[0].get('type'))
            self.eq('bank of visi', nodes[0].get('issuer:name'))
            self.len(1, await core.nodes('econ:bank:aba:account -> ou:org'))
            self.len(1, await core.nodes('econ:bank:aba:account -> meta:name'))
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
            self.eq('usd', nodes[0].get('currency'))
            self.eq('99', nodes[0].get('starting:balance'))
            self.eq('999', nodes[0].get('ending:balance'))
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
            self.len(1, await core.nodes('econ:bank:aba:rtn=123456789 -> meta:name'))
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
            self.eq('99', nodes[0].get('amount'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq(1710806400000000, nodes[0].get('issued'))
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
            self.eq('99', nodes[0].get('amount'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq(0, nodes[0].get('paid'))
            self.eq(1710806400000000, nodes[0].get('due'))
            self.eq(1710806400000000, nodes[0].get('issued'))
            self.len(1, await core.nodes('econ:invoice -> econ:purchase'))
            self.len(1, await core.nodes('econ:invoice :issuer -> entity:contact'))
            self.len(1, await core.nodes('econ:invoice :recipient -> entity:contact'))
