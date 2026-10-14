

.. _userguide_model_v2_254_0:

######################
v2.254.0 Model Updates
######################

The following model updates were made during the ``v2.254.0`` Synapse release.

*********
New Types
*********

``econ:pay:card:funding:type``
  A payment card funding type.



**************
New Properties
**************

``econ:pay:card``
  The form had the following properties added to it:


  ``funding:reloadable``
    Set to true if the prepaid card can be reloaded.


  ``funding:type``
    The funding type of the card.


  ``network``
    The payment network which processes transactions for the card.


  ``network:name``
    The name of the payment network which processes transactions for the card.


``inet:service:platform``
  The form had the following property added to it:

  ``tenant``
    The tenant which owns the platform.



******************
Updated Interfaces
******************

``inet:service:action``
  The interface property ``instance`` has been deprecated.


``inet:service:base``
  The interface property ``instance`` has been deprecated.



****************
Deprecated Types
****************

The following forms have been marked as deprecated:


* ``inet:service:instance``
* ``ps:tokn``



*********************
Deprecated Properties
*********************

``inet:search:query``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:access``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:account``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:agent``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:app``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:bucket``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:bucket:item``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:channel``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:channel:member``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:emote``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:group``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:group:member``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:login``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:message``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:permission``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:relationship``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:resource``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:rule``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:session``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:subscription``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:tenant``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``inet:service:thread``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:dev:repo``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:dev:repo:branch``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:dev:repo:commit``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:dev:repo:diff:comment``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:dev:repo:issue``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:dev:repo:issue:comment``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:dev:repo:issue:label``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:exec:query``
  The form had the following property deprecated:

  ``service:instance``
    Deprecated. Please use :service:platform.


``it:host``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:host:tenancy``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``it:log:event``
  The form had the following property deprecated:

  ``service:instance``
    Deprecated. Please use :service:platform.


``it:software:image``
  The form had the following property deprecated:

  ``instance``
    Deprecated. Please use :platform.


``ps:name``
  The form had the following properties deprecated:


  ``given``
    Deprecated.


  ``middle``
    Deprecated.


  ``sur``
    Deprecated.


``ps:person``
  The form had the following properties deprecated:


  ``name:given``
    Deprecated. Please use :name.


  ``name:middle``
    Deprecated. Please use :name.


  ``name:sur``
    Deprecated. Please use :name.


``ps:persona``
  The form had the following properties deprecated:


  ``name:given``
    Deprecated. Please use :name.


  ``name:middle``
    Deprecated. Please use :name.


  ``name:sur``
    Deprecated. Please use :name.


``risk:alert``
  The form had the following property deprecated:

  ``service:instance``
    Deprecated. Please use :service:platform.

