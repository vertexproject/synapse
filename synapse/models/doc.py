import synapse.exc as s_exc
import synapse.lib.module as s_module

class DocModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('doc', {
            'interfaces': (
                ('doc:document', {
                    'template': {'document': 'document'},
                    'props': (

                        ('id', ('str', {'strip': True}), {
                            'doc': 'The {document} ID.'}),

                        ('name', ('str', {'lower': True, 'onespace': True}), {
                            'doc': 'The {document} name.'}),

                        ('text', ('str', {}), {
                            'doc': 'The text of the {document}.'}),

                        ('file', ('file:bytes', {}), {
                            'doc': 'The file which contains the {document}.'}),

                        ('created', ('time', {}), {
                            'doc': 'The time that the {document} was created.'}),

                        ('updated', ('time', {}), {
                            'doc': 'The time that the {document} was last updated.'}),

                        ('author', ('ps:contact', {}), {
                            'doc': 'The contact information of the primary author.'}),

                        ('contributors', ('array', {'type': 'ps:contact', 'sorted': True, 'uniq': True}), {
                            'doc': 'An array of contacts which contributed to the {document}'}),

                        ('version', ('it:semver', {}), {
                            'doc': 'The version of the {document}.'}),

                        ('supersedes', ('array', {'type': '$self', 'sorted': True, 'uniq': True}), {
                            'doc': 'An array of {document}s which are superseded by this {document}.'}),
                    ),
                }),
            ),
            'types': (

                ('doc:policy:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of policy types.'}),

                ('doc:policy', ('guid', {}), {
                    'interfaces': ('doc:document',),
                    'template': {'document': 'policy'},
                    'doc': 'Guiding principles used to reach a set of goals.'}),

                ('doc:standard:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of standard types.'}),

                ('doc:standard', ('guid', {}), {
                    'interfaces': ('doc:document',),
                    'template': {'document': 'standard'},
                    'doc': 'A group of requirements which define how to implement a policy or goal.'}),
            ),
            'forms': (

                ('doc:policy:type:taxonomy', {}, ()),
                ('doc:policy', {}, ()),

                ('doc:standard:type:taxonomy', {}, ()),
                ('doc:standard', {}, (
                    ('policy', ('ou:policy', {}), {
                        'doc': 'The policy which was used to derive the standard.'}),
                )),
            ),
            'edges': (),
        }),)
