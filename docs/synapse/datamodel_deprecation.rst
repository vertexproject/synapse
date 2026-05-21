
.. _dm-deprecation-policy:

============================
Datamodel Deprecation Policy
============================

As the Synapse Data Model has grown and evolved over time, Vertex has found the need
to deprecate model elements which are no longer useful. These elements may represent
relationships which are better captured with newer elements; concepts which are better
represented by convention; or other issues. As such, model elements (types, forms,
and properties) which are deprecated should no longer be used for new data modeling.
Deprecated model elements will be removed in a future major version Synapse release.

For deprecated model elements, suggested alternatives will be provided and example Storm
queries which can be used to migrate data in such a fashion.

Using Deprecated Model Elements
-------------------------------

When Deprecated model elements are used in a Cortex, the following log events will be made:

- One startup, if a extended property definition uses a deprecated type to define it,
  a warning message will be logged.
- If a extended property is added which uses a deprecated type to define it, a warning
  message will be logged.
- Any Types or Forms, from a datamodel loaded by a custom CoreModule, which use a
  deprecated model component will cause a warning message to be logged. This includes
  any Array or Comp type model elements which utilize a deprecated Type.
- If a property or tag property is set on a node which is deprecated or using a
  deprecated type, that will cause a warning message to be logged and a ``warn``
  message to be sent over the Storm runtime. This only occurs once per given runtime.
- If a node is made using deprecated form or using a deprecated type, that will cause
  a warning message to be logged and a ``warn`` message to be sent over the Storm
  runtime. This only occurs once per given runtime.

Deleting nodes which use deprecated model elements does not trigger warnings, since that
would normally be done after an associated data migration and would be excessive in
the event of a large migration.
