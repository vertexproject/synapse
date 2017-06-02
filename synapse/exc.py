
class SynErr(Exception):

    def __init__(self, *args, **info):
        self.errinfo = info
        Exception.__init__(self, self._getExcMsg() )

    def _getExcMsg(self):
        props = list(self.errinfo.items())
        props.sort()
        displ = ' '.join(['%s=%r' % (p,v) for (p,v) in props ])
        return '%s: %s' % (self.__class__.__name__,displ)

    def items(self):
        return self.errinfo.items()

class NoSuchAct(SynErr):pass
class NoSuchOpt(SynErr):pass
class NoSuchDir(SynErr):pass
class NoSuchDyn(SynErr):pass
class NoSuchMod(SynErr):pass
class NoSuchSeq(SynErr):pass
class NoSuchConf(SynErr):pass
class NoSuchForm(SynErr):pass
class NoSuchPath(SynErr):pass
class NoSuchStat(SynErr):pass
class NoSuchImpl(SynErr):pass
class NoSuchName(SynErr):pass
class NoSuchTufo(SynErr):pass
class NoSuchType(SynErr):pass
class NoSuchProp(SynErr):pass
class NoSuchOper(SynErr):pass
class NoSuchCmpr(SynErr):pass
class NoSuchCore(SynErr):pass
class NoSuchRule(SynErr):pass
class NoSuchGetBy(SynErr):pass

class NoSuchDecoder(SynErr):pass
class NoSuchEncoder(SynErr):pass

class BadOperArg(SynErr):pass
class BadTypeValu(SynErr):pass
class DupTypeName(SynErr):pass
class DupPropName(SynErr):pass
class DupFileName(SynErr):pass
class BadPropName(SynErr):pass
class BadCoreName(SynErr):pass
class BadMesgVers(SynErr):pass
class BadInfoValu(SynErr):pass
class BadStorValu(SynErr):pass

class NoAuthUser(SynErr):pass

class WebAppErr(SynErr):pass

class SyntaxError(SynErr):pass

class BadUrl(Exception):pass
class BadJson(Exception):pass
class BadMesgResp(Exception):pass
class BadPropValu(SynErr):pass
class BadPySource(Exception):pass

class HitStormLimit(SynErr):pass

class DupOpt(Exception):pass
class DupUser(Exception):pass
class DupRole(Exception):pass

class NoSuch(Exception):pass
class NoSuchJob(Exception):pass
class NoSuchObj(SynErr):pass
class NoSuchFile(Exception):pass
class NoSuchIden(Exception):pass
class NoSuchMeth(SynErr):pass
class NoSuchFunc(Exception):pass
class NoSuchPeer(Exception):pass
class NoSuchSess(Exception):pass
class NoSuchUser(SynErr):pass
class NoSuchRole(Exception):pass
class NoSuchProto(Exception):pass

class NoInitCore(Exception):pass # API disabled because no cortex
class NoCurrSess(Exception):pass # API requires a current session

class SidNotFound(Exception):pass
class PropNotFound(Exception):pass

class HitMaxTime(Exception):pass
class HitMaxRetry(Exception):pass

class NotEnoughFree(Exception):pass
class NoWritableAxons(Exception):pass

class MustNotWait(Exception):pass   # blocking function called by no-wait thread

class NoSuchEntity(SynErr):pass
class NoSuchData(SynErr):pass
class FileExists(SynErr):pass
class NotEmpty(SynErr):pass
class NotSupported(SynErr):pass

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
