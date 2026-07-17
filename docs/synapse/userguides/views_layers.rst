.. highlight:: none


.. _userguide_views_layers:

Views and Layers
################

Synapse's architecture supports the separation of data into different storage areas known as **layers.** Layers
can be "stacked" to give users visibility into various combinations of data using **views.**

Views and layers are closely related to Synapse's :ref:`ug_fork_merge` workflow. This section provides some high-level
background on all of these concepts. For additional discussion of views and layers (including examples), see our blog on
`Best Practices for Views & Layers`_.

.. TIP::
  
  Views and layers are closely tied to Synapse's **permissions** system, used to manage which users (or roles)
  can see (read) and edit (create, modify, delete) data. We touch on some high-level permissions concepts here, but
  for a full discussion see the :ref:`adminguide`.

.. _ug_layers:

Layers
======

A :ref:`gloss-layer` is where nodes and node data are stored, where changes to Synapse's data store are made, and
where **write permissions** are enforced. By default, a Synapse Cortex consists of a single layer (the **default**
layer).

Layers can be used to segregate different types of data. For example:

- **Sensitive vs. non-sensitive data.** Organizations may work with data that has varying levels of sensitivity.
  This may include frameworks such as CISA's `Traffic Light Protocol`_ or data that is subject to legal, regulatory,
  or business restrictions (e.g., customer data, personally identifiable information) vs. data that is considered
  to be broadly shareable or public knowledge.
- **Vetted vs. non-vetted data.** Some organizations may publish reporting or otherwise make data in Synapse available
  to customers, partners, or other internal teams. This shared data is typically closely reviewed for accuracy and
  reliability, which may differ from internal data that represents ongoing research or work in progress.

Layers are where data is **written** in Synapse; you create nodes and edges, modify properties, and add or remove tags
in a specific layer. Changes are typically made to the **top** layer of your current **view.**

Layers are typically configured and managed by Synapse Admins. The Storm :ref:`storm-layer` commands are used
to work with layers, as are the :ref:`stormprims-layer-f527` type and its methods, and the :ref:`stormlibs-lib-layer`
libraries. The `Optic UI`_ provides additional GUI-based tools to view and work with layers.

.. _ug_views:

Views
=====

A :ref:`gloss-view` defines the data (specifically, the layer or layers) that users can see; views are where
**read permissions** are enforced. In Synapse, a view consists of an ordered (stacked) set of layers and
provides visibility into the combined data from those layers. The topmost layer in the view is writable and
where any changes are made.

A default installation of Synapse consists of a single view (the **default** view) which contains the default layer;
this setup may be sufficient for simple use cases.

.. TIP::
  
  See :ref:`ug_best_practices` below for considerations related to the **default** view / layer.

In more complex environments, you can define different views (composed of different layers) to provide different
groups of analysts or other users with varying access to Synapse's data. For example:

- the SOC analyst team's view may consist of a layer with a subset of vetted data;
- the threat intel team's view may include the vetted layer and a layer for their ongoing analysis; and
- the incident response team's view may include the vetted data, the analysis data (so they can leverage it for
  their IR activity), and a separate layer for potentially sensitive customer data related to their investigation.

See our blog on `Best Practices for Views & Layers`_ for a more detailed discussion (and examples) of view / layer
architectures.

.. TIP::
  
  A view contains the layer(s) that users can see. Visibility into a view's data is all or nothing; it is not
  possible to let users see "only certain nodes" or "only nodes with this tag" within a given view.

The Storm :ref:`storm-view` commands are used to work with views, along with the :ref:`stormprims-view-f527` type and
its methods and the :ref:`stormlibs-lib-view` libraries. The `Optic UI`_ provides additional GUI-based tools for
working with views.

.. _ug_fork_merge:

Fork and Merge
==============

Synapse includes the ability to :ref:`gloss-fork` an existing view. When you **fork** a view, you create a new view
with a new, empty, writable layer on top of the layer(s) from the original (parent) view. The original layer(s) and
associated data become read-only; any changes that you make in the new view (creating nodes, modifying properties,
adding tags, deleting nodes, etc.) are made to the new topmost layer.

Forked views are used for:

- Easily creating a new view that contains all of the existing layers from the original (parent) view (i.e., you
  do not need to manually construct the new view from scratch).
- Creating a "scratch space" on top of an existing production view.

Forking a view allows you to make changes in the fork without affecting the underlying data. This makes forked views
ideal for a number of purposes:

- analysts can perform exploratory research, enriching data or testing a hypothesis without affecting production
  data.
- junior analysts in training can do their work in a space where it can be reviewed by a senior analyst for
  feedback.
- developers can test new code or automation without affecting live data.

Changes made in a forked view can be reviewed and then **merged** into (written to) the topmost layer of the
parent view. Alternatively, the forked view can be deleted, discarding all unmerged changes. This gives you the
flexibility to:

- incrementally merge subsets of data while you continue your research;
- review and merge some (or all) of your changes when your work in the view is complete;
- optionally delete the view after merging some or all of your data;
- completely delete and discard views (and data) used for testing or that contain errors (such as if you accidentally
  tag 100,000 nodes or retrieve passive DNS data for IPv4 127.0.0.1).

.. NOTE::
  
  When you merge data from a fork in Synapse v3, the merge can include **all** changes - additions,
  modifications, and **deletions**. This behavior differs from Synapse v2, where deletions are not supported
  by the fork and merge workflow and must be made directly in the layer where the data resides.

.. _ug_fork_view:

Fork a View
-----------

The Storm :ref:`storm-view-fork` command is used to fork a view. The `Optic UI`_ includes additional GUI-based tools
to work with (and fork) views, including the `View Selector`_ and `View Task Bar`_ as well as the `Admin Tool`_.

The user who forks a view has **admin** privileges for that view (and its topmost, writable layer). This means
that users who fork a view can do anything within that view; having admin permission to an object allows you
bypass all permissions checks on that object.
  
However, the user may be prevented from **merging** some or all of those changes, based on the write permissions
on the parent layer. See the :ref:`adminguide` for a detailed discussion of permissions, including the example
provided for :ref:`perms_case4`.
  
In addition, the user who forks a view is the only one with access to the view by default. To collaborate
with others within the view or to have someone review your work, you need to grant permissions to individual
users (or to a role or roles). See the :ref:`adminguide` for details on assigning permissions, or the Optic
`User Guide`_ for information on granting permissions in the Optic UI.

.. _ug_review_changes:

Review Changes
--------------

Changes in a forked view should be reviewed before merging. 

The Storm :ref:`storm-diff` command and its options can be used in both the Synapse CLI and the Optic
`Storm Query Bar`_ to display some (or all) changes (differences) between the fork and its parent.

In Optic, the **diff icon** in the `View Task Bar`_ provides an alternative way to view changes.

Both the ``diff`` command and the diff icon will display the **net** changes made in the view. Any
changes that cancel each other out (e.g., applying a tag and then removing it) are not shown in the diff.

.. TIP::
  
  In Optic, you can enable `Review Mode`_ to display changes in bold / dotted underlined text for greater
  visibility.

.. _ug_tombstones:

Tombstones
----------

The fork and merge workflow supports merging **all** changes from the fork into the parent view's topmost
layer, including deletions.

Changes that result from deletions are stored in the forked view as **tombstones**. Within the fork, Synapse
behaves as though deleted properties, tags, edges, or nodes do not exist - e.g., they are not visible when
viewing nodes and are not returned in any query results.

Deletions are displayed in the output of the :ref:`storm-diff` command, along with any other changes in the
fork. The ``diff`` command displays fully deleted nodes as ``syn:deleted`` runtime nodes (runt nodes).

.. TIP::
  
  To view **only** the deleted nodes in a fork, run ``diff | +syn:deleted``.

In Optic, when `Review Mode`_ is enabled, deletions (tombstones) are displayed using bold / strikethrough
text and a tombstone icon. In addition, the ``diff`` command will display fully deleted nodes using their
original form instead of as ``syn:deleted`` nodes.


.. _ug_insert_parent:

Insert a Parent View
--------------------

Forks with a significant number of changes can be challenging to review. In addition, research and enrichment
in a fork may generate many changes that are irrelevant to the final analysis (e.g., research dead ends, or
extraneous data that is not needed to support analytical results). Trying to manually identify, review, and
merge only relevant data can be a time-consuming task (and risky, if the parent view is your production data
where any contamination of that data is undesirable).

To simplify a complex review and merge process, you can **insert** a new view between your forked view and 
its parent. This allows you to safely merge of a subset of data from your fork to the new parent (the inserted
view). This clean subset of data is easier to review and merge into the original parent (production) view
once the review is complete.

In Synapse, the `view.insertparentfork()`_ method can be used to insert the new view.

In Optic, when forking a view (e.g., using the **fork icon** in the `View Task Bar`_), the Fork View dialog
includes a toggle that can be enabled to "Insert as parent view" when creating the fork.
 
.. _ug_merge_changes:

Merge Changes
-------------

Synapse and Optic include simple methods to merge **all** data from a forked view. Both the Storm
:ref:`storm-view-merge` command and the Optic **merge icon** in the `View Task Bar`_ will merge all
changes and then automatically delete the forked view (and its layer) when the merge is complete.

.. TIP::
  
  Both ``view.merge`` and the Optic merge icon run as "set and forget" background tasks. The merge will
  persist and run until completion (e.g., even if the user logs off or the Cortex is disrupted for any
  reason).

Alternatively, the Storm :ref:`storm-merge` command can be used for greater flexibility when merging data.
The command is often used with the :ref:`storm-diff` command to display and then merge specific subsets of
changes. ``Merge`` allows you to:

- show what **would** be merged without actually merging; or
- merge a subset of data based on various filters and selection criteria; or
- merge all data.

