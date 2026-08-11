<a id="syn-tools-axon-copy"></a>

# axon.copy

The Synapse `axon.copy` tool can be used to copy blobs from one Axon to another Axon.

## Syntax

`copy` is executed using `python -m synapse.tools.axon.copy`. The command usage is as follows:

```text
python -m synapse.tools.axon.copy -h
usage: synapse.tools.axon.copy [-h] [--offset OFFSET] src_axon dst_axon

positional arguments:
  src_axon         The telepath URL of the source axon.
  dst_axon         The telepath URL of the destination axon.

options:
  -h, --help       show this help message and exit
  --offset OFFSET  An offset within the source axon to start from.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.axon2axon`. It can still be run with that name.
