<a id="syn-tools-service-shutdown"></a>


# service.shutdown

The Synapse `service.shutdown` tool can be used to initiate a graceful shutdown of a Synapse service.

## Syntax

`service.shutdown` is executed using `python -m synapse.tools.service.shutdown`. The command usage is as follows:

```mdshell --fail-ok
python -m synapse.tools.service.shutdown -h
```

> [!NOTE]
> This tool was previously run using `synapse.tools.shutdown`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
