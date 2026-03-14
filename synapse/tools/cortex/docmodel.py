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

async def genModelMarkdown(core):
    '''Generate a markdown string documenting the data model.'''

    modeldict = await core.getModelDict()

    types = modeldict.get('types', {})
    forms = modeldict.get('forms', {})
    edges = modeldict.get('edges', [])
    interfaces = modeldict.get('interfaces', {})

    lines = []
    lines.append('# Synapse Data Model')
    lines.append('')
    lines.append('## Table of Contents')
    lines.append('')
    lines.append('- [Forms](#forms)')
    lines.append('- [Edges](#edges)')
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
            src = src or '\\*'
            dst = dst or '\\*'
            lines.append(f'| `{_escpipe(src)}` | `{_escpipe(verb)}` | `{_escpipe(dst)}` | {_escpipe(doc)} |')

        lines.append('')

    # Build a mapping of interface name to forms that implement it
    ifaceforms = {ifname: [] for ifname in interfaces}
    for formname in sorted(forms.keys()):
        formtype = types.get(formname)
        if formtype is None:
            continue
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

    opts = pars.parse_args(argv)

    if opts.cortex is not None:
        async with s_telepath.withTeleEnv():
            async with await s_telepath.openurl(opts.cortex) as core:
                text = await genModelMarkdown(core)

    else:
        async with s_cortex.getTempCortex() as core:
            text = await genModelMarkdown(core)

    if opts.save is not None:
        with open(s_common.genpath(opts.save), 'w') as fd:
            fd.write(text)
        outp.printf(f'Model documentation written to {opts.save}')

    else:
        outp.printf(text)

    return 0

if __name__ == '__main__':  # pragma: no cover
    s_cmd.exitmain(main)
