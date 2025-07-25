import os
import asyncio
import logging

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.base as s_base
import synapse.lib.nexus as s_nexus
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

logger = logging.getLogger(__name__)

class JsonStor(s_base.Base):
    '''
    A filesystem like storage mechanism that allows hirarchical lookup of
    reference counted "objects" that have individually editable properties.

    #TODO json validation by path glob matches? (persists?)
    #TODO GUID ACCESS with index generation by type
    #TODO registered types jsonschema with optional write-back validation
    '''
    async def __anit__(self, slab, pref):

        await s_base.Base.__anit__(self)

        self.slab = slab
        self.pref = pref

        self.dirty = {}

        self.pathdb = self.slab.initdb(f'{pref}:paths')
        self.itemdb = self.slab.initdb(f'{pref}:items')

        self.metadb = self.slab.initdb(f'{pref}:meta')
        self.fsinfo = self.slab.initdb(f'{pref}:fsinfo')

        self.slab.on('commit', self._syncDirtyItems)

    async def _syncDirtyItems(self, mesg):
        todo = list(self.dirty.items())
        for buid, item in todo:
            self.slab.put(buid, s_msgpack.en(item), db=self.itemdb)
            self.dirty.pop(buid, None)
            await asyncio.sleep(0)

    async def _incRefObj(self, buid, valu=1):

        refs = 0

        refsbyts = self.slab.get(buid + b'refs', db=self.metadb)
        if refsbyts:
            refs = s_msgpack.un(refsbyts)

        refs += valu
        if refs > 0:
            self.slab.put(buid + b'refs', s_msgpack.en(refs), db=self.metadb)
            return refs

        # remove the meta entries
        for lkey, byts in self.slab.scanByPref(buid, db=self.metadb):
            self.slab.pop(lkey, db=self.metadb)
            await asyncio.sleep(0)

        # remove the item data
        self.slab.pop(buid, db=self.itemdb)
        self.dirty.pop(buid, None)

    async def copyPathObj(self, oldp, newp):
        item = await self.getPathObj(oldp)
        await self.setPathObj(newp, item)

    async def copyPathObjs(self, paths):
        for oldp, newp in paths:
            await self.copyPathObj(oldp, newp)
            await asyncio.sleep(0)

    async def setPathObj(self, path, item):
        '''
        Set (and/or reinitialize) the object at the given path.

        NOTE: This will break any links by creating a new object.
        '''
        buid = os.urandom(16)

        pkey = self._pathToPkey(path)

        oldb = self.slab.replace(pkey, buid, db=self.pathdb)
        if oldb is not None:
            await self._incRefObj(oldb, -1)

        self.slab.put(buid + b'refs', s_msgpack.en(1), db=self.metadb)

        self.dirty[buid] = item

    async def getPathObj(self, path):
        buid = self._pathToBuid(path)
        if buid is None:
            return None
        return self._getBuidItem(buid)

    def _getBuidItem(self, buid):
        item = self.dirty.get(buid)
        if item is not None:
            return item

        byts = self.slab.get(buid, db=self.itemdb)
        if byts is not None:
            return s_msgpack.un(byts)

    def _pathToBuid(self, path):
        pkey = self._pathToPkey(path)
        return self.slab.get(pkey, db=self.pathdb)

    async def hasPathObj(self, path):
        pkey = self._pathToPkey(path)
        return self.slab.has(pkey, db=self.pathdb)

    async def delPathObj(self, path):
        '''
        Remove a path and decref the object it references.
        '''
        pkey = self._pathToPkey(path)
        buid = self.slab.pop(pkey, db=self.pathdb)
        if buid is not None:
            await self._incRefObj(buid, valu=-1)

    async def setPathLink(self, srcpath, dstpath):
        '''
        Add a link from the given srcpath to the dstpath.
        NOTE: This causes the item at dstpath to be incref'd
        '''
        srcpkey = self._pathToPkey(srcpath)
        dstpkey = self._pathToPkey(dstpath)

        buid = self.slab.get(dstpkey, db=self.pathdb)
        if buid is None:
            raise s_exc.NoSuchPath(path=dstpath)

        oldb = self.slab.pop(srcpkey, db=self.pathdb)
        if oldb is not None:
            await self._incRefObj(oldb, valu=-1)

        await self._incRefObj(buid, valu=1)
        self.slab.put(srcpkey, buid, db=self.pathdb)

    async def getPathObjProp(self, path, prop):

        item = await self.getPathObj(path)
        if item is None:
            return None

        for name in self._pathToTupl(prop):
            item = item.get(name, s_common.novalu)
            if item is s_common.novalu:
                return None

        return item

    def _pathToPkey(self, path):
        path = self._pathToTupl(path)
        return ('\x00'.join(path)).encode()

    def _pathToTupl(self, path):

        if isinstance(path, str):
            path = tuple(path.split('/'))

        return path

    def _tuplToPath(self, path):
        return '/'.join(path)

    def _pkeyToTupl(self, pkey):
        return tuple(pkey.decode().split('\x00'))

    async def getPathList(self, path):
        path = self._pathToTupl(path)

        plen = len(path)
        pkey = self._pathToPkey(path)

        for lkey, buid in self.slab.scanByPref(pkey, db=self.pathdb):
            yield self._tuplToPath(self._pkeyToTupl(lkey)[plen:])

    async def getPathObjs(self, path):
        path = self._pathToTupl(path)

        plen = len(path)
        pkey = self._pathToPkey(path)

        for lkey, buid in self.slab.scanByPref(pkey, db=self.pathdb):
            yield self._pkeyToTupl(lkey)[plen:], self._getBuidItem(buid)

    async def setPathObjProp(self, path, prop, valu):

        buid = self._pathToBuid(path)
        if buid is None:
            return False

        item = self._getBuidItem(buid)
        if item is None:
            return False

        step = item
        names = self._pathToTupl(prop)
        for name in names[:-1]:
            down = step.get(name)

            if down is None:
                down = step[name] = {}

            step = down

        name = names[-1]
        if step.get(name, s_common.novalu) == valu:
            return True

        step[name] = valu
        self.dirty[buid] = item
        self.slab.dirty = True
        return True

    async def delPathObjProp(self, path, prop):

        buid = self._pathToBuid(path)
        if buid is None:
            return False

        item = self._getBuidItem(buid)
        if item is None:
            return False

        step = item
        names = self._pathToTupl(prop)
        for name in names[:-1]:
            if (step := step.get(name)) is None:
                return False

        step.pop(names[-1], None)

        self.dirty[buid] = item
        self.slab.dirty = True
        return True

    async def cmpDelPathObjProp(self, path, prop, valu):

        buid = self._pathToBuid(path)
        if buid is None:
            return False

        item = self._getBuidItem(buid)
        if item is None:
            return False

        step = item
        names = self._pathToTupl(prop)
        for name in names[:-1]:
            step = step[name]

        name = names[-1]
        if step.get(name) != valu:
            return False

        step.pop(name, None)
        self.dirty[buid] = item
        self.slab.dirty = True
        return True

    async def popPathObjProp(self, path, prop, defv=None):

        buid = self._pathToBuid(path)
        if buid is None:
            return defv

        item = self._getBuidItem(buid)
        if item is None:
            return defv

        step = item
        names = self._pathToTupl(prop)
        for name in names[:-1]:
            step = step.get(name, s_common.novalu)
            if step is s_common.novalu:
                return defv

        retn = step.pop(names[-1], defv)
        self.dirty[buid] = item
        self.slab.dirty = True
        return retn

