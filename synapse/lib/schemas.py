import synapse.lib.const as s_const
import synapse.lib.config as s_config
import synapse.lib.grammar as s_grammar
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

easyPermSchema = {
    'type': 'object',
    'properties': {
        # users and roles are keyed by iden, so their key space stays open.
        'users': {
            'type': 'object',
            'items': {'type': 'number', 'minimum': 0, 'maximum': 3},
            'additionalProperties': True,
        },
        'roles': {
            'type': 'object',
            'items': {'type': 'number', 'minimum': 0, 'maximum': 3},
            'additionalProperties': True,
        },
        'default': {'type': 'number', 'minimum': 0, 'maximum': 3},
    },
    'additionalProperties': False,
    'required': ['users', 'roles'],
}

_HttpExtAPIConfSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'methods': {
            'type': 'object',
            'default': {},
            'properties': {
                'get': {'type': 'string', 'minLength': 1},
                'head': {'type': 'string', 'minLength': 1},
                'post': {'type': 'string', 'minLength': 1},
                'put': {'type': 'string', 'minLength': 1},
                'delete': {'type': 'string', 'minLength': 1},
                'patch': {'type': 'string', 'minLength': 1},
                'options': {'type': 'string', 'minLength': 1},
            },
            'additionalProperties': False,
        },
        'authenticated': {'type': 'boolean', 'default': True},
        'name': {'type': 'string', 'default': ''},
        'desc': {'type': 'string', 'default': ''},
        'path': {'type': 'string', 'minLength': 1},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'runas': {'type': 'string', 'pattern': '^(owner|user)$'},
        'owner': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'updated': {'type': 'integer', 'minimum': 0},
        'readonly': {'type': 'boolean', 'default': False},
        'perms': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'perm': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}},
                    'default': {'type': 'boolean', 'default': False},
                },
                'additionalProperties': False,
            },
            'default': [],
        },
        # vars are caller defined Storm variables, so the keys are open by design.
        'vars': {'type': 'object', 'default': {}, 'additionalProperties': True}

    },
    'additionalProperties': False
}

reqValidHttpExtAPIConf = s_config.getJsValidator(_HttpExtAPIConfSchema)

layerPushPullSchema = {
    'type': 'object',
    'properties': {
        'url': {'type': 'string'},
        'time': {'type': 'number'},
        'soffs': {'type': 'number', 'minimum': 0},
        'offs': {'type': 'number'},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'queue:size': {'type': 'integer', 'default': s_const.layer_pdef_qsize,
                       'minimum': 1, 'maximum': s_const.layer_pdef_qsize_max},
        'chunk:size': {'type': 'integer', 'default': s_const.layer_pdef_csize,
                       'minimum': 1, 'maximum': s_const.layer_pdef_csize_max}

    },
    'additionalProperties': False,
    'required': ['iden', 'url', 'user', 'time'],
}
reqValidPush = s_config.getJsValidator(layerPushPullSchema)
reqValidPull = reqValidPush

loglevelSchema = {'type': 'string', 'enum': list(s_const.LOG_LEVEL_CHOICES.keys())}
reqValidLoglevel = s_config.getJsValidator(loglevelSchema)

_CronJobSchema = {
    'type': 'object',
    'properties': {
        'storm': {'type': 'string', 'minLength': 1},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'affinity': {'type': ['string', 'null']},
        'doc': {'type': 'string'},
        'indx': {'type': 'integer'},
        'errcount': {'type': 'integer'},
        'startcount': {'type': 'integer'},
        'lasterrs': {'type': 'array', 'items': {'type': 'string'}},
        'recs': {'type': 'array'},
        'recur': {'type': 'boolean'},
        'enabled': {'type': 'boolean'},
        'isrunning': {'type': 'boolean'},
        'nexttime': {'type': ['integer', 'null']},
        'laststarttime': {'type': ['integer', 'null']},
        'lastfinishtime': {'type': ['integer', 'null']},
        'lastresult': {'type': ['string', 'null']},
        'loglevel': s_msgpack.deepcopy(loglevelSchema),
        'incunit': {
            'oneOf': [
                {'type': 'null'},
                {'enum': ['year', 'month', 'dayofmonth', 'dayofweek', 'day', 'hour', 'minute']}
            ]
        },
        'incvals': {
            'type': ['array', 'number', 'null'],
            'items': {'type': 'number'}
        },
        'reqs': {
            'oneOf': [
                {
                    '$ref': '#/definitions/req',
                },
                {
                    'type': ['array'],
                    'items': {'$ref': '#/definitions/req'},
                },
            ]
        },
    },
    'additionalProperties': False,
    'required': ['creator', 'storm', 'user'],
    'dependencies': {
        'incvals': ['incunit'],
        'incunit': ['incvals'],
    },
    'definitions': {
        # the keys are the lower cased synapse.lib.agenda.TimeUnit names, since
        # agenda resolves each one with TimeUnit.fromString().
        'req': {
            'type': 'object',
            'properties': {
                'minute': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'hour': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'day': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'dayofweek': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'dayofmonth': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'month': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'year': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                # "run once, immediately" - only valid on a non recurring job.
                'now': {'type': 'boolean'},
            },
            'additionalProperties': False,
        }
    }
}

reqValidCronDef = s_config.getJsValidator(_CronJobSchema)
vaultSchema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string', 'minLength': 1, 'maxLength': 128},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'type': {'type': 'string', 'minLength': 1, 'maxLength': 128},
        'scope': {'type': ['string', 'null'], 'enum': [None, 'user', 'role', 'global']},
        'owner': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'permissions': s_msgpack.deepcopy(easyPermSchema),
        # a vault type schema declares the shape of these two sections; an untyped
        # vault, or a type with no schema, leaves them open. See getVaultSchema().
        'secrets': {'type': 'object', 'additionalProperties': True},
        'configs': {'type': 'object', 'additionalProperties': True},
        'type:version': {'type': 'integer', 'minimum': 0},
    },
    'additionalProperties': False,
    'required': [
        'iden',
        'name',
        'type',
        'scope',
        'owner',
        'permissions',
        'secrets',
        'configs',
    ],
}
reqValidVault = s_config.getJsValidator(vaultSchema)

# the only sections a vault type schema may describe. The rest of a vault def is
# owned by vaultSchema, so a type schema never restates or overrides a base field.
vaultTypeSections = ('configs', 'secrets')

