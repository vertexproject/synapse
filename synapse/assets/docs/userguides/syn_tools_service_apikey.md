<a id="syn-tools-service-apikey"></a>

# service.apikey

The Synapse `service.apikey` tool can be used to add, list, or delete user API keys from a Synapse service.

## Syntax

`apikey` is executed using `python -m synapse.tools.service.apikey`. The command usage is as follows:

```text
python -m synapse.tools.service.apikey -h
usage: synapse.tools.service.apikey [-h] [--url URL] {add,list,del} ...

Add, list, or delete user API keys from a Synapse service.

positional arguments:
  {add,list,del}
    add           Add a user API key.
    list          List user API keys.
    del           Delete a user API key.

options:
  -h, --help      show this help message and exit
  --url URL       The telepath URL of the Synapse service.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.apikey`. It can still be run with that name.
