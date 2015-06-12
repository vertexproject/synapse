import synapse.link as s_link
import synapse.socket as s_socket

def reqValidLink(link):
    '''
    Check if the link properties are sane.
    '''
    port = link[1].get('port')
    host = link[1].get('host')

    if type(port) != int:
        raise s_link.BadLinkProp(port)

def initLinkSock(link):
    host = link[1].get('host')
    port = link[1].get('port')
    sockaddr = (host,port)
    sock = s_socket.listen(sockaddr)

    if port == 0:
        link[1]['port'] = sock.getsockname()[1]

    return sock
    
