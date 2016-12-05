import csv

from synapse.common import *
from synapse.eventbus import EventBus

import synapse.dyndeps as s_dyndeps
import synapse.lib.datapath as s_datapath

class Ingest(EventBus):
    '''
    An Ingest allows modular data acquisition and cortex loading.

    info = {
        'name':'Example Ingest',
        'iden':'f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0',
        'scheme':'synapse',

        'tags':( <tag0>, [... ]),       # tags to add to *all* formed tufos

        'ingest':(
            ( <iterpath>, {
                 'skipif': TODO
                 'forms':(
                     (<form>, <path>, {
                         'props':(
                             (<prop>,<path>,{}),
                         ),
                     })
                 ),
                # TODO vars / compose
            }),
        ),

        # for the default in-band case only...
        'data':<in-band-data>,
    }

    '''
    def __init__(self, info):
        EventBus.__init__(self)
        self._i_info = info

    def iterDataRoots(self):
        '''
        Yield "root" DataPath elements to ingest from.

        Example:

            for data in gest.iterDataRoots():
                # data is a DataPath instance.
                doStuff( data )

        '''
        for item in self._iterRawData():
            yield s_datapath.DataPath(item)

    def ingest(self, core):
        '''
        Extract data and add it to a Cortex.
        '''
        for root in self.iterDataRoots():
            self._ingFromRoot(core,root)

    def _ingFromRoot(self, core, root):

        for iterpath,iterinfo in self._i_info.get('ingest',()):

            for data in root.iter(*iterpath):

                for formname, forminfo in iterinfo.get('forms'):

                    formpath = forminfo.get('path')

                    props = {}
                    formvalu = data.valu(*formpath)

                    if formvalu == None:
                        continue

                    for propname,propinfo in forminfo.get('props',()):
                        # FIXME implement altername normalization here...
                        proppath = propinfo.get('path')
                        propvalu = data.valu(*proppath)
                        if propvalu == None:
                            continue

                        props[propname] = propvalu

                    core.formTufoByFrob(formname,formvalu,**props)

    def _iterRawData(self):
        # default impl for in-band (in info) data
        yield self._i_info.get('data')

class CsvIngest(Ingest):
    '''
    Ingest implementation for CSV data.
    '''

    def _iterRawData(self):

        # TODO url = self._i_info.get('csv:url')
        #cols = self._i_info.get('csv:columns')
        dial = self._i_info.get('csv:dialect')
        path = self._i_info.get('csv:filepath')

        quot = self._i_info.get('csv:quote')
        delm = self._i_info.get('csv:delimiter')

        fmtinfo = {}

        if dial != None:
            fmtinfo['dialect'] = dial

        if delm != None:
            fmtinfo['delimiter'] = delm

        if quot != None:
            fmtinfo['quotechar'] = quot

        with open(path,'r') as fd:

            rows = []
            for row in csv.reader(fd, **fmtinfo):
                rows.append(row)
                if len(rows) >= 1000:
                    yield rows
                    rows.clear()

            if rows:
                yield rows

formats = {
    'csv':'synapse.lib.ingest.CsvIngest',
}

def init(info):
    '''
    Create and return an Ingest for the given ingest data.

    Example:

        info = {
            'name':'The Woot Ingest v1',

            'format':'woot',
                # ... or ... 
            'ctor':'foo.bar.WootIngest',

            ... scheme specific info ...

        }

    '''
    ctor = info.get('ctor')
    if ctor == None:
        fmat = info.get('format')
        ctor = formats.get(fmat,'synapse.lib.ingest.Ingest')

    return s_dyndeps.tryDynFunc(ctor,info)
