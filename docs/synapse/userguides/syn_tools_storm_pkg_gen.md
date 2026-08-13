<a id="syn-tools-storm-pkg-gen"></a>


# storm.pkg.gen

The Synapse `storm.pkg.gen` tool can be used to generate a Storm [Package](../glossary.md#gloss-package) containing new Storm commands and Storm modules from a YAML definition and optionally push it to a Cortex.

For additional details on using the `storm.pkg.gen` tool see [Building / Loading](../devguides/power-ups.md#dev-rapid-power-ups-build) a Rapid Power-Up.

## Syntax

`storm.pkg.gen` is executed using `python -m synapse.tools.storm.pkg.gen`. The command usage is as follows:

```mdshell --fail-ok
python -m synapse.tools.storm.pkg.gen -h
```

> [!NOTE]
> This tool was previously run using `synapse.tools.genpkg`, which was removed in Synapse 3.0.0. See [CLI Tool Changes](../300_changes/devops-cli-tools.md#vtx_300_devops-cli-tools).
