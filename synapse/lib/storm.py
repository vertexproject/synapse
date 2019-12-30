import asyncio
import logging
import argparse
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.telepath as s_telepath

import synapse.lib.ast as s_ast
import synapse.lib.base as s_base
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.cache as s_cache
import synapse.lib.scope as s_scope
import synapse.lib.types as s_types
import synapse.lib.scrape as s_scrape
import synapse.lib.provenance as s_provenance
import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

stormcmds = (
    {
        'name': 'queue.add',
        'descr': 'Add a queue to the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name of the new queue.'}),
        ),
        'storm': '''
            $lib.queue.add($cmdopts.name)
            $lib.print("queue added: {name}", name=$cmdopts.name)
        ''',
    },
    {
        'name': 'queue.del',
        'descr': 'Remove a queue from the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name of the queue to remove.'}),
        ),
        'storm': '''
            $lib.queue.del($cmdopts.name)
            $lib.print("queue removed: {name}", name=$cmdopts.name)
        ''',
    },
    {
        'name': 'queue.list',
        'descr': 'List the queues in the cortex.',
        'storm': '''
            $lib.print('Storm queue list:')
            for $info in $lib.queue.list() {
                $name = $info.name.ljust(32)
                $lib.print("    {name}:  size: {size} offs: {offs}", name=$name, size=$info.size, offs=$info.offs)
            }
        ''',
    },
    {
        'name': 'dmon.list',
        'descr': 'List the storm daemon queries running in the cortex.',
        'cmdargs': (),
        'storm': '''
            $lib.print('Storm daemon list:')
            for $info in $lib.dmon.list() {
                $name = $info.name.ljust(20)
                $lib.print("    {iden}:  ({name}): {status}", iden=$info.iden, name=$name, status=$info.status)
            }
        ''',
    },
    {
        'name': 'feed.list',
        'descr': 'List the feed functions available in the Cortex',
        'cmdrargs': (),
        'storm': '''
            $lib.print('Storm feed list:')
            for $flinfo in $lib.feed.list() {
                $flname = $flinfo.name.ljust(30)
                $lib.print("    ({name}): {desc}", name=$flname, desc=$flinfo.desc)
            }
        '''
    },
    {
        'name': 'pkg.list',
        'descr': 'List the storm packages loaded in the cortex.',
        'cmdrargs': (),
        'storm': '''
            $pkgs = $lib.pkg.list()

            if $($pkgs.size() = 0) {

                $lib.print('No storm packages installed.')

            } else {
                $lib.print('Loaded storm packages:')
                for $pkg in $pkgs {
                    $lib.print("{name}: {vers}", name=$pkg.name.ljust(32), vers=$pkg.version)
                }
            }
        '''
    },
    {
        'name': 'pkg.del',
        'descr': 'Remove a storm package from the cortex.',
        'cmdargs': (
            ('name', {'help': 'The name (or name prefix) of the package to remove.'}),
        ),
        'storm': '''

            $pkgs = $lib.set()

            for $pkg in $lib.pkg.list() {
                if $pkg.name.startswith($cmdopts.name) {
                    $pkgs.add($pkg.name)
                }
            }

            if $($pkgs.size() = 0) {

                $lib.print('No package names match "{name}". Aborting.', name=$cmdopts.name)

            } elif $($pkgs.size() = 1) {

                $name = $pkgs.list().index(0)
                $lib.print('Removing package: {name}', name=$name)
                $lib.pkg.del($name)

            } else {

                $lib.print('Multiple package names match "{name}". Aborting.', name=$cmdopts.name)

            }
        '''
    }
)

