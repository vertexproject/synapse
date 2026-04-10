scoreenums = (
    (0, 'none'),
    (10, 'lowest'),
    (20, 'low'),
    (30, 'medium'),
    (40, 'high'),
    (50, 'highest'),
)

taskstatusenums = (
    (0, 'new'),
    (10, 'in validation'),
    (20, 'in backlog'),
    (30, 'in sprint'),
    (40, 'in progress'),
    (50, 'in review'),
    (60, 'completed'),
    (70, 'done'),
    (80, 'blocked'),
)

basetypedefs = (
    ('base', {
        'types': (

            ('int', (None, {'ctor': 'synapse.lib.types.Int'}), {
                'doc': 'The base 64 bit signed integer type.'}),

            ('float', (None, {'ctor': 'synapse.lib.types.Float'}), {
                'doc': 'The base floating point type.'}),

            ('range', (None, {'ctor': 'synapse.lib.types.Range', 'type': ('int', {})}), {
                'doc': 'A base range type.'}),

            ('str', (None, {'ctor': 'synapse.lib.types.Str'}), {
                'doc': 'The base string type.'}),

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
                'doc': 'The base type for a synapse tag.'}),

            ('comp', (None, {'ctor': 'synapse.lib.types.Comp'}), {
                'doc': 'The base type for compound node fields.'}),

            ('loc', (None, {'ctor': 'synapse.lib.types.Loc'}), {
                'doc': 'The base geo political location type.'}),

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

            ('taxon', (None, {'ctor': 'synapse.lib.types.Taxon'}), {
                'doc': 'A component of a hierarchical taxonomy.'}),

            ('taxonomy', (None, {'ctor': 'synapse.lib.types.Taxonomy'}), {
                'doc': 'A hierarchical taxonomy.'}),

            ('velocity', (None, {'ctor': 'synapse.lib.types.Velocity'}), {
                'doc': 'A velocity with base units in mm/sec.'}),
        ),
    }),
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
                'prevnames': ('ou:name', 'ou:industryname',
                              'ou:campname', 'ou:goalname', 'lang:name',
                              'risk:vulnname', 'meta:name', 'entity:name',
                              'geo:name'),
                'doc': 'A name used to refer to an entity or event.'}),

            ('event:name', ('base:name', {}), {
                'doc': 'A name used to refer to a specific event or activity.'}),

            ('meta:topic', ('base:name', {}), {
                'interfaces': (
                    ('risk:targetable', {}),
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
                'template': {'title': 'event'},
                'interfaces': (
                    ('base:event', {}),
                ),
                'props': (
                    ('title', ('str', {}), {
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
                    ('base:activity', {}),
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
                'doc': 'A set of rules linked with -(has)> edges.'}),

            ('meta:rule:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of rule types.'}),

            ('meta:rule', ('guid', {}), {
                'template': {'title': 'rule', 'syntax': ''},
                'interfaces': (
                    ('meta:usable', {}),
                    ('doc:authorable', {}),
                ),
                'doc': 'A generic rule linked to matches with -(matches)> edges.'}),

            ('meta:score', ('int', {'enums': scoreenums, 'enums:strict': False}), {
                'doc': 'A generic score enumeration.'}),

            ('meta:task:status', ('int', {'enums': taskstatusenums}), {
                'doc': 'A task status.'}),

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

            ('text', ('str', {'strip': False}), {
                'doc': 'A multi-line, free form text string.'}),

            ('str:lower', ('str', {'lower': True}), {
                'doc': 'A case insensitive string.'}),

            ('text:lower', ('text', {'lower': True}), {
                'doc': 'A case insensitive, multi-line text string.'}),

            ('int:min0', ('int', {'min': 0}), {
                'doc': 'A non-negative integer.'}),

            ('int:min1', ('int', {'min': 1}), {
                'doc': 'A positive integer.'}),

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
                        {'type': 'prop', 'opts': {'name': 'tag'}},
                    ),
                }}),

            ('meta:technique:status:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
                'doc': 'A hierarchical taxonomy of technique statuses.'}),

            ('meta:technique:type:taxonomy', ('taxonomy', {}), {
                'interfaces': (
                    ('meta:taxonomy', {}),
                ),
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
                'template': {'title': 'item'},
                'props': (

                    ('owner', ('entity:actor', {}), {
                        'doc': 'The current owner of the {title}.'}),

                    ('owner:name', ('entity:name', {}), {
                        'doc': 'The name of the current owner of the {title}.'}),
                ),
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
                    'status': '{$self}:status:taxonomy',
                },
                'props': (

                    ('id', ('meta:id', {}), {
                        'alts': ('ids',),
                        'doc': 'A unique ID given to the {title}.'}),

                    ('ids', ('array', {'type': 'meta:id'}), {
                        'doc': 'An array of alternate IDs given to the {title}.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'The URL for the {title}.'}),

                    ('name', ('meta:name', {}), {
                        'alts': ('names',),
                        'doc': 'The primary name of the {title}.'}),

                    ('names', ('array', {'type': 'meta:name'}), {
                        'doc': 'A list of alternate names for the {title}.'}),

                    ('desc', ('text', {}), {
                        'doc': 'A description of the {title}.'}),

                    ('resolved', ('{$self}', {}), {
                        'doc': 'The authoritative {title} which this reporting is about.'}),

                    ('reporter', ('entity:actor', {}), {
                        'doc': 'The entity which reported on the {title}.'}),

                    ('reporter:name', ('entity:name', {}), {
                        'doc': 'The name of the entity which reported on the {title}.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time when the {title} was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time when the {title} was last updated.'}),

                    ('published', ('time', {}), {
                        'doc': 'The time when the reporter published the {title}.'}),

                    ('superseded', ('time', {}), {
                        'doc': 'The time when the {title} was superseded.'}),

                    ('supersedes', ('array', {'type': '{$self}'}), {
                        'doc': 'An array of {title} nodes which are superseded by this {title}.'}),
                ),
            }),

            # TODO: should all the actor <verb>able interfaces move to entity: ?
            ('meta:believable', {
                'doc': 'An interface implemented by forms which may be believed in by an actor.'}),

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

                    ('activity', ('meta:activity', {}), {
                        'doc': 'A parent activity which includes this {title}.'}),
                ),
                'doc': 'Properties common to an event.'}),

            ('base:activity', {
                'template': {'title': 'activity'},
                'interfaces': (
                    ('meta:causal', {}),
                ),
                'props': (
                    ('period', ('ival', {}), {
                        'doc': 'The period over which the {title} occurred.'}),

                    ('activity', ('meta:activity', {}), {
                        'doc': 'A parent activity which includes this {title}.'}),
                ),
                'doc': 'Properties common to activity which occurs over a period.'}),

            ('meta:usable', {
                'template': {'title': 'item'},
                'doc': 'An interface implemented by forms which can be used by an actor.'}),

            ('meta:matchish', {
                'doc': 'Properties which are common to matches based on rules.',
                'template': {'rule': 'rule', 'rule:type': 'rule:type',
                             'target:type': ''},
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

            ('meta:achievable', {
                'doc': 'An interface implemented by forms which are achievable.'}),

            ('meta:task', {
                'doc': 'A common interface for tasks.',
                'template': {'title': 'task'},
                'props': (

                    ('id', ('base:id', {}), {
                        'doc': 'The ID of the {title}.'}),

                    ('parent', ('meta:task', {}), {
                        'doc': 'The parent task which includes this {title}.'}),

                    ('project', ('proj:project', {}), {
                        'doc': 'The project containing the {title}.'}),

                    ('status', ('meta:task:status', {}), {
                        'doc': 'The status of the {title}.'}),

                    ('priority', ('meta:score', {}), {
                        'doc': 'The priority of the {title}.'}),

                    ('created', ('time', {}), {
                        'doc': 'The time the {title} was created.'}),

                    ('updated', ('time', {}), {
                        'doc': 'The time the {title} was last updated.'}),

                    ('due', ('time', {}), {
                        'doc': 'The time the {title} must be complete.'}),

                    ('completed', ('time', {}), {
                        'doc': 'The time the {title} was completed.'}),

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

            (('meta:rule', 'detects', 'meta:usable'), {
                'doc': 'The rule is designed to detect the target node.'}),

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

                ('creator', ('entity:actor', {}), {
                    'doc': 'The actor who authored the note.'}),

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
                    'doc': 'The title of the timeline.'}),

                ('desc', ('text', {}), {
                    'doc': 'A description of the timeline.'}),

                ('type', ('meta:timeline:type:taxonomy', {}), {
                    'doc': 'The type of timeline.'}),
            )),

            ('meta:timeline:type:taxonomy', {
                'prevnames': ('meta:timeline:taxonomy',)}, ()),

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

                ('sophistication', ('meta:score', {}), {
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
