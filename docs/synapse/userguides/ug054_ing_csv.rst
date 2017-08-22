Ingest - Parsing CSV
====================

Now that we've seen how to do an ingest of a simple file containing some lines of text, we can move onto more
complicated structures.  Comma Separated Value (CSV) support is provided via the built-in `csv`_ module.  If we look
at the file below we can see a few FQDN and IP address pairs:

.. literalinclude:: ../examples/ingest_structured_dnsa1.csv

When the CSV helper parses this file, it will return each line as though we were iterating over a csv.reader object.
For the sake of demonstration we'll ingest these in as as ``inet:dns:a`` records. We'll use the following ingest for
doing that:

.. literalinclude:: ../examples/ingest_structured_dnsa1.json
    :language: json

This ingest adds a "vars" section, which denotes variables which are extracted out of the data as we iterate over
the CSV file. The CSV data is just a list of values, and we denote which element of the list to associate with which
variable. That is done with the "path" directive - it can be used to extract specific items out of the data we are
iterating over. Since we do not have a single string we can use as the primary property to make a node, we've added the
"template" directive to the "forms" section.  This allows us to construct the primary property using a string template.
The vars we extracted are substituted into the ``{{domain}}`` and ``{{ipv4}}`` fields using ``str.replace``, after
calling ``str()`` on the vars.

This ingest can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///ingest_examples.db  docs/synapse/examples/ingest_structured_dnsa1.json

After ingesting this, we can see the ``inet:dns:a`` nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///ingest_examples.db
    /cli> ask --props inet:dns:a limit(1)
    inet:dns:a = vertex.link/127.0.0.1
        :fqdn = vertex.link
        :ipv4 = 127.0.0.1
    (1 results)

.. _`csv`: https://docs.python.org/3/library/csv.html
