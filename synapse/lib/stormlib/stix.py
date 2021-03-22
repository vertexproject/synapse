import asyncio
import uuid
import datetime
import collections
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

SYNAPSE_EXTENSION_UUID = '480c630e-be95-2ae5-a189-aa7ff4b40653'


def _validateStix(obj):
    # FIXME
    pass

def _validateConfig(config):
    # FIXME
    pass

@s_stormtypes.registry.registerLib
class LibStix(s_stormtypes.Lib):
    '''
    A Storm Library for exporting to STIX
    '''
    _storm_locals = (  # type: ignore
        # FIXME:  loadConfig
        {'name': 'bundle', 'desc': 'Make an new empty STIX bundle.',
         'type': {'type': 'function', '_funcname': '_methBundle',
                  'args': (),
                  'returns': {'type': 'storm:stix:bundle',
                              'desc': 'A new ``storm:stix:bundle`` instance.',
                              }}},
        {'name': 'convert', 'desc': 'Convert a node into a STIX object.',
         'type': {'type': 'function', '_funcname': '_methConvert',
                  'args': (
                      {'name': 'node', 'desc': 'The node or STIX object to add.', 'type': 'str'},
                      {'name': 'makerels', 'desc': 'Whether to include SROs as well.', 'type': 'bool'},
                      {'name': '**kwargs', 'type': 'any', 'desc': 'Additional properties to set on the STIX object.'},
                  ),
                  'returns': {'type': 'list',
                              'desc': 'A list of STIX objects (i.e. a list of dicts).',
                              }}},
    )
    _storm_lib_path = ('stix',)

    def getObjLocals(self):
        return {
            'bundle': self._methBundle,
            'convert': self._methConvert,
        }

    async def _methBundle(self):
        return StixBundle()

    async def _methFromNode(self, node, **kwargs):
        stixtype = kwargs.pop('type', None)
        config = kwargs.pop('config', _DefaultConfig)

        # FIXME: validate config

        formmap = collections.defaultdict(list)
        for stix, form in config.keys():
            formmap[form].append(stix)

        if stixtype is None:
            form = node.form.name
            guess = formmap.get(node.form.name)
            if guess is None:
                raise Exception(f'Cannot discern STIX object type from form {form}.  Must specify type.')
            if len(guess) > 1:
                raise Exception('Multiple STIX object candidates.  Must specify type.')
            stixtype = guess[0]
        # FIXME:  check against schema

        entry = config.get((stixtype, form))
        if entry is None:
            raise Exception(f'No configuration present for converting a {form} to a {stixtype}')

        obj = await self._convertProps(node, entry)
        obj['type'] = stixtype
        dt = datetime.datetime.utcfromtimestamp(node.props.get('.created', 0) / 1000.0)
        created = dt.isoformat(timespec='milliseconds') + 'Z'
        obj['created'] = obj['modified'] = created
        obj['id'] = _buid_to_uuid4(node.buid)
        obj['extensions'] = {
            f'extension-definition--{SYNAPSE_EXTENSION_UUID}': {
                "extension_type": "property-extension",
                "synapse_ndef": node.ndef,
            }
        }
        obj.update(kwargs)
        if not makerels:
            return [obj]

        return obj

        # FIXME:  schema check

    async def _makeStix(self, **kwargs):
        '''
        Make a STIX object from scratch
        '''
        obj = kwargs
        # FIXME:  json schema check
        return obj

    async def _callStorm(self, node, query):

        try:
            async for _ in node.storm(self.runt, query):
                await asyncio.sleep(0)

        except s_stormctrl.StormReturn as e:
            return await s_stormtypes.toprim(e.item)

        return None

    async def _convertProps(self, node, entry):
        '''
        Apply the queries in a config entry
        '''
        obj = {}
        props = entry.get('props', {})
        for field, query in props.items():
            retn = await self._callStorm(node, query)
            if retn is None:
                continue
            obj[field] = retn
        return obj

@s_stormtypes.registry.registerType
class StixBundle(s_stormtypes.Prim):
    _storm_typename = 'storm:stix:bundle'  # type: ignore
    _storm_locals = (  # type: ignore
        {'name': 'add', 'desc': 'Add a node or STIX object (as JSON) to the bundle.',
         'type': {'type': 'function', '_funcname': '_methAdd',
                  'args': (
                      {'node': 'valu', 'desc': 'The node or STIX object to add.', 'type': ['str', 'storm:node'], },
                  ),
                  'returns': {'desc': '0 or more STIX JSON objects.', 'type': 'list'}}},
    )

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

_DefaultConfig = {
    'identity': {
        'ps:contact': {
            'props': {
                'contact_information':
                    '$lst = $lib.list() '
                    'if (:loc) {$lst.append(:loc)} '
                    'if (:phone) {$lst.append(:phone)} '
                    'if (not $lib.len(lst) {return($lib.null)} '
                    'return ($lib.str.join(" ", $lst))',
                'identity_class': 'return (individual)',
                'name': 'return (:name)',
                'roles': 'if (:title) {return ($lib.list(:title))}',
            },
            # FIXME:  move from default into test config (loc isn't necessarily a country)
            'rels': {
                'location': {
                    'country': '$loc = :loc if ($loc) { return $loc.split(".").0 }'
                }
            }
        }
    }
}
