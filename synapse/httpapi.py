import json
import time
import base64
import fnmatch
import requests
import threading
import collections

import synapse.dyndeps as s_dyndeps
import synapse.eventbus as s_eventbus
import synapse.mindmeld as s_mindmeld

from synapse.common import *

def initkey(**info):
    info.setdefault('en',True)
    info.setdefault('name',None)
    info.setdefault('roles',[])
    info.setdefault('allows',[])
    return info

def initrole(**info):
    info.setdefault('en',True)
    info.setdefault('allows',[])
    return info

def initconf():
    return {
        'port':8080,
        'host':'0.0.0.0',
        'threads':16,

        'sslkey':None,
        'sslcert':None,

        'melddir':None,     # where do we store mindmeld packages?

        'roles':{
            # <name>:{
            #     'en':True,
            #     'allows':[
            #         ('/context/v1/*',{'rate':(10,60), }),
            #     ],
            # }
            'root':{
                'en':True,
                'allows':{
                    '*':{},
                }
            },
        },

        'apikeys':{
            # <apikey>:{
            #     'en':True,
            #     'name':'woot',
            #     'roles':[],
            #     'allows':[
            #         ('/context/v1/*',{'rate':(10,60), }),
            #     ],
            # }
            guidstr():{
                'en':True,
                'name':'root',
                'roles':[],
                'allows':[
                    ('*',{}),
                ],
            },

            #None:{
                #'en':False,
                #'allows':[],
            #},
        },

        'objects':{
            # <objname>:('<ctor>',args,kwargs),
        },

        'apipaths':{
            # <path>:{'obj':<objname>,'meth':<methname>},
        },

        'filepaths':{
            # <path>:{'filepath':<path>},
        },

    }

class DupRole(Exception):pass
class DupApiKey(Exception):pass
class NoSuchApiObj(Exception):pass
class NoSuchApiKey(Exception):pass
class NoSuchApiPath(Exception):pass
class NoSuchCtor(Exception):pass

def httppath(path):
    '''
    '''
    def wraphttp(f):
        f._http_apipath = path
        return f
    return wraphttp

