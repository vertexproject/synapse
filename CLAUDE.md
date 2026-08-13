# CLAUDE.md - Synapse

## Project Overview

Synapse is a production-grade hypergraph-based intelligence analysis platform built in Python by The Vertex Project. It provides a distributed platform for collaborative, interdisciplinary intelligence analysis used by large, demanding, high-impact organizations like Fortune 50 and national governments. Core capabilities include a graph database (Cortex), distributed blob storage (Axon), service discovery (Aha), and the Storm query language DSL.

## Architecture

### Core Services

- **Cortex** (`synapse/cortex.py`) — Central intelligence data store. Hypergraph database with nodes, edges, layers, views. Executes Storm queries. Extends `s_cell.Cell`.
- **Axon** (`synapse/axon.py`) — Distributed blob/file storage with SHA256 content addressing. HTTP API for upload/download.
- **Aha** (`synapse/servers/aha.py`) — Service registry and resolver for distributed deployments.
- **JsonStor** (`synapse/servers/jsonstor.py`) — JSON document storage service.

### Key Subsystems

- **Cell** (`synapse/lib/cell.py`) — Base service class with auth, clustering, nexus replication, HTTP API, and telepath RMI support.
- **Telepath** (`synapse/telepath.py`) — Custom async RPC/RMI framework with SSL/TLS and AHA service discovery.
- **Storm** (`synapse/lib/storm.py`, `synapse/lib/parser.py`) — Query language DSL with Lark-based parser. ~50 stormlib modules in `synapse/lib/stormlib/`.
- **LMDB Slab** (`synapse/lib/lmdbslab.py`) — High-performance LMDB wrapper for persistent key-value storage.
- **Layer/View** (`synapse/lib/layer.py`, `synapse/lib/view.py`) — Layered data storage with snapshot/fork support.
- **Nexus** (`synapse/lib/nexus.py`) — Replication and synchronization for distributed deployments.
- **Data Model** (`synapse/datamodel.py`, `synapse/models/`) — 28+ domain models (cyber, geopolitical, economic, person, org, crypto, etc.).

### Core Beliefs

- Synapse is used in mission critical environments.
- All code must be high quality, high performance, and have thorough tests.
- Every change **MUST** update tests to prove the change works correctly.
- Synapse code has maintained backward compatible interfaces for many years. Do **NOT** break them.

## Code Conventions

### Import Style

Synapse uses a distinctive aliased import convention. Always follow this pattern:

```python
import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.cell as s_cell
import synapse.lib.storm as s_storm
import synapse.lib.stormtypes as s_stormtypes
```

The alias is always `s_` followed by the last segment of the module path.

### Style Rules

- **Async-first**: The codebase is heavily async. Use `async def` / `await` patterns throughout.
- **Is-None**: Use `if foo is None:` rather than `if foo:` for checking for None
- **Cond-Space**: Add a line of white space after a conditional block
- **Import-Order**: Standard library imports come first, then synapse imports. They **MUST** be ordered from shortest to longest and use alphanumeric sorting to break ties.
- **No-Unicode-Arrows**: Do **not** use unicode arrow characters (e.g. `→`, `←`, `⇒`) in code or comments.
- **Exc-Choice**: Raise `s_exc.BadArg` to reject input you know is bad (validation, missing/duplicate things the caller named, bad types/formats). Use `s_exc.StormRuntimeError` sparingly, only for failures that happen *after* the args are accepted and processed. Do not use the removed `BadOperArg`.

### Naming Conventions

- Module-level loggers: `logger = logging.getLogger(__name__)`
- Class names: CamelCase (e.g., `CortexApi`, `StormNode`)
- Methods/functions: camelCase (e.g., `addNode`, `getFormName`) — **not** snake_case
- Internal/private methods: underscore prefix `_methodName`
- Constants: ALL_CAPS in `synapse/lib/const.py`

### Serialization Vocabulary

These short names are **code vocabulary**: use them for identifiers, local
variables, and helper names. User facing text -- an `s_exc` `mesg=`, a changelog
entry, doc prose -- spells the term out instead.

A `tval` is the general form. An `ndef` and a `pdef` are `tval`s whose first
element is specifically a form or a property:

| Name | Long form | Shape |
|------|-----------|-------|
| `tval` | typed value | `(<type>, <valu>)` -- what `Type.normFromTypedValu()` takes, and what the poly tuple holds internally |
| `ndef` | node definition | `(<form>, <valu>)`, a `tval` whose type is a form |
| `pdef` | property definition | `(<prop>, <valu>)`, a `tval` whose type is a property |
| `pode` | packed node | `((<form>, <valu>), <info>)`, the serialization returned by `Node.pack()` |

Name a value for what it actually carries: reach for `ndef` or `pdef` only when
the first element is known to be a form or a property, and use `tval` when it is
any type name.

A doc may introduce the short form once -- "The packed node (pode) info dict ..."
-- and then use it inside code spans such as `pode[1]['props'][name]`.

Do not confuse any of these with a model **propdef**, which is the unrelated
`(<name>, <typedef>, <propinfo>)` triple consumed by
`datamodel.processPropdefs()`.

## Development Setup

```bash
pip install -U wheel pip setuptools
pip install -U -r requirements_dev.txt
pip install -U --upgrade-strategy=eager -e .
```

## Testing

```bash
# Run full test suite with parallelization
python -m pytest -n 8 --dist worksteal -v -rs synapse/tests/

# Run a specific test file
python -m pytest synapse/tests/test_cortex.py -v

# Run with coverage
COVERAGE_PROCESS_START=.coveragerc python -m pytest --cov synapse --cov-config=.coveragerc.main --cov-append synapse/tests/

# Run with nexus replay (replication testing)
SYNDEV_NEXUS_REPLAY=1 python -m pytest synapse/tests/
```

