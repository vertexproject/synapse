import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

from synapse.lib.stormtypes import tostr

@s_stormtypes.registry.registerType
class ProjectEpic(s_stormtypes.Prim):
    '''
    Implements the Storm API for a ProjectEpic
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the Epic. This can be used to set the name as well.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setEpicName', '_gtorfunc': '_getName',
                          'returns': {'type': ['str', 'null'], }}},
    )
    _storm_typename = 'storm:project:epic'

    def __init__(self, proj, node):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.node = node
        self.gtors.update({
            'name': self._getName,
        })
        self.stors.update({
            'name': self._setEpicName,
        })

    async def value(self):
        return self.node.ndef[1]

    async def nodes(self):
        yield self.node

    async def _setEpicName(self, valu):
        self.proj.confirm(('project', 'epic', 'set', 'name'))
        name = await tostr(valu, noneok=True)
        if name is None:
            await self.node.pop('name')
        else:
            await self.node.set('name', name)

    async def _getName(self):
        return self.node.get('name')

@s_stormtypes.registry.registerType
class ProjectEpics(s_stormtypes.Prim):
    '''
    Implements the Storm API for ProjectEpics objects, which are collections of ProjectEpic
    objects associated with a particular Project
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get an epic by name.',
         'type': {'type': 'function', '_funcname': '_getProjEpic',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name (or iden) of the ProjectEpic to get.'},
                  ),
                  'returns': {'type': 'storm:project:epic', 'desc': 'The `storm:project:epic` object', }}},
        {'name': 'add', 'desc': 'Add an epic.',
         'type': {'type': 'function', '_funcname': '_addProjEpic',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name for the new ProjectEpic.'},
                  ),
                  'returns': {'type': 'storm:project:epic', 'desc': 'The newly created `storm:project:epic` object', }}},
        {'name': 'del', 'desc': 'Delete an epic by name.',
         'type': {'type': 'function', '_funcname': '_delProjEpic',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the ProjectEpic to delete.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the ProjectEpic can be found and deleted, otherwise False', }}}
    )
    _storm_typename = 'storm:project:epics'

    def __init__(self, proj):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._getProjEpic,
            'add': self._addProjEpic,
            'del': self._delProjEpic,
        }

    async def _getProjEpic(self, name):
        return await self.proj._getProjEpic(name)

    async def _delProjEpic(self, name):

        self.proj.confirm(('project', 'epic', 'del'))
        epic = await self.proj._getProjEpic(name)
        if epic is None:
            return False

        nodeedits = []
        async for tick in self.proj.runt.snap.nodesByPropValu('proj:ticket:epic', '=', epic.node.ndef[1]):
            nodeedits.append(
                (tick.buid, 'proj:ticket', await tick._getPropDelEdits('epic'))
            )
            await asyncio.sleep(0)

        await self.proj.runt.snap.applyNodeEdits(nodeedits)
        await epic.node.delete()
        return True

    async def _addProjEpic(self, name):
        self.proj.confirm(('project', 'epic', 'add'))
        tick = s_common.now()
        props = {
            'name': await tostr(name),
            'created': tick,
            'creator': self.proj.runt.user.iden,
            'project': self.proj.node.ndef[1],
        }
        node = await self.proj.runt.snap.addNode('proj:epic', '*', props=props)
        return ProjectEpic(self.proj, node)

    async def iter(self):
        opts = {'vars': {'proj': self.proj.node.ndef[1]}}
        async for node, path in self.proj.runt.storm('proj:epic:project=$proj', opts=opts):
            yield ProjectEpic(self.proj, node)

