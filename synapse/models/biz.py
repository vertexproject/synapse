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
                ('biz:bundle', ('guid', {}), {
                    'doc': 'Instances of a specific product offered for a price.',
                }),
                ('biz:product', ('guid', {}), {
                    'doc': 'A product which is available for purchase.',
                }),
                ('biz:dealstatus', ('taxonomy', {}), {
                    'doc': 'A deal/rfp status taxonomy.',
                    'interfaces': ('taxonomy',),
                }),
                ('biz:dealtype', ('taxonomy', {}), {
                    'doc': 'A deal type taxonomy.',
                    'interfaces': ('taxonomy',),
                }),
                ('biz:prodtype', ('taxonomy', {}), {
                    'doc': 'A product type taxonomy.',
                    'interfaces': ('taxonomy',),
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
                    # TODO
                    # -(deal:comms)>
                    # -(buyer:contacts)>
                    # -(seller:contacts)>
                )),
                ('biz:bundle', {}, (
                    ('count', ('int', {}), {
                        'doc': 'The number of instances of the product included in the bundle.',
                    }),
                    ('price', ('econ:price', {}), {
                        'doc': 'The price of the bundle.',
                    }),
                    ('product', ('biz:product', {}), {
                        'doc': 'The product included in the bundle.',
                    }),
                    ('deal', ('biz:deal', {}), {
                        'doc': 'The deal which includes this bundle.',
                    }),
                    ('purchase', ('econ:purchase', {}), {
                        'doc': 'The purchase which includes this bundle.',
                    }),
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
                    ('madeby:org', ('ou:org', {}), {
                        'doc': 'The product manufacturer.'
                    }),
                    ('madeby:orgname', ('ou:name', {}), {
                        'doc': 'The reported ou:name of the product manufacturer.'
                    }),
                    ('madeby:orgfqdn', ('inet:fqdn', {}), {
                        'doc': 'The reported inet:fqdn of the product manufacturer.'
                    }),
                    ('price:retail', ('econ:price', {}), {
                        'doc': 'The MSRP price of the product.',
                    }),
                    ('price:bottom', ('econ:price', {}), {
                        'doc': 'The minimum offered or observed price of the product.',
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
