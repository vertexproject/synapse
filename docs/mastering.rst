.. _synapse-document-mastering:

Synapse Doc Master
==================

Documentation for creation and generation of documentation for Synapse.

Docs Generation
---------------

API documentation is automatically generated from docstrings, and additional
docs may also be added to Synapse as well for more detailed discussions of
Syanpse subsystems.  This is currently done via readthedocs.

In order to do local doc generation you can do the following steps:

#. Install the following packages (preferably in a virtualenv):

   ::

      pip install -U -r requirements_doc.txt
      # Enable extensions for jupyter
      jupyter contrib nbextension install --user

#. Build the docs using sphinx.  A makefile is provided which makes this
   painless.

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

If you need to write explicit docs for Synapse, they should be added to the
repository at docs/synapse and a reference added to the docs in docs/index.rst
in order for the documentation

Additional configuration required to setup document building.

After launching jupytyer notebook to start a local notebook server, go here to enable the hide_input extension.
 http://localhost:8888/nbextensions/?nbextension=hide_input/main

You can then select cells which which will have their code input hidden.

# Try hide-code?
python -m pip install hide_code
jupyter nbextension install --user --py hide_code
jupyter nbextension enable hide_code --user --py
