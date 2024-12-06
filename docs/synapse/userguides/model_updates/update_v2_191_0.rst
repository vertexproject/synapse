

.. _userguide_model_v2_191_0:

######################
v2.191.0 Model Updates
######################

The following model updates were made during the ``v2.191.0`` Synapse release.

**************
New Interfaces
**************

``inet:service:subscriber``
  Properties common to the nodes which subscribe to services.


``econ:pay:instrument``
  An interface for forms which may act as a payment instrument.



*********
New Types
*********

``meta:ruleset:type:taxonomy``
  A taxonomy for meta:ruleset types.


``markdown``
  A markdown string.


``econ:pay:instrument``
  A node which may act as a payment instrument.


``inet:service:subscriber``
  A node which may subscribe to a service subscription.


``meta:activity``
  A generic activity level enumeration.



*********
New Forms
*********

``inet:service:subscription:level:taxonomy``
  A taxonomy of platform specific subscription levels.


``inet:service:subscription``
  A subscription to a service platform or instance.


``inet:service:tenant``
  A tenant which groups accounts and instances.



**************
New Properties
**************

``econ:acct:payment``
  The form had the following properties added to it:


  ``from:instrument``
    The payment instrument used to make the payment.


  ``to:instrument``
    The payment instrument which received funds from the payment.


``inet:service:account``
  The form had the following property added to it:

  ``tenant``
    The tenant which contains the account.


``inet:service:instance``
  The form had the following property added to it:

  ``tenant``
    The tenant which contains the instance.


``inet:service:session``
  The form had the following property added to it:

  ``http:session``
    The HTTP session associated with the service session.


``meta:ruleset``
  The form had the following property added to it:

  ``type``
    The ruleset type.


``meta:source``
  The form had the following properties added to it:


  ``ingest:latest``
    Used by ingest logic to capture the last time a feed ingest ran.


  ``ingest:offset``
    Used by ingest logic to capture the current ingest offset within a feed.


``ps:contactlist``
  The form had the following property added to it:

  ``source:account``
    The service account from which the contact list was extracted.


``risk:outage``
  The form had the following property added to it:

  ``attack``
    An attack which caused the outage.


``risk:threat``
  The form had the following property added to it:

  ``activity``
    The most recently assessed activity level of the threat cluster.



*************
Updated Types
*************

``crypto:currency:address``
  The type interface has been modified from None to ['econ:pay:instrument'].


``econ:bank:account``
  The type interface has been modified from None to ['econ:pay:instrument'].


``econ:pay:card``
  The type interface has been modified from None to ['econ:pay:instrument'].


``inet:service:account``
  The type interface has been modified from ['inet:service:object'] to
  ['inet:service:subscriber'].



*********************
Deprecated Properties
*********************

``auth:creds``
  The form had the following property deprecated:

  ``web:acct``
    Deprecated. Use :service:account.


``econ:acct:payment``
  The form had the following properties deprecated:


  ``from:account``
    Deprecated. Please use :from:instrument.


  ``from:coinaddr``
    Deprecated. Please use :from:instrument.


  ``from:pay:card``
    Deprecated. Please use :from:instrument.


  ``to:account``
    Deprecated. Please use :to:instrument.


  ``to:coinaddr``
    Deprecated. Please use :to:instrument.


``inet:service:message``
  The form had the following property deprecated:

  ``client:address``
    Deprecated. Please use :client


``ps:contact``
  The form had the following properties deprecated:


  ``web:acct``
    Deprecated. Use :service:accounts.


  ``web:accts``
    Deprecated. Use :service:accounts.


  ``web:group``
    Deprecated. Use inet:service:group:profile to link to a group.


``ps:contactlist``
  The form had the following property deprecated:

  ``source:acct``
    Deprecated. Use :source:account.


``tel:mob:telem``
  The form had the following property deprecated:

  ``acct``
    Deprecated, use :account

