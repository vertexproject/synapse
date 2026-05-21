
.. _userguide_model_v2_165_0:

######################
v2.165.0 Model Updates
######################

The following model updates were made during the ``v2.165.0`` Synapse release.

*********
New Forms
*********

``econ:acct:receipt``
  A receipt issued as proof of payment.

``econ:acct:invoice``
  An invoice issued requesting payment.

``econ:bank:account:type:taxonomy``
  A bank account type taxonomy.

``econ:bank:account``
  A bank account.

``econ:bank:balance``
  A balance contained by a bank account at a point in time.

``econ:bank:statement``
  A statement of bank account payment activity over a period of time.

``econ:bank:aba:rtn``
  An American Bank Association (ABA) routing transit number (RTN).

``econ:bank:iban``
  An International Bank Account Number.

``econ:bank:swift:bic``
  A Society for Worldwide Interbank Financial Telecommunication (SWIFT)
  Business Identifier Code (BIC).

``risk:vulnerable``
  Indicates that a node is susceptible to a vulnerability.

``sci:hypothesis:type:taxonomy``
  A taxonomy of hypothesis types.

``sci:hypothesis``
  A hypothesis or theory.

``sci:experiment:type:taxonomy``
  A taxonomy of experiment types.

``sci:experiment``
  An instance of running an experiment.

``sci:observation``
  An observation which may have resulted from an experiment.

``sci:evidence``
  An assessment of how an observation supports or refutes a hypothesis.

******************
Updated Properties
******************

``risk:mitigation``
  The form had the following properties updated on it:

  ``name``
    This property is now lower-cased and single spaced.

``it:mitre:attack:technique``
  The form had the following properties updated on it:

  ``name``
    This property is now lower-cased and single spaced.

``it:mitre:attack:mitigation``
  The form had the following properties updated on it:

  ``name``
    This property is now lower-cased and single spaced.

**************
New Properties
**************

``econ:acct:payment``
  The form had the following properties added to it:

  ``from:account``
    The bank account which made the payment.

  ``to:account``
    The bank account which received the payment.

  ``invoice``
    The invoice that the payment applies to.

  ``receipt``
    The receipt that was issued for the payment.

``file:mime:image``
  The interface had the following property added to it:

  ``text``
    The text contained within the image.

``inet:email:message``
  The form had the following property added to it:

  ``flow``
    The inet:flow which delivered the message.

``ou:id:number``
  The form had the following property added to it:

  ``issuer``
    The contact information of the office which issued the ID number.

``risk:threat``
  The form had the following property added to it:

  ``mitre:attack:group``
    A mapping to a MITRE ATT&CK group if applicable.

``risk:tool:software``
  The form had the following property added to it:

  ``mitre:attack:software``
    A mapping to a MITRE ATT&CK software if applicable.

``risk:mitigation``
  The form had the following property added to it:

  ``mitre:attack:mitigation``
    A mapping to a MITRE ATT&CK mitigation if applicable.

****************
Deprecated Forms
****************

The following forms have been marked as deprecated:

``risk:hasvuln``
  Please use ``risk:vulnerable``.

***********
Light Edges
***********

``has``
  When used with an ``econ:bank:statement`` and an ``econ:acct:payment``, the
  edge indicates the bank statement includes the payment.

  When used with an ``ou:org`` node, the edge indicates the organization is
  or was in possession of the target node.

  When used with a ``ps:contact`` node, the edge indicates the contact is or
  was in possession of the target node.

  When used with a ``ps:person`` node, the edge indicates the person is or
  was in possession of the target node.

  When used with a ``sci:observation`` node, the edge indicates the
  observations are summarized from the target nodes.

  When used with an ``sci:evidence`` node, the edge indicates the evidence
  includes observations from the target nodes.

``owns``
  When used with an ``ou:org`` node, the edge indicates the organization owns
  or owned the target node.

  When used with a ``ps:contact`` node, the edge indicates the contact owns
  or owned the target node.

  When used with a ``ps:person`` node, the edge indicates the person owns or
  owned the target node.

``uses``
  When used with a ``sci:experiment`` node, the edge indicates the
  experiment used the target nodes when it was run.
