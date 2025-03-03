import sys
import copy
import asyncio
import logging
import argparse
import collections

from typing import List, Tuple, Dict, Union

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.json as s_json
import synapse.lib.storm as s_storm
import synapse.lib.config as s_config
import synapse.lib.output as s_output
import synapse.lib.autodoc as s_autodoc
import synapse.lib.dyndeps as s_dyndeps
import synapse.lib.version as s_version
import synapse.lib.stormsvc as s_stormsvc
import synapse.lib.stormtypes as s_stormtypes

import synapse.tools.genpkg as s_genpkg

logger = logging.getLogger(__name__)

# src / name / target
EdgeDef = Tuple[Union[str, None], str, Union[str, None]]
EdgeDict = Dict[str, str]
Edge = Tuple[EdgeDef, EdgeDict]
Edges = List[Edge]

poptsToWords = {
    'ex': 'Example',
    'ro': 'Read Only',
    'deprecated': 'Deprecated',
    'disp': 'Display',
}

info_ignores = (
    'stortype',
    'bases',
    'custom',
    'template',
    'display',
    'deprecated',
)

raw_back_slash_colon = r'\:'


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

        ifaces = info.pop('interfaces', None)
        if ifaces:
            rst.addLines('', 'This type implements the following interfaces:', '')
            for iface in ifaces:
                rst.addLines(f' * ``{iface}``')

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
                         f'This type has the following options set:',
                         ''
                         )

            for key, valu in sorted(topt.items(), key=lambda x: x[0]):
                if key == 'enums':
                    if valu is None:
                        continue
                    lines = [f' * {key}:\n']
                    elines = []
                    if isinstance(valu, str):
                        # handle str
                        enums = valu.split(',')
                        header = 'valu'
                        maxa = max((len(enum) for enum in enums))
                        maxa = max(maxa, len(header))

                        seprline = f'+{"-" * maxa}+'
                        elines.append(seprline)
                        line = f'+{header}{" " * (maxa - len(header))}+'
                        elines.append(line)
                        line = f'+{"=" * maxa}+'
                        elines.append(line)
                        for enum in enums:
                            line = f'+{enum}{" " * (maxa - len(enum))}+'
                            elines.append(line)
                            elines.append(seprline)

                    elif isinstance(valu, (list, tuple)):
                        # handle enum list
                        valu = sorted(valu, key=lambda x: x[0])

                        maxa, maxb = len('int'), len('valu')
                        for (a, b) in valu:
                            maxa = max(len(str(a)), maxa)
                            maxb = max(len(b), maxb)
                        line = f'{"=" * maxa} {"=" * maxb}'
                        elines.append(line)
                        line = f'int{" " * (maxa - 3)} valu{" " * (maxb - 4)}'
                        elines.append(line)
                        line = f'{"=" * maxa} {"=" * maxb}'
                        elines.append(line)

                        for (a, b) in valu:
                            line = f'{a}{" " * (maxa - len(str(a)))} {b}{" " * (maxb - len(b))}'
                            elines.append(line)

                        line = f'{"=" * maxa} {"=" * maxb}'
                        elines.append(line)

                    else:  # pragma: no cover
                        raise ValueError(f'Unknown enum type {type(valu)} for {name}')

                    elines = ['    ' + line for line in elines]
                    lines.extend(elines)
                    lines.append('\n')
                    rst.addLines(*lines)

                elif key in ('fields',
                             'schema',
                             ):
                    if len(str(valu)) < 80:
                        rst.addLines(f' * {key}: ``{valu}``')
                        continue
                    lines = [f' * {key}:\n', '  ::\n\n']
                    json_lines = s_json.dumps(valu, indent=True, sort_keys=True).decode()
                    json_lines = ['   ' + line for line in json_lines.split('\n')]
                    lines.extend(json_lines)
                    lines.append('\n')
                    rst.addLines(*lines)
                else:
                    rst.addLines(f' * {key}: ``{valu}``')

        for key in info_ignores:
            info.pop(key, None)

        if info:
            logger.warning(f'Type {name} has unhandled info: {info}')

