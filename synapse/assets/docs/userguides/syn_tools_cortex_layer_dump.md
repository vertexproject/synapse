<a id="syn-tools-cortex_layer_dump"></a>

# cortex.layer.dump

The Synapse `cortex.layer.dump` tool can be used to export node edits from a Synapse layer.

## Syntax

`cortex.layer.dump` is executed using `python -m synapse.tools.cortex.layer.dump`. The command usage is as follows:

```text
python -m synapse.tools.cortex.layer.dump -h
usage: layer.dump [-h] [--url URL] [--offset OFFSET] [--chunksize CHUNKSIZE]
                  [--statefile STATEFILE]
                  iden outdir

Export node edits from a Synapse layer.

positional arguments:
  iden                  The iden of the layer to export.
  outdir                The directory to save the exported node edits to.

options:
  -h, --help            show this help message and exit
  --url URL             The telepath URL of the Synapse service.
  --offset OFFSET       The starting offset of the node edits to export.
  --chunksize CHUNKSIZE
                        The number of node edits to store in a single file.
                        Zero to disable chunking.
  --statefile STATEFILE
                        Path to the state tracking file for this layer dump.

```
