import uuid
import asyncio
import logging
import datetime

import regex

import synapse.exc as s_exc
import synapse.common as s_common
import synapse.lib.coro as s_coro
import synapse.lib.node as s_node
import synapse.lib.msgpack as s_msgpack
import synapse.lib.schemas as s_schemas
import synapse.lib.stormctrl as s_stormctrl
import synapse.lib.stormtypes as s_stormtypes

import stix2validator

logger = logging.getLogger(__name__)

def uuid5(valu=None):
    guid = s_common.guid(valu=valu)
    return str(uuid.UUID(guid, version=5))

def uuid4(valu=None):
    guid = s_common.guid(valu=valu)
    return str(uuid.UUID(guid, version=4))

stixtype_re = regex.compile('^[a-z0-9-]{3,250}$')

SYN_STIX_EXTENSION_ID = f'extension-definition--{uuid4("bf1c0a4d90ee557ac05055385971f17c")}'

_DefaultConfig = {

    'maxsize': 10000,

    'custom': {
        'objects': {
        },
    },

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
                        ('targets', 'vulnerability', '-> risk:attack :used:vuln -> risk:vuln'),
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
                            init { $list = () }
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
                            init { $goals = () }
                            -> ou:campaign:org -> ou:goal | uniq | +:name $goals.append(:name)
                            fini { if $goals { return($goals) } }
                        ''',
                    },
                    'rels': (
                        ('attributed-to', 'identity', ''),
                        ('located-at', 'location', ':hq -> geo:place'),
                        ('targets', 'identity', '-> ou:campaign -> risk:attack :target:org -> ou:org'),
                        ('targets', 'vulnerability', '-> ou:campaign -> risk:attack :used:vuln -> risk:vuln'),
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
                            init { $refs = () }
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
                            init { $dict = ({}) }
                            { +:md5 $dict.MD5 = :md5 }
                            { +:sha1 $dict."SHA-1" = :sha1 }
                            { +:sha256 $dict."SHA-256" = :sha256 }
                            { +:sha512 $dict."SHA-512" = :sha512 }
                            fini { if $dict { return($dict) } }
                        ''',
                        'mime_type': '+:mime return(:mime)',
                        'contains_refs': '''
                            init { $refs = () }
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
                            init { $refs = () }
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
                            init { $refs = () }
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

        'risk:vuln': {
            'default': 'vulnerability',
            'stix': {
                'vulnerability': {
                    'props': {
                        'name': '{+:name return (:name)} return ($node.repr())',
                        'description': 'if (:desc) { return (:desc) }',
                        'created': 'return($lib.stix.export.timestamp(.created))',
                        'modified': 'return($lib.stix.export.timestamp(.created))',
                        'external_references': 'if :cve { $cve=:cve $cve=$cve.upper() return(([{"source_name": "cve", "external_id": $cve}])) }'
                    },
                    'rels': (

                    ),
                }
            }
        },

        'ou:technique': {
            'default': 'attack-pattern',
            'stix': {
                'attack-pattern': {
                    'props': {
                        'name': '{ +:name return(:name) } return($node.repr())',
                        'description': '+:desc return(:desc)',
                    },
                    'revs': (
                        ('mitigates', 'course-of-action', '<(addresses)- risk:mitigation'),
                    ),
                },
            },
        },

        'risk:mitigation': {
            'default': 'course-of-action',
            'stix': {
                'course-of-action': {
                    'props': {
                        'name': '{ +:name return(:name) } return($node.repr())',
                        'description': '+:desc return(:desc)',
                    },
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
                            init { $refs = () }
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

perm_maxsize = ('storm', 'lib', 'stix', 'export', 'maxsize')
def _validateConfig(runt, config):

    core = runt.snap.core

    maxsize = config.get('maxsize', 10000)

    alltypes = stix_all.copy()

    custom = config.get('custom')
    if custom is not None:
        objdefs = custom.get('objects')
        if objdefs is not None:
            for name, info in objdefs.items():
                if not stixtype_re.match(name):
                    mesg = 'Invalid custom STIX type name. Must match regex: ^[a-z0-9-]{3,250}$'
                    raise s_exc.BadConfValu(mesg=mesg)
                alltypes.add(name)

    if not isinstance(maxsize, int):
        mesg = f'STIX Bundle config maxsize option must be an integer.'
        raise s_exc.BadConfValu(mesg=mesg)

    if maxsize > 10000 and not runt.allowed(perm_maxsize):
        permstr = '.'.join(perm_maxsize)
        mesg = f'Setting STIX export maxsize > 10,000 requires permission: {permstr}'
        raise s_exc.AuthDeny(mesg=mesg, perm=permstr)

    formmaps = config.get('forms')
    if formmaps is None:
        mesg = f'STIX Bundle config is missing "forms" mappings.'
        raise s_exc.NeedConfValu(mesg=mesg)

    for formname, formconf in formmaps.items():
        form = core.model.form(formname)
        if form is None:
            mesg = f'STIX Bundle config contains invalid form name {formname}.'
            raise s_exc.NoSuchForm.init(formname, mesg=mesg)

        stixdef = formconf.get('default')
        if stixdef is None:
            mesg = f'STIX Bundle config is missing default mapping for form {formname}.'
            raise s_exc.NeedConfValu(mesg=mesg)

        if stixdef not in alltypes:
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

            if stixtype not in alltypes:
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

            stixrevs = stixinfo.get('revs')
            if stixrevs is not None:
                for stixrev in stixrevs:
                    if len(stixrev) != 3:
                        mesg = f'STIX Bundle config has invalid rev entry {formname} {stixtype} {stixrev}.'
                        raise s_exc.BadConfValu(mesg=mesg)

            stixpivs = stixinfo.get('pivots')
            if stixpivs is not None:
                for stixpiv in stixpivs:

                    if not isinstance(stixpiv.get('storm'), str):
                        raise s_exc.BadConfValu(mesg=f'Pivot for {formname} (as {stixtype}) has invalid/missing storm field.')

                    pivtype = stixpiv.get('stixtype')
                    if isinstance(pivtype, str):
                        if pivtype not in alltypes:
                            mesg = f'STIX Bundle config has unknown pivot STIX type {pivtype} for form {formname}.'
                            raise s_exc.BadConfValu(mesg=mesg)

def validateStix(bundle, version='2.1'):
    ret = {
        'ok': False,
        'mesg': '',
        'result': {},
    }
    bundle = s_msgpack.deepcopy(bundle, use_list=True)
    opts = stix2validator.ValidationOptions(strict=True, version=version)
    try:
        results = stix2validator.validate_parsed_json(bundle, options=opts)
    except stix2validator.ValidationError as e:
        logger.exception('Error validating STIX bundle.')
        ret['mesg'] = f'Error validating bundle: {e}'
    else:
        ret['result'] = results.as_dict()
        ret['ok'] = bool(results.is_valid)
    return ret

@s_stormtypes.registry.registerLib
class LibStix(s_stormtypes.Lib):
    '''
    A Storm Library for interacting with Stix Version 2.1 CS02.
    '''
    _storm_locals = (  # type: ignore
        {
            'name': 'validate', 'desc': '''
            Validate a STIX Bundle.

            Notes:
                This returns a dictionary containing the following values::

                    {
                        'ok': <boolean> - False if bundle is invalid, True otherwise.
                        'mesg': <str> - An error message if there was an error when validating the bundle.
                        'results': The results of validating the bundle.
                    }
            ''',
            'type': {
                'type': 'function', '_funcname': 'validateBundle',
                'args': (
                    {'type': 'dict', 'name': 'bundle', 'desc': 'The stix bundle to validate.'},
                ),
                'returns': {'type': 'dict', 'desc': 'Results dictionary.'}
            }
        },
        {
        'name': 'lift', 'desc': '''
        Lift nodes from a STIX Bundle made by Synapse.

        Notes:
            This lifts nodes using the Node definitions embedded into the bundle when created by Synapse using
            custom extension properties.

        Examples:
            Lifting nodes from a STIX bundle::

                yield $lib.stix($bundle)
        ''',
            'type': {
                'type': 'function', '_funcname': 'liftBundle',
                'args': (
                    {'type': 'dict', 'name': 'bundle', 'desc': 'The STIX bundle to lift nodes from.'},
                ),
                'returns': {'name': 'Yields', 'type': 'node', 'desc': 'Yields nodes'}
            }
        },
    )
    _storm_lib_path = ('stix', )

    def getObjLocals(self):
        return {
            'lift': self.liftBundle,
            'validate': self.validateBundle,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def validateBundle(self, bundle):
        bundle = await s_stormtypes.toprim(bundle)
        return await s_coro.semafork(validateStix, bundle)

    @s_stormtypes.stormfunc(readonly=True)
    async def liftBundle(self, bundle):
        bundle = await s_stormtypes.toprim(bundle)

        for obj in bundle.get('objects', ()):
            exts = obj.get('extensions')
            if not exts:
                continue
            synx = exts.get(SYN_STIX_EXTENSION_ID)
            if not synx:  # pragma: no cover
                continue
            ndef = synx.get('synapse_ndef')
            if not ndef:  # pragma: no cover
                continue
            node = await self.runt.snap.getNodeByNdef(ndef)
            if node:
                yield node

stixingest = {
    'addbundle': True,
    'bundle': {
        'storm': '''
            it:sec:stix:bundle:id=$bundle.id
            return($node)
            [ it:sec:stix:bundle=* :id=$bundle.id ]
            return($node)
        ''',
    },
    'objects': {
        'intrusion-set': {
            'storm': '''
                ($ok, $name) = $lib.trycast(ou:name, $object.name)
                if $ok {

                    ou:name=$name -> ou:org
                    { for $alias in $object.aliases { [ :names?+=$alias ] } }
                    return($node)

                    [ ou:org=* :name=$name ]
                    { for $alias in $object.aliases { [ :names?+=$alias ] } }
                    return($node)
                }
            ''',
        },
        'identity': {
            'storm': '''
                switch $object.identity_class {
                    group: {[ ps:contact=(stix, identity, $object.id) :orgname?=$object.name ]}
                    organization: {[ ps:contact=(stix, identity, $object.id) :orgname?=$object.name ]}
                    individual: {[ ps:contact=(stix, identity, $object.id) :name?=$object.name ]}
                    system: {[ it:host=(stix, identity, $object.id) :name?=$object.name ]}
                }
            ''',
        },
        'tool': {
            'storm': '''
                ($ok, $name) = $lib.trycast(it:prod:softname, $object.name)
                if $ok {
                    it:prod:softname=$name -> it:prod:soft
                    return($node)
                    [ it:prod:soft=* :name=$name ]
                    return($node)
                }
            ''',
        },
        'threat-actor': {
            'storm': '''
                [ ps:contact=(stix, threat-actor, $object.id)
                    :name?=$object.name
                    :desc?=$object.description
                    :names?=$object.aliases
                ]
                $node.data.set(stix:object, $object)
                return($node)
            ''',
        },
        'course-of-action': {
            'storm': '''
                [ risk:mitigation=(stix, course-of-action, $object.id)
                    :name?=$object.name
                    :desc?=$object.description
                ]
                $node.data.set(stix:object, $object)
                return($node)
            ''',
        },
        'campaign': {
            'storm': '''
                [ ou:campaign=(stix, campaign, $object.id)
                    :name?=$object.name
                    :desc?=$object.description
                    .seen?=$object.last_seen
                    .seen?=$object.first_seen
                ]
                $node.data.set(stix:object, $object)
                return($node)
            ''',
        },
        'malware': {
            'storm': '''
                ($ok, $name) = $lib.trycast(it:prod:softname, $object.name)
                if $ok {
                    it:prod:softname=$name -> it:prod:soft
                    return($node)
                    [ it:prod:soft=* :name=$name ]
                    return($node)
                }
            ''',
        },
        'indicator': {
            'storm': '''
                $guid = $lib.guid(stix, indicator, $object.id)
                switch $object.pattern_type {

                    yara: {[ it:app:yara:rule=$guid
                                :name?=$object.name
                                :text?=$object.pattern
                    ]}

                    snort: {[ it:app:snort:rule=$guid
                                :name?=$object.name
                                :text?=$object.pattern
                    ]}

                    *: {[ it:sec:stix:indicator=$guid
                            :name?=$object.name
                            :pattern?=$object.pattern
                            :created?=$object.created
                            :updated?=$object.modified]
                       | scrape --refs :pattern
                       }
                }
                $node.data.set(stix:object, $object)
                return($node)
            ''',
        },
        'report': {
            'storm': '''
                [ media:news=(stix, report, $object.id)
                    :title?=$object.name
                    :summary?=$object.description
                    :published?=$object.published
                ]
                $node.data.set(stix:object, $object)
                return($node)
            ''',
        },
    },
    'relationships': (

        {'type': ('campaign', 'attributed-to', 'intrusion-set'), 'storm': '''
            $n1node.props.org = $n2node
        '''},

        # this relationship is backwards in the STIX model
        {'type': ('intrusion-set', 'attributed-to', 'threat-actor'), 'storm': '''
            $n2node.props.org = $n1node
        '''},

        {'type': (None, 'uses', None), 'storm': 'yield $n1node [ +(uses)> { yield $n2node } ]'},
        {'type': (None, 'indicates', None), 'storm': 'yield $n1node [ +(indicates)> { yield $n2node } ]'},

        # nothing to do... they are the same for us...
        {'type': ('threat-actor', 'attributed-to', 'identity'), 'storm': ''}
    ),
}

@s_stormtypes.registry.registerLib
class LibStixImport(s_stormtypes.Lib):
    '''
    A Storm Library for importing Stix Version 2.1 data.
    '''
    _storm_lib_path = ('stix', 'import')

    _storm_locals = (  # type: ignore
        {
            'name': 'config', 'desc': '''
            Return an editable copy of the default STIX ingest config.
            ''',
            'type': {
                'type': 'function', '_funcname': 'config',
                'returns': {'type': 'dict', 'desc': 'A copy of the default STIX ingest configuration.'},
            },
        },
        {
            'name': 'ingest', 'desc': '''
            Import nodes from a STIX bundle.
            ''',
            'type': {
                'type': 'function', '_funcname': 'ingest',
                'args': (
                    {'type': 'dict', 'name': 'bundle', 'desc': 'The STIX bundle to ingest.'},
                    {'type': 'dict', 'name': 'config', 'default': None, 'desc': 'An optional STIX ingest configuration.'},
                ),
                'returns': {'name': 'Yields', 'type': 'node', 'desc': 'Yields nodes'}
            },
        },
    )

    def getObjLocals(self):
        return {
            'config': self.config,
            'ingest': self.ingest,
        }

    @s_stormtypes.stormfunc(readonly=True)
    async def config(self):
        return s_msgpack.deepcopy(stixingest, use_list=True)

    async def ingest(self, bundle, config=None):

        if config is None:
            config = stixingest

        bundle = await s_stormtypes.toprim(bundle)
        config = await s_stormtypes.toprim(config)

        if not isinstance(config, dict):
            mesg = 'STIX ingest config must be a dictionary.'
            raise s_exc.BadArg(mesg=mesg)

        config.setdefault('bundle', {})
        config.setdefault('objects', {})
        config.setdefault('relationships', [])

        try:
            rellook = {r['type']: r for r in config.get('relationships', ())}
        except Exception as e:
            mesg = f'Error processing relationships in STIX bundle ingest config: {e}.'
            raise s_exc.BadArg(mesg=mesg)

        bundlenode = None

        bundleconf = config.get('bundle')
        if bundleconf is None:
            bundleconf = {}

        if not isinstance(bundleconf, dict):
            mesg = 'STIX ingest config bundle value must be a dictionary.'
            raise s_exc.BadArg(mesg=mesg)

        bundlestorm = bundleconf.get('storm')
        if bundlestorm:
            if not isinstance(bundlestorm, str):
                mesg = 'STIX ingest config storm query must be a string.'
                raise s_exc.BadArg(mesg=mesg)

            bundlenode = await self._callStorm(bundlestorm, {'bundle': bundle})

        self.runt.layerConfirm(('node', 'edge', 'add', 'refs'))

        config = s_schemas.reqValidStixIngestConfig(config)
        bundle = s_schemas.reqValidStixIngestBundle(bundle)

        try:
            nodesbyid = await self._ingestObjects(bundle, config, rellook)
        except Exception as e:
            mesg = f'Error processing objects in STIX bundle ingest: {e}.'
            raise s_exc.BadArg(mesg=mesg)

        if bundlenode is not None:
            for node in nodesbyid.values():
                await bundlenode.addEdge('refs', node.iden())
                await asyncio.sleep(0)
            yield bundlenode

        for node in nodesbyid.values():
            yield node

    async def _ingestObjects(self, bundle, config, rellook):

        nodesbyid = {}
        relationships = []

        for obj in bundle.get('objects', ()):

            objtype = obj.get('type')

            # do these in a second pass...
            if objtype == 'relationship':
                relationships.append(obj)
                continue

            objconf = config['objects'].get(objtype)
            if objconf is None:
                await self.runt.snap.warnonce(f'STIX bundle ingest has no object definition for: {objtype}.')
                continue

            objstorm = objconf.get('storm')
            if objstorm is None:
                continue

            try:
                node = await self._callStorm(objstorm, {'bundle': bundle, 'object': obj})
                if node is not None:
                    nodesbyid[obj.get('id')] = node
            except asyncio.CancelledError: # pragma: no cover
                raise
            except Exception as e:
                await self.runt.snap.warn(f'Error during STIX import callback for {objtype}: {e}')

        for rel in relationships:

            stixn1 = rel.get('source_ref')
            stixn2 = rel.get('target_ref')

            n1node = nodesbyid.get(stixn1)
            if n1node is None:
                await asyncio.sleep(0)
                continue

            n2node = nodesbyid.get(stixn2)
            if n2node is None:
                await asyncio.sleep(0)
                continue

            reltypes = (
                (None, rel.get('relationship_type'), None),
                (None, rel.get('relationship_type'), stixn2.split('--')[0]),
                (stixn1.split('--')[0], rel.get('relationship_type'), None),
                (stixn1.split('--')[0], rel.get('relationship_type'), stixn2.split('--')[0]),
            )

            foundone = False
            for reltype in reltypes:

                relconf = rellook.get(reltype)
                if relconf is None:
                    continue

                relstorm = relconf.get('storm')
                if relstorm is None: # pragma: no cover
                    continue

                foundone = True

                try:
                    node = await self._callStorm(relstorm, {'bundle': bundle, 'n1node': n1node, 'n2node': n2node})
                    if node is not None:
                        nodesbyid[rel.get('id')] = node
                except asyncio.CancelledError: # pragma: no cover
                    raise
                except Exception as e:
                    await self.runt.snap.warn(f'Error during STIX import callback for {reltype}: {e}')

            if not foundone:
                await self.runt.snap.warnonce(f'STIX bundle ingest has no relationship definition for: {reltype}.')

        # attempt to resolve object_refs
        for obj in bundle.get('objects', ()):

            node = nodesbyid.get(obj.get('id'))
            if node is None:
                continue

            for refid in obj.get('object_refs', ()):
                refsnode = nodesbyid.get(refid)
                if refsnode is None:
                    continue

                await node.addEdge('refs', refsnode.iden())

        return nodesbyid

    async def _callStorm(self, text, varz):

        query = await self.runt.snap.core.getStormQuery(text)
        async with self.runt.getCmdRuntime(query, opts={'vars': varz}) as runt:
            try:
                async for _ in runt.execute():
                    await asyncio.sleep(0)
            except s_stormctrl.StormReturn as e:
                return e.item

        return None

@s_stormtypes.registry.registerLib
class LibStixExport(s_stormtypes.Lib):
    '''
    A Storm Library for exporting to STIX version 2.1 CS02.
    '''
    _storm_lib_perms = (
        {'perm': ('storm', 'lib', 'stix', 'export', 'maxsize'), 'gate': 'cortex',
         'desc': 'Controls the ability to specify a STIX export bundle maxsize of greater than 10,000.'},
    )

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
                                        ),
                                        "revs": (
                                            ( <revname>, <source_stixtype>, <storm> ),
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

                You may also specify pivots on a per form+stixtype basis to automate pivoting to additional nodes
                to include in the bundle::

                    {"forms": {
                        "inet:fqdn":
                            ...
                            "domain-name": {
                                ...
                                "pivots": [
                                    {"storm": "-> inet:dns:a -> inet:ipv4", "stixtype": "ipv4-addr"}
                                ]
                            {
                        }
                    }

                Note:
                    The default config is an evolving set of mappings.  If you need to guarantee stable output please
                    specify a config.
            ''',
            'type': {
                'type': 'function', '_funcname': 'bundle',
                'args': (
                    {'type': 'dict', 'name': 'config', 'default': None, 'desc': 'The STIX bundle export config to use.'},
                ),
                'returns': {'type': 'stix:bundle', 'desc': 'A new ``stix:bundle`` instance.'},
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

    @s_stormtypes.stormfunc(readonly=True)
    async def config(self):
        # make a new mutable config
        return s_msgpack.deepcopy(_DefaultConfig, use_list=True)

    @s_stormtypes.stormfunc(readonly=True)
    async def bundle(self, config=None):

        if config is None:
            config = _DefaultConfig

        config = await s_stormtypes.toprim(config)
        _validateConfig(self.runt, config)

        return StixBundle(self, self.runt, config)

    def timestamp(self, tick):
        dt = datetime.datetime.fromtimestamp(tick / 1000.0, datetime.UTC)
        millis = int(dt.microsecond / 1000)
        return f'{dt.strftime("%Y-%m-%dT%H:%M:%S")}.{millis:03d}Z'

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
    '''
    Implements the Storm API for creating and packing a STIX bundle for v2.1
    '''

    _storm_typename = 'stix:bundle'
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

        {'name': 'size', 'desc': 'Return the number of STIX objects currently in the bundle.',
         'type': {'type': 'function', '_funcname': 'size',
                  'args': (),
                  'returns': {'type': 'int', }}},

    )

    def __init__(self, libstix, runt, config, path=None):

        s_stormtypes.Prim.__init__(self, 'bundle', path=path)

        self.runt = runt
        self.libstix = libstix
        self.config = config
        self.locls.update(self.getObjLocals())
        self.objs = {}  # id -> STIX obj(dict)
        self.synextension = config.get('synapse_extension', True)
        self.maxsize = config.get('maxsize', 10000)

    async def value(self):
        return self.pack()

    def getObjLocals(self):
        return {
            'add': self.add,
            'pack': self.pack,
            'size': self.size,
        }

    # TODO config modification helpers
    # async def addPropMap(self, formname, stixtype, propname, stormtext):
    # async def addRelsMap(self, formname, stixtype, relname, targtype,  stormtext):

    @s_stormtypes.stormfunc(readonly=True)
    async def add(self, node, stixtype=None):

        if len(self.objs) >= self.maxsize:
            mesg = f'STIX Bundle is at maxsize ({self.maxsize}).'
            raise s_exc.StormRuntimeError(mesg=mesg)

        if not isinstance(node, s_node.Node):
            await self.runt.warnonce('STIX bundle add() method requires a node.')
            return None

        formconf = self.config['forms'].get(node.form.name)
        if formconf is None:
            await self.runt.warnonce(f'STIX bundle has no config for mapping {node.form.name}.')
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

        for (revname, revtype, revstorm) in stixconf.get('revs', ()):
            async for revnode, revpath in node.storm(self.runt, revstorm):
                n1id = await self.add(revnode, stixtype=revtype)
                await self._addRel(n1id, revname, stixid)

        for pivdef in stixconf.get('pivots', ()):
            pivtype = pivdef.get('stixtype')
            async for pivnode, pivpath in node.storm(self.runt, pivdef.get('storm')):
                await self.add(pivnode, stixtype=pivtype)

        return stixid

    def _initStixItem(self, stixid, stixtype, node):
        ndef = s_msgpack.deepcopy(node.ndef, use_list=True)
        retn = {
            'id': stixid,
            'type': stixtype,
            'spec_version': '2.1',
        }
        if self.synextension:
            retn['extensions'] = {
                SYN_STIX_EXTENSION_ID: {
                    "extension_type": "property-extension",
                    'synapse_ndef': ndef
                }
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

    def _getSynapseExtensionDefinition(self):
        ret = {
            'id': SYN_STIX_EXTENSION_ID,
            'type': 'extension-definition',
            'spec_version': '2.1',
            'name': 'Vertex Project Synapse',
            'description': 'Synapse specific STIX 2.1 extensions.',
            'created': '2021-04-29T13:40:00.000Z',
            'modified': '2021-04-29T13:40:00.000Z',
            'schema': 'The Synapse Extensions for Stix 2.1',
            'version': '1.0',
            'extension_types': [
                'property-extension',
            ],
        }
        return ret

    @s_stormtypes.stormfunc(readonly=True)
    def pack(self):
        objects = list(self.objs.values())
        if self.synextension:
            objects.insert(0, self._getSynapseExtensionDefinition())
        bundle = {
            'type': 'bundle',
            'id': f'bundle--{uuid4()}',
            'objects': objects
        }
        return bundle

    @s_stormtypes.stormfunc(readonly=True)
    def size(self):
        return len(self.objs)

    async def _callStorm(self, text, node):

        varz = self.runt.getScopeVars()
        varz['bundle'] = self

        opts = {'vars': varz}
        query = await self.runt.snap.core.getStormQuery(text)
        async with self.runt.getCmdRuntime(query, opts=opts) as runt:

            async def genr():
                yield node, runt.initPath(node)

            try:
                async for _ in runt.execute(genr=genr()):
                    await asyncio.sleep(0)
            except s_stormctrl.StormReturn as e:
                return await s_stormtypes.toprim(e.item)

        return s_common.novalu
