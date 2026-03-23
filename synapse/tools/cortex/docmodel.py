import logging

import synapse.common as s_common
import synapse.cortex as s_cortex
import synapse.telepath as s_telepath

import synapse.lib.cmd as s_cmd
import synapse.lib.output as s_output

logger = logging.getLogger(__name__)

def _getFormDoc(formname, forminfo, types):
    '''Get the doc string for a form, falling back to its type doc.'''
    doc = forminfo.get('doc')
    if doc is not None:
        return doc

    tinfo = types.get(formname)
    if tinfo is not None:
        return tinfo.get('info', {}).get('doc', '')

    return ''

def _getPropDoc(propinfo, types):
    '''Get the doc string for a property, falling back to its type doc.'''
    doc = propinfo.get('doc')
    if doc is not None:
        return doc

    typedef = propinfo.get('type', ())
    if typedef:
        typename = typedef[0] if isinstance(typedef, (list, tuple)) else typedef
        tinfo = types.get(typename)
        if tinfo is not None:
            return tinfo.get('info', {}).get('doc', '')

    return ''

def _escpipe(text):
    '''Escape pipe characters for markdown table cells.'''
    if text is None:
        return ''

    return text.replace('|', '\\|').replace('\n', ' ')

def _resolveTypeNames(typedef):
    '''Resolve a typedef to a list of type name strings, expanding poly types.'''
    if not typedef:
        return ['']

    if isinstance(typedef, str):
        return [typedef]

    if isinstance(typedef, (list, tuple)) and len(typedef) >= 1:
        if typedef[0] == 'poly' and len(typedef) >= 2:
            opts = typedef[1] if isinstance(typedef[1], dict) else {}
            names = set()
            ifaces = opts.get('interfaces')
            if ifaces:
                names.update(ifaces)

            forms = opts.get('forms')
            if forms:
                names.update(forms)

            if names:
                return sorted(names)

            return ['poly']

        if typedef[0] == 'array' and len(typedef) >= 2:
            opts = typedef[1] if isinstance(typedef[1], dict) else {}
            atype = opts.get('type')
            if atype is not None:
                if isinstance(atype, str):
                    return [f'array of {atype}']
                if isinstance(atype, (list, tuple)):
                    return [f'array of {", ".join(sorted(atype))}']

            return ['array']

        return [typedef[0]]

    return ['']

def _resolveIfaces(ifacenames, interfaces):
    '''Recursively resolve all interfaces including inherited ones.'''
    resolved = []
    seen = set()

    def _collect(name):
        if name in seen:
            return
        seen.add(name)
        resolved.append(name)
        iface = interfaces.get(name)
        if iface is not None:
            for subname, _subinfo in iface.get('interfaces', ()):
                _collect(subname)

    for name in ifacenames:
        _collect(name)

    return sorted(resolved)

def _getBaseTypeName(typename, types):
    '''Get the immediate parent base type name.'''
    tinfo = types.get(typename)
    if tinfo is None:
        return None

    bases = tinfo.get('info', {}).get('bases', ())
    if bases:
        return bases[-1]

    return None

def _genPropTable(props, types, prefix=':'):
    '''Generate markdown property table rows for a set of properties.'''
    lines = []
    lines.append('| Property | Type | Doc |')
    lines.append('|----------|------|-----|')

    for propname in sorted(props.keys()):
        propinfo = props[propname]
        typedef = propinfo.get('type', ())
        typenames = _resolveTypeNames(typedef)
        typecell = ', '.join(f'`{_escpipe(n)}`' for n in typenames)
        propdoc = _getPropDoc(propinfo, types)
        lines.append(f'| `{prefix}{propname}` | {typecell} | {_escpipe(propdoc)} |')

    return lines

