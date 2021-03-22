import asyncio
import uuid
import datetime
import collections
# import synapse.lib.datfile as s_datfile
import synapse.exc as s_exc
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

_ALL1 = (1 << 128) - 1

def _buid_to_uuid4(buid: bytes) -> str:
    '''
    Construct a UUID4 from the leftmost 122 bits of a buid.

    Shift bits around so that 122 leftmost bits of buid can be reconstructed from a uuid4

    UUID4 overwrites 6 bits.  Bits 62-63 and 76-79 (with bit 0 being LS bit).
    xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx
    '''

    buidi = int.from_bytes(buid[:16], byteorder='big')
    part1 = buidi & (_ALL1 << 80)  # bits 80-127
    part2 = buidi & (_ALL1 << 68) ^ part1 # bits 68-79
    part3 = buidi & (_ALL1 >> 60)  # bits 0-67

    return str(uuid.UUID(int=_ALL1 & (part1 | part2 >> 4 | part3 >> 6), version=4))


def _uuid4_to_buidpre(uuids: str) -> bytes:
    '''
    Construct a 120-bit buid prefix from a UUID string.
    '''
    uuidi = uuid.UUID(uuids).int
    part1 = uuidi & (_ALL1 << 80)  # bits 80-127
    part2 = uuidi & (_ALL1 << 76 ^ _ALL1 << 64) # bits 64-75
    part3 = uuidi & (_ALL1 >> 66) # bits 0-61

    buidi = (part1 | part2 << 4 | part3 << 6) >> 8

    return (buidi.to_bytes(15, byteorder='big'))

# Constant used to identify the extra property we put on every generated STIX object
SYNAPSE_EXTENSION_UUID = uuid.UUID('480c630e-be95-2ae5-a189-aa7ff4b40653')

_contact_info_q = '''
    $lst = $lib.list()
    $loc = :loc
    if ($loc) {
        $lst.append($loc)
    }
    $phone = :phone
    if ($phone) {
        $lst.append($phone)
    }
    if (not $lib.len($lst)) {
        return($lib.null)
    }
    return ($lib.str.join(" ", $lst))'''


# FIXME:  perhaps move to separate file?
_DefaultConfig = {
    'campaign': {
        'ou:campaign': {
            'props': {
                '...': '...'
            },
            'rels': {
                'attributed-to': (
                    {
                        'stixtype': 'threat-actor',
                        'query': ' return (:actors)',
                    },
                    {
                        'stixtype': 'threat-actor',
                        'query': ' return (:org)',
                    }
                )
            }
        }
    },
    'identity': {
        'ps:contact': {
            'props': {
                'contact_information': {
                    'query': _contact_info_q},
                'identity_class': {
                    'query': 'return (individual)'},
                'name': {
                    'query': 'return (:name)'},
                'roles': {
                    'query': 'if (:title) {return ($lib.list(:title))}'},
            },
            'rels': {
                'located-at': [{  # Make a new location STIX object from :loc, add the SRO from here to that
                    'stixtype': 'location',
                    'query': 'return (:loc)',
                    'syntype': 'loc'
                }]
            }
        }
    },
    'location': {
        'loc': {  # A synapse type, not a form
            'country': {
                'query': '{ return ($field.split(".").0) }'}  # FIXME:  for testing purposes.  Need to validate
        }
    },
    'malware': {
        'file:bytes': {
            'props': {
                '...': {},
                'sample_refs': {
                    'stixobj': '',  # FIXME:  return a full file STIX object
                }
            }
        }
    },
    'ipv4-addr': {
        'inet:ipv4': {
            'props': {
                '...': {},  # FIXME
                'belongs_to_refs': {
                    'stixtype': 'autonomous-system',
                    'ref-nodes': ':asn -> inet:asn',  # adds those nodes
                }
            }
        }
    }
}

def _validateStixObj(obj):
    # fastjsonschema.compile(schema, handlers={'file': ':':':   )
    # FIXME
    pass

def _validateConfig(config):
    # FIXME
    pass

