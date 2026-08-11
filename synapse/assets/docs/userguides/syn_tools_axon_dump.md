<a id="syn-tools-axon_dump"></a>

# axon.dump

The Synapse `axon.dump` tool can be used to dump blobs from a Synapse Axon.

## Syntax

`axon.dump` is executed using `python -m synapse.tools.axon.dump`. The command usage is as follows:

```text
python -m synapse.tools.axon.dump -h
usage: synapse.tools.axon.dump [-h] [--url URL] [--offset OFFSET]
                               [--rotate-size ROTATE_SIZE]
                               [--statefile STATEFILE]
                               outdir

Dump blobs from a Synapse Axon.

positional arguments:
  outdir                Directory to dump tar.gz files (required).

options:
  -h, --help            show this help message and exit
  --url URL             Telepath URL for the Axon.
  --offset OFFSET       Starting offset in the Axon.
  --rotate-size ROTATE_SIZE
                        Rotate to a new .blobs file after the current file
                        exceeds this size in bytes (default: 4GB). Note: files
                        may exceed this size if a single blob is larger than
                        the remaining space.
  --statefile STATEFILE
                        Path to the state tracking file for the Axon dump.

```
