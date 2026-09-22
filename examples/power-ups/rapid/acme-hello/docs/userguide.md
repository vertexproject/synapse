```mdstorm-setup --load-pkg ../acme-hello.yaml
```

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

```mdstorm
acme.hello.sayhi
```

## Using Command Line Options

`acme.hello.omgopts` takes a mandatory positional FQDN, an optional `--hehe` value, and a `--debug`
switch:

```mdstorm
acme.hello.omgopts --hehe haha vertex.link
```

The command also acts on any nodes in the pipeline. With `--debug` set, it prints an extra line per
node:

```mdstorm
[ inet:fqdn=vertex.link ] | acme.hello.omgopts --debug vertex.link
```

## Yielding New Nodes

`acme.hello.mayyield` demonstrates the `--yield` convention. Without it, the command makes new
`inet:dns:a` nodes but passes the inbound nodes through:

```mdstorm
inet:fqdn=vertex.link | acme.hello.mayyield
```

With `--yield`, the newly created `inet:dns:a` nodes are emitted instead:

```mdstorm
inet:fqdn=vertex.link | acme.hello.mayyield --yield
```

## Calling the Module Directly

A package's **Storm** modules may also be imported and called directly, rather than through one of
its commands:

```mdstorm
$hello = $lib.import(acme.hello)
$hello.woot("hello from the module!")
```
