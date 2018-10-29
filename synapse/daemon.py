import os
import types
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.share as s_share
import synapse.lib.certdir as s_certdir
import synapse.lib.urlhelp as s_urlhelp

class Genr(s_share.Share):

    typename = 'genr'

    async def _runShareLoop(self):

        try:

            for item in self.item:

                if self.isfini:
                    break

                retn = (True, item)
                mesg = ('share:data', {'share': self.iden, 'data': retn})
                await self.link.tx(mesg)

        except Exception as e:

            retn = s_common.retnexc(e)
            mesg = ('share:data', {'share': self.iden, 'data': retn})
            await self.link.tx(mesg)

        finally:

            mesg = ('share:data', {'share': self.iden, 'data': None})
            await self.link.tx(mesg)
            await self.fini()


class AsyncGenr(s_share.Share):

    typename = 'genr'

    async def _runShareLoop(self):

        try:

            async for item in self.item:

                if self.isfini:
                    break

                retn = (True, item)
                mesg = ('share:data', {'share': self.iden, 'data': retn})
                await self.link.tx(mesg)

        except Exception as e:
            retn = s_common.retnexc(e)
            mesg = ('share:data', {'share': self.iden, 'data': retn})
            await self.link.tx(mesg)

        finally:

            mesg = ('share:data', {'share': self.iden, 'data': None})
            await self.link.tx(mesg)
            await self.fini()

dmonwrap = (
    (s_coro.Genr, AsyncGenr),
    (s_coro.GenrHelp, AsyncGenr),
    (types.AsyncGeneratorType, AsyncGenr),
    (types.GeneratorType, Genr),
)

