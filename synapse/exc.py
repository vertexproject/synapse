'''
Exceptions used by synapse, all inheriting from SynErr
'''

class SynErr(Exception):

    def __init__(self, *args, **info):
        self.errinfo = info
        self.errname = self.__class__.__name__
        Exception.__init__(self, self._getExcMsg())

    def _getExcMsg(self):
        props = sorted(self.errinfo.items())
        displ = ' '.join(['%s=%r' % (p, v) for (p, v) in props])
        return '%s: %s' % (self.__class__.__name__, displ)

    def _setExcMesg(self):
        '''Should be called when self.errinfo is modified.'''
        self.args = (self._getExcMsg(),)

    def __setstate__(self, state):
        '''Pickle support.'''
        super(SynErr, self).__setstate__(state)
        self._setExcMesg()

    def items(self):
        return {k: v for k, v in self.errinfo.items()}

    def get(self, name, defv=None):
        '''
        Return a value from the errinfo dict.

        Example:

            try:
                foothing()
            except SynErr as e:
                blah = e.get('blah')

        '''
        return self.errinfo.get(name, defv)

    def set(self, name, valu):
        '''
        Set a value in the errinfo dict.
        '''
        self.errinfo[name] = valu
        self._setExcMesg()

    def setdefault(self, name, valu):
        '''
        Set a value in errinfo dict if it is not already set.
        '''
        if name in self.errinfo:
            return
        self.errinfo[name] = valu
        self._setExcMesg()

    def update(self, items: dict):
        '''Update multiple items in the errinfo dict at once.'''
        self.errinfo.update(items)
        self._setExcMesg()

class StormRaise(SynErr):
    '''
    This represents a user provided exception raised in the Storm runtime. It requires a errname key.
    '''
    def __init__(self, *args, **info):
        SynErr.__init__(self, *args, **info)
        name = info.get('errname')
        if name is not None:
            self.errname = name
        else:
            raise BadArg(mesg='StormRaise must have a key errname provided')

class AuthDeny(SynErr): pass

class BackupAlreadyRunning(SynErr):
    '''
    Only one backup may be running at a time
    '''
class StormPkgRequires(SynErr): pass
class StormPkgConflicts(SynErr): pass

class BadName(SynErr): pass
class BadPkgDef(SynErr): pass
class BadCmdName(SynErr): pass
class BadCmprValu(SynErr): pass
class BadCmprType(SynErr):
    '''
    Attempt to compare two incomparable values
    '''

class BadCast(SynErr): pass
class BadConfValu(SynErr):
    '''
    The configuration value provided is not valid.

    This should contain the config name, valu and mesg.
    '''
    pass

class NeedConfValu(SynErr): pass

class BadCoreStore(SynErr):
    '''The storage layer has encountered an error'''
    pass

class BadCtorType(SynErr): pass
class BadFormDef(SynErr): pass
class BadHivePath(SynErr): pass
class BadLiftValu(SynErr): pass
class BadPropDef(SynErr): pass
class BadEdgeDef(SynErr): pass
class BadTypeDef(SynErr): pass
class BadTypeValu(SynErr): pass
class BadJsonText(SynErr): pass
class BadDataValu(SynErr):
    '''Cannot process the data as intended.'''
    pass

class BadArg(SynErr):
    ''' Improper function arguments '''
    pass

class BadState(SynErr): pass

class BadFileExt(SynErr): pass
class BadIndxValu(SynErr): pass
class BadMesgVers(SynErr): pass
class BadMesgFormat(SynErr): pass
class BadOperArg(SynErr):
    ''' Improper storm function arguments '''
    pass

class BadOptValu(SynErr): pass
class BadVersion(SynErr):
    '''Generic Bad Version exception.'''
    pass
class BadStorageVersion(SynErr):
    ''' Stored persistent data is incompatible with running software '''
    pass

class BadSyntax(SynErr): pass
class BadTag(SynErr): pass
class BadTime(SynErr): pass
class BadUrl(SynErr): pass

class TypeMismatch(SynErr): pass

class CantDelCmd(SynErr): pass
class CantDelNode(SynErr): pass
class CantDelForm(SynErr): pass
class CantDelProp(SynErr): pass
class CantDelType(SynErr): pass
class CantDelUniv(SynErr): pass
class CantDelView(SynErr): pass
class CantMergeView(SynErr): pass
class CantRevLayer(SynErr): pass
class CliFini(SynErr):
    '''
    Raised when the CLI is to exit.
    '''
    pass

class CryptoErr(SynErr):
    '''
    Raised when there is a synapse.lib.crypto error.
    '''
    pass

class BadEccExchange(CryptoErr):
    ''' Raised when there is an issue doing a ECC Key Exchange '''
    pass

class BadCertBytes(SynErr):
    '''Raised by certdir when the certificate fails to load.'''

class BadCertVerify(SynErr):
    '''Raised by certdir when there is a failure to verify a certificate context.'''

class PathExists(SynErr): pass
class DataAlreadyExists(SynErr):
    '''
    Cannot copy data to a location that already contains data
    '''
    pass

class DbOutOfSpace(SynErr): pass
class DupName(SynErr): pass
class DupIden(SynErr): pass
class DupIndx(SynErr): pass
class DupFileName(SynErr): pass
class DupFormName(SynErr): pass
class DupPropName(SynErr): pass
class DupRoleName(SynErr): pass
class DupTagPropName(SynErr): pass
class DupUserName(SynErr): pass
class DupStormSvc(SynErr): pass

