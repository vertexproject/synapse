
.. _userguide_model_v2_154_0:

######################
v2.156.0 Model Updates
######################

The following model updates were made during the ``v2.156.0`` Synapse release.

*********
New Forms
*********

``ou:requirement``
  A specific requirement.

``risk:leak``
  An event where information was disclosed without permission.

``risk:leak:type:taxonomy``
  A taxonomy of leak event types

``risk:extortion``
  An event where an attacker attempted to extort a victim.

``risk:extortion:type:taxonomy``
  A taxonomy of extortion event types.

**************
New Properties
**************

``ou:org``
  The form had the following property added to it:

  ``tag``
    A base tag used to encode assessments made by the organization.

``risk:compromise``
  The form had the following properties added to it:

  ``ext:id``
    An external unique ID for the compromise.

  ``url``
    A URL which documents the compromise.

``risk:alert``
  The form had the following property added to it:

  ``host``
    The host which generated the alert.

*************
Updated Types
*************

``inet:ipv4``
  RFC6598 addresses now have a ``:type`` property value of ``shared``.

``inet:url``
  Accept Microsoft URLPrefix strings with a strong wildcard host value.

  Add a check to prevent creating ``inet:url`` nodes with an empty host
  and path part, such as ``inet:url=file://''``.

***********
Light Edges
***********

``leaked``
  When used with a ``risk:leak`` node, the edge indicates the leak included
  the disclosure of the target node.

``leveraged``
  When used with a ``risk:extortion`` node, the edge indicates the extortion
  event was based on attacker access to the target node.

``meets``
  When used with a ``ou:requirement`` node, the edge indicates the
  requirement was met by the source node.