def has_popts_data(props):
    # Props contain "doc" which we pop out
    # Check if a list of props has any keys
    # which are not 'doc'
    for _, _, popts in props:
        keys = set(popts.keys())
        if 'doc' in keys:
            keys.remove('doc')
        if keys:
            return True

    return False

def processFormsProps(rst, dochelp, forms, univ_names, alledges):
    rst.addHead('Forms', lvl=1, link='.. _dm-forms:')
    rst.addLines('',
                 'Forms are derived from types, or base types. Forms represent node types in the graph.'
                 '')

    for name, info, props in forms:

        formedges = lookupedgesforform(name, alledges)

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

        props = [blob for blob in props if blob[0] not in univ_names]

        if props:

            has_popts = has_popts_data(props)

            rst.addLines('', '', f'  Properties:', )
            rst.addLines('   .. list-table::',
                         '      :header-rows: 1',
                         '      :widths: auto',
                         '      :class: tight-table',
                         '')
            header = ('      * - name',
                      '        - type',
                      '        - doc',
                      )
            if has_popts:
                header = header + ('        - opts',)
            rst.addLines(*header)

            for pname, (ptname, ptopts), popts in props:

                _ = popts.pop('doc', None)
                doc = dochelp.props.get((name, pname))
                if not doc.endswith('.'):
                    logger.warning(f'Docstring for prop ({name}, {pname}) does not end with a period.]')
                    doc = doc + '.'

                hptlink = f'dm-type-{ptname.replace(":", "-")}'

                rst.addLines(f'      * - ``:{pname}``',)
                if ptopts:

                    rst.addLines(f'        - | :ref:`{hptlink}`', )
                    for k, v in ptopts.items():
                        if ptname == 'array' and k == 'type':
                            tlink = f'dm-type-{v.replace(":", "-")}'
                            rst.addLines(f'          | {k}: :ref:`{tlink}`', )
                        else:
                            rst.addLines(f'          | {k}: ``{v}``', )

                else:
                    rst.addLines(f'        - :ref:`{hptlink}`',)

                rst.addLines(f'        - {doc}',)

                if has_popts:
                    if popts:
                        if len(popts) == 1:
                            for k, v in popts.items():
                                k = poptsToWords.get(k, k.replace(':', raw_back_slash_colon))
                                rst.addLines(f'        - {k}: ``{v}``')
                        else:
                            for i, (k, v) in enumerate(popts.items()):
                                k = poptsToWords.get(k, k.replace(':', raw_back_slash_colon))
                                if i == 0:
                                    rst.addLines(f'        - | {k}: ``{v}``')
                                else:
                                    rst.addLines(f'          | {k}: ``{v}``')
                    else:
                        rst.addLines(f'        - ')

        if formedges:

            source_edges = formedges.pop('source', None)
            dst_edges = formedges.pop('target', None)
            generic_edges = formedges.pop('generic', None)

            if source_edges:
                if generic_edges:
                    source_edges.extend(generic_edges)

                rst.addLines(f'  Source Edges:',)
                rst.addLines('   .. list-table::',
                             '      :header-rows: 1',
                             '      :widths: auto',
                             '      :class: tight-table',
                             '',
                             '      * - source',
                             '        - verb',
                             '        - target',
                             '        - doc',
                             )

                _edges = []
                for (edef, enfo) in source_edges:
                    src, enam, dst = edef
                    doc = enfo.pop('doc', None)

                    if src is None:
                        src = '*'
                    if dst is None:
                        dst = '*'

                    for key in info_ignores:
                        enfo.pop(key, None)

                    if enfo:
                        logger.warning(f'{name} => Light edge {enam} has unhandled info: {enfo}')
                    _edges.append((src, enam, dst, doc))
                _edges.sort(key=lambda x: x[:2])

                for src, enam, dst, doc in _edges:
                    rst.addLines(f'      * - ``{src}``',
                                 f'        - ``-({enam})>``',
                                 f'        - ``{dst}``',
                                 f'        - {doc}',
                                 )

            if dst_edges:
                if generic_edges:
                    dst_edges.extend(generic_edges)

                rst.addLines(f'  Target Edges:', )
                rst.addLines('   .. list-table::',
                             '      :header-rows: 1',
                             '      :widths: auto',
                             '      :class: tight-table',
                             '',
                             '      * - source',
                             '        - verb',
                             '        - target',
                             '        - doc',
                             )

                _edges = []
                for (edef, enfo) in dst_edges:
                    src, enam, dst = edef
                    doc = enfo.pop('doc', None)
                    if src is None:
                        src = '*'
                    if dst is None:
                        dst = '*'

                    for key in info_ignores:
                        enfo.pop(key, None)

                    if enfo:
                        logger.warning(f'{name} => Light edge {enam} has unhandled info: {enfo}')

                    _edges.append((src, enam, dst, doc))
                _edges.sort(key=lambda x: x[:2])

                for src, enam, dst, doc in _edges:
                    rst.addLines(f'      * - ``{src}``',
                                 f'        - ``-({enam})>``',
                                 f'        - ``{dst}``',
                                 f'        - {doc}',
                                 )

                rst.addLines('', '')

            if formedges:
                logger.warning(f'{name} has unhandled light edges: {formedges}')

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