The ``merge`` command does **not** delete the forked view or its layer. In addition, the ``merge`` command
is less efficient than using the ``view.merge`` command or the Optic merge icon. With ``merge``, all merged
data is written **twice** - once to commit the change to the parent layer, and again to remove the merged
change from the fork. This can have a significant performance impact for large merges.

.. NOTE::
  
  Deletions (like all other merged changes) are merged from a fork into their parent view. This means that when
  a tombstone is merged:
  
  - if the tombstoned data exists in the parent view's top layer, the data is deleted.
  - if the tombstoned data exists in a layer underneath the parent, the tombstone is written to and retained in
    the parent view / layer. The associated data is unaffected unless the tombstone is written to the relevant
    layer through a subsequent merge.
  - if the tombstoned data is later re-added to the layer containing the tombstone (either directly, or through
    a merge), the new data will annihilate the corresponding tombstone.

Regardless of the merge method used, if permissions restrict a user from merging (writing) data to the parent
view's topmost layer, another user with appropriate permissions must perform the merge.

Alternatively, Synapse Enterprise users can use Optic's `Quorum`_ feature to automatically merge **all** data
in a fork (and automatically delete the forked view and its layer) when a sufficient number of authorized users
have voted to approve the changes.

.. _ug_delete_fork:

Deleting a Forked View
----------------------

Some Storm and Optic merge methods automatically delete the associated view after merging (see above).

You can also delete a forked view manually (e.g., after manually merging data or to discard a view whose data
you do not want to keep).

.. TIP::
  
  You cannot delete a view that has existing forks.

Depending on the method used, deleting the view may or may not delete the associated layer.

- The Storm :ref:`storm-view-del` command deletes a view, but **not** the view's layer(s). These can be deleted
  with the :ref:`storm-layer-del` command.

- In Optic, the **delete icon** in the `View Task Bar`_ will delete a forked view and the forked view's associated
  layer. The Optic `Admin Tool`_ can also be used to manage views.

.. NOTE::
  
  Deleting a layer, either directly or as part of deleting a view, deletes **all data** stored in that layer.

.. _ug_best_practices:

Best Practices
==============

- Use **layers** to segregate any data that should be visible to some users but not others.

- Use **views** to compose the sets of data (layers) that should be visible to particular users or groups.

- When designing and creating an architecture with multiple views and layers, your least sensitive (most
  shareable) data typically resides in the lower views / layers. Data with greater sensitivity or
  restrictions resides in views / layers higher up in the architecture.

- Synapse's **default** view is visible to **all** users; this cannot be changed. Organizations with data
  segregation or sensitivity concerns may wish to avoid storing **any** data in the default view/layer. Instead,
  consider creating a fork of the default view to act as the foundation of your data store.

- **Always** fork a view for all research, analysis, and testing, no matter how trivial or incidental. This
  applies equally to simple (one layer / one view) Cortexes as well as those with more complex view and layer
  architectures. In short, **do not work directly in your production data.** It is much easier to delete a
  forked view (or selectively merge good data and discard mistakes) than it is to undo errors in production.

- Consider your organization's strategy for reviewing and merging data. Depending on how you are using forked
  views (training, research, testing) determine what level of review, if any, is needed before merging data.
  Consider whether these procedures will be enforced by consensus or the use of permissions.

- Forked views provide "scratch space" for ongoing analysis, but can also create silos of data and analysis
  that are inaccessible to other analysts or groups. We encourage you to develop guidance around what data should
  be merged (and how often) in order to balance the need to more fully develop research with the desire to share 
  data that is beneficial to other users.
  
  For example, analysts may enrich IOCs by pulling data from third party sources into Synapse. They may then
  review existing and new data to identify malware families or TTPs, or to cluster threat activity. Tags
  representing their assessments may be preliminary; in the meantime, the nodes or tags created from third party
  data could be useful to others on their team. The :ref:`storm-merge` command could be used to merge new or
  updated nodes without merging any assessment tags while analysis continues.

.. _`Best Practices for Views & Layers`: https://vertex.link/blogs/views-layers/
.. _`Traffic Light Protocol`: https://www.cisa.gov/news-events/news/traffic-light-protocol-tlp-definitions-and-usage
.. _`Optic UI`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/index.html
.. _`View Selector`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/user_interface/userguides/quick_tour.html#view-selector
.. _`View Task Bar`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/user_interface/userguides/quick_tour.html#view-task-bar
.. _`Review Mode`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/user_interface/userguides/fork_merge.html#enable-review-mode
.. _`view.insertparentfork()`: {{SYN_DOCS_BASEURL}}/docs/synapse/latest/synapse/autodocs/stormtypes_prims.html#insertparentfork-name-null
.. _`Quorum`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/user_interface/userguides/quorum.html
.. _`User Guide`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/user_interface/userguide.html
.. _`Storm Query Bar`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/user_interface/userguides/quick_tour.html#storm-query-bar-query-mode-selector
.. _`Admin Tool`: {{SYN_DOCS_BASEURL}}/docs/synapse-enterprise-optic/latest/user_interface/userguides/quick_tour.html#admin-tool
