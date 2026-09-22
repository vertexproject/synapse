<a id="syn-tools-storm-pkg-gen"></a>


# storm.pkg.gen

The Synapse `storm.pkg.gen` tool can be used to generate a Storm [Package](../glossary.md#gloss-package) containing new Storm commands and Storm modules from a YAML definition and optionally push it to a Cortex.

For additional details on using the `storm.pkg.gen` tool see [Building / Loading](../devguides/power-ups.md#dev-rapid-power-ups-build) a Rapid Power-Up.

## Syntax

`storm.pkg.gen` is executed using `python -m synapse.tools.storm.pkg.gen`. The command usage is as follows:

```mdshell --fail-ok
python -m synapse.tools.storm.pkg.gen -h
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
