<a id="syn-tools-service-backup"></a>

# service.backup

The Synapse `service.backup` tool can be used to create an optimized backup of a Synapse directory.

## Syntax

`service.backup` is executed using `python -m synapse.tools.service.backup`. The command usage is as follows:

```text
python -m synapse.tools.service.backup -h
usage: synapse.tools.service.backup [-h] [--skipdirs SKIPDIRS [SKIPDIRS ...]]
                                    source dstdir

Create an optimized backup of a Synapse service, from a local directory or a
running service URL.

positional arguments:
  source                Path to a Synapse directory, or a telepath URL of a
                        running Synapse service.
  dstdir                Backup target: a directory when backing up a local
                        path, or a .zip file path when backing up a service
                        URL.

options:
  -h, --help            show this help message and exit
  --skipdirs SKIPDIRS [SKIPDIRS ...]
                        Glob patterns of relative directory names to exclude
                        from the backup (local path only).
```

> [!NOTE]
> This tool was previously run using `synapse.tools.backup`. It can still be run with that name.
