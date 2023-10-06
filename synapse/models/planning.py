import asyncio
import logging

import synapse.exc as s_exc

#import synapse.lib.chop as s_chop
#import synapse.lib.types as s_types
import synapse.lib.module as s_module
import synapse.lib.version as s_version

class PlanModule(s_module.CoreModule):

    def getModelDefs(self):
        return (('plan', {
            'types': (
                ('plan:system', ('guid', {}), {
                    'doc': 'A planning or behavioral analysis system that defines phases and procedures.'}),

                ('plan:phase', ('guid', {}), {
                    'doc': 'A phase within a planning system which may be used to group actions.'}),

                ('plan:procedure', ('guid', {}), {
                    'doc': 'A procedure consisting of steps which may be conditional.'}),

                ('plan:step', ('guid', {}), {
                    'doc': 'A step within a procedure.'}),

                #('plan:activity', ('guid', {}), {
                    #'doc': 'An instance of executing a series of actions. Possibly an instance of executing a procedure.'}),

                #('plan:action', ('guid', {}), {
                    #'doc': 'An instance of executing an operation within a path. Likely associated with a procedure or phase.'}),
            ),

            'forms': (
                ('plan:system', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'ex': 'mitre att&ck flow'
                        'doc': 'The name of the planning system.'}),
                    ('author' ('ps:contact', {}), {
                        'doc': 'The contact of the authoring person or organization.'}),
                    ('created', ('time', {}), {
                        'doc': 'The time the planning system was first created.'}),
                    ('url', ('inet:url', {}), {
                        'doc': 'The primary URL which documents the planning system.'}),
                )),
                ('plan:phase', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'ex': ''
                        'doc': 'The name of the phase.'}),
                    ('id'
                    ('desc'
                    ('system', ('plan:system', {}), {
                        'doc': 'The planning system which defines this phase.'}),
                )),
                ('plan:step', {}, (
                    ('phase', ('plan:phase', {}), {
                        'doc': 'The phase that the step belongs within.'}),
                    ('procedure', ('plan:procedure', {}), {
                        'doc': 'The procedure which includes the step.'}),
                    ('condition', (''

                    ('next', ('array', {'type': 'plan:step', 'uniq': True}), {
                        'doc': 'The next steps in the procedure.'}),
                )),
                ('plan:procedure', {}, (
                    ('name', ('str', {'lower': True, 'onespace': True}), {
                        'ex': 'apt1 initial access procedure'
                        'doc': 'The name of the procedure.'}),
                )),
                #('plan:activity', {}, ()),
                #('plan:procedure', {}, ()),

            ),
        }),)
