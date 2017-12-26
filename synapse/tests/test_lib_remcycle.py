import time
import random

import synapse.common as s_common

import synapse.lib.webapp as s_webapp
import synapse.lib.msgpack as s_msgpack
import synapse.lib.remcycle as s_remcycle

import synapse.models.inet as s_inet

from tornado.testing import AsyncTestCase

from synapse.tests.common import *

class FakeIpify():
    IPS = ['1.2.3.4',
           '8.8.8.8',
           '10.0.0.1',
           '127.0.0.1',
           '192.168.1.1',
           '255.255.255.255',
           ]

    def random_ip(self, *args, **kwargs):
        '''Get a random IP'''
        fmt = kwargs.get('format')
        ip = random.choice(self.IPS)
        ret = ip
        if fmt:
            ret = {'ip': ip}
        time.sleep(0.025)
        return ret

class BytsNommer():
    def __init__(self):
        self.nommed = False

    def noms(self, *args, **kwargs):
        body = kwargs.get('body')
        if body:
            self.nommed = True
        time.sleep(0.025)
        return True

class StandaloneTestServer(s_eventbus.EventBus):
    '''
    Creates a Synapse webapp in its own thread, so there is no
    conflict between the AsyncTestCase ioloop and the ioloop
    used by the webapp.
    '''
    def __init__(self, port=40000):
        s_eventbus.EventBus.__init__(self)
        self.port = port
        self.running = False
        self.fake = FakeIpify()
        self.nommer = BytsNommer()
        self.wapp_thr = self.fireWebApp()
        while self.running is False:
            time.sleep(0.05)
        self.onfini(self.onServerFini)

    def onServerFini(self):
        self.running = False
        self.wapp.fini()
        self.wapp_thr.join()

    @s_common.firethread
    def fireWebApp(self):
        self.wapp = s_webapp.WebApp()
        self.wapp.listen(self.port, host='127.0.0.1')
        self.wapp.addApiPath('/v1/ip(\?format=[\w]+)?', self.fake.random_ip)
        self.wapp.addApiPath('/v1/bytes', self.nommer.noms)
        self.running = True


def get_vertex_global_config():
    gconfig = {
        'apis': [
            [
                'http',
                {
                    'doc': 'Get the vertex project landing page.',
                    'url': 'http://vertex.link/',
                    'http': {
                        'validate_cert': False
                    }
                }
            ],
            [
                'https',
                {
                    'doc': 'Get the vertex project landing page.',
                    'url': 'https://vertex.link/',
                    'http': {
                        'validate_cert': False
                    }
                }
            ],
            [
                'fake_endpoint',
                {
                    'doc': 'Fake endpoint',
                    'url': 'https://vertex.link/foo/bar/duck',
                    'http': {
                        'validate_cert': False
                    }
                }
            ]
        ],
        'doc': 'Grab Vertex.link stuff',
        'http': {
            'user_agent': 'ClownBrowser'
        },
        'namespace': 'vertexproject',
    }
    return gconfig

def get_fake_ipify_ingest_global_config(port=40000):
    gconfig = {
        'apis': [
            [
                'jsonip',
                {
                    'doc': 'Get IP in a JSON blob',
                    'http': {
                        'validate_cert': False
                    },
                    'ingest': {
                        'name': 'ipv4',
                        'definition':
                            {
                                'ingest': {
                                    "forms": [
                                        [
                                            "inet:ipv4",
                                            {
                                                "var": "ip"
                                            }
                                        ]
                                    ],
                                    "vars": [
                                        [
                                            "ip",
                                            {
                                                "path": "ret/ip"
                                            }
                                        ]
                                    ]
                                },
                                'open': {
                                    'format': 'json'
                                }
                            }
                    },
                    'url': 'http://localhost:{PORT}/v1/ip?format=json',
                    'vars': {
                        'PORT': port,
                    }
                }
            ],
            [
                'rawip',
                {
                    'doc': 'Get IP in a string',
                    'http': {
                        'validate_cert': False
                    },
                    'url': 'http://localhost:{PORT}/v1/ip',
                    'vars': {
                        'PORT': port,
                    }
                }
            ],
            [
                'fake_endpoint',
                {
                    'doc': 'Fake endpoint',
                    'http': {
                        'validate_cert': False
                    },
                    'url': 'http://localhost:{{}}/foo/bar/duck',
                    'vars': {
                        'PORT': port,
                    }
                }
            ]
        ],
        'doc': 'API for getting calling IP address',
        'http': {
            'user_agent': 'SynapseTest',
            'request_timeout': 30
        },
        'namespace': 'fakeipify',
    }
    return gconfig