class HttpApi(s_eventbus.EventBus):

    def __init__(self, jsinfo=None, jsfile=None):
        if jsinfo == None:
            jsinfo = initconf()

        s_eventbus.EventBus.__init__(self)

        self.jsfile = jsfile
        self.jsinfo = jsinfo
        self.jslock = threading.Lock()

        self.objs = {}
        self.melds = {}
        self.objdefs = {}
        self.pathmeths = {}
        self.rulecache = {}      # (apikey,path):<allowinfo>

        self.jsinfo.setdefault('objects',{})
        self.jsinfo.setdefault('apikeys',{})
        self.jsinfo.setdefault('apipaths',{})
        self.jsinfo.setdefault('filepaths',{})

        melddir = self.jsinfo.get('melddir')
        if melddir != None:
            if not os.path.isdir(melddir):
                raise Exception('Invalid melddir: %s' % (melddir,))

            for filename in os.listdir(melddir):
                meldpath = os.path.join(melddir,filename)
                if not os.path.isfile(meldpath):
                    continue

                with open(meldpath,'rb') as fd:
                    b64 = fd.read().decode('utf8')
                    self._loadMeldBase64(b64)

        for name,(ctor,args,kwargs) in self.jsinfo['objects'].items():
            self._loadApiObject(name,ctor,*args,**kwargs)

        for path,info in self.jsinfo['apipaths'].items():
            objname = info.get('obj')
            methname = info.get('meth')
            self._loadApiPath(path,objname,methname)

        self.loadHttpPaths(self)

    def runHttpGet(self, path, headers, body):
        '''
        Run an HTTP GET request through the HttpApi.
        Returns a tuple of (code,headers,retinfo) for the response.

        Example:

            code,headers,retinfo = api.runHttpGet(path, hdrs, body)

        '''
        return self.runHttpPost(path, headers, body)

    def runHttpPost(self, path, headers, body):
        '''
        Run an HTTP POST request through the HttpApi.
        Returns a tuple of (code,headers,retinfo) for the response.

        Example:

            code,headers,retinfo = api.runHttpPost(path, hdrs, body)

        Notes:

            POST /path/to/api HTTP/1.1
            content-length: 43
            content-type: application/json
            apikey: asdfasdfasdfasdf

            {"args":[arg0,arg1],"kwargs":{"foo":"bar"}}

        '''
        apikey = headers.get('apikey')
        try:
            jsreq = json.loads(body.decode('utf8'))
        except Exception as e:
            return self._initErrResp(500,'BadJsonBody',msg=str(e))

        args = jsreq.get('args',())
        kwargs = jsreq.get('kwargs',{})

        return self.runHttpPath(apikey, path, *args, **kwargs)

    def _initErrResp(self, code, err, **retinfo):
        retinfo['err'] = err
        return (code,{},retinfo)

    def _initRetResp(self, code, ret, **retinfo):
        retinfo['ret'] = ret
        return (code,{},retinfo)

    def runHttpPath(self, apikey, path, *args, **kwargs):
        ruleinfo = self.getApiKeyAllow(apikey, path)
        if ruleinfo == None:
            return self._initErrResp(403,'PermDenied',msg='No Allow Rule')

        meth = self.pathmeths.get(path)
        if meth == None:
            return self._initErrResp(404, 'NoSuchApiPath', msg=path)

        try:
            return self._initRetResp(200, meth(*args,**kwargs) )
        except Exception as e:
            return self._initErrResp(200, e.__class__.__name__, msg=str(e))

    def loadHttpPaths(self, obj):
        '''
        Load any httppath decorated methods from the obj.

        Example:

            class Woot:

                @httppath('/foo/bar')
                def foobar(self):
                    return 'hi'

            w = Woot()
            api = HttpApi()
            api.loadHttpPaths(w)

        '''
        for name in dir(obj):
            meth = getattr(obj, name, None)
            path = getattr(meth, '_http_apipath', None)
            if path == None:
                continue

            self.pathmeths[path] = meth

    def _saveJsInfo(self):
        if self.jsfile == None:
            return

        js = json.dumps( self.jsinfo, indent=2, sort_keys=True)
        with open( self.jsfile, 'wb') as fd:
            fd.write( js.encode('utf8') )

    @httppath('/./loadMeldBase64')
    def loadMeldBase64(self, b64):
        '''
        Add a base64 encoded ( for json HTTP ) binary mind meld.
        '''
        meld = self._loadMeldBase64(b64)
        melddir = self.jsinfo.get('melddir')
        if melddir == None:
            return

        info = meld.getMeldDict()
        name = info.get('name')
        if name == None or not name.isalnum():
            return

        meldpath = os.path.join(melddir,'%s.meld.b64' % name)
        with open(meldpath,'wb') as fd:
            fd.write(b64.encode('utf8'))

    @httppath('/./getMindMelds')
    def getMindMelds(self):
        '''
        Return a list of meldinfo dicts for MindMelds.
        '''
        return self.melds

    def _loadMeldBase64(self, b64):
        meld = s_mindmeld.loadMeldBase64(b64)

        info = meld.getMeldDict()

        name = info.get('name')
        vers = info.get('version')

        self.melds[name] = {'name':name,'version':vers }
        return meld

    @httppath('/./getMeldInfo')
    def getMeldInfo(self, name):
        '''
        Return the info dict for a given MindMeld.
        '''
        return self.melds.get(name)

    @httppath('/./getApiKey')
    def getApiKey(self, apikey):
        '''
        Return the info tuple for an API key.

        Example:

            info = api.getApiKey(apikey)

        '''
        return self.jsinfo['apikeys'].get(apikey)

    @httppath('/./getApiKeys')
    def getApiKeys(self):
        '''
        Return a list of (apikey,info) tuples for the HttpApi keys.

        Example:

            for apikey,keyinfo in api.getApiKeys():
                dostuff()

        '''
        return [ (k,i) for (k,i) in self.jsinfo['apikeys'].items() ]

    @httppath('/./getRole')
    def getRole(self, role):
        '''
        Returns a role info dict by name ( or None ).

        Example:

            info = api.getRole('foorole')

        '''
        return self.jsinfo['roles'].get(role)

    @httppath('/./getRoles')
    def getRoles(self):
        '''
        Return a list of (name,info) tuples for the HttpApi roles.

        Example:

            for role,info in api.getRoles():
                dostuff()

        '''
        return [ (r,i) for (r,i) in self.jsinfo['roles'].items() ]

    @httppath('/./addRole')
    def addRole(self, role, en=True):
        '''
        Add a role to the HttpApi.

        Example:

            api.addRole('foorole')

        '''
        with self.jslock:
            roleinfo = self.jsinfo['roles'].get(role)
            if roleinfo != None:
                raise DupRole(role)

            roleinfo = initrole(en=en)
            self.jsinfo['roles'][role] = roleinfo
            self._saveJsInfo()

        return roleinfo

    @httppath('/./delRole')
    def delRole(self, role):
        '''
        Delete a role from the HttpApi.

        Example:

            api.delRole('foorole')

        '''
        with self.jslock:
            roleinfo = self.jsinfo['roles'].pop(role,None)
            if roleinfo == None:
                raise NoSuchRole(role)
            
            self.rulecache.clear()
            self._saveJsInfo()

    @httppath('/./addApiKey')
    def addApiKey(self, apikey, name=None, en=True):
        '''
        Add a new API key.

        Example:

            api.addApiKey(keystr,name='woot')

        '''
        with self.jslock:

            if self.jsinfo['apikeys'].get(apikey) != None:
                raise DupApiKey()

            keyinfo = initkey(en=en,name=name)
            self.jsinfo['apikeys'][apikey] = keyinfo
            self._saveJsInfo()

        return keyinfo

    @httppath('/./delApiKey')
    def delApiKey(self, apikey):
        '''
        Delete an API key.

        Example:

            api.delApiKey(apikey)

        '''
        with self.jslock:

            keyinfo = self.jsinfo['apikeys'].pop(apikey,None)
            if keyinfo == None:
                raise NoSuchApiKey(apikey)

            self._saveJsInfo()
            self.rulecache.clear()

    @httppath('/./getApiKeyAllow')
    def getApiKeyAllow(self, apikey, path):
        '''
        Returns <ruleinfo> or None for the given API key.

        Example:

            info = api.getApiKeyAllow(apikey,path)
            if info == None:
                raise NotAllowed()

            dostuff()

        '''
        cachekey = (apikey,path)
        hit = self.rulecache.get(cachekey)
        if hit != None:
            return hit

        keyinfo = self.jsinfo['apikeys'].get(apikey)
        if keyinfo == None:
            return None

        if not keyinfo.get('en'):
            return None

        for rule,info in keyinfo.get('allows',()):
            if fnmatch.fnmatch(path,rule):
                self.rulecache[cachekey] = info
                return info

        for role in keyinfo.get('roles',()):
            roleinfo = self.jsinfo['roles'].get(role)
            if roleinfo == None:
                continue

            if not roleinfo.get('en'):
                continue

            for rule,info in roleinfo.get('allows',()):
                if fnmatch.fnmatch(path,rule):
                    self.rulecache[cachekey] = info
                    return info

    @httppath('/./addRoleAllow')
    def addRoleAllow(self, role, rule, rate=None):
        '''
        Add an allow rule to a role.
        '''
        with self.jslock:
            roleinfo = self._reqRole(role)

            roleinfo['allows'].append( (rule,{'rate':rate}) )
            self.rulecache.clear()

            self._saveJsInfo()

    def _reqApiKey(self, apikey):
        keyinfo = self.jsinfo['apikeys'].get(apikey)
        if keyinfo == None:
            raise NoSuchApiKey(apikey)
        return keyinfo

    def _reqRole(self, role):
        roleinfo = self.jsinfo['roles'].get(role)
        if roleinfo == None:
            raise NoSuchRole(role)
        return roleinfo

    @httppath('/./addApiKeyAllow')
    def addApiKeyAllow(self, apikey, rule, rate=None):
        '''
        Add an allow rule to an API key.
        '''
        with self.jslock:
            keyinfo = self._reqApiKey(apikey)

            keyinfo['allows'].append( (rule,{'rate':rate}) )
            self.rulecache.clear()
            self._saveJsInfo()

    @httppath('/./addApiKeyRole')
    def addApiKeyRole(self, apikey, role):
        '''
        Grant a role to an api key.

        Example:

            api.addApiKeyRole(apikey,'foorole')

        '''
        with self.jslock:
            keyinfo = self._reqApiKey(apikey)
            roleinfo = self._reqRole(role)

            roles = keyinfo['roles']
            if role not in roles:
                roles.append(role)

            self.rulecache.clear()
            self._saveJsInfo()

    @httppath('/./delApiKeyRole')
    def delApiKeyRole(self, apikey, role):
        '''
        Revoke a role from an api key.

        Example:

            api.delApiKeyRole(apikey,'foorole')

        '''
        with self.jslock:
            keyinfo = self._reqApiKey(apikey)
            roleinfo = self._reqRole(role)

            roles = keyinfo['roles']
            if role in roles:
                roles.remove(role)

            self.rulecache.clear()
            self._saveJsInfo()

    @httppath('/./getApiObjDef')
    def getApiObjDef(self, name):
        '''
        Returns a (ctor,args,kwargs) tuple for an API object.

        Example:

            objdef = api.getApiObjDef('foo')

        '''

    @httppath('/./getApiObjDefs')
    def getApiObjDefs(self):
        '''
        Returns a list of ( name, (ctor,args,kwargs) ) tuples.

        for name,objdef in api.getApiObjDefs():
            dostuff()

        '''
        return list(self.objdefs.items())

    def _loadApiObject(self, name, ctor, *args, **kwargs):
        meth = s_dyndeps.getDynLocal(ctor)
        if meth == None:
            raise NoSuchCtor(ctor)

        obj = meth(*args,**kwargs)
        self.objs[name] = obj
        self.objdefs[name] = (ctor,args,kwargs)

        self.loadHttpPaths(obj)

        return obj

    @httppath('/./addApiObject')
    def addApiObject(self, name, ctor, *args, **kwargs):
        '''
        Add an object ctor to the HttpApi.
        '''
        self._loadApiObject(name, ctor, *args, **kwargs)
        with self.jslock:
            self.jsinfo['objects'][name] = (ctor,args,kwargs)
            self._saveJsInfo()

    @httppath('/./delApiObject')
    def delApiObject(self, name):
        '''
        Delete an object ctor from the HttpApi.
        '''
        with self.jslock:
            self.objs.pop(name,None)
            # FIXME how to pop his methods?
            self.jsinfo['objects'].pop(name,None)
            self._saveJsInfo()

    @httppath('/./addApiPath')
    def addApiPath(self, path, objname, methname):
        '''
        Add an API path to the HttpApi.

        Example:
            api.addApiObject('woot', 'foo.bar.baz')
            api.addApiPath('/v1/haha', 'woot', 'haha')

        '''
        with self.jslock:
            self._loadApiPath(path, objname, methname)
            self.jsinfo['apipaths'][path] = {'obj':objname,'meth':methname}
            self._saveJsInfo()

    @httppath('/./delApiPath')
    def delApiPath(self, path):
        '''
        Delete an API path from the HttpApi.
        '''
        with self.jslock:
            self.pathmeths.pop(path,None)
            self.jsinfo['apipaths'].pop(path,None)
            self._saveJsInfo()

    def callApiPath(self, apikey, path, *args, **kwargs):
        '''
        Call the given API and return a dict of ret/exc.
        '''
        ret = {}
        start = time.time()

        try:
            ret['ret'] = self.pathmeths.get(path)(*args,**kwargs)
        except Exception as e:
            ret['err'] = e.__class__.__name__
            ret['msg'] = str(e)

        ret['took'] = time.time() - start
        return ret

    @httppath('/./getApiKeyInfo')
    def getApiKeyInfo(self, apikey, prop):
        '''
        Return an api key property.

        Example:

            if api.getApiKeyInfo(apikey,'en'):
                print('enabled!')

        '''
        info = self._reqApiKey(apikey)
        return info.get(prop)

    @httppath('/./setApiKeyInfo')
    def setApiKeyInfo(self, apikey, prop, valu):
        '''
        Set an api key property (and save).

        Example:

            api.setApiKeyInfo(apikey, 'en', False)

        '''
        with self.jslock:
            info = self._reqApiKey(apikey)
            info[prop] = valu

            self.rulecache.clear()
            self._saveJsInfo()

    @httppath('/./getRoleInfo')
    def getRoleInfo(self, role, prop):
        '''
        Return a role property.

        Example:

            if api.getRoleInfo(role, 'en'):
                print('enabled!')

        '''
        info = self._reqApiKey(apikey)
        return info.get(prop)

    @httppath('/./setRoleInfo')
    def setRoleInfo(self, role, prop, valu):
        '''
        Set a role property (and save).

        Example:

            api.setRoleInfo(role, 'en', False)

        '''
        with self.jslock:
            info = self._reqRole(role)
            info[prop] = valu

            self.rulecache.clear()
            self._saveJsInfo()

    def _loadApiPath(self, path, objname, methname):
        obj = self.objs.get(objname)
        if obj == None:
            raise NoSuchApiObj(objname)

        meth = getattr(obj,methname,None)
        if meth == None:
            raise NoSuchApiMeth(methname)

        self.pathmeths[path] = meth