def getVaultSchema(typeschema):
    '''
    Merge a vault type schema into the base vault schema.

    A vault type describes the shape of the "configs" and "secrets" sections and
    nothing else; the surrounding vault def is described by vaultSchema. Only those
    two sections are taken, so a type schema cannot widen or redefine a base field
    even if it declares one. Vault type registration rejects such a schema outright
    (see Cortex._reqValidVaultTypeDef).

    Args:
        typeschema (dict): The schema declared by a vault type.

    Returns:
        dict: A JSON schema for a whole vault def of that type.
    '''
    schema = s_msgpack.deepcopy(vaultSchema, use_list=True)

    props = typeschema.get('properties')
    if props is not None:

        configs = props.get('configs')
        if configs is not None:
            schema['properties']['configs'] = s_msgpack.deepcopy(configs, use_list=True)

        secrets = props.get('secrets')
        if secrets is not None:
            schema['properties']['secrets'] = s_msgpack.deepcopy(secrets, use_list=True)

    # carry definitions across so a section may use $ref
    defs = typeschema.get('definitions')
    if defs is not None:
        schema['definitions'] = s_msgpack.deepcopy(defs, use_list=True)

    defs = typeschema.get('$defs')
    if defs is not None:
        schema['$defs'] = s_msgpack.deepcopy(defs, use_list=True)

    return schema

reqValidVaultType = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'name': {'type': 'string', 'minLength': 1, 'maxLength': 128},
        'version': {'type': 'integer', 'minimum': 0},
        # an opaque JSON schema blob; validated at type registration.
        'schema': {'type': ['object', 'null'], 'default': None, 'additionalProperties': True},
        'migration': {'type': ['string', 'null'], 'default': None},
    },
    'additionalProperties': False,
    'required': ['name', 'version'],
})

reqValidView = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'parent': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'protected': {'type': 'boolean', 'default': False},
        'merging': {'type': 'boolean'},
        'layers': {
            'type': 'array',
            'items': {'type': 'string', 'pattern': s_config.re_iden},
            'minItems': 1,
            'uniqueItems': True
        },
        'quorum': {
            'type': 'object',
            'properties': {
                'roles': {'type': 'array', 'items': {
                    'type': 'string',
                    'pattern': s_config.re_iden},
                    'uniqueItems': True
                },
                'count': {'type': 'number', 'minimum': 1},
            },
            'required': ['count', 'roles'],
            'additionalProperties': False,
        },
    },
    'additionalProperties': False,
    'required': ['iden', 'parent', 'creator', 'layers'],
})

reqValidMerge = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'number', 'minimum': 0},
        'comment': {'type': 'string'},
        'updated': {'type': 'number', 'minimum': 0},
    },
    'required': ['iden', 'creator', 'created'],
    'additionalProperties': False,
})

reqValidVote = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        # -1 is a valid offset, matching Layer.getEditIndx()'s empty-layer sentinel.
        'offset': {'type': 'number', 'minimum': -1},
        'created': {'type': 'number', 'minimum': 0},
        'approved': {'type': 'boolean'},
        'comment': {'type': 'string'},
        'updated': {'type': 'number', 'minimum': 0},
    },
    'required': ['user', 'offset', 'created', 'approved'],
    'additionalProperties': False,
})

reqValidLeadTerm = s_config.getJsValidator({
    'type': 'object', 'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string', 'minLength': 1},
        'nexsoffs': {'type': 'integer', 'minimum': 0},
        'created': {'type': 'integer', 'minimum': 0},
        'id': {'type': 'integer', 'minimum': 0},
    },
    'additionalProperties': False,
    'required': ['iden', 'name', 'nexsoffs', 'created', 'id'],
})

# AHA provisioning discovery messages are enveloped as
# {'type': <msgtype>, 'data': <type-specific-data>}.

# A 'service' request auto-provisions a normal service of the named type.
_provServiceReqSchema = {
    'type': 'object',
    'properties': {
        'type': {'const': 'service'},
        'data': {
            'type': 'object',
            'properties': {
                'type': {'type': 'string', 'minLength': 1},
            },
            'required': ['type'],
            'additionalProperties': False,
        },
    },
    'required': ['type', 'data'],
    'additionalProperties': False,
}

# An 'aha' request enrolls the sender as a clone of the leader AHA service.
_provAhaReqSchema = {
    'type': 'object',
    'properties': {
        'type': {'const': 'aha'},
        'data': {
            'type': 'object',
            'properties': {
                'host': {'type': 'string', 'minLength': 1},
                'port': {'type': 'integer', 'minimum': 1, 'maximum': 65535},
            },
            'required': ['host'],
            'additionalProperties': False,
        },
    },
    'required': ['type', 'data'],
    'additionalProperties': False,
}

_provReqSchema = {'oneOf': [_provServiceReqSchema, _provAhaReqSchema]}
reqValidProvRequest = s_config.getJsValidator(_provReqSchema)

_provRespSchema = {
    'type': 'object',
    'properties': {
        'type': {'const': 'retn'},
        # an ( ok, data ) retn tuple; intentionally unconstrained here.
        'data': {},
    },
    'required': ['type', 'data'],
    'additionalProperties': False,
}
reqValidProvResponse = s_config.getJsValidator(_provRespSchema)

_cellUserApiKeySchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'updated': {'type': 'integer', 'minimum': 0},
        'expires': {'type': 'integer', 'minimum': 1},
        # the shadow struct is versioned and owned by synapse.lib.crypto.passwd,
        # so its shape is left opaque here.
        'shadow': {
            'type': 'object',
            'additionalProperties': True,
        },
    },
    'additionalProperties': False,
    'required': [
        'iden',
        'name',
        'user',
        'created',
        'updated',
        'shadow',
    ],
}
reqValidUserApiKeyDef = s_config.getJsValidator(_cellUserApiKeySchema)

_sslCtxOptsSchema = {
    'type': 'object',
    'properties': {
        'verify': {'type': 'boolean', 'default': True},
        'client_cert': {'type': ['string', 'null'], 'default': None},
        'client_key': {'type': ['string', 'null'], 'default': None},
        'ca_cert': {'type': ['string', 'null'], 'default': None},
    },
    'additionalProperties': False,
}
reqValidSslCtxOpts = s_config.getJsValidator(_sslCtxOptsSchema)

_authRulesSchema = {
    'type': 'array',
    'items': {
        'type': 'array',
        'items': [
            {'type': 'boolean'},
            {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'minLength': 1,
                    'pattern': '^[^.]+$'
                },
                'minItems': 1
            },
        ],
        'minItems': 2,
        'maxItems': 2,
    },
}
reqValidRules = s_config.getJsValidator(_authRulesSchema)

