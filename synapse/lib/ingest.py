import os
import csv
import json
import codecs

from synapse.common import *
from synapse.eventbus import EventBus

import synapse.axon as s_axon
import synapse.dyndeps as s_dyndeps
import synapse.lib.scrape as s_scrape
import synapse.lib.datapath as s_datapath
import synapse.lib.encoding as s_encoding

def _fmt_csv(fd,gest):

    opts = {}

    quot = gest.get('fmt:csv:quote')
    dial = gest.get('fmt:csv:dialect')
    path = gest.get('fmt:csv:filepath')
    delm = gest.get('fmt:csv:delimiter')

    if dial != None:
        opts['dialect'] = dial

    if delm != None:
        opts['delimiter'] = delm

    if quot != None:
        opts['quotechar'] = quot

    return csv.reader(fd,**opts)

def _fmt_lines(fd,gest):

    lowr = gest.get('format:lines:lower')

    for line in fd:

        line = line.strip()
        if line.startswith('#'):
            continue

        if not line:
            continue

        if lowr:
            line = line.lower()

        yield line

fmtyielders = {
    'csv':_fmt_csv,
    'lines':_fmt_lines,
}

fmtopts = {
    'csv':{'mode':'r','encoding':'utf8'},
    'lines':{'mode':'r','encoding':'utf8'},
}

def iterdata(fd,**opts):
    '''
    Iterate through the data provided by a file like object.

    Optional parameters may be used to control how the data
    is deserialized.

    Example:

        with open('foo.csv','rb') as fd:

            for row in iterdata(fd, format='csv', encoding='utf8'):

                dostuff(row)

    '''
    fmt = opts.get('format','lines')
    fopts = fmtopts.get(fmt,{})

    # set default options for format
    for opt,val in fopts.items():
        opts.setdefault(opt,val)

    ncod = opts.get('encoding')
    if ncod != None:
        fd = codecs.getreader(ncod)(fd)

    fmtr = fmtyielders.get(fmt)
    if fmtr == None:
        raise NoSuchImpl(name=fmt,knowns=fmtyielders.keys())

    for item in fmtr(fd,opts):
        yield item

    fd.close()