async def processStormCmds(rst, pkgname, commands):
    '''

    Args:
        rst (RstHelp):
        pkgname (str):
        commands (list):

    Returns:
        None
    '''
    rst.addHead('Storm Commands', lvl=2)

    rst.addLines(f'This package implements the following Storm Commands.\n')

    commands = sorted(commands, key=lambda x: x.get('name'))

    for cdef in commands:

        cname = cdef.get('name')
        cdesc = cdef.get('descr')
        cargs = cdef.get('cmdargs')

        # command names cannot have colons in them thankfully
        cref = f'.. _stormcmd-{pkgname.replace(":", "-")}-{cname.replace(".", "-")}:'
        rst.addHead(cname, lvl=3, link=cref)

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
        nodedata = forms.get('nodedata')

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

        if nodedata:
            line = 'The command may add nodedata with the following keys to the corresponding forms:\n'
            lines.append(line)
            for key, form in nodedata:
                lines.append(f'- ``{key}`` on ``{form}``')
            lines.append('\n')

        rst.addLines(*lines)

async def processStormModules(rst, pkgname, modules):

    rst.addHead('Storm Modules', lvl=2)

    hasapi = False
    modules = sorted(modules, key=lambda x: x.get('name'))

    for mdef in modules:

        apidefs = mdef.get('apidefs')
        if not apidefs:
            continue

        if not hasapi:
            rst.addLines('This package implements the following Storm Modules.\n')
            hasapi = True

        mname = mdef['name']

        mref = f'.. _stormmod-{pkgname.replace(":", "-")}-{mname.replace(".", "-")}:'
        rst.addHead(mname, lvl=3, link=mref)

        for apidef in apidefs:

            apiname = apidef['name']
            apidesc = apidef['desc']
            apitype = apidef['type']

            callsig = s_autodoc.genCallsig(apitype)
            rst.addHead(f'{apiname}{callsig}', lvl=4)
            if depr := apidef.get('deprecated'):
                rst.addLines(*s_autodoc.genDeprecationWarning(apiname, depr, True))
            rst.addLines(*s_autodoc.prepareRstLines(apidesc))
            rst.addLines(*s_autodoc.getArgLines(apitype))
            rst.addLines(*s_autodoc.getReturnLines(apitype))

    if not hasapi:
        rst.addLines('This package does not export any Storm APIs.\n')

