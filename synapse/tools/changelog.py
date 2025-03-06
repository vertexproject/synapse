import os
import re
import sys
import copy
import gzip
import pprint
import asyncio
import argparse
import datetime
import tempfile
import textwrap
import traceback
import subprocess
import collections

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.lib.output as s_output
import synapse.lib.autodoc as s_autodoc
import synapse.lib.schemas as s_schemas
import synapse.lib.version as s_version

defstruct = (
    ('type', None),
    ('desc', ''),
    ('prs', ()),
)

SKIP_FILES = (
    '.gitkeep',
    'modelrefs',
)

version_regex = r'^v[0-9]\.[0-9]+\.[0-9]+((a|b|rc)[0-9]*)?$'

def _getCurrentCommit(outp: s_output.OutPut) -> str | None:
    try:
        ret = subprocess.run(['git', 'rev-parse', 'HEAD'],
                             capture_output=True,
                             timeout=15,
                             check=False,
                             text=True,
                             )
    except Exception as e:
        outp.printf(f'Error grabbing commit: {e}')
        return
    else:
        commit = ret.stdout.strip()
    assert commit
    return commit

async def _getCurrentModl(outp: s_output.OutPut) -> dict:
    with tempfile.TemporaryDirectory() as dirn:
        conf = {'health:sysctl:checks': False}
        async with await s_cortex.Cortex.anit(conf=conf, dirn=dirn) as core:
            modl = await core.getModelDict()
            # Reserialize modl so its consistent with the model on disk
    modl = s_common.yamlloads(s_common.yamldump(modl))
    return modl


