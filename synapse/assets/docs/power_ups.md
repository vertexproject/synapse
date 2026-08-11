<a id="synapse_powerups"></a>


# Synapse Power-Ups

Power-Ups are part of [The Vertex Project](https://vertex.link)'s commercial offering, Synapse Enterprise. Synapse Enterprise is an on-premises solution that includes [Optic (the Synapse UI)](/docs/synapse-enterprise-optic/latest/index.md) and all of the Power-Ups. The license includes unlimited users and does not limit the amount of data or number of instances you deploy. We take a white-glove approach to each deployment where we're with you every step of the way from planning deployment sizes to helping to train your analysts.

Feel free to [contact us](https://vertex.link/contact-us) or [request a demo instance](https://vertex.link/request-a-demo).

Power-Ups provide specific add-on capabilities to Synapse via Storm Packages and Services. For example, Power-Ups may provide connectivity to external databases, third-party data sources, or enable functionality such as the ability to manage YARA rules, scans, and matches.

For an introduction to Power-Ups from our analysts and seeing them in use, see the following video introducing them:

<iframe width="560" height="315" src="https://www.youtube.com/embed/eb6wEYGRTyY" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

The Vertex Project is constantly releasing new Power-Ups and expanding features of existing Power-Ups. If you join the `#synapse-releases` channel in Synapse [Slack](https://v.vtx.lk/slack), you can get realtime notices of these updates!

<a id="rapid-powerups"></a>


## Rapid Power-Ups

Rapid Power-Ups are delivered to a Cortex as Storm packages directly, without requiring any additional containers to be deployed. This allows users to rapidly expand the power of their Synapse deployments without needing to engage with additional operations teams in their environments. For an introduction to Rapid Power-Ups and some information about publicly available Power-Ups, see the following [blog](https://vertex.link/blogs/synapse-power-ups/) post.

### Getting Started with Rapid Power-Ups

Vertex maintains a package repository which allows for loading public and private packages.

If you are a [Synapse User Interface](user_interface.md#synapse-ui) user, you can navigate to the **Power-Ups Tool** to register your Cortex and configure packages.

Alternatively, one can use the [storm](userguides/syn_tools_storm.md#syn-tools-storm) tool to get started with Rapid Power-Ups in their Cortex.

See our [blog article](https://vertex.link/blogs/synapse-power-ups/) for a step-by step guide to registering your Cortex to install the free `synapse-misp`, `synapse-mitre-attack`, and `synapse-tor` Power-Ups.

<a id="advanced-powerups"></a>


## Advanced Power-Ups

Advanced Power-Ups are enhancements to a Cortex which require the deployment of additional containers in order to run their services.

Documentation for specific Advanced Power-Ups can be found here:

- [Synapse Enterprise AHA](/docs/synapse-enterprise/latest/deploymentguide.md#deploy-aha-service)
- [Synapse Enterprise (Cloud) Axon](/docs/synapse-enterprise/latest/deploymentguide.md#deploy-axon-service)
- [Synapse Backup](/docs/synapse-enterprise-backup/latest/)
- [Synapse Fileparser](/docs/synapse-enterprise-fileparser/latest/)
- [Synapse Maxmind](/docs/synapse-enterprise-maxmind/latest/)
- [Synapse Metrics](/docs/synapse-enterprise-metrics/latest/)
- [Synapse Playwright](/docs/synapse-enterprise-playwright/latest/)
- [Synapse Search](/docs/synapse-enterprise-search/latest/)
- [Synapse Swarm](/docs/synapse-enterprise-swarm/latest/)
