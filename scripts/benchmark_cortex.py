import os
import gc
import sys
import time
import random
import asyncio
import logging
import pathlib
import binascii
import tempfile
import argparse
import datetime
import itertools
import contextlib
import statistics
import collections
from typing import List, Dict, AsyncIterator, Tuple, Any, Callable, Sequence

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
import synapse.lib.lmdbslab as s_lmdbslab

import synapse.tests.utils as s_t_utils

# Increment this when the stored benchmark data changes
BENCHMARK_DATA_VERSION = 1

SimpleConf = {'layers:lockmemory': False, 'layer:lmdb:map_async': False, 'nexslog:en': False, 'layers:logedits': False}
MapAsyncConf = {**SimpleConf, 'layer:lmdb:map_async': True}
DedicatedConf = {**SimpleConf, 'layers:lockmemory': True}
DefaultConf = {**MapAsyncConf, 'layers:lockmemory': True}
DefaultNoBuidConf = {**MapAsyncConf, 'layers:lockmemory': True, 'buid:prefetch': False}
DedicatedAsyncLogConf = {**DefaultConf, 'nexslog:en': True, 'layers:logedits': True}

Configs: Dict[str, Dict] = {
    'simple': SimpleConf,
    'mapasync': MapAsyncConf,
    'dedicated': DedicatedConf,
    'default': DefaultConf,
    'defaultnobuid': DefaultNoBuidConf,
    'dedicatedasynclogging': DedicatedAsyncLogConf,
}

