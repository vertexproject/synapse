import regex
import asyncio

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas

nameregex = regex.compile(s_schemas.re_drivename)

LKEY_TYPE = b'\x00' # <type> = <schema>
LKEY_DIRN = b'\x01' # <bidn> <name> = <kid>
LKEY_INFO = b'\x02' # <bidn> = <info>
LKEY_DATA = b'\x03' # <bidn> <vers> = <data>
LKEY_VERS = b'\x04' # <bidn> <vers> = <versinfo>
LKEY_INFO_BYTYPE = b'\x05' # <type> 00 <bidn> = 01

rootdir = '00000000000000000000000000000000'

def isValidName(name):
    return nameregex.match(name) is not None

def getVersIndx(vers):
    maji = vers[0].to_bytes(3, 'big')
    mini = vers[1].to_bytes(3, 'big')
    pati = vers[2].to_bytes(3, 'big')
    return maji + mini + pati

class Drive(s_base.Base):

    async def __anit__(self, slab, name):
        await s_base.Base.__anit__(self)
        self.slab = slab
        self.dbname = slab.initdb(f'drive:{name}')
        self.validators = {}

    def getPathNorm(self, path):

        if isinstance(path, str):
            path = path.strip().strip('/').split('/')

        path = [p.strip().lower() for p in path]

        for part in path:
            if not isValidName(part):
                mesg = f'Path name is invalid: {part}.'
                raise s_exc.BadName(mesg=mesg)

        return path

    def getItemInfo(self, iden):
        return self._getItemInfo(s_common.uhex(iden))

    def _getItemInfo(self, bidn):
        byts = self.slab.get(LKEY_INFO + bidn, db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    def _reqItemInfo(self, bidn):
        info = self._getItemInfo(bidn)
        if info is not None:
            return info

        mesg = 'No drive item with ID {s_common.ehex(bidn)}.'
        raise s_exc.NoSuchIden(mesg=mesg)

    async def setItemPath(self, iden, path):
        '''
        Move an existing item to the given path.
        '''
        return await self._setItemPath(s_common.uhex(iden), path)

    async def getItemPath(self, iden):
        pathinfo = []
        while iden is not None:

            info = self.getItemInfo(iden)
            if info is None:
                break

            pathinfo.append(info)
            iden = info.get('parent')

        pathinfo.reverse()
        return pathinfo

    async def _setItemPath(self, bidn, path):

        path = self.getPathNorm(path)
        pathinfo = await self.getPathInfo(path[:-1])

        # first we must remove the parent reference...
        info = self._getItemInfo(bidn)
        name = info.get('name')

        pariden = info.get('parent')
        if pariden is not None:
            parbidn = s_common.uhex(pariden)
            parinfo = self._reqItemInfo(parbidn)
            self.slab.delete(LKEY_DIRN + parbidn + name.encode(), db=self.dbname)

        name = path[-1]
        pariden = pathinfo[-1].get('iden')
        parbidn = s_common.uhex(pariden)

        info['name'] = name
        info['parent'] = pariden

        self.slab.put(LKEY_DIRN + parbidn + name.encode(), bidn, db=self.dbname)
        self.slab.put(LKEY_INFO + bidn, s_msgpack.en(info), db=self.dbname)

    def _hasStepItem(self, bidn, name):
        return self.slab.has(LKEY_DIRN + bidn + name.encode(), db=self.dbname)

    def getStepInfo(self, iden, name):
        return self._getStepInfo(s_common.uhex(iden), name)

    def _getStepInfo(self, bidn, name):
        step = self.slab.get(LKEY_DIRN + bidn + name.encode(), db=self.dbname)
        if step is None:
            return None

        byts = self.slab.get(LKEY_INFO + step, db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    def _addStepInfo(self, parbidn, parinfo, info):

        newbidn = s_common.uhex(info.get('iden'))

        # name must already be normalized
        name = info.get('name')
        typename = info.get('type')

        rows = [
            (LKEY_DIRN + parbidn + name.encode(), newbidn),
            (LKEY_INFO + newbidn, s_msgpack.en(info)),
        ]

        if parinfo is not None:
            parinfo['kids'] += 1
            rows.append((LKEY_INFO + parbidn, s_msgpack.en(parinfo)))

        if typename is not None:
            typekey = LKEY_INFO_BYTYPE + typename.encode() + b'\x00' + newbidn
            rows.append((typekey, b'\x01'))

        self.slab.putmulti(rows, db=self.dbname)

    def setItemPerm(self, iden, perm):
        return self._setItemPerm(s_common.uhex(iden), perm)

    def _setItemPerm(self, bidn, perm):
        info = self._reqItemInfo(bidn)
        info['perm'] = perm
        s_schema.reqValidDriveInfo(info)
        sefl.slab.put(LKEY_INFO + bidn, s_msgpack.en(info), db=self.dbname)

    async def getPathInfo(self, path, reldir=rootdir):
        '''
        Return a list of item info for each step in the given path
        relative to rootdir.

        This API is designed to allow the caller to retrieve the path info
        and potentially check permissions on each level to control access.
        '''

        path = self.getPathNorm(path)
        parbidn = s_common.uhex(reldir)

        pathinfo = []
        for part in path:
            await asyncio.sleep(0)

            info = self._getStepInfo(parbidn, part)
            if info is None:
                mesg = f'Path step not found: {part}'
                raise s_exc.NoSuchPath(mesg=mesg)

            pathinfo.append(info)
            parbidn = s_common.uhex(info.get('iden'))

        return pathinfo

    def hasItemInfo(self, iden):
        return self._hasItemInfo(s_common.uhex(iden))

    def _hasItemInfo(self, bidn):
        return self.slab.has(LKEY_INFO + bidn, db=self.dbname)

    async def hasPathInfo(self, path, reldir=rootdir):
        '''
        Check for a path existing relative to reldir.
        '''
        path = self.getPathNorm(path)
        parbidn = s_common.uhex(reldir)

        for part in path:

            await asyncio.sleep(0)

            info = self._getStepInfo(parbidn, part)
            if info is None:
                return False

            parbidn = s_common.uhex(info.get('iden'))

        return True

    async def addItemInfo(self, info, path=None, reldir=rootdir):
        '''
        Add a new item at the specified path relative to reldir.
        '''
        pariden = reldir
        parinfo = None
        pathinfo = []

        if path is not None:
            path = self.getPathNorm(path)
            pathinfo = await self.getPathInfo(path, reldir=reldir)
            if pathinfo:
                parinfo = pathinfo[-1]
                pariden = pathinfo[-1].get('iden')

        info['size'] = 0
        info['kids'] = 0
        info['parent'] = pariden

        info.setdefault('perm', {'users': {}, 'roles': {}})
        info.setdefault('version', (0, 0, 0))

        s_schemas.reqValidDriveInfo(info)

        iden = info.get('iden')
        name = info.get('name')
        typename = info.get('type')

        bidn = s_common.uhex(iden)
        parbidn = s_common.uhex(pariden)

        if typename is not None:
            self.reqTypeValidator(typename)

        if self._getItemInfo(bidn) is not None:
            mesg = f'A drive entry with ID {iden} already exists.'
            raise s_exc.DupIden(mesg=mesg)

        if self._hasStepItem(parbidn, name):
            mesg = f'A drive entry with name {name} already exists in parent {pariden}.'
            raise s_exc.DupName(mesg=mesg)

        self._addStepInfo(parbidn, parinfo, info)

        pathinfo.append(info)
        return pathinfo

    async def delItemInfo(self, iden):
        '''
        Recursively remove the info and all associated data versions.
        '''
        return await self._delItemInfo(s_common.uhex(iden))

    async def _delItemInfo(self, bidn):
        async for info in self._walkItemInfo(bidn):
            await self._delOneInfo(info)

    async def _delOneInfo(self, info):
        iden = info.get('iden')
        parent = info.get('parent')

        bidn = s_common.uhex(iden)
        parbidn = s_common.uhex(parent)

        name = info.get('name').encode()

        self.slab.delete(LKEY_INFO + bidn, db=self.dbname)
        self.slab.delete(LKEY_DIRN + parbidn + name, db=self.dbname)

        pref = LKEY_VERS + bidn
        for lkey in self.slab.scanKeysByPref(pref, db=self.dbname):
            self.slab.delete(lkey, db=self.dbname)
            await asyncio.sleep(0)

        pref = LKEY_DATA + bidn
        for lkey in self.slab.scanKeysByPref(pref, db=self.dbname):
            self.slab.delete(lkey, db=self.dbname)
            await asyncio.sleep(0)

    async def walkItemInfo(self, iden):
        async for item in self._walkItemInfo(s_common.uhex(iden)):
            yield item

    async def _walkItemInfo(self, bidn):
        async for knfo in self._walkItemKids(bidn):
            yield knfo
        yield self._getItemInfo(bidn)

    async def walkPathInfo(self, path, reldir=rootdir):

        path = self.getPathNorm(path)
        pathinfo = await self.getPathInfo(path, reldir=reldir)

        bidn = s_common.uhex(pathinfo[-1].get('iden'))
        async for info in self._walkItemKids(bidn):
            yield info

        yield pathinfo[-1]

    async def getItemKids(self, iden):
        '''
        Yield each of the children of the specified item.
        '''
        bidn = s_common.uhex(iden)
        for lkey, bidn in self.slab.scanByPref(LKEY_DIRN + bidn, db=self.dbname):
            await asyncio.sleep(0)

            info = self._getItemInfo(bidn)
            if info is None: # pragma no cover
                continue

            yield info

    async def _walkItemKids(self, bidn):

        for lkey, bidn in self.slab.scanByPref(LKEY_DIRN + bidn, db=self.dbname):
            await asyncio.sleep(0)

            info = self._getItemInfo(bidn)
            if info is None: # pragma: no cover
                continue

            nidn = s_common.uhex(info.get('iden'))
            async for item in self._walkItemKids(nidn):
                yield item

            yield info

    def setItemData(self, iden, versinfo, data):
        return self._setItemData(s_common.uhex(iden), versinfo, data)

    def _setItemData(self, bidn, versinfo, data):

        info = self._reqItemInfo(bidn)

        typename = info.get('type')

        self.reqValidData(typename, data)

        byts = s_msgpack.en(data)

        size = len(byts)

        versinfo['size'] = size

        s_schemas.reqValidDriveDataVers(versinfo)

        curvers = info.get('version')
        datavers = versinfo.get('version')

        versindx = getVersIndx(datavers)
        versbyts = s_msgpack.en(versinfo)

        rows = [
            (LKEY_DATA + bidn + versindx, s_msgpack.en(data)),
            (LKEY_VERS + bidn + versindx, s_msgpack.en(versinfo)),
        ]

        # if new version is greater than the one we have stored
        # update the info with the newest version info...
        if datavers >= curvers:
            info.update(versinfo)
            rows.append((LKEY_INFO + bidn, s_msgpack.en(info)))

        self.slab.putmulti(rows, db=self.dbname)

        return info, versinfo

    def getItemData(self, iden, vers=None):
        '''
        Return a (versinfo, data) tuple for the given iden. If
        version is not specified, the current version is returned.
        '''
        return self._getItemData(s_common.uhex(iden), vers=vers)

    def _getItemData(self, bidn, vers=None):

        if vers is None:
            info = self._getItemInfo(bidn)
            vers = info.get('version')

        versindx = getVersIndx(vers)
        versbyts = self.slab.get(LKEY_VERS + bidn + versindx, db=self.dbname)
        if versbyts is None:
            return None

        databyts = self.slab.get(LKEY_DATA + bidn + versindx, db=self.dbname)
        if databyts is None:
            return None

        return s_msgpack.un(versbyts), s_msgpack.un(databyts)

    def delItemData(self, iden, vers=None):
        return self._delItemData(s_common.uhex(iden), vers=vers)

    def _delItemData(self, bidn, vers=None):

        info = self._reqItemInfo(bidn)
        if vers is None:
            vers = info.get('version')

        versindx = getVersIndx(vers)

        self.slab.delete(LKEY_VERS + bidn + versindx, db=self.dbname)
        self.slab.delete(LKEY_DATA + bidn + versindx, db=self.dbname)

        # back down or revert to 0.0.0
        if vers == info.get('version'):
            versinfo = self._getLastDataVers(bidn)
            if versinfo is None:
                info['size'] = 0
                info['version'] = (0, 0, 0)
                info.pop('updated', None)
                info.pop('updator', None)
            else:
                info.update(versinfo)

        self.slab.put(LKEY_INFO + bidn, s_msgpack.en(info), db=self.dbname)
        return info

    def _getLastDataVers(self, bidn):
        for lkey, byts in self.slab.scanByPrefBack(LKEY_VERS + bidn, db=self.dbname):
            return s_msgpack.un(byts)

    async def getItemDataVersions(self, iden):
        '''
        Yield data version info in reverse created order.
        '''
        bidn = s_common.uhex(iden)
        pref = LKEY_VERS + bidn
        for lkey, byts in self.slab.scanByPrefBack(pref, db=self.dbname):
            yield s_msgpack.un(byts)
            await asyncio.sleep(0)

    def getTypeSchema(self, typename):
        byts = self.slab.get(LKEY_TYPE + typename.encode(), db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    async def setTypeSchema(self, typename, schema, callback=None):

        vtor = s_config.getJsValidator(schema)

        self.validators[typename] = vtor

        lkey = LKEY_TYPE + typename.encode()

        self.slab.put(lkey, s_msgpack.en(schema), db=self.dbname)

        if callback is not None:
            async for info in self.getItemsByType(typename):
                bidn = s_common.uhex(info.get('iden'))
                for lkey, byts in self.slab.scanByPref(LKEY_VERS + bidn, db=self.dbname):
                    versindx = lkey[-9:]
                    databyts = self.slab.get(LKEY_DATA + bidn + versindx, db=self.dbname)
                    data = await callback(info, s_msgpack.un(byts), s_msgpack.un(databyts))
                    self.reqValidData(typename, data)
                    self.slab.put(LKEY_DATA + bidn + versindx, s_msgpack.en(data), db=self.dbname)
                    await asyncio.sleep(0)

    async def getItemsByType(self, typename):
        tkey = typename.encode() + b'\x00'
        for lkey in self.slab.scanKeysByPref(LKEY_INFO_BYTYPE + tkey, db=self.dbname):
            bidn = lkey[-16:]
            info = self._getItemInfo(bidn)
            if info is not None:
                yield info

    def getTypeValidator(self, typename):
        vtor = self.validators.get(typename)
        if vtor is not None:
            return vtor

        schema = self.getTypeSchema(typename)
        if schema is None:
            return None

        vtor = s_config.getJsValidator(schema)
        self.validators[typename] = vtor

        return vtor

    def reqTypeValidator(self, typename):
        vtor = self.getTypeValidator(typename)
        if vtor is not None:
            return vtor

        mesg = f'No schema registered with name: {typename}'
        raise s_exc.NoSuchType(mesg=mesg)

    def reqValidData(self, typename, item):
        self.reqTypeValidator(typename)(item)
