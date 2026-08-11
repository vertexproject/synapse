<a id="syn-tools-aha_clone"></a>

# aha.clone

The Synapse `aha.clone` tool can be used to generate a new clone URL to deploy an AHA mirror.

> [!NOTE]
> Most deployments should deploy an AHA mirror automatically by setting `SYN_PROVISION_FOLLOWER` (along with the shared `SYN_PROVISION_SECRET`) on the new AHA server rather than generating a clone URL with this tool. See [Deploy AHA Mirrors (optional)](../deploymentguide.md#deploy_aha_mirror) in the deployment guide. This tool remains available for advanced cases.

## Syntax

`aha.clone` is executed using `python -m synapse.tools.aha.clone`. The command usage is as follows:

```text
python -m synapse.tools.aha.clone -h
usage: synapse.tools.aha.clone [-h] [--port PORT] [--url URL] [--only-url]
                               dnsname

Generate a new clone URL to deploy an AHA mirror.

Examples:

    python -m synapse.tools.aha.clone 001.aha.loop.vertex.link

positional arguments:
  dnsname      The DNS name of the new AHA server.

options:
  -h, --help   show this help message and exit
  --port PORT  The port that the new AHA server should listen on.
  --url URL    The telepath URL to connect to the AHA service.
  --only-url   Only output the URL upon successful execution

```
