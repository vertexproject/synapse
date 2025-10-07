

.. _userguide_model_v2_224_0:

######################
v2.224.0 Model Updates
######################

The following model updates were made during the ``v2.224.0`` Synapse release.

**************
New Properties
**************

``inet:service:platform``
  The form had the following properties added to it:


  ``creator``
    The service account which created the platform.


  ``id``
    An ID which identifies the platform.


  ``parent``
    A parent platform which owns this platform.


  ``period``
    The period when the platform existed.


  ``remover``
    The service account which removed or decommissioned the platform.


  ``status``
    The status of the platform.


  ``zone``
    The primary zone for the platform.


  ``zones``
    An array of alternate zones for the platform.


``proj:comment``
  The form had the following property added to it:

  ``ext:creator``
    The contact information of the creator from an external system.


``risk:alert``
  The form had the following property added to it:

  ``updated``
    The time the alert was most recently modified.


``syn:cmd``
  The form had the following properties added to it:


  ``deprecated``
    Set to true if this command is scheduled to be removed.


  ``deprecated:date``
    The date when this command will be removed.


  ``deprecated:mesg``
    Optional description of this deprecation.


  ``deprecated:version``
    The Synapse version when this command will be removed.



***********
Light Edges
***********

``about``
    When used with a ``risk:alert`` node, the edge indicates the alert is about
    the target node.

