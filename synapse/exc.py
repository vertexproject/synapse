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

class Retry(SynErr): pass
class TxFull(Retry): pass
class NotReady(Retry): pass

class AuthDeny(SynErr): pass

class NoSuchMod(SynErr): pass
class NoModIden(SynErr): pass

class NoCertKey(SynErr): pass

class NoSuchAct(SynErr): pass
class NoSuchOpt(SynErr): pass
class NoSuchDir(SynErr): pass
class NoSuchDyn(SynErr): pass
class NoSuchSeq(SynErr): pass
class NoRevPath(SynErr): pass
class NoRevAllow(SynErr): pass
class NoSuchAlgo(SynErr): pass
class NoSuchConf(SynErr): pass
class NoSuchCtor(SynErr): pass
class NoSuchFifo(SynErr): pass
class NoSuchForm(SynErr): pass
class NoSuchHash(SynErr): pass
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
class NoSuchIndx(SynErr): pass
class NoSuchGetBy(SynErr): pass
class NoSuchMembrane(SynErr): pass
class MembraneExists(SynErr): pass

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
class DupIndx (SynErr): pass
class BadFileExt(SynErr): pass
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
class BadSpliceMesg(SynErr):
    '''The splice message was invalid'''
    pass
class BadPropValu(SynErr): pass
class BadPySource(Exception): pass

class BadRuleSyntax(SynErr): pass
class BadSyntaxError(SynErr): pass

class TeleClientSide(SynErr): pass

class HitStormLimit(SynErr): pass

class DupOpt(Exception): pass

class DupUserName(SynErr): pass
class DupRoleName(SynErr): pass

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

class HitMaxTime(SynErr): pass
class HitMaxRetry(SynErr): pass
class HitCoreLimit(SynErr):
    ''' You've reached some limit of the storage layer.'''
    pass

class NotEnoughFree(SynErr):
    '''
    There is not enough disk space free for the required operation.
    '''
    pass

class AxonErr(SynErr): pass
class AxonIsRo(AxonErr): pass
class AxonIsClone(AxonErr): pass
class AxonNotClone(AxonErr): pass
class AxonBadChunk(AxonErr): pass

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
class NoCertKey(SynErr):
    '''
    Raised when a Cert object requires a RSA Private Key
    to perform an operation and the key is not present.
    '''
    pass

class CellUserErr(SynErr):
    '''
    Exception raised by a CellUser
    '''
    pass

class BadAtomFile(SynErr):
    '''
    Raised when there is a internal issue with an atomfile.
    '''
    pass

class IsFini(SynErr): pass
class TimeOut(SynErr): pass

class CryptoErr(SynErr):
    '''
    Raised when there is a synapse.lib.crypto error.
    '''
    pass

class BadEccExchange(CryptoErr):
    '''
    Raised when there is an issue doing a ECC Key Exchange
    '''
    pass

class RetnErr(SynErr):
    '''
    Raised when a call using the retn convention has failed.
    '''
    def __init__(self, retn):
        SynErr.__init__(self, excn=retn[0], **retn[1])

class StepTimeout(SynErr):
    '''
    Raised when a TestStep.wait() call times out.
    '''
    pass

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

class LinkTimeOut(SynErr): pass

# TODO: steal these names back for synapse/lib/net.py (and deprecate old users)
class LinkErr(SynErr):

    retry = False
    def __init__(self, link, mesg=''):
        self.link = link
        Exception.__init__(self, '%s %s' % (link[1].get('url'), mesg))

class LinkRefused(LinkErr):
    retry = True

class LinkNotAuth(LinkErr): pass

class ProtoErr(SynErr):
    '''
    There's a network protocol failure (in neuron.Sess)
    '''
    pass

class CorruptDatabase(SynErr): pass