def _genTypeDetail(typename, types, interfaces, seen=None):
    '''Generate a detailed markdown section for a type.'''
    if seen is None:
        seen = set()

    if typename in seen:
        return []

    seen.add(typename)

    tinfo = types.get(typename)
    if tinfo is None:
        return []

    lines = []
    tdoc = tinfo.get('info', {}).get('doc', '')
    bases = tinfo.get('info', {}).get('bases', ())
    opts = tinfo.get('opts', {})
    ifaces = tinfo.get('info', {}).get('interfaces', ())

    lines.append(f'### `{typename}`')
    lines.append('')

    if tdoc:
        lines.append(tdoc)
        lines.append('')

    if bases:
        basetype = bases[-1]
        lines.append(f'The `{typename}` type is derived from the base type: `{basetype}`.')
        lines.append('')

    if ifaces:
        ifacenames = [name for name, _info in ifaces]
        allifaces = _resolveIfaces(ifacenames, interfaces)
        lines.append('This type implements the following interfaces:')
        lines.append('')
        for ifname in allifaces:
            lines.append(f'- `{ifname}`')

        lines.append('')

    if opts:
        basetype = bases[-1] if bases else typename
        lines.append(f'The base type `{basetype}` has the following default options set:')
        lines.append('')
        lines.append('| Option | Value |')
        lines.append('|--------|-------|')

        for key in sorted(opts.keys()):
            val = opts[key]
            if val is None:
                lines.append(f'| `{key}` | None |')
            elif isinstance(val, (list, tuple)):
                if not val:
                    lines.append(f'| `{key}` | () |')
                else:
                    lines.append(f'| `{key}` | `{_escpipe(str(val))}` |')
            elif isinstance(val, bool):
                lines.append(f'| `{key}` | {str(val)} |')
            else:
                lines.append(f'| `{key}` | `{_escpipe(str(val))}` |')

        lines.append('')

    return lines

def _lookupEdgesForForm(formname, edges):
    '''Classify edges as source, target, or generic relative to a form.'''
    retn = {}

    for edge in edges:
        src, verb, dst = edge[0]

        if src is None and dst is None:
            retn.setdefault('generic', []).append(edge)
        elif src is None and dst != formname:
            retn.setdefault('source', []).append(edge)
        elif src is None and dst == formname:
            retn.setdefault('target', []).append(edge)
        elif src != formname and dst is None:
            retn.setdefault('target', []).append(edge)
        elif src == formname and dst is None:
            retn.setdefault('source', []).append(edge)
        elif src != formname and dst == formname:
            retn.setdefault('target', []).append(edge)
        elif src == formname and dst != formname:
            retn.setdefault('source', []).append(edge)
        elif src == formname and dst == formname:
            retn.setdefault('source', []).append(edge)
            retn.setdefault('target', []).append(edge)

    return retn

