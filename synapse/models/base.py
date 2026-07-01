scoreenums = (
    (0, 'none'),
    (10, 'lowest'),
    (20, 'low'),
    (30, 'medium'),
    (40, 'high'),
    (50, 'highest'),
)

modeldefs = (
    {
        'types': (

            ('int', (None, {'ctor': 'synapse.lib.types.Int'}), {
                'doc': 'The base 64 bit signed integer type.'}),

            ('float', (None, {'ctor': 'synapse.lib.types.Float'}), {
                'doc': 'The base floating point type.'}),

            ('range', (None, {'ctor': 'synapse.lib.types.Range', 'type': ('int', {})}), {
                'doc': 'A base range type.'}),

            ('str', (None, {'ctor': 'synapse.lib.types.Str'}), {
                'doc': 'The base string type.'}),

            ('text', (None, {'ctor': 'synapse.lib.types.Text'}), {
                'doc': 'A multi-line, free form, case-preserving text string with case-insensitive comparison.'}),

            ('title', (None, {'ctor': 'synapse.lib.types.Title'}), {
                'doc': 'A single line, free form, case-preserving title or name string with case-insensitive comparison.'}),

            ('hex', (None, {'ctor': 'synapse.lib.types.Hex'}), {
                'doc': 'The base hex type.'}),

            ('bool', (None, {'ctor': 'synapse.lib.types.Bool'}), {
                'doc': 'The base boolean type.'}),

            ('timeprecision', (None, {'ctor': 'synapse.lib.types.TimePrecision'}), {
                'doc': 'A time precision value.'}),

            ('time', (None, {'ctor': 'synapse.lib.types.Time'}), {
                'virts': (
                    ('precision', ('timeprecision', {}), {
                        'doc': 'The precision for display and rounding the time.'}),
                ),
                'doc': 'A date/time value.'}),

            ('duration', (None, {'ctor': 'synapse.lib.types.Duration'}), {
                'doc': 'A duration value.'}),

            ('duration:seconds', ('duration', {'precision': 'second'}), {
                'doc': 'A duration value with second resolution.'}),

            ('ival', (None, {'ctor': 'synapse.lib.types.Ival'}), {
                'virts': (

                    ('min', ('time', {}), {
                        'doc': 'The starting time of the interval.'}),

                    ('max', ('time', {}), {
                        'doc': 'The ending time of the interval.'}),

                    ('duration', ('duration', {}), {
                        'doc': 'The duration of the interval.'}),

                    ('precision', ('timeprecision', {}), {
                        'doc': 'The precision for display and rounding the times.'}),
                ),
                'doc': 'A time window or interval.'}),

            ('guid', (None, {'ctor': 'synapse.lib.types.Guid'}), {
                'doc': 'The base GUID type.'}),

            ('syn:tag:part', (None, {'ctor': 'synapse.lib.types.TagPart'}), {
                'doc': 'A tag component string.'}),

            ('syn:tag', (None, {'ctor': 'synapse.lib.types.Tag'}), {
                'props': (
                    ('up', ('syn:tag', {}), {'computed': True,
                        'doc': 'The parent tag for the tag.'}),

                    ('isnow', ('syn:tag', {}), {
                        'doc': 'Set to an updated tag if the tag has been renamed.'}),

                    ('doc', ('text', {}), {
                        'doc': 'A short definition for the tag.'}),

                    ('doc:url', ('inet:url', {}), {
                        'doc': 'A URL link to additional documentation about the tag.'}),

                    ('depth', ('int', {}), {'computed': True,
                        'doc': 'How deep the tag is in the hierarchy.'}),

                    ('title', ('title', {}), {'doc': 'A display title for the tag.'}),

                    ('base', ('str', {}), {
                        'computed': True,
                        'modes': {
                            'lookup': [
                                {'cmpr': '^='},
                            ]
                        },
                        'doc': 'The tag base name. Eg baz for foo.bar.baz .'}),
                ),
                'doc': 'The base type for a synapse tag.'}),

            ('comp', (None, {'ctor': 'synapse.lib.types.Comp'}), {
                'doc': 'The base type for compound node fields.'}),

            ('loc', (None, {'ctor': 'synapse.lib.types.Loc'}), {
                'doc': 'The base geopolitical location type.'}),

            ('poly', (None, {'ctor': 'synapse.lib.types.Poly'}), {
                'virts': (
                    ('type', ('syn:type', {}), {
                        'computed': True,
                        'doc': 'The type of value which is referenced.'}),

                    ('value', ('data', {}), {
                        'computed': True,
                        'display': {'hidden': True},
                        'doc': 'The value which is referenced.'}),
                ),
                'doc': 'A prop which can be of one or more types.'}),

            ('array', (None, {'ctor': 'synapse.lib.types.Array', 'type': 'int'}), {
                'virts': (
                    ('size', ('int', {}), {
                        'computed': True,
                        'doc': 'The number of elements in the array.'}),
                ),
                'doc': 'A typed array which indexes each field.'}),

            ('data', (None, {'ctor': 'synapse.lib.types.Data'}), {
                'doc': 'Arbitrary json compatible data.'}),

            ('hugenum', (None, {'ctor': 'synapse.lib.types.HugeNum'}), {
                'doc': 'A potentially huge/tiny number. [x] <= 730750818665451459101842 with a fractional '
                       'precision of 24 decimal digits.'}),

            ('percent', ('hugenum', {'min': 0, 'max': 100, 'units': {'%': '1'}, 'defunit': '%'}), {
                'ex': '10.2%',
                'doc': 'A percentage value between 0 and 100.'}),

            ('ratio', ('hugenum', {'units': {'%': '1'}, 'defunit': '%'}), {
                'ex': '-10.2%',
                'doc': 'A ratio expressed as a percentage which may be negative or exceed 100.'}),

            ('taxon', (None, {'ctor': 'synapse.lib.types.Taxon'}), {
                'doc': 'A component of a hierarchical taxonomy.'}),

            ('taxonomy', (None, {'ctor': 'synapse.lib.types.Taxonomy'}), {
                'doc': 'A hierarchical taxonomy.'}),

            ('velocity', (None, {'ctor': 'synapse.lib.types.Velocity'}), {
                'doc': 'A velocity with base units in mm/sec.'}),

            ('date', ('time', {'precision': 'day'}), {
                'doc': 'A date precision time value.'}),

            ('daterange', ('ival', {'precision': 'day'}), {
                'doc': 'A date precision time range.'}),

            ('base:id', ('str', {}), {
                'doc': 'A base type for ID strings.'}),


            ('base:name', ('title', {}), {
                'doc': 'A base type for case insensitive, case preserving names.'}),

            ('event:name', ('base:name', {}), {
                'modes': {
                    'lookup': [
                        {'cmpr': '^='}
                    ]
                },
                'doc': 'A name used to refer to a specific event or activity.'}),

            ('meta:topic', ('base:name', {}), {
                'interfaces': (
                    ('risk:targetable', {}),
                ),
                'props': (
                    ('desc', ('text', {}), {
                        'doc': 'A description of the topic.'}),
                ),
                'doc': 'A topic string.'}),

            ('meta:feed', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'source::name'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                    ),
                },
                'props': (
                    ('id', ('base:id', {}), {
                        'doc': 'An identifier for the feed.'}),

                    ('name', ('base:name', {}), {
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
                ),
                'doc': 'A data feed provided by a specific source.'}),

            ('meta:feed:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A data feed type taxonomy.'}),

            ('meta:source', ('guid', {}), {
                'props': (
                    ('name', ('base:name', {}), {
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
                ),
                'doc': 'A data source unique identifier.'}),

            ('meta:note', ('guid', {}), {
                'template': {'title': 'note'},
                'interfaces': (
                    ('entity:creatable', {}),
                ),
                'props': (
                    ('type', ('meta:note:type:taxonomy', {}), {
                        'doc': 'The note type.'}),

                    ('text', ('text', {}), {
                        'display': {'syntax': 'markdown'},
                        'doc': 'The analyst authored note text.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the note was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the note was updated.'}),

                    ('replyto', ('meta:note', {}), {
                        'doc': 'The note is a reply to the specified note.'}),
                ),
                'doc': 'An analyst note about nodes linked with -(about)> edges.'}),

            ('meta:note:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of note types.'}),

            ('meta:source:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of source types.'}),

            ('meta:timeline', ('guid', {}), {
                'props': (
                    ('title', ('title', {}), {
                        'ex': 'The history of the Vertex Project',
                        'doc': 'The title of the timeline.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the timeline.'}),

                    ('type', ('meta:timeline:type:taxonomy', {}), {
                        'doc': 'The type of timeline.'}),
                ),
                'doc': 'A curated timeline of analytically relevant events.'}),

            ('meta:timeline:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('meta:timeline:taxonomy',),
                'props': (),
                'doc': 'A hierarchical taxonomy of timeline types.'}),

            ('meta:event', ('guid', {}), {
                'template': {'title': 'event'},
                'interfaces': (
                    ('base:event', {}),
                ),
                'props': (
                    ('title', ('title', {}), {
                        'doc': 'A title for the {title}.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),

                    ('type', ('meta:event:type:taxonomy', {}), {
                        'doc': 'The type of event.'}),
                ),
                'doc': 'An analytically relevant event.'}),

            ('meta:activity', ('guid', {}), {
                'template': {'title': 'activity'},
                'interfaces': (
                    ('entity:attendable', {}),
                ),
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'The name of the {title}.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),

                    ('type', ('meta:event:type:taxonomy', {}), {
                        'doc': 'The type of activity.'}),
                ),
                'doc': 'Analytically relevant activity.'}),

            ('meta:event:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'prevnames': ('meta:event:taxonomy',),
                'props': (),
                'doc': 'A hierarchical taxonomy of event types.'}),

            ('meta:ruleset:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A taxonomy for meta:ruleset types.'}),

            ('meta:ruleset', ('guid', {}), {
                'template': {'title': 'ruleset'},
                'interfaces': (
                    ('doc:authorable', {}),
                ),
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'A name for the ruleset.'}),

                    ('type', ('meta:ruleset:type:taxonomy', {}), {
                        'doc': 'The ruleset type.'}),
                ),
                'doc': 'A set of rules linked with -(has)> edges.'}),

            ('meta:rule:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of rule types.'}),

            ('meta:rule', ('guid', {}), {
                'template': {'title': 'rule', 'syntax': ''},
                'interfaces': (
                    ('meta:usable', {}),
                    ('doc:authorable', {}),
                    ('meta:observable', {}),
                ),
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'The rule name.'}),

                    ('type', ('meta:rule:type:taxonomy', {}), {
                        'doc': 'The rule type.'}),

                    ('status', ('title', {}), {
                        'doc': 'The status of the rule.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the {title}.'}),

                    ('enabled', ('bool', {}), {
                        'doc': 'The enabled status of the {title}.'}),

                    ('text', ('text', {}), {
                        'display': {'syntax': '{syntax}'},
                        'doc': 'The text of the {title}.'})
                ),
                'doc': 'A generic rule linked to matches with -(matches)> edges.'}),

            ('meta:algorithm:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of algorithm types.'}),

            ('meta:algorithm', ('guid', {}), {
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:observable', {}),
                ),
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'The name of the algorithm.'}),

                    ('type', ('meta:algorithm:type:taxonomy', {}), {
                        'doc': 'The type of algorithm.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the algorithm.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time that the algorithm was authored.'}),
                ),
                'doc': 'A mathematical or cryptographic algorithm.'}),

            ('meta:score', ('int', {'enums': scoreenums, 'enums:strict': False}), {
                'doc': 'A generic score enumeration.'}),

            ('meta:aggregate:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A type of item being counted in aggregate.'}),

            ('meta:aggregate', ('guid', {}), {
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'time'}},
                        {'type': 'prop', 'opts': {'name': 'type'}},
                        {'type': 'prop', 'opts': {'name': 'count'}},
                    ),
                },
                'props': (
                    ('type', ('meta:aggregate:type:taxonomy', {}), {
                        'ex': 'casualties.civilian',
                        'doc': 'The type of items being counted in aggregate.'}),

                    ('time', ('time', {}), {
                        'doc': 'The time that the count was computed.'}),

                    ('count', ('int', {}), {
                        'doc': 'The number of items counted in aggregate.'}),
                ),
                'doc': 'A node which represents an aggregate count of a specific type.'}),

            ('meta:cluster:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A type taxonomy for meta:cluster nodes.'}),

            ('meta:cluster', ('guid', {}), {
                'template': {'title': 'cluster'},
                'interfaces': (
                    ('meta:reported', {}),
                ),
                'props': (
                    ('type', ('meta:cluster:type:taxonomy', {}), {
                        'doc': 'The type of cluster.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes that are associated with the cluster.'}),
                ),
                'doc': 'A cluster of analytically relevant nodes generated by a specific source.'}),

            ('str:lower', ('str', {'lower': True}), {
                'doc': 'A case insensitive string.'}),

            ('str:upper', ('str', {'upper': True}), {
                'doc': 'A case insensitive string normalized to upper case.'}),

            ('int:min0', ('int', {'min': 0}), {
                'doc': 'A non-negative integer.'}),

            ('int:min1', ('int', {'min': 1}), {
                'doc': 'A positive integer.'}),

            ('byte:flags', ('int', {'min': 0, 'max': 0xff}), {
                'doc': 'A set of flags contained in a single byte.'}),

            ('meta:technique', ('guid', {}), {
                'template': {'title': 'technique'},
                'doc': 'A specific technique used to achieve a goal.',
                'interfaces': (
                    ('meta:usable', {}),
                    ('meta:reported', {}),
                    ('meta:observable', {}),
                    ('risk:mitigatable', {}),
                ),
                'display': {
                    'columns': (
                        {'type': 'prop', 'opts': {'name': 'name'}},
                        {'type': 'prop', 'opts': {'name': 'reporter:name'}},
                        {'type': 'prop', 'opts': {'name': 'tag'}},
                    ),
                },
                'props': (
                    ('id', (
                        ('it:mitre:attack:technique:id', {}),
                        ('base:id', {}),
                    ), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the technique.'}),

                    ('ids', ('array', {'type': (('it:mitre:attack:technique:id', {}), ('base:id', {}))}), {
                        'doc': 'An array of alternate IDs given to the technique.'}),

                    ('type', ('meta:technique:type:taxonomy', {}), {
                        'doc': 'The taxonomy classification of the technique.'}),

                    ('sophistication', ('meta:score', {}), {
                        'doc': 'The assessed sophistication of the technique.'}),

                    ('tag', ('syn:tag', {}), {
                        'doc': 'The tag used to annotate nodes where the technique was employed.'}),

                    ('parent', ('meta:technique', {}), {
                        'doc': 'The parent technique for the technique.'}),
                )}),

            ('meta:technique:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'props': (),
                'doc': 'A hierarchical taxonomy of technique types.'}),

            ('meta:award:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of award types.'}),

            ('meta:award', ('guid', {}), {
                'interfaces': (
                    ('meta:achievable', {}),
                ),
                'props': (
                    ('issuer', ('entity:actor', {}), {
                        'doc': 'The entity which issues the award.'}),

                    ('issuer:name', ('entity:name', {}), {
                        'doc': 'The name of the entity which issues the award.'}),

                    ('name', ('base:name', {}), {
                        'alts': ('names',),
                        'doc': 'The name of the award.',
                        'ex': 'Nobel Peace Prize'}),

                    ('names', ('array', {'type': 'base:name'}), {
                        'doc': 'An array of alternate names for the award.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the award.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period of time when the issuer gave out the award.'}),

                    ('type', ('meta:award:type:taxonomy', {}), {
                        'doc': 'The type of award.',
                        'ex': 'certification'}),
                ),
                'doc': 'An award.'}),

            ('velocity:relative', ('velocity', {'relative': True}), {
                'doc': 'A relative velocity value.'}),

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
            }),

            ('meta:discoverable', {
                'template': {'title': 'item'},
                'props': (

                    ('discoverer', ('entity:actor', {}), {
                        'doc': 'The earliest known actor which discovered the {title}.'}),

                    ('discovered', ('time', {}), {
                        'doc': 'The earliest known time when the {title} was discovered.'}),
                ),
                'doc': 'An interface for items which can be discovered by an actor.',
            }),


            ('meta:reported', {
                'doc': 'Properties common to forms which are created on a per-source basis.',
                'template': {
                    'title': 'item',
                },
                'props': (

                    ('id', ('base:id', {}), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the {title}.'}),

                    ('ids', ('array', {'type': 'base:id'}), {
                        'doc': 'An array of alternate IDs given to the {title}.'}),

                    ('name', ('base:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {title}.'}),

                    ('names', ('array', {'type': 'base:name'}), {
                        'doc': 'A list of alternate names for the {title}.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),

                    ('resolved', ('{$self}', {}), {
                        'doc': 'The authoritative {title} which this reporting is about.'}),

                    ('reporter', ('entity:actor', {}), {
                        'doc': 'The entity which reported on the {title}.'}),

                    ('reporter:name', ('entity:name', {}), {
                        'doc': 'The name of the entity which reported on the {title}.'}),

                    ('reporter:url', ('inet:url', {}), {
                        'doc': 'The URL for the {title} provided by the reporter.'}),

                    ('reporter:period', ('ival', {'names': {'min': 'created', 'max': 'removed'}}), {
                        'doc': 'The period when the {title} existed, according to the reporter.'}),

                    ('reporter:deprecated', ('time', {}), {
                        'doc': 'The time when the reporter retired the {title}.'}),

                    ('reporter:supersedes', ('array', {'type': '{$self}'}), {
                        'doc': 'An array of {title} nodes which are superseded by this {title}.'}),

                    ('reporter:updated', ('time', {}), {
                        'doc': 'The time when the {title} was last updated.'}),

                    ('reporter:published', ('time', {}), {
                        'doc': 'The time when the reporter published the {title}.'}),
                ),
            }),

            # TODO: should all the actor <verb>able interfaces move to entity: ?
            ('meta:believable', {
                'template': {'title': 'item'},
                'props': (
                    ('name', ('base:name', {}), {
                        'doc': 'The name of the {title}.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),
                ),
                'doc': 'An interface implemented by forms which may be believed in by an actor.'}),

            ('meta:taxonomy', {
                'doc': 'Properties common to taxonomies.',
                'props': (
                    ('name', ('title', {}), {
                        'doc': 'A brief name for the definition.'}),

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

                    ('parent', ('{$self}', {}), {
                        'computed': True,
                        'doc': 'The taxonomy parent.'}),
                ),
            }),

            ('meta:causal', {
                'doc': 'Implemented by events and activities which can lead to effects.'}),

            ('base:event', {
                'template': {'title': 'event'},
                'interfaces': (
                    ('meta:causal', {}),
                ),
                'props': (
                    ('time', ('time', {}), {
                        'doc': 'The time that the {title} occurred.'}),

                    ('activity', ('base:activity', {}), {
                        'doc': 'A parent activity which includes this {title}.'}),
                ),
                'doc': 'Properties common to an event.'}),

            ('base:activity', {
                'template': {'title': 'activity', 'activity': 'occurred'},
                'interfaces': (
                    ('meta:causal', {}),
                ),
                'props': (
                    ('period', ('ival', {'names': {'min': 'began', 'max': 'ended'}}), {
                        'doc': 'The period over which the {title} {activity}.'}),

                    ('activity', ('base:activity', {}), {
                        'doc': 'A parent activity which includes this {title}.'}),
                ),
                'doc': 'Properties common to activity which occurs over a period.'}),

            ('meta:schedulable', {
                'template': {'title': 'activity'},
                'interfaces': (
                    ('base:activity', {}),
                ),
                'props': (
                    ('scheduled:period', ('ival', {}), {
                        'doc': 'The scheduled period over which the {title} was expected to occur.'}),
                ),
                'doc': 'An interface implemented by activities which may be scheduled.'}),

            ('meta:usable', {
                'template': {'title': 'item'},
                'doc': 'An interface implemented by forms which can be used by an actor.'}),

            ('base:matched', {
                'doc': 'Properties which are common to matches based on rules.',
                'template': {'title': 'match', 'rule': 'rule', 'rule:type': 'rule:type',
                             'target:type': ''},
                'interfaces': (
                    ('base:event', {'template': {'title': 'match'}}),
                ),
                'props': (

                    ('rule', ('{rule:type}', {}), {
                        'doc': 'The rule which matched the target node.'}),

                    ('target', ('{target:type}', {}), {
                        'doc': 'The target node which matched the {rule}.'}),

                    ('rule:version', ('it:version', {}), {
                        'doc': 'The version of the rule which generated the {title}.'}),
                ),
            }),

            ('meta:achievable', {
                'doc': 'An interface implemented by forms which are achievable.'}),

            ('meta:task', {
                'doc': 'A common interface for tasks.',
                'template': {'title': 'task'},
                'interfaces': (
                    ('entity:participable', {}),
                ),
                'props': (

                    ('id', ('base:id', {}), {
                        'doc': 'The ID of the {title}.'}),

                    ('parent', ('meta:task', {}), {
                        'doc': 'The parent task which includes this {title}.'}),

                    ('project', ('proj:project', {}), {
                        'doc': 'The project containing the {title}.'}),

                    ('status', ('title', {}), {
                        'doc': 'The status of the {title}.'}),

                    ('priority', ('meta:score', {}), {
                        'doc': 'The priority of the {title}.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the {title} was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the {title} was last updated.'}),

                    ('due', ('time', {}), {
                        'doc': 'The time the {title} must be complete.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period when the {title} was being worked on.'}),

                    ('creator', ('entity:actor', {}), {
                        'doc': 'The actor who created the {title}.'}),

                    ('assignee', ('entity:actor', {}), {
                        'doc': 'The actor who is assigned to complete the {title}.'}),
                ),
            }),

            ('meta:negotiable', {
                'doc': 'An interface implemented by activities which involve negotiation.'}),

            ('meta:recordable', {
                'template': {'title': 'event'},
                'props': (
                    ('recording:url', ('inet:url', {}), {
                        'doc': 'The URL hosting a recording of the {title}.'}),

                    ('recording:file', ('file:bytes', {}), {
                        'doc': 'A file containing a recording of the {title}.'}),

                    ('recording:offset', ('duration', {}), {
                        'doc': 'The time offset of the activity within the recording.'}),
                ),
                'doc': 'Properties common to activities which may be recorded or transcribed.'}),
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

            (('meta:event', 'about', None), {
                'doc': 'The event is about the target node.'}),

            (('meta:timeline', 'has', 'meta:event'), {
                'doc': 'The timeline includes the event.'}),

            (('meta:ruleset', 'has', 'meta:rule'), {
               'doc': 'The ruleset includes the rule.'}),

            (('meta:rule', 'matches', None), {
                'doc': 'The rule matched on the target node.'}),

            (('meta:rule', 'detects', 'meta:observable'), {
                'doc': 'The rule is designed to detect the target node.'}),

            (('meta:rule', 'generated', 'risk:alert'), {
                'doc': 'The meta:rule generated the risk:alert node.'}),

            (('meta:rule', 'generated', 'it:log:event'), {
                'doc': 'The meta:rule generated the it:log:event node.'}),

            (('meta:usable', 'uses', 'meta:usable'), {
                'doc': 'The source node uses the target node.'}),

            (('meta:technique', 'addresses', 'meta:technique'), {
                'doc': 'The technique addresses the technique.'}),

            (('meta:technique', 'addresses', 'risk:vuln'), {
                'doc': 'The technique addresses the vulnerability.'}),

            (('meta:causal', 'ledto', 'meta:causal'), {
                'doc': 'The source event led to the target event.'}),

            (('meta:task', 'has', 'file:attachment'), {
                'doc': 'The task includes the file attachment.'}),

            (('it:software', 'uses', 'meta:algorithm'), {
                'doc': 'The software uses the algorithm.'}),

            (('file:bytes', 'uses', 'meta:algorithm'), {
                'doc': 'The file uses the algorithm.'}),

            (('meta:algorithm', 'generated', None), {
                'doc': 'The target node was generated by the algorithm.'}),
        ),

        'tagprops': (

            ('tlp', ('it:sec:tlp', {}), {
                'doc': 'The TLP designation used to communicate the information sharing boundaries for the tag.'}),

            ('confidence', ('meta:score', {}), {
                'doc': 'The analyst confidence that the tag assessment is accurate.'}),

        ),
    },
)
