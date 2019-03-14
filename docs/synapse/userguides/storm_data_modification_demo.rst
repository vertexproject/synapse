




Storm Reference - Data Modification
===================================

Storm can be used to directly modify the Synapse hypergraph by:

- adding or deleting nodes;
- setting, modifying, or deleting properties on nodes; and 
- adding or deleting tags from nodes.

While the Synapse command line (cmdr) is not optimal for adding or modifying large amounts of data, users gain a powerful degree of flexibility and efficiency through the ability to create or modify data on the fly.

For adding or modifying larger amounts of data, it is preferable to use the Synapse feed utility <link>, CSV tool <link>, or programmatic ingest of data to help automate the process.

.. warning::

  The ability to add and modify data from the Synapse CLI is powerful and convenient, but also means users can
  inadvertently modify (or even delete) data inappropriately through mistyped syntax or premature striking of the
  "enter" key. While some built-in protections exist within Synapse itself it is important to remember that
  **there is no "are you sure?" prompt before a Storm query executes**.

  The following recommended “best practices” will help prevent inadvertent changes to the hypergraph:

  Use the Synapse permissions system <link> to enforce least privilege. Limit users to permissions appropriate
  for tasks they have been trained for / are responsible for.

  Limit potentially destructive permissions even for trained / trusted users. Require the use of the sudo
  <link> Storm command for significant / critical changes (such as the deletion of nodes).

  Use extreme caution when constructing complex Storm queries that may modify (or delete) large numbers of nodes.
  It is **strongly recommended** that you validate the output of a query by first running the query on its own
  to ensure it returns the expected results (set of nodes) before permanently modifying (or deleting) those nodes.

See Storm - Document Syntax Conventions <link> for an explanation of the syntax format used below.

Edit Mode
---------

To modify data in a Cortex using Storm, you must enter “edit mode”. The use of **square brackets ( ``[ ]`` )**
within a Storm query can be thought of as entering “edit mode”, with the data in the brackets specifying the
changes to be made. This is true for changes involving nodes, properties, and tags. The only exception is the
deletion of nodes, which is done using the **delnode** <link> Storm command.

The square brackets (``[ ]``) used for the Storm data modification syntax indicate "perform the enclosed changes"
in a generic way. The brackets are shorthand to request any of the following:

- Add nodes.
- Add or modify properties.
- Delete properties.
- Add tags.
- Delete tags.

This means that all of the above directives can be specified within a single set of brackets, in any combination and in any order.

.. warning::

  It is critical to remember that the **brackets are NOT a boundary that segregates nodes**; they simply indicate
  the start and end of data modification operations. They do **NOT** separate “nodes the modifications should apply   "to" from "nodes they should not apply to". Storm operator chaining <link> with left-to-right processing order
  still applies. **Any modification request that operates on previous Storm output will operate on everything to
  the left of the modify operation, regardless of whether those nodes are within or outside the brackets**.

Consider the following example:

.. code:: ipython3

    q = 'inet:ipv4=12.34.56.78 inet:fqdn=woot.com [ inet:ipv4=1.2.3.4 :asn=10101 inet:fqdn=woowoo.com +#my.tag ]'
    podes = await core.eval(q, cmdr=True)
    # An additional assertion code about the output - would fail during execution
    podes = await core.eval('#my.tag')
    # assert len(podes) == 4


.. parsed-literal::

    Error during storm execution
    Traceback (most recent call last):
      File "/home/thesilence/git/syn010/synapse/cortex.py", line 1120, in runStorm
        async for pode in snap.iterStormPodes(text, opts=opts, user=user):
      File "/home/thesilence/git/syn010/synapse/lib/snap.py", line 101, in iterStormPodes
        async for node, path in self.storm(text, opts=opts, user=user):
      File "/home/thesilence/git/syn010/synapse/lib/snap.py", line 113, in storm
        async for x in runt.iterStormQuery(query):
      File "/home/thesilence/git/syn010/synapse/lib/storm.py", line 132, in iterStormQuery
        async for node, path in query.iterNodePaths(self):
      File "/home/thesilence/git/syn010/synapse/lib/ast.py", line 162, in iterNodePaths
        async for node, path in genr:
      File "/home/thesilence/git/syn010/synapse/lib/ast.py", line 1695, in run
        async for node, path in genr:
      File "/home/thesilence/git/syn010/synapse/lib/ast.py", line 1619, in run
        async for node, path in genr:
      File "/home/thesilence/git/syn010/synapse/lib/ast.py", line 1642, in run
        raise s_exc.NoSuchProp(name=name, form=node.form.name)
    synapse.exc.NoSuchProp: NoSuchProp: form='inet:fqdn' name='asn'


