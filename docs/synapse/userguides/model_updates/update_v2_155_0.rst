
.. _userguide_model_v2_155_0:

######################
v2.155.0 Model Updates
######################

The following model updates were made during the ``v2.155.0`` Synapse release.

*********
New Forms
*********

``it:av:scan:result``
  The result of running an antivirus scanner.

**************
New Properties
**************

``proj:ticket``
  The form had the following property added to it:

  ``ext:assignee``
    Ticket assignee contact information from an external system.

``risk:alert``
  The form had the following property added to it:

  ``severity``
    A severity rank for the alert.

``it:exec:query``
  The form had the following property added to it:

  ``offset``
    The offset of the last record consumed from the query.

******************
Updated Properties
******************

``risk:alert``
  The form had the following properties updated on it:

  ``priority``
    The type of this property has been changed from an ``int`` to
    ``meta:priority``.

``risk:attack``
  The form had the following properties updated on it:

  ``severity``
    The type of this property has been changed from an ``int`` to
    ``meta:severity``.

``risk:compromise``
  The form had the following properties updated on it:

  ``severity``
    The type of this property has been changed from an ``int`` to
    ``meta:severity``.

****************
Deprecated Forms
****************

The following forms have been marked as deprecated:

``it:av:sig``
  Please use ``it:av:scan:result``.

``it:av:filehit``
  Please use ``it:av:scan:result``.

``it:av:prochit``
  Please use ``it:av:scan:result``.
