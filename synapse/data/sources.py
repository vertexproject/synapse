import sys
import code
import types
import codecs
import argparse

import tornado.httpclient

import synapse.common as s_common
import synapse.lib.ingest as s_ingest

data_sources = {
    'iana.tlds':{
        'format':'lines',
        'format:lines:lower':1,

        'http:url':'http://data.iana.org/TLD/tlds-alpha-by-domain.txt',

        'ingest':(
            ( (), { 'forms':( ('inet:fqdn', {'props':( ('sfx',{'value':1}), ) }), ) }),
        ),
    },
}

def load(name, **opts):
    '''
    Load a data object from it's original source.

    Example:

        tlds = s_sources.load('iana.tlds')

    NOTE: This most likely requires access to the internet
    '''

    info = data_sources.get(name)
    if info == None:
        raise s_common.NoSuchName(name=name)

    info = dict(info)
    info.update(opts)

    data = None

    surl = info.get('http:url')

    if surl != None:

        http = tornado.httpclient.HTTPClient()
        resp = http.fetch(surl)

        data = s_ingest.openfd(resp.buffer,**info)
    
    if isinstance(data,types.GeneratorType):
        data = list(data)

    return data

if __name__ == '__main__':

    pars = argparse.ArgumentParser(prog='sources', description='Command line tool to load data sources')

    pars.add_argument('--debug', default=False, action='store_true', help='Drop to interactive prompt to inspect data')
    pars.add_argument('--save', default=None, help='Save data to the named file in message pack format')
    pars.add_argument('--no-print', default=False, action='store_true', help='Do not print the loaded data')

    pars.add_argument('names', nargs='*', help='Ingest names to load')

    opts = pars.parse_args(sys.argv[1:])

    datas = []
    for name in opts.names:
        data = load(name)
        datas.append(data)

    if opts.save:
        with s_common.genfile(opts.save) as fd:
            fd.write( s_common.msgenpack(data) )

    if opts.debug:
        code.interact(local=locals())

    if not opts.no_print:
        print( repr(data) )
