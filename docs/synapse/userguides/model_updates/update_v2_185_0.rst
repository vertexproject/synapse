

.. _userguide_model_v2_185_0:

######################
v2.185.0 Model Updates
######################

The following model updates were made during the ``v2.185.0`` Synapse release.

**************
New Interfaces
**************

``doc:document``
  A common interface for documents.


``proj:task``
  A common interface for tasks.



*********
New Forms
*********

``ou:enacted:status:taxonomy``
  A taxonomy of enacted statuses.


``doc:policy``
  Guiding principles used to reach a set of goals.


``doc:policy:type:taxonomy``
  A taxonomy of policy types.


``ou:enacted``
  An organization enacting a document.


``doc:standard``
  A group of requirements which define how to implement a policy or goal.


``doc:standard:type:taxonomy``
  A taxonomy of standard types.



**************
New Properties
**************

``proj:ticket``
  The form had the following properties added to it:


  ``completed``
    The time the ticket was completed.


  ``due``
    The time the ticket must be complete.


  ``id``
    The ID of the ticket.



*************
Updated Types
*************

``proj:ticket``
  The type interface has been modified from None to ['proj:task'].


``syn:role``
  The type has been modified from {'strip': True} to {}.


``syn:user``
  The type has been modified from {'strip': True} to {}.



******************
Updated Properties
******************

``proj:ticket``
  The form had the following properties updated:


    The property ``priority`` has been modified from ['int', {'enums': [[0,
    'none'], [10, 'lowest'], [20, 'low'], [30, 'medium'], [40, 'high'], [50,
    'highest']]}] to ['meta:priority', {}].


    The property ``updated`` has been modified from ['time', {'ismax': True}]
    to ['time', {}].



*********************
Deprecated Properties
*********************

``proj:ticket``
  The form had the following property deprecated:

  ``ext:id``
    Deprecated. Please use :id.

