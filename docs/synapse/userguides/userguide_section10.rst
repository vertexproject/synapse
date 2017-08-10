Using Synapse - Commands
========================

Synapse includes a command line interface (CLI) for interacting with a Synapse Cortex. The ``cortex`` module is used to connect directly to a Cortex. The ``cmdr`` module is used to connect to a remote Cortex, which is the most common scenario for users of a production Cortex.

To connect to a remote Cortex, pass the path to the Cortex as an argument to the ``cmdr`` module:

  ``python.exe -m synapse.tools.cmdr <path_to_cortex>``

Where ``<path_to_cortex>`` should look similar to:

  ``<protocol>://<server>:<port>/<cortex>``

For example:

  ``tcp://synapse.woot.com:1234/cortex01``

or

  ``ssh://user@synapse.woot.com:1234/cortex01``

Once you connect to the Cortex, you should have a Synapse command prompt:

``cli>``

Synapse Commands
----------------

The Synapse CLI supports various commands for interacting with the Synapse Cortex. The list of currently available commands can be viewed by running help at the command prompt::
  
  cli> help
    ask     - Execute a query.
    guid    - Generate a new guid
    help    - List commands and display help output.
    quit    - Quit the current command line interpreter.
    
Individual commands are documented in greater detail below.

**ask** – executes a Storm query.

Storm is the query language used to interact with data in a Synapse hypergraph. The Synapse ``ask`` command indicates that the input following the command and any command options represents a Storm query.

*Syntax:*

  ``ask [--debug --[props|raw]] <query>``

  * Running ``ask`` with no arguments will display help and usage information.

  * ``ask`` displays the set of nodes returned by ``<query>`` in ``<primary_property>=<value>`` form, along with their associated tags, if any. For hierarchical (dotted) tags, only the final (leaf) tags are displayed.

  * ``--debug`` displays the same data as ask with the addition of informational / diagnostic data about the execution of ``<query>``

  * ``--props`` displays the same data as ``ask`` with the addition of the ``<secondary_property>=<value>`` properties from each node. Output is formatted for readability (e.g., epoch timestamps are displayed in ``YYYY/MM/DD hh:mm:ss.mmmm`` format, IPv4 addresses are displayed as dotted-decimal strings).

  * ``--raw`` displays all properties and tags associated with the node in JSON format, including universal properties (e.g., ``tufo:form=<form>``), ephemeral properties (if any), and all tags (not simply leaf tags).
  
*Examples:*

Retrieve (“lift”) the node representing the domain ``woot.com``. Note that the results indicate the node has been labeled with the tag ``foo.bar`` (``#foo.bar``). ::
  
  cli> ask inet:fqdn=woot.com
  
  inet:fqdn = woot.com
      #foo.bar (added 2017/06/20 19:59:02.854)
  (1 results)
  
- - - - - - - - - - - - - - - - - - - - - - - ::
  
  cli> ask --props inet:fqdn=woot.com
  
  inet:fqdn = woot.com
      #foo.bar (added 2017/06/20 19:59:02.854)
      :created = 2015/06/07 12:33:44.000
      :domain = com
      :host = woot
      :sfx = False
      :zone = True
  (1 results)

- - - - - - - - - - - - - - - - - - - - - - - - ::
  
  cli> ask --raw inet:fqdn=woot.com
  
  [
    [
      "a4d82cf025323796617ff57e884a4738",
      {
        "#foo": 1497988742854,
        "#foo.bar": 1497988742854,
        "inet:fqdn": "woot.com",
        "inet:fqdn:created": 1433680424000,
        "inet:fqdn:domain": "com",
        "inet:fqdn:host": "woot",
        "inet:fqdn:sfx": 0,
        "inet:fqdn:zone": 1,
        "tufo:form": "inet:fqdn"
      }
    ]
  ]
  (1 results)

- - - - - - - - - - - - - - - - - - - - - - - - ::
  
    cli> ask --debug inet:fqdn=woot.com
  
  oplog:
      lift (took:0) {'sub': 0, 'took': 0, 'mnem': 'lift', 'add': 1}
  
  options:
      limit = None
      uniq = 1
  
  limits:
      lift = None
      time = None
      touch = None
  
  inet:fqdn = woot.com
      #foo.bar (added 2017/06/20 19:59:02.854)
  (1 results)
  
**guid** - generates a Globally Unique Identifier (GUID).
  
``guid`` simply generates a 32-byte random number. One use for this command would be to generate a value that could be used as the primary property for a node that does not have a characteristic (or set of characteristics) that can act as a unique primary property.

*Syntax:*

``guid`` (does not take any parameters)

*Example:* ::
  
  cli> guid
  new guid: '5ed3cf8f1e903f24dacfa5e97aa15878'