class JsonStorApi(s_cell.CellApi):

    async def popPathObjProp(self, path, prop):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'set', *path))
        return await self.cell.popPathObjProp(path, prop)

    async def hasPathObj(self, path):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'get', *path))
        return await self.cell.hasPathObj(path)

    async def copyPathObj(self, oldp, newp):
        oldp = self.cell.jsonstor._pathToTupl(oldp)
        newp = self.cell.jsonstor._pathToTupl(newp)
        await self._reqUserAllowed(('json', 'get', *oldp))
        await self._reqUserAllowed(('json', 'set', *newp))
        return await self.cell.copyPathObj(oldp, newp)

    async def copyPathObjs(self, paths):
        pathnorms = []
        for oldp, newp in paths:
            oldp = self.cell.jsonstor._pathToTupl(oldp)
            newp = self.cell.jsonstor._pathToTupl(newp)
            await self._reqUserAllowed(('json', 'get', *oldp))
            await self._reqUserAllowed(('json', 'set', *newp))
            pathnorms.append((oldp, newp))

        return await self.cell.copyPathObjs(pathnorms)

    async def getPathList(self, path):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'list', *path))
        async for item in self.cell.getPathList(path):
            yield item

    async def getPathObj(self, path):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'get', *path))
        return await self.cell.getPathObj(path)

    async def getPathObjs(self, path):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'get', *path))
        async for item in self.cell.getPathObjs(path):
            yield item

    async def setPathObj(self, path, item):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'set', *path))
        return await self.cell.setPathObj(path, item)

    async def delPathObj(self, path):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'del', *path))
        return await self.cell.delPathObj(path)

    async def delPathObjProp(self, path, name):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'set', *path))
        return await self.cell.delPathObjProp(path, name)

    async def cmpDelPathObjProp(self, path, name, valu):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'set', *path))
        return await self.cell.cmpDelPathObjProp(path, name, valu)

    async def getPathObjProp(self, path, prop):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'get', *path))
        return await self.cell.getPathObjProp(path, prop)

    async def setPathObjProp(self, path, prop, valu):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('json', 'set', *path))
        return await self.cell.setPathObjProp(path, prop, valu)

    async def setPathLink(self, srcpath, dstpath):
        srcpath = self.cell.jsonstor._pathToTupl(srcpath)
        dstpath = self.cell.jsonstor._pathToTupl(dstpath)
        await self._reqUserAllowed(('json', 'get', *dstpath))
        await self._reqUserAllowed(('json', 'set', *srcpath))
        return await self.cell.setPathLink(srcpath, dstpath)

    async def addQueue(self, name, info):
        await self._reqUserAllowed(('queue', 'add', name))
        info['owner'] = self.user.iden
        info['created'] = s_common.now()
        return await self.cell.addQueue(name, info)

    async def delQueue(self, name):
        await self._reqUserAllowed(('queue', 'del', name))
        return await self.cell.delQueue(name)

    async def cullQueue(self, name, offs):
        await self._reqUserAllowed(('queue', 'gets', name))
        return await self.cell.cullQueue(name, offs)

    async def putsQueue(self, name, items):
        await self._reqUserAllowed(('queue', 'puts', name))
        return await self.cell.putsQueue(name, items)

    async def getsQueue(self, name, offs, size=None, cull=True, wait=True):
        await self._reqUserAllowed(('queue', 'gets', name))
        async for item in self.cell.getsQueue(name, offs, size=size, cull=cull, wait=wait):
            yield item

    @s_cell.adminapi()
    async def addUserNotif(self, useriden, mesgtype, mesgdata=None):
        return await self.cell.addUserNotif(useriden, mesgtype, mesgdata=mesgdata)

    @s_cell.adminapi()
    async def getUserNotif(self, indx):
        return await self.cell.getUserNotif(indx)

    @s_cell.adminapi()
    async def delUserNotif(self, indx):
        return await self.cell.delUserNotif(indx)

    @s_cell.adminapi()
    async def iterUserNotifs(self, useriden, size=None):
        async for item in self.cell.iterUserNotifs(useriden, size=size):
            yield item

    @s_cell.adminapi()
    async def watchAllUserNotifs(self, offs=None):
        async for item in self.cell.watchAllUserNotifs(offs=offs):
            yield item

