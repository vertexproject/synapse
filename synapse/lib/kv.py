import os
import lmdb
import functools

import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.msgpack as s_msgpack
import synapse.lib.threads as s_threads

class KvDict:
    '''
    A KvDict uses the KvStor to implement a pythonic dict-like object.
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
        Yield (prop, valu) tuples from the KvDict.
        '''
        for item in self.vals.items():
            yield item

    def set(self, prop, valu):
        '''
        Set a property in the KvDict.

        Args:
            prop (str): The property name.
            valu (obj): A msgpack compatible value.
        '''
        if self.vals.get(prop) == valu:
            return

        self.vals[prop] = valu

        lkey = self.iden + prop.encode('utf8')
        self.stor.setKvProp(lkey, s_msgpack.en(valu))

    def get(self, prop, defval=None):
        '''
        Get a property from the KvDict.

        Args:
            prop (str): The property name.

        Returns:
            (obj): The return value, or None.
        '''
        return self.vals.get(prop, defval)

    def pop(self, prop):
        '''
        Pop a property from the KvDict.

        Args:
            prop (str): The property name.
        '''
        valu = self.vals.pop(prop, None)

        lkey = self.iden + prop.encode('utf8')
        self.stor.delKvProp(lkey)

        return valu

class KvLook:
    '''
    A KvLook uses the KvStor to implement key=valu lookup namespace.
    '''
    def __init__(self, stor, iden):
        self.stor = stor
        self.iden = iden

    def set(self, prop, valu):
        '''
        Set a property in the KvLook.

        Args:
            prop (str): The property name.
            valu (obj): A msgpack compatible value.
        '''
        lkey = self.iden + prop.encode('utf8')
        self.stor.setKvProp(lkey, s_msgpack.en(valu))
        return valu

    def get(self, prop):
        '''
        Lookup a property from the KvLook.

        Args:
            prop (str): The property name.

        Returns:
            (obj): The return value, or None.
        '''
        lkey = self.iden + prop.encode('utf8')

        lval = self.stor.getKvProp(lkey)
        if lval is None:
            return None

        return s_msgpack.un(lval)

    def getraw(self, lkey):
        return self.stor.getKvProp(self.iden + lkey)

    def setraw(self, lkey, lval):
        return self.stor.setKvProp(self.iden + lkey, lval)

class KvList:
    '''
    A KvList uses the KvStor to implement a pythonic list-like object.
    '''
    def __init__(self, stor, iden):
        self.stor = stor
        self.iden = iden

        self.vals = [s_msgpack.un(b) for b in stor.iterKvDups(iden)]

    def remove(self, valu):
        '''
        Remove a value from the KvList.

        Args:
            valu (obj): A msgpack value to remove.

        Returns:
            (bool): True if the value was found and removed.
        '''
        try:
            self.vals.remove(valu)
        except ValueError as e:
            return False

        lval = s_msgpack.en(valu)
        self.stor.delKvDup(self.iden, lval)
        return True

    def __iter__(self):
        return iter(self.vals)

    def __len__(self):
        return len(self.vals)

    def append(self, valu):
        '''
        Append a value to the KvList.

        Args:
            valu (obj): A msgpack value to add.
        '''
        lval = s_msgpack.en(valu)

        self.vals.append(valu)
        self.stor.addKvDup(self.iden, lval)

    def extend(self, vals):
        '''
        Extend the KvList by appending values from vals.

        Args:
            valu (list): A list of msgpack values to add.
        '''
        dups = [(self.iden, s_msgpack.en(v)) for v in vals]

        self.vals.extend(vals)
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
        '''
        lkey = b'alias:' + name.encode('utf8')

        with self.lenv.begin(db=self.oob, write=True) as xact:

            iden = xact.get(lkey)
            if iden is None:
                iden = os.urandom(16)
                xact.put(lkey, iden)

            return iden

    def getKvList(self, name):
        '''
        Create or retrieve a KvList by name from the KvStor.

        Args:
            name (str): The name of the KvList.

        Returns:
            (KvList): The KvList helper instance.
        '''
        iden = self.genKvAlias(name)
        return KvList(self, iden)

    def getKvDict(self, name):
        '''
        Create or retrieve a KvDict by name from the KvStor.

        Args:
            name (str): The name of the KvDict.

        Returns:
            (KvDict): The KvDict helper instance.
        '''
        iden = self.genKvAlias(name)
        return KvDict(self, iden)

    def getKvLook(self, name):
        '''
        Create or retrieve a KvLook by name from the KvStor.

        Args:
            name (str): The name of the KvDict.

        Returns:
            (KvDict): The KvDict helper instance.
        '''
        iden = self.genKvAlias(name)
        return KvLook(self, iden)

    def iterKvDups(self, lkey):
        '''
        Yield lkey, lval tuples for the given dup prefix.

        Args:
            lkey (bytes): The kv key prefix.
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
            (bool): True if the dups key exists.

        '''
        with self.lenv.begin(db=self.dups) as xact:
            with xact.cursor(db=self.dups) as curs:
                return curs.set_key(lkey)

    def iterKvProps(self, lkey):
        '''
        Yield lkey, lval tuples for the given prop prefix.

        Args:
            lkey (bytes): The kv key prefix.
        '''
        size = len(lkey)
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
        '''
        with self.lenv.begin(db=self.dups, write=True) as xact:
            xact.put(lkey, lval, dupdata=True)

    def setKvProp(self, lkey, lval):
        '''
        Set a non-duplicate key=valu to the KvStor.

        Args:
            lkey (bytes): The kv key.
            lval (bytes): The kv val.
        '''
        with self.lenv.begin(write=True) as xact:
            xact.put(lkey, lval)

    def getKvProp(self, lkey):
        '''
        Retrieve the lval bytes for a key.

        Args:
            lkey (bytes): The kv key.

        Returns:
            (bytes|None): The kv value.
        '''
        with self.lenv.begin() as xact:
            return xact.get(lkey)

    def setKvProps(self, props):
        '''
        Set a multiple non-duplicate key=valu props in the KvStor.

        Args:
            props (dict): A dict of lkey: lvalu pairs.
        '''
        with self.lenv.begin(write=True) as xact:
            for lkey, lval in props.items():
                xact.put(lkey, lval)

    def addKvDups(self, dups):
        '''
        Add a list of (lkey,lval) dups to the KvStor.

        Args:
            dups ([(lkey,lval)]): A list of (lkey,lval) tuples.
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
        '''
        with self.lenv.begin(db=self.dups, write=True) as xact:
            xact.delete(lkey, value=lval)

    def delKvProp(self, lkey):
        '''
        Delete a key=val prop from the KvStor.
        '''
        with self.lenv.begin(write=True) as xact:
            return xact.delete(lkey)
