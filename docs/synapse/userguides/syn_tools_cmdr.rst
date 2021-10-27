.. highlight:: none

.. _syn-tools-cmdr:

Synapse Tools - cmdr
====================

The Synapse ``cmdr`` module is a command line tool used to connect and provide an interactive CLI to an existing local or remote Synapse Cortex.

.. note::
  
  While the ``cmdr`` CLI is still supported, the Synapse storm tool (**Storm CLI**) is the preferred method for users to interact with a Synapse Cortex from the command line. The Storm CLI includes a native Storm interpreter that allows users to execute Storm queries and commands directly, without using the :ref:`syn-storm` command required by ``cmdr`` (see :ref:`syn-tools-storm`).

This section will cover the following Synapse ``cmdr`` CLI topics:

- `Obtaining a Command Line Interface`_
- `Command Line Interface Basics`_

See the :ref:`syn-ref-cmd` for a list of Synapse commands available via ``cmdr``.

.. note::
  
  ``cmdr`` commands are still supported, but the majority are being deprecated in favor of their Storm equivalents (see :ref:`storm-ref-cmd`).

Obtaining a Command Line Interface
----------------------------------

The Synapse ``cmdr`` module can be used to obtain CLI access to a local or remote Synapse Cortex. If you have access to an existing Cortex, proceed to `Connecting to an Existing Cortex`_ for instructions on how to connect to the Cortex. However, if you do not have access to an existing Cortex, proceed to `Connecting to a Temporary Cortex`_ for instructions on creating and connecting to a temporary Cortex on your local machine via ``cmdr``.

.. _cortex-connect:

Connecting to an Existing Cortex
++++++++++++++++++++++++++++++++

To connect to an existing local or remote Cortex using ``cmdr``, run the Synapse ``cmdr`` module by executing the following Python command from a terminal window, where the *<url>* parameter is the URL path to the Cortex.

``python -m synapse.tools.cmdr <url>``

The URL in the above usage statement is the path to the Cortex, and has the following format:

``<scheme>://<server>:<port>/<cortex>``

or

``<scheme>://<user>:<password>@<server>:<port>/<cortex>``

if authentication is used.

**Example URL paths:**

- ``tcp://synapse.woot.com:1234/cortex01``
- ``ssl://synapse.woot.com:1234/cortex01``

Once connected the Cortex, you will be presented with the following Synapse ``cmdr`` CLI command prompt:

``cli>``

.. NOTE::
  
  The path to a storage Axon is specified in the same manner as the path to a data Cortex. That is:
  
    ``<scheme>://<server>:<port>/<axon>``
  
  or
    
    ``<scheme>://<user>:<password>@<server>:<port>/<axon>``


.. _temporary:

Connecting to a Temporary Cortex
++++++++++++++++++++++++++++++++

In the event that you do not have access to an existing Cortex, you can optionally use the Synapse ``feed`` module (:ref:`syn-tools-feed`) to access the CLI. The ``feed`` module is a command line tool that allows you to ingest data into a Cortex. However, it can also be used to create a temporary local Cortex for testing and debugging. 

To create and connect to a temporary local Cortex using the ``feed`` module, execute the following Python command from a terminal window:

``python -m synapse.tools.feed --test --debug``

Once connected the Cortex, you will be presented with the following Synapse CLI command prompt:

``cli>``

.. note::
  
  The Synapse Quickstart_ can be used to quickly set up and connect to a local Cortex using the preferred **Storm CLI** (:ref:`syn-tools-storm`).

Command Line Interface Basics
-----------------------------

Before we delve into Synapse commands, let’s discuss Synapse CLI command parsing and syntax conventions. This section will cover: 

- `Using Whitespace Characters`_
- `Entering Literals`_

.. _whitespace:

Using Whitespace Characters
+++++++++++++++++++++++++++

Whitespace characters (i.e., space) are used within the Synapse CLI to delimit command line arguments. Specifically, whitespace characters are used to separate CLI commands, command arguments, command operators, variables and literals.

Quotation marks are used to preserve whitespace characters in literals entered during variable assignment and comparison (see :ref:`literals`). If quotation marks are not used to quote whitespace characters, Synapse assumes the whitespace characters are used to delimit command line arguments.

When entering a query/command on the Synapse CLI, one or more whitespace characters are **required** between the following command line arguments:

- A command and command line parameters:
  
  ``cli> log --off``
  
  ``cli> storm inet:fqdn=vertex.link inet:email=support@vertex.link``

- An unquoted literal and any subsequent CLI argument:
  
  ``cli> storm inet:email=support@vertex.link | count``
  
  ``cli> storm inet:email=support@vertex.link -> *``

Whitespace characters can **optionally** be used when performing the following CLI operations:

- Assignment operations using the equals sign assignment operator:
  
  ``cli> storm [inet:ipv4=192.168.0.1]``
  
  ``cli> storm [inet:ipv4 = 192.168.0.1]``

- Comparison operations:
  
  ``cli> storm inet:ipv4=192.168.0.1``
  
  ``cli> storm inet:ipv4 = 192.168.0.1``

- Pivot operations:
  
  ``cli> inet:ipv4->*``
  
  ``cli> inet:ipv4 -> *``

Whitespace characters **cannot** be used between reserved characters when performing the following CLI operations:

- Add and remove tag operations. The plus ( ``+`` ) and minus  ( ``-`` ) sign characters are used to add and remove tags to and from nodes in the graph respectively. When performing tag operations using these characters, a whitespace character cannot be used between the actual character and the tag name (e.g., ``+#<tag>``).
  
  ``cli> storm inet:ipv4 = 192.168.0.1 [-#oldtag +#newtag]``


.. _literals:

Entering Literals
+++++++++++++++++

Single ( ``' '`` ) or double ( ``" "`` ) quotation marks can be used when entering a literal on the CLI during an assignment or comparison operation. Enclosing a literal in quotation marks is **required** when the literal:

- begins with a non-alphanumeric character,
- contains a space ( ``\s`` ), tab ( ``\t`` ) or newline( ``\n`` ) character, or
- contains a reserved Synapse character (e.g., ``\ ) , = ] } |``).

Enclosing a literal in single quotation marks will preserve the literal meaning of **each character.** Enclosing literals in double quotation marks will preserve the literal meaning of all characters **except for** the backslash ( ``\`` ) character.

The commands below demonstrate assignment and comparison operations that **do not require** quotation marks:

- Lifting the domain ``vtx.lk``:
  
  ``cli> storm inet:fqdn = vtx.lk``

- Lifting the file name ``windowsupdate.exe``:
  
  ``cli> storm file:base = windowsupdate.exe``

The commands below demonstrate assignment and comparison operations that **require** the use of quotation marks. Failing to enclose the literals below in quotation marks will results in a syntax exception.

- Lift the file name ``windows update.exe`` which contains a whitespace character:
  
  ``cli> storm file:base = "windows update.exe"``

- Lift the file name ``windows,update.exe`` which contains the comma special character:
  
  ``cli> storm file:base = "windows,update.exe"``

.. _Quickstart: https://github.com/vertexproject/synapse-quickstart
