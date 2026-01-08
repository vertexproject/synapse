sophenums = (
    (10, 'very low'),
    (20, 'low'),
    (30, 'medium'),
    (40, 'high'),
    (50, 'very high'),
)

prioenums = (
    (0, 'none'),
    (10, 'lowest'),
    (20, 'low'),
    (30, 'medium'),
    (40, 'high'),
    (50, 'highest'),
)

modeldefs = (
    ('base', {
        'types': (

            ('date', ('time', {'precision': 'day'}), {
                'doc': 'A date precision time value.'}),

            ('base:id', ('str', {}), {
                'doc': 'A base type for ID strings.'}),

            ('meta:id', ('base:id', {}), {
                'interfaces': (('entity:identifier', {}), ),
                'doc': 'A case sensitive identifier string.'}),

            ('base:name', ('str', {'onespace': True, 'lower': True}), {
                'doc': 'A base type for case insensitive names.'}),

            ('meta:name', ('base:name', {}), {
                'prevnames': ('meta:name', 'ou:name', 'ou:industryname',
                              'ou:campname', 'ou:goalname', 'lang:name',
                              'risk:vulnname', 'meta:name', 'it:prod:softname',
                              'entity:name', 'geo:name'),
                'doc': 'A name used to refer to an entity or event.'}),

            ('meta:topic', ('base:name', {}), {
                'doc': 'A topic string.'}),

            ('meta:feed', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'source::name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                },
                'doc': 'A data feed provided by a specific source.'}),

            ('meta:feed:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A data feed type taxonomy.'}),

            ('meta:source', ('guid', {}), {
                'doc': 'A data source unique identifier.'}),

            ('meta:note', ('guid', {}), {
                'doc': 'An analyst note about nodes linked with -(about)> edges.'}),

            ('meta:note:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of note types.'}),

            ('meta:source:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of source types.'}),

            ('meta:timeline', ('guid', {}), {
                'doc': 'A curated timeline of analytically relevant events.'}),

            ('meta:timeline:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of timeline types.'}),

            ('meta:event', ('guid', {}), {
                'doc': 'An analytically relevant event in a curated timeline.'}),

            ('meta:event:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of event types.'}),

            ('meta:ruleset:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy for meta:ruleset types.'}),

            ('meta:ruleset', ('guid', {}), {
                'interfaces': (
                    ('doc:authorable', {'template': {'title': 'ruleset'}}),
                ),
                'doc': 'A set of rules linked with -(has)> edges.'}),

            ('meta:rule:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of rule types.'}),

            ('meta:rule', ('guid', {}), {
                'interfaces': (
                    ('doc:authorable', {'template': {'title': 'rule', 'syntax': ''}}),
                ),
                'doc': 'A generic rule linked to matches with -(matches)> edges.'}),

            ('meta:activity', ('int', {'enums': prioenums, 'enums:strict': False}), {
                'doc': 'A generic activity level enumeration.'}),

            ('meta:priority', ('int', {'enums': prioenums, 'enums:strict': False}), {
                'doc': 'A generic priority enumeration.'}),

            ('meta:severity', ('int', {'enums': prioenums, 'enums:strict': False}), {
                'doc': 'A generic severity enumeration.'}),

            ('meta:sophistication', ('int', {'enums': sophenums}), {
                'doc': 'A sophistication score with named values: very low, low, medium, high, and very high.'}),

            ('meta:aggregate:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A type of item being counted in aggregate.'}),

            ('meta:aggregate', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'time'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                        {'type': 'prop', 'opts': {'name': 'count'}},
                    ),
                },
                'doc': 'A node which represents an aggregate count of a specific type.'}),

            ('meta:havable', ('ndef', {'interface': 'meta:havable'}), {
                'doc': 'An item which may be possessed by an entity.'}),

            ('text', ('str', {'strip': False}), {
                'doc': 'A multi-line, free form text string.'}),

            ('meta:technique', ('guid', {}), {
                'template': {'title': 'technique'},
                'doc': 'A specific technique used to achieve a goal.',
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:reported', {}),
                    ('risk:mitigatable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                        {'type': 'prop', 'opts': {'name': 'tag'}},
                    ),
                }}),

            ('meta:technique:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of technique types.'}),
        ),
        'interfaces': (

            ('meta:observable', {
                'doc': 'Properties common to forms which can be observed.',
                'template': {'title': 'node'},
                'props': (
                    ('seen', ('ival', {}), {
                        'doc': 'The {title} was observed during the time interval.'}),
                ),
            }),

            ('meta:havable', {
                'doc': 'An interface used to describe items that can be possessed by an entity.',
                'template': {'title': 'item'},
                'props': (

                    ('owner', ('entity:actor', {}), {
                        'doc': 'The current owner of the {title}.'}),

                    ('owner:name', ('meta:name', {}), {
                        'doc': 'The name of the current owner of the {title}.'}),
                ),
            }),

            ('meta:reported', {
                'doc': 'Properties common to forms which are created on a per-source basis.',
                'template': {'title': 'item'},
                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'A unique ID given to the {title} by the source.'}),

                    ('name', ('meta:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {title} according to the source.'}),

                    ('names', ('array', {'type': 'meta:name'}), {
                        'doc': 'A list of alternate names for the {title} according to the source.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}, according to the source.'}),

                    ('reporter', ('entity:actor', {}), {
                        'doc': 'The entity which reported on the {title}.'}),

                    ('reporter:name', ('meta:name', {}), {
                        'doc': 'The name of the entity which reported on the {title}.'}),

                    ('reporter:created', ('time', {}), {
                        'doc': 'The time when the reporter first created the {title}.'}),

                    ('reporter:updated', ('time', {}), {
                        'doc': 'The time when the reporter last updated the {title}.'}),

                    ('reporter:published', ('time', {}), {
                        'doc': 'The time when the reporter published the {title}.'}),

                    ('reporter:discovered', ('time', {}), {
                        'doc': 'The time when the reporter first discovered the {title}.'}),

                ),
            }),

            ('meta:taxonomy', {
                'doc': 'Properties common to taxonomies.',
                'props': (
                    ('title', ('str', {}), {
                        'doc': 'A brief title of the definition.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A definition of the taxonomy entry.'}),

                    ('sort', ('int', {}), {
                        'doc': 'A display sort order for siblings.'}),

                    ('base', ('taxon', {}), {
                        'computed': True,
                        'doc': 'The base taxon.'}),

                    ('depth', ('int', {}), {
                        'computed': True,
                        'doc': 'The depth indexed from 0.'}),

                    ('parent', ('$self', {}), {
                        'computed': True,
                        'doc': 'The taxonomy parent.'}),
                ),
            }),

            ('meta:usable', {
                'doc': 'An interface for forms which can be used by an actor.'}),

            ('meta:matchish', {
                'doc': 'Properties which are common to matches based on rules.',
                'template': {'rule': 'rule', 'rule:type': 'rule:type',
                             'target:type': 'ndef'},
                'props': (

                    ('rule', ('{rule:type}', {}), {
                        'doc': 'The rule which matched the target node.'}),

                    ('target', ('{target:type}', {}), {
                        'doc': 'The target node which matched the {rule}.'}),

                    ('version', ('it:version', {}), {
                        'doc': 'The most recent version of the rule evaluated as a match.'}),

                    ('matched', ('time', {}), {
                        'doc': 'The time that the rule was evaluated to generate the match.'}),
                ),
            }),
        ),
        'edges': (
            ((None, 'linked', None), {
                'doc': 'The source node is linked to the target node.'}),

            ((None, 'refs', None), {
                'doc': 'The source node contains a reference to the target node.'}),

            (('meta:source', 'seen', None), {
                'doc': 'The meta:source observed the target node.'}),

            (('meta:feed', 'found', None), {
                'doc': 'The meta:feed produced the target node.'}),

            (('meta:note', 'about', None), {
                'doc': 'The meta:note is about the target node.'}),

            (('meta:note', 'has', 'file:attachment'), {
                'doc': 'The note includes the file attachment.'}),

            (('meta:ruleset', 'has', 'meta:rule'), {
               'doc': 'The ruleset includes the rule.'}),

            (('meta:rule', 'matches', None), {
                'doc': 'The rule matched on the target node.'}),

            (('meta:rule', 'detects', 'meta:usable'), {
                'doc': 'The rule is designed to detect the target node.'}),

            (('meta:rule', 'detects', 'meta:observable'), {
                'doc': 'The rule is designed to detect the target node.'}),

            (('meta:usable', 'uses', 'meta:usable'), {
                'doc': 'The source node uses the target node.'}),

            # TODO - meta:technique addresses meta:usable?
            # TODO - OR meta:technique addresses risk:mitigatable?
            (('meta:technique', 'addresses', 'meta:technique'), {
                'doc': 'The technique addresses the technique.'}),

            (('meta:technique', 'addresses', 'risk:vuln'), {
                'doc': 'The technique addresses the vulnerability.'}),

            # TODO: should meta:rule and it:hardward be usable, and therefore covered
            (('meta:technique', 'uses', 'meta:rule'), {
                'doc': 'The technique uses the rule.'}),

            (('meta:technique', 'uses', 'it:software'), {
                'doc': 'The technique uses the software version.'}),

            (('meta:technique', 'uses', 'it:hardware'), {
                'doc': 'The technique uses the hardware.'}),
        ),
        'forms': (

            ('meta:id', {}, ()),
            ('meta:name', {}, ()),
            ('meta:topic', {}, (
                ('desc', ('text', {}), {
                    'doc': 'A description of the topic.'}),
            )),

            ('meta:source:type:taxonomy', {}, ()),
            ('meta:source', {}, (

                ('name', ('meta:name', {}), {
                    'doc': 'A human friendly name for the source.'}),

                ('type', ('meta:source:type:taxonomy', {}), {
                    'doc': 'The type of source.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'A URL which documents the meta source.'}),

                ('ingest:cursor', ('str', {}), {
                    'doc': 'Used by ingest logic to capture the current ingest cursor within a feed.'}),

                ('ingest:latest', ('time', {}), {
                    'doc': 'Used by ingest logic to capture the last time a feed ingest ran.'}),

                ('ingest:offset', ('int', {}), {
                    'doc': 'Used by ingest logic to capture the current ingest offset within a feed.'}),
            )),

            ('meta:feed:type:taxonomy', {}, ()),
            ('meta:feed', {}, (
                ('id', ('meta:id', {}), {
                    'doc': 'An identifier for the feed.'}),

                ('name', ('meta:name', {}), {
                    'doc': 'A name for the feed.'}),

                ('type', ('meta:feed:type:taxonomy', {}), {
                    'doc': 'The type of data feed.'}),

                ('source', ('meta:source', {}), {
                    'doc': 'The meta:source which provides the feed.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'The URL of the feed API endpoint.'}),

                ('query', ('str', {}), {
                    'doc': 'The query logic associated with generating the feed output.'}),

                ('opts', ('data', {}), {
                    'doc': 'An opaque JSON object containing feed parameters and options.'}),

                ('period', ('ival', {}), {
                    'doc': 'The time window over which results have been ingested.'}),

                ('latest', ('time', {}), {
                    'doc': 'The time of the last record consumed from the feed.'}),

                ('offset', ('int', {}), {
                    'doc': 'The offset of the last record consumed from the feed.'}),

                ('cursor', ('str', {}), {
                    'doc': 'A cursor used to track ingest offset within the feed.'}),
            )),

            ('meta:note:type:taxonomy', {}, ()),
            ('meta:note', {}, (

                ('type', ('meta:note:type:taxonomy', {}), {
                    'doc': 'The note type.'}),

                ('text', ('text', {}), {
                    'display': {'syntax': 'markdown'},
                    'doc': 'The analyst authored note text.'}),

                ('author', ('entity:actor', {}), {
                    'doc': 'The contact information of the author.'}),

                ('creator', ('syn:user', {}), {
                    'doc': 'The synapse user who authored the note.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the note was created.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the note was updated.'}),

                ('replyto', ('meta:note', {}), {
                    'doc': 'The note is a reply to the specified note.'}),
            )),

            ('meta:timeline', {}, (

                ('title', ('str', {}), {
                    'ex': 'The history of the Vertex Project',
                    'doc': 'A title for the timeline.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the timeline.'}),

                ('type', ('meta:timeline:type:taxonomy', {}), {
                    'doc': 'The type of timeline.'}),
            )),

            ('meta:timeline:type:taxonomy', {
                'prevnames': ('meta:timeline:taxonomy',)}, ()),

            ('meta:event', {}, (

                ('period', ('ival', {}), {
                    'doc': 'The period over which the event occurred.'}),

                ('timeline', ('meta:timeline', {}), {
                    'doc': 'The timeline containing the event.'}),

                ('title', ('str', {}), {
                    'doc': 'A title for the event.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the event.'}),

                ('index', ('int', {}), {
                    'doc': 'The index of this event in a timeline without exact times.'}),

                ('type', ('meta:event:type:taxonomy', {}), {
                    'doc': 'Type of event.'}),
            )),

            ('meta:event:type:taxonomy', {
                'prevnames': ('meta:event:taxonomy',)}, ()),

            ('meta:ruleset', {}, (

                ('name', ('base:id', {}), {
                    'doc': 'A name for the ruleset.'}),

                ('type', ('meta:ruleset:type:taxonomy', {}), {
                    'doc': 'The ruleset type.'}),
            )),

            ('meta:rule:type:taxonomy', {}, ()),
            ('meta:rule', {}, (

                ('name', ('base:id', {}), {
                    'doc': 'The rule name.'}),

                ('type', ('meta:rule:type:taxonomy', {}), {
                    'doc': 'The rule type.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'A URL which documents the {title}.'}),

                ('enabled', ('bool', {}), {
                    'doc': 'The enabled status of the {title}.'}),

                ('text', ('text', {}), {
                    'display': {'syntax': '{syntax}'},
                    'doc': 'The text of the {title}.'})
            )),

            ('meta:aggregate:type:taxonomy', {}, ()),
            ('meta:aggregate', {}, (

                ('type', ('meta:aggregate:type:taxonomy', {}), {
                    'ex': 'casualties.civilian',
                    'doc': 'The type of items being counted in aggregate.'}),

                ('time', ('time', {}), {
                    'doc': 'The time that the count was computed.'}),

                ('count', ('int', {}), {
                    'doc': 'The number of items counted in aggregate.'}),
            )),

            ('meta:technique', {}, (

                ('type', ('meta:technique:type:taxonomy', {}), {
                    'doc': 'The taxonomy classification of the technique.'}),

                ('sophistication', ('meta:sophistication', {}), {
                    'doc': 'The assessed sophistication of the technique.'}),

                ('tag', ('syn:tag', {}), {
                    'doc': 'The tag used to annotate nodes where the technique was employed.'}),

                ('parent', ('meta:technique', {}), {
                    'doc': 'The parent technique for the technique.'}),
            )),

            ('meta:technique:type:taxonomy', {}, ()),

        ),
    }),
)
