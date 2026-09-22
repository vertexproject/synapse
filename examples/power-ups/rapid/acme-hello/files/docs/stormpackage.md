
# Storm Package: acme-hello

The following Commands are available from this package.

## Dependencies

This package depends on the following packages.

| Name | Version | Optional | Description |
|---|---|---|---|
| synapse | >=3.0.0,<4.0.0 | no |  |


## Storm Commands

This package implements the following Storm Commands.

<a id="stormcmd-acme-hello-acme-hello-mayyield"></a>

### acme.hello.mayyield

```text
Take in an FQDN and make DNS A records to demo --yield

inet:fqdn=vertex.link | acme.hello.mayyield

Usage: acme.hello.mayyield [options] 

Options:

  --help                      : Display the command usage.
  --yield                     : Yield the newly created inet:dns:a records rather than the input inet:fqdn nodes.
```

<a id="stormcmd-acme-hello-acme-hello-omgopts"></a>

### acme.hello.omgopts

```text
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
```

<a id="stormcmd-acme-hello-acme-hello-sayhi"></a>

### acme.hello.sayhi

```text
Print the hello message.

Usage: acme.hello.sayhi [options] 

Options:

  --help                      : Display the command usage.
```

## Storm Modules

This package implements the following Storm Modules.


<a id="stormmod-acme-hello-acme-hello"></a>

### acme.hello


#### woot(text)

Print a message to the Storm runtime.

**Args:**

- `text` (`str`): The message to print.


**Returns:**
Always returns null. The return type is `null`.

<a id="stormmod-acme-hello-acme-hello-privsep"></a>

### acme.hello.privsep


#### getFooByBar(bar)

Look up a foo by its bar using the Acme API.

The API key is read from protected storage and used on the caller's
behalf, so a caller who may import this module never sees the key.


**Args:**

- `bar` (`str`): The bar value to look up.


**Returns:**
The decoded JSON response, or null if the API call failed. The return type is `dict`.
