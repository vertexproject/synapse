Ingest - Parsing Lines
======================

Parsing structured data is the bread and butter of the Ingest system, allowing us to extract data from various sources
and insert them into a Cortex.  Ths simplest form of structured data is where the structure is simply "parse one line
out of a file at a time". The example we'll work with is a list of Top Level Domains (TLDs) in file like so::

    # Version 2017012300, Last Updated Mon Jan 23 07:07:01 2017 UTC
    COM
    NET
    ORG
    NINJA

We can convert each line into a ``inet:fqdn`` node representing that TLD. The following ingest shows an example of
how to do that:

.. literalinclude:: ../examples/ingest_structured_tlds1.json
    :language: json

The structure of this ingest file differs from the previous example showing the "embed" directive.  This uses the
"sources" directive. This directive specifies a source file and a dictionary continaing "open" and "ingest" directives.
The open directive is below and tells us how to open the file and how it is shaped:

.. literalinclude:: ../examples/ingest_structured_tlds1.json
    :lines: 6-9

It specifies the file encoding (``utf-8``) and the format of the file (``lines``). There are a few file formats
which Synapse will natively parse; they are noted below.  The formats are extensible at runtime as well, so an API user
could register their own formats. By default, the lines starting with ``#`` are ignored as comment lines.

The ingest directive is below and tells us how to process each line within the file:

.. literalinclude:: ../examples/ingest_structured_tlds1.json
    :lines: 10-23

This definition includes a "forms" directive.  This instructs ingest on which types of nodes to make as it processes
the lines of data. In this flat file example, each line of text is a single item. Without any other directive, that
line of text is used as the primary property for creating the ``inet:fqdn`` node. The "props" dictionary specifies
additional properties which will be added to the node; here we are setting the ``sfx`` property to equal ``1``.

This ingest can be run via the ingest tool::

    python -m synapse.tools.ingest --core sqlite:///ingest_examples.db docs/synapse/examples/ingest_structured_tlds1.json

After ingesting this, we can see the ``inet:fqdn`` nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///ingest_examples.db
    cli> ask --props inet:fqdn=ninja
    inet:fqdn = ninja
        :host = ninja
        :sfx = True
        :zone = False
        tufo:form = inet:fqdn
        node:ndef = ee23cd14ec6039abfd656d182c023a82
        node:created = 2018/01/05 15:06:49.792
    (1 results)

