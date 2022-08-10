.. _dev_rapid_power_ups:

Rapid Power-Up Development
##########################

Developing Rapid Power-Ups, also known as Storm Packages, allows Synapse power
users to extend the capabilities of the Storm query language, provides ways to
implement use-case specific commands, embed documentation, and even implement
customized visual workflows in **Optic**, the commercial Synapse UI.

A Rapid Power-Up consists of a **Storm Package** which is a JSON object which
defines everything used to extend the Storm language and provide additional
documentation. **Storm Packages** can be loaded directly into your **Cortex**.

In this guide we will discuss the basics of **Storm Package** development and
discuss a few best practices you can use to ensure they are secure, powerful,
and easy to use.

Anatomy of a Storm Package
==========================

A **Storm Package** consists of a YAML file which defines the various commands, modules,
documentation, and workflows embedded within the package. 

Minimal Example
---------------

As you can see in the minimal example below, the Storm Package is defined by a YAML file
that gets processed and loaded into your Cortex.

``acme-hello.yaml``::

    name: acme-hello
    version: 0.0.1

    synapse_minversion: [2, 101, 0]

    genopts:
        dotstorm: true # Specify that storm command/module files end with ".storm"

    author:
      url: https://acme.newp
      name: ACME Explosives and Anvils

    desc: Acme-Hello is a minimal example of a Rapid Power-Up.

    modules:
      - name: acme.hello

    commands:
      - name: acme.hello.sayhi
        descr: Print the hello message.

.. note::

    First, a note on namespacing. To ensure your **Storm Package** is going to play well
    with other packages, it is important to chose an appropriate namespace for your power-up.
    In this case, the ``acme`` part of the name is meant to be replaced with your company name
    or an abreviated version of it. The ``hello`` part is meant to be replaced with an indicator
    of the type of functionality the **Storm Package** contains.

    Namespace now, thank yourself later.

When you define commands and modules, they will be loaded from files using the location of
the **Storm Package** YAML file to locate their contents::

    acme-hello.yaml
    storm/

        modules/
            acme.hello.storm

        commands/
            acme.hello.sayhi.storm

``storm/modules/acme.hello.storm``::

    function woot(text) {
        $lib.print($text)
    }

``storm/commands/acme.hello.sayhi.storm``::

    $hello = $lib.import(acme.hello)
    $hello.woot("hello storm!")

Building / Loading
------------------

To build and load **Storm Packages**, use the ``genpkg`` tool included within Synapse. For
this example, we will assume you have deployed your Synapse environment according to the
FIXME Deployment Guide::

    python -m synapse.tools.genpkg acme-hello.yaml --load aha://cortex...

.. note::

    If you added an alternate admin user or used a non-standard naming convention
    you may need to adjust the ``aha://cortex...`` telepath URL to connect to
    your Cortex.

Once your **Storm Package** has loaded successfully, you can use the Storm CLI to see it in action::

    invisigoth@visi01:~$ python -m synapse.tools.storm aha://cortex...

    Welcome to the Storm interpreter!

    Local interpreter (non-storm) commands may be executed with a ! prefix:
        Use !quit to exit.
        Use !help to see local interpreter commands.

    storm> acme.hello.sayhi
    hello storm!
    complete. 0 nodes in 1 ms (0/sec).
    storm>

Directory Layout
----------------

Storm Modules
=============

Deploying **Storm** modules allows you to author powerful library functions that you can use in
automation or **Storm** commands to facilitate code re-use and enforce privilidge separation boundaries.

A **Storm** module is specified within the ``modules:`` section of the **Storm Package** YAML file.

::
    modules:

      - name: acme.hello.example00
        modconf:
            varname: varvalu
            othervar: [1, 2, 3]

The ``modconf:`` key can be used to specify variables which will be mapped into the module's **Storm**
runtime and accessible using the implicit variable ``$modconf``::

    function foo() {
        $lib.print($modconf.varname)
        return((10))
    }

    function bar() {
        for $i in $modconf.othervar {
            // do something using $i...
        }
    }

Priviledged Modules
-------------------

In order to facilitate delegating permission for priviledged operations, **Storm** modules may specify
permissions which allow the module to be imported with admin priviledges. It is a best-practice to declare
these permissions within the **Storm** package using the ``perms:`` key before using them::

    perms:
      - perm: [ acme, hello, user ]
        gate: cortex
        desc: Allows a user to call priviliedged APIs from Acme-Hello.

    modules:

      - name: acme.hello.privsep
        asroot:perms:
            - [ acme, hello, user ]

