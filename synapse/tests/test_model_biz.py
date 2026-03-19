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
                    :due:questions = 20210802
                    :due:proposal = 20210820
                    :contact = {[ entity:contact=* :name=visi ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', 'WOO123')
            self.propeq(nodes[0], 'title', 'HeHeHaHa')
            self.propeq(nodes[0], 'desc', 'ZipZop')
            self.propeq(nodes[0], 'status', 'foo.bar.')
            self.propeq(nodes[0], 'url', 'https://vertex.link')
            self.propeq(nodes[0], 'posted', 1627689600000000)
            self.propeq(nodes[0], 'due:questions', 1627862400000000)
            self.propeq(nodes[0], 'due:proposal', 1629417600000000)

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('contact'))

            self.len(2, await core.nodes('biz:deal:status:taxonomy'))

            self.len(1, await core.nodes('biz:rfp -> file:bytes'))
            self.len(1, await core.nodes('biz:rfp -> entity:contact'))
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
            self.propeq(nodes[0], 'id', '12345')
            self.propeq(nodes[0], 'title', 'HeHeHaHa')
            self.propeq(nodes[0], 'type', 'baz.faz.')
            self.propeq(nodes[0], 'status', 'foo.bar.')
            self.propeq(nodes[0], 'updated', 1627689600000000)
            self.propeq(nodes[0], 'contacted', 1627430400000000)
            self.propeq(nodes[0], 'currency', 'usd')
            self.propeq(nodes[0], 'buyer:budget', '300000')
            self.propeq(nodes[0], 'buyer:deadline', 1630454400000000)
            self.propeq(nodes[0], 'offer:price', '299999')
            self.propeq(nodes[0], 'offer:expires', 1633046400000000)

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

            self.propeq(nodes[0], 'name', 'wootwoot')
            self.propeq(nodes[0], 'type', 'woot.woot.')
            self.propeq(nodes[0], 'desc', 'WootWithWootSauce')
            self.propeq(nodes[0], 'price:retail', '29.99')
            self.propeq(nodes[0], 'price:bottom', '3.2')

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
            self.propeq(nodes[0], 'current', True)
            self.propeq(nodes[0], 'period', (1671580800000000, 1672531200000000, 950400000000))
            self.propeq(nodes[0], 'price', '1000000')
            self.propeq(nodes[0], 'currency', 'usd')

            self.len(1, await core.nodes('biz:listing -> entity:contact +:name=visi'))

            nodes = await core.nodes('biz:listing -(has)> econ:lineitem -> biz:service')
            self.len(1, nodes)
            self.propeq(nodes[0], 'launched', 1752624000000000)
