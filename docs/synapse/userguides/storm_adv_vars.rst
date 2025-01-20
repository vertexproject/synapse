.. highlight:: none


.. _storm-adv-vars:

Storm Reference - Advanced - Variables
======================================

Storm supports the use of **variables.** A :ref:`gloss-variable` is a value that can change depending
on conditions or on information passed to the Storm query. (Contrast this with a :ref:`gloss-constant`,
which is a value that is fixed and does not change.)

Variables can be used in a variety of ways, such as providing more efficient ways to reference node properties;
facilitating bulk operations; or writing extensions to Synapse (such as `Power-Ups`_) in Storm.

These documents approach variables and their use from a **user** standpoint and aim to provide sufficient
background for users to understand and begin to use variables. They do not provide an in-depth discussion
of variables and their use. See the :ref:`devguide` for more developer-focused topics.

.. NOTE::
  
  It is important to keep the high-level :ref:`storm-op-concepts` in mind when writing Storm queries
  or code. This is especially true when working with variables, control flow, and other more advanced
  concepts.


.. _var-concepts:

Variable Concepts
-----------------

.. _var-scope:

Variable Scope
++++++++++++++

A variable’s **scope** is its lifetime and under what conditions it may be accessed. There are two
dimensions that impact a variable’s scope: its **call frame** and its **runtime safety** ("runtsafety").

.. _var-call-frame:

Call Frame
++++++++++

A variable’s **call frame** is where the variable is used. The main Storm query starts with its own call
frame, and each call to a "pure" Storm command, function, or subquery creates a new call frame. The new
call frame gets a copy of all the variables from the calling call frame. Changes to existing variables or
the creation of new variables within the new call frame do not impact the calling scope.

Runtsafe vs. Non-Runtsafe
+++++++++++++++++++++++++

An important distinction to keep in mind when using variables in Storm is whether the variable is runtime-safe
(:ref:`gloss-runtsafe`) or non-runtime safe (:ref:`gloss-non-runtsafe`).

A variable that is **runtsafe** has a value independent of any nodes passing through the Storm pipeline. For
example, a variable whose value is explicitly set, such as ``$string = mystring`` or ``$ipv4 = 8.8.8.8``  is
considered runtsafe because the value does not change / is not affected by the specific node passing through
the Storm pipeline (i.e., by the Storm runtime).

A variable that is **non-runtsafe** has a value derived from a node passing through the Storm pipeline. For
example, a variable whose value is set to a node property value may change based on the specific node passing
through the Storm pipeline at the time. In other words, if your Storm query is operating on a set of DNS A nodes
(``inet:dns:a``) and you define the variable ``$fqdn = :fqdn`` to set the variable to the value of the ``:fqdn``
property, the value of the variable will change based on the value of that property for the current
``inet:dns:a`` node.

All non-runtsafe variables are **scoped** to an individual node as it passes through the Storm pipeline. This
means that a variable’s value based on a given node is not available when processing a different node (at least
not without using special commands, methods, or libraries). In other words, the path of a particular node as
it passes through the Storm pipeline is its own scope.

.. NOTE::
  
  The "safe" in non-runtsafe should **not** be interpreted to mean that the use of non-runtsafe variables is
  somehow "risky" or involves insecure programming or processing of data. It simply means the value of the
  variable is not safe from changing (i.e., it may change) as the Storm pipeline progresses.

.. _var-types:

Types of Variables
------------------

Storm supports two types of variables:

- **Built-in variables.** Built-in variables facilitate many common Storm operations. They may vary in their
  scope and in the context in which they can be used.
- **User-defined variables** User-defined variables are named and defined by the user. They are most often
  limited in scope and facilitate operations within a specific Storm query.

.. _vars-builtin:

Built-In Variables
++++++++++++++++++

Storm includes a set of built-in variables and associated variable `methods`_ and `libraries`_ that
facilitate Cortex-wide, node-specific, and context-specific operations.

Built-in variables differ from user-defined variables in that built-in variable names:

- are initialized at Cortex start,
- are reserved,
- can be accessed automatically (i.e., without needing to define them) from within Storm, and
- persist across user sessions and Cortex reboots.

