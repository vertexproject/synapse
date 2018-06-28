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

                ('node', ('guid', {}), {
                    'doc': 'A generic node used to represent objects outside the model.'}),

                ('event', ('guid', {}), {
                    'doc': 'A generic event node to represent events outside the model.'}),

                ('refs', ('edge', {}), {
                    'doc': 'A digraph edge which records that N1 refers to or contains N2.'}),

                ('has', ('edge', {}), {
                    'doc': 'A digraph edge which records that N1 has N2.'}),

                ('wentto', ('timeedge', {}), {
                    'doc': 'A digraph edge which records that N1 went to N2 at a specific time.'}),
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

                ('has', {}, (
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),
                )),

                ('refs', {}, (
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),
                )),

                ('wentto', {}, (
                    ('n1', ('ndef', {}), {'ro': 1}),
                    ('n1:form', ('str', {}), {'ro': 1}),
                    ('n2', ('ndef', {}), {'ro': 1}),
                    ('n2:form', ('str', {}), {'ro': 1}),

                    ('time', ('time', {}), {'ro': 1}),
                )),

                ('node', {}, (

                    ('type', ('str', {'lower': True}), {
                        'doc': 'The type name for the non-model node.'}),

                    ('name', ('str', {}), {
                        'doc': 'A human readable name for this record.'}),

                    ('data', ('data', {}), {
                        'doc': 'Aribtrary non-indexed json/msgpack data attached to the node.'}),

                )),

                ('event', {}, (

                    ('time', ('time', {}), {
                        'doc': 'The time of the event.'}),

                    ('name', ('str', {}), {
                        'doc': 'A name for the event.'}),

                    ('data', ('data', {}), {
                        'doc': 'Aribtrary non-indexed json/msgpack data attached to the event.'}),

                )),

            ),
        }),)