class StormDmon(s_base.Base):
    '''
    A background storm runtime which is restarted by the cortex.
    '''
    async def __anit__(self, core, iden, ddef):

        await s_base.Base.__anit__(self)

        self.core = core
        self.iden = iden
        self.ddef = ddef

        self.task = None
        self.loop_task = None
        self.user = core.auth.user(ddef.get('user'))

        self.count = 0
        self.status = 'initializing'

        async def fini():
            if self.task is not None:
                self.task.cancel()
            if self.loop_task is not None:
                self.loop_task.cancel()

        self.onfini(fini)

    async def run(self):
        self.task = self.schedCoro(self._run())

    def pack(self):
        retn = dict(self.ddef)
        retn['count'] = self.count
        retn['status'] = self.status
        return retn

    async def _run(self):
        name = self.ddef.get('name', 'storm dmon')
        info = {'iden': self.iden, 'name': name}
        await self.core.boss.promote('storm:dmon:main', user=self.user, info=info)
        while not self.isfini:
            try:
                logger.info(f'Dmon loop starting ({self.iden})')
                synt = await self.core.boss.execute(self._innr_run(),
                                                    name='storm:dmon:loop',
                                                    user=self.user,
                                                    info=info)
                self.loop_task = synt.task
                await synt.waitfini()
            except asyncio.CancelledError:
                logger.warning(f'Dmon main cancelled ({self.iden})')
                if self.loop_task:
                    self.loop_task.cancel()
                raise
            except Exception as e:  # pragma: no cover
                logger.exception(f'Dmon error during loop task execution ({self.iden})')
                self.status = f'error: {e}'
                await self.waitfini(timeout=1)

    async def _innr_run(self):

        s_scope.set('storm:dmon', self.iden)

        text = self.ddef.get('storm')
        opts = self.ddef.get('stormopts')

        def dmonPrint(evnt):
            mesg = evnt[1].get('mesg', '')
            logger.info(f'Dmon - {self.iden} - {mesg}')

        while not self.isfini:

            try:

                self.status = 'running'
                async with await self.core.snap(user=self.user) as snap:
                    snap.on('print', dmonPrint)

                    async for nodepath in snap.storm(text, opts=opts, user=self.user):
                        # all storm tasks yield often to prevent latency
                        self.count += 1
                        await asyncio.sleep(0)

                    logger.warning(f'Dmon query exited: {self.iden}')

                    self.status = 'exited'
                    await self.waitfini(timeout=1)

            except asyncio.CancelledError as e:
                logger.warning(f'Dmon loop cancelled ({self.iden})')
                raise

            except Exception as e:
                logger.exception(f'Dmon error ({self.iden})')
                self.status = f'error: {e}'
                await self.waitfini(timeout=1)

