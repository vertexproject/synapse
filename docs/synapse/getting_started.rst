.. toctree::
    :titlesonly:

.. _getting_started:

Getting Started
###############

Now that you have looked over the :ref:`intro` to Synapse, you'd like to try it out! What do you do next?

There are several ways for you to explore Synapse and its features, depending on your needs. Each option is
summarized here and described in more detail below.

+------------------------------+--------------------------------------------------------------------+
|  **Option**                  |  **Description**                                                   |
+------------------------------+--------------------------------------------------------------------+
| :ref:`syn-demo`              | - Cloud-hosted, personal instance of `Synapse Enterprise`_         |
|                              | - Admin-level access to your instance                              |
|                              | - Access via the web-based `Optic`_ user interface                 |
|                              | - Access to all `Rapid Power-Ups`_                                 |
|                              | - Access to most `Advanced Power-Ups`_                             |
|                              | - Sample data                                                      |
|                              | - Data sets for the `APT1 Scavenger Hunt`_ and `Synapse Bootcamp`_ |  
+------------------------------+--------------------------------------------------------------------+
| :ref:`syn-visi`              | - Cloud-hosted, community instance of `Synapse Enterprise`_        |
|                              | - Access via the web-based `Optic`_ user interface                 |
|                              | - User account to explore or contribute to the community instance  |
|                              | - Access to all `Rapid Power-Ups`_                                 |
|                              | - Access to most `Advanced Power-Ups`_                             |
|                              | - Sample data                                                      |
|                              | - Community-generated data and analysis                            |
|                              | - Training materials hosted in the Synapse **Learning Tool**       |
+------------------------------+--------------------------------------------------------------------+
| :ref:`syn-open`              | - Publicly available source code hosted on `Github`_               |
|                              | - Access via the `Storm CLI`_                                      |
|                              | - Access to open-source `Rapid Power-Ups`_                         |
+------------------------------+--------------------------------------------------------------------+
| :ref:`syn-quick`             | - Pre-configured `Docker container`_ for open-source Synapse       |
|                              | - Access via the `Storm CLI`_                                      |
+------------------------------+--------------------------------------------------------------------+

.. TIP::
  
  Both **Synapse Enterprise** and **open-source Synapse** share the same key features, including Synapse's
  core architecture and functionality, our extensive data model, and the full capability of the Storm query
  language and libraries.
  
  **Synapse Enterprise** also includes the web-based Optic UI and access to the full range of Synapse `Power-Ups`_.

.. _syn-demo:

Demo Instance
=============

You can `request a demo instance`_ to receive a fully-functional version of `Synapse Enterprise`_, including
the `Optic`_ web-based user interface (UI).

Demo instances are **cloud-hosted,** so there is nothing for you to configure or deploy to get started - all you
need is a web browser (we recommend Chrome or a Chromium-based browser).

.. NOTE::
  
  Synapse Enterprise can be deployed either on premises or in the cloud. The demo instances are cloud-only.

Demo instances provide access to all of Synapse's `Rapid Power-Ups`_ (both open-source and commercial) and a
subset of `Advanced Power-Ups`_. Any available Power-Up can be installed in your demo instance, although some
Power-Ups may require an API key and / or paid subscriptions from the associated third-party.

Demo instances are updated **automatically** each week with any new releases of Synapse and Optic. New or
updated Power-Ups are available upon release and can be updated **manually** from the Power-Ups Tool.

In addition, demo instances are **pre-loaded** with sample data and tags (approximately 1.2 million objects).
You can:

- explore the data on your own;
- use our `APT1 Scavenger Hunt`_ as a guided way to learn about Synapse and the Storm query language; or
- use the `Synapse Bootcamp`_ data set to work through our self-paced Synapse training course.

A **demo instance** is best for:

- Users who want to test all of Synapse's features and capabilities, including those only available
  with Synapse Enterprise.
- Testing with or supporting multiple users, including the (optional) ability to configure roles and
  permissions.
- Simple deployment - no hardware/software needed (other than a web browser).
- Developers who want insight into developing Power-Ups or Workflows.
- Users and developers who want access to the "latest and greatest" releases and features during testing.
- Users who want to take advantage of all of Synapse's features (including built-in Help for Synapse's
  data model, Storm auto-complete, etc.) while learning - even if you ultimately deploy an open-source
  version.