_passwdPolicySchema = {
    'type': 'object',
    'properties': {
        'complexity': {
            'type': ['object', 'null'],
            'properties': {
                'length': {
                    'type': ['number', 'null'],
                    'minimum': 1,
                    'description': 'Minimum password character length.',
                },
                'sequences': {
                    'type': ['number', 'null'],
                    'minimum': 2,
                    'description': 'Maximum sequence length in a password. Sequences can be letters or number, forward or reverse.',
                },
                'upper:count': {
                    'type': ['number', 'null'],
                    'description': 'The minimum number of uppercase characters required in password.',
                },
                'upper:valid': {
                    'type': ['string', 'null'],
                    'minLength': 1,
                    'description': 'All valid uppercase characters.',
                },
                'lower:count': {
                    'type': ['number', 'null'],
                    'minimum': 0,
                    'description': 'The minimum number of lowercase characters required in password.',
                },
                'lower:valid': {
                    'type': ['string', 'null'],
                    'minLength': 1,
                    'description': 'All valid lowercase characters.',
                },
                'special:count': {
                    'type': ['number', 'null'],
                    'minimum': 0,
                    'description': 'The minimum number of special characters required in password.',
                },
                'special:valid': {
                    'type': ['string', 'null'],
                    'minLength': 1,
                    'description': 'All valid special characters.',
                },
                'number:count': {
                    'type': ['number', 'null'],
                    'minimum': 0,
                    'description': 'The minimum number of digit characters required in password.',
                },
                'number:valid': {
                    'type': ['string', 'null'],
                    'minLength': 1,
                    'description': 'All valid digit characters.',
                },
            },
            'additionalProperties': False,
        },
        'attempts': {
            'type': ['number', 'null'],
            'minimum': 1,
            'description': 'Maximum number of incorrect attempts before locking user account.',
        },
        'previous': {
            'type': ['number', 'null'],
            'minimum': 1,
            'description': 'Number of previous passwords to disallow.',
        },
    },
    'additionalProperties': False,
}
reqValidPasswdPolicy = s_config.getJsValidator(_passwdPolicySchema)

tabularConfSchema = {
    'type': 'object',
    'properties': {
        'separators': {
            'type': 'object',
            'properties': {
                'row:outline': {'type': 'boolean', 'default': False,
                                'description': 'Add the row separator before the header data and after each row.'},
                'column:outline': {'type': 'boolean', 'default': False,
                                   'description': 'Add the column separator to the beginning and end of each row.'},
                'header:row': {'type': 'string', 'default': '=',
                               'description': 'The string to use to create a separator row when printing the header.'},
                'data:row': {'type': 'string', 'default': '-',
                             'description': 'The string to use to create a separator row when printing data rows.'},
                'column': {'type': 'string', 'default': '|',
                           'description': 'The string to use to separate columns.'},
            },
            'additionalProperties': False,
        },
        'columns': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string',
                             'description': 'The column name which will be used in the header row.'},
                    'width': {'type': 'number', 'default': None, 'exclusiveMinimum': 0,
                              'description': 'If not provided each cell will expand to fit the data.'},
                    'justify': {'type': 'string', 'default': 'left', 'enum': ['left', 'center', 'right'],
                                'description': 'Justification for the header titles and data rows.'},
                    'overflow': {'type': 'string', 'default': 'trim', 'enum': ['wrap', 'trim'],
                                 'description': 'For text exceeding the width, '
                                                'either wrap text in multiple lines or trim and append "...".'},
                    'newlines': {'type': 'string', 'default': 'replace', 'enum': ['replace', 'split'],
                                 'description': 'Replace newlines with a space or split into multiple lines.'
                                               'Split is only applied if width is undefined.'},
                },
                'required': ['name'],
                'minItems': 1,
                'additionalProperties': False,
            },
        },
    },
    'required': ['columns'],
    'additionalProperties': False,
}

reqValidTabularConf = s_config.getJsValidator(tabularConfSchema)

emptySchema = {'object': {}, 'additionalProperties': False}
re_drivename = r'^[\w_.-]{1,128}$'

driveInfoSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'parent': {'type': 'string', 'pattern': s_config.re_iden},
        'type': {'type': 'string', 'pattern': re_drivename},
        'name': {'type': 'string', 'pattern': re_drivename},
        'permissions': s_msgpack.deepcopy(easyPermSchema),
        'kids': {'type': 'number', 'minimum': 0},
        'created': {'type': 'number'},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        # these are also data version info...
        'size': {'type': 'number', 'minimum': 0},
        'updated': {'type': 'number'},
        'updater': {'type': 'string', 'pattern': s_config.re_iden},
        'version': {'type': 'array', 'items': {'type': 'number', 'minItems': 3, 'maxItems': 3}},
        'nexs': {'type': 'number', 'minimum': 0},
    },
    'required': ('iden', 'parent', 'name', 'created', 'creator', 'kids'),
    'additionalProperties': False,
}
reqValidDriveInfo = s_config.getJsValidator(driveInfoSchema)

driveDataVersSchema = {
    'type': 'object',
    'properties': {
        'size': {'type': 'number', 'minimum': 0},
        'updated': {'type': 'number'},
        'updater': {'type': 'string', 'pattern': s_config.re_iden},
        'version': {'type': 'array', 'items': {'type': 'number', 'minItems': 3, 'maxItems': 3}},
        # the nexus offset of the edit which produced this version of the data. It is set
        # by the nexus handler rather than the caller, since the offset is not known until
        # the edit is applied and must be the same on a mirror.
        'nexs': {'type': 'number', 'minimum': 0},
    },
    'required': ('size', 'version', 'updated', 'updater'),
    'additionalProperties': False,
}
reqValidDriveDataVers = s_config.getJsValidator(driveDataVersSchema)

stixIngestConfigSchema = {
    'type': 'object',
    'properties': {
        'addbundle': {'type': 'boolean'},
        'bundle': {
            'type': ['object', 'null'],
            'properties': {'storm': {'type': 'string'}},
            'additionalProperties': False,
        },
        # keyed by STIX object type (indicator, malware, ...) so the key space is
        # open; each value is the per-type ingest definition.
        'objects': {
            'type': 'object',
            'additionalProperties': {
                'type': 'object',
                'properties': {'storm': {'type': 'string'}},
                'additionalProperties': False,
            },
        },
        'relationships': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'array',
                        'items': {
                            'type': ['string', 'null'],
                            'minItems': 3,
                            'maxItems': 3,
                        },
                    },
                    'storm': {'type': 'string'},
                },
                'required': ['type'],
                'additionalProperties': False,
            },
        },
        'reporter': {
            'type': ['string', 'null'],
        },
    },
    'additionalProperties': False,
    'required': ['bundle', 'objects'],
}
reqValidStixIngestConfig = s_config.getJsValidator(stixIngestConfigSchema)

