

.. _userguide_model_v2_188_0:

######################
v2.188.0 Model Updates
######################

The following model updates were made during the ``v2.188.0`` Synapse release.

*********
New Types
*********

``inet:service:object``
  An ndef type including all forms which implement the ``inet:service:object``
  interface.



*********
New Forms
*********

``risk:outage``
  An outage event which affected resource availability.


``meta:aggregate:type:taxonomy``
  A type of item being counted in aggregate.


``ou:candidate:method:taxonomy``
  A taxonomy of methods by which a candidate came under consideration.


``risk:outage:type:taxonomy``
  An outage type taxonomy.


``file:attachment``
  A file attachment.


``risk:outage:cause:taxonomy``
  An outage cause taxonomy.


``inet:service:relationship``
  A relationship between two service objects.


``meta:aggregate``
  A node which represents an aggregate count of a specific type.


``inet:service:relationship:type:taxonomy``
  A service object relationship type taxonomy.


``inet:service:emote``
  An emote or reaction by an account.


``ou:candidate``
  A candidate being considered for a role within an organization.



**************
New Properties
**************

``inet:flow``
  The form had the following properties added to it:


  ``dst:txfiles``
    An array of files sent by the destination host.


  ``src:txfiles``
    An array of files sent by the source host.


``ou:industry``
  The form had the following properties added to it:


  ``reporter``
    The organization reporting on the industry.


  ``reporter:name``
    The name of the organization reporting on the industry.



***********
Light Edges
***********

``caused``
    When used with a ``risk:attack`` and an ``risk:outage`` node, the edge
    indicates the attack caused the outage.

    When used with a ``meta:event`` and an ``risk:outage`` node, the edge
    indicates the event caused the outage.


``impacted``
    When used with a ``risk:outage`` node, the edge indicates the outage event
    impacted the availability of the target node.

    When used with a ``risk:vuln`` and an ``ou:technique`` node, the edge
    indicates the vulnerability uses the technique.


``uses``
    When used with a ``ou:technique`` and an ``risk:vuln`` node, the edge
    indicates the technique uses the vulnerability.

