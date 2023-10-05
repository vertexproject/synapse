.. highlight:: none


.. _storm-adv-methods:

Storm Reference - Advanced - Methods
====================================

Some of Storm’s :ref:`vars-builtin` support **methods** used to perform various actions on the object
represented by the variable.

A **subset** of the built-in variables / objects that support methods, along with a few commonly used
methods and examples, are listed below. For full detail, refer to the :ref:`stormtypes-prim-header`
technical reference.

The built-in :ref:`vars-global-lib` variable is used to access Storm libraries. See the :ref:`stormtypes-libs-header`
technical reference for additional detail on available libraries.

.. NOTE::

  In the examples below, the ``$lib.print()`` library function is used to display the value returned
  when a specific built-in variable or method is called. This is done for illustrative purposes only;
  ``$lib.print()`` is not required in order to use variables or methods.
  
  In some examples the Storm :ref:`storm-spin` command is used to suppress display of the node itself.
  We do this for cases where displaying the node detracts from illustrating the value of the variable.

In some instances we have included "use-case" examples, where the variable or method is used in a sample
query to illustrate a possible practical use. These represent exemplar Storm queries for how a variable
or method might be used in practice. While we have attempted to use relatively simple examples for clarity,
some examples may leverage additional Storm features such as `subqueries`_, `subquery filters`_, or 
`control flow`_ elements such as for loops or switch statements.


.. _meth-node:

$node
-----

:ref:`vars-node-node` is a built-in Storm variable that references **the current node in the Storm query pipeline.**
``$node`` can be used as a variable on its own or with the example methods listed below. See the
:ref:`stormprims-node-f527` section of the :ref:`stormtypes-prim-header` technical documentation
for a full list.

.. NOTE::

  As the ``$node`` variable and related methods reference the current node in the Storm pipeline, any Storm
  logic referencing ``$node`` will fail to execute if the pipeline does not contain a node (i.e., based on
  previously executing Storm logic).

**Examples**

- Print the value of ``$node`` for an ``inet:dns:a`` node:

::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node) | spin
    Node{(('inet:dns:a', ('woot.com', 917309932)), {'iden': '01235b5877954084e798f09ba3fd3f1cda2e7b41d79b752b80acbed1b609cbaa', 'tags': {}, 'props': {'.created': 1696542454644, 'fqdn': 'woot.com', 'ipv4': 917309932, '.seen': (1482957991000, 1482957991001)}, 'tagprops': defaultdict(<class 'dict'>, {}), 'nodedata': {}})}


- Print the value of ``$node`` for an ``inet:fqdn`` node with tags present:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node) | spin
    Node{(('inet:fqdn', 'aunewsonline.com'), {'iden': '53aa7a2f7125392302c36247b97569dd84a7f3fe9e92eb99abd984349dc53fe4', 'tags': {'rep': (None, None), 'rep.mandiant': (None, None), 'rep.mandiant.apt1': (None, None), 'cno': (None, None), 'cno.infra': (None, None), 'cno.infra.dns': (None, None), 'cno.infra.dns.sink': (None, None), 'cno.infra.dns.sink.hole': (None, None), 'cno.infra.dns.sink.hole.kleissner': (1385424000000, 1480118400000)}, 'props': {'.created': 1696542454743, 'host': 'aunewsonline', 'domain': 'com', 'issuffix': 0, 'iszone': 1, 'zone': 'aunewsonline.com'}, 'tagprops': defaultdict(<class 'dict'>, {}), 'nodedata': {}})}


.. NOTE::

  The value of ``$node`` is the entire node object and associated properties and tags, as opposed to a specific
  aspect of the node, such as its iden or primary property value.
  
  As demonstrated below, some node constructors can "intelligently" leverage the relevant aspects of the full
  node object (the value of the ``$node`` variable) when creating new nodes.

- Use the ``$node`` variable to create multiple whois name server records (``inet:whois:recns``) for the name
  server ``ns1.somedomain.com`` from a set of inbound whois record nodes for the domain ``woot.com``:

