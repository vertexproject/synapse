# Regression cells

On-disk cells written by older versions of Synapse, used by the migration and regression tests. Each cell is a single
gzipped tar, under a directory for its service:

```
cortexes/<name>.tar.gz   SynTest.getRegrCore(<name>) / getRegrDir('cortexes', <name>)
axons/<name>.tar.gz      SynTest.getRegrAxon(<name>) / getRegrDir('axons', <name>)
scripts/                 generator scripts, gen-<name>.py, and packcell.py
```

`getRegrDir()` extracts the tar into a temporary directory, so a test never modifies the checked-in cell. The tars are
tracked by Git LFS. This directory is excluded from the wheel and sdist (`synsrc/pyproject.toml`), so do not move it
under `tests/files/`.

Enterprise-only cells follow the same layout under `test/<module>/assets/regression/` (`TstBase.getRegrRoot()`).

## Cells

| Cell | Generator | Written by |
|------|-----------|------------|
| `axons/axon-axon_v2.tar.gz` | synapse-regression | 2.210.0 |
| `cortexes/model-3.2.0.tar.gz` | `scripts/gen-model-3.2.0.py` | 3.7.0, under `python -O` |

Each generator script manages exactly one cell. Cells whose generator is in `synapse-regression` were copied verbatim
from that repo.

The 3.x migration expects the layout of a current 2.x release, so a cell written by an older one is booted once
under a current 2.x, the way an operator upgrades before migrating, and written back with the 2.x
`synapse.tools.backup`, which compacts the slabs that boot grew.

## Generating a cell

A generator must run on the Synapse release the cell was written with (see the table above), not on this source
tree. Install that version into a separate virtual environment, and run the script from there:

```bash
pip install 'synapse==<version>'
python <path to>/regression/scripts/gen-<name>.py
```

A 3.x release is not published to PyPI, so install it from its tag in this repo instead. A generator which records
values only the release's own normalizer stored says so, and checks for it, such as `gen-model-3.2.0.py`, which must
run under `python -O`:

```bash
mkdir /tmp/syn370 && git archive synapse@v3.7.0 synsrc | tar -x -C /tmp/syn370
python -m venv /tmp/syn370/venv && /tmp/syn370/venv/bin/pip install /tmp/syn370/synsrc
cd /tmp && /tmp/syn370/venv/bin/python -O <path to>/regression/scripts/gen-model-3.2.0.py
```

Run it from outside this repo, so that `import synapse` resolves to the 2.x install rather than this source tree. The
script builds the cell in `/tmp/v/` and replaces its tar in `cortexes/` in place. Look up anything a test needs
(layers, views, users) by name, since the idens change every time the cell is regenerated.

## Packing a cell

`scripts/packcell.py` turns a cell directory into its tar, and the generators import it to write theirs. It only uses
the standard library, so it runs under the 2.x environment as well. To pack a cell by hand, for one without a
generator:

```bash
python scripts/packcell.py cortexes/<name>
```

This writes `cortexes/<name>.tar.gz` next to the directory. Delete the directory afterwards; only the tar is checked in.

The tar holds only the cell's files, in sorted order, with the mode, owner and mtime of every member normalized, and
no name or mtime in the gzip header, so packing an unchanged cell reproduces the same bytes.