class JsonStorCell(s_cell.Cell):

    cellapi = JsonStorApi

    async def initServiceStorage(self):
        self.jsonstor = await JsonStor.anit(self.slab, 'jsonstor')
        self.multique = await s_lmdbslab.MultiQueue.anit(self.slab, 'multique')

        self.onfini(self.jsonstor.fini)
        self.onfini(self.multique.fini)

        self.notif_abrv_user = self.slab.getNameAbrv('users')
        self.notif_abrv_type = self.slab.getNameAbrv('types')

        self.notifseqn = self.slab.getSeqn('notifs')
        self.notif_indx_usertime = self.slab.initdb('indx:user:time', dupsort=True)
        self.notif_indx_usertype = self.slab.initdb('indx:user:type', dupsort=True)

    @classmethod
    def getEnvPrefix(cls):
        return (f'SYN_JSONSTOR', f'SYN_{cls.__name__.upper()}', )

    async def getPathList(self, path):
        async for item in self.jsonstor.getPathList(path):
            yield item

    @s_nexus.Pusher.onPushAuto('json:pop:prop')
    async def popPathObjProp(self, path, prop):
        return await self.jsonstor.popPathObjProp(path, prop)

    async def hasPathObj(self, path):
        return await self.jsonstor.hasPathObj(path)

    @s_nexus.Pusher.onPushAuto('json:copy')
    async def copyPathObj(self, oldp, newp):
        return await self.jsonstor.copyPathObj(oldp, newp)

    @s_nexus.Pusher.onPushAuto('json:copys')
    async def copyPathObjs(self, paths):
        return await self.jsonstor.copyPathObjs(paths)

    async def getPathObj(self, path):
        return await self.jsonstor.getPathObj(path)

    async def getPathObjs(self, path):
        async for item in self.jsonstor.getPathObjs(path):
            yield item
            await asyncio.sleep(0)

    async def getPathObjProp(self, path, prop):
        return await self.jsonstor.getPathObjProp(path, prop)

    @s_nexus.Pusher.onPushAuto('json:set')
    async def setPathObj(self, path, item):
        return await self.jsonstor.setPathObj(path, item)

    @s_nexus.Pusher.onPushAuto('json:del')
    async def delPathObj(self, path):
        return await self.jsonstor.delPathObj(path)

    @s_nexus.Pusher.onPushAuto('json:del:prop')
    async def delPathObjProp(self, path, name):
        return await self.jsonstor.delPathObjProp(path, name)

    @s_nexus.Pusher.onPushAuto('json:cmp:del:prop')
    async def cmpDelPathObjProp(self, path, name, valu):
        return await self.jsonstor.cmpDelPathObjProp(path, name, valu)

    @s_nexus.Pusher.onPushAuto('json:set:prop')
    async def setPathObjProp(self, path, prop, valu):
        return await self.jsonstor.setPathObjProp(path, prop, valu)

    @s_nexus.Pusher.onPushAuto('json:link')
    async def setPathLink(self, srcpath, dstpath):
        return await self.jsonstor.setPathLink(srcpath, dstpath)

    @s_nexus.Pusher.onPushAuto('q:add')
    async def addQueue(self, name, info):
        if not self.multique.exists(name):
            await self.multique.add(name, info)
            return True
        return False

    @s_nexus.Pusher.onPushAuto('q:del')
    async def delQueue(self, name):
        if not self.multique.exists(name):
            return False
        await self.multique.rem(name)
        return True

    async def putsQueue(self, name, items):
        return await self._push('q:puts', name, items)

    @s_nexus.Pusher.onPush('q:puts', passitem=True)
    async def _putsQueue(self, name, items, nexsitem):
        nexsoff, nexsmesg = nexsitem
        return await self.multique.puts(name, items, reqid=nexsoff)

    @s_nexus.Pusher.onPushAuto('q:cull')
    async def cullQueue(self, name, offs):
        return await self.multique.cull(name, offs)

    async def getsQueue(self, name, offs, size=None, cull=True, wait=True):
        if cull and offs > 0:
            await self.cullQueue(name, offs - 1)
        async for item in self.multique.gets(name, offs, size=size, wait=wait):
            yield item

    async def addUserNotif(self, useriden, mesgtype, mesgdata=None):
        mesg = (useriden, s_common.now(), mesgtype, mesgdata)
        return await self._push('notif:add', mesg)

    async def getUserNotif(self, indx):
        return self.notifseqn.get(indx)

    @s_nexus.Pusher.onPush('notif:add', passitem=True)
    async def _addUserNotif(self, mesg, nexsitem):

        indx = self.notifseqn.add(mesg, indx=nexsitem[0])
        indxbyts = s_common.int64en(indx)

        useriden, mesgtime, mesgtype, mesgdata = mesg

        userbyts = s_common.uhex(useriden)
        timebyts = s_common.int64en(mesgtime)
        typeabrv = self.notif_abrv_type.setBytsToAbrv(mesgtype.encode())

        self.slab.put(userbyts + timebyts, indxbyts, db=self.notif_indx_usertime, dupdata=True)
        self.slab.put(userbyts + typeabrv + timebyts, indxbyts, db=self.notif_indx_usertype, dupdata=True)

        return indx

    @s_nexus.Pusher.onPushAuto('notif:del')
    async def delUserNotif(self, indx):
        envl = self.notifseqn.pop(indx)
        if envl is None:
            return

        mesg = envl[1]
        useriden, mesgtime, mesgtype, mesgdata = mesg

        indxbyts = s_common.int64en(indx)
        userbyts = s_common.uhex(useriden)
        timebyts = s_common.int64en(mesgtime)
        typeabrv = self.notif_abrv_type.setBytsToAbrv(mesgtype.encode())

        self.slab.delete(userbyts + timebyts, indxbyts, db=self.notif_indx_usertime)
        self.slab.delete(userbyts + typeabrv + timebyts, indxbyts, db=self.notif_indx_usertype)

    async def iterUserNotifs(self, useriden, size=None):
        # iterate user notifications backward
        userbyts = s_common.uhex(useriden)
        count = 0
        for _, indxbyts in self.slab.scanByPrefBack(userbyts, db=self.notif_indx_usertype):
            indx = s_common.int64un(indxbyts)
            mesg = self.notifseqn.getraw(indxbyts)
            yield (indx, mesg)
            count += 1
            if size is not None and count >= size:
                break

    async def watchAllUserNotifs(self, offs=None):
        # yield only new notifications as they arrive
        if offs is None:
            offs = self.notifseqn.index()
        async for item in self.notifseqn.aiter(offs=offs, wait=True, timeout=120):
            yield item

    # async def iterUserNotifsByTime(self, useriden, ival):
    # async def iterUserNotifsByType(self, useriden, mesgtype, ival=None):
