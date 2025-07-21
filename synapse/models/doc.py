import synapse.exc as s_exc

modeldefs = (
    ('doc', {
        'interfaces': (

            ('doc:authorable', {
                'doc': 'Properties common to authorable forms.',
                'template': {'authorable': 'document'},
                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'The {authorable} ID.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the {authorable} is available.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {authorable}.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time that the {authorable} was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time that the {authorable} was last updated.'}),

                    ('author', ('entity:actor', {}), {
                        'doc': 'The contact information of the primary author.'}),

                    ('contributors', ('array', {'type': 'entity:actor', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of contacts which contributed to the {authorable}.'}),

                    ('version', ('it:semver', {}), {
                        'doc': 'The version of the {authorable}.'}),

                    ('supersedes', ('array', {'type': '$self', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of {authorable} versions which are superseded by this {authorable}.'}),
                ),
            }),
            ('doc:document', {

                'doc': 'A common interface for documents.',
                'interfaces': (
                    ('doc:authorable', {}),
                ),

                'template': {
                    'type': '{$self}:type:taxonomy',
                    'syntax': '',
                    'document': 'document'},

                'props': (

                    ('type', ('{type}', {}), {
                        'doc': 'The type of {authorable}.'}),

                    ('text', ('text', {}), {
                        'display': {'syntax': '{syntax}'},
                        'doc': 'The text of the {authorable}.'}),

                    ('title', ('str', {}), {
                        'doc': 'The title of the {authorable}.'}),

                    ('file', ('file:bytes', {}), {
                        'doc': 'The file containing the {authorable} contents.'}),

                    ('file:name', ('file:base', {}), {
                        'doc': 'The name of the file containing the {authorable} contents.'}),
                ),
            }),
        ),
        'types': (

            ('doc:policy:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of policy types.'}),

            ('doc:policy', ('guid', {}), {
                'interfaces': (
                    ('doc:document', {
                        'template': {
                            'authorable': 'policy',
                            'type': 'doc:policy:type:taxonomy'},
                    }),
                ),
                'doc': 'Guiding principles used to reach a set of goals.'}),

            ('doc:standard:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of standard types.'}),

            ('doc:standard', ('guid', {}), {
                'interfaces': (
                    ('doc:document', {
                        'template': {
                            'authorable': 'standard',
                            'type': 'doc:standard:type:taxonomy'}}),
                ),
                'doc': 'A group of requirements which define how to implement a policy or goal.'}),

            ('doc:requirement', ('guid', {}), {
                'interfaces': (
                    ('doc:authorable', {'template': {'authorable': 'requirement'}}),
                ),
                'doc': 'A single requirement, often defined by a standard.'}),

            ('doc:resume:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy of resume types.'}),

            ('doc:resume', ('guid', {}), {
                'interfaces': (
                    ('doc:document', {
                        'template': {
                            'authorable': 'resume',
                            'type': 'doc:resume:type:taxonomy'}}),
                ),
                'doc': 'A CV/resume document.'}),

            ('doc:report:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (('meta:taxonomy', {}),),
                'doc': 'A taxonomy of report types.'}),

            ('doc:report', ('guid', {}), {
                'prevnames': ('media:news',),
                'interfaces': (
                    ('doc:document', {'template': {
                        'authorable': 'report',
                        'type': 'doc:report:type:taxonomy'}}),
                ),
                'doc': 'A report.'}),

            ('doc:contract', ('guid', {}), {
                'prevnames': ('ou:contract',),
                'interfaces': (
                    ('doc:document', {'template': {
                        'authorable': 'contract',
                        'type': 'doc:contract:type:taxonomy'}}),
                ),
                'doc': 'A contract between multiple entities.'}),

            ('doc:contract:type:taxonomy', ('taxonomy', {}), {
                'prevnames': ('ou:conttype',),
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of contract types.'}),

        ),
        'edges': (
            (('doc:contract', 'has', 'doc:requirement'), {
                'doc': 'The contract contains the requirement.'}),
        ),
        'forms': (

            ('doc:policy:type:taxonomy', {}, ()),
            ('doc:policy', {}, ()),

            ('doc:standard:type:taxonomy', {}, ()),
            ('doc:standard', {}, (
                ('policy', ('doc:policy', {}), {
                    'doc': 'The policy which was used to derive the standard.'}),
            )),

            ('doc:requirement', {}, (

                ('text', ('text', {}), {
                    'doc': 'The requirement definition.'}),

                ('optional', ('bool', {}), {
                    'doc': 'Set to true if the requirement is optional as defined by the standard.'}),

                ('priority', ('meta:priority', {}), {
                    'doc': 'The priority of the requirement as defined by the standard.'}),

                ('standard', ('doc:standard', {}), {
                    'doc': 'The standard which defined the requirement.'}),
            )),

            ('doc:resume:type:taxonomy', {}, ()),
            ('doc:resume', {}, (

                ('contact', ('entity:individual', {}), {
                    'doc': 'Contact information for subject of the resume.'}),

                ('summary', ('text', {}), {
                    'doc': 'The summary of qualifications from the resume.'}),

                ('workhist', ('array', {'type': 'ps:workhist', 'sorted': True, 'uniq': True}), {
                    'doc': 'Work history described in the resume.'}),

                ('education', ('array', {'type': 'ps:education', 'sorted': True, 'uniq': True}), {
                    'doc': 'Education experience described in the resume.'}),

                ('achievements', ('array', {'type': 'ps:achievement', 'sorted': True, 'uniq': True}), {
                    'doc': 'Achievements described in the resume.'}),

            )),
            ('doc:report:type:taxonomy', {}, ()),
            ('doc:report', {}, (

                ('public', ('bool', {}), {
                    'doc': 'Set to true if the report is publicly available.'}),

                ('published', ('time', {}), {
                    'doc': 'The time the report was published.'}),

                ('publisher', ('entity:actor', {}), {
                    'doc': 'The entity which published the report.'}),

                ('publisher:name', ('meta:name', {}), {
                    'doc': 'The name of the entity which published the report.'}),
            )),

            ('doc:contract:type:taxonomy', {}, ()),
            ('doc:contract', {}, (

                ('issuer', ('entity:actor', {}), {
                    'prevnames': ('sponsor',),
                    'doc': 'The contract sponsor.'}),

                ('parties', ('array', {'type': 'entity:actor', 'uniq': True, 'sorted': True}), {
                    'doc': 'The entities bound by the contract.'}),

                ('signers', ('array', {'type': 'entity:individual', 'uniq': True, 'sorted': True}), {
                    'doc': 'The individuals who signed the contract.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time period when the contract is in effect.'}),

                ('signed', ('time', {}), {
                    'doc': 'The date that the contract signing was complete.'}),

                ('completed', ('time', {}), {
                    'doc': 'The date that the contract was completed.'}),

                ('terminated', ('time', {}), {
                    'doc': 'The date that the contract was terminated.'}),
            )),
        ),
        'edges': (),
    }),
)
