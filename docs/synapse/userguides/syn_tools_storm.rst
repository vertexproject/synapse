.. highlight:: none

.. _syn-tools-storm:

Synapse Tools - storm
=====================

The Synapse Storm tool (commonly referred to as the **Storm CLI**) is a text-based interpreter that leverages the Storm query language (see :ref:`storm-ref-intro`). The Storm CLI replaces the Synapse ``cmdr`` tool (see :ref:`syn-tools-cmdr`) as the preferred means for users to interact with a Synapse Cortex. Because the Storm CLI is a native Storm interpreter, users do not need to use the :ref:`syn-storm` command before entering and executing Storm queries or commands.

- `Connecting to a Cortex with the Storm CLI`_
- `Storm CLI Basics`_
- `Accessing Synapse Tools from the Storm CLI`_

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

Once connected to a Synapse Cortex with the Storm CLI, you can execute any Storm queries or commands directly (i.e., without needing to precede them with the :ref:`syn-storm` command).

For information on using the Storm query language to interact with data in a Synapse Cortex, see :ref:`storm-ref-intro` and related Storm documentation.

To view a list of available Storm commands, type ``help`` from the Storm CLI prompt:

``storm> help``

For additional detail on Storm commands, see :ref:`storm-ref-cmd`.


Accessing Synapse Tools from the Storm CLI
------------------------------------------

Most of the commands for working in and with a Synapse Cortex are native Storm commands that can be viewed using the ``help`` command and executed directly from the Storm CLI. 

The Storm CLI also allows you to access a few external Synapse tools. Specifically, the Synapse ``pushfile`` and ``pullfile`` tools can be used to upload and download files from a Synapse storage :ref:`gloss-axon`. These tools can be accessed from the Storm CLI by preceding the command with a bang / exclamation point ( ``!``) character:

``storm> !pushfile``

``storm> !pullfile``

Similarly, **help** for each tool can be viewed by entering ``-h`` or ``--help`` after each "bang" command:

``storm> !pushfile -h``

``storm> !pullfile --help``

See :ref:`syn-tools-pushfile` and :ref:`syn-tools-pullfile` for additional detail on these tools.


.. _Quickstart: https://github.com/vertexproject/synapse-quickstart