async def genFormMarkdown(core, formname):
    '''Generate detailed markdown for a single form.'''

    modeldict = await core.getModelDict()

    types = modeldict.get('types', {})
    forms = modeldict.get('forms', {})
    edges = modeldict.get('edges', [])
    interfaces = modeldict.get('interfaces', {})

    forminfo = forms.get(formname)
    if forminfo is None:
        return f'Form `{formname}` not found in model.'

    formprops = forminfo.get('props', {})
    formdoc = _getFormDoc(formname, forminfo, types)

    lines = []
    lines.append(f'# `{formname}`')
    lines.append('')

    if formdoc:
        lines.append(formdoc)
        lines.append('')

    basetype = _getBaseTypeName(formname, types)
    if basetype is not None:
        lines.append(f'The `{formname}` type is derived from the base type: `{basetype}`.')
        lines.append('')

    # Interfaces
    formtype = types.get(formname)
    if formtype is not None:
        directifaces = [name for name, _info in formtype.get('info', {}).get('interfaces', ())]
        allifaces = _resolveIfaces(directifaces, interfaces)
        if allifaces:
            lines.append('## Interfaces')
            lines.append('')
            lines.append('| Interface |')
            lines.append('|-----------|')

            for ifname in allifaces:
                ifdoc = interfaces.get(ifname, {}).get('doc', '')
                if ifdoc:
                    lines.append(f'| `{ifname}` - {_escpipe(ifdoc)} |')
                else:
                    lines.append(f'| `{ifname}` |')

            lines.append('')

    # Properties
    nestedtypes = set()

    if basetype is not None:
        nestedtypes.add(basetype)

    if formprops:
        lines.append('## Properties')
        lines.append('')
        lines.extend(_genPropTable(formprops, types))
        lines.append('')

        for propinfo in formprops.values():
            typedef = propinfo.get('type', ())
            if typedef:
                if isinstance(typedef, (list, tuple)) and len(typedef) >= 1:
                    tname = typedef[0]
                    if tname == 'array' and len(typedef) >= 2:
                        opts = typedef[1] if isinstance(typedef[1], dict) else {}
                        atype = opts.get('type')
                        if isinstance(atype, str):
                            nestedtypes.add(atype)
                    elif tname != 'poly':
                        nestedtypes.add(tname)

    # Referenced Types
    if nestedtypes:
        lines.append('## Referenced Types')
        lines.append('')

        seen = set()
        seen.add(formname)
        for tname in sorted(nestedtypes):
            detail = _genTypeDetail(tname, types, interfaces, seen)
            if detail:
                lines.extend(detail)

    # Edges
    formedges = _lookupEdgesForForm(formname, edges)

    srcedges = formedges.get('source', [])
    dstedges = formedges.get('target', [])
    genedges = formedges.get('generic', [])

    if srcedges or genedges:
        alledges = srcedges + genedges
        alledges.sort(key=lambda e: (e[0][0] or '*', e[0][1], e[0][2] or '*'))

        lines.append('## Source Edges')
        lines.append('')
        lines.append('| Source | Verb | Target | Doc |')
        lines.append('|--------|------|--------|-----|')

        for edef, einfo in alledges:
            src, verb, dst = edef
            doc = einfo.get('doc', '')
            src = src or '*'
            dst = dst or '*'
            lines.append(f'| `{_escpipe(src)}` | `-({_escpipe(verb)})>` | `{_escpipe(dst)}` | {_escpipe(doc)} |')

        lines.append('')

    if dstedges or genedges:
        alledges = dstedges + genedges
        alledges.sort(key=lambda e: (e[0][0] or '*', e[0][1], e[0][2] or '*'))

        lines.append('## Target Edges')
        lines.append('')
        lines.append('| Source | Verb | Target | Doc |')
        lines.append('|--------|------|--------|-----|')

        for edef, einfo in alledges:
            src, verb, dst = edef
            doc = einfo.get('doc', '')
            src = src or '*'
            dst = dst or '*'
            lines.append(f'| `{_escpipe(src)}` | `-({_escpipe(verb)})>` | `{_escpipe(dst)}` | {_escpipe(doc)} |')

        lines.append('')

    return '\n'.join(lines)

