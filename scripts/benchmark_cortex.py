import os
import gc
import time
import random
import asyncio
import logging
import argparse
import contextlib
import statistics
import collections
from typing import List, Dict, AsyncIterator, Tuple, Any, Callable

import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.time as s_time

import synapse.tests.utils as s_t_utils

'''
Benchmark cortex operations

TODO:  separate client process, multiple clients
TODO:  tagprops, regex, control flow, node data, multiple layers, spawn option, remote layer
TODO:  standard serialized output format
'''

logger = logging.getLogger(__name__)
if __debug__:
    logger.warning('Running benchmark without -O.  Performance will be slower.')

s_common.setlogging(logger, 'ERROR')

async def acount(genr):
    '''
    Counts an async generator
    '''
    count = 0
    async for _ in genr:
        count += 1
    return count

class TestData:
    '''
    Pregenerates a bunch of data for future test runs
    '''
    def __init__(self, num_records):
        '''
        # inet:ipv4 -> inet:dns:a -> inet:fqdn
        # For each even ipv4 record, make an inet:dns:a record that points to <ipaddress>.website, if it is
        # divisible by ten also make a inet:dns:a that points to blackhole.website
        '''
        self.nrecs = num_records
        random.seed(4)  # 4 chosen by fair dice roll.  Guaranteed to be random
        ips = list(range(num_records))
        random.shuffle(ips)
        dnsas = [(f'{ip}.website', ip) for ip in ips if ip % 2 == 0]
        dnsas += [('blackhole.website', ip) for ip in ips if ip % 10 == 0]
        random.shuffle(dnsas)

        def oe(num):
            return 'odd' if num % 2 else 'even'

        self.ips = [(('inet:ipv4', ip), {'tags': {'all': (None, None), oe(ip): (None, None)}}) for ip in ips]
        self.dnsas = [(('inet:dns:a', dnsas), {}) for dnsas in dnsas]

        self.asns = [(('inet:asn', asn * 2), {}) for asn in range(num_records)]
        self.asns2 = [(('inet:asn', asn * 2 + 1), {}) for asn in range(num_records)]
        random.shuffle(self.asns)
        random.shuffle(self.asns2)

        self.urls = [(('inet:url', f'http://{hex(n)}.ninja'), {}) for n in range(num_records)]
        random.shuffle(self.urls)

syntest = s_t_utils.SynTest()

def isatrial(meth):
    '''
    Mark a method as being a trial
    '''
    meth._isatrial = True
    return meth

