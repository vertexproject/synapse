Ingest - Parsing JSONL
======================

The "jsonl" format is a combination of the lines and JSON formats. It assumes the data it is processing is a multi-line
document, and each line of the document is a single json blob which needs to be deserialized and ingested. A simple
jsonl file is shown below:

.. literalinclude:: ../examples/ingest_structured_dnsa2.jsonl

This is similar to the earlier CSV data; except each line may have multiple objects we want to consume, and we've got
to treat the data as a list of JSON dictionaries. This will require directly iterating on the data we are consuming
and creating the nodes from that. A wilcard ``*`` can be used to indicate to iterate directly over the object being
processed. This ingest can be seen below:

.. literalinclude:: ../examples/ingest_structured_dnsa2.json
    :language: json
    :emphasize-lines: 13

It can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose --core sqlite:///ingest_examples.db  docs/synapse/examples/ingest_structured_dnsa2.json

After ingesting this, we can see the various nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///ingest_examples.db
    cli> ask #src.jsonldemo
    inet:dns:a = acmecorp.knight.net/8.8.8.8
        #src.jsonldemo (added 2017/08/18 00:36:21.414)
    inet:dns:a = foobar.com/192.168.0.1
        #src.jsonldemo (added 2017/08/18 00:36:21.414)
    inet:dns:a = knight.net/10.20.30.40
        #src.jsonldemo (added 2017/08/18 00:36:21.414)
    inet:dns:a = knight.net/127.0.0.1
        #src.jsonldemo (added 2017/08/18 00:36:21.414)
    inet:dns:a = w00t.foobar.com/192.168.0.100
        #src.jsonldemo (added 2017/08/18 00:36:21.414)
    (5 results)
