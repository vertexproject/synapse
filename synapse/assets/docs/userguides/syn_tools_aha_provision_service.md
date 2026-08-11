<a id="syn-tools-aha_provision_service"></a>

# aha.provision.service

The Synapse `aha.provision.service` tool can be used to prepare provisioning entries in the AHA server.

> [!NOTE]
> Most deployments should use automatic provisioning via the shared `SYN_PROVISION_SECRET` environment variable rather than this tool. To deploy a service as a follower (mirror) of an existing leader, also set `SYN_PROVISION_FOLLOWER` so it clones from the current leader rather than booting fresh. See [Service Provisioning](../deploymentguide.md#deploy_provisioning) in the deployment guide. This tool remains available for advanced use cases.

## Syntax

`aha.provision.service` is executed using `python -m synapse.tools.aha.provision.service`. The command usage is as follows:

```text
python -m synapse.tools.aha.provision.service -h
usage: synapse.tools.aha.provision.service [-h] [--url URL]
                                           [--cellyaml CELLYAML]
                                           [--dmon-port DMON_PORT]
                                           [--https-port HTTPS_PORT]
                                           [--only-url]
                                           svcname

A tool to prepare provisioning entries in the AHA server.

Examples:

    # provision a new service named 000.axon from within the AHA container.
    python -m synapse.tools.aha.provision.service 000.axon

    # provision a new service named 001.cortex from within the AHA container. it will
    # follow the current leader for its service type until promoted.
    python -m synapse.tools.aha.provision.service 001.cortex

positional arguments:
  svcname               The name of the service relative to the AHA network.

options:
  -h, --help            show this help message and exit
  --url URL             The telepath URL to connect to the AHA service.
  --cellyaml CELLYAML   Specify the path to a YAML file containing config
                        options for the service.
  --dmon-port DMON_PORT
                        Provision the services SSL listener on a given port.
  --https-port HTTPS_PORT
                        Provision the services HTTPS listener on a given port.
  --only-url            Only output the URL upon successful execution

```
