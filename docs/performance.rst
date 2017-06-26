Synapse Performance
===================

Measuring the performance of a synapse cortex is a complex undertaking which depends
not only on the test configurations, but the "shape" of the data being ingested and
queried.  These tests attempt to take an acurate measure of a set of "book end" data sets
selected specifically to demonstrate best case and worst case ingest performance.

A Note on Comparisons
---------------------
When comparing these numbers to benchmarks published by various big data systems such
as Hadoop and Elastic Search, it is very important to keep in mind the fundamental difference
between a knowledge system like a synapse cortex versus a simple indexer such as Elastic Search.
A knowledge system is required to deconflict all new data against what is already known.  This
means for each new node added to the hypergraph, it must atomically determine if that node already
exists so there is only ever one node which represents a particular thing.  While many big data
systems claim this type of ACID compliant deconfliction is possible, our testing has shown that
the claimed performance of these types of systems is drastically reduced when required to carry
out atomic check-and-add operations.

However, there is also an advantage for a deconflicted knowledge system.  When encountering a node
which has been previously observed, the system does not create a new node.  This has the counterintuitive
effect of making a cortex typically become faster as it ingests more data.  This performance
increase is especially true when ingesting data with many recurrent nodes.

"It doesn't matter that a 747 can carry more passengers than the space shuttle, when the mission
is to repair a satellite" -visi

Test Data Sets
==============

Majestic Million
----------------

The Majestic Million is a ranked list of a million FQDNs which is freely
available at http://downloads.majestic.com/majestic_million.csv .  

This dataset was selected for performance benchmarking due to it being a "worst case" bookend.
Within a cortex, inet:fqdn nodes undergo extensive normalization and often the creation of one
inet:fqdn node causes the creation of several others.  For example, creating inet:fqdn=www.woot.com
would subsequently cause the creation of inet:fqdn=woot.com and inet:fqdn=com.  Additionally, the
FQDNs within the Majestic Million dataset are already deconflicted, meaning each FQDN only occurs
once within the dataset.  This causes every record to deconflict and create new nodes.

Non-Deconflicted
----------------

A synapse cortex is also capable of ingestion and indexing of "instance knowledge" which is not
typically deconflicted.  The primary property for such nodes is typically a system generated GUID
and insert times are typically higher.  This test is intended to be close to a "best case" scenario
where node insertion is not being atomically deconflicted and node properties are not subject
to extensive normalization rules.

Cortex Configurations
=====================

Each of the supported storage technologies used by a synapse cortex are tested.  Where possible,
tests are executed with minimal or no specialized configuration in an attempt to show performance
capabilities without the use of exotic configuration.  All cortex instances are configured without
caching in an attempt to measure the speed of the storage layer implementations rather than the
caching subsystem.  A production cortex configured with caches is likely to perform queries much
faster than these results.

Ram Python-3.5 ram:///
----------------------
The RAM storage backing provides cortex storage and indexing using native python data structures
such as dictionaries and lists.  This configuration is a highly performant cortex typically used
for hypergraph data which can fit in system memory.  For these tests, the RAM cortex is initialized
with default configuration options.


LMDB lmdb:////tmp/bench.db
--------------------------
The LMDB storage backing provides cortex storage and indexing using the Symas Lightning DB
available here: https://symas.com/lightning-memory-mapped-database/

For these tests, the RAM cortex is initialized with default configuration options.

Postgres (9.5) postgres:///
---------------------------
The Postgres storage layer provides cortex storage and indexing using the Postgresql Database
available here: https://www.postgresql.org/.  For these tests, the Postgresql cortex is initialized
with default values communicating with a default Postgresql 9.5 database on Ubuntu 16.04 LTS.

Telepath Cluster
----------------
The Telepath cluster test is designed to measure the scalability of a multi-cortex federation which
is operating with the assumption of shard-based division of node creation across several cortex
hypergraphs.  The primary purpose of the test is to determine the expected overhead of cluster
logic and network protocol efficiency.  The remote cortexes are simple RAM cortexes.

Test Systems
============

The current benchmark testing environment is a cluster of 3 hosts with the following hardware:

* Intel(R) Xeon(R) CPU E5-2609 v4 @ 1.70GHz (8 cores)
* 256 GB Memory
* 1000 base T network interface ( 1 Gbps )

Results
=======

.. image:: images/synapse_bench.png

ram
---
* add w/ deconf: 3,347 nodes/sec
* query node: 21,296 queries/sec
* add w/o deconf: 11,460 nodes/sec

lmdb
----

* add w/ deconf: 1,478 nodes/sec
* query node: 7,610 queries/sec
* add w/o deconf: 6,310 nodes/sec

sqlite
------

* add w/ deconf: 385 nodes/sec
* query node: 8681 queries/sec
* add w/o deconf: 911 nodes/sec

postgres
--------

* add w/ deconf: 336 nodes/sec
* query node: 1,304 queries/sec
* add w/o deconf: 2473 nodes/sec

telepath x3
-----------

* add w/o deconf: 32,779 nodes/sec
* scale efficiency: 2.8 / 3.0

Current results show highly efficient scale gains when using multiple cortexes in a shard configuration.
However, the current testing environment involves the use of only 3 systems.  Future scale testing
using additional hardware will be a better estimate of performance in a truly production scale cluster.
That being said, current results are promising.

Additional Tests
================

Over the course of subsequent releases, a table will be added here showing the performance of releases
over time using line graphs showing the various test results over time.
