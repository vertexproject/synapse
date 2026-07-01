.. _vtx_300_datamodel-timestamps:

Microsecond Timestamps and ISO-8601 Repr
=========================================

In 3.0.0 the time type and time utilities operate in epoch microseconds rather than epoch
milliseconds, and the string representation of time values is now ISO 8601 instead of the
legacy ``YYYY/MM/DD HH:MM:SS.mmm`` format.

What changed
    Time values now store and convert epoch microseconds rather than milliseconds, and the
    ``time``, ``ival``, and ``duration`` types default to microsecond precision. Microsecond is
    now the base duration unit, and is available as a precision level alongside the existing
    millisecond level.

    Concurrently, the string representation of a time value -- which backs ``$node.repr(...)``
    of a time property, ``$lib.repr(...)`` of a time value, and node display -- changed from
    ``2021/01/15 03:04:05.678`` to ISO 8601, e.g. ``2021-01-15T03:04:05.678Z``. Sub-second
    precision in the repr is now up to six fractional digits (trailing zeros are stripped).

Why
    ISO 8601 is the unambiguous, widely-interoperable datetime format. Microsecond precision
    avoids silently losing accuracy when ingesting data -- such as network flow timestamps --
    that is more precise than milliseconds, as 2.x millisecond storage did.

What you need to do
    Anywhere you work with raw epoch integers (ingesting or exporting timestamps, computing
    durations, or comparing to stored time values), provide and interpret microseconds rather
    than milliseconds. A 2.x value of N milliseconds is N times 1000 microseconds. Time props
    still accept human and relative strings (``now``, ``2023``, ``?``, ``*``) unchanged.

    ::

        // 2.x: epoch millis
        $tick = (1700000000000)

        // 3.x: epoch micros
        $tick = (1700000000000000)

    Update any parsing or formatting that assumed the old repr. Prefer reading time values via
    the type rather than string-matching the repr.

    ::

        // 2.x repr of a time property (pass the property name)
        $ts = $node.repr(.created)   // e.g. "2021/01/15 03:04:05.678"

        // 3.x repr of a time property (pass the property name)
        $ts = $node.repr(.created)   // e.g. "2021-01-15T03:04:05.678Z" (ISO 8601, micros)
