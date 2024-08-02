.. _userguide_model_v2_174_0:

######################
v2.174.0 Model Updates
######################

The following model updates were made during the ``v2.174.0`` Synapse release.


*********
New Forms
*********

``econ:currency``
  The name of a system of money in general use.

``entity:name``
  A name used to refer to an entity.


**************
New Properties
**************

``crypto:key``
  The form had the following properties added to it:

  ``private:text``
    Set only if the ``:private`` property decodes to ASCII.

  ``public:text``
    Set only if the ``:public`` property decodes to ASCII.

``econ:acct:payment``
  The form had the following properties added to it:

  ``from:cash``
    Set to true if the payment input was in cash.

  ``to:cash``
    Set to true if the payment output was in cash.

  ``place``
    The place where the payment occurred.

  ``place:address``
    The address of the place where the payment occurred.

  ``place:latlong``
    The latlong where the payment occurred.

  ``place:loc``
    The loc of the place where the payment occurred.

  ``place:name``
    The name of the place where the payment occurred.

``pol:country``
  The form had the following property added to it:

  ``currencies``
    The official currencies used in the country.


******************
Updated Properties
******************

``ou:position``
  The form had the following property updated on it:

  ``title``
    This property is now an ``entity:name`` type.

``ou:conference``
  The form had the following properties updated on it:

  ``name``
    This property is now an ``entity:name`` type.

  ``names``
    This property is now an array of ``entity:name`` type.

***********
Light Edges
***********

``refs``
  When used with a ``files:bytes`` and an ``it:dev:str`` node, the edge
  indicates the source file contains the target string.
