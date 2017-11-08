import os
import sys
import argparse
import importlib
import collections

import synapse

import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.tufo as s_tufo
import synapse.lib.config as s_config
import synapse.lib.output as s_output
import synapse.lib.reflect as s_reflect

base_synaspe_dir = os.path.split(synapse.__file__)[0]

dir_skips = ('/tests',
             '/tools',
             '/__pycache__',
             'synapse/docker',
             )

fn_skips = ('__init__.py',
            )

obj_path_skips = ('synapse.cores.common.Runtime',
                  'synapse.cores.storage.Storage',
                  )

descr = '''
Command line tool to generate various synapse documentation
'''

rstlvls = [
    ('#', {'over': True}),
    ('*', {'over': True}),
    ('=', {}),
    ('-', {}),
    ('^', {}),
]

def reprvalu(valu):
    if isinstance(valu, str):
        return repr(valu)
    return '%d (0x%x)' % (valu, valu)

def inspect_mod(mod, cls):
    '''Find Config classes in a module which has @confdef decorated functions in them.'''
    for modname in dir(mod):
        valu = getattr(mod, modname)
        try:
            is_cls = issubclass(valu, cls)
        except TypeError:
            continue
        if not is_cls:
            continue
        # Snag configable defs
        for name, meth in s_reflect.getItemLocals(valu):
            attr = getattr(meth, '_syn_config', None)
            if attr is None:
                continue
            yield modname, valu, name, meth()


