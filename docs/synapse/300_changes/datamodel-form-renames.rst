.. _vtx_300_datamodel-form-renames:

Form and Property Renames
=========================

Synapse 3.0.0 renames and relocates a number of forms and type-taxonomies for naming
consistency and to push shared behavior onto interfaces. Update your Storm to the new names;
existing data is reconciled when a Cortex is migrated to 3.x. The entries below are ordered
roughly most-common first.

.. note::

    The most significant name changes are described below, but this is not a complete list of
    changes.

Hash forms move under ``crypto:hash:*``
---------------------------------------

What changed
    The top-level 2.x hash forms ``hash:md5``, ``hash:sha1``, ``hash:sha256``, ``hash:sha384``, and
    ``hash:sha512`` are renamed to ``crypto:hash:md5`` / ``crypto:hash:sha1`` / ``crypto:hash:sha256`` /
    ``crypto:hash:sha384`` / ``crypto:hash:sha512``. The 3.x forms are hex types implementing the
    ``crypto:hash`` and ``meta:observable`` interfaces. Hash-valued properties are now typed
    ``crypto:hash:*`` (for example ``file:bytes:md5`` is typed ``crypto:hash:md5`` and
    ``file:bytes:sha256`` is typed ``crypto:hash:sha256``).

Why
    This consolidates all hash primitives under the ``crypto`` namespace alongside the rest of the
    cryptography model and gives them the observable interface (``:seen``).

What you need to do
    Replace the old ``hash:*`` form names with ``crypto:hash:*``. Existing nodes are reconciled when
    a Cortex is migrated to 3.x. Properties that were typed to the old forms still accept a raw hex
    string, so only the form name changes.

    ::

        // 2.x
        hash:sha256=ad9f...

        // 3.x
        crypto:hash:sha256=ad9f...

Batch form and taxonomy renames
-------------------------------

What changed
    A batch of forms and type-taxonomies were renamed. Verified renames include:

    - ``it:account`` -> ``it:host:account``
    - ``it:group`` -> ``it:host:group``
    - ``it:dev:regkey`` -> ``it:os:windows:registry:key``
    - ``it:dev:regval`` -> ``it:os:windows:registry:entry``
    - ``it:prod:softname`` -> ``it:softwarename``
    - ``it:prod:hardware`` -> ``it:hardware``
    - ``it:hosturl`` -> ``it:exec:fetch``
    - ``it:prod:soft`` / ``it:prod:softver`` / ``risk:tool:software`` -> ``it:software``
    - ``it:prod:hardwaretype`` / ``it:hardwaretype`` -> ``it:hardware:type:taxonomy``
    - ``risk:tool:software:taxonomy`` -> ``it:software:type:taxonomy``
    - ``inet:whois:rec`` -> ``inet:whois:record``
    - ``inet:cidr4`` / ``inet:cidr6`` -> ``inet:net`` (``inet:cidr`` is now a CIDR-aligned
      subtype of ``inet:net``, and the 2.x range forms ``inet:net4`` / ``inet:net6`` are
      likewise superseded by ``inet:net``; see :ref:`vtx_300_datamodel-ip-unification`)
    - ``geo:place:taxonomy`` -> ``geo:place:type:taxonomy``
    - ``ou:contract`` -> ``doc:contract``
    - ``ou:conttype`` -> ``doc:contract:type:taxonomy``
    - ``ou:orgtype`` -> ``ou:org:type:taxonomy`` (the ``:orgtype`` prop becomes ``:type``)
    - ``ou:jobtype`` -> ``ou:job:type:taxonomy``
    - ``biz:dealtype`` -> ``biz:deal:type:taxonomy``
    - ``biz:prodtype`` -> ``biz:product:type:taxonomy``
    - ``meta:event:taxonomy`` -> ``meta:event:type:taxonomy``
    - ``meta:timeline:taxonomy`` -> ``meta:timeline:type:taxonomy``

Why
    Naming consistency: type-taxonomies converge on the ``:type:taxonomy`` suffix, OS-specific forms
    move under ``it:os:windows:*``, and several forms relocate to a more appropriate namespace (for
    example contracts move to ``doc:*``).

What you need to do
    Update Storm to the new form names. Existing data is reconciled when a Cortex is migrated
    to 3.x.

    ::

        // 2.x
        it:dev:regkey="HKLM\\Software\\Foo"
        it:prod:softname="acme tool"

        // 3.x
        it:os:windows:registry:key="HKLM\\Software\\Foo"
        it:softwarename="acme tool"

``ps:contact`` renamed to ``entity:contact``
--------------------------------------------

What changed
    The 2.x ``ps:contact`` form is renamed to ``entity:contact`` and reconciled at Cortex
    migration time. The 3.x ``entity:contact`` is an entity form whose properties are now
    supplied by shared interfaces rather than declared directly on the form -- for example
    ``:name`` / ``:names``, ``:id``, ``:bio``, ``:photo``, ``:lifespan``, and ``:seen``.

Why
    Contacts are not specific to persons or personas; but are instead about entities, which
    may represent organizations, people, etc. Using the entity namespace to store contact
    information further reinforces that concept.

What you need to do
    Replace ``ps:contact`` with ``entity:contact``. Existing nodes are reconciled when a Cortex
    is migrated to 3.x. Be aware that some properties were reshaped by the interface model --
    confirm the exact target property per field rather than assuming a flat one-to-one mapping.
    Verified reshapes include ``:dob`` / ``:dod`` -> ``:lifespan`` (an ival, settable via
    ``:lifespan:min`` / ``:lifespan:max``) and ``:asof`` -> ``:seen``.

    ::

        // 2.x
        [ ps:contact=* :name="bob smith" ]

        // 3.x
        [ entity:contact=({"name": "bob smith"}) ]

