

.. _userguide_model_v2_216_0:

######################
v2.216.0 Model Updates
######################

The following model updates were made during the ``v2.216.0`` Synapse release.

**************
New Properties
**************

``inet:service:app``
  The form had the following properties added to it:


  ``provider``
    The organization which provides the application.


  ``provider:name``
    The name of the organization which provides the application.



***********
Light Edges
***********

``uses``
    When used with a ``risk:threat`` and an ``inet:service:app`` node, the edge
    indicates the threat cluster uses the online application.

