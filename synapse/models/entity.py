import asyncio
import logging

import synapse.exc as s_exc

#import synapse.lib.chop as s_chop
#import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.version as s_version

class PlanModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('entity', {
            'types': (
                ('entity:name', ('str', {'onespace': True, 'lower': True}), {
                    'doc': 'An entity name which may refer to a person or organization.'}),

                ('entity:contact', ('guid', {}), {
                    'interfaces': ('entity:contact',),
                    'doc': 'A group of contact information which may be resolved to a person or organization.'}),
            ),
            'interfaces': (
                # TODO ('entity:contact', {}),
            ),

            'forms': (
                ('entity:name', {}, ()),
                ('entity:contact', {}, (

                    ('name', ('entity:name', {}), {
                        'doc': 'The current primary name of the contact.'}),

                    ('user', ('inet:user', {}), {
                        'doc': 'The current primary user name of the contact.'}),

                    ('email', ('inet:email', {}), {
                        'doc': 'The current primary email address of the contact.'}),

                    ('jobtitle', ('ou:jobtitle', {}), {
                        'doc': 'The job title assigned to the contact.'}),

                    # TODO ... more props ...
                    # TODO ndef/node prop for resolved -> ps:person | ou:org?

                    ('history', ('array': {'type': 'entity:contact', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of contacts which represent changes to this contact over time.'}),

                    ('period', ('ival', {}), {
                        'doc': 'The period over which this contact was considered current.'}),

                    ('alt:users', ('array', {'type': 'inet:user', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of user names present in the contact record.'}),

                    ('alt:emails', ('array', {'type': 'tel:phone', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of phone numbers present in the contact record.'}),

                    ('alt:phones', ('array', {'type': 'tel:phone', 'sorted': True, 'uniq': True}), {
                        'doc': 'An array of phone numbers present in the contact record.'}),

                )),
            ),
        }),)
