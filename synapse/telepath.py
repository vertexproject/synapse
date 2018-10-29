'''
An RMI framework for synapse.
'''

import os
import asyncio
import logging
import contextlib

import synapse.exc as s_exc
import synapse.glob as s_glob
import synapse.common as s_common
import synapse.lib.base as s_base
import synapse.lib.queue as s_queue
import synapse.lib.certdir as s_certdir
import synapse.lib.threads as s_threads
import synapse.lib.urlhelp as s_urlhelp

logger = logging.getLogger(__name__)

televers = (3, 0)

class Aware:
    '''
    The telepath.Aware mixin allows shared objects to
    handle individual links managed by the Daemon.
    '''
    async def getTeleApi(self, link, mesg):
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
    def __init__(self, loop):
        self.retn = None
        self.iden = s_common.guid()
        self.done = asyncio.Event(loop=loop)

    async def result(self):
        await self.done.wait()
        return s_common.result(self.retn)

    def reply(self, retn):
        self.retn = retn
        self.done.set()

class Share(s_base.Base):
    '''
    The telepath client side of a dynamically shared object.
    '''
    async def __anit__(self, proxy, iden):
        await s_base.Base.__anit__(self)
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

    def __enter__(self):
        '''
        Convenience function to enable using Proxy objects as synchronous context managers.

        Note:
            This should never be used by synapse core code.  This is for sync client code convenience only.
        '''
        if s_threads.iden() == self.tid:
            raise s_exc.SynErr('Use of synchronous context manager in async code')
        self._ctxobj = self.schedCoroSafePend(self.__aenter__())
        return self

    def __exit__(self, *args):
        '''
        This should never be used by synapse core code.  This is for sync client code convenience only.
        '''
        return self.schedCoroSafePend(self._ctxobj.__aexit__(*args))

class Genr(Share):

    async def __anit__(self, proxy, iden):
        await Share.__anit__(self, proxy, iden)
        self.queue = await s_queue.AQueue.anit()
        self.onfini(self.queue.fini)

    async def _onShareData(self, data):
        self.queue.put(data)

    async def __aiter__(self):

        try:

            while not self.isfini:

                for retn in await self.queue.slice():
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

    async def __anit__(self, proxy, iden):
        await Share.__anit__(self, proxy, iden)
        # a with is optimized to already be entered.
        # so a fini() with no enter causes exit with error.
        self.entered = True

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

class Proxy(s_base.Base):
    '''
    A telepath Proxy is used to call remote APIs on a shared object.

    Example:

        import synapse.telepath as s_telepath

        # open the "foo" object shared in a dmon on localhost:3344

        async def doFooThing():

            proxy = await s_telepath.openurl('tcp://127.0.0.1:3344/foo')

            valu = await proxy.getFooValu(x, y)

    The proxy (and openurl function) may also be used from sync code:

        proxy = s_telepath.openurl('tcp://127.0.0.1:3344/foo')

        valu = proxy.getFooValu(x, y)

    '''
    async def __anit__(self, link, name):

        await s_base.Base.__anit__(self)
        self.tid = s_threads.iden()

        self.link = link
        self.name = name

        self.tasks = {}
        self.shares = {}

        self.synack = None
        self.syndone = asyncio.Event(loop=self.loop)

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

            del self.syndone
            await self.link.fini()

        self.onfini(fini)
        self.link.onfini(self.fini)

    def __enter__(self):
        '''
        Convenience function to enable using Proxy objects as synchronous context managers.

        Note:
            This must not be used from async code, and it should never be used in core synapse code.
        '''
        if s_threads.iden() == self.tid:
            raise s_exc.SynErr('Use of synchronous context manager in async code')
        self._ctxobj = self.schedCoroSafePend(self.__aenter__())
        return self

    def __exit__(self, *args):
        '''
        Note:
            This should never be used by core synapse code.
        '''
        return self.schedCoroSafePend(self._ctxobj.__aexit__(*args))

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
        if self.isfini:
            raise s_exc.IsFini()

        task = Task(loop=self.loop)

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
            retn = (True, await ctor.anit(self, retn[1]))

        return task.reply(retn)

    def __getattr__(self, name):
        meth = Method(self, name)
        setattr(self, name, meth)
        return meth

def alias(name):
    '''
    Resolve a telepath alias via ~/.syn/aliases.yaml

    Args:
        name (str): Name of the alias to resolve.

    Notes:
        An exact match against the aliases will always be returned first.
        If no exact match is found and the name contains a '/' in it, the
        value before the slash is looked up and the remainder of the path
        is joined to any result. This is done to support dynamic Telepath
        share names.

    Returns:
        str: The url string, if present in the alias.  None will be returned
        if there are no matches.
    '''
    path = s_common.getSynPath('aliases.yaml')
    if not os.path.isfile(path):
        return None

    conf = s_common.yamlload(path)

    # Is there an exact match - if so, return it.
    url = conf.get(name)
    if url:
        return url

    # Since telepath supports dynamic shared object access,
    # slice a name at the first '/', look up using that value
    # and then append the second value to it.
    dynname = None
    if '/' in name:
        name, dynname = name.split('/', 1)
    url = conf.get(name)
    if url and dynname:
        url = '/'.join([url, dynname])

    return url

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

    ... or ...

        async with await openurl(url) as proxy:
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
        passwd = info.get('passwd')
        auth = (user, {'passwd': passwd})

    sslctx = None
    if info.get('scheme') == 'ssl':
        certpath = info.get('certdir')
        certdir = s_certdir.CertDir(certpath)
        sslctx = certdir.getClientSSLContext()

    link = await s_glob.plex.link(host, port, ssl=sslctx)

    prox = await Proxy.anit(link, name)

    await prox.handshake(auth=auth)

    return prox