class Runtime:
    '''
    A Runtime represents the instance of a running query.
    '''
    def __init__(self, snap, opts=None, user=None):

        if opts is None:
            opts = {}

        self.vars = {}
        self.ctors = {
            'lib': s_stormtypes.LibBase,
        }

        self.opts = opts
        self.snap = snap
        self.user = user

        self.task = asyncio.current_task()

        self.inputs = []    # [synapse.lib.node.Node(), ...]

        self.iden = s_common.guid()

        varz = self.opts.get('vars')
        if varz is not None:
            self.vars.update(varz)

        self.runtvars = set()
        self.runtvars.update(self.vars.keys())
        self.runtvars.update(self.ctors.keys())
        self.isModuleRunt = False
        self.globals = set()
        self.modulefuncs = {}

        self.proxies = {}
        self.elevated = False

    def getStormMod(self, name):
        return self.snap.getStormMod(name)

    async def getStormQuery(self, text):
        return self.snap.core.getStormQuery(text)

    async def getTeleProxy(self, url, **opts):

        flat = tuple(sorted(opts.items()))
        prox = self.proxies.get((url, flat))
        if prox is not None:
            return prox

        prox = await s_telepath.openurl(url, **opts)

        self.proxies[(url, flat)] = prox
        self.snap.onfini(prox.fini)

        return prox

    def isRuntVar(self, name):
        if name in self.runtvars:
            return True
        return False

    async def printf(self, mesg):
        return await self.snap.printf(mesg)

    async def warn(self, mesg, **info):
        return await self.snap.warn(mesg, **info)

    def elevate(self):
        self.elevated = True

    def tick(self):
        pass

    def cancel(self):
        self.task.cancel()

    def initPath(self, node):
        return s_node.Path(self, dict(self.vars), [node])

    def getOpt(self, name, defval=None):
        return self.opts.get(name, defval)

    def setOpt(self, name, valu):
        self.opts[name] = valu

    def getVar(self, name, defv=None):

        item = self.vars.get(name, s_common.novalu)
        if item is not s_common.novalu:
            return item

        ctor = self.ctors.get(name)
        if ctor is not None:
            item = ctor(self)
            self.vars[name] = item
            return item

        return defv

    def setVar(self, name, valu):
        self.vars[name] = valu

    def addInput(self, node):
        '''
        Add a Node() object as input to the query runtime.
        '''
        self.inputs.append(node)

    async def getInput(self):

        for node in self.inputs:
            yield node, self.initPath(node)

        for ndef in self.opts.get('ndefs', ()):

            node = await self.snap.getNodeByNdef(ndef)
            if node is not None:
                yield node, self.initPath(node)

        for iden in self.opts.get('idens', ()):

            buid = s_common.uhex(iden)
            if len(buid) != 32:
                raise s_exc.NoSuchIden(mesg='Iden must be 32 bytes', iden=iden)

            node = await self.snap.getNodeByBuid(buid)
            if node is not None:
                yield node, self.initPath(node)

    def reqLayerAllowed(self, perms):
        if self._allowed(perms, ask_layer=True):
            return

        perm = '.'.join(perms)
        mesg = f'User must have permission {perm} on write layer'
        raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.user.name)

    def reqAllowed(self, perms):
        '''
        Raise AuthDeny if user doesn't have global permissions and write layer permissions

        '''
        if self._allowed(perms):
            return

        perm = '.'.join(perms)
        mesg = f'User must have permission {perm}'
        raise s_exc.AuthDeny(mesg=mesg, perm=perm, user=self.user.name)

    @s_cache.memoize(size=100)
    def _allowed(self, perms, ask_layer=False):
        '''
        Note:
            Caching results is acceptable because the cache lifetime is that of a single query
        '''
        if self.user is None or self.user.admin or self.elevated:
            return True

        if ask_layer:
            return self.snap.wlyr.allowed(self.user, perms)
        else:
            return self.user.allowed(perms)

    def loadRuntVars(self, query):
        # do a quick pass to determine which vars are per-node.
        for oper in query.kids:
            for name in oper.getRuntVars(self):
                if self.isModuleRunt and isinstance(oper, s_ast.Function):
                    self.modulefuncs[name] = oper
                self.runtvars.add(name)

    async def iterStormQuery(self, query, genr=None):

        with s_provenance.claim('storm', q=query.text, user=self.user.iden):

            self.loadRuntVars(query)

            # init any options from the query
            # (but dont override our own opts)
            for name, valu in query.opts.items():
                self.opts.setdefault(name, valu)

            async for node, path in query.iterNodePaths(self, genr=genr):
                self.tick()
                yield node, path

    def canPropName(self, name):
        if name not in self.modulefuncs and name not in self.ctors:
            return True
        return False

    async def getScopeRuntime(self, query, opts=None, impd=False):
        '''
        Derive a new runt off of an existing runt. It will pass down any global level vars. It has to
        re run the oper.run function on any function opers so that it gets the correct context of
        variable values and functions.
        '''
        runt = Runtime(self.snap, user=self.user, opts=opts)
        # imported implies module level
        runt.isModuleRunt = impd
        if not impd:  # respect the import boundary

            # if we are a top level module we need to
            # push down our runtvars
            if self.isModuleRunt:
                for name in self.runtvars:
                    valu = self.vars.get(name, s_common.novalu)
                    if valu is s_common.novalu:
                        continue
                    if self.canPropName(name):
                        runt.globals.add(name)
                        runt.runtvars.add(name)
                        runt.vars[name] = valu

            # propagate down all the global variables
            for name in self.globals:
                if self.canPropName(name):
                    runt.vars[name] = self.vars[name]
                    runt.globals.add(name)
                    runt.runtvars.add(name)

            # regardless of module level, we have to reload the module functions
            # we were given so they run with the right runt. We need this so we have
            # the whole function telescoping going on, and module level variables get
            # set to the right values
            runt.modulefuncs = dict(self.modulefuncs)
            for name, oper in self.modulefuncs.items():
                runt.runtvars.add(name)
                async for item in oper.run(runt, s_ast.agen()):
                    pass  # pragma: no cover

        runt.loadRuntVars(query)
        return runt

    async def propBackGlobals(self, runt):
        '''
        From a called runt (passed in by parameter), propagate the vars we know to be global
        to the module back up into the calling runt. *Don't* propagate any functions, since
        those need the context of which runt they're being called from, and just for safety
        don't mess with the base lib object.
        '''
        for name in runt.globals:
            valu = runt.vars.get(name, s_common.novalu)
            if valu is s_common.novalu:
                continue
            if not self.canPropName(name):
                # don't override our parent's version of a function
                continue
            self.vars[name] = valu

class Parser(argparse.ArgumentParser):

    def __init__(self, prog=None, descr=None, root=None):

        if root is None:
            root = self

        self.root = root
        self.exited = False
        self.mesgs = []

        argparse.ArgumentParser.__init__(self,
                                         prog=prog,
                                         description=descr,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)

    def exit(self, status=0, message=None):
        '''
        Argparse expects exit() to be a terminal function and not return.
        As such, this function must raise an exception which will be caught
        by Cmd.hasValidOpts.
        '''
        self.exited = True
        if message is not None:
            self.mesgs.extend(message.split('\n'))
        raise s_exc.BadSyntax(mesg=message, prog=self.prog, status=status)

    def add_subparsers(self, *args, **kwargs):

        def ctor():
            return Parser(root=self.root)

        kwargs['parser_class'] = ctor
        return argparse.ArgumentParser.add_subparsers(self, *args, **kwargs)

    def _print_message(self, text, fd=None):
        '''
        Note:  this overrides an existing method in ArgumentParser
        '''
        # Since we have the async->sync->async problem, queue up and print at exit
        self.root.mesgs.extend(text.split('\n'))

