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

            ('base:id', ('str', {'strip': True}), {
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
                'doc': 'A name used to refer to a entity or event.'}),

            ('meta:feed', ('guid', {}), {
                'doc': 'A data feed provided by a specific source.'}),

            ('meta:feed:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A data feed type taxonomy.'}),

            ('meta:source', ('guid', {}), {
                'doc': 'A data source unique identifier.'}),

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
                'doc': 'A set of rules linked with -(has)> edges.'}),

            ('meta:rule:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of rule types.'}),

            ('meta:rule', ('guid', {}), {
                'interfaces': (
                    ('meta:ruleish', {}),
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
                        {'type': 'prop', 'opts': {'name': 'type'}},
                        {'type': 'prop', 'opts': {'name': 'count'}},
                    ),
                },
                'doc': 'A node which represents an aggregate count of a specific type.'}),

            ('meta:havable', ('ndef', {'interface': 'meta:havable'}), {
                'doc': 'An item which may be possessed by an entity.'}),

            ('text', ('str', {'strip': False}), {
                'doc': 'A multi-line, free form text string.'}),
        ),
        'interfaces': (

            ('meta:observable', {
                'doc': 'Properties common to forms which can be observed.',
                'template': {'observable': 'node'},
                'props': (
                    ('seen', ('ival', {}), {
                        'doc': 'The {observable} was observed during the time interval.'}),
                ),
            }),

            ('meta:havable', {
                'doc': 'An interface used to describe items that can be possessed by an entity.',
            }),

            ('meta:sourced', {
                'doc': 'Properties common to forms which are created on a per-source basis.',
                'template': {'sourced': 'item'},
                'props': (

                    ('id', ('meta:id', {}), {
                        'doc': 'A unique ID given to the {sourced} by the source.'}),

                    ('name', ('meta:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {sourced} according to the source.'}),

                    ('names', ('array', {'type': 'meta:name', 'sorted': True, 'uniq': True}), {
                        'doc': 'A list of alternate names for the {sourced} according to the source.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {sourced}, according to the source.'}),

                    ('source', ('entity:actor', {}), {
                        'prevnames': ('reporter',),
                        'doc': 'The entity which was the source of the {sourced}.'}),

                    ('source:name', ('meta:name', {}), {
                        'prevnames': ('reporter:name',),
                        'doc': 'The name of the entity which was the source of the {sourced}.'}),

                    ('source:created', ('time', {}), {
                        'doc': 'The time when the source first created the {sourced}.'}),

                    ('source:updated', ('time', {}), {
                        'doc': 'The time when the source last updated the {sourced}.'}),
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
            ('meta:ruleish', {
                'doc': 'Properties which are common to rules used in evaluation systems.',
                'interfaces': (
                    ('doc:authorable', {'template': {'document': 'rule', 'syntax': ''}}),
                ),
                'props': (

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {document}.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the {document}.'}),

                    ('enabled', ('bool', {}), {
                        'doc': 'The enabled status of the {document}.'}),

                    ('text', ('text', {}), {
                        'display': {'syntax': '{syntax}'},
                        'doc': 'The text of the {document}.'})
                ),
            }),
            ('meta:matchish', {
                'doc': 'Properties which are common to matches based on rules.',
                'template': {'rule': 'rule', 'rule:type': 'rule:type',
                             'target:type': 'ndef'},
                'props': (

                    ('rule', ('{rule:type}', {}), {
                        'doc': 'The rule which matched the target node.'}),

                    ('target', ('{target:type}', {}), {
                        'doc': 'The target node which matched the {rule}.'}),

                    ('version', ('it:semver', {}), {
                        'doc': 'The most recent version of the rule evaluated as a match.'}),

                    ('matched', ('time', {}), {
                        'doc': 'The time that the rule was evaluated to generate the match.'}),
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

            (('meta:ruleset', 'has', 'meta:ruleish'), {
               'doc': 'The ruleset includes the rule.'}),

            # FIXME meta:rule:match
            (('meta:rule', 'matches', None), {
                'doc': 'The meta:rule has matched on target node.'}),

            (('meta:rule', 'detects', None), {
                'doc': 'The meta:rule is designed to detect instances of the target node.'}),
        ),
        'forms': (

            ('meta:id', {}, ()),
            ('meta:name', {}, ()),

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

                ('cursor', ('str', {'strip': True}), {
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

                ('timeline', ('meta:timeline', {}), {
                    'doc': 'The timeline containing the event.'}),

                ('title', ('str', {}), {
                    'doc': 'A title for the event.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the event.'}),

                # FIXME period
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

                ('name', ('meta:name', {}), {
                    'doc': 'A name for the ruleset.'}),

                ('type', ('meta:ruleset:type:taxonomy', {}), {
                    'doc': 'The ruleset type.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the ruleset.'}),

                # FIXME authored interface?
                ('author', ('entity:actor', {}), {
                    'doc': 'The contact information of the ruleset author.'}),

                ('created', ('time', {}), {
                    'doc': 'The time the ruleset was initially created.'}),

                ('updated', ('time', {}), {
                    'doc': 'The time the ruleset was most recently modified.'}),
            )),

            ('meta:rule:type:taxonomy', {}, ()),
            ('meta:rule', {}, (

                ('type', ('meta:rule:type:taxonomy', {}), {
                    'doc': 'The rule type.'}),
            )),

            ('meta:aggregate:type:taxonomy', {}, ()),
            # FIXME valuable?
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
