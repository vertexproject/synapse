import json
import uuid
import asyncio
import datetime

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.node as s_node
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes


def uuid5(valu=None):
    guid = s_common.guid(valu=valu)
    return str(uuid.UUID(guid, version=5))

def uuid4(valu=None):
    guid = s_common.guid(valu=valu)
    return str(uuid.UUID(guid, version=4))

_DefaultConfig = {

    'maxsize': 10000,

    'forms': {

        'ou:campaign': {
            'default': 'campaign',
            'stix': {
                'campaign': {
                    'props': {
                        'name': '{+:name return(:name)} return($node.repr())',
                        'description': '+:desc return(:desc)',
                        'objective': '+:goal :goal -> ou:goal +:name return(:name)',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                    },
                    'rels': (
                        ('attributed-to', 'threat-actor', ':org -> ou:org'),
                        ('originates-from', 'location', ':org -> ou:org :hq -> geo:place'),
                        ('targets', 'identity', '-> risk:attack :target:org -> ou:org'),
                        ('targets', 'identity', '-> risk:attack :target:person -> ps:person'),
                    ),
                },
            },
        },

        'ou:org': {
            'default': 'identity',
            'stix': {
                'identity': {
                    'props': {
                        'name': '{-:name return($node.repr())} return(:name)',
                        'identity_class': 'return(organization)',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'sectors': '''
                            init { $list = $lib.list() }
                            -> ou:industry +:name $list.append(:name)
                            fini { if $list { return($list) } }
                        ''',
                    }
                },
                'threat-actor': {
                    'props': {
                        'name': '{+:name return(:name)} return($node.repr())',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'first_seen': '+.seen $seen=.seen return($lib.stix.export.timestamp($seen.0))',
                        'last_seen': '+.seen $seen=.seen return($lib.stix.export.timestamp($seen.1))',
                        'goals': '''
                            init { $goals = $lib.list() }
                            -> ou:campaign:org -> ou:goal | uniq | +:name $goals.append(:name)
                            fini { if $goals { return($goals) } }
                        ''',
                    },
                    'rels': (
                        ('attributed-to', 'identity', ''),
                        ('located-at', 'location', ':hq -> geo:place'),
                        ('targets', 'identity', '-> ou:campaign -> risk:attack :target:org -> ou:org'),
                        # ('targets', 'location', ''),
                        # ('impersonates', 'identity', ''),
                    ),
                },
            },
        },

        'ps:person': {
            'default': 'identity',
            'stix': {
                'identity': {
                    'props': {
                        'name': '{+:name return(:name)} return($node.repr())',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'identity_class': 'return(individual)',
                    }
                },
            },
        },

        'ps:contact': {
            'default': 'identity',
            'stix': {
                'identity': {
                    'props': {
                        'name': '{+:name return(:name)} return($node.repr())',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'identity_class': 'return(individual)',
                    }
                },
            },
        },

        'geo:place': {
            'default': 'location',
            'stix': {
                'location': {
                    'props': {
                        'name': '{+:name return(:name)} return($node.repr())',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'country': '+:loc $loc = :loc return($loc.split(".").0)',
                        'latitude': '+:latlong $latlong = :latlong return($latlong.0)',
                        'longitude': '+:latlong $latlong = :latlong return($latlong.1)',
                    },
                },
            },
        },

        'inet:ipv4': {
            'default': 'ipv4-addr',
            'stix': {
                'ipv4-addr': {
                    'props': {
                        'value': 'return($node.repr())',
                    },
                    'rels': (
                        ('belongs-to', 'autonomous-system', '-> inet:asn'),
                    ),
                }
            },
        },

        'inet:ipv6': {
            'default': 'ipv6-addr',
            'stix': {
                'ipv6-addr': {
                    'props': {
                        'value': 'return($node.repr())',
                    },
                    'rels': (
                        ('belongs-to', 'autonomous-system', '-> inet:asn'),
                    ),
                }
            },
        },

        'inet:fqdn': {
            'default': 'domain-name',
            'stix': {
                'domain-name': {
                    'props': {
                        'value': 'return($node.repr())',
                        'resolves_to_refs': '''
                            init { $refs = $lib.list() }
                            { -> inet:dns:a -> inet:ipv4 $refs.append($bundle.add($node)) }
                            { -> inet:dns:aaaa -> inet:ipv6 $refs.append($bundle.add($node)) }
                            { -> inet:dns:cname:fqdn :cname -> inet:fqdn $refs.append($bundle.add($node)) }
                            fini { if $refs { return($refs)} }
                         ''',
                    },
                }
            },
        },

        'inet:asn': {
            'default': 'autonomous-system',
            'stix': {
                'autonomous-system': {
                    'props': {
                        'name': '+:name return(:name)',
                        'number': 'return($node.value())',
                    },
                }
            },
        },

        'inet:email': {
            'default': 'email-addr',
            'stix': {
                'email-addr': {
                    'props': {
                        'value': 'return($node.repr())',
                        'display_name': '-> ps:contact +:name return(:name)',
                        'belongs_to_ref': '-> inet:web:acct return($bundle.add($node))',
                    },
                }
            },
        },

        'inet:web:acct': {
            'default': 'user-account',
            'stix': {
                'user-account': {
                    'props': {
                        'user_id': 'return(:user)',
                        'account_login': 'return(:user)',
                        'account_type': '''
                            {+:site=twitter.com return(twitter)}
                            {+:site=facebook.com return(facebook)}
                        ''',
                        'credential': '+:passwd return(:passwd)',
                        'display_name': '+:realname return(:realname)',
                        'account_created': '+:signup return($lib.stix.export.timestamp(:signup))',
                        'account_last_login': '+.seen $ival = .seen return($lib.stix.export.timestamp($ival.0))',
                        'account_first_login': '+.seen $ival = .seen return($lib.stix.export.timestamp($ival.1))',
                    },
                }
            },
        },

        'file:bytes': {
            'default': 'file',
            'stix': {
                'file': {
                    'props': {
                        'name': '{+:name return(:name)} return($node.repr())',
                        'size': '+:size return(:size)',
                        'hashes': '''
                            init { $dict = $lib.dict() }
                            { +:md5 $dict.MD5 = :md5 }
                            { +:sha1 $dict."SHA-1" = :sha1 }
                            { +:sha256 $dict."SHA-256" = :sha256 }
                            { +:sha512 $dict."SHA-512" = :sha512 }
                            fini { if $dict { return($dict) } }
                        ''',
                        'mime_type': '+:mime return(:mime)',
                        'contains_refs': '''
                            init { $refs = $lib.list() }
                            -(refs)> *
                            $stixid = $bundle.add($node)
                            if $stixid { $refs.append($stixid) }
                            fini { if $refs { return($refs) } }
                        ''',
                    },
                },
            },
        },

        'inet:email:message': {
            'default': 'email-message',
            'stix': {
                'email-message': {
                    'props': {
                        'date': '+:date return($lib.stix.export.timestamp(:date))',
                        'subject': '+:subject return(:subject)',
                        'message_id': '-> inet:email:header +:name=message_id return(:value)',
                        'is_multipart': 'return($lib.false)',
                        'from_ref': ':from -> inet:email return($bundle.add($node))',
                        'to_refs': '''
                            init { $refs = $lib.list() }
                            { :to -> inet:email $refs.append($bundle.add($node)) }
                            fini { if $refs { return($refs) } }
                        ''',
                    },
                },
            },
        },

        'inet:url': {
            'default': 'url',
            'stix': {
                'url': {
                    'props': {
                        'value': 'return($node.repr())',
                    },
                }
            },
        },

        'syn:tag': {
            'default': 'malware',
            'stix': {
                'malware': {
                    'props': {
                        'name': '{+:title return(:title)} return($node.repr())',
                        'is_family': 'return($lib.true)',
                        'first_seen': '+.seen $seen=.seen return($lib.stix.export.timestamp($seen.0))',
                        'last_seen': '+.seen $seen=.seen return($lib.stix.export.timestamp($seen.1))',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'sample_refs': '''
                            init { $refs = $lib.list() }
                            -> file:bytes $refs.append($bundle.add($node))
                            fini { if $refs { return($refs) } }
                        ''',
                    },
                    'rels': (
                        # many of these depend on tag conventions (left for user to decide)

                        # ('controls', 'malware', '',
                        # ('authored-by', 'threat-actor', '',

                        # ('drops', 'file', '',
                        # ('drops', 'tool', '',
                        # ('drops', 'malware', '',

                        # ('downloads', 'file', '',
                        # ('downloads', 'tool', '',
                        # ('downloads', 'malware', '',

                        # ('uses', 'tool', '',
                        # ('uses', 'malware', '',
                        # ('targets', 'identity', '',
                        # ('targets', 'location', '',

                        # ('communicates-with', 'ipv4-addr',
                        # ('communicates-with', 'ipv6-addr',
                        # ('communicates-with', 'domain-name',
                        # ('communicates-with', 'url',
                    ),
                },
            },
        },

        'it:prod:soft': {
            'default': 'tool',
            'stix': {
                'tool': {
                    'props': {
                        'name': '{+:name return(:name)} return($node.repr())',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                    },
                },
            },
        },

        'it:prod:softver': {
            'default': 'tool',
            'stix': {
                'tool': {
                    'props': {
                        'name': '-> it:prod:soft {+:name return(:name)} return($node.repr())',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'tool_version': '+:vers return(:vers)',
                    },
                    'rels': (
                        # TODO
                        # ('has', 'vulnerability', ''),

                        #  depends on tag conventions
                        # ('delivers', 'malware', ''),
                        # ('drops', 'malware', ''),
                        # ('targets', 'identity', '')
                        # ('targets', 'infrastructure', '')
                        # ('targets', 'location', '')
                        # ('targets', 'vulnerability', '')
                        # ('uses', 'infrastructure', ''),
                    ),
                },
            },
        },

        'media:news': {
            'default': 'report',
            'stix': {
                'report': {
                    'props': {
                        'name': 'return(:title)',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'published': 'return($lib.stix.export.timestamp(:published))',
                        'object_refs': '''
                            init { $refs = $lib.list() }
                            -(refs)> *
                            $stixid = $bundle.add($node)
                            if $stixid { $refs.append($stixid) }
                            fini { return($refs) }
                        ''',
                    },
                },
            },
        },

        'it:app:yara:rule': {
            'default': 'indicator',
            'stix': {
                'indicator': {
                    'props': {
                        'name': '+:name return(:name)',
                        'description': 'return("a yara rule")',
                        'pattern': '+:text return(:text)',
                        'pattern_type': 'return(yara)',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'valid_from': 'return($lib.stix.export.timestamp(.created))',
                    },
                },
            },
        },

        'it:app:snort:rule': {
            'default': 'indicator',
            'stix': {
                'indicator': {
                    'props': {
                        'name': '+:name return(:name)',
                        'description': 'return("a snort rule")',
                        'pattern': '+:text return(:text)',
                        'pattern_type': 'return(snort)',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'valid_from': 'return($lib.stix.export.timestamp(.created))',
                    },
                },
            },
        },
    },
}

