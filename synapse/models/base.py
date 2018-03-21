import logging

import synapse.common as s_common

import synapse.lib.tufo as s_tufo
import synapse.lib.module as s_module

logger = logging.getLogger(__name__)

class BaseMod(s_module.CoreModule):

    @staticmethod
    def getBaseModels():
        modl = {

            'types': (

                ('source', {
                    'subof': 'guid',
                    'doc': 'A unique source of data.'}),

                ('seen', {
                    'subof': 'comp',
                    'fields': 'source=source,node=node:ndef',
                    'doc': 'Annotates that the data in a node was obtained from or observed by a given source.'}),

                ('record', {
                    'subof': 'guid',
                    'doc': 'A flexible clustering type used for custom records that reference other nodes.'}),

                ('recref', {
                    'subof': 'comp',
                    'fields': 'record=record,node=ndef',
                    'doc': 'A record reference used to connect records to nodes which they group'}),
            ),

            'forms': (

                ('source', {}, (
                    ('name', {'ptype': 'str:lwr',
                        'doc': 'A human friendly name for the source.'}),
                    ('type', {'ptype': 'str:lwr',
                        'doc': 'An optional type field used to group sources.'}),
                )),

                ('seen', {}, (
                    ('source', {'ptype': 'source', 'req': 1, 'ro': 1,
                        'doc': 'The source which observed or provided the node.'}),
                    ('node', {'ptype': 'ndef', 'req': 1, 'ro': 1,
                        'doc': 'The node which was observed by or received from the source.'}),
                    ('node:form', {'ptype': 'syn:prop', 'req': 1, 'ro': 1,
                        'doc': 'The form of the observed node.'}),
                    ('time:min', {'ptype': 'time:min',
                        'doc': 'An optional earliest time the data in the node was observed by the source.'}),
                    ('time:max', {'ptype': 'time:max',
                        'doc': 'An optional most recent time the data in the node was observed by the source.'}),
                )),

                ('record', {}, (
                    ('type', {'ptype': 'str:lwr', 'req': 1, 'ro': 1,
                        'doc': 'The type name for the record.  Used to group records by expected relationships.'}),
                    ('name', {'ptype': 'str:lwr',
                        'doc': 'A human readable name for this record.'}),
                )),

                ('recref', {}, (
                    ('record', {'ptype': 'record', 'req': 1, 'ro': 1,
                        'doc': 'The record which references the target node.'}),
                    ('node', {'ptype': 'ndef', 'req': 1, 'ro': 1,
                        'doc': 'The node which the record references.'}),
                    ('node:form', {'ptype': 'syn:prop', 'req': 1, 'ro': 1,
                        'doc': 'The :type field from the record node.'}),
                )),
            ),
        }

        return (
            ('base', modl),
        )
