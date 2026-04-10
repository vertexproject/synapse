'''
One-time conversion script: reads all Python modeldefs from synapse/models/,
merges forms into types, inlines enum constants, and writes synapse/datamodel.yaml.
'''
import os
import sys
import collections

# Ensure synapse is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yaml

import synapse.lib.dyndeps as s_dyndeps

import synapse.models as s_models

# Import enum variables and lookup functions
import synapse.models.base as s_base
import synapse.models.crypto as s_crypto
import synapse.models.dns as s_dns
import synapse.models.inet as s_inet
import synapse.models.infotech as s_infotech
import synapse.models.risk as s_risk

import synapse.lookup.macho as s_l_macho
import synapse.lookup.pe as s_l_pe


def _tuplesToLists(obj):
    '''Recursively convert tuples to lists for YAML output.'''
    if isinstance(obj, tuple):
        return [_tuplesToLists(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _tuplesToLists(v) for k, v in obj.items()}
    if isinstance(obj, (FlowList, list)):
        return type(obj)(_tuplesToLists(item) for item in obj)
    return obj


class YamlAlias:
    '''Marker for a YAML alias reference.'''
    def __init__(self, name):
        self.name = name


def _buildEnumConsts():
    '''Build const name -> value mapping and id -> const name reverse lookup.'''

    consts = collections.OrderedDict()
    ids = {}

    def add(name, val, pyobj=None):
        converted = _tuplesToLists(val)
        # Make each enum entry a flow list for compact rendering
        consts[name] = [FlowList(entry) for entry in converted]
        if pyobj is not None:
            ids[id(pyobj)] = name
        else:
            ids[id(val)] = name

    add('scoreenums', s_base.scoreenums)
    add('taskstatusenums', s_base.taskstatusenums)
    add('x509vers', s_crypto.x509vers)
    add('dnsreplycodes', s_dns.dnsreplycodes)
    add('loglevels', s_infotech.loglevels)
    add('tlplevels', s_infotech.tlplevels)
    add('suslevels', s_infotech.suslevels)
    add('svcobjstatus', s_inet.svcobjstatus)
    add('svcaccesstypes', s_inet.svcaccesstypes)
    add('alertstatus', s_risk.alertstatus)

    # Function-generated enums - call once and track the objects
    macho_lc = s_l_macho.getLoadCmdTypes()
    macho_st = s_l_macho.getSectionTypes()
    pe_rt = s_l_pe.getRsrcTypes()
    pe_lc = s_l_pe.getLangCodes()

    add('macho_loadcmd_types', macho_lc)
    add('macho_section_types', macho_st)
    add('pe_resource_types', pe_rt)
    add('pe_lang_codes', pe_lc)

    return consts, ids


def _resolveEnums(opts, enum_ids):
    '''If opts contains an 'enums' key referencing a known Python variable, replace with YamlAlias.'''
    if 'enums' not in opts:
        return opts
    enums_val = opts['enums']
    const_name = enum_ids.get(id(enums_val))
    if const_name is not None:
        opts = dict(opts)
        opts['enums'] = YamlAlias(const_name)
    return opts


def _edgeSortKey(edge):
    '''Sort key for edge entries with None sorting first.'''
    key = edge[0]
    return tuple(x if x is not None else '' for x in key)


def convertTypedef(typedef, enum_ids):
    '''Convert a type definition tuple to YAML-friendly list format.'''
    # Poly types: ((type1, {}), (type2, {}), ...) - first element is a tuple
    if isinstance(typedef[0], tuple):
        return [FlowList([t[0], _tuplesToLists(t[1])]) for t in typedef]

    basetype, opts = typedef
    opts = dict(opts)
    opts = _resolveEnums(opts, enum_ids)
    converted_opts = _tuplesToLists(opts)
    return FlowList([basetype, converted_opts])


def convertPropdef(typedef, propinfo, enum_ids):
    '''Convert a property definition to a YAML-friendly dict.'''
    result = collections.OrderedDict()
    if typedef is not None:
        result['type'] = convertTypedef(typedef, enum_ids)
    for key, val in propinfo.items():
        if key in ('prevnames', 'alts'):
            result[key] = FlowList(_tuplesToLists(val))
        else:
            result[key] = _tuplesToLists(val)
    return result


def convertProps(propdefs, enum_ids):
    '''Convert a tuple of (propname, typedef, propinfo) to an ordered dict.'''
    result = collections.OrderedDict()
    for propname, typedef, propinfo in propdefs:
        result[propname] = convertPropdef(typedef, propinfo, enum_ids)
    return result


def convertTypeInfo(typeinfo, typedef, enum_ids):
    '''Convert type info dict to YAML-friendly format.'''
    result = collections.OrderedDict()

    result['type'] = convertTypedef(typedef, enum_ids)

    key_order = ['doc', 'ex', 'interfaces', 'template', 'display', 'virts',
                 'on', 'runt', 'liftfunc', 'prevnames', 'deprecated', 'props']

    processed = set()
    for key in key_order:
        if key in typeinfo:
            val = typeinfo[key]
            if key == 'interfaces':
                result[key] = [FlowList([name, _tuplesToLists(opts)]) for name, opts in val]
            elif key == 'props':
                if val == () or val == []:
                    result[key] = {}
                else:
                    result[key] = convertProps(val, enum_ids)
            elif key == 'virts':
                result[key] = convertProps(val, enum_ids)
            elif key == 'prevnames':
                result[key] = FlowList(_tuplesToLists(val))
            else:
                result[key] = _tuplesToLists(val)
            processed.add(key)

    for key, val in typeinfo.items():
        if key not in processed:
            result[key] = _tuplesToLists(val)

    return result


def convertInterface(ifaceinfo, enum_ids):
    '''Convert interface info dict to YAML-friendly format.'''
    result = collections.OrderedDict()

    key_order = ['doc', 'interfaces', 'template', 'props']

    processed = set()
    for key in key_order:
        if key in ifaceinfo:
            val = ifaceinfo[key]
            if key == 'props':
                result[key] = convertProps(val, enum_ids)
            elif key == 'interfaces':
                result[key] = [FlowList([name, _tuplesToLists(opts)]) for name, opts in val]
            else:
                result[key] = _tuplesToLists(val)
            processed.add(key)

    for key, val in ifaceinfo.items():
        if key not in processed:
            result[key] = _tuplesToLists(val)

    return result


class FlowList(list):
    '''A list that should be rendered in YAML flow style.'''


class FlowDict(dict):
    '''A dict that should be rendered in YAML flow style.'''


def _renderYaml(doc, enum_consts):
    '''Render YAML with anchor/alias support for consts.'''

    # Build shared anchor objects for each const
    anchors = {}
    for name, val in doc['consts'].items():
        anchors[name] = val

    def _replaceAliases(obj):
        if isinstance(obj, YamlAlias):
            return anchors[obj.name]
        if isinstance(obj, dict):
            newdict = collections.OrderedDict() if isinstance(obj, collections.OrderedDict) else {}
            for k, v in obj.items():
                newdict[k] = _replaceAliases(v)
            return newdict
        if isinstance(obj, FlowList):
            return FlowList(_replaceAliases(item) for item in obj)
        if isinstance(obj, list):
            return [_replaceAliases(item) for item in obj]
        return obj

    resolved = _replaceAliases(doc)

    # Restore anchor objects in consts so they share identity with alias references
    for name, val in anchors.items():
        resolved['consts'][name] = val

    class OrderedDumper(yaml.SafeDumper):
        pass

    def _dict_representer(dumper, data):
        return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())

    def _flow_list_representer(dumper, data):
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)

    def _flow_dict_representer(dumper, data):
        return dumper.represent_mapping('tag:yaml.org,2002:map', data.items(), flow_style=True)

    OrderedDumper.add_representer(collections.OrderedDict, _dict_representer)
    OrderedDumper.add_representer(FlowList, _flow_list_representer)
    OrderedDumper.add_representer(FlowDict, _flow_dict_representer)

    output = yaml.dump(resolved, Dumper=OrderedDumper,
                       default_flow_style=False,
                       sort_keys=False,
                       width=200,
                       allow_unicode=False)

    # Post-process: rename auto-generated anchors/aliases to const names
    # PyYAML generates &id001, *id001 etc. We need to map them to &scoreenums, *scoreenums
    import re

    # Find all anchor definitions: &idNNN after const key names
    anchor_map = {}
    for name in anchors:
        pattern = re.compile(rf'  {re.escape(name)}: &(id\d+)\n')
        match = pattern.search(output)
        if match:
            anchor_map[match.group(1)] = name

    # Replace all occurrences
    for auto_name, const_name in anchor_map.items():
        output = output.replace(f'&{auto_name}', f'&{const_name}')
        output = output.replace(f'*{auto_name}', f'*{const_name}')

    return output


