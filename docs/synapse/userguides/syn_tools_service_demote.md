<a id="syn-tools-service-demote"></a>


# service.demote

The Synapse `service.demote` tool can be used to automatically select a new leader and demote this service.

## Syntax

`service.demote` is executed using `python -m synapse.tools.service.demote`. The command usage is as follows:

```mdshell --fail-ok
python -m synapse.tools.service.demote -h
```

> [!NOTE]
> This tool was previously run using `synapse.tools.demote`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
