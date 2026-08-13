```mdtoc

```

<a id="getting_started"></a>


# Getting Started

Now that you have looked over the [Introduction](intro.md) to Synapse, you'd like to try it out! What do you do next?

There are several ways for you to explore Synapse and its features, depending on your needs. Each option is summarized here and described in more detail below.

## [Demo Instance](getting_started.md#syn-demo)
- Cloud hosted, personal instance of [Synapse Enterprise](https://vertex.link/synapse)
- Admin-level access to your instance
- Access via the web-based [Optic](/docs/synapse-enterprise-optic/latest/index.md)
- Access to all [Rapid Power-Ups](power_ups.md#rapid-power-ups)
- Access to most [Advanced Power-Ups](power_ups.md#advanced-powerups)
- Sample data
- Data sets for the [APT1 Scavenger Hunt](https://v.vtx.lk/apt1hunt) and [Synapse Bootcamp](https://vertex.link/training/bootcamp)

## [Vertex Intel-Sharing Instance (VISI)](getting_started.md#syn-visi)
- Cloud-hosted, community instance of [Synapse Enterprise](https://vertex.link/synapse)
- Access via the web-based [Optic](/docs/synapse-enterprise-optic/latest/index.md) user interface
- User account to explore or contribute to the community instance
- Access to all [Rapid Power-Ups](power_ups.md#rapid-power-ups)
- Access to most [Advanced Power-Ups](power_ups.md#advanced-powerups)
- Sample data
- Community-generated data and analysis
- Training materials hosted in the Synapse Learning Tool

## [Open-Source Synapse](getting_started.md#syn-open)
- Publicly available source code hosted on [Github](https://github.com/vertexproject/synapse)
- Access via the [Storm CLI](userguides/syn_tools_storm.md)
- Access to open-source [Rapid Power-Ups](power_ups.md#rapid-power-ups)

## [Synapse Quickstart](getting_started.md#syn-quick)
- Pre-configured [Docker container](https://www.docker.com/resources/what-container/) for open-source Synapse |
- Access via the [Storm CLI](userguides/syn_tools_storm.md)

> [!TIP]
> Both **Synapse Enterprise** and **open-source Synapse** share the same key features, including Synapse's core architecture and functionality, our extensive data model, and the full capability of the Storm query language and libraries.
>
> **Synapse Enterprise** also includes the web-based Optic UI and access to the full range of Synapse [Power-Ups](./power_ups.md).

<a id="syn-demo"></a>


## Demo Instance

You can [request a demo instance](https://vertex.link/request-a-demo) to receive a fully-functional version of [Synapse Enterprise](https://vertex.link/synapse), including the [Optic](/docs/synapse-enterprise-optic/latest/index.md) web-based user interface (UI).

Demo instances are **cloud-hosted,** so there is nothing for you to configure or deploy to get started - all you need is a web browser (we recommend Chrome or a Chromium-based browser).

> [!NOTE]
> Synapse Enterprise can be deployed either on premises or in the cloud. The demo instances are cloud-only.

Demo instances provide access to all of Synapse's [Rapid Power-Ups](power_ups.md#rapid-power-ups) (both open-source and commercial) and a subset of [Advanced Power-Ups](power_ups.md#advanced-powerups). Any available Power-Up can be installed in your demo instance, although some Power-Ups may require an API key and / or paid subscriptions from the associated third-party.

Demo instances are updated **automatically** each week with any new releases of Synapse and Optic. New or updated Power-Ups are available upon release and can be updated **manually** from the Power-Ups Tool.

In addition, demo instances are **pre-loaded** with sample data and tags (approximately 1.2 million objects). You can:

- explore the data on your own;
- use our [APT1 Scavenger Hunt](https://v.vtx.lk/apt1hunt) as a guided way to learn about Synapse and the Storm query language; or
- use the [Synapse Bootcamp](https://vertex.link/training/bootcamp) data set to work through our self-paced Synapse training course.

A **demo instance** is best for:

- Users who want to test all of Synapse's features and capabilities, including those only available with Synapse Enterprise.
- Testing with or supporting multiple users, including the (optional) ability to configure roles and permissions.
- Simple deployment - no hardware/software needed (other than a web browser).
- Developers who want insight into developing Power-Ups or Workflows.
- Users and developers who want access to the "latest and greatest" releases and features during testing.
- Users who want to take advantage of all of Synapse's features (including built-in Help for Synapse's data model, Storm auto-complete, etc.) while learning - even if you ultimately deploy an open-source version.

> [!NOTE]
> Because demo instances are cloud-based, they are **not suitable** for hosting any sensitive or proprietary data.

<a id="syn-visi"></a>


## Vertex Intel-Sharing Synapse Instance (VISI)

The Vertex Project hosts a cloud-based, community instance of Synapse - the Vertex Intel-Sharing Synapse Instance, or [VISI](https://vertex.link/blogs/intel-sharing-faq/) for short. Any community member can [request access](https://vertex.link/intel-sharing) to the VISI to browse (or contribute to) the available data and analysis.

The VISI includes the full set of Synapse [Power-Ups](./power_ups.md). In order to use certain Power-Ups, you may need "contributor" permissions and / or to provide a personal API key (if required by a third-party data source).

In addition, the VISI uses the **Learning Tool** (part of Synapse Enterprise) to host some of the Challenges and Workshops presented by The Vertex Project at conferences such as [PIVOTcon](https://vertex.link/blogs/threat-clustering-challenge/) and [CYBERWARCON](https://vertex.link/blogs/insider-threat-challenge/). This scenario-based content can be taken on demand and provides an engaging and interactive way to learn about Synapse while honing your investigation and analysis skills.

The **VISI** is best for:

- Individual users.
- Users who want to examine a larger data set (compared to the default data included in a [Demo Instance](getting_started.md#syn-demo)).
- Users who want to explore the content available in the Synapse **Learning Tool**.

<a id="syn-open"></a>


## Open-Source Synapse

The full open-source version of Synapse is available from our [Github](https://github.com/vertexproject/synapse) repository. Instructions for deploying a test or production environment are available in the [Synapse Deployment Guide](deploymentguide.md#deploymentguide).

**Open-source Synapse** is best for:

- Users who want to work with or try out a full version of Synapse.
- Supporting multiple users and / or networked users, including the (optional) ability to configure roles and permissions.
- Developers who want to build on or integrate with Synapse.
- Users who are not concerned with access to the Synapse UI (Optic) or UI-based features.
- Users who want to test or use Synapse with proprietary or sensitive data that must be hosted locally.

Open-source Synapse is **not** pre-loaded with any data. However, some of Synapse's [rapid Power-Ups](power_ups.md#rapid-power-ups) are available as open source and can help you automate adding data to Synapse:

- Synapse MISP
- Synapse MITRE-ATTACK
- Synapse TOR

<a id="syn-quick"></a>


## Synapse Quickstart

**Synapse Quickstart** is a [Docker container](https://www.docker.com/resources/what-container/) that includes everything you need to start using Synapse and the [Storm CLI](./userguides/syn_tools_storm.md) right away. Because Synapse Quickstart is self-contained, you can easily install and launch this basic Synapse instance on Linux, Windows, or MacOS.

You can find the instructions to download and install Synapse Quickstart [here](https://github.com/vertexproject/synapse-quickstart).

**Synapse Quickstart** is best for:

- Individual users.
- Users who want to test Synapse without the need for a formal deployment.
- Users who are most interested in learning about Synapse's data and analytical models and the Storm query language (vs. deployment or development tasks).
- Users who are not concerned with access to the Synapse UI (Optic) or UI-based features.
- Users who want to test or use Synapse with proprietary or sensitive data that must be hosted locally.

Synapse Quickstart is **not** pre-loaded with any data.
