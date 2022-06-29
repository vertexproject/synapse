import logging

import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

class BaseModule(s_module.CoreModule):

    def getModelDefs(self):

        return (('base', {

            'types': (

                ('meta:source', ('guid', {}), {
                    'doc': 'A data source unique identifier.'}),

                ('meta:seen', ('comp', {'fields': (('source', 'meta:source'), ('node', 'ndef'))}), {
                    'doc': 'Annotates that the data in a node was obtained from or observed by a given source.'}),

                ('meta:note', ('guid', {}), {
                    'doc': 'An analyst note about nodes linked with -(about)> edges.'}),

                ('meta:timeline', ('guid', {}), {
                    'doc': 'A curated timeline of analytically relevant events.'}),

                ('meta:timeline:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('taxonomy',),
                    'doc': 'A taxonomy of timeline types for meta:timeline nodes.'}),

                ('meta:event', ('guid', {}), {
                    'doc': 'An analytically relevant event in a curated timeline.'}),

                ('meta:event:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('taxonomy',),
                    'doc': 'A taxonomy of event types for meta:event nodes.'}),

                ('meta:ruleset', ('guid', {}), {
                    'doc': 'A set of rules linked with -(has)> edges.'}),

                ('meta:rule', ('guid', {}), {
                    'doc': 'A generic rule linked to matches with -(matches)> edges.'}),

                ('graph:cluster', ('guid', {}), {
                    'doc': 'A generic node, used in conjunction with Edge types, to cluster arbitrary nodes to a '
                           'single node in the model.'}),

                ('graph:node', ('guid', {}), {
                    'doc': 'A generic node used to represent objects outside the model.'}),

                ('graph:event', ('guid', {}), {
                    'doc': 'A generic event node to represent events outside the model.'}),

                ('edge:refs', ('edge', {}), {
                    'doc': 'A digraph edge which records that N1 refers to or contains N2.'}),

                ('edge:has', ('edge', {}), {
                    'doc': 'A digraph edge which records that N1 has N2.'}),

                ('edge:wentto', ('timeedge', {}), {
                    'doc': 'A digraph edge which records that N1 went to N2 at a specific time.'}),

                ('graph:edge', ('edge', {}), {
                    'doc': 'A generic digraph edge to show relationships outside the model.'}),

                ('graph:timeedge', ('timeedge', {}), {
                    'doc': 'A generic digraph time edge to show relationships outside the model.'}),
            ),

            'forms': (

                ('meta:source', {}, (
                    ('name', ('str', {'lower': True}), {
                        'doc': 'A human friendly name for the source.'}),
                    ('type', ('str', {'lower': True}), {
                        'doc': 'An optional type field used to group sources.'}),
                )),

                ('meta:seen', {}, (

                    ('source', ('meta:source', {}), {'ro': True,
                        'doc': 'The source which observed or provided the node.'}),

                    ('node', ('ndef', {}), {'ro': True,
                        'doc': 'The node which was observed by or received from the source.'}),

                )),

                ('meta:note', {}, (
                    ('text', ('str', {}), {
                        'disp': {'hint': 'text'},
                        'doc': 'The analyst authored note text.'}),
                    ('author', ('ps:contact', {}), {
                        'doc': 'The contact information of the author.'}),
                    ('creator', ('syn:user', {}), {
                        'doc': 'The synapse user who authored the note.'}),
                    ('created', ('time', {}), {
                        'doc': 'The time the note was created.'}),
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
                    ('duration', ('duration', {}), {
                        'doc': 'The duration of the event.'}),
                    ('type', ('meta:event:taxonomy', {}), {
                        'doc': 'Type of event.'}),
                )),

                ('meta:event:taxonomy', {}, ()),

                ('meta:ruleset', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A name for the ruleset.'}),
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

                ('meta:rule', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'doc': 'A name for the rule.'}),
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
                        'doc': 'Aribtrary non-indexed msgpack data attached to the node.'}),

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
                        'doc': 'Aribtrary non-indexed msgpack data attached to the event.'}),

                )),

            ),
        }),)
