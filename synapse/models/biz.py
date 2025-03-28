'''
Model elements related to sales / bizdev / procurement
'''
modeldefs = (
    ('biz', {
        'types': (
            ('biz:rfp', ('guid', {}), {
                'doc': 'An RFP (Request for Proposal) soliciting proposals.',
            }),
            ('biz:deal', ('guid', {}), {
                'doc': 'A sales or procurement effort in pursuit of a purchase.',
            }),
            ('biz:stake', ('guid', {}), {
                'doc': 'A stake or partial ownership in a company.',
            }),
            ('biz:listing', ('guid', {}), {
                'doc': 'A product or service being listed for sale at a given price by a specific seller.',
            }),
            ('biz:bundle', ('guid', {}), {
                'doc': 'A bundle allows construction of products which bundle instances of other products.',
            }),
            ('biz:product', ('guid', {}), {
                'doc': 'A product which is available for purchase.',
            }),
            ('biz:service', ('guid', {}), {
                'doc': 'A service which is performed by a specific organization.',
            }),
            ('biz:service:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of service types.',
            }),
            ('biz:deal:status:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of deal status values.',
            }),
            ('biz:deal:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of deal types.',
            }),
            ('biz:product:type:taxonomy', ('taxonomy', {}), {
                'doc': 'A hierarchical taxonomy of product types.',
                'interfaces': ('meta:taxonomy',),
            }),
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
                ('ext:id', ('str', {}), {
                    'doc': 'An externally specified identifier for the RFP.',
                }),
                ('title', ('str', {}), {
                    'doc': 'The title of the RFP.',
                }),
                ('summary', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A brief summary of the RFP.',
                }),
                ('status', ('biz:deal:status:taxonomy', {}), {
                    'doc': 'The status of the RFP.',
                }),
                ('url', ('inet:url', {}), {
                    'doc': 'The official URL for the RFP.',
                }),
                ('file', ('file:bytes', {}), {
                    'doc': 'The RFP document.',
                }),
                ('posted', ('time', {}), {
                    'doc': 'The date/time that the RFP was posted.',
                }),
                ('quesdue', ('time', {}), {
                    'doc': 'The date/time that questions are due.',
                }),
                ('propdue', ('time', {}), {
                    'doc': 'The date/time that proposals are due.',
                }),
                ('contact', ('entity:actor', {}), {
                    'doc': 'The contact information given for the org requesting offers.',
                }),
                ('purchases', ('array', {'type': 'econ:purchase', 'uniq': True, 'sorted': True}), {
                    'doc': 'Any known purchases that resulted from the RFP.',
                }),
                ('requirements', ('array', {'type': 'ou:goal', 'uniq': True, 'sorted': True}), {}),
            )),
            ('biz:deal', {}, (
                ('id', ('str', {'strip': True}), {
                    'doc': 'An identifier for the deal.',
                }),

                ('title', ('str', {}), {
                    'doc': 'A title for the deal.',
                }),
                ('type', ('biz:deal:type:taxonomy', {}), {
                    'doc': 'The type of deal.',
                }),
                ('status', ('biz:deal:status:taxonomy', {}), {
                    'doc': 'The status of the deal.',
                }),
                ('updated', ('time', {}), {
                    'doc': 'The last time the deal had a significant update.',
                }),
                ('contacted', ('time', {}), {
                    'doc': 'The last time the contacts communicated about the deal.',
                }),
                ('rfp', ('biz:rfp', {}), {
                    'doc': 'The RFP that the deal is in response to.',
                }),
                ('buyer', ('entity:actor', {}), {
                    'doc': 'The primary contact information for the buyer.',
                }),
                ('buyer:org', ('ou:org', {}), {
                    'doc': 'The buyer org.',
                }),
                ('buyer:orgname', ('entity:name', {}), {
                    'doc': 'The reported name of the buyer org.',
                }),
                ('buyer:orgfqdn', ('inet:fqdn', {}), {
                    'doc': 'The reported inet:fqdn of the buyer org.',
                }),
                ('seller', ('entity:actor', {}), {
                    'doc': 'The primary contact information for the seller.',
                }),
                ('seller:org', ('ou:org', {}), {
                    'doc': 'The seller org.',
                }),
                ('seller:orgname', ('entity:name', {}), {
                    'doc': 'The reported name of the seller org.',
                }),
                ('seller:orgfqdn', ('inet:fqdn', {}), {
                    'doc': 'The reported inet:fqdn of the seller org.',
                }),
                ('currency', ('econ:currency', {}), {
                    'doc': 'The currency of econ:price values associated with the deal.',
                }),
                ('buyer:budget', ('econ:price', {}), {
                    'doc': 'The buyers budget for the eventual purchase.',
                }),
                ('buyer:deadline', ('time', {}), {
                    'doc': 'When the buyer intends to make a decision.',
                }),
                ('offer:price', ('econ:price', {}), {
                    'doc': 'The total price of the offered products.',
                }),
                ('offer:expires', ('time', {}), {
                    'doc': 'When the offer expires.',
                }),
                ('purchase', ('econ:purchase', {}), {
                    'doc': 'Records a purchase resulting from the deal.',
                }),
            )),
            ('biz:bundle', {}, (
                ('count', ('int', {}), {
                    'doc': 'The number of instances of the product or service included in the bundle.',
                }),
                ('price', ('econ:price', {}), {
                    'doc': 'The price of the bundle.',
                }),
                ('product', ('biz:product', {}), {
                    'doc': 'The product included in the bundle.',
                }),
                ('service', ('biz:service', {}), {
                    'doc': 'The service included in the bundle.',
                }),
            )),
            ('biz:listing', {}, (

                ('seller', ('entity:actor', {}), {
                    'doc': 'The contact information for the seller.'}),

                ('product', ('biz:product', {}), {
                    'doc': 'The product being offered.'}),

                ('service', ('biz:service', {}), {
                    'doc': 'The service being offered.'}),

                ('current', ('bool', {}), {
                    'doc': 'Set to true if the offer is still current.'}),

                ('time', ('time', {}), {
                    'doc': 'The first known offering of this product/service by the organization for the asking price.'}),

                ('expires', ('time', {}), {
                    'doc': 'Set if the offer has a known expiration date.'}),

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
                ('provider', ('entity:actor', {}), {
                    'doc': 'The contact info of the entity which performs the service.'}),
                ('name', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'The name of the service being performed.'}),
                ('summary', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A brief summary of the service.'}),
                ('type', ('biz:service:type:taxonomy', {}), {
                    'doc': 'A taxonomy of service types.'}),
                ('launched', ('time', {}), {
                    'doc': 'The time when the operator first made the service available.'}),
                # TODO: billing types (fixed, hourly, subscription, etc)
            )),
            ('biz:product', {}, (
                ('name', ('str', {}), {
                    'doc': 'The name of the product.',
                }),
                ('type', ('biz:product:type:taxonomy', {}), {
                    'doc': 'The type of product.',
                }),
                # TODO ('upc', ('biz:upc', {}), {}),
                ('summary', ('str', {}), {
                    'doc': 'A brief summary of the product.',
                    'disp': {'hint': 'text'},
                }),
                # FIXME: manufactur?
                ('maker', ('entity:actor', {}), {
                    'doc': 'A contact for the maker of the product.',
                }),
                ('price:retail', ('econ:price', {}), {
                    'doc': 'The MSRP price of the product.',
                }),
                ('price:bottom', ('econ:price', {}), {
                    'doc': 'The minimum offered or observed price of the product.',
                }),
                ('price:currency', ('econ:currency', {}), {
                    'doc': 'The currency of the retail and bottom price properties.',
                }),
                ('bundles', ('array', {'type': 'biz:bundle', 'uniq': True, 'sorted': True}), {
                    'doc': 'An array of bundles included with the product.',
                }),
            )),
            ('biz:stake', {}, (
                ('vitals', ('ou:vitals', {}), {
                    'doc': 'The ou:vitals snapshot this stake is part of.',
                }),
                ('org', ('ou:org', {}), {
                    'doc': 'The resolved org.',
                }),
                ('org:name', ('entity:name', {}), {
                    'prevnames': ('orgname',),
                    'doc': 'The org name as reported by the source of the stake.',
                }),
                ('org:fqdn', ('inet:fqdn', {}), {
                    'doc': 'The org FQDN as reported by the source of the stake.',
                }),
                ('name', ('str', {}), {
                    'doc': 'An arbitrary name for this stake. Can be non-contact like "pool".',
                }),
                # FIXME asof -> updated ( in general? )
                ('asof', ('time', {}), {
                    'doc': 'The time the stake is being measured.',
                }),
                ('shares', ('int', {}), {
                    'doc': 'The number of shares represented by the stake.',
                }),
                ('invested', ('econ:price', {}), {
                    'doc': 'The amount of money invested in the cap table iteration.',
                }),
                ('value', ('econ:price', {}), {
                    'doc': 'The monetary value of the stake.',
                }),
                ('percent', ('hugenum', {}), {
                    'doc': 'The percentage ownership represented by this stake.',
                }),
                ('owner', ('entity:actor', {}), {
                    'doc': 'Contact information of the owner of the stake.',
                }),
                ('purchase', ('econ:purchase', {}), {
                    'doc': 'The purchase event for the stake.',
                }),
            )),
        ),
    }),
)