::

    storm> inet:whois:rec:fqdn=woot.com [ inet:whois:recns=(ns1.somedomain.com,$node) ]
    inet:whois:recns=('ns1.somedomain.com', ('woot.com', '2019/06/13 00:00:00.000'))
            :ns = ns1.somedomain.com
            :rec = ('woot.com', '2019/06/13 00:00:00.000')
            :rec:asof = 2019/06/13 00:00:00.000
            :rec:fqdn = woot.com
            .created = 2023/10/05 21:47:34.817
    inet:whois:rec=('woot.com', '2019/06/13 00:00:00.000')
            :asof = 2019/06/13 00:00:00.000
            :fqdn = woot.com
            :text = ns1.somedomain.com
            .created = 2023/10/05 21:47:34.778
    inet:whois:recns=('ns1.somedomain.com', ('woot.com', '2019/09/12 00:00:00.000'))
            :ns = ns1.somedomain.com
            :rec = ('woot.com', '2019/09/12 00:00:00.000')
            :rec:asof = 2019/09/12 00:00:00.000
            :rec:fqdn = woot.com
            .created = 2023/10/05 21:47:34.823
    inet:whois:rec=('woot.com', '2019/09/12 00:00:00.000')
            :asof = 2019/09/12 00:00:00.000
            :fqdn = woot.com
            :text = ns1.somedomain.com
            .created = 2023/10/05 21:47:34.781


In the example above, the :ref:`meth-node-value` method could have been used instead of ``$node`` to create
the ``inet:whois:recns`` nodes. In this case, the node constructor knows to use the primary property value
from the ``inet:whois:rec`` nodes to create the ``inet:whois:recns`` nodes.

.. _meth-node-form:

$node.form()
++++++++++++

The ``$node.form()`` method returns the **form** of the current node in the Storm pipeline.

The method takes no arguments.

**Examples**

- Print the form of an ``inet:dns:a`` node:


::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.form()) | spin
    inet:dns:a

    

.. _meth-node-globtags:

$node.globtags()
++++++++++++++++

The ``$node.globtags()`` method returns a **list of string matches from the set of tags applied to the current node**
in the Storm pipeline.

The method takes a single argument consisting of a wildcard expression for the substring to match.
      
- The argument requires at least one wildcard ( ``*`` ) representing the substring(s) to match.
- The method performs an **exclusive match** and returns **only** the matched substring(s), not the entire
  tag containing the substring match.
- The wildcard ( ``*`` ) character can be used to match full or partial tag elements.
- Single wildcards are constrained by tag element boundaries (i.e., the dot ( ``.`` ) character). Single
  wildcards can match an entire tag element or a partial string within an element.
- The double wildcard ( ``**`` ) can be used to match across any number of tag elements; that is, the
  double wildcard is not constrained by the dot boundary.
- If the string expression starts with a wildcard, it must be enclosed in quotes in accordance with the
  use of :ref:`storm-literals`.

See :ref:`meth-node-tags` to access full tags (vs. tag substrings).

**Examples**

- Print the set of top-level (root) tags from any tags applied to the current node:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags("*")) | spin
    ['cno', 'rep']



- Print the list of numbers associated with any threat group tags (e.g., such as ``cno.threat.t42.own``
  or ``cno.threat.t127.use``) applied to the current node:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags(cno.threat.t*)) | spin
    ['83']


In the example above, ``$node.globtags()`` returns the matching substring only ("83"), which is the
portion matching the wildcard; it does not return the "t" character.


- Print the list of organizations and associated names (e.g., threat group or malware family names) from
  any third-party ("rep") tags applied to the current node:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags(rep.*.*)) | spin
    [('crowdstrike', 'commentpanda'), ('mandiant', 'apt1'), ('mcafee', 'commentcrew'), ('symantec', 'commentcrew')]



- Print all sub-tags for any tags starting with "foo" applied to the current node:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.globtags(foo.**)) | spin
    ['bar', 'bar.baz', 'derp']

    

.. _meth-node-iden:

$node.iden()
++++++++++++

The ``$node.iden()`` method returns the :ref:`gloss-iden` of the current node in the Storm pipeline.

The method takes no arguments.

**Examples**

- Print the iden of an ``inet:dns:a`` node:


::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.iden()) | spin
    01235b5877954084e798f09ba3fd3f1cda2e7b41d79b752b80acbed1b609cbaa

    

.. _meth-node-isform:

$node.isform()
++++++++++++++

The ``$node.isform()`` method returns a Boolean value (true / false) for whether the current node in the Storm pipeline is of a specified form.

The method takes a single argument of a form name.

**Examples**

- Print the Boolean value for whether a node is an ``inet:dns:a`` form:


::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.isform(inet:dns:a)) | spin
    true



