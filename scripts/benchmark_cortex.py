import gc
import time
import random
import asyncio
import contextlib
import collections
import logging

logger = logging.getLogger(__name__)

from typing import List, Dict, Optional, AsyncIterator, Tuple, Any, TYPE_CHECKING
if TYPE_CHECKING:
    import synapse.telepath as s_telepath

import synapse.common as s_common
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

s_common.setlogging(logger, 'ERROR')

# Construct existing cortex
# Copy cortex directory to a new one

# inet:ipv4 -> inet:dns:a -> inet:fqdn

# Pivot that returns no nodes
  # Pivot that returns a lot of nodes

# Lift by tag
# Lift by buid
# Lift by primary prop prefix
  # No nodes
  # 1 node
  # Lots of nodes

# Lift by secondary prop

# Future plans:
# Benchmark multi-layer
# Benchmark remote layer
# Benchmark parallel

async def acount(genr):
    count = 0
    async for _ in genr:
        count += 1
    return count

class TestData:
    def __init__(self, num_records):
        # inet:ipv4 -> inet:dns:a -> inet:fqdn
        # N ipv4s
        # For each even ipv4 record, make an inet:dns:a record that points to <ipaddress>.website, if it is
        # divisible by ten also make a inet:dns:a that points to blackhole.website
        self.nrecs = num_records
        random.seed(4)  # 4 chosen by fair dice roll.  Guaranteed to be random
        ips = list(range(num_records))
        random.shuffle(ips)
        dnsas = [(f'{ip}.website', ip) for ip in ips if ip % 2 == 0]
        dnsas += [('blackhole.website', ip) for ip in ips if ip % 10 == 0]
        random.shuffle(dnsas)
        self.ips = [(('inet:ipv4', ip), {'tags': {'odd' if ip % 2 else 'even': (None, None)}}) for ip in ips]
        self.dnsas = [(('inet:dns:a', dnsas), {}) for dnsas in dnsas]

        self.names2 = ['f{hex(ip)}.ninja' for ip in ips]


syntest = s_t_utils.SynTest()

class Benchmarker:
    NUM_ITERS = 6

    def __init__(self, config, num_nodes):
        self.measurements = collections.defaultdict(list)
        self.coreconfig = config
        self.num_nodes = num_nodes

    def report(self, configname):
        for name, measurements in self.measurements.items():
            ms = ', '.join(f'{m:0.3}' for m in measurements)
            print(f'{name:17}: {ms}')

    async def _loadtestdata(self, core, testdata):
        await s_common.aspin(core.addNodes(testdata.ips))
        await s_common.aspin(core.addNodes(testdata.dnsas))

    @contextlib.asynccontextmanager
    async def getCortexAndProxy(self, dirn) -> AsyncIterator[Tuple[Any, Any]]:
        async with syntest.getTestCoreAndProxy(conf=self.coreconfig, dirn=dirn) as (core, prox):
            yield core, prox

    async def doNothing(self, prox: 's_telepath.Client') -> None:
        count = await acount(prox.eval(''))
        assert count == 0

    async def doSimpleCount(self, prox: 's_telepath.Client') -> None:
        count = await acount(prox.eval('inet:ipv4 | count | spin'))
        assert count == 0

    async def doSimpleLift(self, prox: 's_telepath.Client') -> None:
        count = await acount(prox.eval('inet:dns:a'))
        assert count == self.num_nodes // 2 + self.num_nodes // 10

    async def doSimpleLiftByTag(self, prox: 's_telepath.Client') -> None:
        count = await acount(prox.eval('inet:ipv4#even'))
        assert count == self.num_nodes // 2

    async def doPivotToNothing(self, prox: 's_telepath.Client') -> None:
        count = await acount(prox.eval('inet:ipv4#odd -> inet:dns:a'))
        assert count == 0

    async def doPivotToSomething(self, prox: 's_telepath.Client') -> None:
        count = await acount(prox.eval('inet:ipv4#even -> inet:dns:a'))
        assert count == self.num_nodes // 2 + self.num_nodes // 10

    async def run(self, core, name, dirn, coro):
        for i in range(self.NUM_ITERS):
            # We set up the cortex each time to void intra-cortex caching
            # (there's still a substantial amount of OS caching)
            async with self.getCortexAndProxy(dirn) as (core, prox):
                gc.collect()

                start = time.time()
                await coro(prox)
                self.measurements[name].append(time.time() - start)
                # yappi.get_func_stats().print_all()

    async def runSuite(self, testdata, config, numprocs):
        assert numprocs == 1
        with syntest.getTestDir() as dirn:
            async with self.getCortexAndProxy(dirn) as (core, _):
                await self._loadtestdata(core, testdata)
            await self.run(core, 'Nothing', dirn, self.doNothing)
            await self.run(core, 'SimpleCount', dirn, self.doSimpleCount)
            await self.run(core, 'SimpleLift', dirn, self.doSimpleLift)
            await self.run(core, 'SimpleLiftByTag', dirn, self.doSimpleLiftByTag)
            await self.run(core, 'PivotToNothing', dirn, self.doPivotToNothing)
            await self.run(core, 'PivotToSomething', dirn, self.doPivotToSomething)

Configs: Dict[str, Dict] = {
    'simple': {'layer:lmdb:map_async': True}
}

def benchmarkAll(confignames: List = None, num_procs=1, num_nodes=1000) -> None:

    test_data = TestData(num_nodes)
    if not confignames:
        confignames = ['simple']
    for configname in confignames:
        config = Configs[configname]
        bench = Benchmarker(config, num_nodes)
        print(f'{num_procs}-process benchmarking: {configname}')
        asyncio.run(bench.runSuite(test_data, config, num_procs))
        bench.report(configname)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('which_configs', nargs='*', default=None)
    parser.add_argument('--num-clients', type=int, default=1)
    parser.add_argument('--num-nodes', type=int, default=1000)
    # FIXME: tmpdir location
    opts = parser.parse_args()
    benchmarkAll(opts.which_configs, opts.num_clients, opts.num_nodes)
