Cortex: Storage Layer Details
=============================

The storage layer for a Cortex is a standalone object which can be instantiated
on its own. This allows the creation of empty Cortex's, raw data manipulation
or reuse of the Storage object for other purposes.  In addition, the clean API
separation between the Cortex and Storage classes allows for additional storage
layer backings to be implemented.

What is a Storage Row
---------------------

Most fundamentally, the Storage layer implements a way to store rows of data
with simple prop/valu indexing.  A row consists of four values::

    iden | prop | valu | time

These rows values are what we call a row from an API perspective. The field
definitions are the following:

  - iden: This is a ``str`` value which acts as unique identifer for a given
    collection of related rows. A lift of all the rows with the same iden in
    a Storage layer is considered a join operation; and the resulting rows may
    be then converted into a tufo object by the Cortex or an external caller.
    By convention, the iden is typically a random, 16 byte guid value.  An
    example is the following: "e2ac3afddab9394490d55f37a21f013d" (with
    lowercase characters). While it is possible to create and add rows with
    arbitrary iden values, tools and code made by the Vertex Project may not
    support them in all use cases. Suitable iden values can be made using the
    synapse.common.guid() function.
  - prop: This is a ``str`` value which represents a property.  When rows
    are lifted together by a join operation and folder into a tufo, these
    become the keys of the tufo dictionary.
  - valu: This is either a ``str`` or ``int`` value which is associated
    with the prop. When rows are folded into a tufo, this valu becomes the
    value of the corresponding prop in the tufo dictionary. If the storage
    implementation allows for multiple values for the same prop the tufos
    may be inconsistent. The storage layer should enforce iden/prop/valu
    combination uniqueness.
  - time: This is a ``int`` containing the epoch timestamp in milliseconds.
    This should record when row was created.  Suitable time values can be made
    using the synapse.common.time() function.

Through synapse documentation, when row level API is referenced, it is
referring to either adding or retrieving rows in this (iden, prop, valu, time)
format. In many cases this is shortened to (i, p, v, t) in both documentation
and code.

It is possible for a storage implementation to store these rows across multiple
columns, DBs or indices, as long as they adhere to the (i, p, v, t) format
going in and coming out.  For example the SQL based stores stores these rows
in a five column table, with a separate columns for valus which are strings
and valus which are integers.

Storage Layer APIs
------------------

The complete list of Storage layer APIs can be found at `Cortex Storage API`_.

Implementing a Storage Layer
----------------------------

When implementing a new storage layer five things must be done.

    #. The Storage class from synapse/cores/storage.py must be subclassed and
       multiple methods overridden. Some of these are private methods since
       they are wrapped by public APIs or called by other functions.
    #. The StoreXact class from synapse/cores/xact.py must be subclassed and
       multiple methods overridden.
    #. Additional Storage and StoreXact optional methods may be overridden to
       provided storage layer specific functionality for these objects which
       overrides default behaviors.  This may be the case where a storage layer
       may have a more optimized way to do something, such as via a specific
       type of query or lift.
    #. The Storage class should implement a helper function to allow creating
       a Cortex with the Storage implementation as the backing store.
    #. The Cortex should pass the basic Cortex tests provided in the
       test_cortex.py test suite.

Each of these is actions is detailed below.


Overriding Required Storage APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following APIs must be implemented:

Initializtion Type APIs
***********************


  - _initCoreStor(self):
  - getStoreType(self):

Transaction APIs
****************

These are used to provide transaction safety around a Storage object.

  - getStoreXact(self, size=None):

Blob Storage APIs
*****************

  - _getBlobValu(self, key):
  - _setBlobValu(self, key, valu):
  - _hasBlobValu(self, key):
  - _delBlobValu(self, key):
  - _getBlobKeys(self):

Adding Data to the Store
************************

  - _addRows(self, rows):

Deleting  Data from the Store
*****************************

  - _delRowsById(self, iden):
  - _delRowsByProp(self, prop, valu=None, mintime=None, maxtime=None):
  - _delRowsByIdProp(self, iden, prop, valu=None):

