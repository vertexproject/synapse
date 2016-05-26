import imp
import logging

import synapse.eventbus as s_eventbus

logger = logging.getLogger(__name__)

class Plugins(s_eventbus.EventBus):
    '''
    Helper class for managing/calling plugins in a cortex.

    Example:

        core = s_cortex.openurl(url)

        plugs = Plugins(core)

        srccode = """

            # make plugin accessible to others by name

            _syn_plug_name = 'foo'
            _syn_plug_vers = (0,2,3)

            def onfoobar(mesg):
                dostuff( mesg[1].get('baz') )

            def _syn_plug_init( plugins ):
                plugins.on('foo:bar', onfoobar)

            def _syn_plug_fini( plugins ):
                plugins.off('foo:bar',onfoobar)

        """

        core.formTufoByProp('plugin', guid(), en=True, source=srccode)

        plugs.fire('foo:bar',baz='faz')

    '''
    def __init__(self, core, form='syn:plugin'):

        s_eventbus.EventBus.__init__(self)

        self.core = core
        self.form = form

        self.plugs = {}
        self.plugmods = {}
        self.plugfuncs = {}

        self.core.addTufoForm(form,ptype='guid')
        self.core.addTufoProp(form,'en',ptype='bool')
        self.core.addTufoProp(form,'name',ptype='str')
        self.core.addTufoProp(form,'source',ptype='str')

        self.core.on('tufo:add:%s' % (form,), self._onPlugAdd )
        self.core.on('tufo:set:%s:en' % (form,), self._onPlugSetEn )
        self.core.on('tufo:set:%s:source' % (form,), self._onPlugSetSource )

        [ self._runInitPlug(plug) for plug in core.getTufosByProp('%s:en' % form, 1) ]

        self.onfini( self._onPlugsFini )

    def _onPlugsFini(self):
        plugs = list( self.plugs.values() )
        [ self._runFiniPlug(plug) for plug in plugs ]

    def call(self, name, *args, **kwargs):
        '''
        Call a method on all loaded plugins which implement it.
        '''
        funcs = self.plugfuncs.get(name)
        if funcs == None:
            funcs = self._getPlugAttrs(name)
            self.plugfuncs[name] = funcs

        ret = []
        for func in funcs:
            try:
                ret.append( func(*args,**kwargs) )
            except Exception as e:
                logger.exception(e)

        return ret

    def _getPlugAttrs(self, name):
        ret = []
        for pmod in self.plugmods.values():
            item = getattr(pmod,name,None)
            if item == None:
                continue
            ret.append(item)
        return ret

    def _runFiniPlug(self, plug):

        iden = plug[1].get(self.form)

        oldp = self.plugs.pop(iden,None)
        pmod = self.plugmods.pop(iden,None)

        self.plugfuncs.clear()

        if pmod != None:
            fini = getattr(pmod,'_syn_plug_fini',None)
            if fini != None:
                try:
                    fini(self)
                except Exception as e:
                    logger.exception(e)

    def _runInitPlug(self, plug):
        sorc = plug[1].get('%s:source' % self.form)
        if not sorc:
            return

        self.plugfuncs.clear()
        iden = plug[1].get(self.form)
        name = 'synapse.plugins.%s' % iden

        code = compile(sorc, name, 'exec')
        pmod = imp.new_module('synapse.plugins.%s' % iden)

        exec(code,pmod.__dict__)

        init = getattr(pmod,'_syn_plug_init',None)
        if init != None:
            try:
                init(self)
            except Exception as e:
                logger.exception(e)

        self.plugs[iden] = plug
        self.plugmods[iden] = pmod

    def _runBumpPlug(self,plug):
        self._runFiniPlug(plug)
        self._runInitPlug(plug)

    def _onPlugSetSource(self, mesg):
        plug = mesg[1].get('tufo')
        if not plug[1].get('%s:en' % (self,form,)):
            return

        self._runBumpPlug(plug)

    def _onPlugSetEn(self, mesg):
        plug = mesg[1].get('tufo')

        enab = mesg[1].get('valu')
        if not enab:
            return self._runFiniPlug(plug)

        return self._runInitPlug(plug)

    def _onPlugAdd(self, mesg):
        plug = mesg[1].get('tufo')
        enab = plug[1].get('%s:en' % self.form)
        if not enab:
            return

        self._runInitPlug(plug)
