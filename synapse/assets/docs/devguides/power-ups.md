<a id="dev_rapid_power_ups"></a>

# Rapid Power-Up Development

Developing Rapid Power-Ups allows Synapse power users to extend the capabilities of the Storm query language, provides ways to implement use-case specific commands, embed documentation, and even implement customized visual workflows in **Optic**, the commercial Synapse UI.

A Rapid Power-Up consists of a **Storm Package** which is a JSON object which defines everything used to extend the Storm language and provide additional documentation. **Storm Packages** can be loaded directly into your **Cortex**.

In this guide we will discuss the basics of **Storm Package** development and discuss a few best practices you can use to ensure they are secure, powerful, and easy to use.

The example `acme-hello` power-up discussed in this guide is included in the **Synapse** repository within the `examples/power-ups/rapid/acme-hello` folder. You can find that at [Acme-Hello Example](https://github.com/vertexproject/synapse/tree/master/examples/power-ups/rapid/acme-hello).

## Anatomy of a Storm Package

A **Storm Package** consists of a YAML file which defines the various commands, modules, documentation, and workflows embedded within the package.

### Minimal Example

As you can see in the minimal example below, the **Storm Package** is defined by a YAML file that gets processed and loaded into your Cortex.

`acme-hello.yaml`:

``` yaml
name: acme-hello
version: 0.0.1
title: Acme Hello

dependencies:
  synapse:
    version: '>=3.0.0,<4.0.0'
  acme-utils:
    version: '>=1.0.0'
    optional: true

author:
  url: https://acme.newp
  name: ACME Explosives and Anvils

desc: Acme-Hello is a minimal example of a Rapid Power-Up.

modules:
  - name: acme.hello
  - name: acme.hello.privsep
    asroot:perms:
        - [ acme, hello, user ]

commands:
  - name: acme.hello.sayhi
    desc: Print the hello message.
```

The `title` field is a short, human-readable name for the package which is displayed in UIs such as **Optic**, as opposed to the `name` field which is the package's namespaced identifier.

The `dependencies` field is a dictionary, keyed by package name, which declares the other **Storm Packages** (and/or **Synapse** version) that your package requires. The reserved name `synapse` refers to the running **Synapse** version rather than a loaded **Storm Package**, and replaces the old top level `synapse_version` field. Each entry may specify a `version` requirement using the same range syntax shown above, an optional `desc` describing the dependency, and an optional `optional` flag (defaults to `false`). When a non-optional dependency is unmet, the **Storm Package** will fail to load and an error is raised. Unmet optional dependencies are only logged and do not block package load.

The `conflicts` field is similarly a dictionary, keyed by package name, of packages (or `synapse` versions) that must **not** be present for your package to load. If a conflict is matched, the **Storm Package** will fail to load and an error is raised.

> [!NOTE]
> First, a note on namespacing. To ensure your **Storm Package** is going to play well with other packages, it is important to choose an appropriate namespace for your power-up. In this case, the `acme` part of the name is meant to be replaced with your company name or an abbreviated version of it. The `hello` part is meant to be replaced with an indicator of the type of functionality the **Storm Package** contains.
>
> Namespace now, thank yourself later.

When you define commands and modules, they will be loaded from files using the location of the **Storm Package** YAML file to locate their contents:

``` text
acme-hello.yaml
storm/

    modules/
        acme.hello.storm
        acme.hello.privsep.storm

    commands/
        acme.hello.sayhi.storm
```

`storm/modules/acme.hello.storm`:

``` text
function woot(text) {
    $lib.print($text)
    return((null))
}
```

`storm/commands/acme.hello.sayhi.storm`:

``` text
$hello = $lib.import(acme.hello)
$hello.woot("hello storm!")
```

<a id="dev-rapid-power-ups-build"></a>

### Building / Loading

To build and load **Storm Packages**, use the `storm.pkg.gen` tool included within Synapse. For this example, we will assume you have deployed your Synapse environment according to the [Deployment Guide](../deploymentguide.md):

``` text
python -m synapse.tools.storm.pkg.gen acme-hello.yaml --push aha://cortex...
```

> [!NOTE]
> If you added an alternate admin user or used a non-standard naming convention you may need to adjust the `aha://cortex...` telepath URL to connect to your Cortex.

> [!NOTE]
> The package definition schema rejects unknown keys, so a misspelled or stray key fails the build
> with a `SchemaViolation` naming the offending key rather than being silently ignored. The `modconf`
> and `cmdconf` values, a vault type `schema`, and the `optic` section are exempt, since they hold
> package-defined or separately-validated data. See
> [Package definitions reject unknown keys](../300_changes/storm-package-strict-keys.md#vtx_300_storm-package-strict-keys).

Once your **Storm Package** has loaded successfully, you can use the **Storm** CLI to see it in action:

``` text
invisigoth@visi01:~$ python -m synapse.tools.storm aha://cortex...

Welcome to the Storm interpreter!

Local interpreter (non-storm) commands may be executed with a ! prefix:
    Use !quit to exit.
    Use !help to see local interpreter commands.

storm> acme.hello.sayhi
hello storm!
complete. 0 nodes in 1 ms (0/sec).
storm>
```

## Storm Modules

Deploying **Storm Modules** allows you to author powerful library functions that you can use in automation or **Storm Commands** to facilitate code re-use and enforce privilege separation boundaries.

A **Storm Module** is specified within the `modules:` section of the **Storm Package** YAML file.

``` yaml
modules:

  - name: acme.hello
    modconf:
        varname: varvalu
        othervar: [1, 2, 3]
```

The `modconf:` key can be used to specify variables which will be mapped into the module's **Storm** runtime and accessible using the implicit variable `$modconf`:

``` text
function foo() {
    $lib.print($modconf.varname)
    return((10))
}

function bar() {
    for $i in $modconf.othervar {
        // Do something using $i...
    }
}
```

<a id="privileged-modules"></a>

### Privileged Modules

In order to facilitate delegating permission for privileged operations, **Storm** modules may specify permissions which allow the module to be imported with admin privileges. It is a best-practice to declare these permissions within the **Storm** package using the `perms:` key before using them:

``` yaml
perms:
  - perm: [ acme, hello, user ]
    gate: cortex
    desc: Allows a user to call privileged APIs from Acme-Hello.

modules:

  - name: acme.hello.privsep
    asroot:perms:
        - [ acme, hello, user ]
```

To minimize risk, you must very carefully consider what functions to implement within a privileged **Storm** module! Privileged modules should contain the absolute minimum required functionality.

An excellent example use case for a privileged **Storm** module exists when you have an API key or password which you would like to use on a user's behalf without disclosing the actual API key. The **Storm** library `$lib.globals.set(<name>, <valu>)` and `$lib.globals.get(<name>)` can be used to access protected global variables which regular users may not access without special permissions. By implementing a privileged **Storm** module which retrieves the API key and uses it on the user's behalf without disclosing it, you may protect the API key from disclosure while also allowing users to use it. For example, `acme.hello.privsep.storm`:

```storm
function getFooByBar(bar) {

    // Retrieve an API key from protected storage
    $apikey = $lib.globals.get(acme:hello:apikey)

    $headers = ({
        "apikey": $apikey
    })

    $url = `https://acme.newp/api/v1/foo/{$bar}`

    // Use the API key on the callers behalf
    $resp = $lib.inet.http.get($url, headers=$headers)
    if ($resp.code != 200) {
        $lib.warn(`/api/v1/foo returned HTTP code: {$resp.code}`)
        return((null))
    }

    // Return the JSON response (but not the API key)
    return($resp.json())
}
```

Notice that the `$apikey` is being retrieved and used to call the HTTP API but is not returned to the caller.

## Storm Commands

Adding **Storm Commands** to your Cortex via a **Storm Package** is a great way to extend the functionality of your Cortex in a CLI user-friendly way.

### Command Line Options

Every **Storm** command has the `--help` option added automatically. This means that it is always safe to execute any command with `--help` to get a usage statement and enumerate command line arguments. The `desc` field specified in the command is included in the output:

``` text
storm> acme.hello.sayhi --help

Print the hello message.

Usage: acme.hello.sayhi [options]

Options:

  --help                      : Display the command usage.
complete. 0 nodes in 4 ms (0/sec).
storm>
```

**Storm Commands** may specify command line arguments using a convention which is similar (although not identical to) Python's `argparse` library.

A more complex command declaration:

``` yaml
commands:

  - name: acme.hello.omgopts
    desc: |
        This is a multi-line description containing usage examples.

        // Run the command with some nodes
        inet:fqdn=acme.newp | acme.hello.omgopts vertex.link

        // Run the command with some command line switches
        acme.hello.omgopts --debug --hehe haha vertex.link

    cmdargs:

      - - --hehe
        - type: str
          help: The value of the hehe optional input.

      - - --debug
        - type: bool
          default: false
          action: store_true
          help: Enable debug output.

      - - fqdn
        - type: str
          help: A mandatory / positional command line argument.
```

A more complete example of help output:

``` text
storm> acme.hello.omgopts --help

This is a multi-line description containing usage examples.

// Run the command with some nodes
inet:fqdn=acme.newp | acme.hello.omgopts vertex.link

// Run the command with some command line switches
acme.hello.omgopts --debug --hehe haha vertex.link

Usage: acme.hello.omgopts [options] <fqdn>

Options:

  --help                      : Display the command usage.
  --hehe <hehe>               : The value of the hehe optional input.
  --debug                     : Enable debug output.

Arguments:

  <fqdn>                      : A mandatory / positional command line argument.
complete. 0 nodes in 6 ms (0/sec).
```

Command line options are available within the **Storm** command by accessing the implicit `$cmdopts` variable. The command example (`storm/commands/acme.hello.omgopts.storm`) can be seen below:

```storm
// An init {} block only runs once even if there are multiple nodes in the pipeline.

init {

    // Set global debug (once) if the user specified --debug
    if $cmdopts.debug { $lib.debug = (true) }

    if ($cmdopts.hehe) { $lib.print(`User Specified hehe: {$cmdopts.hehe}`) }

    // Normalize the FQDN in case we want to send it to an external system
    ($ok, $fqdn) = $lib.trycast(inet:fqdn, $cmdopts.fqdn)
    if (not $ok) {
        $lib.exit(`Invalid FQDN Specified: {$cmdopts.fqdn}`)
    }

    // Maybe call an API here or something...
    $lib.print(`FQDN: {$fqdn}`)
}

// You may also act on nodes in the pipeline
$lib.print(`GOT NODE: {$node.repr()}`)

if $lib.debug { $lib.print("debug mode detected!") }

// Any nodes still in the pipeline are sent as output
```

### Command Option Conventions

--help

:   This option is reserved and handled automatically to print a command usage statement which also enumerates any positional or optional arguments.

--debug

:   This option is typically used to enable debug output in the **Storm** interpreter by setting the `$lib.debug` variable if it is specified. The `$lib.debug` variable has a recursive effect and will subsequently enable debug output in any command or functions called from the command.

--yield

:   By default, a command is generally expected to yield the nodes that it received as input from the pipeline. In some instances it is useful to instruct the command to yield the nodes it creates. For example, if you specify `inet:fqdn` nodes as input to a DNS resolver command, it may be useful to tell the command to yield the newly created `inet:dns:a` records rather than the input `inet:fqdn` nodes. Commands frequently use the `divert` **Storm** command to implement `--yield` functionality.

--asof \<time\>

:   To minimize duplicate API calls, many **Storm** packages cache results using the `$lib.jsonstor` API. When caching is in use, the `--asof <time>` option is used to control cache aging. Users may specify `--asof now` to disable caching.

## Package Files

A **Storm Package** ships arbitrary data files, such as databases or models, by placing them in a `files` directory beside the **Storm Package** YAML file. The directory is walked recursively, so it may be organized however suits the package. A package's documentation is one common use of `files`: running `python -m synapse.tools.storm.pkg.doc acme-hello.yaml` renders a `docs/` source tree of Markdown pages (processing any ` ```mdstorm ` directives) into `files/docs`, so the built pages travel with the package like any other declared file.

