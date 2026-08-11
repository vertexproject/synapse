<a id="syn-tools-axon_load"></a>

# axon.load

The Synapse `axon.load` tool can be used to load blobs into a Synapse Axon.

## Syntax

`axon.load` is executed using `python -m synapse.tools.axon.load`. The command usage is as follows:

```text
python -m synapse.tools.axon.load -h
usage: synapse.tools.axon.load [-h] [--url URL] files [files ...]

Load blobs into a Synapse Axon.

positional arguments:
  files       List of .tar.gz files to import from.

options:
  -h, --help  show this help message and exit
  --url URL   Telepath URL for the Axon.

```
