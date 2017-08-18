Ingest Subsystem
================

Introduction to Ingest
----------------------

The Synapse Ingest subsystem was designed in order to assist users load data into the Synapse hypergraph (Cortex). The
design principals around the ingest system were that users should be able to load data into a Cortex without needing
to write code in order to do so. The Ingest system can also be used to parse data from structured data sources; for
example, it can be used to parse data from web APIs and store the results in Cortex. Since Ingest is designed to be
non-programmer friendly, Ingest definitions are typically written in JSON.

Writing an Ingest definition, either for a static set of data or for parsing data several times over, does require
familiarity with the Synapse model. Documentation on the built in models can be found at `Data Model`_.
Additional modeling documentation can be found at the `Synapse User Guide`_.

Follow Along
************

The examples shown here can also be executed directly, so readers may follow along if they have a copy of the Synapse
git repository checked out. These examples show running the ingest tool and querying a Cortex to see the results of
running the examples.


Ingest Tool
-----------

While the Ingest subsystem in Synapse lives at synapse.lib.ingest, most users may use the standalone ingest tool
directly.  This can be invoked with the following command: ``python -m synapse.tools.ingest <options> <ingest files>``.
If invoked with the --help flag, the following options are listed::

    ~/synapse$ python -m synapse.tools.ingest --help
    usage: ingest [-h] [--core CORE] [--progress] [--sync SYNC] [--save SAVE]
                  [--debug] [--verbose]
                  [files [files ...]]

    Command line tool for ingesting data into a cortex

    positional arguments:
      files        JSON ingest definition files

    optional arguments:
      -h, --help   show this help message and exit
      --core CORE  Cortex to use for ingest deconfliction
      --progress   Print loading progress
      --sync SYNC  Sync to an additional cortex
      --save SAVE  Save cortex sync events to a file
      --debug      Drop to interactive prompt to inspect cortex
      --verbose    Show changes to local cortex incrementally

These options control what we are ingesting, where it is going too, and various logging details.

