.. _userguide_model_v2_133_0:

######################
v2.133.0 Model Updates
######################

The following model updates were made during the ``v2.133.0`` Synapse release.

**************
New Properties
**************

``risk:vuln``
  The ``risk:vuln`` form had the following properties added to it:

  ``cvss:v2``
      The CVSS v2 vector for the vulnerability.
  ``cvss:v2_0:score``
      The CVSS v2.0 overall score for the vulnerability.
  ``cvss:v2_0:score:base``
      The CVSS v2.0 base score for the vulnerability.
  ``cvss:v2_0:score:temporal``
      The CVSS v2.0 temporal score for the vulnerability.
  ``cvss:v2_0:score:environmental``
      The CVSS v2.0 environmental score for the vulnerability.
  ``cvss:v3``
      The CVSS v3 vector for the vulnerability.
  ``cvss:v3_0:score``
      The CVSS v3.0 overall score for the vulnerability.
  ``cvss:v3_0:score:base``
      The CVSS v3.0 base score for the vulnerability.
  ``cvss:v3_0:scare:temporal``
      The CVSS v3.0 temporal score for the vulnerability.
  ``cvss:v3_0:score:environmental``
      The CVSS v3.0 environmental score for the vulnerability.
  ``cvss:v3_1:score``
      The CVSS v3.1 overall score for the vulnerability.
  ``cvss:v3_1:score:base``
      The CVSS v3.1 base score for the vulnerability.
  ``cvss:v3_1:scare:temporal``
      The CVSS v3.1 temporal score for the vulnerability.
  ``cvss:v3_1:score:environmental``
      The CVSS v3.1 environmental score for the vulnerability.

*********************
Deprecated Properties
*********************

``risk:vuln``
  The ``risk:vuln`` form had the following properties marked as deprecated:

  * ``cvss:av``
  * ``cvss:ac``
  * ``cvss:pr``
  * ``cvss:ui``
  * ``cvss:s``
  * ``cvss:c``
  * ``cvss:i``
  * ``cvss:a``
  * ``cvss:e``
  * ``cvss:rl``
  * ``cvss:rc``
  * ``cvss:mav``
  * ``cvss:mac``
  * ``cvss:mpr``
  * ``cvss:mui``
  * ``cvss:ms``
  * ``cvss:mc``
  * ``cvss:mi``
  * ``cvss:ma``
  * ``cvss:cr``
  * ``cvss:ir``
  * ``cvss:ar``
  * ``cvss:score``
  * ``cvss:score:temporal``
  * ``cvss:score:environmental``
