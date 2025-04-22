'''
Model elements related to sales / bizdev / procurement
'''
modeldefs = (
    ('biz', {
        'types': (

            ('biz:rfp', ('guid', {}), {
                'doc': 'An RFP (Request for Proposal) soliciting proposals.'}),

            ('biz:deal', ('guid', {}), {
                'doc': 'A sales or procurement effort in pursuit of a purchase.'}),

            ('biz:listing', ('guid', {}), {
                'doc': 'A product or service being listed for sale at a given price by a specific seller.'}),

            ('biz:product', ('guid', {}), {
                'doc': 'A product which is available for purchase.'}),

            ('biz:service', ('guid', {}), {
                'doc': 'A service which is performed by a specific organization.'}),

            ('biz:service:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of service types.'}),

            ('biz:deal:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of deal status values.'}),

            ('biz:deal:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of deal types.'}),

            ('biz:product:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of product types.'}),
        ),
        'forms': (
            ('biz:deal:type:taxonomy', {
                'prevnames': ('biz:dealtype',)}, ()),

            ('biz:product:type:taxonomy', {
                'prevnames': ('biz:prodtype',)}, ()),

            ('biz:deal:status:taxonomy', {
                'prevnames': ('biz:dealstatus',)}, ()),

            ('biz:service:type:taxonomy', {}, ()),

            ('biz:rfp', {}, (

                ('id', ('meta:id', {}), {
                    'prevnames': ('id',),
                    'doc': 'An externally specified identifier for the RFP.'}),

                ('title', ('str', {}), {
                    'doc': 'The title of the RFP.'}),

                ('summary', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A brief summary of the RFP.'}),

                ('status', ('biz:deal:status:taxonomy', {}), {
                    'doc': 'The status of the RFP.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The official URL for the RFP.'}),

                ('file', ('file:bytes', {}), {
                    'doc': 'The RFP document.'}),

                ('posted', ('time', {}), {
                    'doc': 'The date/time that the RFP was posted.'}),

                ('quesdue', ('time', {}), {
                    'doc': 'The date/time that questions are due.'}),

                ('propdue', ('time', {}), {
                    'doc': 'The date/time that proposals are due.'}),

                ('contact', ('entity:actor', {}), {
                    'doc': 'The contact information given for the org requesting offers.'}),

                ('purchases', ('array', {'type': 'econ:purchase', 'uniq': True, 'sorted': True}), {
                    'doc': 'Any known purchases that resulted from the RFP.'}),

                ('requirements', ('array', {'type': 'ou:goal', 'uniq': True, 'sorted': True}), {
                    'doc': 'Any stated goals of the RFP.'}),
            )),
            ('biz:deal', {}, (

                ('id', ('meta:id', {}), {
                    'doc': 'An identifier for the deal.'}),

                ('title', ('str', {}), {
                    'doc': 'A title for the deal.'}),

                ('type', ('biz:deal:type:taxonomy', {}), {
                    'doc': 'The type of deal.'}),

                ('status', ('biz:deal:status:taxonomy', {}), {
                    'doc': 'The status of the deal.'}),

                ('updated', ('time', {}), {
                    'doc': 'The last time the deal had a significant update.'}),

                ('contacted', ('time', {}), {
                    'doc': 'The last time the contacts communicated about the deal.'}),

                ('rfp', ('biz:rfp', {}), {
                    'doc': 'The RFP that the deal is in response to.'}),

                ('buyer', ('entity:actor', {}), {
                    'doc': 'The primary contact information for the buyer.'}),

                ('seller', ('entity:actor', {}), {
                    'doc': 'The primary contact information for the seller.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of econ:price values associated with the deal.'}),

                ('buyer:budget', ('econ:price', {}), {
                    'doc': 'The buyers budget for the eventual purchase.'}),

                ('buyer:deadline', ('time', {}), {
                    'doc': 'When the buyer intends to make a decision.'}),

                ('offer:price', ('econ:price', {}), {
                    'doc': 'The total price of the offered products.'}),

                ('offer:expires', ('time', {}), {
                    'doc': 'When the offer expires.'}),

                ('purchase', ('econ:purchase', {}), {
                    'doc': 'Records a purchase resulting from the deal.'}),
            )),
            # FIXME convert to aggregates?
            # ('biz:bundle', {}, (
            ('biz:listing', {}, (

                ('seller', ('entity:actor', {}), {
                    'doc': 'The contact information for the seller.'}),

                # FIXME valuable?
                ('product', ('biz:product', {}), {
                    'doc': 'The product being offered.'}),

                ('service', ('biz:service', {}), {
                    'doc': 'The service being offered.'}),

                ('current', ('bool', {}), {
                    'doc': 'Set to true if the offer is still current.'}),

                # FIXME period
                ('time', ('time', {}), {
                    'doc': 'The first known offering of this product/service by the organization for the asking price.'}),

                ('expires', ('time', {}), {
                    'doc': 'Set if the offer has a known expiration date.'}),

                # FIXME valuable
                ('price', ('econ:price', {}), {
                    'doc': 'The asking price of the product or service.'}),

                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of the asking price.'}),

                ('count:total', ('int', {'min': 0}), {
                    'doc': 'The number of instances for sale.'}),

                ('count:remaining', ('int', {'min': 0}), {
                    'doc': 'The current remaining number of instances for sale.'}),
            )),
            ('biz:service', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the service being performed.'}),

                ('provider', ('entity:actor', {}), {
                    'doc': 'The contact info of the entity which performs the service.'}),

                ('summary', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A brief summary of the service.'}),

                ('type', ('biz:service:type:taxonomy', {}), {
                    'doc': 'A taxonomy of service types.'}),

                # FIXME offered=ival?
                ('launched', ('time', {}), {
                    'doc': 'The time when the operator first made the service available.'}),
                # TODO: billing types (fixed, hourly, subscription, etc)
            )),
            ('biz:product', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'The name of the product.'}),

                ('type', ('biz:product:type:taxonomy', {}), {
                    'doc': 'The type of product.'}),

                # TODO ('upc', ('biz:upc', {}), {}),
                ('summary', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A brief summary of the product.'}),

                # FIXME: manufactur?
                ('maker', ('entity:actor', {}), {
                    'doc': 'A contact for the maker of the product.'}),

                ('price:retail', ('econ:price', {}), {
                    'doc': 'The MSRP price of the product.'}),

                ('price:bottom', ('econ:price', {}), {
                    'doc': 'The minimum offered or observed price of the product.'}),

                ('price:currency', ('econ:currency', {}), {
                    'doc': 'The currency of the retail and bottom price properties.'}),
            )),
        ),
    }),
)
