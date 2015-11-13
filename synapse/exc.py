
class BadUrl(Exception):pass
class BadMesgResp(Exception):pass
class BadPropValu(Exception):pass
class BadPySource(Exception):pass

class DupUser(Exception):pass
class DupRole(Exception):pass

class NoSuch(Exception):pass
class NoSuchAct(Exception):pass
class NoSuchJob(Exception):pass
class NoSuchMod(Exception):pass
class NoSuchObj(Exception):pass
class NoSuchMeth(Exception):pass
class NoSuchPeer(Exception):pass
class NoSuchProp(Exception):pass
class NoSuchPath(Exception):pass
class NoSuchSess(Exception):pass
class NoSuchUser(Exception):pass
class NoSuchRole(Exception):pass
class NoSuchProto(Exception):pass

class NoInitCore(Exception):pass # API disabled because no cortex
class NoCurrSess(Exception):pass # API requires a current session

class SidNotFound(Exception):pass
class PropNotFound(Exception):pass

class HitMaxTime(Exception):pass
class HitMaxRetry(Exception):pass

class CallError(Exception):
    '''
    Used for remote exception propigation.
    '''
    def __init__(self, mesg):
        self.mesg = mesg

        err = mesg[1].get('err')
        errmsg = mesg[1].get('errmsg')
        errfile = mesg[1].get('errfile')
        errline = mesg[1].get('errline')

        Exception.__init__(self, '%s: %s (%s:%d)' % (err,errmsg,errfile,errline))
