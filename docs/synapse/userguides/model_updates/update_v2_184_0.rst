

.. _userguide_model_v2_184_0:

######################
v2.184.0 Model Updates
######################

The following model updates were made during the ``v2.184.0`` Synapse release.

*********
New Forms
*********

``ou:asset``
  A node for tracking assets which belong to an organization.

``ou:asset:status:taxonomy``
  An asset status taxonomy.

``ou:asset:type:taxonomy``
  An asset type taxonomy.

``ou:requirement:type:taxonomy``
  A taxonomy of requirement types.

``risk:mitigation:type:taxonomy``
  A taxonomy of mitigation types.


**************
New Properties
**************

``it:app:snort:hit``
  The form had the following property added to it:

  ``dropped``
    Set to true if the network traffic was dropped due to the match.


``ou:requirement``
  The form had the following property added to it:

  ``type``
    The type of requirement.


``ou:vitals``
  The form had the following property added to it:

  ``budget``
    The budget allocated for the period.


``risk:mitigation``
  The form had the following property added to it:

  ``type``
    A taxonomy type entry for the mitigation.



***********
Light Edges
***********

``uses``
    When used with a ``risk:mitigation`` and an ``inet:service:rule`` node, the
    edge indicates the mitigation uses the service rule.

    When used with a ``risk:mitigation`` and an ``meta:rule`` node, the edge
    indicates the mitigation uses the rule.

    When used with a ``risk:mitigation`` and an ``it:app:yara:rule`` node, the
    edge indicates the mitigation uses the YARA rule.

    When used with a ``risk:mitigation`` and an ``it:app:snort:rule`` node, the
    edge indicates the mitigation uses the Snort rule.

