
class BadUrl(Exception):pass
class BadMesgResp(Exception):pass
class BadPropValu(Exception):pass
class BadPySource(Exception):pass

class NoSuchMod(Exception):pass
class NoSuchObj(Exception):pass
class NoSuchMeth(Exception):pass
class NoSuchProp(Exception):pass
class NoSuchPath(Exception):pass
class NoSuchProto(Exception):pass

class PropNotFound(Exception):pass

class HitTimeMax(Exception):pass
class HitRetryMax(Exception):pass

class CallError(Exception):
    '''
    Used for remote exception propigation.
    '''
    def __init__(self, err, errmsg, errtb):
        self.err = err
        self.errtb = errtb
        self.errmsg = errmsg

        Exception.__init__(self, '%s: %s' % (err,errmsg))
