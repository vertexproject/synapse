import logging

import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

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

class BaseModule(s_module.CoreModule):

    def getModelDef(self):

        return {

            'ctors': (

                ('int', 'synapse.lib.types.Int', {}, {
                    'doc': 'The base 64 bit signed integer type.'}),

                ('float', 'synapse.lib.types.Float', {}, {
                    'doc': 'The base floating point type.'}),

                ('range', 'synapse.lib.types.Range', {'type': ('int', {})}, {
                    'doc': 'A base range type.'}),

                ('str', 'synapse.lib.types.Str', {}, {
                    'doc': 'The base string type.'}),

                ('hex', 'synapse.lib.types.Hex', {}, {
                    'doc': 'The base hex type.'}),

                ('bool', 'synapse.lib.types.Bool', {}, {
                    'doc': 'The base boolean type.'}),

                ('time', 'synapse.lib.types.Time', {}, {
                    'doc': 'A date/time value.'}),

                ('duration', 'synapse.lib.types.Duration', {}, {
                    'doc': 'A duration value.'}),

                ('ival', 'synapse.lib.types.Ival', {}, {
                    'doc': 'A time window/interval.'}),

                ('guid', 'synapse.lib.types.Guid', {}, {
                    'doc': 'The base GUID type.'}),

                ('syn:tag:part', 'synapse.lib.types.TagPart', {}, {
                    'doc': 'A tag component string.'}),

                ('syn:tag', 'synapse.lib.types.Tag', {}, {
                    'doc': 'The base type for a synapse tag.'}),

                ('comp', 'synapse.lib.types.Comp', {}, {
                    'doc': 'The base type for compound node fields.'}),

                ('loc', 'synapse.lib.types.Loc', {}, {
                    'doc': 'The base geo political location type.'}),

                ('ndef', 'synapse.lib.types.Ndef', {}, {
                    'doc': 'The node definition type for a (form,valu) compound field.'}),

                ('array', 'synapse.lib.types.Array', {'type': 'int'}, {
                    'doc': 'A typed array which indexes each field.'}),

                ('edge', 'synapse.lib.types.Edge', {}, {
                    'deprecated': True,
                    'doc': 'An digraph edge base type.'}),

                ('timeedge', 'synapse.lib.types.TimeEdge', {}, {
                    'deprecated': True,
                    'doc': 'An digraph edge base type with a unique time.'}),

                ('data', 'synapse.lib.types.Data', {}, {
                    'doc': 'Arbitrary json compatible data.'}),

                ('nodeprop', 'synapse.lib.types.NodeProp', {}, {
                    'doc': 'The nodeprop type for a (prop,valu) compound field.'}),

                ('hugenum', 'synapse.lib.types.HugeNum', {}, {
                    'doc': 'A potentially huge/tiny number. [x] <= 730750818665451459101842 with a fractional precision of 24 decimal digits.'}),

                ('taxon', 'synapse.lib.types.Taxon', {}, {
                    'doc': 'A component of a hierarchical taxonomy.'}),

                ('taxonomy', 'synapse.lib.types.Taxonomy', {}, {
                    'doc': 'A hierarchical taxonomy.'}),

                ('velocity', 'synapse.lib.types.Velocity', {}, {
                    'doc': 'A velocity with base units in mm/sec.'}),
            ),

            'univs': (

                ('seen', ('ival', {}), {
                    'doc': 'The time interval for first/last observation of the node.'}),

                ('created', ('time', {'ismin': True}), {
                    'ro': True,
                    'doc': 'The time the node was created in the cortex.'}),
            ),

            'types': (

                ('meta:feed', ('guid', {}), {
                    'doc': 'A data feed provided by a specific source.'}),

                ('meta:feed:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A data feed type taxonomy.'}),

                ('meta:source', ('guid', {}), {
                    'doc': 'A data source unique identifier.'}),

                ('meta:seen', ('comp', {'fields': (('source', 'meta:source'), ('node', 'ndef'))}), {
                    'deprecated': True,
                    'doc': 'Annotates that the data in a node was obtained from or observed by a given source.'}),

                ('meta:note', ('guid', {}), {
                    'doc': 'An analyst note about nodes linked with -(about)> edges.'}),

                ('meta:note:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'An analyst note type taxonomy.'}),

                ('meta:timeline', ('guid', {}), {
                    'doc': 'A curated timeline of analytically relevant events.'}),

                ('meta:timeline:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of timeline types for meta:timeline nodes.'}),

                ('meta:event', ('guid', {}), {
                    'doc': 'An analytically relevant event in a curated timeline.'}),

                ('meta:event:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy of event types for meta:event nodes.'}),

                ('meta:ruleset:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy for meta:ruleset types.'}),

                ('meta:ruleset', ('guid', {}), {
                    'doc': 'A set of rules linked with -(has)> edges.'}),

                ('meta:rule:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A taxonomy for meta:rule types.'}),

                ('meta:rule', ('guid', {}), {
                    'doc': 'A generic rule linked to matches with -(matches)> edges.'}),

                ('graph:cluster', ('guid', {}), {
                    'deprecated': True,
                    'doc': 'A generic node, used in conjunction with Edge types, to cluster arbitrary nodes to a '
                           'single node in the model.'}),

                ('graph:node', ('guid', {}), {
                    'deprecated': True,
                    'doc': 'A generic node used to represent objects outside the model.'}),

                ('graph:event', ('guid', {}), {
                    'deprecated': True,
                    'doc': 'A generic event node to represent events outside the model.'}),

                ('edge:refs', ('edge', {}), {
                    'deprecated': True,
                    'doc': 'A digraph edge which records that N1 refers to or contains N2.'}),

                ('edge:has', ('edge', {}), {
                    'deprecated': True,
                    'doc': 'A digraph edge which records that N1 has N2.'}),

                ('edge:wentto', ('timeedge', {}), {
                    'deprecated': True,
                    'doc': 'A digraph edge which records that N1 went to N2 at a specific time.'}),

                ('graph:edge', ('edge', {}), {
                    'deprecated': True,
                    'doc': 'A generic digraph edge to show relationships outside the model.'}),

                ('graph:timeedge', ('timeedge', {}), {
                    'deprecated': True,
                    'doc': 'A generic digraph time edge to show relationships outside the model.'}),

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

                        ('summary', ('str', {}), {
                            'deprecated': True,
                            'doc': 'Deprecated. Please use title/desc.',
                            'disp': {'hint': 'text'}}),

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

                (('meta:ruleset', 'has', 'inet:service:rule'), {
                    'doc': 'The meta:ruleset includes the inet:service:rule.'}),

                (('meta:ruleset', 'has', 'it:app:snort:rule'), {
                    'doc': 'The meta:ruleset includes the it:app:snort:rule.'}),

                (('meta:ruleset', 'has', 'it:app:yara:rule'), {
                    'doc': 'The meta:ruleset includes the it:app:yara:rule.'}),

                (('meta:rule', 'matches', None), {
                    'doc': 'The meta:rule has matched on target node.'}),

                (('meta:rule', 'detects', None), {
                    'doc': 'The meta:rule is designed to detect instances of the target node.'}),
            ),
            'forms': (

                ('meta:source', {}, (

                    ('name', ('str', {'lower': True}), {
                        'doc': 'A human friendly name for the source.'}),

                    # TODO - 3.0 move to taxonomy type
                    ('type', ('str', {'lower': True}), {
                        'doc': 'An optional type field used to group sources.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the meta source.'}),

                    ('ingest:cursor', ('str', {}), {
                        'doc': 'Used by ingest logic to capture the current ingest cursor within a feed.'}),

                    ('ingest:latest', ('time', {}), {
                        'doc': 'Used by ingest logic to capture the last time a feed ingest ran.'}),

                    ('ingest:offset', ('int', {}), {
                        'doc': 'Used by ingest logic to capture the current ingest offset within a feed.'}),
                )),

                ('meta:seen', {}, (

                    ('source', ('meta:source', {}), {'ro': True,
                        'doc': 'The source which observed or provided the node.'}),

                    ('node', ('ndef', {}), {'ro': True,
                        'doc': 'The node which was observed by or received from the source.'}),

                )),

                ('meta:feed:type:taxonomy', {}, ()),
                ('meta:feed', {}, (

                    ('name', ('str', {'lower': True, 'onespace': True}), {
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

                    ('author', ('ps:contact', {}), {
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
                    ('type', ('meta:timeline:taxonomy', {}), {
                        'doc': 'The type of timeline.'}),
                )),

                ('meta:timeline:taxonomy', {}, ()),

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

                    ('type', ('meta:event:taxonomy', {}), {
                        'doc': 'Type of event.'}),
                )),

                ('meta:event:taxonomy', {}, ()),

                ('meta:ruleset', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A name for the ruleset.'}),

                    ('type', ('meta:ruleset:type:taxonomy', {}), {
                        'doc': 'The ruleset type.'}),

                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the ruleset.'}),
                    ('author', ('ps:contact', {}), {
                        'doc': 'The contact information of the ruleset author.'}),
                    ('created', ('time', {}), {
                        'doc': 'The time the ruleset was initially created.'}),
                    ('updated', ('time', {}), {
                        'doc': 'The time the ruleset was most recently modified.'}),
                )),

                ('meta:rule:type:taxonomy', {}, ()),
                ('meta:rule', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A name for the rule.'}),
                    ('type', ('meta:rule:type:taxonomy', {}), {
                        'doc': 'The rule type.'}),
                    ('desc', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'A description of the rule.'}),
                    ('text', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The text of the rule logic.'}),
                    ('author', ('ps:contact', {}), {
                        'doc': 'The contact information of the rule author.'}),
                    ('created', ('time', {}), {
                        'doc': 'The time the rule was initially created.'}),
                    ('updated', ('time', {}), {
                        'doc': 'The time the rule was most recently modified.'}),
                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the rule.'}),
                    ('ext:id', ('str', {}), {
                        'doc': 'An external identifier for the rule.'}),
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

                ('graph:cluster', {}, (
                    ('name', ('str', {'lower': True}), {
                        'doc': 'A human friendly name for the cluster.'}),
                    ('desc', ('str', {'lower': True}), {
                        'doc': 'A human friendly long form description for the cluster.'}),
                    ('type', ('str', {'lower': True}), {
                        'doc': 'An optional type field used to group clusters.'}),
                )),

                ('edge:has', {}, (
                    ('n1', ('ndef', {}), {'ro': True}),
                    ('n1:form', ('str', {}), {'ro': True}),
                    ('n2', ('ndef', {}), {'ro': True}),
                    ('n2:form', ('str', {}), {'ro': True}),
                )),

                ('edge:refs', {}, (
                    ('n1', ('ndef', {}), {'ro': True}),
                    ('n1:form', ('str', {}), {'ro': True}),
                    ('n2', ('ndef', {}), {'ro': True}),
                    ('n2:form', ('str', {}), {'ro': True}),
                )),

                ('edge:wentto', {}, (
                    ('n1', ('ndef', {}), {'ro': True}),
                    ('n1:form', ('str', {}), {'ro': True}),
                    ('n2', ('ndef', {}), {'ro': True}),
                    ('n2:form', ('str', {}), {'ro': True}),

                    ('time', ('time', {}), {'ro': True}),
                )),

                ('graph:node', {}, (

                    ('type', ('str', {}), {
                        'doc': 'The type name for the non-model node.'}),

                    ('name', ('str', {}), {
                        'doc': 'A human readable name for this record.'}),

                    ('data', ('data', {}), {
                        'doc': 'Arbitrary non-indexed msgpack data attached to the node.'}),

                )),

                ('graph:edge', {}, (
                    ('n1', ('ndef', {}), {'ro': True}),
                    ('n1:form', ('str', {}), {'ro': True}),
                    ('n2', ('ndef', {}), {'ro': True}),
                    ('n2:form', ('str', {}), {'ro': True}),
                )),

                ('graph:timeedge', {}, (
                    ('time', ('time', {}), {'ro': True}),
                    ('n1', ('ndef', {}), {'ro': True}),
                    ('n1:form', ('str', {}), {'ro': True}),
                    ('n2', ('ndef', {}), {'ro': True}),
                    ('n2:form', ('str', {}), {'ro': True}),
                )),

                ('graph:event', {}, (

                    ('time', ('time', {}), {
                        'doc': 'The time of the event.'}),

                    ('type', ('str', {}), {
                        'doc': 'A arbitrary type string for the event.'}),

                    ('name', ('str', {}), {
                        'doc': 'A name for the event.'}),

                    ('data', ('data', {}), {
                        'doc': 'Arbitrary non-indexed msgpack data attached to the event.'}),

                )),

            ),
        }
