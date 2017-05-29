from tornado.testing import AsyncTestCase
import synapse.daemon as s_daemon
import synapse.telepath as s_telepath
import synapse.models.inet as s_inet
import synapse.lib.remcycle as s_remcycle


from synapse.tests.common import *



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
            ]
        ],
        'doc': 'Grab Vertex.link stuff',
        'http': {
            'user_agent': 'ClownBrowser'
        },
        'namespace': 'vertexproject',
    }
    return gconfig

def get_bad_vertex_global_config():
    gconfig = {
        'apis': [
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

def get_ipify_global_config():
    gconfig = {
        'apis': [
            [
                'jsonip',
                {
                    'doc': 'Get IP in a JSON blob',
                    'http': {
                        'validate_cert': False
                    },
                    'url': 'https://api.ipify.org/?format=json',
                }
            ]
        ],
        'doc': 'API for getting calling IP address',
        'http': {
            'user_agent': 'SynapseTest'
        },
        'namespace': 'ipify',
    }
    return gconfig

def get_ipify_ingest_global_config():
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
                                                "path": "ip"
                                            }
                                        ]
                                    ]
                                },
                                'open': {
                                    'format': 'json'
                                }
                            }
                    },
                    'url': 'https://api.ipify.org/?format=json',
                }
            ]
        ],
        'doc': 'API for getting calling IP address',
        'http': {
            'user_agent': 'SynapseTest'
        },
        'namespace': 'ipify',
    }
    return gconfig

