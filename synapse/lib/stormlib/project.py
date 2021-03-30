import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.stormtypes as s_stormtypes

from synapse.lib.stormtypes import tostr

@s_stormtypes.registry.registerType
class ProjectEpic(s_stormtypes.Prim):

    _storm_typename = 'storm:project:epic'

    def __init__(self, proj, node):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.node = node
        self.locls.update(self.getObjLocals())
        self.stors.update({
            'name': self._setEpicName,
        })

    def getObjLocals(self):
        return {
            'name': self.node.get('name'),
        }

    async def value(self):
        return self.node.ndef[1]

    async def _setEpicName(self, valu):
        self.proj.confirm(('project', 'epic', 'set', 'name'))
        name = await tostr(valu, noneok=True)
        if name is None:
            await self.node.pop('name')
        else:
            await self.node.set('name', name)

@s_stormtypes.registry.registerType
class ProjectEpics(s_stormtypes.Prim):

    _storm_typename = 'storm:project:epics'

    def __init__(self, proj):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self.proj._getProjEpic,
            'add': self._addProjEpic,
            'del': self._delProjEpic,
        }

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
class ProjectTicket(s_stormtypes.Prim):

    _storm_typename = 'storm:project:ticket'

    def __init__(self, proj, node):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.node = node
        self.locls.update(self.getObjLocals())
        self.stors.update({
            'name': self._setName,
            'desc': self._setDesc,
            'epic': self._setEpic,
            'status': self._setStatus,
            'sprint': self._setSprint,
            'assignee': self._setAssignee,
            'priority': self._setPriority,
        })

    def getObjLocals(self):
        return {
            'name': self.node.get('name'),
            'desc': self.node.get('desc'),
            'priority': self.node.get('priority'),
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def value(self):
        return self.node.ndef[1]

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

@s_stormtypes.registry.registerType
class ProjectTickets(s_stormtypes.Prim):

    _storm_typename = 'storm:project:tickets'

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

        # TODO cacade delete comments?
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

    _storm_typename = 'storm:project:sprint'

    def __init__(self, proj, node):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.node = node
        self.locls.update(self.getObjLocals())
        self.ctors.update({
            'tickets': self._getSprintTickets,
        })
        self.stors.update({
            'name': self._setSprintName,
            'status': self._setSprintStatus,
        })

    async def _setSprintStatus(self, valu):
        self.proj.confirm(('project', 'sprint', 'set', 'status'))
        valu = await tostr(valu, noneok=True)
        if valu is None:
            await self.node.pop('status')
        else:
            await self.node.set('status', valu)

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

    def getObjLocals(self):
        return {
            'name': self.node.get('name'),
            'desc': self.node.get('desc'),
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def value(self):
        return self.node.ndef[1]

@s_stormtypes.registry.registerType
class ProjectSprints(s_stormtypes.Prim):

    _storm_typename = 'storm:project:sprints'

    def __init__(self, proj):
        s_stormtypes.Prim.__init__(self, None)
        self.proj = proj
        self.locls.update(self.getObjLocals())

    def getObjLocals(self):
        return {
            'get': self.proj._getProjSprint,
            'add': self._addProjSprint,
            'del': self._delProjSprint,
        }

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

    _storm_typename = 'storm:project'

    def __init__(self, runt, node, path=None):
        s_stormtypes.Prim.__init__(self, None)
        self.node = node
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.ctors.update({
            'epics': self._ctorProjEpics,
            'sprints': self._ctorProjSprints,
            'tickets': self._ctorProjTickets,
        })
        self.stors.update({
            'name': self._setName,
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

    def getObjLocals(self):
        return {
            'name': self.node.get('name'),
        }

    async def _setName(self, valu):
        self.confirm(('project', 'set', 'name'))
        await self.node.set('name', await tostr(valu))

    @s_stormtypes.stormfunc(readonly=True)
    def value(self):
        return self.node.ndef[1]

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
    A Storm Library for interacting with Projects.
    '''
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