class Cmd:
    '''
    A one line description of the command.

    Command usage details and long form description.

    Example:

        cmd --help

    Notes:
        Python Cmd implementers may override the ``forms`` attribute with a dictionary to provide information
        about Synapse forms which are possible input and output nodes that a Cmd may recognize.

        Example:

            ::

                {
                    'input': (
                        'inet:ipv4',
                        'tel:mob:telem',
                    ),
                    'output': (
                        'geo:place',
                    ),
                }

    '''
    name = 'cmd'
    pkgname = ''
    svciden = ''
    forms = {}

    def __init__(self, argv):
        self.opts = None
        self.argv = argv
        self.pars = self.getArgParser()

    @classmethod
    def getCmdBrief(cls):
        return cls.__doc__.strip().split('\n')[0]

    def getName(self):
        return self.name

    def getDescr(self):
        return self.__class__.__doc__

    def getArgParser(self):
        return Parser(prog=self.getName(), descr=self.getDescr())

    async def hasValidOpts(self, snap):

        self.pars.printf = snap.printf
        try:
            self.opts = self.pars.parse_args(self.argv)
        except s_exc.BadSyntax as e:
            pass
        for line in self.pars.mesgs:
            await snap.printf(line)
        return not self.pars.exited

    async def execStormCmd(self, runt, genr):
        ''' Abstract base method '''
        raise s_exc.NoSuchImpl('Subclass must implement execStormCmd')
        for item in genr:
            yield item

    def getStormEval(self, runt, name):
        '''
        Construct an evaluator function that takes a path and returns a value.
        This allows relative / absolute props and variables.
        '''
        if name.startswith('$'):
            varn = name[1:]
            def func(path):
                return path.getVar(varn, defv=None)
            return func

        if name.startswith(':'):
            prop = name[1:]
            def func(path):
                return path.node.get(prop)
            return func

        if name.startswith('.'):
            def func(path):
                return path.node.get(name)
            return func

        form = runt.snap.core.model.form(name)
        if form is not None:
            def func(path):
                if path.node.form != form:
                    return None
                return path.node.ndef[1]
            return func

        prop = runt.snap.core.model.prop(name)
        if prop is not None:
            def func(path):
                if path.node.form != prop.form:
                    return None
                return path.node.get(prop.name)
            return func

        mesg = 'Unknown prop/variable syntax'
        raise s_exc.BadSyntax(mesg=mesg, valu=name)

class PureCmd(Cmd):

    def __init__(self, cdef, argv):
        self.cdef = cdef
        Cmd.__init__(self, argv)

    def getDescr(self):
        return self.cdef.get('descr', 'no documentation provided')

    def getName(self):
        return self.cdef.get('name')

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        for name, opts in self.cdef.get('cmdargs', ()):
            pars.add_argument(name, **opts)
        return pars

    async def execStormCmd(self, runt, genr):

        text = self.cdef.get('storm')
        query = runt.snap.core.getStormQuery(text)

        cmdvars = {
            'cmdopts': vars(self.opts),
            'cmdconf': self.cdef.get('cmdconf', {})
        }

        opts = {'vars': cmdvars}
        with runt.snap.getStormRuntime(opts=opts, user=runt.user) as subr:

            async def wrapgenr():
                # wrap paths in a scope to isolate vars
                async for node, path in genr:
                    path.initframe(initvars=cmdvars, initrunt=subr)
                    yield node, path

            subr.loadRuntVars(query)

            async for node, path in subr.iterStormQuery(query, genr=wrapgenr()):
                path.finiframe()
                yield node, path

class HelpCmd(Cmd):
    '''
    List available commands and a brief description for each.
    '''
    name = 'help'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('command', nargs='?', help='Show the help output for a given command.')
        return pars

    async def execStormCmd(self, runt, genr):

        async for item in genr:
            yield item

        if not self.opts.command:
            stormcmds = sorted(runt.snap.core.getStormCmds())
            stormpkgs = await runt.snap.core.getStormPkgs()

            pkgsvcs = {}
            pkgcmds = {}
            pkgmap = {}

            for pkg in stormpkgs:
                svciden = pkg.get('svciden')
                pkgname = pkg.get('name')

                for cmd in pkg.get('commands', []):
                    pkgmap[cmd.get('name')] = pkgname

                ssvc = runt.snap.core.getStormSvc(svciden)
                if ssvc is not None:
                    pkgsvcs[pkgname] = f'{ssvc.name} ({svciden})'

            if stormcmds:
                maxlen = max(len(x[0]) for x in stormcmds)

                for name, ctor in stormcmds:
                    cmdinfo = f'{name:<{maxlen}}: {ctor.getCmdBrief()}'
                    pkgcmds.setdefault(pkgmap.get(name, 'synapse'), []).append(cmdinfo)

                await runt.printf(f'package: synapse')

                for cmd in pkgcmds.pop('synapse', []):
                    await runt.printf(cmd)

                await runt.printf('')

                for name, cmds in sorted(pkgcmds.items()):
                    svcinfo = pkgsvcs.get(name)

                    if svcinfo:
                        await runt.printf(f'service: {svcinfo}')

                    await runt.printf(f'package: {name}')

                    for cmd in cmds:
                        await runt.printf(cmd)

                    await runt.printf('')

        await runt.printf('For detailed help on any command, use <cmd> --help')

