import sys
import asyncio
import logging
import argparse

import collections

import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

poptsToWords = {
        'ex': 'Example',
        'ro': 'Read Only',
    }

raw_back_slash_colon = r'\:'

# TODO Ensure this is consistent with other documentation.
rstlvls = [
    ('#', {'over': True}),
    ('*', {'over': True}),
    ('=', {}),
    ('-', {}),
    ('^', {}),
]


class DocHelp:
    '''
    Helper to pre-compute all doc strings hierarchically
    '''
    def __init__(self, ctors, types, forms, props, univs):
        self.ctors = {c[0]: c[3].get('doc', 'BaseType has no doc string.') for c in ctors}
        self.types = {t[0]: t[2].get('doc', self.ctors.get(t[1][0])) for t in types}
        self.forms = {f[0]: f[1].get('doc', self.types.get(f[0], self.ctors.get(f[0]))) for f in forms}
        self.univs = {}
        for unam, utyp, unfo in univs:
            tn = utyp[0]
            doc = unfo.get('doc', self.forms.get(tn, self.types.get(tn, self.ctors.get(tn))))
            self.univs[unam] = doc
        self.props = {}
        for form, props in props.items():
            for prop in props:
                tn = prop[1][0]
                doc = prop[2].get('doc', self.forms.get(tn, self.types.get(tn, self.ctors.get(tn))))
                self.props[(form, prop[0])] = doc

class RstHelp:

    def __init__(self):
        self.lines = []

    def addHead(self, name, lvl=0, link=None):
        char, info = rstlvls[lvl]
        under = char * len(name)

        lines = []

        lines.append('')

        if link:
            lines.append('')
            lines.append(link)
            lines.append('')

        if info.get('over'):
            lines.append(under)

        lines.append(name)
        lines.append(under)
        lines.append('')

        self.addLines(*lines)

    def addLines(self, *lines):
        self.lines.extend(lines)

    def getRstText(self):
        return '\n'.join(self.lines)

def processCtors(rst, dochelp, ctors):
    '''

    Args:
        rst (RstHelp):
        dochelp (DocHelp):
        ctors (list):

    Returns:
        None
    '''
    rst.addHead('Base Types', lvl=1, link='.. _dm-base-types:')
    rst.addLines('',
                 'Base types are defined via Python classes.',
                 '')

    for name, ctor, opts, info in ctors:

        doc = dochelp.ctors.get(name)
        if not doc.endswith('.'):
            logger.warning(f'Docstring for ctor {name} does not end with a period.]')
            doc = doc + '.'

        # Break implicit links to nowhere
        hname = name
        if ':' in name:
            hname = name.replace(':', raw_back_slash_colon)

        link = f'.. _dm-type-{name.replace(":", "-")}:'
        rst.addHead(hname, lvl=2, link=link)

        rst.addLines(doc, f'It is implemented by the following class{raw_back_slash_colon} ``{ctor}``.')
        _ = info.pop('doc', None)
        ex = info.pop('ex', None)
        if ex:
            rst.addLines('',
                         f'A example of ``{name}``{raw_back_slash_colon}',
                         '',
                         f' * ``{ex}``',
                         )

        if opts:
            rst.addLines('',
                         f'The base type ``{name}`` has the following default options set:',
                         ''
                         )
            for k, v in opts.items():
                rst.addLines(f' * {k}: ``{v}``')

        if info:
            logger.warning(f'Base type {name} has unhandled info: {info}')

def processTypes(rst, dochelp, types):
    '''

    Args:
        rst (RstHelp):
        dochelp (DocHelp):
        ctors (list):

    Returns:
        None
    '''

    rst.addHead('Types', lvl=1, link='.. _dm-types:')

    rst.addLines('',
                 'Regular types are derived from BaseTypes.',
                 '')

    for name, (ttyp, topt), info in types:

        doc = dochelp.types.get(name)
        if not doc.endswith('.'):
            logger.warning(f'Docstring for type {name} does not end with a period.]')
            doc = doc + '.'

        # Break implicit links to nowhere
        hname = name
        if ':' in name:
            hname = name.replace(':', raw_back_slash_colon)

        link = f'.. _dm-type-{name.replace(":", "-")}:'
        rst.addHead(hname, lvl=2, link=link)

        rst.addLines(doc,
                     f'The ``{name}`` type is derived from the base type: ``{ttyp}``.')

        _ = info.pop('doc', None)
        ex = info.pop('ex', None)
        if ex:
            rst.addLines('',
                         f'A example of {name}{raw_back_slash_colon}:',
                         '',
                         f' * ``{ex}``',
                         )

        if topt:
            rst.addLines('',
                         f'The type ``{name}`` has the following options set:',
                         ''
                         )
            for k, v in sorted(topt.items(), key=lambda x: x[0]):
                rst.addLines(f' * {k}: ``{v}``')

        if info:
            logger.warning(f'Type {name} has unhandled info: {info}')

