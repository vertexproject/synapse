

.. _userguide_model_v2_226_0:

######################
v2.226.0 Model Updates
######################

The following model updates were made during the ``v2.226.0`` Synapse release.

*********
New Forms
*********

``inet:service:platform:type:taxonomy``
  A service platform type taxonomy.


``inet:service:agent``
  An instance of a deployed agent or software integration which is part of the
  service architecture.


``it:dev:repo:entry``
  A file included in a repository.



**************
New Properties
**************

``inet:search:query``
  The form had the following properties added to it:


  ``agent``
    The service agent which performed the action potentially on behalf of an
    account.


  ``client:software``
    The client software used to initiate the action.


``inet:service:access``
  The form had the following properties added to it:


  ``agent``
    The service agent which performed the action potentially on behalf of an
    account.


  ``client:software``
    The client software used to initiate the action.


``inet:service:login``
  The form had the following properties added to it:


  ``agent``
    The service agent which performed the action potentially on behalf of an
    account.


  ``client:software``
    The client software used to initiate the action.


  ``url``
    The URL of the login endpoint used for this login attempt.


``inet:service:message``
  The form had the following property added to it:

  ``agent``
    The service agent which performed the action potentially on behalf of an
    account.


``inet:service:platform``
  The form had the following properties added to it:


  ``family``
    A family designation for use with instanced platforms such as Slack,
    Discord, or Mastodon.


  ``software``
    The latest known software version that the platform is running.


  ``type``
    The type of service platform.



******************
Updated Interfaces
******************

``inet:service:action``
  The interface property ``app`` has been deprecated.


  The interface property ``client:app`` has been deprecated.


  The property ``agent`` has been added to the interface.


  The property ``client:software`` has been added to the interface.


``inet:service:object``
  The interface property ``app`` has been deprecated.



***********
Light Edges
***********

``about``
    When used with a ``it:log:event`` node, the edge indicates the it:log:event
    is about the target node.


``has``
    When used with a ``it:dev:repo:commit`` and an ``it:dev:repo:entry`` node,
    the edge indicates the file entry is present in the commit version of the
    repository.


``linked``
    The source node is linked to the target node.



****************
Deprecated Types
****************

The following forms have been marked as deprecated:


* ``inet:service:app``



*********************
Deprecated Properties
*********************

``inet:search:query``
  The form had the following properties deprecated:


  ``app``
    Deprecated. Please use ``:agent`` / ``inet:service:agent``.


  ``client:app``
    Deprecated. Please use ``:client:software``.


``inet:service:access``
  The form had the following properties deprecated:


  ``app``
    Deprecated. Please use ``:agent`` / ``inet:service:agent``.


  ``client:app``
    Deprecated. Please use ``:client:software``.


``inet:service:account``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:app``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:bucket``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:bucket:item``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:channel``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:channel:member``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:emote``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:group``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:group:member``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:instance``
  The form had the following property deprecated:

  ``app``
    Deprecated. Instances are no longer scoped to applications.


``inet:service:login``
  The form had the following properties deprecated:


  ``app``
    Deprecated. Please use ``:agent`` / ``inet:service:agent``.


  ``client:app``
    Deprecated. Please use ``:client:software``.


``inet:service:message``
  The form had the following properties deprecated:


  ``app``
    Deprecated. Please use ``:agent`` / ``inet:service:agent``.


  ``client:app``
    Deprecated. Please use ``:client:software``.


``inet:service:permission``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:relationship``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:resource``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:rule``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:session``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:subscription``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:tenant``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``inet:service:thread``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:dev:repo``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:dev:repo:branch``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:dev:repo:commit``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:dev:repo:diff:comment``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:dev:repo:issue``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:dev:repo:issue:comment``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:dev:repo:issue:label``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:host``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:host:tenancy``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.


``it:software:image``
  The form had the following property deprecated:

  ``app``
    Deprecated. Objects are no longer scoped to an application or agent.

