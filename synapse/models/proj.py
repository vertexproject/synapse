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
    (80, 'blocked'),
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
                    ('proj:epic', ('guid', {}), {
                        'doc': 'A collection of tickets related to a topic.',
                    }),
                    ('proj:ticket', ('guid', {}), {
                        'doc': 'A ticket in a ticketing system.',
                    }),
                    ('proj:sprint', ('guid', {}), {
                        'doc': 'A timeboxed period to complete a set amount of work.',
                    }),
                    ('proj:comment', ('guid', {}), {
                        'doc': 'A user comment on a ticket.',
                    }),
                    ('proj:project', ('guid', {}), {
                        'doc': 'A project in a ticketing system.',
                    }),
                    ('proj:attachment', ('guid', {}), {
                        'doc': 'A file attachment added to a ticket or comment.',
                    }),
                ),

                'forms': (

                    ('proj:project', {}, (

                        ('name', ('str', {'lower': True, 'onespace': True}), {
                            'doc': 'The project name.'}),

                        ('desc', ('str', {}), {
                            'disp': {'hint': 'text'},
                            'doc': 'The project description.'}),

                        ('creator', ('syn:user', {}), {
                            'doc': 'The synapse user who created the project.'}),

                        ('created', ('time', {}), {
                            'doc': 'The time the project was created.'}),
                    )),

                    ('proj:sprint', {}, (

                        ('name', ('str', {'lower': True, 'onespace': True}), {
                            'doc': 'The name of the sprint.'}),

                        ('status', ('str', {'enums': 'planned,current,completed'}), {
                            'doc': 'The sprint status.'}),

                        ('project', ('proj:project', {}), {
                            'doc': 'The project containing the sprint.'}),

                        ('creator', ('syn:user', {}), {
                            'doc': 'The synapse user who created the sprint.'}),

                        ('created', ('time', {}), {
                            'doc': 'The date the sprint was created.'}),

                        ('period', ('ival', {}), {
                            'doc': 'The interval for the sprint.'}),

                        ('desc', ('str', {}), {
                            'doc': 'A description of the sprint.'}),
                    )),

                    # TODO this will require a special layer storage mechanism
                    # ('proj:backlog', {}, (

                    ('proj:comment', {}, (

                        ('creator', ('syn:user', {}), {
                            'doc': 'The synapse user who added the comment.'}),

                        ('created', ('time', {}), {
                            'doc': 'The time the comment was added.'}),

                        ('updated', ('time', {'max': True}), {
                            'doc': 'The last time the comment was updated.'}),

                        ('ticket', ('proj:ticket', {}), {
                            'doc': 'The ticket the comment was added to.'}),

                        ('text', ('str', {}), {
                            'doc': 'The text of the comment'}),
                        # -(refs)> thing comment is about
                    )),

                    ('proj:epic', {}, (

                        ('name', ('str', {'onespace': True}), {
                            'doc': 'The name of the epic.'}),

                        ('project', ('proj:project', {}), {
                            'doc': 'The project containing the epic.'}),

                        ('creator', ('syn:user', {}), {
                            'doc': 'The synapse user who created the epic.'}),

                        ('created', ('time', {}), {
                            'doc': 'The time the epic was created.'}),

                        ('updated', ('time', {'max': True}), {
                            'doc': 'The last time the epic was updated.'}),
                    )),

                    ('proj:attachment', {}, (

                        ('name', ('file:base', {}), {
                            'doc': 'The name of the file that was attached.'}),

                        ('file', ('file:bytes', {}), {
                            'doc': 'The file that was attached.'}),

                        ('creator', ('syn:user', {}), {
                            'doc': 'The synapse user who added the attachment.'}),

                        ('created', ('time', {}), {
                            'doc': 'The time the attachment was added.'}),

                        ('ticket', ('proj:ticket', {}), {
                            'doc': 'The ticket the attachment was added to.'}),

                        ('comment', ('proj:comment', {}), {
                            'doc': 'The comment the attachment was added to.'}),
                    )),

                    ('proj:ticket', {}, (

                        ('project', ('proj:project', {}), {
                            'doc': 'The project containing the ticket.'}),

                        ('ext:id', ('str', {'strip': True}), {
                            'doc': 'A ticket ID from an external system.'}),

                        ('ext:url', ('inet:url', {}), {
                            'doc': 'A URL to the ticket in an external system.'}),

                        ('ext:creator', ('ps:contact', {}), {
                            'doc': 'Ticket creator contact information from an external system.'}),

                        ('epic', ('proj:epic', {}), {
                            'doc': 'The epic that includes the ticket.'}),

                        ('created', ('time', {}), {
                            'doc': 'The time the ticket was created.'}),

                        ('updated', ('time', {'max': True}), {
                            'doc': 'The last time the ticket was updated.'}),

                        ('name', ('str', {'onespace': True}), {
                            'doc': 'The name of the ticket.'}),

                        ('desc', ('str', {}), {
                            'doc': 'A description of the ticket.'}),

                        ('points', ('int', {}), {
                            'doc': 'Optional SCRUM style story points value.'}),

                        ('status', ('int', {'enums': statusenums}), {
                            'doc': 'The ticket completion status.'}),

                        ('sprint', ('proj:sprint', {}), {
                            'doc': 'The sprint that contains the ticket.'}),

                        ('priority', ('int', {'enums': prioenums}), {
                            'doc': 'The priority of the ticket.'}),

                        ('type', ('str', {'lower': True, 'strip': True}), {
                            'doc': 'The type of ticket. (eg story / bug)'}),

                        ('creator', ('syn:user', {}), {
                            'doc': 'The synapse user who created the ticket.'}),

                        ('assignee', ('syn:user', {}), {
                            'doc': 'The synapse user who the ticket is assigned to.'}),
                    )),
                ),
            }),
        )
