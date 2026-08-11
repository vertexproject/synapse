<a id="deploymentguide"></a>


# Synapse Deployment Guide

## Introduction

This step-by-step guide will walk you through a production-ready Synapse deployment. Services will be configured to register with `AHA` for service discovery and to prepare for future devops tasks such as promoting a mirror to leader and provisioning future Synapse Advanced Power-Ups.

This guide will also walk you through creating a Cortex user and generating an API key, which is how users and client tools authenticate to the Cortex over HTTPS. AHA issues the TLS certificates the services use to authenticate to each other, so there are no service credentials for you to manage.

For the purposes of this guide, we will use `docker compose` as a light-weight orchestration mechanism. The steps, configurations, and volume mapping guidance given in this guide apply equally to other container orchestration mechanisms such as Kubernetes but for simplicity's sake, this guide will only cover `docker compose` based deployments.

> [!NOTE]
> Due to [known networking limitations of docker on Mac](https://docs.docker.com/desktop/mac/networking/#known-limitations-use-cases-and-workarounds) we do **not** support or recommend the use of Docker for Mac for testing or deploying production Synapse instances. Containers run within separate `docker compose` commands will not be able to reliably communicate with each other.

Synapse services **require persistent storage**. Each `docker` container expects persistent storage to be available within the directory `/vertex/storage` which should be a persistent mapped volume. Only one container may run from a given volume at a time.

> [!NOTE]
> To allow hosts to be provisioned on one system, this guide instructs you to disable HTTP API listening ports on all services other than the main Cortex. You may remove those configuration options if you are running on separate hosts or select alternate ports which do not conflict.

## Prepare your Hosts

Ensure that you have an updated install of [docker](https://docs.docker.com/engine/install/) and [docker-compose](https://docs.docker.com/compose/install/).

Synapse service docker containers run their service process as an unprivileged user named `synuser` with UID `999`. The containers start as `root` and their entrypoint prepares the mapped `/vertex/storage` volume, adjusts its ownership to `synuser`, and drops privileges to `synuser` before starting the service. You do not need to pre-create the storage volume or change its ownership.

Default kernel parameters on most Linux distributions are not optimized for database performance. We recommend adding the following lines to `/etc/sysctl.conf` on all systems being used to host Synapse services:

``` text
vm.swappiness=10
vm.dirty_expire_centisecs=20
vm.dirty_writeback_centisecs=20
```

See [Performance Tuning](devopsguide.md#devops-task-performance) for a list of additional tuning options.

We will use the directory `/srv/syn/` on the host systems as the base directory used to deploy the Synapse services. Each service will be deployed in separate `/srv/syn/<svcname>` directories. This directory can be changed to whatever you would like, and the services may be deployed to any host provided that the hosts can directly connect to each other. It is critical to performance that these storage volumes be low-latency. More latent storage mechanisms such as spinning disks, NFS, or EFS should be avoided!

We highly recommend that hosts used to run Synapse services deploy a log aggregation agent to make it easier to view the logs from the various containers in a single place.

When using AHA, you may run any of the **other** services on additional hosts as long as they can connect directly to the AHA service. You may also shutdown a service, move it's volume to a different host, and start it backup without changing anything.

<a id="deploy-aha-service"></a>


## Deploy AHA Service

The AHA service is used for service discovery and acts as a CA to issue host/user certificates used to link Synapse services. Other Synapse services will need to be able to resolve the IP address of the AHA service by name, so it is likely that you need to create a DNS A/AAAA record in your existing resolver. When you are using AHA, the only host that needs DNS or other external name resolution is the AHA service.

> [!NOTE]
> The AHA service resolver requires that registered services connect directly using IP addresses which must also be reachable to AHA clients. Using an `aha://` telepath URL requires direct routes to the service via its AHA facing network address. If you need to provide telepath access from outside the Synapse service network via any network address translation (NAT) method such as an inbound TCP proxy or docker/kubernetes port mapping, you will need to use `ssl://` based URIs and specify `hostname`, `certname`, and `ca` parameters which match the service's AHA registration info. You will also need to set the `telepath:port` config option (for example via `SYN_<SVC>_TELEPATH_PORT`) to bind the service to a static port that you can provide mappings to.

### Choose an AHA Network Name

Your AHA network name is separate from DNS and is used by services within the AHA service deployment. It is generally a good idea to chose a name that aligns with the use case for the Synapse deployment. For example, if you plan to have a test/dev/prod deployment, choosing a name like `prod.synapse` will make it clear which deployment is which. Changing this name later is difficult, so choose carefully! Throughout the examples, we will be using `prod.synapse` as the AHA network name which is also used as the common-name (CN) for the CA certificate.

### Choose a Provisioning Secret

Synapse services provision themselves automatically by sharing a secret with the AHA server. Choose a strong, random value to use as the provisioning secret and set it as `SYN_PROVISION_SECRET` on the AHA server and on every service you deploy. Services use it to discover AHA and provision themselves on their first boot. See [Service Provisioning](deploymentguide.md#deploy_provisioning) for details. Treat this value as sensitive and store it in your secrets manager. Throughout the examples, `<shared-secret>` refers to this value.

### Configure an AHA DNS Name

When choosing the DNS name for your AHA server, it is important to keep in mind that you may eventually want to deploy AHA mirrors for a high-availability deployment. Choosing a name like `000.aha.<dns-network>`, where `<dns-network>` is a DNS zone you control, will allow you to deploy mirrors with a consistent naming convention in the future. Once you have selected the DNS name for your AHA server, you will need to ensure that all deployed Synapse services will be able to resolve that name.

> [!NOTE]
> It is important to ensure that `000.aha.<dns-network>` is resolvable via DNS or docker container service name resolution from within the container environment!

### Deploy the AHA Container

Create the `/srv/syn/000.aha/docker-compose.yaml` file with contents:

``` text
services:
  000.aha:
    image: vertexproject/synapse-aha:v3.x.x
    network_mode: host
    restart: unless-stopped
    volumes:
        - ./storage:/vertex/storage
    environment:
        # disable HTTPS API for now to prevent port collisions
        - SYN_AHA_HTTPS_PORT=null
        - SYN_AHA_AHA_NETWORK=prod.synapse
        - SYN_AHA_DNS_NAME=000.aha.<dns-network>
        # shared secret which enables automatic service provisioning
        - SYN_PROVISION_SECRET=<shared-secret>
```

> [!NOTE]
> Don't forget to replace `<dns-network>` with your configured DNS suffix.

Start the container using `docker compose`:

``` text
docker compose --file /srv/syn/000.aha/docker-compose.yaml pull
docker compose --file /srv/syn/000.aha/docker-compose.yaml up -d
```

To view the container logs at any time you may run the following command on the *host* from the `/srv/syn/aha` directory:

``` text
docker compose logs -f
```

You may also execute a shell inside the container using `docker compose` from the `/srv/syn/aha` directory on the *host*. This will be necessary for some of the additional provisioning steps:

``` text
docker compose exec 000.aha /bin/bash
```

<a id="deploy_axon"></a>
<a id="deploy_aha_mirror"></a>


## Deploy AHA Mirrors (optional)

For high-availability deployments, you will want to deploy an AHA mirror or two. An AHA cannot resolve its own leader via `aha://` (it *is* the registry), so it enrolls as a clone of the current leader by setting `SYN_PROVISION_FOLLOWER`. On its first boot, the new AHA discovers the current leader over the network using the shared `SYN_PROVISION_SECRET` and clones from it automatically.

> [!NOTE]
> You can deploy AHA mirrors at any time in the future. Once a mirror is deployed, the updated list of AHA servers is distributed to every AHA enabled Synapse service in real time, so running services begin using the new server without a restart.

For this example, we will assume you chose a DNS name for your primary AHA server similar to the steps listed above. If so, you can simply replace `00` with sequential numbers and repeat this step to deploy however many AHA mirrors you deem appropriate.

By default, AHA uses port `27492` to listen for RPC connections from other Synapse services and port `27272` for the provisioning listener. The following example steps assume you will be running each AHA server on separate hosts or in a containerized deployment to avoid port collisions.

Create the `/srv/syn/001.aha/docker-compose.yaml` file with contents:

``` text
services:
  001.aha:
    image: vertexproject/synapse-aha:v3.x.x
    network_mode: host
    restart: unless-stopped
    volumes:
        - ./storage:/vertex/storage
    environment:
        # disable HTTPS API for now to prevent port collisions
        - SYN_AHA_HTTPS_PORT=null
        # the DNS name this AHA clone will be reachable at
        - SYN_AHA_DNS_NAME=001.aha.<dns-network>
        # shared secret which enables automatic provisioning discovery
        - SYN_PROVISION_SECRET=<shared-secret>
        # discover the current leader AHA and enroll as a clone of it
        - SYN_PROVISION_FOLLOWER=1
```

Start the container:

``` text
docker compose --file /srv/syn/001.aha/docker-compose.yaml pull
docker compose --file /srv/syn/001.aha/docker-compose.yaml up -d
```

> [!NOTE]
> An AHA clone assumes a leader already exists: it waits indefinitely for the leader to become reachable rather than ever starting empty, logging a warning roughly once a minute while the leader remains unresolved. Ensure the leader AHA is deployed so the clone can complete its bootstrap.

<a id="deploy_provisioning"></a>


## Service Provisioning

Synapse services provision themselves automatically using the shared `SYN_PROVISION_SECRET` you configured on the AHA server. When a service boots for the first time with `SYN_PROVISION_SECRET` set, it discovers the AHA server, provisions itself, retrieves its configuration, and generates its SSL certificates.

AHA names each service automatically from its service type. The first instance of a type becomes the leader and is named `000.<type>` (for example `000.cortex`); additional instances of the same type are named `NNN.<type>` (for example `001.cortex`) and provisioned as mirrors of the leader. The AHA name `<type>.<aha-network>` always resolves to the current leader.

> [!NOTE]
> The AHA service registers itself in its own service registry using this same convention: the leader is automatically named `000.aha` and each AHA clone is named `001.aha`, `002.aha`, and so on. The AHA service therefore appears in `getAhaSvcs` and the service list like any other service, and `aha.<aha-network>` resolves to the current leader AHA. This automatically assigned AHA *name* is independent of the `SYN_AHA_DNS_NAME` you choose for reachability; the two may differ. Services may connect to the AHA service using that name, such as `aha://aha...` or `aha://000.aha...`, the same way they connect to any other service in the registry.

Set `SYN_PROVISION_SECRET` to the same value on every service you deploy:

``` text
environment:
    - SYN_PROVISION_SECRET=<shared-secret>
```

> [!NOTE]
> Discovery requests are encrypted and authenticated with a key derived from `SYN_PROVISION_SECRET`; requests which fail to decrypt are silently ignored. Discovery uses multicast with a TTL of `1`, so services must share a subnet with the AHA server.

> [!NOTE]
> If a service does not share a broadcast domain (subnet) with the AHA server, set the optional environment variable `SYN_PROVISION_HOST` on the service to the AHA host name or address. The discovery request is then sent directly to that host rather than to the multicast group.

> [!NOTE]
> By default a fresh service of a type which has no registered leader boots as the first leader. Set the optional environment variable `SYN_PROVISION_FOLLOWER` on a service to instead assume a leader of its type already exists and deploy (clone) from it. Rather than ever booting fresh, the service waits indefinitely for a leader to register (logging a warning roughly once a minute until one does). This removes the ambiguity of the first-boot leadership race when a follower may start before the leader has registered.

## Deploy Axon Service

In the Synapse service architecture, an Axon provides a place to store arbitrary bytes/files as binary blobs and exposes APIs for streaming files in and out regardless of their size. Given sufficient file system size, an Axon can be used to efficiently store and retrieve very large files as well as a high number (easily billions) of files.

Create the `/srv/syn/000.axon/docker-compose.yaml` file with contents:

``` text
services:
  000.axon:
    image: vertexproject/synapse-axon:v3.x.x
    network_mode: host
    restart: unless-stopped
    volumes:
        - ./storage:/vertex/storage
    environment:
        # disable HTTPS API for now to prevent port collisions
        - SYN_AXON_HTTPS_PORT=null
        - SYN_PROVISION_SECRET=<shared-secret>
```

On its first boot the Axon discovers AHA and provisions itself, registering as `000.axon.prod.synapse`.

Start the container:

``` text
docker compose --file /srv/syn/000.axon/docker-compose.yaml pull
docker compose --file /srv/syn/000.axon/docker-compose.yaml up -d
```

## Deploy JSONStor Service

Create the `/srv/syn/000.jsonstor/docker-compose.yaml` file with contents:

``` text
services:
  000.jsonstor:
    image: vertexproject/synapse-jsonstor:v3.x.x
    network_mode: host
    restart: unless-stopped
    volumes:
        - ./storage:/vertex/storage
    environment:
        # disable HTTPS API for now to prevent port collisions
        - SYN_JSONSTOR_HTTPS_PORT=null
        - SYN_PROVISION_SECRET=<shared-secret>
```

On its first boot the JSONStor discovers AHA and provisions itself, registering as `000.jsonstor.prod.synapse`.

Start the container:

``` text
docker compose --file /srv/syn/000.jsonstor/docker-compose.yaml pull
docker compose --file /srv/syn/000.jsonstor/docker-compose.yaml up -d
```

## Deploy Cortex Service

Create the `/srv/syn/000.cortex/docker-compose.yaml` file with contents:

``` text
services:
  000.cortex:
    image: vertexproject/synapse-cortex:v3.x.x
    network_mode: host
    restart: unless-stopped
    volumes:
        - ./storage:/vertex/storage
    environment:
        # 4443 is the default HTTPS port
        - SYN_CORTEX_HTTPS_PORT=4443
        - SYN_PROVISION_SECRET=<shared-secret>
```

Unlike the other services, the Cortex leader keeps its HTTPS API listening port. This is the port the Storm CLI and any HTTP API client connect to, and [Create a Cortex User](deploymentguide.md#create-a-cortex-user) below uses it to get an interactive Storm shell. Because this container uses host networking, the API is reachable at port `4443` on the Cortex host.

On its first boot the Cortex discovers AHA and provisions itself, registering as `000.cortex.prod.synapse`.

> [!NOTE]
> Once the Cortex has joined the AHA network it automatically locates the Axon and JsonStor services by their service type. There is no need to configure telepath URLs to reach them.

Start the container:

``` text
docker compose --file /srv/syn/000.cortex/docker-compose.yaml pull
docker compose --file /srv/syn/000.cortex/docker-compose.yaml up -d
```

Remember, you can view the container logs in real-time using:

``` text
docker compose --file /srv/syn/000.cortex/docker-compose.yaml logs -f
```

<a id="deployment-guide-mirror"></a>


## Deploy Cortex Mirror (optional)

To deploy a Cortex mirror for high availability, deploy another Cortex service with the same `SYN_PROVISION_SECRET` and set `SYN_PROVISION_FOLLOWER` so it deploys as a mirror of the current leader. The new service assumes a Cortex leader already exists, waits for it to register, and clones from it rather than racing to become the first leader. AHA names the mirror `001.cortex` (and `002.cortex`, and so on for additional mirrors).

> [!NOTE]
> AHA determines a single leader per service type by tracking a *leadership term*. Mirrors automatically follow the current leader without any static upstream configuration, and follow the new leader after a promotion. A service which has been superseded by a forced promotion detects the divergence on startup and must be restored from a backup. The `parent` cell configuration option may be set to a telepath URL to explicitly override the leader determined by AHA, but this is rarely needed.

Create the `/srv/syn/001.cortex/docker-compose.yaml` file with contents:

``` text
services:
  001.cortex:
    image: vertexproject/synapse-cortex:v3.x.x
    network_mode: host
    restart: unless-stopped
    volumes:
        - ./storage:/vertex/storage
    environment:
        # disable HTTPS API for now to prevent port collisions
        - SYN_CORTEX_HTTPS_PORT=null
        - SYN_PROVISION_SECRET=<shared-secret>
        # deploy as a mirror of the current Cortex leader
        - SYN_PROVISION_FOLLOWER=1
```

Start the container:

``` text
docker compose --file /srv/syn/001.cortex/docker-compose.yaml pull
docker compose --file /srv/syn/001.cortex/docker-compose.yaml up -d
```

> [!NOTE]
> If you are deploying a mirror from an existing large Cortex, this startup may take a while to complete initialization.

<a id="enroll_cli_users"></a>


## Create a Cortex User

A Synapse user is generally synonymous with a user account on the Cortex. The steps in this section run from **inside the Cortex container**, which you may reach using `docker compose` on the *host*:

``` text
docker compose --file /srv/syn/000.cortex/docker-compose.yaml exec 000.cortex /bin/bash
```

To add a new admin user to the Cortex, run:

``` text
python -m synapse.tools.service.moduser --add --admin true visi
```

> [!NOTE]
> If you are a Synapse Enterprise customer, using the Synapse UI with SSO, the admin may now login to the Synapse UI. You may skip the following steps if the admin will not be using CLI tools to access the Cortex.

### Generate an API Key

The Cortex HTTP API endpoints used by the Storm CLI accept **API key authentication only**, so the new user will need an API key. An API key authenticates as the user who owns it and carries that user's full privileges. Run the following command from **inside the Cortex container** to create one for them:

``` text
python -m synapse.tools.service.apikey add --username visi storm-cli
```

You should see output that looks similar to this:

``` text
Successfully added API key with name=storm-cli.
Iden: 30fdf7f7f1571f0abd5a41f0e37cf37f
  API Key: XauBgBIUKgWJEm7VyvkmcuaGZbIl6M2nmueWjRtnYtA=
  Name: storm-cli
  Created: 2026-07-26T15:52:13.250342Z
  Updated: 2026-07-26T15:52:13.250342Z
```

The API key value is displayed only when the key is created, so record it and treat it as sensitive. To revoke a key, use the `Iden` value from the output above:

``` text
python -m synapse.tools.service.apikey del <iden>
```

See [API Key Support](httpapi.md#http-api-apikey) for additional details on user API keys.

> [!NOTE]
> Because a key carries the privileges of the user which owns it, a key created for an admin user grants full control of the Cortex. For routine CLI access, consider creating the key for a user with only the permissions that user needs rather than for an admin.

### Connect with the Storm CLI

The API key is provided as the user portion of an `https://` URL. Synapse is already installed inside the Cortex container, so you can get an interactive Storm shell there by connecting to `localhost` on the HTTPS port you configured when you [deployed it](deploymentguide.md#deploy-cortex-service):

``` text
python -m synapse.tools.storm --https-noverify https://<apikey>@localhost:4443/
```

Once connected, you will be presented with the Storm CLI command prompt:

``` text
storm>
```

> [!NOTE]
> The `--https-noverify` disables authentication of the server, so the client cannot tell the Cortex apart from anything else answering on that address and will send it the API key. It is used here because a Cortex with no installed certificate generates a self-signed certificate on first boot which clients cannot verify. Use it only over a network path you trust, such as this connection to `localhost` from within the container. Once you have installed a certificate the client can verify, drop the option, or use `--https-ca-dir <path>` to specify a directory of CA certificates used to verify the server. See [HTTPS Certificates](devopsguide.md#https-certificates) for instructions on installing your own certificate.

> [!NOTE]
> To run the Storm CLI from a workstation rather than from inside the container, install [Synapse](https://pypi.org/project/synapse/) from PyPI with `pip install synapse` and replace `localhost` with the host running the Cortex leader, which must be reachable on the Cortex HTTPS port. Install a certificate the client can verify before connecting that way, so that `--https-noverify` is not needed across the network.

See [Connecting with the HTTP API](userguides/syn_tools_storm.md#connecting-with-the-http-api) for the full set of Storm CLI options which apply to an `https://` connection.

Some Synapse CLI tools, such as `synapse.tools.cortex.csv` and `synapse.tools.axon.put`, connect over the Telepath API rather than HTTPS and require an `aha://` URL. Using those tools requires provisioning the user a TLS client certificate and enrolling them with AHA, which is a devops task rather than part of deploying the services. See [Managing Users and Roles](devopsguide.md#devops-task-users) in the Synapse Devops Guide for that walkthrough.

## Orchestration Examples

The walkthrough above deploys each service from its own `docker-compose.yaml` using host networking, which keeps each service independent and allows any of them to be moved to a different host later. The example below is an alternative way to orchestrate the same deployment.

### Docker Compose

The following single `docker-compose.yaml` deploys all four services onto one host using a user-defined bridge network. Because each service runs in its own container with its own network namespace, there are no port collisions between services and there is **no need to disable the internal HTTPS API ports** -- so the `SYN_<SVC>_HTTPS_PORT=null` settings used earlier are omitted here.

Because all of the services share the `synapse` bridge network, they resolve the AHA service by its container name and provision themselves using the shared `SYN_PROVISION_SECRET`. The Cortex publishes its HTTPS API on host port `4443` via a port mapping, so the Storm CLI reaches it at `4443` on the docker host just as it does in the walkthrough. Add a mapping for any other service you need to reach from outside the docker network.

Create a `docker-compose.yaml` file with contents:

``` text
x-vtx-constants:
  # Modify this secret value to a unique value for your deployment
  provision_secret: &provision_secret "<shared-secret>"

services:

  000.aha:
    image: vertexproject/synapse-aha:v3.x.x
    restart: unless-stopped
    networks: [ synapse ]
    volumes:
      - ./storage/000.aha:/vertex/storage
    environment:
      SYN_AHA_AHA_NETWORK: 'prod.synapse'
      SYN_AHA_DNS_NAME: '000.aha'
      SYN_PROVISION_SECRET: *provision_secret

  000.axon:
    image: vertexproject/synapse-axon:v3.x.x
    restart: unless-stopped
    networks: [ synapse ]
    volumes:
      - ./storage/000.axon:/vertex/storage
    environment:
      SYN_PROVISION_SECRET: *provision_secret

  000.jsonstor:
    image: vertexproject/synapse-jsonstor:v3.x.x
    restart: unless-stopped
    networks: [ synapse ]
    volumes:
      - ./storage/000.jsonstor:/vertex/storage
    environment:
      SYN_PROVISION_SECRET: *provision_secret

  000.cortex:
    image: vertexproject/synapse-cortex:v3.x.x
    restart: unless-stopped
    networks: [ synapse ]
    # publish host port 4443 to the Cortex HTTPS API listening port
    ports:
      - 4443:4443
    volumes:
      - ./storage/000.cortex:/vertex/storage
    environment:
      SYN_PROVISION_SECRET: *provision_secret

networks:
  synapse:
    driver: bridge
```

Start the whole deployment:

``` text
docker compose pull
docker compose up -d
```

> [!NOTE]
> The `SYN_AHA_DNS_NAME` value is the `000.aha` compose service name, which docker resolves for the other containers on the `synapse` network. Unlike the walkthrough above, this deployment needs no external DNS record. If you later move a service to another host, give AHA a DNS name which resolves from every host and update this value.

Once the services are running, follow [Create a Cortex User](deploymentguide.md#create-a-cortex-user) to add a user, generate an API key, and drop into the Storm CLI. Those steps apply to this deployment unchanged, except that the Cortex container is reached from the directory holding this `docker-compose.yaml`:

``` text
docker compose exec 000.cortex /bin/bash
```

## What's next?

See the [Synapse Admin Guide](adminguide.md#adminguide) for instructions on performing application administrator tasks. See the [Synapse Devops Guide](devopsguide.md#devopsguide) for instructions on performing various maintenance tasks on your deployment!
