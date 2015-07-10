from urllib.parse import urlparse, parse_qsl

import synapse.links.tcp as s_tcp
import synapse.links.local as s_local

from synapse.eventbus import EventBus

linkprotos = {
    'tcp':s_tcp.TcpRelay,
    #'local':s_local.LocalProto(),
}

def addLinkProto(name, ctor):
    '''
    Add a custom LinkProto by name.

    Example:

        class MyRelay(LinkRelay):
            # ...

        addLinkProto('mine',MyRelay())

    '''
    linkprotos[name] = ctor

def delLinkProto(name):
    '''
    Delete a LinkProto by name.

    Example:

        delLinkProto('mine')

    '''
    linkprotos.pop(name,None)

def reqLinkProto(name):
    '''
    Return a LinkProto by name or raise.
    '''
    proto = linkprotos.get(name)
    if proto == None:
        raise NoSuchLinkProto(name)
    return proto

def initLinkRelay(link):
    '''
    Construct a LinkRelay for the given link tuple.

    Example:
        relay = initLinkRelay(link)

    '''
    ctor = reqLinkProto(link[0])
    return ctor(link)

def chopLinkUrl(url):
    '''
    Parse a link tuple from a url.

    Example:

        link = chopLinkUrl('tcp://1.2.3.4:80/')

    Notes:

        * url parameters become link properties
        * user:passwd@host syntax is used for authdata

    '''
    p = urlparse(url)
    q = dict(parse_qsl(p.query))

    link = (p.scheme,{})
    if p.hostname != None:
        link[1]['host'] = p.hostname

    if p.port != None:
        link[1]['port'] = p.port

    if p.path != None:
        link[1]['path'] = p.path

    if p.username != None:
        link[1]['authinfo'] = {'user':p.username}
        if p.password != None:
            link[1]['authinfo']['passwd'] = p.password

    timeout = q.get('timeout')
    if timeout != None:
        link[1]['timeout'] = float(timeout)

    rc4key = q.get('rc4key')
    if rc4key != None:
        link[1]['rc4key'] = rc4key.encode('utf8')

    zerosig = q.get('zerosig')
    if zerosig != None:
        link[1]['zerosig'] = True

    apikey = q.get('apikey')
    if apikey != None:
        authinfo = link[1].get('authinfo')
        if authinfo == None:
            authinfo = {}
            link[1]['authinfo'] = authinfo

        authinfo['apikey'] = apikey

    return link
