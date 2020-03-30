import os
import gc
import sys
import time
import random
import asyncio
import logging
import argparse
import contextlib
import statistics
import collections
from typing import List, Dict, AsyncIterator, Tuple, Any, Callable

try:
    import tqdm
    DoProgress = True
except ModuleNotFoundError:
    print('"tqdm" module not found.  Install it to see progress.')
    DoProgress = False

try:
    import yappi
    YappiHere = True
except ModuleNotFoundError:
    YappiHere = False

import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.time as s_time

import synapse.tools.backup as s_tools_backup

import synapse.tests.utils as s_t_utils

SimpleConf = {'layers:lockmemory': False, 'layer:lmdb:map_async': False, 'nexslog:en': False, 'layers:logedits': False}
MapAsyncConf = {**SimpleConf, 'layer:lmdb:map_async': True}
DedicatedConf = {**SimpleConf, 'layers:lockmemory': True}
DefaultConf = {**MapAsyncConf, 'layers:lockmemory': True}
DedicatedAsyncLogConf = {**DefaultConf, 'nexslog:en': True, 'layers:logedits': True}

Configs: Dict[str, Dict] = {
    'simple': SimpleConf,
    'mapasync': MapAsyncConf,
    'dedicated': DedicatedConf,
    'default': DefaultConf,
    'dedicatedasynclogging': DedicatedAsyncLogConf,
}

