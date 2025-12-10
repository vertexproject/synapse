Synapse Release Process
=======================

This doc details the release process we use for Synapse.

Github Milestone Management
---------------------------

The next milestone should be created in github.  For example, if the current release is v2.220.0, we should have a
v2.22x.x milestone created. When PRs are created or issues are addressed (via PR), they should be added to the
milestone before merge time. This allows us to easily group PRs that will go into the release.

Writing Changelog Entries
-------------------------

Pull requests should have changelog entries associated with them. These entries can be generated via the
``synapse.tools.utils.changelog`` tool. These should generally be written in past tense, with the intended audience as
users of Synapse. The usage of engineering terminology discouraged.

A changelog can be generated like the following::

    python -m synapse.tools.utils.changelog gen --add --type feat 'Added a cool new feature to Synapse!'

.. note::

    Running this CLI tool must be done from a directory with a ``./.git`` repo in it.

That will store a ``.yaml`` file in ``./changes/`` in the root of the repo and stage it in git. The filenames are
randomly generated. The contents can be inspected and edited as needed. For example, the above command would have
generated the following file::

    cat ./changes/e1e8443ed479483e1e9501541be9ad08.yaml
    ---
    desc: Added a cool new feature to Synapse!
    desc:literal: false
    prs: []
    type: feat
    ...

Since the file has been added to the git staging area; the next ``git commit`` will commit the file.

Each key in the ``.yaml`` file has the following purposes:

``desc``
    The ``desc`` key contains the text of the changelog entry.

``desc:literal``
    This is boolean value which indicates the ``desc`` value should be inserted as-is into the RST output when
    formatting the changelog. That is only neccesary if the changelog entry needs to be more complex than a simple
    line wrapped string.

``prs``
    This lists PR numbers that would be included in the changelog entry. This is optional; as PR numbers will also be
    pulled from ``git`` commit history when generating the changelog as well.

``type``
    This is the type of entry that is changelog is for. This is used as part of the sorting of changlog entries and
    the presentation of certain information in the changelog.

The changelog tool ``gen`` command supports creating entries with the following ``--type`` values:

``migration``
    This category should be used for any changes which will cause a automatic migration to occur for data stored in
    Synapse.

``model``
    This category should be used for any changes related to the Synapse data model. This should especially be used when
    the changes will not be included in the model differ, such as changing the norm functionality of a built in type.

``feat``
    This category should be used for any changes related to new functionality being added to Synapse.

``bug``
    This category should be used for any changes related to erroneous or incorrect behaviors.

``note``
    This category should be used for any changes that are more engineering oriented that should not be the first things
    presented to a user.

``doc``
    This category should be used for any changes related to the documentation of Synapse.

``deprecation``
    This category should be used for any changes related to the documentation of Synapse.

A given PR should have as many changelog entries as it needs to convey the changes being made as a result of the work.
Small, internal changes which are not user facing may not require a changelog entry.
Small model changes may not need a ``model`` entry either, as those changes should be picked up with the model differ.

Cutting the Release
-------------------

This in done in several parts:

    #. Check latest images for known vulnerabilities.
    #. Run internal regression testing tools.
    #. Ensure the Github milestone is correct.
    #. Prepare a PR with the release notes.
    #. Tag the release.
    #. Add a record of model changes; if needed.
    #. Close out the Github milestone.

Image checking
**************

Using the script in ``./scripts/image_check.sh``, we can run it to generate image vulnerability reports.
Items found in this script should be triaged and addressed as needed.

.. note::
    This scripts requires additional tools to execute. These are not bundled in this repository.

Github Milestone checking
*************************

Find all the commits on the release branch since the last tag from the branch. This can easily be done
here: https://github.com/vertexproject/synapse/compare

Select the previous tag as the ``base`` value; and the release branch as the ``compare`` value.

For each PR in the commit history do the following:

#. Ensure it has been added to the next release milestone.
#. Ensure it has a changelog file, if needed. Sometimes large PRs may miss a changelog entry and entries will have to
   be written for them during the release proces.
#. If the PR is changing something that was changed in another PR it may not have a changelog entry. Note it so that PR
   can be added to the links during the release process.

Once that is done, you can update the milestone name here to match the next release tag for the branch:
https://github.com/vertexproject/synapse/milestones

Preparing The Release Notes
***************************

