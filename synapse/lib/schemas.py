import synapse.lib.const as s_const
import synapse.lib.config as s_config
import synapse.lib.grammar as s_grammar
import synapse.lib.msgpack as s_msgpack
import synapse.lib.version as s_version

easyPermSchema = {
    'type': 'object',
    'properties': {
        'users': {
            'type': 'object',
            'items': {'type': 'number', 'minimum': 0, 'maximum': 3},
        },
        'roles': {
            'type': 'object',
            'items': {'type': 'number', 'minimum': 0, 'maximum': 3},
        },
    },
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
                'get': {'type': 'string', 'minLen': 1},
                'head': {'type': 'string', 'minLen': 1},
                'post': {'type': 'string', 'minLen': 1},
                'put': {'type': 'string', 'minLen': 1},
                'delete': {'type': 'string', 'minLen': 1},
                'patch': {'type': 'string', 'minLen': 1},
                'options': {'type': 'string', 'minLen': 1},
            },
            'additionalProperties': False,
        },
        'authenticated': {'type': 'boolean', 'default': True},
        'name': {'type': 'string', 'default': ''},
        'desc': {'type': 'string', 'default': ''},
        'path': {'type': 'string', 'minlen': 1},
        'pool': {'type': 'boolean', 'default': False},
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
                    'perm': {'type': 'array', 'items': {'type': 'string', 'minlen': 1}},
                    'default': {'type': 'boolean', 'default': False},
                }
            },
            'default': [],
        },
        'vars': {'type': 'object', 'default': {}}

    },
    'additionalProperties': False
}

reqValidHttpExtAPIConf = s_config.getJsValidator(_HttpExtAPIConfSchema)

_LayerPushPullSchema = {
    'type': 'object',
    'properties': {
        'url': {'type': 'string'},
        'time': {'type': 'number'},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'queue:size': {'type': 'integer', 'default': s_const.layer_pdef_qsize,
                       'minimum': 1, 'maximum': s_const.layer_pdef_qsize_max},
        'chunk:size': {'type': 'integer', 'default': s_const.layer_pdef_csize,
                       'minimum': 1, 'maximum': s_const.layer_pdef_csize_max}

    },
    'additionalProperties': True,
    'required': ['iden', 'url', 'user', 'time'],
}
reqValidPush = s_config.getJsValidator(_LayerPushPullSchema)
reqValidPull = reqValidPush

_CronJobSchema = {
    'type': 'object',
    'properties': {
        'storm': {'type': 'string'},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'pool': {'type': 'boolean'},
        'doc': {'type': 'string'},
        'loglevel': {'type': 'string', 'enum': list(s_const.LOG_LEVEL_CHOICES.keys())},
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
    'required': ['creator', 'storm'],
    'dependencies': {
        'incvals': ['incunit'],
        'incunit': ['incvals'],
    },
    'definitions': {
        'req': {
            'type': 'object',
            'properties': {
                'minute': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'hour': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'dayofmonth': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'month': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
                'year': {'oneOf': [{'type': 'number'}, {'type': 'array', 'items': {'type': 'number'}}]},
            }
        }
    }
}

reqValidCronDef = s_config.getJsValidator(_CronJobSchema)
reqValidVault = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'name': {'type': 'string', 'pattern': '^.{1,128}$'},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'type': {'type': 'string', 'pattern': '^.{1,128}$'},
        'scope': {'type': ['string', 'null'], 'enum': [None, 'user', 'role', 'global']},
        'owner': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'permissions': s_msgpack.deepcopy(easyPermSchema),
        'secrets': {'type': 'object'},
        'configs': {'type': 'object'},
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
    'additionalProperties': True,
    'required': ['iden', 'parent', 'creator', 'layers'],
})

reqValidMerge = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'number', 'minval': 0},
        'comment': {'type': 'string'},
        'updated': {'type': 'number', 'minval': 0},
    },
    'required': ['iden', 'creator', 'created'],
    'additionalProperties': False,
})

reqValidVote = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'offset': {'type': 'number', 'minval': 0},
        'created': {'type': 'number', 'minval': 0},
        'approved': {'type': 'boolean'},
        'comment': {'type': 'string'},
        'updated': {'type': 'number', 'minval': 0},
    },
    'required': ['user', 'offset', 'created', 'approved'],
    'additionalProperties': False,
})

reqValidAhaPoolDef = s_config.getJsValidator({
    'type': 'object', 'properties': {
        'name': {'type': 'string', 'minLength': 1},
        'created': {'type': 'number', 'minval': 0},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        'services': {'type': 'object', 'patternProperties': {
            '.+': {'type': 'object', 'properties': {
                'created': {'type': 'number', 'minval': 0},
                'creator': {'type': 'string', 'pattern': s_config.re_iden},
            },
            'required': ['creator', 'created'],
            'additionalProperties': False,
        }}},
    },
    'additionalProperties': False,
    'required': ['name', 'creator', 'created', 'services'],
})

