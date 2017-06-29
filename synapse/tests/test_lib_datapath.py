from synapse.tests.common import *

import synapse.lib.datapath as s_datapath

item0 = {
    'results': [
        {'foo': 10},
        {'foo': 20},
    ],
    'woot': 'hehe',
    '..': 'hurr',
    '20': 'durr',
}


class DataPathTest(SynTest):

    def test_datapath_valu(self):
        data = s_datapath.initelem(item0)
        self.eq(data.valu('results/0/foo'), 10)
        self.eq(data.valu('results/1/foo'), 20)

    def test_datapath_iter(self):
        data = s_datapath.initelem(item0)
        vals = tuple(data.vals('results/*/foo'))
        self.eq(vals, (10, 20))

    def test_datapath_parent(self):
        data = s_datapath.initelem(item0)
        self.eq(data.valu('results/../woot'), 'hehe')

    def test_datapath_quoted(self):
        data = s_datapath.initelem(item0)
        self.eq(data.valu('".."'), 'hurr')
        self.eq(data.valu('"20"'), 'durr')

    #def test_datapath_abs(self):
        #data = s_datapath.initelem(item0)
        #woot = data.open('woot')
        #self.eq( woot.open('/results/0/foo').valu(), 10 )

    def test_datapath_self(self):
        data = s_datapath.initelem(item0)
        self.eq(data.valu('results/0/././foo'), 10)