class DupTypeName(SynErr):
    @classmethod
    def init(cls, name, mesg=None):
        if mesg is None:
            mesg = f'Type already exists: {name}.'
        return DupTypeName(mesg=mesg, name=name)

class DupEdgeType(SynErr):

    @classmethod
    def init(cls, edge, mesg=None):
        if mesg is None:
            (n1form, verb, n2form) = edge
            mesg = f'Edge already exists: {n1form} -({verb})> {n2form}.'
        return DupEdgeType(mesg=mesg, n1form=n1form, verb=verb, n2form=n2form)

class FileExists(SynErr): pass

class InconsistentStorage(SynErr):
    '''
    Stored persistent data is inconsistent
    '''
    pass

class IsFini(SynErr): pass
class IsReadOnly(SynErr): pass
class IsDeprLocked(SynErr): pass
class IsRuntForm(SynErr): pass

class LayerInUse(SynErr): pass

class LinkErr(SynErr): pass
class LinkBadCert(LinkErr): pass
class LinkShutDown(LinkErr): pass

class LowSpace(SynErr): pass

class NoCertKey(SynErr):
    ''' Raised when a Cert object requires a RSA Private Key to perform an operation and the key is not present.  '''
    pass
class NoSuchCert(SynErr): pass
class BadCertHost(SynErr): pass

class ModAlreadyLoaded(SynErr): pass
class MustBeJsonSafe(SynErr): pass
class NotMsgpackSafe(SynErr): pass

class NoSuchForm(SynErr):

    # new convention where exceptions with an init() class
    # method may be called to enforce normalization of message
    # contents based on variables that are relevant to the
    # exception type...
    @classmethod
    def init(cls, name, mesg=None):
        if mesg is None:
            mesg = f'No form named {name}.'
        return NoSuchForm(mesg=mesg, name=name)

class NoSuchType(SynErr):
    @classmethod
    def init(cls, name, mesg=None):
        if mesg is None:
            mesg = f'No type named {name}.'
        return NoSuchType(mesg=mesg, name=name)

class NoSuchProp(SynErr):

    @classmethod
    def init(cls, name, mesg=None):
        if mesg is None:
            mesg = f'No property named {name}.'
        return NoSuchProp(mesg=mesg, name=name)

class NoSuchEdge(SynErr):

    @classmethod
    def init(cls, edge, mesg=None):
        if mesg is None:
            (n1form, verb, n2form) = edge
            mesg = f'No edge defined for {n1form} -({verb})> {n2form}.'
        return NoSuchEdge(mesg=mesg, n1form=n1form, verb=verb, n2form=n2form)

class NoSuchAbrv(SynErr): pass
class NoSuchAct(SynErr): pass
class NoSuchAuthGate(SynErr): pass
class NoSuchCmd(SynErr): pass
class NoSuchPkg(SynErr): pass
class NoSuchCmpr(SynErr): pass
class NoSuchCond(SynErr): pass
class NoSuchCtor(SynErr): pass
class NoSuchDecoder(SynErr): pass
class NoSuchDir(SynErr): pass
class NoSuchDyn(SynErr): pass
class NoSuchEncoder(SynErr): pass
class NoSuchFile(SynErr): pass
class NoSuchFunc(SynErr): pass
class NoSuchIden(SynErr): pass
class NoSuchImpl(SynErr): pass
class NoSuchIndx(SynErr): pass
class NoSuchLayer(SynErr): pass
class NoSuchLift(SynErr): pass
class NoSuchMeth(SynErr): pass
class NoSuchName(SynErr): pass
class NoSuchObj(SynErr): pass
class NoSuchOpt(SynErr): pass
class NoSuchPath(SynErr): pass
class NoSuchPivot(SynErr): pass
class NoSuchUniv(SynErr): pass
class NoSuchRole(SynErr): pass
class NoSuchUser(SynErr): pass
class NoSuchVar(SynErr): pass
class NoSuchView(SynErr): pass
class NoSuchTagProp(SynErr): pass
class NoSuchStormSvc(SynErr): pass

class NotANumberCompared(SynErr): pass

class ParserExit(SynErr):
    ''' Raised by synapse.lib.cmd.Parser on Parser exit() '''
    pass

class DmonSpawn(SynErr):
    '''
    Raised by a dispatched telepath method that has answered the call
    using a spawned process. ( control flow that is compatible with
    aborting standard calls, generators, and async generators ).
    '''
    pass

class SchemaViolation(SynErr): pass

class SlabAlreadyOpen(SynErr): pass
class SlabInUse(SynErr): pass
class SpawnExit(SynErr): pass
class FeatureNotSupported(SynErr): pass

class HitLimit(SynErr): pass
class ReadOnlyLayer(SynErr): pass
class ReadOnlyProp(SynErr): pass
class RecursionLimitHit(SynErr): pass

class TimeOut(SynErr): pass

class Retry(SynErr): pass
class NotReady(Retry): pass

class StepTimeout(SynErr):
    '''
    Raised when a TestStep.wait() call times out.
    '''
    pass

class StormRuntimeError(SynErr): pass
class StormVarListError(StormRuntimeError): pass

class FatalErr(SynErr):
    '''
    Raised when a fatal error has occurred which an application cannot recover from.
    '''
    pass

class LmdbLock(SynErr): pass