class Ingest(EventBus):
    '''
    An Ingest allows modular data acquisition and cortex loading.

    info = {

        'ingest':{
            'name':'Example Ingest',
            'iden':'f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0',

            'tags':( <tag0>, [... ]),       # tags to add to *all* formed tufos

            'iters':(
                (<path/*>, {<ingest>}),
            ),

            'forms':(
                (<form>, {'path':<path>, 'props':{
                    <prop>:{ 'path':<path> | 'value':<value> }
                )
            ),

            'files':(
                (<path>, {'mime':<mime>, 'decode':<decode> }),
            ),

            'scrapes':(
                (<path>, {<opts>}),
            ),

        },

        # for the default in-band case only...
        'data':<in-band-data>,
    }

    '''
    def __init__(self, info, axon=None):
        EventBus.__init__(self)
        self._i_info = info
        self._i_axon = axon

    def get(self, name, defval=None):
        return self._i_info.get(name,defval)

    def set(self, name, valu):
        self._i_info[name] = valu

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

    def _openDataSorc(self, path, info):
        '''
        Open a data source tuple and return a data yielder object.
        '''
        if path.startswith('http://'):
            return self._openHttpSorc(path,info)

        if path.startswith('https://'):
            return self._openHttpSorc(path,info)

        # do we have a known running dir?
        basedir = self.get('basedir')
        if basedir != None and not os.path.isabs(path):
            path = os.path.join(basedir,path)

        # FIXME universal open...
        fd = open(path,'rb')
        onfo = info.get('open',{})

        return iterdata(fd,**onfo)

    def ingest(self, core, data=None):
        '''
        Ingest the data from this definition into the specified cortex.
        '''
        if data != None:
            root = s_datapath.DataPath(data)
            gest = self._i_info.get('ingest')
            self._ingDataInfo(core, root, gest)
            return

        for path,info in self.get('sources'):

            data = self._openDataSorc(path,info)

            gest = info.get('ingest')
            if gest == None:
                gest = self._i_info.get('ingest')

            if gest == None:
                raise Exception('Ingest Info Not Found: %s' % (path,))

            root = s_datapath.DataPath(data)
            self._ingDataInfo(core, root, gest)

    def _ingDataInfo(self, core, data, info, **ctx):

        ctx['tags'] = tuple(info.get('tags',())) + ctx.get('tags',())

        # extract files embedded within the data structure
        for path,flfo in info.get('files',()):

            for item in data.iter(path):
                byts = item.valu()

                dcod = flfo.get('decode')
                if dcod != None:
                    byts = s_encoding.decode(dcod,byts)

                hset = s_axon.HashSet()
                hset.update(byts)

                iden,props = hset.guid()

                mime = flfo.get('mime')
                if mime != None:
                    props['mime'] = mime

                tufo = core.formTufoByProp('file:bytes',iden,**props)

                self.fire('gest:prog', act='file')

                for tag in ctx.get('tags'):
                    core.addTufoTag(tufo,tag)
                    self.fire('gest:prog', act='tag')

        for path,scfo in info.get('scrapes',()):

            tags = list( ctx.get('tags',()) )
            tags.extend( scfo.get('tags',() ) )

            for item in data.iter(path):
                text = item.valu()

                for form,valu in s_scrape.scrape(text):

                    tufo = core.formTufoByProp(form,valu)

                    self.fire('gest:prog', act='form')

                    for tag in tags:
                        self.fire('gest:prog', act='tag')
                        core.addTufoTag(tufo,tag)

        # iterate and create any forms at our level
        for form,fnfo in info.get('forms',()):

            base = data

            # Allow dynamic forms...
            fstr = fnfo.get('form')
            if fstr != None:
                form = base.valu(fstr)

            # iterate elements from the specified path
            path = fnfo.get('path')
            for base in base.iter(path):

                #valu = self._get_prop(core,base,fnfo)
                valu = self._get_form(core,base,fnfo)
                if valu == None:
                    continue

                tufo = core.formTufoByFrob(form,valu)
                self.fire('gest:prog', act='form')

                props = {}
                for prop,pnfo in fnfo.get('props',{}).items():
                    valu = self._get_prop(core,base,pnfo)
                    if valu == None:
                        continue

                    props[prop] = valu


                if props:
                    core.setTufoFrobs(tufo,**props)
                    self.fire('gest:prog', act='set')

                for tag in ctx.get('tags'):
                    core.addTufoTag(tufo,tag)
                    self.fire('gest:prog', act='tag')


        for path,tifo in info.get('iters',()):
            for base in data.iter(path):
                self._ingDataInfo(core, base, tifo, **ctx)

    def _get_form(self, core, base, info):

        valu = info.get('value')
        if valu != None:
            return valu

        # template=('{{foo}}:80', {'foo':{'path':'bar/baz'}})
        template = info.get('template')
        if template != None:
            valu,tnfo = template

            for tname,tinfo in tnfo.items():

                tval = self._get_prop(core,base,tinfo)
                if tval == None:
                    return None

                valu = valu.replace('{{%s}}' % tname, tval)

            return valu

        valu = base.valu()
        if valu == None:
            return None

        pivot = info.get('pivot')
        if pivot != None:
            pivf,pivt = pivot

            pivo = core.getTufoByFrob(pivf,valu)
            if pivo == None:
                return None

            valu = pivo[1].get(pivt)

        return valu

    def _get_prop(self, core, base, info):

        valu = info.get('value')
        if valu != None:
            return valu

        #FIXME explicit cast/frob

        # template=('{{foo}}:80', {'foo':{'path':'bar/baz'}})
        template = info.get('template')
        if template != None:
            valu,tnfo = template

            for tname,tinfo in tnfo.items():

                tval = self._get_prop(core,base,tinfo)
                if tval == None:
                    return None

                valu = valu.replace('{{%s}}' % tname, tval)

            return valu

        path = info.get('path')
        valu = base.valu(path)
        if valu == None:
            return None

        pivot = info.get('pivot')
        if pivot != None:
            pivf,pivt = pivot

            pivo = core.getTufoByFrob(pivf,valu)
            if pivo == None:
                return None

            valu = pivo[1].get(pivt)

        return valu

def loadfile(*paths):
    '''
    Load a json ingest def from file and construct an Ingest class.

    This routine is useful because it implements the convention
    for adding runtime info to the ingest json to facilitate path
    relative file opening etc...
    '''
    path = genpath(*paths)

    # FIXME universal open

    with reqfile(path) as fd:
        jsfo = json.loads( fd.read().decode('utf8') )

    gest = Ingest(jsfo)

    gest.set('basedir', os.path.dirname(path))

    return gest