class Daemon(s_base.Base):

    confdefs = (

        ('listen', {'defval': 'tcp://127.0.0.1:27492',
            'doc': 'The default listen host/port'}),

        ('modules', {'defval': (),
            'doc': 'A list of python modules to import before Cell construction.'}),

        #('hostname', {'defval':
        #('ssl': {'defval': None,
            #'doc': 'An SSL config dict with certfile/keyfile optional cacert.'}),
    )

    async def __anit__(self, dirn):

        await s_base.Base.__anit__(self)

        self.dirn = s_common.gendir(dirn)
        self._shareLoopTasks = set()

        conf = self._loadDmonYaml()
        self.conf = s_common.config(conf, self.confdefs)
        self.certdir = s_certdir.CertDir(os.path.join(dirn, 'certs'))

        self.mods = {}      # keep refs to mods we load ( mostly for testing )
        self.televers = s_telepath.televers

        self.addr = None    # our main listen address
        self.cells = {}     # all cells are shared.  not all shared are cells.
        self.shared = {}    # objects provided by daemon
        self.listenservers = [] # the sockets we're listening on
        self.connectedlinks = [] # the links we're currently connected on

        self.mesgfuncs = {
            'tele:syn': self._onTeleSyn,
            'task:init': self._onTaskInit,
            'share:fini': self._onShareFini,
        }

        self.onfini(self._onDmonFini)

        await self._loadDmonConf()
        await self._loadDmonCells()

    @s_glob.synchelp
    async def listen(self, url, **opts):
        '''
        Bind and listen on the given host/port with possible SSL.

        Args:
            host (str): A hostname or IP address.
            port (int): The TCP port to bind.
        '''
        info = s_urlhelp.chopurl(url, **opts)
        info.update(opts)

        host = info.get('host')
        port = info.get('port')

        sslctx = None
        if info.get('scheme') == 'ssl':
            sslctx = self.certdir.getServerSSLContext(hostname=host)

        server = await s_glob.plex.listen(host, port, self._onLinkInit, ssl=sslctx)
        self.listenservers.append(server)
        return server.sockets[0].getsockname()

    def share(self, name, item):
        '''
        Share an object via the telepath protocol.

        Args:
            name (str): Name of the shared object
            item (object): The object to share over telepath.
        '''

        try:

            if isinstance(item, s_telepath.Aware):
                item.onTeleShare(self, name)

            self.shared[name] = item

        except Exception as e:
            logger.exception(f'onTeleShare() error for: {name}')

    async def _onDmonFini(self):
        for s in self.listenservers:
            try:
                s.close()
            except Exception as e:  # pragma: no cover
                logger.warning('Error during socket server close()', exc_info=e)
        for name, share in self.shared.items():
            if isinstance(share, s_base.Base):
                await share.fini()

        for name, share in self.shared.items():
            if isinstance(share, s_base.Base):
                await share.fini()

        for task in self._shareLoopTasks:
            try:
                if task.done():
                    continue
                task.cancel()
            except Exception as e:
                logger.error('Error cancelling task: %s', str(e))

        finis = [link.fini() for link in self.connectedlinks]
        if finis:
            await asyncio.wait(finis, loop=self.loop)

    def _loadDmonYaml(self):
        path = s_common.genpath(self.dirn, 'dmon.yaml')
        return self._loadYamlPath(path)

    def _loadYamlPath(self, path):
        if os.path.isfile(path):
            return s_common.yamlload(path)

        logger.warning('config not found: %r' % (path,))
        return {}

    async def _loadDmonCells(self):

        # load our services from a directory

        path = s_common.gendir(self.dirn, 'cells')

        for name in os.listdir(path):

            if name.startswith('.'):
                continue

            await self.loadDmonCell(name)

    async def loadDmonCell(self, name):
        dirn = s_common.gendir(self.dirn, 'cells', name)
        logger.info(f'loading cell from: {dirn}')

        path = os.path.join(dirn, 'boot.yaml')

        if not os.path.exists(path):
            raise s_exc.NoSuchFile(name=path)

        conf = self._loadYamlPath(path)

        kind = conf.get('type')

        cell = await s_cells.init(kind, dirn)

        self.share(name, cell)
        self.cells[name] = cell

    async def _loadDmonConf(self):

        # process per-conf elements...
        for name in self.conf.get('modules', ()):
            try:
                self.mods[name] = s_dyndeps.getDynMod(name)
            except Exception as e:
                logger.exception('dmon module error')

        lisn = self.conf.get('listen')
        if lisn is not None:
            self.addr = await self.listen(lisn)

    async def _onLinkInit(self, link):

        async def onrx(mesg):
            self.schedCoro(self._onLinkMesg(link, mesg))

        link.onrx(onrx)
        self.connectedlinks.append(link)

    async def _onLinkMesg(self, link, mesg):

        try:
            func = self.mesgfuncs.get(mesg[0])
            if func is None:
                logger.exception('Dmon.onLinkMesg Invalid: %.80r' % (mesg,))
                return

            await func(link, mesg)

        except Exception as e:
            logger.exception('Dmon.onLinkMesg Handler: %.80r' % (mesg,))

    async def _onShareFini(self, link, mesg):

        iden = mesg[1].get('share')
        share = link.get('dmon:items').get(iden)
        if share is None:
            return

        await share.fini()

    async def _onTeleSyn(self, link, mesg):

        reply = ('tele:syn', {
            'vers': self.televers,
            'retn': (True, None),
        })

        try:

            vers = mesg[1].get('vers')

            if vers[0] != s_telepath.televers[0]:
                raise s_exc.BadMesgVers(vers=vers, myvers=s_telepath.televers)

            name = mesg[1].get('name')

            item = self.shared.get(name)

            # allow a telepath aware object a shot at dynamic share names
            if item is None and name.find('/') != -1:

                path = name.split('/')

                base = self.shared.get(path[0])
                if base is not None and isinstance(base, s_telepath.Aware):
                    item = await s_coro.ornot(base.onTeleOpen, link, path)

            if item is None:
                raise s_exc.NoSuchName(name=name)

            if isinstance(item, s_telepath.Aware):
                item = await s_coro.ornot(item.getTeleApi, link, mesg)

            items = {None: item}
            link.set('dmon:items', items)

            async def fini():

                items = list(link.get('dmon:items').values())

                for item in items:
                    if isinstance(item, s_base.Base):
                        try:
                            await item.fini()
                        except Exception as e:  # pragma: no cover
                            logger.exception('item fini error')

            link.onfini(fini)

        except Exception as e:
            logger.exception('tele:syn error')
            reply[1]['retn'] = s_common.retnexc(e)

        await link.tx(reply)

    async def _runTodoMeth(self, link, meth, args, kwargs):

        valu = meth(*args, **kwargs)

        for wraptype, wrapctor in dmonwrap:
            if isinstance(valu, wraptype):
                return await wrapctor.anit(link, valu)

        if s_coro.iscoro(valu):
            valu = await valu

        return valu

    def _getTaskFiniMesg(self, task, valu):

        if not isinstance(valu, s_share.Share):
            retn = (True, valu)
            return ('task:fini', {'task': task, 'retn': retn})

        retn = (True, valu.iden)
        typename = valu.typename
        return ('task:fini', {'task': task, 'retn': retn, 'type': typename})

    async def _onTaskInit(self, link, mesg):

        task = mesg[1].get('task')
        name = mesg[1].get('name')

        item = link.get('dmon:items').get(name)
        if item is None:
            raise s_exc.NoSuchObj(f'name={name}')

        try:

            methname, args, kwargs = mesg[1].get('todo')

            if methname[0] == '_':
                raise s_exc.NoSuchMeth(name=methname)

            meth = getattr(item, methname, None)
            if meth is None:
                logger.warning(f'{item!r} has no method: {methname}')
                raise s_exc.NoSuchMeth(name=methname)

            valu = await self._runTodoMeth(link, meth, args, kwargs)

            mesg = self._getTaskFiniMesg(task, valu)
            await link.tx(mesg)

            # if it's a Share(), spin off the share loop
            if isinstance(valu, s_share.Share):
                async def spinshareloop():
                    try:
                        await valu._runShareLoop()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        logger.exception('Error running %r', valu)
                    finally:
                        await valu.fini()
                task = s_glob.plex.coroLoopTask(spinshareloop())
                self._shareLoopTasks.add(task)
                task.add_done_callback(self._getTaskResult)

        except Exception as e:

            logger.exception('on task:init: %r' % (mesg,))

            retn = s_common.retnexc(e)

            await link.tx(
                ('task:fini', {'task': task, 'retn': retn})
            )

    def _getTaskResult(self, task):
        result = s_common.novalu
        try:
            result = task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error('Error encountered for %s: [%s]',
                         task, e)
        finally:
            try:
                self._shareLoopTasks.remove(task)
            except KeyError:
                pass
            return result