class ModelDiffer:
    def __init__(self, current_model: dict, reference_model: dict):
        self.cur_model = current_model
        self.ref_model = reference_model
        self.changes = {}

        self.cur_iface_to_allifaces = collections.defaultdict(list)
        for iface, info in self.cur_model.get('interfaces').items():
            self.cur_iface_to_allifaces[iface] = [iface]
            q = collections.deque(info.get('interfaces', ()))
            while q:
                _iface = q.popleft()
                if _iface in self.cur_iface_to_allifaces[iface]:
                    continue
                self.cur_iface_to_allifaces[iface].append(_iface)
                q.extend(self.cur_model.get('interfaces').get(_iface).get('interfaces', ()))

        self.cur_type2iface = collections.defaultdict(list)

        for _type, tnfo in  self.cur_model.get('types').items():
            for iface in tnfo.get('info').get('interfaces', ()):
                ifaces = self.cur_iface_to_allifaces[iface]
                for _iface in ifaces:
                    if _iface not in self.cur_type2iface[_type]:
                        self.cur_type2iface[_type].append(_iface)

    def _compareEdges(self, curv, oldv, outp: s_output.OutPut) -> dict:
        changes = {}
        if curv == oldv:
            return changes

        # Flatten the edges into structures that can be handled
        _curv = {tuple(item[0]): item[1] for item in curv}
        _oldv = {tuple(item[0]): item[1] for item in oldv}

        curedges = set(_curv.keys())
        oldedges = set(_oldv.keys())

        new_edges = curedges - oldedges
        del_edges = oldedges - curedges  # This should generally not happen...
        assert len(del_edges) == 0, 'A edge was removed from the data model!'

        if new_edges:
            changes['new_edges'] = {k: _curv.get(k) for k in new_edges}

        updated_edges = collections.defaultdict(dict)
        deprecated_edges = {}

        for edge, curinfo in _curv.items():
            if edge in new_edges:
                continue
            oldinfo = _oldv.get(edge)
            if curinfo == oldinfo:
                continue

            if curinfo.get('deprecated') and not oldinfo.get('deprecated'):
                deprecated_edges[edge] = curinfo
                continue

            if oldinfo.get('doc') != curinfo.get('doc'):
                updated_edges[edge] = curinfo
                continue

            # TODO - Support additional changes to the edges?
            assert False, f'A change was found for the edge: {edge}'

        if updated_edges:
            changes['updated_edges'] = dict(updated_edges)

        if deprecated_edges:
            changes['deprecated_edges'] = deprecated_edges

        return changes

    def _compareForms(self, curv, oldv, outp: s_output.OutPut) -> dict:
        changes = {}
        if curv == oldv:
            return changes

        curforms = set(curv.keys())
        oldforms = set(oldv.keys())

        new_forms = curforms - oldforms
        del_forms = oldforms - curforms  # This should generally not happen...
        assert len(del_forms) == 0, 'A form was removed from the data model!'

        if new_forms:
            changes['new_forms'] = {k: curv.get(k) for k in new_forms}

        updated_forms = collections.defaultdict(dict)
        for form, curinfo in curv.items():
            if form in new_forms:
                continue
            oldinfo = oldv.get(form)
            if curinfo == oldinfo:
                continue

            # Check for different properties
            nprops = curinfo.get('props')
            oprops = oldinfo.get('props')

            new_props = set(nprops.keys()) - set(oprops.keys())
            del_props = set(oprops.keys()) - set(nprops.keys())  # This should generally not happen...
            assert len(del_props) == 0, 'A form was removed from the data model!'

            if new_props:
                updated_forms[form]['new_properties'] = {prop: nprops.get(prop) for prop in new_props}
                np_noiface = {}
                ifaces = self.cur_type2iface[form]

                for prop in new_props:
                    # TODO record raw new_props to make bulk edits possible
                    is_ifaceprop = False
                    for iface in ifaces:
                        # Is the prop in the new_interfaces or updated_interfaces lists?
                        new_iface = self.changes.get('interfaces').get('new_interfaces', {}).get(iface)
                        if new_iface and prop in new_iface.get('props', {}):
                            is_ifaceprop = True
                            break

                        upt_iface = self.changes.get('interfaces').get('updated_interfaces', {}).get(iface)
                        if upt_iface and prop in upt_iface.get('new_properties', {}):
                            is_ifaceprop = True
                            break

                    if is_ifaceprop:
                        continue

                    np_noiface[prop] = nprops.get(prop)

                if np_noiface:
                    updated_forms[form]['new_properties_no_interfaces'] = np_noiface

            updated_props = {}
            updated_props_noiface = {}

            deprecated_props = {}
            deprecated_props_noiface = {}

            for prop, cpinfo in nprops.items():
                if prop in new_props:
                    continue
                opinfo = oprops.get(prop)
                if cpinfo == opinfo:
                    continue

                # Deprecation has a higher priority than updated type information
                if cpinfo.get('deprecated') and not opinfo.get('deprecated'):
                    # A deprecated property could be present on an updated iface
                    deprecated_props[prop] = cpinfo

                    is_ifaceprop = False
                    for iface in self.cur_type2iface[form]:
                        upt_iface = self.changes.get('interfaces').get('updated_interfaces', {}).get(iface)
                        if upt_iface and prop in upt_iface.get('deprecated_properties', {}):
                            is_ifaceprop = True
                            break
                    if is_ifaceprop:
                        continue

                    deprecated_props_noiface[prop] = cpinfo
                    continue

                okeys = set(opinfo.keys())
                nkeys = set(cpinfo.keys())

                if nkeys - okeys:
                    # We've added a key to the prop def.
                    updated_props[prop] = {'type': 'addkey', 'keys': list(nkeys - okeys)}

                if okeys - nkeys:
                    # We've removed a key from the prop def.
                    updated_props[prop] = {'type': 'delkey', 'keys': list(okeys - nkeys)}

                # Check if type change happened, we'll want to document that.
                ctyp = cpinfo.get('type')
                otyp = opinfo.get('type')
                if ctyp == otyp:
                    continue

                updated_props[prop] = {'type': 'type_change', 'new_type': ctyp, 'old_type': otyp}
                is_ifaceprop = False
                for iface in self.cur_type2iface[form]:
                    upt_iface = self.changes.get('interfaces').get('updated_interfaces', {}).get(iface)
                    if upt_iface and prop in upt_iface.get('updated_properties', {}):
                        is_ifaceprop = True
                        break
                if is_ifaceprop:
                    continue
                updated_props_noiface[prop] = {'type': 'type_change', 'new_type': ctyp, 'old_type': otyp}

            if updated_props:
                updated_forms[form]['updated_properties'] = updated_props

            if updated_props_noiface:
                updated_forms[form]['updated_properties_no_interfaces'] = updated_props_noiface

            if deprecated_props:
                updated_forms[form]['deprecated_properties'] = deprecated_props

            if deprecated_props_noiface:
                updated_forms[form]['deprecated_properties_no_interfaces'] = deprecated_props_noiface

        if updated_forms:
            changes['updated_forms'] = dict(updated_forms)

        return changes

    def _compareIfaces(self, curv, oldv, outp: s_output.OutPut) -> dict:
        changes = {}
        if curv == oldv:
            return changes

        curfaces = set(curv.keys())
        oldfaces = set(oldv.keys())

        new_faces = curfaces - oldfaces
        del_faces = oldfaces - curfaces  # This should generally not happen...
        assert len(del_faces) == 0, 'An interface was removed from the data model!'

        if new_faces:
            nv = {}
            for iface in new_faces:
                k = copy.deepcopy(curv.get(iface))
                # Rewrite props into a dictionary for easier lookup later
                k['props'] = {item[0]: {'type': item[1], 'props': item[2]} for item in k['props']}
                nv[iface] = k

            changes['new_interfaces'] = nv

        updated_interfaces = collections.defaultdict(dict)

        for iface, curinfo in curv.items():
            if iface in new_faces:
                continue
            oldinfo = oldv.get(iface)

            # Did the interface inheritance change?
            if curinfo.get('interfaces') != oldinfo.get('interfaces'):
                updated_interfaces[iface] = {'updated_interfaces': {'curv': curinfo.get('interfaces'),
                                                                    'oldv': oldinfo.get('interfaces')}}
            # Did the interface have a property definition change?
            nprops = curinfo.get('props')
            oprops = oldinfo.get('props')

            # Convert props to dictionary
            nprops = {item[0]: {'type': item[1], 'props': item[2]} for item in nprops}
            oprops = {item[0]: {'type': item[1], 'props': item[2]} for item in oprops}

            new_props = set(nprops.keys()) - set(oprops.keys())
            del_props = set(oprops.keys()) - set(nprops.keys())  # This should generally not happen...
            assert len(del_props) == 0, f'A prop was removed from the iface {iface}'

            if new_props:
                updated_interfaces[iface]['new_properties'] = {prop: nprops.get(prop) for prop in new_props}

            updated_props = {}
            deprecated_props = {}
            for prop, cpinfo in nprops.items():
                if prop in new_props:
                    continue
                opinfo = oprops.get(prop)
                if cpinfo == opinfo:
                    continue

                if cpinfo.get('props').get('deprecated') and not opinfo.get('props').get('deprecated'):
                    deprecated_props[prop] = cpinfo
                    continue

                okeys = set(opinfo.keys())
                nkeys = set(cpinfo.keys())

                if nkeys - okeys:
                    # We've added a key to the prop def.
                    updated_props[prop] = {'type': 'addkey', 'keys': list(nkeys - okeys)}

                if okeys - nkeys:
                    # We've removed a key from the prop def.
                    updated_props[prop] = {'type': 'delkey', 'keys': list(okeys - nkeys)}

                # Check if type change happened, we'll want to document that.
                ctyp = cpinfo.get('type')
                otyp = opinfo.get('type')
                if ctyp == otyp:
                    continue

                updated_props[prop] = {'type': 'type_change', 'new_type': ctyp, 'old_type': otyp}
            if updated_props:
                updated_interfaces[iface]['updated_properties'] = updated_props

            if deprecated_props:
                updated_interfaces[iface]['deprecated_properties'] = deprecated_props

        changes['updated_interfaces'] = dict(updated_interfaces)

        return changes

    def _compareTagprops(self, curv, oldv, outp: s_output.OutPut) -> dict:
        changes = {}
        if curv == oldv:
            return changes
        raise NotImplementedError('_compareTagprops')

    def _compareTypes(self, curv, oldv, outp: s_output.OutPut) -> dict:
        changes = {}
        if curv == oldv:
            return changes

        curtypes = set(curv.keys())
        oldtypes = set(oldv.keys())

        new_types = curtypes - oldtypes
        del_types = oldtypes - curtypes  # This should generally not happen...
        assert len(del_types) == 0, 'A type was removed from the data model!'

        if new_types:
            changes['new_types'] = {k: curv.get(k) for k in new_types}

        updated_types = collections.defaultdict(dict)
        deprecated_types = collections.defaultdict(dict)

        for _type, curinfo in curv.items():
            if _type in new_types:
                continue
            oldinfo = oldv.get(_type)
            if curinfo == oldinfo:
                continue

            cnfo = curinfo.get('info')
            onfo = oldinfo.get('info')

            if cnfo.get('deprecated') and not onfo.get('deprecated'):
                deprecated_types[_type] = curinfo
                continue

            if cnfo.get('interfaces') != onfo.get('interfaces'):
                updated_types[_type]['updated_interfaces'] = {'curv': cnfo.get('interfaces'),
                                                              'oldv': onfo.get('interfaces'),
                                                              }

            if curinfo.get('opts') != oldinfo.get('opts'):
                updated_types[_type]['updated_opts'] = {'curv': curinfo.get('opts'),
                                                        'oldv': oldinfo.get('opts'),
                                                        }

        if updated_types:
            changes['updated_types'] = dict(updated_types)

        if deprecated_types:
            changes['deprecated_types'] = dict(deprecated_types)

        return changes

    def _compareUnivs(self, curv, oldv, outp: s_output.OutPut) -> dict:
        changes = {}
        if curv == oldv:
            return changes
        raise NotImplementedError('_compareUnivs')

    def diffModl(self, outp: s_output.OutPut) -> dict | None:
        if self.changes:
            return self.changes

        # These are order sensitive due to interface knowledge being required in order
        # to deconflict downstream changes on forms.
        known_keys = {
            'interfaces': self._compareIfaces,
            'types': self._compareTypes,
            'forms': self._compareForms,
            'tagprops': self._compareTagprops,
            'edges': self._compareEdges,
            'univs': self._compareUnivs,
        }

        all_keys = set(self.cur_model.keys()).union(self.ref_model.keys())

        for key, func in known_keys.items():
            self.changes[key] = func(self.cur_model.get(key),
                                     self.ref_model.get(key),
                                     outp)
            all_keys.remove(key)

        if all_keys:
            outp.printf(f'ERROR: Unknown model key found: {all_keys}')
            return

        return self.changes

