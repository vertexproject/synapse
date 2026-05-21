

.. _userguide_model_v2_180_0:

######################
v2.180.0 Model Updates
######################

The following model updates were made during the ``v2.180.0`` Synapse release.

**************
New Properties
**************

``auth:creds``
  The form had the following property added to it:

  ``service:account``
    The service account that the credentials allow access to.


``inet:search:query``
  The form had the following properties added to it:


  ``account``
    The account which initiated the action.


  ``client``
    The network address of the client which initiated the action.


  ``client:host``
    The client host which initiated the action.


  ``error:code``
    The platform specific error code if the action was unsuccessful.


  ``error:reason``
    The platform specific friendly error reason if the action was unsuccessful.


  ``id``
    A platform specific ID.


  ``instance``
    The platform instance which defines the node.


  ``platform``
    The platform which defines the node.


  ``rule``
    The rule which allowed or denied the action.


  ``server``
    The network address of the server which handled the action.


  ``server:host``
    The server host which handled the action.


  ``session``
    The session which initiated the action.


  ``success``
    Set to true if the action was successful.


``it:dev:repo``
  The form had the following properties added to it:


  ``creator``
    The service account which created the object.


  ``id``
    A platform specific ID.


  ``instance``
    The platform instance which defines the node.


  ``period``
    The period when the object existed.


  ``platform``
    The platform which defines the node.


  ``remover``
    The service account which removed or decommissioned the object.


  ``status``
    The status of this object.


``it:dev:repo:branch``
  The form had the following properties added to it:


  ``creator``
    The service account which created the object.


  ``id``
    A platform specific ID.


  ``instance``
    The platform instance which defines the node.


  ``period``
    The period when the object existed.


  ``platform``
    The platform which defines the node.


  ``remover``
    The service account which removed or decommissioned the object.


  ``status``
    The status of this object.


``it:dev:repo:commit``
  The form had the following properties added to it:


  ``creator``
    The service account which created the object.


  ``instance``
    The platform instance which defines the node.


  ``period``
    The period when the object existed.


  ``platform``
    The platform which defines the node.


  ``remover``
    The service account which removed or decommissioned the object.


  ``status``
    The status of this object.


``it:dev:repo:diff:comment``
  The form had the following properties added to it:


  ``creator``
    The service account which created the object.


  ``id``
    A platform specific ID.


  ``instance``
    The platform instance which defines the node.


  ``period``
    The period when the object existed.


  ``platform``
    The platform which defines the node.


  ``remover``
    The service account which removed or decommissioned the object.


  ``status``
    The status of this object.


``it:dev:repo:issue``
  The form had the following properties added to it:


  ``creator``
    The service account which created the object.


  ``instance``
    The platform instance which defines the node.


  ``period``
    The period when the object existed.


  ``platform``
    The platform which defines the node.


  ``remover``
    The service account which removed or decommissioned the object.


  ``status``
    The status of this object.


``it:dev:repo:issue:comment``
  The form had the following properties added to it:


  ``creator``
    The service account which created the object.


  ``id``
    A platform specific ID.


  ``instance``
    The platform instance which defines the node.


  ``period``
    The period when the object existed.


  ``platform``
    The platform which defines the node.


  ``remover``
    The service account which removed or decommissioned the object.


  ``status``
    The status of this object.


``it:dev:repo:issue:label``
  The form had the following properties added to it:


  ``creator``
    The service account which created the object.


  ``id``
    A platform specific ID.


  ``instance``
    The platform instance which defines the node.


  ``period``
    The period when the object existed.


  ``platform``
    The platform which defines the node.


  ``remover``
    The service account which removed or decommissioned the object.


  ``status``
    The status of this object.


``pol:candidate``
  The form had the following property added to it:

  ``id``
    A unique ID for the candidate issued by an election authority.


``ps:contact``
  The form had the following property added to it:

  ``service:accounts``
    The service accounts associated with this contact.


``tel:mob:telem``
  The form had the following property added to it:

  ``account``
    The service account which is associated with the tracked device.



*************
Updated Types
*************

``inet:search:query``
  The type now inherits from the ``inet:service:action`` interface.


``it:dev:repo``
  The type now inherits from the ``inet:service:object`` interface.


``it:dev:repo:branch``
  The type now inherits from the ``inet:service:object`` interface.


``it:dev:repo:commit``
  The type now inherits from the ``inet:service:object`` interface.


``it:dev:repo:diff:comment``
  The type now inherits from the ``inet:service:object`` interface.


``it:dev:repo:issue``
  The type now inherits from the ``inet:service:object`` interface.


``it:dev:repo:issue:comment``
  The type now inherits from the ``inet:service:object`` interface.


``it:dev:repo:issue:label``
  The type now inherits from the ``inet:service:object`` interface.


******************
Updated Properties
******************

``it:dev:repo:commit``
  The form had the following property updated:

    The property ``id`` has been modified to strip trailing and leading whitespace.


*********************
Deprecated Properties
*********************

``it:dev:repo``
  The form had the following property deprecated:

  ``created``
    Deprecated. Please use ``:period``.


``it:dev:repo:branch``
  The form had the following properties deprecated:


  ``created``
    Deprecated. Please use ``:period``.


  ``deleted``
    Deprecated. Please use ``:period``.


``it:dev:repo:commit``
  The form had the following property deprecated:

  ``created``
    Deprecated. Please use ``:period``.


``it:dev:repo:diff:comment``
  The form had the following property deprecated:

  ``created``
    Deprecated. Please use ``:period``.


``it:dev:repo:issue``
  The form had the following property deprecated:

  ``created``
    Deprecated. Please use ``:period``.


``it:dev:repo:issue:comment``
  The form had the following property deprecated:

  ``created``
    Deprecated. Please use ``:period``.


``it:dev:repo:issue:label``
  The form had the following properties deprecated:


  ``applied``
    Deprecated. Please use ``:period``.


  ``removed``
    Deprecated. Please use ``:period``.

