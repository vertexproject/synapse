

.. _userguide_model_v2_210_0:

######################
v2.210.0 Model Updates
######################

The following model updates were made during the ``v2.210.0`` Synapse release.

*********
New Types
*********

``entity:actor``
  An entity which has initiative to act.



*********
New Forms
*********

``entity:relationship``
  A directional relationship between two actor entities.


``entity:relationship:type:taxonomy``
  A hierarchical taxonomy of entity relationship types.



**************
New Properties
**************

``inet:service:channel``
  The form had the following property added to it:

  ``topic``
    The visible topic of the channel.


``inet:service:message``
  The form had the following properties added to it:


  ``hashtags``
    An array of hashtags mentioned within the message.


  ``mentions``
    Contactable entities mentioned within the message.


``ps:contact``
  The form had the following properties added to it:


  ``banner``
    The file representing the banner for the contact.


  ``passwd``
    The current password for the contact.


  ``website``
    A related URL specified by the contact (e.g., a personal or company web
    page, blog, etc.).


  ``websites``
    Alternative related URLs specified by the contact.