def _getModelFile(fp: str) -> dict | None:
    with s_common.genfile(fp) as fd:
        bytz = fd.read()
        large_bytz = gzip.decompress(bytz)
        ref_modl = s_common.yamlloads(large_bytz)
    return ref_modl

async def gen(opts: argparse.Namespace,
              outp: s_output.OutPut):

    name = opts.name
    if name is None:
        name = f'{s_common.guid()}.yaml'
    fp = s_common.genpath(opts.cdir, name)

    data = dict(defstruct)
    data['type'] = opts.type
    data['desc'] = opts.desc

    if opts.pr:
        data['prs'] = [opts.pr]

    if opts.verbose:
        outp.printf('Validating data against schema')

    s_schemas._reqChangelogSchema(data)

    if opts.verbose:
        outp.printf('Saving the following information:')
        outp.printf(s_common.yamldump(data).decode())

    s_common.yamlsave(data, fp)

    outp.printf(f'Saved changelog entry to {fp=}')

    if opts.add:
        if opts.verbose:
            outp.printf('Adding file to git staging')
        argv = ['git', 'add', fp]
        ret = subprocess.run(argv, capture_output=True)
        if opts.verbose:
            outp.printf(f'stddout={ret.stdout}')
            outp.printf(f'stderr={ret.stderr}')
        ret.check_returncode()

    return 0

