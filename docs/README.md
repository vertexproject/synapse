# mdstorm

`synapse.lib.mdstorm` is a Markdown-native pre-processor for embedding and executing Storm
queries inside `.md` files. It replaced the older RST/`rstorm` pipeline (`synapse.lib.rstorm`,
now removed), with the directives moved from RST directive lines to fenced Markdown code
blocks, and the directive set itself consolidated (see "Converting from the old directives"
below).

Run it with:

```bash
python -m synapse.tools.utils.mdstorm mydoc.md --save mydoc.out.md
```

## Directives

A directive is a fenced code block whose info string starts with `mdstorm`, `mdstorm-setup`,
`mdshell`, `mdinclude`, or `mdautodoc` (optionally followed by flags -- see below). Any other
fenced block (` ```python `, ` ```json `, or a plain ` ```storm ` example left for future syntax
highlighting) passes through untouched.

- ` ```mdstorm ` -- run a Storm query and render its output. Recognizes `--hide-query`,
  `--hide-tags`, `--hide-props`, `--vars`, `--opts`, `--fail`, `--hide-output`, `--hide`, and
  `--mock-http`.
- ` ```mdstorm-setup ` -- one-time, whole-document setup: which Cortex to run against, packages/
  services to load, VCR options, and default envvars. Recognizes `--cortex`, `--vcr-opts`,
  `--envvar`, `--load-pkg`, and `--load-svc`.
- ` ```mdshell ` -- run a shell command and render its output. Recognizes
  `--include-stderr`, `--hide-query`, and `--fail-ok`.
- ` ```mdinclude ` -- splice another file's content into the document verbatim. Takes one
  required positional `path` (relative to the including document unless absolute) and an
  optional `--code LANG`, which wraps the content in a fenced code block with that info string
  instead of splicing it in as literal Markdown.
- ` ```mdautodoc ` -- generate Markdown and splice it into the document at the point of use.
  Recognizes exactly one of `--conf CTOR` (a Cell subclass's confdefs), `--api CTOR` (a class's
  own public methods, `cls.__dict__` not its full MRO), `--stormpkg PATH` (a Storm package's
  command/module/dependency/endpoint reference, given the package prototype .yaml path, relative
  to the including document unless absolute), `--model-types`, `--model-forms`,
  `--stormtypes-libs`, or `--stormtypes-prims`, plus an optional `--level N` that shifts every
  heading in the generated block down N levels, so it renders as a section under an
  author-written heading rather than a whole page.

Flags may be given on the opening fence line, in the fence body, or both. Body flags occupy one or
more lines at the top of the body -- the flags themselves don't need to be one per line, or in any
particular arrangement -- but that flags region must be terminated by a line containing exactly
`--` and nothing else (the terminator itself does need to be alone on its line); everything after
that line is the literal query (or command) text, rendered in the doc exactly as authored.
`mdstorm-setup`, `mdinclude`, and `mdautodoc` are the exception -- their whole body is flags/path,
so no `--` terminator is needed there.

    ```mdstorm
    --vars {"targ": "vertex.link"}
    --
    inet:fqdn=$targ
    ```

is equivalent to putting the flag on the fence line instead:

    ```mdstorm --vars {"targ": "vertex.link"}
    inet:fqdn=$targ
    ```

## Converting from the old directives

The old `rstorm` directive set was spread across many one-off directives, several of which set
shared state that silently applied to every later directive in the document. `mdstorm` folds all
of that into per-call flags on `mdstorm`/`mdstorm-setup`/`mdshell`, so each fence is
self-contained.

| Old (`rstorm`)                  | New (`mdstorm`)                                          |
|----------------------------------|-----------------------------------------------------------|
| `.. storm::`                    | ` ```mdstorm `                                             |
| `.. storm-cli::`                | ` ```mdstorm `                                             |
| `.. storm-pre::`                | ` ```mdstorm ` with `--hide`                               |
| `.. storm-fail::`                | `--fail` on the individual ` ```mdstorm ` fence            |
| `.. storm-opts::`                | `--vars`/`--opts` on the individual ` ```mdstorm ` fence   |
| `.. storm-cortex::`              | `--cortex` on ` ```mdstorm-setup `                         |
| `.. storm-pkg::`                 | `--load-pkg` on ` ```mdstorm-setup `                       |
| `.. storm-svc::`                 | `--load-svc` on ` ```mdstorm-setup `                       |
| `.. storm-envvar::`              | `--envvar` on ` ```mdstorm-setup `                         |
| `.. storm-vcr-opts::`            | `--vcr-opts` on ` ```mdstorm-setup `                       |
| `.. storm-mock-http::`           | `--mock-http` on the CLI (document default) or on an individual ` ```mdstorm ` fence (overrides the default for that one call -- for documents with more than one distinct cassette) |
| `.. storm-clear-http::`          | removed -- not needed; `--mock-http` is scoped per run     |
| `.. storm-vcr-callback::`        | removed -- use `--mock-http` with a recorded cassette      |
| `.. shell::`                     | ` ```mdshell `                                             |
| `.. shell-env::`                 | `--envvar` on ` ```mdstorm-setup `                         |
| `.. storm-python-path::`         | removed -- no longer needed                                |
| `.. storm-multiline::`           | removed -- a fence body is already multi-line              |
| `.. storm-expect::`              | removed -- was already a no-op in `rstorm`                 |
| `.. include::`                   | ` ```mdinclude `                                           |
| `.. literalinclude::`            | ` ```mdinclude ` with `--code LANG`                        |

Where `rstorm` set shared context once (`storm-cortex`, `storm-opts`, `storm-envvar`,
`storm-vcr-opts`) that applied to every following directive, `mdstorm-setup` still runs once per
document, but everything else (`--vars`/`--opts`/`--fail`/etc.) is now a per-call flag on the
fence it belongs to.

## Examples

Set up a Cortex once for the document, load a Storm package into it, and load a fully-qualified
domain name, hiding the query line but keeping the output:

    ```mdstorm-setup
    --load-pkg ../assets/synapse-mypkg.yaml
    ```

    ```mdstorm --hide-query --vars {"targ": "vertex.link"}
    [ inet:fqdn=$targ ]
    ```

Show a query that is expected to raise an error, rendering the error in the doc instead of
failing the build:

    ```mdstorm --fail
    $lib.raise(BadArg, "no such target")
    ```

Splice in a Cell's confdefs, nested under an author-written heading, or splice in a Kubernetes
manifest as a highlighted code block:

    ### Cortex Configuration Options

    ```mdautodoc --conf synapse.cortex.Cortex --level 1
    ```

    ```mdinclude --code yaml
    kubernetes/cortex.yaml
    ```

## Getting help

The full set of directives and their flags is generated from the same argparse definitions
`mdstorm` uses to run them, so it can never drift out of sync with the code. To see it:

```bash
python -m synapse.tools.utils.mdstorm --help
```
