import synapse.lib.module as s_module

'''
Model elements related to sales / bizdev / procurement
'''

class OuModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (
                ('biz:rfp', ('guid', {}), {}),
                ('biz:deal', ('guid', {}), {
                    'doc': 'A sales or procurement effort in pursuit of a purchase.',
                }),
                ('biz:product', ('guid', {}), {}),
                ('biz:produnit', ('guid', {}), {}),
                ('biz:rfpstatus', ('str', {'lower': True, 'strip': True, 'onespace': True}), {}),
                ('biz:dealstatus', ('str', {'lower': True, 'strip': True, 'onespace': True}), {}),
            ),
            'forms': (
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
                        'doc': 'The announcement URL for the solicitation.',
                    }),

                    ('posted', ('time', {}), {}),
                    ('quesdue', ('time', {}), {}),
                    ('propdue', ('time', {}), {}),

                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact information given for the org reqesting offers.',
                    }),
                    ('purchases', ('econ:purchase', {}), {
                        'doc': 'Any known purchases that resulted from the RFP.',
                    }),
                    ('requirements', ('array', {'type': 'ou:goal'}), {}),
                )),

                ('biz:deal', {}, (

                    # proposal / procurement / opportunity
                    ('title', ('str', {}), {
                        'doc': 'A title for the deal.',
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
                    ('currency', ('econ:currency', {}), {}),

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
                ('biz:produnit', {}, (
                    # order?  unit?  shipment? subscription?
                    ('deal', ('biz:deal', {}), {}),
                    ('purchase', ('econ:purchase', {}), {}),
                    ('product', ('biz:product', {}), {}),
                    ('price', ('econ:price', {}), {}),
                    ('count', ('int', {}), {}),
                    ('currency', ('econ:currency', {}), {}),
                    ('shipped', ('time', {}), {}),
                    ('delivered', ('time', {}), {}),
                    ('accepted', ('bool', {}), {}),
                    ('expires', ('time', {}), {}),
                )),
                ('biz:product', {}, (
                    ('name', ('str', {}), {
                        'doc': 'The name of the product.',
                    }),
                    # TODO properties to model subscriptions
                    # TODO ('upc', ('biz:upc', {}), {}),
                    ('summary', ('str', {}), {
                        'doc': 'A brief summary of the product.',
                        'disp': {'hint': 'text'},
                    }),
                    ('price:retail', ('econ:price', {}), {}),
                    ('price:bottom', ('econ:price', {}), {}),
                    ('bundles', ('array', {'type': 'biz:produnit', 'uniq': True, 'sorted': True}), {}),
                )),
            ),
        )
        name = 'biz'
        return ((name, modl),)
