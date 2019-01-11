Contributing to Synapse
=======================

* `Project Style Guide`_.
* `Git Hook & Syntax Checking`_.
* `Contribution Process`_.

Project Style Guide
-------------------

The following items should be considered when contributing to Synapse:

* The project is not currently strictly PEP8 compliant.  Compliant sections
  include the following:

  - `Whitespace in Expressions and Statements <https://www.python.org/dev/peps/pep-0008/#whitespace-in-expressions-and-statements>`_.
  - `Programming Recommendations <https://www.python.org/dev/peps/pep-0008/#programming-recommendations>`_ regarding
    singleton comparison (use 'is' instead of equality operators).

* Please keep line lengths under 120 characters.
* Use single quotes for string constants (including docstrings) unless double
  quotes are required.

  ::

     # Do this
     foo = '1234'
     # NOT this
     foo = "1234"

* Use a single line break between top level functions and class definitions,
  and class methods.  This helps conserve vertical space.

  - Do this

    ::

       import foo
       import duck

       def bar():
           return True

       def baz():
           return False

       class Obj(object):

           def __init__(self, a):
               self.a = a

           def gimmeA(self):
               return self.a

    - NOT this

    ::

       import foo
       import duck


       def bar():
           return True


       def baz():
           return False


       class Obj(object):

           def __init__(self, a):
               self.a = a


           def gimmeA(self):
               return self.a

