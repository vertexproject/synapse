<a id="syn-tools-service-shutdown"></a>

# service.shutdown

The Synapse `service.shutdown` tool can be used to initiate a graceful shutdown of a Synapse service.

## Syntax

`service.shutdown` is executed using `python -m synapse.tools.service.shutdown`. The command usage is as follows:

```text
python -m synapse.tools.service.shutdown -h
usage: synapse.tools.service.shutdown [-h] [--url URL] [--timeout TIMEOUT]
                                      [--drain]

Initiate a graceful shutdown of a service.

This tool puts the service into a state where no new tasks are
created. By default, tasks are cancelled instead of awaited,
allowing the operator to bound shutdown wall time. Pass --drain to
wait for promoted tasks to complete instead.

The --timeout value bounds the entire operation. Demote discovery, demote,
and task reaping share the single timeout value; no sub-phase may exceed
the time remaining when it starts.

Exit codes:
  0 - graceful shutdown was initiated successfully
  1 - the shutdown was aborted because the timeout was reached; the
      service may be in a partially shutdown state as a result of this
      timeout.
  2 - an unexpected error occurred

NOTE: This will also demote the service if run on a leader with mirrors.

options:
  -h, --help         show this help message and exit
  --url URL          The telepath URL to connect to the service.
  --timeout TIMEOUT  An optional timeout in seconds. If timeout is reached,
                     the shutdown is aborted.
  --drain            Wait for tasks to complete instead of cancelling them.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.shutdown`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
