import logging

import synapse.tests.utils as s_t_utils

logger = logging.getLogger(__name__)

class BizModelTest(s_t_utils.SynTest):

    async def test_model_biz(self):

        async with self.getTestCore() as core:
            nodes = await core.nodes('''
                [ biz:rfp=*
                    :ext:id = WOO123
                    :title = HeHeHaHa
                    :summary = ZipZop
                    :status = foo.bar
                    :url = "https://vertex.link"
                    :file = *
                    :posted = 20210731
                    :quesdue = 20210802
                    :propdue = 20210820
                    :contact = {[ ps:contact=* :name=visi ]}
                    :purchases += *
                    :requirements += *
                ]
            ''')
            self.len(1, nodes)
            self.eq(nodes[0].get('ext:id'), 'WOO123')
            self.eq(nodes[0].get('title'), 'HeHeHaHa')
            self.eq(nodes[0].get('summary'), 'ZipZop')
            self.eq(nodes[0].get('status'), 'foo.bar.')
            self.eq(nodes[0].get('url'), 'https://vertex.link')
            self.eq(nodes[0].get('posted'), 1627689600000)
            self.eq(nodes[0].get('quesdue'), 1627862400000)
            self.eq(nodes[0].get('propdue'), 1629417600000)

            self.nn(nodes[0].get('file'))
            self.nn(nodes[0].get('contact'))
            self.nn(nodes[0].get('purchases'))
            self.nn(nodes[0].get('requirements'))

            self.len(2, await core.nodes('biz:dealstatus'))

            self.len(1, await core.nodes('biz:rfp -> ou:goal'))
            self.len(1, await core.nodes('biz:rfp -> ps:contact'))
            self.len(1, await core.nodes('biz:rfp -> file:bytes'))
            self.len(1, await core.nodes('biz:rfp -> econ:purchase'))
            self.len(1, await core.nodes('biz:rfp -> biz:dealstatus'))

            nodes = await core.nodes('''
                [ biz:deal=*

                    :id = " 12345  "
                    :title = HeHeHaHa
                    :type = baz.faz
                    :status = foo.bar
                    :updated = 20210731
                    :contacted = 20210728
                    :rfp = { biz:rfp }
                    :buyer = {[ ps:contact=* :name=buyer ]}
                    :buyer:org = *
                    :buyer:orgname = hehehaha
                    :buyer:orgfqdn = hehehaha.com
                    :seller:org = *
                    :seller:orgname = lololol
                    :seller:orgfqdn = lololol.com
                    :seller = {[ ps:contact=* :name=seller ]}
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
            self.eq(nodes[0].get('updated'), 1627689600000)
            self.eq(nodes[0].get('contacted'), 1627430400000)
            self.eq(nodes[0].get('currency'), 'usd')
            self.eq(nodes[0].get('buyer:budget'), '300000')
            self.eq(nodes[0].get('buyer:deadline'), 1630454400000)
            self.eq(nodes[0].get('offer:price'), '299999')
            self.eq(nodes[0].get('offer:expires'), 1633046400000)

            self.nn(nodes[0].get('rfp'))
            self.nn(nodes[0].get('buyer'))
            self.nn(nodes[0].get('seller'))
            self.nn(nodes[0].get('purchase'))

            self.nn(nodes[0].get('buyer:org'))
            self.nn(nodes[0].get('seller:org'))

            self.eq('hehehaha', nodes[0].get('buyer:orgname'))
            self.eq('hehehaha.com', nodes[0].get('buyer:orgfqdn'))
            self.eq('lololol', nodes[0].get('seller:orgname'))
            self.eq('lololol.com', nodes[0].get('seller:orgfqdn'))

            self.len(2, await core.nodes('biz:dealtype'))

            self.len(1, await core.nodes('biz:deal -> biz:rfp'))
            self.len(1, await core.nodes('biz:deal -> econ:purchase'))
            self.len(1, await core.nodes('biz:deal :buyer -> ps:contact +:name=buyer'))
            self.len(1, await core.nodes('biz:deal :seller -> ps:contact +:name=seller'))
            self.len(1, await core.nodes('biz:deal :type -> biz:dealtype'))
            self.len(1, await core.nodes('biz:deal :status -> biz:dealstatus'))

            nodes = await core.nodes('''
                [ biz:bundle=*
                    :count = 10
                    :price = 299999
                    :product = {[ biz:product=* :name=LoLoLoL ]}
                    :service = {[ biz:service=* :name=WoWoWow ]}
                    :deal = { biz:deal }
                    :purchase = *
                ]
            ''')
            self.len(1, nodes)

            self.eq(nodes[0].get('count'), 10)
            self.eq(nodes[0].get('price'), '299999')

            self.nn(nodes[0].get('deal'))
            self.nn(nodes[0].get('product'))
            self.nn(nodes[0].get('service'))
            self.nn(nodes[0].get('purchase'))

            self.len(1, await core.nodes('biz:bundle -> biz:deal'))
            self.len(1, await core.nodes('biz:bundle -> biz:deal +:id=12345'))
            self.len(1, await core.nodes('biz:bundle -> econ:purchase'))
            self.len(1, await core.nodes('biz:bundle -> biz:product +:name=LoLoLoL'))
            self.len(1, await core.nodes('biz:bundle -> biz:service +:name=WoWoWoW'))

            nodes = await core.nodes('''
                [ biz:product=*
                    :name = WootWoot
                    :type = woot.woot
                    :madeby:org = *
                    :madeby:orgname = wootwoot
                    :madeby:orgfqdn = wootwoot.com
                    :summary = WootWithWootSauce
                    :price:retail = 29.99
                    :price:bottom = 3.20
                    :bundles = { biz:bundle }
                ]
            ''')
            self.len(1, nodes)

            self.eq(nodes[0].get('name'), 'WootWoot')
            self.eq(nodes[0].get('type'), 'woot.woot.')
            self.eq(nodes[0].get('summary'), 'WootWithWootSauce')
            self.eq(nodes[0].get('price:retail'), '29.99')
            self.eq(nodes[0].get('price:bottom'), '3.2')

            self.nn(nodes[0].get('bundles'))

            self.nn(nodes[0].get('madeby:org'))
            self.eq(nodes[0].get('madeby:orgname'), 'wootwoot')
            self.eq(nodes[0].get('madeby:orgfqdn'), 'wootwoot.com')

            self.len(2, await core.nodes('biz:prodtype'))

            self.len(1, await core.nodes('biz:product:name=WootWoot -> biz:bundle'))
            self.len(1, await core.nodes('biz:product:name=WootWoot -> biz:prodtype'))

            nodes = await core.nodes('''
                [ biz:stake=*
                    :vitals = *
                    :org = {[ ou:org=* :alias=vertex ]}
                    :orgname = vertex_project
                    :orgfqdn = vertex.link
                    :name = LoL
                    :asof = 20210731
                    :shares = 42
                    :invested = 299999
                    :value = 400000
                    :percent = 0.02
                    :owner = {[ ps:contact=* :name=visi ]}
                    :purchase = {[ econ:purchase=* ]}
                ]
            ''')
            self.len(1, nodes)

            self.nn(nodes[0].get('org'))
            self.nn(nodes[0].get('owner'))
            self.nn(nodes[0].get('vitals'))
            self.nn(nodes[0].get('purchase'))

            self.eq(nodes[0].get('name'), 'LoL')
            self.eq(nodes[0].get('value'), '400000')
            self.eq(nodes[0].get('invested'), '299999')

            self.eq(nodes[0].get('asof'), 1627689600000)
            self.eq(nodes[0].get('percent'), '0.02')
            self.eq(nodes[0].get('orgfqdn'), 'vertex.link')
            self.eq(nodes[0].get('orgname'), 'vertex_project')

            self.len(1, await core.nodes('biz:stake -> ou:org'))
            self.len(1, await core.nodes('biz:stake -> ou:name'))
            self.len(1, await core.nodes('biz:stake -> inet:fqdn'))
            self.len(1, await core.nodes('biz:stake :owner -> ps:contact'))
            self.len(1, await core.nodes('biz:stake :purchase -> econ:purchase'))

            nodes = await core.nodes('''
                [ biz:listing=*
                    :seller={ ps:contact:name=visi | limit 1 }
                    :product={[ biz:product=* :name=wootprod ]}
                    :service={[ biz:service=*
                        :name=wootsvc
                        :type=awesome
                        :summary="hehe haha"
                        :provider={ ps:contact:name=visi | limit 1}
                        :launched=20230124
                    ]}
                    :current=1
                    :time=20221221
                    :expires=2023
                    :price=1000000
                    :currency=usd
                ]
            ''')
            self.len(1, nodes)
            self.nn(nodes[0].get('seller'))
            self.nn(nodes[0].get('product'))
            self.nn(nodes[0].get('service'))
            self.eq(True, nodes[0].get('current'))
            self.eq(1671580800000, nodes[0].get('time'))
            self.eq(1672531200000, nodes[0].get('expires'))
            self.eq('1000000', nodes[0].get('price'))
            self.eq('usd', nodes[0].get('currency'))

            self.len(1, await core.nodes('biz:listing -> ps:contact +:name=visi'))
            self.len(1, await core.nodes('biz:listing -> biz:product +:name=wootprod'))
            self.len(1, await core.nodes('biz:listing -> biz:service +:name=wootsvc'))

            nodes = await core.nodes('biz:listing -> biz:service')
            self.len(1, nodes)
            self.eq(1674518400000, nodes[0].get('launched'))
