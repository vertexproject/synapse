import sys
import asyncio
import inspect
import logging
import argparse
import collections

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.storm as s_storm
import synapse.lib.config as s_config
import synapse.lib.output as s_output
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.version as s_version
import synapse.lib.stormsvc as s_stormsvc

import synapse.lib.stormtypes as s_stormtypes

logger = logging.getLogger(__name__)

poptsToWords = {
    'ex': 'Example',
    'ro': 'Read Only',
}

info_ignores = (
    'stortype',
)

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
        typed = {t[0]: t for t in types}
        ctord = {c[0]: c for c in ctors}
        self.formhelp = {}  # form name -> ex string for a given type
        for form in forms:
            formname = form[0]
            tnfo = typed.get(formname)
            ctor = ctord.get(formname)
            if tnfo:
                tnfo = tnfo[2]
                example = tnfo.get('ex')
                self.formhelp[formname] = example
            elif ctor:
                ctor = ctor[3]
                example = ctor.get('ex')
                self.formhelp[formname] = example
            else:  # pragma: no cover
                logger.warning(f'No ctor/type available for [{formname}]')

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
                         f'An example of ``{name}``{raw_back_slash_colon}',
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

        for key in info_ignores:
            info.pop(key, None)

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
                         f'An example of ``{name}``{raw_back_slash_colon}',
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

        for key in info_ignores:
            info.pop(key, None)

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

        baseline = f'The base type for the form can be found at :ref:`dm-type-{name.replace(":", "-")}`.'
        rst.addLines(doc,
                     '',
                     baseline,
                     '')

        ex = dochelp.formhelp.get(name)
        if ex:
            rst.addLines('',
                         f'An example of ``{name}``{raw_back_slash_colon}',
                         '',
                         f' * ``{ex}``',
                         ''
                         )

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

    # Validate examples
    for form, example in dochelp.formhelp.items():
        if example is None:
            continue
        if example.startswith('('):
            q = f"[{form}={example}]"
        else:
            q = f"[{form}='{example}']"
        node = False
        async for (mtyp, mnfo) in core.storm(q, {'editformat': 'none'}):
            if mtyp in ('init', 'fini'):
                continue
            if mtyp == 'err':  # pragma: no cover
                raise s_exc.SynErr(mesg='Invalid example', form=form, example=example, info=mnfo)
            if mtyp == 'node':
                node = True
        if not node:  # pramga: no cover
            raise s_exc.SynErr(mesg='Unable to make a node from example.', form=form, example=example)

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

async def docConfdefs(ctor, reflink=':ref:`devops-cell-config`'):
    cls = s_dyndeps.tryDynLocal(ctor)

    if not hasattr(cls, 'confdefs'):
        raise Exception('ctor must have a confdefs attr')

    rst = RstHelp()

    clsname = cls.__name__
    conf = cls.initCellConf()  # type: s_config.Config

    rst.addHead(f'{clsname} Configuration Options', lvl=0, link=f'.. _autodoc-{clsname.lower()}-conf:')
    rst.addLines(f'The following are boot-time configuration options for the cell.')

    rst.addLines(f'See {reflink} for details on how to set these options.')

    # access raw config data

    # Get envar and argparse mapping
    name2envar = conf.getEnvarMapping()
    name2cmdline = conf.getCmdlineMapping()

    schema = conf.json_schema.get('properties', {})

    for name, conf in sorted(schema.items(), key=lambda x: x[0]):

        nodesc = f'No description available for ``{name}``.'
        hname = name
        if ':' in name:
            hname = name.replace(':', raw_back_slash_colon)

        rst.addHead(hname, lvl=1)

        desc = conf.get('description', nodesc)
        if not desc.endswith('.'):  # pragma: no cover
            logger.warning(f'Description for [{name}] is missing a period.')

        lines = []
        lines.append(desc)

        extended_description = conf.get('extended_description')
        if extended_description:
            lines.append('\n')
            lines.append(extended_description)

        # Type/additional information

        lines.append('\n')
        # lines.append('Configuration properties:\n')

        ctyp = conf.get('type')
        lines.append('Type')
        lines.append(f'    ``{ctyp}``\n')

        defval = conf.get('default', s_common.novalu)
        if defval is not s_common.novalu:
            lines.append('Default Value')
            lines.append(f'    ``{repr(defval)}``\n')

        envar = name2envar.get(name)
        if envar:
            lines.append('Environment Variable')
            lines.append(f'    ``{envar}``\n')

        cmdline = name2cmdline.get(name)
        if cmdline:
            lines.append('Command Line Argument')
            lines.append(f'    ``--{cmdline}``\n')

        rst.addLines(*lines)

    return rst, clsname

