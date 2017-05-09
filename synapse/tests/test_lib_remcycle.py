import synapse.lib.remcycle as s_remcycle
import synapse.models.inet as s_inet

from synapse.tests.common import *

from tornado.testing import AsyncTestCase


def get_vertex_global_config():
    gconfig = {
        'apis': {
            'http': {
                'doc': 'Get the vertex project landing page.',
                'url': 'http://vertex.link/',
                'http': {'validate_cert': False}
            },
            'https': {
                'doc': 'Get the vertex project landing page.',
                'url': 'https://vertex.link/',
                'http': {'validate_cert': False}
            }
        },
        'doc': 'Grab Vertex.link stuff',
        'http': {
            'user_agent': 'ClownBrowser'
        },
        'namespace': 'vertexproject',
    }
    return gconfig


def get_bad_vertex_global_config():
    gconfig = {
        'apis': {
            'fake_endpoint': {
                'doc': 'Fake endpoint',
                'url': 'https://vertex.link/foo/bar/duck',
                'http': {'validate_cert': False}
            }
        },
        'doc': 'Grab Vertex.link stuff',
        'http': {
            'user_agent': 'ClownBrowser'
        },
        'namespace': 'vertexproject',
    }
    return gconfig


def get_ipify_global_config():
    gconfig = {
        'apis': {
            'jsonip': {
                'doc': 'Get IP in a JSON blob',
                'http': {
                    'validate_cert': False
                },
                'url': 'https://api.ipify.org?format=json',
            }
        },
        'doc': 'API for getting calling IP address',
        'http': {
            'user_agent': 'SynapseTest'
        },
        'namespace': 'ipify',
    }
    return gconfig


