class SynErr(Exception):

    def __init__(self, *args, **info):
        self.errinfo = info
        Exception.__init__(self, self._getExcMsg())

    def _getExcMsg(self):
        props = sorted(self.errinfo.items())
        displ = ' '.join(['%s=%r' % (p, v) for (p, v) in props])
        return '%s: %s' % (self.__class__.__name__, displ)

    def items(self):
        return {k: v for k, v in self.errinfo.items()}

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

##########################################################################
class NoLinkRx(SynErr):
    '''
    No onrx() has been set for the link.
    '''
    pass

##########################################################################

class CliFini(SynErr):
    '''
    Raised when the CLI is to exit.
    '''
    pass

class Retry(SynErr): pass
class NotReady(Retry): pass

class AuthDeny(SynErr): pass

class BadTypeDef(SynErr): pass
class BadPropDef(SynErr): pass
class BadThreadIden(SynErr): pass
class BadLiftValu(SynErr): pass
class BadCmprValu(SynErr): pass
class BadTypeValu(SynErr): pass
class BadIndxValu(SynErr): pass
class BadFileExt(SynErr): pass
class BadPropName(SynErr): pass
class BadCoreName(SynErr): pass
class BadCtorType(SynErr): pass
class BadMesgVers(SynErr): pass
class BadInfoValu(SynErr): pass
class BadStorValu(SynErr): pass
class BadRuleValu(SynErr): pass
class BadOperArg(SynErr): pass
class BadUrl(SynErr): pass
class BadOptValu(SynErr): pass
class BadPropValu(SynErr): pass
class BadStormSyntax(SynErr): pass
class BadSyntaxError(SynErr): pass
class BadPropConf(SynErr):
    '''
    The configuration for the property is invalid.
    '''
    pass
class BadCoreStore(SynErr):
    '''The storage layer has encountered an error'''
    pass
class BadConfValu(SynErr):
    '''
    The configuration value provided is not valid.

    This should contain the config name, valu and mesg.
    '''
    pass

class CantDelNode(SynErr): pass
class CantDelProp(SynErr): pass

class DupTypeName(SynErr): pass  # FIXME this is unused, but should we check for dup types like we check for dup props?
class DupPropName(SynErr): pass
class DupFileName(SynErr): pass
class DupIndx (SynErr): pass
class DupUserName(SynErr): pass
class DupRoleName(SynErr): pass

class HitStormLimit(SynErr): pass

class IsRuntProp(SynErr): pass

class MustBeLocal(SynErr): pass

class NoModIden(SynErr): pass
class NoSuchAct(SynErr): pass
class NoSuchOpt(SynErr): pass
class NoSuchDir(SynErr): pass
class NoSuchDyn(SynErr): pass
class NoSuchSeq(SynErr): pass
class NoSuchVar(SynErr): pass
class NoRevPath(SynErr): pass
class NoSuchCtor(SynErr): pass
class NoSuchPath(SynErr): pass
class NoSuchImpl(SynErr): pass
class NoSuchIden(SynErr): pass
class NoSuchName(SynErr): pass
class NoSuchOper(SynErr): pass
class NoSuchCmpr(SynErr): pass
class NoSuchRule(SynErr): pass
class NoSuchDecoder(SynErr): pass
class NoSuchEncoder(SynErr): pass
class NoSuchType(SynErr): pass
class NoSuchForm(SynErr): pass
class NoSuchProp(SynErr): pass
class NoSuchStor(SynErr): pass
class NoSuchObj(SynErr): pass
class NoSuchFile(SynErr): pass
class NoSuchMeth(SynErr): pass
class NoSuchLift(SynErr): pass
class NoSuchFunc(SynErr): pass
class NoSuchUser(SynErr): pass
class NoSuchRole(SynErr): pass
class NoSuchIndx(SynErr): pass

class NoCurrTask(SynErr): pass

class ReadOnlyProp(SynErr): pass
class ReqConfOpt(SynErr): pass

class AxonErr(SynErr): pass
class AxonBadChunk(AxonErr): pass
class AxonNoBlobStors(AxonErr): pass
class AxonBlobStorBsidChanged(AxonErr): pass
class AxonUnknownBsid(AxonErr): pass
class AxonUploaderFinished(AxonErr): pass
class AxonBlobStorDisagree(AxonErr): pass

class FileExists(SynErr): pass
class NoCertKey(SynErr):
    '''
    Raised when a Cert object requires a RSA Private Key
    to perform an operation and the key is not present.
    '''
    pass

class IsFini(SynErr): pass
class TimeOut(SynErr): pass
class Canceled(SynErr): pass

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

class StepTimeout(SynErr):
    '''
    Raised when a TestStep.wait() call times out.
    '''
    pass

class JobErr(SynErr):
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

class CorruptDatabase(SynErr): pass

class AlreadyInAsync(SynErr):
    '''
    Raised when an attempt to pend on getting the value back from a coroutine, when already in the event loop thread
    '''
    pass

class DbOutOfSpace(SynErr): pass

class IsReadOnly(SynErr): pass
class RecursionLimitHit(SynErr): pass