async def docStormsvc(ctor):
    cls = s_dyndeps.tryDynLocal(ctor)

    if not hasattr(cls, 'cellapi'):
        raise Exception('ctor must have a cellapi attr')

    clsname = cls.__name__

    cellapi = cls.cellapi

    if not issubclass(cellapi, s_stormsvc.StormSvc):
        raise Exception('cellapi must be a StormSvc implementation')

    # Make a dummy object
    class MockSess:
        def __init__(self):
            self.user = None

    class DummyLink:
        def __init__(self):
            self.info = {'sess': MockSess()}

        def get(self, key):
            return self.info.get(key)

    async with await cellapi.anit(s_common.novalu, DummyLink(), s_common.novalu) as obj:
        svcinfo = await obj.getStormSvcInfo()

    rst = RstHelp()

    # Disable default python highlighting
    rst.addLines('.. highlight:: none\n')

    rst.addHead(f'{clsname} Storm Service')
    lines = ['The following Storm Packages and Commands are available from this service.',
             f'This documentation is generated for version '
             f'{s_version.fmtVersion(*svcinfo.get("vers"))} of the service.',
             f'The Storm Service name is ``{svcinfo.get("name")}``.',
             ]
    rst.addLines(*lines)

    for pkg in svcinfo.get('pkgs'):
        pname = pkg.get('name')
        pver = pkg.get('version')
        commands = pkg.get('commands')

        hname = pname
        if ':' in pname:
            hname = pname.replace(':', raw_back_slash_colon)

        rst.addHead(f'Storm Package\\: {hname}', lvl=1)

        rst.addLines(f'This documentation for {pname} is generated for version {s_version.fmtVersion(*pver)}')

        if commands:
            rst.addHead('Storm Commands', lvl=2)

            rst.addLines(f'This package implements the following Storm Commands.\n')

            for cdef in commands:

                cname = cdef.get('name')
                cdesc = cdef.get('descr')
                cargs = cdef.get('cmdargs')

                # command names cannot have colons in them thankfully

                rst.addHead(cname, lvl=3)

                # Form the description
                lines = ['::\n']

                # Generate help from args
                pars = s_storm.Parser(prog=cname, descr=cdesc)
                if cargs:
                    for (argname, arginfo) in cargs:
                        pars.add_argument(argname, **arginfo)
                pars.help()

                for line in pars.mesgs:
                    if '\n' in line:
                        for subl in line.split('\n'):
                            lines.append(f'    {subl}')
                    else:
                        lines.append(f'    {line}')

                lines.append('\n')

                forms = cdef.get('forms', {})
                iforms = forms.get('input')
                oforms = forms.get('output')
                if iforms:
                    line = 'The command is aware of how to automatically handle the following forms as input nodes:\n'
                    lines.append(line)
                    for form in iforms:
                        lines.append(f'- ``{form}``')
                    lines.append('\n')

                if oforms:
                    line = 'The command may make the following types of nodes in the graph as a result of its execution:\n'
                    lines.append(line)
                    for form in oforms:
                        lines.append(f'- ``{form}``')
                    lines.append('\n')

                rst.addLines(*lines)

        # TODO: Modules are not currently documented.

    return rst, clsname

def ljuster(ilines):
    '''Helper to lstrip lines of whitespace an appropriate amount.'''
    baseline = ilines[0]
    assert baseline != ''
    newbaseline = baseline.lstrip()
    assert newbaseline != ''
    diff = len(baseline) - len(newbaseline)
    assert diff >= 0
    newlines = [line[diff:] for line in ilines]
    return newlines

def scrubLines(lines):
    '''Remove any empty lines until we encounter non-empty linee'''
    newlines = []
    for line in lines:
        if line == '' and not newlines:
            continue
        newlines.append(line)

    return newlines

def getDoc(obj, errstr):
    '''Helper to get __doc__'''
    doc = getattr(obj, '__doc__')
    if doc is None:
        doc = f'No doc for {errstr}'
        logger.warning(doc)
    return doc

def cleanArgsRst(doc):
    '''Clean up args strings to be RST friendly.'''
    replaces = (('*args', '\\*args'),
                ('*vals', '\\*vals'),
                ('**info', '\\*\\*info'),
                ('**kwargs', '\\*\\*kwargs'),
                )
    for (new, old) in replaces:
        doc = doc.replace(new, old)
    return doc

def getCallsig(func):
    '''Get the callsig of a function, stripping self if present.'''
    callsig = inspect.signature(func)
    params = list(callsig.parameters.values())
    if params and params[0].name == 'self':
        callsig = callsig.replace(parameters=params[1:])
    return callsig

def prepareRstLines(doc, cleanargs=False):
    '''Prepare a __doc__ string for RST lines.'''
    if cleanargs:
        doc = cleanArgsRst(doc)
    lines = doc.split('\n')
    lines = scrubLines(lines)
    lines = ljuster(lines)
    return lines

