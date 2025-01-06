

.. _userguide_model_v2_193_0:

######################
v2.193.0 Model Updates
######################

The following model updates were made during the ``v2.193.0`` Synapse release.

**************
New Properties
**************

``inet:egress``
  The form had the following property added to it:

  ``host:iface``
    The interface which the host used to connect out via the egress.


``inet:email:message``
  The form had the following property added to it:

  ``id``
    The ID parsed from the "message-id" header.


``inet:flow``
  The form had the following property added to it:

  ``capture:host``
    The host which captured the flow.


``inet:service:account``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the account.


``inet:service:bucket``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the bucket.


``inet:service:bucket:item``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the bucket item.


``inet:service:channel``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the channel.


``inet:service:channel:member``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the channel membership.


``inet:service:emote``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the emote.


``inet:service:group``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the group.


``inet:service:group:member``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the group membership.


``inet:service:permission``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the permission.


``inet:service:relationship``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the relationship.


``inet:service:rule``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the rule.


``inet:service:session``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the session.


``inet:service:subscription``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the subscription.


``inet:service:tenant``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the tenant.


``inet:service:thread``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the thread.


``it:dev:repo:issue:label``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the object.


``it:host``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the object.


``it:host:tenancy``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the object.


``it:software:image``
  The form had the following property added to it:

  ``url``
    The primary URL associated with the object.


``risk:leak``
  The form had the following property added to it:

  ``recipient``
    The identity which received the leaked information.



******************
Updated Interfaces
******************

``inet:service:object``
  The property ``url`` has been added to the interface.



*************
Updated Types
*************

``inet:web:hashtag``
  The type has been modified from {'enums': None, 'globsuffix': False, 'lower':
  True, 'onespace': False, 'regex': '^#\\w[\\w·]*(?<!·)$', 'replace': [],
  'strip': False} to {'enums': None, 'globsuffix': False, 'lower': True,
  'onespace': False, 'regex': '^#[^\\p{Z}#]+$', 'replace': [], 'strip': True}.



***********
Light Edges
***********

``enabled``
    When used with a ``risk:leak`` and an ``risk:leak`` node, the edge
    indicates The source leak enabled the target leak to occur.


``uses``
    When used with a ``risk:mitigation`` and an ``it:prod:softver`` node, the
    edge indicates The mitigation uses the software version.


``uses``
    When used with a ``risk:mitigation`` and an ``it:prod:hardware`` node, the
    edge indicates The mitigation uses the hardware.



*********************
Deprecated Properties
*********************

``risk:mitigation``
  The form had the following properties deprecated:


  ``hardware``
    Deprecated. Please use risk:mitigation -(uses)> it:prod:hardware.


  ``software``
    Deprecated. Please use risk:mitigation -(uses)> it:prod:softver.