def get_generic_domain_global_config():
    gconfig = {
        'apis': [
            [
                'fqdn',
                {
                    'doc': 'Get arbitrary domain name.',
                    'http': {
                        'validate_cert': False
                    },
                    'url': 'https://{{fqdn}}/{{endpoint}}',
                    'api_args': ['fqdn'],
                    'api_optargs': {'endpoint': ''}
                }
            ]
        ],
        'doc': 'Definition for getting an arbitrary domain.',
        'http': {
            'user_agent': 'SynapseTest.RemCycle'
        },
        'namespace': 'generic',
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

    def test_nyx_tornado_http_check(self):
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

    def test_nyx_make_request(self):
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
        nyx = s_remcycle.Nyx(config=self.config)
        req = nyx.buildHttpRequest(api_args={'someplace': 'foo bar',
                                             'domore': 'eeep@foo.bar'})
        e_url = 'http://vertex.link/api/v4/geoloc/foo+bar/info?domore=eeep%40foo.bar&apikey=8675309'
        self.eq(req.url, e_url)

class HypnosTest(SynTest, AsyncTestCase):

    def test_hypnos_config_bounds(self):

        with self.raises(ValueError) as cm:
            hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 0},
                                         ioloop=self.io_loop)
        self.true('Bad pool configuration provided' in str(cm.exception))

        with self.raises(ValueError) as cm:
            hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MAX_WORKER_THREADS: 1,
                                               s_remcycle.MIN_WORKER_THREADS: 2},
                                         ioloop=self.io_loop)
        self.true('Bad pool configuration provided' in str(cm.exception))

    def test_hypnos_fini(self):
        # Ensure we call fini on all objects created by the core.
        hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                                     ioloop=self.io_loop)
        hypo_obj.fini()
        self.true(hypo_obj.isfini)
        self.true(hypo_obj.web_boss.isfini)
        self.false(hypo_obj.web_iothr.is_alive())
        self.true(hypo_obj.web_core.isfini)

    def test_hypnos_fini_core(self):
        # Ensure we don't tear down a Cortex provided to us by the constructor.
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
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj._web_apis)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                data[_jid] = jobd

            def cb(*args, **kwargs):
                resp = kwargs.get('resp')
                self.true(resp.get('code') == 200)
                body = resp.get('body')
                body = json.loads(body)
                self.true('ip' in body)

            jid = hypo_obj.fireWebApi('ipify:jsonip',
                                      callback=cb,
                                      ondone=ondone)

            job = hypo_obj.web_boss.job(jid)
            hypo_obj.web_boss.wait(jid)
            self.true(jid in data)
            self.true(job[1].get('done'))

    def test_hypnos_config_register_deregister(self):
        vertex_conf = get_vertex_global_config()
        ipify_conf = get_ipify_ingest_global_config()

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
            self.true(len(hypo_obj._web_apis) == 2)
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
            self.true('ipify' in hypo_obj._web_namespaces)
            self.true('ipify' in hypo_obj._web_docs)
            self.true(len(hypo_obj._web_namespaces) == 2)
            self.true(len(hypo_obj._web_apis) == 3)
            self.true('ipify:jsonip' in hypo_obj._web_apis)
            self.true('ipify:jsonip' in hypo_obj._web_api_ingests)
            self.true('ipify:jsonip' in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' in hypo_obj.web_core._syn_funcs)

            # Check repr!
            r = repr(hypo_obj)
            self.true('Hypnos' in r)
            self.true('vertexproject' in r)
            self.true('ipify' in r)
            self.true('synapse.cores.ram.Cortex' in r)

            # Ensure that if we remove everything when we dereregister a namespace
            hypo_obj.delWebConf(namespace='ipify')
            self.true('ipify' not in hypo_obj._web_namespaces)
            self.true('ipify' not in hypo_obj._web_docs)
            self.true(len(hypo_obj._web_namespaces) == 1)
            self.true(len(hypo_obj._web_apis) == 2)
            self.true('ipify:jsonip' not in hypo_obj._web_apis)
            self.true('ipify:jsonip' not in hypo_obj._web_api_ingests)
            self.true('ipify:jsonip' not in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' not in hypo_obj.web_core._syn_funcs)

            # Trying to re-register a present namespace should fail
            with self.raises(NameError) as cm:
                hypo_obj.addWebConfig(config=vertex_conf, reload_config=False)
            self.true('Namespace is already registered' in str(cm.exception))

            # Register ipfy again
            hypo_obj.addWebConfig(config=ipify_conf)
            self.true('ipify' in hypo_obj._web_namespaces)
            self.true('ipify' in hypo_obj._web_docs)
            self.true(len(hypo_obj._web_namespaces) == 2)
            self.true(len(hypo_obj._web_apis) == 3)
            self.true('ipify:jsonip' in hypo_obj._web_apis)
            self.true('ipify:jsonip' in hypo_obj._web_api_ingests)
            self.true('ipify:jsonip' in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' in hypo_obj.web_core._syn_funcs)
            self.true('ipify:jsonip' in hypo_obj._web_api_gest_opens)

            # Now change something with ipify, register it and force a reload to occur
            api_def = ipify_conf['apis'].pop(0)
            gest_def = api_def[1]['ingest']
            gest_def['name'] = 'foobar'
            ipify_conf['apis'].append(['duckip', api_def[1]])

            hypo_obj.addWebConfig(config=ipify_conf)

            self.true('ipify' in hypo_obj._web_namespaces)
            self.true('ipify' in hypo_obj._web_docs)
            self.true(len(hypo_obj._web_namespaces) == 2)
            self.true(len(hypo_obj._web_apis) == 3)
            self.true('ipify:jsonip' not in hypo_obj._web_apis)
            self.true('ipify:jsonip' not in hypo_obj._web_api_ingests)
            self.true('ipify:jsonip' not in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' not in hypo_obj.web_core._syn_funcs)
            self.true('ipify:jsonip' not in hypo_obj._web_api_gest_opens)
            self.true('ipify:duckip' in hypo_obj._web_apis)
            self.true('ipify:duckip' in hypo_obj._web_api_ingests)
            self.true('ipify:duckip' in hypo_obj._syn_funcs)
            self.true('ipify:duckip:foobar' in hypo_obj.web_core._syn_funcs)
            self.true('ipify:duckip' in hypo_obj._web_api_gest_opens)

        # ensure all the expected events fired during testing
        self.true('hypnos:register:namespace:add' in data)
        self.true('hypnos:register:namespace:del' in data)
        self.true('hypnos:register:api:add' in data)
        self.true('hypnos:register:api:del' in data)

    def test_hypnos_fire_api_callback(self):
        # Ensure that the provided callback is fired and args are passed to the callbacks.
        self.skipIfNoInternet()
        gconf = get_vertex_global_config()
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

            jid1 = hypo_obj.fireWebApi('vertexproject:http', 'foo', 'bar', key='12345', callback=cb)
            jid2 = hypo_obj.fireWebApi('vertexproject:http', 'foo', 'bar', key='67890', callback=cb)

            hypo_obj.web_boss.wait(jid=jid1)
            hypo_obj.web_boss.wait(jid=jid2)
            self.eq(d['set'], True)
            self.eq(d.get('keys'), {'12345', '67890'})

    def test_hypnos_default_callback(self):
        # Ensure that the default callback, of firing an event handler, works.
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1}, ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj._web_apis)

            def func(event_tufo):
                event_name, argdata = event_tufo
                kwargs = argdata.get('kwargs')
                resp = kwargs.get('resp')
                self.eq(resp.get('code'), 200)

            hypo_obj.on('ipify:jsonip', func=func)

            jid = hypo_obj.fireWebApi('ipify:jsonip')

            job = hypo_obj.web_boss.job(jid)
            hypo_obj.web_boss.wait(jid)
            self.true(job[1].get('done'))

    def test_hypnos_default_callback_null(self):
        # Ensure the Job is complete even if we have no explicit callback or
        # listening event handlers.
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj._web_apis)

            jid = hypo_obj.fireWebApi('ipify:jsonip')

            job = hypo_obj.web_boss.job(jid)
            hypo_obj.web_boss.wait(jid)
            self.true(job[1].get('done'))
            self.eq(job[1].get('task')[2].get('resp').get('code'), 200)

    def test_hypnos_manual_ingest_via_eventbus(self):
        # This is a manual setup of the core / ingest type of action.
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)
            core = s_cortex.openurl('ram://')

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
                                "path": "ip"
                            }
                        ]
                    ]
                }
            }

            name = 'ipify:jsonip'
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
                ip = jobd.get('task')[2].get('resp', {}).get('data', {}).get('ip', '')
                data[_jid] = ip

            hypo_obj.on(name=name, func=glue)

            jid = hypo_obj.fireWebApi(name=name, ondone=ondone)
            hypo_obj.web_boss.wait(jid)

            tufos = core.getTufosByProp('inet:ipv4')
            self.eq(len(tufos), 1)
            # Validate the IP of the tufo is the same we got from ipify
            self.eq(s_inet.ipv4str(tufos[0][1].get('inet:ipv4')), data[jid])

        core.fini()

    def test_hypnos_automatic_ingest(self):
        # Ensure that a configuration object with a ingest definition is automatically parsed.
        self.skipIfNoInternet()
        gconf = get_ipify_ingest_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' in hypo_obj.web_core._syn_funcs)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                _data = jobd.get('task')[2].get('resp', {}).get('data')
                _bytez = _data.read()
                _d = json.loads(_bytez.decode())
                data[_jid] = _d.get('ip')

            jid = hypo_obj.fireWebApi(name='ipify:jsonip', ondone=ondone)
            hypo_obj.web_boss.wait(jid)

            tufos = hypo_obj.web_core.getTufosByProp('inet:ipv4')
            self.eq(len(tufos), 1)
            # Validate the IP of the tufo is the same we got from ipify
            self.nn(data[jid])
            self.eq(s_inet.ipv4str(tufos[0][1].get('inet:ipv4')), data[jid])

    def test_hypnos_throw_timeouts(self):
        # Run a test scenario which will generate hundreds of jobs which will timeout.
        self.skipTest(reason='This test can periodically cause coverage.py failures and even then may not run '
                             'sucessfully.')
        self.skipIfNoInternet()
        gconf = get_ipify_ingest_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                data[_jid] = jobd

            n = 500

            jids = []
            for i in range(n):
                jid = hypo_obj.fireWebApi(name='ipify:jsonip',
                                          ondone=ondone,
                                          request_args={'request_timeout': 0.6,
                                                     'connect_timeout': 0.3})
                jids.append(jid)
            for jid in jids:
                hypo_obj.web_boss.wait(jid)

            completed_jobs = {jid: d for jid, d in data.items() if 'ret' in d}
            error_jobs = {jid: d for jid, d in data.items() if 'ret' not in d}
            self.true(len(completed_jobs) > 1)
            self.true(len(error_jobs) > 1)
            bad_job = list(error_jobs.values())[0]
            # Ensure that we have error information propogated up to the job
            self.true('err' in bad_job)
            self.true('errfile' in bad_job)
            self.true('errline' in bad_job)
            self.true('errmsg' in bad_job)

            # The following are error messages which are expected
            e_messages = ['HTTP 599: Timeout in request queue',
                          'HTTP 599: Timeout while connecting',
                          'HTTP 599: Timeout during request']
            error_messages = {d.get('errmsg') for d in error_jobs.values()}
            i = 0
            for msg in e_messages:
                if msg in error_messages:
                    i = i + 1
            # Expect 2-3 of the error messages to exist.
            self.true(0 < i < 4)

    def test_hypnos_simple_fail(self):
        # Test a simple failure case
        self.skipIfNoInternet()
        gconf = get_bad_vertex_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                data[_jid] = jobd

            jid = hypo_obj.fireWebApi(name='vertexproject:fake_endpoint',
                                      ondone=ondone)
            hypo_obj.web_boss.wait(jid)
            job = data.get(jid)

            # Ensure that we have error information propogated up to the job
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

    def test_hypnos_generic_config(self):
        # Test hypnos with a generic config which allows the user to request
        # arbitrary fqdns and paths. This is really example code.
        self.skipIfNoInternet()

        fqdns = [('www.google.com', ''),
                 ('www.cnn.com', ''),
                 ('www.vertex.link', ''),
                 ('www.reddit.com', ''),
                 ('www.foxnews.com', ''),
                 ('www.msnbc.com', ''),
                 ('www.bbc.co.uk', ''),
                 ('www.amazon.com', ''),
                 ('www.paypal.com', ''),
                 ]

        outp = s_output.OutPutStr()

        def func(event_tufo):
            event_name, argdata = event_tufo
            kwargs = argdata.get('kwargs')
            resp = kwargs.get('resp')
            msg = 'Asked for [{}], got [{}] with code {}'.format(resp.get('request').get('url'),
                                                                 resp.get('effective_url'),
                                                                 resp.get('code')
                                                                 )
            outp.printf(msg)

        gconf = get_generic_domain_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 4},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)
            hypo_obj.on('generic:fqdn', func)

            job_ids = []
            for fqdn, endpoint in fqdns:
                jid = hypo_obj.fireWebApi('generic:fqdn',
                                          api_args={'fqdn': fqdn, 'endpoint': endpoint},
                                          )
                job_ids.append(jid)

            for jid in job_ids:
                hypo_obj.web_boss.wait(jid)

            mesgs = str(outp)
            for fqdn, _ in fqdns:
                self.true(fqdn in mesgs)

    def test_hypnos_with_telepath(self):
        # Setup the Hypnos object using telepath, then get the proxy object and
        # issue the fireWebApi calls via telepath, validate that they worked
        # against ingested tufo in the hypnos cortex. Use daemon to handle
        # telepath proxying.
        self.skipIfNoInternet()

        gconf = get_ipify_ingest_global_config()
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
                'tcp://127.0.0.1:50000'
            ]
        }

        dmon = s_daemon.Daemon()
        dmon.loadDmonConf(dconf)

        hypnos_proxy = s_telepath.openurl('tcp://127.0.0.1:50000/hypnos')
        core_proxy = s_telepath.openurl('tcp://127.0.0.1:50000/core')
        # Lets do a remote config load!
        hypnos_proxy.addWebConfig(config=gconf)

        description = hypnos_proxy.getWebDescription()
        self.true('ipify' in description)
        # Fire the
        jid = hypnos_proxy.fireWebApi(name='ipify:jsonip')
        self.nn(jid)
        hypnos_proxy.webJobWait(jid)
        tufos = core_proxy.getTufosByProp('inet:ipv4')
        self.eq(len(tufos), 1)
        ip = s_inet.ipv4str(tufos[0][1].get('inet:ipv4'))
        self.true(len(ip) >= 7)

    def test_hypnos_content_type_skips(self):
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj._web_apis)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                resp_data = jobd.get('task')[2].get('resp').get('data')
                data[_jid] = type(resp_data)

            jid1 = hypo_obj.fireWebApi('ipify:jsonip',
                                       ondone=ondone)
            hypo_obj.web_boss.wait(jid1)

            hypo_obj.webContentTypeSkipAdd('application/json')
            jid2 = hypo_obj.fireWebApi('ipify:jsonip',
                                       ondone=ondone)
            hypo_obj.web_boss.wait(jid2)

            hypo_obj.webContentTypeSkipDel('application/json')
            jid3 = hypo_obj.fireWebApi('ipify:jsonip',
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
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 2,
                                     s_remcycle.CACHE_ENABLED: True},
                               ioloop=self.io_loop) as hypo_obj:  # type: s_remcycle.Hypnos
            hypo_obj.addWebConfig(config=gconf)

            jid1 = hypo_obj.fireWebApi('ipify:jsonip')
            self.false(jid1 in hypo_obj.web_cache)
            hypo_obj.web_boss.wait(jid=jid1)
            time.sleep(0.01)
            self.true(jid1 in hypo_obj.web_cache)
            cached_data = hypo_obj.getWebCachedReponse(jid=jid1)
            self.true(isinstance(cached_data, dict))
            resp = cached_data.get('resp')
            self.true('data' in resp)
            data = resp.get('data')
            # This is expected data from the API endpoint.
            self.true('ip' in data)
            cached_data2 = hypo_obj.delWebCachedResponse(jid=jid1)
            self.eq(cached_data, cached_data2)
            self.false(jid1 in hypo_obj.web_cache)
            # Disable the cache and ensure the responses are cleared and no longer cached.
            hypo_obj.webCacheDisable()
            self.false(jid1 in hypo_obj.web_cache)
            jid2 = hypo_obj.fireWebApi('ipify:jsonip')
            hypo_obj.web_boss.wait(jid=jid1)
            time.sleep(0.01)
            self.false(jid2 in hypo_obj.web_cache)
            cached_data3 = hypo_obj.delWebCachedResponse(jid=jid2)
            self.none(cached_data3)

    def test_hypnos_cache_with_ingest(self):
        # Ensure that the cached data from a result with a ingest definition is msgpack serializable.
        self.skipIfNoInternet()
        gconf = get_ipify_ingest_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1,
                                     s_remcycle.CACHE_ENABLED: True},
                               ioloop=self.io_loop) as hypo_obj:  # type: s_remcycle.Hypnos
            hypo_obj.addWebConfig(config=gconf)

            jid = hypo_obj.fireWebApi(name='ipify:jsonip')
            job = hypo_obj.web_boss.job(jid=jid)
            hypo_obj.web_boss.wait(jid)
            time.sleep(0.01)
            cached_data = hypo_obj.getWebCachedReponse(jid=jid)
            self.nn(cached_data)
            # Ensure the cached data can be msgpacked as needed.
            buf = msgenpack(cached_data)
            self.true(isinstance(buf, bytes))
            # Ensure that the existing job tufo is untouched when caching.
            self.true('ingdata' in job[1].get('task')[2].get('resp'))

    def test_hypnos_cached_failure(self):
        # Test a simple failure case
        self.skipIfNoInternet()
        gconf = get_bad_vertex_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1,
                                     s_remcycle.CACHE_ENABLED: True},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addWebConfig(config=gconf)

            jid = hypo_obj.fireWebApi(name='vertexproject:fake_endpoint')
            job = hypo_obj.web_boss.job(jid=jid)[1]  # type: dict
            hypo_obj.web_boss.wait(jid)
            # Ensure that we have error information cached for the job
            time.sleep(0.01)
            cached_data = hypo_obj.getWebCachedReponse(jid=jid)
            self.true('err' in cached_data)
            self.eq(cached_data.get('err'), 'HTTPError')
            self.true('errfile' in cached_data)
            self.true('errline' in cached_data)
            self.true('errmsg' in cached_data)
