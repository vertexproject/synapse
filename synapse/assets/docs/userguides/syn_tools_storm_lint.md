<a id="syn-tools-storm-lint"></a>

# storm.lint

The Synapse `storm.lint` tool checks Storm code for syntax errors, code which does not run as intended on Synapse 3.x, and Storm which could be written more simply. It parses the Storm locally and does not connect to a Cortex.

## Syntax

`storm.lint` is executed using `python -m synapse.tools.storm.lint`. The command usage is as follows:

```text
python -m synapse.tools.storm.lint -h
usage: synapse.tools.storm.lint [-h] [--select SELECT] [--ignore IGNORE]
                                [--enable ENABLE] [--config CONFIG]
                                [--format {text,json}] [--show-rules]
                                [paths ...]

Lint Storm code.

Each path is a file, a directory which is searched recursively for *.storm files, or - to read stdin.

Without --config, settings are read from the [tool.stormlint] table of the nearest pyproject.toml
which has one, searching upward from the current directory.

With --format json, each finding or file error is printed as one JSON object per line.

Exit codes: 0 when clean, 1 when there are findings, 2 on a usage, config or file error.

positional arguments:
  paths                 Files or directories to lint (use - for stdin).

options:
  -h, --help            show this help message and exit
  --select SELECT       Comma-separated rule IDs or prefixes to run in place
                        of the default rules.
  --ignore IGNORE       Comma-separated rule IDs or prefixes to disable.
  --enable ENABLE       Comma-separated rule IDs or prefixes to add to the
                        selected rules, such as rules which are off by
                        default.
  --config CONFIG       Path to a pyproject.toml with a [tool.stormlint]
                        table.
  --format {text,json}  Print findings as text, or as one JSON object per
                        line.
  --show-rules          Print the lint rules and exit.

```

Each path may be:

- a Storm file, which is linted whatever its extension,
- a directory, which is searched recursively for `*.storm` files, or
- `-`, which reads Storm code from stdin.

For example, to lint every Storm file in a Power-Up and a query read from stdin:

```bash
python -m synapse.tools.storm.lint acme-hello/storm/
echo '$x = $lib.true' | python -m synapse.tools.storm.lint -
```

## Output

Each finding is printed as `<path>:<line>:<column>: <rule> <message>`, followed by a count of the findings:

```text
example.storm:1:6: R001 $lib.true was removed, use (true).
example.storm:3:11: S005 Use a list literal such as ([]) instead of $lib.list().
Found 2 errors.
```

When there are no findings, the tool prints `All checks passed!`.

### JSON Output

`--format json` prints each finding as one JSON object per line, with `path`, `line`, `column`, `rule`, `severity` and `mesg` keys, and no summary line. A file which could not be read is printed as an object with `path` and `error` keys. When there are no findings, nothing is printed:

```text
python -m synapse.tools.storm.lint --format json example.storm
{"path":"example.storm","line":1,"column":6,"rule":"R001","severity":"high","mesg":"$lib.true was removed, use (true)."}
{"path":"example.storm","line":3,"column":11,"rule":"S005","severity":"low","mesg":"Use a list literal such as ([]) instead of $lib.list()."}
```

The exit codes are the same for both formats. A usage or configuration error is printed as text. `--show-rules` always prints text.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No findings. |
| `1` | One or more findings. |
| `2` | A usage error, an invalid configuration, an unknown rule ID, or a file which could not be read. |

## Selecting Rules

Three options choose which rules run:

- `--select` is exclusive: it replaces the default rule set, so only the selected rules run. Without it, every rule which is on by default is run.
- `--enable` is additive: it adds rules to the selected set, which is mostly used to turn on rules which are off by default.
- `--ignore` removes rules from the selected set.

Each option takes a comma-separated list of rule IDs or ID prefixes. A prefix matches every rule whose ID starts with it, so `S` matches every style rule and `S01` matches `S010` through `S016`. A rule named by `--select` or `--enable` runs whether or not it is on by default.

```bash
# only the 3.x runtime rules
python -m synapse.tools.storm.lint --select R mypkg/storm/

# the default rules, plus S010, S015 and S016 which are off by default
python -m synapse.tools.storm.lint --enable S010,S015,S016 mypkg/storm/

# the default rules, except the style rules
python -m synapse.tools.storm.lint --ignore S mypkg/storm/
```

