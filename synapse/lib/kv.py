import os
import lmdb
import functools

import synapse.eventbus as s_eventbus

import synapse.lib.msgpack as s_msgpack


class KvDict:
    '''
    A KvDict uses the KvStor to implement a pythonic dict-like object.

    Unlike the KvLook object, the KvDict keeps all items in the dictionary
    in memory, so retrieval is fast; and only updates needs to be written
    to the the underlying KvStor object.

    Note: set() must be called to persist changes to mutable values like
    dicts or lists
    '''
    def __init__(self, stor, iden):
        self.stor = stor
        self.iden = iden
        self.vals = {}

        # load all the props
        for lkey, lval in stor.iterKvProps(iden):
            prop = lkey[16:].decode('utf8')
            self.vals[prop] = s_msgpack.un(lval)

    def items(self):
        '''
        Return a tuple of (prop, valu) tuples from the KvDict.

        Returns:
            (((str, object), ...)): Tuple of (prop, valu) tuples.
        '''
        return tuple(self.vals.items())

    def set(self, prop, valu):
        '''
        Set a property in the KvDict.

        Args:
            prop (str): The property name.
            valu (obj): A msgpack compatible value.

        Returns:
            None
        '''
        if self.vals.get(prop) == valu:
            return

        byts = s_msgpack.en(valu)
        self.vals[prop] = s_msgpack.un(byts)

        lkey = self.iden + prop.encode('utf8')
        self.stor.setKvProp(lkey, byts)

    def get(self, prop, defval=None):
        '''
        Get a property from the KvDict.

        Args:
            prop (str): The property name.
            defval (obj): The default value to return.

        Returns:
            (obj): The return value, or None.
        '''
        return self.vals.get(prop, defval)

    def pop(self, prop):
        '''
        Pop a property from the KvDict.

        Args:
            prop (str): The property name.

        Returns:
            object: The object stored in the KvDict, or None if the object was not present.
        '''
        valu = self.vals.pop(prop, None)

        lkey = self.iden + prop.encode('utf8')
        self.stor.delKvProp(lkey)

        return valu

class KvLook:
    '''
    A KvLook uses the KvStor to implement key=valu lookup namespace.

    The primary APIs, ``get()`` and ``set()``, will use msgpack to decode and
    encode objects retrieved from the store.  This allows storing complex data
    structures in the KV store.  ``getraw()`` and ``setraw()`` APIs exist for
    purely bytes in / bytes out interfaces.
    '''
    def __init__(self, stor, iden):
        self.stor = stor
        self.iden = iden

    def set(self, prop, valu):
        '''
        Set a property in the KvLook.

        Args:
            prop (str): The property name to set.
            valu (obj): A msgpack compatible value.

        Returns:
            None
        '''
        lkey = self.iden + prop.encode('utf8')
        self.stor.setKvProp(lkey, s_msgpack.en(valu))

    def get(self, prop, defval=None):
        '''
        Lookup a property from the KvLook.

        Args:
            prop (str): The property name.
            defval (obj): The default value to return.

        Returns:
            object: The valu, aftering being unpacked via msgpack, or None.
        '''
        lkey = self.iden + prop.encode('utf8')

        lval = self.stor.getKvProp(lkey)
        if lval is None:
            return defval

        return s_msgpack.un(lval)

    def items(self):
        '''
        Iterate over items stored in the KvLook namespace.

        Yields:
            ((str, object)): The name and object for items in KvLook namespace.
        '''
        size = len(self.iden)
        for lkey, lval in self.stor.iterKvProps(self.iden):
            prop = lkey[size:].decode('utf8')
            valu = s_msgpack.un(lval)
            yield prop, valu

    def getraw(self, lkey):
        '''
        Retrieve a value directly by bytes.

        Args:
            lkey (bytes): Byte value to retrieve.

        Returns:
            bytes: Bytes for a given key, or None if it does not exist.
        '''
        return self.stor.getKvProp(self.iden + lkey)

    def setraw(self, lkey, lval):
        '''
        Set the value directly by bytes.

        Args:
            lkey (bytes): Byte value to set.
            lval (bytes): Bytes to set to the value.

        Returns:
            None
        '''
        self.stor.setKvProp(self.iden + lkey, lval)

class KvSet:
    '''
    A KvSet uses the KvStor to implement a pythonic set-like object.

    Unlike the KvLook object, the KvSet keeps all items in the set in
    memory, so access is fast; and only updates needs to be written to the
    the underlying KvStor object.
    '''
    def __init__(self, stor, iden):
        self.stor = stor
        self.iden = iden

        self.vals = {s_msgpack.un(b) for b in stor.iterKvDups(iden)}

    def remove(self, valu):
        '''
        Remove a value from the KvSet.

        Args:
            valu (obj): A msgpack value to remove.

        Returns:
            (bool): True if the value was found and removed.
        '''
        try:
            self.vals.remove(valu)
        except KeyError as e:
            return False

        lval = s_msgpack.en(valu)
        return self.stor.delKvDup(self.iden, lval)

    def __iter__(self):
        '''
        Protect against RuntimeError during iteration
        '''
        for valu in tuple(self.vals):
            yield valu

    def __len__(self):
        return len(self.vals)

    def add(self, valu):
        '''
        Add a value to the KvSet.

        Args:
            valu (obj): A msgpack value to add.

        Returns:
            None
        '''
        lval = s_msgpack.en(valu)
        self.vals.add(valu)
        self.stor.addKvDup(self.iden, lval)

    def update(self, vals):
        '''
        Extend the KvSet by adding any new values from vals to the set.

        Args:
            vals (list): A list of msgpack values to add to the set.

        Returns:
            None
        '''
        dups = [(self.iden, s_msgpack.en(v)) for v in vals]

        self.vals.update(vals)
        self.stor.addKvDups(dups)

