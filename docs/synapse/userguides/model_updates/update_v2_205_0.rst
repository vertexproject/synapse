

.. _userguide_model_v2_205_0:

######################
v2.205.0 Model Updates
######################

The following model updates were made during the ``v2.205.0`` Synapse release.

*********
New Forms
*********

``tel:phone:type:taxonomy``
  A taxonomy of phone number types.



**************
New Properties
**************

``econ:acct:balance``
  The form had the following property added to it:

  ``instrument``
    The financial instrument holding the balance.


``tel:phone``
  The form had the following property added to it:

  ``type``
    The type of phone number.



***********
Light Edges
***********

``targets``
    When used with a ``risk:compromise`` and an ``ou:industry`` node, the edge
    indicates the compromise was assessed to be based on the victim's role in
    the industry.


``uses``
    When used with an ``it:prod:soft`` and a ``risk:vuln`` node, the edge
    indicates the software uses the vulnerability.



*********************
Deprecated Properties
*********************

``econ:acct:balance``
  The form had the following properties deprecated:


  ``crypto:address``
    Deprecated. Please use ``:instrument``.


  ``pay:card``
    Deprecated. Please use ``:instrument``.