async def genIfaceMarkdown(core, ifacename):
    '''Generate detailed markdown for a single interface.'''

    modeldict = await core.getModelDict()

    types = modeldict.get('types', {})
    forms = modeldict.get('forms', {})
    interfaces = modeldict.get('interfaces', {})

    ifinfo = interfaces.get(ifacename)
    if ifinfo is None:
        return f'Interface `{ifacename}` not found in model.'

    ifdoc = ifinfo.get('doc', '')

    lines = []
    lines.append(f'# `{ifacename}`')
    lines.append('')

    if ifdoc:
        lines.append(ifdoc)
        lines.append('')

    # Parent interfaces
    parents = [name for name, _info in ifinfo.get('interfaces', ())]
    if parents:
        allifaces = _resolveIfaces(parents, interfaces)
        lines.append('## Inherits From')
        lines.append('')
        lines.append('| Interface |')
        lines.append('|-----------|')

        for pname in allifaces:
            lines.append(f'| `{pname}` |')

        lines.append('')

    # Interface properties
    ifprops = ifinfo.get('props', ())
    nestedtypes = set()

    if ifprops:
        lines.append('## Properties')
        lines.append('')
        lines.append('| Property | Type | Doc |')
        lines.append('|----------|------|-----|')

        for propdef in sorted(ifprops, key=lambda x: x[0]):
            propname = propdef[0]
            typedef = propdef[1]
            propinfo = propdef[2] if len(propdef) > 2 else {}

            typenames = _resolveTypeNames(typedef)
            typecell = ', '.join(f'`{_escpipe(n)}`' for n in typenames)
            propdoc = _getPropDoc(propinfo, types)
            lines.append(f'| `:{propname}` | {typecell} | {_escpipe(propdoc)} |')

            if typedef:
                if isinstance(typedef, (list, tuple)) and len(typedef) >= 1:
                    tname = typedef[0]
                    if tname == 'array' and len(typedef) >= 2:
                        opts = typedef[1] if isinstance(typedef[1], dict) else {}
                        atype = opts.get('type')
                        if isinstance(atype, str):
                            nestedtypes.add(atype)
                    elif tname != 'poly':
                        nestedtypes.add(tname)

        lines.append('')

    # Forms implementing this interface
    implforms = []
    for fname in sorted(forms.keys()):
        ftype = types.get(fname)
        for iname, _iinfo in ftype.get('info', {}).get('interfaces', ()):
            if iname == ifacename:
                implforms.append(fname)
                break

    if implforms:
        lines.append('## Implementing Forms')
        lines.append('')
        lines.append('| Form |')
        lines.append('|------|')

        for fname in implforms:
            lines.append(f'| `{fname}` |')

        lines.append('')

    # Referenced Types
    if nestedtypes:
        lines.append('## Referenced Types')
        lines.append('')

        seen = set()
        for tname in sorted(nestedtypes):
            detail = _genTypeDetail(tname, types, interfaces, seen)
            if detail:
                lines.extend(detail)

    return '\n'.join(lines)

async def genModelMarkdown(core):
    '''Generate a markdown string documenting the data model.'''

    modeldict = await core.getModelDict()

    types = modeldict.get('types', {})
    forms = modeldict.get('forms', {})
    edges = modeldict.get('edges', [])
    interfaces = modeldict.get('interfaces', {})
    tagprops = modeldict.get('tagprops', {})

    lines = []
    lines.append('# Synapse Data Model')
    lines.append('')
    lines.append('## Table of Contents')
    lines.append('')
    lines.append('- [Forms](#forms)')
    lines.append('- [Edges](#edges)')
    lines.append('- [Tag Properties](#tag-properties)')
    lines.append('- [Interfaces](#interfaces)')
    lines.append('')

    # Forms section
    lines.append('## Forms')
    lines.append('')

    for formname in sorted(forms.keys()):

        forminfo = forms[formname]
        formprops = forminfo.get('props', {})

        formdoc = _getFormDoc(formname, forminfo, types)

        lines.append(f'### `{formname}`')
        lines.append('')
        if formdoc:
            lines.append(formdoc)
            lines.append('')

        formtype = types.get(formname)
        if formtype is not None:
            directifaces = [name for name, _info in formtype.get('info', {}).get('interfaces', ())]
            allifaces = _resolveIfaces(directifaces, interfaces)
            if allifaces:
                lines.append('| Interface |')
                lines.append('|-----------|')

                for ifname in allifaces:
                    lines.append(f'| `{ifname}` |')

                lines.append('')

        if formprops:
            lines.append('| Property | Type | Doc |')
            lines.append('|----------|------|-----|')

            for propname in sorted(formprops.keys()):
                propinfo = formprops[propname]

                typedef = propinfo.get('type', ())
                typenames = _resolveTypeNames(typedef)
                typecell = ', '.join(f'`{_escpipe(n)}`' for n in typenames)
                propdoc = _getPropDoc(propinfo, types)
                lines.append(f'| `:{propname}` | {typecell} | {_escpipe(propdoc)} |')

            lines.append('')

    # Edges section
    lines.append('## Edges')
    lines.append('')

    if edges:
        lines.append('| Source | Verb | Target | Doc |')
        lines.append('|--------|------|--------|-----|')

        sortededges = sorted(edges, key=lambda e: (
            e[0][0] or '*',
            e[0][1],
            e[0][2] or '*',
        ))

        for edef, einfo in sortededges:
            src, verb, dst = edef
            doc = einfo.get('doc', '')
            src = src or '*'
            dst = dst or '*'
            lines.append(f'| `{_escpipe(src)}` | `{_escpipe(verb)}` | `{_escpipe(dst)}` | {_escpipe(doc)} |')

        lines.append('')

    # Tag Properties section
    lines.append('## Tag Properties')
    lines.append('')

    if tagprops:
        lines.append('| Property | Type | Doc |')
        lines.append('|----------|------|-----|')

        for propname in sorted(tagprops.keys()):
            propinfo = tagprops[propname]

            typedef = propinfo.get('type', ())
            typenames = _resolveTypeNames(typedef)
            typecell = ', '.join(f'`{_escpipe(n)}`' for n in typenames)
            propdoc = propinfo.get('doc') or propinfo.get('info', {}).get('doc', '')
            lines.append(f'| `{propname}` | {typecell} | {_escpipe(propdoc)} |')

        lines.append('')

    # Build a mapping of interface name to forms that implement it
    ifaceforms = {ifname: [] for ifname in interfaces}
    for formname in sorted(forms.keys()):
        formtype = types.get(formname)
        for ifname, _ifinfo in formtype.get('info', {}).get('interfaces', ()):
            if ifname in ifaceforms:
                ifaceforms[ifname].append(formname)

    # Interfaces section
    lines.append('## Interfaces')
    lines.append('')

    for ifname in sorted(interfaces.keys()):

        ifinfo = interfaces[ifname]
        ifdoc = ifinfo.get('doc', '')

        lines.append(f'### `{ifname}`')
        lines.append('')
        if ifdoc:
            lines.append(ifdoc)
            lines.append('')

        ifprops = ifinfo.get('props', ())
        if ifprops:
            lines.append('| Property | Type | Doc |')
            lines.append('|----------|------|-----|')

            for propdef in sorted(ifprops, key=lambda x: x[0]):
                propname = propdef[0]
                typedef = propdef[1]
                propinfo = propdef[2] if len(propdef) > 2 else {}

                typenames = _resolveTypeNames(typedef)
                typecell = ', '.join(f'`{_escpipe(n)}`' for n in typenames)
                propdoc = _getPropDoc(propinfo, types)
                lines.append(f'| `:{propname}` | {typecell} | {_escpipe(propdoc)} |')

            lines.append('')

        implforms = ifaceforms.get(ifname, [])
        if implforms:
            lines.append('| Form |')
            lines.append('|------|')

            for formname in implforms:
                lines.append(f'| `{formname}` |')

            lines.append('')

    return '\n'.join(lines)

