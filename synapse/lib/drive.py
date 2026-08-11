import asyncio
import inspect

import regex

import synapse.exc as s_exc
import synapse.common as s_common

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.config as s_config
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.lmdbslab as s_lmdbslab

nameregex = regex.compile(s_schemas.re_drivename)
def reqValidName(name):
    if nameregex.match(name) is None:
        mesg = f'Name {name} is invalid. It must match: {s_schemas.re_drivename}.'
        raise s_exc.BadName(mesg=mesg)
    return name

LKEY_TYPE = b'\x00' # <type> = <schema>
LKEY_DIRN = b'\x01' # <bidn> <name> = <kid>
LKEY_INFO = b'\x02' # <bidn> = <info>
LKEY_DATA = b'\x03' # <bidn> <vers> = <data>
LKEY_VERS = b'\x04' # <bidn> <vers> = <versinfo>
LKEY_INFO_BYTYPE = b'\x05' # <type> 00 <bidn> = 01
LKEY_TYPE_VERS = b'\x06' # <type> = <uint64>
LKEY_INDX = b'\x07' # <abrv> <indxbyts> <bidn> = <bidn>
LKEY_IREV = b'\x08' # <bidn> <abrv> <indxbyts> = 01
LKEY_ABRV = b'\x09' # <type> = <abrv>

# the fixed width type abbreviation which prefixes every index row, so that a scan may be
# bounded by type without a separator the way LKEY_INFO_BYTYPE needs one
ABRV_LEN = 8

# LKEY + abrv + indxbyts + bidn must fit within an LMDB key, and the reverse index row is
# the same bytes in another order, so the one bound covers both
MAX_INDX_LEN = s_lmdbslab.MAX_MDB_KEYLEN - 1 - ABRV_LEN - 16

rootdir = '00000000000000000000000000000000'

def getVersIndx(vers):
    maji = vers[0].to_bytes(3, 'big')
    mini = vers[1].to_bytes(3, 'big')
    pati = vers[2].to_bytes(3, 'big')
    return maji + mini + pati

# the edit types accepted by Drive.editItemData(), which index Drive.editors
DRIVE_EDIT_SET = 0
DRIVE_EDIT_DEL = 1
DRIVE_EDIT_INS = 2
DRIVE_EDIT_MOV = 3

