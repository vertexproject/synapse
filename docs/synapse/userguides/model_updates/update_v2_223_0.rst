

.. _userguide_model_v2_223_0:

######################
v2.223.0 Model Updates
######################

The following model updates were made during the ``v2.223.0`` Synapse release.

*************
Updated Types
*************

``pe:langid``
  The type has been modified to set ``enums:strict`` to ``False``. The type
  now allows any integer in the range from `0` to `65535`.
