import synapse.exc as s_exc
import synapse.telepath as s_telepath
import synapse.datamodel as s_datamodel

import synapse.lib.base as s_base
import synapse.lib.boss as s_boss
import synapse.lib.hive as s_hive
import synapse.lib.view as s_view
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.grammar as s_grammar

class SpawnCore(s_base.Base):

    async def __anit__(self, spawninfo):

        await s_base.Base.__anit__(self)

        self.conf = {}
        self.views = {}
        self.layers = {}
        self.spawninfo = spawninfo

        self.iden = spawninfo.get('iden')
        self.dirn = spawninfo.get('dirn')

        self.stormcmds = {}
        self.stormmods = spawninfo['storm']['mods']

        for name, ctor in spawninfo['storm']['cmds']['ctors']:
            self.stormcmds[name] = ctor

        for name, cdef in spawninfo['storm']['cmds']['cdefs']:

            def ctor(argv):
                return PureCmd(cdef, argv)

            self.stormcmds[name] = ctor

        self.boss = await s_boss.Boss.anit()
        self.onfini(self.boss.fini)

        self.model = s_datamodel.Model()
        self.model.addDataModels(spawninfo.get('model'))

        self.prox = await s_telepath.openurl(f'cell://{self.dirn}')
        self.onfini(self.prox.fini)

        self.hive = await s_hive.openurl(f'cell://{self.dirn}', name='*/hive')
        self.onfini(self.hive.fini)

        # TODO cortex configured for remote auth...
        node = await self.hive.open(('auth',))
        self.auth = await s_hive.HiveAuth.anit(node)
        self.onfini(self.auth.fini)

        for layrinfo in self.spawninfo.get('layers'):

            iden = layrinfo.get('iden')
            path = ('cortex', 'layers', iden)

            ctorname = layrinfo.get('ctor')

            ctor = s_dyndeps.tryDynLocal(ctorname)

            node = await self.hive.open(path)
            layr = await ctor(self, node, readonly=True)

            self.onfini(layr)

            self.layers[iden] = layr

        for viewinfo in self.spawninfo.get('views'):

            iden = viewinfo.get('iden')
            path = ('cortex', 'views', iden)

            node = await self.hive.open(path)
            view = await s_view.View.anit(self, node)

            self.onfini(view)

            self.views[iden] = view

        # initialize pass-through methods from the telepath proxy
        self.runRuntLift = self.prox.runRuntLift

    def getStormQuery(self, text):
        '''
        Parse storm query text and return a Query object.
        '''
        query = s_grammar.Parser(text).query()
        query.init(self)
        return query

    def _logStormQuery(self, *args, **kwargs):
        pass

    def getStormCmd(self, name):
        return self.stormcmds.get(name)

    async def getStormMods(self):
        return self.stormmods

async def spawnstorm(spawninfo):

    useriden = spawninfo.get('user')
    viewiden = spawninfo.get('view')

    coreinfo = spawninfo.get('core')
    storminfo = spawninfo.get('storm')

    opts = storminfo.get('opts')
    text = storminfo.get('query')

    async with await SpawnCore.anit(coreinfo) as core:

        user = core.auth.user(useriden)
        if user is None:
            raise s_exc.NoSuchUser(iden=useriden)

        view = core.views.get(viewiden)
        if view is None:
            raise s_exc.NoSuchView(iden=viewiden)

        async for mesg in view.streamstorm(text, opts=opts, user=user):
            yield mesg