def docStormLibs(libs):
    page = RstHelp()

    page.addHead('Storm Libraries', lvl=0, link='.. _stormtypes-libs-header:')

    lines = (
        '',
        'Storm Libraries represent powerful tools available inside of the Storm query language.',
        ''
    )
    page.addLines(*lines)

    basepath = 'lib'

    for (path, lib) in libs:
        libpath = '.'.join((basepath,) + path)
        fulllibpath = f'${libpath}'

        liblink = f'.. _stormlibs-{libpath.replace(".", "-")}:'
        page.addHead(fulllibpath, lvl=1, link=liblink)

        libdoc = getDoc(lib, fulllibpath)
        lines = prepareRstLines(libdoc)

        page.addLines(*lines)

        for (name, locl) in sorted(list(lib.getObjLocals(lib).items())):  # python trick

            loclpath = '.'.join((libpath, name))
            locldoc = getDoc(locl, loclpath)

            loclfullpath = f'${loclpath}'
            header = loclfullpath
            link = f'.. _stormlibs-{loclpath.replace(".", "-")}:'
            lines = None

            if callable(locl):
                lines = prepareRstLines(locldoc, cleanargs=True)
                callsig = getCallsig(locl)
                header = f'{header}{callsig}'
                header = header.replace('*', r'\*')

            elif isinstance(locl, property):
                lines = prepareRstLines(locldoc)

            else:  # pragma: no cover
                logger.warning(f'Unknown constant found: {loclfullpath} -> {locl}')

            if lines:
                page.addHead(header, lvl=2, link=link)
                page.addLines(*lines)

    return page

def docStormPrims(types):
    page = RstHelp()

    page.addHead('Storm Types', lvl=0, link='.. _stormtypes-prim-header:')

    lines = (
        '',
        'Storm Objects are used as view objects for manipulating data in the Storm Runtime and in the Cortex itself.'
        ''
    )
    page.addLines(*lines)

    for (sname, styp) in types:

        typelink = f'.. _stormprims-{sname}:'
        page.addHead(sname, lvl=1, link=typelink)

        typedoc = getDoc(styp, sname)
        lines = prepareRstLines(typedoc)

        page.addLines(*lines)

        locls = styp.getObjLocals(styp)

        for (name, locl) in sorted(list(locls.items())):

            loclname = '.'.join((sname, name))
            locldoc = getDoc(locl, loclname)

            header = loclname
            link = f'.. _stormprims-{loclname.replace(".", "-")}:'
            lines = None

            if callable(locl):

                lines = prepareRstLines(locldoc, cleanargs=True)

                callsig = getCallsig(locl)

                header = f'{loclname}{callsig}'
                header = header.replace('*', r'\*')

            elif isinstance(locl, property):

                lines = prepareRstLines(locldoc)

            else:  # pragma: no cover
                logger.warning(f'Unknown constant found: {loclname} -> {locl}')

            if lines:
                page.addHead(header, lvl=2, link=link)
                page.addLines(*lines)

    return page

async def docStormTypes():
    registry = s_stormtypes.registry
    libs = registry.iterLibs()
    types = registry.iterTypes()

    libs.sort(key=lambda x: x[0])
    types.sort(key=lambda x: x[0])

    libspage = docStormLibs(libs)  # type: RstHelp
    typespage = docStormPrims(types)  # type: RstHelp

    return libspage, typespage

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

    if opts.doc_conf:
        confdocs, cname = await docConfdefs(opts.doc_conf,
                                            reflink=opts.doc_conf_reflink)

        if opts.savedir:
            with open(s_common.genpath(opts.savedir, f'conf_{cname.lower()}.rst'), 'wb') as fd:
                fd.write(confdocs.getRstText().encode())

    if opts.doc_storm:
        confdocs, svcname = await docStormsvc(opts.doc_storm)

        if opts.savedir:
            with open(s_common.genpath(opts.savedir, f'stormsvc_{svcname.lower()}.rst'), 'wb') as fd:
                fd.write(confdocs.getRstText().encode())

    if opts.doc_stormtypes:
        libdocs, typedocs = await docStormTypes()
        if opts.savedir:
            with open(s_common.genpath(opts.savedir, f'stormtypes_libs.rst'), 'wb') as fd:
                fd.write(libdocs.getRstText().encode())
            with open(s_common.genpath(opts.savedir, f'stormtypes_prims.rst'), 'wb') as fd:
                fd.write(typedocs.getRstText().encode())

    return 0

def makeargparser():
    desc = 'Command line tool to generate various synapse documentation.'
    pars = argparse.ArgumentParser('synapse.tools.autodoc', description=desc)

    pars.add_argument('--cortex', '-c', default=None,
                      help='Cortex URL for model inspection')
    pars.add_argument('--savedir', default=None,
                      help='Save output to the given directory')
    doc_type = pars.add_mutually_exclusive_group()
    doc_type.add_argument('--doc-model', action='store_true', default=False,
                          help='Generate RST docs for the DataModel within a cortex')
    doc_type.add_argument('--doc-conf', default=None,
                          help='Generate RST docs for the Confdefs for a given Cell ctor')
    pars.add_argument('--doc-conf-reflink', default=':ref:`devops-cell-config`',
                      help='Reference link for how to set the cell configuration options.')

    doc_type.add_argument('--doc-storm', default=None,
                          help='Generate RST docs for a stormssvc implemented by a given Cell')

    doc_type.add_argument('--doc-stormtypes', default=None, action='store_true',
                          help='Generate RST docs for StormTypes')

    return pars

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    asyncio.run(main(sys.argv[1:]))