# Externally sourced STIX. Both this envelope and the SDOs it carries hold far more
# fields than the ingest reads, so this stays open at every level and states
# additionalProperties explicitly to keep that a decision rather than an omission.
stixIngestBundleSchema = {
    'type': 'object',
    'properties': {
        'objects': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'string'},
                    'type': {'type': 'string'},
                    'object_refs': {'type': 'array', 'items': {'type': 'string'}},
                    'relationship_type': {'type': 'string'},
                    'source_ref': {'type': 'string'},
                    'target_ref': {'type': 'string'},
                },
                'required': ['id', 'type'],
                'if': {'properties': {'type': {'const': 'relationship'}}},
                'then': {'required': ['source_ref', 'target_ref']},
                'additionalProperties': True,
            }
        },
    },
    'additionalProperties': True,
}
reqValidStixIngestBundle = s_config.getJsValidator(stixIngestBundleSchema)

_reqValidGdefSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string', 'minLength': 1},
        'desc': {'type': 'string', 'default': ''},
        'scope': {'type': 'string', 'enum': ['user', 'power-up']},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'power-up': {'type': 'string', 'minLength': 1},
        'maxsize': {'type': 'number', 'minimum': 0},
        # NIDs the caller already has. SubGraph.run() packs each one with
        # s_common.int64en(), so these are integer NIDs and not 2.x hex idens.
        'existing': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0}},
        'created': {'type': 'number'},
        'updated': {'type': 'number'},
        'refs': {'type': 'boolean', 'default': False},
        'edges': {'type': 'boolean', 'default': True},
        'edgelimit': {'type': 'number', 'default': 3000},
        'degrees': {'type': ['integer', 'null'], 'minimum': 0},
        'filterinput': {'type': 'boolean', 'default': True},
        'yieldfiltered': {'type': 'boolean', 'default': False},
        'filters': {
            'type': ['array', 'null'],
            'items': {'type': 'string'}
        },
        'pivots': {
            'type': ['array', 'null'],
            'items': {'type': 'string'}
        },
        'forms': {
            'type': 'object',
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'filters': {
                            'type': ['array', 'null'],
                            'items': {'type': 'string'}
                        },
                        'pivots': {
                            'type': ['array', 'null'],
                            'items': {'type': 'string'}
                        }
                    },
                    'additionalProperties': False,
                }
            }
        },
        'permissions': s_msgpack.deepcopy(easyPermSchema)
    },
    'additionalProperties': False,
    'required': ['iden', 'name', 'scope'],
    'allOf': [
        {
            'if': {'properties': {'scope': {'const': 'power-up'}}},
            'then': {'required': ['power-up']},
            'else': {'required': ['creator']},
        }
    ]
}
reqValidGdef = s_config.getJsValidator(_reqValidGdefSchema)

# Graph display options whose absence would change behavior at projection time.
# synapse.tools.storm.pkg.gen populates these at build time so a built package is
# explicit about them, and the Cortex fills in any which are missing on its own
# copy as the package loads. They are deliberately NOT required: a package may be
# authored at runtime via $lib.pkg.add(), and these are optional display tuning
# rather than something every author should have to spell out.
pkggraph_defaults = {name: _reqValidGdefSchema['properties'][name]['default']
                     for name in ('refs', 'edges', 'edgelimit', 'filterinput', 'yieldfiltered')}

# A package declares what a graph projection is; the Cortex derives its identity
# and provenance (iden, scope, power-up) when the package loads, so those keys
# are not author supplied. Derived from the gdef schema so the display options
# cannot drift apart.
_reqValidPkgGdefSchema = s_msgpack.deepcopy(_reqValidGdefSchema, use_list=True)
for _propname in ('iden', 'scope', 'power-up', 'creator', 'permissions', 'created', 'updated'):
    _reqValidPkgGdefSchema['properties'].pop(_propname, None)

_reqValidPkgGdefSchema['required'] = ['name']
_reqValidPkgGdefSchema.pop('allOf', None)

# The graph opt takes an inline rules dict as well as the name of a stored
# projection, and Runtime.setGraph() writes a fully resolved gdef back into the opt
# once one is chosen. It therefore reuses the gdef shape with the identity and
# provenance gates dropped, rather than restating a shape which could drift.
_stormOptsGraphSchema = s_msgpack.deepcopy(_reqValidGdefSchema, use_list=True)
_stormOptsGraphSchema.pop('required', None)
_stormOptsGraphSchema.pop('allOf', None)

# The opts dict accepted by the Storm APIs. This is the single description of the
# opt surface; Cortex._initStormOpts() validates every Storm call against it.
#
# The root is closed, so an opt which is not declared here is rejected rather than
# silently ignored. A client with its own per query state puts it in "meta", which
# the Cortex echoes back untouched. The one exception is "readpool", which Synapse
# Enterprise reads to pin a query to the leader.
stormOptsSchema = {
    'type': 'object',
    'properties': {

        # Caller defined Storm variables. Cortex._initStormOpts() raises BadArg for
        # a non string name or one of the reserved names, so the keys stay open.
        'vars': {'type': 'object', 'additionalProperties': True},

        # Caller defined metadata. The Cortex does not read or interpret it; it is
        # echoed back verbatim as the "meta" key of the init message so a caller can
        # correlate a message stream with its own per query state.
        'meta': {'type': 'object', 'additionalProperties': True},

        # null is "unset" for each of these: the read paths fall back to the user's
        # default view, the root user, and an auto generated task iden respectively.
        'view': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'user': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'task': {'type': ['string', 'null'], 'pattern': s_config.re_iden},

        # mode is not null tolerant; getStormQuery() raises BadArg on an unknown one.
        'mode': {'type': 'string', 'enum': ['storm', 'lookup']},

        'debug': {'type': 'boolean'},
        'sudo': {'type': 'boolean'},
        'readonly': {'type': 'boolean'},

        'limit': {'type': ['integer', 'null'], 'minimum': 1},

        # the range is enforced by View.storm() so the caller gets a specific mesg.
        'keepalive': {'type': ['number', 'null']},

        # show is an allowlist and hide is a blocklist over message types. They are
        # mutually exclusive, which _initStormOpts() enforces so the caller gets a
        # specific mesg rather than a schema violation naming both keys.
        'show': {'type': 'array', 'items': {'type': 'string'}},
        'hide': {'type': 'array', 'items': {'type': 'string'}},

        # the members are checked by the runtime, which coerces an int like value
        # with s_common.intify() and raises BadTypeValu for anything else.
        'nids': {'type': 'array'},

        # ( <form>, <systemvalu> ) pairs used as initial input.
        'ndefs': {
            'type': 'array',
            'items': {
                'type': 'array',
                'minItems': 2,
                'maxItems': 2,
                'items': [{'type': 'string'}, {}],
            },
        },

        'graph': {
            'oneOf': [
                {'type': 'null'},
                {'type': 'boolean'},
                {'type': 'string'},
                _stormOptsGraphSchema,
            ],
        },

        'node:opts': {
            'type': 'object',
            'properties': {
                'repr': {'type': 'boolean'},
                'links': {'type': 'boolean'},
                'virts': {'type': 'boolean'},
                'storage': {'type': 'boolean'},
                # { <form>: { <nodepath>: ( <relprop>, ... ) } } where nodepath is a
                # "::" delimited chain of form typed props to walk from the node.
                'embeds': {
                    'type': 'object',
                    'additionalProperties': {
                        'type': 'object',
                        'additionalProperties': {'type': 'array', 'items': {'type': 'string'}},
                    },
                },
            },
            'additionalProperties': False,
        },

        # Hold the query until the Cortex reaches a nexus offset, which is how a
        # caller keeps a read behind its own write when a mirror or a read pool
        # worker may serve it. The offset comes off a previous fini message.
        'nexus': {
            'type': 'object',
            'properties': {
                'offset': {'type': ['integer', 'null'], 'minimum': 0},
                'timeout': {'type': ['number', 'null'], 'minimum': 0},
            },
            'additionalProperties': False,
        },

        # Not read by the Cortex. See the note above.
        'readpool': {'type': 'boolean'},
    },
    'additionalProperties': False,
}

