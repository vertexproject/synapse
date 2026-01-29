.. _userguide_model_v2_137_0:

######################
v2.137.0 Model Updates
######################

The following model updates were made during the ``v2.137.0`` Synapse release.


*********
New Types
*********

``it:mitre:attack:matrix``
  Add a type to capture the enumeration of MITRE ATT&CK matrix values.

*********
New Forms
*********

``inet:egress``
  Add a form to capture a host using a specific network egress client
  address.

``it:prod:softreg``
  Add a form to capture a registry entry is created by a specific software
  version.

``transport:land:vehicle``
  Add a form to capture an individual vehicle.

``transport:land:registration``
  Add a form to capture the registration issued to a contact for a land
  vehicle.

``transport:land:license``
  Add a form to capture the license to operate a land vehicle issued to a
  contact.

**************
New Properties
**************

``inet:http:request``
  The form had the following property added to it:

  ``referer``
    The referer URL parsed from the "Referer:" header in the request.

``inet:search:query``
  The form had the following property added to it:

  ``request``
    The HTTP request used to issue the query.

``it:mitre:attack:tactic``
  The form had the following property added to it:

  ``matrix``
    The ATT&CK matrix which defines the tactic.

``it:mitre:attack:technique``
  The form had the following property added to it:

  ``matrix``
    The ATT&CK matrix which defines the technique.

``it:mitre:attack:mitigation``
  The form had the following property added to it:

  ``matrix``
    The ATT&CK matrix which defines the mitigation.

``it:app:snort:rule``
  The form had the following property added to it:

  ``engine``
    The snort engine ID which can parse and evaluate the rule text.

``it:app:yara:rule``
  The form had the following properties added to it:

  ``ext:id``
    The YARA rule ID from an external system.

  ``url``
    A URL which documents the YARA rule.

``ou:campaign``
  The form had the following property added to it:

  ``tag``
    The tag used to annotate nodes that are associated with the campaign.

``ou:org``
  The form had the following properties added to it:

    ``country``
      The organization's country of origin.

    ``country:code``
      The 2 digit ISO 3166 country code for the organization's country of
      origin.

``risk:threat``
  The form had the following properties added to it:

    ``country``
      The reporting organization's assessed country of origin of the threat
      cluster.

    ``country:code``
      The 2 digit ISO 3166 country code for the threat cluster's assessed
      country of origin.

``risk:compromise``
  The form had the following property added to it:

  ``vector``
    The attack assessed to be the initial compromise vector.

***********
Light Edges
***********

``detects``
  When used with a ``meta:rule`` node, the edge indicates the rule was
  designed to detect instances of the target node.

  When used with an ``it:app:snort:rule`` node, the edge indicates the rule
  was designed to detect instances of the target node.

  When used with an ``it:app:yara:rule`` node, the edge indicates the rule
  was designed to detect instances of the target node.

``contains``
  When used between two ``geo:place`` nodes, the edge indicates the source
  place completely contains the target place.

*********************
Deprecated Properties
*********************

``geo:place``
  The form had the following property marked as deprecated:

  * ``parent``
