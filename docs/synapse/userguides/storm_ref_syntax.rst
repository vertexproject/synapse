.. highlight:: none

.. _storm-ref-syntax:

Storm Reference - Document Syntax Conventions
=============================================

This section covers the following important conventions used within the Storm Reference Documents:

- `Storm and Layers`_
- `Storm Syntax Conventions`_
- `Usage Statements vs. Specific Storm Queries`_
- `Type-Specific Behavior`_
- `Whitespace`_

Storm and Layers
----------------

**The Storm Reference documentation provides basic syntax examples that assume a simple Storm environment - that is, a Cortex with a single Layer.** For multi-Layer Cortexes, the effects of specific Storm commands - particularly data modification commands - may vary based on the specific arrangement of read / write Layers, the Layer in which the command is executed, and the permissions of the user.

Storm Syntax Conventions
------------------------

The Storm Reference documentation provides numerous examples of both abstract Storm syntax (usage statements) and specific Storm queries. The following conventions are used for Storm **usage statements:**

- Items that must be entered literally on the command line are in **bold.** These items include command names and literal characters.
- Items that represent "variables" that must be replaced with a name or value are placed within angle brackets ( ``< >`` ) in *italics*. Most "variables" are self-explanatory, however a few commonly used variable terms are defined here for convenience:

    - *<form>* refers to a form / node primary property, such as ``inet:fqdn``.
    - *<valu>* refers to the value of a primary property, such as ``woot.com`` in ``inet:fqdn=woot.com``.
    - *<prop>* refers to a node secondary property (including universal properties) such as ``inet:ip:asn`` or ``inet:ip.created``.
    - *<pval>* refers to the value of a secondary property, such as ``4808`` in ``inet:ip:asn=4808``.
    - *<query>* refers to a Storm query.
    - *<inet:fqdn>* refers to a Storm query whose results contain the specified form(s)
    - *<tag>* refers to a tag (``#sometag`` as opposed to a ``syn:tag`` form).

- **Bold brackets** are literal characters. Parameters enclosed in non-bolded brackets are optional.
- Parameters **not** enclosed in brackets are required.
- A vertical bar signifies that you choose only one parameter. For example:

    - ``a | b`` indicates that you must choose a or b.
    - ``[ a | b ]`` indicates that you can choose a, b, or nothing (the non-bolded brackets indicate the parameter is optional).

- Ellipses ( `...` ) signify the parameter can be repeated on the command line.
- The ``storm`` command that must precede a Storm query is assumed and is omitted from examples.

**Example:**

**[** *<form>* **=** *<valu>* [ **:** *<prop>* **=** *<pval>* ... ] **]**

The Storm query above adds a new node.

- The outer brackets are in **bold** and are required literal characters to specify a data modification (add) operation. Similarly, the equals signs are in **bold** to indicate literal characters.
- *<form>* and *<valu>* would need to be replaced by the specific form (such as ``inet:ip``) and primary property value (such as ``1.2.3.4``) for the node being created.
- The inner brackets are not bolded and indicate that one or more secondary properties can **optionally** be specified.
- *<prop>* and *<pval>* would need to be replaced by the specific secondary property and value to add to the node, such as ``:loc = us``.
- The ellipsis ( ``...`` ) indicate that additional secondary properties can optionally be specified. 

Usage Statements vs. Specific Storm Queries
-------------------------------------------

Examples of specific queries represent fully literal input, but are not shown in bold for readability. For example:

**Usage statement:**

**[** *<form>* **=** *<valu>* [ **:** *<prop>* **=** *<pval>* ...] **]**

**Example query:**

[ inet:ip = 1.2.3.4 :loc = us ]

Type-Specific Behavior
----------------------

Some data types within the Synapse data model have been optimized in ways that impact their behavior within Storm queries (e.g., how types can be input, lifted, filtered, etc.) See :ref:`storm-ref-type-specific` for details.

Whitespace
----------

Whitespace may be used in the examples for formatting and readability.
