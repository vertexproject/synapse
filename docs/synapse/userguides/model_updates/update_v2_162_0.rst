
.. _userguide_model_v2_162_0:

######################
v2.162.0 Model Updates
######################

The following model updates were made during the ``v2.162.0`` Synapse release.

**************
New Properties
**************

``inet:email:message``
  The form had the following properties added to it:

  ``received:from:ipv4``
    The sending SMTP server IPv4, potentially from the Received: header.

  ``received:from:ipv6``
    The sending SMTP server IPv6, potentially from the Received: header.

  ``received:from:fqdn``
    The sending server FQDN, potentially from the Received: header.

``ou:oid:type``
  The form had the following property added to it:

    ``url``
      The official URL of the issuer.

``proj:project``
  The form had the following property added to it:

    ``type``
      The project type.

``risk:alert``
  The form had the following properties added to it:

  ``status``
    The status of the alert.

  ``assignee``
    The Synapse user who is assigned to investigate the alert.

  ``ext:assignee``
    The alert assignee contact information from an external system.

``risk:mitigation``
  The form had the following properties added to it:

  ``reporter``
    The organization reporting on the mitigation.

  ``reporter:name``
    The name of the organization reporting on the mitigation.

  ``tag``
    The tag used to annotate nodes which have the mitigation in place.

*********
New Forms
*********

``proj:project:type:taxonomy``
  A type taxonomy for projects.

*********************
Deprecated Properties
*********************

``it:mitre:attack:group``
  The ``it:mitre:attack:group`` form had the following property marked as deprecated:

  * ``tag``

``it:mitre:attack:tactic``
  The ``it:mitre:attack:tactic`` form had the following property marked as deprecated:

  * ``tag``

``it:mitre:attack:technique``
  The ``it:mitre:attack:technique`` form had the following property marked as deprecated:

  * ``tag``

``it:mitre:attack:software``
  The ``it:mitre:attack:software`` form had the following property marked as deprecated:

  * ``tag``

``it:mitre:attack:campaign``
  The ``it:mitre:attack:campaign`` form had the following property marked as deprecated:

  * ``tag``
