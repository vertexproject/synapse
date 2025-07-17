import logging

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class BizModelTest(s_t_utils.SynTest):

    async def test_model_biz(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ biz:rfp=*
                    :id = WOO123
                    :title = HeHeHaHa
                    :desc = ZipZop
                    :status = foo.bar
                    :url = "https://vertex.link"
                    :file = *
                    :posted = 20210731
                    :quesdue = 20210802
                    :propdue = 20210820
                    :contact = {[ entity:contact=* :name=visi ]}
                    :purchases += *
                    :requirements += *
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('id'), 'WOO123')
            self.eq(nodes[0].get('title'), 'hehehaha')
            self.eq(nodes[0].get('desc'), 'ZipZop')
            self.eq(nodes[0].get('status'), 'foo.bar.')
            self.eq(nodes[0].get('url'), 'https://vertex.link')
            self.eq(nodes[0].get('posted'), 1627689600000000)
            self.eq(nodes[0].get('quesdue'), 1627862400000000)
            self.eq(nodes[0].get('propdue'), 1629417600000000)

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('contact'))
            self.nn(nodes[0].get('purchases'))
            self.nn(nodes[0].get('requirements'))

            self.len(2, await core.nodes('biz:deal:status:taxonomy'))

            self.len(1, await core.nodes('biz:rfp -> ou:goal'))
            self.len(1, await core.nodes('biz:rfp -> entity:contact'))
            self.len(1, await core.nodes('biz:rfp -> file:bytes'))
            self.len(1, await core.nodes('biz:rfp -> econ:purchase'))
            self.len(1, await core.nodes('biz:rfp -> biz:deal:status:taxonomy'))

            nodes = await core.nodes('''
                [ biz:deal=*

                    :id = " 12345  "
                    :title = HeHeHaHa
                    :type = baz.faz
                    :status = foo.bar
                    :updated = 20210731
                    :contacted = 20210728
                    :rfp = { biz:rfp }
                    :buyer = {[ entity:contact=* :name=buyer ]}
                    :seller = {[ entity:contact=* :name=seller ]}
                    :currency = USD
                    :buyer:budget = 300000
                    :buyer:deadline = 20210901
                    :offer:price = 299999
                    :offer:expires = 20211001
                    :purchase = *
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('id'), '12345')
            self.eq(nodes[0].get('title'), 'HeHeHaHa')
            self.eq(nodes[0].get('type'), 'baz.faz.')
            self.eq(nodes[0].get('status'), 'foo.bar.')
            self.eq(nodes[0].get('updated'), 1627689600000000)
            self.eq(nodes[0].get('contacted'), 1627430400000000)
            self.eq(nodes[0].get('currency'), 'usd')
            self.eq(nodes[0].get('buyer:budget'), '300000')
            self.eq(nodes[0].get('buyer:deadline'), 1630454400000000)
            self.eq(nodes[0].get('offer:price'), '299999')
            self.eq(nodes[0].get('offer:expires'), 1633046400000000)

            self.nn(nodes[0].get('rfp'))
            self.nn(nodes[0].get('buyer'))
            self.nn(nodes[0].get('seller'))
            self.nn(nodes[0].get('purchase'))

            self.len(2, await core.nodes('biz:deal:type:taxonomy'))

            self.len(1, await core.nodes('biz:deal -> biz:rfp'))
            self.len(1, await core.nodes('biz:deal -> econ:purchase'))
            self.len(1, await core.nodes('biz:deal :buyer -> entity:contact +:name=buyer'))
            self.len(1, await core.nodes('biz:deal :seller -> entity:contact +:name=seller'))
            self.len(1, await core.nodes('biz:deal :type -> biz:deal:type:taxonomy'))
            self.len(1, await core.nodes('biz:deal :status -> biz:deal:status:taxonomy'))

            nodes = await core.nodes('''
                [ biz:product=*
                    :name = WootWoot
                    :type = woot.woot
                    :desc = WootWithWootSauce
                    :price:retail = 29.99
                    :price:bottom = 3.20
                ]
            ''')
            self.len(1, nodes)

            self.eq(nodes[0].get('name'), 'wootwoot')
            self.eq(nodes[0].get('type'), 'woot.woot.')
            self.eq(nodes[0].get('desc'), 'WootWithWootSauce')
            self.eq(nodes[0].get('price:retail'), '29.99')
            self.eq(nodes[0].get('price:bottom'), '3.2')

            self.len(2, await core.nodes('biz:product:type:taxonomy'))
            self.len(1, await core.nodes('biz:product:name=wootwoot -> biz:product:type:taxonomy'))

            nodes = await core.nodes('''
                [ biz:listing=*
                    :seller={ entity:contact:name=visi | limit 1 }
                    +(has)> {[ econ:lineitem=* :item={[ biz:service=* :launched=20250716 ]} ]}
                    :current=(true)
                    :period=(20221221, 2023)
                    :price=1000000
                    :currency=usd
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('seller'))
            self.eq(True, nodes[0].get('current'))
            self.eq(nodes[0].get('period'), (1671580800000000, 1672531200000000))
            self.eq('1000000', nodes[0].get('price'))
            self.eq('usd', nodes[0].get('currency'))

            self.len(1, await core.nodes('biz:listing -> entity:contact +:name=visi'))

            nodes = await core.nodes('biz:listing -(has)> econ:lineitem -> biz:service')
            self.len(1, nodes)
            self.eq(1752624000000000, nodes[0].get('launched'))
