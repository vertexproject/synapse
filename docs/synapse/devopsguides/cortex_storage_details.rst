Cortex: Storage Layer Details
=============================

The storage layer for a Cortex is a standalone object which can be instantiated on its own. This allows the creation
of empty Cortex's, raw data manipulation or reuse of the Storage object for other purposes.  In addition, the clean API
separation between the Cortex and Storage classes allows for additional storage layer backings to be implemented.

Heading
-------

Words

Heading
-------

Knights who say ni

Implementing a Storage Layer
----------------------------

When implementing a new storage layer five things must be done.

    #. The Storage class from synapse/cores/storage.py must be subclassed and multiple methods overridden.
       Some of these are private methods since they are wrapped by public APIs or called by other functions.
    #. The StoreXact class from synapse/cores/storage.py must be subclassed and multiple methods overridden.
    #. Additional Storage and StoreXact optional methods may be overridden to provided storage layer specific
       functionality for these objects which overrides default behaviors.
    #. The Storage class should implement a helper function to allow creating a Cortex with the Storage
       implementation as the backing store.
    #. The Cortex should pass the basic Cortex tests provided in the test_cortex.py test suite.

Each of these is actions is detailed below.


Overriding Required Storage APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following APIs must be implemented:

Initializtion / State APIs

  - _initCoreStor(self):
  - getStoreType(self):

Transaction APIs

These are used to provide transaction safety around a Storage object.

  - getStoreXact(self, size=None):

Blob Storage APIs

  - _getBlobValu(self, key):
  - _setBlobValu(self, key, valu):
  - _hasBlobValu(self, key):
  - _delBlobValu(self, key):
  - _getBlobKeys(self):

Adding Data to the Store

  - _addRows(self, rows):

Deleting  Data from the Store

  - _delRowsById(self, iden):
  - _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
  - _delRowsByIdProp(self, iden, prop, valu=None):

Getting Data From the Store

  - getRowsById(self, iden):
  - getRowsByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
  - getRowsByIdProp(self, iden, prop, valu=None):
  - getSizeByProp(self, prop, valu=None, mintime=None, maxtime=None):
  - rowsByRange(self, prop, valu, limit=None):
  - rowsByGe(self, prop, valu, limit=None):
  - rowsByLe(self, prop, valu, limit=None):
  - sizeByGe(self, prop, valu, limit=None):
  - sizeByLe(self, prop, valu, limit=None):
  - sizeByRange(self, prop, valu, limit=None):
  - tufosByGe(self, prop, valu, limit=None):
  - tufosByLe(self, prop, valu, limit=None):
  - _genStoreRows(self, **kwargs):

Override the StoreXact APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following APIs must be overridden:

  - _coreXactBegin(self):
  - _coreXactCommit(self):

Optional APIs to Override
~~~~~~~~~~~~~~~~~~~~~~~~~

Some of the APIs provided in the Storage and StoreXact classes provide default implementations which will generically
work but may not be the best choice for a given storage layer.


Implementing a helper function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A helper function for making a Cortex with your storage layer should be provided. It should match the following call
signature and return a Cortex class which uses your storage layer for backing.  A simple example is seen below::

    def initMyStorageCortex(link, conf=None, storconf=None):
        '''
        Initialize a MyStore based Cortex from a link tufo.

        Args:
            link ((str, dict)): Link tufo.
            conf (dict): Configable opts for the Cortex object.
            storconf (dict): Configable opts for the storage object.

        Returns:
            s_cores_common.Cortex: Cortex created from the link tufo.
        '''
        if not conf:
            conf = {}
        if not storconf:
            storconf = {}

        store = MyStorage(link, **storconf)
        return s_cores_common.Cortex(link, store, **conf)

Then, in synapse/cortex.py, a few changes need to be made.  We have to import the file containing the Storage object
implementation and the helper function, as well as updating a pair of dictionaries to register URL handlers for
making either raw Storage objects or making a Cortex backed by the new Storage implementation.  The storectors
dictionary should contain the path of your Storage class implementation, and the corctors should contain the path to
the helper function. Assuming the storage object was implemented in synaspe/cores/mystorage.py, these would look like
the following::

    import synapse.cores.ram
    import synapse.cores.lmdb
    import synapse.cores.sqlite
    import synapse.cores.postgres
    import synapse.cores.mystorage

    ...

    storectors = {
        'lmdb': synapse.cores.lmdb.LmdbStorage,
        'sqlite': synapse.cores.sqlite.SqliteStorage,
        'ram': synapse.cores.ram.RamStorage,
        'postgres': synapse.cores.postgres.PsqlStorage,
        'mystorage': synapse.cores.mystorage.MyStorage,
    }

    corctors = {
        'lmdb': synapse.cores.lmdb.initLmdbCortex,
        'sqlite': synapse.cores.sqlite.initSqliteCortex,
        'ram': synapse.cores.ram.initRamCortex,
        'postgres': synapse.cores.postgres.initPsqlCortex,
        'mystorage': synapse.cores.mystorage.initMyStorageCortex,
    }

With these registered, users can easily make raw storage objects or Cortexs using the openstorage() and openurl()
functions provided in synapse/cortex.py.  Examples of that are below::

    import synapse.cortex as s_cortex
    stor = s_cortex.openstore('mystorage:///./some/path')
    # Now you have a raw Storage object available.
    # This may be useful for various tests or direct storage layer activity.
    core = s_cortex.openurl('mystorage:///./some/other/path')
    # Now you have a Cortex available which has the Hypergraph data model loaded in it so you actually
    # store nodes using prop normalization, join a swarm instance, ask queries via storm, etc.

Basic Cortex Test Suite
~~~~~~~~~~~~~~~~~~~~~~~

Adding a new storage layer implementation to the test suite is fairly straightforward.  In the
synapse/tests/test_cortex.py file, add the following test to the CortexTest class (this assumes you registered the
handler as "mystore")::

    def test_cortex_mystore(self):
        with s_cortex.openurl('mystore:///./store/path') as core:
            self.basic_core_expectations(core, 'mystoretype')

Then you can run the Cortex tests using the following command to ensure your Cortex works properly::

    python -m unittest synapse.tests.test_cortex.CortexTest.test_cortex_mystore

