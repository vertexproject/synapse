
class SynErr(Exception):

    def __init__(self, *args, **info):
        self.errinfo = info
        Exception.__init__(self, self._getExcMsg())

    def _getExcMsg(self):
        props = sorted(self.errinfo.items())
        displ = ' '.join(['%s=%r' % (p, v) for (p, v) in props])
        return '%s: %s' % (self.__class__.__name__, displ)

    def items(self):
        return self.errinfo.items()

    def get(self, name):
        '''
        Return a value from the errinfo dict.

        Example:

            try:
                foothing()
            except SynErr as e:
                blah = e.get('blah')

        '''
        return self.errinfo.get(name)

class CliFini(SynErr):
    '''
    Raised when the CLI is to exit.
    '''
    pass

class AuthDeny(SynErr): pass

class NoSuchMod(SynErr): pass
class NoModIden(SynErr): pass

class NoSuchAct(SynErr): pass
class NoSuchOpt(SynErr): pass
class NoSuchDir(SynErr): pass
class NoSuchDyn(SynErr): pass
class NoSuchSeq(SynErr): pass
class NoRevPath(SynErr): pass
class NoRevAllow(SynErr): pass
class NoSuchConf(SynErr): pass
class NoSuchCtor(SynErr): pass
class NoSuchFifo(SynErr): pass
class NoSuchForm(SynErr): pass
class NoSuchPath(SynErr): pass
class NoSuchStat(SynErr): pass
class NoSuchImpl(SynErr): pass
class NoSuchName(SynErr): pass
class NoSuchTufo(SynErr): pass
class NoSuchType(SynErr): pass
class NoSuchProp(SynErr): pass
class NoSuchOper(SynErr): pass
class NoSuchCmpr(SynErr): pass
class NoSuchCore(SynErr): pass
class NoSuchRule(SynErr): pass
class NoSuchGetBy(SynErr): pass

class NoSuchDecoder(SynErr): pass
class NoSuchEncoder(SynErr): pass

class BadOperArg(SynErr): pass
class ReqConfOpt(SynErr): pass
class BadConfValu(SynErr):
    '''
    The configuration value provided is not valid.

    This should contain the config name, valu and mesg.
    '''
    pass

class BadRevValu(SynErr): pass
class BadFifoSeq(SynErr): pass
class BadTypeValu(SynErr): pass
class DupTypeName(SynErr): pass
class DupPropName(SynErr): pass
class DupFileName(SynErr): pass
class BadPropName(SynErr): pass
class BadCoreName(SynErr): pass
class BadCtorType(SynErr): pass
class BadMesgVers(SynErr): pass
class BadInfoValu(SynErr): pass
class BadStorValu(SynErr): pass
class BadRuleValu(SynErr): pass
class BadPropConf(SynErr):
    '''
    The configuration for the property is invalid.
    '''
    pass


class BadCoreStore(SynErr):
    '''The storage layer has encountered an error'''
    pass

class CantDelProp(SynErr): pass
class CantSetProp(SynErr): pass

class MustBeLocal(SynErr): pass
class MustBeProxy(SynErr): pass

class NoAuthUser(SynErr): pass

class WebAppErr(SynErr): pass

class BadUrl(Exception): pass
class BadJson(Exception): pass
class BadMesgResp(Exception): pass
class BadPropValu(SynErr): pass
class BadPySource(Exception): pass

class BadRuleSyntax(SynErr): pass
class BadSyntaxError(SynErr): pass

class TeleClientSide(SynErr): pass

class HitStormLimit(SynErr): pass

class DupOpt(Exception): pass
class DupUser(Exception): pass
class DupRole(Exception): pass

class IsRuntProp(SynErr): pass

class NoSuch(Exception): pass
class NoSuchJob(Exception): pass
class NoSuchObj(SynErr): pass
class NoSuchFile(SynErr): pass
class NoSuchIden(Exception): pass
class NoSuchMeth(SynErr): pass
class NoSuchFunc(SynErr): pass
class NoSuchPerm(SynErr): pass
class NoSuchPeer(Exception): pass
class NoSuchSess(Exception): pass
class NoSuchUser(SynErr): pass
class NoSuchRole(SynErr): pass
class NoSuchProto(Exception): pass

class NoInitCore(Exception): pass # API disabled because no cortex
class NoCurrSess(Exception): pass # API requires a current session

class SidNotFound(Exception): pass
class PropNotFound(SynErr): pass

class HitMaxTime(Exception): pass
class HitMaxRetry(Exception): pass
class HitCoreLimit(SynErr):
    ''' You've reached some limit of the storage layer.'''
    pass

class NotEnoughFree(SynErr):
    '''
    There is not enough disk space free for the required operation.
    '''
    pass

class NoWritableAxons(SynErr):
    '''
    There are no writable axons available for the required operation.
    '''
    pass

class MustNotWait(Exception): pass   # blocking function called by no-wait thread

class NoSuchEntity(SynErr): pass
class NoSuchData(SynErr): pass
class FileExists(SynErr): pass
class NotEmpty(SynErr): pass
class NotSupported(SynErr): pass

class BadAtomFile(SynErr):
    '''
    Raised when there is a internal issue with an atomfile.
    '''
    pass

class BadHeapFile(SynErr):
    '''
    Raised when there is an internal issue with a heapfile
    '''
    pass

class IsFini(Exception): pass

class JobErr(Exception):
    '''
    Used for remote exception propagation.
    '''
    def __init__(self, job):
        self.job = job

        err = job[1].get('err')
        errmsg = job[1].get('errmsg')
        errfile = job[1].get('errfile')
        errline = job[1].get('errline')

        Exception.__init__(self, '%s: %s (%s:%s)' % (err, errmsg, errfile, errline))

class LinkErr(Exception):

    retry = False
    def __init__(self, link, mesg=''):
        self.link = link
        Exception.__init__(self, '%s %s' % (link[1].get('url'), mesg))

class LinkRefused(LinkErr):
    retry = True

class LinkNotAuth(LinkErr): pass
