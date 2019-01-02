



.. _synapse-document-mastering:

Synapse Doc Mastering
=====================

Documentation for creation and generation of documentation for Synapse.

Generating Docs Locally
-----------------------

API documentation is automatically generated from docstrings, and additional
docs may also be added to Synapse as well for more detailed discussions of
Syanpse subsystems.  This is currently done via readthedocs.

In order to do local doc generation you can do the following steps:

#. Install the following packages (preferably in a virtualenv):

   ::

      # cd to your synapse checkout
      cd synapse
      # Install additional packages - this assumes the environment already has
      # any additional packages required for executing synapse code in it.
      python -m pip install -U -r requirements_doc.txt
      # Alternativly, you can install synapse directly in develop mode with pip
      # python -m pip install .[docs]

      # Install pandoc package, required for building HTML.
      # This may require sudo access depending on your environment.
      apt install pandoc


#. Build the docs using sphinx.  A makefile is provided which makes this easy.

   ::

      # Go to your synapse repo
      cd synapse
      # Go to the docs folder
      cd docs
      # Use the make command to build the HTML docs
      make html

#. Now you can open the HTML docs for browsing them.

   ::

      xdg-open _build/html/index.html

#. To rebuild documentation from scratch you can delete the _build directory
   and the ``api`` directories.  Deleting the ``api`` directory will cause the
   automatic Synapse API documentation to be rebuilt.

   ::

      # Delete the _build directory
      make clean
      # Delete the API directory
      rm -rf api

Mastering Docs
--------------

Synapse documents are mastered using either raw ReStructuredText (.rst) files
or as Jupyter Notebooks (.ipynb). Notebooks should be used for documenting
anything which may include Storm or code examples, so that the examples can be
written in a manner that can be asserted, so the documentation can be tested
in the CI pipeline.  Notebooks are also executed during sphinx document build
steps, so any output is current as of document build time. Text in Notebooks
should be mastered as RST using raw NbConvert cells.

In general, docs for Synapse fall into two categories: User guides and devops
guides.  User guides should be mastered in ``./docs/synapse/userguides`` and
devops guides should be mastered in ``./docs/synapse/devops``.  Additional top
level sections may be added over time.

In order to master Notebooks, you will need to setup the hide_code extension
for Jupyter. That is used to selectively hide code and output blocks as
needed. For example, this allows use to hide the code used to run a Storm
command and show the output.

The following steps are a high level overview of the process to setup Jupyter
and add or edit notebooks for documentation purposes.

- Setup the hide_code extension:

   ::

      # Then install & enable the Jupyter hide-code extension
      # This only has to be run once.
      jupyter nbextension install --py --user hide_code
      jupyter nbextension enable --py --user hide_code
      jupyter serverextension enable --py --user hide_code

- Launch Jupyter to run a local notebook server:

   ::

      # Go to your synapse repo
      cd synapse
      # Launch the notebook server
      jupyter notebook

- Navigate to the docs directory in Jupyter.  Create a new notebook or open
  an existing notebook as needed.  This will likely be located under the
  ``docs/synapse/userguides`` or ``docs/synapse/devops`` directories.

- For Storm CLI integration, you can add the following code block into the
  first code cell in order to get some Synapse Jupyter helpers:

.. code:: ipython3

    import os, sys
    try:
        from synapse.lib.jupyter import *
    except ImportError as e:
        # Insert the root path of the repository to sys.path.
        # This assumes the notebook is located three directories away
        # From the root synapse directory. It may need to be varied
        synroot = os.path.abspath('../../../')
        sys.path.insert(0, synroot)
        from synapse.lib.jupyter import *

- You can use helpers to execute storm commands in the following fashion
  to get a CoreCmdr object, execute a storm query printing the CLI ouput
  to screen, while asserting the number of nodes returned, and then 
  closing the object.

.. code:: ipython3

    # Get a CoreCmdr object
    corecmdr = await getTempCoreCmdr()
    # Execute the query and get the packed nodes.
    podes = await corecmdr.eval('[inet:ipv4=1.2.3.4]', 
                                num=1, cmdr=True)


.. parsed-literal::

    cli> storm [inet:ipv4=1.2.3.4]
    
    inet:ipv4=1.2.3.4
            .created = 2019/01/02 00:20:39.780
            :asn = 0
            :loc = ??
            :type = unicast
    complete. 1 nodes in 9 ms (111/sec).


.. code:: ipython3

    await corecmdr.cmdr.runCmdLine('storm reindex --help')


.. parsed-literal::

    cli> storm reindex --help
    
    usage: reindex [-h] [--type TYPE] [--subs] [--form-counts]
    
        Use admin privileges to re index/normalize node properties.
    
        Example:
    
            foo:bar | reindex --subs
    
            reindex --type inet:ipv4
    
        NOTE: This is mostly for model updates and migrations.
              Use with caution and be very sure of what you are doing.
        
    
    optional arguments:
      -h, --help     show this help message and exit
      --type TYPE    Re-index all properties of a specified type.
      --subs         Re-parse and set sub props.
      --form-counts  Re-calculate all form counts.
    
    complete. 0 nodes in 2 ms (0/sec).




- Since the Code cells are persistent, you can reuse the objects from
  earlier cells until a resource has been closed (``.fini()``'d). The
  following example shows using the ``corecmdr`` object from the above
  code section to lift a node and print it to the screen; then closing
  the resource with ``fini()``.

.. code:: ipython3

    from pprint import pprint # We want to make our nodes pretty
    podes = await(corecmdr.eval('inet:ipv4'))
    for pode in podes:
        pprint(pode)
    # Close the object.
    _ = await corecmdr.fini()


.. parsed-literal::

    (('inet:ipv4', 16909060),
     {'iden': '20153b758f9d5eaaa38e4f4a65c36da797c3e59e549620fa7c4895e1a920991f',
      'path': {},
      'props': {'.created': 1546388439780,
                'asn': 0,
                'loc': '??',
                'type': 'unicast'},
      'tags': {}})


- You can enable the hide_code options by selecting the
  "View -> Cell Toolbar -> Hide code" option. This will allow you to
  optionally hide code or output blocks.

- After adding text and code to a notebook, ensure that it runs properly and
  any produces the expected outputs. You can then mark any code cells for
  hiding as necessary; then save your notebook. You can then follow the
  earlier instructions for how to build and view the docs locally.

- Once new documents are made, they will needto be added to the appropriate
  toctree directive. There are three index documents:

  - index.rst - This controls top-level documentation ordering. It generally
    should not need to be edited unless adding a new top level document or
    adding an additional section to the second level Synapse directory.
  - synapse/userguide.rst - This controls the TOC ordering for user guides.
  - synapse/devops.rst - The controls the TOC ordering for devops guides.

- Add notebooks to the repository using ``git add ..path/to/notebook.ipynb``.
  You can then commit the notebook using ``git commit``. If you have the git
  pre-commit hook from ``scripts/githooks/pre-commit``, this will strip any
  output from the notebook upon commit time. This will result in cleaner
  ``git diff`` views over time. See :ref:`synapse-contributing-hook`


Under the hood
--------------

Docs are built from Notebooks using a custom ``conf.py`` file which executes
the notebooks, converting them to RST and using a custom template
(``vertex.tpl``) which looks for flags set by the ``hide_code`` extension.

ReadTheDocs
-----------

Building documents on ReadTheDocs.org using cPython 3.7 is currently an
unsupported operation. This is accomplished using a ``readthedocs.yml`` file,
which uses ``environment_docs.yml`` to configure an 3.7 Anaconda environment.
This is the environment which