.. TIP::
  
  We cover a few of the **most common** built-in variables here. For additional detail on Synapse's
  Storm types (objects) and libraries, see the :ref:`stormtypes_index`.


.. _vars-global:

Global Variables
~~~~~~~~~~~~~~~~

Global variables operate independently of any node. That is, they can be invoked in a Storm query in the
absence of any nodes in the Storm execution pipeline (though they can also be used when performing
operations on nodes).

.. _vars-global-lib:

$lib
####

The library variable ( ``$lib`` ) is a built-in variable that provides access to the global Storm library.
In Storm, libraries are accessed using built-in variable names (e.g., ``$lib.print()``).

Libraries provide access to a wide range of additional functionality with Storm. See the
:ref:`stormtypes-libs-header` technical documentation for descriptions of the libraries available
within Storm.

.. _vars-node:

Node-Specific Variables
~~~~~~~~~~~~~~~~~~~~~~~

Storm includes node-specific variables that are designed to operate on or in conjunction with nodes and
require one or more nodes in the Storm pipeline.

.. NOTE::

  Node-specific variables are always non-runtsafe.

.. _vars-node-node:

$node
#####

The node variable (``$node``) is a built-in Storm variable that **references the current node in the Storm
pipeline.** Specifically, this variable contains the inbound node’s node object, and provides access to the
node’s attributes, properties, and associated attribute and property values.

Invoking this variable during a Storm query is useful when you want to:

- access the entire raw node object,
- store the value of the current node before pivoting to another node, or
- use an aspect of the current node in subsequent query operations.

The ``$node`` variable supports a number of built-in **methods** that can be used to access specific data
or properties associated with a node. See the technical documentation for the :ref:`stormprims-node-f527`
object or the :ref:`meth-node` section of the :ref:`storm-adv-methods` user documentation for additional
detail and examples.

.. _vars-node-path:

$path
#####

The path variable (``$path``) is a built-in Storm variable that **references the path of a node as it travels
through the pipeline of a Storm query.**

The ``$path`` variable is not used on its own, but in conjunction with its methods. See the technical
documentation for the :ref:`stormprims-node-path-f527` object or the :ref:`meth-path` section of the
:ref:`storm-adv-methods` user documentation for additional detail and examples.

.. _vars-trigger:

Trigger-Specific Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

A :ref:`gloss-trigger` is used to support automation within a Cortex. Triggers use events (such as creating a
node, setting a node’s property value, or applying a tag to a node) to fire ("trigger") the execution of a
predefined Storm query. Storm uses a built-in variable specifically within the context of trigger-initiated
Storm queries.

.. _vars-trigger-auto:

$auto
#####

The ``$auto`` variable is a dictionary which is automatically populated when a trigger executes, containing
information about the trigger and the event which caused the trigger to execute.

See the :ref:`auto-triggers` section of the :ref:`storm-ref-automation` document and the Storm :ref:`storm-trigger`
command for a more detailed discussion of triggers and associated Storm commands.

.. _vars-ingest:

Ingest Variables
~~~~~~~~~~~~~~~~

Synapse's :ref:`syn-tools-csvtool` can be used to ingest (import) data into Synapse from a comma-separated
value (CSV) file. Storm includes a built-in variable to facilitate bulk data ingest using CSV.

.. _vars-ingest-rows:

$rows
#####

The ``$rows`` variable refers to the set of rows in a CSV file. When ingesting data into Synapse, CSVTool
(or the Optic Ingest Tool) reads a CSV file and a file containing a Storm query that tells Synapse how to
process the CSV data. The Storm query is typically constructed to iterate over the set of rows (``$rows``)
using a :ref:`flow-for` that uses user-defined variables to reference each field (column) in the CSV data.

For example:

::

  for ($var1, $var2, $var3, $var4) in $rows { <do stuff> }


.. TIP::
  
  The commercial Synapse UI (:ref:`gloss-optic`) includes an `Ingest Tool`_ that can ingest data in CSV, 
  JSONL, or JSON format. The ``$rows`` variable is used in the Ingest Tool to refer to either the set
  of rows in a CSV file or the set of lines ("rows") in a JSONL file. In addition, the ``$blob`` variable
  is used to refer to the entire JSON blob when ingesting JSON data. See the `ingest examples`_ section
  of the Ingest Tool documentation for additional detail.