`--show-rules` prints every rule with its severity, whether it is on by default, its name and its description, and exits.

## Suppressing Findings

A `// noqa` comment suppresses findings reported on its line. A `// noqa: <ID>` comment suppresses only the named rules, and takes a comma-separated list of rule IDs or ID prefixes:

```storm
$x = $lib.true            // noqa
$y = $lib.dict()          // noqa: S005
$z = $lib.list($lib.null) // noqa: R001, S005
```

A parse failure (`E001`) is always reported and cannot be suppressed.

## Configuration

Default options may be set in a `[tool.stormlint]` table in a `pyproject.toml` file. Without `--config`, the tool uses the nearest `pyproject.toml` with a `[tool.stormlint]` table, searching upward from the current directory. `--config <path>` reads the table from the given `pyproject.toml` instead.

```toml
[tool.stormlint]
select = ["E", "R", "S"]
ignore = ["S002"]
enable = ["S015"]
exclude = [
    "tests/files/*",
    "storm/vendored.storm",
]
```

| Key | Description |
|-----|-------------|
| `select` | Rule IDs or prefixes to run, in place of the default rules. Only the selected rules run. |
| `ignore` | Rule IDs or prefixes to skip. |
| `enable` | Rule IDs or prefixes to add to the selected rules, such as rules which are off by default. |
| `exclude` | Glob patterns, relative to the directory of the `pyproject.toml`, for files and directories which are not linted. |

Each value is a list of strings. A command line option replaces the configured value for the same key rather than adding to it. An unknown key or a value which is not a list of strings is a configuration error.

## Rules

Rule IDs are grouped by prefix: `E` rules report errors, `R` rules report code which does not run as intended on Synapse 3.x, `P` rules report pipeline usage which may not do what was intended, and `S` rules report Storm which could be written more simply.

