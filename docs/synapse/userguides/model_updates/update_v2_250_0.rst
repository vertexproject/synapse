

.. _userguide_model_v2_250_0:

######################
v2.250.0 Model Updates
######################

The following model updates were made during the ``v2.250.0`` Synapse release.

*********
New Forms
*********

``crypto:smart:effect:freeze``
  A smart contract effect which freezes or unfreezes an address on an issuer
  blocklist.


``crypto:currency:bridge:swap``
  A cross-chain swap which bridges value between two transactions on different
  chains.


``crypto:payment:fee``
  A fee paid to execute a transaction.


``crypto:smart:effect:swaptokens``
  A smart contract effect which swaps one token or currency for another.


``crypto:smart:effect:seize``
  A smart contract effect which destroys the tokens held by an address.



**************
New Properties
**************

``econ:purchase``
  The form had the following property added to it:

  ``platform``
    The platform used to facilitate the purchase.


``inet:http:request``
  The form had the following property added to it:

  ``response:cookies``
    An array of HTTP cookie values parsed from the "Set-Cookie:" headers in the
    response.

