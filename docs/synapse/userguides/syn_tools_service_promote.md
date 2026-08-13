<a id="syn-tools-service-promote"></a>


# service.promote

The Synapse `service.promote` tool can be used to promote a mirror to the leader.

## Syntax

`service.promote` is executed using `python -m synapse.tools.service.promote`. The command usage is as follows:

```mdshell --fail-ok
python -m synapse.tools.service.promote -h
```

> [!WARNING]
> By default this tool performs a graceful handoff coordinated with the current leader. The `--failure` option forces promotion without that coordination and should only be used once the current leader is confirmed offline -- if it is actually still alive and reachable, using `--failure` will very likely render it unusable, requiring a restore from backup. See [Promoting a Mirror](../devopsguide.md#devops-task-promote) for details.

> [!NOTE]
> This tool was previously run using `synapse.tools.promote`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