Changelog entries are automatically generated from the ``./changes/*.yaml`` files which were written during PRs. The
generated changelog can be made with the ``synapse.tools.utils.changelog`` tool.

First, checkout a new branch::

    git checkout -b docs_changelog_`date +%Y%m%d`
    Switched to a new branch 'docs_changelog_20251209'

To test the generation you can need to with the changelog too, you need to specify the release version and the path to
the previous model entry. The following is an example of that::

    python -m synapse.tools.utils.changelog format --version v2.229.0 --model-ref ./changes/modelrefs/model_2.228.0_c75a6ca0b5678ebdb4dc4f840be23852462bbb5b.yaml.gz
    No model changes detected.
    CHANGELOG ENTRY:


    v2.229.0 - 2025-12-10
    =====================

    Features and Enhancements
    -------------------------
    - Updated Python logging configuration to write messages in a separate thread
      for better performance.
      (`#4601 <https://github.com/vertexproject/synapse/pull/4601>`_)
    - Added ``storm.sudo`` permission which allows users to optionally run Storm
      queries as a global admin.
      (`#4607 <https://github.com/vertexproject/synapse/pull/4607>`_)

    Bugfixes
    --------
    - Fixed a bug where the ``auth.role.show`` command would show empty AuthGates
      after all rules were removed from the gate.
      (`#4597 <https://github.com/vertexproject/synapse/pull/4597>`_)
    - Fixed an issue where the maximum value allowed for unsigned integer types was
      lower than the actual maximum value possible for the size.
      (`#4598 <https://github.com/vertexproject/synapse/pull/4598>`_)
    - Fixed an issue with Telepath links not inheriting ``certhash`` and
      ``hostname`` options from their parent link.
      (`#4608 <https://github.com/vertexproject/synapse/pull/4608>`_)

In this example, no model changes were detected. If model differences are detected, then there will also be a changelog
entry added about that those findings and generated model update will be written to
``./docs/synapse/userguides/model_updates/``.

When that output is sufficient, you can re-run the changelog tool with ``--rm`` to also ``git rm`` the ``.yaml`` files
used to generate the changelog::

    python -m synapse.tools.utils.changelog format --version v2.229.0 --rm --model-ref ./changes/modelrefs/model_2.228.0_c75a6ca0b5678ebdb4dc4f840be23852462bbb5b.yaml.gz

Then the changelog can be copied to the top of the ``./CHANGELOG.rst`` file at the root of the repository.

Ensure that any notable PRs missing entries get entries written here in the appropriate category.

Ensure that any PRs which amended an existing change get linked to the relavent changed here as well. For example, if
PR 4500 modified the work on PR 4490, the original log may look like this::

    - Made the foo objects extra fast.
      (`#4490 <https://github.com/vertexproject/synapse/pull/4490>`_)

Adding PR 4500 would look like this::

    - Made the foo objects extra fast.
      (`#4490 <https://github.com/vertexproject/synapse/pull/4490>`_)
      (`#4500 <https://github.com/vertexproject/synapse/pull/4500>`_)

Any model doc output should be reviewed as well for grammar and structural differences. Some of the differ output may
be opaque data structure changes that need to be rewritten as prose. The original model doc update ``.rst`` file will
be automatically added to the ``git`` staging area; so additional changes should be quick to add via ``git add -p``.

Commit the changes that include the following items:

#. The removed ``.yaml`` files.
#. The updated ``CHANGELOG.rst`` file.
#. The new model update ``.rst`` file, if applicable for the release.

The commit should look like this::

    git commit -m "Changelog for v2.229.0 release."

Push the branch and open a PR for review and merge. This PR should be added to the release milestone.

Tagging the Release
*******************

Version tagging in Synapse is managed by ``bump2version``. This handles updating the .py files containing the version
number in them, as well as creating git tags and commit messages.  There should not be a need to manually edit
version numbers or do git commits.

bump2version is a python application, and can be installed via pip::

    python -m pip install -r requirements_dev.txt

    # Or if a editable install is used:

    python -m pip install -e .[dev]

Bumpversion is designed for projects which do semantic versioning. This can be done via the following (assuming the vertexproject/synapse
remote is called 'upstream')::

    # Ensure we're on master with the latest version
    git checkout master && git fetch --all && git merge master
    # Do a dry-run to ensure that we're updating things properly
    bumpversion --dry-run --verbose minor
    # Bump the patch version
    bumpversion --verbose minor
    # Ensure that no erroneous changes were introduced by bumpversion
    git show HEAD
    # Push the new commit and tag up to github
    git push
    # Push the new tag up explicitly. Do not use --tags
    git push <the new tag>

The release in Github will be created automatically as a CI step.

Making a record of the model
****************************

If there were data model changes in the release, we copy of the data model needs to be saved. This can be done with the
changelog tool. This should be done immediately after the tag commit; so the commit embedded in the model file matches
that of the release. For example::

    python -m synapse.tools.utils.changelog model --save
    Saved model to /home/work/synapse/changes/modelrefs/model_2.228.0_783329e059c437fbe27d012b72aa52f1fb942324.yaml.gz

Then add the model file, commit it, and push that up to the release branch as well::

    git commit -m "Added model ref from v2.228.0"
    git push

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