def get_fake_ipify_global_config(port=40000):
    gconfig = {
        'apis': [
            [
                'jsonip',
                {
                    'doc': 'Get IP in a JSON blob',
                    'http': {
                        'validate_cert': False
                    },
                    'url': 'http://localhost:{PORT}/v1/ip?format=json',
                    'vars': {
                        'PORT': port,
                    }
                }
            ],
            [
                'rawip',
                {
                    'doc': 'Get IP in a string',
                    'http': {
                        'validate_cert': False
                    },
                    'url': 'http://localhost:{PORT}/v1/ip',
                    'vars': {
                        'PORT': port,
                    }
                }
            ],
            [
                'byts',
                {
                    'doc': 'nom some bytes',
                    'http': {
                        'method': 'POST',
                    },
                    'url': 'http://localhost:{PORT}/v1/bytes',
                    'vars': {
                        'PORT': port,
                    }
                }
            ],
            [
                'fake_endpoint',
                {
                    'doc': 'Fake endpoint',
                    'http': {
                        'validate_cert': False
                    },
                    'url': 'http://localhost:{PORT}/foo/bar/duck',
                    'vars': {
                        'PORT': port,
                    }
                }
            ]
        ],
        'doc': 'API for getting calling IP address',
        'http': {
            'user_agent': 'SynapseTest',
            'request_timeout': 30
        },
        'namespace': 'fakeipify',
    }
    return gconfig

