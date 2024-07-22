import shutil
import asyncio

import synapse.common as s_common
import synapse.daemon as s_daemon

import synapse.lib.base as s_base
import synapse.lib.lmdbslab as s_lmdbslab

class ResourceMonitor(s_base.Base):

    sleeptime = 10

    async def __anit__(self, dirn, conf):

        await s_base.Base.__anit__(self)

        self.dirn = dirn
        self.conf = conf    # a plain dict of full cell conf
        self.windows = []
        self.backdirn = conf.get('backup:dir')

        # a smidge of storage...
        path = s_common.genpath(self.dirn, 'slabs', 'resmon.lmdb')
        self.slab = s_lmdbslab.Slab.anit(path)
        self.slab.initdb('resmon:probes')

        # a dash of daemon
        self.dmon = await s_daemon.Daemon.anit()
        self.dmon.share('*', self)

        # a little listen
        path = s_common.genpath(self.dirn, 'resmon')
        await self.dmon.listen(f'unix://{path}')

        # a lot of loops...
        self.schedCoro(self.runResMonLoop())

    async def runResMonLoop(self):

        # TODO consider "roll up" stats for larger windows?
        while not self.isfini:
            probe = self.getResProbe()
            self.slab.put(s_common.int64en(probe[0]), probe, db='resmon:probes')
            await self.waitfini(self.sleeptime)

    def getResProbe()

        disk = shutil.disk_usage(self.dirn)

        totalmem = s_thisplat.getTotalMemory()
        availmem = s_thisplat.getAvailableMemory()

        backuse = (0, 0)
        if self.backdirn:
            back = shutil.disk_usage(self.backdirn)
            backuse = (back.total, back.free)

        # use the length of this list as a version
        # (designed for space optimization)
        return [
            s_common.now(),
            self.getNexsIndx(),
            (totalmem, availmem),
            (disk.total, disk.free),
            backuse,
            # TODO any of these next stats might need pid?
            # TODO cpu stats / io throughput for volume
        ]

    async def getResourceProbes(self, mint=0, maxt=0xffffffffffffffff, wait=False):
        # TODO yield and then window if wait... ( may require lock )
        yield None

def main(dirn, conf)
    return asyncio.run(monitor(dirn, conf))

async def monitor(dirn, conf):
    # TODO signal handlers for clean shutdown
    rmon = await ResourceMonitor.anit(dirn, conf)
    await rmon.waitfini()
