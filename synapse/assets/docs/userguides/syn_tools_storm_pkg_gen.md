<a id="syn-tools-storm-pkg-gen"></a>

# storm.pkg.gen

The Synapse `storm.pkg.gen` tool can be used to generate a Storm [Package](../glossary.md#gloss-package) containing new Storm commands and Storm modules from a YAML definition and optionally push it to a Cortex.

For additional details on using the `storm.pkg.gen` tool see [Building / Loading](../devguides/power-ups.md#dev-rapid-power-ups-build) a Rapid Power-Up.

## Syntax

`storm.pkg.gen` is executed using `python -m synapse.tools.storm.pkg.gen`. The command usage is as follows:

```text
python -m synapse.tools.storm.pkg.gen -h
usage: synapse.tools.storm.pkg.gen [-h] [--push <url>] [--push-verify]
                                   [--save <path>] [--signas <name>]
                                   [--certdir <dir>] [--no-build] [--encrypt]
                                   [--encrypt-pubkey <path>]
                                   <pkgfile>

A tool for generating/pushing storm packages from YAML prototypes.

positional arguments:
  <pkgfile>             Path to a storm package prototype .yaml file, or a
                        completed package .json/.yaml file.

options:
  -h, --help            show this help message and exit
  --push <url>          A telepath URL of a Cortex.
  --push-verify         Tell the Cortex to verify the package signature.
  --save <path>         Save the completed package JSON to a file.
  --signas <name>       Specify a code signing identity to use from
                        ~/.syn/certs/code.
  --certdir <dir>       Specify an alternate certdir to ~/.syn/certs.
  --no-build            Treat pkgfile argument as an already-built package
  --encrypt             Encrypt the Storm queries within package modules and
                        commands.
  --encrypt-pubkey <path>
                        Path to a PEM encoded RSA public key. Encrypts the
                        package for that specific deployment (implies
                        --encrypt).

```

> [!NOTE]
> This tool was previously run using `synapse.tools.genpkg`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
