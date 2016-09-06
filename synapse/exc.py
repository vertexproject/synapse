
class SynErr(Exception):

    def __init__(self, **info):
        self.errinfo = info
        Exception.__init__(self, self._getExcMsg() )

    def _getExcMsg(self):
        props = list(self.errinfo.items())
        props.sort()
        displ = ' '.join(['%s=%r' % (p,v) for (p,v) in props ])
        return '%s: %s' % (self.__class__.__name__,displ)

class NoSuchForm(SynErr):pass
class NoSuchType(SynErr):pass
class NoSuchProp(SynErr):pass
class NoSuchOper(SynErr):pass
class NoSuchRule(SynErr):pass


class BadTypeValu(SynErr):pass
class DupTypeName(SynErr):pass
class DupPropName(SynErr):pass
class BadPropName(SynErr):pass
class BadMesgVers(SynErr):pass

class BadUrl(Exception):pass
class BadJson(Exception):pass
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
class NoSuchImpl(Exception):pass
class NoSuchIden(Exception):pass
class NoSuchMeth(Exception):pass
class NoSuchFunc(Exception):pass
class NoSuchPeer(Exception):pass
class NoSuchPath(Exception):pass
class NoSuchSess(Exception):pass
class NoSuchUser(Exception):pass
class NoSuchTufo(Exception):pass
class NoSuchRole(Exception):pass
class NoSuchProto(Exception):pass

class NoInitCore(Exception):pass # API disabled because no cortex
class NoCurrSess(Exception):pass # API requires a current session

class SidNotFound(Exception):pass
class PropNotFound(Exception):pass

class HitMaxTime(Exception):pass
class HitMaxRetry(Exception):pass

class MustNotWait(Exception):pass   # blocking function called by no-wait thread

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

class LinkErr(Exception):

    retry = False
    def __init__(self, link, mesg=''):
        self.link = link
        Exception.__init__(self,'%s %s' % (link[1].get('url'), mesg))

class LinkRefused(LinkErr):
    retry = True

class LinkNotAuth(LinkErr):pass
