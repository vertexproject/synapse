

.. _userguide_model_v2_251_0:

######################
v2.251.0 Model Updates
######################

The following model updates were made during the ``v2.251.0`` Synapse release.

**************
New Properties
**************

``econ:bank:account``
  The form had the following property added to it:

  ``swift:bic``
    The SWIFT BIC for the bank which issued the account.


``risk:attack``
  The form had the following property added to it:

  ``actor``
    The actor which conducted the attack.


``risk:threat``
  The form had the following property added to it:

  ``ext:ids``
    An array of alternate external identifiers for the threat.



*************
Updated Types
*************

``econ:bank:aba:rtn``
  The type has been modified from {'enums': None, 'globsuffix': False, 'lower':
  False, 'onespace': False, 'regex': '[0-9]{9}', 'replace': [], 'strip': False}
  to {'enums': None, 'globsuffix': False, 'lower': False, 'onespace': False,
  'regex': '^[0-9]{9}$', 'replace': [], 'strip': False}.


``econ:bank:iban``
  The type has been modified from {'enums': None, 'globsuffix': False, 'lower':
  False, 'onespace': False, 'regex': '[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{1,30}',
  'replace': [], 'strip': False} to {'enums': None, 'globsuffix': False,
  'lower': False, 'onespace': False, 'regex':
  '^[A-Z]{2}[0-9]{2}[a-zA-Z0-9]{1,30}$', 'replace': [], 'strip': False}.


``econ:bank:swift:bic``
  The type has been modified from {'enums': None, 'globsuffix': False, 'lower':
  False, 'onespace': False, 'regex': '[A-Z]{6}[A-Z0-9]{5}', 'replace': [],
  'strip': False} to {'enums': None, 'globsuffix': False, 'lower': False,
  'onespace': False, 'regex': '^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$', 'replace':
  [], 'strip': False}.



******************
Updated Properties
******************

``risk:threat``
  The form had the following property updated:


    The property ``ext:id`` had the ``['alts']`` keys added to its definition.

