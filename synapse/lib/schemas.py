import synapse.lib.const as s_const
import synapse.lib.config as s_config
import synapse.lib.msgpack as s_msgpack


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
_reqChanglogSchema = s_config.getJsValidator(_changelogSchema)

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
