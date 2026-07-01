modeldefs = (
    {
        'interfaces': (

            ('doc:authorable', {
                'template': {'title': 'document'},
                'interfaces': (
                    ('entity:creatable', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'alts': ('ids',),
                        'doc': 'The {title} ID.'}),

                    ('ids', ('array', {'type': 'base:id'}), {
                        'doc': 'An array of alternate IDs for the {title}.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'The URL where the {title} is available.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time that the {title} was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time that the {title} was last updated.'}),

                    ('version', ('it:version', {}), {
                        'doc': 'The version of the {title}.'}),

                    ('supersedes', ('array', {'type': '{$self}'}), {
                        'doc': 'An array of {title} versions which are superseded by this {title}.'}),
                ),
                'doc': 'Properties common to authorable forms.'}),

            ('doc:document', {
                'template': {'title': 'document', 'syntax': ''},
                'interfaces': (
                    ('doc:authorable', {}),
                ),
                'props': (

                    ('type', ('{$self}:type:taxonomy', {}), {
                        'doc': 'The type of {title}.'}),

                    ('body', ('text', {}), {
                        'display': {'hint': 'text', 'syntax': '{syntax}'},
                        'doc': 'The text of the {title}.'}),

                    ('title', ('title', {}), {
                        'doc': 'The title of the {title}.'}),

                    ('file', ('file:bytes', {}), {
                        'doc': 'The file containing the {title} contents.'}),

                    ('file:name', ('file:base', {}), {
                        'doc': 'The name of the file containing the {title} contents.'}),

                    ('file:captured', ('time', {}), {
                        'doc': 'The time when the file content was captured.'}),
                ),
                'doc': 'A common interface for documents.'}),

            ('doc:published', {
                'template': {'title': 'report'},
                'props': (
                    ('public', ('bool', {}), {
                        'doc': 'Set to true if the {title} is publicly available.'}),

                    ('published', ('time', {}), {
                        'doc': 'The time the {title} was published.'}),

                    ('publisher', ('entity:actor', {}), {
                        'doc': 'The entity which published the {title}.'}),

                    ('publisher:name', ('entity:name', {}), {
                        'doc': 'The name of the entity which published the {title}.'}),

                    ('topics', ('array', {'type': 'meta:topic'}), {
                        'doc': 'The topics discussed in the {title}.'}),
                ),
                'doc': 'Properties common to published documents.'}),

            ('doc:signable', {
                'template': {'title': 'document'},
                'props': (
                    ('signed', ('time', {}), {
                        'doc': 'The date that the {title} signing was complete.'}),
                ),
                'doc': 'An interface implemented by documents which can be signed by actors.'}),
        ),
        'types': (

            ('doc:policy:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy of policy types.'}),

            ('doc:policy', ('guid', {}), {
                'template': {'title': 'policy'},
                'interfaces': (
                    ('doc:document', {}),
                ),
                'props': (),
                'doc': 'Guiding principles used to reach a set of goals.'}),

            ('doc:standard:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy of standard types.'}),

            ('doc:standard', ('guid', {}), {
                'template': {'title': 'standard'},
                'interfaces': (
                    ('doc:document', {}),
                ),
                'props': (
                    ('policy', ('doc:policy', {}), {
                        'doc': 'The policy which was used to derive the standard.'}),
                ),
                'doc': 'A group of requirements which define how to implement a policy or goal.'}),

            ('doc:requirement', ('guid', {}), {
                'template': {'title': 'requirement'},
                'interfaces': (
                    ('doc:authorable', {}),
                ),
                'props': (

                    ('text', ('text', {}), {
                        'doc': 'The requirement definition.'}),

                    ('optional', ('bool', {}), {
                        'doc': 'Set to true if the requirement is optional as defined by the standard.'}),

                    ('priority', ('meta:score', {}), {
                        'doc': 'The priority of the requirement as defined by the standard.'}),

                    ('standard', ('doc:standard', {}), {
                        'doc': 'The standard which defined the requirement.'}),
                ),
                'doc': 'A single requirement, often defined by a standard.'}),

            ('doc:resume:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A taxonomy of resume types.'}),

            ('doc:resume', ('guid', {}), {
                'template': {'title': 'resume'},
                'interfaces': (
                    ('doc:document', {}),
                ),
                'props': (

                    ('contact', ('entity:individual', {}), {
                        'doc': 'Contact information for subject of the resume.'}),

                    ('summary', ('text', {}), {
                        'doc': 'The summary of qualifications from the resume.'}),

                    ('skills', ('array', {'type': 'ps:skill'}), {
                        'doc': 'The skills described in the resume.'}),

                    ('workhist', ('array', {'type': 'ps:workhist'}), {
                        'doc': 'Work history described in the resume.'}),

                    ('education', ('array', {'type': 'entity:studied'}), {
                        'doc': 'Education experience described in the resume.'}),

                    ('achievements', ('array', {'type': 'entity:achieved'}), {
                        'doc': 'Achievements described in the resume.'}),

                ),
                'doc': 'A CV/resume document.'}),

            ('doc:report:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (('meta:taxonomy', {}),),
                'props': (),
                'doc': 'A taxonomy of report types.'}),

            ('doc:report', ('guid', {}), {
                'prevnames': ('media:news',),
                'template': {'title': 'report', 'syntax': 'markdown'},
                'interfaces': (
                    ('doc:document', {}),
                    ('doc:published', {}),
                ),
                'props': (),
                'doc': 'A report.'}),

            ('doc:contract', ('guid', {}), {
                'prevnames': ('ou:contract',),
                'template': {'title': 'contract'},
                'interfaces': (
                    ('doc:document', {}),
                    ('doc:signable', {}),
                    ('entity:activity', {}),
                ),
                'props': (),
                'doc': 'A contract between multiple entities.'}),

            ('doc:contract:type:taxonomy', ('taxonomy', {}), {
                'prevnames': ('ou:conttype',),
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of contract types.'}),

            ('doc:reference', ('guid', {}), {
                'props': (

                    ('source', (
                            ('doc:report', {}),
                            ('risk:vuln', {}),
                            ('it:software', {}),
                            ('risk:threat', {}),
                            ('entity:campaign', {}),
                            ('meta:technique', {}),
                            ('plan:phase', {}),
                        ), {
                        'doc': 'The source which contains the reference.'}),

                    ('text', ('title', {}), {
                        'doc': 'A reference string included in the source.'}),

                    ('doc', ('doc:document', {}), {
                        'doc': 'The document which the reference refers to.'}),

                    ('doc:url', ('inet:url', {}), {
                        'doc': 'A URL for the reference.'}),
                ),
                'doc': 'A reference included in a source.'}),

        ),
        'edges': (
            (('doc:contract', 'has', 'doc:requirement'), {
                'doc': 'The contract contains the requirement.'}),

            (('meta:technique', 'meets', 'doc:requirement'), {
                'doc': 'Use of the source technique meets the target requirement.'}),
        ),
    },
)
