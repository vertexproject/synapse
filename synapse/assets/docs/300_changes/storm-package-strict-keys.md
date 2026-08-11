<a id="vtx_300_storm-package-strict-keys"></a>


# Package definitions reject unknown keys

What changed

:   The Storm package definition (pkgdef) schema and its nested object schemas no longer accept unknown keys. A pkgdef carrying a misspelled or stray key now fails validation with a `SchemaViolation` at `reqValidPkgdef()` time -- when the package is built by `synapse.tools.storm.pkg.gen`, and again when it is added to a Cortex -- rather than being silently accepted. This applies to the top level of the pkgdef and to:

    - `build`, `metadata.codesign`, `author`, `logo`.
    - `modules` entries, `commands` entries, and command `cmdargs` opts, `cmdinputs` entries, and `forms` hints.
    - `configvars` entries, `perms` entries, `inits`, and `dependencies` / `conflicts` entries.

    These values are intentionally left open and continue to accept arbitrary keys, since they hold package-defined or externally-validated data:

    - `modules[].modconf` and `commands[].cmdconf` -- package-defined configuration.
    - `inits.versions[].queryopts` -- Storm query options.
    - `vaults.<type>.schema` -- a JSON Schema, validated as a schema in its own right.
    - `optic` -- owned by Optic and validated against Optic's own generated schema.

    The `optic` key is now declared in the pkgdef schema. It was previously accepted only because the top level allowed unknown keys.

Why

:   A permissive schema turned authoring typos into silent, hard-to-trace misbehavior. A command definition that used `descr` instead of `desc` validated and loaded successfully, but its autocomplete brief silently fell back to `"No description"`; the mistake only surfaced through an unrelated UI test. Rejecting unknown keys makes that class of mistake fail immediately, at the point where it can be fixed.

What you need to do

:   Build your package with `synapse.tools.storm.pkg.gen` and fix any key it rejects. A rejected key is almost always one of:

    - A typo -- `deafult` for `default`, `time` for `type`, `descr` for `desc` (see [Package description fields renamed to `desc`](storm-package-command-desc.md#vtx_300_storm-package-command-desc)).
    - A key that no longer does anything in 3.x. Notably, `asroot` on a *command* definition is not consumed by the Cortex; declare a module's required privileges via the `asroot:perms` key on the `modules` entry instead, and gate commands with `perms`. The 2.x `synapse_version` and `synapse_minversion` keys are likewise gone -- declare the requirement under `dependencies.synapse.version`. The `optic_version` key is gone the same way, at both the `optic` block and the per-Workflow level -- declare it under `dependencies.synapse-enterprise-optic.version`. Note that specifier must not be epoch-scoped, since the Optic package version carries no epoch.

    ```yaml
    # rejected in 3.x
    commands:
      - name: mypkg.mycmd
        storm: ''
        desc: Do the thing.
        asroot: true
        cmdargs:
          - - --timeout
            - type: int
              deafult: 30
              help: How long to wait.

    # 3.x
    commands:
      - name: mypkg.mycmd
        storm: ''
        desc: Do the thing.
        perms:
          - [ power-ups, mypkg, user ]
        cmdargs:
          - - --timeout
            - type: int
              default: 30
              help: How long to wait.
    ```


<a id="vtx_300_storm-package-derived-keys"></a>


# Cortex-derived keys are no longer author supplied

What changed

:   Loading a package no longer modifies the package definition at all. The definition the Cortex stores is identical to the one it was given.

    Keys the Cortex used to write into the pkgdef are now derived where they are used. Two are also rejected if a package supplies them:

    - `commands[].pkgname`. The Cortex stamped the package name onto every command definition before validating it. The providing package is now passed to the command registration directly, so the key is neither needed nor accepted.
    - `graphs[].iden`, `graphs[].scope` and `graphs[].power-up`. These are derived when the package loads, onto the Cortex's own copy of the graph definition. A package graph declares only *what the graph is*; its identity and provenance belong to the Cortex.

    A package graph is still addressable by the same derived iden, `$lib.guid(<pkgname>, <graphname>)`, so saved references keep working.

    The package metadata handed to running Storm code is unchanged, but is now assembled onto the Cortex's own copy rather than written back into the package:

    - A module still receives `$modconf.pkgmeta`, with `modname` and `pkgname`.

    A package that declares its own `modconf.pkgmeta` still has it respected, exactly as before. The difference is only that a package which did *not* declare these no longer grows them, so `$lib.pkg.get()` and the stored definition show what the author actually wrote.

    Relatedly, validating a package no longer writes schema defaults into it. The graph display options whose absence would change projection behavior -- `refs`, `edges`, `edgelimit`, `filterinput` and `yieldfiltered` -- are populated by `synapse.tools.storm.pkg.gen` at build time so a built package is explicit about them, and the Cortex fills in any which are missing on its own copy as the package loads. They remain optional: a package authored at runtime via `$lib.pkg.add()` need not spell them out.

    A package `version` must now be a semver **string**. A version tuple or list was previously converted in place, which meant modifying the package; it is now rejected. This only affects package definitions built by hand -- `version: 1.2.3` in a package YAML already loads as a string.

Why

:   A Storm package's code signature is verified against the definition as it was signed, but the Cortex then mutated that definition and persisted the mutated copy. The stored package no longer matched what was signed, which made re-verifying a stored package impossible. Deriving instead of stamping keeps the stored package byte-identical to the signed one.

What you need to do

:   Rebuild with `synapse.tools.storm.pkg.gen`. Only hand-rolled package definitions need edits: drop `pkgname` from command definitions, drop `iden` / `scope` / `power-up` from graph definitions, and give `version` as a string (`'1.2.3'` rather than `(1, 2, 3)`).
