Ingest - Commandline Ingest Tool
================================

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

These options control what we are ingesting, where it is going, and various logging details.

``--core``

    This specifies which Cortex to connect to and add the ingest data to. By default, this is a ram cortex
    (``ram://``), but could be any supported Cortex url or a Telepath url to a Cortex.

``--progress``

    Display the progress of the ingest process every second. This expects no arguments.

``--sync``

    This can be used to sync events from the Cortex specified in the ``--core`` option with a remote Cortex via a
    splice pump. See the `Syncing Data`_ section below for more details.

``--save``

    This creates a savefile for changes made to the Cortex specified in the ``--core`` option. This can be used to
    replay events to another Cortex.

``--debug``

    This drops the user into a cmdr session for the Cortex specified in the ``--core`` option after the ingest
    processing is complete.  It accepts no arguments.

``--verbose``

    This prints the nodes added to the Cortex specified in the ``--core`` option as the nodes are created in the Cortex.
    It accpts no arguments.

Source File Path Location
-------------------------

In many of the Ingest examples, the ingest data files themselves have been located in the ``docs/synapse/examples/``
directory of the Synapse git repository.  They specify source files by name - such as ``ingest_structured_dnsa2.jsonl``.
The Ingest subsystem uses a helper (``loadfile``) which sets a "basedir" value where the ingest definition file
resides. This basedir is where the full file path for source files made with, using ``os.path.join()``. In other words,
the path to the source file in a Ingest definition is relative to the path of the definition file loaded by the Ingest
tool.

.. _`Syncing Data`: ./ug059_ing_sync.html