def _validateConfig(core, config):

    maxsize = config.get('maxsize', 10000)

    if not isinstance(maxsize, int):
        mesg = f'STIX Bundle config maxsize option must be an integer.'
        raise s_exc.BadConfValu(mesg=mesg)

    if maxsize > 10000:
        mesg = f'STIX Bundle config maxsize option must be <= 10000.'
        raise s_exc.BadConfValu(mesg=mesg)

    formmaps = config.get('forms')
    if formmaps is None:
        mesg = f'STIX Bundle config is missing "forms" mappings.'
        raise s_exc.NeedConfValu(mesg=mesg)

    for formname, formconf in formmaps.items():
        form = core.model.form(formname)
        if form is None:
            mesg = f'STIX Bundle config contains invalid form name {formname}.'
            raise s_exc.NoSuchForm(mesg=mesg)

        stixdef = formconf.get('default')
        if stixdef is None:
            mesg = f'STIX Bundle config is missing default mapping for form {formname}.'
            raise s_exc.NeedConfValu(mesg=mesg)

        if stixdef not in stix_all:
            mesg = f'STIX Bundle default mapping ({stixdef}) for {formname} is not a STIX type.'
            raise s_exc.BadConfValu(mesg=mesg)

        stixmaps = formconf.get('stix')
        if stixmaps is None:
            mesg = f'STIX Bundle config is missing STIX maps for form {formname}.'
            raise s_exc.NeedConfValu(mesg=mesg)

        if stixmaps.get(stixdef) is None:
            mesg = f'STIX Bundle config is missing STIX map for form {formname} default value {stixdef}.'
            raise s_exc.BadConfValu(mesg=mesg)

        for stixtype, stixinfo in stixmaps.items():

            if stixtype not in stix_all:
                mesg = f'STIX Bundle config has unknown STIX type {stixtype} for form {formname}.'
                raise s_exc.BadConfValu(mesg=mesg)

            stixprops = stixinfo.get('props')
            if stixprops is not None:
                for stixprop, stormtext in stixprops.items():
                    if not isinstance(stormtext, str):
                        mesg = f'STIX Bundle config has invalid prop entry {formname} {stixtype} {stixprop}.'
                        raise s_exc.BadConfValu(mesg=mesg)

            stixrels = stixinfo.get('rels')
            if stixrels is not None:
                for stixrel in stixrels:
                    if len(stixrel) != 3:
                        mesg = f'STIX Bundle config has invalid rel entry {formname} {stixtype} {stixrel}.'
                        raise s_exc.BadConfValu(mesg=mesg)

