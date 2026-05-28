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

### Naming Conventions

- Module-level loggers: `logger = logging.getLogger(__name__)`
- Class names: CamelCase (e.g., `CortexApi`, `StormNode`)
- Methods/functions: camelCase (e.g., `addNode`, `getFormName`) — **not** snake_case
- Internal/private methods: underscore prefix `_methodName`
- Constants: ALL_CAPS in `synapse/lib/const.py`

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

## Key Development CLI Tools

| Tool                            | Purpose |
|---------------------------------|---------|
| `synapse.tools.storm`           | Storm CLI |
| `synapse.tools.storm.pkg.gen`   | Storm package generation |
| `synapse.tools.utils.changelog` | Generate changelog entry |

## Documentation

- Sphinx-based docs in `docs/synapse/`.
- Build: `cd docs && make html`
- Files with the `.rstorm` extension are converted to `.rst` using the `synapse.tools.utils.rstorm` tool.
- Key docs: `adminguide.rstorm`, `deploymentguide.rst`, `devopsguide.rst`, `httpapi.rst`

## Important Notes

- The Storm language (`.storm` files, stormlib modules) is central to the system. Changes to the parser or stormlib modules can have wide-reaching effects.
- The Nexus system provides write-ahead logging for replication. Test with `SYNDEV_NEXUS_REPLAY=1` to verify transaction idempotency.
- Follow existing code and documentation syle conventions.
- Every change **MUST** update the tests to confirm correctness and maintain high code coverage.
- Every change **MUST** update any existing docs to reflect the change.
- Any change which affects a user **MUST** have a changelog entry.
