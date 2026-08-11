import synapse.exc as s_exc

import synapse.lib.cluster as s_cluster

import synapse.tests.utils as s_test

class ClusterLibTest(s_test.SynTest):

    async def test_lib_cluster_requires_ctor(self):

        # getCluster() has no built-in registry of service ctors -- a service
        # entry with none supplied is rejected rather than silently falling
        # through to some default.
        with self.raises(s_exc.BadArg):
            async with s_cluster.getCluster({'newpservice': {}}):
                pass  # pragma: no cover

    async def test_lib_cluster_default_svcs(self):

        # a bare call defaults to a single cortex, with its axon/jsonstor
        # peers implicitly added ( the base synapse ctors, since neither was
        # given its own envelope ).
        async with s_cluster.getCluster() as clus:
            self.nn(clus.cortex)
            self.nn(clus.axon)
            self.nn(clus.jsonstor)