class KvStor(s_eventbus.EventBus):
    '''
    The KvStor uses an LMDB key-value database to implement
    persistence and indexing for primitive data structures.
    '''

    def __init__(self, path):
        s_eventbus.EventBus.__init__(self)
        self.lenv = lmdb.open(path, writemap=True, max_dbs=16)

        self.oob = self.lenv.open_db(b'oob')
        self.dups = self.lenv.open_db(b'dups', dupsort=True)

        self.onfini(self._onKvFini)

    def _onKvFini(self):
        self.lenv.sync()
        self.lenv.close()

    @functools.lru_cache(maxsize=1024)
    def genKvAlias(self, name):
        '''
        Resolve or create a new object alias by name.

        Args:
            name (str): String to create or resolve an alias for.

        Notes:
            The iden returned as an alias is randomly generated the first time
            that ``genKvAlias`` is called for a given name.

        Returns:
            bytes: The iden for the name
        '''
        lkey = b'alias:' + name.encode('utf8')

        with self.lenv.begin(db=self.oob, write=True) as xact:

            iden = xact.get(lkey)
            if iden is None:
                iden = os.urandom(16)
                xact.put(lkey, iden)

            return iden

    def getKvSet(self, name):
        '''
        Create or retrieve a KvSet by name from the KvStor.

        Args:
            name (str): The name of the KvSet.

        Returns:
            KvSet: The KvSet helper instance.
        '''
        iden = self.genKvAlias(name)
        return KvSet(self, iden)

    def getKvDict(self, name):
        '''
        Create or retrieve a KvDict by name from the KvStor.

        Args:
            name (str): The name of the KvDict.

        Returns:
            KvDict: The KvDict helper instance.
        '''
        iden = self.genKvAlias(name)
        return KvDict(self, iden)

    def getKvLook(self, name):
        '''
        Create or retrieve a KvLook by name from the KvStor.

        Args:
            name (str): The name of the KvLook.

        Returns:
            KvLook: The KvLook helper instance.
        '''
        iden = self.genKvAlias(name)
        return KvLook(self, iden)

    def iterKvDups(self, lkey):
        '''
        Yield lkey, lval tuples for the given dup key.

        Args:
            lkey (bytes): The kv key.

        Yields:
            bytes: The value of the dups for a given key.
        '''
        with self.lenv.begin(db=self.dups) as xact:

            with xact.cursor(db=self.dups) as curs:

                if not curs.set_key(lkey):
                    return

                for byts in curs.iternext_dup():
                    yield byts

    def hasKvDups(self, lkey):
        '''
        Returns True if the number of values for lkey is greater than 0.

        Args:
            lkey (bytes): The kv key.

        Returns:
            bool: True if the dups key exists, False otherwise.
        '''
        with self.lenv.begin(db=self.dups) as xact:
            with xact.cursor(db=self.dups) as curs:
                return curs.set_key(lkey)

    def iterKvProps(self, lkey):
        '''
        Yield lkey, lval tuples for the given prop prefix.

        Args:
            lkey (bytes): The kv key prefix.

        Yields:
            ((bytes, bytes)): A tuple of key, value pairs which start with
            the prefix.
        '''
        with self.lenv.begin() as xact:

            with xact.cursor() as curs:

                if not curs.set_range(lkey):
                    return

                for ikey, ival in curs.iternext():

                    if not ikey.startswith(lkey):
                        break

                    yield (ikey, ival)

    def addKvDup(self, lkey, lval):
        '''
        Add a (potentially duplicate) key=valu to the KvStor.

        Args:
            lkey (bytes): The kv key.
            lval (bytes): The kv val.

        Returns:
            None
        '''
        with self.lenv.begin(db=self.dups, write=True) as xact:
            xact.put(lkey, lval, dupdata=True)

    def setKvProp(self, lkey, lval):
        '''
        Set a non-duplicate key=valu to the KvStor.

        Args:
            lkey (bytes): The kv key.
            lval (bytes): The kv val.

        Returns:
            None
        '''
        with self.lenv.begin(write=True) as xact:
            xact.put(lkey, lval)

    def getKvProp(self, lkey):
        '''
        Retrieve the lval bytes for a key.

        Args:
            lkey (bytes): The kv key.

        Returns:
            bytes: The kv value, or None if it does not exist.
        '''
        with self.lenv.begin() as xact:
            return xact.get(lkey)

    def setKvProps(self, props):
        '''
        Set a multiple non-duplicate key=valu props in the KvStor.

        Args:
            props (dict): A dict of lkey: lvalu pairs.

        Returns:
            None
        '''
        with self.lenv.begin(write=True) as xact:
            for lkey, lval in props.items():
                xact.put(lkey, lval)

    def addKvDups(self, dups):
        '''
        Add a list of (lkey,lval) dups to the KvStor.

        Args:
            dups (list): A list of (lkey,lval) tuples.
        '''
        with self.lenv.begin(db=self.dups, write=True) as xact:
            with xact.cursor() as curs:
                curs.putmulti(dups, dupdata=True)

    def delKvDup(self, lkey, lval):
        '''
        Delete a single key=value pair from the KvStor.

        Args:
            lkey: (bytes): The kv key.
            lval: (bytes): The kv value.

        Returns:
            bool: True if at least one key was deleted, False otherwise
        '''
        with self.lenv.begin(db=self.dups, write=True) as xact:
            return xact.delete(lkey, value=lval)

    def delKvProp(self, lkey):
        '''
        Delete a key=val prop from the KvStor.

        Args:
            lkey (bytes): key to delete

        Returns:
            bool: True if at least one key was deleted, False otherwise
        '''
        with self.lenv.begin(write=True) as xact:
            return xact.delete(lkey)
