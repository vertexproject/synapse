
.. _userguide_model_v2_170_0:

######################
v2.170.0 Model Updates
######################

The following model updates were made during the ``v2.170.0`` Synapse release.


*********
New Forms
*********

``file:mime:lnk``
  Metadata pulled from a Windows shortcut or LNK file.

``it:mitre:attack:datasource``
  A MITRE ATT&CK Datasource ID.

``it:mitre:attack:data:component``
  A MITRE ATT&CK data component.

**************
New Properties
**************

``it:mitre:attack:technique``
  The form had the following property added to it:

  ``data:components``
    An array of MITRE ATT&CK data components that detect the ATT&CK technique.

``it:prod:hardware``
  The form had the following properties added to it:

  ``manufacturer``
    The organization that manufactures this hardware.

  ``manufacturer:name``
    The name of the organization that manufactures this hardware.

*********************
Deprecated Properties
*********************

``it:prod:hardware``
  The ``it:prod:hardware`` form had the following property marked as deprecated:

  * ``make``