class LimitCmd(Cmd):
    '''
    Limit the number of nodes generated by the query in the given position.

    Example:

        inet:ipv4 | limit 10
    '''

    name = 'limit'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('count', type=int, help='The maximum number of nodes to yield.')
        return pars

    async def execStormCmd(self, runt, genr):

        count = 0
        async for item in genr:

            yield item
            count += 1

            if count >= self.opts.count:
                await runt.printf(f'limit reached: {self.opts.count}')
                break

class UniqCmd(Cmd):
    '''
    Filter nodes by their uniq iden values.
    When this is used a Storm pipeline, only the first instance of a
    given node is allowed through the pipeline.

    Examples:

        #badstuff +inet:ipv4 ->* | uniq

    '''

    name = 'uniq'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        return pars

    async def execStormCmd(self, runt, genr):

        buidset = set()

        async for node, path in genr:

            if node.buid in buidset:
                continue

            buidset.add(node.buid)
            yield node, path

class MaxCmd(Cmd):
    '''
    Consume nodes and yield only the one node with the highest value for a property or variable.

    Examples:

        file:bytes +#foo.bar | max :size

        file:bytes +#foo.bar | max file:bytes:size

        file:bytes +#foo.bar +.seen ($tick, $tock) = .seen | max $tick

    '''

    name = 'max'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('name')
        return pars

    async def execStormCmd(self, runt, genr):

        maxvalu = None
        maxitem = None

        func = self.getStormEval(runt, self.opts.name)

        async for node, path in genr:

            valu = func(path)
            if valu is None:
                continue

            # Specifically if the name given is a ival property,
            # we want to max on upper bound of the ival.
            prop = node.form.prop(self.opts.name)
            if prop and isinstance(prop.type, s_types.Ival):
                valu = valu[1]

            if maxvalu is None or valu > maxvalu:
                maxvalu = valu
                maxitem = (node, path)

        if maxitem:
            yield maxitem

class MinCmd(Cmd):
    '''
    Consume nodes and yield only the one node with the lowest value for a property.

    Examples:

        file:bytes +#foo.bar | min :size

        file:bytes +#foo.bar | min file:bytes:size

        file:bytes +#foo.bar +.seen ($tick, $tock) = .seen | min $tick
    '''
    name = 'min'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('name')
        return pars

    async def execStormCmd(self, runt, genr):

        minvalu = None
        minitem = None

        func = self.getStormEval(runt, self.opts.name)

        async for node, path in genr:

            valu = func(path)
            if valu is None:
                continue

            if minvalu is None or valu < minvalu:
                minvalu = valu
                minitem = (node, path)

        if minitem:
            yield minitem

class DelNodeCmd(Cmd):
    '''
    Delete nodes produced by the previous query logic.

    (no nodes are returned)

    Example

        inet:fqdn=vertex.link | delnode
    '''
    name = 'delnode'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        forcehelp = 'Force delete even if it causes broken references (requires admin).'
        pars.add_argument('--force', default=False, action='store_true', help=forcehelp)
        return pars

    async def execStormCmd(self, runt, genr):

        if self.opts.force:
            if runt.user is not None and not runt.user.admin:
                mesg = '--force requires admin privs.'
                raise s_exc.AuthDeny(mesg=mesg)

        i = 0
        async for node, path in genr:

            # make sure we can delete the tags...
            for tag in node.tags.keys():
                runt.reqLayerAllowed(('tag:del', *tag.split('.')))

            runt.reqLayerAllowed(('node:del', node.form.name))

            await node.delete(force=self.opts.force)

            i += 1
            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

        # a bit odd, but we need to be detected as a generator
        if False:
            yield

class SudoCmd(Cmd):
    '''
    Use admin privileges to bypass standard query permissions.

    Example:

        sudo | [ inet:fqdn=vertex.link ]
    '''
    name = 'sudo'

    async def execStormCmd(self, runt, genr):
        runt.reqAllowed(('storm', 'cmd', 'sudo'))
        runt.elevate()
        async for item in genr:
            yield item

