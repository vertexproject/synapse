.. _vtx_300_admin-core-modules-removed:

Cortex Core Modules Removed
===========================

Cortexes no longer support in-process Python Core modules. The deprecated ``modules`` config option and
the associated ``CoreModule`` loading APIs have been removed in 3.0.0.

What changed
    The Cortex no longer loads Core modules. In 2.x the Cortex accepted a ``modules`` config key -- a list of
    Python module classes loaded into the Cortex process -- and exposed the ``getCoreMod()``, ``getCoreMods()``,
    and ``loadCoreModule()`` APIs, backed by ``synapse.lib.modules`` and ``synapse.lib.module``.

    In 3.x the ``modules`` confdef has been removed from the Cortex config schema, the
    ``getCoreMod()``/``getCoreMods()``/``loadCoreModule()`` APIs are gone, and ``synapse/lib/module.py`` and
    ``synapse/lib/modules.py`` no longer exist.

    Note: the ``modules`` key inside a *Storm package* definition is unrelated to this change and is unaffected.

Why
    Core modules could run arbitrary Python inside the Cortex process, significantly changing behavior and
    introducing performance, stability, and security risk. Functionality previously delivered via a Core module
    can now be implemented with a Storm package or other Synapse features, so supporting in-process Python
    modules was an unnecessary risk.

What you need to do
    Remove the ``modules`` key from your Cortex ``cell.yaml`` (or other config) before upgrading. Reimplement any
    custom Core-module behavior as a Storm package (commands/modules) or as a Storm service.

    .. code-block:: yaml

        # 2.x cell.yaml
        modules:
          - myorg.synmods.MyCoreModule

        # 3.x cell.yaml -- remove the key entirely
        # (custom logic moves to a Storm package)
