from synapse.tests.common import *

import synapse.lib.datapath as s_datapath

item0 = {
    'results':[
        {'foo':10},
        {'foo':20},
    ],
    'woot':'hehe',
}


class DataPathTest(SynTest):

    def test_datapath_valu(self):
        data = s_datapath.DataPath(item0)
        self.eq( data.valu('results',0,'foo'), 10 )
        self.eq( data.valu('results',1,'foo'), 20 )

    def test_datapath_iter(self):
        dat0 = s_datapath.DataPath(item0)
        vals = []
        for dat1 in dat0.iter('results'):
            vals.append( dat1.valu('foo') )

        self.eq( tuple(vals), (10,20) )

    def test_datapath_parent(self):
        data = s_datapath.DataPath(item0)
        subd = data.walk('results',0)
        self.eq( subd.valu(-1,-1,'woot'), 'hehe' )