# TODO
# class AddNodeCmd(Cmd):     # addnode inet:ipv4 1.2.3.4 5.6.7.8
# class DelPropCmd(Cmd):     # | delprop baz
# class SetPropCmd(Cmd):     # | setprop foo bar
# class AddTagCmd(Cmd):      # | addtag --time 2015 #hehe.haha
# class DelTagCmd(Cmd):      # | deltag #foo.bar
# class SeenCmd(Cmd):        # | seen --from <guid>update .seen and seen=(src,node).seen
# class SourcesCmd(Cmd):     # | sources ( <nodes> -> seen:ndef :source -> source )

class ReIndexCmd(Cmd):
    '''
    Use admin privileges to re index/normalize node properties.

    Example:

        foo:bar | reindex --subs

        reindex --type inet:ipv4

    NOTE: This is mostly for model updates and migrations.
          Use with caution and be very sure of what you are doing.
    '''
    name = 'reindex'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        mutx = pars.add_mutually_exclusive_group(required=True)
        mutx.add_argument('--type', default=None, help='Re-index all properties of a specified type.')
        mutx.add_argument('--subs', default=False, action='store_true', help='Re-parse and set sub props.')
        mutx.add_argument('--form-counts', default=False, action='store_true', help='Re-calculate all form counts.')
        mutx.add_argument('--fire-handler', default=None,
                          help='Fire onAdd/wasSet/runTagAdd commands for a fully qualified form/property'
                               ' or tag name on inbound nodes.')
        return pars

    async def execStormCmd(self, runt, genr):

        snap = runt.snap

        if snap.user is not None and not snap.user.admin:
            await snap.warn('reindex requires an admin')
            return

        # are we re-indexing a type?
        if self.opts.type is not None:

            # is the type also a form?
            form = snap.model.forms.get(self.opts.type)

            if form is not None:

                await snap.printf(f'reindex form: {form.name}')

                async for buid, norm in snap.xact.iterFormRows(form.name):
                    await snap.stor(form.getSetOps(buid, norm))

            for prop in snap.model.getPropsByType(self.opts.type):

                await snap.printf(f'reindex prop: {prop.full}')

                formname = prop.form.name

                async for buid, norm in snap.xact.iterPropRows(formname, prop.name):
                    await snap.stor(prop.getSetOps(buid, norm))

            return

        if self.opts.subs:

            async for node, path in genr:

                form, valu = node.ndef
                norm, info = node.form.type.norm(valu)

                subs = info.get('subs')
                if subs is not None:
                    for subn, subv in subs.items():
                        if node.form.props.get(subn):
                            await node.set(subn, subv, init=True)

                yield node, path

            return

        if self.opts.form_counts:
            await snap.printf(f'reindex form counts (full) beginning...')
            await snap.core._calcFormCounts()
            await snap.printf(f'...done')
            return

        if self.opts.fire_handler:
            obj = None
            name = None
            tname = None

            if self.opts.fire_handler.startswith('#'):
                name, _ = runt.snap.model.prop('syn:tag').type.norm(self.opts.fire_handler)
                tname = '#' + name
            else:
                obj = runt.snap.model.prop(self.opts.fire_handler)
                if obj is None:
                    raise s_exc.NoSuchProp(mesg='',
                                           name=self.opts.fire_handler)

            async for node, path in genr:
                if hasattr(obj, 'wasAdded'):
                    if node.form.full != obj.full:
                        continue
                    await obj.wasAdded(node)
                elif hasattr(obj, 'wasSet'):
                    if obj.form.name != node.form.name:
                        continue
                    valu = node.get(obj.name)
                    if valu is None:
                        continue
                    await obj.wasSet(node, valu)
                else:
                    # We're a tag...
                    valu = node.get(tname)
                    if valu is None:
                        continue
                    await runt.snap.view.runTagAdd(node, name, valu)

                yield node, path

            return