@s_stormtypes.registry.registerType
class ProjectTicketComment(s_stormtypes.Prim):
    '''
    Implements the Storm API for a ProjectTicketComment
    '''
    _storm_locals = (
        {'name': 'text', 'desc': 'The comment text. This can be used to set the text as well.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setCommentText', '_gtorfunc': '_getCommentText',
                  'returns': {'type': ['str', 'null'], }}},
        {'name': 'del', 'desc': 'Delete the comment.',
         'type': {'type': 'function', '_funcname': '_delTicketComment',
                  'returns': {'type': 'boolean', 'desc': 'True if the ProjectTicketComment was deleted'}}},
    )

    _storm_typename = 'storm:project:ticket:comment'

    def __init__(self, ticket, node):
        s_stormtypes.Prim.__init__(self, None)
        self.node = node
        self.proj = ticket.proj
        self.ticket = ticket
        self.locls.update(self.getObjLocals())
        self.stors.update({
            'text': self._setCommentText,
        })
        self.gtors.update({
            'text': self._getCommentText,
        })

    def getObjLocals(self):
        return {
            'del': self._delTicketComment,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def value(self):
        if self.node is None:
            raise s_exc.StormRuntimeError(mesg='Comment has been deleted')
        return self.node.ndef[1]

    async def nodes(self):
        yield self.node

    async def _getCommentText(self):
        if self.node is None:
            raise s_exc.StormRuntimeError(mesg='Comment has been deleted')
        return self.node.get('text')

    async def _setCommentText(self, valu):

        if self.node is None:
            raise s_exc.StormRuntimeError(mesg='Comment has been deleted')

        useriden = self.proj.runt.user.iden
        if useriden != self.node.get('creator'):
            raise s_exc.AuthDeny(mesg='Comment was created by a different user')

        strvalu = await tostr(valu)
        await self.node.set('text', strvalu)
        await self.node.set('updated', s_common.now())

    async def _delTicketComment(self):

        if self.node is None:
            raise s_exc.StormRuntimeError(mesg='Comment has been deleted')

        if self.node.get('creator') != self.proj.runt.user.iden:
            self.proj.confirm(('project', 'comment', 'del'))

        await self.node.delete()
        self.node = None
        return True

@s_stormtypes.registry.registerType
class ProjectTicketComments(s_stormtypes.Prim):
    '''
    Implements the Storm API for ProjectTicketComments objects, which are collections of comments
    associated with a ticket.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a ticket comment by guid.',
         'type': {'type': 'function', '_funcname': '_getTicketComment',
                  'args': (
                      {'name': 'guid', 'type': 'str', 'desc': 'The guid of the ProjectTicketComment to get.'},
                  ),
                  'returns': {'type': 'storm:project:ticket:comment',
                              'desc': 'The `storm:project:ticket:comment` object', }}},
        {'name': 'add', 'desc': 'Add a comment to the ticket.',
         'type': {'type': 'function', '_funcname': '_addTicketComment',
                  'args': (
                      {'name': 'text', 'type': 'str', 'desc': 'The text for the new ProjectTicketComment.'},
                  ),
                  'returns': {'type': 'storm:project:ticket:comment',
                              'desc': 'The newly created `storm:project:ticketcomment` object', }}},
    )

    _storm_typename = 'storm:project:ticket:comments'

    def __init__(self, ticket):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = ticket.proj
        self.ticket = ticket
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'add': self._addTicketComment,
            'get': self._getTicketComment,
        }

    async def _addTicketComment(self, text):
        self.proj.confirm(('project', 'comment', 'add'))
        tick = s_common.now()
        props = {
            'text': await tostr(text),
            'ticket': self.ticket.node.ndef[1],
            'created': tick,
            'updated': tick,
            'creator': self.proj.runt.user.iden,
        }
        node = await self.proj.runt.snap.addNode('proj:comment', '*', props=props)
        return ProjectTicketComment(self.ticket, node)

    @s_stormtypes.stormfunc(readonly=True)
    async def _getTicketComment(self, guid):

        async def filt(node):
            return node.get('ticket') == self.ticket.node.ndef[1]

        guid = await tostr(guid)

        node = await self.proj.runt.getOneNode('proj:comment', guid, filt=filt, cmpr='=')
        if node is not None:
            return ProjectTicketComment(self.ticket, node)

        return None

    @s_stormtypes.stormfunc(readonly=True)
    async def iter(self):
        opts = {'vars': {'ticket': self.ticket.node.ndef[1]}}
        async for node, path in self.proj.runt.storm('proj:comment:ticket=$ticket', opts=opts):
            yield ProjectTicketComment(self.ticket, node)

@s_stormtypes.registry.registerType
class ProjectTicket(s_stormtypes.Prim):
    '''
    Implements the Storm API for a ProjectTicket.
    '''
    _storm_locals = (
        {'name': 'desc', 'desc': 'A description of the ticket. This can be used to set the description.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setDesc', '_gtorfunc': '_getTicketDesc',
                  'returns': {'type': ['str', 'null'], }}},
        {'name': 'epic', 'desc': 'The epic associated with the ticket. This can be used to set the epic.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setEpic', '_gtorfunc': '_getTicketEpic',
                  'returns': {'type': ['str', 'null'], }}},
        {'name': 'name', 'desc': 'The name of the ticket. This can be used to set the name of the ticket.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setName', '_gtorfunc': '_getTicketName',
                          'returns': {'type': ['str', 'null'], }}},
        {'name': 'status', 'desc': 'The status of the ticket. This can be used to set the status of the ticket.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setStatus', '_gtorfunc': '_getTicketStatus',
                  'returns': {'type': ['int', 'null'], }}},
        {'name': 'sprint', 'desc': 'The sprint the ticket is in. This can be used to set the sprint this ticket is in.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setSprint', '_gtorfunc': '_getTicketSprint',
                  'returns': {'type': ['int', 'null'], }}},
        {'name': 'assignee',
         'desc': 'The user the ticket is assigned to. This can be used to set the assignee of the ticket.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setAssignee', '_gtorfunc': '_getTicketAssignee',
                  'returns': {'type': ['int', 'null'], }}},
        {'name': 'priority',
         'desc': 'An integer value from the enums [0, 10, 20, 30, 40, 50] of the priority of the ticket. This can be used to set the priority of the ticket.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setPriority', '_gtorfunc': '_getTicketPriority',
                          'returns': {'type': ['int', 'null'], }}},
        {'name': 'comments',
         'desc': 'A ``storm:project:ticket:comments`` object that contains comments associated with the given ticket.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorTicketComments',
                  'returns': {'type': 'storm:project:ticket:comments', }}},
    )

    _storm_typename = 'storm:project:ticket'

    def __init__(self, proj, node):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.node = node
        self.ctors.update({
            'comments': self._ctorTicketComments,
        })
        self.gtors.update({
            'desc': self._getTicketDesc,
            'epic': self._getTicketEpic,
            'name': self._getTicketName,
            'status': self._getTicketStatus,
            'sprint': self._getTicketSprint,
            'assignee': self._getTicketAssignee,
            'priority': self._getTicketPriority,
        })
        self.stors.update({
            'desc': self._setDesc,
            'epic': self._setEpic,
            'name': self._setName,
            'status': self._setStatus,
            'sprint': self._setSprint,
            'assignee': self._setAssignee,
            'priority': self._setPriority,
        })

    async def _getTicketDesc(self):
        return self.node.get('desc')

    async def _getTicketEpic(self):
        return self.node.get('epic')

    async def _getTicketName(self):
        return self.node.get('name')

    async def _getTicketStatus(self):
        return self.node.get('status')

    async def _getTicketSprint(self):
        return self.node.get('sprint')

    async def _getTicketAssignee(self):
        return self.node.get('assignee')

    async def _getTicketPriority(self):
        return self.node.get('priority')

    @s_stormtypes.stormfunc(readonly=True)
    async def value(self):
        return self.node.ndef[1]

    async def nodes(self):
        yield self.node

    async def _setName(self, valu):

        useriden = self.proj.runt.user.iden
        if useriden != self.node.get('creator'):
            self.proj.confirm(('project', 'ticket', 'set', 'name'))

        strvalu = await tostr(valu, noneok=True)
        if strvalu is None:
            await self.node.pop('name')
        else:
            await self.node.set('name', strvalu)
        await self.node.set('updated', s_common.now())

    async def _setDesc(self, valu):

        useriden = self.proj.runt.user.iden
        if useriden != self.node.get('creator'):
            self.proj.confirm(('project', 'ticket', 'set', 'desc'))

        strvalu = await tostr(valu, noneok=True)
        if strvalu is None:
            await self.node.pop('desc')
        else:
            await self.node.set('desc', strvalu)
        await self.node.set('updated', s_common.now())

    async def _setEpic(self, valu):

        useriden = self.proj.runt.user.iden
        if useriden != self.node.get('creator'):
            self.proj.confirm(('project', 'ticket', 'set', 'epic'))

        strvalu = await tostr(valu, noneok=True)
        if strvalu is None:
            await self.node.pop('epic')
            await self.node.set('updated', s_common.now())
            return

        epic = await self.proj._getProjEpic(strvalu)
        if epic is None:
            mesg = 'No epic found by that name/iden.'
            raise s_exc.NoSuchName(mesg=mesg)

        await self.node.set('epic', epic.node.ndef[1])
        await self.node.set('updated', s_common.now())

    async def _setStatus(self, valu):

        useriden = self.proj.runt.user.iden
        if useriden != self.node.get('assignee'):
            self.proj.confirm(('project', 'ticket', 'set', 'status'))

        strvalu = await tostr(valu)
        await self.node.set('status', strvalu)
        await self.node.set('updated', s_common.now())

    async def _setPriority(self, valu):

        self.proj.confirm(('project', 'ticket', 'set', 'priority'))

        strvalu = await tostr(valu)
        await self.node.set('priority', strvalu)
        await self.node.set('updated', s_common.now())

    async def _setAssignee(self, valu):

        self.proj.confirm(('project', 'ticket', 'set', 'assignee'))

        strvalu = await tostr(valu, noneok=True)

        if strvalu is None:
            await self.node.pop('assignee')
            await self.node.set('updated', s_common.now())
            return

        udef = await self.proj.runt.snap.core.getUserDefByName(strvalu)
        if udef is None:
            mesg = f'No user found by the name {strvalu}'
            raise s_exc.NoSuchUser(mesg=mesg)
        await self.node.set('assignee', udef['iden'])
        await self.node.set('updated', s_common.now())

    async def _setSprint(self, valu):

        self.proj.confirm(('project', 'ticket', 'set', 'sprint'))

        strvalu = await tostr(valu, noneok=True)

        if strvalu is None:
            await self.node.pop('sprint')
            await self.node.set('updated', s_common.now())
            return

        sprint = await self.proj._getProjSprint(strvalu)
        if sprint is None:
            mesg = f'No sprint found by that name/iden ({strvalu}).'
            raise s_exc.NoSuchName(mesg=mesg)

        await self.node.set('sprint', sprint.node.ndef[1])
        await self.node.set('updated', s_common.now())

    def _ctorTicketComments(self, path=None):
        return ProjectTicketComments(self)

@s_stormtypes.registry.registerType
class ProjectTickets(s_stormtypes.Prim):
    '''
    Implements the Storm API for ProjectTickets objects, which are collections of tickets
    associated with a project
    '''

    _storm_typename = 'storm:project:tickets'
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a ticket by name.',
         'type': {'type': 'function', '_funcname': '_getProjTicket',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name (or iden) of the ProjectTicket to get.'},
                  ),
                  'returns': {'type': 'storm:project:ticket', 'desc': 'The `storm:project:ticket` object', }}},
        {'name': 'add', 'desc': 'Add a ticket.',
         'type': {'type': 'function', '_funcname': '_addProjTicket',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name for the new ProjectTicket.'},
                      {'name': 'desc', 'type': 'str', 'desc': 'A description of the new ticket', 'default': ''},
                  ),
                  'returns': {'type': 'storm:project:ticket', 'desc': 'The newly created `storm:project:ticket` object', }}},
        {'name': 'del', 'desc': 'Delete a sprint by name.',
         'type': {'type': 'function', '_funcname': '_delProjTicket',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the ProjectTicket to delete.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the ProjectTicket can be found and deleted, otherwise False', }}}
    )

    def __init__(self, proj):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._getProjTicket,
            'add': self._addProjTicket,
            'del': self._delProjTicket,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def _getProjTicket(self, name):

        async def filt(node):
            return node.get('project') == self.proj.node.ndef[1]

        name = await tostr(name)

        node = await self.proj.runt.getOneNode('proj:ticket:name', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectTicket(self.proj, node)

        node = await self.proj.runt.getOneNode('proj:ticket', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectTicket(self.proj, node)

        return None

    async def _delProjTicket(self, name):

        tick = await self._getProjTicket(name)
        if tick is None:
            return False

        if tick.node.get('creator') != self.proj.runt.user.iden:
            self.proj.confirm(('project', 'ticket', 'del'))

        # cascade delete comments
        async for node in self.proj.runt.snap.nodesByPropValu('proj:comment:ticket', '=', tick.node.ndef[1]):
            await node.delete()

        await tick.node.delete()
        return True

    async def _addProjTicket(self, name, desc=''):
        self.proj.confirm(('project', 'ticket', 'add'))
        tick = s_common.now()
        props = {
            'name': await tostr(name),
            'desc': await tostr(desc),
            'status': 0,
            'priority': 0,
            'created': tick,
            'updated': tick,
            'creator': self.proj.runt.user.iden,
            'project': self.proj.node.ndef[1],
        }
        node = await self.proj.runt.snap.addNode('proj:ticket', '*', props=props)
        return ProjectTicket(self.proj, node)

    @s_stormtypes.stormfunc(readonly=True)
    async def iter(self):
        opts = {'vars': {'proj': self.proj.node.ndef[1]}}
        async for node, path in self.proj.runt.storm('proj:ticket:project=$proj', opts=opts):
            yield ProjectTicket(self.proj, node)

@s_stormtypes.registry.registerType
class ProjectSprint(s_stormtypes.Prim):
    '''
    Implements the Storm API for a ProjectSprint
    '''

    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the sprint. This can also be used to set the name.',
          'type': {'type': ['gtor', 'stor'], '_storfunc': '_setSprintName', '_gtorfunc': '_getSprintName',
          'returns': {'type': ['str', 'null'], }}},
        {'name': 'desc', 'desc': 'A description of the sprint. This can also be used to set the description.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setSprintDesc', '_gtorfunc': '_getSprintDesc',
          'returns': {'type': ['str', 'null'], }}},
        {'name': 'status', 'desc': 'The status of the sprint. This can also be used to set the status.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setSprintStatus', '_gtorfunc': '_getSprintStatus',
                  'returns': {'type': ['int', 'null'], }}},
        {'name': 'tickets', 'desc': 'Yields out the tickets associated with the given sprint (no call needed).',
         'type': {'type': 'ctor', '_ctorfunc': '_getSprintTickets',
                  'returns': {'type': 'generator', }}},
    )

    _storm_typename = 'storm:project:sprint'

    def __init__(self, proj, node):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.node = node
        self.ctors.update({
            'tickets': self._getSprintTickets,
        })
        self.stors.update({
            'name': self._setSprintName,
            'desc': self._setSprintDesc,
            'status': self._setSprintStatus,
        })
        self.gtors.update({
            'name': self._getSprintName,
            'desc': self._getSprintDesc,
            'status': self._getSprintStatus,
        })

    async def _getSprintDesc(self):
        return self.node.get('desc')

    async def _getSprintName(self):
        return self.node.get('name')

    async def _getSprintStatus(self):
        return self.node.get('status')

    async def _setSprintStatus(self, valu):
        self.proj.confirm(('project', 'sprint', 'set', 'status'))
        valu = await tostr(valu, noneok=True)
        if valu is None:
            await self.node.pop('status')
        else:
            await self.node.set('status', valu)

    async def _setSprintDesc(self, valu):
        self.proj.confirm(('project', 'sprint', 'set', 'desc'))
        valu = await tostr(valu, noneok=True)
        if valu is None:
            await self.node.pop('desc')
        else:
            await self.node.set('desc', valu)

    async def _setSprintName(self, valu):

        self.proj.confirm(('project', 'sprint', 'set', 'name'))
        valu = await tostr(valu, noneok=True)
        if valu is None:
            await self.node.pop('name')
        else:
            await self.node.set('name', valu)

    async def _getSprintTickets(self, path=None):
        async for node in self.proj.runt.snap.nodesByPropValu('proj:ticket:sprint', '=', self.node.ndef[1]):
            yield ProjectTicket(self.proj, node)

    @s_stormtypes.stormfunc(readonly=True)
    async def value(self):
        return self.node.ndef[1]

    async def nodes(self):
        yield self.node

@s_stormtypes.registry.registerType
class ProjectSprints(s_stormtypes.Prim):
    '''
    Implements the Storm API for ProjectSprints objects, which are collections of sprints
    associated with a single project
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Get a sprint by name.',
         'type': {'type': 'function', '_funcname': '_getProjSprint',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name (or iden) of the ProjectSprint to get.'},
                  ),
                  'returns': {'type': 'storm:project:sprint', 'desc': 'The `storm:project:sprint` object', }}},
        {'name': 'add', 'desc': 'Add a sprint.',
         'type': {'type': 'function', '_funcname': '_addProjSprint',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name for the new ProjectSprint.'},
                      {'name': 'period', 'type': 'ival', 'desc': 'The time interval the ProjectSprint runs for',
                       'default': None},
                  ),
                  'returns': {'type': 'storm:project:sprint', 'desc': 'The newly created `storm:project:sprint` object', }}},
        {'name': 'del', 'desc': 'Delete a sprint by name.',
         'type': {'type': 'function', '_funcname': '_delProjSprint',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Sprint to delete.'},
                  ),
                  'returns': {'type': 'boolean', 'desc': 'True if the ProjectSprint can be found and deleted, otherwise False', }}}
    )

    _storm_typename = 'storm:project:sprints'

    def __init__(self, proj):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self._getProjSprint,
            'add': self._addProjSprint,
            'del': self._delProjSprint,
        }

    async def _getProjSprint(self, name):
        return await self.proj._getProjSprint(name)

    async def _addProjSprint(self, name, period=None):

        self.proj.confirm(('project', 'sprint', 'add'))

        props = {
            'name': await tostr(name),
            'created': s_common.now(),
            'project': self.proj.node.ndef[1],
            'creator': self.proj.runt.snap.user.iden,
            'status': 'planned',
        }

        if period is not None:
            props['period'] = period

        node = await self.proj.runt.snap.addNode('proj:sprint', '*', props=props)
        return ProjectSprint(self.proj, node)

    async def _delProjSprint(self, name):

        self.proj.confirm(('project', 'sprint', 'del'))
        sprint = await self.proj._getProjSprint(name)
        if sprint is None:
            return False

        sprintiden = sprint.node.ndef[1]

        nodeedits = []
        async for tick in self.proj.runt.snap.nodesByPropValu('proj:ticket:sprint', '=', sprintiden):
            nodeedits.append(
                (tick.buid, 'proj:ticket', await tick._getPropDelEdits('sprint'))
            )
            await asyncio.sleep(0)

        await self.proj.runt.snap.applyNodeEdits(nodeedits)
        await sprint.node.delete()
        return True

    @s_stormtypes.stormfunc(readonly=True)
    async def iter(self):
        opts = {'vars': {'proj': self.proj.node.ndef[1]}}
        async for node, path in self.proj.runt.storm('proj:sprint:project=$proj', opts=opts):
            yield ProjectSprint(self.proj, node)

