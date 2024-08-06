import synapse.lib.module as s_module

'''
Model elements related to sales / bizdev / procurement
'''

class BizModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
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
                    'doc': 'A taxonomy of service offering types.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('biz:dealstatus', ('taxonomy', {}), {
                    'doc': 'A deal/rfp status taxonomy.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('biz:dealtype', ('taxonomy', {}), {
                    'doc': 'A deal type taxonomy.',
                    'interfaces': ('meta:taxonomy',),
                }),
                ('biz:prodtype', ('taxonomy', {}), {
                    'doc': 'A product type taxonomy.',
                    'interfaces': ('meta:taxonomy',),
                }),
            ),
            'forms': (
                ('biz:dealtype', {}, ()),
                ('biz:prodtype', {}, ()),
                ('biz:dealstatus', {}, ()),
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
                    ('status', ('biz:dealstatus', {}), {
                        'disp': {'hint': 'enum'},
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
                    ('contact', ('ps:contact', {}), {
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
                    ('type', ('biz:dealtype', {}), {
                        'doc': 'The type of deal.',
                        'disp': {'hint': 'taxonomy'},
                    }),
                    ('status', ('biz:dealstatus', {}), {
                        'doc': 'The status of the deal.',
                        'disp': {'hint': 'taxonomy'},
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
                    ('buyer', ('ps:contact', {}), {
                        'doc': 'The primary contact information for the buyer.',
                    }),
                    ('buyer:org', ('ou:org', {}), {
                        'doc': 'The buyer org.',
                    }),
                    ('buyer:orgname', ('ou:name', {}), {
                        'doc': 'The reported ou:name of the buyer org.',
                    }),
                    ('buyer:orgfqdn', ('inet:fqdn', {}), {
                        'doc': 'The reported inet:fqdn of the buyer org.',
                    }),
                    ('seller', ('ps:contact', {}), {
                        'doc': 'The primary contact information for the seller.',
                    }),
                    ('seller:org', ('ou:org', {}), {
                        'doc': 'The seller org.',
                    }),
                    ('seller:orgname', ('ou:name', {}), {
                        'doc': 'The reported ou:name of the seller org.',
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
                    ('deal', ('biz:deal', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use econ:receipt:item for instances of bundles being sold.',
                    }),
                    ('purchase', ('econ:purchase', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use econ:receipt:item for instances of bundles being sold.',
                    }),
                )),
                ('biz:listing', {}, (

                    ('seller', ('ps:contact', {}), {
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
                    ('provider', ('ps:contact', {}), {
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
                    ('type', ('biz:prodtype', {}), {
                        'doc': 'The type of product.',
                        'disp': {'hint': 'taxonomy'},
                    }),
                    # TODO ('upc', ('biz:upc', {}), {}),
                    ('summary', ('str', {}), {
                        'doc': 'A brief summary of the product.',
                        'disp': {'hint': 'text'},
                    }),
                    ('maker', ('ps:contact', {}), {
                        'doc': 'A contact for the maker of the product.',
                    }),
                    ('madeby:org', ('ou:org', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use biz:product:maker.',
                    }),
                    ('madeby:orgname', ('ou:name', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use biz:product:maker.',
                    }),
                    ('madeby:orgfqdn', ('inet:fqdn', {}), {
                        'deprecated': True,
                        'doc': 'Deprecated. Please use biz:product:maker.',
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
                    ('orgname', ('ou:name', {}), {
                        'doc': 'The org name as reported by the source of the vitals.',
                    }),
                    ('orgfqdn', ('inet:fqdn', {}), {
                        'doc': 'The org FQDN as reported by the source of the vitals.',
                    }),
                    ('name', ('str', {}), {
                        'doc': 'An arbitrary name for this stake. Can be non-contact like "pool".',
                    }),
                    ('asof', ('time', {}), {
                        'doc': 'The time the stake is being measured. Likely as part of an ou:vitals.',
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
                    ('owner', ('ps:contact', {}), {
                        'doc': 'Contact information of the owner of the stake.',
                    }),
                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase event for the stake.',
                    }),
                )),
            ),
        }
        name = 'biz'
        return ((name, modl),)
