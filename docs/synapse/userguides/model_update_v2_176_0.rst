.. _userguide_model_v2_176_0:

v2.176.0 Model Updates
######################

The following model updates were made during the ``v2.176.0`` Synapse release.

**New Forms**

``inet:service:thread``
  A message thread.

**New Properties**

``inet:service:message``
The form had the following properties added to it:

  ``thread``
    The thread which contains the message.

  ``title``
    The message title.

**Updated Forms**

``inet:service:account``
   The form now inherits from the ``inet:service:object`` interface.