def processFormsProps(rst, dochelp, forms, univ_names):

    rst.addHead('Forms', lvl=1, link='.. _dm-forms:')
    rst.addLines('',
                 'Forms are derived from types, or base types. Forms represent node types in the graph.'
                 '')

    for name, info, props in forms:

        doc = dochelp.forms.get(name)
        if not doc.endswith('.'):
            logger.warning(f'Docstring for form {name} does not end with a period.]')
            doc = doc + '.'

        hname = name
        if ':' in name:
            hname = name.replace(':', raw_back_slash_colon)
        link = f'.. _dm-form-{name.replace(":", "-")}:'
        rst.addHead(hname, lvl=2, link=link)

        rst.addLines(doc,
                     '')

        if props:
            rst.addLines('Properties:',
                         )
        for pname, (ptname, ptopts), popts in props:

            if pname in univ_names:
                continue

            hpname = pname
            if ':' in pname:
                hpname = pname.replace(':', raw_back_slash_colon)

            _ = popts.pop('doc', None)
            doc = dochelp.props.get((name, pname))
            if not doc.endswith('.'):
                logger.warning(f'Docstring for prop ({name}, {pname}) does not end with a period.]')
                doc = doc + '.'

            rst.addLines('',
                         raw_back_slash_colon + hpname + ' / ' + f'{":".join([hname, hpname])}',
                         '  ' + doc,
                         )

            if popts:

                rst.addLines('  ' + 'It has the following property options set:',
                             ''
                             )
                for k, v in popts.items():
                    k = poptsToWords.get(k, k.replace(':', raw_back_slash_colon))
                    rst.addLines('  ' + f'* {k}: ``{v}``')

            hptlink = f'dm-type-{ptname.replace(":", "-")}'
            tdoc = f'The property type is :ref:`{hptlink}`.'

            rst.addLines('',
                         '  ' + tdoc,
                         )
            if ptopts:
                rst.addLines('  ' + "Its type has the following options set:",
                             '')
                for k, v in ptopts.items():
                    rst.addLines('  ' + f'* {k}: ``{v}``')

def processUnivs(rst, dochelp, univs):
    rst.addHead('Universal Properties', lvl=1, link='.. _dm-universal-props:')

    rst.addLines('',
                 'Universal props are system level properties which may be present on every node.',
                 '',
                 'These properties are not specific to a particular form and exist outside of a particular',
                 'namespace.',
                 '')

    for name, (utyp, uopt), info in univs:

        _ = info.pop('doc', None)
        doc = dochelp.univs.get(name)
        if not doc.endswith('.'):
            logger.warning(f'Docstring for form {name} does not end with a period.]')
            doc = doc + '.'

        hname = name
        if ':' in name:
            hname = name.replace(':', raw_back_slash_colon)

        rst.addHead(hname, lvl=2, link=f'.. _dm-univ-{name.replace(":", "-")}:')

        rst.addLines('',
                     doc,
                     )

        if info:
            rst.addLines('It has the following property options set:',
                         ''
                         )
            for k, v in info.items():
                k = poptsToWords.get(k, k.replace(':', raw_back_slash_colon))
                rst.addLines('  ' + f'* {k}: ``{v}``')

        hptlink = f'dm-type-{utyp.replace(":", "-")}'
        tdoc = f'The universal property type is :ref:`{hptlink}`.'

        rst.addLines('',
                     tdoc,
                     )
        if uopt:
            rst.addLines("Its type has the following options set:",
                         '')
            for k, v in uopt.items():
                rst.addLines('  ' + f'* {k}: ``{v}``')

async def docModel(outp,
             core):
    coreinfo = await core.getCoreInfo()
    _, model = coreinfo.get('modeldef')[0]

    ctors = model.get('ctors')
    types = model.get('types')
    forms = model.get('forms')
    univs = model.get('univs')
    props = collections.defaultdict(list)

    ctors = sorted(ctors, key=lambda x: x[0])
    univs = sorted(univs, key=lambda x: x[0])
    types = sorted(types, key=lambda x: x[0])
    forms = sorted(forms, key=lambda x: x[0])
    univ_names = {univ[0] for univ in univs}

    for fname, fnfo, fprops in forms:
        for prop in fprops:
            props[fname].append(prop)

    [v.sort() for k, v in props.items()]

    dochelp = DocHelp(ctors, types, forms, props, univs)

    rst = RstHelp()
    rst.addHead('Synapse Data Model - Types', lvl=0)

    processCtors(rst, dochelp, ctors)
    processTypes(rst, dochelp, types)

    rst2 = RstHelp()
    rst2.addHead('Synapse Data Model - Forms', lvl=0)

    processFormsProps(rst2, dochelp, forms, univ_names)
    processUnivs(rst2, dochelp, univs)

    # outp.printf(rst.getRstText())
    # outp.printf(rst2.getRstText())
    return rst, rst2

async def main(argv, outp=None):

    if outp is None:
        outp = s_output.OutPut()

    pars = makeargparser()

    opts = pars.parse_args(argv)

    if opts.doc_model:

        if opts.cortex:
            async with await s_telepath.openurl(opts.cortex) as core:
                rsttypes, rstforms = await docModel(outp, core)

        else:
            async with s_cortex.getTempCortex() as core:
                rsttypes, rstforms = await docModel(outp, core)

        if opts.savedir:
            with open(s_common.genpath(opts.savedir, 'datamodel_types.rst'), 'wb') as fd:
                fd.write(rsttypes.getRstText().encode())
            with open(s_common.genpath(opts.savedir, 'datamodel_forms.rst'), 'wb') as fd:
                fd.write(rstforms.getRstText().encode())

    return 0

def makeargparser():
    desc = 'Command line tool to generate various synapse documentation.'
    pars = argparse.ArgumentParser('synapse.tools.autodoc', description=desc)

    pars.add_argument('--cortex', '-c', default=None,
                      help='Cortex URL for model inspection')
    pars.add_argument('--savedir', default=None,
                      help='Save output to the given directory')
    pars.add_argument('--doc-model', action='store_true', default=False,
                      help='Generate RST docs for the DataModel within a cortex')
    return pars

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    asyncio.run(main(sys.argv[1:]))
