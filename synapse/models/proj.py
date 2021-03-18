import synapse.common as s_common

import synapse.lib.module as s_module

prioenums = (
    (0, 'none'),
    (10, 'lowest'),
    (20, 'low'),
    (30, 'medium'),
    (40, 'high'),
    (50, 'highest'),
)

statusenums = (
    (0, 'new'),
    (10, 'in validation'),
    (20, 'in backlog'),
    (30, 'in sprint'),
    (40, 'in progress'),
    (50, 'in review'),
    (60, 'completed'),
    (70, 'done'),
)

class ProjectModule(s_module.CoreModule):

    async def initCoreModule(self):
        self.model.form('proj:project').onAdd(self._onAddProj)
        self.model.form('proj:project').onDel(self._onDelProj)

    async def _onAddProj(self, node):
        # ref counts on authgates?
        gateiden = node.ndef[1]

        await self.core.auth.addAuthGate(node.ndef[1], 'storm:project')

        useriden = node.snap.user.iden

        rule = (True, ('project', 'admin'))
        await node.snap.user.addRule(rule, gateiden=gateiden)

    async def _onDelProj(self, node):
        gateiden = node.ndef[1]
        await self.core.auth.delAuthGate(gateiden)

    def getModelDefs(self):
        return (

            ('proj', {

                'types': (
                    ('proj:epic', ('guid', {}), {}),
                    ('proj:ticket', ('guid', {}), {}),
                    ('proj:sprint', ('guid', {}), {}),
                    ('proj:comment', ('guid', {}), {}),
                    ('proj:project', ('guid', {}), {}),
                ),

                'forms': (

                    ('proj:project', {}, (
                        ('name', ('str', {'lower': True, 'strip': True, 'onespace': True}), {}),
                        ('creator', ('syn:user', {}), {}),
                        ('created', ('time', {}), {}),
                        ('updated', ('time', {}), {}),
                    )),

                    ('proj:sprint', {}, (
                        ('name', ('str', {'lower': True, 'strip': True, 'onespace': True}), {}),
                        ('project', ('proj:project', {}), {}),
                        ('creator', ('syn:user', {}), {}),
                        ('created', ('time', {}), {}),
                        ('period', ('ival', {}), {}),
                    )),

                    # TODO this will require a special layer storage mechanism
                    #('proj:backlog', {}, (

                    ('proj:comment', {}, (
                        ('creator', ('syn:user', {}), {}),
                        ('created', ('time', {}), {}),
                        ('updated', ('time', {}), {}),
                        ('ticket', ('proj:ticket', {}), {}),
                        ('text', ('str', {}), {}),
                        # -(refs)> thing comment is about
                    )),

                    ('proj:epic', {}, (
                        ('name', ('str', {'strip': True, 'onespace': True}), {}),
                        ('project', ('proj:project', {}), {}),

                        ('creator', ('syn:user', {}), {}),
                        ('created', ('time', {}), {}),
                        ('updated', ('time', {'max': True}), {}),
                    )),

                    ('proj:ticket', {}, (

                        ('project', ('proj:project', {}), {}),

                        ('ext:id', ('str', {'strip': True}), {
                            'doc': 'A ticket ID from an external system.'}),

                        ('ext:url', ('inet:url', {}), {
                            'doc': 'A URL to the ticket in an external system.'}),

                        ('epic', ('proj:epic', {}), {}),
                        ('created', ('time', {}), {}),
                        ('updated', ('time', {'max': True}), {}),

                        ('name', ('str', {'strip': True, 'onespace': True}), {}),
                        ('desc', ('str', {}), {}),
                        ('status', ('int', {'enums': statusenums}), {}),
                        ('sprint', ('proj:sprint', {}), {}),
                        ('priority', ('int', {'enums': prioenums}), {}),

                        ('type', ('str', {'lower': True, 'strip': True}), {}),

                        ('creator', ('syn:user', {}), {}),
                        ('assignee', ('syn:user', {}), {}),
                    )),
                ),
            }),
        )
