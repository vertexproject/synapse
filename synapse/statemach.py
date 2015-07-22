import msgpack
import functools
import threading

def keepstate(f):
    name = f.__name__

    @functools.wraps(f)
    def callmeth(*args, **kwargs):
        ret = f(*args,**kwargs)
        # if the call doesn't exception, add state
        self = args[0]
        args = args[1:]
        self.addStateDelta(name,args,kwargs)
        return ret

    return callmeth
        
class StateMachine:
    '''
    A class which can be used to save/replay API calls to allow
    saving the "state" of an object as a sequence of calls.
    '''
    def __init__(self, statefd=None, load=True):
        self.statefd = None
        if statefd != None and load:
            self._loadStateFd(statefd)
        self.statefd = statefd

    def loadStateFd(self, fd):
        self.statefd = None
        self._loadStateFd(fd)
        self.statefd = fd

    def _loadStateFd(self, fd):
        unpk = msgpack.Unpacker(fd,use_list=0,encoding='utf8')
        for name,args,kwargs in unpk:
            meth = getattr(self,name,None)
            if meth == None:
                raise Exception('StateMachine Method Missing: %s' % (name,))

            try:
                meth(*args,**kwargs)
            except Exception as e:
                raise Exception('StateMachine Method Error (%s): %s' % (name,e))


    def addStateDelta(self, name, args, kwargs):
        if self.statefd == None:
            return

        self.statefd.write( msgpack.dumps( (name,args,kwargs), use_bin_type=True ) )
