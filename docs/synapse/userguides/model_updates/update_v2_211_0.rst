

.. _userguide_model_v2_211_0:

######################
v2.211.0 Model Updates
######################

The following model updates were made during the ``v2.211.0`` Synapse release.

*********
New Types
*********

``inet:service:access:action:taxonomy``
  A hierarchical taxonomy of service actions.



*********
New Forms
*********

``inet:service:app``
  A platform specific application.



**************
New Properties
**************

``inet:search:query``
  The form had the following properties added to it:


  ``app``
    The app which handled the action.


  ``client:app``
    The client service app which initiated the action.


``inet:service:access``
  The form had the following properties added to it:


  ``action``
    The platform specific action which this access records.


  ``app``
    The app which handled the action.


  ``client:app``
    The client service app which initiated the action.


``inet:service:login``
  The form had the following properties added to it:


  ``app``
    The app which handled the action.


  ``client:app``
    The client service app which initiated the action.


``inet:service:message``
  The form had the following properties added to it:


  ``app``
    The app which handled the action.


  ``client:app``
    The client service app which initiated the action.


``inet:service:platform``
  The form had the following properties added to it:


  ``names``
    An array of alternate names for the platform.


  ``urls``
    An array of alternate URLs for the platform.



******************
Updated Interfaces
******************

``inet:service:action``
  The property ``app`` has been added to the interface.


  The property ``client:app`` has been added to the interface.



******************
Updated Properties
******************

``inet:service:platform``
  The form had the following properties updated:


    The property ``name`` had the ``names`` property declared as an alternative
    value for guid based deconfliction.

    The property ``url`` had the ``urls`` property declared as an alternative
    value for guid based deconfliction.


``ou:conference:event``
  The form had the following property updated:

    The property ``conference`` had the ``readonly`` flag removed from its
    definition.