- Print the Boolean value for whether a node is an ``inet:fqdn`` form:


::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.isform(inet:fqdn))  | spin
    false

    

.. _meth-node-ndef:

$node.ndef()
++++++++++++

The ``$node.ndef()`` method returns the :ref:`gloss-ndef` ("node definition") of the current node in the Storm pipeline.

The method takes no arguments.

**Examples**

- Print the ndef of an ``inet:dns:a`` node:


::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.ndef()) | spin
    ('inet:dns:a', ('woot.com', 917309932))


.. _meth-node-repr:

$node.repr()
++++++++++++

The ``$node.repr()`` method returns the human-friendly :ref:`gloss-repr` ("representation") of the specified property of the current node in the Storm pipeline (as opposed to the raw value stored by Synapse).

The method can optionally take one argument.

- If no arguments are provided, the method returns the repr of the node's primary property value.
- If an argument is provided, it should be the string of the secondary property name (i.e., without the leading colon ( ``:`` ) from relative property syntax).
- If a universal property string is provided, it must be preceded by the dot / period ( ``.`` ) and enclosed in quotes in accordance with the use of :ref:`storm-literals`.

See :ref:`meth-node-value` to return the raw value of a property.

**Examples**

- Print the repr of the primary property value of an ``inet:dns:a`` node:

::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.repr())  | spin
    ('woot.com', '54.173.9.236')



- Print the repr of the ``:ipv4`` secondary property value of an ``inet:dns:a`` node:

::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.repr(ipv4)) | spin
    54.173.9.236



- Print the repr of the ``.seen`` universal property value of an ``inet:dns:a`` node:

::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.repr(".seen")) | spin
    ('2016/12/28 20:46:31.000', '2016/12/28 20:46:31.001')

    

.. _meth-node-tags:

$node.tags()
++++++++++++

The ``$node.tags()`` method returns a **list of the tags applied to the current node** in the Storm pipeline.

The method can optionally take one argument.

- If no arguments are provided, the method returns the full list of all tags applied to the node.
- An optional argument consisting of a wildcard string expression can be used to match a subset of tags.
  
  - If a string is used with no wildcards, the string must be an exact match for the tag element.
  - The wildcard ( ``*`` ) character can be used to match full or partial tag elements.
  - The method performs an **inclusive match** and returns the full tag for all tags that match the
    provided expression.
  - Single wildcards are constrained by tag element boundaries (i.e., the dot ( ``.`` ) character).
    Single wildcards can match an entire tag element or a partial string within an element.
  - The double wildcard ( ``**`` ) can be used to match across any number of tag elements; that is,
    the double wildcard is not constrained by the dot boundary.
  - If the string expression starts with a wildcard, it must be enclosed in quotes in accordance with
    the use of :ref:`storm-literals`.

See :ref:`meth-node-globtags` to access tag substrings (vs. full tags).

**Examples**

- Print the list of all tags associated with an ``inet:fqdn`` node:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.tags()) | spin
    ['cno', 'cno.infra', 'cno.infra.dns', 'cno.infra.dns.sink', 'cno.infra.dns.sink.hole', 'cno.infra.dns.sink.hole.kleissner', 'cno.threat', 'cno.threat.t83', 'cno.threat.t83.own', 'faz', 'faz.baz', 'foo', 'foo.bar', 'foo.bar.baz', 'foo.derp', 'rep', 'rep.crowdstrike', 'rep.crowdstrike.commentpanda', 'rep.mandiant', 'rep.mandiant.apt1', 'rep.mcafee', 'rep.mcafee.commentcrew', 'rep.symantec', 'rep.symantec.commentcrew']



- Print the tag that exactly matches the string "cno" if present on an ``inet:fqdn`` node:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(cno)) | spin
    ['cno']



- Print the list of all tags two elements in length that start with "foo":

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(foo.*)) | spin
    ['foo.bar', 'foo.derp']

    

- Print the list of all tags of any length that start with "f":

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(f**)) | spin
    ['faz', 'faz.baz', 'foo', 'foo.bar', 'foo.bar.baz', 'foo.derp']



- Print the list of all tags of any length whose first element is "rep" and whose third element
  starts with "comment":

::

    storm> inet:fqdn=aunewsonline.com $lib.print($node.tags(rep.*.comment*)) | spin
    ['rep.crowdstrike.commentpanda', 'rep.mcafee.commentcrew', 'rep.symantec.commentcrew']

    

