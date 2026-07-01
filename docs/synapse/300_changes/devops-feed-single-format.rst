.. _vtx_300_devops-feed-single-format:

Single Feed Data Format
=======================

Cortex feed ingest is standardized on a single packed-node format. The pluggable feed-format
registry is gone, and the ``addFeedData`` API and feed CLI changed accordingly.

What changed
    In 2.x the Cortex maintained a registry of named feed functions (``setFeedFunc`` /
    ``getFeedFunc`` / ``getFeedFuncs``), and ``addFeedData`` took a leading format-name argument:
    ``CellApi.addFeedData(name, items, *, viewiden=None)`` and
    ``Cortex.addFeedData(name, items, *, viewiden=None)``. The built-in ``syn.nodes`` format
    ingested packed nodes.

    In 3.x the registry is removed and the format-name argument is dropped. The telepath-facing
    signature is now ``addFeedData(items, *, viewiden=None, reqmeta=True)`` and the cell-level method
    is ``addFeedData(items, *, user=None, viewiden=None)``. Data is always the packed-node format.
    When ``reqmeta`` is ``True`` (the telepath CellApi default), the first item must be an
    export-meta header dict, which is validated by ``reqValidExportStormMeta`` (``vers`` must be
    ``1`` and ``synapse_ver`` must satisfy ``>=3.0.0b1,<4.0.0``). The HTTP ``/api/v3/feed`` endpoint
    has no ``reqmeta`` toggle and always requires the export-meta header.

    The CLI ``synapse.tools.cortex.feed`` dropped its ``--format`` / ``-f`` option. It treats
    ``.mpk`` and ``.nodes`` inputs as packed-node files, reads the export-meta header from the file,
    and passes ``reqmeta`` accordingly. Other input types (``.json``, ``.jsonl``, ``.yaml``) are fed
    without a meta header (``reqmeta=False``).

Why
    Named feed functions and multiple feed formats were rarely used and added API surface. Settling
    on the single packed-node format simplifies the API and the tool, and lets ingest validate the
    data against a versioned export-meta header.

What you need to do
    Stop passing a format name to ``addFeedData`` over telepath/HTTP -- pass just the items list
    (and keyword ``viewiden``). If your items do not include an export-meta header, pass
    ``reqmeta=False``. If you fed any non-``syn.nodes`` format via a custom feed function, convert
    your ingest to produce packed nodes. Drop ``--format`` / ``-f`` from any
    ``synapse.tools.cortex.feed`` invocation; the tool infers the format from the file extension.

    .. code-block:: python

        # 2.x telepath -- format name was the first argument
        await prox.addFeedData('syn.nodes', items, viewiden=viewiden)

        # 3.x telepath -- no format name; items without a meta header
        await prox.addFeedData(items, viewiden=viewiden, reqmeta=False)

    .. code-block:: bash

        # 2.x CLI -- explicit --format
        python -m synapse.tools.cortex.feed -c cell://./core --format syn.nodes data.nodes

        # 3.x CLI -- format inferred from the .nodes/.mpk extension
        python -m synapse.tools.cortex.feed -c cell://./core data.nodes
