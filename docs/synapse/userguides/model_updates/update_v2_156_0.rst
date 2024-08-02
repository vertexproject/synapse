
.. _userguide_model_v2_156_0:

######################
v2.156.0 Model Updates
######################

The following model updates were made during the ``v2.156.0`` Synapse release.

**************
New Properties
**************

``it:av:scan:result``
  The form had the following properties added to it:

    ``target:ipv4``
      The IPv4 address that was scanned to produce the result.

    ``target:ipv6``
      The IPv6 address that was scanned to produce the result.

``ou:campaign``
  The form had the following property added to it:

  ``mitre:attack:campaign``
    A mapping to a Mitre ATT&CK campaign if applicable.

``risk:vuln``
  The form had the following property added to it:

  ``id``
    An identifier for the vulnerability.

*********
New Forms
*********

``it:mitre:attack:campaign``
  A Mitre ATT&CK Campaign ID.

``risk:technique:masquerade``
  Represents the assessment that a node is designed to resemble another
  in order to mislead.

*************
Updated Types
*************

``it:os:windows:sid``
  The regular expression used to validate the SID has been updated
  to allow modeling well-known SID values.
