

.. _userguide_model_v2_201_0:

######################
v2.201.0 Model Updates
######################

The following model updates were made during the ``v2.201.0`` Synapse release.

**************
New Properties
**************

``risk:mitigation:type:taxonomy``
  The form had the following properties added to it:


  ``base``
    The base taxon.


  ``depth``
    The depth indexed from 0.


  ``desc``
    A definition of the taxonomy entry.


  ``parent``
    The taxonomy parent.


  ``sort``
    A display sort order for siblings.


  ``summary``
    Deprecated. Please use title/desc.


  ``title``
    A brief title of the definition.



*************
Updated Types
*************

``risk:mitigation:type:taxonomy``
  The type interface has been modified to inherit from the ``meta:taxonomy`` interface.



******************
Updated Properties
******************

``proj:ticket``
  The form had the following property updated:


    The property ``type`` had an example added to its definition.

