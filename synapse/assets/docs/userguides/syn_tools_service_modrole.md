<a id="syn-tools-service-modrole"></a>

# service.modrole

The Synapse `service.modrole` tool can be used to add or modify a role in a Synapse service.

## Syntax

`service.modrole` is executed using `python -m synapse.tools.service.modrole`. The command usage is as follows:

```text
python -m synapse.tools.service.modrole -h
usage: synapse.tools.service.modrole [-h] [--url URL] [--add] [--del] [--list]
                                     [--allow ALLOW] [--deny DENY]
                                     [--gate GATE]
                                     [rolename]

Add or modify a role in a Synapse service.

positional arguments:
  rolename       The rolename to add/edit.

options:
  -h, --help     show this help message and exit
  --url URL      The telepath URL of the Synapse service.
  --add          Add the role if they do not already exist.
  --del          Delete the role if it exists.
  --list         List existing roles, or rules of a specific role.
  --allow ALLOW  A permission string to allow for the role.
  --deny DENY    A permission string to deny for the role.
  --gate GATE    The iden of an auth gate to add/del rules on.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.modrole`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