def get_ipify_ingest_global_config():
    gconfig = {
        'apis': {
            'jsonip': {
                'doc': 'Get IP in a JSON blob',
                'http': {
                    'validate_cert': False
                },
                'ingests': {
                    'ipv4': {
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
                        }
                    }
                },
                'url': 'https://api.ipify.org?format=json',
            }
        },
        'doc': 'API for getting calling IP address',
        'http': {
            'user_agent': 'SynapseTest'
        },
        'namespace': 'ipify',
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

    def test_nyx_tornado_http_values(self):
        # Ensure a few expected values are in the valid tornado arguments
        self.true('user_agent' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('headers' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('method' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('request_timeout' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('connect_timeout' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('auth_username' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('auth_password' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('auth_mode' in s_remcycle.VALID_TORNADO_HTTP_ARGS)
        self.true('validate_cert' in s_remcycle.VALID_TORNADO_HTTP_ARGS)

    def test_nyx_tornado_http_check(self):
        good_dict = {'method': 'PUT',
                     'user_agent': 'VertexWeb',
                     'headers': {'X-Derry': 'FriendlyClowns',
                                 'CSRF-Token': '1234'},
                     'request_timeout': 100,
                     'connect_timeout': 20,
                     }
        self.true(s_remcycle.validateHttpValues(vard=good_dict))

        # Duck typing
        with self.raises(AttributeError) as cm:
            s_remcycle.validateHttpValues('A string')
        self.true("""object has no attribute 'items'""" in str(cm.exception))

        bad_dict = {'method': 'PUT',
                    'user-agent': 'Lynx',  # Typo / misspelling
                    }

        with self.raises(Exception) as cm:
            s_remcycle.validateHttpValues(bad_dict)
        self.true('Varn is not a valid tornado arg' in str(cm.exception))

    def test_nyx_simple_config(self):
        nyx = s_remcycle.Nyx(config=self.config)
        e_url = 'http://vertex.link/api/v4/geoloc/{someplace}/info?domore={domore}&apikey=8675309'
        self.eq(nyx.effective_url, e_url)
        self.eq(nyx.api_args, ['someplace'])
        self.eq(nyx.api_kwargs, {'domore': 0})

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
        self.false(hypo_obj.core_provided)
        hypo_obj.fini()
        self.true(hypo_obj.isfini)
        self.true(hypo_obj.boss.isfini)
        self.false(hypo_obj.iothr.is_alive())
        self.true(hypo_obj.core.isfini)

    def test_hypnos_fini_core(self):
        # Ensure we don't tear down a Cortex provided to us by the constructor.
        core = s_cortex.openurl('ram:///')
        hypo_obj = s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                                     ioloop=self.io_loop, core=core)
        self.true(hypo_obj.core_provided)
        hypo_obj.fini()
        self.true(hypo_obj.isfini)
        self.true(hypo_obj.boss.isfini)
        self.false(hypo_obj.iothr.is_alive())
        self.false(hypo_obj.core.isfini)
        core.fini()
        self.true(hypo_obj.core.isfini)

    def test_hypnos_callback_ondone(self):
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj.apis)

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

            jid = hypo_obj.fireApi('ipify:jsonip',
                                   callback=cb,
                                   ondone=ondone)

            job = hypo_obj.boss.job(jid)
            hypo_obj.boss.wait(jid)
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

            hypo_obj.addConfig(config=vertex_conf)
            self.true('vertexproject' in hypo_obj.namespaces)
            self.true('vertexproject' in hypo_obj.docs)
            self.true(len(hypo_obj.apis) == 2)
            self.true('vertexproject:http' in hypo_obj.apis)
            self.true('vertexproject:https' in hypo_obj.apis)
            self.eq(dict(hypo_obj._api_ingests), {})

            hypo_obj.addConfig(config=ipify_conf)
            self.true('ipify' in hypo_obj.namespaces)
            self.true('ipify' in hypo_obj.docs)
            self.true(len(hypo_obj.namespaces) == 2)
            self.true(len(hypo_obj.apis) == 3)
            self.true('ipify:jsonip' in hypo_obj.apis)
            self.true('ipify:jsonip' in hypo_obj._api_ingests)
            self.true('ipify:jsonip' in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' in hypo_obj.core._syn_funcs)

            # Check repr!
            r = repr(hypo_obj)
            self.true('Hypnos' in r)
            self.true('vertexproject' in r)
            self.true('ipify' in r)
            self.true('synapse.cores.ram.Cortex' in r)

            # Ensure that if we remove everything when we dereregister a namespace
            hypo_obj.delConfig(namespace='ipify')
            self.true('ipify' not in hypo_obj.namespaces)
            self.true('ipify' not in hypo_obj.docs)
            self.true(len(hypo_obj.namespaces) == 1)
            self.true(len(hypo_obj.apis) == 2)
            self.true('ipify:jsonip' not in hypo_obj.apis)
            self.true('ipify:jsonip' not in hypo_obj._api_ingests)
            self.true('ipify:jsonip' not in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' not in hypo_obj.core._syn_funcs)

            # Trying to re-register a present namespace should fail
            with self.raises(NameError) as cm:
                hypo_obj.addConfig(config=vertex_conf)
            self.true('Namespace is already registered' in str(cm.exception))

            # Register ipfy again
            hypo_obj.addConfig(config=ipify_conf)
            self.true('ipify' in hypo_obj.namespaces)
            self.true('ipify' in hypo_obj.docs)
            self.true(len(hypo_obj.namespaces) == 2)
            self.true(len(hypo_obj.apis) == 3)
            self.true('ipify:jsonip' in hypo_obj.apis)
            self.true('ipify:jsonip' in hypo_obj._api_ingests)
            self.true('ipify:jsonip' in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' in hypo_obj.core._syn_funcs)

            # Now change something with ipify, register it and force a reload to occur
            api_def = ipify_conf['apis'].pop('jsonip')
            gest_def = api_def['ingests'].pop('ipv4')
            api_def['ingests']['foobar'] = gest_def
            ipify_conf['apis']['duckip'] = api_def

            hypo_obj.addConfig(config=ipify_conf, reload_config=True)

            self.true('ipify' in hypo_obj.namespaces)
            self.true('ipify' in hypo_obj.docs)
            self.true(len(hypo_obj.namespaces) == 2)
            self.true(len(hypo_obj.apis) == 3)
            self.true('ipify:jsonip' not in hypo_obj.apis)
            self.true('ipify:jsonip' not in hypo_obj._api_ingests)
            self.true('ipify:jsonip' not in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' not in hypo_obj.core._syn_funcs)
            self.true('ipify:duckip' in hypo_obj.apis)
            self.true('ipify:duckip' in hypo_obj._api_ingests)
            self.true('ipify:duckip' in hypo_obj._syn_funcs)
            self.true('ipify:duckip:foobar' in hypo_obj.core._syn_funcs)

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
                               oloop=self.io_loop) as hypo_obj:
            hypo_obj.addConfig(config=gconf)

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

            jid1 = hypo_obj.fireApi('vertexproject:http', 'foo', 'bar', key='12345', callback=cb)
            jid2 = hypo_obj.fireApi('vertexproject:http', 'foo', 'bar', key='67890', callback=cb)

            hypo_obj.boss.wait(jid=jid1)
            hypo_obj.boss.wait(jid=jid2)
            self.eq(d['set'], True)
            self.eq(d.get('keys'), {'12345', '67890'})

    def test_hypnos_default_callback(self):
        # Ensure that the default callback, of firing an event handler, works.
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1}, ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj.apis)

            def func(event_tufo):
                event_name, argdata = event_tufo
                kwargs = argdata.get('kwargs')
                resp = kwargs.get('resp')
                self.eq(resp.get('code'), 200)

            hypo_obj.on('ipify:jsonip', func=func)

            jid = hypo_obj.fireApi('ipify:jsonip')

            job = hypo_obj.boss.job(jid)
            hypo_obj.boss.wait(jid)
            self.true(job[1].get('done'))

    def test_hypnos_default_callback_null(self):
        # Ensure the Job is complete even if we have no explicit callback or
        # listening event handlers.
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj.apis)

            jid = hypo_obj.fireApi('ipify:jsonip')

            job = hypo_obj.boss.job(jid)
            hypo_obj.boss.wait(jid)
            self.true(job[1].get('done'))
            self.eq(job[1].get('task')[2].get('resp').get('code'), 200)

    def test_hypnos_manual_ingest_via_eventbus(self):
        # This is a manual setup of the core / ingest type of action.
        self.skipIfNoInternet()
        gconf = get_ipify_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addConfig(config=gconf)
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

            jid = hypo_obj.fireApi(name=name, ondone=ondone)
            hypo_obj.boss.wait(jid)

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
            hypo_obj.addConfig(config=gconf)

            self.true('ipify:jsonip' in hypo_obj._syn_funcs)
            self.true('ipify:jsonip:ipv4' in hypo_obj.core._syn_funcs)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                ip = jobd.get('task')[2].get('resp', {}).get('data', {}).get('ip', '')
                data[_jid] = ip

            jid = hypo_obj.fireApi(name='ipify:jsonip', ondone=ondone)
            hypo_obj.boss.wait(jid)

            tufos = hypo_obj.core.getTufosByProp('inet:ipv4')
            self.eq(len(tufos), 1)
            # Validate the IP of the tufo is the same we got from ipify
            self.eq(s_inet.ipv4str(tufos[0][1].get('inet:ipv4')), data[jid])

    def test_hypnos_throw_timeouts(self):
        # Run a test scenario which will generate hundreds of jobs which will timeout.
        self.skipTest(reason='This test can periodically cause coverage.py failures and even then may not run '
                             'sucessfully.')
        self.skipIfNoInternet()
        gconf = get_ipify_ingest_global_config()
        with s_remcycle.Hypnos(opts={s_remcycle.MIN_WORKER_THREADS: 1},
                               ioloop=self.io_loop) as hypo_obj:
            hypo_obj.addConfig(config=gconf)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                data[_jid] = jobd

            n = 500

            jids = []
            for i in range(n):
                jid = hypo_obj.fireApi(name='ipify:jsonip',
                                       ondone=ondone,
                                       request_args={'request_timeout': 0.6,
                                                     'connect_timeout': 0.3})
                jids.append(jid)
            for jid in jids:
                hypo_obj.boss.wait(jid)

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
            hypo_obj.addConfig(config=gconf)

            data = {}

            def ondone(job_tufo):
                _jid, jobd = job_tufo
                data[_jid] = jobd

            jid = hypo_obj.fireApi(name='vertexproject:fake_endpoint',
                                   ondone=ondone)
            hypo_obj.boss.wait(jid)
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
