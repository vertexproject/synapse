<a id="vtx_300_storm-package-command-desc"></a>


# Package description fields renamed to `desc`

What changed

:   Every human-readable description field on a Storm package definition (pkgdef) that was previously named `descr` is now named `desc`, matching the `desc` key already used elsewhere in the pkgdef (for example the top-level package `desc`, and the `desc` on dependencies/conflicts and vault/endpoint entries). This applies to:

    - Command definitions: each entry in a package's `commands` list.
    - Optic node actions: each entry in `optic.actions`.
    - Optic Spotlight extractors: each entry in `optic.spotlight.extractors`.

Why

:   `descr` and `desc` had drifted into inconsistent use across different parts of the pkgdef schema for the same concept -- a human-readable description. Standardizing on `desc` everywhere removes the need to remember which spelling a given section uses.

What you need to do

:   Rename `descr` to `desc` in your package YAML/dict wherever it appears on a command definition, an `optic.actions` entry, or an `optic.spotlight.extractors` entry. A package that still supplies `descr` in one of these spots fails pkgdef schema validation (`SchemaViolation`) rather than being silently accepted with a missing description.

    ``` text
    # 2.x
    commands:
      - name: mypkg.mycmd
        storm: ''
        descr: Do the thing.

    optic:
      actions:
        - name: enrich
          storm: mypkg.enrich
          forms: [ inet:fqdn ]
          descr: Enrich an inet:fqdn node.
      spotlight:
        extractors:
          - name: my extractor
            query: '[ it:dev:str=$text ]'
            descr: Make a dev str from the selection.

    # 3.x
    commands:
      - name: mypkg.mycmd
        storm: ''
        desc: Do the thing.

    optic:
      actions:
        - name: enrich
          storm: mypkg.enrich
          forms: [ inet:fqdn ]
          desc: Enrich an inet:fqdn node.
      spotlight:
        extractors:
          - name: my extractor
            query: '[ it:dev:str=$text ]'
            desc: Make a dev str from the selection.
    ```

:   This is a pure pkgdef authoring change and does not affect data already stored in a Cortex. It does, however, affect an existing Optic user's saved workspace node actions and Spotlight extractors, since those are read/written under `desc` now. Optic migrates any already-saved entry that still carries the old `descr` key to `desc` automatically the next time it is loaded, so no manual action is required.
