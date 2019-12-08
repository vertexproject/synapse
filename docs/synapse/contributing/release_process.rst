Synapse Release Process
=======================

This doc details the release process we use for Synapse.

Github Milestone Management
---------------------------

The current milestone and the next milestone should be created in github.  For example, if the current release is
v0.1.1, we should have a v0.1.2 and v0.1.3 milestones created. When PRs are created or issues are addressed (via PR),
they should be added to the milestone.  This allows us to easily pull stories and PRs for release note generation.

Release Notes Format
--------------------

Release notes should be compiled from the issues and PRs assigned to the milestone being released. These can all be
obtained via a issue search in github.  For example, if we're releasing v0.1.2, we can pull all the stories via the
following query in github::

    milestone:v0.1.2

Release notes should break things out by the following categories:

    #. New Features in Synapse & Enhancements to existing features
    #. Bugfixes
    #. Major documentation updates

Short text form is fine for describing these.

Cutting the Release
-------------------

This includes three parts:

    #. Preparing the release notes/changelog information.
    #. Tagging the release and pushing to github.
    #. Close out the milestone in Github.

Preparing The Release Notes
***************************

Changelog notes are kept in the ``CHANGELOG.rst`` file.  This allows us to keep a copy of the release notes in the
repository, as well as having them automatically built into our documentation.
This file needs to be updated prior to the release tagging. The formatting for adding the content to the file is the
following::

    <git tag> - YYYY-MM-DD
    ======================

    Features and Enhancements
    -------------------------

    - Add new features (`#XXX <https://github.com/vertexproject/synapse/pull/XXX>`_)

    Bugfixes
    --------

    - Fix old bugs (`#XXX <https://github.com/vertexproject/synapse/pull/XXX>`_)

    Improved Documentation
    ----------------------

    - Write awesome docs (`#XXX <https://github.com/vertexproject/synapse/pull/XXX>`_)

This also allows for machine parseable notes so that ``pyup.io`` can show our changelogs.

It is recommended that as new PRs are made, the PR includes an update to the ``CHANGELOG.rst`` file so that during a
release, notes don't have to be updated.  If that has been done; a simple double check of the issues in the Github
milestone should show anything missing.

When prepping the release, it is okay to add a blank template with the tag set to the next patch value and TBD date,
so that PRs have a place to put their changelogs as they come in.

Tagging the Release
*******************

Version tagging in Synapse is managed by bumpversion. This handles updating the .py files containing the version
number in them, as well as creating git tags and commit messages.  There should not be a need to manually edit
version numbers or do git commits.

bumpversion is a python application, and can be installed via pip::

    python -m pip install bumpversion

.. warning::
    Do *not* use ``bump2version``, the API compatible fork of bumpversion. It changed how tags are made which are
    incompatible with our current CircleCI based workflows.

Bumpversion is designed for projects which do semantic versioning. This can be done via the following (assuming the vertexproject/synapse
remote is called 'upstream')::

    # Ensure we're on master with the latest version
    git checkout master && git fetch --all && git merge upstream/master
    # Do a dry-run to ensure that we're updating things properly
    bumpversion --dry-run --verbose patch
    # Bump the patch version
    bumpversion --verbose patch
    # Ensure that no erroneous changes were introduced by bumvpersion
    git show HEAD
    # Push the new commit and tag up to github
    git push upstream
    # Push the new tag up explicitly. Do not use --tags
    git push upstream <the new tag>

Next, go to github at https://github.com/vertexproject/synapse/tags and edit the release notes for the tag that was
pushed up.  Add a link to the release notes from the readthedocs changelog page for the current release.

Closing Milestone in Github
***************************

Close out the milestone associated with the just released version at the milestones_  page so no new issues are added to
it.

Publishing on Pypi
*******************
Publishing packages to PyPI is done via CircleCi configuration.

Updating Docker images
**********************
Publishing docker images to DockerHub is done via CircleCi configuration.

.. _milestones: https://github.com/vertexproject/synapse/milestones/
