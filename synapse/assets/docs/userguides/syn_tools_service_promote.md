<a id="syn-tools-service-promote"></a>

# service.promote

The Synapse `service.promote` tool can be used to promote a mirror to the leader.

## Syntax

`service.promote` is executed using `python -m synapse.tools.service.promote`. The command usage is as follows:

```text
python -m synapse.tools.service.promote -h
usage: synapse.tools.service.promote [-h] [--url URL] [--failure]

Promote a mirror to the leader.

By default this performs a graceful handoff coordinated with the current
leader. Use --failure only when the current leader is confirmed offline;
if it is actually still alive, this will very likely render it unusable.

Example (being run from a Cortex mirror docker container):
    python -m synapse.tools.service.promote

options:
  -h, --help  show this help message and exit
  --url URL   The telepath URL of the Synapse service.
  --failure   Force promotion because the leader is offline and a graceful
              handoff is not possible. This does NOT stop the old leader from
              believing it is still the leader: if it is actually still alive
              and reachable, it will very likely detect a leadership schism
              and require a restore from backup. Only use this once the old
              leader is confirmed unreachable/offline.

```

> [!WARNING]
> By default this tool performs a graceful handoff coordinated with the current leader. The `--failure` option forces promotion without that coordination and should only be used once the current leader is confirmed offline -- if it is actually still alive and reachable, using `--failure` will very likely render it unusable, requiring a restore from backup. See [Promoting a Mirror](../devopsguide.md#devops-task-promote) for details.

> [!NOTE]
> This tool was previously run using `synapse.tools.promote`. It can still be run with that name.
