import synapse.cortex as s_cortex

from synapse.tests.common import *

class StormRunTest(SynTest):

    def getStormCore(self):
        core = s_cortex.openurl('ram://')

    def prepStormCore(self, core):
        t0 = core.formTufoByProp('inet:ipv4',0)
        t1 = core.formTufoByProp('inet:ipv4',0x7f000001)
        t2 = core.formTufoByProp('inet:ipv4',0x01020304)

        core.addTufoTag(t0,'omit.cmn')
        core.addTufoTag(t1,'omit.cmn')

        t3 = core.formTufoByProp('dns:a','woot.com/1.2.3.4')
        t4 = core.formTufoByProp('dns:a','vertex.link/127.0.0.1')
        t5 = core.formTufoByProp('dns:a','woot.com/127.0.0.1')

        t6 = core.formTufoByProp('inet:fqdn','woot.com')
        t7 = core.formTufoByProp('inet:fqdn','vertex.link')

        return core

    def test_storm_ram(self):
        with s_cortex.openurl('ram://') as core:
            self.prepStormCore(core)
            self.runStormBasics(core)

    def test_storm_sqlite(self):
        with s_cortex.openurl('sqlite:///:memory:') as core:
            self.prepStormCore(core)
            self.runStormBasics(core)

    def test_storm_postgres(self):
        with self.getPgCore() as core:
            self.prepStormCore(core)
            self.runStormBasics(core)

    def runStormBasics(self, core):

        t0 = core.formTufoByProp('inet:ipv4',0)
        t1 = core.formTufoByProp('inet:ipv4',0x7f000001)
        t2 = core.formTufoByProp('inet:ipv4',0x01020304)

        t3 = core.formTufoByProp('dns:a','woot.com/1.2.3.4')
        t4 = core.formTufoByProp('dns:a','vertex.link/127.0.0.1')
        t5 = core.formTufoByProp('dns:a','woot.com/127.0.0.1')

        t6 = core.formTufoByProp('inet:fqdn','woot.com')
        t7 = core.formTufoByProp('inet:fqdn','vertex.link')

        self.sorteq( core.eval('inet:ipv4'), [t0,t1,t2] )
        self.sorteq( core.eval('inet:ipv4="1.2.3.4"'), [t2] )
        self.sorteq( core.eval('inet:ipv4=0x01020304'), [t2] )

        self.sorteq( core.eval('inet:ipv4="127.0.0.1" ^dns:a:ipv4=inet:ipv4 ^inet:fqdn=dns:a:fqdn'), [t6,t7] )

        # test join operator basics
        self.sorteq( core.eval('inet:ipv4="127.0.0.1" join("inet:ipv4:cc")'), [t0,t1,t2] )
        self.sorteq( core.eval('inet:ipv4="127.0.0.1" ^dns:a:ipv4=inet:ipv4 join("inet:fqdn","dns:a:fqdn")'), [t4,t5,t6,t7] )

        # test filt #####################################################

        # test filt cmp=tag
        self.sorteq( core.eval('inet:ipv4 -#omit'), [t2] )
        self.sorteq( core.eval('inet:ipv4 +#omit'), [t0,t1])

        # test filt cmp=has
        self.sorteq( core.eval('inet:ipv4 +inet:ipv4:cc'), [t0,t1,t2] )

        # test filt cmp=gt
        self.sorteq( core.eval('inet:ipv4 +inet:ipv4>0x7f000000'), [ t1 ] )

        # test filt cmp=ge
        self.sorteq( core.eval('inet:ipv4 +inet:ipv4>=0x7f000001'), [ t1 ] )

        # test filt cmp=lt
        self.sorteq( core.eval('inet:ipv4 +inet:ipv4<1'), [ t0 ] )

        # test filt cmp=le
        self.sorteq( core.eval('inet:ipv4 +inet:ipv4<=0'), [ t0 ] )

        # test filt cmp=re
        self.sorteq( core.eval('inet:fqdn +inet:fqdn~="^ver"'), [ t7 ] )

        # test opts #####################################################
        self.sorteq( core.eval('%uniq=1 inet:fqdn="woot.com" inet:fqdn="woot.com"'), [ t6 ] )
        self.sorteq( core.eval('%uniq=0 inet:fqdn="woot.com" inet:fqdn="woot.com"'), [ t6, t6 ] )

        self.eq( core.ask('%foo="bar"')['options'].get('foo'), 'bar' )

        # test lift #####################################################

        # test lift cmp=tag
        self.sorteq( core.eval('inet:ipv4*tag="omit"'), [t0,t1] )

        # test lift cmp=has
        self.sorteq( core.eval('inet:ipv4:cc'), [t0,t1,t2] )

        # test lift cmp=gt
        self.sorteq( core.eval('inet:ipv4>0x7f000000'), [ t1 ] )

        # test lift cmp=ge
        self.sorteq( core.eval('inet:ipv4>=0x7f000001'), [ t1 ] )

        # test lift cmp=lt
        self.sorteq( core.eval('inet:ipv4<1'), [ t0 ] )

        # test lift cmp=le
        self.sorteq( core.eval('inet:ipv4<=0'), [ t0 ] )

