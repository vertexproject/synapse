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

    def getObjLocals(self):
        return {
            'name': self.node.get('name'),
        }

    async def repr(self):
        epicname = self.node.get('name')
        projname = self.proj.node.get('name')
        return f'Project Epic: {projname} - {epicname}'

    async def value(self):
        return self.node.ndef[1]

    async def setitem(self, name, valu):
        if name == 'name':
            self.proj.confirm(('project', 'admin', 'manager'))
            await self.node.set('name', await tostr(valu))
        return s_stormtypes.Prim.setitem(name, valu)

@s_stormtypes.registry.registerType
class ProjectEpics(s_stormtypes.Prim):

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

        # return ProjectEpic based on name or iden lookup
        async def filt(node):
            return node.get('project') == self.proj.node.ndef[1]

        name = await tostr(name)

        node = await self.proj.runt.getOneNode('proj:epic:name', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectEpic(self.proj, node)

        node = await self.proj.runt.getOneNode('proj:epic', name, filt=filt, cmpr='^=')
        if node is not None:
            return ProjectEpic(self.proj, node)

    async def _delProjEpic(self, name):
        self.proj.confirm(('project', 'admin', 'manager'))
        # clear :epic on any matching tickets
        # delete the proj:epic node

    async def _addProjEpic(self, name):
        self.proj.confirm(('project', 'admin', 'manager'))
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

    def getObjLocals(self):
        return {
            'name': self.node.get('name'),
            'descr': self.node.get('descr'),
            'priority': self.node.get('priority'),
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def repr(self):
        tickname = self.node.get('name')
        projname = self.proj.node.get('name')
        return f'Project Ticket: {projname} - {tickname}'

    @s_stormtypes.stormfunc(readonly=True)
    async def value(self):
        return self.node.ndef[1]

    def _reqUserPerms(self):
        if self.proj.runt.asroot:
            return
        if self.node.get('creator') == self.proj.runt.user.iden:
            return
        self.proj.confirm(('project', 'admin', 'manager'))

    def _reqSelfPerms(self, useriden):
        if self.proj.runt.asroot:
            return
        if useriden == self.proj.runt.user.iden:
            return
        self.proj.confirm(('project', 'admin', 'manager'))

    async def setitem(self, name, valu):
        creator = self.node.get('creator')

        strvalu = await tostr(valu, noneok=True)

        if name == 'name':
            self._reqUserPerms()
            await self.node.set('name', await tostr(valu))
            await self.node.set('updated', s_common.now())
            return

        if name == 'descr':
            self._reqUserPerms()
            await self.node.set('descr', await tostr(valu))
            await self.node.set('updated', s_common.now())
            return

        if name == 'priority':
            self.proj.confirm(('project', 'manager'))
            await self.node.set('priority', await tostr(valu))
            await self.node.set('updated', s_common.now())
            return

        if name == 'assignee':
            #FIXME lookup user guid from name here
            useriden = self.proj.runt.core.getUserDef(strval)
            self._reqSelfPerms(useriden)
            await self.node.set('assignee', useriden)
            await self.node.set('updated', s_common.now())
            return

        return s_stormtypes.Prim.setitem(name, valu)

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

        props = ('proj:ticket', 'proj:ticket:name')
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
        pass
        # allow delete tickets you created...
        #self.proj.confirm(('project', 'ticket', 'del'))

    async def _addProjTicket(self, name, descr=''):
        self.proj.confirm(('project', 'admin', 'manager', 'user'))
        tick = s_common.now()
        props = {
            'name': await tostr(name),
            'descr': await tostr(descr),
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
class Project(s_stormtypes.Prim):

    _storm_typename = 'storm:project'

    def __init__(self, runt, node, path=None):
        s_stormtypes.Prim.__init__(self, None)
        self.node = node
        self.runt = runt
        self.locls.update(self.getObjLocals())

    def confirm(self, perm):
        gateiden = self.node.ndef[1]
        return self.runt.confirm(perm, gateiden=gateiden)

    def getObjLocals(self):
        return {
            'name': self.node.get('name'),
            'repr': self.repr,
            'epics': ProjectEpics(self),
            'tickets': ProjectTickets(self),
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def repr(self):
        projname = self.node.get('name')
        return f'Project - {projname}'

    async def setitem(self, name, valu):
        if name == 'name':
            self.confirm(('project', 'manager'))
            await self.node.set('name', await tostr(valu))
            return

        return s_stormtypes.Prim.setitem(self, name, valu)

    @s_stormtypes.stormfunc(readonly=True)
    def value(self):
        return self.node.ndef[1]

@s_stormtypes.registry.registerLib
class LibProjects(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with the Storm Macros in the Cortex.
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
        pass

    async def _funcProjGet(self, name):

        name = await tostr(name)

        node = await self.runt.getOneNode('proj:project:name', name, cmpr='^=')
        if node is not None:
            return Project(self.runt, node)

        node = await self.runt.getOneNode('proj:project', name, cmpr='^=')
        if node is not None:
            return Project(self.runt, node)

    async def _funcProjAdd(self, name, descr=''):
        self.runt.layerConfirm(('project', 'admin'))
        tick = s_common.now()
        props = {
            'name': await tostr(name),
            'descr': await tostr(descr),
            'created': tick,
            'updated': tick,
            'creator': self.runt.user.iden,
        }
        node = await self.runt.snap.addNode('proj:project', '*', props=props)
        return Project(self.runt, node)
