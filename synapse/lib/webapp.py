import os
import sys
import json
import argparse

import tornado
import tornado.web
import tornado.ioloop
import tornado.httpserver

import synapse.async as s_async
import synapse.common as s_common
import synapse.daemon as s_daemon
import synapse.lib.config as s_config

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
        if perm is not None:

            iden = self.get_cookie('synsess', None)
            if iden is None:
                # FIXME redirect to login? Other status?
                self.sendHttpResp(403, {}, 'Forbidden')
                return

        kwargs = {k: v[0].decode('utf8') for (k, v) in self.request.arguments.items()}
        if self.request.body:
            kwargs['body'] = self.request.body

        boss.initJob(task=(func, args, kwargs), ondone=self._onJobDone)

    @tornado.web.asynchronous
    def post(self, *args):
        wapp = self.globs.get('wapp')
        boss = self.globs.get('boss')
        func = self.globs.get('func')

        kwargs = {k: v[0].decode('utf8') for (k, v) in self.request.arguments.items()}
        if self.request.body:
            kwargs['body'] = self.request.body

        boss.initJob(task=(func, args, kwargs), ondone=self._onJobDone)

    def _fmtJobResp(self, job):
        """Format job results into a standard response envelope."""
        ret = {'status': 'ok'}
        err = job[1].get('err')
        if err is not None:
            ret['status'] = 'err'
            ret['err'] = job[1].get('err')
        else:
            ret['ret'] = job[1].get('ret')
        return ret

    def _onJobDone(self, job):
        ret = self._fmtJobResp(job)
        self.sendHttpResp(200, {}, ret)

    def sendHttpResp(self, code, headers, content):
        loop = self.globs.get('loop')
        loop.add_callback(self._sendHttpResp, code, headers, content)

    def _sendHttpResp(self, code, headers, retinfo):
        self.set_status(code)
        [self.set_header(k, v) for (k, v) in headers.items()]
        self.write(retinfo)
        self.finish()

class WebApp(tornado.web.Application, s_daemon.DmonConf, s_config.Config):
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
    def __init__(self, **conf):
        s_config.Config.__init__(self)
        s_daemon.DmonConf.__init__(self)

        app_config = conf.get('app', {})
        srv_config = conf.get('server', {})
        boss_config = conf.get('boss', {})
        boss_minsize = boss_config.get('minsize', 8)
        boss_maxsize = boss_config.get('maxsize', 128)

        tornado.web.Application.__init__(self, **app_config)
        self.loop = tornado.ioloop.IOLoop()
        self.serv = tornado.httpserver.HTTPServer(self, **srv_config)

        self.boss = s_async.Boss()
        self.boss.runBossPool(boss_minsize, maxsize=boss_maxsize)

        self.iothr = self._runWappLoop()

        self.onfini(self._onWappFini)

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
            'wapp': self,
            'func': func,
            'perm': perm,
            'loop': self.loop,
            'boss': self.boss,
        }
        self.add_handlers(host, [(regex, BaseHand, globs)])

    def addHandPath(self, regex, handler, host='.*', **globs):
        '''
        Add a BaseHand derived handler.
        '''
        globs.update({
            'wapp': self,
            'loop': self.loop,
            'boss': self.boss,
        })
        self.add_handlers(host, [(regex, handler, globs), ])

    def addFilePath(self, regex, path, host='.*'):
        '''
        Add a static file path ( or directory path ) to the WebApp.

        Example:

            wapp.addFilePath('/js/(.*)', '/path/to/js' )

        '''
        globs = {'path': path}
        self.add_handlers(host, [(regex, tornado.web.StaticFileHandler, globs)])

    @s_common.firethread
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
        return [s.getsockname() for s in self.serv._sockets.values()]

# FIXME This function is untested and does not currently work. Commenting out and adding an issue to make WebApp configable.
#    def loadDmonConf(self, conf):
#        '''
#        Load API publishing info from the given config dict.
#
#        Entries in the config define a set of objects to construct
#        and methods to share via the specified URLs.
#
#        Format:
#
#            config = {
#
#                'ctors':(
#                    (<name>,<evalurl>),
#                ),
#
#                'http:apis':(
#                    ( <regex>, <name>.<meth>, <props> )
#                ),
#
#                'http:paths':(
#                    ( <regex>, <path>, <props> ),
#                ),
#
#                'http:listen':(
#                    (<host>,<port>),
#                ),
#            }
#
#        Example:
#
#           The following example creates an instance of the
#           class mypkg.mymod.Woot (named "woot") and shares
#           the method woot.getByFoo(foo) at /v1/woot/by/foo/<foo>
#
#           config = {
#
#               'ctors':(
#                   ( 'woot', 'tcp://telepath.kenshoto.com/woot' ),
#                   ( 'blah', 'ctor://mypkg.mymod.Blah("haha")' ),
#               ),
#
#               'http:apis':(
#                   ( '/v1/woot/by/foo/(.*)', 'woot.getByFoo', {} ),
#               ),
#
#               'http:paths':(
#                   ( '/static/(.*)', '/path/to/static', {}),
#               )
#
#               'http:listen':(
#                   ('0.0.0.0',8080),
#               ),
#           }
#
#        Notes:
#
#            ctor:// based urls may use previous ctor names as vars
#
#            Example:
#
#            'ctors':(
#                ( 'woot', 'ctor://synapse.cortex.openurl("ram:///")' ),
#                ( 'blah', 'ctor://thing.needs.a.cortex(woot)' ),
#            )
#
#        '''
#        # add our API paths...
#       s_daemon.DmonConf.loadDmonConf(self, conf)
#
#       for path, methname, props in conf.get('http:apis', ()):
#
#           name, meth = methname.split('.', 1)
#
#           item = self.locs.get(name)
#           if item is None:
#               raise s_common.NoSuchObj(name)
#
#           func = getattr(item, meth, None)
#           if func is None:
#               raise s_common.NoSuchMeth(meth)
#
#           self.addApiPath(path, func)
#
#       for regx, path in conf.get('http:paths', ()):
#           self.addFilePath(regx, path)
#
#       for host, port in conf.get('http:listen', ()):
#            self.listen(port, host=host)
