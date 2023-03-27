.. toctree::
    :titlesonly:

.. _quickstart:

Getting Started
###############

So you've looked over our :ref:`intro` to Synapse and want to try it out! What do you do next?

Open-source Synapse and demo versions of commercial Synapse (Synapse Enterprise) are both available for
you to deploy and test. Both versions include the **same key features,** including Synapse's core
architecture and functionality, our extensive data model, and the full capabilities of the Storm query
language and libraries.

Open-source versions of Synapse provide a **command-line interface** (the `Storm CLI`_) to interact with
Synapse and its data. You can download :ref:`syn-open` from our Github repository or use :ref:`syn-quick` to
easily load a basic instance of Synapse.

Demo instances of Synapse Enterprise include Synapse's **web-based UI**, also known as **Optic.**

- If you want to get started with Synapse as quickly as possible, then a :ref:`syn-demo` or :ref:`syn-quick`
  are right for you.

- If you're interested in deploying your own test or production environment, then take a look at :ref:`syn-open`.

We'll explain each option in more detail below.

.. _syn-quick:

Synapse Quickstart
==================

**Synapse Quickstart** is a `Docker container`_ that includes everything you need to start using Synapse
and the Storm CLI right away. Because Synapse Quickstart is self-contained, you can easily install and
launch this basic Synapse instance on Linux, Windows, or MacOS.

You can find the instructions to download and install Synapse Quickstart here_.

**Synapse Quickstart** is best for:

- Individual users.
- Users who want to test Synapse without the need for a formal deployment.
- Users who are most interested in learning about Synapse's data and analytical models and the Storm query
  langauge (vs. deployment or development tasks).
- Users who want to test or use Synapse with proprietary or sensitive data that must be hosted locally.

Synapse Quickstart is **not** pre-loaded with any data.

.. _syn-open:

Open-Source Synapse
===================

The full open-source version of Synapse is available from our `Github repository`_. Instructions for
deploying a test or production envirionment are available in the :ref:`deploymentguide`.

**Open-source Synapse** is best for:

- Users who want to work with or try out a full version of Synapse.
- Supporting multiple users and / or networked users, including the (optional) ability to configure 
  roles and permissions.
- Developers who want to build on or integrate with Synapse.
- Users who want to test or use Synapse with proprietary or sensitive data that must be hosted locally.

Open-source Synapse is **not** pre-loaded with any data. However, some of Synapse's `Power-Ups`_ are
available as open source and can help you automate adding data to Synapse:

- `Synapse-MISP`_
- `Synapse-MITRE-ATTACK`_
- `Synapse-TOR`_

.. _syn-demo:

Synapse Demo Instance
=====================

Commercial Synapse (Synapse Enterprise) and our commercial demo instances include the web-based Synapse
UI (Optic). **Demo instances** are **cloud-hosted,** so there is nothing for you configure or deploy to
get started - all you need is a web browser (we recommend Chrome).

You can request a demo instance from our `web site`_.

.. NOTE::
  
  Synapse Enterprise can be deployed either on premises or in the cloud. Only the demo instances are
  cloud-only.

Demo instances provide access to all of Synapse's `Rapid Power-Ups`_, both open-source and commercial.
Any Rapid Power-Up can be installed in your demo instance (although some Power-Ups may reqiure API keys
and / or paid subscriptions from the associated third-party).

Demo instances are updated automatically each week with any new releases of Synapse and Optic. New or
updated Rapid Power-Ups are available upon release and can be updated manually from the Power-Ups Tool.

In addition, demo instances are **pre-loaded** with sample data and tags (just under 300,000 objects).
You can explore the data on your own, or use our `APT1 Scavenger Hunt`_ as a guided way to learn
about the Synapse UI and Storm query language.

A **demo instance** is best for:

- Users who want to test all of Synapse's features and capabilities, including those only available
  with Synapse Enterprise.
- Supporting multiple users and / or networked users, including the (optional) ability to configure 
  roles and permissions.
- Simple deployment - no hardware/software needed (other than a web browser).
- Developers who want insight into developing Power-Ups or Workflows.
- Users and developers who want access to the "latest and greatest" releases and features during testing.
- Users who want to take advantage of all of Synapse's features (including built-in Help for Synapse's
  data model, Storm auto-complete, etc.) while learning - even if you ultimately deploy an open-source
  version.

.. NOTE::
  
  Because demo instances are cloud-based, they are **not suitable** for hosting any sensitive or
  proprietary data.


.. _Index:              ../index.html

.. _`Storm CLI`: https://synapse.docs.vertex.link/en/latest/synapse/userguides/syn_tools_storm.html

.. _`Docker container`: https://www.docker.com/resources/what-container/
.. _here: https://github.com/vertexproject/synapse-quickstart

.. _`Github repository`: https://github.com/vertexproject/synapse
.. _Power-Ups: https://synapse.docs.vertex.link/en/latest/synapse/power_ups.html
.. _Synapse-MISP: https://synapse.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-misp/index.html
.. _Synapse-MITRE-ATTACK: https://synapse.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-mitre-attack/index.html
.. _Synapse-TOR: https://synapse.docs.vertex.link/projects/rapid-powerups/en/latest/storm-packages/synapse-tor/index.html

.. _`web site`: https://vertex.link/request-a-demo
.. _`Rapid Power-Ups`: https://synapse.docs.vertex.link/en/latest/synapse/power_ups.html#rapid-power-ups
.. _`APT1 Scavenger Hunt`: https://v.vtx.lk/scavenger-hunt