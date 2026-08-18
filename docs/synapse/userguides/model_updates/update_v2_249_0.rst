

.. _userguide_model_v2_249_0:

######################
v2.249.0 Model Updates
######################

The following model updates were made during the ``v2.249.0`` Synapse release.

*********
New Forms
*********

``it:app:suricata:matched``
  An instance of a suricata rule hit.


``it:app:suricata:rule``
  A suricata rule.



**************
New Properties
**************

``it:cmd:history``
  The form had the following property added to it:

  ``output``
    The output of the command.



*************
Updated Types
*************

``hash:ssdeep``
  Allow the type to accept empty hash segments, such as the
  empty-file hash ``3::``.



***********
Light Edges
***********

``detects``
    When used with a ``it:app:suricata:rule`` node, the edge indicates the
    suricata rule is intended for use in detecting the target node.

