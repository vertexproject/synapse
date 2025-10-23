

.. _userguide_model_v2_225_0:

######################
v2.225.0 Model Updates
######################

The following model updates were made during the ``v2.225.0`` Synapse release.

**************
New Properties
**************

``inet:service:account``
  The form had the following property added to it:

  ``users``
    An array of alternate user names for this account.


``media:news``
  The form had the following property added to it:

  ``body``
    The body of the news item.


``risk:mitigation``
  The form had the following property added to it:

  ``id``
    An identifier for the mitigation.



******************
Updated Properties
******************

``inet:service:account``
  The form had the following property updated:

    The property ``user`` had the ``users`` property added as an ``alts``
    value for deconfliction.
