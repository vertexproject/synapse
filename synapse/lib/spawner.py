import asyncio
import logging
import tempfile

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.link as s_link
import synapse.lib.const as s_const
import synapse.lib.process as s_process

logger = logging.getLogger(__name__)

def _ioWorkProc(todo, sockpath):

    async def workloop():

        async with await s_daemon.Daemon.anit() as dmon:

            func, args, kwargs = todo

            async with await func(*args, **kwargs) as item:

                assert isinstance(item, s_base.Base), f'Item is not a Base object: {item}'

                await item.addSignalHandlers()

                dmon.share('dmon', dmon)
                dmon.share('item', item)

                # bind last so we're ready to go...
                try:
                    await dmon.listen(f'unix://{sockpath}')
                except OSError:
                    logger.exception(f'IO worker failed to open listening socket at [{sockpath}]')
                    raise
                await item.waitfini()

    asyncio.run(workloop())

async def _spawnerWait(sockpath, timeout=30):

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        try:
            await asyncio.wait_for(s_link.unixwait(sockpath), timeout=1)
            return
        except asyncio.TimeoutError:
            if loop.time() > deadline:
                raise s_exc.FatalErr(
                    mesg=f'IO worker failed to open listening socket at [{sockpath}] within {timeout}s'
                )

class SpawnerMixin:

    @classmethod
    def spawner(cls, base=None, sockpath=None):
        async def _spawn(*args, **kwargs):
            return await cls._spawn(args, kwargs, base=base, sockpath=sockpath)
        return _spawn

    @classmethod
    async def _spawn(cls, args, kwargs, base=None, sockpath=None):

        todo = (cls.anit, args, kwargs)

        iden = s_common.guid()

        if sockpath is not None and len(sockpath) > s_const.UNIX_SOCKET_PATH_MAX:
            sockpath = None
        if sockpath is None:
            tmpdir = tempfile.gettempdir()
            sockpath = s_common.genpath(tmpdir, iden)

        if base is None:
            base = await s_base.Base.anit()

        base.schedCoro(s_process.spawn((_ioWorkProc, (todo, sockpath), {})))

        await _spawnerWait(sockpath)

        proxy = await s_telepath.openurl(f'unix://{sockpath}:item')

        async def fini():

            try:
                async with await s_telepath.openurl(f'unix://{sockpath}:item') as finiproxy:
                    await finiproxy.task(('fini', (), {}))
            except (s_exc.LinkErr, s_exc.NoSuchPath, asyncio.CancelledError):
                # This can fail if the subprocess was terminated from outside...
                pass

            if not base.isfini:
                logger.error(f'IO Worker Socket Closed: {sockpath}')

            await base.fini()

        proxy.onfini(fini)
        base.onfini(proxy)

        return proxy
