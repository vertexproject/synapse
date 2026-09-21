

.. _userguide_model_v2_252_0:

######################
v2.252.0 Model Updates
######################

The following model updates were made during the ``v2.252.0`` Synapse release.

*********
New Forms
*********

``it:os:windows:task``
  A Windows Scheduled Task entry.


``it:app:sigma:rule``
  A Sigma rule.


``it:app:sigma:matched``
  An instance of a Sigma rule hit.



***********
Light Edges
***********

``detects``
    When used with a ``it:app:sigma:rule`` node, the edge indicates the Sigma
    rule is intended for use in detecting the target node.

