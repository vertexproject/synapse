import os
import sys
import json
import argparse

import tornado
import tornado.web
import tornado.ioloop
import tornado.httpserver

import synapse.async as s_async
import synapse.httpapi as s_httpapi

def getArgParser():
    p = argparse.ArgumentParser()
    p.add_argument('config', help='json config file')
    return p

def main(argv):

    p = getArgParser()
    opts = p.parse_args(argv)

    if not os.path.isfile(opts.config):
        jsinfo = s_httpapi.initconf()
        with open(opts.config,'wb') as fd:
            fd.write( json.dumps(jsinfo, indent=2, sort_keys=True).encode('utf8') )

    with open(opts.config,'rb') as fd:
        jsinfo = json.loads( fd.read().decode('utf8') )

    httpd(jsinfo,jsfile=opts.config)

def httpd(jsinfo, jsfile=None):

    api = s_httpapi.HttpApi(jsinfo, jsfile=jsfile)

    pool = jsinfo.get('pool',16)
    boss = s_async.AsyncBoss(pool=pool)

    port = jsinfo.get('port',8080)
    host = jsinfo.get('host','0.0.0.0')

    sslkey = jsinfo.get('sslkey')
    sslcert = jsinfo.get('sslcert')

    # tornado settings
    settings = {}
    if sslkey and sslcert:
        settings['ssl_options'] = {'certfile':sslcert,'keyfile':sslkey}

    app = tornado.web.Application()

    serv = tornado.httpserver.HTTPServer(app, **settings)
    serv.listen(port,address=host)

    loop = tornado.ioloop.IOLoop.current()

    # implemented as an inner class to simplify scope
    # issues with RequestHandler awareness of HttpApi.
    class HttpApiHandler(tornado.web.RequestHandler):

        @tornado.web.asynchronous
        def get(self):
            path = self.request.path
            hdrs = self.request.headers
            body = self.request.body

            job = boss.initAsyncJob()
            job.setJobTask( api.runHttpGet, path, hdrs, body )
            job.ondone( self.sendHttpResp )
            job.runInPool()

        @tornado.web.asynchronous
        def post(self):

            path = self.request.path
            hdrs = self.request.headers
            body = self.request.body

            job = boss.initAsyncJob()
            job.setJobTask( api.runHttpPost, path, hdrs, body )
            job.onerr( self.sendHttpErr )
            job.ondone( self.sendHttpResp )
            job.runInPool()

        def sendHttpErr(self, exc):
            retinfo = {'err':exc.__class__.__name__, 'msg':str(exc)}
            loop.add_callback(self._sendHttpResp, 500, {}, retinfo)

        def sendHttpResp(self, resptup):
            # *must* be called from tornado ioloop thread!
            loop.add_callback(self._sendHttpResp, *resptup)

        def _sendHttpResp(self, code, headers, retinfo):
            self.set_status(code)
            [ self.set_header(k,v) for (k,v) in headers.items() ]
            self.write(retinfo)
            self.finish()

    app.add_handlers('.*',[ ('.*',HttpApiHandler) ])
    loop.start()

if __name__ == '__main__':
    sys.exit( main( sys.argv[1:] ) )
