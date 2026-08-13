<a id="syn-tools-service-snapshot"></a>


# service.snapshot

The Synapse `service.snapshot` tool can be used to freeze/resume service operations to allow system admins to generate a transactionally consistent volume snapshot using 3rd party tools.

## Syntax

`service.snapshot` is executed using `python -m synapse.tools.service.snapshot`. The command usage is as follows:

```mdshell --fail-ok
python -m synapse.tools.service.snapshot -h
```

> [!NOTE]
> This tool was previously run using `synapse.tools.snapshot`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
