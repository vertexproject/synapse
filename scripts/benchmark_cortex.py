import os
import gc
import time
import random
import asyncio
import contextlib
import collections
import logging
import statistics

logger = logging.getLogger(__name__)

from typing import List, Dict, AsyncIterator, Tuple, Any, TYPE_CHECKING
if TYPE_CHECKING:
    import synapse.telepath as s_telepath
    import synapse.cortex as s_cortex

import synapse.common as s_common

import synapse.tests.utils as s_t_utils

s_common.setlogging(logger, 'ERROR')

# Construct existing cortex
# Copy cortex directory to a new one

# inet:ipv4 -> inet:dns:a -> inet:fqdn

# Pivot that returns no nodes
#   Pivot that returns a lot of nodes

# Lift by tag
# Lift by buid
# Lift by primary prop prefix
#   No nodes
#   1 node
#   Lots of nodes

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
    '''
    Pregenerate a bunch of data for future test runs
    '''
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

        self.asns = [(('inet:asn', asn * 2), {}) for asn in range(num_records)]
        self.asns2 = [(('inet:asn', asn * 2 + 1), {}) for asn in range(num_records)]
        random.shuffle(self.asns)
        random.shuffle(self.asns2)

        self.urls = [(('inet:url', f'http://{hex(n)}.ninja'), {}) for n in range(num_records)]
        random.shuffle(self.urls)

syntest = s_t_utils.SynTest()

class Benchmarker:
    def __init__(self, config: Dict[Any, Any], testdata: TestData, workfactor: int, num_iters=4):
        '''
        Args:
            config: the cortex config
            testdata: pre-generated data
            workfactor:  a positive integer indicating roughly the amount of work each benchmark should do
            num_iters:  the number of times each test is run

        Note:  the actual benchmarked methods start with 'do' (so don't add a property or non-benchmark method that
        starts with 'do').  All these benchmark methods are independent and should not have an effect (other than btree
        caching, and size) on the other tests.  The only precondition is that the testdata has been loaded.
        '''
        self.measurements: Dict[str, List] = collections.defaultdict(list)
        self.num_iters = num_iters
        self.coreconfig = config
        self.workfactor = workfactor
        self.testdata = testdata

    def report(self, configname: str):
        print(f'Config: {self.coreconfig}, Num Iters: {self.num_iters} Debug: {__debug__}')
        for name, measurements in self.measurements.items():
            # ms = ', '.join(f'{m[0]:0.3}' for m in measurements)
            tottimes = [m[0] for m in measurements[1:]]
            pertimes = [m[0] / m[1] for m in measurements[1:]]
            totmean = statistics.mean(tottimes)
            mean = statistics.mean(pertimes) * 100000
            stddev = statistics.stdev(pertimes) * 100000
            count = measurements[0][1]

            print(f'{name:20}: {totmean:8.3}s / {count:5} = {mean:6.3}μs stddev: {stddev:6.4}μs')

    async def _loadtestdata(self, core):
        await s_common.aspin(core.addNodes(self.testdata.ips))
        await s_common.aspin(core.addNodes(self.testdata.dnsas))
        await s_common.aspin(core.addNodes(self.testdata.urls))

    @contextlib.asynccontextmanager
    async def getCortexAndProxy(self, dirn: str) -> AsyncIterator[Tuple[Any, Any]]:
        async with syntest.getTestCoreAndProxy(conf=self.coreconfig, dirn=dirn) as (core, prox):
            yield core, prox

    async def do00Nothing(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval(''))
        assert count == 0
        return 1

    async def do01SimpleCount(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval('inet:ipv4 | count | spin'))
        assert count == 0
        return self.workfactor

    async def do02SimpleLift(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval('inet:dns:a'))
        assert count == self.workfactor // 2 + self.workfactor // 10
        return count

    async def do03LiftBySecondary(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval('inet:dns:a:fqdn=blackhole.website'))
        assert count == self.workfactor // 10
        return count

    async def do04SimpleLiftByTag(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval('inet:ipv4#even'))
        assert count == self.workfactor // 2
        return count

    async def do05PivotToNothing(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval('inet:ipv4#odd -> inet:dns:a'))
        assert count == 0
        return self.workfactor // 2

    async def do06PivotToSomething(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval('inet:ipv4#even -> inet:dns:a'))
        assert count == self.workfactor // 2 + self.workfactor // 10
        return count

    async def do07AddNodes(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.addNodes(self.testdata.asns2))
        assert count == self.workfactor
        return count

    async def do07AddNodesBounce(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.addNodes(self.testdata.ips))
        assert count == self.workfactor
        return count

    async def do08LocalAddNodes(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(core.addNodes(self.testdata.asns))
        assert count == self.workfactor
        return count

    async def do09DelNodes(self, core: 's_cortex.Cortex', prox: 's_telepath.Client') -> int:
        count = await acount(prox.eval('inet:url | delnode'))
        assert count == 0
        return self.workfactor

    async def run(self, core: 's_cortex.Cortex', name: str, dirn: str, coro) -> None:
        for i in range(self.num_iters):
            # We set up the cortex each time to avoid intra-cortex caching
            # (there's still a substantial amount of OS caching)
            async with self.getCortexAndProxy(dirn) as (core, prox):
                gc.collect()

                start = time.time()
                count = await coro(core, prox)
                self.measurements[name].append((time.time() - start, count))
                # yappi.get_func_stats().print_all()

    async def runSuite(self, config: Dict[str, Dict], numprocs: int, tmpdir: str = None):
        assert numprocs == 1
        if tmpdir is not None:
            tmpdir = os.path.abspath(tmpdir)
        with syntest.getTestDir(tmpdir) as dirn:
            async with self.getCortexAndProxy(dirn) as (core, _):
                await self._loadtestdata(core)
            funcnames = sorted(f for f in dir(self) if f.startswith('do'))
            for funcname in funcnames:
                funclabel = funcname[2:]
                func = getattr(self, funcname)
                await self.run(core, funclabel, dirn, func)

Configs: Dict[str, Dict] = {
    'simple': {},
    'mapasync': {'layer:lmdb:map_async': True}
}

def benchmarkAll(confignames: List = None, num_procs=1, workfactor=1000, tmpdir=None) -> None:

    testdata = TestData(workfactor)
    if not confignames:
        confignames = ['simple']
    for configname in confignames:
        config = Configs[configname]
        bench = Benchmarker(config, testdata, workfactor)
        print(f'{num_procs}-process benchmarking: {configname}')
        asyncio.run(bench.runSuite(config, num_procs))
        bench.report(configname)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='*', default=None)
    parser.add_argument('--num-clients', type=int, default=1)
    parser.add_argument('--workfactor', type=int, default=1000)
    parser.add_argument('--tmpdir', nargs=1)
    opts = parser.parse_args()
    benchmarkAll(opts.config, opts.num_clients, opts.workfactor, opts.tmpdir)
