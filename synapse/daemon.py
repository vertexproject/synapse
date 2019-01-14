import os
import types
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.cells as s_cells
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.telepath as s_telepath

import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.link as s_link
import synapse.lib.scope as s_scope
import synapse.lib.share as s_share
import synapse.lib.certdir as s_certdir
import synapse.lib.urlhelp as s_urlhelp

class Sess(s_base.Base):

    async def __anit__(self):

        await s_base.Base.__anit__(self)

        self.items = {}
        self.iden = s_common.guid()

    def getSessItem(self, name):
        return self.items.get(name)

    def setSessItem(self, name, item):
        self.items[name] = item

    def popSessItem(self, name):
        return self.items.pop(name, None)

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

    async def __anit__(self, dirn=None, conf=None):

        await s_base.Base.__anit__(self)

        self.dirn = None
        if dirn is not None:
            self.dirn = s_common.gendir(dirn)

        self._shareLoopTasks = set()

        yaml = self._loadDmonYaml()
        if conf is not None:
            yaml.update(conf)

        self.conf = s_common.config(yaml, self.confdefs)
        self.certdir = s_certdir.CertDir(os.path.join(dirn, 'certs'))

        self.mods = {}      # keep refs to mods we load ( mostly for testing )
        self.televers = s_telepath.televers

        self.addr = None    # our main listen address
        self.cells = {}     # all cells are shared.  not all shared are cells.
        self.shared = {}    # objects provided by daemon
        self.listenservers = [] # the sockets we're listening on
        self.connectedlinks = [] # the links we're currently connected on

        self.sessions = {}

        self.mesgfuncs = {
            'tele:syn': self._onTeleSyn,
            'task:init': self._onTaskInit,
            'share:fini': self._onShareFini,

            # task version 2 API
            't2:init': self._onTaskV2Init,
        }

        self.onfini(self._onDmonFini)

        await self._loadDmonConf()
        await self._loadDmonCells()

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

        server = await s_link.listen(host, port, self._onLinkInit, ssl=sslctx)
        self.listenservers.append(server)
        ret = server.sockets[0].getsockname()

        if self.addr is None:
            self.addr = ret

        return ret

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

        finis = [sess.fini() for sess in self.sessions.values()]
        if finis:
            await asyncio.wait(finis)

        finis = [link.fini() for link in self.connectedlinks]
        if finis:
            await asyncio.wait(finis)

    def _loadDmonYaml(self):
        if self.dirn is not None:
            path = s_common.genpath(self.dirn, 'dmon.yaml')
            return self._loadYamlPath(path)

    def _loadYamlPath(self, path):

        if os.path.isfile(path):
            return s_common.yamlload(path)

        return {}

    async def _loadDmonCells(self):

        # load our services from a directory

        if self.dirn is None:
            return

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

        async def rxloop():

            while not link.isfini:

                mesg = await link.rx()
                if mesg is None:
                    return

                coro = self._onLinkMesg(link, mesg)
                self.schedCoro(coro)

        self.schedCoro(rxloop())

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

        sess = link.get('sess')
        if sess is None:
            return

        name = mesg[1].get('share')

        item = sess.popSessItem(name)
        if item is None:
            return

        await item.fini()

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

            sess = await Sess.anit()
            async def sessfini():
                self.sessions.pop(sess.iden, None)

            sess.onfini(sessfini)
            link.onfini(sess.fini)

            self.sessions[sess.iden] = sess

            link.set('sess', sess)

            if isinstance(item, s_telepath.Aware):
                item = await s_coro.ornot(item.getTeleApi, link, mesg)
                if isinstance(item, s_base.Base):
                    link.onfini(item.fini)

            sess.setSessItem(None, item)
            reply[1]['sess'] = sess.iden

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

    async def _onTaskV2Init(self, link, mesg):

        # t2:init is used by the pool sockets on the client

        name = mesg[1].get('name')
        sidn = mesg[1].get('sess')
        todo = mesg[1].get('todo')

        try:

            if sidn is None or todo is None:
                raise s_exc.NoSuchObj(name=name)

            sess = self.sessions.get(sidn)
            if sess is None:
                raise s_exc.NoSuchObj(name=name)

            item = sess.getSessItem(name)
            if item is None:
                raise s_exc.NoSuchObj(name=name)

            s_scope.set('sess', sess)
            # TODO set user....

            methname, args, kwargs = todo

            if methname[0] == '_':
                raise s_exc.NoSuchMeth(name=methname)

            meth = getattr(item, methname, None)
            if meth is None:
                logger.warning(f'{item!r} has no method: {methname}')
                raise s_exc.NoSuchMeth(name=methname)

            valu = meth(*args, **kwargs)

            if s_coro.iscoro(valu):
                valu = await valu

            if isinstance(valu, types.AsyncGeneratorType):

                try:

                    await link.tx(('t2:genr', {}))

                    async for item in valu:
                        await link.tx(('t2:yield', {'retn': (True, item)}))

                    await link.tx(('t2:yield', {'retn': None}))

                except Exception as e:
                    if not link.isfini:
                        retn = s_common.retnexc(e)
                        await link.tx(('t2:yield', {'retn': retn}))

                return

            if isinstance(valu, types.GeneratorType):

                try:

                    await link.tx(('t2:genr', {}))

                    for item in valu:
                        await link.tx(('t2:yield', {'retn': (True, item)}))

                    await link.tx(('t2:yield', {'retn': None}))

                except Exception as e:
                    if not link.isfini:
                        retn = s_common.retnexc(e)
                        await link.tx(('t2:yield', {'retn': (False, retn)}))

                return

            if isinstance(valu, s_share.Share):
                iden = s_common.guid()
                sess.setSessItem(iden, valu)
                await link.tx(('t2:share', {'iden': iden}))
                return

            await link.tx(('t2:fini', {'retn': (True, valu)}))

        except Exception as e:

            logger.exception('on task:init: %r' % (mesg,))

            if not link.isfini:
                retn = s_common.retnexc(e)
                await link.tx(('t2:fini', {'retn': retn}))

    async def _onTaskInit(self, link, mesg):

        task = mesg[1].get('task')
        name = mesg[1].get('name')

        sess = link.get('sess')
        if sess is None:
            raise s_exc.NoSuchObj(name=name)

        item = sess.getSessItem(name)
        if item is None:
            raise s_exc.NoSuchObj(name=name)

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

                if isinstance(item, s_base.Base):
                    item.onfini(valu)

                async def spinshareloop():
                    try:
                        await valu._runShareLoop()
                    except asyncio.CancelledError:
                        pass
                    except Exception:
                        logger.exception('Error running %r', valu)
                    finally:
                        await valu.fini()

                self.schedCoro(spinshareloop())

        except Exception as e:

            logger.exception('on task:init: %r' % (mesg,))

            retn = s_common.retnexc(e)

            await link.tx(
                ('task:fini', {'task': task, 'retn': retn})
            )