# use_default=False so validating never writes schema defaults into a caller's opts.
reqValidStormOpts = s_config.getJsValidator(stormOptsSchema, use_default=False)

# For the places which persist an opts dict and use null to mean "none given".
_nullableStormOptsSchema = s_msgpack.deepcopy(stormOptsSchema, use_list=True)
_nullableStormOptsSchema['type'] = ['object', 'null']

_reqValidPermDefSchema = {
    'type': 'object',
    'properties': {
        'perm': {'type': 'array', 'items': {'type': 'string'}},
        'desc': {'type': 'string'},
        'gate': {'type': 'string'},
        'ex': {'type': 'string'},  # Example string
        'workflowconfig': {'type': 'boolean'},
        'default': {'type': 'boolean', 'default': False},
    },
    'additionalProperties': False,
    'required': ['perm', 'desc', 'gate'],
}

reqValidPermDef = s_config.getJsValidator(_reqValidPermDefSchema)

# N.B. This is kept in sync with s_datamodel.Datamodel().types
# with the DatamodelTest.test_datamodel_schema_basetypes test.
datamodel_basetypes = [
    'int',
    'float',
    'range',
    'str',
    'text',
    'title',
    'hex',
    'bool',
    'time',
    'duration',
    'ival',
    'guid',
    'syn:tag:part',
    'syn:tag',
    'comp',
    'loc',
    'array',
    'data',
    'poly',
    'hugenum',
    'taxon',
    'taxonomy',
    'velocity',
    'timeprecision',
]