.. NOTE::
  
  Because demo instances are cloud-based, they are **not suitable** for hosting any sensitive or
  proprietary data.

.. _syn-visi:

Vertex Intel-Sharing Synapse Instance (VISI)
============================================

The Vertex Project hosts a cloud-based, community instance of Synapse - the Vertex Intel-Sharing Synapse
Instance, or `VISI`_ for short. Any community member can `request access`_ to the VISI to browse (or contribute
to) the available data and analysis.

The VISI includes the full set of Synapse `Power-Ups`_. In order to use certain Power-Ups, you may need
"contributor" permissions and / or to provide a personal API key (if required by a third-party data source).

In addition, the VISI uses the **Learning Tool** (part of Synapse Enterprise) to host some of the Challenges
and Workshops presented by The Vertex Project at conferences such as `PIVOTcon`_ and `CYBERWARCON`_. This
scenario-based content can be taken on demand and provides an engaging and interactive way to learn about Synapse
while honing your investigation and analysis skills.

The **VISI** is best for:

- Individual users.
- Users who want to examine a larger data set (compared to the default data included in a :ref:`syn-demo`).
- Users who want to explore the content available in the Synapse **Learning Tool**.

.. _syn-open:

Open-Source Synapse
===================

The full open-source version of Synapse is available from our `Github`_ repository. Instructions for
deploying a test or production environment are available in the :ref:`deploymentguide`.

**Open-source Synapse** is best for:

- Users who want to work with or try out a full version of Synapse.
- Supporting multiple users and / or networked users, including the (optional) ability to configure 
  roles and permissions.
- Developers who want to build on or integrate with Synapse.
- Users who are not concerned with access to the Synapse UI (Optic) or UI-based features.
- Users who want to test or use Synapse with proprietary or sensitive data that must be hosted locally.

Open-source Synapse is **not** pre-loaded with any data. However, some of Synapse's `rapid Power-Ups`_ are
available as open source and can help you automate adding data to Synapse:

- Synapse MISP
- Synapse MITRE-ATTACK
- Synapse TOR

.. _syn-quick:

Synapse Quickstart
==================

**Synapse Quickstart** is a `Docker container`_ that includes everything you need to start using Synapse
and the `Storm CLI`_ right away. Because Synapse Quickstart is self-contained, you can easily install and
launch this basic Synapse instance on Linux, Windows, or MacOS.

You can find the instructions to download and install Synapse Quickstart here_.

**Synapse Quickstart** is best for:

- Individual users.
- Users who want to test Synapse without the need for a formal deployment.
- Users who are most interested in learning about Synapse's data and analytical models and the Storm query
  language (vs. deployment or development tasks).
- Users who are not concerned with access to the Synapse UI (Optic) or UI-based features.
- Users who want to test or use Synapse with proprietary or sensitive data that must be hosted locally.

Synapse Quickstart is **not** pre-loaded with any data.

.. _Index:                     ../index.html
.. _`Synapse Enterprise`:      https://vertex.link/synapse
.. _`Optic`:                   https://synapse.docs.vertex.link/projects/optic/en/latest/  
.. _`Rapid Power-Ups`:         ./power_ups.html#rapid-power-ups
.. _`Advanced Power-Ups`:      ./power_ups.html#advanced-power-ups
.. _`Power-Ups`:               ./power_ups.html
.. _`APT1 Scavenger Hunt`:     https://v.vtx.lk/apt1hunt
.. _`Synapse Bootcamp`:        https://vertex.link/training/bootcamp
.. _`VISI`:                    https://vertex.link/blogs/intel-sharing-faq/  
.. _`PIVOTcon`:                https://vertex.link/blogs/threat-clustering-challenge/
.. _`CYBERWARCON`:             https://vertex.link/blogs/insider-threat-challenge/
.. _`Github`:                  https://github.com/vertexproject/synapse
.. _`Storm CLI`:               ./userguides/syn_tools_storm.html
.. _`Docker container`:        https://www.docker.com/resources/what-container/
.. _`request a demo instance`: https://vertex.link/request-a-demo
.. _`request access`:          https://vertex.link/intel-sharing
.. _`here`:                    https://github.com/vertexproject/synapse-quickstart
