import synapse.lib.module as s_module

'''
Model elements related to sales / bizdev / procurement
'''

class BizModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (
                ('biz:rfp', ('guid', {}), {}),
                ('biz:deal', ('guid', {}), {
                    'doc': 'A sales or procurement effort in pursuit of a purchase.',
                }),
                ('biz:bundle', ('guid', {}), {
                    'doc': 'Instances of a specific product offered for a price.',
                }),
                ('biz:product', ('guid', {}), {
                    'doc': 'A product which is available for purchase.',
                }),
                ('biz:rfpstatus', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                    'doc': 'A unique status value for a biz:rfp:status.',
                }),
                ('biz:dealstatus', ('str', {'lower': True, 'strip': True, 'onespace': True}), {
                    'doc': 'A unique status value for a biz:deal:status.',
                }),
                ('biz:dealtype', ('taxonomy', {}), {
                    'doc': 'A deal type taxonomy.',
                    'interfaces': ('taxonomy',),
                }),
            ),
            'forms': (
                ('biz:dealtype', {}, ()),
                ('biz:rfpstatus', {}, ()),
                ('biz:dealstatus', {}, ()),
                ('biz:rfp', {}, (
                    ('ext:id', ('str', {}), {
                        'doc': 'An externally specified identifier for the RFP.',
                    }),
                    ('title', ('str', {}), {
                        'doc': 'The title of the RFP.',
                    }),
                    ('summary', ('str', {}), {
                        'doc': 'A brief summary of the RFP.',
                    }),
                    ('status', ('biz:rfpstatus', {}), {
                        'disp': {'hint': 'enum'},
                        'doc': 'The status of the RFP.',
                    }),
                    ('url', ('inet:url', {}), {
                        'doc': 'The official URL for the RFP.',
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
                        'doc': 'The contact information given for the org reqesting offers.',
                    }),
                    ('purchases', ('econ:purchase', {}), {
                        'doc': 'Any known purchases that resulted from the RFP.',
                    }),
                    ('requirements', ('array', {'type': 'ou:goal'}), {}),
                )),
                ('biz:deal', {}, (
                    ('title', ('str', {}), {
                        'doc': 'A title for the deal.',
                    }),
                    ('type', ('biz:dealtype', {}), {
                        'doc': 'The type of deal.',
                        'disp': {'hint': 'tree',
                                 'lift': 'biz:dealtype:depth=0',
                                 'walk': '-> biz:dealtype:parent'},
                    }),
                    ('status', ('biz:dealstatus', {}), {
                        'doc': 'The status of the deal.',
                        'disp': {'hint': 'enum'},
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
                    ('seller', ('ps:contact', {}), {
                        'doc': 'The primary contact information for the seller.',
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
                    # TODO ('upc', ('biz:upc', {}), {}),
                    ('summary', ('str', {}), {
                        'doc': 'A brief summary of the product.',
                        'disp': {'hint': 'text'},
                    }),
                    ('price:retail', ('econ:price', {}), {
                        'doc': 'The MSRP price of the product.',
                    }),
                    ('price:bottom', ('econ:price', {}), {
                        'doc': 'The minium offered or observed price of the product.',
                    }),
                    ('bundles', ('array', {'type': 'biz:bundle', 'uniq': True, 'sorted': True}), {
                        'doc': 'An array of bundles included with the product.',
                    }),
                )),
            ),
        )
        name = 'biz'
        return ((name, modl),)
