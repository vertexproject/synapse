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

            ('meta:id', ('str', {'strip': True}), {
                'doc': 'A case sensitive identifier string.'}),

            ('meta:name', ('str', {'onespace': True, 'strip': True}), {
                'doc': 'A case sensitive identifier string.'}),

            ('meta:feed', ('guid', {}), {
                'doc': 'A data feed provided by a specific source.'}),

            ('meta:feed:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A data feed type taxonomy.'}),

            ('meta:source', ('guid', {}), {
                'doc': 'A data source unique identifier.'}),

            ('meta:source', ('guid', {}), {
                'doc': 'A data source unique identifier.'}),

            ('meta:note', ('guid', {}), {
                'doc': 'An analyst note about nodes linked with -(about)> edges.'}),

            ('meta:note:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of note types.'}),

            ('meta:source:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of source types.'}),

            ('meta:timeline', ('guid', {}), {
                'doc': 'A curated timeline of analytically relevant events.'}),

            ('meta:timeline:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of timeline types.'}),

            ('meta:event', ('guid', {}), {
                'doc': 'An analytically relevant event in a curated timeline.'}),

            ('meta:event:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of event types.'}),

            ('meta:ruleset:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A taxonomy for meta:ruleset types.'}),

            ('meta:ruleset', ('guid', {}), {
                'doc': 'A set of rules linked with -(has)> edges.'}),

            ('meta:rule:type:taxonomy', ('taxonomy', {}), {
                'interfaces': ('meta:taxonomy',),
                'doc': 'A hierarchical taxonomy of rule types.'}),

            ('meta:rule', ('guid', {}), {
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
                'interfaces': ('meta:taxonomy',),
                'doc': 'A type of item being counted in aggregate.'}),

            ('meta:aggregate', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'type'}},
                        {'type': 'prop', 'opts': {'name': 'count'}},
                    ),
                },
                'doc': 'A node which represents an aggregate count of a specific type.'}),

            ('markdown', ('str', {}), {
                'doc': 'A markdown string.'}),
        ),
        'interfaces': (
            ('meta:taxonomy', {
                'doc': 'Properties common to taxonomies.',
                'props': (
                    ('title', ('str', {}), {
                        'doc': 'A brief title of the definition.'}),

                    ('desc', ('str', {}), {
                        'doc': 'A definition of the taxonomy entry.',
                        'disp': {'hint': 'text'}}),

                    ('sort', ('int', {}), {
                        'doc': 'A display sort order for siblings.'}),

                    ('base', ('taxon', {}), {
                        'ro': True,
                        'doc': 'The base taxon.'}),

                    ('depth', ('int', {}), {
                        'ro': True,
                        'doc': 'The depth indexed from 0.'}),

                    ('parent', ('$self', {}), {
                        'ro': True,
                        'doc': 'The taxonomy parent.'}),
                ),
            }),
        ),
        'edges': (
            ((None, 'refs', None), {
                'doc': 'The source node contains a reference to the target node.'}),

            (('meta:source', 'seen', None), {
                'doc': 'The meta:source observed the target node.'}),

            (('meta:feed', 'found', None), {
                'doc': 'The meta:feed produced the target node.'}),

            (('meta:note', 'about', None), {
                'doc': 'The meta:note is about the target node.'}),

            (('meta:ruleset', 'has', 'meta:rule'), {
                'doc': 'The meta:ruleset includes the meta:rule.'}),

            (('meta:rule', 'matches', None), {
                'doc': 'The meta:rule has matched on target node.'}),

            (('meta:rule', 'detects', None), {
                'doc': 'The meta:rule is designed to detect instances of the target node.'}),
        ),
        'forms': (

            ('meta:id', {}, ()),

            ('meta:source:type:taxonomy', {}, ()),
            ('meta:source', {}, (

                ('name', ('entity:name', {}), {
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

                ('name', ('entity:name', {}), {
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

                ('cursor', ('str', {'strip': True}), {
                    'doc': 'A cursor used to track ingest offset within the feed.'}),
            )),

            ('meta:note:type:taxonomy', {}, ()),
            ('meta:note', {}, (

                ('type', ('meta:note:type:taxonomy', {}), {
                    'doc': 'The note type.'}),

                ('text', ('str', {}), {
                    'disp': {'hint': 'text', 'syntax': 'markdown'},
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
                ('summary', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A prose summary of the timeline.'}),
                ('type', ('meta:timeline:type:taxonomy', {}), {
                    'doc': 'The type of timeline.'}),
            )),

            ('meta:timeline:type:taxonomy', {
                'prevnames': ('meta:timeline:taxonomy',)}, ()),

            ('meta:event', {}, (

                ('timeline', ('meta:timeline', {}), {
                    'doc': 'The timeline containing the event.'}),

                ('title', ('str', {}), {
                    'doc': 'A title for the event.'}),

                ('summary', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A prose summary of the event.'}),

                ('time', ('time', {}), {
                    'doc': 'The time that the event occurred.'}),

                ('index', ('int', {}), {
                    'doc': 'The index of this event in a timeline without exact times.'}),

                ('duration', ('duration', {}), {
                    'doc': 'The duration of the event.'}),

                ('type', ('meta:event:type:taxonomy', {}), {
                    'doc': 'Type of event.'}),
            )),

            ('meta:event:type:taxonomy', {
                'prevnames': ('meta:event:taxonomy',)}, ()),

            ('meta:ruleset', {}, (

                ('name', ('entity:name', {}), {
                    'doc': 'A name for the ruleset.'}),

                ('type', ('meta:ruleset:type:taxonomy', {}), {
                    'doc': 'The ruleset type.'}),

                ('desc', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A description of the ruleset.'}),

                ('author', ('entity:actor', {}), {
                    'doc': 'The contact information of the ruleset author.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the ruleset was initially created.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the ruleset was most recently modified.'}),
            )),

            ('meta:rule:type:taxonomy', {}, ()),
            ('meta:rule', {}, (

                ('id', ('meta:id', {}), {
                    'prevnames': ('ext:id',),
                    'doc': 'The rule ID.'}),

                ('name', ('entity:name', {}), {
                    'doc': 'A name for the rule.'}),

                ('type', ('meta:rule:type:taxonomy', {}), {
                    'doc': 'The rule type.'}),

                ('desc', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'A description of the rule.'}),

                ('text', ('str', {}), {
                    'disp': {'hint': 'text'},
                    'doc': 'The text of the rule logic.'}),

                ('author', ('entity:actor', {}), {
                    'doc': 'The contact information of the rule author.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the rule was initially created.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the rule was most recently modified.'}),

                ('url', ('inet:url', {}), {
                    'doc': 'A URL which documents the rule.'}),
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

        ),
    }),
)
