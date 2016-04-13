import synapse.async as s_async
import synapse.eventbus as s_eventbus
import synapse.lib.service as s_service
import synapse.swarm.syntax as s_syntax

class QueryKilled(Exception):pass
class QueryCancelled(QueryKilled):pass
class QueryLimitTime(QueryKilled):pass
class QueryLimitTouch(QueryKilled):pass

# TODO: implement per-form perms
# TODO: implement per-instruction perms
# TODO: move instruction methods to other module
# TODO: runtime data model awareness
# TODO: instr to pull rest/json info and flatten to tufo form
# TODO: plugin/event based macro last-ditch parser
# TODO: objectify syntax parser to allow events/plugins
# TODO: def bytag(query,inst):
# TODO: support by queries via a different instr?
# TODO: syntax error exception classes
# TODO: optimize core selection by form
# TODO: sync/monitor data model for Cortex instances
# TODO: implement/expose unified data model

deftag = 'class.synapse.cores.common.Cortex'

def lift(query,inst):
    '''
    The "lift" instruction for the swarm query language.

    Example:

        # retrieve the foo's where bar == 10

        lift(foo:bar,10)

        # TODO FIXME STANDARD FOR TIMWINDOW SYNTAX!

        foos.that.bar/foo:bar:baz@2016,+2days#8="yermom"

        lift(foo:bar:baz,valu="yermom",timewin="2016,+2days",limit=8,from="foos.that.bar")

    '''
    args = inst[1].get('args',())
    if len(args) != 1:
        raise Exception('lift() requires a property argument :)')

    kwargs = dict(inst[1].get('kwlist',()))

    prop = args[0]

    valu = kwargs.pop('valu',None)
    limit = kwargs.pop('limit',None)
    fromtag = kwargs.get('from',deftag)

    if kwargs:
        raise Exception('lift() left over args: %r' % (kwargs,))

    mode = query.mode()
    if mode not in ('rows','tufo'):
        raise Exception('lift() mode not supported: %s' % (mode,))

    callkw = {'limit':limit,'valu':valu}
    if mode == 'rows':
        for svcfo,jobfo in query.callByTag(fromtag,'getRowsByProp',prop,**callkw):
            for data in s_async.jobret(jobfo):
                query.addData(data,svcfo=svcfo)

        return

    # TODO lift rows to issue ticks and then return in chunks for iden->tufo

    for svcfo,jobfo in query.callByTag(fromtag,'getTufosByProp',prop,**callkw):
        for data in s_async.jobret(jobfo):
            query.addData(data,svcfo=svcfo)

def opts(query,inst):
    '''
    Set various query options within an instruction.

    # FIXME macro syntax?

    %uniq=1

    opts(uniq)
    opts(foo="bar",baz=30)

    '''
    args = inst[1].get('args')
    kwlist = inst[1].get('kwlist')

    # Setting an option with no value makes it 1 (bool True)
    # to allow opts(uniq) syntax
    for name in args:
        query.setOpt(name,1)

    for name,valu in kwlist:
        query.setOpt(name,valu)

def pivot(query,inst):
    '''
    Pivot to results based on property values.

        foo:bar=10 ^foo:baz

        foo:bar=10 ^hehe:haha=foo:baz

        lift("foo:bar",valu=10) pivot("hehe:haha","foo:bar")

    '''
    if query.mode() not in ('tufo',):
        raise Exception('pivot() invalid mode: %s' % (query.mode(),))

    args = inst[1].get('args')
    kwargs = dict(inst[1].get('kwlist'))

    if len(args) not in (1,2):
        raise Exception('pivot() requires 1 or 2 args')

    dstprop = args[0]
    srcprop = dstprop
    if len(args) == 2:
        srcprop = args[1]

    fromtag = kwargs.get('from',deftag)

    vals = set()

    for tufo in query.takeData():
        valu = tufo[1].get(srcprop)
        if valu == None:
            continue

        vals.add(valu)

    for valu in vals:
        for svcfo,jobfo in query.callByTag(fromtag,'getTufosByProp',dstprop,valu=valu):
            for tufo in s_async.jobret(jobfo):
                query.addData(tufo,svcfo=svcfo)

def cant(query,inst):
    '''

    Examples:

        # macro syntax to remove results with prop foo:bar
        -foo:bar

        # macro syntax to remove results where foo:bar=10
        -foo:bar=10

        # long form syntax for the above
        must("foo:bar",valu=10)

    '''
    args = inst[1].get('args')
    kwargs = dict(inst[1].get('kwlist'))

    if len(args) != 1:
        raise Exception('cant() requires 1 property argument')

    prop = args[0]
    valu = kwargs.get('valu')

    if query.mode() == 'tufo':
        args = inst[1].get('args')
        kwargs = dict(inst[1].get('kwlist'))

        for tufo in query.takeData():
            if valu != None and tufo[1].get(prop) == valu:
                continue

            if valu == None and tufo[1].get(prop) != None:
                continue

            query.addData(tufo)

