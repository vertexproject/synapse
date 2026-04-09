'''
Model elements related to sales / bizdev / procurement
'''
modeldefs = (
    ('biz', {
        'types': (

            ('biz:rfp:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of RFP types.'}),

            ('biz:rfp', ('guid', {}), {
                'template': {'title': 'RFP'},
                'interfaces': (
                    ('doc:document', {}),
                    ('doc:published', {}),
                ),
                'doc': 'An RFP (Request for Proposal) soliciting proposals.'}),

            ('biz:deal', ('guid', {}), {
                'interfaces': (
                    ('base:activity', {}),
                    ('meta:negotiable', {}),
                ),
                'doc': 'A sales or procurement effort in pursuit of a purchase.'}),

            ('biz:listing', ('guid', {}), {
                'template': {'title': 'listing'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'doc': 'A product or service being listed for sale.'}),

            ('biz:product', ('guid', {}), {
                'template': {'title': 'product'},
                'interfaces': (
                    ('meta:havable', {}),
                    ('entity:creatable', {}),
                ),
                'doc': 'A type of product which is available for purchase.'}),

            ('biz:service', ('guid', {}), {
                'template': {'title': 'service offering'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'doc': 'A service offered by an actor.'}),

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

        'edges': (
            (('biz:listing', 'has', 'econ:lineitem'), {
                'doc': 'The listing offers the line item.'}),

            (('biz:deal', 'has', 'econ:lineitem'), {
                'doc': 'The deal includes the line item.'}),

            (('biz:rfp', 'has', 'doc:requirement'), {
                'doc': 'The RFP lists the requirement.'}),

            (('biz:rfp', 'ledto', 'biz:deal'), {
                'doc': 'The RFP led to the deal being proposed.'}),

            (('biz:listing', 'ledto', 'econ:purchase'), {
                'doc': 'The listing led to the purchase.'}),

            (('biz:deal', 'ledto', 'econ:purchase'), {
                'doc': 'The deal led to the purchase.'}),
        ),

        'forms': (
            ('biz:deal:type:taxonomy', {
                'prevnames': ('biz:dealtype',)}, ()),

            ('biz:product:type:taxonomy', {
                'prevnames': ('biz:prodtype',)}, ()),

            ('biz:deal:status:taxonomy', {
                'prevnames': ('biz:dealstatus',)}, ()),

            ('biz:service:type:taxonomy', {}, ()),

            ('biz:rfp:type:taxonomy', {}, ()),
            ('biz:rfp', {}, (

                ('status', ('biz:deal:status:taxonomy', {}), {
                    'doc': 'The status of the RFP.'}),

                ('due:questions', ('time', {}), {
                    'prevnames': ('quesdue',),
                    'doc': 'The date/time that questions are due.'}),

                ('due:proposal', ('time', {}), {
                    'prevnames': ('propdue',),
                    'doc': 'The date/time that proposals are due.'}),
            )),
            ('biz:deal', {}, (

                ('id', ('base:id', {}), {
                    'doc': 'An identifier for the deal.'}),

                ('name', ('base:name', {}), {
                    'doc': 'The name of the deal.'}),

                ('type', ('biz:deal:type:taxonomy', {}), {
                    'doc': 'The type of deal.'}),

                ('status', ('biz:deal:status:taxonomy', {}), {
                    'doc': 'The status of the deal.'}),

                ('updated', ('time', {}), {
                    'doc': 'The last time the deal had a significant update.'}),

                ('contacted', ('time', {}), {
                    'doc': 'The last time the contacts communicated about the deal.'}),

                ('buyer', ('entity:actor', {}), {
                    'doc': 'The buyer.'}),

                ('buyer:name', ('entity:name', {}), {
                    'doc': 'The name of the the buyer.'}),

                ('seller', ('entity:actor', {}), {
                    'doc': 'The seller.'}),

                ('seller:name', ('entity:name', {}), {
                    'doc': 'The name of the seller.'}),
            )),

            ('biz:listing', {}, (

                ('name', ('base:name', {}), {
                    'doc': 'The name or title of the listing.'}),

                ('price', ('econ:price', {}), {
                    'doc': 'The asking price of the product or service.'}),

                ('count:total', ('int', {'min': 0}), {
                    'doc': 'The number of instances for sale.'}),

                ('count:remaining', ('int', {'min': 0}), {
                    'doc': 'The current remaining number of instances for sale.'}),
            )),
            ('biz:service', {}, (

                ('name', ('base:name', {}), {
                    'doc': 'The name of the service being performed.'}),

                ('period', ('ival', {}), {
                    'doc': 'The period of time when the actor made the service available.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the service.'}),

                ('type', ('biz:service:type:taxonomy', {}), {
                    'doc': 'A taxonomy of service types.'}),
            )),
            ('biz:product', {}, (

                ('name', ('base:name', {}), {
                    'doc': 'The name of the product.'}),

                ('type', ('biz:product:type:taxonomy', {}), {
                    'doc': 'The type of product.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the product.'}),

                ('launched', ('time', {}), {
                    'doc': 'The time the product was first made available.'}),

                ('price', ('econ:price', {}), {
                    'doc': 'The price of the product.'}),
            )),
        ),
    }),
)