``media:news`` renamed to ``doc:report``
----------------------------------------

What changed
    The 2.x ``media:news`` form is renamed to ``doc:report``. The 3.x ``doc:report`` declares
    no direct properties of its own -- fields such as
    ``:title``, ``:body``, ``:desc``, ``:type``, and the publishing fields (``:published`` /
    ``:publisher``) now come from interfaces (note there is no ``:name`` or ``:summary`` prop on
    ``doc:report``; the 2.x ``media:news:title`` maps to ``:title``). The ``media:news:taxonomy``
    type-taxonomy is renamed to ``doc:report:type:taxonomy``.

Why
    Reports are documents; folding ``media:news`` into the ``doc:*`` document family lets reports share
    the publishing and document interfaces with contracts and other documents.

What you need to do
    Replace ``media:news`` with ``doc:report``; existing data is reconciled when a Cortex is
    migrated to 3.x. Use ``doc:report:type:taxonomy`` instead of
    ``media:news:taxonomy``. Because the report fields are now interface-supplied, verify each
    property name against the generated data model docs before porting ingest.

    ::

        // 2.x
        [ media:news=* :title="APT1 report" ]

        // 3.x
        [ doc:report=({"title": "APT1 report"}) ]

``ou:campaign`` renamed to ``entity:campaign``
----------------------------------------------

What changed
    The 2.x ``ou:campaign`` form is renamed to ``entity:campaign`` (a guid form that implements
    ``entity:activity``, so it carries an actor, an activity period, and the shared reporting
    properties). The ``ou:camptype`` taxonomy is renamed to ``entity:campaign:type:taxonomy``.

Why
    A campaign is an activity that is not tied to a single org, so it moves into the entity
    layer where it can be linked to any actor.

What you need to do
    Use ``entity:campaign`` and set ``:actor`` (from ``entity:activity``) rather than a single
    org reference, and ``:type`` from ``entity:campaign:type:taxonomy``. Treat this as a remodel
    -- there is no automatic one-to-one form rename; confirm the migration path for existing
    campaign nodes.

    ::

        // 2.x
        [ ou:campaign=* :name="op cloudfall" :camptype=cyber ]

        // 3.x
        [ entity:campaign=({"name": "op cloudfall"}) :type=cyber :actor={ ou:org:name=apt99 } ]

Goals remodeled: ``entity:goal`` and ``entity:motive``
------------------------------------------------------

What changed
    The 2.x ``ou:goal`` form is renamed to ``entity:goal``, and how goals attach to other nodes
    changes in two ways:

    - The ``:goal`` / ``:goals`` properties are removed from activity forms (those that
      implement ``entity:activity``, such as the former ``ou:campaign`` -> ``entity:campaign``,
      ``risk:attack``, and so on). An activity now links to a goal with an
      ``entity:activity -(supported)> entity:goal`` edge.
    - Actors (``entity:actor``) link to a goal through the new ``entity:motive`` form rather
      than the 2.x ``-(has)>`` edge. An ``entity:motive`` records an ``:actor`` holding a
      ``:goal`` over a ``:period`` (it implements ``entity:activity``).

Why
    Activities do not have goals -- actors do. Separating the two lets an activity state which
    goal it supported (via the ``-(supported)>`` edge) while an actor's goal is modeled in its
    own right. ``ou:goal`` was also arbitrarily placed under ``ou:*`` even though persons and
    other actors have goals, so it moved to ``entity:goal``. 3.x further distinguishes a goal
    (an objective to be achieved) from a motive (an actor holding a specific goal for a period
    of time): ``entity:motive`` links an ``:actor`` to a ``:goal`` for a ``:period``, which lets
    goals be generic or specific and lets you model actors with differing goals and goals that
    change over time.

What you need to do
    Replace ``ou:goal`` with ``entity:goal``. Drop any ``:goal`` / ``:goals`` property on an
    activity form and instead add an ``entity:activity -(supported)> entity:goal`` edge. Replace
    a 2.x actor-to-goal ``-(has)>`` edge with an ``entity:motive`` node that sets ``:actor``,
    ``:goal``, and ``:period``.

    ::

        // 2.x: a goal on the activity, and an actor "has" a goal
        [ ou:campaign=$campiden :goals+=$goaliden ]
        ou:org=$orgiden [ +(has)> { ou:goal=$goaliden } ]

        // 3.x: the activity supports a goal; an actor's goal is an entity:motive
        entity:campaign=$campiden [ +(supported)> { entity:goal=$goaliden } ]
        [ entity:motive=* :actor={ ou:org=$orgiden } :goal=$goaliden :period=(2023, ?) ]

New ``ind:*`` industry model
----------------------------

What changed
    A new top-level ``ind:*`` model introduces ``ind:industry`` as the home for industry data,
    distinct from the 2.x ``ou:industry`` form. It includes ``ind:name`` (typed ``base:name``),
    ``ind:industry:id``, and ``ind:industry:type:taxonomy``.

Why
    Industry classification is cross-cutting -- orgs, campaigns, and threats reference it -- so it
    warrants its own model rather than living under ``ou:*``.

What you need to do
    When modeling industry sectors in 3.x, use the ``ind:industry`` family instead of ``ou:industry``.
    The ``gen.ou.industry`` Storm command is renamed to ``gen.industry`` and now builds an
    ``ind:industry`` node. Verify exact property names against the generated data model docs before
    porting industry ingest.

    ::

        // 2.x -- built ou:industry
        gen.ou.industry "Aerospace"

        // 3.x -- builds ind:industry
        gen.industry "Aerospace"
