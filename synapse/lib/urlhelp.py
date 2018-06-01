import synapse.exc as s_exc

def chopurl(url):
    '''
    A sane "stand alone" url parser.

    Example:

        info = chopurl(url)
    '''
    ret = {}
    if url.find('://') == -1:
        raise s_exc.BadUrl(':// not found in [{}]!'.format(url))

    scheme, remain = url.split('://', 1)
    ret['scheme'] = scheme.lower()

    # carve query params from the end
    if remain.find('?') != -1:
        query = {}
        remain, queryrem = remain.split('?', 1)

        for qkey in queryrem.split('&'):
            qval = None
            if qkey.find('=') != -1:
                qkey, qval = qkey.split('=', 1)

            query[qkey] = qval

        ret['query'] = query

    pathrem = ''
    slashoff = remain.find('/')
    if slashoff != -1:
        pathrem = remain[slashoff:]
        remain = remain[:slashoff]

    # detect user[:passwd]@netloc syntax
    if remain.find('@') != -1:
        user, remain = remain.rsplit('@', 1)
        if user.find(':') != -1:
            user, passwd = user.split(':', 1)
            ret['passwd'] = passwd

        ret['user'] = user

    # remain should be down to host[:port]

    # detect ipv6 [addr]:port syntax
    if remain.startswith('['):
        hostrem, portstr = remain.rsplit(':', 1)
        ret['port'] = int(portstr)
        ret['host'] = hostrem[1:-1]

    # detect ipv6 without port syntax
    elif remain.count(':') > 1:
        ret['host'] = remain

    # regular old host or host:port syntax
    else:

        if remain.find(':') != -1:
            remain, portstr = remain.split(':', 1)
            ret['port'] = int(portstr)

        ret['host'] = remain

    ret['path'] = pathrem
    return ret