_cellUserApiKeySchema = {
    'type': 'object',
    'properties': {
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'name': {'type': 'string'},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'created': {'type': 'integer', 'minimum': 0},
        'updated': {'type': 'integer', 'minimum': 0},
        'expires': {'type': 'integer', 'minimum': 1},
        'shadow': {
            'type': 'object',
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

reqValidSslCtxOpts = s_config.getJsValidator({
    'type': 'object',
    'properties': {
        'verify': {'type': 'boolean', 'default': True},
        'client_cert': {'type': ['string', 'null'], 'default': None},
        'client_key': {'type': ['string', 'null'], 'default': None},
        'ca_cert': {'type': ['string', 'null'], 'default': None},
    },
    'additionalProperties': False,
})

_stormPoolOptsSchema = {
    'type': 'object',
    'properties': {
        'timeout:sync': {'type': 'integer', 'minimum': 1},
        'timeout:connection': {'type': 'integer', 'minimum': 1},
    },
    'additionalProperties': False,
}
reqValidStormPoolOpts = s_config.getJsValidator(_stormPoolOptsSchema)

_authRulesSchema = {
    'type': 'array',
    'items': {
        'type': 'array',
        'items': [
            {'type': 'boolean'},
            {'type': 'array', 'items': {'type': 'string'}},
        ],
        'minItems': 2,
        'maxItems': 2,
    }
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

# These types are order sensitive
_changelogTypes = {'migration': 'Automatic Migrations',
                   'model': 'Model Changes',
                   'feat': 'Features and Enhancements',
                   'bug': 'Bugfixes',
                   'note': 'Notes',
                   'doc': 'Improved documentation',
                   'deprecation': 'Deprecations'}

_changelogSchema = {
    'type': 'object',
    'properties': {
        'type': {
            'type': 'string',
            'enum': list(_changelogTypes.keys()),
        },
        'desc': {
            'type': 'string',
            'minLength': 1,
        },
        'prs': {
            'type': 'array',
            'items': {
                'type': 'integer',
            }
        }
    },
    'additionalProperties': False,
    'required': ['type', 'desc']
}
_reqChangelogSchema = s_config.getJsValidator(_changelogSchema)

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
        'perm': s_msgpack.deepcopy(easyPermSchema),
        'kids': {'type': 'number', 'minimum': 0},
        'created': {'type': 'number'},
        'creator': {'type': 'string', 'pattern': s_config.re_iden},
        # these are also data version info...
        'size': {'type': 'number', 'minimum': 0},
        'updated': {'type': 'number'},
        'updater': {'type': 'string', 'pattern': s_config.re_iden},
        'version': {'type': 'array', 'items': {'type': 'number', 'minItems': 3, 'maxItems': 3}},
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
    },
    'required': ('size', 'version', 'updated', 'updater'),
    'additionalProperties': False,
}
reqValidDriveDataVers = s_config.getJsValidator(driveDataVersSchema)

stixIngestConfigSchema = {
    'type': 'object',
    'properties': {
        'bundle': {
            'type': ['object', 'null'],
            'properties': {'storm': {'type': 'string'}},
        },
        'objects': {
            'type': 'object',
            'properties': {'storm': {'type': 'string'}},
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
            },
        },
    },
    'required': ['bundle', 'objects'],
}
reqValidStixIngestConfig = s_config.getJsValidator(stixIngestConfigSchema)

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
            }
        },
    },
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
        'existing': {'type': 'array', 'items': {'type': 'string'}},
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
    'ndef',
    'array',
    'edge',
    'timeedge',
    'data',
    'nodeprop',
    'hugenum',
    'taxon',
    'taxonomy',
    'velocity',
]

