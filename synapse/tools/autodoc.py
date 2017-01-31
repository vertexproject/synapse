import sys
import argparse
import collections

import synapse.cortex as s_cortex
import synapse.compat as s_compat

import synapse.lib.tufo as s_tufo
import synapse.lib.output as s_output

descr = '''
Command line tool to generate various synapse documentation
'''

rstlvls = [
    ('#',{'over':True}),
    ('*',{'over':True}),
    ('=',{}),
    ('-',{}),
    ('^',{}),
]

def reprvalu(valu):
    if s_compat.isstr(valu):
        return repr(valu)
    return '%d (0x%x)' % (valu,valu)

class RstHelp:

    def __init__(self):
        self.lines = []

    def addHead(self, name, lvl=0):
        char,info = rstlvls[lvl]
        under = char * len(name)

        self.lines.append('')

        if info.get('over'):
            self.lines.append(under)

        self.lines.append(name)
        self.lines.append(under)

        self.lines.append('')

    def addLines(self, *lines):
        self.lines.extend(lines)

    def getRstText(self):
        return '\n'.join(self.lines)

def main(argv, outp=None):

    if outp == None:
        outp = s_output.OutPut()

    pars = argparse.ArgumentParser(prog='autodoc', description=descr)

    #pars.add_argument('--format', default='rst')
    pars.add_argument('--cortex', default='ram://', help='Cortex URL for model inspection')
    pars.add_argument('--doc-model', action='store_true', default=False, help='Generate RST docs for the DataModel within a cortex')
    pars.add_argument('--savefile', default=None, help='Save output to the given file')

    opts = pars.parse_args(argv)
    if opts.savefile:
        fd = open(opts.savefile,'wb')
        outp = s_output.OutPutFd(fd)

    core = s_cortex.openurl(opts.cortex)

    if opts.doc_model:

        forms = []
        types = []

        props = collections.defaultdict(list)

        for tufo in core.getTufosByProp('syn:type'):
            name = tufo[1].get('syn:type')
            info = s_tufo.props(tufo)
            types.append( (name,info) )

        for tufo in core.getTufosByProp('syn:form'):
            name = tufo[1].get('syn:form')
            info = s_tufo.props(tufo)
            forms.append( (name,info) )

        for tufo in core.getTufosByProp('syn:prop'):
            prop = tufo[1].get('syn:prop')
            form = tufo[1].get('syn:prop:form')
            info = s_tufo.props(tufo)
            props[form].append( (prop,info) )

        types.sort()
        forms.sort()

        [ v.sort() for v in props.values() ]

        rst = RstHelp()
        rst.addHead('Synapse Data Model', lvl=0)

        rst.addHead('Types',lvl=1)

        for name,info in types:

            rst.addHead(name, lvl=2)
            inst = core.getTypeInst(name)

            ex = inst.get('ex')
            doc = inst.get('doc')

            if doc != None:
                rst.addLines( doc )

            bases = core.getTypeBases(name)
            rst.addLines('','Type Hierarchy: %s' % (' -> '.join(bases),),'')

            if ex != None:

                #valu = core.getTypeParse(name,ex)
                #vrep = reprvalu(valu)

                rst.addLines('','Examples:','')
                rst.addLines('- repr mode: %s' % (repr(ex),))
                #rst.addLines('- system mode: %s' % (vrep,))
                rst.addLines('')

            cons = []
            xforms = []

            if core.isSubType(name,'str'):

                regex = inst.get('regex')
                if regex != None:
                    cons.append('- regex: %s' % (regex,))

                lower = inst.get('lower')
                if lower:
                    xforms.append('- case: lower')

                restrip = inst.get('restrip')
                if restrip != None:
                    xforms.append('- regex strip: %s' % (restrip,))

                nullval = inst.get('nullval')
                if nullval != None:
                    cons.append('- null value: %s' % (nullval,))

            if core.isSubType(name,'int'):

                minval = inst.get('min')
                if minval != None:
                    cons.append('- min value: %d (0x%x)' % (minval,minval))

                maxval = inst.get('max')
                if maxval != None:
                    cons.append('- max value: %d (0x%x)' % (maxval,maxval))

                ismin = inst.get('ismin')
                if ismin != None:
                    xforms.append('- is minimum: True')

                ismax = inst.get('ismax')
                if ismax != None:
                    xforms.append('- is maximum: True')

            if core.isSubType(name,'sepr'):

                sep = inst.get('sep')
                fields = inst.get('fields')

                parts = []
                for part in fields.split('|'):
                    name,stype = part.split(',')
                    parts.append(stype)

                seprs = sep.join( [ '<%s>' % p for p in parts ])
                rst.addLines('','Sepr Fields: %s' % (seprs,))

            if cons:
                cons.append('')
                rst.addLines('','Type Constraints:', '', *cons)

            if xforms:
                xforms.append('')
                rst.addLines('','Type Transforms:', '', *xforms)

        rst.addHead('Forms',lvl=1)

        for name,info in forms:
            ftype = info.get('ptype','str')
            rst.addHead('%s = <%s>' % (name,ftype), lvl=2)

            doc = core.getPropInfo(name,'doc')
            if doc != None:
                rst.addLines(doc)

            rst.addLines('','Properties:','')

            for prop,pnfo in props.get(name,()):

                # use the resolver funcs that will recurse upward
                pex = core.getPropInfo(prop,'ex')
                pdoc = core.getPropInfo(prop,'doc')

                ptype = pnfo.get('ptype')

                pline = '\t- %s = <%s>' % (prop,ptype)

                defval = pnfo.get('defval')
                if defval != None:
                    pline += ' (default: %r)' % (defval,)

                rst.addLines(pline)

                if pdoc:
                    rst.addLines('\t\t- %s' % (pdoc,))

        outp.printf( rst.getRstText() )
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
