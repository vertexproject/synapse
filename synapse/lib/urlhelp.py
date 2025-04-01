import urllib.parse

import synapse.exc as s_exc

import synapse.lib.cache as s_cache

def chopurl(url):
    '''
    A sane "stand alone" url parser.

    Example:

        info = chopurl(url)
    '''
    ret = {}
    if url.find('://') == -1:
        raise s_exc.BadUrl(mesg=':// not found in [{}]!'.format(url))

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
            ret['passwd'] = urllib.parse.unquote(passwd)
        ret['user'] = urllib.parse.unquote(user)

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

@s_cache.memoize(size=1024)
def sanitizeUrl(url):
    '''
    Returns a URL with the password (if present) replaced with ``****``

    RFC 3986 3.2.1 'Applications should not render as clear text any data after the first colon (":") character found
    within a userinfo subcomponent unless the data after the colon is the empty string (indicating no password)'

    Essentially, replace everything between the 2nd colon (if it exists) and the first succeeding at sign.  Return the
    original string otherwise.

    Note: this depends on this being a reasonably-well formatted URI that starts with a scheme (e.g. http) and '//:'
    Failure of this condition yields the original string.
    '''
    try:
        info = chopurl(url)
    except Exception as e:
        return url
    else:
        if info.get('passwd'):
            # Rebuild the URL from info
            valu = f"{info.get('scheme')}://{info.get('user')}:****@"
            host = info.get('host')
            port = info.get('port')
            if ':' in host and port:
                valu = f"{valu}[{host}]:{port}"
            elif port:
                valu = f"{valu}{host}:{port}"
            else:
                valu = f"{valu}{host}"
            if path := info.get('path'):
                valu = f"{valu}{path}"
            if query := info.get('query'):
                parts = []
                for k, v in query.items():
                    parts.append(f'{k}={v}')
                valu = f"{valu}?{'&'.join(parts)}"
            return valu
        return url
