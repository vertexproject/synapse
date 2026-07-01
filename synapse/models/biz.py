'''
Model elements related to sales / bizdev / procurement
'''
modeldefs = (
    {
        'interfaces': (
            ('biz:manufactured', {
                'template': {'title': 'item'},
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'The name of the {title}.'}),

                    ('model', ('biz:model', {}), {
                        'doc': 'The model number or name of the {title}.'}),
                ),
                'doc': 'Properties common to items being manufactured.'}),
        ),

        'types': (

            ('biz:model', ('base:id', {}), {
                'props': (),
                'doc': 'A model name or number for a product.'}),

            ('biz:rfp:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of RFP types.'}),

            ('biz:rfp', ('guid', {}), {
                'template': {'title': 'RFP'},
                'interfaces': (
                    ('doc:document', {}),
                    ('doc:published', {}),
                ),
                'props': (

                    ('status', ('title', {}), {
                        'doc': 'The status of the RFP.'}),

                    ('due:questions', ('time', {}), {
                        'prevnames': ('quesdue',),
                        'doc': 'The date/time that questions are due.'}),

                    ('due:proposal', ('time', {}), {
                        'prevnames': ('propdue',),
                        'doc': 'The date/time that proposals are due.'}),
                ),
                'doc': 'An RFP (Request for Proposal) soliciting proposals.'}),

            ('biz:deal', ('guid', {}), {
                'interfaces': (
                    ('base:activity', {}),
                    ('meta:negotiable', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'doc': 'An identifier for the deal.'}),

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the deal.'}),

                    ('type', ('biz:deal:type:taxonomy', {}), {
                        'doc': 'The type of deal.'}),

                    ('status', ('title', {}), {
                        'doc': 'The status of the deal.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The last time the deal had a significant update.'}),

                    ('contacted', ('time', {}), {
                        'doc': 'The last time the contacts communicated about the deal.'}),

                    ('buyer', ('entity:actor', {}), {
                        'doc': 'The buyer.'}),

                    ('buyer:name', ('entity:name', {}), {
                        'doc': 'The name of the buyer.'}),

                    ('seller', ('entity:actor', {}), {
                        'doc': 'The seller.'}),

                    ('seller:name', ('entity:name', {}), {
                        'doc': 'The name of the seller.'}),
                ),
                'doc': 'A sales or procurement effort in pursuit of a purchase.'}),

            ('biz:listing', ('guid', {}), {
                'template': {'title': 'listing', 'verb': 'posted'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The name or title of the listing.'}),

                    ('price', ('econ:price', {}), {
                        'doc': 'The asking price of the product or service.'}),

                    ('count:total', ('int:min0', {}), {
                        'doc': 'The number of instances for sale.'}),

                    ('count:remaining', ('int:min0', {}), {
                        'doc': 'The current remaining number of instances for sale.'}),
                ),
                'doc': 'A product or service being listed for sale.'}),

            ('biz:product', ('guid', {}), {
                'template': {'title': 'product'},
                'interfaces': (
                    ('meta:havable', {}),
                    ('entity:creatable', {}),
                ),
                'props': (

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
                ),
                'doc': 'A type of product which is available for purchase.'}),

            ('biz:service', ('guid', {}), {
                'template': {'title': 'service offering', 'verb': 'provided'},
                'interfaces': (
                    ('entity:activity', {}),
                ),
                'props': (

                    ('name', ('base:name', {}), {
                        'doc': 'The name of the service being performed.'}),

                    ('period', None, {
                        'doc': 'The period of time when the actor made the service available.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the service.'}),

                    ('type', ('biz:service:type:taxonomy', {}), {
                        'doc': 'The type of service.'}),
                ),
                'doc': 'A service offered by an actor.'}),

            ('biz:service:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of service types.'}),

            ('biz:deal:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('biz:dealtype',),
                'props': (),
                'doc': 'A hierarchical taxonomy of deal types.'}),

            ('biz:product:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('biz:prodtype',),
                'props': (),
                'doc': 'A hierarchical taxonomy of product types.'}),
        ),

        'edges': (
            (('biz:listing', 'has', 'econ:lineitem'), {
                'doc': 'The listing offers the line item.'}),

            (('biz:deal', 'has', 'econ:lineitem'), {
                'doc': 'The deal includes the line item.'}),

            (('biz:product', 'has', 'econ:lineitem'), {
                'doc': 'The product is offered via the line item.'}),

            (('biz:product', 'has', 'meta:havable'), {
                'doc': 'The product includes the item.'}),

            (('biz:rfp', 'has', 'doc:requirement'), {
                'doc': 'The RFP lists the requirement.'}),

            (('biz:rfp', 'ledto', 'biz:deal'), {
                'doc': 'The RFP led to the deal being proposed.'}),

            (('biz:listing', 'ledto', 'econ:purchase'), {
                'doc': 'The listing led to the purchase.'}),

            (('biz:deal', 'ledto', 'econ:purchase'), {
                'doc': 'The deal led to the purchase.'}),
        ),

    },
)
