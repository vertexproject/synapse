<a id="syn-tools-service-moduser"></a>

# service.moduser

The Synapse `service.moduser` tool can be used to add, modify, or list users of a Synapse service.

## Syntax

`service.moduser` is executed using `python -m synapse.tools.service.moduser`. The command usage is as follows:

```text
python -m synapse.tools.service.moduser -h
usage: synapse.tools.service.moduser [-h] [--url URL] [--add] [--del] [--list]
                                     [--admin {true,false}] [--passwd PASSWD]
                                     [--email EMAIL] [--locked {true,false}]
                                     [--grant GRANT] [--revoke REVOKE]
                                     [--allow ALLOW] [--deny DENY]
                                     [--gate GATE]
                                     [username]

Add, modify, or list users of a Synapse service.

positional arguments:
  username              The username to add/edit or show details.

options:
  -h, --help            show this help message and exit
  --url URL             The telepath URL of the Synapse service.
  --add                 Add the user if they do not already exist.
  --del                 Delete the user if they exist.
  --list                List existing users of the service, or details of a
                        specific user.
  --admin {true,false}  Set the user admin status.
  --passwd PASSWD       A password to set for the user.
  --email EMAIL         An email to set for the user.
  --locked {true,false}
                        Set the user locked status.
  --grant GRANT         A role to grant to the user.
  --revoke REVOKE       A role to revoke from the user.
  --allow ALLOW         A permission string to allow for the user.
  --deny DENY           A permission string to deny for the user.
  --gate GATE           The iden of an auth gate to add/del rules or set admin
                        status on.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.moduser`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
