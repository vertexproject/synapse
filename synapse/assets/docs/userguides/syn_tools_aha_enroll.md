<a id="syn-tools-aha_enroll"></a>

# aha.enroll

The Synapse `aha.enroll` tool can be used to initialize your AHA user environment from a one-time key.

## Syntax

`aha.enroll` is executed using `python -m synapse.tools.aha.enroll`. The command usage is as follows:

```text
python -m synapse.tools.aha.enroll -h
usage: synapse.tools.aha.enroll [-h] onceurl

Use a one-time use key to initialize your AHA user enrivonment.

Examples:

    python -m synapse.tools.aha.enroll tcp://aha.loop.vertex.link:27272/b751e6c3e6fc2dad7a28d67e315e1874

positional arguments:
  onceurl     The one-time use AHA user enrollment URL.

options:
  -h, --help  show this help message and exit

```
