.. highlight:: none

.. _syn-tools-csvtool:

csvtool
=======

The Synapse ``csvtool`` command can be used to ingest structured data from a comma-separated values (CSV) file to create nodes in a Cortex. ``csvtool`` is useful for bulk-loading CSV-formatted data without the need to develop custom ingest code. (For other data formats such as JSON, yaml, or msgpack, see :ref:`syn-tools-feed`.)

The ``--export`` option can be used to export a set of data from a Cortex into a CSV file.

Storm queries are used both to ingest and export data using ``csvtool``. Users should be familiar with the Storm query language (:ref:`storm-ref-intro` et al.) and the Synapse data model (:ref:`data-model-terms` et al.) in order to use ``csvtool`` effectively.

The Storm syntax used with ``csvtool`` makes use of a few more advanced Storm concepts such as variables, methods, libraries, and some programming flow control concepts (e.g., for loops and switch statements). However, the examples below should be fairly self-explanatory. In other words, users do **not** need to understand in detail how those concepts work in order to create basic ``stormfile`` queries and start loading data using ``csvtool``.

That said, the set of advanced Storm concepts and features can be fully leveraged within a ``stormfile`` to perform complex data ingest. Interested users are encouraged to refer to the appropriate sections of the Storm reference documents for a more detailed discussion of those concepts, which may be useful for creating more complex ``stormfile`` queries (or Storm queries in general).

- :ref:`storm-ref-subquery`
- :ref:`storm-adv-vars`
- :ref:`storm-adv-methods`
- :ref:`storm-adv-control`
- :ref:`stormtypes-libs-header`
- :ref:`stormtypes-prim-header`


Syntax
------

``csvtool`` is executed from an operating system command shell. The command usage is as follows (line is wrapped for readability):

::
  
  usage: synapse.tools.csvtool [-h] [--logfile LOGFILE] [--csv-header] [--cli] [--debug] 
    (--cortex CORTEX | --test) [--export] [--view VIEW] [--optsfile OPTSFILE]
    stormfile csvfiles [csvfiles ...]

Where:

- ``-h`` displays detailed help and examples.
- ``LOGFILE`` is the optional name / path to log Storm events associated with running the ``csvtool`` command as a JSONL file.  Messages are appended to this file when they are written to them.
- ``--csv-header`` is an option that indicates the first row in the CSV file is a header row and should be skipped for purposes of parsing and node creation.
- ``--cli`` opens a ``storm`` command prompt after ``csvtool`` exits.

  - The command prompt will be connected to the Cortex specified by the ``--cortex CORTEX`` or ``--test`` option.

- ``--debug`` will send verbose output to ``stdout`` during execution.
- ``CORTEX`` specifies the telepath URL to the Cortex where the data should be ingested.

- ``--test`` specifies the data should be loaded into a temporary local Cortex (i.e., for testing / validation).

  - When using a temporary Cortex, you do not need to provide a path.

- ``--export`` is used to extract data from the specified Cortex into a CSV file.
- ``--view`` is used to optionally specify the iden of a view to use on the Cortex.
- ``--optsfile`` is used specify additional Storm runtime query options.
- ``stormfile`` is the name / path to a file containing a Storm query that tells Synapse how to ingest the CSV data (or how to lift and export data if the ``--export`` option is used).
- ``csvfiles`` is the name / path to one or more CSV files containing the data to be ingested (or the name/path where the CSV output should be written if the ``--export`` option is used).

  - If multiple ``csvfiles`` are listed for ingest, they are all processed with the specified ``stormfile``.
  - Only a single ``csvfile`` can be specified for output with ``--export``.

.. NOTE::
  The same events are output by both ``--logfile`` and ``--debug``; one is written to file and the other is written to ``stdout``.

help
++++

The detailed help (``-h``) output for ``csvtool`` is shown below (lines are wrapped for readability).

