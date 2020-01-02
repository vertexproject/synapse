import os

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

def joinurlinfo(info):
    '''
    Reconstructs a url from the components created by chopurl() with required keys scheme, host, path.

    Args:
         info (dict): Dictionary matching output from chopurl()

    Returns:
        (str): Reconstructed URL

    Raises:
        KeyError: If one of the required keys is not present
    '''
    comps = [info['scheme'], '://']

    user = info.get('user')
    if user is not None:
        comps.append(user)
        passwd = info.get('passwd')
        if passwd is not None:
            comps.extend([':', passwd])
        comps.append('@')

    host = info['host']
    # detect ipv6 and use [host] syntax
    if ':' in host:
        comps.extend(['[', host, ']'])
    else:
        comps.append(host)

    port = info.get('port')
    if port is not None:
        comps.extend([':', str(port)])

    comps.append(info['path'])

    query = info.get('query')
    if query is not None:
        comps.append('?')
        querystr = '&'.join([''.join([key, '=', val]) for key, val in query.items()])
        comps.append(querystr)

    return ''.join(comps)

def hidepasswd(url, replw='*****'):
    '''
    Chops the url and if a password is present replaces it.

    Args:
        url (str): URL for password replacement
        replw (str): String to replace the password with, defaults to fixed length asterisks

    Returns:
        (str): URL with replaced password, or original URL if no password was present

    Raises:
        SynErr.BadUrl: If URL is malformed for chopurl()
    '''

    info = chopurl(url)

    if info.get('passwd') is not None:
        info['passwd'] = replw
        url = joinurlinfo(info)

    return url
