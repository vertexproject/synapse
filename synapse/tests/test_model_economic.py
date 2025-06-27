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

                    :settled=20180205
                    :listing = *
            ]'''

            perc = (await core.nodes(text))[0]

            self.nn(perc.get('listing'))
            self.eq('13.37', perc.get('price'))
            self.eq('usd', perc.get('currency'))

            self.len(1, await core.nodes('econ:purchase -> biz:listing'))

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

            self.eq(1517788800000000, perc.get('settled'))

            self.eq(perc.get('place:loc'), 'us.ny.brooklyn')

            self.len(1, await core.nodes('econ:purchase -> geo:place'))
            self.len(2, await core.nodes('econ:purchase -> entity:contact | uniq'))

            text = '''[
                econ:payment=*

                    :to:contact={[ entity:contact=* :name=payee ]}
                    :from:contact={[ entity:contact=* :name=payer ]}

                    :amount = 20.30
                    :currency = usd

                    :time=20180202
                    :purchase={ econ:purchase }

                    :place=*
                    :place:loc=us.ny.brooklyn
                    :place:name=myhouse
                    :place:address="123 main street, brooklyn, ny, 11223"
                    :place:latlong=(90,80)
            ]'''
            nodes = await core.nodes(text)

            self.eq('myhouse', nodes[0].get('place:name'))
            self.eq((90, 80), nodes[0].get('place:latlong'))
            self.eq('us.ny.brooklyn', nodes[0].get('place:loc'))
            self.eq('123 main street, brooklyn, ny, 11223', nodes[0].get('place:address'))

            self.len(1, await core.nodes('econ:payment -> geo:place'))

            self.len(1, await core.nodes('econ:payment -> econ:purchase'))
            self.len(2, await core.nodes('econ:payment -> entity:contact | uniq'))

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
                        :ival=(20200202, 20200203)
                        :security=(us, nasdaq, tsla)
                        :price:open=9999.00
                        :price:close=9999.01
                        :price:high=999999999999.00
                        :price:low=0.00001
                ]
            ''')
            self.len(1, nodes)
            self.eq((1580601600000000, 1580688000000000), nodes[0].get('ival'))
            self.eq('947183947f2e2c7bdc55264c20670f19', nodes[0].get('security'))
            self.eq('9999', nodes[0].get('price:open'))
            self.eq('9999.01', nodes[0].get('price:close'))
            self.eq('999999999999', nodes[0].get('price:high'))
            self.eq('0.00001', nodes[0].get('price:low'))

            nodes = await core.nodes('[ econ:payment=* :memo="2012 Chateauneuf du Pape" ]')
            self.len(1, nodes)
            self.eq('2012 Chateauneuf du Pape', nodes[0].get('memo'))

            nodes = await core.nodes('''
                [ econ:balance=*
                    :time = 20211031
                    :instrument=(econ:bank:account, *)
                    :amount = 123.45
                    :currency = usd
                ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('instrument'))
            self.eq(nodes[0].get('time'), 1635638400000000)
            self.eq(nodes[0].get('amount'), '123.45')
            self.eq(nodes[0].get('currency'), 'usd')

            self.eq('usd', await core.callStorm('econ:balance return($node.protocol(econ:adjustable, propname=amount).vars.currency)'))

            self.len(1, await core.nodes('econ:balance:instrument -> econ:bank:account'))

            nodes = await core.nodes('''
                [ econ:receipt:item=*
                    :purchase=*
                    :count=10
                    :product={[ biz:product=* :name=bananna ]}
                    :price=100
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('product'))
            self.nn(nodes[0].get('purchase'))
            self.eq(nodes[0].get('count'), 10)
            self.eq(nodes[0].get('price'), '100')
            self.len(1, await core.nodes('econ:receipt:item -> econ:purchase'))
            self.len(1, await core.nodes('econ:receipt:item -> biz:product +:name=bananna'))

            nodes = await core.nodes('''
                [ econ:bank:account=*
                    :name=visi
                    :number=1234
                    :type=checking
                    :aba:rtn=123456789
                    :iban=VV09WootWoot
                    :issuer={ gen.ou.org "bank of visi" }
                    :issuer:name="bank of visi"
                    :currency=usd
                    :balance=*
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('issuer'))
            self.nn(nodes[0].get('balance'))
            self.eq('visi', nodes[0].get('name'))
            self.eq('1234', nodes[0].get('number'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq('checking.', nodes[0].get('type'))
            self.eq('VV09WootWoot', nodes[0].get('iban'))
            self.eq('bank of visi', nodes[0].get('issuer:name'))
            self.len(1, await core.nodes('econ:bank:account -> ou:org'))
            self.len(2, await core.nodes('econ:bank:account -> meta:name'))
            self.len(1, await core.nodes('econ:bank:account -> econ:bank:aba:rtn'))
            self.len(1, await core.nodes('econ:bank:account -> econ:bank:account:type:taxonomy'))

            nodes = await core.nodes('''[
                econ:bank:swift:bic=DEUTDEFFXXX
                    :business={ gen.ou.org "Deutsche Bank" }
                    :office={[ entity:contact=* ]}
            ]''')
            self.len(1, nodes)
            self.len(1, await core.nodes('econ:bank:swift:bic -> ou:org +:name="deutsche bank"'))
            self.len(1, await core.nodes('econ:bank:swift:bic -> entity:contact'))

            nodes = await core.nodes('''[
                econ:statement=*
                    :period=202403*
                    :instrument={econ:bank:account | limit 1}
                    :currency=usd
                    :starting:balance=99
                    :ending:balance=999
            ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('instrument'))
            self.eq('usd', nodes[0].get('currency'))
            self.eq('99', nodes[0].get('starting:balance'))
            self.eq('999', nodes[0].get('ending:balance'))
            self.eq((1709251200000000, 1709251200000001), nodes[0].get('period'))

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
