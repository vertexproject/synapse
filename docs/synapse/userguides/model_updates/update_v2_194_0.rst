

.. _userguide_model_v2_194_0:

######################
v2.194.0 Model Updates
######################

The following model updates were made during the ``v2.194.0`` Synapse release.

**************
New Properties
**************

``inet:service:message``
  The form had the following property added to it:

  ``repost``
    The original message reposted by this message.


``it:prod:soft``
  The form had the following property added to it:

  ``id``
    An ID for the software.


``ps:contact``
  The form had the following property added to it:

  ``bio``
    A brief bio provided for the contact.



******************
Updated Properties
******************

``geo:place``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``it:prod:soft``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``it:prod:softver``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``ou:campaign``
  The form had the following properties updated:


    The property ``goal`` had the alternative property names added to its definition.


    The property ``name`` had the alternative property names added to its definition.


``ou:conference``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``ou:goal``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``ou:industry``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``pol:country``
  The form had the following property updated:

    The property ``name`` had the alternative property names added to its definition.


``ps:contact``
  The form had the following properties updated:


    The property ``email`` had the alternative property names added to its definition.


    The property ``id:number`` had the alternative property names added to its
    definition.


    The property ``lang`` had the alternative property names added to its definition.


    The property ``name`` had the alternative property names added to its definition.


    The property ``orgname`` had the alternative property names added to its definition.


    The property ``title`` had the alternative property names added to its definition.


    The property ``user`` had the alternative property names added to its definition.


``ps:person``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``risk:threat``
  The form had the following property updated:


    The property ``org:name`` had the alternative property names added to its
    definition.


``risk:tool:software``
  The form had the following property updated:


    The property ``soft:name`` had the alternative property names added to its
    definition.


``risk:vuln``
  The form had the following property updated:


    The property ``name`` had the alternative property names added to its definition.


``tel:mob:telem``
  The form had the following property updated:


    The property ``adid`` had the following docstring added:

        The advertising ID of the mobile telemetry sample.



****************
Deprecated Types
****************

The following forms have been marked as deprecated:


* ``it:os:android:aaid``
* ``it:os:ios:idfa``



*********************
Deprecated Properties
*********************

``tel:mob:telem``
  The form had the following properties deprecated:


  ``aaid``
    Deprecated. Please use ``:adid``.


  ``idfa``
    Deprecated. Please use ``:adid``.

