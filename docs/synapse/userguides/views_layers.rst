.. highlight:: none


.. _userguide_views_layers:

Views and Layers
################

Synapse's architecture supports the separation of data into different storage areas known as **layers.** Layers
can be "stacked" to give users visibility into various combinations of data using **views.**

Views and layers are closely related to Synapse's :ref:`ug_fork_merge` workflow. This section provides some high-level
background on these concepts. For additional discussion of views and layers (incuding examples), see our blog on
`Best Practices for Views & Layers`_.

.. TIP::
  
  Views and layers are also closely tied to Synapse's **permissions** system, used to manage which users (or roles)
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
  This may include data at different "classification" levels (such as CISA's `Traffic Light Protocol`_) or
  data that is subject to legal, regulatory, or business restrictions (customer data, personally identifiable
  information) vs. data that is considered public knowledge.
- **Vetted vs. non-vetted data.** Some organizations may publish reporting or otherwise make data in Synapse available
  to customers, partners, or other internal teams. This shared data is typically closely reviewed for accuracy and
  reliability, which may differ from "internal" data that represents ongoing research or work-in-progress.

Layers are where data is **written** in Synapse; you create nodes, modify properties, and add or remove tags in a
specific layer. Changes are typically made to the **top** layer of your current **view.**

Layers are typically configured and managed by Synapse Admins. The Storm :ref:`storm-layer` commands are used
to work with layers, as are the :ref:`stormprims-layer-f527` type and its methods, and the :ref:`stormlibs-lib-layer`
libraries. The `Optic UI`_ provides additional GUI-based tools to view and work with layers.

.. _ug_views:

Views
=====

A :ref:`gloss-view` defines the data (specifically, the layer or layers) that users can see; views are where
**read permissions** are enforced. In Synapse, a view consists of an ordered ("stacked") set of layers and
provides visibility into the combined data from those layers. The topmost layer in the view is writeable and
where any changes are made.

A default installation of Synapse consists of a single view (the **default** view) which contains the default layer;
this setup may be sufficient for many use cases.

In more complex environments, you can define different views (composed of different layers) to provide different
groups of analysts or other users with varying access to Synapse's data. For example:

- the SOC analyst team's view may consist of a layer with a subset of vetted data;
- the threat intel team's view may include the vetted layer and a layer for their ongoing analysis; and
- the incident response team's view may include the vetted data, the analysis data (so they can leverage it for
  their IR activity), and a separate layer for potentially sensitive customer data related to their investigation.

.. TIP::
  
  A view contains the layer(s) users can see. Visibility into a layer's data is all or nothing; it is not possible
  to let users see "only certain nodes" or "only nodes with this tag" within a given layer.

The Storm :ref:`storm-view` commands are used to work with views, along with the :ref:`stormprims-view-f527` type and
its methods and the :ref:`stormlibs-lib-view` libraries. The `Optic UI`_ provides additional GUI-based tools for
working with views.

.. _ug_fork_merge:

Fork and Merge
==============

.. _ug_fork_view:

Fork a View
-----------

Synapse includes the ability to :ref:`gloss-fork` an existing view. When you fork a view, you create a new view
with a new, empty, writeable layer on top of the layer(s) from the original (parent) view. The original layer(s) and
associated data become read-only; any changes that you make in the new view (creating nodes, modifying properties,
adding tags, etc.) are made to the new topmost layer.

Forked views are used for:

- Easily creating a new view that contains all of the existing layers from the original (parent) view (that is,
  you do not need to fully construct the new view from scratch).
- Creating a "scratch space" on top of an existing "production" view.

Forking a view allows you to make changes without affecting the underlying data. Any changes can be reviewed and
either committed (**merged**) into the underlying (original) view or discarded. This makes forked views ideal for
a number of purposes:

- analysts can perform exploratory research, testing an approach or hypothesis without affecting "production" data.
- junior analysts undergoing training can do their work in a space where it can be reviewed by a senior analyst
  for feedback before committing their work to production.
- developers can test new code or automation without affecting live data.

The Storm :ref:`storm-view-fork` command is used to fork a view. The `Optic UI`_ includes additional GUI-based tools
to work with (and fork) views, including the `View Selector`_ and `View Task Bar`_ as well as the `Admin Tool`_.

.. TIP::

  The user who forks a view has **admin** privileges for that view (and its topmost, writeable layer). This
  means that users who fork a view can "do anything" within that view. However, they may be prevented from
  **merging** some or all of those changes, based on the write permissions associated with the underlying
  layer. See the :ref:`adminguide` for a detailed discussion of permissions, including the example provided for
  :ref:`perms_case4`.
  
  In addition, the user who forks a view is the only one with access to the view by default. To collaborate
  with others within the view or to have someone review your work, you need to grant permissions to individual
  users (or a role or roles). See the :ref:`adminguide` for details on assigning permissions, or the Optic
  `User Guide`_ for information on granting permissions in the Optic UI.