class RstHelp:

    def __init__(self):
        self.lines = []

    def addHead(self, name, lvl=0):
        char, info = rstlvls[lvl]
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

    if outp is None:
        outp = s_output.OutPut()

    pars = argparse.ArgumentParser(prog='autodoc', description=descr)

    #pars.add_argument('--format', default='rst')
    pars.add_argument('--cortex', default='ram://', help='Cortex URL for model inspection')
    pars.add_argument('--doc-model', action='store_true', default=False, help='Generate RST docs for the DataModel within a cortex')
    pars.add_argument('--configable-opts', action='store_true', default=False, help='Generate RST docs of the Configable classes in Synapse.')
    pars.add_argument('--savefile', default=None, help='Save output to the given file')

    opts = pars.parse_args(argv)
    fd = None
    if opts.savefile:
        fd = open(opts.savefile, 'wb')
        outp = s_output.OutPutFd(fd)

    core = s_cortex.openurl(opts.cortex)

    if opts.doc_model:

        forms = []
        types = []

        props = collections.defaultdict(list)

        for tufo in core.getTufosByProp('syn:type'):
            name = tufo[1].get('syn:type')
            info = s_tufo.props(tufo)
            types.append((name, info))

        for tufo in core.getTufosByProp('syn:form'):
            name = tufo[1].get('syn:form')
            info = s_tufo.props(tufo)
            forms.append((name, info))

        for tufo in core.getTufosByProp('syn:prop'):
            prop = tufo[1].get('syn:prop')
            form = tufo[1].get('syn:prop:form')
            info = s_tufo.props(tufo)
            props[form].append((prop, info))

        types.sort()
        forms.sort()

        [v.sort() for v in props.values()]

        rst = RstHelp()
        rst.addHead('Synapse Data Model', lvl=0)

        rst.addHead('Types', lvl=1)

        for name, info in types:

            rst.addHead(name, lvl=2)
            inst = core.getTypeInst(name)

            ex = inst.get('ex')
            doc = inst.get('doc')

            if doc is not None:
                rst.addLines(doc)

            bases = core.getTypeBases(name)
            rst.addLines('', 'Type Hierarchy: %s' % (' -> '.join(bases),), '')

            if ex is not None:

                #valu = core.getTypeParse(name,ex)
                #vrep = reprvalu(valu)

                rst.addLines('', 'Examples:', '')
                rst.addLines('- repr mode: %s' % (repr(ex),))
                #rst.addLines('- system mode: %s' % (vrep,))
                rst.addLines('')

            cons = []
            xforms = []

            if core.isSubType(name, 'str'):

                regex = inst.get('regex')
                if regex is not None:
                    cons.append('- regex: %s' % (regex,))

                lower = inst.get('lower')
                if lower:
                    xforms.append('- case: lower')

                restrip = inst.get('restrip')
                if restrip is not None:
                    xforms.append('- regex strip: %s' % (restrip,))

                nullval = inst.get('nullval')
                if nullval is not None:
                    cons.append('- null value: %s' % (nullval,))

            if core.isSubType(name, 'int'):

                minval = inst.get('min')
                if minval is not None:
                    cons.append('- min value: %d (0x%x)' % (minval, minval))

                maxval = inst.get('max')
                if maxval is not None:
                    cons.append('- max value: %d (0x%x)' % (maxval, maxval))

                ismin = inst.get('ismin')
                if ismin is not None:
                    xforms.append('- is minimum: True')

                ismax = inst.get('ismax')
                if ismax is not None:
                    xforms.append('- is maximum: True')

            if core.isSubType(name, 'sepr'):

                sep = inst.get('sep')
                fields = inst.get('fields')

                parts = []
                for part in fields.split('|'):
                    name, stype = part.split(',')
                    parts.append(stype)

                seprs = sep.join(['<%s>' % p for p in parts])
                rst.addLines('', 'Sepr Fields: %s' % (seprs,))

            if cons:
                cons.append('')
                rst.addLines('', 'Type Constraints:', '', *cons)

            if xforms:
                xforms.append('')
                rst.addLines('', 'Type Transforms:', '', *xforms)

        rst.addHead('Forms', lvl=1)

        for name, info in forms:
            ftype = info.get('ptype', 'str')
            rst.addHead('%s = <%s>' % (name, ftype), lvl=2)

            doc = core.getPropInfo(name, 'doc')
            if doc is not None:
                rst.addLines(doc)

            rst.addLines('', 'Properties:', '')

            for prop, pnfo in props.get(name, ()):

                # use the resolver funcs that will recurse upward
                pex = core.getPropInfo(prop, 'ex')
                pdoc = core.getPropInfo(prop, 'doc')

                ptype = pnfo.get('ptype')

                pline = '\t- %s = <%s>' % (prop, ptype)

                defval = pnfo.get('defval')
                if defval is not None:
                    pline += ' (default: %r)' % (defval,)

                rst.addLines(pline)

                if pdoc:
                    rst.addLines('\t\t- %s' % (pdoc,))

        # Add universal props last - they are not associated with a form.
        uniprops = props.get(None)
        if uniprops:
            rst.addHead('Universal Props', lvl=1)

            rst.addLines('', 'Universal props are system level properties which are generally present on every node.',
                         '', 'These properties are not specific to a particular form and exist outside of a particular'
                             ' namespace.', '')
            plist = sorted(uniprops, key=lambda x: x[0])
            for prop, pnfo in plist:
                rst.addHead(prop, lvl=2)

                pdoc = core.getPropInfo(prop, 'doc')

                ptype = pnfo.get('ptype')

                pline = '\t- %s = <%s>' % (prop, ptype)
                rst.addLines(pline)

                if pdoc:
                    rst.addLines('\t\t- %s' % (pdoc,))

        outp.printf(rst.getRstText())
        return 0

    if opts.configable_opts:
        rst = RstHelp()
        rst.addHead('Synapse Configable Classes', lvl=0)
        rst.addLines('The following objects are Configable objects. They have'
                     ' settings which may be provided at runtime or during object'
                     ' initialization which may change their behavior.')
        basename = 'synapse'
        confdetails = collections.defaultdict(list)

        for root, dirs, files in os.walk(base_synaspe_dir):

            if any([v for v in dir_skips if v in root]):
                continue

            for fn in files:
                if fn in fn_skips:
                    continue
                if not fn.endswith('.py'):
                    continue

                modname = fn.rsplit('.', 1)[0]
                _modpath = root[len(base_synaspe_dir) + 1:].replace(os.sep, '.')
                modpath = '.'.join([v for v in [basename, _modpath, modname] if v])

                mod = importlib.import_module(modpath)
                for modattr, valu, name, results in inspect_mod(mod, cls=s_config.Configable):
                    confdetails[modpath].append((modattr, name, results))

        # Collapse details into a modpath -> Details struct
        detaildict = collections.defaultdict(list)

        for modpath, details in confdetails.items():
            for detail in details:
                modattr, name, results = detail
                obj_path = '.'.join([modpath, modattr])
                if obj_path in obj_path_skips:
                    continue
                for rslt in results:
                    if not rslt:
                        continue
                    detaildict[obj_path].append(rslt)

        # Now make the RST proper like
        keys = list(detaildict.keys())
        keys.sort()
        for obj_path in keys:
            details = detaildict.get(obj_path, [])
            details.sort(key=lambda x: x[0])
            rst.addHead(name=obj_path, lvl=1)
            for detail in details:
                confvalu, confdict = detail[0], detail[1]
                rst.addHead(confvalu, lvl=2)
                _keys = list(confdict.keys())
                _keys.sort()
                for _key in _keys:
                    v = confdict.get(_key)
                    line = '  - {}: {}'.format(_key, v)
                    rst.addLines(line)

        outp.printf(rst.getRstText())
        if fd:
            fd.close()
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