.. parsed-literal::

    cli> storm inet:ipv4=12.34.56.78 inet:fqdn=woot.com [ inet:ipv4=1.2.3.4 :asn=10101 inet:fqdn=woowoo.com +#my.tag ]
    
    inet:ipv4=12.34.56.78
            .created = 2018/12/20 16:40:30.235
            :asn = 10101
            :loc = ??
            :type = unicast
            #my.tag
    complete. 1 nodes in 15 ms (66/sec).


The above Storm query will:

* lift the nodes for IP 12.34.56.78 and domain woot.com;
* create the node for IP 1.2.3.4 (if it does not exist), or retrieve it if it does;
* set the :asn property for IP 12.34.56.78 and IP 1.2.3.4;
* create the node for domain woowoo.com (if it does not exist), or retrieve it if it does; and
* apply the tag my.tag to IP 12.34.56.78, domain woot.com, IP 1.2.3.4 and domain woowoo.com.


Adding Nodes
------------

Operation to add the specified node(s) to a Cortex.

.. note::
   This following syntax block was generated as a raw nbconvert cell without any special attention given to formatting.

Syntax:

[ <form> = <valu> ... [ : <prop> = <pval> ...] ]

[ <form> = ( <valu_1> , <valu_2> , ... ) [ : <prop> = <pval> ...] ]

[ <form> = “ * ” [ : <prop> = <pval> ...] ]

Examples:

Create Simple Node:


.. parsed-literal::

    cli> storm [ inet:fqdn = woot.com ]
    
    inet:fqdn=woot.com
            .created = 2018/12/20 16:40:30.237
            :domain = com
            :host = woot
            :issuffix = False
            :iszone = True
            :zone = woot.com
    complete. 1 nodes in 2 ms (500/sec).


Create Composite (comp) Node:


.. parsed-literal::

    cli> storm [ inet:dns:a = ( woot.com , 12.34.56.78 ) ]
    
    inet:dns:a=('woot.com', '12.34.56.78')
            .created = 2018/12/20 16:40:30.304
            :fqdn = woot.com
            :ipv4 = 12.34.56.78
    complete. 1 nodes in 13 ms (76/sec).


Create GUID Node:


.. parsed-literal::

    cli> storm [ ou:org = "*" ]
    
    ou:org=102dbdc8a7c8f9b9bd2c2b6ce7224351
            .created = 2018/12/20 16:40:30.328
    complete. 1 nodes in 9 ms (111/sec).


Create Digraph (“Edge”) Node:


.. parsed-literal::

    cli> storm [ refs = ( (media:news, 00a1f0d928e25729b9e86e2d08c127ce), (inet:fqdn, woot.com) ) ]
    
    refs=((media:news, "00a1f0d928e25729b9e86e2d08c127ce"), (inet:fqdn, "woot.com"))
            .created = 2018/12/20 16:40:30.359
            :n1 = ('media:news', '00a1f0d928e25729b9e86e2d08c127ce')
            :n1:form = media:news
            :n2 = ('inet:fqdn', 'woot.com')
            :n2:form = inet:fqdn
    complete. 1 nodes in 12 ms (83/sec).


Create Multiple Nodes at once:


.. parsed-literal::

    cli> storm [ inet:fqdn = hehe.com inet:ipv4 = 127.0.0.1 hash:md5 = d41d8cd98f00b204e9800998ecf8427e]
    
    inet:fqdn=hehe.com
            .created = 2018/12/20 16:40:30.391
            :domain = com
            :host = hehe
            :issuffix = False
            :iszone = True
            :zone = hehe.com
    inet:ipv4=127.0.0.1
            .created = 2018/12/20 16:40:30.392
            :asn = 0
            :loc = ??
            :type = loopback
    hash:md5=d41d8cd98f00b204e9800998ecf8427e
            .created = 2018/12/20 16:40:30.392
    complete. 3 nodes in 11 ms (272/sec).


Create Simple Node with Secondary Properties:


.. parsed-literal::

    cli> storm [ inet:ipv4 = 94.75.194.194 :loc = nl ]
    
    inet:ipv4=94.75.194.194
            .created = 2018/12/20 16:40:30.419
            :asn = 0
            :loc = nl
            :type = unicast
    complete. 1 nodes in 11 ms (90/sec).


Usage Notes:

* Storm can create as many nodes as are specified within the brackets. It is not necessary to create only one node at a time.
* For nodes specified within the brackets that do not already exist, Storm will create and return the node. For nodes that already exist, Storm will simply return that node.
* When creating a <form> whose <valu> consists of multiple components, the components must be passed as a comma-separated list enclosed in parentheses.
* When creating a node whose primary property is a GUID, an asterisk ( `*` ) can be used to instruct Storm to generate a randomly-generated GUID on node creation.


Modifying Nodes
---------------

Once a node is created, its primary property (<form> = <valu>) cannot be modified. The only way to “change” a node’s primary property is to create a new node.

“Changing” nodes therefore consists of adding, modifying, or deleting secondary properties (including universal properties).


Adding or Modifying Properties
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Operation to add (set) or change one or more properties on the specified node(s).

The same syntax is used to apply a new property or modify an existing property.

Syntax:

<query> [ : <prop> = <pval> ... ]

Examples:

Set (or modify) secondary property:


.. parsed-literal::

    cli> storm inet:ipv4=12.34.56.78 [ :loc = us.oh.wilmington ]
    
    inet:ipv4=12.34.56.78
            .created = 2018/12/20 16:40:30.235
            :asn = 10101
            :loc = us.oh.wilmington
            :type = unicast
            #my.tag
    complete. 1 nodes in 8 ms (125/sec).


Set (or modify) universal secondary property:


.. parsed-literal::

    cli> storm inet:dns:a = (woot.com,  12.34.56.78) [ .seen=( 201708010123, 201708100456 ) ]
    
    inet:dns:a=('woot.com', '12.34.56.78')
            .created = 2018/12/20 16:40:30.304
            .seen = ('2017/08/01 01:23:00.000', '2017/08/10 04:56:00.000')
            :fqdn = woot.com
            :ipv4 = 12.34.56.78
    complete. 1 nodes in 7 ms (142/sec).


Set (or modify) interval property with open-ended maximum:


.. parsed-literal::

    cli> storm inet:dns:a = (woot.com,  12.34.56.78) [ .seen=( 201708010123, "?" ) ]
    
    inet:dns:a=('woot.com', '12.34.56.78')
            .created = 2018/12/20 16:40:30.304
            .seen = ('2017/08/01 01:23:00.000', '?')
            :fqdn = woot.com
            :ipv4 = 12.34.56.78
    complete. 1 nodes in 8 ms (125/sec).


Set (or modify) string property to null value:


.. parsed-literal::

    cli> storm media:news = 00a1f0d928e25729b9e86e2d08c127ce [ :summary = "" ]
    
    media:news=00a1f0d928e25729b9e86e2d08c127ce
            .created = 2018/12/20 16:40:30.358
            :author = ?,?
            :published = 1970/01/01 00:00:00.000
            :summary = 
            :title = ??
    complete. 1 nodes in 9 ms (111/sec).


Usage Notes:
* Additions or changes to properties are performed on the output of a previous Storm query. 
* Storm will set or change the specified properties for all nodes in the current working set (i.e., all nodes resulting from Storm syntax to the left of the <prop>=<pval> statement(s)) for which that property is valid, **whether those nodes are within or outside of the brackets**.
* Specifying a property will set the <prop> = <pval> if it does not exist, or modify (overwrite) the <prop> = <pval> if it already exists.
* Storm will set or modify the secondary property for all nodes returned by <query> for which that secondary property is a valid property. Nodes for which that property is not a valid secondary property will be ignored.
* Secondary properties must be specified by their relative property name. For the form foo:bar and the property baz (e.g., foo:bar:baz) the relative property name is specified as :baz.
* Storm can set or modify any property except those explicitly defined as read-only ('ro' : 1) in the data model. Attempts to modify read only properties will return an error.