@s_stormtypes.registry.registerLib
class LibStix(s_stormtypes.Lib):
    '''
    A Storm Library for exporting to STIX version 2.1
    '''
    _storm_locals = (  # type: ignore
        {
            'name': 'bundle',
            'desc': '''
                Return a new empty STIX bundle.

                The config argument maps synapse forms to stix types and allows you to specify
                how to resolve STIX properties and relationships.  The config expects to following format::

                    {
                        "maxsize": 10000,

                        "forms": {
                            <formname>: {
                                "default": <stixtype0>,
                                "stix": {
                                    <stixtype0>: {
                                        "props": {
                                            <stix_prop_name>: <storm_with_return>,
                                            ...
                                        },
                                        "rels": (
                                            ( <relname>, <target_stixtype>, <storm> ),
                                            ...
                                        )
                                    },
                                    <stixtype1>: ...
                                },
                            },
                        },
                    },

                For example, the default config includes the following entry to map ou:campaign nodes to stix campaigns::

                    { "forms": {
                        "ou:campaign": {
                            "default": "campaign",
                            "stix": {
                                "campaign": {
                                    "props": {
                                        "name": "{+:name return(:name)} return($node.repr())",
                                        "description": "+:desc return(:desc)",
                                        "objective": "+:goal :goal -> ou:goal +:name return(:name)",
                                        "created": "return($lib.stix.export.timestamp(.created))",
                                        "modified": "return($lib.stix.export.timestamp(.created))",
                                    },
                                    "rels": (
                                        ("attributed-to", "threat-actor", ":org -> ou:org"),
                                        ("originates-from", "location", ":org -> ou:org :hq -> geo:place"),
                                        ("targets", "identity", "-> risk:attack :target:org -> ou:org"),
                                        ("targets", "identity", "-> risk:attack :target:person -> ps:person"),
                                    ),
                                },
                            },
                    }},

                Note:
                    The default config is an evolving set of mappings.  If you need to guarantee stable output please
                    specify a config.
            ''',
            'type': {
                'type': 'function', '_funcname': 'bundle',
                'args': (
                    {'type': 'dict', 'name': 'config', 'default': None, 'desc': 'The STIX bundle export config to use.'},
                ),
                'returns': {'type': 'storm:stix:bundle', 'desc': 'A new ``storm:stix:bundle`` instance.'},
            },
        },

        {
            'name': 'timestamp', 'desc': 'Format an epoch milliseconds timestamp for use in STIX output.',
             'type': {
                'type': 'function', '_funcname': 'timestamp',
                'args': (
                    {'type': 'time', 'name': 'tick', 'desc': 'The epoch milliseconds timestamp.'},
                ),
                'returns': {'type': 'str', 'desc': 'A STIX formatted timestamp string.'},
            }
        },

        {
            'name': 'config',
            'desc': 'Construct a default STIX bundle export config.',
            'type': {
                'type': 'function', '_funcname': 'config',
                'returns': {'type': 'dict', 'desc': 'A default STIX bundle export config.'},
            },
        },
    )
    _storm_lib_path = ('stix', 'export')

    def __init__(self, runt, name=()):
        s_stormtypes.Lib.__init__(self, runt, name)

    def getObjLocals(self):
        return {
            'bundle': self.bundle,
            'config': self.config,
            'timestamp': self.timestamp,
        }

    async def config(self):
        # make a new mutable config
        return json.loads(json.dumps(_DefaultConfig))

    async def bundle(self, config=None):

        if config is None:
            config = _DefaultConfig

        config = await s_stormtypes.toprim(config)
        _validateConfig(self.runt.snap.core, config)

        return StixBundle(self, self.runt, config)

    def timestamp(self, tick):
        dt = datetime.datetime.utcfromtimestamp(tick / 1000.0)
        return dt.isoformat(timespec='milliseconds') + 'Z'