def must(query,inst):
    '''

    Examples:

        # macro syntax to require results to have foo:bar=10
        +foo:bar=10

        # long form syntax for the same.
        must("foo:bar",valu=10)

    '''
    args = inst[1].get('args')
    kwargs = dict(inst[1].get('kwlist'))

    if len(args) != 1:
        raise Exception('must() requires 1 property argument')

    prop = args[0]
    valu = kwargs.get('valu')

    if query.mode() == 'tufo':
        args = inst[1].get('args')
        kwargs = dict(inst[1].get('kwlist'))

        for tufo in query.takeData():
            if valu != None and tufo[1].get(prop) != valu:
                continue

            if valu == None and tufo[1].get(prop) == None:
                continue

            query.addData(tufo)

class Query(s_eventbus.EventBus):

    def __init__(self, runt, text, **info):
        s_eventbus.EventBus.__init__(self)
        self.text = text
        self.runt = runt
        self.info = info
        self.canc = False

        self.user = info.get('user')

        self.insts = s_syntax.parse(text)

        self.touched = 0

        self.maxtime = None
        self.maxtouch = None

        self.results = {

            'options':{
                'uniq':True,
            },

            'limits':{
                'lift':None,
                'time':None,
                'touch':None,
            },

            'data':[],
            'mode':'tufo',

        }

    def addData(self, data, svcfo=None):
        # FIXME enforce perms here?
        # FIXME enforce opts like uniq here!
        self.tick()
        self.results['data'].append(data)

    def setMode(self, mode):
        self.results['mode'] = mode

    def callByTag(self, *args, **kwargs):
        # provide direct access to the callByTag API to prevent object reaching
        return self.runt.svcprox.callByTag(*args,**kwargs)

    def setOpt(self, name, valu):
        '''
        Set a query option to the given value.
        '''
        self.results['options'][name] = valu

    def opt(self,name):
        '''
        Return the current value of a query option.
        '''
        return self.results['options'].get(name)

    def mode(self):
        '''
        Return the current query mode.
        '''
        return self.results.get('mode')

    def data(self):
        return self.results.get('data')

    def takeData(self):
        data = self.results.get('data')
        self.results['data'] = []
        return data
        # FIXME reset any uniq stuff here!

    def run(self, inst):
        '''
        Execute a swarm instruction tufo in the query context.
        '''
        func = self.runt.getInstFunc(inst[0])
        if func == None:
            raise Exception('Unknown Instruction: %s' % inst[0])

        try:
            func(self,inst)
        except Exception as e:
            raise Exception('Swarm Instr Error: %s: %s' % (inst[0],e))

    def execute(self):
        '''
        Execute the parsed swarm query instructions.
        '''
        # FIXME setup user limits
        [ self.run(i) for i in self.insts ]
        return self.results

    def cancel(self):
        '''
        Cancel the current query ( occurs at next tick() call ).
        '''
        self.canc = True

    def tick(self, touch=1):
        '''
        '''
        if self.canc:
            raise QueryCancelled()

        if self.maxtime != None and time.time() > self.maxtime:
            raise QueryLimitTime()

        self.touched += touch
        if self.maxtouch != None and self.touched > self.maxtouch:
            raise QueryLimitTouch()

class Runtime(s_eventbus.EventBus):

    def __init__(self, svcbus, **info):
        s_eventbus.EventBus.__init__(self)
        self.info = info

        self.svcbus = svcbus
        self.svcprox = s_service.SvcProxy(svcbus)

        self.insts = {}

        self.setInstFunc('opts',opts)
        self.setInstFunc('lift',lift)
        self.setInstFunc('must',must)
        self.setInstFunc('cant',cant)
        self.setInstFunc('pivot',pivot)

    def setInstFunc(self, name, func):
        '''
        Add an instruction to the 
        '''
        self.insts[name] = func

    def getInstFunc(self, name):
        return self.insts.get(name)

    def ask(self, text, **info):
        '''
        user= mode= stdin=
        '''
        query = Query(self,text,**info)
        return query.execute()

class SwarmApi:
    '''
    The SwarmApi is meant for "less trusted" exposure via telepath/svcbus.
    '''
    def __init__(self, runt):
        self.runt = runt

    def ask(self, *args, **kwargs):
        return self.runt.ask(*args,**kwargs)

