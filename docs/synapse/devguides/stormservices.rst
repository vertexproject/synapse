.. _dev_stormservices:

Storm Service Development
#########################

NOTE: These docs are an initial place holder to hold some notes.

Anatomy of a Storm Service
==========================

Storm Service Modules
=====================

Storm Service Commands
======================

Input/Output Conventions
------------------------

Most commands that enrich or add additional context to nodes should simply yield the nodes they were given as inputs.  If they don’t know how to enrich or add additional context to a given form, nodes of that form should be yielded rather than producing an error.  This allows a series of enrichment commands to be pipelined regardless of the different inputs that a given command knows how to operate on.

Argument Conventions
--------------------

``--verbose``
~~~~~~~~~~~~~

In general, storm commands should operate silently over their input nodes and should especially avoid printing anything "per node".  However, when an error occurs, the command may use ``$lib.warn()`` to print a warning message per-node.  Commands should implement a ``--verbose`` command line option to enable printing "per node" informational output.

``--debug``
~~~~~~~~~~~

``--yield``
~~~~~~~~~~~

For commands that create additional nodes, it may be beneficial to add a --yield option to allow a query to operate on the newly created nodes.  Some guidelines for ``--yield`` options:

- The command should *not* yield the input node(s) when a --yield is specified
- The --yield option should *not* be implemented when pivoting from the input node to reach the newly created node is a “refs out” or 1-to-1 direct pivot. For example, there is no need to have a --yield option on the ``maxmind`` command even though it may create an ``inet:asn`` node for an input ``inet:ipv4`` node due to the 1-to-1 pivot ``-> inet:asn`` being possible.
- The ``--yield`` option should ideally determine a “primary” node form to yield even when the command may create many forms in order to tag them or update .seen times.
