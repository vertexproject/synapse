<a id="syn-tools-aha_provision_user"></a>

# aha.provision.user

The Synapse `aha.provision.user` tool can be used to create a new user auto-enroll entry on an AHA server.

## Syntax

`aha.provision.user` is executed using `python -m synapse.tools.aha.provision.user`. The command usage is as follows:

```text
python -m synapse.tools.aha.provision.user -h
usage: synapse.tools.aha.provision.user [-h] [--url URL] [--again]
                                        [--only-url]
                                        username

A tool to create a new user auto-enroll entry on an AHA server.

Examples:

    # Create a new one-time use key to enroll a user
    python -m synapse.tools.aha.provision.user visi

    # Create an addtional key for an existing user.
    python -m synapse.tools.aha.provision.user --again visi

positional arguments:
  username    The username which will be enrolled as <username>@<network>.

options:
  -h, --help  show this help message and exit
  --url URL   The telepath URL to connect to the AHA service.
  --again     Generate a new enroll URL for an existing user.
  --only-url  Only output the URL upon successful execution

```
