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
                    :published = 20210731
                    :due:questions = 20210802
                    :due:proposal = 20210820
                    :creator = {[ entity:contact=* :name=visi ]}
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', 'WOO123')
            self.propeq(nodes[0], 'title', 'HeHeHaHa')
            self.propeq(nodes[0], 'desc', 'ZipZop')
            self.propeq(nodes[0], 'status', 'foo.bar.')
            self.propeq(nodes[0], 'url', 'https://vertex.link')
            self.propeq(nodes[0], 'published', 1627689600000000)
            self.propeq(nodes[0], 'due:questions', 1627862400000000)
            self.propeq(nodes[0], 'due:proposal', 1629417600000000)

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('creator'))

            self.len(2, await core.nodes('biz:deal:status:taxonomy'))

            self.len(1, await core.nodes('biz:rfp -> file:bytes'))
            self.len(1, await core.nodes('biz:rfp -> entity:contact'))
            self.len(1, await core.nodes('biz:rfp -> biz:deal:status:taxonomy'))

            nodes = await core.nodes('''
                [ biz:deal=*

                    :id = " 12345  "
                    :name = HeHeHaHa
                    :type = baz.faz
                    :status = foo.bar
                    :updated = 20210731
                    :contacted = 20210728
                    :buyer = {[ entity:contact=* :name=buyer ]}
                    :seller = {[ entity:contact=* :name=seller ]}
                    +(ledto)> {[ econ:purchase=* ]}
                    <(ledto)+ { biz:rfp | limit 1 }
                ]
            ''')
            self.len(1, nodes)
            self.propeq(nodes[0], 'id', '12345')
            self.propeq(nodes[0], 'name', 'hehehaha')
            self.propeq(nodes[0], 'type', 'baz.faz.')
            self.propeq(nodes[0], 'status', 'foo.bar.')
            self.propeq(nodes[0], 'updated', 1627689600000000)
            self.propeq(nodes[0], 'contacted', 1627430400000000)

            self.nn(nodes[0].get('buyer'))
            self.nn(nodes[0].get('seller'))

            self.len(2, await core.nodes('biz:deal:type:taxonomy'))

            self.len(1, await core.nodes('biz:deal <(ledto)- biz:rfp'))
            self.len(1, await core.nodes('biz:deal -(ledto)> econ:purchase'))
            self.len(1, await core.nodes('biz:deal :buyer -> entity:contact +:name=buyer'))
            self.len(1, await core.nodes('biz:deal :seller -> entity:contact +:name=seller'))
            self.len(1, await core.nodes('biz:deal :type -> biz:deal:type:taxonomy'))
            self.len(1, await core.nodes('biz:deal :status -> biz:deal:status:taxonomy'))

            nodes = await core.nodes('''
                [ biz:product=*
                    :name = WootWoot
                    :type = woot.woot
                    :desc = WootWithWootSauce
                    :price = 29.99
                ]
            ''')
            self.len(1, nodes)

            self.propeq(nodes[0], 'name', 'wootwoot')
            self.propeq(nodes[0], 'type', 'woot.woot.')
            self.propeq(nodes[0], 'desc', 'WootWithWootSauce')
            self.propeq(nodes[0], 'price', '29.99')

            self.len(2, await core.nodes('biz:product:type:taxonomy'))
            self.len(1, await core.nodes('biz:product:name=wootwoot -> biz:product:type:taxonomy'))

            nodes = await core.nodes('''
                [ biz:listing=*
                    :actor={ entity:contact:name=visi | limit 1 }
                    +(has)> {[ econ:lineitem=* :item={[ biz:service=* :period=20250716 ]} ]}
                    :period=(20221221, 2023)
                    :price=1000000
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('actor'))
            self.propeq(nodes[0], 'period', (1671580800000000, 1672531200000000, 950400000000))
            self.propeq(nodes[0], 'price', '1000000')

            self.len(1, await core.nodes('biz:listing -> entity:contact +:name=visi'))

            nodes = await core.nodes('biz:listing -(has)> econ:lineitem -> biz:service')
            self.len(1, nodes)
            self.propeq(nodes[0], 'period', (1752624000000000, 1752624000000001, 1))
