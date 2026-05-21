

.. _userguide_model_v2_230_0:

######################
v2.230.0 Model Updates
######################

The following model updates were made during the ``v2.230.0`` Synapse release.

**************
New Properties
**************

``inet:email``
  The form had the following properties added to it:


  ``base``
    The base email address which is populated if the email address contains a
    user with a ``+<tag>``.


  ``plus``
    The optional email address "tag".


``inet:http:request``
  The form had the following properties added to it:


  ``header:host``
    The FQDN parsed from the "Host:" header in the request.


  ``header:referer``
    The referer URL parsed from the "Referer:" header in the request.


``ou:goal``
  The form had the following properties added to it:


  ``reporter``
    The organization reporting on the goal.


  ``reporter:name``
    The name of the organization reporting on the goal.



*********************
Deprecated Properties
*********************

``inet:http:request``
  The form had the following property deprecated:

  ``referer``
    Deprecated. Please use ``:header:referer``.