def _gen_model_rst(version, model_ref, changes, current_model, outp: s_output.OutPut, width=80) -> s_autodoc.RstHelp:
    rst = s_autodoc.RstHelp()
    rst.addHead(f'{version} Model Updates', link=f'.. _{model_ref}:')
    rst.addLines(f'The following model updates were made during the ``{version}`` Synapse release.')

    if new_interfaces := changes.get('interfaces').get('new_interfaces'):
        rst.addHead('New Interfaces', lvl=1)
        for interface, info in new_interfaces.items():
            rst.addLines(f'``{interface}``')
            rst.addLines(*textwrap.wrap(info.get('doc'), initial_indent='  ', subsequent_indent='  ',
                                        width=width))
            rst.addLines('\n')

    # Deconflict new_forms vs new_types -> do not add types which appear in new_forms.
    new_forms = changes.get('forms').get('new_forms', {})
    new_types = changes.get('types').get('new_types', {})
    types_to_document = {k: v for k, v in new_types.items() if k not in new_forms}

    if types_to_document:
        rst.addHead('New Types', lvl=1)
        for _type, info in types_to_document.items():
            rst.addLines(f'``{_type}``')
            rst.addLines(*textwrap.wrap(info.get('info').get('doc'), initial_indent='  ', subsequent_indent='  ',
                                        width=width))
            rst.addLines('\n')

    if new_forms:
        rst.addHead('New Forms', lvl=1)
        for form, info in new_forms.items():
            rst.addLines(f'``{form}``')
            # Pull the form doc from the current model directly. In the event of an existing
            # type being turned into a form + then reindexed, it would not show up in the
            # type diff, so we can't rely on the doc being present there.
            doc = current_model.get('types').get(form).get('info').get('doc')
            rst.addLines(*textwrap.wrap(doc, initial_indent='  ', subsequent_indent='  ',
                                        width=width))
            rst.addLines('\n')

    # Check for new properties
    updated_forms = changes.get('forms').get('updated_forms', {})
    new_props = []
    for form, info in updated_forms.items():
        if 'new_properties' in info:
            new_props.append((form, info))
    if new_props:
        rst.addHead('New Properties', lvl=1)
        new_props.sort(key=lambda x: x[0])
        for form, info in new_props:
            rst.addLines(f'``{form}``')
            new_form_props = list(info.get('new_properties').items())
            if len(new_form_props) > 1:
                rst.addLines('  The form had the following properties added to it:', '\n')
                new_form_props.sort(key=lambda x: x[0])
                for name, info in new_form_props:
                    lines = [
                        f'  ``{name}``',
                        *textwrap.wrap(info.get('doc'), initial_indent='    ', subsequent_indent='    ',
                                       width=width),
                        '\n'
                    ]
                    rst.addLines(*lines)

            else:
                name, info = new_form_props[0]
                lines = [
                    '  The form had the following property added to it:',
                    '\n'
                    f'  ``{name}``',
                    *textwrap.wrap(info.get('doc'), initial_indent='    ', subsequent_indent='    ',
                                   width=width),
                    '\n'
                ]
                rst.addLines(*lines)

    # Updated interfaces
    if updated_interfaces := changes.get('interfaces').get('updated_interfaces', {}):
        upd_ifaces = list(updated_interfaces.items())
        upd_ifaces.sort(key=lambda x: x[0])
        rst.addHead('Updated Interfaces', lvl=1)
        for iface, info in upd_ifaces:
            lines = [f'``{iface}``',
                     ]
            for key, valu in sorted(info.items(), key=lambda x: x[0]):
                if key == 'deprecated_properties':
                    for prop, pnfo in sorted(valu.items(), key=lambda x: x[0]):
                        mesg = f'The interface property ``{prop}`` has been deprecated.'
                        lines.extend(textwrap.wrap(mesg, initial_indent='  ', subsequent_indent='  ',
                                                   width=width))
                        lines.append('\n')
                elif key == 'new_properties':
                    for prop, pnfo in sorted(valu.items(), key=lambda x: x[0]):
                        mesg = f'The property ``{prop}`` has been added to the interface.'
                        lines.extend(textwrap.wrap(mesg, initial_indent='  ', subsequent_indent='  ',
                                                   width=width))
                        lines.append('\n')
                elif key == 'updated_properties':
                    for prop, pnfo in sorted(valu.items(), key=lambda x: x[0]):
                        ptyp = pnfo.get('type')
                        if ptyp == 'type_change':
                            mesg = f'The property ``{prop}`` has been modified from {pnfo.get("old_type")}' \
                                   f' to {pnfo.get("new_type")}.'
                        elif ptyp == 'delkey':
                            mesg = f'The property ``{prop}`` had the ``{pnfo.get("keys")}`` keys removed from its definition.'
                        else:
                            raise s_exc.NoSuchImpl(mesg=f'pnfo.type={ptyp} not supported.')
                        lines.extend(textwrap.wrap(mesg, initial_indent='  ', subsequent_indent='  ',
                                                   width=width))
                        lines.append('\n')
                else:  # pragma: no cover
                    outp.printf(f'Unknown key: {key=} {valu=}')
                    raise s_exc.SynErr(mesg=f'Unknown updated interface key: {key=} {valu=}')
            rst.addLines(*lines)

    # Updated types
    if updated_types := changes.get('types').get('updated_types', {}):
        upd_types = list(updated_types.items())
        upd_types.sort(key=lambda x: x[0])
        rst.addHead('Updated Types', lvl=1)
        for _type, info in upd_types:
            lines = [f'``{_type}``',
                     ]
            for key, valu in sorted(info.items(), key=lambda x: x[0]):
                if key == 'updated_interfaces':
                    mesg = f'The type interface has been modified from {valu.get("oldv")}' \
                           f' to {valu.get("curv")}.'
                    lines.extend(textwrap.wrap(mesg, initial_indent='  ', subsequent_indent='  ',
                                               width=width))
                    lines.append('\n')
                elif key == 'updated_opts':
                    mesg = f'The type has been modified from {valu.get("oldv")}' \
                           f' to {valu.get("curv")}.'
                    lines.extend(textwrap.wrap(mesg, initial_indent='  ', subsequent_indent='  ',
                                               width=width))
                    lines.append('\n')
                else:  # pragma: no cover
                    outp.printf(f'Unknown key: {key=} {valu=}')
                    raise s_exc.SynErr(mesg=f'Unknown updated type key: {key=} {valu=}')
            rst.addLines(*lines)

    # Updated Forms
    # We don't really have a "updated forms" to display since the delta for forms data is really property
    # deltas covered elsewhere.

    # Updated Edges
    # TODO Add support for updated edges

    # Updated Properties
    upd_props = []
    for form, info in updated_forms.items():
        if 'updated_properties' in info:
            upd_props.append((form, info))
    if upd_props:
        rst.addHead('Updated Properties', lvl=1)
        upd_props.sort(key=lambda x: x[0])
        for form, info in upd_props:
            rst.addLines(f'``{form}``')
            upd_form_props = list(info.get('updated_properties').items())
            if len(upd_form_props) > 1:
                rst.addLines('  The form had the following properties updated:', '\n')
                upd_form_props.sort(key=lambda x: x[0])
                for prop, pnfo in upd_form_props:
                    ptyp = pnfo.get('type')
                    if ptyp == 'type_change':
                        mesg = f'The property ``{prop}`` has been modified from {pnfo.get("old_type")}' \
                               f' to {pnfo.get("new_type")}.'
                    elif ptyp == 'delkey':
                        mesg = f'The property ``{prop}`` had the ``{pnfo.get("keys")}`` keys removed from its definition.'
                    elif ptyp == 'addkey':
                        mesg = f'The property ``{prop}`` had the ``{pnfo.get("keys")}`` keys added to its definition.'
                    else:
                        raise s_exc.NoSuchImpl(mesg=f'pnfo.type={ptyp} not supported.')
                    lines = [
                        *textwrap.wrap(mesg, initial_indent='    ', subsequent_indent='    ',
                                       width=width),
                        '\n'
                    ]
                    rst.addLines(*lines)

            else:
                prop, pnfo = upd_form_props[0]
                ptyp = pnfo.get('type')
                if ptyp == 'type_change':
                    mesg = f'The property ``{prop}`` has been modified from {pnfo.get("old_type")}' \
                           f' to {pnfo.get("new_type")}.'
                elif ptyp == 'delkey':
                    mesg = f'The property ``{prop}`` had the ``{pnfo.get("keys")}`` keys removed from its definition.'
                elif ptyp == 'addkey':
                    mesg = f'The property ``{prop}`` had the ``{pnfo.get("keys")}`` keys added to its definition.'
                else:
                    raise s_exc.NoSuchImpl(mesg=f'pnfo.type={ptyp} not supported.')

                lines = [
                    '  The form had the following property updated:',
                    '\n',
                    *textwrap.wrap(mesg, initial_indent='    ', subsequent_indent='    ',
                                   width=width),
                    '\n'
                ]
                rst.addLines(*lines)

    # Light Edges
    if new_edges := changes.get('edges').get('new_edges'):
        new_edges = list(new_edges.items())
        new_edges.sort(key=lambda x: x[0][1])
        rst.addHead('Light Edges', lvl=1)
        for (n1, name, n2), info in new_edges:
            if n1 is not None and n2 is not None:
                mesg = f'''When used with a ``{n1}`` and an ``{n2}`` node, the edge indicates {info.get('doc')}'''
            elif n1 is None and n2 is not None:
                mesg = f'''When used with a ``{n2}`` target node, the edge indicates {info.get('doc')}'''
            elif n1 is not None and n2 is None:
                mesg = f'''When used with a ``{n1}`` node, the edge indicates {info.get('doc')}'''
            else:
                mesg = info.get('doc')

            rst.addLines(
                f'``{name}``',
                *textwrap.wrap(mesg, initial_indent='    ', subsequent_indent='    ', width=width),
                '\n',
            )

    # Deprecated Interfaces
    # TODO Support deprecated interfaces!

    # Deprecated Types
    # Deconflict deprecated forms vs deprecated_types, so we do not
    # not call out types which are also forms in the current model.
    deprecated_types = changes.get('types').get('deprecated_types', {})
    deprecated_forms = {k: v for k, v in deprecated_types.items() if k in current_model.get('forms')}
    deprecated_types = {k: v for k, v in deprecated_types.items() if k not in deprecated_forms}
    if deprecated_types:
        rst.addHead('Deprecated Types', lvl=1)
        rst.addLines('The following types have been marked as deprecated:', '\n')

        for _type, info in deprecated_types.items():
            rst.addLines(
                f'* ``{_type}``',
            )
        rst.addLines('\n')

    # Deprecated Forms
    if deprecated_forms:
        rst.addHead('Deprecated Types', lvl=1)
        rst.addLines('The following forms have been marked as deprecated:', '\n')

        for _type, info in deprecated_forms.items():
            rst.addLines(
                f'* ``{_type}``',
            )
        rst.addLines('\n')

    # Deprecated Properties
    dep_props = []
    for form, info in updated_forms.items():
        if 'deprecated_properties' in info:
            dep_props.append((form, info))
    if dep_props:
        rst.addHead('Deprecated Properties', lvl=1)
        dep_props.sort(key=lambda x: x[0])
        for form, info in dep_props:
            rst.addLines(f'``{form}``')
            dep_form_props = list(info.get('deprecated_properties').items())
            if len(dep_form_props) > 1:
                rst.addLines('  The form had the following properties deprecated:', '\n')
                dep_form_props.sort(key=lambda x: x[0])
                for name, info in dep_form_props:
                    lines = [
                        f'  ``{name}``',
                        *textwrap.wrap(info.get('doc'), initial_indent='    ', subsequent_indent='    ',
                                       width=width),
                        '\n'
                    ]
                    rst.addLines(*lines)

            else:
                name, info = dep_form_props[0]
                lines = [
                    '  The form had the following property deprecated:',
                    '\n'
                    f'  ``{name}``',
                    *textwrap.wrap(info.get('doc'), initial_indent='    ', subsequent_indent='    ',
                                   width=width),
                    '\n'
                ]
                rst.addLines(*lines)

    if dep_edges := changes.get('edges').get('deprecated_edges'):

        rst.addHead('Deprecated Edges', lvl=1)
        for (n1, name, n2), info in dep_edges.items():
            if n1 is not None and n2 is not None:
                mesg = f'''The edge has been deprecated when used with a ``{n1}`` and an ``{n2}`` node. {info.get('doc')}'''
            elif n1 is None and n2 is not None:
                mesg = f'''The edge has been deprecated when used with a ``{n2}`` target node. {info.get('doc')}'''
            elif n1 is not None and n2 is None:
                mesg = f'''The edge has been deprecated when used with a  ``{n1}`` node. {info.get('doc')}'''
            else:
                mesg = f'''The edge has been deprecated. {info.get('doc')}'''

            rst.addLines(
                f'``{name}``',
                *textwrap.wrap(mesg, initial_indent='    ', subsequent_indent='    ', width=width),
                '\n',
            )

    return rst


