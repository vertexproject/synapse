.. _orch-kubernetes:

Kubernetes
==========

A popular option for Orchestration is Kubernetes. Kubernetes is an open-source system for automating the deployment,
scaling and managemetn of containerized applications. We provide a examples that you can use to quickly get started
using Kubernetes to orchestrate your Synapse deployment.  These examples include an Aha cell, a Axon, a Cortex,
the Maxmind connector, and the Optic UI.

Since all Telepath services connect via Aha, this allows for easy lookup of services via Aha. This allows for users to
ignore most application awareness of port numbers. For example, the Maxmind connector can easily be be added to the
Cortex via ``service.add maxmind aha://root:demo@maxmind.aha.demo.net``.

The Optic deployment uses a ``initContainers`` container to copy the TLS certificates into the service directory for
Optic. The Traefik ``IngressRouteTCP`` directs all TLS traffic to the service to the Optic service. Since the TLS
certificates have been put into the Cell directory for Optic, and the ``IngressRouteTCP`` acts a TLS passthrough,
users are using TLS end to end to connect to Optic.

Passwords used for doing inter-service communications are stored in Kubernetes Secrets and are interpolated from
environment variables form Telepath URLs when needed. To keep these examples from being too large, passwords are shared
between services.

The following examples make the following assumptions:

1. A PersistentVolumeClaim provider is available. These examples use Digital Ocean block storage.
2. Traefik is available to provide ``IngressRouteTCP`` providers. The examples here are treated as TLS passthrough
   examples with a default websecure ``entryPoint``, which means the service must provide its own TLS endpoint. Further
   Traefik configuration for providing TLS termination and connecting to backend services over TLS is beyond the scope
   of this documentation.
3. There is a ``cert-manager`` Certificate provider available to generate a Let's Encrypt TLS certificate.
4. There is a secret ``regcred`` available which can be used to pull a Docker pull secret that can access the private
   images.

Single Pod
----------

This single pod example can be readily used, provided that the assumptions noted earlier are accounted for. The DNS name
for the Certificate, IngressRouteTCP, and SYN_OPTIC_NETLOC value would need to be updated to account for your own DNS
settings.

.. literalinclude:: demo-aha-onepod.yaml
    :language: yaml
    :lines: 1-284

Multiple Pods
-------------

Each service can also be broken into separate pods. This example is broken down across three sections, a Cortex, an Axon,
and other services. This lines up with three distinct Persistent Volume Claims being made to host the data for the
services. This isolates the storage between the Cortex, Axon and other services. Each service is deployed into its own
pods; and each Telepath-capable service reports itself into an Aha server.

First, the shared Secret.

.. literalinclude:: demo-aha-pods.yaml
    :language: yaml
    :lines: 17-27

The Cortex is straightforward. It uses a PVC, it is configured via environment variables, and has its Telepath
port exposed as a service that other Pods can connect to. This example also adds a ``startupProbe`` and
``livenessProbe`` added to check the Cortex (and other services). This allows us to know when the service is available;
since the Cortex may take some time to load all of the memory maps associated with layer data.

.. literalinclude:: demo-aha-pods.yaml
    :language: yaml
    :lines: 37-147

The Axon is very similar to the Cortex.

.. literalinclude:: demo-aha-pods.yaml
    :language: yaml
    :lines: 155-253

The last set of components shown here is the most complex. It includes the Aha server, the Maxmind connector, and the
Optic UI.

.. literalinclude:: demo-aha-pods.yaml
    :language: yaml
    :lines: 273-607