stix_sdos = {
    'attack-pattern',
    'campaign',
    'course-of-action',
    'grouping',
    'identity',
    'incident',
    'indicator',
    'infrastructure',
    'intrusion-set',
    'location',
    'malware-analysis',
    'malware',
    'note',
    'observed-data',
    'opinion',
    'report',
    'threat-actor',
    'tool',
    'vulnerability',
}

stix_sros = {
    'sighting',
    'relationship',
}

stix_observables = {
    'artifact',
    'autonomous-system',
    'directory',
    'domain-name',
    'email-addr',
    'email-message',
    'file',
    'ipv4-addr',
    'ipv6-addr',
    'mac-addr',
    'mutex',
    'network-traffic',
    'process',
    'software',
    'url',
    'user-account',
    'windows-registry-key',
    'x509-certificate',
}

stix_all = set().union(stix_sdos, stix_sros, stix_observables)

@s_stormtypes.registry.registerType
class StixBundle(s_stormtypes.Prim):

    _storm_typename = 'storm:stix:bundle'
    _storm_locals = (

        {'name': 'add', 'desc': '''
        Make one or more STIX objects from a node, and add it to the bundle.

        Examples:
            Example Storm which would be called remotely via the ``callStorm()`` API::

                init { $bundle = $lib.stix.bundle() }
                #aka.feye.thr.apt1
                $bundle.add($node)
                fini { return($bundle) }
            ''',
         'type': {'type': 'function', '_funcname': 'add',
                  'args': (
                      {'name': 'node', 'desc': 'The node to make a STIX object from.', 'type': 'node'},
                      {'name': 'stixtype', 'type': 'str', 'default': None,
                       'desc': 'The explicit name of the STIX type to map the node to. This will override the default'
                               ' mapping.', },
                  ),
                  'returns': {'type': 'str', 'desc': 'The stable STIX id of the added object.'}}},

        {'name': 'pack', 'desc': 'Return the bundle as a STIX JSON object.',
         'type': {'type': 'function', '_funcname': 'pack',
                  'args': (),
                  'returns': {'type': 'dict', }}},

    )

    def __init__(self, libstix, runt, config, path=None):

        s_stormtypes.Prim.__init__(self, 'bundle', path=path)

        self.runt = runt
        self.libstix = libstix
        self.config = config
        self.locls.update(self.getObjLocals())
        self.objs = {}  # id -> STIX obj(dict)
        self.maxsize = config.get('maxsize', 10000)

    async def value(self):
        return self.pack()

    def getObjLocals(self):
        return {
            'add': self.add,
            'pack': self.pack,
        }

    # TODO config modification helpers
    #async def addPropMap(self, formname, stixtype, propname, stormtext):
    #async def addRelsMap(self, formname, stixtype, relname, targtype,  stormtext):

    async def add(self, node, stixtype=None):

        if len(self.objs) >= self.maxsize:
            mesg = f'STIX Bundle is at maxsize ({self.maxsize}).'
            raise s_exc.StormRuntimeError(mesg=mesg)

        if not isinstance(node, s_node.Node):
            await self.runt.warnonce('STIX bundle add() method requires a node.')
            return None

        formconf = self.config['forms'].get(node.form.name)
        if formconf is None:
            await self.runt.warnonce('STIX bundle has no config for mapping {node.form.name}.')
            return None

        if stixtype is None:
            stixtype = formconf.get('default')

        # cyber observables have UUIDv5 the rest have UUIDv4
        if stixtype in stix_observables:
            stixid = f'{stixtype}--{uuid5(node.ndef)}'
        else:
            stixid = f'{stixtype}--{uuid4(node.ndef)}'

        if self.objs.get(stixid) is not None:
            return stixid

        stixconf = formconf['stix'].get(stixtype)
        if stixconf is None:
            await self.runt.warnonce(f'STIX bundle config has no config to map {node.form.name} to {stixtype}.')
            return None

        stixitem = self.objs.get(stixid)
        if stixitem is None:
            stixitem = self.objs[stixid] = self._initStixItem(stixid, stixtype, node)

        props = stixconf.get('props')
        if props is not None:

            for name, storm in props.items():
                valu = await self._callStorm(storm, node)
                if valu is s_common.novalu:
                    continue

                stixitem[name] = valu

        for (relname, reltype, relstorm) in stixconf.get('rels', ()):
            async for relnode, relpath in node.storm(self.runt, relstorm):
                n2id = await self.add(relnode, stixtype=reltype)
                await self._addRel(stixid, relname, n2id)

        return stixid

    def _initStixItem(self, stixid, stixtype, node):
        retn = {
            'id': stixid,
            'type': stixtype,
            'spec_version': '2.1',
        }
        return retn

    async def _addRel(self, srcid, reltype, targid):

        stixid = f'relationship--{uuid4((srcid, reltype, targid))}'
        tstamp = self.libstix.timestamp(s_common.now())

        obj = {
            'id': stixid,
            'type': 'relationship',
            'relationship_type': reltype,
            'created': tstamp,
            'modified': tstamp,
            'source_ref': srcid,
            'target_ref': targid,
            'spec_version': '2.1',
        }

        self.objs[stixid] = obj
        return stixid

    def pack(self):
        bundle = {
            'type': 'bundle',
            'id': f'bundle--{uuid4()}',
            'objects': list(self.objs.values())
        }
        return bundle

    async def _callStorm(self, text, node):

        opts = {'vars': {'bundle': self}}
        query = self.runt.snap.core.getStormQuery(text)
        async with self.runt.getSubRuntime(query, opts=opts) as runt:

            async def genr():
                yield node, runt.initPath(node)

            try:
                async for _ in runt.execute(genr=genr()):
                    await asyncio.sleep(0)
            except s_stormctrl.StormReturn as e:
                return await s_stormtypes.toprim(e.item)

        return s_common.novalu