class MoveTagCmd(Cmd):
    '''
    Rename an entire tag tree and preserve time intervals.

    Example:

        movetag #foo.bar #baz.faz.bar
    '''
    name = 'movetag'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('oldtag', help='The tag tree to rename.')
        pars.add_argument('newtag', help='The new tag tree name.')
        return pars

    async def execStormCmd(self, runt, genr):
        snap = runt.snap

        nodes = [node async for node in snap.getNodesBy('syn:tag', self.opts.oldtag)]
        if not nodes:
            raise s_exc.BadOperArg(mesg='Cannot move a tag which does not exist.',
                                   oldtag=self.opts.oldtag)
        oldt = nodes[0]
        oldstr = oldt.ndef[1]
        oldsize = len(oldstr)
        oldparts = oldstr.split('.')
        noldparts = len(oldparts)

        newt = await snap.addNode('syn:tag', self.opts.newtag)
        newstr = newt.ndef[1]

        if oldstr == newstr:
            raise s_exc.BadOperArg(mesg='Cannot retag a tag to the same valu.',
                                   newtag=newstr, oldtag=oldstr)

        retag = {oldstr: newstr}

        # first we set all the syn:tag:isnow props
        async for node in snap.getNodesBy('syn:tag', self.opts.oldtag, cmpr='^='):

            tagstr = node.ndef[1]
            tagparts = tagstr.split('.')
            # Are we in the same tree?
            if tagparts[:noldparts] != oldparts:
                continue

            newtag = newstr + tagstr[oldsize:]

            newnode = await snap.addNode('syn:tag', newtag)

            olddoc = node.get('doc')
            if olddoc is not None:
                await newnode.set('doc', olddoc)

            oldtitle = node.get('title')
            if oldtitle is not None:
                await newnode.set('title', oldtitle)

            # Copy any tags over to the newnode if any are present.
            for k, v in node.tags.items():
                await newnode.addTag(k, v)

            retag[tagstr] = newtag
            await node.set('isnow', newtag)

        # now we re-tag all the nodes...
        count = 0
        async for node in snap.getNodesBy(f'#{oldstr}'):

            count += 1

            tags = list(node.tags.items())
            tags.sort(reverse=True)

            for name, valu in tags:

                newt = retag.get(name)
                if newt is None:
                    continue

                await node.delTag(name)
                await node.addTag(newt, valu=valu)

        await snap.printf(f'moved tags on {count} nodes.')

        async for node, path in genr:
            yield node, path

class SpinCmd(Cmd):
    '''
    Iterate through all query results, but do not yield any.
    This can be used to operate on many nodes without returning any.

    Example:

        foo:bar:size=20 [ +#hehe ] | spin

    '''
    name = 'spin'

    async def execStormCmd(self, runt, genr):

        if False:  # make this method an async generator function
            yield None

        i = 0

        async for node, path in genr:
            i += 1

            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

class CountCmd(Cmd):
    '''
    Iterate through query results, and print the resulting number of nodes
    which were lifted. This does yield the nodes counted.

    Example:

        foo:bar:size=20 | count

    '''
    name = 'count'

    async def execStormCmd(self, runt, genr):

        i = 0
        async for item in genr:
            yield item
            i += 1

            # Yield to other tasks occasionally
            if not i % 1000:
                await asyncio.sleep(0)

        await runt.printf(f'Counted {i} nodes.')

class IdenCmd(Cmd):
    '''
    Lift nodes by iden.

    Example:

        iden b25bc9eec7e159dce879f9ec85fb791f83b505ac55b346fcb64c3c51e98d1175 | count
    '''
    name = 'iden'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('iden', nargs='*', type=str, default=[],
                          help='Iden to lift nodes by. May be specified multiple times.')
        return pars

    async def execStormCmd(self, runt, genr):

        async for x in genr:
            yield x

        for iden in self.opts.iden:
            try:
                buid = s_common.uhex(iden)
            except Exception:
                await runt.warn(f'Failed to decode iden: [{iden}]')
                continue
            if len(buid) != 32:
                await runt.warn(f'iden must be 32 bytes [{iden}]')
                continue

            node = await runt.snap.getNodeByBuid(buid)
            if node is not None:
                yield node, runt.initPath(node)

class SleepCmd(Cmd):
    '''
    Introduce a delay between returning each result for the storm query.

    NOTE: This is mostly used for testing / debugging.

    Example:

        #foo.bar | sleep 0.5

    '''
    name = 'sleep'

    async def execStormCmd(self, runt, genr):
        async for item in genr:
            yield item
            await asyncio.sleep(self.opts.delay)

    def getArgParser(self):
        pars = Cmd.getArgParser(self)
        pars.add_argument('delay', type=float, default=1, help='Delay in floating point seconds.')
        return pars

