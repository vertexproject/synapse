<a id="syn-tools-cortex-feed"></a>


# cortex.feed

The Synapse `cortex.feed` tool is a way to ingest data exported from one Cortex into another Cortex. Users should be familiar with both the Synapse data model ([Data Model Objects](data_model.md#data-model-terms) et al.) as well as Synapse concepts such as packed nodes in order to use and understand the `cortex.feed` tool effectively.

## Syntax

The `cortex.feed` tool is executed from an operating system command shell. The command usage is as follows (line is wrapped for readability):

``` text
usage: synapse.tools.cortex.feed [-h] (--cortex CORTEX | --test) [--debug] [--modules MODULES] [--chunksize CHUNKSIZE]
  [--offset OFFSET] [--view VIEW] [files ...]
```

Where: - `-h` displays detailed help and these command line options - `CORTEX` specifies the telapth URL to the Cortex where the data should be ingested.

- `--test` means to perform the ingest against a temporary, local Cortex instead of a live cortex, for testing or validation.
  - When using a temporary Cortex, you do not need to provide a path.
- `--debug` specifies to drop into an interactive prompt to inspect the state of the Cortex post-ingest.
- `MODULES` specifies a path to a Synapse CoreModule class that will be loaded into the temporary Cortex.
  - This option has no effect if the `--test` option is not specified
- `CHUNKSIZE` specifies how many lines or chunks of data to read at a time from the given files.
  - Defaults to 1000 if not specified
- `OFFSET` specifies how many chunks of data to skip over (starting at the beginning)
- `VIEW` specifies a View in the Cortex to ingest the data into.
- `files` is a series of file paths containing data to load into the Cortex (or temporary Cortex)
  - Every file must be either json-serialized data, msgpack-serialized data, yaml-serialized data, or a json lines file. The files do not have to all be of the same type.

### help

The detailed help (`-h`) output for the `cortex.feed` tool is shown below.

```mdshell --fail-ok
python -m synapse.tools.cortex.feed -h
```

> [!NOTE]
> This tool was previously run using `synapse.tools.feed`. It can still be run with that name.

## Ingest Examples - Overview

The `cortex.feed` tool

### Ingest Example 1

This example demonstrates loading a set of nodes via the `cortex.feed` tool. The nodes are of a variety of types, and are encoded in a json lines (jsonl) format.

**JSONL File:**

The jsonl file (`testnodes.jsonl`) contains a list of nodes in their packed form, as returned by `Node.pack()` and written by a `.nodes` export. Each line corresponds to a single node. Each value in `props`, `tags` and `tagprops` is a two element envelope, `[<valu>, <info>]`, where the info dict may carry a `t` type name, an `r` repr and a `v` dict of virtual property values. The ingest reads `props`, `tags`, `tagprops`, `nodedata` and `edges`; the `nid` and `meta` entries are informational and are ignored.

``` text
[["it:dev:function", "9710579930d831abd88acff1f2ecd04f"], {"nid": 0, "meta": {"created": 1786357031915388, "updated": 1786357031916842}, "tags": {"my": [[null, null, null], {}], "my.cool": [[null, null, null], {}], "my.cool.tag": [[null, null, null], {}]}, "props": {"name": ["CreateRemoteThread", {"t": "it:dev:str"}], "desc": ["An example function", {"t": "text"}]}, "tagprops": {}, "n1verbs": {}, "n2verbs": {}}]
[["inet:ip", [4, 386412289]], {"nid": 5, "meta": {"created": 1786357031920431, "updated": 1786357031920897}, "tags": {"my": [[null, null, null], {}], "my.cool": [[null, null, null], {}], "my.cool.tag": [[null, null, null], {}]}, "props": {"version": [4, {"t": "inet:ipversion"}], "type": ["unicast", {"t": "str:lower"}]}, "tagprops": {}, "n1verbs": {}, "n2verbs": {}}]
[["inet:url", "https://noexist.vertex.link/en/latest/synapse/userguide.html#userguide"], {"nid": 6, "meta": {"created": 1786357031924803, "updated": 1786357031926711}, "tags": {"my": [[null, null, null], {}], "my.cool": [[null, null, null], {}], "my.cool.tag": [[null, null, null], {}]}, "props": {"proto": ["https", {"t": "str:lower"}], "path": ["/en/latest/synapse/userguide.html#userguide", {"t": "str"}], "params": ["", {"t": "str"}], "host": ["noexist.vertex.link", {"t": "inet:fqdn"}], "port": [443, {"t": "inet:port"}], "base": ["https://noexist.vertex.link/en/latest/synapse/userguide.html#userguide", {"t": "str"}]}, "tagprops": {}, "n1verbs": {}, "n2verbs": {}}]
[["file:bytes", "65d80fbfc2984751710c3de0f4ca55ad"], {"nid": 10, "meta": {"created": 1786357031954252, "updated": 1786357031955605}, "tags": {"my": [[null, null, null], {}], "my.cool": [[null, null, null], {}], "my.cool.tag": [[null, null, null], {}]}, "props": {"sha256": ["ffd19426d3f020996c482255b92a547a2f63afcfc11b45a98fb3fb5be69dd75c", {"t": "crypto:hash:sha256"}], "size": [16, {"t": "int"}], "md5": ["be1bb5ab2057d69fb6d0a9d0684168fe", {"t": "crypto:hash:md5"}], "sha1": ["57d13f1fa2322058dc80e5d6d768546b47238fcd", {"t": "crypto:hash:sha1"}]}, "tagprops": {}, "n1verbs": {}, "n2verbs": {}}]
```

**Verifying the Data:**

Typically, users will want to double check the data they have before loading it into a production Cortex. The `cortex.feed` tool allows us to perform an ingest our of nodes file against an empty, ephemeral Cortex, so that we can check what nodes get created before adding them to a production Cortex. To load `testnodes.jsonl` into an ephemeral Cortex and drop into a prompt to explore the ingested nodes, run:

``` text
python -m synapse.tools.cortex.feed --test --debug testnodes.jsonl
```

Assuming the command completed with no errors, we should now have a `storm` prompt connected to our test Cortex:

``` text
storm>
```

From which we can issue Storm commands to interact with and validate the nodes that were just ingested. For example:

``` text
storm> #my.cool.tag
it:dev:function=9710579930d831abd88acff1f2ecd04f
        :desc = An example function
        :name = CreateRemoteThread
        #my.cool.tag
inet:ip=23.8.47.1
        :type = unicast
        :version = 4
        #my.cool.tag
inet:url=https://noexist.vertex.link/en/latest/synapse/userguide.html#userguide
        :base = https://noexist.vertex.link/en/latest/synapse/userguide.html#userguide
        :host = noexist.vertex.link
        :params =
        :path = /en/latest/synapse/userguide.html#userguide
        :port = 443
        :proto = https
        #my.cool.tag
file:bytes=65d80fbfc2984751710c3de0f4ca55ad
        :md5 = be1bb5ab2057d69fb6d0a9d0684168fe
        :sha1 = 57d13f1fa2322058dc80e5d6d768546b47238fcd
        :sha256 = ffd19426d3f020996c482255b92a547a2f63afcfc11b45a98fb3fb5be69dd75c
        :size = 16
        #my.cool.tag
complete. 4 nodes in 4 ms (1000/sec).
```

**Loading the Data:**

Once we've inspected and verified the data is acceptable for loading, we can point the `cortex.feed` tool to the Cortex we want to load the nodes into, and the same nodes should be added.

``` text
python -m synapse.tools.cortex.feed --cortex "aha://cortex..." testnodes.jsonl
```

However, once we've inspected the data, let's say that the `it:dev:function` and `inet:ip` nodes are not allowed in the production Cortex, but the `inet:url` and `file:bytes` are. We can skip these two nodes by using a combination of the `chunksize` and `offset` parameters:

``` text
python -m synapse.tools.cortex.feed --cortex "aha://cortex..." testnodes.jsonl --chunksize 2 --offset 1
```

With the `chunksize` parameter signifying that the `cortex.feed` tool should read two lines at a time from the file and process those before reading the next line, and the `offset` parameter meaning the `cortex.feed` tool should skip all lines before and including line 1 (so lines 1 and 0) when attempting to add nodes, and only add nodes once it's read in lines 2 and beyond.
