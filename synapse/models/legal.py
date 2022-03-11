import synapse.lib.module as s_module

class LegalModule(s_module.CoreModule):
    def getModelDefs(self):
        modl = {
            'types': (
                ('legal:law', ('guid', {}), {}),
                ('legal:case', ('guid', {}), {}),
                ('legal:charge', ('guid', {}), {}),
                #('legal:sentence', ('guid', {}), {}),
                ('legal:indictment', ('guid', {}), {}),
                ('legal:casetype', ('taxonomy', {}), {
                    'interfaces': ('taxonomy',),
                }),
                ('legal:citation', ('str', {'lower': True, 'onespace': True, 'strip':True}), {}),
            ),
            'forms': (
                ('legal:law', {}, (
                    ('name', ('legal:citation', {}),
                    ('names', ('array', {'type': 'legal:citation'}), {}),

                    ('loc', ('loc', {}), {
                        'ex': 'us.va.reston',
                        'doc': 'The geopolitical jurisdiction of the law.',
                    }),

                    ('status', ('str', {'enum': ('proposed', 'enacted', 'withdrawn', 'struckdown')}), {}),

                    ('enacted', ('time', {}), {}),
                    ('proposed', ('time', {}), {}),
                    ('struckdown', ('time', {}), {}),

                    ('govbody', ('ou:org', {}),

                    ('url', ('inet:url', {}), {}),
                    ('file', ('file:bytes', {}), {}),
                )),
                ('legal:code', #('us', 'usc.18.1030.c.2.b.ii')
                    #('section', ('legal:section', {}), {
                        #'doc': 'The designation within the global taxonomy for this law.',
                        #'ex': 'us.title18',
                    #}),

                ('legal:case', {}, (
                    ('name', ('legal:citation', {}),
                    ('names', ('array', {'type': 'legal:citation'}), {}),

                    ('type', ('legal:casetype', {}),
                    #('eu:ecli', ('legal:eu:ecli', {}), {}),

                    ('venue', ('ps:contact', {}), {
                        'doc': 'The court which heard the case.',
                    }),
                    ('plaintiff', ('ps:contact', {}), {
                        'doc': 'Plaintiff contact information as provided in the case documents.',
                    }),
                    ('defendant', ('ps:contact', {}), {
                        'doc': 'Defendant contact information as provided in the case documents.',
                    }),

                    ('timeline', ('meta:timeline', {}), {}),

                    # may need these to be nodes for rico style cases...
                    #('sentence:pay:price', ...
                    #('sentence:emprisonment:type', ...
                    #('sentence:emprisonment:duration', ...

                    # how to handle appeals?
                )),
                #('legal:section', (), {}),
                ('legal:charge', {}, (
                    ('name', ('str', {'onespace': True, 'lower': True, 'strip': True}), {
                        'ex': 'voter intimidation',
                    }),
                    ('case', ('legal:case', {}), {}),
                    ('indictment', ('legal:indictment', {}), {}),
                    ('defendant', ('ps:contact', {}), {}),
                    
                    #('law', ('legal:case', {}), {}),
                    #('sections', ('array', 
                    #('citations', ('array', {'type': 'legal:citation'}), {}),

                    ('guilty', ('bool', {}), {}),
                )),
                ('legal:indictment', 
                    ('name', ('str', {'onespace': True, 'lower': True, 'strip': True}), {}),
                    ('issued', ('time', {}), {}),
                    ('file', ('file:bytes', {}), {}),
                    ('url', ('inet:url', {}), {}),
                ),
            ),
        }

        return (('legal', modl),)
