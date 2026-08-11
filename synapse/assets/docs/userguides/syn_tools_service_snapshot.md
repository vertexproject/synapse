<a id="syn-tools-service-snapshot"></a>

# service.snapshot

The Synapse `service.snapshot` tool can be used to freeze/resume service operations to allow system admins to generate a transactionally consistent volume snapshot using 3rd party tools.

## Syntax

`service.snapshot` is executed using `python -m synapse.tools.service.snapshot`. The command usage is as follows:

```text
python -m synapse.tools.service.snapshot -h
usage: synapse.tools.service.snapshot [-h] {freeze,resume} ...

Command line tool to freeze/resume service operations to allow
system admins to generate a transactionally consistent volume
snapshot using 3rd party tools.

The use pattern should be::

    python -m synapse.tools.service.snapshot freeze

    <generate volume snapshot using 3rd party tools>

    python -m synapse.tools.service.snapshot resume

The tool will set the process exit code to 0 on success.

options:
  -h, --help       show this help message and exit

commands:
  {freeze,resume}
    freeze         Suspend edits and sync changes to disk.
    resume         Resume edits and continue normal operation.

```

> [!NOTE]
> This tool was previously run using `synapse.tools.snapshot`. It can still be run with that name.
