import os
import json
import yaml
import types
import asyncio
import logging

logger = logging.getLogger(__name__)

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.dyndeps as s_dyndeps
import synapse.registry as s_registry
import synapse.telepath as s_telepath

from synapse.eventbus import EventBus

import synapse.lib.urlhelp as s_urlhelp

class Daemon(EventBus):

    def __init__(self, dirn, conf=None):

        EventBus.__init__(self)

        self.dirn = dirn
        self.televers = s_telepath.televers

        if self.dirn is not None:
            self.dirn = s_common.gendir(dirn)

        self.shared = {}    # objects provided by daemon

        self.mesgfuncs = {
            'tele:syn': self._onTeleSyn,
            'task:init': self._onTaskInit,
            #'chan:data': self._onChanData,
            'chan:fini': self._onChanFini,
        }

        if self.dirn is not None:
            self._loadDmonYaml()
            self._loadSvcDir()

    def _loadDmonYaml(self):

        path = s_common.genpath(self.dirn, 'dmon.yaml')
        if os.path.isfile(path):
            conf = self._loadYamlPath(path)
            self._loadDmonConf(conf)

    def _loadSvcDir(self):

        # load our services from a directory

        path = s_common.gendir(self.dirn, 'services')
        for name in os.listdir(path):

            if name.startswith('.'):
                continue

            dirn = os.path.join(path, name)
            path = os.path.join(dirn, 'service.yaml')

            if not os.path.exists(path):
                raise s_exc.NoSuchFile(name=path)

            conf = self.loadYamlPath(path)

            kind = conf.get('type')

            ctor = s_registry.getService(kind)
            if ctor is None:
                raise s_exc.NoSuchSvcType(name=kind)

            subc = conf.get('config')
            item = ctor(dirn, conf=subc)

            self.share(name, item)

    def _loadYamlPath(self, path):
        # load a yaml dmon config path
        with open(path, 'rb') as fd:
            byts = fd.read()
            return yaml.load(byts.decode('utf8'))

    def _loadDmonConf(self, conf):
        # process a dmon config dict.

        lisn = conf.get('listen')
        if lisn is not None:

            url = lisn.get('url')

            if url is not None:
                opts = lisn.get('opts', {})
                link = self.listen(url, **opts)

        for name in conf.get('modules', ()):
            try:
                pymod = s_dyndeps.getDynMod(name)
            except Exception as e:
                mesg = 'dmon module error (%s): %s' % (name, e)
                logger.exception(mesg)

    async def _onLinkInit(self, link):

        async def onrx(mesg):
            await self._onLinkMesg(link, mesg)

        link.onrx(onrx)

    async def _onLinkMesg(self, link, mesg):

        try:

            func = self.mesgfuncs.get(mesg[0])
            if func is None:
                logger.exception('Dmon.onLinkMesg Invalid: %r' % (mesg,))
                return

            coro = func(link, mesg)
            if asyncio.iscoroutine(coro):
                await coro

        except Exception as e:
            logger.exception('Dmon.onLinkMesg Handler: %r' % (mesg,))

    async def _onChanFini(self, link, mesg):

        iden = mesg[1].get('chan')

        chan = link.chans.get(iden)
        if chan is None:
            return

        chan.fini()

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
            if item is None:
                raise s_exc.NoSuchName(name=name)

            link.set('dmon:item', item)

        except Exception as e:

            logger.warning('tele:syn error')

            reply[1]['retn'] = s_common.retnexc(e)

        await link.tx(reply)

    async def _feedAsyncGenrChan(self, link, iden, genr):

        chan = link.chan()
        try:

            if not await chan.init(iden):
                return

            async for item in genr:
                if not await chan.tx(item):
                    return

        except Exception as e:
            logger.exception()
            await chan.txexc(e)

        finally:
            await chan.txfini()
            chan.fini()

    @s_glob.inpool
    def _feedGenrChan(self, link, iden, genr):

        chan = link.chan()
        try:

            if not s_glob.sync(chan.init(iden)):
                return

            for item in genr:

                if not s_glob.sync(chan.tx(item)):
                    break

        except Exception as e:
            logger.exception()
            s_glob.sync(chan.txexc(e))

        finally:
            s_glob.sync(chan.txfini())

    async def _onTaskInit(self, link, mesg):

        task = mesg[1].get('task')

        user = link.get('syn:user')
        item = link.get('dmon:item')

        import synapse.lib.scope as s_scope

        ##with s_scope.enter({'dmon': self, 'sock': sock, 'syn:user': user, 'syn:auth': self.auth}):

        with s_scope.enter({'syn:user': user}):

            try:

                name = mesg[1].get('meth')
                if name[0] == '_':
                    raise s_exc.NoSuchMeth(name=name)

                args = mesg[1].get('args')
                kwargs = mesg[1].get('kwargs')

                meth = getattr(item, name, None)
                if meth is None:
                    raise s_exc.NoSuchMeth(name=name)

                valu = meth(*args, **kwargs)

                if isinstance(valu, types.AsyncGeneratorType):
                    await self._feedAsyncGenrChan(link, task, valu)
                    return

                if isinstance(valu, types.GeneratorType):
                    self._feedGenrChan(link, task, valu)
                    return

                # await a coroutine if we got one
                if asyncio.iscoroutine(valu):
                    valu = await valu

                await link.tx(
                    ('task:fini', {'task': task, 'retn': (True, valu)})
                )

                return

            except Exception as e:

                logger.exception('on task:init: %r' % (mesg,))

                retn = s_common.retnexc(e)

                await link.tx(
                    ('task:fini', {'task': task, 'retn': retn})
                )

    def listen(self, url, **opts):
        '''
        Create and run a link server by url.

        Example:

            link = dmon.listen('tcp://127.0.0.1:8888')

        Notes:

            * Returns the parsed link tufo

        '''
        info = s_urlhelp.chopurl(url)
        info.update(opts)

        host = info.get('host')
        port = info.get('port')

        return s_glob.plex.listen(host, port, self._onLinkInit, ssl=None)

    def share(self, name, item):
        '''
        Share an object via the telepath protocol.

        Args:
            name (str): Name of the shared object
            item (object): The object to share over telepath.
        '''
        if isinstance(item, s_telepath.Aware):
            item = item.getTeleApi()

        self.shared[name] = item