_reqValidPkgdefSchema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'version': {
            'type': 'string',
            'pattern': s_version.verstr,
        },
        'build': {
            'type': 'object',
            'properties': {
                'time': {'type': 'number'},
                'synapse:version': {
                    'type': 'string',
                    'pattern': s_version.verstr
                },
                'synapse:commit': {
                    'type': 'string',
                    # Note: This pattern allows empty string for dev environments
                    'pattern': '^[0-9a-fA-F]*$'
                },
            },
            'additionalProperties': False,
            'required': ['time'],
        },
        'metadata': {
            'type': 'object',
            'properties': {
                'codesign': {
                    'type': 'object',
                    'properties': {
                        'sign': {'type': 'string'},
                        'cert': {'type': 'string'},
                    },
                    'additionalProperties': False,
                    'required': ['cert', 'sign'],
                },
                'encryption': {
                    'type': 'object',
                    'properties': {
                        # length is constrained by the if/then/else below: exactly 64 hex
                        # for a plaintext seed, and the longer RSA-encrypted form only for
                        # a per-deployment (deploy=True) package
                        'seed': {'type': 'string', 'pattern': '^[0-9a-f]{64,1024}$'},
                        'salt': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
                        'deploy': {'type': 'boolean'},
                        'pbkdf2': {
                            'type': 'object',
                            'properties': {
                                'iters': {'type': 'integer', 'minimum': 1, 'maximum': 10_000_000},
                                'hash': {'type': 'string', 'pattern': '^[a-z0-9_]+$'},
                            },
                            'required': ['iters', 'hash'],
                            'additionalProperties': False,
                        },
                    },
                    'required': ['seed', 'salt', 'pbkdf2'],
                    'additionalProperties': False,
                    # a plaintext seed is always exactly 32 bytes. Only a per-deployment
                    # package carries the RSA-encrypted seed, whose hex length is 2x the
                    # key modulus bytes -- 512 for a 2048-bit key, 768 for the 3072-bit
                    # default, 1024 for 4096-bit. Constraining these separately keeps a
                    # non-deploy package from silently accepting an over-long seed.
                    'if': {'properties': {'deploy': {'const': True}}, 'required': ['deploy']},
                    'then': {'properties': {'seed': {'pattern': '^[0-9a-f]{512,1024}$'}}},
                    'else': {'properties': {'seed': {'pattern': '^[0-9a-f]{64}$'}}},
                },
            },
            'additionalProperties': False,
        },
        'title': {'type': 'string'},
        'modules': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/module'}
        },
        'endpoints': {
            'type': 'object',
            'additionalProperties': {'$ref': '#/definitions/endpoint'},
        },
        'logo': {
            'type': 'object',
            'properties': {
                'mime': {'type': 'string'},
                'file': {'type': 'string'},
            },
            'additionalProperties': False,
            'required': ['mime', 'file'],
        },
        'commands': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/command'},
        },
        # keyed by the path the file is served by, relative to the package files directory
        'files': {
            'type': ['object', 'null'],
            'additionalProperties': {'$ref': '#/definitions/fileentry'},
        },
        'graphs': {
            'type': ['array', 'null'],
            'items': s_msgpack.deepcopy(_reqValidPkgGdefSchema, use_list=True),
        },
        'desc': {'type': 'string'},
        # declared by an advanced power-up, which is delivered by a deployed storm
        # service rather than installed as a package. Being a top level key it is
        # covered by the package code signature.
        'advanced': {'type': 'boolean'},
        # derived by the cortex onto the definitions it hands out, naming the
        # storm service which delivered the package. Declared so a caller may
        # push back a definition it read; any supplied value is ignored.
        'svcname': {'type': ['string', 'null']},
        'onload': {'type': 'string'},
        'inits': {
            'type': 'object',
            'properties': {
                'versions': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/initdef'},
                    'minItems': 1,
                },
            },
            'additionalProperties': False,
            'required': ['versions'],
        },
        # the optic section is owned by Optic, which validates it separately
        # against a schema generated from its own types, so it stays opaque here.
        'optic': {'type': 'object', 'additionalProperties': True},
        'author': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
                'name': {'type': 'string'},
            },
            'additionalProperties': False,
            'required': ['name', 'url'],
        },
        'dependencies': {
            'type': 'object',
            'additionalProperties': {'$ref': '#/definitions/dependency'},
        },
        'conflicts': {
            'type': 'object',
            'additionalProperties': {'$ref': '#/definitions/conflict'},
        },
        'perms': {
            'type': 'array',
            'items': s_msgpack.deepcopy(_reqValidPermDefSchema),
        },
        'configvars': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'name': {'type': 'string'},
                    'varname': {'type': 'string'},
                    'desc': {'type': 'string'},
                    'default': {},
                    'workflowconfig': {'type': 'boolean'},
                    'type': {'$ref': '#/definitions/configvartype'},
                    'scopes': {
                        'type': 'array',
                        'items': {
                            'type': 'string',
                            'enum': ['global', 'self']
                        },
                    },
                },
                'additionalProperties': False,
                'required': ['name', 'varname', 'desc', 'type', 'scopes'],
            },
        },
        'vaults': {
            'type': 'object',
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'version': {'type': 'integer', 'minimum': 0},
                        'migration': {'type': 'string'},
                        # opaque here: the schema is validated (and rejected for
                        # miscased keywords) at type registration via
                        # validateSchemaDef. A $ref to the draft-07 meta-schema
                        # would additionally materialize meta-schema defaults into
                        # it, diverging from the API registration path.
                        'schema': {'type': 'object', 'additionalProperties': True},
                    },
                    'additionalProperties': False,
                    'required': ['version'],
                },
            },
            'additionalProperties': False,
        }
    },
    'additionalProperties': False,
    'required': ['name', 'version'],
    'definitions': {
        'fileentry': {
            'type': 'object',
            'properties': {
                # the sha256 the file is stored and retrieved by
                'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'},
            },
            'additionalProperties': False,
            'required': ['sha256'],
        },
        'module': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'storm': {'type': 'string'},
                'interfaces': {
                    'type': 'array',
                    'items': {'type': 'string'},
                },
                # modconf is opaque package-defined configuration
                'modconf': {
                    'type': 'object',
                    'additionalProperties': True,
                },
                'apidefs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/apidef'},
                },
                'asroot:perms': {'type': 'array',
                    'items': {'type': 'array',
                        'items': {'type': 'string'}},
                },
                'asroot:ondeny:import': {
                    'type': 'string',
                    'enum': ['allow', 'warn', 'deny'],
                },
            },
            'additionalProperties': False,
            'required': ['name', 'storm']
        },
        'initdef': {
            'type': 'object',
            'properties': {
                'desc': {'type': 'string'},
                'inaugural': {'type': 'boolean', 'default': False},
                'name': {'type': 'string'},
                'query': {'type': 'string'},
                # arbitrary Storm opts for the init query.
                'queryopts': {'type': 'object', 'additionalProperties': True},
                'version': {'type': 'integer', 'minimum': 0},
            },
            'additionalProperties': False,
            'required': ['name', 'query', 'version']
        },
        'apidef': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'desc': {'type': 'string'},
                'deprecated': {'$ref': '#/definitions/deprecatedItem'},
                'type': {
                    'type': 'object',
                    'properties': {
                        'type': {
                            'type': 'string',
                            'enum': ['function']
                        },
                        'args': {
                            'type': 'array',
                            'items': {'$ref': '#/definitions/apiarg'},
                        },
                        'returns': {
                            'type': 'object',
                            'properties': {
                                'name': {
                                    'type': 'string',
                                    'enum': ['yields'],
                                },
                                'desc': {'type': 'string'},
                                'type': {
                                    'oneOf': [
                                        {'$ref': '#/definitions/apitype'},
                                        {'type': 'array', 'items': {'$ref': '#/definitions/apitype'}},
                                    ],
                                },
                            },
                            'additionalProperties': False,
                            'required': ['type', 'desc']
                        },
                    },
                    'additionalProperties': False,
                    'required': ['type', 'returns'],
                },
            },
            'additionalProperties': False,
            'required': ['name', 'desc', 'type']
        },
        'apiarg': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'desc': {'type': 'string'},
                'type': {
                    'oneOf': [
                        {'$ref': '#/definitions/apitype'},
                        {'type': 'array', 'items': {'$ref': '#/definitions/apitype'}},
                    ],
                },
                'default': {'type': ['boolean', 'integer', 'string', 'null']},
            },
            'additionalProperties': False,
            'required': ['name', 'desc', 'type']
        },
        'deprecatedItem': {
            'type': 'object',
            'properties': {
                'eolvers': {'type': 'string', 'minLength': 1,
                            'description': "The version which will not longer support the item."},
                'eoldate': {'type': 'string', 'minLength': 1,
                            'description': 'Optional string indicating Synapse releases after this date may no longer support the item.'},
                'mesg': {'type': ['string', 'null'], 'default': None,
                         'description': 'Optional message to include in the warning text.'}
            },
            'oneOf': [
                {
                    'required': ['eolvers'],
                    'not': {'required': ['eoldate']}
                },
                {
                    'required': ['eoldate'],
                    'not': {'required': ['eolvers']}
                }
            ],
            'additionalProperties': False,
        },
        'apitype': {
            'type': 'string',
        },
        'endpoint': {
            'type': 'object',
            'properties': {
                'path': {'type': 'string'},
                'url': {'type': 'string'},
                'desc': {'type': 'string'},
            },
            'required': ['path'],
            'additionalProperties': False
        },
        'command': {
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                    'pattern': s_grammar.re_scmd
                },
                'endpoints': {
                    'type': 'array',
                    'items': {'$ref': '#/definitions/endpoint'},
                },
                'cmdargs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/cmdarg'},
                },
                'cmdinputs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/cmdinput'},
                },
                # cmdconf is opaque package-defined configuration
                'cmdconf': {
                    'type': 'object',
                    'additionalProperties': True,
                },
                'storm': {'type': 'string'},
                'desc': {'type': 'string'},
                'perms': {'type': 'array',
                    'items': {'type': 'array',
                        'items': {'type': 'string'}},
                },
                'deprecated': {'$ref': '#/definitions/deprecatedItem'},
            },
            'additionalProperties': False,
            'required': ['name', 'storm']
        },
        'cmdarg': {
            'type': 'array',
            'items': [
                {'type': 'string'},
                {
                    'type': 'object',
                    'properties': {
                        'help': {'type': 'string'},
                        'default': {},
                        'dest': {'type': 'string'},
                        'required': {'type': 'boolean'},
                        'action': {'type': 'string'},
                        'nargs': {'type': ['string', 'integer']},
                        'choices': {
                            'type': 'array',
                            'uniqueItems': True,
                            'minItems': 1,
                        },
                        'type': {
                            'type': 'string',
                            'enum': s_msgpack.deepcopy(datamodel_basetypes),
                        },
                        'deprecated': {'$ref': '#/definitions/deprecatedItem'},
                    },
                    'additionalProperties': False,
                }
            ],
            'additionalItems': False,
        },
        'cmdinput': {
            'type': 'object',
            'properties': {
                'form': {'type': 'string'},
                'help': {'type': 'string'},
            },
            'additionalProperties': False,
            'required': ['form'],
        },
        'configvartype': {
            'anyOf': [
                {'type': 'array', 'items': {'$ref': '#/definitions/configvartype'}},
                {'type': 'string'},
            ]
        },
        'dependency': {
            'type': 'object',
            'properties': {
                'version': {'type': 'string'},
                'desc': {'type': 'string'},
                'optional': {'type': 'boolean'},
            },
            'additionalProperties': False,
            'required': ('version',),
        },
        'conflict': {
            'type': 'object',
            'properties': {
                'version': {'type': 'string'},
                'desc': {'type': 'string'},
            },
            'additionalProperties': False,
        }
    }
}
# use_default=False so validating a package never writes schema defaults into it;
# a built package must already carry everything it needs.
reqValidPkgdef = s_config.getJsValidator(_reqValidPkgdefSchema, use_default=False)

