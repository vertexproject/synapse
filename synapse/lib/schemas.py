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
        'nomerge': {'type': 'boolean'},
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