async def main(argv, outp=s_output.stdout):

    desc = 'Generate a markdown file documenting the Synapse data model.'
    pars = s_cmd.Parser(prog='synapse.tools.cortex.docmodel', outp=outp, description=desc)

    pars.add_argument('--cortex', '-c', default=None,
                      help='Telepath URL of an existing Cortex to connect to. If not specified, a temporary Cortex is used.')

    pars.add_argument('--save', '-s', default=None,
                      help='Output file path. If not specified, prints to stdout.')

    pars.add_argument('--form', '-f', default=None,
                      help='Output detailed documentation for a specific form.')

    pars.add_argument('--interface', '-i', default=None,
                      help='Output detailed documentation for a specific interface.')

    opts = pars.parse_args(argv)

    genfunc = genModelMarkdown
    genfuncargs = ()

    if opts.form is not None:
        genfunc = genFormMarkdown
        genfuncargs = (opts.form,)

    elif opts.interface is not None:
        genfunc = genIfaceMarkdown
        genfuncargs = (opts.interface,)

    if opts.cortex is not None:
        async with s_telepath.withTeleEnv():
            async with await s_telepath.openurl(opts.cortex) as core:
                text = await genfunc(core, *genfuncargs)

    else:
        async with s_cortex.getTempCortex() as core:
            text = await genfunc(core, *genfuncargs)

    if opts.save is not None:
        with open(s_common.genpath(opts.save), 'w') as fd:
            fd.write(text)
        outp.printf(f'Model documentation written to {opts.save}')

    else:
        outp.printf(text)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