.. _meth-node-value:

$node.value()
+++++++++++++

The ``$node.value()`` method returns the raw value of the primary property of the current node in the Storm pipeline.

The method takes no arguments.

See :ref:`meth-node-repr` to return the human-friendly value of a property.

.. NOTE::

  The ``$node.value()`` method is only used to return the primary property value of a node. Secondary
  property values can be accessed via a user-defined variable (i.e., ``$myvar = :<prop>``).

**Examples**

- Print the value of the primary property value of an ``inet:dns:a`` node:

::

    storm> inet:dns:a=(woot.com,54.173.9.236) $lib.print($node.value()) | spin
    ('woot.com', 917309932)

    

.. _meth-path:

$path
-----

:ref:`vars-node-path` is a built-in Storm variable that **references the path of a node as it travels through the pipeline of a Storm query.**

The ``$path`` variable is generally not used on its own, but in conjunction with its methods. See the
:ref:`stormprims-node-path-f527` section of the :ref:`stormtypes-prim-header` technical documentation
for a full list.

.. _meth-path-idens:

$path.idens()
+++++++++++++

The ``$path.idens()`` method returns the list of idens (:ref:`gloss-iden`) of each node in a node's path
through a Storm query.

The method takes no arguments.

**Examples**

- Print the list of iden(s) for the path of a single lifted node:

::

    storm> inet:fqdn=aunewsonline.com $lib.print($path.idens()) | spin
    ['53aa7a2f7125392302c36247b97569dd84a7f3fe9e92eb99abd984349dc53fe4']

    
.. NOTE::

  A lift operation contains no pivots (i.e., no "path"), so the method returns only the iden of the lifted node.


- Print the list of idens for the path of a single node through two pivots to a single end node:

::

    storm> inet:fqdn=aunewsonline.com -> inet:dns:a +:ipv4=67.215.66.149 -> inet:ipv4 $lib.print($path.idens())
    ['53aa7a2f7125392302c36247b97569dd84a7f3fe9e92eb99abd984349dc53fe4', '07c79039d00b4391699c9328dc6ccaf864d84d0b38545ded117d1d7ccc6e366c', '9596f5253f25ee74689157706ddf3b459874a6d3cb0adfce4e07018ec8162fc1']
    inet:ipv4=67.215.66.149
            :type = unicast
            .created = 2023/10/05 21:47:35.105

    
The example above returns the idens of the original ``inet:fqdn`` node, the ``inet:dns:a`` node with the
specified IP, and the ``inet:ipv4`` node.


- Print the list of idens for the path of a single node through two pivots to three different end nodes
  (i.e., three paths):

::

    storm> inet:fqdn=aunewsonline.com -> inet:dns:a -> inet:ipv4 $lib.print($path.idens())
    ['53aa7a2f7125392302c36247b97569dd84a7f3fe9e92eb99abd984349dc53fe4', '07c79039d00b4391699c9328dc6ccaf864d84d0b38545ded117d1d7ccc6e366c', '9596f5253f25ee74689157706ddf3b459874a6d3cb0adfce4e07018ec8162fc1']
    inet:ipv4=67.215.66.149
            :type = unicast
            .created = 2023/10/05 21:47:35.105
    ['53aa7a2f7125392302c36247b97569dd84a7f3fe9e92eb99abd984349dc53fe4', '0dde48198d3bcc58b40ab82155b218ecd48b533b964d5d2fa3e7453d990541f5', '5af9ae36456988c24edecafa739da75231c067ba3d104a2746e9616ea7a312d6']
    inet:ipv4=184.168.221.92
            :type = unicast
            .created = 2023/10/05 21:47:35.109
    ['53aa7a2f7125392302c36247b97569dd84a7f3fe9e92eb99abd984349dc53fe4', '1c53655a7f3bc67be338cde70d6565d4bc84d343d37513679d4efcd0ec59d3fe', 'acecd1f87d1dfc31148bf0ed417b69fde1c77eb2e7effdea434765fe8b759351']
    inet:ipv4=104.239.213.7
            :type = unicast
            .created = 2023/10/05 21:47:35.112


In the example above, the FQDN has three DNS A records, thus there are three different paths that the
original node takes through the query.


.. _subqueries: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_subquery.html
.. _subquery filters: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_ref_filter.html#subquery-filters
.. _control flow: https://synapse.docs.vertex.link/en/latest/synapse/userguides/storm_adv_control.html