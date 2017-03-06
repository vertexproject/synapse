import os
import re
import csv
import json
import codecs
import logging
import traceback

import xml.etree.ElementTree as x_etree

from synapse.common import *
from synapse.eventbus import EventBus

import synapse.axon as s_axon
import synapse.gene as s_gene
import synapse.compat as s_compat
import synapse.dyndeps as s_dyndeps

import synapse.lib.scope as s_scope
import synapse.lib.syntax as s_syntax
import synapse.lib.scrape as s_scrape
import synapse.lib.datapath as s_datapath
import synapse.lib.encoding as s_encoding
import synapse.lib.filepath as s_filepath
import synapse.lib.openfile as s_openfile

logger = logging.getLogger(__name__)

def _xml_stripns(e):

    # believe it or not, this is the recommended
    # way to strip XML namespaces...
    if e.tag.find('}') != -1:
        e.tag = e.tag.split('}')[1]

    for name,valu in e.attrib.items():
        if name.find('}') != -1:
            e.attrib[name.split('{')[1]] = valu

    for x in e:
        _xml_stripns(x)


def _fmt_xml(fd,gest):
    #TODO stream XML ingest for huge files
    elem = x_etree.fromstring(fd.read())
    _xml_stripns(elem)
    yield {elem.tag:elem}

def _fmt_csv(fd,gest):

    opts = {}

    quot = gest.get('format:csv:quote')
    cmnt = gest.get('format:csv:comment')
    dial = gest.get('format:csv:dialect')
    delm = gest.get('format:csv:delimiter')

    if dial != None:
        opts['dialect'] = dial

    if delm != None:
        opts['delimiter'] = delm

    if quot != None:
        opts['quotechar'] = quot

    # do we need to strip a comment char?
    if cmnt != None:

        # use this if we need to strip comments
        # (but avoid it otherwise for perf )
        def lineiter():
            for line in fd:
                if not line.startswith(cmnt):
                    yield line

        return csv.reader(lineiter(),**opts)

    return csv.reader(fd,**opts)

def _fmt_lines(fd,gest):

    skipre = None
    mustre = None

    lowr = gest.get('format:lines:lower')
    cmnt = gest.get('format:lines:comment','#')

    skipstr = gest.get('format:lines:skipre')
    if skipstr != None:
        skipre = re.compile(skipstr)

    muststr = gest.get('format:lines:mustre')
    if muststr != None:
        mustre = re.compile(muststr)

    for line in fd:

        line = line.strip()

        if not line:
            continue

        if line.startswith(cmnt):
            continue

        if lowr:
            line = line.lower()

        if skipre != None and skipre.match(line) != None:
            continue

        if mustre != None and mustre.match(line) == None:
            continue

        yield line

def _fmt_json(fd,info):
    yield json.loads( fd.read() )

def _fmt_jsonl(fd,info):
    for line in fd:
        yield json.loads(line)

fmtyielders = {
    'csv':_fmt_csv,
    'xml':_fmt_xml,
    'json':_fmt_json,
    'jsonl':_fmt_jsonl,
    'lines':_fmt_lines,
}

fmtopts = {
    'xml':{'mode':'r','encoding':'utf8'},
    'csv':{'mode':'r','encoding':'utf8'},
    'json':{'mode':'r','encoding':'utf8'},
    'jsonl':{'mode':'r','encoding':'utf8'},
    'lines':{'mode':'r','encoding':'utf8'},
}

