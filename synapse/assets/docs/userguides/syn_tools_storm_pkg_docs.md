<a id="syn-tools-storm-pkg-docs"></a>

# storm.pkg.doc

The Synapse `storm.pkg.doc` tool can be used to build Storm package documents from Markdown/mdstorm sources.

## Syntax

`storm.pkg.doc` is executed using `python -m synapse.tools.storm.pkg.doc`. The command usage is as follows:

```text
python -m synapse.tools.storm.pkg.doc -h
usage: synapse.tools.storm.pkg.doc [-h] [--save <dir>] [--ci]
                                   [--warnfile <path>]
                                   <pkgfile>

A tool for building a storm package docs/ directory into a files/docs bundle.

positional arguments:
  <pkgfile>          Path to a storm package prototype yaml file.

options:
  -h, --help         show this help message and exit
  --save <dir>       Output directory to build the bundle into. Defaults to
                     <pkgdir>/files/docs.
  --ci               Collect warnings/validation issues into --warnfile
                     instead of failing the build (see docs/Makefile
                     mddocs_ciflag for why).
  --warnfile <path>  With --ci, write warnings/validation issues here instead
                     of raising.

```