_reqValidPkgdefSchema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'version': {
            'type': 'string',
            'pattern': s_version.semverstr,
        },
        'build': {
            'type' 'object'
            'properties': {
                'time': {'type': 'number'},
            },
            'required': ['time'],
        },
        'codesign': {
            'type': 'object',
            'properties': {
                'sign': {'type': 'string'},
                'cert': {'type': 'string'},
            },
            'required': ['cert', 'sign'],
        },
        # TODO: Remove me after Synapse 3.0.0.
        'synapse_minversion': {
            'type': ['array', 'null'],
            'items': {'type': 'number'}
        },
        'synapse_version': {
            'type': 'string',
        },
        'modules': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/module'}
        },
        'docs': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/doc'},
        },
        'logo': {
            'type': 'object',
            'properties': {
                'mime': {'type': 'string'},
                'file': {'type': 'string'},
            },
            'additionalProperties': True,
            'required': ['mime', 'file'],
        },
        'commands': {
            'type': ['array', 'null'],
            'items': {'$ref': '#/definitions/command'},
        },
        'graphs': {
            'type': ['array', 'null'],
            'items': s_msgpack.deepcopy(_reqValidGdefSchema, use_list=True),
        },
        'desc': {'type': 'string'},
        'svciden': {'type': ['string', 'null'], 'pattern': s_config.re_iden},
        'onload': {'type': 'string'},
        'author': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string'},
                'name': {'type': 'string'},
            },
            'required': ['name', 'url'],
        },
        'depends': {
            'properties': {
                'requires': {'type': 'array', 'items': {'$ref': '#/definitions/require'}},
                'conflicts': {'type': 'array', 'items': {'$ref': '#/definitions/conflict'}},
            },
            'additionalProperties': True,
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
                'required': ['name', 'varname', 'desc', 'type', 'scopes'],
            },
        },
    },
    'additionalProperties': True,
    'required': ['name', 'version'],
    'definitions': {
        'doc': {
            'type': 'object',
            'properties': {
                'title': {'type': 'string'},
                'content': {'type': 'string'},
            },
            'additionalProperties': True,
            'required': ['title', 'content'],
        },
        'module': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'storm': {'type': 'string'},
                'modconf': {'type': 'object'},
                'apidefs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/apidef'},
                },
                'asroot': {'type': 'boolean'},
                'asroot:perms': {'type': 'array',
                    'items': {'type': 'array',
                        'items': {'type': 'string'}},
                },
            },
            'additionalProperties': True,
            'required': ['name', 'storm']
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
        'command': {
            'type': 'object',
            'properties': {
                'name': {
                    'type': 'string',
                    'pattern': s_grammar.re_scmd
                },
                'endpoints': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'path': {'type': 'string'},
                            'host': {'type': 'string'},
                            'desc': {'type': 'string'},
                        },
                        'required': ['path'],
                        'additionalProperties': False
                    }
                },
                'cmdargs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/cmdarg'},
                },
                'cmdinputs': {
                    'type': ['array', 'null'],
                    'items': {'$ref': '#/definitions/cmdinput'},
                },
                'storm': {'type': 'string'},
                'forms': {'$ref': '#/definitions/cmdformhints'},
                'perms': {'type': 'array',
                    'items': {'type': 'array',
                        'items': {'type': 'string'}},
                },
            },
            'additionalProperties': True,
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
                    },
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
            'additionalProperties': True,
            'required': ['form'],
        },
        'configvartype': {
            'anyOf': [
                {'type': 'array', 'items': {'$ref': '#/definitions/configvartype'}},
                {'type': 'string'},
            ]
        },
        # deprecated
        'cmdformhints': {
            'type': 'object',
            'properties': {
                'input': {
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {
                        'type': 'string',
                    }
                },
                'output': {
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {
                        'type': 'string',
                    }
                },
                'nodedata': {
                    'type': 'array',
                    'uniqueItems': True,
                    'items': {
                        'type': 'array',
                        'items': [
                            {'type': 'string'},
                            {'type': 'string'},
                        ],
                        'additionalItems': False,
                    },
                },
            }
        },
        'require': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'version': {'type': 'string'},
                'desc': {'type': 'string'},
                'optional': {'type': 'boolean'},
            },
            'additionalItems': True,
            'required': ('name', 'version'),
        },
        'conflict': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'version': {'type': 'string'},
                'desc': {'type': 'string'},
            },
            'additionalItems': True,
            'required': ('name',),
        },
    }
}
reqValidPkgdef = s_config.getJsValidator(_reqValidPkgdefSchema)

_reqValidDdefSchema = {
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'storm': {'type': 'string'},
        'view': {'type': 'string', 'pattern': s_config.re_iden},
        'user': {'type': 'string', 'pattern': s_config.re_iden},
        'iden': {'type': 'string', 'pattern': s_config.re_iden},
        'enabled': {'type': 'boolean', 'default': True},
        'stormopts': {
            'oneOf': [
                {'type': 'null'},
                {'$ref': '#/definitions/stormopts'}
            ]
        }
    },
    'additionalProperties': True,
    'required': ['iden', 'user', 'storm'],
    'definitions': {
        'stormopts': {
            'type': 'object',
            'properties': {
                'repr': {'type': 'boolean'},
                'path': {'type': 'string'},
                'show': {'type': 'array', 'items': {'type': 'string'}}
            },
            'additionalProperties': True,
        },
    }
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
                        'vars': {'type': 'object'},
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
        'ssl_verify': {'type': 'boolean', 'default': True},
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
