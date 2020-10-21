import os
import collections

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.cell as s_cell
import synapse.lib.base as s_base
import synapse.lib.nexus as s_nexus
import synapse.lib.msgpack as s_msgpack
import synapse.lib.lmdbslab as s_lmdbslab

def dictdict():
    return collections.defaultdict(dictdict)

class JsonStor(s_base.Base):
    '''
    A filesystem like storage mechanism that allows hirarchical lookup of
    reference counted "objects" that have individually editable properties.

    #TODO json validation by path glob matches? (persists?)
    #TODO GUID ACCESS with index generation by type
    #TODO registered types jsonschema with optional write-back validation
    '''
    async def __anit__(self, slab, pref, path=None):

        await s_base.Base.__anit__(self)

        self.slab = slab
        self.pref = pref
        self.path = None

        if path is not None:
            self.path = self._pathToTupl(path)

        self.pathdb = self.slab.initdb(f'{pref}:paths')
        self.itemdb = self.slab.initdb(f'{pref}:items')

        self.metadb = self.slab.initdb(f'{pref}:meta')
        self.fsinfo = self.slab.initdb(f'{pref}:fsinfo')

    def _getFlatObj(self, buid, x):

        def recurse(path, item):

            for name, valu in item.items():

                if path:
                    name = f'{path}/{name}'

                if type(valu) in (str, int, float, bool, None, list, tuple):
                    yield (buid + name.encode(), s_msgpack.en(valu))
                    continue

                if valu is None:
                    yield (buid + name.encode(), s_msgpack.en(valu))
                    continue

                yield from recurse(name, valu)

        return recurse('', x)

    def _incRefObj(self, buid, valu=1):

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

        # remove the item data
        for lkey, byts in self.slab.scanByPref(buid, db=self.itemdb):
            self.slab.pop(lkey, db=self.metadb)

    async def getPathMeta(self, path, name):
        '''
        Get metadata about the path.
        '''
        byts = self.slab.get(f'{path}|{name}'.encode(), db=self.fsinfo)
        if byts is not None:
            return s_msgpack.un(byts)

    async def setPathMeta(self, path, name, valu):
        '''
        Set metadata about the path.
        '''
        # TODO path validation
        byts = s_msgpack.en(valu)
        self.slab.put(f'{path}|{name}'.encode(), byts, db=self.fsinfo)

    async def setPathObj(self, path, item):
        '''
        Set (and/or reinitialize) the object at the given path.
        '''
        buid = os.urandom(16)

        pkey = self._pathToPkey(path)

        oldb = self.slab.replace(pkey, buid, db=self.pathdb)
        if oldb is not None:
            self._incRefObj(oldb, -1)

        self.slab.put(buid + b'refs', s_msgpack.en(1), db=self.metadb)

        tups = list(self._getFlatObj(buid, item))
        self.slab.putmulti(tups, db=self.itemdb)

    async def getPathObj(self, path, prop=None):

        pkey = self._pathToPkey(path)

        buid = self.slab.get(pkey, db=self.pathdb)
        if buid is None:
            # dostuff()
            return None

        item = dictdict()

        offs = 16
        scankey = buid

        if prop is not None:
            penc = prop.encode()
            offs += len(penc) + 1
            scankey += penc + b'/'

        for lkey, byts in self.slab.scanByPref(scankey, db=self.itemdb):

            hehe = item
            parts = lkey[offs:].decode().split('/')

            for name in parts[:-1]:
                hehe = hehe[name]

            hehe[parts[-1]] = s_msgpack.un(byts)

        return item

    def delPath(self, path):
        '''
        Remove a path and decref the object it references.
        '''
        pkey = self._pathToPkey(path)

        buid = self.slab.pop(pkey, db=self.pathdb)
        if buid is not None:
            self._incRefObj(buid, -1)

        for lkey, lval in self.slab.scanByPref(f'{path}|'.encode(), db=self.fsinfo):
            self.slab.pop(lkey, db=self.fsinfo)

    async def setPathLink(self, srcpath, dstpath):
        '''
        Add a link from the given srcpath to the dstpath.
        NOTE: This causes the item at dstpath to be incref'd
        '''
        srcpkey = self._pathToPkey(srcpath)
        dstpkey = self._pathToPkey(dstpath)

        if self.slab.get(srcpkey, db=self.pathdb):
            raise s_exc.PathExists(path=srcpath)

        buid = self.slab.get(dstpkey, db=self.pathdb)
        if buid is None:
            raise s_exc.NoSuchPath(path=dstpath)

        self._incRefObj(buid, 1)
        self.slab.put(srcpkey, buid, db=self.pathdb)

    async def getPathObjProp(self, path, prop):

        pkey = self._pathToPkey(path)
        buid = self.slab.get(pkey, db=self.pathdb)
        if buid is None:
            # dostuff()
            return None

        byts = self.slab.get(buid + prop.encode(), db=self.itemdb)
        if byts is not None:
            return s_msgpack.un(byts)

    def _pathToPkey(self, path):
        path = self._pathToTupl(path)
        return ('\x00'.join(path)).encode()

    def _pathToTupl(self, path):

        if isinstance(path, str):
            path = path.split('/')

        if self.path is not None:
            path = self.path + path

        return path

    def _pkeyToPath(self, pkey):
        return pkey.decode().split('\x00')

    def listPaths(self, path):
        path = self._pathToTupl(path)

        plen = len(path)
        pkey = self._pathToPkey(path)

        for lkey, buid in self.slab.scanByPref(pkey, db=self.pathdb):
            yield tuple(self._pkeyToPath(lkey)[plen:]), buid

    async def setPathObjProp(self, path, prop, valu):

        penc = prop.encode()
        pkey = self._pathToPkey(path)
        buid = self.slab.get(pkey, db=self.pathdb)
        if buid is None:
            # dostuff()
            return None

        # when we set a path prop we must delete all keys "under" it
        pkey = buid + penc
        prefkey = pkey + b'/'

        self.slab.pop(pkey, db=self.itemdb)
        for lkey, lval in self.slab.scanByPref(prefkey, db=self.itemdb):
            self.slab.pop(lkey, db=self.itemdb)

        if type(valu) in (str, int, bool, None, list, tuple):
            self.slab.put(pkey, s_msgpack.en(valu), db=self.itemdb)
            return

        tups = list(self._getFlatObj(prefkey, valu))
        self.slab.putmulti(tups, db=self.itemdb)

    async def delPathObjProp(self, path, prop):

        pkey = self._pathToPkey(path)
        buid = self.slab.get(pkey, db=self.pathdb)
        if buid is None:
            return False

        penc = prop.encode()
        pkey = buid + penc
        prefkey = pkey + b'/'

        self.slab.pop(pkey, db=self.itemdb)
        for lkey, lval in self.slab.scanByPref(prefkey, db=self.itemdb):
            self.slab.pop(lkey, db=self.itemdb)

        return True

    #def listPathsByGlob(self, glob):
    #def listPathsByPrefix(self, pref):

