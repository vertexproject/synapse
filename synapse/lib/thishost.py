import ctypes

import synapse.glob as s_glob
import synapse.eventbus as s_eventbus

# Allows other APIs to add things to host info
thisbus = s_eventbus.EventBus()

def get(prop):
    info = getHostInfo()
    return info.get(prop)

def newHostInfo():
    return {}

def getHostInfo():
    if s_glob.hostinfo == None:
        with s_glob.lock:
            if s_glob.hostinfo == None:

                s_glob.hostinfo = newHostInfo()

                #addHostInfo( s_glob.hostinfo )

    return s_glob.hostinfo
    #info = {}
    #thisbus.fire('this:init', info)
    #return info