``` text
acme-hello.yaml
files/
    data.mmdb
    models/
        classifier.bin
```

When the package is built with `storm.pkg.gen`, a `files:` section is generated from that directory. It is keyed by the path each file is served under -- its path relative to the `files` directory -- and each entry carries the SHA256 of its contents:

``` yaml
files:
    data.mmdb:
        sha256: 0f4b3fa39e8f4bd4f2a1e35e2a83ff3d9c50a5c0ea6b0e29b1a3cb5eaf2d7f61
    models/classifier.bin:
        sha256: 6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d
```

Which files ship, and their SHA256 values, are derived from the directory rather than authored, so the section can never drift from what is actually there. An entry may still be declared in the prototype to carry additional fields for the file it names; declaring one for a path the package does not ship is an error. A file's path is stable across rebuilds, while its SHA256 changes whenever the contents do -- which is why a **Storm Service** serves its files by path.

The file contents are **not** embedded in the package definition. Instead they are stored on the **Vertex Hub** and downloaded into the **Cortex** [Axon](../glossary.md#gloss-axon) ( by SHA256 ) when the package is installed, where the package may retrieve them using `$lib.axon`. Because the SHA256 values are part of the package definition, they are covered by the package's code signature and cannot be tampered with independently of the package.

A package delivered by a **Storm Service** has no publisher to upload its files, so the **Cortex** retrieves them from the service itself and saves them to its [Axon](../glossary.md#gloss-axon) before the package `onload` runs. Such a package also declares `advanced: true`, which is what marks it an Advanced Power-Up -- deployed as a service rather than installed. See [Advanced Power-Up Development](adv_power_ups.md#dev_adv_power_ups).

To publish a package and its files to the **Vertex Hub**, use the `storm.pkg.publish` tool. It builds the documentation and the package, uploads any files it declares, and then publishes the package definition:

``` text
python -m synapse.tools.storm.pkg.publish acme-hello.yaml
```

The API key used to publish must belong to a **Vertex Hub** account with the `builder` role. It may be specified with `--apikey` or by setting the `VERTEX_HUB_APIKEY` environment variable. The `--url` option defaults to the **Vertex Hub** at `https://hub.vertex.link`. The files are uploaded before the package definition is published, so a published package always has its file contents available.

Publishing always encrypts the **Storm** queries within the package modules and commands, so a published package never exposes its **Storm** source. There is no way to publish a package unencrypted.

Installing a package downloads its files into the **Cortex** [Axon](../glossary.md#gloss-axon) before the package is added, so a **Cortex** never holds a package without the files it declares. If a file cannot be downloaded, the install fails and the package is not added.

The `storm.pkg.gen --push` option behaves the same way for a package pushed directly to a **Cortex**: the files are uploaded into its **Axon** first, and the package is not added if they cannot be.

> [!NOTE]
> A file is located using the package YAML file, so it can only be uploaded when the package is built from its prototype. Pushing an already built package with `--no-build` warns for each file it cannot find locally.

## Testing Storm Packages

It is **highly** recommended that any production **Storm Packages** use development "best practices" including version control and unit testing. For the `acme-hello` example, we have included a test file (`test_acme_hello.py`) that you can use as an example to expand on:

```python3
import os

import synapse.tests.utils as s_test

dirname = os.path.abspath(os.path.dirname(__file__))

class AcmeHelloTest(s_test.StormPkgTest):

    assetdir = os.path.join(dirname, 'testassets')
    pkgprotos = (os.path.join(dirname, 'acme-hello.yaml'),)

    async def test_acme_hello(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('acme.hello.sayhi')
            self.stormIsInPrint('hello storm!', msgs)
            self.stormHasNoWarnErr(msgs)

    async def test_acme_hello_mayyield(self):

        async with self.getTestCore() as core:

            msgs = await core.stormlist('[ inet:fqdn=vertex.link ] | acme.hello.mayyield')
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(1, nodes)
            self.eq(('inet:fqdn', 'vertex.link'), nodes[0][0])

            msgs = await core.stormlist('[ inet:fqdn=vertex.link ] | acme.hello.mayyield --yield')
            self.stormHasNoWarnErr(msgs)
            nodes = [m[1] for m in msgs if m[0] == 'node']
            self.len(2, nodes)
            self.eq(('inet:dns:a', (('inet:fqdn', 'vertex.link'), ('inet:ipv4', (4, 0x01020304)))), nodes[0][0])
            self.eq(('inet:dns:a', (('inet:fqdn', 'vertex.link'), ('inet:ipv4', (4, 0x7b7b7b7b)))), nodes[1][0])
```

With the file `test_acme_hello.py` located in the same directory as `acme-hello.yaml` you can use the standard `pytest` invocation to run the test:

``` text
python -m pytest -svx test_acme_hello.py
```

## Advanced Features

### Using `divert` to implement `--yield`

The `--yield` option is typically used to allow a **Storm** command which takes nodes as input to optionally output the new nodes it added rather than the nodes it received as input. The `divert` command was added to **Storm** to simplify implementing this convention.

To implement a command with a `--yield` option is typically accomplished via the following pattern:

``` yaml
commands:

  - name: acme.hello.mayyield
    desc: |
         Take in an FQDN and make DNS A records to demo --yield

         inet:fqdn=vertex.link | acme.hello.mayyield

    cmdargs:

      - - --yield
        - default: false
          action: store_true
          help: Yield the newly created inet:dns:a records rather than the input inet:fqdn nodes.
```

Then within `storm/commands/acme.hello.mayyield.storm`:

```storm
function nodeGenrFunc(fqdn) {
    // Fake a DNS lookup and make a few inet:dns:a records...
    [ inet:dns:a=($fqdn, 1.2.3.4) ]
    [ inet:dns:a=($fqdn, 123.123.123.123) ]
}

divert $cmdopts.yield $nodeGenrFunc($node)
```

When executed, the `acme.hello.mayyield` command will output the nodes received as inputs which is useful for pipelining enrichments. If the user specifies `--yield` the command will output the resulting `inet:dns:a` nodes constructed by the `nodeGenrFunc()` function.

### Optic Actions

If you have access to the **Synapse** commercial UI **Optic** you may find it helpful to embed **Optic** actions within your **Storm Package**. These actions will be presented to users in the context-menu when they right-click on nodes within **Optic**.

To define **Optic** actions, you declare them in the **Storm Package** YAML file:

``` yaml
optic:
    actions:
      - name: Hello Omgopts
        storm: acme.hello.omgopts --debug
        desc: This description is displayed as the tooltip in the menu
        forms: [ inet:ip, inet:fqdn ]
```

By specifying the `forms:` key, you can control which node actions will be presented on different forms. For example, if you are writing a DNS power-up, you may want to limit the specified actions to `inet:ip` and `inet:fqdn` nodes.

When selected, the query specified in the `storm:` key will be run with the currently selected nodes as input. For example, if you right-click on the node `inet:fqdn=vertex.link` and select `actions -> acme-hello -> Hello Omgopts` it will execute the specified query as though it were run like this:

``` text
inet:fqdn=vertex.link | acme.hello.omgopts --debug
```

Any printed output, including warnings, will be displayed in the **Optic** `Console Tool`.