* Use Google style Python docstrings.  This format is very readable and will
  allow type hinting for IDE users. See the following notes below about our
  slight twist on this convention.

  - Use ''' quotes instead of """ for starting/stoping doc strings.
  - Google Style typically has the summary line after the opening ''' marker.
    Place this summary value on the new line following the opening ''' marker.
  - More information about Google Style docstrings (and examples) can be found
    at the `examples here <http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.
  - We use Napoleon for parsing these doc strings. More info `here <https://sphinxcontrib-napoleon.readthedocs.io>`_.
  - Synapse as a project is not written using the Napoleon format currently
    but all new modules should audhere to that format.
  - Synapse acceptable example:

    ::

        def fooTheBar(param1, param2, **kwargs):
            '''
            Summary line goes first.

            Longer description lives here. It can be a bunch of stuff across
            multiple blocks if necessary.

            Example:
                Examples should be given using either the ``Example`` section.
                Sections support any reStructuredText formatting, including
                literal blocks::

                    woah = fooTheBar('a', 'b', duck='quacker')

            Section breaks are created by resuming unindented text. Section breaks
            are also implicitly created anytime a new section starts.

            `PEP 484`_ type annotations are supported. If attribute, parameter, and
            return types are annotated according to `PEP 484`_, they do not need to be
            included in the docstring:

            Args:
                param1 (int): The first parameter.
                param2 (str): The second parameter.

            Keyword Arguments:
                duck (str): Optional keyword args which come in via **kwargs call conventions,
                            which modify function behavior, should be documented under the
                            Keyword Args section.

            Returns:
                bool: The return value. True for success, False otherwise.

                      The ``Returns`` section supports any reStructuredText formatting,
                      including literal blocks::

                          {
                              'param1': param1,
                              'param2': param2
                          }

            Raises:
                AttributeError: The ``Raises`` section is a list of all exceptions
                    that are relevant to the interface.
                ValueError: If `param2` is equal to `param1`.


            .. _PEP 484:
                https://www.python.org/dev/peps/pep-0484/

            '''
            # Do stuff the with args...


* Imports should first be sorted  in order of shortest to longest import, then
  by alphabetical order (when lengths match). Imports should be ordered
  starting from the Python standard library first, then any third party
  packages, then any Synapse specific imports. The following example shows the
  recommended styling for imports:

  ::

    # Stdlib
    import logging
    import collections
    # Third Party Code
    import barlib.duck as b_duck
    import foolib.thing as f_thing
    # Synapse Code
    import synapse.common as s_common
    import synapse.compat as s_compat
    import synapse.cortex as s_cortex
    import synapse.lib.config as s_config

* Previously we used * imports in the Synapse codebase (especially around synapse.exc and synapse.common). If common
  functions or exceptions are needed, import synapse.common as noted above, and both the common functions and the
  entirety of synapse.exc exceptions will be available.  This provides a consistent manner for referencing common
  functions and Synapse specific exception classes. New code should generally not use * imports.  Here is an example:

  ::

     # Do this
     import synapse.common as s_common
     tick = s_common.now()
     if tick < 1000000000:
        raise s_common.HitMaxTime(mesg='We have gone too far!')

     # NOT this
     from synapse.common import *
     tick = now()
     if tick < 1000000000:
        raise HitMaxTime(mesg='We have gone too far!')

* Function names should follow the mixedCase format for anything which is
  exposed as a externally facing API on a object or module.

  ::

    # Do this
    fooTheBar()
    # NOT this
    foo_the_bar()

* Private methods should be marked as such with a proceeding underscore.

  ::

    # Do this
    _internalThing()
    # NOT this
    privateInternalThingDontUseMe()

  - The corralary to this is that any function which is not private may be
    called arbitrarily at any time, so avoid public API functions which are
    tightly bound to instance state. For example, if a processing routine is
    broken into smaller subroutines for readability or testability, these
    routines are likely private and should not be exposed to outside callers.


* Function calls with mandatory arguments should be called with positional
  arguments.  Do not use keyword arguments unless neccesary.

  ::

    def foo(a, b, duck=None):
       print(a, b, duck)

    # Do this
    foo('a', 'b', duck='quacker')
    # Not this
    foo(a='a', b='b', duck='quacker')

* Avoid the use of @property decorators. They do not reliably work over the
  telepath RMI.
* Logging should be setup on a per-module basis, with loggers created using
  calls to logging.getLogger(__name__).  This allows for module level control
  of loggers as neccesary.

  - Logger calls should use logging string interpolation, instead of using
    % or .format() methods.  See Python Logging module docs for reference.
  - Example:

   ::

      # Get the module level logger
      logger = logging.getLogger(__name__)
      # Do this - it only forms the final string if the message is
      # actually going to be logged
      logger.info('I am a message from %s about %s', 'bob', 'a duck')
      # NOT this - it performs the string format() call regardless of
      # whether or not the message is going to be logged.
      logger.info('I am a message from {} about {}'.format('bob', 'a duck'))

* It may be neccesary from time to time to include non-ASCII characters. Use
  UTF8 formatting for such source files and use the following encoding
  declaration at the top of the source file.

  ::

     # -*- coding: utf-8 -*-

* Convenience methods are available for unit tests, primarily through the
  SynTest class. This is a subclass of unittest.TestCase and provides many
  short aliases for the assert* functions that TestCase provides.

  - Ensure you are closing resources which may be open with test cases. Many
    Synapse objects may be used as content managers which make this easy for
    test authors.

* Avoid the use of the built-in ``re`` module. Instead use the third-party ``regex``
  module. ``regex`` is preferred due to known bugs with unicode in the ``re``
  module. Additionally, ``regex`` does provide some performance benefits over
  ``re``, especially when using pre-compiled regular expression statements.

* Whenever possible, regular expressions should be pre-compiled. String
  matches/comparisons should be performed against the pre-compiled regex instance.

  ::

      # Do this
      fqdnre = regex.compile(r'^[\w._-]+$', regex.U)

      def checkValue(valu):
          if not fqdnre.match(valu):
              self._raiseBadValu(valu)

      # NOT this
      def checkValue(valu):
          if not regex.match(r'^[\w._-]+$', valu, regex.U)
              self._raiseBadValu(valu)

* Return values should be preferred over raising exceptions. Functions/methods
  that return a value should return None (or a default value) in the case of an
  error.  The logic behind this is that it is much easier, cleaner, faster to
  check a return value than to handle an exception.

  Raising exceptions is reserved for "exceptional circumstances" and should
  NEVER be used for normal program flow.

  ::

      # Do this
      def getWidgetById(self, wid):
          widget_hash = self._index.get(wid)
          if widget_hash is None:
              return None

          widget = self._widgets.get(widget_hash)
          return widget

      # NOT this
      def getWidgetById(self, wid):
          widget_hash = self._index.get(wid)
          if widget_hash is None:
              raise NotFoundError

          widget = self._widgets.get(widget_hash)
          if widget is None:
              raise NotFoundError

          return widget

Contributions to Synapse which do not follow the project style guidelines may
not be accepted.


.. _synapse-contributing-hook:

Git Hook & Syntax Checking
--------------------------

A set of helper scripts are available for doing python syntax checking.
These include a script to do generic syntax checking of all synapse files;
a git pre-commit hook; and a script to run autopep8 on staged git files.

The pre-commit hook does syntax checking on .py files which contain invalid
syntax. The hook will **ALSO** run nbstripout on .ipynb files to remove output
data from cells. This results in cleaner diffs for .ipynb files over time.

#. An example of running the generic syntax check script is seen below:

   ::

      ~/git/synapse$ ./scripts/syntax_check.py
      PEP8 style violations have been detected.

      ./synapse/tests/test_lib_types.py:397: [E226] missing whitespace around arithmetic operator
      ./synapse/tests/test_lib_types.py:398: [E226] missing whitespace around arithmetic operator


#. Installing the git hook is easy:

   ::

      cp scripts/githooks/pre-commit .git/hooks/pre-commit
      chmod +x .git/hooks/pre-commit


#. After installing the hook, attempting a commit with a syntax error will fail

   ::

      ~/git/synapse$ git commit -m "Demo commit"
      PEP8 style violations have been detected.  Please fix them
      or force the commit with "git commit --no-verify".

      ./synapse/tests/test_lib_types.py:397: [E226] missing whitespace around arithmetic operator
      ./synapse/tests/test_lib_types.py:398: [E226] missing whitespace around arithmetic operator

#. This may be automatically fixed for you using the `pep8_staged_files.py` script.
   Note that **most**, but not **all** syntax errors may be fixed with the helper script.

   ::

      # Run the pep8_staged_files.py script
      ~/git/synapse$ ./scripts/pep8_staged_files.py
      # Check the diff
      ~/git/synapse$ git diff synapse/tests/test_lib_types.py
      diff --git a/synapse/tests/test_lib_types.py b/synapse/tests/test_lib_types.py
      index 0e3a7498..b81575ef 100644
      --- a/synapse/tests/test_lib_types.py
      +++ b/synapse/tests/test_lib_types.py
       class TypesTest(s_t_utils.SynTest):

           def test_type(self):
      @@ -397,8 +395,8 @@ class TypesTest(s_t_utils.SynTest):
                   self.eq({node.ndef[1] for node in nodes}, {'m'})
                   nodes = await alist(core.eval('testcomp +testcomp*range=((1024, grinch), (4096, zemeanone))'))
                   self.eq({node.ndef[1] for node in nodes}, {(2048, 'horton'), (4096, 'whoville')})
      -            guid0 = 'B'*32
      -            guid1 = 'D'*32
      +            guid0 = 'B' * 32
      +            guid1 = 'D' * 32
                   nodes = await alist(core.eval(f'testguid +testguid*range=({guid0}, {guid1})'))
                   self.eq({node.ndef[1] for node in nodes}, {'c' * 32})
                   nodes = await alist(core.eval('testint | noderefs | +testcomp*range=((1000, grinch), (4000, whoville))'))

      # Add the file and commit
      ~/git/synapse$ git add synapse/tests/test_lib_types.py
      ~/git/synapse$ git commit -m "Demo commit"
      [some-branch f254f5bf] Demo commit
       1 file changed, 3 insertions(+), 2 deletions(-)


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

#. Ensure that both your tests and existing Synapse tests successfully run.
   You can do that manually via the python unittest module, or you can set
   up CircleCI to run tests for your fork (this is a exercise for the reader).
   The following examples shows manual test runs:

   ::

      pytest -v
      pytest -v synapse/tests/your_test_file.py

   If test coverage is desired, you can use the provided testrunner.sh shell
   script to run a test. This script will generate HTML coverage reports and
   attempt to open those reports using xdg-open. This requires the pytest,
   pytest-cov, pytest-xdist packages to be installed.

   ::

      ./scripts/testrunner.sh
      ./scripts/testrunner.sh synapse/tests/your_test_file.py
      ./scripts/testrunner.sh synapse/tests/your_test_file.py::YourTestClass
      ./scripts/testrunner.sh synapse/tests/your_test_file.py::YourTestClass::test_function

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
#. If your changes require extensive documentation, please very your API
   documentation builds properly and any additional user or devops docs are
   created as needed. See :ref:`synapse-document-mastering` for documentation
   mastering notes.
#. Create the Pull Request in Github, from your fork's feature branch to the
   master branch of the Vertex Project Synapse repository.  Include a
   description and a reference to any open issues related to the PR.