class NyxTest(SynTest):
    def setUp(self):
        self.config = {
            "url": "http://vertex.link/api/v4/geoloc/{{someplace}}/info?domore={{domore}}&apikey={APIKEY}",

            "vars": {"APIKEY": "8675309"},

            "http": {
                "method": "GET",  # this defaults to GET obvs, just making an example
                "headers": {
                    "x-notes-log": "stardate 1234",
                    "token-goodness": "sekrit token"
                },
                "user_agent": "Totally Not a Python application."
            },

            "doc": "api example",

            "api_args": ["someplace"],
            "api_optargs": {"domore": 0}
        }
        self.post_config = {
            "url": "http://vertex.link/api/v4/geoloc/{{someplace}}/postendpoint",

            "http": {
                "method": "POST",  # this defaults to GET obvs, just making an example
                "headers": {
                    "x-notes-log": "stardate 1234",
                    "token-goodness": "sekrit token"
                },
                "user_agent": "Totally Not a Python application."
            },

            "doc": "api example",
            "api_args": ["someplace"],
        }
        self.bad_config = {
            "url": "http://vertex.link/api/v4/geoloc/{{req_body}}/postendpoint",
            "doc": "api example",
            "api_args": ["req_body"],
        }

    def test_nyx_tornado_http_check(self):
        self.thisHostMustNot(platform='windows')
        nyx = s_remcycle.Nyx(config=self.config)

        good_dict = {'method': 'PUT',
                     'user_agent': 'VertexWeb',
                     'headers': {'X-Derry': 'FriendlyClowns',
                                 'CSRF-Token': '1234'},
                     'request_timeout': 100,
                     'connect_timeout': 20,
                     }

        nyx.request_defaults = good_dict

        r = nyx.buildHttpRequest({'someplace': 'A house'})
        self.nn(r)

        bad_dict = {'method': 'PUT',
                    'user-agent': 'Lynx',  # Typo / misspelling
                    }

        nyx.request_defaults = bad_dict

        with self.raises(Exception) as cm:
            nyx.buildHttpRequest({'someplace': 'A house'})
        self.true('unexpected keyword argument' in str(cm.exception))

    def test_nyx_simple_config(self):
        self.thisHostMustNot(platform='windows')
        nyx = s_remcycle.Nyx(config=self.config)
        e_url = 'http://vertex.link/api/v4/geoloc/{someplace}/info?domore={domore}&apikey=8675309'
        self.eq(nyx.effective_url, e_url)
        self.eq(nyx.api_args, ['someplace'])
        self.eq(nyx.api_kwargs, {'domore': 0})

        # Ensure property is structured correctly and data from the property
        # cannot mutate the Nyx object
        desc = nyx.description()
        self.true(isinstance(desc, dict))
        self.true('doc' in desc)
        self.true('api_args' in desc)
        self.true(desc.get('api_args') == nyx.api_args)
        self.true(desc.get('api_args') is not nyx.api_args)
        self.true('api_optargs' in desc)
        self.true(desc.get('api_optargs') is not nyx.api_kwargs)
        # Overkill
        desc.get('api_optargs')['foo'] = '1'
        self.true('foo' not in nyx.api_kwargs)
        desc.get('api_optargs')['domore'] = '1'
        self.true(nyx.api_kwargs['domore'] == 0)

        with self.raises(BadConfValu) as cm:
            nyx = s_remcycle.Nyx(self.bad_config)
        self.eq(cm.exception.get('name'), 'req_body')
        self.eq(cm.exception.get('valu'), None)
        self.isin('Reserved api_arg used', cm.exception.get('mesg'))

    def test_nyx_make_request(self):
        self.thisHostMustNot(platform='windows')
        nyx = s_remcycle.Nyx(config=self.config)
        e_url = 'http://vertex.link/api/v4/geoloc/{someplace}/info?domore={domore}&apikey=8675309'
        self.eq(nyx.effective_url, e_url)
        req = nyx.buildHttpRequest(api_args={'someplace': 'foobar'})
        e_url = 'http://vertex.link/api/v4/geoloc/foobar/info?domore=0&apikey=8675309'
        self.eq(req.url, e_url)
        self.eq(req.user_agent, self.config.get('http').get('user_agent'))

        req = nyx.buildHttpRequest(api_args={'someplace': 'duck', 'domore': 1})
        e_url = 'http://vertex.link/api/v4/geoloc/duck/info?domore=1&apikey=8675309'
        self.eq(req.url, e_url)
        self.eq(req.connect_timeout, None)  # Default value for the object itself
        self.eq(req.request_timeout, None)  # Default value for the object itself

        # Ensure that extra params don't make it through
        req = nyx.buildHttpRequest(api_args={'someplace': 'duck', 'domore': 1, 'beep': 1234})
        e_url = 'http://vertex.link/api/v4/geoloc/duck/info?domore=1&apikey=8675309'
        self.eq(req.url, e_url)

        # Ensure that values stamped in via HTTP get used
        conf = self.config.copy()
        conf['http']['request_timeout'] = 1000
        conf['http']['connect_timeout'] = 100
        nyx2 = s_remcycle.Nyx(config=conf)
        req = nyx2.buildHttpRequest(api_args={'someplace': 'duck', 'domore': 1})
        e_url = 'http://vertex.link/api/v4/geoloc/duck/info?domore=1&apikey=8675309'
        self.eq(req.url, e_url)
        self.eq(req.connect_timeout, 100)  # Default value for the object itself
        self.eq(req.request_timeout, 1000)  # Default value for the object itself

    def test_nyx_quoted_values(self):
        self.thisHostMustNot(platform='windows')
        nyx = s_remcycle.Nyx(config=self.config)
        req = nyx.buildHttpRequest(api_args={'someplace': 'foo bar',
                                             'domore': 'eeep@foo.bar'})
        e_url = 'http://vertex.link/api/v4/geoloc/foo+bar/info?domore=eeep%40foo.bar&apikey=8675309'
        self.eq(req.url, e_url)

    def test_hypnos_make_body(self):
        self.thisHostMustNot(platform='windows')
        nyx = s_remcycle.Nyx(config=self.post_config)
        byts = json.dumps({'foo': 'bar', 'baz': [1, 2, 3]}).encode()
        req = nyx.buildHttpRequest(api_args={'someplace': 'Derry'})
        e_url = 'http://vertex.link/api/v4/geoloc/Derry/postendpoint'
        self.eq(req.method, 'POST')
        self.eq(req.url, e_url)
        self.eq(req.body, None)
        body_req = nyx.buildHttpRequest(api_args={'req_body': byts, 'someplace': 'Derry'})
        self.eq(body_req.url, e_url)
        self.eq(body_req.body, byts)
        # Ensure the req_body can be put onto a GET for badly shaped APIs
        put_nyx = s_remcycle.Nyx(config=self.config)
        put_req = nyx.buildHttpRequest(api_args={'someplace': 'foo bar',
                                                 'domore': 'eeep@foo.bar',
                                                 'req_body': byts})
        self.eq(put_req.body, byts)