async def format(opts: argparse.Namespace,
           outp: s_output.OutPut):

    if not regex.match(version_regex, opts.version):
        outp.printf(f'Failed to match {opts.version} vs {version_regex}')
        return 1

    entries = collections.defaultdict(list)

    files_processed = []  # Eventually for removing files from git.

    for fn in os.listdir(opts.cdir):
        if fn in SKIP_FILES:
            continue
        fp = s_common.genpath(opts.cdir, fn)
        if opts.verbose:
            outp.printf(f'Reading: {fp=}')
        try:
            data = s_common.yamlload(fp)
        except Exception as e:
            outp.printf(f'Error parsing yaml from {fp=}: {e}')
            continue

        if opts.verbose:
            outp.printf('Got the following data:')
            outp.printf(pprint.pformat(data))

        files_processed.append(fp)

        s_schemas._reqChangelogSchema(data)

        data.setdefault('prs', [])
        prs = data.get('prs')

        if opts.prs_from_git:

            argv = ['git', 'log', '--pretty=oneline', fp]
            ret = subprocess.run(argv, capture_output=True)
            if opts.verbose:
                outp.printf(f'stddout={ret.stdout}')
                outp.printf(f'stderr={ret.stderr}')
            ret.check_returncode()

            for line in ret.stdout.splitlines():
                line = line.decode()
                line = line.strip()
                if not line:
                    continue
                match = re.search('\\(#(?P<pr>\\d{1,})\\)', line)
                if match:
                    for pr in match.groups():
                        pr = int(pr)
                        if pr not in prs:
                            prs.append(pr)
                            if opts.verbose:
                                outp.printf(f'Added PR #{pr} to the pr list from [{line=}]')

        if opts.enforce_prs and not prs:
            outp.printf(f'Entry is missing PR numbers: {fp=}')
            return 1

        if opts.verbose:
            outp.printf(f'Got data from {fp=}')

        prs.sort() # sort the PRs inplace
        entries[data.get('type')].append(data)

    if not entries:
        outp.printf(f'No files passed validation from {opts.dir}')
        return 1

    date = opts.date
    if date is None:
        date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    header = f'{opts.version} - {date}'
    text = f'{header}\n{"=" * len(header)}\n'

    modeldiff = False
    clean_vers_ref = opts.version.replace(".", "_")
    model_rst_ref = f'userguide_model_{clean_vers_ref}'

    if opts.model_ref:
        # TODO find previous model file automatically?
        if opts.verbose:
            outp.printf(f'Getting reference model from {opts.model_ref}')

        ref_modl = _getModelFile(opts.model_ref)

        if opts.model_current:
            to_modl = _getModelFile(opts.model_current)
            cur_modl = to_modl.get('model')
            if opts.verbose:
                outp.printf(f'Comparing {to_modl.get("version")} - {to_modl.get("commit")} vs {ref_modl.get("version")} - {ref_modl.get("commit")}')
        else:
            cur_modl = await _getCurrentModl(outp)
            if opts.verbose:
                outp.printf(f'Comparing current model vs {ref_modl.get("version")} - {ref_modl.get("commit")}')

        differ = ModelDiffer(cur_modl, ref_modl.get('model'))
        changes = differ.diffModl(outp)
        has_changes = sum([len(v) for v in changes.values()])
        if has_changes:
            entries['model'].append({'prs': [], 'type': 'skip'})
            modeldiff = True
            rst = _gen_model_rst(opts.version, model_rst_ref, changes, cur_modl, outp, width=opts.width)
            model_text = rst.getRstText()
            if opts.verbose:
                outp.printf(model_text)
            if opts.model_doc_dir:
                fp = s_common.genpath(opts.model_doc_dir, f'update_{clean_vers_ref}.rst')
                with s_common.genfile(fp) as fd:
                    fd.truncate(0)
                    fd.write(model_text.encode())
                outp.printf(f'Wrote model changes to {fp}')
                if opts.verbose:
                    outp.printf(f'Adding file to git.')
                argv = ['git', 'add', fp]
                ret = subprocess.run(argv, capture_output=True)
                if opts.verbose:
                    outp.printf(f'stddout={ret.stdout}')
                    outp.printf(f'stderr={ret.stderr}')
                ret.check_returncode()
        else:
            outp.printf(f'No model changes detected.')

    for key, header in s_schemas._changelogTypes.items():
        dataz = entries.get(key)
        if dataz:
            text = text + f'\n{header}\n{"-" * len(header)}'
            dataz.sort(key=lambda x: x.get('prs'))
            for data in dataz:
                desc = data.get('desc')  # type: str
                if desc is None and data.get('type') == 'skip':
                    continue
                desc_lines = desc.splitlines()
                for i, chunk in enumerate(desc_lines):
                    if i == 0:
                        for line in textwrap.wrap(chunk, initial_indent='- ', subsequent_indent='  ', width=opts.width):
                            text = f'{text}\n{line}'
                    else:
                        text = text + '\n'
                        for line in textwrap.wrap(chunk, initial_indent='  ', subsequent_indent='  ', width=opts.width):
                            text = f'{text}\n{line}'

                if not opts.hide_prs:
                    for pr in data.get('prs'):
                        text = f'{text}\n  (`#{pr} <https://github.com/vertexproject/synapse/pull/{pr}>`_)'
            if key == 'migration':
                text = text + '\n- See :ref:`datamigration` for more information about automatic migrations.'
            elif key == 'model':
                if modeldiff:
                    text = text + f'\n- See :ref:`{model_rst_ref}` for more detailed model changes.'
            text = text + '\n'

    if opts.rm:
        if opts.verbose:
            outp.printf('Staging file removals in git')
        for fp in files_processed:
            argv = ['git', 'rm', fp]
            ret = subprocess.run(argv, capture_output=True)
            if opts.verbose:
                outp.printf(f'stddout={ret.stdout}')
                outp.printf(f'stderr={ret.stderr}')
            ret.check_returncode()

    outp.printf('CHANGELOG ENTRY:\n\n')
    outp.printf(text)

    return 0

