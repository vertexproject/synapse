<a id="syn-tools-service-demote"></a>

# service.demote

The Synapse `service.demote` tool can be used to automatically select a new leader and demote this service.

## Syntax

`service.demote` is executed using `python -m synapse.tools.service.demote`. The command usage is as follows:

```text
python -m synapse.tools.service.demote -h
usage: synapse.tools.service.demote [-h] [--url URL] [--timeout TIMEOUT]

Automatically select a new leader and demote this service.

Example:
    python -m synapse.tools.service.demote

options:
  -h, --help         show this help message and exit
  --url URL          The telepath URL of the Synapse service.
  --timeout TIMEOUT  The timeout to use awaiting network connections.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.demote`. It can still be run with that name.
