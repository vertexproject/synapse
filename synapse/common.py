import os

def guid():
    return os.urandom(16)

def tufo(name,**kwargs):
    return (name,kwargs)

