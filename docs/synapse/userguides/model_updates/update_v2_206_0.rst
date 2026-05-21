

.. _userguide_model_v2_206_0:

######################
v2.206.0 Model Updates
######################

The following model updates were made during the ``v2.206.0`` Synapse release.

*********
New Forms
*********

``tel:mob:tadig``
  A Transferred Account Data Interchange Group number issued to a GSM carrier.



**************
New Properties
**************

``it:network``
  The form had the following property added to it:

  ``dns:resolvers``
    An array of DNS servers configured to resolve requests for hosts on the
    network.


``tel:mob:carrier``
  The form had the following property added to it:

  ``tadig``
    The TADIG code issued to the carrier.



***********
Light Edges
***********

``has``
    When used with a ``meta:ruleset`` and an ``it:app:yara:rule`` node, the
    edge indicates the meta:ruleset includes the it:app:yara:rule.


``has``
    When used with a ``meta:ruleset`` and an ``it:app:snort:rule`` node, the
    edge indicates the meta:ruleset includes the it:app:snort:rule.


``has``
    When used with a ``meta:ruleset`` and an ``inet:service:rule`` node, the
    edge indicates the meta:ruleset includes the inet:service:rule.

