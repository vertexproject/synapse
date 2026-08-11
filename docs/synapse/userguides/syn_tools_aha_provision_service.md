<a id="syn-tools-aha_provision_service"></a>


# aha.provision.service

The Synapse `aha.provision.service` tool can be used to prepare provisioning entries in the AHA server.

> [!NOTE]
> Most deployments should use automatic provisioning via the shared `SYN_PROVISION_SECRET` environment variable rather than this tool. To deploy a service as a follower (mirror) of an existing leader, also set `SYN_PROVISION_FOLLOWER` so it clones from the current leader rather than booting fresh. See [Service Provisioning](../deploymentguide.md#deploy_provisioning) in the deployment guide. This tool remains available for advanced use cases.

## Syntax

`aha.provision.service` is executed using `python -m synapse.tools.aha.provision.service`. The command usage is as follows:

```mdshell --fail-ok
python -m synapse.tools.aha.provision.service -h
```