.. _ug_merge_view:

Merge a View
------------

Changes made in a forked view can be merged into the underlying view (in whole or in part). Alternatively, the
forked view can be deleted, discarding all unmerged changes. This gives you the flexibility to:

- incrementally merge subsets of data while you continue your research;
- review and merge some (or all) of your changes when your work in the view is complete;
- optionally delete the view after merging some or all of your data;
- completely delete and discard views (and data) used for testing or that contain errors (such as if you accidentally
  tag 100,000 nodes or retrieve passive DNS data for IPv4 127.0.0.1).

.. _ug_merge_review_changes:

Reviewing Changes
~~~~~~~~~~~~~~~~~

The Storm :ref:`storm-diff` command can be used in both the Synapse CLI and the Optic `Storm Query Bar`_ and provides
a flexible way to review some or all changes using the command's options. The **diff icon** in the Optic
`View Task Bar`_ provides an alternative way to view changes.

.. _ug_merge_merge_changes:

Merging Changes
~~~~~~~~~~~~~~~

The Storm :ref:`storm-view-merge` command can be used to merge **all** changes and optionally delete the view. In
Optic, the **merge icon** in the `View Task Bar`_ will merge **all** changes and automatically delete the view.

The Storm :ref:`storm-merge` command provides greater flexibility to view and merge data, including:

- show what **would** be merged without actually merging;
- merge all data;
- merge a subset of data based on a range of filters and selection criteria (in conjunction with the :ref:`storm-diff`
  command).

The :ref:`storm-merge` command does not delete the forked view.

.. _ug_delete_fork:

Deleting a Forked View
~~~~~~~~~~~~~~~~~~~~~~

Some merge methods can automatically or optionally delete the associated view (see above).

The Storm :ref:`storm-view-del` command can be used to delete a forked view and its associated layer. The **delete icon**
in the Optic `View Task Bar`_ will also delete a forked view. The Optic `Admin Tool`_ can also be used to manage
views.

.. NOTE::
  
  Deleting a view will delete all unmerged changes in that view.


.. _ug_best_practices:

Best Practices
==============

- Use dedicated layers to segregate any data that should be visible to some users but not others.

- Use views to compose the sets of data (layers) that should be visible to particular users or groups.

- We **strongly encourage** forking views for all research, analysis, and testing, no matter how trivial or
  incidental. This applies equally to simple (one layer / one view) Cortexes as well as those with more complex
  view and layer architectures. In short, **do not work directly in your production data.** It is much easier to
  delete a forked view (or selectively merge "good" data and discard mistakes) than it is to undo errors in
  production.

- Consider your organization's strategy for reviewing and merging data. Depending on how you are using forked
  views (training, research, testing) determine what level of review, if any, is desired (or required) before
  merging data. Consider whether any procedures will be enforced by agreement/consensus or the use of permissions.

- Forked views provide "scratch space" for ongoing analysis, but can also create silos of data and analysis
  that are inaccessible to other analysts or groups. We encourage you to develop guidance around "what" should
  be merged and how often in order to balance the need to more fully develop research with the desire to share 
  data that is beneficial to other users.
  
  For example, analysts may enrich IOCs by pulling data from third party sources into Synapse. They may then
  review existing and new data to identify malware families or TTPs, or to cluster threat activity. Tags
  representing their assessments may be preliminary; in the meantime, the nodes created from third party data
  could be useful to others on their team. The :ref:`storm-merge` command could be used to merge new or updated
  nodes without merging any tags while analysis continues.

.. _`Best Practices for Views & Layers`: https://vertex.link/blogs/views-layers/
.. _`Traffic Light Protocol`: https://www.cisa.gov/news-events/news/traffic-light-protocol-tlp-definitions-and-usage
.. _`Optic UI`: https://synapse.docs.vertex.link/projects/optic/en/latest/index.html
.. _`View Selector`: https://synapse.docs.vertex.link/projects/optic/en/latest/user_interface/userguides/quick_tour.html#view-selector
.. _`View Task Bar`: https://synapse.docs.vertex.link/projects/optic/en/latest/user_interface/userguides/quick_tour.html#view-task-bar
.. _`User Guide`: https://synapse.docs.vertex.link/projects/optic/en/latest/user_interface/userguide.html
.. _`Storm Query Bar`: https://synapse.docs.vertex.link/projects/optic/en/latest/user_interface/userguides/quick_tour.html#storm-query-bar-query-mode-selector
.. _`Admin Tool`: https://synapse.docs.vertex.link/projects/optic/en/latest/user_interface/userguides/quick_tour.html#admin-tool
