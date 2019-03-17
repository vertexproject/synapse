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

                    ('source', ('meta:source', {}), {'ro': 1,
                        'doc': 'The source which observed or provided the node.'}),

                    ('node', ('ndef', {}), {'ro': 1,
                        'doc': 'The node which was observed by or received from the source.'}),

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
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),
                )),

                ('edge:refs', {}, (
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),
                )),

                ('edge:wentto', {}, (
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),

                    ('time', ('time', {}), {'ro': 1}),
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
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),
                )),

                ('graph:timeedge', {}, (
                    ('time', ('time', {}), {'ro': 1}),
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),
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