- Tests use pytest with pytest-xdist for parallel execution (8 workers).
- CI runs on CircleCI with Python 3.11 on xlarge instances.
- Tests must NOT bind to fixed ports (audited via `conftest.py` hook).
- VCR (vcrpy) is used for HTTP mocking in tests.
- Regression tests use a separate repo: `synapse-regression`.
- To detect whether code is currently executing inside a test, check `synapse.common.isTestRun()` (backed by the
  `PYTEST_CURRENT_TEST` envar pytest sets for the duration of each test). Prefer this over a hand-rolled "are we in
  CI"-style envar -- it needs no test-suite-side setup and is accurate for exactly the lifetime of one running test.

## Key Development CLI Tools

| Tool                            | Purpose |
|---------------------------------|---------|
| `synapse.tools.storm`           | Storm CLI |
| `synapse.tools.storm.pkg.gen`   | Storm package generation |
| `vtxtools.changelog synapse`    | Generate changelog entry (run from monorepo root) |
| `vtxtools.update_datamodel`     | Regenerate `docs/datamodel.md` — always run from the repo root after any data model change: `python -m vtxtools.update_datamodel` |

## Documentation

- Markdown docs in `docs/synapse/`. Sphinx has been removed; there is no `.rst`/`.rstorm` content or `rstorm` tool
  usage left in this tree.
- `synapse.tools.utils.mdstorm` processes any Markdown file with fenced-code-block directives named
  ` ```mdstorm `, ` ```mdstorm-setup `, ` ```mdshell `, and ` ```mdautodoc ` (the `mdstorm` prefix, rather than
  bare ` ```storm `, keeps that fence name free for future Storm syntax highlighting). ` ```mdautodoc ` generates
  Markdown (a Cell's confdefs, a class's own API (`cls.__dict__`, not its full MRO), a Storm package's
  command/module/dependency reference, the data model, or the Storm types reference) and splices it in at the
  point of use; `--level N` shifts the generated headings down N levels to nest under an author-written heading.
  See `synsrc/docs/README.md` for the full directive set.
- A doc bundle's source tree (an `index.md` plus a ` ```mdtoc ` nav) is built into its own canonical, committed
  bundle directory -- see `synapse.lib.mddocs.buildBundle` for the stage/mdstorm/nav/validate/merge pipeline. A
  Storm package builds with `synapse.tools.storm.pkg.doc <pkgfile>` (default destination: `files/docs`, next to
  the pkgdef); this `docs/synapse/` bundle has no pkgdef of its own, so it instead builds with
  `synapse.tools.utils.doc docs/synapse synapse/assets/docs`, given both directories explicitly (also how
  `synapse-enterprise` builds, in the enterprise monorepo). `synapse.tools.utils.mddocs` (the old per-bundle
  `mddocs.yaml`-driven site builder) stayed removed; `doc` is a from-scratch replacement for the narrower case of
  a bundle with no pkgdef. A bundle's category is not part of either build; it is derived where a doc manifest is
  delivered (`synmods.hub.app.HubCell.getDocsManifest`'s Product model for the Hub, `vtxtools.docsmanifest`
  offline). `docs/` holds only directive-bearing files (see
  `synapse/assets/docs/contributing/doc_mastering.md`); a plain page lives in the committed bundle dir and is
  edited there directly.
- Key docs: `adminguide.md`, `deploymentguide.md`, `devopsguide.md`, `httpapi.md`
- Whenever possible, link between documents/sections with relative Markdown links (`[text](file.md#anchor)`).

## Docker

`docker/scripts/build.sh` is the canonical builder for the synapse base images.

```bash
# Build all five base images with the default tag (3.x.x-dev):
./docker/scripts/build.sh

# Build with an explicit tag:
./docker/scripts/build.sh 3.x.x-dev

# Build only the vertexproject/synapse base, skip the four service variants:
./docker/scripts/build.sh --only-base my_tag

# Skip the BuildKit cache prune at the start (preserves the cache for iterative
# integrations driven by external tooling):
./docker/scripts/build.sh --no-prune my_tag

# Flags compose; positional TAG comes last:
./docker/scripts/build.sh --no-prune --only-base my_tag
```

Default behavior (no flags) produces:

- `vertexproject/synapse:TAG`
- `vertexproject/synapse-aha:TAG`
- `vertexproject/synapse-axon:TAG`
- `vertexproject/synapse-cortex:TAG`
- `vertexproject/synapse-jsonstor:TAG`

and starts with `docker builder prune -a -f`. `--no-prune` and `--only-base` are the supported escape hatches for callers that need lighter-touch behavior; the script must continue to be runnable directly with no flags for standalone use (CI base image publish, etc.).

`docker/scripts/test.sh [TAG]` smoke-tests the produced images. It runs the synapse base entrypoint, starts the four service-variant containers, and polls each one's Docker `Health.Status` every 2s up to a 300s timeout. The poll loop exits as soon as a container reports a decisive status (anything other than `starting`); a final `healthy` check decides the script's exit code. An EXIT trap stops all containers on both success and failure paths so nothing leaks.

## Important Notes

- The Storm language (`.storm` files, stormlib modules) is central to the system. Changes to the parser or stormlib modules can have wide-reaching effects.
- The Nexus system provides write-ahead logging for replication. Test with `SYNDEV_NEXUS_REPLAY=1` to verify transaction idempotency.
- Follow existing code and documentation syle conventions.
- Every change **MUST** update the tests to confirm correctness and maintain high code coverage.
- Every change **MUST** update any existing docs to reflect the change.
- Any change which affects a user **MUST** have a changelog entry.
