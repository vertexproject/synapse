
.. _userguide_model_v2_145_0:

######################
v2.145.0 Model Updates
######################

The following model updates were made during the ``v2.145.0`` Synapse release.

*********
New Types
*********

``it:sec:tlp``
  The US CISA Traffic-Light-Protocol used to designate information sharing
  boundaries.

``meta:priority``
  A generic priority enumeration.

``meta:severity``
  A generic severity enumeration.

*********
New Forms
*********

``it:sec:metrics``
  A node used to track metrics of an organization's infosec program.

``it:sec:vuln:scan``
  An instance of running a vulnerability scan.

``it:sec:vuln:scan:result``
  A vulnerability scan result for an asset.``

**************
New Properties
**************

``it:dev:repo:issue``
  The form had the following properties added to it:

  ``updated``
    The time the issue was updated.

  ``id``
    The ID of the issue in the repository system.

``it:dev:repo:issue:comment``
  The form had the following properties added to it:

  ``created``
    The time the comment was created.

  ``updated``
    The time the comment was updated.

``it:dev:repo:diff:comment``
  The form had the following properties added to it:

  ``created``
    The time the comment was created.

  ``updated``
    The time the comment was updated.

``meta:note``
  The form had the following properties added to it:

  ``updated``
    The time the note was updated.

*********************
Deprecated Properties
*********************

``it:exec:proc``
  The ``it:exec:proc`` form had the following property marked as deprecated:

  * ``src:exe``

``inet:whois:iprec``
  The ``inet:whois:iprec`` form had the following property marked as deprecated:

  * ``registrant``
