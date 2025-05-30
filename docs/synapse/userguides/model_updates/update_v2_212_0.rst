

.. _userguide_model_v2_212_0:

######################
v2.212.0 Model Updates
######################

The following model updates were made during the ``v2.212.0`` Synapse release.

*********
New Forms
*********

``inet:tls:ja4:sample``
  A JA4 TLS client fingerprint used by a client.


``inet:tls:ja4s:sample``
  A JA4S TLS server fingerprint used by a server.


``inet:tls:ja4``
  A JA4 TLS client fingerprint.


``inet:tls:ja4s``
  A JA4S TLS server fingerprint.



**************
New Properties
**************

``inet:tls:handshake``
  The form had the following properties added to it:


  ``client:ja3``
    The JA3 fingerprint of the client request.


  ``client:ja4``
    The JA4 fingerprint of the client request.


  ``server:ja3s``
    The JA3S fingerprint of the server response.


  ``server:ja4s``
    The JA4S fingerprint of the server response.



*********************
Deprecated Properties
*********************

``inet:tls:handshake``
  The form had the following properties deprecated:


  ``client:fingerprint:ja3``
    Deprecated. Please use ``:client:ja3``.


  ``server:fingerprint:ja3``
    Deprecated. Please use ``:server:ja3s``.

