.. _userguide_model_v2_173_1:

######################
v2.173.1 Model Updates
######################

The following model updates were made during the ``v2.173.1`` Synapse release.

**************
New Properties
**************

``ou:conference``
  The form had the following property added to it:

  ``names``
    An array of alternate names for the conference.

``ps:contact``
  The form had the following property added to it:

  ``titles``
    An array of alternate titles for the contact.

***********
Light Edges
***********

``uses``
  When used with a ``plan:procedure:step`` node, the edge indicates the
  step in the procedure makes use of the target node.