_reqValidDdefSchema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'storm': {'type': 'string'},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'enabled': {'type': 'boolean', 'default': True},
        # A dmon runs its query through Runtime.anit() rather than View.storm(), so
        # it never reaches Cortex._initStormOpts() and this is the only place its
        # opts are checked. It previously named three opts the dmon does not read
        # (repr and path are no longer read anywhere, and show is implemented by
        # View.storm) while leaving the dict open, so nothing was validated at all.
        # null is spliced into the type rather than wrapped in a oneOf so a bad opt
        # reports which key failed instead of "must be valid exactly by one".
        'stormopts': _nullableStormOptsSchema,
    },
    'additionalProperties': False,
    'required': ['iden', 'user', 'storm'],
}
reqValidDdef = s_config.getJsValidator(_reqValidDdefSchema)

_client_assertion_schema = {
    'type': 'object',
    'oneOf': [
        {
            'required': ['cortex:callstorm'],
            'properties': {
                'cortex:callstorm': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string'},
                        # caller defined Storm variables.
                        'vars': {'type': 'object', 'additionalProperties': True},
                        'view': {'type': 'string', 'pattern': s_config.re_iden},
                    },
                    'required': ['query', 'view'],
                    'additionalProperties': False,
                },
            },
            'additionalProperties': False,
            'not': {
                'required': ['msft:azure:workloadidentity'],
            }
        },
        {
            'required': ['msft:azure:workloadidentity'],
            'properties': {
                'msft:azure:workloadidentity': {
                    'type': 'object',
                    'properties': {
                        'token': {'type': 'boolean'},
                        'client_id': {'type': 'boolean'},
                    },
                    'required': ['token'],
                    'additionalProperties': False,
                }
            },
            'additionalProperties': False,
            'not': {
                'required': ['cortex:callstorm'],
            }
        }
    ]
}
_reqValidOauth2ProviderSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'flow_type': {'type': 'string', 'default': 'authorization_code', 'enum': ['authorization_code']},
        'auth_scheme': {'type': 'string', 'default': 'basic', 'enum': ['basic', 'client_assertion']},
        'client_id': {'type': 'string'},
        'client_secret': {'type': 'string'},
        'client_assertion': _client_assertion_schema,
        'scope': {'type': 'string'},
        'ssl': s_msgpack.deepcopy(_sslCtxOptsSchema, use_list=True),
        'auth_uri': {'type': 'string'},
        'token_uri': {'type': 'string'},
        'redirect_uri': {'type': 'string'},
        'extensions': {
            'type': 'object',
            'properties': {
                'pkce': {'type': 'boolean'},
            },
            'additionalProperties': False,
        },
        'extra_auth_params': {
            'type': 'object',
            'additionalProperties': {'type': 'string'},
        },
    },
    'additionalProperties': False,
    'required': ['iden', 'name', 'scope', 'auth_uri', 'token_uri', 'redirect_uri'],
}
reqValidOauth2Provider = s_config.getJsValidator(_reqValidOauth2ProviderSchema)

# an externally sourced RFC 6749 token response. additionalProperties is True because
# providers return refresh_token, scope, token_type and their own extensions alongside
# the two fields we require.
_reqValidOauth2TokenResponseSchema = {
    'type': 'object',
    'properties': {
        'access_token': {'type': 'string'},
        'expires_in': {'type': 'number', 'exclusiveMinimum': 0},
    },
    'additionalProperties': True,
    'required': ['access_token', 'expires_in'],
}
reqValidOauth2TokenResponse = s_config.getJsValidator(_reqValidOauth2TokenResponseSchema)

tagrestr = r'((\w+|\*|\*\*)\.)*(\w+|\*|\*\*)'  # tag with optional single or double * as segment
_tagre, _formre, _propre = (f'^{re}$' for re in (tagrestr, s_grammar.formrestr, s_grammar.proprestr))

TrigSchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'form': {'type': 'string', 'pattern': _formre},
        'n2form': {'type': 'string', 'pattern': _formre},
        'tag': {'type': 'string', 'pattern': _tagre},
        'prop': {'type': 'string', 'pattern': _propre},
        'verb': {'type': 'string', },
        'name': {'type': 'string', },
        'doc': {'type': 'string', },
        'cond': {'enum': ['node:add', 'node:del', 'tag:add', 'tag:del', 'prop:set', 'edge:add', 'edge:del']},
        'storm': {'type': 'string'},
        'async': {'type': 'boolean'},
        'enabled': {'type': 'boolean'},
        'created': {'type': 'integer', 'minimum': 0},
    },
    'additionalProperties': False,
    'required': ['iden', 'user', 'storm', 'enabled', 'creator'],
    'allOf': [
        {
            'if': {'properties': {'cond': {'const': 'node:add'}}},
            'then': {'required': ['form']},
        },
        {
            'if': {'properties': {'cond': {'const': 'node:del'}}},
            'then': {'required': ['form']},
        },
        {
            'if': {'properties': {'cond': {'const': 'tag:add'}}},
            'then': {'required': ['tag']},
        },
        {
            'if': {'properties': {'cond': {'const': 'tag:del'}}},
            'then': {'required': ['tag']},
        },
        {
            'if': {'properties': {'cond': {'const': 'prop:set'}}},
            'then': {'required': ['prop']},
        },
        {
            'if': {'properties': {'cond': {'const': 'edge:add'}}},
            'then': {'required': ['verb']},
        },
        {
            'if': {'properties': {'cond': {'const': 'edge:del'}}},
            'then': {'required': ['verb']},
        },
    ],
}
reqValidTriggerDef = s_config.getJsValidator(TrigSchema)

