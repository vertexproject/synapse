from __future__ import absolute_import,unicode_literals
'''
A module to isolate python version compatibility filth.
'''
import os
import sys
import time
import base64
import socket
import struct
import itertools
import collections

major = sys.version_info.major
minor = sys.version_info.minor
micro = sys.version_info.micro

majmin = (major,minor)
version = (major,minor,micro)

if version < (3,0,0):
    import select

    import Queue as queue

    from cStringIO import StringIO as BytesIO

    import urllib

    # since py27 is aparently incapable of interning
    # unicode strings, we will simply nop this optimization 
    def intern(x):
        return x

    numtypes = (int,long)
    strtypes = (str,unicode)

    fmts = {
        1:'B',
        2:'<H',
        4:'<I',
        8:'<Q',
    }

    sockerrs = (socket.error,)

    def enbase64(s):
        return s.encode('base64')

    def debase64(s):
        return s.decode('base64')

    def isstr(s):
        return type(s) in (str,unicode)

    def isint(s):
        return type(s) in (int,long)

    def canstor(s):
        return type(s) in (int,long,str,unicode)

    def typeof(x):

        if isint(x):
            return int

        if isstr(x):
            return str

        return type(x)

    def iterbytes(byts):
        for c in byts:
            yield(ord(c))

    def makedirs(path,mode=0o777):
        os.makedirs(path,mode=mode)

    def to_bytes(valu, size):
        fmt = fmts.get(size)

        if fmt == None:
            raise Exception('to_bytes size not supported: %d' % (size,))

        return struct.pack(fmt,valu)

    def to_int(byts):
        fmt = fmts.get(len(byts))
        if fmt == None:
            raise Exception('to_int size not supported: %d' % (len(byts),))

        return struct.unpack(fmt,byts)[0]

    def iterzip(*args):
        return itertools.izip_longest(*args)

    def url_quote(s):
        return urllib.quote(s)

    def url_quote_plus(s):
        return urllib.quote_plus(s)


else:

    import sys
    import queue
    import builtins

    from io import BytesIO

    import urllib.parse

    intern = sys.intern

    numtypes = (int,)
    strtypes = (str,)

    sockerrs = (builtins.ConnectionError,builtins.FileNotFoundError)

    def to_bytes(valu, size):
        return valu.to_bytes(size,byteorder='little')

    def to_int(byts):
        return int.from_bytes(byts,'little')

    def enbase64(b):
        return base64.b64encode(b).decode('utf8')

    def debase64(b):
        return base64.b64decode( b.encode('utf8') )

    def isstr(s):
        return isinstance(s,str)

    def isint(s):
        return isinstance(s,int)

    def canstor(s):
        return type(s) in (int,str)

    def typeof(x):
        return type(x)

    def iterbytes(byts):
        return iter(byts)

    def makedirs(path,mode=0o777):
        os.makedirs(path,mode=mode,exist_ok=True)

    def iterzip(*args):
        return itertools.zip_longest(*args)

    def url_quote(s):
        return urllib.parse.quote(s)

    def url_quote_plus(s):
        return urllib.parse.quote_plus(s)
