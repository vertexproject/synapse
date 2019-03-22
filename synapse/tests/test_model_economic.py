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
            byorg = s_common.guid()
            fromorg = s_common.guid()

            bycont = s_common.guid()
            fromcont = s_common.guid()

            byps = s_common.guid()
            fromps = s_common.guid()
            text = f'''[
                econ:purchase="*"

                    :by:org={byorg}
                    :by:person={byps}
                    :by:contact={bycont}

                    :from:org={fromorg}
                    :from:person={fromps}
                    :from:contact={fromcont}

                    :time=20180202
                    :place={place}

                    :paid=true
                    :paid:time=20180202
            ]'''

            perc = (await core.nodes(text))[0]

            self.eq(byorg, perc.get('by:org'))
            self.eq(byps, perc.get('by:person'))
            self.eq(bycont, perc.get('by:contact'))

            self.eq(fromorg, perc.get('from:org'))
            self.eq(fromps, perc.get('from:person'))
            self.eq(fromcont, perc.get('from:contact'))

            self.eq(True, perc.get('paid'))
            self.eq(1517529600000, perc.get('paid:time'))

            self.eq(1517529600000, perc.get('time'))
            self.eq(place, perc.get('place'))

            self.len(2, await core.nodes('econ:purchase -> ou:org | uniq'))
            self.len(2, await core.nodes('econ:purchase -> ps:person | uniq'))
            self.len(2, await core.nodes('econ:purchase -> ps:contact | uniq'))
            self.len(1, await core.nodes('econ:purchase -> geo:place | uniq'))

            acqu = (await core.nodes(f'[ econ:acquired=({perc.ndef[1]}, (inet:fqdn,vertex.link)) ]'))[0]
            self.eq(perc.ndef[1], acqu.get('purchase'))

            self.eq(('inet:fqdn', 'vertex.link'), acqu.get('item'))

            text = f'''[
                econ:acct:payment="*"
                    :from:org={fromorg}
                    :from:person={fromps}
                    :from:contact={fromcont}

                    :from:pay:card={card.ndef[1]}

                    :time=20180202
                    :purchase={perc.ndef[1]}
            ]'''
            paym = (await core.nodes(text))[0]
            self.eq(card.ndef[1], paym.get('from:pay:card'))
