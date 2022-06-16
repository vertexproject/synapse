import synapse.exc as s_exc
import synapse.tests.utils as s_utils

import synapse.common as s_common

class EconTest(s_utils.SynTest):

    async def test_model_econ(self):

        async with self.getTestCore() as core:

            # test card number 4024007150779444
            card = (await core.nodes('[ econ:pay:card="*" :expr=201802 :name="Bob Smith" :cvv=123 :pin=1234 :pan=4024007150779444 ]'))[0]
            self.eq('bob smith', card.get('name'))
            self.eq(1517443200000, card.get('expr'))
            self.eq('4024007150779444', card.get('pan'))
            self.eq(4, card.get('pan:mii'))
            self.eq(402400, card.get('pan:iin'))

            place = s_common.guid()
            bycont = s_common.guid()
            fromcont = s_common.guid()

            text = f'''[
                econ:purchase="*"

                    :price=13.37
                    :currency=USD
                    :by:contact={bycont}
                    :from:contact={fromcont}

                    :time=20180202
                    :place={place}

                    :paid=true
                    :paid:time=20180202

                    :settled=20180205
            ]'''

            perc = (await core.nodes(text))[0]

            self.eq('13.37', perc.get('price'))
            self.eq('usd', perc.get('currency'))

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

            self.eq(bycont, perc.get('by:contact'))
            self.eq(fromcont, perc.get('from:contact'))

            self.eq(True, perc.get('paid'))
            self.eq(1517529600000, perc.get('paid:time'))

            self.eq(1517788800000, perc.get('settled'))

            self.eq(1517529600000, perc.get('time'))
            self.eq(place, perc.get('place'))

            self.len(1, await core.nodes('econ:purchase -> geo:place'))
            self.len(2, await core.nodes('econ:purchase -> ps:contact | uniq'))

            acqu = (await core.nodes(f'[ econ:acquired=({perc.ndef[1]}, (inet:fqdn,vertex.link)) ]'))[0]
            self.eq(perc.ndef[1], acqu.get('purchase'))

            self.len(1, await core.nodes('econ:acquired:item:form=inet:fqdn'))
            self.len(1, await core.nodes('inet:fqdn=vertex.link'))

            self.eq(('inet:fqdn', 'vertex.link'), acqu.get('item'))

            text = f'''[
                econ:acct:payment="*"

                    :to:contact={bycont}
                    :to:coinaddr=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)

                    :from:contact={fromcont}
                    :from:coinaddr=(btc, 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2)

                    :from:pay:card={card.ndef[1]}
                    :amount = 20.30
                    :currency = usd

                    :time=20180202
                    :purchase={perc.ndef[1]}
            ]'''
            await core.nodes(text)

            self.len(1, await core.nodes('econ:acct:payment +:time@=(2017,2019) +{-> econ:pay:card +:name="bob smith"}'))

            self.len(1, await core.nodes('econ:acct:payment -> econ:purchase'))
            self.len(1, await core.nodes('econ:acct:payment -> econ:pay:card'))
            self.len(2, await core.nodes('econ:acct:payment -> ps:contact | uniq'))

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
            self.eq('stock', nodes[0].get('type'))
            self.eq('nasdaq/tsla', nodes[0].get('ticker'))
            self.eq('9999', nodes[0].get('price'))
            self.eq(1580515200000, nodes[0].get('time'))

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
            self.eq(1580601600000, nodes[0].get('time'))
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
            self.eq((1580601600000, 1580688000000), nodes[0].get('ival'))
            self.eq('947183947f2e2c7bdc55264c20670f19', nodes[0].get('security'))
            self.eq('9999', nodes[0].get('price:open'))
            self.eq('9999.01', nodes[0].get('price:close'))
            self.eq('999999999999', nodes[0].get('price:high'))
            self.eq('0.00001', nodes[0].get('price:low'))

            nodes = await core.nodes('[ econ:acct:payment=* :from:contract=* :to:contract=* :memo="2012 Chateauneuf du Pape" ]')
            self.len(1, nodes)
            self.eq('2012 Chateauneuf du Pape', nodes[0].get('memo'))
            self.nn(nodes[0].get('to:contract'))
            self.nn(nodes[0].get('from:contract'))
            nodes = await core.nodes('econ:acct:payment :to:contract -> ou:contract')
            self.len(1, nodes)
            nodes = await core.nodes('econ:acct:payment :from:contract -> ou:contract')
            self.len(1, nodes)

            nodes = await core.nodes('''
                [ econ:acct:balance=*
                    :time = 20211031
                    :pay:card = *
                    :crypto:address = btc/12345
                    :amount = 123.45
                    :currency = usd
                    :delta = 12.00
                    :total:received = 13.14
                    :total:sent = 15.16
                ]''')
            self.len(1, nodes)
            self.nn(nodes[0].get('pay:card'))
            self.eq(nodes[0].get('time'), 1635638400000)
            self.eq(nodes[0].get('crypto:address'), ('btc', '12345'))
            self.eq(nodes[0].get('amount'), '123.45')
            self.eq(nodes[0].get('currency'), 'usd')
            self.eq(nodes[0].get('delta'), '12')
            self.eq(nodes[0].get('total:received'), '13.14')
            self.eq(nodes[0].get('total:sent'), '15.16')
