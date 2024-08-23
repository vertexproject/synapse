

.. _userguide_model_v2_179_0:

######################
v2.179.0 Model Updates
######################

The following model updates were made during the ``v2.179.0`` Synapse release.

*********
New Forms
*********

``it:app:yara:netmatch``
  An instance of a YARA rule network hunting match.



**************
New Properties
**************

``geo:telem``
  The form had the following property added to it:

  ``node``
    The node that was observed at the associated time and place.


``it:sec:stix:indicator``
  The form had the following properties added to it:


  ``confidence``
    The confidence field from the STIX indicator.


  ``description``
    The description field from the STIX indicator.


  ``pattern_type``
    The STIX indicator pattern type.


  ``revoked``
    The revoked field from the STIX indicator.


  ``valid_from``
    The valid_from field from the STIX indicator.


  ``valid_until``
    The valid_until field from the STIX indicator.



*************
Updated Types
*************

``pe:langid``
  The type has been modified to add additional known language codes to it
  enums list.


******************
Updated Properties
******************

``inet:dns:request``
  The form had the following property updated:


    The property ``reply:code`` has been modified to add enums for known DNS
    reply code values.



****************
Deprecated Edges
****************

``seenat``
    The edge has been deprecated when used with a ``geo:telem`` target node.
    Deprecated. Please use ``geo:telem:node``.

