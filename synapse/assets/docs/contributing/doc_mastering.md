<a id="synapse-document-mastering"></a>


# Synapse Doc Mastering

Documentation for creation and generation of documentation for Synapse.

## Generating Docs Locally

API documentation is automatically generated from docstrings, and additional docs may also be added to Synapse as well for more detailed discussions of Synapse subsystems.

A doc bundle builds one of two ways, depending on whether it belongs to a Storm package:

1.  Install synapse in develop mode (this assumes the environment already has any additional packages required for
    executing synapse code in it):

    ``` text
    # cd to your synapse checkout
    cd synapse
    python -m pip install -U -e .
    ```

2.  **A Storm package's own docs.** Build with `synapse.tools.storm.pkg.doc`, pointed at the package's pkgdef. The
    tool builds that package's `docs/` source tree and, by default, saves the result to `files/docs` next to the
    pkgdef so the built pages travel with the package as ordinary declared files; `--save` redirects the output
    elsewhere:

    ``` text
    # Go to your synapse repo
    cd synapse
    # Build a package's docs to _build instead of its files/docs
    python -m synapse.tools.storm.pkg.doc mypkg/mypkg.yaml --save _build
    ```

    **A docs/ tree with no pkgdef of its own** -- this `synapse` bundle and the enterprise `synapse-enterprise`
    bundle are the two examples -- instead builds with `synapse.tools.utils.doc`, given the source directory and
    the destination directory explicitly:

    ``` text
    # Build synapse's own docs/synapse/ into its committed bundle dir
    python -m synapse.tools.utils.doc docs/synapse synapse/assets/docs
    ```

    Either way the destination is a bundle's own canonical, **committed** directory -- not a throwaway preview
    copy -- so the result is reviewed and committed alongside the source change that prompted it (see
    `docs/Makefile` at the monorepo root for how CI builds and diff-checks every bundle at once).

3.  Now you can open the Markdown docs for browsing, or view `metadata.json` for the generated nav tree.

4.  To rebuild from scratch, just re-run the same command -- a build always starts from a clean staging copy of
    `docs/` (see `synapse.lib.mddocs.buildBundle`), merging the result into the destination without deleting any
    pre-existing static content there (see the docs/-vs-committed split below).

## Mastering Docs

Synapse documents are mastered as Markdown (`.md`) files. Storm examples are embedded using fenced code blocks named
` ```mdstorm `, ` ```mdstorm-setup `, and ` ```mdshell ` (processed by `synapse.tools.utils.mdstorm`), so the code is
run at the time of document generation. See `synsrc/docs/README.md` (a level above this bundle's own docroot,
`synsrc/docs/synapse/` -- not part of the built nav itself) for the full directive set.

**docs/ vs. the committed bundle dir.** `docs/` holds only files that carry one of these directives (or an
` ```mdtoc ` fence) -- a page whose content is entirely plain Markdown, and any non-Markdown file that is not
itself a directive's input (an image, etc. -- as opposed to a Storm package's own pkgdef yaml, consumed by an
` ```mdautodoc --stormpkg ` fence), lives instead
in the committed bundle dir (`synapse/assets/docs/` for this bundle) and is edited there directly. A build merges
its own output into that directory without touching what it never staged, so a plain page and a generated one sit
side by side in the built result, and ordinary relative Markdown links between them work exactly the same either
way.

In general, docs for Synapse fall into two categories: User guides and developer guides. User guides should be
mastered in `docs/synapse/userguides` and developer guides should be mastered in `docs/synapse/devguides`.
Additional top level sections may be added over time.

Once new documents are made, they need to be added to the appropriate ` ```mdtoc ` fence (the toctree replacement --
a fenced block listing child page paths, one per line). There are three index documents, all paths relative to the
`docs/synapse/` docroot:

- `index.md` - This controls top-level documentation ordering. It generally should not need to be edited unless
  adding a new top level document or adding an additional section to the second level Synapse directory.
- `userguide.md` - This controls the TOC ordering for user guides.
- `devguide.md` - The controls the TOC ordering for developer guides.