.. _vars-user:

User-Defined Variables
++++++++++++++++++++++

User-defined variables can be defined in one of two ways:

- At runtime (i.e., within the scope of a specific Storm query). This is the most common use for user-defined
  variables.
- Mapped via options passed to the Storm runtime (for example, when using the :ref:`http-api-cortex` API). This
  method is less common for everyday users. When defined in this manner, user-defined variables will behave as
  though they are built-in variables that are runtsafe.

.. _vars-names:

Variable Names
~~~~~~~~~~~~~~

All variable names in Storm (including built-in variables) begin with a dollar sign ( ``$`` ). A variable name
can be any alphanumeric string, **except for** the name of a built-in variable (see :ref:`vars-builtin`), as
those names are reserved. Variable names are case-sensitive; the variable ``$MyVar`` is different from ``$myvar``.

.. NOTE::

  Storm will not **prevent** you from using the name of a built-in variable to define a variable (such as
  ``$node = 7``). However, doing so may result in undesired effects or unexpected errors due to the variable
  name collision.

.. _vars-define:

Defining Variables
~~~~~~~~~~~~~~~~~~

Within Storm, a user-defined variable is defined using the syntax:

::

  $<varname> = <value>

The variable name must be specified first, followed by the equals sign and the value of the variable itself.

``<value>`` can be:

- an explicit value (literal),
- a node property (secondary or universal),
- a built-in variable or method (e.g., can allow you to access a node's primary property, form name, or other
  elements),
- a tag (allows you to access timestamps associated with a tag),
- a library function,
- an expression, or
- an embedded Storm query.

Examples
~~~~~~~~

The examples below use the ``$lib.print()`` library function to display the **value** of the user-defined
variable being set. (This is done for illustrative purposes only; ``$lib.print()`` is not required in order
to use variables or methods.)

In some instances we include a second example to illustrate how a particular kind of variable assignment
might be used in a real-world scenario. While we have attempted to use relatively simple examples for clarity,
some examples may leverage additional Storm features such as `subqueries`_, `subquery filters`_, or 
`control flow`_ elements such as for loops or switch statements.

.. TIP::
  
  Keep Storm's operation chaining, pipeline, and node consumption aspects in mind when reviewing the
  following examples. When using ``$lib.print()`` to display the value of a variable, the queries
  below will:
  
  - Lift the specified node(s).
  - Assign the variable. Note that assigning a variable has no impact on the nodes themselves.
  - Print the variable's value using ``$lib.print()``.
  - Return any nodes still in the pipeline. Because variable assignment doesn't impact the node(s) or
    transform the working set, the nodes remain in the pipeline and are returned (displayed) at the CLI.
  
  The effect of this process is that for each node in the Storm query pipeline, the output of ``$lib.print()``
  is displayed, followed by the relevant node.
  
  In some examples the Storm :ref:`storm-spin` command is used to suppress display of the node itself.
  We do this for cases where displaying the node detracts from illustrating the value of the variable.


**Explicit values / literals**

You can assign an explicit, unchanging value to a variable.

- Assign the value 5 to the variable ``$threshold``:

::

    storm> $threshold=5 $lib.print($threshold)
    5

    

*Example:*

- Tag ``file:bytes`` nodes that have a number of malicious AV scan results higher than a given threshold for review:

::

    storm> $threshold=5 file:bytes +{ -> it:av:scan:result +:verdict=malicious } >= $threshold [ +#review ]
    file:bytes=sha256:00007694135237ec8dc5234007043814608f239befdfc8a61b992e4d09e0cf3f
            :sha256 = 00007694135237ec8dc5234007043814608f239befdfc8a61b992e4d09e0cf3f
            .created = 2025/01/20 15:47:31.446
            #review


.. TIP::
  
  The example above uses a subquery filter (:ref:`filter-subquery`) to pivot to the ``it:av:scan:result`` nodes
  associated with the ``file:bytes`` node, and compares the number of malicious AV scan results to the value of the ``$threshold``
  variable.


**Node properties**

You can assign the value of a particular node property (secondary or universal) to a variable.

- **Secondary property:** Assign the ``:email`` property from an Internet-based account (``inet:service:account``) to
  the variable ``$email``:

::

    storm> inet:service:account=(twitter.com,hacks4cats) $email=:email $lib.print($email)
    ron@protonmail.com
    inet:service:account=f8f802be12282d27423e241f7d108b80
            :email = ron@protonmail.com
            .created = 2025/01/20 15:47:31.514



- **Universal property:** Assign the ``.seen`` universal property from a DNS A node to the variable ``$time``:

::

    storm> inet:dns:a=(woot.com,1.2.3.4) $time=.seen $lib.print($time)
    (1543289294000, 1565893967000)
    inet:dns:a=('woot.com', '1.2.3.4')
            :fqdn = woot.com
            :ip = 1.2.3.4
            .created = 2025/01/20 15:47:31.531
            .seen = ('2018/11/27 03:28:14.000', '2019/08/15 18:32:47.000')


.. NOTE::
  
  In the output above, the variable value is displayed as a pair of epoch milliseconds, which is how Synapse
  stores date/time values.


*Example:*
  
- Given a DNS A record observed within a specific time period, find other DNS A records that pointed to the
  same IP address in the same time window:

::

    storm> inet:dns:a=(woot.com,1.2.3.4) $time=.seen -> inet:ip -> inet:dns:a +.seen@=$time
    inet:dns:a=('woot.com', '1.2.3.4')
            :fqdn = woot.com
            :ip = 1.2.3.4
            .created = 2025/01/20 15:47:31.531
            .seen = ('2018/11/27 03:28:14.000', '2019/08/15 18:32:47.000')
    inet:dns:a=('hurr.net', '1.2.3.4')
            :fqdn = hurr.net
            :ip = 1.2.3.4
            .created = 2025/01/20 15:47:31.548
            .seen = ('2018/12/09 06:02:53.000', '2019/01/03 11:27:01.000')


.. TIP::
  
  An interval (such as a ``.seen`` property) consists of a **pair** of date/time values. In the example
  above, the value of the variable ``$time`` is the combined pair (min / max) of times.
  
  To access the "first seen" (minimum) or "last seen" (maximum) time values separately, use a pair of
  variables in the assignment:
  
  ``($min, $max) = .seen``


**Built-in variables and methods**

:ref:`vars-builtin` (including :ref:`vars-node`) allow you to reference common Synapse objects and their
associated components. For many common user-facing tasks, the ``$node`` variable and its methods are the
most useful.

- **Node object:** Assign an entire FQDN node to the variable ``$fqdn`` using the ``$node`` built-in
  variable:

::

    storm> inet:fqdn=mail.mydomain.com $fqdn=$node $lib.print($fqdn)
    Node{(('inet:fqdn', 'mail.mydomain.com'), {'nid': 28, 'iden': '6511121afd61bf42cb4d14aed4f61daf62ebfc76042dba12d95a6506dd8b6cc4', 'tags': {}, 'props': {'host': 'mail', 'domain': 'mydomain.com', '.created': 1737388051565, 'issuffix': 0, 'iszone': 0, 'zone': 'mydomain.com'}, 'tagprops': defaultdict(<class 'dict'>, {})})}
    inet:fqdn=mail.mydomain.com
            :domain = mydomain.com
            :host = mail
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2025/01/20 15:47:31.565


.. NOTE::
  
  When you use the built-in variable ``$node`` to assign a value to a variable, the value is set to the
  **entire node object** (refer to the output above). For common user-facing tasks, it is less likely that
  users will need "the entire node"; more often, they need to refer to a **component** of the node, such as
  its primary property value, form name, or associated tags.
  
  For some use cases, Synapse and Storm can "understand" which component of the node you want when
  referring to the full ``$node`` object. However, you can always be explicit by using the appropriate
  **method** to access the component you want (such as ``$node.value()`` or ``$node.form()``).
  
  See the technical documentation for the :ref:`stormprims-node-f527` object or the :ref:`meth-node`
  section of the :ref:`storm-adv-methods` user documentation for additional detail and examples when using
  methods associated with the ``$node`` built-in variable.

- **Node method:** Assign the **primary property value** of a domain node to the variable ``$fqdn`` using
  the ``$node.value()`` method:

::

    storm> inet:fqdn=mail.mydomain.com $fqdn=$node.value() $lib.print($fqdn)
    mail.mydomain.com
    inet:fqdn=mail.mydomain.com
            :domain = mydomain.com
            :host = mail
            :issuffix = false
            :iszone = false
            :zone = mydomain.com
            .created = 2025/01/20 15:47:31.565

    

- Find the DNS A records associated with a given domain where the PTR record for the IP matches the FQDN:

::

    storm> inet:fqdn=mail.mydomain.com $fqdn=$node.value() -> inet:dns:a +{ -> inet:ip +:dns:rev=$fqdn }
    inet:dns:a=('mail.mydomain.com', '25.25.25.25')
            :fqdn = mail.mydomain.com
            :ip = 25.25.25.25
            .created = 2025/01/20 15:47:31.583


.. TIP::
  
  The example above uses a subquery filter (see :ref:`filter-subquery`) to pivot from the DNS A records
  to associated IP nodes (``inet:ip``) and checks whether the ``:dns:rev`` property matches the FQDN
  in the variable ``$fqdn``.


**Tags**

Recall that tags are both **nodes** (``syn:tag=my.tag``) and **labels** that can be applied to other nodes
(``#my.tag``). Tags can also have optional timestamps (a time interval) associated with them.

There are various ways to assign tags as variables, depending on what part of the tag you want to access.
Many of these use cases are covered above so are briefly illustrated here.

- **Tag value:** Assign an explicit tag value (literal) to the variable ``$mytag``:

::

    storm> $mytag=cno.infra.dns.sinkhole


- **Tag on a node:** Given a ``hash:md5`` node, assign any malware tags (tags matching the glob pattern
  ``cno.mal.*``) to the variable ``$mytags`` using the ``$node.tags()`` method:

::

    storm> hash:md5=d41d8cd98f00b204e9800998ecf8427e $mytags=$node.tags(cno.mal.*) $lib.print($mytags)
    ['cno.mal.bar', 'cno.mal.foo']
    hash:md5=d41d8cd98f00b204e9800998ecf8427e
            .created = 2025/01/20 15:47:31.615
            #cno.mal.bar
            #cno.mal.foo
            #cno.threat.baz


.. TIP::
  
  In the example above, the value of the variable ``$mytags`` is the **set** of two tags, ``cno.mal.foo``
  and ``cno.mal.bar``, because the MD5 hash node has two tags that match the pattern ``cno.mal.*``.
  
  To assign the set of any / all tags on a node to a variable, simply use ``$mytags=$node.tags()``.
  
  **Note** that you can also use ``$node.tags()`` directly (this method **always** refers to the full set
  of tags on the current node) without explicitly assigning a separate variable.)
  
  Where the value of a variable is a **set**, a :ref:`flow-for` is often used to "do something" based on each
  value in the set.

*Example*

- Given an MD5 hash, copy any ``cno.mal.*`` tags from the hash to the associated file (``file:bytes`` node):

::

    storm> hash:md5=d41d8cd98f00b204e9800998ecf8427e $mytags=$node.tags(cno.mal.*) for $tag in $mytags { -> file:bytes [ +#$tag ] }
    file:bytes=sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            :md5 = d41d8cd98f00b204e9800998ecf8427e
            :sha1 = da39a3ee5e6b4b0d3255bfef95601890afd80709
            :sha256 = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            :size = 0
            .created = 2025/01/20 15:47:31.631
            #cno.mal.bar
    file:bytes=sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            :md5 = d41d8cd98f00b204e9800998ecf8427e
            :sha1 = da39a3ee5e6b4b0d3255bfef95601890afd80709
            :sha256 = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            :size = 0
            .created = 2025/01/20 15:47:31.631
            #cno.mal.bar
            #cno.mal.foo


The output above includes two "copies" of the ``file:bytes`` node because the node is output twice - once
for each iteration of the for loop. The first iteration copies / applies the ``cno.mal.foo`` tag; the
second iteration applies the ``cno.mal.bar`` tag. For a detailed explanation of this behavior, see
:ref:`storm-adv-example`.

.. TIP::
  
  The above example explicitly creates and assigns the variable ``$mytags`` and then uses that variable in a
  :ref:`flow-for`. In this case you can shorten the syntax by skipping the explicit variable assignment and
  using the ``$node.tags()`` method directly:
  
  ::
    
    hash:md5=d41d8cd98f00b204e9800998ecf8427e for $tag in $node.tags(cno.mal.*) { -> file:bytes [ +#$tag ] }
  

- **Tag timestamps:** Assign the times associated with Threat Group 20’s control of a malicious domain to the variable
  ``$time``:

::

    storm> inet:fqdn=evildomain.com $time=#cno.threat.t20.own $lib.print($time)
    (1567900800000, 1631059200000)
    inet:fqdn=evildomain.com
            :domain = com
            :host = evildomain
            :issuffix = false
            :iszone = true
            :zone = evildomain.com
            .created = 2025/01/20 15:47:31.649
            #cno.threat.t20.own = (2019/09/08 00:00:00.000, 2021/09/08 00:00:00.000)


*Example*

- Find DNS A records for any subdomain associated with a Threat Group 20 FQDN (zone) during the time they
  controlled the domain:

::

    storm> inet:fqdn#cno.threat.t20.own $time=#cno.threat.t20.own -> inet:fqdn:zone -> inet:dns:a +.seen@=$time
    inet:dns:a=('www.evildomain.com', '1.2.3.4')
            :fqdn = www.evildomain.com
            :ip = 1.2.3.4
            .created = 2025/01/20 15:47:31.665
            .seen = ('2020/07/12 00:00:00.000', '2020/12/13 00:00:00.000')
    inet:dns:a=('smtp.evildomain.com', '5.6.7.8')
            :fqdn = smtp.evildomain.com
            :ip = 5.6.7.8
            .created = 2025/01/20 15:47:31.668
            .seen = ('2020/04/04 00:00:00.000', '2020/08/02 00:00:00.000')



**Library Functions**

Storm types (Storm objects) and Storm libraries allow you to inspect, edit, and otherwise work with data in
Synapse in various ways. You can assign a value to a variable based on the output of a method or library.

A full discussion of this topic is outside of the scope of this user guide. See :ref:`stormtypes_index` for
additional details.


- Assign the current time to the variable ``$now`` using ``$lib.time.now()``:

::

    storm> $now=$lib.time.now() $lib.print($now)
    1737388051684


- Convert an epoch milliseconds integer into a human-readable date/time string using ``$lib.str.format()``:

::

    storm> $now=$lib.time.now() $time=$lib.time.format($now, '%Y/%m/%d %H:%M:%S') $lib.print($time)
    2025/01/20 15:47:31


**Expressions**

You can assign a value to a variable based on the computed value of an expression:

- Use an expression to increment the variable ``$x``:

::

    storm> $x=5 $x=($x + 1) $lib.print($x)
    6



**Embedded Storm query**

You can assign a value to a variable based on the output of a Storm query. To denote the Storm query to be
evaluated, enclose the query in curly braces (``{ <storm query> }``).

- Assign an ``ou:org`` node's guid value to the variable ``$org`` by lifting the associated org node using its
  ``:name`` property:

::

    storm> $org={ ou:org:name=vertex } $lib.print($org)
    Node{(('ou:org', '6276cd1298ade9037906b02b00aa8c31'), {'nid': 54, 'iden': 'dc7b6be323e8d7ec91849c5485a59fb7c804be99d6cd807705d22462980f416c', 'tags': {}, 'props': {'.created': 1737388051725, 'name': 'vertex', 'loc': 'us.va', 'url': 'https://vertex.link/'}, 'tagprops': defaultdict(<class 'dict'>, {})})}



.. _Power-Ups: https://synapse.docs.vertex.link/en/latest/synapse/glossary.html#power-up

.. _more detail: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_intro.html#storm-operating-concepts

.. _methods: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_adv_methods.html

.. _libraries: https://synapse.docs.vertex.link/en/latest/synapse/autodocs/stormtypes_libs.html

.. _subqueries: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_subquery.html

.. _subquery filters: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_filter.html#subquery-filters

.. _control flow: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_adv_control.html

.. _Ingest Tool: https://synapse.docs.vertex.link/projects/optic/en/latest/user_interface/userguides/ingest_tool.html

.. _ingest examples: https://synapse.docs.vertex.link/projects/optic/en/latest/user_interface/userguides/ingest_tool.html#ingest-examples