def main():

    enum_consts, enum_ids = _buildEnumConsts()

    # Load all model definitions
    all_mdefs = []
    for path in s_models.modeldefs:
        defs = s_dyndeps.getDynLocal(path)
        if defs is not None:
            all_mdefs.extend(defs)

    # Collect all types, forms, interfaces, edges
    all_types = collections.OrderedDict()
    all_forms = {}
    all_interfaces = collections.OrderedDict()
    all_edges = []

    for mdef in all_mdefs:
        for typename, typedef, typeinfo in mdef.get('types', ()):
            all_types[typename] = (typedef, dict(typeinfo))

        for formname, forminfo, propdefs in mdef.get('forms', ()):
            all_forms[formname] = (dict(forminfo), propdefs)

        for ifacename, ifaceinfo in mdef.get('interfaces', ()):
            all_interfaces[ifacename] = dict(ifaceinfo)

        for edge in mdef.get('edges', ()):
            all_edges.append(edge)

    # Merge forms into types
    for formname, (forminfo, propdefs) in all_forms.items():
        if formname not in all_types:
            print(f'WARNING: Form {formname} has no corresponding type!', file=sys.stderr)
            continue

        typedef, typeinfo = all_types[formname]

        if 'props' in typeinfo:
            for key in ('on', 'runt', 'liftfunc', 'prevnames', 'deprecated'):
                if key in forminfo and key not in typeinfo:
                    typeinfo[key] = forminfo[key]
            continue

        typeinfo['props'] = propdefs

        for key in ('on', 'runt', 'liftfunc', 'prevnames', 'deprecated'):
            if key in forminfo and key not in typeinfo:
                typeinfo[key] = forminfo[key]

    # Build the YAML document
    doc = collections.OrderedDict()

    doc['consts'] = collections.OrderedDict()
    for name, val in enum_consts.items():
        doc['consts'][name] = val

    doc['types'] = collections.OrderedDict()
    for typename in sorted(all_types.keys()):
        typedef, typeinfo = all_types[typename]
        doc['types'][typename] = convertTypeInfo(typeinfo, typedef, enum_ids)

    doc['interfaces'] = collections.OrderedDict()
    for ifacename in sorted(all_interfaces.keys()):
        doc['interfaces'][ifacename] = convertInterface(all_interfaces[ifacename], enum_ids)

    sorted_edges = sorted(all_edges, key=_edgeSortKey)
    doc['edges'] = []
    for edgekey, edgeinfo in sorted_edges:
        key = FlowList(edgekey)
        doc['edges'].append(FlowList([key, _tuplesToLists(dict(edgeinfo))]))

    outpath = os.path.join(os.path.dirname(__file__), '..', 'synapse', 'datamodel.yaml')
    outpath = os.path.abspath(outpath)

    output = _renderYaml(doc, enum_consts)

    with open(outpath, 'w') as fd:
        fd.write(output)

    print(f'Wrote {outpath}')
    print(f'  Types: {len(doc["types"])}')
    print(f'  Interfaces: {len(doc["interfaces"])}')
    print(f'  Edges: {len(doc["edges"])}')
    print(f'  Consts: {len(doc["consts"])}')


if __name__ == '__main__':
    main()
