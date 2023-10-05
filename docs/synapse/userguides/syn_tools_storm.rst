.. highlight:: none


.. _syn-tools-storm:

storm
=====

The Synapse Storm tool (commonly referred to as the **Storm CLI**) is a text-based interpreter that leverages the Storm query language (see :ref:`storm-ref-intro`).

- `Connecting to a Cortex with the Storm CLI`_
- `Storm CLI Basics`_
- `Accessing External Commands`_

Connecting to a Cortex with the Storm CLI
-----------------------------------------

To access the Storm CLI you must use the ``storm`` module to connect to a local or remote Synapse Cortex.

.. note::

  If you're just getting started with Synapse, you can use the Synapse Quickstart_ to quickly set up and connect to a local Cortex using the Storm CLI.

To connect to a local or remote Synapse Cortex using the Storm CLI, simply run the Synapse ``storm`` module by executing the following Python command from a terminal window, where the *<url>* parameter is the URL path to the Synapse Cortex.

``python -m synapse.tools.storm <url>``

The URL has the following format:

``<scheme>://<server>:<port>/<cortex>``

or

``<scheme>://<user>:<password>@<server>:<port>/<cortex>``

if authentication is used.

**Example URL paths:**

- ``cell://vertex/storage`` (default if using Synapse Quickstart)
- ``tcp://synapse.woot.com:1234/cortex01``
- ``ssl://synapse.woot.com:1234/cortex01``

Once connected, you will be presented with the following Storm CLI command prompt:

``storm>``


Storm CLI Basics
----------------

Once connected to a Synapse Cortex with the Storm CLI, you can execute any Storm queries or Storm commands directly. Detailed information on using the Storm query language to interact with data in a Synapse Cortex can be found in the :ref:`userguide_storm_ref`.

To view a list of available **Storm commands,** type ``help`` from the Storm CLI prompt:

``storm> help``

 - Detailed help for any command can be viewed by entering ``-h`` or ``--help`` after the individual command.
 - For additional detail on Storm commands, see :ref:`storm-ref-cmd`.

To exit the Storm CLI, enter ``!quit``:

``storm> !quit``

 - The ``!quit`` command is technically an "external" (to Storm) command, so must be preceded by the bang (exclamation point) symbol.
 
 
Accessing External Commands
---------------------------

You can access a subset of external Synapse tools and commands from within the Storm CLI. External commands differ from native Storm commands in that they are preceded by a bang / exclamation point ( ``!`` ) symbol.

You can view the available **external commands** by typing ``!help`` from the Storm CLI prompt:

::

    storm> !help
    !export   - Export the results of a storm query into a nodes file.
    !help     - List interpreter extended commands and display help output.
    !pullfile - Download a file by sha256 and store it locally.
    !pushfile - Upload a file and create a file:bytes node.
    !quit     - Quit the current command line interpreter.
    !runfile  - Run a local storm file.


Notably, the Synapse ``pushfile`` and ``pullfile`` tools (used to upload and download files from a Synapse storage :ref:`gloss-axon`) are accessible from the Storm CLI:

``storm> !pushfile``

``storm> !pullfile``

See :ref:`syn-tools-pushfile` and :ref:`syn-tools-pullfile` for additional detail on these tools.

**Help** for any external command can be viewed by entering ``-h`` or ``--help`` after the command:

``storm> !export -h``

``storm> !export --help``



.. _Quickstart: https://github.com/vertexproject/synapse-quickstart
