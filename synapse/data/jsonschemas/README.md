# JSON Schemas

## What/Why?
This directory (synapse/data/jsonschemas) hosts any JSON schemas we want to be
locally cached. Two reasons for this:
1. Performance. fastjsonschema will attempt to download externally referenced
   json schemas every time it encounters one. This could obviously add a lot of
   latency to the (already kinda slow) validation.
2. Security. Some cortexes might not have direct access to the internet for
   security reasons. This allows the json schemas we rely on to continue to
   operate with external references.

## How?
The `s_config.getJsValidator()` function sets up a local schema handler which is
passed to fastjsonschema. The ref handler will parse the URL to get the path and
then look for the schema path starting from this directory as the root. If the
file is found, it is returned and used, if not an exception is raised. 