| ID | Name | Severity | Default | Description |
|----|------|----------|---------|-------------|
| `E001` | `parse-failure` | high | yes | The Storm code failed to parse. This finding is always reported and cannot be suppressed. |
| `E002` | `invalid-escape` | high | yes | A double-quoted or backtick string contains a backslash escape which is not a valid Python string escape. Single-quoted strings do not process escapes and are not checked. |
| `E003` | `duplicate-function` | high | yes | A function is defined more than once in the same scope. |
| `P001` | `spin` | low | yes | The `spin` command discards the nodes in the pipeline. Run the query whose nodes are not needed in an `exec { ... }` block, which discards the nodes it yields, or isolate it in a function which uses `return()` or a `fini` block. |
| `P002` | `spin-return` | medium | yes | `spin \| return(...)` runs the return after consuming every node. Use `return(...)` when only one node can flow, `fini { return(...) }` when more than one can, or run the query which yields the nodes in an `exec { ... }` block. |
| `R001` | `lib-constant` | high | yes | `$lib.true`, `$lib.false` and `$lib.null` were removed in 3.x. Use `(true)`, `(false)` and `(null)`. |
| `R002` | `gtor-call` | high | yes | `$node.value`, `$node.form`, `$node.ndef`, `$lib.version.synapse` and `$lib.version.commit` are gtors in 3.x and can not be called. Drop the parentheses. |
| `R003` | `node-iden` | high | yes | `$node.iden` was removed in 3.x. |
| `R004` | `bare-constant` | medium | yes | A bare `true`, `false` or `null` used as an assignment value, call argument, return value or function argument default is the string `"true"`, `"false"` or `"null"`. Use `(true)`, `(false)` or `(null)`, or quote the string. |
| `R005` | `removed-api` | high | yes | A `$lib` API which was removed in 3.x is used, such as `$lib.str`, `$lib.text`, `$lib.user`, `$lib.ps`, `$lib.bytes.put()` or the `$lib.gen` helpers. The message names the replacement when there is one. `$lib.vars`, `$lib.globals`, `$lib.env` and user vars (`$user.vars`) are dict-like in 3.x, so calling `get()`, `set()`, `pop()`, `list()` and similar methods on them is reported. Read and assign `$lib.globals.<name>`, assign `$lib.undef` to delete, and iterate with a `for` loop. |
| `S001` | `guid-seed` | medium | yes | A guid form node is added with a value from `$lib.guid()`. Use a list seed such as `[ form=(a, $b) ]`, or `[ form=* ]` for a random guid. The resulting guid may differ, so verify it before changing existing code. |
| `S002` | `unnecessary-parens` | low | yes | Parens open an expression. Inside one which is already open, a literal, variable, call, or nested dict or list needs no parens of its own, and a lone variable assigned, passed as an argument or returned needs none either: `($y)` is just `$y`. Parens are still required around a literal value such as `(true)` or `(10)`, a dict or list literal used as a value, and grouping which changes precedence. Grouping a compound sub-expression is never reported. |
| `S003` | `edge-yield` | low | yes | An edge edit uses a subquery which only yields a variable. Use the variable directly, such as `+(refs)> $v` instead of `+(refs)> { yield $v }`. |
| `S004` | `return-null` | low | yes | `return((null))` and `return($lib.null)` return the same value as `return()`. |
| `S005` | `lib-list-dict` | low | yes | `$lib.list()` and `$lib.dict()` should be list and dict literals such as `([])` and `({})`. |
| `S006` | `print-kwargs` | low | yes | `$lib.print()` and `$lib.warn()` format their message with kwargs. Use a backtick format string. |
| `S008` | `guarded-for` | low | yes | An `if` statement which only guards a `for` loop over the variable it tests. An empty or null value iterates zero times, so the guard is not needed. The guard is only redundant when no node is in the pipeline, because a `for` loop over an empty or null value drops the inbound node. Verify it before changing existing code. |
| `S010` | `guarded-prop-set` | low | no | An `if` statement which only sets a property to the variable it tests. Use `?=` which skips a null value. The `if` statement also skips a value which is not null but is false, such as `0`, an empty string or an empty list, while `?=` sets it, and `?=` also skips a value which fails to norm. Verify the value can not be one of those before changing existing code. |
| `S011` | `subquery-lift-value` | low | yes | A property is set from a subquery which only lifts a form by its primary value. Set the property to the value directly, using an `as` cast when it needs norming into the form type. |
| `S012` | `lift-filter` | low | yes | A query lifts a form and then filters on one of its properties by a value which does not read the node. Lift by the property instead. |
| `S014` | `try-cast` | low | yes | A `try` block calls `$lib.cast()`. Use `$lib.trycast()` and check its result instead. |
| `S015` | `return-import` | medium | no | A function returns a module from `$lib.import()`. In a privsep module the returned module inherits root privileges, and binding the import as `$__name` does not prevent that. Never return an imported module. |
| `S016` | `print-http-resp` | medium | no | An HTTP response or `$lib.axon.wget()` result is printed or logged. It includes the request headers, which carry credentials such as an API key. Print fields such as its code and reason instead. The rule follows variables assigned from `$lib.inet.http` calls and `$lib.axon.wget()` or `$lib.axon.wput()` in the same scope, until the variable is assigned something else. An assignment in an `if`, `try`, `switch`, loop, subquery or `empty` block only ends it for a print in the same block. A parameter of a function defined in the same query is followed when any call to the function passes it a response. Suppress a finding for an object which is known to hold no credentials with a `noqa` comment. |

## Linting from Python

The `synapse.lib.stormlint.StormLinter` class lints Storm text directly. It takes the same `select`, `ignore` and `enable` options as the tool, and its `lint()` method returns a list of `Finding` tuples, each with `rule`, `severity`, `line`, `column` and `mesg` fields, sorted by line, column and rule:

```python
import synapse.lib.stormlint as s_stormlint

linter = s_stormlint.StormLinter(enable=('S015',))
for finding in linter.lint('$x = $lib.true'):
    print(finding.rule, finding.line, finding.column, finding.mesg)
```

By default the rules which check form and property names, such as `S011` and `S012`, use the built-in data model. Pass a data model dictionary, in the shape returned by the Cortex `getModelDict()` API, as `model` to check names against that model instead, including its extended model forms and properties:

```python
linter = s_stormlint.StormLinter(model=await core.getModelDict())
```

The Cortex MCP server's `storm_lint` tool lints a query this way against the Cortex's own data model.

`StormLinter` raises `BadArg` for an unknown rule ID or prefix. `lint()` honors `noqa` comments; the `[tool.stormlint]` table is only read by the `storm.lint` tool.