class Drive(s_base.Base):
    '''
    Drive is a hierarchical storage abstraction which:

    * Provides enveloping which includes meta data for each item:
      * creator iden / time
      * updated iden / time / version
      * number of children
      * data type for the item
      * easy perms (enforcement is up to the caller)

    * Enforces schemas, and optional per-type validators, for data
    * Maintains optional per-type secondary indexes for data
    * Allows storage of historical versions of data
    * Provides a "path traversal" based API
    * Provides an iden based API that does not require traversal
    '''
    async def __anit__(self, slab, name):
        await s_base.Base.__anit__(self)
        self.slab = slab
        self.dbname = slab.initdb(f'drive:{name}')
        self.validators = {}

        # the per-type callables registered by setTypeValidator(), which run after the JSON
        # schema validators in self.validators. These are not persisted -- the cell registers
        # them at startup.
        self.itemvtors = {}

        # the per-type callables registered by setTypeIndxer(), which produce the secondary
        # index values of an item. These are not persisted either.
        self.itemindxrs = {}

        # the next type abrv to hand out. There are only ever a handful of types, so it is
        # recovered by reading the ones already assigned rather than by keeping a counter.
        self.abrvoffs = 0
        for _, byts in self.slab.scanByPref(LKEY_ABRV, db=self.dbname):
            self.abrvoffs = max(self.abrvoffs, s_common.int64un(byts) + 1)

        # indexed by the DRIVE_EDIT_* constants
        self.editors = [
            self._editSet,
            self._editDel,
            self._editIns,
            self._editMov,
        ]

    def _getDataStep(self, item, path):
        '''
        Resolve the container which holds the last element of path.
        '''
        try:
            step = item
            for name in path[:-1]:
                step = step[name]
        except (KeyError, IndexError, TypeError):
            raise s_exc.BadArg(mesg=f'Invalid path {path}') from None

        return step

    def _getDataIndx(self, step, path):
        '''
        Resolve the last element of path as an index into the list step.
        '''
        indx = path[-1]

        # bool is an int subclass, so it must be rejected explicitly
        if not isinstance(indx, int) or isinstance(indx, bool):
            mesg = f'Invalid path {path}. The last element must be a list index.'
            raise s_exc.BadArg(mesg=mesg)

        if not isinstance(step, list):
            mesg = f'Invalid path {path}. The path must resolve to a list.'
            raise s_exc.BadArg(mesg=mesg)

        # -1 appends. no other negative index is allowed, so that inserting relative to
        # the end of the list is never ambiguous.
        if indx == -1:
            return len(step)

        if indx < 0 or indx > len(step):
            mesg = f'Invalid list index {indx} in path {path}. Use -1 to append.'
            raise s_exc.BadArg(mesg=mesg)

        return indx

    def _editSet(self, item, path, info):
        step = self._getDataStep(item, path)
        try:
            step[path[-1]] = info.get('valu')
        except (KeyError, IndexError, TypeError):
            raise s_exc.BadArg(mesg=f'Invalid path {path}') from None

    def _editDel(self, item, path, info):
        step = self._getDataStep(item, path)
        try:
            del step[path[-1]]
        except (KeyError, IndexError, TypeError):
            pass

    def _editIns(self, item, path, info):
        step = self._getDataStep(item, path)
        indx = self._getDataIndx(step, path)
        step.insert(indx, info.get('valu'))

    def _editMov(self, item, path, info):

        newpath = info.get('path')
        if isinstance(newpath, str):
            newpath = (newpath,)

        if not newpath:
            raise s_exc.BadArg(mesg='A mov item edit requires a path in its info.')

        newpath = tuple(newpath)

        step = self._getDataStep(item, path)

        try:
            valu = step[path[-1]]
            del step[path[-1]]
        except (KeyError, IndexError, TypeError):
            raise s_exc.BadArg(mesg=f'Invalid path {path}') from None

        # newpath is resolved after the removal, so moving a value within one list
        # reorders it the way remove-then-insert does
        newstep = self._getDataStep(item, newpath)

        if isinstance(newpath[-1], int) and not isinstance(newpath[-1], bool):
            indx = self._getDataIndx(newstep, newpath)
            newstep.insert(indx, valu)
            return

        try:
            newstep[newpath[-1]] = valu
        except (KeyError, IndexError, TypeError):
            raise s_exc.BadArg(mesg=f'Invalid path {newpath}') from None

    def _editData(self, item, edits):
        '''
        Apply edits to an item's data in order, in place.

        Args:
            item (dict): The item data, which must have lists rather than the tuples
                msgpack decodes an array as, since a list edit mutates it in place.
            edits (list): A list of (type, path, info) tuples.

        Returns:
            dict: The item data.
        '''
        for edit in edits:

            try:
                (etyp, path, info) = edit
            except (TypeError, ValueError):
                raise s_exc.BadArg(mesg=f'Invalid item edit: {edit!r}') from None

            try:
                etor = self.editors[etyp]
            except (IndexError, TypeError):
                raise s_exc.BadArg(mesg=f'Invalid item edit type: {etyp}', type=etyp) from None

            if isinstance(path, str):
                path = (path,)

            path = tuple(path)
            if not path:
                raise s_exc.BadArg(mesg='An item edit requires a path.')

            etor(item, path, info)

        return item

    async def editItemData(self, iden, versinfo, edits, nexs=None):
        '''
        Apply edits to the data of an item and store the result.

        Every edit is applied before the item is stored, so the data and its version info
        are written by one putmulti and either all of the edits land or none of them do.

        Args:
            iden (str): The item iden.
            versinfo (dict): The version info to store the result under.
            edits (list): A list of (type, path, info) tuples.
            nexs: The nexs the edits were computed against.

        Notes:
            When nexs is given it is compared to the nexs of the stored data, so edits
            computed against a version of the item which has since been written by someone
            else are refused rather than applied over the top of theirs.

            When the versinfo carries the nexs the stored data already has, these edits
            have been applied and this call is a replay of them, which does nothing.

            The version info and the data which are returned are always the ones which are
            current, whether or not the edits were applied. A caller whose nexs did not
            match therefore has what it needs to rebase its edits and try again, without a
            second read which could race another writer. The version info carries the nexs
            to pass as the nexs of the next edit.

        Returns:
            (bool, dict, dict): Whether the edits were applied, the current version info,
            and the current data.
        '''
        data = await self.getItemData(iden)
        if data is None:
            mesg = f'No drive item with ID {iden}.'
            raise s_exc.NoSuchIden(mesg=mesg)

        curinfo, item = data

        # msgpack decodes an array as a tuple, so the item is copied with lists to make
        # every array within it mutable in place. The copy is taken before the checks below
        # so that the data is the same shape whether it is returned as the current value or
        # as the result of the edits.
        item = s_msgpack.deepcopy(item, use_list=True)

        curnexs = curinfo.get('nexs')

        if curnexs is not None and curnexs == versinfo.get('nexs'):
            return True, curinfo, item

        if nexs is not None and curnexs != nexs:
            return False, curinfo, item

        item = self._editData(item, edits)

        # the version info which is stored is the one to return, since _setItemData() sets
        # its size and normalizes its version
        _, versinfo = await self.setItemData(iden, versinfo, item)

        return True, versinfo, item

    async def sync(self):
        await self.slab.sync()

    async def getPathNorm(self, path):

        if isinstance(path, str):
            path = path.strip().strip('/').split('/')

        return [reqValidName(p.strip().lower()) for p in path]

    def _reqInfoType(self, info, typename):
        infotype = info.get('type')
        if infotype != typename:
            mesg = f'Drive item has the wrong type. Expected: {typename} got {infotype}.'
            raise s_exc.TypeMismatch(mesg=mesg, expected=typename, got=infotype)

    async def getItemInfo(self, iden, typename=None):
        info = self._getItemInfo(s_common.uhex(iden))
        if not info:
            return

        if typename is not None:
            self._reqInfoType(info, typename)
        return info

    def _getItemInfo(self, bidn):
        byts = self.slab.get(LKEY_INFO + bidn, db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    async def reqItemInfo(self, iden, typename=None):
        return self._reqItemInfo(s_common.uhex(iden), typename=typename)

    def _reqItemInfo(self, bidn, typename=None):
        info = self._getItemInfo(bidn)
        if info is None:
            mesg = f'No drive item with ID {s_common.ehex(bidn)}.'
            raise s_exc.NoSuchIden(mesg=mesg)

        if typename is not None:
            self._reqInfoType(info, typename)

        return info

    async def setItemPath(self, iden, path):
        '''
        Move an existing item to the given path.
        '''
        return await self._setItemPath(s_common.uhex(iden), path)

    async def getItemPath(self, iden):
        pathinfo = []
        while iden is not None:

            info = await self.reqItemInfo(iden)

            pathinfo.append(info)
            iden = info.get('parent')
            if iden == rootdir:
                break

        pathinfo.reverse()
        return pathinfo

    async def _setItemPath(self, bidn, path, reldir=rootdir):

        path = await self.getPathNorm(path)

        # new parent iden / bidn
        parinfo = None
        pariden = reldir

        pathinfo = await self.getPathInfo(path[:-1], reldir=reldir)
        if pathinfo:
            parinfo = pathinfo[-1]
            pariden = parinfo.get('iden')

        parbidn = s_common.uhex(pariden)

        self._reqFreeStep(parbidn, path[-1])

        info = self._reqItemInfo(bidn)

        oldp = info.get('parent')
        oldb = s_common.uhex(oldp)
        oldname = info.get('name')

        name = path[-1]

        info['name'] = name
        info['parent'] = pariden

        s_schemas.reqValidDriveInfo(info)

        rows = [
            (LKEY_INFO + bidn, s_msgpack.en(info)),
            (LKEY_DIRN + parbidn + name.encode(), bidn),
        ]

        if parinfo is not None:
            parinfo['kids'] += 1
            s_schemas.reqValidDriveInfo(parinfo)
            rows.append((LKEY_INFO + parbidn, s_msgpack.en(parinfo)))

        # if old parent is rootdir this may be None
        oldpinfo = self._getItemInfo(oldb)
        if oldpinfo is not None:
            oldpinfo['kids'] -= 1
            s_schemas.reqValidDriveInfo(oldpinfo)
            rows.append((LKEY_INFO + oldb, s_msgpack.en(oldpinfo)))

        self.slab.delete(LKEY_DIRN + oldb + oldname.encode(), db=self.dbname)
        await self.slab.putmulti(rows, db=self.dbname)

        pathinfo.append(info)
        return pathinfo

    def _hasStepItem(self, bidn, name):
        return self.slab.has(LKEY_DIRN + bidn + name.encode(), db=self.dbname)

    async def getStepInfo(self, iden, name):
        return self._getStepInfo(s_common.uhex(iden), name)

    def _getStepInfo(self, bidn, name):
        step = self.slab.get(LKEY_DIRN + bidn + name.encode(), db=self.dbname)
        if step is None:
            return None

        byts = self.slab.get(LKEY_INFO + step, db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    async def _addStepInfo(self, parbidn, parinfo, info):

        newbidn = s_common.uhex(info.get('iden'))

        # name must already be normalized
        name = info.get('name')
        typename = info.get('type')

        self._reqFreeStep(parbidn, name)

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

        await self.slab.putmulti(rows, db=self.dbname)

    async def setItemPerm(self, iden, perm):
        return self._setItemPerm(s_common.uhex(iden), perm)

    def _setItemPerm(self, bidn, perm):
        info = self._reqItemInfo(bidn)
        info['permissions'] = perm
        s_schemas.reqValidDriveInfo(info)
        self.slab._put(LKEY_INFO + bidn, s_msgpack.en(info), db=self.dbname)
        return info

    async def getPathInfo(self, path, reldir=rootdir):
        '''
        Return a list of item info for each step in the given path
        relative to rootdir.

        This API is designed to allow the caller to retrieve the path info
        and potentially check permissions on each level to control access.
        '''
        path = await self.getPathNorm(path)
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

    async def hasItemInfo(self, iden):
        return self._hasItemInfo(s_common.uhex(iden))

    def _hasItemInfo(self, bidn):
        return self.slab.has(LKEY_INFO + bidn, db=self.dbname)

    async def hasPathInfo(self, path, reldir=rootdir):
        '''
        Check for a path existing relative to reldir.
        '''
        path = await self.getPathNorm(path)
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
        pathinfo = []

        if path is not None:
            path = await self.getPathNorm(path)
            pathinfo = await self.getPathInfo(path, reldir=reldir)
            if pathinfo:
                pariden = pathinfo[-1].get('iden')

        parbidn = s_common.uhex(pariden)
        parinfo = self._getItemInfo(parbidn)

        info['size'] = 0
        info['kids'] = 0
        info['parent'] = pariden

        info.setdefault('permissions', {'users': {}, 'roles': {}})
        info.setdefault('version', (0, 0, 0))

        s_schemas.reqValidDriveInfo(info)

        iden = info.get('iden')
        typename = info.get('type')

        bidn = s_common.uhex(iden)

        if typename is not None:
            await self._reqTypeValidator(typename)

        if self._getItemInfo(bidn) is not None:
            mesg = f'A drive entry with ID {iden} already exists.'
            raise s_exc.DupIden(mesg=mesg)

        await self._addStepInfo(parbidn, parinfo, info)

        pathinfo.append(info)
        return pathinfo

    async def reqFreeStep(self, iden, name):
        return self._reqFreeStep(s_common.uhex(iden), name)

    def _reqFreeStep(self, bidn, name):
        if self._hasStepItem(bidn, name):
            mesg = f'A drive entry with name {name} already exists in parent {s_common.ehex(bidn)}.'
            raise s_exc.DupName(mesg=mesg)

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

        # the index rows are driven from the reverse index, so a teardown needs neither a
        # type nor a registered indexer to be exact
        self._setIndxRows(bidn, None, None)

        typename = info.get('type')
        if typename is not None:
            self.slab.delete(LKEY_INFO_BYTYPE + typename.encode() + b'\x00' + bidn, db=self.dbname)

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

        path = await self.getPathNorm(path)
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

    async def setItemData(self, iden, versinfo, data):
        return await self._setItemData(s_common.uhex(iden), versinfo, data)

    async def _setItemData(self, bidn, versinfo, data):

        info = self._reqItemInfo(bidn)

        typename = info.get('type')

        await self.reqValidData(typename, data)

        byts = s_msgpack.en(data)

        size = len(byts)

        versinfo['size'] = size

        s_schemas.reqValidDriveDataVers(versinfo)

        curvers = info.get('version')

        # a caller which arrived over a json transport has a list here, which will not
        # compare against the tuple msgpack decodes the stored one as
        datavers = tuple(versinfo.get('version'))
        versinfo['version'] = datavers

        versindx = getVersIndx(datavers)

        # the type validator runs here, after both schemas have passed and after the version
        # info has been normalized, so that it is handed exactly what is about to be stored:
        # an item with the schema defaults filled in, and a versinfo with its size set and
        # its version as a tuple. By contract it must not modify either.
        itemvtor = self.itemvtors.get(typename)
        if itemvtor is not None:
            await s_coro.ornot(itemvtor, versinfo, data)

        rows = [
            (LKEY_DATA + bidn + versindx, s_msgpack.en(data)),
            (LKEY_VERS + bidn + versindx, s_msgpack.en(versinfo)),
        ]

        # if new version is greater than the one we have stored
        # update the info with the newest version info...
        if datavers >= curvers:

            # the index tracks only the version which is current, so a write which lands
            # below it stores its data and changes no index rows. The rows are written before
            # the data so that the two land together: nothing between here and the put
            # awaits, and a commit can only happen at an await. An indexer which raises does
            # so before a row is touched, which refuses the whole write.
            self._setIndxRows(bidn, typename, data)

            info.update(versinfo)
            rows.append((LKEY_INFO + bidn, s_msgpack.en(info)))

        # the sync _putmulti() is deliberate. putmulti() only writes without awaiting when
        # the rows fit its fast path, and that guarantee is what keeps the index rows above
        # in the same commit as the data rather than a property of how many rows there are.
        self.slab._putmulti(rows, db=self.dbname)

        return info, versinfo

    async def getItemData(self, iden, vers=None):
        '''
        Return a (versinfo, data) tuple for the given iden. If
        version is not specified, the current version is returned.
        '''
        return self._getItemData(s_common.uhex(iden), vers=vers)

    def _getItemData(self, bidn, vers=None):

        if vers is None:
            info = self._getItemInfo(bidn)
            if info is None:
                return None
            vers = info.get('version')

        versindx = getVersIndx(vers)
        versbyts = self.slab.get(LKEY_VERS + bidn + versindx, db=self.dbname)
        if versbyts is None:
            return None

        databyts = self.slab.get(LKEY_DATA + bidn + versindx, db=self.dbname)
        if databyts is None: # pragma: no cover
            return None

        return s_msgpack.un(versbyts), s_msgpack.un(databyts)

    async def delItemData(self, iden, vers=None):
        return self._delItemData(s_common.uhex(iden), vers=vers)

    def _delItemData(self, bidn, vers=None):

        info = self._reqItemInfo(bidn)
        if vers is None:
            vers = info.get('version')

        # a caller which arrived over a json transport has a list here, which will not
        # compare against the tuple msgpack decodes the stored one as
        vers = tuple(vers)

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
                info.pop('updater', None)
            else:
                info.update(versinfo)

            # the index follows whatever is current now, which is nothing at all once the
            # last version of the data is gone
            item = None
            if versinfo is not None:
                lkey = LKEY_DATA + bidn + getVersIndx(info.get('version'))
                item = s_msgpack.un(self.slab.get(lkey, db=self.dbname))

            self._setIndxRows(bidn, info.get('type'), item)

        self.slab._put(LKEY_INFO + bidn, s_msgpack.en(info), db=self.dbname)
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

    async def getTypeSchema(self, typename):
        byts = self.slab.get(LKEY_TYPE + typename.encode(), db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts, use_list=True)

    async def getTypeSchemaVersion(self, typename):
        verskey = LKEY_TYPE_VERS + typename.encode()
        byts = self.slab.get(verskey, db=self.dbname)
        if byts is not None:
            return s_msgpack.un(byts)

    async def setTypeSchema(self, typename, schema, callback=None, vers=None):
        '''
        Register the schema which the data of items with the given type is validated against.

        Args:
            typename (str): The drive type name.
            schema (dict): A JSON schema.
            callback (str): The dotted path of a coroutine function which migrates the data
                of the items which are already stored, called as
                callback(info, versinfo, data, curv) and returning the migrated data.
            vers (int): The schema version, which must not go backwards.

        Returns:
            bool: False when the version is unchanged and nothing was done.

        Notes:
            The migration callback also refreshes the secondary index rows of each item, and
            it is the only thing which does so for items which are already stored. It can
            only do that for a type whose indexer is registered by the time it runs, so call
            setTypeIndxer() before this.
        '''
        reqValidName(typename)

        cbfunc = None
        if callback is not None:
            cbfunc = s_dyndeps.reqDynCoro(callback)

        # if we were invoked via telepath, the schema needs to be mutable...
        schema = s_msgpack.deepcopy(schema, use_list=True)

        curv = await self.getTypeSchemaVersion(typename)

        if vers is not None:
            vers = int(vers)
            if curv is not None:
                if vers == curv:
                    return False

                if vers < curv:
                    mesg = f'Cannot downgrade drive schema version for type {typename}.'
                    raise s_exc.BadVersion(mesg=mesg)

        vtor = s_config.getJsValidator(schema)

        self.validators[typename] = vtor

        lkey = LKEY_TYPE + typename.encode()

        await self.slab.put(lkey, s_msgpack.en(schema), db=self.dbname)

        if vers is not None:
            verskey = LKEY_TYPE_VERS + typename.encode()
            await self.slab.put(verskey, s_msgpack.en(vers), db=self.dbname)

        # a migration is a repair path, so it re-validates only against the schema. A type
        # validator may depend on state which does not exist yet when a schema is registered.
        if cbfunc is not None:
            async for info in self.getItemsByType(typename):
                bidn = s_common.uhex(info.get('iden'))
                for lkey, byts in self.slab.scanByPref(LKEY_VERS + bidn, db=self.dbname):
                    versindx = lkey[-9:]
                    databyts = self.slab.get(LKEY_DATA + bidn + versindx, db=self.dbname)
                    data = await cbfunc(info, s_msgpack.un(byts), s_msgpack.un(databyts), curv)
                    vtor(data)
                    await self.slab.put(LKEY_DATA + bidn + versindx, s_msgpack.en(data), db=self.dbname)
                    await asyncio.sleep(0)

                # the walk rewrites every stored version but the index tracks only the one
                # which is current, so it is refreshed once, after they have all been written
                item = self._getItemData(bidn)
                if item is not None:
                    self._setIndxRows(bidn, typename, item[1])

                await asyncio.sleep(0)

        return True

    def setTypeValidator(self, typename, validator):
        '''
        Register a callback which validates the data of items with the given type.

        The validator is called as validator(versinfo, item) each time item data is set,
        after the item has been validated against the type schema and the version info has
        been normalized. It may be a coroutine function or a plain function. Raising from it
        refuses the write.

        Args:
            typename (str): The drive type name.
            validator: A callable which takes (versinfo, item).

        Notes:
            The validator MUST NOT modify versinfo or item. It is handed the objects which
            are about to be stored and no copy is made of either.

            Unlike setTypeSchema(), this registers only. It is not persisted, it has no
            version semantics, and it does not run over the items which are already stored.
            Register it at startup, before the cell serves requests.

            Item data writes are replicated through the nexus handlers in the Cell, so a
            leader and its mirrors must register the same validators, or a write which the
            leader accepted will be refused when a mirror replays it.
        '''
        reqValidName(typename)

        if not callable(validator):
            mesg = f'Drive type validator for {typename} must be a callable.'
            raise s_exc.BadArg(mesg=mesg, type=typename)

        self.itemvtors[typename] = validator

    def setTypeIndxer(self, typename, indexer):
        '''
        Register a callback which produces the secondary index values of items with the
        given type.

        The indexer is called as indexer(item) each time the data of an item of the type
        becomes the current version, and must return a list of bytes. Each entry becomes an
        index row which iterItemsByPrefix() and iterItemsByRange() may look the item up by.

        Args:
            typename (str): The drive type name.
            indexer: A callable which takes (item) and returns a list of bytes.

        Notes:
            The indexer MUST NOT be a coroutine function and MUST NOT modify item. The index
            rows are maintained within the transaction which stores the data, and everything
            in that sequence is synchronous, which leaves nowhere to await.

            Each index value must be MAX_INDX_LEN bytes or less. A value which the indexer
            returns more than once is stored once.

            The indexer is handed the item as it is stored, so an array within it is a list
            on the write path and the tuple which msgpack decodes it as when it is read back
            by delItemData() or by a setTypeSchema() migration. An indexer which walks an
            array must tolerate both.

            Unlike setTypeSchema(), this registers only. It is not persisted, it has no
            version semantics, and it does NOT index the items which are already stored.
            Register it at startup, before the cell serves requests, and BEFORE the
            setTypeSchema() call whose migration callback rewrites them -- that walk is what
            refreshes the index rows of the items which are already there, and it only does
            so for a type whose indexer is registered by the time it runs.

            Item data writes are replicated through the nexus handlers in the Cell, so a
            leader and its mirrors must register the same indexers, or their indexes will
            diverge.
        '''
        reqValidName(typename)

        if not callable(indexer):
            mesg = f'Drive type indexer for {typename} must be a callable.'
            raise s_exc.BadArg(mesg=mesg, type=typename)

        if inspect.iscoroutinefunction(indexer):
            mesg = f'Drive type indexer for {typename} must not be a coroutine function.'
            raise s_exc.BadArg(mesg=mesg, type=typename)

        self.itemindxrs[typename] = indexer

    def _getTypeAbrv(self, typename, init=False):
        '''
        Return the fixed width abbreviation of a type name, or None.

        The abrv is local to one drive. Index rows are derived from data writes rather than
        replicated, so a leader and a mirror may hand out different abrvs for one type
        without diverging.
        '''
        lkey = LKEY_ABRV + typename.encode()

        abrv = self.slab.get(lkey, db=self.dbname)
        if abrv is not None:
            return abrv

        if not init:
            return None

        abrv = s_common.int64en(self.abrvoffs)

        self.abrvoffs += 1

        self.slab._put(lkey, abrv, db=self.dbname)

        return abrv

    def _reqIndxByts(self, typename, byts):

        if not isinstance(byts, bytes):
            mesg = f'Drive index values for type {typename} must be bytes, got {byts.__class__.__name__}.'
            raise s_exc.BadArg(mesg=mesg, type=typename)

        if len(byts) > MAX_INDX_LEN:
            mesg = f'Drive index values for type {typename} must be {MAX_INDX_LEN} bytes or less, got {len(byts)}.'
            raise s_exc.BadArg(mesg=mesg, type=typename, size=len(byts))

        return byts

    def _getIndxByts(self, typename, indexer, item):
        '''
        Return the set of index row suffixes which the indexer produces for an item.

        Every value is checked before the caller touches a row, so an indexer which returns
        something invalid refuses the write rather than half applying it.
        '''
        abrv = self._getTypeAbrv(typename, init=True)

        return {abrv + self._reqIndxByts(typename, byts) for byts in indexer(item)}

    def _setIndxRows(self, bidn, typename, item):
        '''
        Bring the index rows of an item into line with the data which is now current.

        An item of None removes every index row, whether or not the type has an indexer
        registered, so that a teardown never leaves one behind.
        '''
        newkeys = set()

        if item is not None:

            # a type with no indexer is the common case, and it has no rows to reconcile, so
            # it returns before the scan below rather than paying it on every data write
            indexer = self.itemindxrs.get(typename)
            if indexer is None:
                return

            newkeys = self._getIndxByts(typename, indexer, item)

        # the rows in place are read back rather than re-derived, so an indexer whose output
        # has changed since they were written still tears them down exactly
        pref = LKEY_IREV + bidn
        oldkeys = {lkey[len(pref):] for lkey in self.slab.scanKeysByPref(pref, db=self.dbname)}

        for suff in oldkeys - newkeys:
            self.slab.delete(LKEY_INDX + suff + bidn, db=self.dbname)
            self.slab.delete(LKEY_IREV + bidn + suff, db=self.dbname)

        for suff in newkeys - oldkeys:
            self.slab._put(LKEY_INDX + suff + bidn, bidn, db=self.dbname)
            self.slab._put(LKEY_IREV + bidn + suff, b'\x01', db=self.dbname)

    async def iterItemsByPrefix(self, typename, byts, reverse=False):
        '''
        Yield the (versinfo, item) tuple of each item with an index value beneath a prefix.

        Args:
            typename (str): The drive type name.
            byts (bytes): The index value prefix. An empty prefix is every index value of
                the type.
            reverse (bool): Yield in descending rather than ascending index value order.

        Notes:
            The index tracks only the current version of an item, so the version info which
            is yielded is always the current one.

            An item is yielded once for each of its index values which matches, so an item
            with two matching values is yielded twice.
        '''
        async for item in self._iterItemsByIndex(typename, byts, byts, reverse):
            yield item

    async def iterItemsByRange(self, typename, minv, maxv=None, reverse=False):
        '''
        Yield the (versinfo, item) tuple of each item within a range of index values.

        Args:
            typename (str): The drive type name.
            minv (bytes): The inclusive lower bound index value, which is used as a prefix.
            maxv (bytes): The inclusive upper bound index value, which is used as a prefix.
                It defaults to None, which scans to the end of the type's index.
            reverse (bool): Yield in descending rather than ascending index value order.

        Notes:
            Both bounds are prefixes, so a bound shorter than the values which the indexer
            produces includes every index value beneath it at either end of the range.

            The index tracks only the current version of an item, so the version info which
            is yielded is always the current one.

            An item is yielded once for each of its index values which falls within the
            range, so an item with two matching values is yielded twice.
        '''
        async for item in self._iterItemsByIndex(typename, minv, maxv, reverse):
            yield item

    async def _iterItemsByIndex(self, typename, byts, maxv, reverse):

        self._reqIndxByts(typename, byts)

        if maxv is not None:
            self._reqIndxByts(typename, maxv)

        abrv = self._getTypeAbrv(typename)
        if abrv is None:
            return

        pref = LKEY_INDX + abrv

        if reverse:
            # scanByRangeBack() compares its lower bound against the whole key, which is what
            # the prefix semantics want, but it seeks by stepping back off any key longer
            # than its upper bound, which would start it below every value beneath a prefix.
            # Padding builds the greatest key the prefix can hold, which is only sound
            # because MAX_INDX_LEN is enforced when a row is written.
            lmax = pref if maxv is None else pref + maxv
            lmax += b'\xff' * (s_lmdbslab.MAX_MDB_KEYLEN - len(lmax))
            genr = self.slab.scanByRangeBack(lmax, lmin=pref + byts, db=self.dbname)

        elif maxv is None:
            # the abrv prefix is what confines an unbounded scan to this type, and the start
            # key is what begins it at byts
            genr = self.slab.scanByPref(pref, startkey=byts, db=self.dbname)

        else:
            # scanByRange() compares its upper bound truncated to its own length, which is
            # already the prefix semantics, so the bound is passed unpadded
            genr = self.slab.scanByRange(pref + byts, lmax=pref + maxv, db=self.dbname)

        for lkey, bidn in genr:

            await asyncio.sleep(0)

            # an index row whose item is no longer fetchable is skipped rather than raising,
            # so a row orphaned by a partial teardown degrades to a missing answer
            item = self._getItemData(bidn)
            if item is None:
                continue

            yield item

    async def getItemsByType(self, typename):
        tkey = typename.encode() + b'\x00'
        for lkey in self.slab.scanKeysByPref(LKEY_INFO_BYTYPE + tkey, db=self.dbname):
            bidn = lkey[-16:]
            info = self._getItemInfo(bidn)
            if info is not None:
                yield info

    async def _getTypeValidator(self, typename):
        vtor = self.validators.get(typename)
        if vtor is not None:
            return vtor

        schema = await self.getTypeSchema(typename)
        if schema is None:
            return None

        vtor = s_config.getJsValidator(schema)
        self.validators[typename] = vtor

        return vtor

    async def _reqTypeValidator(self, typename):
        vtor = await self._getTypeValidator(typename)
        if vtor is not None:
            return vtor

        mesg = f'No schema registered with name: {typename}'
        raise s_exc.NoSuchType(mesg=mesg)

    async def reqValidData(self, typename, item):
        return (await self._reqTypeValidator(typename))(item)

CELLDRIVE = 'celldrive'
