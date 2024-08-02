

.. _userguide_model_v2_167_0:

######################
v2.167.0 Model Updates
######################

The following model updates were made during the ``v2.167.0`` Synapse release.

*************
Updated Types
*************

``file:path``
  Normalizing paths such as ``../.././..`` previously failed. This now
  produces an empty path.

****************
Deprecated Types
****************

The following types have been marked as deprecated:

* ``edge``
* ``timeedge``

****************
Deprecated Forms
****************

The following forms have been marked as deprecated:

* ``graph:cluster``
* ``graph:node``
* ``graph:event``
* ``edge:refs``
* ``edge:has``
* ``edge:wentto``
* ``graph:edge``
* ``graph:timeedge``
