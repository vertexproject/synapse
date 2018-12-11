Cortex: Built-In Storage Layers
===============================

There are multiple different storage layers available for use with the Cortex hypgeraph.
The choice of storage layer may affect performance characteristics of Cortex.

XXX Notes about open_* handlers in cortex.py
XXX Notes about cortex ctor helper in each storage definition.

ram://
------
The ram:// storage implementation is implemented in put python data structures resulting in
a mind bending level of performance.  However, this storage backing is only appropriate for
data which does not cause the Cortex to exceed the available amount of memory on the system.

With the addition of the savefile=<path> URL parameter, a RAM cortex can persist to disk.
However, for large or frequently changed data this savefile can grow very large due to storing
all changes since the beginning and may take a long time to start up and apply all changes
before the Cortex comes online.

sqlite://
---------
The SQLite3 storage implementation uses a single SQLite3 db file to store a Cortex.  They
are reasonably fast for medium sized data sets and very simple to create and manage.

postgres://
-----------
The PostgreSQL storage backing implements storage for a Cortex as a single table within
a PostgreSQL database. While slower than a ram:// Cortex, a PostgreSQL core has the
advantage of being backed by PSQL and having associated PSQL management tools available
for administrators to use.

lmdb://
-------
A cortex backed by the Symas Lightning DB (lmdb).

Cortex Storage Compatibility Notes
----------------------------------

Due to issues with Python serialization, the data stored and accessed from a Cortex is not
guaranteed across Cortexes created in Python 2.7 and Python 3.x.  In short, if a Cortex or
savefile was created in Python 2.7; its use in a Python3 environment isn't guaranteed. The
inverse is also true; a Cortex created in 3.x may not work in Python2.7 as expected.

This is known to affect the LMDB Cortex implementation, which heavily relies on using msgpack
for doing key/value serialization, which has issues across python 2/3 with string handling.
The Blob store APIs may also be affected by this, since the stored data is stored as a
msgpack'd object.

If there is a need for doing a data migration in order to ensure that your able to access a
Cortex created on 2.7 with python 3.x, we have plans to provide a row level dump/backup tool
in the near future that can be used to migrate data.
