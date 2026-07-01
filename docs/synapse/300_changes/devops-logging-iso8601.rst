.. _vtx_300_devops-logging-iso8601:

ISO-8601 UTC Microsecond Logging
================================

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
