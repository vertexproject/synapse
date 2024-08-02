.. _userguide_model_v2_140_0:

######################
v2.140.0 Model Updates
######################

The following model updates were made during the ``v2.140.0`` Synapse release.

*********
New Types
*********

``file:archive:entry``
  Add a type to capture an archive entry representing a file and metadata
  from within a parent archive file.

*************
Updated Types
*************

``time``
  Time values with precision beyond milliseconds are now truncated to
  millsecond values.

``hex``
  Hex types now have whitespace and colon ( ``:`` ) characters stripped
  from them when lifting and normalizing them.

``inet:ipv6``
  Add comparators for ``>=``, ``>``, ``<=``, ``<`` operations when lifting
  and filtering IPV6 values.

``ou:naics``
  Update the type to allow recording NIACS sector and subsector prefixes.