def lookupedgesforform(form: str, edges: Edges) -> Dict[str, Edges]:
    ret = collections.defaultdict(list)

    for edge in edges:
        src, name, dst = edge[0]

        # src and dst may be None, form==name, or form!=name.
        # This gives us 9 possible states to consider.
        # src  |  dst | -> ret
        # ===================================
        # none | none | -> generic
        # none |   != | -> source
        # none |    = | -> target
        #   != | none | -> target
        #    = | none | -> source
        #   != |    = | -> target
        #    = |   != | -> source
        #   != |   != | -> no-op
        #    = |    = | -> source, target

        if src is None and dst is None:
            ret['generic'].append(edge)
            continue
        if src is None and dst != form:
            ret['source'].append(edge)
            continue
        if src is None and dst == form:
            ret['target'].append(edge)
            continue
        if src != form and dst is None:
            ret['target'].append(edge)
            continue
        if src == form and dst is None:
            ret['source'].append(edge)
            continue
        if src != form and dst == form:
            ret['target'].append(edge)
            continue
        if src == form and dst != form:
            ret['source'].append(edge)
            continue
        if src != form and dst != form:
            # no-op
            continue
        if src == form and dst == form:
            ret['source'].append(edge)
            ret['target'].append(edge)

    return copy.deepcopy(dict(ret))

async def docModel(outp,
                   core):
    coreinfo = await core.getCoreInfo()
    _, model = coreinfo.get('modeldef')[0]

    ctors = model.get('ctors')
    types = model.get('types')
    forms = model.get('forms')
    univs = model.get('univs')
    edges = model.get('edges')
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
        if not node:  # pragma: no cover
            raise s_exc.SynErr(mesg='Unable to make a node from example.', form=form, example=example)

    rst = s_autodoc.RstHelp()
    rst.addHead('Synapse Data Model - Types', lvl=0)

    processCtors(rst, dochelp, ctors)
    processTypes(rst, dochelp, types)

    rst2 = s_autodoc.RstHelp()
    rst2.addHead('Synapse Data Model - Forms', lvl=0)

    processFormsProps(rst2, dochelp, forms, univ_names, edges)
    processUnivs(rst2, dochelp, univs)

    return rst, rst2

async def docConfdefs(ctor):
    cls = s_dyndeps.tryDynLocal(ctor)

    if not hasattr(cls, 'confdefs'):
        raise Exception('ctor must have a confdefs attr')

    rst = s_autodoc.RstHelp()

    clsname = cls.__name__

    conf = cls.initCellConf()  # type: s_config.Config

    # access raw config data

    # Get envar and argparse mapping
    name2envar = conf.getEnvarMapping()

    schema = conf.json_schema.get('properties', {})

    for name, conf in sorted(schema.items(), key=lambda x: x[0]):

        if conf.get('hideconf'):
            continue

        if conf.get('hidedocs'):
            continue

        nodesc = f'No description available for ``{name}``.'

        desc = conf.get('description', nodesc)
        if not desc.endswith('.'):  # pragma: no cover
            logger.warning(f'Description for [{name}] is missing a period.')

        hname = name.replace(':', raw_back_slash_colon)
        lines = []
        lines.append(hname)
        lines.append('~' * len(hname))
        lines.append('')
        lines.append(desc)

        extended_description = conf.get('extended_description')
        if extended_description:
            lines.append('\n')
            lines.append(extended_description)

        # Type/additional information

        lines.append('\n')

        ctyp = conf.get('type')
        lines.append('Type')
        lines.append(f'    ``{ctyp}``\n')

        if ctyp == 'object':
            if conf.get('properties'):
                lines.append('Properties')
                lines.append('    The object expects the following properties:')
                data = {k: v for k, v in conf.items() if k not in (
                    'description', 'default', 'type', 'hideconf', 'hidecmdl',
                )}
                parts = s_json.dumps(data, sort_keys=True, indent=True).decode().split('\n')
                lines.append('    ::')
                lines.append('\n')
                lines.extend([f'      {p}' for p in parts])
                lines.append('\n')

        defval = conf.get('default', s_common.novalu)
        if defval is not s_common.novalu:
            lines.append('Default Value')
            lines.append(f'    ``{repr(defval)}``\n')

        envar = name2envar.get(name)
        if envar:
            lines.append('Environment Variable')
            lines.append(f'    ``{envar}``\n')

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

    rst = s_autodoc.RstHelp()

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
            await processStormCmds(rst, pname, commands)

        if modules := pkg.get('modules'):
            await processStormModules(rst, pname, modules)

    return rst, clsname

