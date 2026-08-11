<a id="syn-tools-aha_mirror"></a>

# aha.mirror

The Synapse `aha.mirror` tool can be used to query the AHA server for the service cluster status of mirrors.

## Syntax

`aha.mirror` is executed using `python -m synapse.tools.aha.mirror`. The command usage is as follows:

```text
python -m synapse.tools.aha.mirror -h
usage: synapse.tools.aha.mirror [-h] [--url URL] [--timeout TIMEOUT] [--wait]

Query the Aha server for the service cluster status of mirrors.

Examples:

    python -m synapse.tools.aha.mirror --timeout 30

options:
  -h, --help         show this help message and exit
  --url URL          The telepath URL to connect to the AHA service.
  --timeout TIMEOUT  The timeout in seconds for individual service API calls
  --wait             Whether to wait for the mirrors to sync.

```
