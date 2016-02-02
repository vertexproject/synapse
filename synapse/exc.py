
class BadUrl(Exception):pass
class BadMesgResp(Exception):pass
class BadPropValu(Exception):pass
class BadPySource(Exception):pass

class DupOpt(Exception):pass
class DupUser(Exception):pass
class DupRole(Exception):pass

class NoSuch(Exception):pass
class NoSuchAct(Exception):pass
class NoSuchJob(Exception):pass
class NoSuchDir(Exception):pass
class NoSuchMod(Exception):pass
class NoSuchObj(Exception):pass
class NoSuchFile(Exception):pass
class NoSuchMeth(Exception):pass
class NoSuchFunc(Exception):pass
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

class IsFini(Exception):pass

class JobErr(Exception):
    '''
    Used for remote exception propigation.
    '''
    def __init__(self, job):
        self.job = job

        err = job[1].get('err')
        errmsg = job[1].get('errmsg')
        errfile = job[1].get('errfile')
        errline = job[1].get('errline')

        Exception.__init__(self, '%s: %s (%s:%s)' % (err,errmsg,errfile,errline))

class LinkErr(Exception):pass
class LinkRefused(LinkErr):pass
class LinkNotAuth(LinkErr):pass