'''
Benchmark cortex operations

TODO:  separate client process, multiple clients
TODO:  tagprops, regex, control flow, node data, multiple layers, spawn option, remote layer
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

syntest = s_t_utils.SynTest()

class TestData(s_base.Base):
    '''
    Pregenerates a bunch of data for future test runs
    '''
    async def __anit__(self, num_records, dirn):
        '''
        # inet:ipv4 -> inet:dns:a -> inet:fqdn
        # For each even ipv4 record, make an inet:dns:a record that points to <ipaddress>.website, if it is
        # divisible by ten also make a inet:dns:a that points to blackhole.website
        '''
        await s_base.Base.__anit__(self)
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

        tstdirctx = syntest.getTestDir(startdir=dirn)
        self.dirn = await self.enter_context(tstdirctx)

        async with await s_cortex.Cortex.anit(self.dirn, conf=DefaultConf) as core:
            await s_common.aspin(core.addNodes(self.ips))
            await s_common.aspin(core.addNodes(self.dnsas))
            await s_common.aspin(core.addNodes(self.urls))

def isatrial(meth):
    '''
    Mark a method as being a trial
    '''
    meth._isatrial = True
    return meth

class Benchmarker:

    def __init__(self, config: Dict[Any, Any], testdata: TestData, workfactor: int, num_iters=4, tmpdir=None,
                 bench=None):
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
        self.tmpdir = tmpdir
        self.bench = bench

    def printreport(self, configname: str):
        print(f'Config {configname}: {self.coreconfig}, Num Iters: {self.num_iters} Debug: {__debug__}')
        for name, info in self.reportdata():
            totmean = info.get('totmean')
            count = info.get('count')
            mean = info.get('mean') * 1000000
            stddev = info.get('stddev') * 1000000
            print(f'{name:30}: {totmean:8.3f}s / {count:5} = {mean:6.0f}μs stddev: {stddev:6.0f}μs')

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

    @contextlib.asynccontextmanager
    async def getCortexAndProxy(self) -> AsyncIterator[Tuple[Any, Any]]:
        with syntest.getTestDir(startdir=self.tmpdir) as dirn:

            s_tools_backup.backup(self.testdata.dirn, dirn, compact=False)

            async with await s_cortex.Cortex.anit(dirn, conf=self.coreconfig) as core:
                assert not core.inaugural

                lockmemory = self.coreconfig.get('layers:lockmemory', False)
                nexuslogen = self.coreconfig.get('nexslog:en', True)
                logedits = self.coreconfig.get('layers:logedits', True)

                await core.view.layers[0].layrinfo.set('lockmemory', lockmemory)
                await core.view.layers[0].layrinfo.set('logedits', logedits)

            async with await s_cortex.Cortex.anit(dirn, conf=self.coreconfig) as core:
                async with core.getLocalProxy() as prox:
                    if lockmemory:
                        await core.view.layers[0].layrslab.lockdoneevent.wait()

                    if nexuslogen:
                        core.nexsroot._nexusslab.forcecommit()

                    yield core, prox

    @isatrial
    async def do00EmptyQuery(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        for _ in range(self.workfactor // 10):
            count = await acount(prox.eval(''))

        assert count == 0
        return self.workfactor // 10

    @isatrial
    async def do01SimpleCount(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4 | count | spin'))
        assert count == 0
        return self.workfactor

    @isatrial
    async def do02LiftSimple(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4'))
        assert count == self.workfactor
        return count

    @isatrial
    async def do02LiftFilterAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4 | +#newp'))
        assert count == 0
        return 1

    @isatrial
    async def do02LiftFilterPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4 | +#all'))
        assert count == self.workfactor
        return count

    @isatrial
    async def do03LiftBySecondaryAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:dns:a:fqdn=newp'))
        assert count == 0
        return 1

    @isatrial
    async def do03LiftBySecondaryPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:dns:a:fqdn=blackhole.website'))
        assert count == self.workfactor // 10
        return count

    @isatrial
    async def do04LiftByTagAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4#newp'))
        assert count == 0
        return 1

    @isatrial
    async def do04LiftByTagPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4#even'))
        assert count == self.workfactor // 2
        return count

    @isatrial
    async def do05PivotAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4#odd -> inet:dns:a'))
        assert count == 0
        return self.workfactor // 2

    @isatrial
    async def do06PivotPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:ipv4#even -> inet:dns:a'))
        assert count == self.workfactor // 2 + self.workfactor // 10
        return count

    @isatrial
    async def do07AddNodes(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.addNodes(self.testdata.asns2))
        assert count == self.workfactor
        return count

    @isatrial
    async def do07AddNodesPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.addNodes(self.testdata.ips))
        assert count == self.workfactor
        return count

    @isatrial
    async def do08LocalAddNodes(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(core.addNodes(self.testdata.asns))
        assert count == self.workfactor
        return count

    @isatrial
    async def do09DelNodes(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(prox.eval('inet:url | delnode'))
        assert count == 0
        return self.workfactor

    @isatrial
    async def do10AutoAdds(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        q = "inet:ipv4 $val=$lib.str.format('{num}.rev', num=$(1000000-$node.value())) [:dns:rev=$val]"
        count = await acount(prox.eval(q))
        assert count == self.workfactor
        return self.workfactor

    @isatrial
    async def do10Formatting(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        '''
        The same as do10AutoAdds without the adds (to isolate the autoadd part)
        '''
        q = "inet:ipv4 $val=$lib.str.format('{num}.rev', num=$(1000000-$node.value()))"
        count = await acount(prox.eval(q))
        assert count == self.workfactor
        return self.workfactor

    async def run(self, name: str, testdirn: str, coro, do_profiling=False) -> None:
        for _ in range(self.num_iters):
            # We set up the cortex each time to avoid intra-cortex caching
            # (there's still a substantial amount of OS caching)
            async with self.getCortexAndProxy() as (core, prox):
                gc.collect()
                gc.disable()

                if do_profiling:
                    yappi.start()
                start = time.time()
                count = await coro(core, prox)
                self.measurements[name].append((time.time() - start, count))
                if do_profiling:
                    yappi.stop()
                gc.enable()
            renderProgress()

    def _getTrialFuncs(self):
        funcs: List[Tuple[str, Callable]] = []
        funcnames = sorted(f for f in dir(self))
        for funcname in funcnames:
            func = getattr(self, funcname)
            if not hasattr(func, '_isatrial'):
                continue
            if self.bench is not None:
                if not any(funcname.startswith(b) for b in self.bench):
                    continue
            funcs.append((funcname, func))
        return funcs

    async def runSuite(self, numprocs: int, tmpdir: str = None, do_profiling=False):
        assert numprocs == 1
        if tmpdir is not None:
            tmpdir = os.path.abspath(tmpdir)
        with syntest.getTestDir(tmpdir) as dirn:
            logger.info('Loading test data complete.  Starting benchmarks')
            for funcname, func in self._getTrialFuncs():
                await self.run(funcname, dirn, func, do_profiling=do_profiling)

ProgressBar = None

def initProgress(total):
    if not DoProgress:
        return
    global ProgressBar

    ProgressBar = tqdm.tqdm(total=total)

def renderProgress():
    if not DoProgress:
        return

    ProgressBar.update()

def endProgress():
    global ProgressBar
    if not DoProgress:
        return
    ProgressBar.close()

async def benchmarkAll(confignames: List = None,
                       num_procs=1,
                       workfactor=1000,
                       tmpdir: str = None,
                       jsondir: str = None,
                       jsonprefix: str = None,
                       niters: int = 4,
                       bench=None,
                       do_profiling=False,
                       ) -> None:

    if jsondir:
        s_common.gendir(jsondir)

    if do_profiling:
        yappi.set_clock_type('wall')

    with syntest.getTestDir(startdir=tmpdir) as dirn:

        async with await TestData.anit(workfactor, dirn) as testdata:
            print('Initial cortex created')
            if not confignames:
                confignames = ['simple']

            for configname in confignames:
                tick = s_common.now()
                config = Configs[configname]
                bench = Benchmarker(config, testdata, workfactor, num_iters=niters, tmpdir=tmpdir, bench=bench)
                print(f'{num_procs}-process benchmarking: {configname}')
                initProgress(niters * len(bench._getTrialFuncs()))
                try:
                    await bench.runSuite(num_procs, do_profiling=do_profiling)
                    endProgress()

                    if do_profiling:
                        yappi.get_func_stats().print_all()

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
                            data['prefix'] = jsonprefix
                        s_common.jssave(data, jsondir, fn)
                finally:
                    endProgress()

def getParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', nargs='*', default=['default'])
    # parser.add_argument('--num-clients', type=int, default=1)
    parser.add_argument('--workfactor', type=int, default=1000)
    parser.add_argument('--niters', type=int, default=4, help='Number of times to run each benchmark')
    parser.add_argument('--tmpdir', type=str),
    parser.add_argument('--jsondir', default=None, type=str,
                        help='Directory to output JSON report data too.')
    parser.add_argument('--jsonprefix', default=None, type=str,
                        help='Prefix to append to the autogenerated filename for json output.')
    parser.add_argument('--bench', '-b', nargs='*', default=None,
                        help='Prefixes of which benchmarks to run (defaults to run all)')
    parser.add_argument('--do-profiling', action='store_true')
    return parser

if __name__ == '__main__':

    parser = getParser()
    opts = parser.parse_args()

    if opts.do_profiling and not YappiHere:
        print('Error: module "yappi" must be installed to use --do-profiling')
        sys.exit(1)

    asyncio.run(benchmarkAll(opts.config, 1, opts.workfactor, opts.tmpdir,
                             jsondir=opts.jsondir, jsonprefix=opts.jsonprefix,
                             niters=opts.niters, bench=opts.bench, do_profiling=opts.do_profiling))
