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

                ('verb', ('str', {'lower': True, 'onespace': True}), {
                    'doc': 'An extesible digraph edge type name.'}),

                ('edge', ('comp', {'fields': (('n1', 'ndef'), ('verb', 'verb'), ('n2', 'ndef'))}), {
                    'doc': 'An extensible digraph edge like node allowing linking of any two nodes using a verb.'}),

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

                #('record', {}, (
                    #('type', {'ptype': 'str:lwr', 'req': 1, 'ro': 1,
                        #'doc': 'The type name for the record.  Used to group records by expected relationships.'}),
                    #('name', {'ptype': 'str:lwr',
                        #'doc': 'A human readable name for this record.'}),
                #)),

                #('recref', {}, (
                    #('record', {'ptype': 'record', 'req': 1, 'ro': 1,
                        #'doc': 'The record which references the target node.'}),
                    #('node', {'ptype': 'ndef', 'req': 1, 'ro': 1,
                        #'doc': 'The node which the record references.'}),
                    #('node:form', {'ptype': 'syn:prop', 'req': 1, 'ro': 1,
                        #'doc': 'The :type field from the record node.'}),
                #)),
            ),
        }),)
