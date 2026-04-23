

.. _userguide_model_v2_240_0:

######################
v2.240.0 Model Updates
######################

The following model updates were made during the ``v2.240.0`` Synapse release.

*********
New Forms
*********

``hash:ssdeep``
  A fuzzy hash of a file in ssdeep format.


``crypto:currency:chain``
  A crypto currency chain.


``meta:rule:status:taxonomy``
  A taxonomy for rule status values.



**************
New Properties
**************

``crypto:currency:address``
  The form had the following property added to it:

  ``chain``
    The chain where the address is defined.


``crypto:payment:input``
  The form had the following property added to it:

  ``index``
    The index of this input in the array of inputs for the transaction.


``crypto:payment:output``
  The form had the following property added to it:

  ``index``
    The index of this output in the array of outputs for the transaction.


``file:bytes``
  The form had the following property added to it:

  ``ssdeeps``
    The ssdeep fuzzy hashes of the file.


``meta:rule``
  The form had the following property added to it:

  ``status``
    The status of the rule.


``pol:candidate``
  The form had the following property added to it:

  ``votes``
    The total number of votes received by the candidate.

