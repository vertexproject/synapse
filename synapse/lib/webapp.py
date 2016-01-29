import os
import sys
import json
import argparse

import tornado
import tornado.web
import tornado.ioloop
import tornado.httpserver

import synapse.async as s_async
import synapse.dyndeps as s_dyndeps
import synapse.datamodel as s_datamodel

import synapse.lib.threads as s_threads

from synapse.eventbus import EventBus

# TODO:
# * built in rate limiting
# * modular authentication
# * support raise / etc for redirect

class BaseHand(tornado.web.RequestHandler):

    def initialize(self, **globs):
        self.globs = globs

    @tornado.web.asynchronous
    def get(self, *args):
        wapp = self.globs.get('wapp')
        boss = self.globs.get('boss')
        func = self.globs.get('func')

        perm = self.globs.get('perm')
        if perm != None:

            iden = self.get_cookie('synsess',None)
            if iden == None:
                # FIXME redirect to login? Other status?
                self.sendHttpResp(403,{},'Forbidden')
                return

        kwargs = { k:v[0].decode('utf8') for (k,v) in self.request.arguments.items() }

        boss.initJob( task=(func,args,kwargs), ondone=self._onJobDone )

    @tornado.web.asynchronous
    def post(self, *args):
        wapp = self.globs.get('wapp')
        boss = self.globs.get('boss')
        func = self.globs.get('func')

        kwargs = { k:v[0].decode('utf8') for (k,v) in self.request.arguments.items() }

        boss.initJob( task=(func,args,kwargs), ondone=self._onJobDone )

    def _onJobDone(self, job):

        # a bit of "json friendlyness"
        ret = {'status':'ok'}

        err = job[1].get('err')
        if err != None:
            ret['status'] = 'err'
            ret['err'] = job[1].get('err')

        else:
            ret['ret'] = job[1].get('ret')

        self.sendHttpResp(200, {}, ret)

    def sendHttpResp(self, code, headers, content):
        loop = self.globs.get('loop')
        loop.add_callback( self._sendHttpResp, code, headers, content)

    def _sendHttpResp(self, code, headers, retinfo):
        self.set_status(code)
        [ self.set_header(k,v) for (k,v) in headers.items() ]
        self.write(retinfo)
        self.finish()

class WebApp(EventBus,tornado.web.Application):
    '''
    The WebApp class allows easy publishing of python methods as HTTP APIs.

    Example:

        class Woot:

            def getFooByBar(self, bar):
                stuff()

        woot = Woot()
        wapp = WebApp()

        wapp.addApiPath('/v1/foo/bybar/(.*)', woot.getFooByBar )

        wapp.listen(8080)
        wapp.main()

    '''
    def __init__(self, **settings):
        EventBus.__init__(self)
        tornado.web.Application.__init__(self, **settings)

        self.loop = tornado.ioloop.IOLoop.current()
        self.serv = tornado.httpserver.HTTPServer(self)

        self.boss = s_async.Boss()

        # FIXME options
        self.boss.runBossPool(8, maxsize=128)

        self.items = {}
        self.iothr = self._runWappLoop()

        self.onfini( self._onWappFini )

    def listen(self, port, host='0.0.0.0'):
        '''
        Add a listener to the tornado HTTPServer.

        Example:

            wapp.listen(8080)

        '''
        self.serv.listen(port, host)

    def addApiPath(self, regex, func, host='.*', perm=None):
        '''
        Add a path regex to allow access to a function.

        Example:

            def getFooByBar(self, bar):
                stuff()

            wapp.addApiPath('/v1/foo/(.+)', getFooByBar)

        Notes:

            See parsetypes decorator for adding type safety

        '''
        globs = {
            'wapp':self,
            'func':func,
            'perm':perm,
            'loop':self.loop,
            'boss':self.boss,
        }
        self.add_handlers(host, [ (regex,BaseHand,globs) ])

    def addHandPath(self, regex, handler, host='.*'):
        '''
        Add a BaseHand derived handler.
        '''
        globs = {
            'wapp':self,
            'loop':self.loop,
            'boss':self.boss,
        }
        self.add_handlers(host, [ (regex,handler,globs), ] )

    def addFilePath(self, regex, path, host='.*'):
        '''
        Add a static file path ( or directory path ) to the WebApp.

        Example:

            wapp.addFilePath('/js/(.*)', '/path/to/js' )

        '''
        globs = {'path':path}
        self.add_handlers(host, [ (regex, tornado.web.StaticFileHandler, globs) ])

    @s_threads.firethread
    def _runWappLoop(self):
        self.loop.start()

    def _onWappFini(self):
        self.loop.stop()
        self.iothr.join()

    def getServBinds(self):
        '''
        Get a list of sockaddr tuples for the bound listeners.

        ( mostly used to facilitate unit testing )
        '''
        return [ s.getsockname() for s in self.serv._sockets.values() ]

    def load(self, config):
        '''
        Load API publishing info from the given config dict.

        Entries in the config define a set of objects to construct
        and methods to share via the specified URLs.

        Format:

            config = {

                'ctors':[
                    [ <name>, <dynfunc>, <args>, <kwargs> ]
                ],

                'apis':[
                    [ <regex>, <ctorname>, <methname> ]
                ]

                'paths':[
                    [ <regex>, <path> ]
                ]
            }

        Example:

            The following example creates an instance of the
            class mypkg.mymod.Woot (named "woot") and shares
            the method woot.getByFoo(foo) at /v1/woot/by/foo/<foo>

            config = {

                'ctors':[
                    [ 'woot', 'mypkg.mymod.Woot', [], {} ]
                ],

                'apis':[
                    [ '/v1/woot/by/foo/(.*)', 'woot', 'getByFoo']
                }

                'paths':[
                    [ '/static/(.*)', '/path/to/static']
                ]
            }

        '''
        # create our local items...
        for name, dynfunc, args, kwargs in config.get('ctors',()):
            self.items[name] = s_dyndeps.runDynTask( (dynfunc,args,kwargs) )

        # add our API paths...
        for path,name,meth in config.get('apis',()):

            item = self.items.get(name)
            if item == None:
                raise Exception('NoSuchFIXME')

            func = getattr(item,meth,None)
            if func == None:
                raise Exception('NoSuchFIXME')

            self.addApiPath(path, func)

        for path,filepath in config.get('paths',()):
            self.addFilePath(path,filepath)