To minimize risk, you must very carefully consider what functions to implement within a priviledged **Storm**
module! Priviledged modules should contain the absolute minimum required functionality.

An excellent example use case for a priviledged **Storm** module exists when you have an API key or password
which you would like to use on a user's behalf without disclosing the actual API key. The **Storm** library
``$lib.globals.set(<name>, <valu>)`` and ``$lib.globals.get(<name>)`` can be used to access protected global
variables which regular users may not access without special permissions.  By implementing a priviledged
**Storm** module which retrieves the API key and uses on the user's behalf without disclosing it, you may
protect the API key from disclosure while also allowing users to use it. For example,
``acme.hello.privsep.storm``::

    function getFooByBar(bar) {

        $apikey = $lib.globals.get(acme:hello:apikey)
        $headers = ({"apikey": $apikey})

        $url = $lib.str.format("https://acme.newp/api/v1/foo/{bar}", bar=$bar)

        $resp = $lib.inet.http.get($url, headers=$headers)
        if ($resp.code != 200) {
            $lib.warn("/api/v1/foo returned HTTP code: {code}", code=$resp.code)
        }

        return($resp.json())
    }

Notice that the ``$apikey`` is being retrived and used to call the HTTP API but is not returned to the caller.

Storm Commands
==============

Adding Storm Commands to your Cortex via a Storm Package is a great way to extend the functionality
of your Cortex in a CLI user-friendly way.

Command Line Options
--------------------

Every **Storm** command has the ``--help`` option added automatically. This means that it is always safe to
execute any command with ``--help`` to get a usage statement and enumerate command line arguments. The
``desc`` field specified in the command is included in the output::

    storm> acme.hello.sayhi --help

    Print the hello message.

    Usage: acme.hello.sayhi [options]

    Options:

      --help                      : Display the command usage.
    complete. 0 nodes in 4 ms (0/sec).
    storm>

**Storm** commands may specify command line arguments using a convention which is similar (although not
identitcal to) Python's ``argparse`` library.

A more complex command declaration::

  commands:

    - name: acme.hello.omgopts
      descr: |
          This is a mult-line description containing usage examples.

          // run the command with some nodes
          inet:fqdn=acme.newp | acme.hello.omgopts vertex.link

          // run the command with some command line switches
          acme.hello.omgopts --debug --hehe haha vertex.link

      cmdargs:

        - - --hehe
          - type: str
            help: The value of the hehe optional input.

        - - --debug
          - type: bool
            default: false
            action: store_true
            help: Enable debug output.

        - - fqdn
          - type: str
            help: A mandatory / positional command line argument.

A more complete example of help output::

    storm> acme.hello.omgopts --help

    This is a mult-line description containing usage examples.

    // run the command with some nodes
    inet:fqdn=acme.newp | acme.hello.omgopts vertex.link

    // run the command with some command line switches
    acme.hello.omgopts --debug --hehe haha vertex.link


    Usage: acme.hello.omgopts [options] <fqdn>

    Options:

      --help                      : Display the command usage.
      --hehe <hehe>               : The value of the hehe optional input.
      --debug                     : Enable debug output.

    Arguments:

      <fqdn>                      : A mandatory / positional command line argument.
    complete. 0 nodes in 6 ms (0/sec).

Command line options are available within the **Storm** command by accessing the implicit
``$cmdopts`` variable.

``storm/commands/acme.hello.omgopts.storm``::

    // An init {} block only runs once even if there are multiple nodes in the pipeline.
    init {

        // set global debug (once) if the user specified --debug
        if $cmdopts.debug { $lib.debug = $lib.true } }

        if ($cmdopts.hehe) { $lib.print("User Specified hehe: {hehe}", hehe=$cmdopts.hehe) }

        // Normalize the FQDN in case we want to send it to an external system
        ($ok, $fqdn) = $lib.trycast($cmdopts.fqdn, inet:fqdn)
          
        if (not $ok) {
            $lib.exit("Invalid FQDN Specified: {fqdn}", ipv4=$cmdopts.fqdn)
        }

        // Maybe call an API here or something...
        $lib.print("FQDN: {fqdn}", fqdn=$fqdn)
    }


    // You may also act on nodes in the pipeline
    $lib.print("GOT NODE: {repr}", repr=$node.repr())

    // Any nodes in the pipeline here are yielded to the caller

