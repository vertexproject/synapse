'''
An RMI framework for synapse.
'''
import time
import zlib
import asyncio
import logging
import threading
import collections

import synapse.glob as s_glob
import synapse.common as s_common
import synapse.eventbus as s_eventbus

import synapse.lib.scope as s_scope
import synapse.lib.msgpack as s_msgpack
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

class Method:
    '''
    The telepath Method is used to provide proxy method calls.
    '''
    def __init__(self, proxy, name):
        self.name = name
        self.proxy = proxy

        # act as much like a bound method as possible...
        self.__name__ = name
        self.__self__ = proxy

    def __call__(self, *args, **kwargs):
        return self.proxy.call(self.name, *args, **kwargs)

class Proxy(s_eventbus.EventBus):
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

        self.link = link
        self.name = name

        self.tasks = {}
        #self.chans = {}

        self.synack = None
        self.syndone = asyncio.Event()

        self.timeout = None     # API call timeout default

        self.handlers = {
            'tele:syn': self._onTeleSyn,
            'task:fini': self._onTaskFini,
            'chan:init': self._onChanInit,
            'chan:data': self._onChanData,
            'chan:fini': self._onChanFini,
        }

    @s_glob.synchelp
    async def call(self, name, *args, **kwargs):
        '''
        Call a remote method by name.

        Args:
            name (str): The name of the remote method.
            *args: Arguments to the method call.
            **kwargs: Keyword arguments to the method call.

        Most use cases will likely use the proxy methods directly:

        The following two are effectively the same:

            valu = proxy.getFooBar(x, y)
            valu = proxy.call('getFooBar', x, y)
        '''

        task = Task()

        todo = (name, args, kwargs)
        mesg = ('task:init', {
                    'task': task.iden,
                    'todo': todo,
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
            raise s_common.BadMesgVers(myver=televers, hisver=vers)

        retn = self.synack[1].get('retn')

        return s_common.result(retn)

    async def _onLinkRx(self, mesg):
        # handle a message on a link
        try:

            func = self.handlers.get(mesg[0])
            if func is None:
                logger.warning('Proxy.onLinkRx: Invalid Message: %r' % (mesg,))
                return

            coro = func(mesg)
            if asyncio.iscoroutine(coro):
                self.link.plex.coroLoopTask(coro)

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

    async def _onChanFini(self, mesg):
        # handle a chan:fini message
        iden = mesg[1].get('chan')

        chan = self.link.chans.pop(iden, None)
        if chan is None:
            return

        chan.fini()

    async def _sendChanFini(self, iden):
        # send a chan:fini message without a chan.
        await self.link.tx(
            ('chan:fini', {'chan': iden}),
        )

    def _onTaskFini(self, mesg):
        # handle task:fini message
        iden = mesg[1].get('task')

        task = self.tasks.pop(iden, None)
        if task is None:
            print(repr(mesg))
            logger.warning('task:fini for invalid task: %r' % (iden,))
            return

        retn = mesg[1].get('retn')
        task.reply(retn)

    def __getattr__(self, name):
        meth = Method(self, name)
        setattr(self, name, meth)
        return meth

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
