.. _vtx_300_devops-nexus-deconfliction:

Deconflicted Node Edits in the Nexus Log
========================================

What changed
    In 2.x, ``saveNodeEdits`` passed the raw requested edits straight to the
    Nexus (``saveToNexs('edits', edits, meta)``); deconfliction -- dropping
    edits that make no change -- happened afterward inside the
    ``_storNodeEdits`` push handler, and the deconflicted edits were written to
    a separate per-layer node-edit log slab (the ``nodeeditlog`` on the layer's
    ``nodeeditslab``), gated by the ``logedits`` option.

    In 3.x, ``saveNodeEdits`` first deconflicts the proposed edits, then only the
    deconflicted edits are sent to the Nexus via
    ``saveToNexs('edits', realedits, meta)``. The per-layer
    ``nodeeditlog`` slab is gone. ``syncNodeEdits`` now reads node edits
    directly from the Cortex Nexus log (``self.core.getNexusChanges``), filtered
    to entries where ``item[0]`` is the layer iden and ``item[1]`` is
    ``'edits'``, and the layer edit offset returned by ``getEditIndx`` is simply
    the Nexus offset.

    The local edit form is also keyed by NID rather than BUID.

Why
    Storing only deconflicted edits once, in the Nexus log -- rather than raw
    edits in the Nexus plus a deduplicated copy in every layer's own log --
    reduces storage utilization and removes a class of per-layer write
    amplification. It also lets downstream consumers read the Cortex Nexus log
    directly instead of aggregating per-layer edit logs.

What you need to do
    For most users this is transparent. Integrators that consume node edits
    should read the Cortex Nexus log directly rather than aggregating each
    layer's edit log. The Nexus log now contains already-deconflicted edits
    (no redundant no-op edits), and the local edit form is keyed by NID, not
    BUID. The ``logedits`` configuration option that controlled the old
    per-layer edit log no longer exists -- remove it from your layer
    configuration.
