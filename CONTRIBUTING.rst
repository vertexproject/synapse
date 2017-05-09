Contributing to Synapse
=======================

* `Project Style Guide`_.
* `Docs Generation`_.
* `Contribution Process`_.


Project Style Guide
-------------------

The following items should be considered when contributing to Synapse:

* The project is not currently strictly PEP8 compliant.
* Please keep line lengths under 120 characters.
* Use single quotes for docstrings, not double quotes.
* Use Restructured Text (RST) form when writing docstrings.
* Imports should be in order of shortest to longest import, not alphabetical
  order. Imports should be ordered starting from the Python standard library
  first, then any third party packages, then any Synapse specific imports.
  Please review source files if you are unsure of what this should look like.
* Function names should follow the mixedCase format for anything which is
  exposed as a externally facing API on a object or module.

  - fooTheBar() is acceptable.
  - foo_the_bar() is not acceptable.

* Private methods should be marked as such with a proceeding underscore.

  - privateInternalThingDontUseMe() is not acceptable.
  - _internalThing() is acceptable.

* Convenience methods are availible for unit tests, primarily through the
  SynTest class. This is a subclass of unittest.TestCase and provides many
  short aliases for the assert* functions that TestCase provides.

  - Ensure you are closing resources which may be open with test cases. Many
    Synapse objects may be used as content managers which make this easy for
    test authors.

Contributions to Synapse which do not follow the project style guidelines may
not be accepted.


Docs Generation
---------------

API documentation is automatically generated from docstrings, and additional
docs may also be added to Synapse as well for more detailed discussions of
Syanpse subsystems.  This is currently done via readthedocs.

In order to do local doc generation you can do the following steps:

#. Install the following packages (preferably in a virtualenv):

   ::

      pip install sphinx==1.5.3 Pygments==2.2.0 setuptools==28.8.0 docutils==0.13.1 mkdocs==0.15.0 mock==1.0.1 pillow==2.6.1 git+https://github.com/rtfd/readthedocs-sphinx-ext.git@0.6-alpha#egg=readthedocs-sphinx-ext alabaster>=0.7,<0.8,!=0.7.5 commonmark==0.5.4 recommonmark==0.4.0

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

Contribution Process
--------------------

The Vertex Project welcomes contributions to the Synapse Hypergraph framework
in order to continue its growth!

In order to contribute to the project, do the following:

#. Fork the Synapse repository from the Vertex Project.  Make a new branch in
   git with a descriptive name for your change.  For example:

   ::

       git checkout -b foohuman_new_widget


#. Make your changes. Changes should include the following information:

   * Clear documentation for new features or changed behavior
   * Unit tests for new features or changed behaviors
   * If possible, unit tests should also show minimal use examples of new
     features.

#. Ensure that both your tests and existing Synapse tests succesfully run.
   You can do that manually via the python unittest module, or you can set
   up Travis CI to run tests for your fork.  The following examples show
   manual test runs:

   ::

       python -m unittest discover -v
       python -m unittest synapse.tests.your_test_file -v

   If test coverage is desired, you can use the provided testrunner.sh shell
   script to run a test.  This script will generate HTML coverage reports and
   attempt to open those reports using xdg-open.

   ::

        ./testrunner.sh
        ./testrunner.sh synapse.tests.your_test_file

#. Rebase your feature branch on top of the latest master branch of the Vertex
   Project Synapse repository. This may require you to add the Vertex Project
   repository to your git remotes. The following example of rebasing can be
   followed:

   ::

      # Add the Vertex project repository as a remote named "upstream".
      git remote add upstream https://github.com/vertexproject/synapse.git
      # Grab data from the upstream repository
      git fetch --all
      # Change to your local git master branch
      git checkout master
      # Merge changes from upstream/master to your local master
      git merge upstream/master
      # Move back to your feature branch
      git checkout foohuman_new_feature
      # Rebase your feature branch ontop of master.
      # This may require resolving merge conflicts.
      git rebase master
      # Push your branch up to to your fork - this may require a --force
      # flag if you had previously pushed the branch prior to the rebase.
      git push

#. Ensure your tests still pass with the rebased feature branch.
#. Create the Pull Request in Github, from your fork's feature branch to the
   master branch of the Vertex Project Synapse repository.  Include a
   description and a reference to any open issues related to the PR.