``--core``

    This specifies which Cortex to connect to and add the ingest data too. By default, this is a ram cortex
    (``ram://``), but could be any supported Cortex url or a Telepath url to a Cortex.

``--progress``

    Display the progress of the ingest process every second.  This expects no arguments.

``--sync``

    This can be used to sync events from the Cortex specified in the ``--core`` option with a remote Cortex via a
    splice pump. See the <syncing data> section below for more details.

``--save``

    This creates a savefile for changes made to the Cortex specified in the ``--core`` option. This can be used to
    replay events to another Cortex.

``--debug``

    This drops the user into a cmdr session for the Cortex specified in the ``--core`` option after the ingest
    processing is complete.  It accepts no arguments.

``--verbose``

    This prints the nodes added to the Cortex specified in the ``--core`` option as the nodes are created in the Cortex.
    It accpts no arguments.

Embed Directives
----------------

The simplest example is ingesting static data which is located in the ingest file itself. This is done via an
"embed" directive. It allows us to embed nodes directly into a ingest file. We can also include secondary properties
in the files as well.

Here is a brief example showing an ingest containing two inet:fqdn nodes:

.. literalinclude:: examples/ingest_embed1.json
    :language: json

The items in the "nodes" key is a list of two-value pairs.  The first item in the form we are creating. The second
item is a list of objects of that will be used to make the nodes.  In this case, simple have two ``inet:fqdn``'s listed.
If we ingest this file, if would be the equivalent of either adding nodes via storm
(`ask [inet:fqdn=vertex.link inet:fqdn=woot.com]` or if we had used the Cortex formTufoByProp() API.

We can use the ingest tool (located at synapse.tools.ingest) to ingest this into a Cortex::

    ~/synapse$ python -m synapse.tools.ingest --core sqlite:///ingest_examples.db --verbose docs/synapse/devopsguides/examples/ingest_embed1.json
    add: inet:fqdn=com
          :host = com
          :sfx = 1
          :zone = 0
    add: inet:fqdn=woot.com
          :domain = com
          :host = woot
          :sfx = 0
          :zone = 1
    add: inet:fqdn=link
          :host = link
          :sfx = 1
          :zone = 0
    add: inet:fqdn=vertex.link
          :domain = link
          :host = vertex
          :sfx = 0
          :zone = 1
    ingest took: 0.031163692474365234 sec

Then we can open up the Cortex and see that we have made those nodes::

    ~/synapse$ python -m synapse.Cortex sqlite:///ingest_examples.db
    cli> ask --props inet:fqdn=vertex.link
    inet:fqdn = vertex.link
       :domain = link
       :host = vertex
       :sfx = False
       :zone = True
    (1 results)

Expanding on the previous example, we can add additional types in the embed directive - we are not limited to just a
single node type.  Here is an example showing the addition of two ``inet:netuser`` nodes - one with a single primary
property, and one with multiple secondary properties:

.. literalinclude:: examples/ingest_embed2.json
    :language: json

This adds the two inet:netuser nodes to our Cortex.  We can run that with the following command to add the nodes to
our example core::

    ~/synapse$ python -m synapse.tools.ingest --core sqlite:///ingest_examples.db --verbose docs/synapse/devopsguides/examples/ingest_embed2.json
    add: inet:netuser=github.com/bobtheuser
          :email = bobtheuser@gmail.com
          :seen:max = 1514764800000
          :seen:min = 1388534400000
          :site = github.com
          :user = bobtheuser
    add: inet:user=bobtheuser
    add: inet:fqdn=github.com
          :domain = com
          :host = github
          :sfx = 0
          :zone = 1
    add: inet:email=bobtheuser@gmail.com
          :fqdn = gmail.com
          :user = bobtheuser
    add: inet:fqdn=gmail.com
          :domain = com
          :host = gmail
          :sfx = 0
          :zone = 1
    add: inet:netuser=google.com/bobtheuser
          :site = google.com
          :user = bobtheuser
    add: inet:fqdn=google.com
          :domain = com
          :host = google
          :sfx = 0
          :zone = 1
    ingest took: 0.021549463272094727 sec

Since we are using verbose mode we can see the ``inet:netuser`` nodes were created; while the already existing
`inet:fqdn`` nodes were not. The default behavior for creating new nodes is to also create nodes for secondary
properties if they are also a node type.  In the example above we also saw the creation of the ``inet:email``,
``inet:netuser`` and other nodes which were not explicitly defined in the ingest definition. We can also confirm those
via the cmdr interface as well::

    ~/synapse$ python -m synapse.Cortex sqlite:///ingest_examples.db
    cli> ask inet:netuser
    inet:netuser = github.com/bobtheuser
    inet:netuser = google.com/bobtheuser
    (2 results)
    cli> ask --props inet:user refs()
    inet:user    = bobtheuser
    inet:email   = bobtheuser@gmail.com
       :fqdn = gmail.com
       :user = bobtheuser
    inet:netuser = github.com/bobtheuser
       :email = bobtheuser@gmail.com
       :seen:max = 2018/01/01 00:00:00.000
       :seen:min = 2014/01/01 00:00:00.000
       :site = github.com
       :user = bobtheuser
    inet:netuser = google.com/bobtheuser
       :site = google.com
       :user = bobtheuser
    (4 results)

In addition to adding properties, we can also add tags <link to tag userguide> to the ingest files. An example below
shows adding some tags to the nodes in the embed directive. These tags can apply to either then entire set of
nodes in the embed directive (``#story.bob``) or specific to those of a single node (the one ``#src.commercial`` tag).

.. literalinclude:: examples/ingest_embed3.json
    :language: json

We can then apply this ingest with the following command (output omitted - it is rather long)::

    ~/synapse$ python -m synapse.tools.ingest --core sqlite:///ingest_examples.db --verbose docs/synapse/devopsguides/examples/ingest_embed3.json

Back in cmdr we can lift the nodes via the tags we just added::

    ~/synapse$ python -m synapse.Cortex sqlite:///ingest_examples.db
    cli> ask #src.osint
    inet:netuser = github.com/bobtheuser
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.accounts (added 2017/08/16 02:16:35.409)
    inet:netuser = google.com/bobtheuser
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.accounts (added 2017/08/16 02:16:35.409)
    inet:fqdn    = woot.com
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.infrastructure (added 2017/08/16 02:16:35.409)
    (3 results)
    cli> ask #src.commercial
    inet:fqdn = vertex.link
       #src.commercial (added 2017/08/16 02:16:35.409)
       #story.bob.infrastructure (added 2017/08/16 02:16:35.409)
    (1 results)
    cli> ask #story.bob
    inet:netuser = github.com/bobtheuser
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.accounts (added 2017/08/16 02:16:35.409)
    inet:netuser = google.com/bobtheuser
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.accounts (added 2017/08/16 02:16:35.409)
    inet:fqdn    = vertex.link
       #src.commercial (added 2017/08/16 02:16:35.409)
       #story.bob.infrastructure (added 2017/08/16 02:16:35.409)
    inet:fqdn    = woot.com
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.infrastructure (added 2017/08/16 02:16:35.409)
    (4 results)
    cli> ask #story.bob.accounts
    inet:netuser = github.com/bobtheuser
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.accounts (added 2017/08/16 02:16:35.409)
    inet:netuser = google.com/bobtheuser
       #src.osint (added 2017/08/16 02:16:35.409)
       #story.bob.accounts (added 2017/08/16 02:16:35.409)
    (2 results)
    cli>

A complete example of this example embed ingest is shown below.  While the previous three ingests demonstrated
different parts of the ingest system, this is close to how the ingest file would look for longer term storage or for
doing a one-time load of data into a Cortex.

.. literalinclude:: examples/ingest_embed4.json
    :language: json

This can at the file path ``docs/synapse/devopsguides/examples/ingest_embed4.json`` and ingested like the
previous examples were.  However, since there is nothing new to add here, there will be no new nodes created as a
result of ingesting it into ``sqlite:///ingest_examples.db``.

Parsing a Structured File - Lines
---------------------------------

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

.. literalinclude:: examples/ingest_structured_tlds1.json
    :language: json

The structure of this ingest file difers from the previous example showing the "embed" directive.  This uses the
"sources" directive. This direct specifies a source file and a dictionary continaing a "open" and "ingest" directive.
The open direct is below and tells us how to open the file and how it is shaped:

.. literalinclude:: examples/ingest_structured_tlds1.json
    :lines: 6-9

It specifies the file "encoding" (``utf-8``) and the "format" of the file (``lines``).  There are a few file formats
which Synapse will natively parse; they are noted below.  The formats are extensible at runtime as well, so an API user
could register their own formats as well.  By default, the lines starting with ``#`` are ignored, as comment lines.

The ingest directive is below and tells us how to process each line within the file:

.. literalinclude:: examples/ingest_structured_tlds1.json
    :lines: 10-23

This definition includes a "forms" directive.  This instructs ingest on which types of nodes to make as it processes
the lines of data. In this flat file example, each line of text is a single item. Without any other directive, that
line of text is used as the primary property for creating the ``inet:fqdn`` node. The "props" dictionary specifies
additional properties which will be added to the node as well; here we are setting the ``sfx`` property to equal ``1``.

This ingest can be run via the ingest tool::

    python -m synapse.tools.ingest --core sqlite:///embed_examples.db docs/synapse/devopsguides/examples/ingest_structured_tlds1.json

After ingesting this, we can see the ``inet:fqdn`` nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    cli> ask --props inet:fqdn=ninja
    inet:fqdn = ninja
        :host = ninja
        :sfx = True
        :zone = False
    (1 results)


Parsing a Structured File - CSV
-------------------------------

Now that we've seen how to do an ingest of a simple file containing some lines of text, we can move onto more
complicated structures.  Comma Separated Value (CSV) support is provided via the built-in `csv`_ module.  If we look
at the file below we can see a few FQDN and IP address pairs:

.. literalinclude:: examples/ingest_structured_dnsa1.csv

When the CSV helper parses this file, it will return each line as though we were iterating over a csv.reader object.
For the sake of demonstration we'll ingest these in as as ``inet:dns:a`` records. We'll use the following ingest for
doing that:

.. literalinclude:: examples/ingest_structured_dnsa1.json
    :language: json

This ingest adds in a "vars" section, which denotes variables which are extracted out of the data as we iterate over
the CSV file. The CSV data is just a list of values, and we denote which element of the list to associate with which
variable. That is done with the "path" directive - it can be used to extract specific items out of the data we are
iterating over.  Since we do not have a single string we can use as the primary property to make a node, we've added the
"template" directive to the "forms" section.  This allows us to construct the primary property using a string template.
The vars we extracted are substituted into the ``{{domain}}`` and ``{{ipv4}}`` fields using ``str.replace``, after
calling ``str()`` on the vars.

This ingest can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/devopsguides/examples/ingest_structured_dnsa1.json

After ingesting this, we can see the ``inet:dns:a`` nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    /cli> ask --props inet:dns:a limit(1)
    inet:dns:a = vertex.link/127.0.0.1
        :fqdn = vertex.link
        :ipv4 = 127.0.0.1
    (1 results)

Parsing a Structured File - XML
-------------------------------

Todo

Parsing a Structured File - JSON
--------------------------------

JSON is a very commonly encountered data format, since it is so portable and easy to use. JSON support is provided via
the built-in `json`_ module. For this, we'll look at a more complicated example - a blob of information about a social
media account for a user at the made up site, ``socialnetwork.ninja``.

The data we want to ingest can be seen below:

.. literalinclude:: examples/ingest_structured_nested_data.json
    :language: json

There are several nodes we can create here from this data.  First, the site and user can be made into a ``inet:netuser``
form, and we can set some time-based properties there. We have some friendship which are noted, which we'll consider as
bidirectional relationships, which we can use the ``inet:follows`` node type to represent. Similarly, the user has some
organizations they are a part of on the site which can be treated as ``inet:netmemb`` nodes. Lastly, there is some post
information from the user which we can use to make ``inet:netpost`` nodes from.  We'll look at each of these
separately, then together as a single document.

.. literalinclude:: examples/ingest_structured_nested_def.json
    :lines: 11-52

The above definition shows the extraction of a few vars from the json object, using their names as the path. This sets
the variables ``domain``, ``user``, ``account_created`` and ``last_login``.  Those are used to create the
``inet:netuser`` node for the user.

The following sections require the "iter" directive, which is used to iterate over a set of data which is structured
in a object.  This allows us to handle nested data structures in a clean fashion. There is one important concept to
consdier when dealing with "iter" directives - variable scope.  When a iter is encounted, the Ingest process enters
into a new scope and the variables set in the parent section are available to the child scopes.  When a iter is
exhausted, it leaves the scope and the variables it set are no longer available.

A simple iter, going over the user's organizations, can be seen below:

.. literalinclude:: examples/ingest_structured_nested_def.json
    :lines: 53-74

Since we are iterating over the list of strings, if we want to set that string as a variable we can do so with the path
set to the value ``0`` (not ``"0"`` as in the CSV example). Since we're in a child scope, we still have access the
parent "vars", so we can use those when making the ``inet:netmemb`` nodes.  This is seen in the template string::

    "template": "({{domain}}/{{user}},{{domain}}/{{org}})"

This makes the string form of the ``inet:netmemb`` comp type using the ``org`` var extracted during the current iter,
and the ``domain`` and ``user`` vars from the parent.

Likewise, the ``domain`` and ``user`` are reused again in the iter which is used to make the ``inet:follows`` nodes.

.. literalinclude:: examples/ingest_structured_nested_def.json
    :lines: 75-101

In the above example, we're making two ``inet:follows`` nodes for each friend, under the assumption that the friend
relationship of ``socialnetwork.ninja`` is bi-directional. This is important since the ``inet:follows`` node itself
is a one-way relationship (think of a Twitter follow), not a a two-way relationship.

Next, we need to iterate over the dictionary objects containing the users posts.  That is seen below:

.. literalinclude:: examples/ingest_structured_nested_def.json
    :lines: 102-133

The big difference in this section is that, unlike the previous two, is that we are accessing variables like in the
parent scope (using key names). We then create the ``inet:netpost`` in a similar manner to other sections, in order to
make those nodes.

Putting this all together gives us the following ingest document:

.. literalinclude:: examples/ingest_structured_nested_def.json
    :language: json

This ingest can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/devopsguides/examples/ingest_structured_nested_def.json

After ingesting this, we can see the various nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    cli> ask inet:netuser:site=socialnetwork.ninja
    inet:netuser = socialnetwork.ninja/alicethefriend
    inet:netuser = socialnetwork.ninja/bobtheuser
    inet:netuser = socialnetwork.ninja/mallorythespy
    (3 results)
    cli> ask --props inet:netuser=socialnetwork.ninja/bobtheuser inet:netuser->inet:follows:follower show:cols(inet:follows:follower, inet:follows:followee)
    socialnetwork.ninja/bobtheuser  socialnetwork.ninja/mallorythespy
    socialnetwork.ninja/bobtheuser socialnetwork.ninja/alicethefriend
    (2 results)
    cli> ask --props inet:netuser=socialnetwork.ninja/bobtheuser inet:netuser->inet:netpost:netuser
    inet:netpost = 0e89cf5db1fd8c426daa8b01e58cd2dd
        :netuser = socialnetwork.ninja/bobtheuser
        :netuser:site = socialnetwork.ninja
        :netuser:user = bobtheuser
        :text = hallo!
        :time = 2017/05/02 01:06:03.000
    inet:netpost = 16a550ca28e7e62e0b47b482cc02b58e
        :netuser = socialnetwork.ninja/bobtheuser
        :netuser:site = socialnetwork.ninja
        :netuser:user = bobtheuser
        :text = Just got back from the concert
     had a great time
        :time = 2017/08/17 01:02:03.000
    inet:netpost = e6b5d03f398a02548d9201efbdc58a06
        :netuser = socialnetwork.ninja/bobtheuser
        :netuser:site = socialnetwork.ninja
        :netuser:user = bobtheuser
        :text = Just did hax with nine bit bytes @ defcon
        :time = 2017/08/01 02:03:04.000
    (3 results)

When ingesting data like this format, its not uncommon to also apply tags to a ingest definition. This can be useful
for adding additional analytical data or categorization to the nodes as they are created in the Cortex. This can be done
by adding a "tags" directive in line with other ingest directives.  An example of modifying the above ingest to add a
``#src.socialnetwork`` tag can be seen highlighted below:

.. literalinclude:: examples/ingest_structured_nested_def2.json
    :language: json
    :emphasize-lines: 11-13

This will add the ``#src.socialnetwork`` tag to all of the nodes created directly by the ingest process. This ingest
can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/devopsguides/examples/ingest_structured_nested_def2.json

Then we can lift nodes from this ingest via tags. The following example shows lifting all of the ``inet:netuser`` nodes
made with this ingest::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    cli> ask inet:netuser*tag=src.socialnetwork
    inet:netuser = socialnetwork.ninja/bobtheuser
        #src.socialnetwork (added 2017/08/17 23:53:30.024)
    (1 results)

This result may seem odd - in the previous query ``ask inet:netuser:site=socialnetwork.ninja`` we had three
``inet:netuser`` accounts found; but ``ask inet:netuser*tag=src.socialnetwork`` only gave us one account. This is
because we only created one ``inet:netuser`` account directly in the ingest definition, the other accounts were created
as a result of creating the ``inet:netfollows`` nodes. If we wanted to be thorough, we could also create the
``inet:netuser`` accounts as well. See the highlighted section of the updated ingest below:

.. literalinclude:: examples/ingest_structured_nested_def3.json
    :language: json
    :emphasize-lines: 82-87

This updated ingest will make the ``inet:netuser`` nodes for the friends and tag them prior to making the
``inet:netfollows`` nodes.  It can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/devopsguides/examples/ingest_structured_nested_def3.json

Repeating our earlier Storm query gives us all three ``inet:netuser`` nodes::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
    cli> ask inet:netuser*tag=src.socialnetwork
    inet:netuser = socialnetwork.ninja/alicethefriend
        #src.socialnetwork (added 2017/08/17 23:59:57.797)
    inet:netuser = socialnetwork.ninja/bobtheuser
        #src.socialnetwork (added 2017/08/17 23:53:30.024)
    inet:netuser = socialnetwork.ninja/mallorythespy
        #src.socialnetwork (added 2017/08/17 23:59:57.797)
    (3 results)



Parsing a Structured File - JSONL
---------------------------------

The "jsonl" format is a combination of the lines and JSON formats. It assumes the data it is processing is a multi-line
document, and each line of the document is a single json blob which needs to be deserialized and ingested. A simple
jsonl file is shown below:

.. literalinclude:: examples/ingest_structured_dnsa2.jsonl

This is similar to the earlier CSV data; except each line may have multiple objects we want to consume, and we've got
to treat the data as a list of JSON dictionaries. This will require directly iterating on the data we are consuming
and creating the nodes from that. A wilcard ``*`` can be used to indicate to iterate directly over the object being
processed. This ingest can be seen below:

.. literalinclude:: examples/ingest_structured_dnsa2.json
    :language: json
    :emphasize-lines: 13

It can be run via the ingest tool::

    python -m synapse.tools.ingest --verbose  --core sqlite:///embed_examples.db  docs/synapse/devopsguides/examples/ingest_structured_dnsa2.json

After ingesting this, we can see the various nodes have been added to our Cortex::

    ~/synapse$ python -m synapse.cortex sqlite:///embed_examples.db
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


Source File Path Location
-------------------------

In all of these examples, the ingest files themselves have been located in the ``docs/synapse/devopsguides/examples/``
directory of the Synapse git repository.  They specify source files by name - such as ``ingest_structured_dnsa2.jsonl``.
The Ingest subsystem uses a helper (``loadfile``) which sets a "basedir" value where the ingest definition file
resides. This basedir is where the full file path for source files made with, using ``os.path.join()``.

Builtin Ingest Format Helpers
-----------------------------

The following format options are built into the Ingest system by default. These common formats allow for users to
quickly get started with Ingest in order to start parsing content into a Cortex.

csv
***

Todo

xml
***

Todo

json
****

Todo

jsonl
*****

Todo

lines
*****

Todo

Ingest & ``file:bytes`` Nodes
-----------------------------

Todo

Conditional Expressions
-----------------------

Todo

Syncing Data to a Remote Cortex
-------------------------------

It is easy to send data processed by an Ingest to a remote Cortex.  This is done using the ``--sync`` option when
invoking the ingest tool.  An example can be seen below::

    python -m synapse.lib.ingest --sync tcp://some.place.com/core /path/too/ingestdef.json

The above invocation doesn't specify a Cortex with the ``--core`` option - instead it runs the ingest into a ``ram://``
backed Cortex by default. This can be useful so that the local ram Cortex can quickly deduplicate data from the ingest,
and the resulting events will be sent up to the remote Cortex as splice events.  The remote Cortex will then apply any
changes it needs in order to add anything new (nodes, props, tags, etc) from the ingest processing.

Ingesting Data from the Web
---------------------------

Todo

Registering Format Helpers
--------------------------

Todo

Ingest Under the Hood
---------------------

Todo

.. _`Synapse User Guide`: ../userguide_section0.html
.. _`Data Model`: ../datamodel.html
.. _`csv`: https://docs.python.org/3/library/csv.html
.. _`json`: https://docs.python.org/3/library/json.html