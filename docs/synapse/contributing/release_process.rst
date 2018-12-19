Synapse Release Process
=======================

This doc details the release process we use for Synapse.

Github Milestone Management
---------------------------

The current milestone and the next milestone should be created in github.  For example, if the current release is
v0.0.20, we should have a v0.0.21 and v0.0.22 milestones created. When PRs are created or issues are addressed (via PR),
they should be added to the milestone.  This allows us to easily pull stories and PRs for release note generation.

Release Notes
-------------

Release notes should be compiled from the issues and PRs assigned to the milestone being released. These can all be
obtained via a issue search in github.  For example, if we're releasing v0.0.20, we can pull all the stories via the
following query in github::

    milestone:v0.0.20

Release notes should break things out by the following categories:

    #. New Features in Synapse
    #. Enhancements to existing features
    #. Bugfixes
    #. Major documentation updates

Short text form is fine for describing these.  These notes will be posted up on github on the releases page for
consumption.

Markdown Template
*****************

The following can be used as a markdown template for Github release notes::

    # Synapse <version number> Release Notes

    ## New Features
    - item 1
    - item 2

    ## Enhancements
    - item 1
    - item 2

    ## Bugs
    - item 1
    - item 2

    ## Documentation
    - item 1
    - item 2

Cutting the Release
-------------------

This includes four parts:

    #. Preparing the release notes/changelog information.
    #. Tagging the release and pushing to github.
    #. Publishing the release on pypi.
    #. Publishing new docker images on dockerhub.

Preparing The Release Notes
***************************

Release notes are to be prepared as per the release notes format noted above.

The markdown template also needs to be added to the top of the ``CHANGELOG.md`` file.  This allows us to keep the
changes in repository as well. This file needs to be updated prior to the release tagging. The formatting for adding
the content to the file is the following::

    <git tag> - YYYY-MM-DD
    ----------------------

    ## New Features
    - item 1
    - item 2

    ## Enhancements
    - item 1
    - item 2

    ## Bugs
    - item 1
    - item 2

    ## Documentation
    - item 1
    - item

This also allows for machine parseable notes so that ``pyup.io`` can show our changelogs.

Tagging the Release
*******************

Version tagging in Synapse is managed by bumpversion. This handles updating the .py files containing the version
number in them, as well as creating git tags and commit messages.  There should not be a need to manually edit
version numbers or do git commits.

bumpversion is a python application, and can be installed via pip::

    python -m pip install bumpversion

Bumpversion is designed for projects which do semantic versioning. Since synapse is not yet in that state, we'll be
using bumpversion to do patch releases.  This can be done via the following (assuming the vertexproject/synapse
remote is called 'upstream')::

    # Ensure we're on master with the latest version
    git checkout master && git fetch --all && git merge upstream/master
    # Do a dry-run to ensure that we're updating things properly
    bumpversion --dry-run --verbose patch
    # Bump the patch version
    bumpversion --verbose patch
    # Push the new commit and tag up to github
    git push upstream
    git push upstream --tags

Next, go to github at https://github.com/vertexproject/synapse/tags and edit the release notes for the tag that was
pushed up.  Add the release notes compiled from the previous step.

Publishing on Pypi
*******************
Coming soon (this may be automated very soon)

Updating Docker images
**********************
Coming soon