class GraphCmd(Cmd):
    '''
    Generate a subgraph from the given input nodes and command line options.
    '''
    name = 'graph'

    def getArgParser(self):

        pars = Cmd.getArgParser(self)
        pars.add_argument('--degrees', type=int, default=1, help='How many degrees to graph out.')

        pars.add_argument('--pivot', default=[], action='append', help='Specify a storm pivot for all nodes. (must quote)')
        pars.add_argument('--filter', default=[], action='append', help='Specify a storm filter for all nodes. (must quote)')

        pars.add_argument('--form-pivot', default=[], nargs=2, action='append', help='Specify a <form> <pivot> form specific pivot.')
        pars.add_argument('--form-filter', default=[], nargs=2, action='append', help='Specify a <form> <filter> form specific filter.')

        return pars

    async def execStormCmd(self, runt, genr):

        rules = {
            'degrees': self.opts.degrees,

            'pivots': [],
            'filters': [],

            'forms': {},
        }

        for pivo in self.opts.pivot:
            rules['pivots'].append(pivo[1:-1])

        for filt in self.opts.filter:
            rules['filters'].append(filt[1:-1])

        for name, pivo in self.opts.form_pivot:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['pivots'].append(pivo[1:-1])

        for name, filt in self.opts.form_filter:

            formrule = rules['forms'].get(name)
            if formrule is None:
                formrule = {'pivots': [], 'filters': []}
                rules['forms'][name] = formrule

            formrule['filters'].append(filt[1:-1])

        subg = s_ast.SubGraph(rules)

        genr = subg.run(runt, genr)

        async for node, path in subg.run(runt, genr):
            yield node, path

class TeeCmd(Cmd):
    '''
    Execute multiple Storm queries on each node in the input stream, joining output streams together.

    Commands are executed in order they are given.

    Examples:

        # Perform a pivot out and pivot in on a inet:ivp4 node
        inet:ipv4=1.2.3.4 | tee { -> * } { <- * }

        # Also emit the inbound node
        inet:ipv4=1.2.3.4 | tee --join { -> * } { <- * }

    '''
    name = 'tee'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--join', '-j', default=False, action='store_true',
                          help='Emit inbound nodes after processing storm queries.')

        pars.add_argument('query', nargs='*',
                          help='Specify a query to execute on the input nodes.')

        return pars

    async def execStormCmd(self, runt, genr):

        if not self.opts.query:
            raise s_exc.StormRuntimeError(mesg='Tee command must take at least one query as input.',
                                          name=self.name)

        hasnodes = False
        async for node, path in genr:  # type: s_node.Node, s_node.Path
            hasnodes = True
            for text in self.opts.query:
                text = text[1:-1]
                # This does update path with any vars set in the last npath (node.storm behavior)
                async for nnode, npath in node.storm(text, user=runt.user, path=path):
                    yield nnode, npath

            if self.opts.join:
                yield node, path

        if not hasnodes:
            for text in self.opts.query:
                text = text[1:-1]
                query = await runt.getStormQuery(text)
                subr = await runt.getScopeRuntime(query)
                async for nnode, npath in subr.iterStormQuery(query):
                    yield nnode, npath

class ScrapeCmd(Cmd):
    '''
    Use textual properties of existing nodes to find other easily recognizable nodes.

    Examples:

        # Scrape properties from inbound nodes and create standalone nodes.
        inet:search:query | scrape

        # Scrape properties from inbound nodes and make edge:refs to the scraped nodes.
        inet:search:query | scrape --refs

        # Scrape only the :engine and :text props from the inbound nodes.
        inet:search:query | scrape --props text engine
    '''

    name = 'scrape'

    def getArgParser(self):
        pars = Cmd.getArgParser(self)

        pars.add_argument('--props', '-p', nargs='+', type=str, default=[],
                          help='Specify relative properties to scrape')
        pars.add_argument('--refs', '-r', default=False, action='store_true',
                          help='Create edge:refs to any scraped nodes from the source node')
        pars.add_argument('-j', '--join', default=False, action='store_true',
                          help='Include source nodes in the output of the command.')

        return pars

    async def execStormCmd(self, runt, genr):

        async for node, path in genr:  # type: s_node.Node, s_node.Path

            # repr all prop vals and try to scrape nodes from them
            reprs = node.reprs()

            # make sure any provided props are valid
            proplist = [p.strip().lstrip(':') for p in self.opts.props]
            for fprop in proplist:
                if node.form.props.get(fprop, None) is None:
                    raise s_exc.BadOptValu(mesg=f'{fprop} not a valid prop for {node.ndef[1]}',
                                           name='props', valu=self.opts.props)

            # if a list of props haven't been specified, then default to ALL of them
            if not proplist:
                proplist = [k for k in node.props.keys()]

            for prop in proplist:
                val = node.props.get(prop)
                if val is None:
                    await runt.snap.printf(f'No prop ":{prop}" for {node.ndef}')
                    continue

                # use the repr val or the system mode val as appropriate
                sval = reprs.get(prop, val)
                sval = str(sval)

                for form, valu in s_scrape.scrape(sval):
                    nnode = await node.snap.addNode(form, valu)
                    npath = path.fork(nnode)
                    yield nnode, npath

                    if self.opts.refs:
                        rnode = await node.snap.addNode('edge:refs', (node.ndef, nnode.ndef))
                        rpath = path.fork(rnode)
                        yield rnode, rpath

            if self.opts.join:
                yield node, path