async def docStormpkg(pkgpath):
    pkgdef = s_genpkg.loadPkgProto(pkgpath)
    pkgname = pkgdef.get('name')

    rst = s_autodoc.RstHelp()

    # Disable default python highlighting
    rst.addLines('.. highlight:: none\n')

    hname = pkgname
    if ':' in pkgname:
        hname = pkgname.replace(':', raw_back_slash_colon)

    rst.addHead(f'Storm Package\\: {hname}')
    lines = ['The following Commands are available from this package.',
             f'This documentation is generated for version '
             f'{s_version.fmtVersion(pkgdef.get("version"))} of the package.',
             ]
    rst.addLines(*lines)

    commands = pkgdef.get('commands')
    if commands:
        await processStormCmds(rst, pkgname, commands)

    if modules := pkgdef.get('modules'):
        await processStormModules(rst, pkgname, modules)

    return rst, pkgname

async def docStormTypes():
    registry = s_stormtypes.registry

    libsinfo = registry.getLibDocs()

    libspage = s_autodoc.RstHelp()

    libspage.addHead('Storm Libraries', lvl=0, link='.. _stormtypes-libs-header:')

    lines = (
        '',
        'Storm Libraries represent powerful tools available inside of the Storm query language.',
        ''
    )
    libspage.addLines(*lines)

    # This value is appended to the end of the ref to the first level header of a type.
    # This prevents accidental cross linking between parts of the docs; which can happen
    # when secondary properties of a type may overlap with the main name of the type.
    types_suffix = 'f527'

    s_autodoc.docStormTypes(libspage, libsinfo, linkprefix='stormlibs', islib=True,
                            known_types=registry.known_types, types_prefix='stormprims', types_suffix=types_suffix)

    priminfo = registry.getTypeDocs()
    typespage = s_autodoc.RstHelp()

    typespage.addHead('Storm Types', lvl=0, link='.. _stormtypes-prim-header:')

    lines = (
        '',
        'Storm Objects are used as view objects for manipulating data in the Storm Runtime and in the Cortex itself.'
        ''
    )
    typespage.addLines(*lines)
    s_autodoc.docStormTypes(typespage, priminfo, linkprefix='stormprims', known_types=registry.known_types,
                            types_prefix='stormprims', types_suffix=types_suffix)

    return libspage, typespage

async def main(argv, outp=None):
    if outp is None:
        outp = s_output.OutPut()

    pars = makeargparser()

    opts = pars.parse_args(argv)

    if opts.doc_model:

        if opts.cortex:
            async with s_telepath.withTeleEnv():
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
        confdocs, cname = await docConfdefs(opts.doc_conf)

        if opts.savedir:
            with open(s_common.genpath(opts.savedir, f'conf_{cname.lower()}.rst'), 'wb') as fd:
                fd.write(confdocs.getRstText().encode())

    if opts.doc_storm:
        confdocs, svcname = await docStormsvc(opts.doc_storm)

        if opts.savedir:
            with open(s_common.genpath(opts.savedir, f'stormsvc_{svcname.lower()}.rst'), 'wb') as fd:
                fd.write(confdocs.getRstText().encode())

    if opts.doc_stormpkg:
        pkgdocs, pkgname = await docStormpkg(opts.doc_stormpkg)

        if opts.savedir:
            with open(s_common.genpath(opts.savedir, f'stormpkg_{pkgname.lower()}.rst'), 'wb') as fd:
                fd.write(pkgdocs.getRstText().encode())

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
    doc_type.add_argument('--doc-storm', default=None,
                          help='Generate RST docs for a stormssvc implemented by a given Cell')

    doc_type.add_argument('--doc-stormpkg', default=None,
                          help='Generate RST docs for the specified Storm package YAML file.')

    doc_type.add_argument('--doc-stormtypes', default=None, action='store_true',
                          help='Generate RST docs for StormTypes')

    return pars

if __name__ == '__main__':  # pragma: no cover
    s_common.setlogging(logger, 'DEBUG')
    asyncio.run(main(sys.argv[1:]))
