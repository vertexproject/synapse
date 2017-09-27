'''
Provides access to the synapse link protocols.
'''
import synapse.common as s_common

import synapse.lib.urlhelp as s_urlhelp

import synapse.links.ssl as s_ssl
import synapse.links.ssh as s_ssh
import synapse.links.tcp as s_tcp
import synapse.links.local as s_local

protos = {
    'tcp': s_tcp.TcpRelay,
    'ssl': s_ssl.SslRelay,
    'ssh': s_ssh.SshRelay,
    'local': s_local.LocalRelay,
}

def addLinkProto(name, ctor):
    '''
    Add a custom LinkRelay by name.

    Example:

        class MyRelay(LinkRelay):
            # ...

        addLinkProto('mine',MyRelay())

    '''
    protos[name] = ctor

def getLinkRelay(link):
    '''
    Get a LinkRelay for the given link tufo.

    Example:

        relay = getLinkRelay(link)

    '''
    proto = link[0]
    ctor = protos.get(proto)
    if ctor is None:
        raise s_common.NoSuchProto(proto)
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
    urlinfo = s_urlhelp.chopurl(url)

    scheme = urlinfo.get('scheme')

    link = (scheme, {})
    link[1]['url'] = url
    link[1]['host'] = urlinfo.get('host')
    link[1]['port'] = urlinfo.get('port')
    link[1]['path'] = urlinfo.get('path')
    link[1]['user'] = urlinfo.get('user')
    link[1]['passwd'] = urlinfo.get('passwd')

    query = urlinfo.get('query', {})

    timeout = query.pop('timeout', None)
    if timeout is not None:
        link[1]['timeout'] = float(timeout)

    poolmax = query.pop('poolmax', None)
    if poolmax is not None:
        link[1]['poolmax'] = int(poolmax)

    poolsize = query.pop('poolsize', None)
    if poolsize is not None:
        link[1]['poolsize'] = int(poolsize)

    rc4key = query.pop('rc4key', None)
    if rc4key is not None:
        link[1]['rc4key'] = rc4key.encode('utf8')

    zerosig = query.pop('zerosig', None)
    if zerosig is not None:
        link[1]['zerosig'] = True

    retry = query.pop('retry', None)
    if retry is not None:
        link[1]['retry'] = int(retry, 0)

    link[1].update(query)
    return link

def listen(url, **info):
    '''
    Chop a link url and form a listening socket.
    '''
    link = chopLinkUrl(url)
    link[1].update(info)

    relay = getLinkRelay(link)
    return relay.listen()
