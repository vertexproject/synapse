
.. _userguide_model_v2_142_0:

######################
v2.142.0 Model Updates
######################

The following model updates were made during the ``v2.142.0`` Synapse release.

*********
New Forms
*********

``risk:vulnname``
  Add a form to capture vulnerability name such as log4j or rowhammer.

**************
New Properties
**************

``it:sec:c2:config``
  The form had the following properties added to it:

  ``decoys``
    An array of URLs used as decoy connections to obfuscate the C2 servers.

``ou:technique``
  The form had the following properties added to it:

  ``reporter``
    The organization reporting on the technique.

  ``reporter:name``
    The name of the organization reporting on the technique.

``risk:vuln``
  The form had the following properties added to it:

  ``names``
    An array of alternate names for the vulnerability.

*************
Updated Types
*************

``hex``
  The ``hex`` base type now accepts a ``zeropad`` option that can be used
  to zero-extend a hex string during normalization.

``cvss:v2``
  The type now accepts and normalizes unordered CVSS vectors.

``cvss:v3``
  The type now accepts and normalizes unordered CVSS vectors.
