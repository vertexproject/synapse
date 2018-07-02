'''
An RMI framework for synapse.
'''

import os
import asyncio
import logging

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.lib.urlhelp as s_urlhelp

logger = logging.getLogger(__name__)

televers = (3, 0)

class Aware:
    '''
    The telepath.Aware mixin allows shared objects to
    handle individual links managed by the Daemon.
    '''
    def getTeleApi(self, link, mesg):
        '''
        Return a shared object for this link.
        Args:
            link (synapse.lib.link.Link): A network link.
            mesg ((str,dict)): The tele:syn handshake message.
        '''
        return self

    def onTeleShare(self, dmon, name):
        pass

    def onTeleOpen(self, link, path):
        '''
        Allow a telepath share to create a new sub-share.
        '''
        return None

class Task:
    '''
    A telepath Task is used to internally track calls/responses.
    '''
    def __init__(self):
        self.retn = None
        self.iden = s_common.guid()
        self.done = asyncio.Event()

    async def result(self):
        await self.done.wait()
        return s_common.result(self.retn)

    def reply(self, retn):
        self.retn = retn
        self.done.set()

import synapse.lib.coro as s_coro

class Share(s_coro.Fini):
    '''
    The telepath client side of a dynamically shared object.
    '''
    def __init__(self, proxy, iden):
        s_coro.Fini.__init__(self)
        self.iden = iden
        self.proxy = proxy

        self.proxy.shares[iden] = self

        self.txfini = True
        self.onfini(self._txShareFini)

    async def _txShareFini(self):

        self.proxy.shares.pop(self.iden, None)

        if not self.txfini:
            return

        mesg = ('share:fini', {'share': self.iden})
        await self.proxy.link.tx(mesg)

    async def _onShareData(self, data):
        logger.warning(f'share:data with no handler: {data!r}')

    def __getattr__(self, name):
        meth = Method(self.proxy, name, share=self.iden)
        setattr(self, name, meth)
        return meth

class Genr(Share):

    def __init__(self, proxy, iden):
        Share.__init__(self, proxy, iden)
        self.queue = s_coro.Queue()
        self.onfini(self.queue.fini)

    async def _onShareData(self, data):
        self.queue.put(data)

    async def __aiter__(self):

        try:

            while not self.isfini:

                for retn in self.queue.slice():
                    if retn is None:
                        return

                    yield s_common.result(retn)

        finally:
            await self.fini()

    def __iter__(self):
        try:
            while not self.isfini:

                for retn in s_glob.sync(self.queue.slice()):

                    if retn is None:
                        return

                    yield s_common.result(retn)

        finally:
            s_glob.sync(self.fini())

class With(Share):

    def __init__(self, proxy, iden):
        Share.__init__(self, proxy, iden)
        # a with is optimized to already be entered.
        # so a fini() with no enter causes exit with error.
        self.entered = True # local to synapse.lib.coro.Fini()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc, cls, tb):
        await self.teleexit(exc is not None)

    def __enter__(self):
        return self

    def __exit__(self, exc, cls, tb):
        return s_glob.sync(self.__aexit__(exc, cls, tb))

sharetypes = {
    'share': Share,
    'genr': Genr,
    'with': With,
}

class Method:
    '''
    The telepath Method is used to provide proxy method calls.
    '''
    def __init__(self, proxy, name, share=None):
        self.name = name
        self.share = share
        self.proxy = proxy

        # act as much like a bound method as possible...
        self.__name__ = name
        self.__self__ = proxy

    @s_glob.synchelp
    async def __call__(self, *args, **kwargs):
        todo = (self.name, args, kwargs)
        return await self.proxy.task(todo, name=self.share)

