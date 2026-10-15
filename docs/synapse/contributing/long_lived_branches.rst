.. _synapse-long-lived-branches:

Synapse Long-Lived Branches
===========================

This doc details the long-lived branches in the Synapse repository and how they
are maintained. ``master`` is the default branch.

2x-3x-preparation
-----------------

The ``2x-3x-preparation`` branch stages Synapse v3 readiness checking work that
is long lived and reviewed atomically. It was cut from ``master``.

* Feature PRs target ``2x-3x-preparation`` and are squash merged into it.
* ``master`` is merged into ``2x-3x-preparation`` periodically. See
  `Syncing master`_.
* ``2x-3x-preparation`` will be squash merged into ``master`` once, and then
  retired. See `Merging back into master and retiring`_.

Protection
----------

``2x-3x-preparation`` has the same protection as ``master``:

* The following status checks are required, and the branch must be up to date
  before merging:

  - ``codecov/patch``
  - ``ci/circleci: doctests``
  - ``ci/circleci: python311``

* One approving review is required. Stale approvals are dismissed when new
  commits are pushed.
* Force pushes and deletions are not allowed.

The repository allows merge commits. They are used only for sync PRs. Feature
PRs, and PRs into ``master``, are squash merged.

Syncing master
--------------

A sync of ``master`` into ``2x-3x-preparation`` must land as a merge commit,
never squashed. A merge commit advances the merge base of the two branches to
the synced ``master`` commit, so each sync only carries what is new on
``master``, and the final squash PR into ``master`` shows only the preparation
work. A squash would leave the merge base at the original cut from ``master``,
so later syncs would re-conflict, and the final PR would show every synced
change as new.

The following steps run non-interactively in one shell, which shares ``$day``
and ``$branch`` between them. Steps 1 through 3 run unattended. Step 4 waits for
a person to approve the PR.

#. Create a sync branch from ``2x-3x-preparation``::

    day=$(date -u +%Y%m%d)
    branch="sync/master-$day"
    git fetch origin
    git switch -c "$branch" origin/2x-3x-preparation

#. Merge ``master`` into the sync branch::

    git merge --no-ff origin/master -m 'Merge master into 2x-3x-preparation'

   On a conflict, resolve it, ``git add`` the resolved files, and run
   ``git commit``. ``git merge`` exits non-zero on a conflict; a script must stop
   there and hand off to a person, and never push.

#. Push the sync branch and open the PR::

    git push -u origin "$branch"
    gh pr create --repo vertexproject/synapse --base 2x-3x-preparation --head "$branch" \
        --title "Sync master into 2x-3x-preparation ($day)" \
        --body 'Merges origin/master into 2x-3x-preparation. This PR must land with a merge commit, never squashed.'

   Do not open the PR with ``master`` itself as the head. Conflicts can only be
   resolved on a branch you can push to.

#. Once the PR is approved and the required checks pass, merge it with a merge
   commit::

    gh pr checks "$branch" --repo vertexproject/synapse --required --watch
    gh pr view "$branch" --repo vertexproject/synapse --json reviewDecision --jq .reviewDecision
    gh pr merge "$branch" --repo vertexproject/synapse --merge

   The ``reviewDecision`` must be ``APPROVED``. Never ``--squash`` a sync.
   Auto-merge is disabled in this repository, so run ``gh pr merge`` only after
   both conditions hold; stop on a failed check or a missing approval.

Merging back into master and retiring
-------------------------------------

#. Sync ``master`` into ``2x-3x-preparation`` one last time, following
   `Syncing master`_.
#. Open a PR from ``2x-3x-preparation`` into ``master`` and squash merge it.
#. Remove the branch protection from ``2x-3x-preparation`` and delete the
   branch.
#. Turn "Allow merge commits" back off in the repository settings.
