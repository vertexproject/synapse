import asyncio
import logging

import synapse.exc as s_exc

import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.version as s_version

logger = logging.getLogger(__name__)

class BeliefModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('belief', {
            'types': (

                ('belief:system', ('guid', {}), {
                    'doc': 'A belief system such as an ideology, philosophy, or religion.'}),

                ('belief:system:type:taxonomy', ('taxonomy', {}), {
                    'interfaces': ('taxonomy',),
                    'doc': 'A hierarchical taxonomy of belief systems.'}),

                ('belief:tenet', ('guid', {}), {
                    'doc': 'A concrete tenet potentially shared by multiple belief systems.'}),

                ('belief:subscriber', ('guid', {}), {
                    'doc': 'A contact which subscribes to a belief system.'}),
            ),
            'forms': (

                ('belief:system', {}, (

                    ('name', ('str', {'onespace': True, 'lower': True}), {
                        'doc': 'The name of the belief system.'}),

                    ('type', ('belief:system:type:taxonomy', {}), {
                        'doc': 'A taxonometric type for the belief system.'}),

                    ('began', ('time', {}), {
                        'doc': 'The time that the belief system was first observed.'}),

                )),

                ('belief:tenet', {}, (

                    ('name', ('str', {'onespace': True, 'lower': True}), {
                        'doc': 'The name of the tenet.'}),
                )),

                ('belief:subscriber', {}, (

                    ('contact', ('ps:contact', {}), {
                        'doc': 'The contact which subscribes to the belief system.'}),

                    ('system', ('belief:system', {}), {
                        'doc': 'The belief ssytem to which the contact subscribes.'}),

                    ('began', ('time', {}), {
                        'doc': 'The time that the contact began to be a subscriber to the belief system.'}),

                    ('ended', ('time', {}), {
                        'doc': 'The time when the contact ceased to be a subcriber to the belief system.'}),
                )),
            ),
            'edges': (

                (('belief:system', 'has', 'belief:tenet'), {
                    'doc': 'The belief system includes the tenat.'}),

                (('belief:subscriber', 'follows', 'belief:tenet'), {
                    'doc': 'The subscriber is assessed to generally adhere to the specific tenet.'}),
            ),
        }),)