::
  
  python -m synapse.tools.csvtool -h
  
  usage: synapse.tools.csvtool [-h] [--logfile LOGFILE] [--csv-header] [--cli] [--debug]
    (--cortex CORTEX | --test) [--export] stormfile csvfiles [csvfiles ...]
  
  Command line tool for ingesting csv files into a cortex
  
  The storm file is run with the CSV rows specified in the variable "rows" so most storm files
    will use a variable based for loop to create edit nodes.  For example:
  
  for ($fqdn, $ipv4, $tag) in $rows {
      [ inet:dns:a=($fqdn, $ipv4) +#$tag ]
  }
  
  More advanced uses may include switch cases to provide different logic based on a
    column value.
  
  for ($type, $valu, $info) in $rows {
      
      switch $type {
          fqdn: {
              [ inet:fqdn=$valu ]
          }
          
          "person name": {
              [ ps:name=$valu ]
          }
          
          *: {
              // default case...
          }
      }
      
      switch $info {
          "known malware": { [+#cno.mal] }
      }
  }
  
  positional arguments:
  
  stormfile             A STORM script describing how to create nodes
                        from rows.
  csvfiles              CSV files to load.
  
  optional arguments:
  -h, --help            show this help message and exit
  --logfile LOGFILE     Set a log file to get JSON lines from the
                        server events.
  --csv-header          Skip the first line from each CSV file.
  --cli                 Drop into a cli session after loading data.
  --debug               Enable verbose debug output.
  --cortex CORTEX, -c CORTEX
                        The telepath URL for the cortex ( or alias
                        from ~/.syn/aliases ).
  --test, -t            Perform a local CSV ingest against a temporary
                        cortex.
  --export              Export CSV data to file from storm using
                        $lib.csv.emit(...) events.

.. _csvtool-examples-ingest:
  
Ingest Examples - Overview
--------------------------

The key components for using the ``csvtool`` command are the CSV file itself (``csvfile``) and the file containing the Storm query (``stormfile``) used to ingest the data.

The ``stormfile`` contains a Storm query to describe how the data from the CSV file(s) should be used to create nodes in a Cortex, including optionally setting properties and / or adding tags.

.. NOTE::
  When ingesting large sets of CSV-formatted data where the data has not been vetted, it may be useful to use the :ref:`edit-try` operator instead of the equivalent ( ``=`` ) operator within the Storm syntax in the ``stormfile`` used to create nodes. When using the try operator ( ``?=`` ), Storm will process what it can, creating nodes from "well-formatted" data and simply skipping rows that may contain bad data.
  In contrast, using the equivalent operator ( ``=`` ) will result in Storm throwing an error and halting processing if bad data is encountered.

.. _ingest-1:

Ingest Example 1
++++++++++++++++

This example demonstrates loading a structured set of data to create nodes of a single form (in this case, DNS A records) and set secondary properties (in this case, the ``.seen`` universal property).

**CSV File:**

A CSV file (``testfile.csv``) contains a list of domains, the IP addresses the domains have resolved to, and the first and last observed times for the resolution, as represented by the example header and row data below:

::
  
  domain,IP,first,last
  woot.com,1.2.3.4,2018/04/18 13:12:47,2018/06/23 09:45:12
  hurr.net,5.6.7.8,2018/10/03 00:47:29,2018/10/04 18:26:06
  derp.org,4.4.4.4,2019/06/09 09:00:18,2019/07/03 15:07:52

.. NOTE::
  Because the file contains a header row, we need to use the ``--csv-header`` option to tell ``csvtool`` to skip the first row when ingesting data.

We want to load the data in the CSV file into a Cortex as a set of DNS A records (``inet:dns:a`` nodes) with the first and last dates represented as the ``.seen`` universal property.

**Stormfile:**

Storm references the set of rows in the CSV file by the :ref:`vars-ingest-rows` built-in variable. We need to define a set of variables (see :ref:`storm-adv-vars`) to represent each field in a row (i.e., each column in the CSV file) and tell Storm to iterate over each row using a :ref:`flow-for`. For example:

::
  
  for ($fqdn, $ipv4, $first, $last) in $rows

This assigns the variable ``$fqdn`` to the first column (i.e., the one containing ``woot.com``), ``$ipv4`` to the second column, and so on, and sets up the "for" loop.

We then need a Storm query that tells the "for" loop what to do with each row - that is, how to create the DNS A records from each row in the CSV file:

::
  
  [ inet:dns:a = ( $fqdn, $ipv4 ) .seen=( $first, $last ) ]

We combine these elements to create our ``stormfile``, as follows:

::
  
  for ($fqdn, $ipv4, $first, $last) in $rows {
  
      [ inet:dns:a = ( $fqdn, $ipv4 ) .seen=( $first, $last ) ]
  
  }

**Testing the Ingest:**

Typically, users will want to test that their ``stormfile`` loads and formats the data correctly by first ingesting the data into a local test cortex (``--test``) before loading the data into a production Cortex. This is typically done using either the ``--debug`` or ``--logfile`` option to check for errors and reviewing the loaded data (via ``--cli``).

Testing the data will highlight common errors such as:

- Invalid Storm syntax in the ``stormfile``.
- Data in the CSV file that does not pass :ref:`data-type` validation on node creation (i.e., bad or incorrect data, such as an IP address in an FQDN column).

We can attempt to load our data into a test Cortex using the following command (line is wrapped for readability):

::
  
  python -m synapse.tools.csvtool --logfile mylog.json --csv-header --cli --test
    stormfile testfile.csv

Assuming the command executed with no errors, we should have a ``storm`` CLI prompt for our local test Cortex:

::
  
  cli>

We can now issue Storm commands to interact with and validate the data (i.e., did ``csvtool`` create the expected number of nodes, were the properties set correctly, etc.)

For example:

::
  
  cli> storm inet:dns:a
  
  inet:dns:a=('hurr.net', '5.6.7.8')
      .created = 2019/07/03 22:25:43.966
      .seen = ('2018/10/03 00:47:29.000', '2018/10/04 18:26:06.000')
      :fqdn = hurr.net
      :ip = 5.6.7.8
  inet:dns:a=('derp.org', '4.4.4.4')
      .created = 2019/07/03 22:25:43.968
      .seen = ('2019/06/09 09:00:18.000', '2019/07/03 15:07:52.000')
      :fqdn = derp.org
      :ip = 4.4.4.4
  inet:dns:a=('woot.com', '1.2.3.4')
      .created = 2019/07/03 22:25:43.962
      .seen = ('2018/04/18 13:12:47.000', '2018/06/23 09:45:12.000')
      :fqdn = woot.com
      :ip = 1.2.3.4
  complete. 3 nodes in 12 ms (250/sec).

**Loading the Data:**

Once we have validated that our data has loaded correctly, we can modify our ``csvtool`` command to load the data into a live Cortex (replace the Cortex path below with the path to your Cortex; line is wrapped for readability):

::
  
  python -m synapse.tools.csvtool --logfile mylog.json --csv-header
    --cortex aha://cortex... stormfile testfile.csv

.. _ingest-2:

Ingest Example 2
++++++++++++++++

This example demonstrates loading a more complex set of data to create nodes of multiple types, apply a single tag to all nodes, and apply custom tags to only some nodes based on additional criteria.

**CSV File:**

A CSV file (``testfile.csv``) contains a set of malicious indicators, listed by type and the indicator value, as represented by the example header and row data below:

::
  
  Indicator type,Indicator,Description
  URL,http://search.webstie.net/,
  FileHash-SHA256,b214c7a127cb669a523791806353da5c5c04832f123a0a6df118642eee1632a3,
  FileHash-SHA256,b20327c03703ebad191c0ba025a3f26494ff12c5908749e33e71589ae1e1f6b3,
  FileHash-SHA256,7fd526e1a190c10c060bac21de17d2c90eb2985633c9ab74020a2b78acd8a4c8,
  FileHash-SHA256,b4e3b2a1f1e343d14af8d812d4a29440940b99aaf145b5699dfe277b5bfb8405,
  hostname,dns.domain-resolve.org,
  hostname,search.webstie.net,

Note that while the CSV file contains a header field titled “Description”, that field in this particular file contains no data.

Let’s say that in addition to the raw indicators, we know that the indicators came from a blog post describing the activity of the Vicious Wombat threat group, and that the SHA256 hashes are samples of the UMPTYSCRUNCH malware family. To provide additional context for the data in our Cortex, we want to:

- Tag all of the indicators as associated with Vicious Wombat (``#cno.threat.viciouswombat``).
- Tag all of the SHA256 hashes as associated with UMPTYSCRUNCH malware (``#cno.mal.umptyscrunch``).

**Stormfile:**

Similar to our first example, we need to define a set of variables to represent each column (field) for each row and set up the "for" loop:

::
  
  for ($type, $value, $desc) in $rows

In this case, the rows contain different types of data that will be used to create different nodes (forms). The ``Indicator type`` column (``$type``) tells us what type of data is available and what type of node we should create. We can use a "switch" statement to tell Storm how to handle each type of data (i.e., each value in the ``$type`` field). Since we know the SHA256 hashes refer to UMPTYSCRUNCH malware samples, we want to add tags to those nodes:

::
  
  switch $type {
      
      URL: {
          [ inet:url = $value ]
      }
      
      FileHash-SHA256: {
          [ hash:sha256 = $value +#cno.mal.umptyscrunch ]
      }
      
      hostname: {
          [ inet:fqdn = $value ]
      }
  }

Finally, because we know all of the indicators are associated with the Vicious Wombat threat group, we want to add a tag to all of the indicators. We can add that after the "switch" statement:

::
  
  [ +#cno.threat.viciouswombat ]


So our full ``stormfile`` script looks like this:

::
  
  for ($type, $value, $desc) in $rows {
  
      switch $type {
      
          URL: {
              [ inet:url = $value ]
          }
          
          FileHash-SHA256: {
              [ hash:sha256 = $value +#cno.mal.umptyscrunch ]
          }
          
          hostname: {
              [ inet:fqdn = $value ]
          }
      }
      
      [ +#cno.threat.viciouswombat ]
  }

**Testing the Ingest:**

We can now test our ingest by loading the data into a test Cortex (line is wrapped for readability):

::
  
  python -m synapse.tools.csvtool --logfile mylog.json --csv-header --cli --test
    stormfile testfile.csv

From the ``storm`` CLI, we can now query the data to make sure the nodes were created and the tags applied correctly. For example:

Check that two ``inet:fqdn`` nodes were created and given the ``#cno.threat.viciouswombat`` tag:

::
  
  cli> storm inet:fqdn#cno
  
  inet:fqdn=search.webstie.net
      .created = 2019/07/05 14:49:20.110
      :domain = webstie.net
      :host = search
      :issuffix = False
      :iszone = False
      :zone = webstie.net
      #cno.threat.viciouswombat
  inet:fqdn=dns.domain-resolve.org
      .created = 2019/07/05 14:49:20.117
      :domain = domain-resolve.org
      :host = dns
      :issuffix = False
      :iszone = False
      :zone = domain-resolve.org
      #cno.threat.viciouswombat
  complete. 2 nodes in 14 ms (142/sec).

Check that four ``hash:sha256`` nodes were created and given both the Vicious Wombat and the UMPTYSCRUNCH tags:

::
  
  cli> storm hash:sha256
  
  hash:sha256=7fd526e1a190c10c060bac21de17d2c90eb2985633c9ab74020a2b78acd8a4c8
      .created = 2019/07/05 14:49:20.115
      #cno.mal.umptyscrunch
      #cno.threat.viciouswombat
  hash:sha256=b20327c03703ebad191c0ba025a3f26494ff12c5908749e33e71589ae1e1f6b3
      .created = 2019/07/05 14:49:20.115
      #cno.mal.umptyscrunch
      #cno.threat.viciouswombat
  hash:sha256=b214c7a127cb669a523791806353da5c5c04832f123a0a6df118642eee1632a3
      .created = 2019/07/05 14:49:20.113
      #cno.mal.umptyscrunch
      #cno.threat.viciouswombat
  hash:sha256=b4e3b2a1f1e343d14af8d812d4a29440940b99aaf145b5699dfe277b5bfb8405
      .created = 2019/07/05 14:49:20.116
      #cno.mal.umptyscrunch
      #cno.threat.viciouswombat
  complete. 4 nodes in 3 ms (1333/sec).

**Loading the Data:**

Once the data has been validated, we can load it into our live Cortex (replace the Cortex path below with the path to your Cortex; line is wrapped for readability):

::
  
  python -m synapse.tools.csvtool --logfile mylog.json --csv-header
    --cortex aha://cortex... stormfile testfile.csv

.. _csvtool-examples-export:

Export Examples - Overview
--------------------------

The ``--export`` option allows you to export a set of data from a Cortex into a CSV file.

When ``--export`` is used:

- ``stormfile`` contains:

  - the Storm query that specifies the data to be exported; and
  - a statement telling Storm how to format and generate the rows of the CSV file.

- ``csvfile`` is the location where the data should be written.

The Storm ``$lib.csv`` library includes functions for working with CSV files. The ``$lib.csv.emit()`` function will emit CSV rows; the parameters passed to the function define the data that should be included in each row.

``$lib.csv.emit()`` will create one row for each node that it processes (i.e., each node in the Storm "pipeline" that passes through the ``$lib.csv.emit()`` command), as determined by the preceding Storm query.

.. _export-1:

Export Example 1
++++++++++++++++

For this example, we will export the data we imported in :ref:`ingest-2`. For this simple example, we want to export the set of malicious indicators associated with the Vicious Wombat threat group.

**Stormfile:**

To lift all the indicators associated with Vicious Wombat, we can use the following Storm query:

::
  
  #cno.threat.viciouswombat

We then need to tell ``$lib.csv.emit()`` how to format our exported data. We want to list the indicator type (its form) and the indicator itself (the node’s primary property value).

While this seems pretty straightforward, there are two considerations:

- Given our example above, we have multiple node types to export (``inet:url``, ``hash:sha256``, ``inet:fqdn``).
- While we can reference any secondary property directly using its relative property name (i.e., ``:zone`` for ``inet:fqdn:zone``), referencing the primary property value is a bit trickier, as is referencing the form of the node.

:ref:`vars-node-node` is a built-in Storm variable that represents the **current node** passing through the Storm pipeline. ``$node`` supports a number of methods (:ref:`storm-adv-methods`) that allow Storm to access various attributes of the current node. In this case:

- The :ref:`meth-node-form` method will access (return) the current node’s form.
- The :ref:`meth-node-value` method will access (return) the current node’s primary property value.

This means we can tell ``$lib.csv.emit()`` to create a CSV file with a list of indicators as follows:

::
  
  $lib.csv.emit($node.form(), $node.value())

So our overall ``stormfile`` to lift and export all of the Vicious Wombat indicators is relatively simple:

::
  
  #cno.threat.viciouswombat
  $lib.csv.emit($node.form(), $node.value())

**Exporting the Data:**

We can now test our export of the data we ingested in :ref:`ingest-2` (replace the Cortex path below with the path to your Cortex; line is wrapped for readability):

::
  
  python -m synapse.tools.csvtool --debug --export
    --cortex aha://cortex... stormfile export.csv

If we view the contents of ``export.csv``, we should see our list of indicators:

::
  
  inet:fqdn,search.webstie.net
  hash:sha256,7fd526e1a190c10c060bac21de17d2c90eb2985633c9ab74020a2b78acd8a4c8
  inet:fqdn,dns.domain-resolve.org
  hash:sha256,b20327c03703ebad191c0ba025a3f26494ff12c5908749e33e71589ae1e1f6b3
  hash:sha256,b214c7a127cb669a523791806353da5c5c04832f123a0a6df118642eee1632a3
  hash:sha256,b4e3b2a1f1e343d14af8d812d4a29440940b99aaf145b5699dfe277b5bfb8405
  inet:url,http://search.webstie.net/

.. _export-2:

Export Example 2
++++++++++++++++

For this example, we will export the DNS A records we imported in :ref:`ingest-1`. We will create a CSV file that matches the format of our original ingest file, with columns for domain, IP, and first / last resolution times.

**Stormfile:**

To lift the DNS A records for the domains ``woot.com``, ``hurr.net``, and ``derp.org``, we can use the following Storm query:

::
  
  inet:dns:a:fqdn=woot.com inet:dns:a:fqdn=hurr.net inet:dns:a:fqdn=derp.org

In this case we want ``$lib.csv.emit()`` to include:

- the domain (``:fqdn`` property of the ``inet:dns:a`` node).
- the IP (``:ip`` property of the ``inet:dns:a`` node).
- the first observed resolution (the first half of the ``.seen`` property).
- the most recently observed resolution (the second half of the ``.seen`` property).

As a first attempt, we could specify our output format as follows to export those properties:

::
  
  $lib.csv.emit(:fqdn, :ip, .seen)

This exports the data from the relevant nodes as expected, but does so in the following format:

::
  
  woot.com,"(4, 16909060)","(1524057167000, 1529747112000)"

We have a few potential issues with our current output:

- The IP address is exported using its raw value instead of in human-friendly dotted-decimal format.
- The ``.seen`` value is exported into a single field as a combined ``"(<min>, <max>)"`` pair, not as individual comma-separated timestamps.
- The ``.seen`` values are exported using their raw Epoch millis format instead of in human-friendly datetime strings.

We need to do some additional formatting to get the output we want in the CSV file.

*IP Address*

Synapse stores IP addresses as tuples of integers, so specifying ``:ip`` for our output definition gives us the raw value for that property. If we want the human-readable value, we need to use the human-friendly representation (:ref:`gloss-repr`) of the value. We can do this using the :ref:`meth-node-repr` method to tell Storm to obtain and use the repr value of a node instead of its raw value (:ref:`meth-node-value`).

``$node.repr()`` by itself (e.g., with no parameters passed to the method) returns the repr of the primary property value of the node passing through the runtime. Our original Storm query, above, lifts DNS A records - so the nodes passing through the runtime are ``inet:dns:a`` nodes, not IP nodes. This means that using ``$node.repr()`` by itself will return the repr of the ``inet:dns:a`` node, not the ``:ip`` property.

We can tell ``$node.repr()`` to return the repr of a specific secondary property of the node by passing the **string** of the property name to the method:

::
  
  $node.repr(ip)

*.seen times*

``.seen`` is an :ref:`type-ival` (interval) type whose property value is a paired set of minimum and maximum timestamps. To export the minimum and maximum as separate fields in our CSV file, we need to split the ``.seen`` value into two parts by assigning each timestamp to its own variable. We can do this as follows:

::
  
  ($first, $last) = .seen

However, simply splitting the value will result in the variables ``$first`` and ``$last`` storing (and emitting) the raw Epoch millis value of the time, not the human-readable repr value. Similar to the way in which we obtained the repr value for the ``:ip`` property, we need to assign the human-readable repr values of the ``.seen`` property to ``$first`` and ``$last``:

::
  
  ($first, $last) = $node.repr(".seen")

**Stormfile**

We can now combine all of these elements into a Storm query that:

- Lifts the ``inet:dns:a`` nodes we want to export.
- Splits the human-readable version of the ``.seen`` property into two time values and assigns them to variables.
- Generates ``$lib.csv.emit()`` messages to create the CSV rows.

Our full stormfile query looks like this:

::
  
  inet:dns:a:fqdn=woot.com inet:dns:a:fqdn=hurr.net inet:dns:a:fqdn=derp.org
  
  ($first, $last) = $node.repr(".seen")
  
  $lib.csv.emit(:fqdn, $node.repr(ip), $first, $last)

.. WARNING::
  
  The data submitted to ``$lib.csv.emit()`` to create the CSV rows **must** exist for every node processed by the function. For example, if one of the ``inet:dns:a`` nodes lifted by the Storm query and submitted to ``$lib.csv.emit()`` does not have a ``.seen`` property, Storm will generate an error and halt further processing, which may result in a partial export of the desired data.
  
  Subqueries (:ref:`storm-ref-subquery`) or various flow control processes (:ref:`storm-adv-control`) can be used to conditionally account for the presence or absence of data for a given node.


**Exporting the Data:**

We can now test our export of the data we ingested in :ref:`ingest-1` (replace the Cortex path below with the path to your Cortex; line is wrapped for readability):

::
  
  python -m synapse.tools.csvtool --debug --export
    --cortex aha://cortex... stormfile export.csv

If we view the contents of ``export.csv``, we should see the following:

::
  
  woot.com,1.2.3.4,2018/04/18 13:12:47.000,2018/06/23 09:45:12.000
  hurr.net,5.6.7.8,2018/10/03 00:47:29.000,2018/10/04 18:26:06.000
  derp.org,4.4.4.4,2019/06/09 09:00:18.000,2019/07/03 15:07:52.000