class JsonStorApi(s_cell.CellApi):

    async def getPathObj(self, path, prop=None):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('get', *path))
        return await self.cell.getPathObj(path, prop=prop)

    async def setPathObj(self, path, item):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('set', *path))
        return await self.cell.setPathObj(path, item)

    async def getPathObjProp(self, path, prop):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('get', *path))
        return await self.cell.getPathObjProp(path, prop)

    async def setPathObjProp(self, path, prop, valu):
        path = self.cell.jsonstor._pathToTupl(path)
        await self._reqUserAllowed(('set', *path))
        return await self.cell.setPathObjProp(path, prop, valu)

    async def setPathLink(self, srcpath, dstpath):
        srcpath = self.cell.jsonstor._pathToTupl(srcpath)
        dstpath = self.cell.jsonstor._pathToTupl(dstpath)
        await self._reqUserAllowed(('get', *dstpath))
        await self._reqUserAllowed(('set', *srcpath))
        return await self.cell.setPathLink(srcpath, dstpath)

    async def addQueue(self, name, info):
        await self._reqUserAllowed(('queue', 'add', name))
        info['owner'] = self.user.iden
        info['created'] = s_common.now()
        return await self.cell.addQueue(name, info)

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

class JsonStorCell(s_cell.Cell):

    cellapi = JsonStorApi

    async def initServiceStorage(self):
        self.jsonstor = await JsonStor.anit(self.slab, 'jsonstor')
        self.multique = await s_lmdbslab.MultiQueue.anit(self.slab, 'multique')

    async def getPathObj(self, path, prop=None):
        return await self.jsonstor.getPathObj(path, prop=prop)

    async def getPathObjProp(self, path, prop):
        return await self.jsonstor.getPathObjProp(path, prop)

    @s_nexus.Pusher.onPushAuto('json:set')
    async def setPathObj(self, path, item):
        return await self.jsonstor.setPathObj(path, item)

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

    @s_nexus.Pusher.onPushAuto('q:puts')
    async def putsQueue(self, name, items, reqid=None):
        return await self.multique.puts(name, items, reqid=reqid)

    @s_nexus.Pusher.onPushAuto('q:cull')
    async def cullQueue(self, name, offs):
        return await self.multique.cull(name, offs)

    async def getsQueue(self, name, offs, size=None, cull=True, wait=True):
        if cull and offs > 0:
            await self.cullQueue(name, offs - 1)
        async for item in self.multique.gets(name, offs, size=size, wait=wait):
            yield item
