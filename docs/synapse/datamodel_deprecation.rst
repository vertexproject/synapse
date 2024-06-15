
.. _dm-deprecation-policy:

============================
Datamodel Deprecation Policy
============================

As the Synapse Data Model has grown and evolved over time, Vertex has found the need
to deprecate model elements which are no longer useful. These elements may represent
relationships which are better captured with newer elements; concepts which are better
represented by convention; or other issues. As such, model elements (types, forms,
and properties) which are deprecated should no longer be used for new data modeling.
Deprecated model elements will be removed in a future Synapse release, no earlier than
``v3.0.0``.

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

Deprecated Model Elements
-------------------------

The following elements are deprecated.

Types
+++++

- `file:string`
    - -(refs)> it:dev:str
- `it:reveng:funcstr`
    - Please use the `:strings` array property on the `it:reveng:function` form.
- `lang:idiom`
    - Please use `lang:translation` instead.
- `lang:trans`
    - Please use `lang:translation` instead.
- `ou:hasalias`
    - `ou:hasalias` is deprecated in favor of the `:alias` property on `ou:org` nodes.
- `ou:meet:attendee`
    - `ou:meet:attendee` has been superseded by `ou:attendee`. `ou:attendee` has the `:meet` property to denote what meeting the attendee attended.
- `ou:conference:attendee`
    - `ou:conference:attendee` has been superseded by `ou:attendee`. `ou:attendee` has the `:conference` property to denote what conference the attendee attended.
- `ou:conference:event:attendee`
    - `ou:conference:attendee` has been superseded by `ou:attendee`. `ou:attendee` has the `:conference` property to denote what conference event the attendee attended.
- `ou:member`
    - `ou:member` has been superseded by `ou:position`.
- `ps:persona`
    - Please use the `ps:person` or `ps:contact` types.
- `ps:person:has`
    - Please use a light edge.
- `ps:persona:has`
    - Please use `ps:person` or `ps:context` in combination with a light edge.
- `inet:ssl:cert`
    - `inet:ssl:cert` is deprecated in favor of `inet:tls:servercert` and `inet:tls:clientcert`.

Forms
+++++

Consistent with the deprecated types, the following forms are deprecated:
- `file:string`
- `it:reveng:funcstr`
- `lang:idiom`
- `lang:trans`
- `ou:hasalias`
- `ou:meet:attendee`
- `ou:conference:attendee`
- `ou:conference:event:attendee`
- `ou:member`
- `ps:person:has`
- `ps:persona`
- `ps:persona:has`
- `inet:ssl:cert`

Properties
++++++++++

- `ps:person`
    - `:img`
        - `ps:person:img` has been renamed to `ps:person:photo`.

- `it:prod:soft`
    - `author:org`, `author:acct`, `author:email`, and `author:person`
        - These properties have been collected into the `it:prod:soft:author` property, which is typed as a `ps:contact`.

- `media:news`
    - `:author`
        - The `media:news:author` property has been superseded by the array property of `media:news:authors`, which is an array of type `ps:contact`.

- `file:subfile`
    - `:name`
        - The `file:subfile:name` property has been superseded by the property `file:subfile:path`, which is typed as `file:path`.

- `ou:org`
    - `:naics` and `:sic`
        - The `ou:org:naics` and `ou:org:sic` properties has been collected into the `ou:org:industries` property, which is an array of type `ou:industry`.
    - `:has`
        - Please use a light edge.

- `risk:attack`
    - `:actor:org`
        - Please use the `:attacker` `ps:contact` property to allow entity resolution.
    - `:actor:person`
        - Please use the `:attacker` `ps:contact` property to allow entity resolution.
    - `:target:org`
        - Please use the `:target` `ps:contact` property to allow entity resolution.
    - `:target:person`
        - Please use the `:target` `ps:contact` property to allow entity resolution.

- `ou:campaign`
    - `:type`
        - Please use the `:camptype` `taxonomy` property.

- `it:host`
    - `:manu`
        - This property has been superseded by the `it:prod:hardware:make` property, which is typed as `ou:name`.
    - `:model`
        - This property has been superseded by the `it:prod:hardware:model` property, which is typed as string.

- `it:exec:proc`
    - `:user`
        - Please use the `:account` `it:exec:proc` property to link processes to users.

- `it:prod:hardware`
    - `:make`
        - The `:make` property has been superseded by the properties `it:prod:hardware:manufacturer` and  `it:prod:hardware:manufacturer:name`, which are typed as `ou:org` and `ou:name` respectively.
