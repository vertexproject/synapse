import asyncio

import synapse.exc as s_exc

import synapse.lib.base as s_base
import synapse.lib.config as s_config
import synapse.lib.schemas as s_schemas

nameregex = s_regex.compile(s_schema.re_drivename)
#LKEY_META = b'\x00'
#LKEY_ABRV = b'\x00'
#LKEY_VRBA = b'\x00'
#LKEY_META = b'\x00'

LKEY_TYPE = b'\x00'
LKEY_DIRN = b'\x01'
LKEY_INFO = b'\x02'
LKEY_DATA = b'\x03'
# TODO separate int var for kid count

LKEY_VERS_INFO = b'\x04'
LKEY_VERS_DATA = b'\x05'

LKEY_INFO_BYTYPE = b'\x06'
LKEY_DATA_BYVERS = b'\x07'

#LKEY_BYNAME = b'\x02'
#LKEY_BYPATH = b'\x02'

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
        self.slab = slab
        self.dbname = slab.initdb(f'drive:{name}')

    def getPathNorm(self, path):

        if isinstance(path, str):
            path = path.strip().strip('/').split('/')

        path = [p.strip().lower() for p in path]

        for part in path:
            if not isValidName(part):
                raise s_exc.TODO()

        return path

    def getItemInfo(self, iden):
        return self._getItemInfo(s_common.uhex(iden))

    def _getItemInfo(self, bidn):
        byts = self.slab.get(LKEY_INFO + bidn, db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    def _reqItemInfo(self, bidn):
        info = self._getItemInfo(bidn)
        if info is None:
            raise s_exc.TODO()

    def setItemPath(self, iden, path):
        '''
        Move an existing item to the given path.
        '''
        return self._setItemPath(s_common.uhex(iden), path)

    def _setItemPath(self, bidn, path):

        path = self.getPathNorm(path)
        pathinfo = self.getPathInfo(path[:-1])

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

    def _addStepInfo(self, bidn, info):

        # all data must be validated in advance

        newbidn = s_common.uhex(info.get('iden'))

        # name must already be normalized
        name = info.get('name').encode()
        typename = info.get('type').encode()

        lkey = LKEY_DIRN + bidn + name

        # TODO multiput
        self.slab.put(lkey, newbidn, db=self.dbname)
        self.slab.put(LKEY_INFO + newbidn, s_msgpack.en(info), db=self.dbname)
        self.slab.put(LKEY_BYTYPE + typename + b'\x00' + bidn, b'\x01', db=self.dbname)

    def setItemPerm(self, iden, perm):
        return self._setItemPerm(s_common.uhex(iden), perm)

    def _setItemPerm(self, bidn, perm):
        info = self._reqItemInfo(bidn)
        info['perm'] = perm
        sefl.slab.put(LKEY_INFO + bidn, s_msgpack.en(info), db=self.dbname)

    #async def genUserDir(self, useriden):
    #async def delUserDir(self, useriden):

    #def setItemPath(
    #def setItemName(
    #def setDirPerms(

    #def getDirItems(self, path, user=None):
    #def moveItem(self, srcpath, dstpath):

    async def getPathInfo(self, path, reldir=rootdir):

        path = self.getPathNorm(path)
        parbidn = s_common.uhex(reldir)

        pathinfo = []
        for part in path:
            await asyncio.sleep(0)

            info = self._getStepInfo(parbidn, part)
            if info is None:
                raise s_exc.TODO()

            pathinfo.append(info)
            parbidn = s_common.uhex(info.get('iden'))

        return pathinfo

    async def hasPathInfo(self, path, reldir=rootdir):

        path = self.getPathNorm(path)
        parbidn = s_common.uhex(reldir)

        for part in path:
            await asyncio.sleep(0)

            info = self._getStepInfo(parbidn, part)
            if info is None:
                return False

            parbidn = s_common.uhex(info.get('iden'))

        return True

    async def getPathData(self, path, reldir=rootdir, vers=None):

        path = self.getPathNorm(path)
        pathinfo = self.getPathInfo(path, reldir=reldir)

        iden = pathinfo[-1].get('iden')
        if vers is None:
            vers = pathinfo[-1].get('version')

        data = self.getItemData(iden, vers=vers)

        return (pathinfo, data)

    async def addItemInfo(self, info, path=None, reldir=rootdir):

        parent = reldir
        pathinfo = []

        if path is not None:
            path = sef.getNormPath(path)
            pathinfo = self.getPathInfo(path, reldir=reldir)
            if pathinfo:
                parent = pathinfo[-1].get('iden')

        info['size'] = 0
        info['parent'] = parent
        info['version'] = (0, 0, 0)

        info.setdefault('perm', {})
        info.setdefault('type', 'dir')

        s_schemas.reqValidDriveInfo(info)

        iden = info.get('iden')
        name = info.get('name')
        typename = info.get('type')

        bidn = s_common.uhex(iden)
        parbidn = s_common.uhex(parent)

        if self._getItemInfo(bidn) is not None:
            raise s_exc.TODO()

        if self._hasStepItem(parbidn, name):
            raise s_exc.TODO()

        self._addStepInfo(parbidn, info)

        pathinfo.append(info)
        return pathinfo

    async def delPathItem(self, path):
        path = self.getNormPath(path)
        async for info in self.walkPathInfo(path):
            bidn = s_common.uhex(info.get('iden'))
            await self._delItemData(bidn)
            await self._delItemInfo(bidn, info)
            await asyncio.sleep(0)

    #async def delItemInfo(self, iden):
        #bidn = s_common.uhex(iden)
        #info = self._getItemInfo(bidn)

    async def _delItemInfo(self, bidn, info):
        parent = info.get('parent')
        parbidn = s_common.uhex(parent)

        name = info.get('name').encode()

        self.slab.delete(LKEY_INFO + bidn, db=self.dbname)
        self.slab.delete(LKEY_DIRN + parbidn + name, db=self.dbname)

    async def walkPathInfo(self, path, reldir=rootdir):

        path = self.getNormPath(path)
        pathinfo = self.getPathInfo(path, reldir=reldir)

        bidn = s_common.uhex(pathinfo[-1].get('iden'))
        async for info in self._walkItemInfo(bidn):
            yield info

        yield pathinfo[-1]

    async def _walkItemInfo(self, bidn):

        for lkey, bidn in self.slab.scanByPref(LKEY_DIRN + bidn, db=self.dbname):

            info = self._getItemInfo(bidn)
            if info is None:
                continue

            nidn = s_common.uhex(info.get('iden'))
            async for item in self._walkItemInfo(nidn):
                yield item

            yield info

    #def setPathData(self, path, data, reldir=rootdir):
        #path = self.getPathNorm(path)
        #infos = self.getPathInfo(path, reldir=reldir)

        #iden = infos[-1].get('iden')
        #typename = infos[-1].get('type')

        #self.reqValidData(typename, data)
        #byts = s_msgpack.en(data)
        #self.slab.put(LKEY_DATA + s_common.uhex(iden), 

    def setItemData(self, iden, data, versinfo=None):
        return self._setItemData(s_common.uhex(iden), data, versinfo=versinfo)

    async def getItemDataVersions(self, iden):
        '''
        Yield data version info in reverse created order.
        '''
        bidn = s_common.uhex(iden)
        pref = LKEY_VERS_INFO + bidn
        for lkey, byts in self.slab.scanByPrefBack(pref, db=self.dbname):
            yield s_msgpack.un(byts)

    def _setItemData(self, bidn, data, versinfo=None):

        info = self._reqItemInfo(bidn)

        typename = info.get('type')

        self.reqValidData(typename, data)

        byts = s_msgpack.en(data)

        # if versinfo is specified this is a versioned item
        if versinfo is not None:

            versinfo['size'] = len(byts)

            s_schemas.reqValidDriveDataVers(versinfo)

            curvers = info.get('version')
            datavers = versinfo.get('version')

            # if new version is greater than the one we have stored
            # update the info with the newest version info...
            if datavers > curvers:
                info.update(versinfo)

            versindx = getVersIndx(datavers)
            versbyts = s_msgpack.en(versinfo)

            # TODO multi-rows
            self.slab.put(LKEY_VERS_INFO + bidn + versindx, versbyts, db=self.dbname)

        info['size'] = len(byts)

        lkey = LKEY_DATA + bidn + getVersIndx(info.get('version'))

        self.slab.put(lkey, byts, db=self.dbname)
        self.slab.put(LKEY_INFO + bidn, s_msgpack.en(info), db=self.dbname)

    def getItemData(self, iden, vers=None):
        return self._getItemData(common.uhex(iden), vers=vers)

    def _getItemData(self, bidn, vers=None):

        if vers is None:
            info = self._getItemInfo(bidn)
            vers = info.get('version')

        versindx = getVersIndx(vers)
        byts = self.slab.get(LKEY_DATA + bidn + versindx, db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    def delItemData(self, iden):
        return self._delItemData(s_common.uhex(iden))

    async def _delItemData(self, bidn):
        pref = LKEY_DATA + bidn
        for lkey in self.slab.scanKeysByPref(LKEY_DATA + bidn, db=self.dbname):
            self.slab.delete(lkey, db=self.dbname)
            await asyncio.sleep(0)

    def getTypeSchema(self, typename):
        byts = self.slab.get(LKEY_TYPE + typename.encode(), db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    #def addTypeSchema(self, typename, schema):

        #lkey = LKEY_TYPE + typename.encode()
        #if self.slab.get(lkey, db=self.dbname) is not None:
            #raise s_exc.TODO()

        #vtor = s_config.getJsValidator(schema)
        #self.validators[typename] = vtor

        #self.slab.put(lkey, s_msgpack.en(schema), db=self.dbname)

    async def setTypeSchema(self, typename, schema, callback):

        vtor = s_config.getJsValidator(schema)

        self.validators[typename] = vtor

        lkey = LKEY_TYPE + typename.encode()

        self.slab.put(lkey, s_msgpack.en(schema), db=self.dbname)

        for item in self.getItemsByType(typename):
            await asyncio.sleep(0)
            callback(item)

    async def getItemsByType(self, typename):

        tkey = typename.encode() + b'\x00'
        for lkey in self.slab.scanKeysByPref(LKEY_BYTYPE + tkey):

            bidn = lkey[-16:]
            info = self._getItemInfo(bidn)
            data = self._getItemData(bidn)

            yield info, data

            # TODO how to handle versions?

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

    def reqValidData(self, typename, item):
        self.getTypeValidator(typename)(item)
