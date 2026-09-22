# Acme-Hello User Guide

Acme-Hello ships three example **Storm** commands and two **Storm** modules. It is not a real
integration -- it exists so a Rapid Power-Up developer has a working package to read and copy.

Every **Storm** query on this page is executed against a real **Cortex** when these docs are built,
and its output is captured below it. That makes the guide a small integration test of the package as
well as documentation.

## Getting Started

Acme-Hello has no configuration to set before it can be used. Ask your admin whether they have
configured an API key if you intend to use `acme.hello.privsep`, which is covered in the
[Admin Guide](adminguide.md).

## Saying Hi

`acme.hello.sayhi` is the smallest possible command. It imports the `acme.hello` module and calls a
function in it:

```stormdoc
storm> acme.hello.sayhi
hello storm!
```

## Using Command Line Options

`acme.hello.omgopts` takes a mandatory positional FQDN, an optional `--hehe` value, and a `--debug`
switch:

```stormdoc
storm> acme.hello.omgopts --hehe haha vertex.link
User Specified hehe: haha
FQDN: vertex.link
```

The command also acts on any nodes in the pipeline. With `--debug` set, it prints an extra line per
node:

```stormdoc
storm> [ inet:fqdn=vertex.link ] | acme.hello.omgopts --debug vertex.link
FQDN: vertex.link
GOT NODE: vertex.link
debug mode detected!
inet:fqdn=vertex.link
        :domain = link
        :host = vertex
        :issuffix = false
        :iszone = true
        :zone = vertex.link
```

## Yielding New Nodes

`acme.hello.mayyield` demonstrates the `--yield` convention. Without it, the command makes new
`inet:dns:a` nodes but passes the inbound nodes through:

```stormdoc
storm> inet:fqdn=vertex.link | acme.hello.mayyield
inet:fqdn=vertex.link
        :domain = link
        :host = vertex
        :issuffix = false
        :iszone = true
        :zone = vertex.link
```

With `--yield`, the newly created `inet:dns:a` nodes are emitted instead:

```stormdoc
storm> inet:fqdn=vertex.link | acme.hello.mayyield --yield
inet:dns:a=('vertex.link', '1.2.3.4')
        :fqdn = vertex.link
        :ip = 1.2.3.4
inet:dns:a=('vertex.link', '123.123.123.123')
        :fqdn = vertex.link
        :ip = 123.123.123.123
```

## Calling the Module Directly

A package's **Storm** modules may also be imported and called directly, rather than through one of
its commands:

```stormdoc
storm> $hello = $lib.import(acme.hello)
$hello.woot("hello from the module!")
hello from the module!
```