'''
Benchmark cortex operations

TODO:  separate client process, multiple clients
TODO:  tagprops, regex, control flow, node data, multiple layers, spawn option
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

async def acountPodes(genr):
    '''Count storm node messages'''
    count = 0
    async for (m, _) in genr:
        if m == 'node':
            count += 1
    return count

syntest = s_t_utils.SynTest()

async def layerByName(prox: s_telepath.Proxy, name: str):
    retn = await prox.callStorm('''
               for $layr in $lib.layer.list() {
                   if ($name=$layr.get(name)) {
                       return ($layr.iden)
                   }
               }''', opts={'vars': {'name': name}})
    return retn

FeedT = List[Tuple[Tuple, Dict[str, Any]]]

class TestData(s_base.Base):
    '''
    Pregenerates a bunch of data for future test runs
    '''
    async def __anit__(self, work_factor: int, dirn: str, remote: str = None, keep=False):  # type: ignore
        '''
        Args:
            work_factor:  a rough scale of the amount of data to generate
            dirn: directory where to put a temporary cortex.  Not used if remote is set
            remote: Telepath URL to a remote cortex
            keep: Whether to keep (and use if already there) the benchmark data between runs of this tool

        Notes:
            inet:ipv4 -> inet:dns:a -> inet:fqdn
            For each even ipv4 record, make an inet:dns:a record that points to <ipaddress>.website, if it is
            divisible by ten also make a inet:dns:a that points to blackhole.website
        '''
        await s_base.Base.__anit__(self)
        self.nrecs = work_factor
        rando = random.Random(4)  # 4 chosen by fair dice roll.  Guaranteed to be random
        self.rando = rando
        ips = list(range(work_factor))
        rando.shuffle(ips)
        dnsas = [(f'{ip}.website', ip) for ip in ips if ip % 2 == 0]
        dnsas += [('blackhole.website', ip) for ip in ips if ip % 10 == 0]
        rando.shuffle(dnsas)
        self.remote = remote

        def oe(num):
            return 'odd' if num % 2 else 'even'

        # Ip addresses with an all tag with half having an 'even' tag and the other an 'odd' tag
        self.ips = [(('inet:ipv4', ip), {'tags': {'all': (None, None), oe(ip): (None, None)}}) for ip in ips]
        self.dnsas: List[Tuple[Tuple, Dict]] = [(('inet:dns:a', dnsas), {}) for dnsas in dnsas]

        self.asns: FeedT = [(('inet:asn', asn * 2), {}) for asn in range(work_factor)]
        self.asns2: FeedT = [(('inet:asn', asn * 2 + 1), {}) for asn in range(work_factor)]
        rando.shuffle(self.asns)
        rando.shuffle(self.asns2)

        self.asns2prop: FeedT = [(asn[0], {'props': {'name': 'x'}}) for asn in self.asns]

        fredguid = self.myguid()
        self.asns2formexist: FeedT = [(asn[0], {'props': {'owner': fredguid}}) for asn in self.asns]
        self.asns2formnoexist: FeedT = [(asn[0], {'props': {'owner': self.myguid()}}) for asn in self.asns]

        self.urls: FeedT = [(('inet:url', f'http://{hex(n)}.ninja'), {}) for n in range(work_factor)]
        rando.shuffle(self.urls)
        orgs: FeedT = [(('ou:org', fredguid), {})]
        already_got_one = False

        if remote:
            self.dirn = None
            core = None
            prox = await s_telepath.openurl(self.remote)
            self.prox = prox
        else:
            tstdirctx = syntest.getTestDir(startdir=dirn)
            self.dirn = await self.enter_context(tstdirctx)
            core = await s_cortex.Cortex.anit(self.dirn, conf=DefaultConf)
            prox = await self.enter_context(core.getLocalProxy())

        self.layriden = None

        name = str(('benchmark base', BENCHMARK_DATA_VERSION, work_factor))
        if remote and keep:
            self.layriden = await layerByName(prox, name)

        if self.layriden is None:
            retn = await prox.callStorm('''
                $layr = $lib.layer.add($lib.dict(name=$name)) return ($layr.iden)''', opts={'vars': {'name': name}})
            self.layriden = retn
        else:
            logger.info('Reusing existing benchmarking layer')
            already_got_one = True

        retn = await prox.callStorm('''
            $view = $lib.view.add(($layr,))
            $view.set(name, $name)
            return ($view.iden)''', opts={'vars': {'name': name, 'layr': self.layriden}})

        self.viewiden = retn

        if not already_got_one:
            gen = itertools.chain(self.ips, self.dnsas, self.urls, self.asns, orgs)
            await prox.addFeedData('syn.nodes', list(gen), viewiden=self.viewiden)

        if core:
            await core.fini()

        async def fini():
            opts = {'vars': {'view': self.viewiden, 'layer': self.layriden}}
            await prox.callStorm('$lib.view.del($view)', opts=opts)
            if not keep:
                await prox.callStorm('$lib.layer.del($layer)', opts=opts)
            await self.prox.fini()

        if remote:
            self.onfini(fini)

    def myguid(self):
        '''
        Like s_common.guid but uses the rng seed so is predictable
        '''
        return binascii.hexlify(self.rando.getrandbits(128).to_bytes(16, 'big')).decode('utf8')

def benchmark(tags=None):

    def _inner(meth):
        '''
        Mark a method as being a benchmark
        '''
        meth._benchmark = True

        mytags = set() if tags is None else tags
        mytags.add('all')

        meth._tags = mytags
        return meth

    return _inner

class Benchmarker:

    def __init__(self, config: Dict[Any, Any], testdata: TestData, workfactor: int, num_iters=4, tmpdir=None,
                 bench=None, tags=None):
        '''
        Args:
            config: the cortex config
            testdata: pre-generated data
            workfactor:  a positive integer indicating roughly the amount of work each benchmark should do
            num_iters:  the number of times each test is run
            tags:  filters which individual measurements should be run (all tags must be present)
            remote: the remote telepath URL of a remote cortex

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
        self.tags = tags

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
        if self.num_iters < 3:
            print('--niters must be > 2 for effective statistics')
            return retn

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
        '''
        Prepares a cortex/proxy for a benchmark run
        '''
        ldef = {
            'lockmemory': self.coreconfig.get('layers:lockmemory', False),
            'logedits': self.coreconfig.get('layers:logedits', True),
            'name': 'tmp for benchmark',
        }
        core = None

        async with contextlib.AsyncExitStack() as stack:
            if not self.testdata.remote:
                ctx = await s_cortex.Cortex.anit(self.testdata.dirn, conf=self.coreconfig)
                core = await stack.enter_async_context(ctx)
                prox = await stack.enter_async_context(core.getLocalProxy())
                assert not core.inaugural
            else:
                ctx = await s_telepath.openurl(self.testdata.remote)
                prox = await stack.enter_async_context(ctx)

            layer = await prox.cloneLayer(self.testdata.layriden, ldef)
            layeriden = layer['iden']
            view = await prox.callStorm('return($lib.view.add(($layer, ), name="tmp for benchmark"))',
                                        opts={'vars': {'layer': layeriden}})
            self.viewiden = view['iden']
            self.opts = {'view': self.viewiden}

            await prox.dyncall(layeriden, s_common.todo('waitForHot'))

            try:
                yield core, prox

            finally:
                await prox.callStorm('''
                    $lib.view.del($view)
                    $lib.layer.del($layer)
                ''', opts={'vars': {'view': self.viewiden, 'layer': layeriden}})

    @benchmark({'remote'})
    async def do00EmptyQuery(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        for _ in range(self.workfactor // 10):
            count = await acountPodes(prox.storm('', opts=self.opts))

        assert count == 0
        return self.workfactor // 10

    @benchmark({'remote'})
    async def do00NewQuery(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        for i in range(self.workfactor):
            count = await acountPodes(prox.storm(f'$x={i}', opts=self.opts))

        assert count == 0
        return self.workfactor

    @benchmark({'official', 'remote'})
    async def do01SimpleCount(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4 | count | spin', opts=self.opts))
        assert count == 0
        return self.workfactor

    @benchmark({'official', 'remote'})
    async def do02LiftSimple(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4', opts=self.opts))
        assert count == self.workfactor
        return count

    @benchmark({'official', 'remote'})
    async def do02LiftFilterAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4 | +#newp', opts=self.opts))
        assert count == 0
        return 1

    @benchmark({'official', 'remote'})
    async def do02LiftFilterPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4 | +#all', opts=self.opts))
        assert count == self.workfactor
        return count

    @benchmark({'official', 'remote'})
    async def do03LiftBySecondaryAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:dns:a:fqdn=newp', opts=self.opts))
        assert count == 0
        return 1

    @benchmark({'official', 'remote'})
    async def do03LiftBySecondaryPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:dns:a:fqdn=blackhole.website', opts=self.opts))
        assert count == self.workfactor // 10
        return count

    @benchmark({'official', 'remote'})
    async def do04LiftByTagAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4#newp', opts=self.opts))
        assert count == 0
        return 1

    @benchmark({'official', 'remote'})
    async def do04LiftByTagPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4#even', opts=self.opts))
        assert count == self.workfactor // 2
        return count

    @benchmark({'official', 'remote'})
    async def do05PivotAbsent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4#odd -> inet:dns:a', opts=self.opts))
        assert count == 0
        return self.workfactor // 2

    @benchmark({'official', 'remote'})
    async def do06PivotPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:ipv4#even -> inet:dns:a', opts=self.opts))
        assert count == self.workfactor // 2 + self.workfactor // 10
        return count

    @benchmark({'addnodes', 'remote'})
    async def do07AAddNodesCallStorm(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        tags_to_add = '+#test'
        count = 0

        for node in self.testdata.asns2prop:
            props_to_add = f":name = {node[1]['props']['name']}"
            form, valu = node[0]

            opts = {'vars': {'valu': valu}, 'view': self.viewiden}
            await prox.callStorm(f'[ {form}=$valu {props_to_add} {tags_to_add}] return($node.pack(dorepr=1))',
                                 opts=opts)
            count += 1
        assert count == self.workfactor
        return count

    @benchmark({'addnodes', 'remote'})
    async def do07AAddNodesStorm(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        tags_to_add = '+#test'
        msgs = []

        for node in self.testdata.asns2prop:
            props_to_add = f":name = {node[1]['props']['name']}"
            form, valu = node[0]

            opts = {'vars': {'valu': valu}, 'view': self.viewiden}
            msgs.extend([x async for x in prox.storm(f'[ {form}=$valu {props_to_add} {tags_to_add}]', opts=opts)])
            newnodes = [m for m in msgs if m[0] == 'node:edits' and m[1]['edits'][0][2][0][0] == 2]
        assert len(newnodes) == self.workfactor
        return len(newnodes)

    @benchmark({'official', 'addnodes', 'remote', 'this'})
    async def do07BAddNodesSimpleProp(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        '''
        Add simple node with a single non-form secondary prop
        '''
        await prox.addFeedData('syn.nodes', self.testdata.asns2prop, viewiden=self.viewiden)

        assert self.workfactor == await prox.count('inet:asn:name=x', opts=self.opts)

        return self.workfactor

    @benchmark({'official', 'addnodes', 'remote'})
    async def do07CAddNodesFormProp(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        '''
        Add simple node with a single form secondary prop and that secondary prop form doesn't exist
        '''
        await prox.addFeedData('syn.nodes', self.testdata.asns2formnoexist, viewiden=self.viewiden)

        if __debug__:
            assert self.workfactor + 1 == await prox.count('ou:org', opts=self.opts)
        return self.workfactor

    @benchmark({'official', 'addnodes', 'remote'})
    async def do07DAddNodesFormPropExists(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        '''
        Add simple node with a single form secondary prop and that secondary prop form already exists
        '''
        await prox.addFeedData('syn.nodes', self.testdata.asns2formexist, viewiden=self.viewiden)

        assert self.workfactor == await prox.count('inet:asn', opts=self.opts)
        return self.workfactor

    @benchmark({'official', 'addnodes', 'remote'})
    async def do07EAddNodesPresent(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        await prox.addFeedData('syn.nodes', self.testdata.asns, viewiden=self.viewiden)
        assert len(self.testdata.asns) == await prox.count('inet:asn', opts=self.opts)
        return len(self.testdata.asns)

    @benchmark({'official', 'addnodes'})
    async def do08LocalAddNodes(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acount(core.addNodes('syn.nodes', self.testdata.asns2, viewiden=self.viewiden))
        assert count == self.workfactor
        return count

    @benchmark({'official', 'remote'})
    async def do09DelNodes(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        count = await acountPodes(prox.storm('inet:url | delnode', opts=self.opts))
        assert count == 0
        return self.workfactor

    @benchmark({'remote'})
    async def do10AutoAdds(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        q = "inet:ipv4 $val=$lib.str.format('{num}.rev', num=$(1000000-$node.value())) [:dns:rev=$val]"
        count = await acountPodes(prox.storm(q, opts=self.opts))
        assert count == self.workfactor
        return self.workfactor

    @benchmark({'remote'})
    async def do10SlashAdds(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        q = '[ inet:ipv4=1.2.0.0/16 ] | spin'
        count = await acountPodes(prox.storm(q, opts=self.opts))
        assert count == 0
        return 2 ** 16

    @benchmark({'remote'})
    async def do10Formatting(self, core: s_cortex.Cortex, prox: s_telepath.Proxy) -> int:
        '''
        The same as do10AutoAdds without the adds (to isolate the autoadd part)
        '''
        q = "inet:ipv4 $val=$lib.str.format('{num}.rev', num=$(1000000-$node.value()))"
        count = await acountPodes(prox.storm(q, opts=self.opts))
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
                await s_lmdbslab.Slab.syncLoopOnce()
                self.measurements[name].append((time.time() - start, count))
                if do_profiling:
                    yappi.stop()
                gc.enable()
            renderProgress()

    def _getTrialFuncs(self):
        funcs: List[Tuple[str, Callable]] = []
        funcnames = sorted(f for f in dir(self))
        tags = set(self.tags) if self.tags is not None else set()
        for funcname in funcnames:
            func = getattr(self, funcname)
            if not hasattr(func, '_benchmark'):
                continue
            if self.bench is not None:
                if not any(funcname.startswith(b) for b in self.bench):
                    continue
            if not tags.issubset(func._tags):
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
                       tags: Sequence = None,
                       remote: str = None,
                       keep: bool = False,
                       ) -> None:

    if jsondir:
        s_common.gendir(jsondir)

    if do_profiling:
        yappi.set_clock_type('wall')

    with syntest.getTestDir(startdir=tmpdir) as dirn:

        async with await TestData.anit(workfactor, dirn, remote=remote, keep=keep) as testdata:

            if not confignames:
                confignames = ['simple']

            for configname in confignames:
                tick = s_common.now()
                config = Configs[configname]
                bencher = Benchmarker(config, testdata, workfactor, num_iters=niters, tmpdir=tmpdir, bench=bench,
                                      tags=tags)
                print(f'{num_procs}-process benchmarking: {configname}')
                initProgress(niters * len(bencher._getTrialFuncs()))
                try:
                    await bencher.runSuite(num_procs, do_profiling=do_profiling)
                    endProgress()

                    if do_profiling:
                        stats = yappi.get_func_stats()
                        stats.print_all()
                        perfdir = tmpdir or tempfile.gettempdir()
                        perffn = pathlib.Path(perfdir) / f'{configname}_{datetime.datetime.now().isoformat()}.out'
                        print(f'Callgrind stats output to {str(perffn)}')
                        stats.save(perffn, 'CALLGRIND')
                        yappi.clear_stats()

                    bencher.printreport(configname)

                    if jsondir:
                        data = {'time': tick,
                                'config': config,
                                'configname': configname,
                                'workfactor': workfactor,
                                'niters': niters,
                                'results': bencher.reportdata()
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
    parser.add_argument('--remote', type=str, help='Telepath URL of remote cortex (benchmark is nondestructive)')
    parser.add_argument('--workfactor', type=int, default=1000)
    parser.add_argument('--niters', type=int, default=4, help='Number of times to run each benchmark')
    parser.add_argument('--tmpdir', type=str),
    parser.add_argument('--jsondir', default=None, type=str,
                        help='Directory to output JSON report data too.')
    parser.add_argument('--jsonprefix', default=None, type=str,
                        help='Prefix to append to the autogenerated filename for json output.')
    parser.add_argument('--bench', '-b', nargs='*', default=None,
                        help='Prefixes of which benchmarks to run (defaults to run all)')
    parser.add_argument('--tags', '-t', nargs='*',
                        help='Tag(s) of which suite to run (defaults to "official" if bench not set)')
    parser.add_argument('--do-profiling', action='store_true')
    parser.add_argument('--keep', action='store_true',
                        help='Whether to keep and use existing initial benchmark data')
    return parser

if __name__ == '__main__':

    parser = getParser()
    opts = parser.parse_args()

    if opts.do_profiling and not YappiHere:
        print('Error: module "yappi" must be installed to use --do-profiling')
        sys.exit(1)

    if opts.bench is None and opts.tags is None:
        opts.tags = ['official', ]

    if opts.tags is None:
        opts.tags = []

    if opts.remote:
        opts.tags.append('remote')

    asyncio.run(benchmarkAll(opts.config, 1, opts.workfactor, opts.tmpdir,
                             jsondir=opts.jsondir, jsonprefix=opts.jsonprefix,
                             niters=opts.niters, bench=opts.bench, do_profiling=opts.do_profiling, tags=opts.tags,
                             remote=opts.remote, keep=opts.keep))
