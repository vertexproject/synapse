
.. _userguide_model_v2_166_0:

######################
v2.166.0 Model Updates
######################

The following model updates were made during the ``v2.166.0`` Synapse release.

*********
New Forms
*********

``inet:tls:handshake``
  An instance of a TLS handshake between a server and client.

``inet:tls:ja3:sample``
  A JA3 sample taken from a client.

``inet:tls:ja3s:sample``
  A JA3 sample taken from a server.

``inet:tls:servercert``
  An x509 certificate sent by a server for TLS.

``inet:tls:clientcert``
  An x509 certificate sent by a client for TLS.

**************
New Properties
**************

``risk:extortion``
  The form had the following property added to it:

  ``deadline``
    The time that the demand must be met.

``risk:leak``
  The form had the following properties added on it:

  ``extortion``
    The extortion event which used the threat of the leak as leverage.

  ``size:bytes``
    The approximate uncompressed size of the total data leaked.

``it:mitre:attack:technique``
  The form had the following properties updated on it:

  ``name``
    This property is now lower-cased and single spaced.

****************
Deprecated Forms
****************

The following forms have been marked as deprecated:

``inet:ssl:cert``
  Please use ``inet:tls:clientcert`` or ``inet:tls:servercert``.

********************
Column Display Hints
********************

The following forms had column display hints added to them:

  ``ou:campaign``
  ``ou:conference``
  ``ou:goal``
  ``ou:org``
  ``ou:team``
  ``ou:technique``
  ``ps:contact``
  ``ps:skill``
  ``ps:proficiency``
  ``risk:threat``
  ``risk:compromise``
  ``risk:mitigation``
  ``risk:tool:software``

***********
Light Edges
***********

``uses``
  When used with a ``risk:extortion`` and an ``ou:technique`` node, the edge
  indicates the attacker used the technique to extort the victim.
