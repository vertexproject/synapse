

.. _userguide_model_v2_200_0:

######################
v2.200.0 Model Updates
######################

The following model updates were made during the ``v2.200.0`` Synapse release.

**************
New Properties
**************

``it:av:scan:result``
  The form had the following property added to it:

  ``categories``
    A list of categories for the result returned by the scanner.


``it:sec:cve``
  The form had the following properties added to it:


  ``cisa:kev:action``
    The action to mitigate the vulnerability according to the CISA KEV
    database.


  ``cisa:kev:added``
    The date the vulnerability was added to the CISA KEV database.


  ``cisa:kev:desc``
    The description of the vulnerability according to the CISA KEV database.


  ``cisa:kev:duedate``
    The date the action is due according to the CISA KEV database.


  ``cisa:kev:name``
    The name of the vulnerability according to the CISA KEV database.


  ``cisa:kev:product``
    The product name listed in the CISA KEV database.


  ``cisa:kev:vendor``
    The vendor name listed in the CISA KEV database.


  ``nist:nvd:modified``
    The date the vulnerability was last modified in the NVD.


  ``nist:nvd:published``
    The date the vulnerability was first published in the NVD.


  ``nist:nvd:source``
    The name of the organization which reported the vulnerability to NIST.


``ou:contest:result``
  The form had the following property added to it:

  ``period``
    The period of time when the participant competed in the contest.


``risk:vuln``
  The form had the following property added to it:

  ``tag``
    A tag used to annotate the presence or use of the vulnerability.



******************
Updated Properties
******************

``transport:sea:vessel``
  The form had the following property updated:


    The property ``name`` has been modified from ['str', {'lower': True,
    'onespace': True}] to ['entity:name', {}].



*********************
Deprecated Properties
*********************

``it:prod:softver``
  The form had the following properties deprecated:


  ``semver:build``
    Deprecated.


  ``semver:major``
    Deprecated. Please use semver range queries.


  ``semver:minor``
    Deprecated. Please use semver range queries.


  ``semver:patch``
    Deprecated. Please use semver range queries.


  ``semver:pre``
    Deprecated.


``risk:vuln``
  The form had the following properties deprecated:


  ``cisa:kev:action``
    Deprecated. Please use it:sec:cve:cisa:kev:action.


  ``cisa:kev:added``
    Deprecated. Please use it:sec:cve:cisa:kev:added.


  ``cisa:kev:desc``
    Deprecated. Please use it:sec:cve:cisa:kev:desc.


  ``cisa:kev:duedate``
    Deprecated. Please use it:sec:cve:cisa:kev:duedate.


  ``cisa:kev:name``
    Deprecated. Please use it:sec:cve:cisa:kev:name.


  ``cisa:kev:product``
    Deprecated. Please use it:sec:cve:cisa:kev:product.


  ``cisa:kev:vendor``
    Deprecated. Please use it:sec:cve:cisa:kev:vendor.


  ``nist:nvd:modified``
    Deprecated. Please use it:sec:cve:nist:nvd:modified.


  ``nist:nvd:published``
    Deprecated. Please use it:sec:cve:nist:nvd:published.


  ``nist:nvd:source``
    Deprecated. Please use it:sec:cve:nist:nvd:source.

