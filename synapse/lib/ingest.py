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

def opendata(path,**opts):
    '''
    Open a data file on disk and iterate through the top level elements.
    '''
    fmt = opts.get('format','lines')

    fopts = fmtopts.get(fmt,{})

    fmtr = fmtyielders.get(fmt)
    if fmtr == None:
        raise NoSuchImpl(name=fmt,knowns=fmtyielders.keys())

    with reqfile(path,**fopts) as fd:
        for item in fmtr(fd,opts):
            yield item

def openfd(fd,**opts):

    fmt = opts.get('format','lines')
    fopts = fmtopts.get(fmt,{})

    ncod = fopts.get('encoding')
    if ncod != None:
        fd = codecs.getreader(ncod)(fd)

    fmtr = fmtyielders.get(fmt)
    if fmtr == None:
        raise NoSuchImpl(name=fmt,knowns=fmtyielders.keys())

    for item in fmtr(fd,opts):
        yield item

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

    def ingest(self, core, data):
        '''
        Extract data and add it to a Cortex.

        The data input is expected to be an iterable object
        full of dicts/lists/strings/integers.  If a source
        of data yields a single monolithic data structure,
        it is still expected to be contained within a list
        or generator.

        Example:

            data = s_ingest.opendata('foo/bar/baz.csv', format='csv')

            gest = s_ingest.Ingest(info)

            gest.ingest(core,data)

        '''
        root = s_datapath.DataPath(data)
        info = self._i_info.get('ingest',{})
        self._ingDataInfo(core, root, info)

    def _getBaseValu(self, base, info):
        path = flfo.get('path')
        if path != None:
            base = path.open(base)

        if base == None:
            return None

        return base.valu()

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
                for tag in ctx.get('tags'):
                    core.addTufoTag(tufo,tag)

        for path,scfo in info.get('scrapes',()):

            tags = list( ctx.get('tags',()) )
            tags.extend( scfo.get('tags',() ) )

            for item in data.iter(path):
                text = item.valu()

                for form,valu in s_scrape.scrape(text):
                    tufo = core.formTufoByProp(form,valu)
                    core.addTufoTags(tufo,tags)

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

                props = {}
                for prop,pnfo in fnfo.get('props',{}).items():
                    valu = self._get_prop(core,base,pnfo)
                    if valu == None:
                        continue

                    props[prop] = valu


                if props:
                    core.setTufoFrobs(tufo,**props)

                for tag in ctx.get('tags'):
                    core.addTufoTag(tufo,tag)

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