Getting Data From the Store
***************************

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
  - joinsByGe(self, prop, valu, limit=None):
  - joinsByLe(self, prop, valu, limit=None):
  - _genStoreRows(self, **kwargs):

Override the StoreXact APIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following APIs must be overridden:

  - _coreXactBegin(self):
  - _coreXactCommit(self):

Optional Storage APIs to Override
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some of the APIs provided in the Storage and StoreXact classes provide default
implementations which will generically work but may not be the best choice for
a given storage layer.

Initializtion Type APIs
***********************

These allow for the the storage layer to close resources on teardown and allow
it to do custom function/helper registration when a Cortex class is registered
with a Storage object.

  - _finiCoreStore(self):
  - _setSaveFd(self, fd, load=True, fini=False):

Row Level APIs
**************

These are row level APIs which may be overridden.

  - _setRowsByIdProp(self, iden, prop, valu):
  - _delJoinByProp(self, prop, valu=None, mintime=None, maxtime=None):
  - getJoinByProp(self, prop, valu=None, mintime=None, maxtime=None, limit=None):
  - rowsByLt(self, prop, valu, limit=None):
  - rowsByGt(self, prop, valu, limit=None):

Join Level APIs
***************

These APIs return rows which can be turned into complete tufos. They are broken
out so that the Storage layer can provide optimized methods which may be
quicker than the default implementations.  These are expected to return lists
of rows which the Cortex can turn into tufos as needed.

  - getRowsById(self, iden):
  - getRowsByIdens(self, idens):

The default implementations of these functions are just wrappers for
joinsByLe / joinsByGt, respectively.

  - joinsByLt(self, prop, valu, limit=None):
  - joinsByGt(self, prop, valu, limit=None):


Optional StorXact APIs
~~~~~~~~~~~~~~~~~~~~~~

These APIs may be used to acquire/release resources needed for the transaction:

  - _coreXactAcquire(self):
  - _coreXactRelease(self):

These APIs may be used to perform work during __enter__ and __exit__ calls:

  - _coreXactInit(self):
  - _coreXactFini(self):


Implementing a helper function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A helper function for making a Cortex with your storage layer should be
provided. It should match the following call signature and return a Cortex
class which uses your storage layer for backing.  A simple example is seen
below::

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

Then, in synapse/cortex.py, a few changes need to be made.  We have to import
the file containing the Storage object implementation and the helper function,
as well as updating a pair of dictionaries to register URL handlers for
making either raw Storage objects or making a Cortex backed by the new Storage
implementation.  The storectors dictionary should contain the path of your
Storage class implementation, and the corctors should contain the path to the
helper function. Assuming the storage object was implemented in
synaspe/cores/mystorage.py, these would look like the following::

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

With these registered, users can easily make raw storage objects or Cortexs
using the openstorage() and openurl() functions provided in synapse/cortex.py.
Examples of that are below::

    import synapse.cortex as s_cortex
    stor = s_cortex.openstore('mystorage:///./some/path')
    # Now you have a raw Storage object available.
    # This may be useful for various tests or direct storage layer activity.
    core = s_cortex.openurl('mystorage:///./some/other/path')
    # Now you have a Cortex available which has the Hypergraph data model loaded in it so you actually
    # store nodes using prop normalization, join a swarm instance, ask queries via storm, etc.

Basic Cortex Test Suite
~~~~~~~~~~~~~~~~~~~~~~~

Adding a new storage layer implementation to the test suite is fairly
straightforward.  In the synapse/tests/test_cortex.py file, add the following
test to the CortexBaseTest class (this assumes you registered the handler as
"mystore")::

    def test_cortex_mystore(self):
        with s_cortex.openurl('mystore:///./store/path') as core:
            self.basic_core_expectations(core, 'mystoretype')

Then you can run the Cortex tests using the following command to ensure your
Cortex works properly::

    python -m unittest synapse.tests.test_cortex.CortexBaseTest.test_cortex_mystore



.. _`Cortex Storage API`: ../api/synapse.cores.html#synapse.cores.storage.Storage
