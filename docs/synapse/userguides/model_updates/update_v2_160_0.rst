
.. _userguide_model_v2_160_0:

######################
v2.160.0 Model Updates
######################

The following model updates were made during the ``v2.160.0`` Synapse release.

**************
New Properties
**************

``risk:vuln``
  The form had the following properties added to it:

  ``severity``
    The severity of the vulnerability.

  ``priority``
    The priority of the vulnerability.

``inet:ipv6``
  The form had the following properties added to it:

  ``type``
    The type of IP address (e.g., private, multicast, etc.).

  ``scope``
    The IPv6 scope of the address (e.g., global, link-local, etc.).

*************
Updated Types
*************

``it:exec:proc``
  This now inherits the ``it:host:activity`` interface.

``it:exec:thread``
  This now inherits the ``it:host:activity`` interface.

``it:exec:loadlib``
  This now inherits the ``it:host:activity`` interface.

``it:exec:mmap``
  This now inherits the ``it:host:activity`` interface.

``it:exec:mutex``
  This now inherits the ``it:host:activity`` interface.

``it:exec:pipe``
  This now inherits the ``it:host:activity`` interface.

``it:exec:url``
  This now inherits the ``it:host:activity`` interface.

``it:exec:bind``
  This now inherits the ``it:host:activity`` interface.

``it:exec:file:add``
  This now inherits the ``it:host:activity`` interface.

``it:exec:file:read``
  This now inherits the ``it:host:activity`` interface.

``it:exec:file:write``
  This now inherits the ``it:host:activity`` interface.

``it:exec:file:del``
  This now inherits the ``it:host:activity`` interface.

``it:exec:reg:get``
  This now inherits the ``it:host:activity`` interface.

``it:exec:reg:set``
  This now inherits the ``it:host:activity`` interface.

``it:exec:reg:del``
  This now inherits the ``it:host:activity`` interface.
