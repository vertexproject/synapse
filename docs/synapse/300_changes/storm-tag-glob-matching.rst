.. _vtx_300_storm-tag-glob-matching:

Tag Glob Zero-Length Matching
=============================

Wildcards in tag glob expressions now allow zero-length matches instead of requiring at least one character. This affects every place tags are matched by glob, including the ``+#glob`` / ``-#glob`` filters, ``$node.tags(glob)``, ``$node.globtags(glob)``, and trigger tag globs.

What changed
    A tag glob wildcard can now match an empty (zero-length) portion. A single ``*`` matches one tag component (the text between dots), and ``**`` matches any run of characters, including dots, so it can span more than one component. In 2.x each wildcard required at least one character; in 3.x either can also match nothing.

    Concretely, for a node tagged only ``#foo``:

    - ``#foo*`` now matches ``#foo`` (the trailing ``*`` matches a zero-length component). In 2.x it did not match.
    - ``#foo**`` now matches ``#foo`` (the ``**`` matches zero characters). In 2.x it did not match.

    Note that ``#foo.*`` still does NOT match the bare tag ``#foo``: the literal ``.`` in the glob still requires a dot to be present. Only the wildcard component itself is now allowed to be empty.

Why
    The old behavior surprised users: a wildcard always forced at least one character, so a glob could fail to match a shorter tag that was otherwise a prefix of the pattern. Allowing zero-length matches makes the wildcard behave consistently regardless of whether the matched portion is empty.

What you need to do
    Audit any glob that relied on a wildcard forcing at least one character. In 3.x a trailing wildcard component will now also match when that component is empty, so globs like ``#foo*`` and ``#foo**`` will match a node tagged only ``#foo``. If you depended on requiring a non-empty segment, make the requirement explicit (for example, by matching against the more specific tag directly).

    ::

        // 2.x: node has only the tag #foo
        +#foo*         // does NOT match #foo (the * requires >=1 char)
        +#foo**        // does NOT match #foo (the ** requires >=1 char)

        // 3.x: node has only the tag #foo
        +#foo*         // NOW matches #foo (the * matches a zero-length component)
        +#foo**        // NOW matches #foo (the ** matches zero characters)

        // Unchanged in both 2.x and 3.x: the literal dot is still required
        +#foo.*        // does NOT match #foo