class Proxy(s_coro.Fini):
    '''
    A telepath Proxy is used to call remote APIs on a shared object.

    Example:

        import synpase.telepath as s_telepath

        # open the "foo" object shared in a dmon on localhost:3344

        async def doFooThing():

            proxy = await s_telepath.openurl('tcp://127.0.0.1:3344/foo')

            valu = await proxy.getFooValu(x, y)

    The proxy ( and openurl function ) may also be used from sync code:

        proxy = s_telepath.openurl('tcp://127.0.0.1:3344/foo')

        valu = proxy.getFooValu(x, y)

    '''
    def __init__(self, link, name):
        s_coro.Fini.__init__(self)

        self.link = link
        self.name = name

        self.tasks = {}
        self.shares = {}

        self.synack = None
        self.syndone = asyncio.Event()

        self.timeout = None     # API call timeout default

        self.handlers = {
            'tele:syn': self._onTeleSyn,
            'task:fini': self._onTaskFini,
            'share:data': self._onShareData,
            'share:fini': self._onShareFini,
        }

        async def fini():
            for item in list(self.shares.values()):
                await item.fini()
            for name, task in list(self.tasks.items()):
                task.reply((False, (('IsFini', {}))))
                del self.tasks[name]
            await self.link.fini()

        self.onfini(fini)
        self.link.onfini(self.fini)

    async def _onShareFini(self, mesg):

        iden = mesg[1].get('share')
        share = self.shares.get(iden)
        if share is None:
            return

        share.txfini = False
        await share.fini()

    async def _onShareData(self, mesg):

        data = mesg[1].get('data')
        iden = mesg[1].get('share')

        share = self.shares.get(iden)
        if share is None:
            return

        await share._onShareData(data)

    async def call(self, methname, *args, **kwargs):
        '''
        Call a remote method by name.

        Args:
            methname (str): The name of the remote method.
            *args: Arguments to the method call.
            **kwargs: Keyword arguments to the method call.

        Most use cases will likely use the proxy methods directly:

        The following two are effectively the same:

            valu = proxy.getFooBar(x, y)
            valu = proxy.call('getFooBar', x, y)
        '''
        todo = (methname, args, kwargs)
        return await self.task(todo)

    async def task(self, todo, name=None):

        task = Task()

        mesg = ('task:init', {
                    'task': task.iden,
                    'todo': todo,
                    'name': name,
        })

        self.tasks[task.iden] = task

        try:

            await self.link.tx(mesg)
            return await task.result()

        finally:

            self.tasks.pop(task.iden, None)

    async def handshake(self, auth=None):

        self.link.onrx(self._onLinkRx)

        mesg = ('tele:syn', {
            'auth': auth,
            'vers': televers,
            'name': self.name,
        })

        await self.link.tx(mesg)
        await self.syndone.wait()

        vers = self.synack[1].get('vers')
        if vers[0] != televers[0]:
            raise s_exc.BadMesgVers(myver=televers, hisver=vers)

        retn = self.synack[1].get('retn')

        return s_common.result(retn)

    async def _onLinkRx(self, mesg):

        # handle a message on a link

        try:

            func = self.handlers.get(mesg[0])
            if func is None:
                logger.warning('Proxy.onLinkRx: Invalid Message: %r' % (mesg,))
                return

            await func(mesg)

        except Exception as e:
            logger.exception('Proxy.onLinkRx for %r' % (mesg,))

    async def _onTeleSyn(self, mesg):
        # handle a tele:syn message
        self.synack = mesg
        self.syndone.set()

    async def _onChanInit(self, mesg):

        # this happens when the server API returns a channel.
        # (it is also considered a task:fini since we return)
        chaniden = mesg[1].get('chan')
        taskiden = mesg[1].get('task')

        task = self.tasks.pop(taskiden, None)
        if task is None:
            return await self._sendChanFini(chaniden)

        chan = self.link.chan(chaniden)
        task.reply((True, chan))

    async def _onChanData(self, mesg):

        iden = mesg[1].get('chan')

        chan = self.link.chans.get(iden)
        if chan is None:
            return await self._sendChanFini(iden)

        retn = mesg[1].get('retn')
        chan.rx(retn)

    async def _txShareExc(self, iden):
        # send a share:fini for an unhandled share.
        await self.link.tx(
            ('share:fini', {'share': iden, 'isexc': True})
        )

    async def _onTaskFini(self, mesg):
        # handle task:fini message
        iden = mesg[1].get('task')

        task = self.tasks.pop(iden, None)
        if task is None:
            logger.warning('task:fini for invalid task: %r' % (iden,))
            return

        retn = mesg[1].get('retn')

        # fast path errors...
        if not retn[0]:
            return task.reply(retn)

        # check for special return types
        retntype = mesg[1].get('type')
        if retntype is not None:
            ctor = sharetypes.get(retntype, Share)
            retn = (True, ctor(self, retn[1]))

        return task.reply(retn)

    def __getattr__(self, name):
        meth = Method(self, name)
        setattr(self, name, meth)
        return meth

def alias(name):
    '''
    Resolve a telepath alias via ~/.syn/aliases.yaml
    '''
    path = s_common.getSynPath('aliases.yaml')
    if not os.path.isfile(path):
        return None

    conf = s_common.yamlload(path)
    return conf.get(name)

@s_glob.synchelp
async def openurl(url, **opts):
    '''
    Open a URL to a remote telepath object.

    Args:
        url (str): A telepath URL.
        **opts (dict): Telepath connect options.

    Returns:
        (synapse.telepath.Proxy): A telepath proxy object.

    The telepath proxy may then be used for sync or async calls:

        proxy = openurl(url)
        value = proxy.getFooThing()

    ... or ...

        proxy = await openurl(url)
        valu = await proxy.getFooThing()

    '''
    if url.find('://') == -1:
        newurl = alias(url)
        if newurl is None:
            raise s_exc.BadUrl(f':// not found in [{url}] and no alias found!')
        url = newurl

    info = s_urlhelp.chopurl(url)
    info.update(opts)

    host = info.get('host')
    port = info.get('port')
    name = info.get('path')[1:]

    auth = None

    user = info.get('user')
    if user is not None:
        auth = (user, {
            'passwd': info.get('passwd')
        })

    #TODO SSL

    link = await s_glob.plex.link(host, port)

    prox = Proxy(link, name)

    await prox.handshake(auth=auth)

    return prox
