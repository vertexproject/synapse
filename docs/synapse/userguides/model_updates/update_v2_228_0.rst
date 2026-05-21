

.. _userguide_model_v2_228_0:

######################
v2.228.0 Model Updates
######################

The following model updates were made during the ``v2.228.0`` Synapse release.

**************
New Properties
**************

``entity:relationship``
  The form had the following properties added to it:


  ``reporter``
    The organization reporting on the relationship.


  ``reporter:name``
    The name of the organization reporting on the relationship.


``media:news``
  The form had the following property added to it:

  ``version``
    The version of the news item.



***********
Light Edges
***********

``decrypts``
    When used with a ``crypto:key`` and a ``file:bytes`` node, the edge
    indicates the key is used to decrypt the file.

