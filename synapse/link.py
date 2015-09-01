import synapse.links.tcp as s_tcp
import synapse.links.local as s_local

from synapse.links.common import *
from synapse.eventbus import EventBus

class BadUrl(Exception):pass

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

def chopurl(url):
    '''
    A sane "stand alone" url parser.

    Example:

        info = chopurl(url)
    '''
    ret = {}
    if url.find('://') == -1:
        raise BadUrl(':// not found!')

    scheme,remain = url.split('://', 1)
    ret['scheme'] = scheme.lower()

    # carve query params from the end
    if remain.find('?') != -1:
        query = {}
        remain,queryrem = remain.split('?',1)

        for qkey in queryrem.split('&'):
            qval = None
            if qkey.find('=') != -1:
                qkey,qval = qkey.split('=',1)

            query[qkey] = qval

        ret['query'] = query

    pathrem = ''
    slashoff = remain.find('/')
    if slashoff != -1:
        pathrem = remain[slashoff:]
        remain = remain[:slashoff]

    # detect user[:passwd]@netloc syntax
    if remain.find('@') != -1:
        user, remain = remain.split('@',1)
        if user.find(':') != -1:
            user,passwd = user.split(':',1)
            ret['passwd'] = passwd

        ret['user'] = user

    # remain should be down to host[:port]

    # detect ipv6 [addr]:port syntax
    if remain.startswith('['):
        hostrem,portstr = remain.rsplit(':',1)
        ret['port'] = int( portstr )
        ret['host'] = hostrem[1:-1]

    # detect ipv6 without port syntax
    elif remain.count(':') > 1:
        ret['host'] = remain

    # regular old host or host:port syntax
    else:

        if remain.find(':') != -1:
            remain,portstr = remain.split(':',1)
            ret['port'] = int(portstr)

        ret['host'] = remain

    ret['path'] = pathrem
    return ret

def chopLinkUrl(url):
    '''
    Parse a link tuple from a url.

    Example:

        link = chopLinkUrl('tcp://1.2.3.4:80/')

    Notes:

        * url parameters become link properties
        * user:passwd@host syntax is used for authdata

    '''
    #p = urlparse(url)
    #q = dict(parse_qsl(p.query))

    urlinfo = chopurl(url)

    scheme = urlinfo.get('scheme')

    link = (scheme,{})
    link[1]['host'] = urlinfo.get('host')
    link[1]['port'] = urlinfo.get('port')
    link[1]['path'] = urlinfo.get('path')

    user = urlinfo.get('user')
    passwd = urlinfo.get('passwd')

    if user:
        link[1]['authinfo'] = {'user':user}
        if passwd:
            link[1]['authinfo']['passwd'] = passwd

    query = urlinfo.get('query',{})

    timeout = query.pop('timeout',None)
    if timeout != None:
        link[1]['timeout'] = float(timeout)

    rc4key = query.pop('rc4key',None)
    if rc4key != None:
        link[1]['rc4key'] = rc4key.encode('utf8')

    zerosig = query.pop('zerosig',None)
    if zerosig != None:
        link[1]['zerosig'] = True

    retry = query.pop('retry',None)
    if retry != None:
        link[1]['retry'] = int(retry,0)

    link[1].update(query)
    return link
