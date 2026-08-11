<a id="vtx_300_storm-package-docs-removed"></a>


# Package definition `docs` key removed

What changed

:   The Storm package definition (pkgdef) schema no longer has a `docs` key. A package's documentation can no longer travel as inline `title`/`path`/`content` entries in the pkgdef itself.

Why

:   Package documentation is being moved onto the same sha256-addressed package files pipeline that already ships other package assets.

What you need to do

:   Delete the `docs:` block from a hand-authored package prototype.

    ```yaml
    # 2.x
    docs:
      - title: User Guide
        path: docs/_build/userguide.md
      - title: Changelog
        path: docs/_build/changelog.md

    # 3.x
    # (no docs: key)
    ```

    There is no drop-in replacement for inline `docs` content. Build a package's `docs/` source tree with
    `synapse.tools.storm.pkg.doc <pkgfile>`: it renders every ```mdstorm directive at build time and writes the
    result to `files/docs` next to the package's own pkgdef, so the built pages travel with the package as
    ordinary sha256-addressed files (see [Storm Package Files](../devguides/power-ups.md)) rather than as inline
    pkgdef content.