async def model(opts: argparse.Namespace,
           outp: s_output.OutPut):

    if opts.save:
        modl = await _getCurrentModl(outp)

        dirn = s_common.gendir(opts.cdir, 'modelrefs')
        current_commit = _getCurrentCommit(outp)
        if not current_commit:
            return 1
        wrapped_modl = {
            'model': modl,
            'commit': current_commit,
            'version': s_version.version,
        }

        fp = s_common.genpath(dirn, f'model_{s_version.verstring}_{current_commit}.yaml.gz')
        with s_common.genfile(fp) as fd:
            fd.truncate(0)
            bytz = s_common.yamldump(wrapped_modl)
            small_bytz = gzip.compress(bytz)
            _ = fd.write(small_bytz)

        outp.printf(f'Saved model to {fp}')
        return 0

    if opts.compare:
        ref_modl = _getModelFile(opts.compare)
        if opts.to:
            to_modl = _getModelFile(opts.to)
            modl = to_modl.get('model')
            outp.printf(f'Comparing {to_modl.get("version")} - {to_modl.get("commit")} vs {ref_modl.get("version")} - {ref_modl.get("commit")}')
        else:
            modl = await _getCurrentModl(outp)
            outp.printf(f'Comparing current model vs {ref_modl.get("version")} - {ref_modl.get("commit")}')
        differ = ModelDiffer(modl, ref_modl.get('model'))
        changes = differ.diffModl(outp)
        for line in pprint.pformat(changes).splitlines(keepends=False):
            outp.printf(line)
        return 0