class HypnosTest(SynTest, AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        '''Spin up the fake ipify server on a random port'''
        cls.env = TstEnv()
        cls.port = random.randint(20000, 50000)
        cls.env.add('testserver',
                    StandaloneTestServer(port=cls.port),
                    fini=True)

    @classmethod
    def tearDownClass(cls):
        cls.env.fini()

    def test_hypnos_config_bounds(self):
        self.thisHostMustNot(platform='windows')
        with self.raises(s_common.BadConfValu) as cm:
            hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 0},
                                         ioloop=self.io_loop)
        self.isin('web:worker:threads:min must be greater than 1', str(cm.exception))

        with self.raises(s_common.BadConfValu) as cm:
            hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MAX_WORKER_THREADS: 1,
                                               s_remcycle.MIN_WORKER_THREADS: 2},
                                         ioloop=self.io_loop)
        self.isin('web:worker:threads:max must be greater than the web:worker:threads:min', str(cm.exception))
        with self.raises(s_common.BadConfValu) as cm:
            hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MAX_CLIENTS: 0, },
                                         ioloop=self.io_loop)
        self.isin('web:tornado:max_clients must be greater than 1', str(cm.exception))

    def test_hypnos_fini(self):
        # Ensure we call fini on all objects created by the core.
        self.thisHostMustNot(platform='windows')
        hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                                     ioloop=self.io_loop)
        hypo_obj.fini()
        self.true(hypo_obj.isfini)
        self.true(hypo_obj.web_boss.isfini)
        self.false(hypo_obj.web_iothr.is_alive())
        self.true(hypo_obj.web_core.isfini)

    def test_hypnos_fini_core(self):
        # Ensure we don't tear down a Cortex provided to us by the constructor.
        self.thisHostMustNot(platform='windows')
        core = s_cortex.openurl('ram:///')
        hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                                     ioloop=self.io_loop, core=core)
        hypo_obj.fini()
        self.true(hypo_obj.isfini)
        self.true(hypo_obj.web_boss.isfini)
        self.false(hypo_obj.web_iothr.is_alive())
        self.false(hypo_obj.web_core.isfini)
        core.fini()
        self.true(hypo_obj.web_core.isfini)

    def test_hypnos_callback_ondone(self):
        self.thisHostMustNot(platform='windows')

        # testserver = Foo()
        gconf = get_fake_ipify_global_config(port=self.port)

        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('fakeipify:jsonip' in hypo_obj._web_apis)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                data[_jid] = jobd

            def cb(*args, **kwargs):
                resp = kwargs.get('resp')
                self.true(resp.get('code') == 200)
                data = resp.get('data')
                self.true('ret' in data)
                ret = data.get('ret')
                self.true('ip' in ret)

            jid = hypo_obj.fireWebApi('fakeipify:jsonip',
                                      callback=cb,
                                      ondone=ondone)

            job = hypo_obj.web_boss.job(jid)
            hypo_obj.web_boss.wait(jid)

            self.true(jid in data)
            self.true(job[1].get('done'))

    def test_hypnos_config_register_deregister(self):
        self.thisHostMustNot(platform='windows')
        vertex_conf = get_vertex_global_config()
        ipify_conf = get_fake_ipify_ingest_global_config()

        data = set([])

        def func(eventdata):
            evtname, _ = eventdata
            data.add(evtname)

        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            # Register callbacks
            hypo_obj.on('hypnos:register:namespace:add', func)
            hypo_obj.on('hypnos:register:namespace:del', func)
            hypo_obj.on('hypnos:register:api:del', func)
            hypo_obj.on('hypnos:register:api:add', func)

            hypo_obj.addWebConfig(config=vertex_conf)
            self.true('vertexproject' in hypo_obj._web_namespaces)
            self.true('vertexproject' in hypo_obj._web_docs)
            self.true(len(hypo_obj._web_apis) == 3)
            self.true('vertexproject:http' in hypo_obj._web_apis)
            self.true('vertexproject:https' in hypo_obj._web_apis)
            self.eq(dict(hypo_obj._web_api_ingests), {})

            # Test description data
            d = hypo_obj.getWebDescription()
            self.true(isinstance(d, dict))
            self.true('vertexproject' in d)
            self.true('doc' in d['vertexproject'])
            self.true('vertexproject:http' in d['vertexproject'])
            self.true('doc' in d['vertexproject']['vertexproject:http'])

            hypo_obj.addWebConfig(config=ipify_conf)
            self.true('fakeipify' in hypo_obj._web_namespaces)
            self.true('fakeipify' in hypo_obj._web_docs)
            self.eq(len(hypo_obj._web_namespaces), 2)
            self.eq(len(hypo_obj._web_apis), 6)
            self.true('fakeipify:jsonip' in hypo_obj._web_apis)
            self.true('fakeipify:jsonip' in hypo_obj._web_api_ingests)
            self.true('fakeipify:jsonip' in hypo_obj._syn_funcs)
            self.nn(hypo_obj.web_core.getTufoByProp('syn:ingest', 'fakeipify:jsonip:ipv4'))

            # Check repr!
            r = repr(hypo_obj)
            self.true('Hypnos' in r)
            self.true('vertexproject' in r)
            self.true('fakeipify' in r)
            self.true('synapse.cores.common.Cortex' in r)

            # Ensure that if we remove everything when we dereregister a namespace
            hypo_obj.delWebConf(namespace='fakeipify')
            self.true('fakeipify' not in hypo_obj._web_namespaces)
            self.true('fakeipify' not in hypo_obj._web_docs)
            self.eq(len(hypo_obj._web_namespaces), 1)
            self.eq(len(hypo_obj._web_apis), 3)
            self.true('fakeipify:jsonip' not in hypo_obj._web_apis)
            self.true('fakeipify:jsonip' not in hypo_obj._web_api_ingests)
            self.true('fakeipify:jsonip' not in hypo_obj._syn_funcs)
            self.true('fakeipify:jsonip:ipv4' not in hypo_obj.web_core._syn_funcs)

            # Trying to re-register a present namespace should fail
            with self.raises(NameError) as cm:
                hypo_obj.addWebConfig(config=vertex_conf, reload_config=False)
            self.true('Namespace is already registered' in str(cm.exception))

            # Register ipfy again
            hypo_obj.addWebConfig(config=ipify_conf)
            self.true('fakeipify' in hypo_obj._web_namespaces)
            self.true('fakeipify' in hypo_obj._web_docs)
            self.eq(len(hypo_obj._web_namespaces), 2)
            self.eq(len(hypo_obj._web_apis), 6)
            self.true('fakeipify:jsonip' in hypo_obj._web_apis)
            self.true('fakeipify:jsonip' in hypo_obj._web_api_ingests)
            self.true('fakeipify:jsonip' in hypo_obj._syn_funcs)
            self.nn(hypo_obj.web_core.getTufoByProp('syn:ingest', 'fakeipify:jsonip:ipv4'))
            self.true('fakeipify:jsonip' in hypo_obj._web_api_gest_opens)

            # Now change something with ipify, register it and force a reload to occur
            api_def = ipify_conf['apis'].pop(0)
            gest_def = api_def[1]['ingest']
            gest_def['name'] = 'foobar'
            ipify_conf['apis'].append(['duckip', api_def[1]])

            hypo_obj.addWebConfig(config=ipify_conf)

            self.true('fakeipify' in hypo_obj._web_namespaces)
            self.true('fakeipify' in hypo_obj._web_docs)
            self.eq(len(hypo_obj._web_namespaces), 2)
            self.eq(len(hypo_obj._web_apis), 6)
            self.true('fakeipify:jsonip' not in hypo_obj._web_apis)
            self.true('fakeipify:jsonip' not in hypo_obj._web_api_ingests)
            self.true('fakeipify:jsonip' not in hypo_obj._syn_funcs)
            self.true('fakeipify:jsonip:ipv4' not in hypo_obj.web_core._syn_funcs)
            self.true('fakeipify:jsonip' not in hypo_obj._web_api_gest_opens)
            self.true('fakeipify:duckip' in hypo_obj._web_apis)
            self.true('fakeipify:duckip' in hypo_obj._web_api_ingests)
            self.true('fakeipify:duckip' in hypo_obj._syn_funcs)
            self.nn(hypo_obj.web_core.getTufoByProp('syn:ingest', 'fakeipify:duckip:foobar'))
            self.true('fakeipify:duckip' in hypo_obj._web_api_gest_opens)

        # ensure all the expected events fired during testing
        self.true('hypnos:register:namespace:add' in data)
        self.true('hypnos:register:namespace:del' in data)
        self.true('hypnos:register:api:add' in data)
        self.true('hypnos:register:api:del' in data)

    def test_hypnos_fire_api_callback(self):
        # Ensure that the provided callback is fired and args are passed to the callbacks.
        self.thisHostMustNot(platform='windows')

        # testserver = Foo()
        gconf = get_fake_ipify_global_config(port=self.port)

        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 2},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)
            d = {'set': False,
                 'keys': set([])}

            def cb(*args, **kwargs):
                self.true('foo' in args)
                self.true('bar' in args)
                self.true('resp' in kwargs)
                self.true('key' in kwargs)
                resp = kwargs.get('resp')
                self.eq(resp.get('code'), 200)
                d['set'] = True
                d['keys'].add(kwargs.get('key'))

            jid1 = hypo_obj.fireWebApi('fakeipify:rawip', 'foo', 'bar', key='12345', callback=cb)
            jid2 = hypo_obj.fireWebApi('fakeipify:rawip', 'foo', 'bar', key='67890', callback=cb)

            hypo_obj.web_boss.wait(jid=jid1)
            hypo_obj.web_boss.wait(jid=jid2)
            self.eq(d['set'], True)
            self.eq(d.get('keys'), {'12345', '67890'})

    def test_hypnos_default_callback(self):
        # Ensure that the default callback, of firing an event handler, works.
        self.thisHostMustNot(platform='windows')
        # testserver = Foo()
        gconf = get_fake_ipify_global_config(port=self.port)
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1}, ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('fakeipify:jsonip' in hypo_obj._web_apis)

            def func(event_tufo):
                event_name, argdata = event_tufo
                kwargs = argdata.get('kwargs')
                resp = kwargs.get('resp')
                self.eq(resp.get('code'), 200)

            hypo_obj.on('fakeipify:jsonip', func=func)

            jid = hypo_obj.fireWebApi('fakeipify:jsonip')

            job = hypo_obj.web_boss.job(jid)
            hypo_obj.web_boss.wait(jid)

            self.true(job[1].get('done'))

    def test_hypnos_default_callback_null(self):
        # Ensure the Job is complete even if we have no explicit callback or
        # listening event handlers.
        self.thisHostMustNot(platform='windows')
        gconf = get_fake_ipify_global_config(port=self.port)
        # testserver = Foo()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('fakeipify:jsonip' in hypo_obj._web_apis)

            jid = hypo_obj.fireWebApi('fakeipify:jsonip')

            job = hypo_obj.web_boss.job(jid)
            hypo_obj.web_boss.wait(jid)

            self.true(job[1].get('done'))
            self.eq(job[1].get('task')[2].get('resp').get('code'), 200)

    def test_hypnos_manual_ingest_via_eventbus(self):
        # This is a manual setup of the core / ingest type of action.
        self.thisHostMustNot(platform='windows')

        core = s_cortex.openurl('ram://')

        gconf = get_fake_ipify_global_config(port=self.port)
        # testserver = Foo()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            data = {}

            ingest_def = {
                "ingest": {
                    "forms": [
                        [
                            "inet:ipv4",
                            {
                                "var": "ip"
                            }
                        ]
                    ],
                    "vars": [
                        [
                            "ip",
                            {
                                "path": "ret/ip"
                            }
                        ]
                    ]
                }
            }

            name = 'fakeipify:jsonip'
            core_name = ':'.join([name, 'ingest'])

            gest = s_ingest.Ingest(info=ingest_def)

            s_ingest.register_ingest(core=core,
                                     gest=gest,
                                     evtname=core_name)

            def glue(event):
                evtname, event_args = event
                kwargs = event_args.get('kwargs')
                resp = kwargs.get('resp')
                data = resp.get('data')
                core.fire(core_name, data=data)

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                _data = jobd.get('task')[2].get('resp', {}).get('data', {})
                ip = _data.get('ret', {}).get('ip', '')
                data[_jid] = ip

            hypo_obj.on(name, func=glue)

            jid = hypo_obj.fireWebApi(name=name, ondone=ondone)
            hypo_obj.web_boss.wait(jid)

            tufos = core.getTufosByProp('inet:ipv4')
            self.eq(len(tufos), 1)
            # Validate the IP of the tufo is the same we got from ipify
            self.eq(s_inet.ipv4str(tufos[0][1].get('inet:ipv4')), data[jid])

        core.fini()

    def test_hypnos_automatic_ingest(self):
        # Ensure that a configuration object with a ingest definition is automatically parsed.
        self.thisHostMustNot(platform='windows')
        gconf = get_fake_ipify_ingest_global_config(port=self.port)
        # testserver = Foo()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('fakeipify:jsonip' in hypo_obj._syn_funcs)
            self.nn(hypo_obj.web_core.getTufoByProp('syn:ingest', 'fakeipify:jsonip:ipv4'))

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                _data = jobd.get('task')[2].get('resp', {}).get('data')
                _bytez = _data.read()
                _d = json.loads(_bytez.decode())
                data[_jid] = _d.get('ret').get('ip')

            jid = hypo_obj.fireWebApi(name='fakeipify:jsonip', ondone=ondone)
            hypo_obj.web_boss.wait(jid)

            tufos = hypo_obj.web_core.getTufosByProp('inet:ipv4')
            self.eq(len(tufos), 1)
            # Validate the IP of the tufo is the same we got from ipify
            self.nn(data[jid])
            self.eq(s_inet.ipv4str(tufos[0][1].get('inet:ipv4')), data[jid])

    def test_hypnos_simple_fail(self):
        # Test a simple failure case
        self.thisHostMustNot(platform='windows')
        gconf = get_fake_ipify_global_config(port=self.port)
        # testserver = Foo()

        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)
            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                data[_jid] = jobd

            jid = hypo_obj.fireWebApi(name='fakeipify:fake_endpoint',
                                      ondone=ondone)
            hypo_obj.web_boss.wait(jid)
            job = data.get(jid)

            # Ensure that we have error information propagated up to the job
            self.true('err' in job)
            self.eq(job.get('err'), 'HTTPError')
            self.true('errfile' in job)
            self.true('errline' in job)
            self.true('errmsg' in job)
            # Since our fail is going to be a http error we have some response data
            resp = job.get('task')[2].get('resp')
            self.true('code' in resp)
            self.true('request' in resp)
            self.true('headers' in resp)

    def test_hypnos_with_telepath(self):
        # Setup the Hypnos object using telepath, then get the proxy object and
        # issue the fireWebApi calls via telepath, validate that they worked
        # against ingested tufo in the hypnos cortex. Use daemon to handle
        # telepath proxying.
        self.thisHostMustNot(platform='windows')
        gconf = get_fake_ipify_ingest_global_config(port=self.port)
        dconf = {
            'vars': {
                'hopts': {
                    s_remcycle.MIN_WORKER_THREADS: 1,
                },
                'hioloop': self.io_loop,
                'cortex_url': 'ram://'
            },
            'ctors': [
                [
                    'core',
                    'ctor://synapse.cortex.openurl(cortex_url)'
                ],
                [
                    'hypnos',
                    'ctor://synapse.lib.remcycle.Hypnos(core=core, ioloop=hioloop,opts=hopts)'
                ]
            ],
            'share': [
                [
                    'hypnos',
                    {}
                ],
                [
                    'core',
                    {}
                ]
            ],
            'listen': [
                'tcp://127.0.0.1:50001'
            ]
        }

        dmon = s_daemon.Daemon()
        dmon.loadDmonConf(dconf)

        hypnos_proxy = s_telepath.openurl('tcp://127.0.0.1:50001/hypnos')
        core_proxy = s_telepath.openurl('tcp://127.0.0.1:50001/core')
        # Lets do a remote config load!
        hypnos_proxy.addWebConfig(config=gconf)

        description = hypnos_proxy.getWebDescription()
        self.true('fakeipify' in description)
        # Fire the web api
        jid = hypnos_proxy.fireWebApi(name='fakeipify:jsonip')
        self.nn(jid)
        hypnos_proxy.webJobWait(jid)
        tufos = core_proxy.getTufosByProp('inet:ipv4')
        self.eq(len(tufos), 1)
        ip = s_inet.ipv4str(tufos[0][1].get('inet:ipv4'))
        self.true(len(ip) >= 7)

    def test_hypnos_content_type_skips(self):
        self.thisHostMustNot(platform='windows')
        gconf = get_fake_ipify_global_config(port=self.port)
        # testserver = Foo()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('fakeipify:jsonip' in hypo_obj._web_apis)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                resp_data = jobd.get('task')[2].get('resp').get('data')
                data[_jid] = type(resp_data)

            jid1 = hypo_obj.fireWebApi('fakeipify:jsonip',
                                       ondone=ondone)
            hypo_obj.web_boss.wait(jid1)

            hypo_obj.webContentTypeSkipAdd('application/json')
            jid2 = hypo_obj.fireWebApi('fakeipify:jsonip',
                                       ondone=ondone)
            hypo_obj.web_boss.wait(jid2)

            hypo_obj.webContentTypeSkipDel('application/json')
            jid3 = hypo_obj.fireWebApi('fakeipify:jsonip',
                                       ondone=ondone)
            hypo_obj.web_boss.wait(jid3)

            self.true(jid1 in data)
            self.eq(data[jid1], type({}))
            self.true(jid2 in data)
            self.eq(data[jid2], type(b''))
            self.true(jid3 in data)
            self.eq(data[jid3], type({}))

    def test_hypnos_cache_job(self):
        # Ensure that job results are available via cache when caching is enabled.
        self.thisHostMustNot(platform='windows')
        gconf = get_fake_ipify_global_config(port=self.port)
        # testserver = Foo()

        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 2,
                                     s_remcycle.CACHE_ENABLED: True,
                                     },
                               ioloop=self.io_loop) as hypo_obj:  # type: s_remcycle.Hypnos
            hypo_obj.addWebConfig(config=gconf)

            jid1 = hypo_obj.fireWebApi('fakeipify:jsonip')
            self.false(jid1 in hypo_obj.web_cache)
            hypo_obj.web_boss.wait(jid=jid1)
            time.sleep(0.01)
            self.true(jid1 in hypo_obj.web_cache)
            cached_data = hypo_obj.webCacheGet(jid=jid1)
            self.true(isinstance(cached_data, dict))
            resp = cached_data.get('resp')
            self.true('data' in resp)
            # Cached response data is a bytes object
            data = json.loads(resp.get('data').decode())
            # This is expected data from the API endpoint.
            self.true('ret' in data)
            self.true('ip' in data.get('ret'))
            cached_data2 = hypo_obj.webCachePop(jid=jid1)
            self.eq(cached_data, cached_data2)
            self.false(jid1 in hypo_obj.web_cache)
            # Disable the cache and ensure the responses are cleared and no longer cached.
            hypo_obj.setConfOpt(s_remcycle.CACHE_ENABLED, False)
            self.false(jid1 in hypo_obj.web_cache)
            jid2 = hypo_obj.fireWebApi('fakeipify:jsonip')
            hypo_obj.web_boss.wait(jid=jid1)
            time.sleep(0.01)
            self.false(jid2 in hypo_obj.web_cache)
            cached_data3 = hypo_obj.webCachePop(jid=jid2)
            self.none(cached_data3)

    def test_hypnos_cache_with_ingest(self):
        # Ensure that the cached data from a result with a ingest definition is msgpack serializable.
        self.thisHostMustNot(platform='windows')
        # testserver = Foo()
        gconf = get_fake_ipify_ingest_global_config(port=self.port)

        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1,
                                     s_remcycle.CACHE_ENABLED: True},
                               ioloop=self.io_loop) as hypo_obj:  # type: s_remcycle.Hypnos
            hypo_obj.addWebConfig(config=gconf)

            jid = hypo_obj.fireWebApi(name='fakeipify:jsonip')
            job = hypo_obj.web_boss.job(jid=jid)
            hypo_obj.web_boss.wait(jid)
            cached_data = hypo_obj.webCacheGet(jid=jid)
            self.nn(cached_data)
            # Ensure the cached data can be msgpacked as needed.
            buf = s_msgpack.en(cached_data)
            self.true(isinstance(buf, bytes))
            # Ensure that the existing job tufo is untouched when caching.
            self.true('ingdata' in job[1].get('task')[2].get('resp'))

    def test_hypnos_cache_with_failure(self):
        # Test a simple failure case
        self.thisHostMustNot(platform='windows')

        gconf = get_fake_ipify_global_config(port=self.port)
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1,
                                     s_remcycle.CACHE_ENABLED: True},
                               ioloop=self.io_loop) as hypo_obj:  # type: s_remcycle.Hypnos
            hypo_obj.addWebConfig(config=gconf)

            jid = hypo_obj.fireWebApi(name='fakeipify:fake_endpoint')
            hypo_obj.web_boss.wait(jid)
            # Ensure that we have error information cached for the job
            cached_data = hypo_obj.webCacheGet(jid=jid)
            self.true('err' in cached_data)
            self.eq(cached_data.get('err'), 'HTTPError')
            self.true('errfile' in cached_data)
            self.true('errline' in cached_data)
            self.true('errmsg' in cached_data)

    def test_hypnos_post_byts(self):
        self.thisHostMustNot(platform='windows')

        testserver = self.env.testserver  # type: StandaloneTestServer
        self.false(testserver.nommer.nommed)
        byts = json.dumps({'foo': 'bar', 'baz': [1, 2, 3]}).encode()
        gconf = get_fake_ipify_global_config(port=self.port)
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1,
                                     },
                               ioloop=self.io_loop) as hypo_obj:  # type: s_remcycle.Hypnos
            hypo_obj.addWebConfig(config=gconf)

            jid = hypo_obj.fireWebApi(name='fakeipify:byts', api_args={'req_body': byts})
            job = hypo_obj.web_boss.job(jid=jid)[1]  # type: dict
            hypo_obj.web_boss.wait(jid)
            # Did the server actually nom a POST body?
            self.true(testserver.nommer.nommed)
            resp = job.get('task')[2].get('resp')  # type: dict
            self.eq(resp.get('code'), 200)
            self.true(resp.get('data').get('ret'))