class HttpCallError(Exception):
    def __init__(self, retinfo):
        self.retinfo = retinfo
        err = retinfo.get('err')
        msg = retinfo.get('msg')
        Exception.__init__(self, '%s: %s' % (err,msg))

class HttpApiMeth:
    def __init__(self, url, apikey=None):
        self.url = url
        self.apikey = apikey
        self.headers = {}

        if self.apikey != None:
            self.headers['apikey'] = apikey

    def __call__(self, *args, **kwargs):
        data = json.dumps({'args':args,'kwargs':kwargs})
        reply = requests.post(self.url, headers=self.headers, data=data)
        retinfo = reply.json()
        if retinfo.get('err') != None:
            raise HttpCallError(retinfo)

        return retinfo.get('ret')

class HttpApiProxy:
    '''
    Pythonic HTTP API proxy which allows "object like" calling.

    Example:

        api = HttpApiProxy('https://kenshoto.com/v1/context', apikey=mykey)

        x = api.getfoo('woot')

    '''
    def __init__(self, url, apikey=None):
        self.url = url
        self.apikey = apikey
        self.apicache = {}

    def __getattr__(self, name):
        meth = self.apicache.get(name)
        if meth != None:
            return meth

        if not self.url.endswith('/'):
            name = '/' + name

        meth = HttpApiMeth(self.url + name, apikey=self.apikey)
        self.apicache[name] = meth
        return meth
