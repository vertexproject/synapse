<a id="syn-tools-cortex_layer_load"></a>

# cortex.layer.load

The Synapse `cortex.layer.load` tool can be used to import node edits to a Synapse layer.

## Syntax

`cortex.layer.load` is executed using `python -m synapse.tools.cortex.layer.load`. The command usage is as follows:

```text
python -m synapse.tools.cortex.layer.load -h
usage: layer.load [-h] [--dryrun] [--url URL] iden files [files ...]

Import node edits to a Synapse layer.

positional arguments:
  iden        The iden of the layer to import to.
  files       The .nodeedits files to import from.

options:
  -h, --help  show this help message and exit
  --dryrun    Process files but don't apply changes.
  --url URL   The telepath URL of the Synapse service.

```
