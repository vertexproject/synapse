

.. _userguide_model_v2_247_0:

######################
v2.247.0 Model Updates
######################

The following model updates were made during the ``v2.247.0`` Synapse release.

**************
New Properties
**************

``inet:whois:iprec``
  The form had the following property added to it:

  ``registrant:name``
    The name assigned to the network by the registrant.


``inet:whois:rec``
  The form had the following property added to it:

  ``registrant:name``
    The registrant name from the whois record.


``risk:vuln``
  The form had the following property added to it:

  ``reporter:url``
    The URL for the vulnerability provided by the reporter.



*********************
Deprecated Properties
*********************

``inet:whois:rec``
  The form had the following property deprecated:

  ``registrant``
    Deprecated. Please use :registrant:name.