@s_stormtypes.registry.registerType
class Project(s_stormtypes.Prim):
    '''
    Implements the Storm API for Project objects, which are used for managing a scrum style project in the Cortex
    '''
    _storm_locals = (
        {'name': 'name', 'desc': 'The name of the project. This can also be used to set the name of the project.',
         'type': {'type': ['gtor', 'stor'], '_storfunc': '_setName', '_gtorfunc': '_getName',
                  'returns': {'type': ['str', 'null'], }}},
        {'name': 'epics', 'desc': 'A `storm:project:epics` object that contains the epics associated with the given project.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorProjEpics',
                 'returns': {'type': 'storm:project:epics', }}},
        {'name': 'sprints', 'desc': 'A `storm:project:sprints` object that contains the sprints associated with the given project.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorProjSprints',
                  'returns': {'type': 'storm:project:sprints', }}},
        {'name': 'tickets', 'desc': 'A `storm:project:tickets` object that contains the tickets associated with the given project.',
         'type': {'type': 'ctor', '_ctorfunc': '_ctorProjTickets',
                  'returns': {'type': 'storm:project:tickets', }}},
    )

    _storm_typename = 'storm:project'

    def __init__(self, runt, node, path=None):
        s_stormtypes.Prim.__init__(self, None)
        self.node = node
        self.runt = runt
        self.ctors.update({
            'epics': self._ctorProjEpics,
            'sprints': self._ctorProjSprints,
            'tickets': self._ctorProjTickets,
        })
        self.stors.update({
            'name': self._setName,
        })
        self.gtors.update({
            'name': self._getName,
        })

    def _ctorProjEpics(self, path=None):
        return ProjectEpics(self)

    def _ctorProjSprints(self, path=None):
        return ProjectSprints(self)

    def _ctorProjTickets(self, path=None):
        return ProjectTickets(self)

    def confirm(self, perm):
        gateiden = self.node.ndef[1]
        # bypass runt.confirm() here to avoid asroot
        return self.runt.user.confirm(perm, gateiden=gateiden)

    async def _setName(self, valu):
        self.confirm(('project', 'set', 'name'))
        await self.node.set('name', await tostr(valu))

    async def _getName(self):
        return self.node.get('name')

    @s_stormtypes.stormfunc(readonly=True)
    def value(self):
        return self.node.ndef[1]

    async def nodes(self):
        yield self.node

    async def _getProjEpic(self, name):

        async def filt(node):
            return node.get('project') == self.node.ndef[1]

        name = await tostr(name)

        node = await self.runt.getOneNode('proj:epic:name', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectEpic(self, node)

        node = await self.runt.getOneNode('proj:epic', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectEpic(self, node)

    async def _getProjSprint(self, name):

        async def filt(node):
            return node.get('project') == self.node.ndef[1]

        name = await tostr(name)

        node = await self.runt.getOneNode('proj:sprint:name', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectSprint(self, node)

        node = await self.runt.getOneNode('proj:sprint', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectSprint(self, node)

        return None

@s_stormtypes.registry.registerLib
class LibProjects(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Projects in the Cortex.
    '''
    _storm_locals = (
        {'name': 'get', 'desc': 'Retrieve a project by name',
         'type': {'type': 'function', '_funcname': '_funcProjGet',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Project to get'},
                  ),
                  'returns': {'type': 'storm:project',
                              'desc': 'The `storm:project `object, if it exists, otherwise null'}}},

        {'name': 'add', 'desc': 'Add a new project',
         'type': {'type': 'function', '_funcname': '_funcProjAdd',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Project to add'},
                      {'name': 'desc', 'type': 'str', 'desc': 'A description of the overall project', 'default': ''},
                  ),
                  'returns': {'type': 'storm:project', 'desc': 'The newly created `storm:project` object'}}},
        {'name': 'del', 'desc': 'Delete an existing project',
         'type': {'type': 'function', '_funcname': '_funcProjDel',
                  'args': (
                      {'name': 'name', 'type': 'str', 'desc': 'The name of the Project to delete'},
                  ),
                  'returns': {'type': 'boolean',
                              'desc': 'True if the project exists and gets deleted, otherwise False'}}},
    )
    _storm_lib_path = ('projects',)

    def getObjLocals(self):
        return {
            'get': self._funcProjGet,
            'add': self._funcProjAdd,
            'del': self._funcProjDel,
        }

    async def iter(self):
        async for node, path in self.runt.storm('proj:project'):
            yield Project(self.runt, node)

    async def _funcProjDel(self, name):
        gateiden = self.runt.snap.view.iden
        # do not use self.runt.confirm() to avoid asroot
        self.runt.user.confirm(('project', 'del'), gateiden=gateiden)
        proj = await self._funcProjGet(name)
        if proj is None:
            return False

        await proj.node.delete()
        return True

    async def _funcProjGet(self, name):

        name = await tostr(name)

        node = await self.runt.getOneNode('proj:project:name', name, cmpr='^=')
        if node is not None:
            return Project(self.runt, node)

        node = await self.runt.getOneNode('proj:project', name, cmpr='^=')
        if node is not None:
            return Project(self.runt, node)

    async def _funcProjAdd(self, name, desc=''):

        gateiden = self.runt.snap.view.iden
        # do not use self.runt.confirm() to avoid asroot
        self.runt.user.confirm(('project', 'add'), gateiden=gateiden)

        tick = s_common.now()
        props = {
            'name': await tostr(name),
            'desc': await tostr(desc),
            'created': tick,
            'updated': tick,
            'creator': self.runt.user.iden,
        }
        node = await self.runt.snap.addNode('proj:project', '*', props=props)
        return Project(self.runt, node)
