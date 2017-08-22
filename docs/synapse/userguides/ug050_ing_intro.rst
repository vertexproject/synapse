Ingest - Introduction
=====================

The Synapse Ingest subsystem was designed to help users load data into the Synapse hypergraph (Cortex). The
design principle of the ingest system was that users should be able to load data into a Cortex without needing
to write code to do so. The Ingest system can also be used to parse data from structured data sources; for
example, it can be used to parse data from web APIs and store the results in Cortex. Since Ingest is designed to be
friendly to non-programmers, Ingest definitions are typically written in JSON.

Writing an Ingest definition, either for a static set of data or for parsing data several times over, requires
familiarity with the Synapse model. Documentation on the built in models can be found at `Data Model`_.
Additional modeling documentation can be found at the `Synapse User Guide`_.

Follow Along
************

The examples shown here in the user guide can also be executed directly, so readers may follow along if they have a copy
of the Synapse git repository checked out. These examples show running the ingest tool and querying a Cortex to see
the results of running the examples.

.. _`Synapse User Guide`: ../userguide_section0.html
.. _`Data Model`: ../datamodel.html
