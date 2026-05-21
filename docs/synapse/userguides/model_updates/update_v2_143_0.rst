
.. _userguide_model_v2_143_0:

######################
v2.143.0 Model Updates
######################

The following model updates were made during the ``v2.143.0`` Synapse release.

*************
Updated Types
*************

``hex``
  The ``zeropad`` option has been changed from a ``bool`` to an ``int``.
  It may now be used to specify the zero extended length of the hex string.

******************
Updated Properties
******************

``crypto:x509:cert``
  The form had the following properties updated on it:

  ``serial``
    The ``size`` value has been changed to ``zeropad`` to zeropad values
    with less than 40 octets, and to allow storing large serial numbers from
    malformed certificates.