Command Option Conventions
--------------------------

--help
  This option is reserved and handled automatically to print a command usage statement which also enumerates any
  positional or optional arguments.

--debug
  This option is typically used to enable debug output in the **Storm** interpreter by setting the ``$lib.debug``
  variable if it us specified. The ``$lib.debug`` variable has a recursive effect and will subsequently enable
  debug output in any command or functions called from the command.

--yield
  By default, a command is generally expected to yield the nodes that it recieved as input from the pipeline. In
  some instances it is useful to instruct the command to yield the nodes it creates. For example, if you specify
  ``inet:fqdn`` nodes as input to a DNS resolver command, it may be useful to tell the command to yield the newly
  created ``inet:dns:a`` records rather than the input ``inet:fqdn`` nodes.  Commands frequently use the ``divert``
  **Storm** command to implement ``--yield`` functionality.

--asof <time>
  To minimize duplicate API calls, many **Storm** packages cache results using the ``$lib.jsonstor`` API. When
  caching is in use, the ``--asof <time>`` option is used to control cache aging. Users may specify ``--asof now``
  to disable caching.

Specifying Documentation
========================

Documentation may be specified in the **Storm Package** file that will embed ``markdown`` documentation into the
package. While there are not currently any CLI tools to view/use this documentation, it is presented in the
**Power-Ups** tab in the **Help Tool** within the commercial Synapse UI Optic_.

<img>

Markdown documents may be specified for inclusion by adding a ``docs:`` section to the **Storm Package** YAML file::
    docs:
        - title: User Guide
          path: docs/userguide.md
        - title: Admin Guide
          path: docs/adminguide.md
        - title: Changelog
          path: docs/changelog.md


Testing Storm Packages
======================

It is **highly** recommended that any production **Storm Packages** use development "best practices" including
version control and unit testing. For this example, we have included a small unit test you can use as an example
to expand upon

``test_acme_hello.py``::

    import synapse.tests.util as s_test
    import synapse.tools.genpkg as s_genpkg

    dirname = os.path.abspath(__module__.path)
    pkgpath = os.path.join(dirname, 'acme-hello.yaml')

    class AcmeHelloTest(s_test.SynTest):

        async def test_acme_hello(self):

            async with self.getTestCore() as core:

                await s_genpkg.main((pkgpath, '--push', core.getLocalUrl()))

                msgs = await core.stormlist('acme.hello.sayhi')
                self.stormIsInPrint('hello storm!', msgs)

                valu = await core.callStorm('return($lib.import(acme.hello.example00).foo())')
                self.eq(10, valu)

With the file ``test_acme_hello.py`` located in the same directory as ``acme-hello.yaml`` you can use the
standard ``pytest`` invocation to run the test::

    pytest -svx test_acme_hello.py

Advanced Features
=================

Optic Actions
-------------

If you have access to the **Synapse** commercial UI **Optic** you may find it helpful to embed **Optic** actions
within your **Storm Package**. These actions will be presented to users in the context-menu when they right-click 
on nodes within **Optic**.

<img>

To define **Optic** actions, you declare them in the **Storm Package** YAML file::

    optic:
        actions:
          - name: Hello Omgopts
            storm: acme.hello.omgopts --debug
            descr: This description is displayed as the tooltip in the menu
            forms: [ inet:ipv4, inet:fqdn ]

By specifying the ``forms:`` key, you can control which node actions will be presented on different forms. For example,
if you are writing a DNS power-up, you may want to limit the specified actions to ``inet:ipv4``, ``inet:ipv6``, and ``inet:fqdn``
nodes.

When selected, the query specified in the ``storm:`` key will be run with the currently selected nodes as input. For example,
if you right-click on the node ``inet:fqdn=vertex.link`` and select ``actions -> acme-hello -> Hello Omgopts`` it will execute
the specified as though it were run like this::

    inet:fqdn=vertex.link | acme.hello.omgopts --debug

Any printed output, including warnings, will be displayed in the ``Console Tool``.

Optic Workflows
---------------

Dependancies
------------

_Optic: http://woot