@s_stormtypes.registry.registerLib
class LibStix(s_stormtypes.Lib):
    '''
    A Storm Library for exporting to STIX version 2.1
    '''
    _storm_locals = (  # type: ignore
        {'name': 'bundle', 'desc': 'Return a new empty STIX bundle.',
         'type': {'type': 'function', '_funcname': '_methBundle',
                  'args': (
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Optional config parameter.', },
                  ),
                  'returns': {'type': 'storm:stix:bundle',
                              'desc': 'A new ``storm:stix:bundle`` instance.',
                              }}},

    )
    _storm_lib_path = ('stix',)

    def __init__(self, runt, name=()):
        _validateConfig(_DefaultConfig)
        s_stormtypes.Lib.__init__(self, runt, name)

    def getObjLocals(self):
        return {
            'bundle': self._methBundle,  # FIXME:  should this be a ctor?
        }

    async def _methBundle(self, **kwargs):
        config = kwargs.pop('config', None)

        if config:
            _validateConfig(config)
        else:
            config = _DefaultConfig
        return StixBundle(self.runt, config)

@s_stormtypes.registry.registerType
class StixBundle(s_stormtypes.Prim):

    _storm_typename = 'storm:stix:bundle'  # type: ignore
    _storm_locals = (  # type: ignore

        {'name': 'addNode', 'desc': '''
        Make one or more STIX objects from a node, and add it to the bundle.

        If the object already exists in the bundle, the existing object will
        be modified.

        Optional args:
            props(dict): Additional properties to set on the STIX object.
                         If "type" is set, returned object's STIX type shall
                         match.'},
            dorels(bool):Also add outgoing relationships and objects targeted
                         by refs' properties.  Defaults to true.'

        Example:
            FIXME ''',
         'type': {'type': 'function', '_funcname': '_methAddNode',
                  'args': (
                      {'name': 'node', 'desc': 'The node to make a STIX object from.', 'type': 'node'},
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Key-value parameters used to add the cron job.', },
                  ),
                  'returns': {'type': 'dict',
                              'desc': 'The primary object converted.'}}},

        {'name': 'addRaw', 'desc': 'Add a raw STIX object to the bundle.',
         'type': {'type': 'function', '_funcname': '_methAddRaw',
                  'args': (
                      {'name': 'obj', 'desc': 'STIX object to add.', 'type': 'dict'},
                  ),
                  'returns': {'type': 'dict', }}},

        {'name': 'addRel', 'desc': 'Construct and add a STIX relationship object (SRO) to the bundle.',
         'type': {'type': 'function', '_funcname': '_methAddRel',
                  'args': (
                      {'name': 'srcid', 'desc': 'Identifier of source STIX object.', 'type': 'str'},
                      {'name': 'reltype', 'desc': 'Relationship type.', 'type': 'str'},
                      {'name': 'srcid', 'desc': 'Identifier of destination STIX object.', 'type': 'str'},
                      {'name': 'props', 'desc': 'Extra properties to set on SRO.', 'type': 'dict'},
                  ),
                  'returns': {'type': 'dict', }}},

        {'name': 'get', 'desc': 'Retrieve a STIX object from the bundle.',
         'type': {'type': 'function', '_funcname': '_methGet',
                  'args': (
                      {'id': 'obj', 'desc': 'Identifier of STIX object to retrieve.', 'type': 'str'},
                  ),
                  'returns': {'type': 'dict', }}},

        {'name': 'json', 'desc': 'Return the bundle as a STIX object.',
         'type': {'type': 'function', '_funcname': '_methJson',
                  'args': (),
                  'returns': {'type': 'dict', }}},

    )

    def __init__(self, runt, config, path=None):
        s_stormtypes.Prim.__init__(self, 'bundle', path=path)
        self.runt = runt
        self.locls.update(self.getObjLocals())
        self.config = config
        self.objs = {}  # id -> STIX obj(dict)
        self.rels = {}  # (srcid, reltype, targid) -> STIX obj(dict)

    def getObjLocals(self):
        return {
            'addNode': self._methAddNode,
            'addRaw': self._methAddRaw,
            'addRel': self._methAddRel,
            'get': self._methGet,
            'json': self._methJson,
        }

    async def _methAddNode(self, node, **kwargs):
        props = kwargs.get('props', {})
        stixtype = props.pop('type', None)
        dorels = kwargs.get('dorels', True)
        form = node.form.name

        formmap = collections.defaultdict(list)
        for stixt, stixtypedict in self.config.items():
            for formname in stixtypedict.keys():
                formmap[formname].append(stixt)

        if stixtype is None:
            guess = formmap.get(node.form.name)
            if guess is None:
                raise s_exc.NeedConfValu(mesg=f'Cannot discern STIX object type from form {form}.  Must specify type.')
            if len(guess) > 1:
                raise s_exc.NeedConfValu(mesg='Multiple STIX object candidates.  Must specify type.')
            stixtype = guess[0]

        stixid = f'{stixtype}--{_buid_to_uuid4(node.buid)}'

        # Check if we already added this node
        obj = self.objs.get(stixid, {})
        if obj and stixtype != obj['type']:
            raise s_exc.NeedConfValu(mesg='Cannot add the same node as two different STIX types in the same bundle.')

        stixtentry = self.config.get(stixtype)
        if stixtentry is None:
            raise s_exc.NeedConfValu(mesg=f'No configuration present for converting to a {stixtype}')

        entry = stixtentry.get(form)
        if entry is None:
            raise s_exc.NeedConfValu(mesg=f'No configuration present for converting a {form} to a {stixtype}')

        propsentry = entry.get('props')
        if propsentry is None:
            raise s_exc.NeedConfValu(mesg=f'"props" property required in config {stixtype}.{form}')

        # Make/update the STIX object from the node
        obj.update(await self._convertProps(node, propsentry, dorefs=dorels))
        obj.update(self._obj_boilerplate(stixid, stixtype, node))

        # TODO:  node tags to 'labels'?
        obj.update(props)

        self.objs[stixid] = obj
        rels = entry.get('rels')
        if dorels and rels:
            await self._make_rels(obj, node, rels)

        _validateStixObj(obj)

        return obj

    def _obj_boilerplate(self, stixid, stixtype, node):
        dt = datetime.datetime.utcfromtimestamp(node.props.get('.created', 0) / 1000.0)
        created = dt.isoformat(timespec='milliseconds') + 'Z'

        return {
            'type': stixtype,
            'created': created,
            'modified': created,
            'id': stixid,
            'spec_version': '2.1',
            'extensions': {
                f'extension-definition--{SYNAPSE_EXTENSION_UUID}': {
                    "extension_type": "property-extension",
                    "synapse_ndef": node.ndef,
                }
            }
        }

    async def _methAddRel(self, srcid, reltype, targid, props=None):
        # TODO:  should relationships have stable UUIDs between bundles?
        stixid = f'relationship--{uuid.uuid4()}'
        key = (srcid, reltype, targid)
        rel = self.rels.get(key)
        if rel:
            return rel

        obj = {
            'id': stixid,
            'type': 'relationship',
            'relationship_type': reltype,
            'source_ref': srcid,
            'target_ref': targid,
            'spec_version': '2.1',
        }

        if props:
            obj.update(props)

        self.rels[key] = obj
        self.objs[stixid] = obj
        return obj

    async def _make_rels(self, obj, node, rels):
        '''
        Make all the SROs and dest objects by trying all the rels
        '''
        for reltype, relentries in rels.items():
            for relentry in relentries:
                query = relentry.get('query')
                if query is None:
                    mesg = f'STIX config: relationship entry {reltype} must contain "query" property'
                    raise s_exc.NeedConfValu(mesg=mesg)
                stixtype = relentry.get('stixtype')
                if stixtype is None:
                    mesg = f'STIX config: relationship entry {reltype} must contain "stixtype" property'
                    raise s_exc.NeedConfValu(mesg=mesg)
                retn = await self._callStorm(node, query)
                if retn is None or not len(retn):
                    continue
                syntype = relentry.get('syntype')
                if syntype is None:
                    destobj = await self._methAddNode(retn, {'type': stixtype, 'dorels': False})
                else:
                    destobj = await self._addSynType(stixtype, syntype, node, retn)

                if destobj is None:
                    continue

                await self._methAddRel(obj['id'], reltype, destobj['id'])

    async def _addSynType(self, stixtype, syntype, node, valu):
        guid = uuid.uuid5(SYNAPSE_EXTENSION_UUID, str((stixtype, valu)))
        stixid = f'{stixtype}--{guid}'
        obj = self.objs.get(stixid)
        if obj is not None:
            return obj

        stixtentry = self.config.get(stixtype)
        if stixtentry is None:
            raise s_exc.NeedConfValu(mesg=f'STIX config: config[{stixtype}][{syntype}] missing')

        entry = stixtentry.get(syntype)
        if entry is None:
            return None

        obj = await self._convertProps(node, entry, dorefs=False, vars_={'field': valu})

        obj.update(self._obj_boilerplate(stixid, stixtype, node))

        self.objs[stixid] = obj
        _validateStixObj(obj)
        return obj

    async def _methAddRaw(self, stixobj):
        _validateStixObj(stixobj)
        # FIXME:  don't replace if already exists?
        self.objs[stixobj['id']] = stixobj
        return stixobj

    async def _methJson(self):
        bundle = {
            'type': 'bundle',
            'id': str(uuid.uuid4()),
            'objects': list(self.objs.values())
        }
        return bundle

    async def _methGet(self, guid):
        return self.objs.get(guid)

    async def _callStorm(self, node, query, vars_=None):
        opts = {'vars': vars_} if vars_ else None
        try:
            async for _ in node.storm(self.runt, query, opts=opts):
                await asyncio.sleep(0)

        except s_stormctrl.StormReturn as e:
            return await s_stormtypes.toprim(e.item)

        return None

    async def _convertProps(self, node, entry, dorefs=True, vars_=None):
        '''
        Apply the queries in a config entry
        '''
        obj = {}
        for field, fconf in entry.items():
            if not dorefs and (field.endswith('_ref') or field.endswith('_refs')):
                continue
            query = fconf.get('query')
            if query:
                retn = await self._callStorm(node, query, vars_=vars_)
                if retn is None:
                    continue
                obj[field] = retn
                continue

            stopatone = False
            refnodesq = fconf.get('ref-nodes')
            if not refnodesq:
                refnodesq = fconf.get('ref-node')
                if not refnodesq:
                    mesg = f'STIX config: No conversion config for {field} (must have query, ref-node, ref-nodes set)'
                    raise s_exc.NeedConfValu(mesg=mesg)
                stopatone = True

            stixtype = fconf.get('stixtype')
            if not stixtype:
                mesg = 'STIX config: "stixtype" property must be present if "ref-nodes" is present'
                raise s_exc.NeedConfValu(mesg=mesg)

            # Convert the nodes returned from the query in ref-nodes and put their ids as a list
            refids = []
            async for refnode in await node.storm(self.runt, refnodesq):
                refobj = self._methAdd(refnode, props={'type': stixtype})
                refids.append(refobj['id'])
                if stopatone:
                    break

            if refids:
                if stopatone:
                    obj[field] = refids[0]
                else:
                    obj[field] = refids

        return obj

# FIXME:  extract from schema
STIX_INDUSTRIES = {
    "agriculture",
    "aerospace",
    "automotive",
    "chemical",
    "commercial",
    "communications",
    "construction",
    "defense",
    "education",
    "energy",
    "engineering",
    "entertainment",
    "financial-services",
    "government",
    "emergency-services",
    "government-local",
    "government-national",
    "government-public-services",
    "government-regional",
    "healthcare",
    "hospitality-leisure",
    "infrastructure",
    "dams",
    "nuclear",
    "water",
    "insurance",
    "manufacturing",
    "mining",
    "non-profit",
    "pharmaceuticals",
    "retail",
    "technology",
    "telecommunications",
    "transportation",
    "utilities"
}
