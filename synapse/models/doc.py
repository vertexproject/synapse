import synapse.exc as s_exc
import synapse.lib.module as s_module

class DocModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('doc', {
            'interfaces': (
                ('doc:document', {

                    'doc': 'A common interface for documents.',

                    'template': {
                        'type': 'NEWP',
                        'document': 'document',
                        'documents': 'documents'},

                    'props': (

                        ('id', ('str', {'strip': True}), {
                            'doc': 'The {document} ID.'}),

                        ('name', ('str', {'lower': True, 'onespace': True}), {
                            'doc': 'The {document} name.'}),

                        ('type', ('{type}', {}), {
                            'doc': 'The type of {document}.'}),

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
                            'doc': 'An array of contacts which contributed to the {document}.'}),

                        ('version', ('it:semver', {}), {
                            'doc': 'The version of the {document}.'}),

                        ('supersedes', ('array', {'type': '$self', 'sorted': True, 'uniq': True}), {
                            'doc': 'An array of {documents} which are superseded by this {document}.'}),
                    ),
                }),
            ),
            'types': (

                ('doc:policy:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of policy types.'}),

                ('doc:policy', ('guid', {}), {
                    'interfaces': ('doc:document',),
                    'template': {
                        'document': 'policy',
                        'documents': 'policies',
                        'type': 'doc:policy:type:taxonomy'},
                    'doc': 'Guiding principles used to reach a set of goals.'}),

                ('doc:standard:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of standard types.'}),

                ('doc:standard', ('guid', {}), {
                    'interfaces': ('doc:document',),
                    'template': {
                        'document': 'standard',
                        'documents': 'standards',
                        'type': 'doc:standard:type:taxonomy'},
                    'doc': 'A group of requirements which define how to implement a policy or goal.'}),

                ('doc:requirement:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of requirement types.'}),

                ('doc:requirement', ('guid', {}), {
                    'interfaces': ('doc:document',),
                    'template': {
                        'document': 'requirement',
                        'documents': 'requirements',
                        'type': 'doc:requirement:type:taxonomy'},
                    'doc': 'A single requirement, often defined by a standard.'}),

                ('doc:resume:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of resume types.'}),

                ('doc:resume', ('guid', {}), {
                    'interfaces': ('doc:document',),
                    'template': {
                        'document': 'resume',
                        'documents': 'resumes',
                        'type': 'doc:resume:type:taxonomy'},
                    'doc': 'A CV/resume document.'}),
            ),
            'forms': (

                ('doc:policy:type:taxonomy', {}, ()),
                ('doc:policy', {}, ()),

                ('doc:standard:type:taxonomy', {}, ()),
                ('doc:standard', {}, (
                    ('policy', ('doc:policy', {}), {
                        'doc': 'The policy which was used to derive the standard.'}),
                )),

                ('doc:requirement:type:taxonomy', {}, ()),
                ('doc:requirement', {}, (

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A summary of the requirement definition.'}),

                    ('optional', ('bool', {}), {
                        'doc': 'Set to true if the requirement is optional as defined by the standard.'}),

                    ('priority', ('meta:priority', {}), {
                        'doc': 'The priority of the requirement as defined by the standard.'}),

                    ('standard', ('doc:standard', {}), {
                        'doc': 'The standard which defined the requirement.'}),
                )),

                ('doc:resume:type:taxonomy', {}, ()),
                ('doc:resume', {}, (

                    ('contact', ('ps:contact', {}), {
                        'doc': 'Contact information for subject of the resume.'}),

                    ('summary', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The summary of qualifications from the resume.'}),

                    ('workhist', ('array', {'type': 'ps:workhist', 'sorted': True, 'uniq': True}), {
                        'doc': 'Work history described in the resume.'}),

                    ('education', ('array', {'type': 'ps:education', 'sorted': True, 'uniq': True}), {
                        'doc': 'Education experience described in the resume.'}),

                    ('achievements', ('array', {'type': 'ps:achievement', 'sorted': True, 'uniq': True}), {
                        'doc': 'Achievements described in the resume.'}),

                )),
            ),
            'edges': (),
        }),)