class Benchmarker:
    def __init__(self, config: Dict[Any, Any], testdata: TestData, workfactor: int, num_iters=4):
        '''
        Args:
            config: the cortex config
            testdata: pre-generated data
            workfactor:  a positive integer indicating roughly the amount of work each benchmark should do
            num_iters:  the number of times each test is run

        All the benchmark methods are independent and should not have an effect (other than btree caching and size)
        on the other tests.  The only precondition is that the testdata has been loaded.
        '''
        self.measurements: Dict[str, List] = collections.defaultdict(list)
        self.num_iters = num_iters
        self.coreconfig = config
        self.workfactor = workfactor
        self.testdata = testdata

    def printreport(self, configname: str):
        print(f'Config {configname}: {self.coreconfig}, Num Iters: {self.num_iters} Debug: {__debug__}')
        for name, info in self.reportdata():
            totmean = info.get('totmean')
            count = info.get('count')
            mean = info.get('mean') * 1000000
            stddev = info.get('stddev') * 1000000
            print(f'{name:30}: {totmean:8.3}s / {count:5} = {mean:9.5}μs stddev: {stddev:6.4}μs')

    def reportdata(self):
        retn = []
        for name, measurements in self.measurements.items():
            # ms = ', '.join(f'{m[0]:0.3}' for m in measurements)
            tottimes = [m[0] for m in measurements[1:]]
            pertimes = [m[0] / m[1] for m in measurements[1:]]
            totmean = statistics.mean(tottimes)
            mean = statistics.mean(pertimes)
            stddev = statistics.stdev(pertimes)
            count = measurements[0][1]

            retn.append((name, {'measurements': measurements,
                                'tottimes': tottimes,
                                'pertimes': pertimes,
                                'totmean': totmean,
                                'mean': mean,
                                'stddev': stddev,
                                'count': count}))
        return retn

    async def _loadtestdata(self, core):
        await s_common.aspin(core.addNodes(self.testdata.ips))
        await s_common.aspin(core.addNodes(self.testdata.dnsas))
        await s_common.aspin(core.addNodes(self.testdata.urls))

    @contextlib.asynccontextmanager
    async def getCortexAndProxy(self, dirn: str) -> AsyncIterator[Tuple[Any, Any]]:
        async with syntest.getTestCoreAndProxy(conf=self.coreconfig, dirn=dirn) as (core, prox):
            yield core, prox

    @isatrial
    async def do00EmptyQuery(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        for _ in range(self.workfactor // 10):
            count = await acount(prox.eval(''))
        assert count == 0
        return self.workfactor // 10

    @isatrial
    async def do01SimpleCount(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4 | count | spin'))
        assert count == 0
        return self.workfactor

    @isatrial
    async def do02Lift(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4'))
        assert count == self.workfactor
        return count

    @isatrial
    async def do02LiftFilterAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4 | +#newp'))
        assert count == 0
        return 1

    @isatrial
    async def do02LiftFilterPresent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4 | +#all'))
        assert count == self.workfactor
        return count

    @isatrial
    async def do03LiftBySecondaryAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:dns:a:fqdn=newp'))
        assert count == 0
        return 1

    @isatrial
    async def do03LiftBySecondaryPresent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:dns:a:fqdn=blackhole.website'))
        assert count == self.workfactor // 10
        return count

    @isatrial
    async def do04LiftByTagAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4#newp'))
        assert count == 0
        return 1

    @isatrial
    async def do04LiftByTagPresent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4#even'))
        assert count == self.workfactor // 2
        return count

    @isatrial
    async def do05PivotAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4#odd -> inet:dns:a'))
        assert count == 0
        return self.workfactor // 2

    @isatrial
    async def do06PivotPresent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:ipv4#even -> inet:dns:a'))
        assert count == self.workfactor // 2 + self.workfactor // 10
        return count

    @isatrial
    async def do07AddNodes(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.addNodes(self.testdata.asns2))
        assert count == self.workfactor
        return count

    @isatrial
    async def do07AddNodesPresent(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.addNodes(self.testdata.ips))
        assert count == self.workfactor
        return count

    @isatrial
    async def do08LocalAddNodes(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(core.addNodes(self.testdata.asns))
        assert count == self.workfactor
        return count

    @isatrial
    async def do09DelNodes(self, core: s_cortex.Cortex, prox: s_telepath.Client) -> int:
        count = await acount(prox.eval('inet:url | delnode'))
        assert count == 0
        return self.workfactor

    async def run(self, core: s_cortex.Cortex, name: str, dirn: str, coro) -> None:
        for i in range(self.num_iters):
            # We set up the cortex each time to avoid intra-cortex caching
            # (there's still a substantial amount of OS caching)
            async with self.getCortexAndProxy(dirn) as (core, prox):
                gc.collect()

                start = time.time()
                count = await coro(core, prox)
                self.measurements[name].append((time.time() - start, count))
                # yappi.get_func_stats().print_all()

    def _getTrialFuncs(self):
        funcs: List[Tuple[str, Callable]] = []
        funcnames = sorted(f for f in dir(self))
        for funcname in funcnames:
            func = getattr(self, funcname)
            if not hasattr(func, '_isatrial'):
                continue
            funcs.append((funcname, func))
        return funcs

    async def runSuite(self, config: Dict[str, Dict], numprocs: int, tmpdir: str = None):
        assert numprocs == 1
        if tmpdir is not None:
            tmpdir = os.path.abspath(tmpdir)
        with syntest.getTestDir(tmpdir) as dirn:
            logger.info('Loading test data')
            async with self.getCortexAndProxy(dirn) as (core, _):
                await self._loadtestdata(core)
            logger.info('Loading test data complete.  Starting benchmarks')
            for funcname, func in self._getTrialFuncs():
                await self.run(core, funcname, dirn, func)

Configs: Dict[str, Dict] = {
    'simple': {},
    'mapasync': {'layer:lmdb:map_async': True},
    'dedicated': {'dedicated': True},
    'dedicatedasync': {'dedicated': True, 'layer:lmdb:map_async': True},
}

def benchmarkAll(confignames: List = None, num_procs=1, workfactor=1000, tmpdir=None,
                 jsondir: str =None,
                 jsonprefix: str =None,
                 ) -> None:

    if jsondir:
        s_common.gendir(jsondir)

    testdata = TestData(workfactor)
    if not confignames:
        confignames = ['simple']
    for configname in confignames:
        tick = s_common.now()
        config = Configs[configname]
        bench = Benchmarker(config, testdata, workfactor)
        print(f'{num_procs}-process benchmarking: {configname}')
        asyncio.run(bench.runSuite(config, num_procs))
        bench.printreport(configname)

        if jsondir:
            data = {'time': tick,
                    'config': config,
                    'configname': configname,
                    'workfactor': workfactor,
                    'niters': bench.num_iters,
                    'results': bench.reportdata()
                    }
            fn = f'{s_time.repr(tick, pack=True)}_{configname}.json'
            if jsonprefix:
                fn = f'{jsonprefix}{fn}'
            s_common.jssave(data, jsondir, fn)

def getParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='*', default=None)
    # parser.add_argument('--num-clients', type=int, default=1)
    parser.add_argument('--workfactor', type=int, default=1000)
    parser.add_argument('--tmpdir', nargs=1)
    parser.add_argument('--jsondir', default=None, type=str,
                        help='Directory to output JSON report data too.')
    parser.add_argument('--jsonprefix', default=None, type=str,
                        help='Prefix to append to the autogenerated filename for json output.')
    return parser

if __name__ == '__main__':

    parser = getParser()
    opts = parser.parse_args()

    benchmarkAll(opts.config, 1, opts.workfactor, opts.tmpdir,
                 jsondir=opts.jsondir, jsonprefix=opts.jsonprefix)