async def main(argv, outp=None):
    if outp is None:
        outp = s_output.OutPut()

    pars = makeargparser()

    opts = pars.parse_args(argv)
    if opts.git_dir_check:
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            outp.printf('Current working directory must be the root of the repository.')
            return 1

    if opts.verbose:
        outp.printf(f'{opts=}')

    try:
        return await opts.func(opts, outp)
    except Exception as e:
        outp.printf(f'Error running {opts.func}: {traceback.format_exc()}')
    return 1

def makeargparser():
    desc = '''Command line tool to manage changelog entries.
    This tool and any data formats associated with it may change at any time.
    '''
    pars = argparse.ArgumentParser('synapse.tools.changelog', description=desc)

    subpars = pars.add_subparsers(required=True,
                                  title='subcommands',
                                  dest='cmd', )
    gen_pars = subpars.add_parser('gen', help='Generate a new changelog entry.')
    gen_pars.set_defaults(func=gen)
    gen_pars.add_argument('-t', '--type', required=True, choices=list(s_schemas._changelogTypes.keys()),
                          help='The changelog type.')
    gen_pars.add_argument('desc', type=str,
                          help='The description to populate the initial changelog entry with.', )
    gen_pars.add_argument('-p', '--pr', type=int, default=False,
                          help='PR number associated with the changelog entry.')
    gen_pars.add_argument('-a', '--add', default=False, action='store_true',
                          help='Add the newly created file to the current git staging area.')
    # Hidden name override. Mainly for testing.
    gen_pars.add_argument('-n', '--name', default=None, type=str,
                          help=argparse.SUPPRESS)

    format_pars = subpars.add_parser('format', help='Format existing files into a RST block.')
    format_pars.set_defaults(func=format)
    mux_prs = format_pars.add_mutually_exclusive_group()
    mux_prs.add_argument('--hide-prs', default=False, action='store_true',
                         help='Hide PR entries.')
    mux_prs.add_argument('--enforce-prs', default=False, action='store_true',
                         help='Enforce PRs list to be populated with at least one number.', )
    format_pars.add_argument('--prs-from-git', default=False, action='store_true',
                             help='Attempt to populate any PR numbers from a given files commit history.')
    format_pars.add_argument('-w', '--width', help='Maximum column width to wrap descriptions at.',
                             default=79, type=int)
    format_pars.add_argument('--version', required=True, action='store', type=str,
                             help='Version number')
    format_pars.add_argument('-d', '--date', action='store', type=str,
                             help='Date to use with the changelog entry')
    format_pars.add_argument('-r', '--rm', default=False, action='store_true',
                             help='Stage the changelog files as deleted files in git.')
    format_pars.add_argument('-m', '--model-ref', default=None, action='store', type=str,
                             help='Baseline model to use when generating model deltas. This is normally the previous releases model file.')
    format_pars.add_argument('--model-current', default=None, action='store',
                             help='Optional model file to use as a reference as the current model.')
    format_pars.add_argument('--model-doc-dir', default=None, action='store',
                             help='Directory to write the model changes too.')

    model_pars = subpars.add_parser('model', help='Helper for working with the Cortex data model.')
    model_pars.set_defaults(func=model)
    mux_model = model_pars.add_mutually_exclusive_group(required=True)
    mux_model.add_argument('-s', '--save', action='store_true', default=False,
                           help='Save a copy of the current model to a file.')
    mux_model.add_argument('-c', '--compare', action='store', default=None,
                           help='Model to compare the current model against. Useful for debugging modl diff functionality.'
                           )
    model_pars.add_argument('-t', '--to', action='store', default=None,
                            help='The model file to compare against. Will not use current model if specified.')

    for p in (gen_pars, format_pars, model_pars):
        p.add_argument('-v', '--verbose', default=False, action='store_true',
                       help='Enable verbose output')
        p.add_argument('--cdir', default='./changes', action='store',
                       help='Directory of changelog files.')
        p.add_argument('--disable-git-dir-check', dest='git_dir_check', default=True, action='store_false',
                       help=argparse.SUPPRESS)

    return pars

if __name__ == '__main__':  # pragma: no cover
    sys.exit(asyncio.run(main(sys.argv[1:], s_output.stdout)))
