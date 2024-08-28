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

    def getModelDefs(self):

        return (('base', {

            'types': (

                ('meta:source', ('guid', {}), {
                    'doc': 'A data source unique identifier.'}),

                ('meta:seen', ('comp', {'fields': (('source', 'meta:source'), ('node', 'ndef'))}), {
                    'doc': 'Annotates that the data in a node was obtained from or observed by a given source.'}),

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

                ('meta:ruleset', ('guid', {}), {
                    'doc': 'A set of rules linked with -(has)> edges.'}),

                ('meta:rule:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('meta:taxonomy',),
                    'doc': 'A hierarchical taxonomy of rule types.'}),

                ('meta:rule', ('guid', {}), {
                    'doc': 'A generic rule linked to matches with -(matches)> edges.'}),

                ('meta:priority', ('int', {'enums': prioenums, 'enums:strict': False}), {
                    'doc': 'A generic priority enumeration.'}),

                ('meta:severity', ('int', {'enums': prioenums, 'enums:strict': False}), {
                    'doc': 'A generic severity enumeration.'}),

                ('meta:sophistication', ('int', {'enums': sophenums}), {
                    'doc': 'A sophistication score with named values: very low, low, medium, high, and very high.'}),
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
                (('meta:note', 'about', None), {
                    'doc': 'The meta:note is about the target node.'
                }),
                (('meta:ruleset', 'has', 'meta:rule'), {
                    'doc': 'The meta:ruleset includes the meta:rule.'}),
                (('meta:rule', 'matches', None), {
                    'doc': 'The meta:rule has matched on target node.'}),
                (('meta:rule', 'detects', None), {
                    'doc': 'The meta:rule is designed to detect instances of the target node.'}),
            ),
            'forms': (

                ('meta:source:type:taxonomy', {}, ()),
                ('meta:source', {}, (

                    ('name', ('str', {'lower': True}), {
                        'doc': 'A human friendly name for the source.'}),

                    ('type', ('meta:source:type:taxonomy', {'lower': True}), {
                        'doc': 'The type of source.'}),

                    ('url', ('inet:url', {}), {
                        'doc': 'A URL which documents the meta source.'}),
                )),

                ('meta:seen', {}, (

                    ('source', ('meta:source', {}), {'ro': True,
                        'doc': 'The source which observed or provided the node.'}),

                    ('node', ('ndef', {}), {'ro': True,
                        'doc': 'The node which was observed by or received from the source.'}),

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
                    ('type', ('meta:timeline:type:taxonomy', {}), {
                        'doc': 'The type of timeline.'}),
                )),

                ('meta:timeline:type:taxonomy', {}, ()),

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

                ('meta:event:type:taxonomy', {}, ()),

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

            ),
        }),)