def addFormat(name, fn, opts):
    '''
    Add an additional ingest file format
    '''
    fmtyielders[name] = fn
    fmtopts[name] = opts

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
    '''
    def __init__(self, info, axon=None):
        EventBus.__init__(self)
        self._i_res = {}
        self._i_info = info
        self._i_axon = axon

        self._i_glab = s_gene.GeneLab()

        self._tvar_cache = {}
        self._tvar_regex = re.compile('{{(\w+)}}')

    def _re_compile(self, regex):
        ret = self._i_res.get(regex)
        if ret == None:
            self._i_res[regex] = ret = re.compile(regex)
        return ret

    def get(self, name, defval=None):
        return self._i_info.get(name,defval)

    def set(self, name, valu):
        self._i_info[name] = valu

    def _iterDataSorc(self, path, info):

        if not os.path.isabs(path):
            basedir = self.get('basedir')
            if basedir:
                path = os.path.join(basedir,path)

        onfo = info.get('open')
        for fd in s_filepath.openfiles(path,mode='rb'):
            yield iterdata(fd,**onfo)

    def ingest(self, core, data=None):
        '''
        Ingest the data from this definition into the specified cortex.
        '''
        scope = s_scope.Scope()
        if data != None:
            root = s_datapath.initelem(data)
            gest = self._i_info.get('ingest')
            self._ingDataInfo(core, root, gest, scope)
            return

        for path,info in self.get('sources'):

            scope.enter()

            scope.add('tags', *info.get('tags',()) )

            gest = info.get('ingest')
            if gest == None:
                gest = self._i_info.get('ingest')

            if gest == None:
                raise Exception('Ingest Info Not Found: %s' % (path,))

            for datasorc in self._iterDataSorc(path,info):
                for data in datasorc:
                    root = s_datapath.initelem(data)
                    self._ingDataInfo(core, root, gest, scope)

    def _ingMergScope(self, core, data, info, scope):

        vard = info.get('vars')
        if vard != None:
            for varn,vnfo in vard:
                valu = self._get_prop(core,data,vnfo,scope)
                scope.set(varn,valu)

        for tagv in info.get('tags',()):

            # if it's a simple tag string, add and move along
            if s_compat.isstr(tagv):
                scope.add('tags',tagv.lower())
                continue

            # otherwise it's an iteration compatible prop dict
            tags = [ t.lower() for t in self._iter_prop(core,data,tagv,scope) ]

            scope.add('tags',*tags)

    def _ingFileInfo(self, core, data, info, scope):

        with scope:

            self._ingMergScope(core,data,info,scope)

            cond = info.get('cond')
            if cond != None and not self._isCondTrue(cond,scope):
                return

            path = info.get('path')

            byts = data.valu(path)

            dcod = info.get('decode')
            if dcod != None:
                byts = s_encoding.decode(dcod,byts)

            hset = s_axon.HashSet()
            hset.update(byts)

            iden,props = hset.guid()

            mime = info.get('mime')
            if mime != None:
                props['mime'] = mime

            tufo = core.formTufoByProp('file:bytes',iden,**props)

            self.fire('gest:prog', act='file')

            for tag in scope.iter('tags'):
                core.addTufoTag(tufo,tag)
                self.fire('gest:prog', act='tag')

    def _ingFormInfo(self, core, data, info, scope):

        with scope:

            try:

                form = info.get('form')
                self._ingMergScope(core,data,info,scope)

                cond = info.get('cond')
                if cond != None and not self._isCondTrue(cond,scope):
                    return

                valu = self._get_prop(core,data,info,scope)
                if valu == None:
                    return

                tufo = core.formTufoByFrob(form,valu)
                if tufo == None:
                    return

                self.fire('gest:prog', act='form')

                props = {}
                for prop,pnfo in info.get('props',{}).items():
                    valu = self._get_prop(core,data,pnfo,scope)
                    if valu == None:
                        continue

                    props[prop] = valu

                if props:
                    core.setTufoFrobs(tufo,**props)
                    self.fire('gest:prog', act='set')

                for tag in scope.iter('tags'):
                    core.addTufoTag(tufo,tag)
                    self.fire('gest:prog', act='tag')

            except Exception as e:
                traceback.print_exc()
                core.logCoreExc(e,subsys='ingest')

    def _ingDataInfo(self, core, data, info, scope):

        with scope:

            self._ingMergScope(core,data,info,scope)

            cond = info.get('cond')
            if cond != None and not self._isCondTrue(cond,scope):
                return

            self.fire('gest:prog', act='data')

            # extract files embedded within the data structure
            for flfo in info.get('files',()):
                self._ingFileInfo(core,data,flfo,scope)

            for cond,cnfo in info.get('conds',()):
                if not self._isCondTrue(cond,scope):
                    continue
                self._ingDataInfo(core,data,cnfo,scope)

            # iterate and create any forms at our level
            for form,fnfo in info.get('forms',()):
                fnfo.setdefault('form',form)
                self._ingFormInfo(core,data,fnfo,scope)

            # handle explicit nested iterators
            for path,tifo in info.get('iters',()):
                for base in data.iter(path):
                    self._ingDataInfo(core, base, tifo, scope)

    def _isCondTrue(self, cond, scope):
        expr = self._i_glab.getGeneExpr(cond)
        return bool( expr( scope ) )

    def _iter_prop(self, core, data, info, scope):

        cond = info.get('cond')
        if cond != None and not self._isCondTrue(cond,scope):
            return

        path = info.get('iter')

        if path == None:

            valu = self._get_prop(core, data, info, scope)
            if valu != None:
                yield valu

            return

        for base in data.iter(path):

            with scope:

                self._ingMergScope(core,base,info,scope)
                valu = self._get_prop(core, base, info, scope)
                if valu == None:
                    continue

                yield valu

    def _getTmplVars(self, text):
        ret = self._tvar_cache.get(text)
        if ret == None:
            self._tvar_cache[text] = ret = self._tvar_regex.findall(text)
        return ret

    def _get_prop(self, core, base, info, scope):

        cond = info.get('cond')
        if cond != None and not self._isCondTrue(cond,scope):
            return

        valu = info.get('value')
        if valu != None:
            return valu

        if valu == None:
            varn = info.get('var')
            valu = scope.get(varn)

        template = info.get('template')
        if template != None:

            valu = template

            for tvar in self._getTmplVars(template):
                tval = scope.get(tvar)
                if tval == None:
                    return None

                # FIXME optimize away the following format string
                valu = valu.replace('{{%s}}' % tvar, tval)

        if valu == None:
            path = info.get('path')
            valu = base.valu(path)

        if valu == None:
            return None

        # If we have a regex field, use it to extract valu from the
        # first grouping
        rexs = info.get('regex')
        if rexs != None:
            rexo = self._re_compile(rexs)
            match = rexo.search(valu)
            if match == None:
                return None

            groups = match.groups()
            if groups:
                valu = groups[0]

        # allow type based normalization here
        cast = info.get('cast')
        if cast != None:
            valu = core.getTypeCast(cast,valu)

        # FIXME make a mechanism here for field translation based
        # on an included translation table within the ingest def

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
