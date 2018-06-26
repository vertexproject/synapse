import logging

import synapse.common as s_common

import synapse.lib.tufo as s_tufo
import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

class BaseModule(s_module.CoreModule):

    def getModelDefs(self):

        return (('base', {

            'types': (

                ('source', ('guid', {}), {
                    'doc': 'A data source unique identifier.'}),

                ('seen', ('comp', {'fields': (('source', 'source'), ('node', 'ndef'))}), {
                    'doc': 'Annotates that the data in a node was obtained from or observed by a given source.'}),

                ('record', ('guid', {}), {
                    'doc': 'A node to represent an external record or super-model node.'}),

                ('verb', ('str', {'lower': True}), {
                    'doc': 'A relationship described by a digraph edge.'}),
            ),

            'forms': (

                ('source', {}, (
                    ('name', ('str', {'lower': True}), {
                        'doc': 'A human friendly name for the source.'}),
                    ('type', ('str', {'lower': True}), {
                        'doc': 'An optional type field used to group sources.'}),
                )),

                ('seen', {}, (

                    ('source', ('source', {}), {'ro': 1,
                        'doc': 'The source which observed or provided the node.'}),

                    ('node', ('ndef', {}), {'ro': 1,
                        'doc': 'The node which was observed by or received from the source.'}),

                )),

                ('edge', {}, (

                    ('n1', ('ndef', {}), {'ro': 1,
                        'doc': 'The "source" node for the digraph edge.'}),

                    ('n1:form', ('str', {}), {'ro': 1,
                        'doc': 'The form name of the source node.'}),

                    ('verb', ('verb', {}), {
                        'doc': 'The relationship type described by the digraph edge.'}),

                    ('n2', ('ndef', {}), {'ro': 1,
                        'doc': 'The "destination" node for the digraph edge.'}),

                    ('n2:form', ('str', {}), {'ro': 1,
                        'doc': 'The form name of the destination node.'}),
                )),

                ('record', {}, (

                    ('type', ('str', {'lower': True}), {
                        'doc': 'The type name for the record.  Used to group records by expected relationships.'}),

                    ('name', ('str', {}), {
                        'doc': 'A human readable name for this record.'}),

                    ('data', ('data', {}), {
                        'doc': 'Aribtrary msgpack data which represents the record.'}),

                )),
            ),
        }),)
