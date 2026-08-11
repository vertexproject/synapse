```mdstorm-setup
```

<a id="syn-tools-storm"></a>


# storm

The Synapse Storm tool (commonly referred to as the **Storm CLI**) is a text-based interpreter that leverages the Storm query language (see [Storm Reference - Introduction](storm_ref_intro.md#storm-ref-intro)).

- [Connecting to a Cortex with the Storm CLI](syn_tools_storm.md#connecting-to-a-cortex-with-the-storm-cli)
- [Connecting with the HTTP API](syn_tools_storm.md#connecting-with-the-http-api)
- [Storm CLI Basics](syn_tools_storm.md#storm-cli-basics)
- [Accessing External Commands](syn_tools_storm.md#accessing-external-commands)

## Connecting to a Cortex with the Storm CLI

To access the Storm CLI you must use the `storm` module to connect to a local or remote Synapse Cortex.

> [!NOTE]
> If you're just getting started with Synapse, you can use the Synapse [Quickstart](https://github.com/vertexproject/synapse-quickstart) to quickly set up and connect to a local Cortex using the Storm CLI.

To connect to a local or remote Synapse Cortex using the Storm CLI, simply run the Synapse `storm` module by executing the following Python command from a terminal window, where the *\<url\>* parameter is the URL path to the Synapse Cortex.

`python -m synapse.tools.storm <url>`

The URL has the following format:

`<scheme>://<server>:<port>/<cortex>`

or

`<scheme>://<user>:<password>@<server>:<port>/<cortex>`

if authentication is used.

**Example URL paths:**

- `cell://vertex/storage` (default if using Synapse Quickstart)
- `tcp://synapse.woot.com:1234/cortex01`
- `ssl://synapse.woot.com:1234/cortex01`

Once connected, you will be presented with the following Storm CLI command prompt:

`storm>`

## Connecting with the HTTP API

The Storm CLI may also connect to a Cortex using the HTTP API (see [HTTP/REST API](../httpapi.md#http-api)) rather than Telepath. This is useful when the Cortex is only reachable over HTTPS, such as when it is behind a reverse proxy or load balancer.

To use the HTTP API, provide an `https://` URL. The Storm HTTP APIs only accept user API keys, so one **must** be provided as the user portion of the URL:

`python -m synapse.tools.storm https://<apikey>@synapse.woot.com:4443/`

See [API Key Support](../httpapi.md#http-api-apikey) for details on creating a user API key.

The following options are only valid with an `https://` URL:

- `--https-ca-dir` - A directory of CA certificates which are added to the TLS CA chain used to verify the server.
- `--https-noverify` - Ignore SSL certificate validation errors.
- `--https-proxy` - An aiohttp-socks compatible proxy URL to tunnel the connection through.

> [!NOTE]
> When streaming Storm queries over the HTTP API, the Storm CLI sets the `keepalive` option to 6 seconds so that long running queries do not have their connections terminated while they produce no output. This may be changed by setting `keepalive` in an `--optsfile`. Note that `!export` does not support keepalive messages.

## Storm CLI Basics

Once connected to a Synapse Cortex with the Storm CLI, you can execute any Storm queries or Storm commands directly. Detailed information on using the Storm query language to interact with data in a Synapse Cortex can be found in the [Storm Reference](index_storm_ref.md#userguide_storm_ref).

To view a list of available **Storm commands,** type `help` from the Storm CLI prompt:

`storm> help`

> - Detailed help for any command can be viewed by entering `-h` or `--help` after the individual command.
> - For additional detail on Storm commands, see [Storm Reference - Storm Commands](storm_ref_cmd.md#storm-ref-cmd).

To exit the Storm CLI, enter `!quit`:

`storm> !quit`

> - The `!quit` command is technically an "external" (to Storm) command, so must be preceded by the bang (exclamation point) symbol.

## Accessing External Commands

You can access a subset of external Synapse tools and commands from within the Storm CLI. External commands differ from native Storm commands in that they are preceded by a bang / exclamation point ( `!` ) symbol.

You can view the available **external commands** by typing `!help` from the Storm CLI prompt:

```mdstorm
!help
```

Notably, the Synapse `pushfile` and `pullfile` tools (used to upload and download files from a Synapse storage [Axon](../glossary.md#gloss-axon)) are accessible from the Storm CLI:

`storm> !pushfile`

`storm> !pullfile`

See [axon.put](syn_tools_axon_put.md#syn-tools-axon-put) and [axon.get](syn_tools_axon_get.md#syn-tools-axon-get) for additional detail on these tools.

**Help** for any external command can be viewed by entering `-h` or `--help` after the command:

`storm> !export -h`

`storm> !export --help`