# the persistable keys of a trigger def. Trigger.pack() decorates a def with runtime
# counters and resolved user names, so a packed def must be filtered through this
# before it may be handed back to addTrigger().
trigDefKeys = frozenset(TrigSchema['properties'])

_httpLoginV1Schema = {
    'type': 'object',
    'properties': {
        'user': {'type': 'string'},
        'passwd': {'type': 'string'},
        },
    'additionalProperties': False,
    'required': ['user', 'passwd'],
}
reqValidHttpLoginV1 = s_config.getJsValidator(_httpLoginV1Schema)

_exportStormMetaSchema = {
    'type': 'object',
    'properties': {
        'type': {'type': 'string', 'enum': ['meta']},
        'vers': {'type': 'integer', 'minimum': 1},
        'forms': {
            'type': 'object',
            'patternProperties': {
                '^.*$': {'type': 'integer', 'minimum': 0}
            },
            'description': 'Dictionary mapping form names to their counts in the export.'
        },
        'edges': {
            'type': 'object',
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'patternProperties': {
                        '^.*$': {
                            'type': 'array',
                            'items': {'type': 'string'},
                        }
                    }
                }
            },
            'description': 'Mapping of source form to verbs to target forms.'
        },
        'count': {'type': 'integer', 'minimum': 0, 'description': 'Number of nodes exported.'},
        'synapse_ver': {
            'type': 'string',
            'description': 'Version of Synapse that exported the data.'
        },
        'creatorname': {'type': 'string', 'description': 'User who ran the export.'},
        'creatoriden': {'type': 'string', 'pattern': s_config.re_iden, 'description': 'User iden who ran the export.'},
        'created': {'type': 'integer', 'minimum': 0, 'description': 'Timestamp of the export.'},
        'query': {'type': 'string', 'description': 'The Storm query string.'},
    },
    'required': ['type', 'vers', 'forms', 'count', 'synapse_ver'],
    'additionalProperties': False,
}

reqValidExportStormMeta = s_config.getJsValidator(_exportStormMetaSchema)

_QueueDefSchema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string', 'minLength': 1},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
    },
    'required': ['name', 'creator'],
    'additionalProperties': False,
}

reqValidQueueDef = s_config.getJsValidator(_QueueDefSchema)

_v2ModelMapSchema = {
    'type': 'object',
    'properties': {
        # the shared strategic goals table, keyed by goal id.
        'goals': {
            'type': 'object',
            'additionalProperties': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string', 'minLength': 1},
                    'doc': {'type': 'string', 'minLength': 1},
                },
                'required': ['title', 'doc'],
                'additionalProperties': False,
            },
        },
        # retired v2 names, keyed by the full name. A change entry may nest
        # changed properties (keyed by relative prop name) under "props"; each
        # nested prop entry has the same shape minus "props". A nested "became"
        # is relative to the entry's form when it begins with a colon, and a
        # full property path otherwise.
        'changes': {
            'type': 'object',
            'additionalProperties': {
                'type': 'object',
                'properties': {
                    'became': {'type': 'string', 'minLength': 1},
                    'goals': {
                        'type': 'array',
                        'items': {'type': 'string', 'minLength': 1},
                    },
                    'reason': {'type': 'string', 'minLength': 1},
                    'props': {
                        'type': 'object',
                        'additionalProperties': {
                            'type': 'object',
                            'properties': {
                                'became': {'type': 'string', 'minLength': 1},
                                'goals': {
                                    'type': 'array',
                                    'items': {'type': 'string', 'minLength': 1},
                                },
                                'reason': {'type': 'string', 'minLength': 1},
                            },
                            'anyOf': [
                                {'required': ['became']},
                                {'required': ['reason']},
                            ],
                            'additionalProperties': False,
                        },
                    },
                },
                'anyOf': [
                    {'required': ['became']},
                    {'required': ['reason']},
                    {'required': ['props']},
                ],
                'additionalProperties': False,
            },
        },
    },
    'required': ['goals'],
    'additionalProperties': False,
}

reqValidV2ModelMap = s_config.getJsValidator(_v2ModelMapSchema)

# RFC 7519 2 StringOrURI: an arbitrary string, but any value containing a ':' MUST be an
# RFC 3986 URI (a valid scheme followed by URI-legal characters). An empty string has no ':'
# and stays valid. '$' is a legal sub-delim but is omitted from the class because
# fastjsonschema rewrites a literal '$' in a pattern to '\Z' (it can be percent-encoded as %24).
_jwtStringOrUri = r"^(?:[^:]*|[A-Za-z][A-Za-z0-9+.\-]*:[A-Za-z0-9\-._~:/?#\[\]@!&'()*+,;=%]*)$"

# JSON Schema for the RFC 7519 4.1 registered claims. additionalProperties is True so
# callers may set custom claims; there is no "required" list because every registered
# claim is optional. iss/sub/aud are StringOrURI (see above); jti is a plain string
# (RFC 7519 4.1.7). exp/nbf/iat are NumericDate values (epoch seconds), so they
# are numbers rather than strings.
_jwtclaimschema = {
    'type': 'object',
    'additionalProperties': True,
    'properties': {
        'iss': {'type': 'string', 'pattern': _jwtStringOrUri},
        'sub': {'type': 'string', 'pattern': _jwtStringOrUri},
        'aud': {'oneOf': [{'type': 'string', 'pattern': _jwtStringOrUri},
                          {'type': 'array', 'items': {'type': 'string', 'pattern': _jwtStringOrUri}}]},
        'exp': {'type': 'number', 'minimum': 0},
        'nbf': {'type': 'number', 'minimum': 0},
        'iat': {'type': 'number', 'minimum': 0},
        'jti': {'type': 'string'},
    },
}
reqValidJwtClaims = s_config.getJsValidator(_jwtclaimschema)
jwtRegisteredClaims = frozenset(_jwtclaimschema['properties'])
