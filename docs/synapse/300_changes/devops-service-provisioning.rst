.. _vtx_300_devops-service-provisioning:

Automatic Service Provisioning (SYN_PROVISION_SECRET)
=====================================================

What changed
    Synapse 3.0.0 adds automatic service provisioning. When the ``SYN_PROVISION_SECRET``
    environment variable is set to a shared secret on the AHA server and on a service, the
    service discovers AHA over the network on its first boot, provisions itself, and generates
    its certificates -- with no operator step to generate and copy a one-time use provisioning
    URL. AHA names the service automatically from its service type: the first instance of a type
    becomes the leader ``000.<type>`` and additional instances become mirrors ``NNN.<type>``.

    Setting ``SYN_PROVISION_SECRET`` declares that AHA must provision the service. If AHA is not
    yet reachable when the service boots -- for example during an orchestrated startup where
    containers come up in an arbitrary order -- the service retries discovery indefinitely,
    logging a periodic warning, rather than booting un-provisioned.

    In 2.x, provisioning each service required running
    ``python -m synapse.tools.aha.provision.service <name>`` on the AHA server and pasting the
    resulting single-use ``ssl://...`` URL into the service's ``aha:provision`` configuration.

Why
    Sharing a single secret removes the per-service manual step and makes deployments (and
    autoscaling) reproducible without generating and handling one-time use URLs.

What you need to do
    Nothing is required -- URL-based provisioning via ``aha:provision`` still works exactly as
    before. To adopt automatic provisioning, set the same ``SYN_PROVISION_SECRET`` on the AHA
    server and on each service, and omit the per-service ``aha:provision`` URL. If a service does
    not share a broadcast domain (subnet) with AHA, also set ``SYN_PROVISION_HOST`` on the service
    to the AHA host/address so the discovery request is unicast rather than multicast.

    .. code-block:: yaml

        # 3.x -- automatic provisioning
        environment:
            - SYN_PROVISION_SECRET=<shared-secret>

    To force an inaugural service to deploy as a follower of an existing leader (assume a leader
    of its type exists and clone from it rather than ever booting fresh as the first leader), also
    set ``SYN_PROVISION_FOLLOWER``. This also lets an AHA server enroll itself as a clone
    automatically -- set ``SYN_PROVISION_FOLLOWER`` and ``dns:name`` on the new AHA and omit the
    manual ``SYN_AHA_CLONE`` URL.

    See :ref:`deploy_provisioning` in the deployment guide for the full walkthrough.
