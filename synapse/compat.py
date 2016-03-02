from __future__ import absolute_import,unicode_literals
'''
A module to isolate python version compatibility filth.
'''
import sys
import time
import base64
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

    numtypes = (int,long)
    strtypes = (str,unicode)

    def enbase64(s):
        return s.encode('base64')

    def debase64(s):
        return s.decode('base64')

    def isstr(s):
        return type(s) in (str,unicode)

    def iterbytes(byts):
        for c in byts:
            yield(ord(c))

else:
    import queue

    from io import BytesIO

    numtypes = (int,)
    strtypes = (str,)

    def enbase64(b):
        return base64.b64encode(b).decode('utf8')

    def debase64(b):
        return base64.b64decode( b.encode('utf8') )

    def isstr(s):
        return isinstance(s,str)

    def iterbytes(byts):
        return iter(byts)
