
.. _userguide_model_v2_149_0:

######################
v2.149.0 Model Updates
######################

The following model updates were made during the ``v2.149.0`` Synapse release.

**************
New Properties
**************

``taxonomy``
  The interface had the following property added to it:

  ``description``
    A definition of the taxonomy entry.

``inet:email:message``
  The form had the following property added to it:

  ``cc``
    Email addresses parsed from the "cc" header.

``meta:source``
  The form had the following property added to it:

  ``url``
    A URL which documents the meta source.

``ou:campaign``
  The form had the following property added to it:

  ``timeline``
    A timeline of significant events related to the campaign.

*********************
Deprecated Properties
*********************

``taxonomy``
  The ``taxonomy`` interface had the following property marked as deprecated:

  ``summary``
