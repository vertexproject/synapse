.. _vtx_300_devops-logging:

Logging
=======

Two logging defaults changed for Synapse 3.x: containers now emit structured JSON logs by default,
and log timestamps are rendered as ISO-8601 UTC with microsecond precision.

Structured logging on by default
--------------------------------

What changed
    Synapse Docker containers now emit JSON structured logging output by default. The
    ``synsrc/docker/images/synapse/Dockerfile`` sets ``ENV SYN_LOG_STRUCT="true"``, so the
    service variants built from it log structured JSON out of the box.

    In 2.x, containers emitted unstructured text logs by default and structured JSON was opt-in by
    setting the ``SYN_LOG_STRUCT=true`` environment variable. This change flips the *container*
    default only; the library default when ``SYN_LOG_STRUCT`` is unset is unchanged.

Why
    Structured logs contain the log message, level, time, and metadata about where the message
    came from, and are designed to be easy to ingest and index into third party log collection
    platforms. Structured output is the sensible default for the containerized deployments most
    operators run.

What you need to do
    If you consume container logs, expect JSON on stdout by default and update any pipelines that
    parsed the old plaintext output accordingly. To keep unstructured text output, set the
    ``SYN_LOG_STRUCT=false`` environment variable on the container.

    .. code-block:: bash

        # 3.x container default: JSON structured logs

        # opt back out to unstructured text:
        SYN_LOG_STRUCT=false

ISO-8601 UTC microsecond timestamps
-----------------------------------

What changed
    Log timestamps are now rendered in UTC as ISO-8601 with microsecond
    precision and a trailing ``Z`` (for example ``2026-06-25T13:42:07.123456Z``).
    ``synapse.lib.logging.JsonFormatter`` adds a ``formatTime()`` override that
    builds the timestamp from ``datetime.datetime.fromtimestamp(record.created,
    tz=datetime.timezone.utc)``. This affects both the structured JSON logs (the
    ``time`` field) and the unstructured text logs, because ``TextFormatter``
    subclasses ``JsonFormatter`` and its ``%(asctime)s`` field is produced by the
    same override.

    In 2.x ``JsonFormatter`` had no ``formatTime`` override and inherited the
    standard library ``logging.Formatter.formatTime``, which emitted local-time
    timestamps with comma-separated milliseconds (for example
    ``2026-06-25 09:42:07,123``).

Why
    UTC microsecond timestamps remove timezone ambiguity in aggregated logs, give
    consistent ordering across hosts, and match the move to microsecond-precision
    timestamps elsewhere in 3.x.

What you need to do
    Update any log-ingestion or parsing pipelines (SIEM, fluentd/vector grok
    patterns, dashboards) that assumed local-time, millisecond, comma-separated
    timestamps. By default expect ``YYYY-MM-DDTHH:MM:SS.ffffffZ`` in UTC.

    The ``SYN_LOG_DATEFORMAT`` environment variable still maps to the formatter
    ``datefmt``, but with the override a custom ``datefmt`` is now applied via
    ``dt.strftime(datefmt)`` against a UTC ``datetime``. If you set a custom
    format and want sub-second precision, you must include ``%f``.

    .. code-block:: bash

        # 2.x default text log timestamp (local time, ms, comma)
        # 2026-06-25 09:42:07,123 [INFO] cortex started ...

        # 3.x default (UTC, microseconds, ISO-8601 'Z')
        # 2026-06-25T13:42:07.123456Z [INFO] cortex started ...

        # custom UTC format (include %f for microseconds):
        export SYN_LOG_DATEFORMAT='%Y-%m-%dT%H:%M:%S.%fZ'
