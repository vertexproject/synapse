.. _synapse-document-mastering:

Synapse Doc Mastering
=====================

Documentation for creation and generation of documentation for Synapse.

Generating Docs Locally
-----------------------

API documentation is automatically generated from docstrings, and additional
docs may also be added to Synapse as well for more detailed discussions of
Synapse subsystems.  This is currently done via readthedocs.

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
      # Remove all old files and remove the autodocs directory
      rm -rf synapse/autodocs

Mastering Docs
--------------

Synapse documents are mastered using either raw ReStructuredText (.rst) files
or Synapse RStorm files (.rstorm). RStorm allows for embedding Storm directives,
and therefore should be used for documenting Storm examples, so that the code is
run at the time of document generation.

In general, docs for Synapse fall into two categories: User guides and developer
guides.  User guides should be mastered in ``./docs/synapse/userguides`` and
developer guides should be mastered in ``./docs/synapse/devguides``.  Additional top
level sections may be added over time.

In some cases there may undesired Python syntax highlighting. In order to disable that,
add the following to the first line of the RST body of a document:
  
  ``.. highlight:: none``

This will disable all code highlighting in a given document, until another
``highlight`` directive is encountered.

Once new documents are made, they will need to be added to the appropriate
toctree directive. There are three index documents:

- index.rst - This controls top-level documentation ordering. It generally
  should not need to be edited unless adding a new top level document or
  adding an additional section to the second level Synapse directory.

- synapse/userguide.rst - This controls the TOC ordering for user guides.

- synapse/devguide.rst - The controls the TOC ordering for developer guides.
