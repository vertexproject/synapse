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
                                   [--https-proxy HTTPS_PROXY]
                                   [--https-ca-dir HTTPS_CA_DIR]
                                   [--https-noverify]
                                   <pkgfile>

A tool for generating/pushing storm packages from YAML prototypes.

positional arguments:
  <pkgfile>             Path to a storm package prototype .yaml file, or a
                        completed package .json/.yaml file.

options:
  -h, --help            show this help message and exit
  --push <url>          A telepath URL of a Cortex, or an https:// URL for the
                        Cortex HTTP API.
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
  --https-proxy HTTPS_PROXY
                        An aiohttp-socks compatible proxy URL to use for
                        https:// URLs.
  --https-ca-dir HTTPS_CA_DIR
                        A directory of CAs which are added to the TLS CA chain
                        for https:// URLs.
  --https-noverify      Ignore SSL certificate validation errors for https://
                        URLs.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.genpkg`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).

## Pushing with the HTTP API

`--push` may also target a Cortex using the HTTP API (see [HTTP/REST API](../httpapi.md#http-api)) rather than Telepath. This is useful when the Cortex is only reachable over HTTPS, such as when it is behind a reverse proxy or load balancer.

To use the HTTP API, provide an `https://` URL. The Storm HTTP APIs only accept user API keys, so one **must** be provided as the user portion of the URL:

`python -m synapse.tools.storm.pkg.gen --push https://<apikey>@synapse.example.com:4443/ acme-hello.yaml`

See [API Key Support](../httpapi.md#http-api-apikey) for details on creating a user API key. The API key's user needs the `pkg.add` permission to add the package, and the `axon.has` and `axon.upload` permissions to upload the files the package declares.

The following options are only valid with an `https://` URL:

- `--https-ca-dir` - A directory of CA certificates which are added to the TLS CA chain used to verify the server.
- `--https-noverify` - Ignore SSL certificate validation errors.
- `--https-proxy` - An aiohttp-socks compatible proxy URL to tunnel the connection through.
