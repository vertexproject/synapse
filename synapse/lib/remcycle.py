#!/usr/bin/env python
# -*- coding: utf-8 -*-
# synapse - remcycle.py
# Created on 4/28/17.
'''
Remcycle provides a mechanism for kicking off asynchronous HTTP(S) requests
via Tornado's AsyncHTTPClient.

A method for templating URL endpoints, providing default configuration values
and user set configuration values, per request, is available.  In addition,
data can also be ingested into a cortex (provided, or a default ram cortex)
for immediate consumption.

These requests are handled by Hypnos objects, which can have a single or
multiple definitions snapped into them in order to grab data on demand.
Hypnos grabs these requests with a single IO thread, and offloads the
consumption of the data to multiple worker threads.
'''
# Stdlib
import cgi
import logging
import collections
# Third Party Code
import tornado.ioloop as t_ioloop
import tornado.httpclient as t_http
# Custom Code
import synapse.async as s_async
import synapse.compat as s_compat
import synapse.cortex as s_cortex
import synapse.lib.ingest as s_ingest
import synapse.lib.config as s_config
import synapse.lib.threads as s_threads

from synapse.common import *

logger = logging.getLogger(__name__)

MIN_WORKER_THREADS = 'min_worker_threads'
MAX_WORKER_THREADS = 'max_worker_threads'
HYPNOS_BASE_DEFS = (
    (MIN_WORKER_THREADS, {'type': 'int', 'doc': 'Minimum number of worker threads to spawn', 'defval': 8}),
    (MAX_WORKER_THREADS, {'type': 'int', 'doc': 'Maximum number of worker threads to spawn', 'defval': 64}),
)

class Nyx(object):
    '''
    Configuration parser & request generator for a REST service.

    This class is responsible for doing the actual HTTPRequest generation
    in a parameterized fashion for a given input.

    The API configuration is expected to be a dictionary with the expected
    values:

        * doc: Human readable description of the current API endpoint.
        * url: This is the actual URL which will be used to connect to a
          service.  This string will be run through format() twice - once
          during the construction of the Nyx object, and the second time
          during the construction of the per-request url. As such, any
          values set by the api_args and api_optargs configuration methods
          noted below should be enclosed with double curly brackets.

    The following configuration values are optional for a Nyx configuration.

        * api_args: This is a list of values which must be provided by the
          user when they call buildHttpRequest. These would represent URL
          parameters which are required to be provided by the user each time
          a new HTTPRequest object is built.
        * api_optargs: This is a dictionary of URL parameters which are
          are optional for the user to provide when calling buildHttpRequest.
          This dictionary represents the parameter names and default values
          for them.  A user may provide alternative values when calling 
          buildHttpRequest, but sensible defaults should be provided here.
        * http: A dictionary of key/value items which can provide per-api
          specific arguements for the creation of HTTPRequest objects. These
          values should conform to the Tornado HTTPRequest constructor.
        * ingests: A sequence, containing Synapse ingest definitions which 
          will be used to create Ingest objects.  During registration of a
          Nyx object with Hypnos, these will be registered into the Hypnos
          cortex. Multiple named ingests may be made available for a single 
          API.  This sequence should contain two value pairs, the first is the
          name given for the individual ingest, the second is the ingest
          definition itself.
        * vars: This is a dictionary of items which are stamped into the url
          template during the construction of the Nyx object using format().

    See a complete example below:

    ::

        {
          "api_args": [
            "someplace"
          ],
          "api_optargs": {
            "domore": 0
          },
          "doc": "api example",
          "http": {
            "headers": {
              "token-goodness": "sekrit token"
            }
          },
          "ingests": [
            [
              "ingest_definition",
              {
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
            ]
          ],
          "url": "http://vertex.link/api/v4/geoloc/{{someplace}}/info?domore={{domore}}&apikey={APIKEY}",
          "vars": {
            "APIKEY": "8675309"
          }
        }

    ::

    This example should be interpreted as the following:

        1. The APIKEY value in the 'vars' will be set in the URL, resulting in
           the following default url:

        ::

            "http://vertex.link/api/v4/geoloc/{someplace}/info?domore={domore}&apikey=8675309"

        ::

        2. The HTTP request will have the header "token-goodness" set to
           "sekrit token" for the request.
        3. The caller must provide the "someplace" value in the api_args when
           calling buildHttpRequest.  The caller may provide the "domore"
           value if they want to override the default value of "0".
        4. An Ingest will be created for parsing the data from the API and
           made available to the Hypnos object.

    :param config: API Endpoint configuration outlined above.
    '''

    def __init__(self, config):
        self._raw_config = dict(config)
        self.required_keys = ['url',
                              'doc'
                              ]
        self.doc = ''
        self.url_template = ''
        self.url_vars = {}
        self.effective_url = ''
        self.request_defaults = {}
        self.api_args = []
        self.api_kwargs = {}
        self.gests = {}

        self._parse_config()

    @property
    def description(self):
        '''
        Get a dictionary containing an objects docstring, required api_args
        and optional api args.

        :return: Dictionary contiaining data.
        '''
        # Make copies of object so the returned multable dictionary does not
        # affect the
        d = {'doc': str(self.doc),
             'api_args': list(self.api_args),
             'api_optargs': self.api_kwargs.copy(),
             }
        return d

    def _parse_config(self):
        for key in self.required_keys:
            if key not in self._raw_config:
                logger.error('Remcycle config is missing a required value %s.', key)
                raise NoSuchName(name=key, mesg='Missing required key.')
        self.url_template = self._raw_config.get('url')
        self.doc = self._raw_config.get('doc')

        self.url_vars.update(self._raw_config.get('vars', {}))
        self.request_defaults = self._raw_config.get('http', {})
        _gests = {k: s_ingest.Ingest(v) for k, v in self._raw_config.get('ingests', [])}
        self.gests.update(_gests)

        self.api_args.extend(self._raw_config.get('api_args', []))
        self.api_kwargs.update(self._raw_config.get('api_optargs', {}))

        # Set effective url
        self.effective_url = self.url_template.format(**self.url_vars)

    def buildHttpRequest(self,
                         api_args=None):
        '''
        Build the HTTPRequest object for a given configuration.

        :param api_args: Arguments support either required or optional URL
                         values.
        :return: tornado.httpclient.HTTPRequest object with the configured
                 url and attributes.
        :raises: NoSuchName if the api_args is missing a required API value.
        '''
        t_args = {}
        for argn in self.api_args:
            argv = api_args.get(argn, novalu)
            if argv is novalu:
                logger.error('Missing argument: %s', argn)
                raise NoSuchName(name=argn, mesg='Missing an expected argument')
            t_args[argn] = s_compat.url_quote_plus(str(argv))
        for argn, defval in self.api_kwargs.items():
            t_args[argn] = s_compat.url_quote_plus(str(api_args.get(argn, defval)))
        url = self.effective_url.format(**t_args)
        req = t_http.HTTPRequest(url, **self.request_defaults)
        return req

class Hypnos(s_config.Config):
    '''
    Object for grabbing a bunch of HTTP(S) data and consuming it via callbacks
    or ingest definitions.  Users can register multiple namespaces, each with
    their own set of API endpoints configured with them.  See the fire_api()
    function for details on retrieving data with Hypnos.

    The Hypnos object inherits from the Config object, and as such has both
    configable parameters and an EventBus available for message passing.

    The following items may be passed via kwargs to change the Hypnos object
    behavior:

        * ioloop: Tornado ioloop used by the IO thread. This would normally
                  be left unset, and an ioloop will be created for the io
                  thread. This is provided as a helper for testing.

    :param core: Cortex used to store ingest data.  By default, a ram cortex
                 is used.
    :param opts: Opts applied to the object via the Config interface.
    :param defs: Default options applied to the object via the Config
                 interface.  Generally this would not be overridden.
    '''

    def __init__(self,
                 core=None,
                 opts=None,
                 defs=HYPNOS_BASE_DEFS,
                 *args,
                 **kwargs):
        s_config.Config.__init__(self,
                                 opts,
                                 defs)

        self.required_keys = ('namespace', 'doc', 'apis')

        self.apis = {}
        self.namespaces = set([])
        self.docs = {}
        self.global_request_headers = {}  # Global request headers per namespace

        # Check configable options before we spin up any resources
        pool_min = self.getConfOpt(MIN_WORKER_THREADS)
        pool_max = self.getConfOpt(MAX_WORKER_THREADS)
        if pool_min < 1 or pool_max < pool_min:
            raise ValueError('Bad pool configuration provided.')

        # Tornado Async
        loop = kwargs.get('ioloop')
        if loop is None:
            loop = t_ioloop.IOLoop()
        self.loop = loop
        self.client = t_http.AsyncHTTPClient(io_loop=self.loop)
        self.iothr = self._runIoLoop()

        # Synapse Async and thread pool
        self.boss = s_async.Boss()
        self.pool = s_threads.Pool(pool_min, pool_max)

        # Synapse Core and ingest tracking
        if core is None:
            core = s_cortex.openurl('ram://')
            self.onfini(core.fini)
        self.core = core
        self._api_ingests = collections.defaultdict(list)

        # Setup Fini handlers
        self.onfini(self._onHypoFini)

    def __repr__(self):
        d = {'name': self.__class__.__name__,
             'loc': hex(id(self)),
             'ns': list(self.namespaces),
             'core': self.core,
             }
        s = '<{name} at {loc}, namespaces: {ns}, core: {core}>'.format(**d)
        return s

    @s_threads.firethread
    def _runIoLoop(self):
        self.loop.start()

    def _onHypoFini(self):
        # Stop the IOLoop async thread
        self.loop.stop()
        self.iothr.join()
        # Stop the boss making jobs
        self.boss.fini()
        # Stop the consuming pool
        self.pool.fini()

    def getWebDescription(self):
        '''
        Get a dictionary containing all namespaces, their docstrings, and
        registered api data.

        :return: Dictionary describing the regsistered namespace API data.
        '''
        return self._webDescription

    @property
    def _webDescription(self):
        '''
        Get a dictionary containing all namespaces, their docstrings, and
        registered api data.

        :return: Dictionary describing the regsistered namespace API data.
        '''
        # Make copies of object so the returned multable dictionary does not
        # affect the
        d = {}
        for ns in self.namespaces:
            nsd = {'doc': self.docs[ns]}
            for api_name, api_obj in self.apis.items():
                nsd[api_name] = api_obj.description
            if nsd:
                d[ns] = nsd
        return d

    def addWebConfig(self, config, reload_config=True):
        '''
        Register a configuration into a Hypnos object.

        The Hypnos object can accept a configuration object shaped like the following:

        ::

            {
              "apis": [
                [
                  "geoloc",
                  {
                    "api_args": [
                      "someplace"
                    ],
                    "api_optargs": {
                      "domore": 0
                    },
                    "doc": "apiexample",
                    "http": {
                      "headers": {
                        "token-goodness": "sekrittoken"
                      }
                    },
                    "ingests": [
                      [
                        "ingest_definition",
                        {
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
                      ]
                    ],
                    "url": "http://vertex.link/api/v4/geoloc/{{someplace}}/info?domore={{domore}}&apikey={APIKEY}",
                    "vars": [
                      [
                        "APIKEY",
                        "8675309"
                      ]
                    ]
                  }
                ],
                [
                  "https",
                  {
                    "doc": "Getthevertexprojectlandingpage.",
                    "http": {
                      "validate_cert": false
                    },
                    "url": "https://vertex.link/"
                  }
                ]
              ],
              "doc": "GrabVertex.linkstuff",
              "http": {
                "user_agent": "TotallyNotaPythonapplication."
              },
              "namespace": "vertexproject"
            }

        ::

        The following keys are required:

            * namespace: String identifier for all APIs present in the
              configuration.  Must be locally unique.
            * doc: Simple string describing the overall namespace.
            * apis: Sequence containing containing configuration values for
              API endpoints. See Nyx object for details of how this data
              should be shaped. The sequence should contain two value pairs
              of data. The first value should be the name of the API, while
              the second value is the actual API configuration. The name of
              the API, when joined with the namespace, forms the name the API
              can be called with for for later use.  Given the example above,
              the following APIs would be registered:
                - vertexproject:geoloc
                - vertexproject:https

        The following keys are optional:

            * http: Global HTTP Request arguments which will be the basis
              for creating HTTPRequest objects. These values should conform to
              the Tornado HTTPRequest constructor.


        :param config: Dictionary containing the configuration information.
        :param reload_config: If true and the namespace is already registered,
                              the existing namespace will be removed and the new
                              config added.
        :return: None
        :raises: NameError if the existing namespace is registered or a
                 invalid HTTP value is provided.
        :raises: Other exceptions are possible if the configuration isn't
                 shaped properly, this would likely come from duck typing.
        '''
        try:
            self._parseWebConf(config, reload_config)
        except Exception as e:
            logger.exception('Failed to process configuration')
            raise e

    def _parseWebConf(self, config, reload_config):

        for key in self.required_keys:
            if key not in config:
                logger.error('Remcycle config is missing a required value %s.', key)
                raise NoSuchName(name=key, mesg='Missing required key.')

        _apis = config.get('apis')
        _namespace = config.get('namespace')
        _doc = config.get('doc')

        if _namespace in self.namespaces:
            if reload_config:
                self.delWebConf(_namespace)
            else:
                raise NameError('Namespace is already registered.')

        self.docs[_namespace] = _doc
        self.global_request_headers[_namespace] = {k: v for k,v in config.get('http', {}).items()}

        # Register APIs
        for varn, val in _apis:
            name = ':'.join([_namespace, varn])
            # Stamp api http config ontop of global config, then stamp it into the API config
            _http = self.global_request_headers[_namespace].copy()
            _http.update(val.get('http', {}))
            val['http'] = _http
            nyx_obj = Nyx(val)
            self._registerWebApi(name, nyx_obj)
        self.namespaces.add(_namespace)

        self.fire('hypnos:register:namespace:add', namespace=_namespace)

    def _registerWebApi(self, name, obj):
        '''
        Register a Nyx object and any corresponding ingest definitions to the
        cortex.
        '''
        if name in self.apis:
            raise NameError('Already registered {}'.format(name))
        self.apis[name] = obj
        for gest_name, gest in obj.gests.items():
            action_name = ':'.join([name, gest_name])
            # Register the action with the attached cortex
            ingest_func = s_ingest.register_ingest(self.core,
                                                   gest,
                                                   action_name,
                                                   True
                                                   )

            def gest_glue(event):
                evtname, event_args = event
                kwargs = event_args.get('kwargs')
                resp = kwargs.get('resp')
                data = resp.get('data')
                self.core.fire(action_name, data=data)

            # Register the action to unpack the async.Boss job results and fire the cortex event
            self.on(name, gest_glue)

            # Store things for later reuse (for deregistartion)
            self._api_ingests[name].append((action_name, ingest_func, gest_glue))

        self.fire('hypnos:register:api:add', api=name)

    def delWebConf(self, namespace):
        '''
        Remove a given namespace, APIs and any corresponding event handlers
        which have been snapped into the Hypnos object and its cortex via
        the register_config API.

        :param namespace: Namespace of objects to remove.
        :return: None
        :raises: NoSuchName if the namespace requested does not exist.
        '''

        if namespace not in self.namespaces:
            raise NoSuchName('Namespace is not registered.')

        self.namespaces.remove(namespace)
        self.docs.pop(namespace, None)
        self.global_request_headers.pop(namespace, None)

        apis_to_remove = []
        for api_name in list(self.apis.keys()):
            ns, name = api_name.split(':', 1)
            if ns == namespace:
                apis_to_remove.append(api_name)

        for api_name in apis_to_remove:
            self._delWebApi(api_name)

        self.fire('hypnos:register:namespace:del', namespace=namespace)

    def _delWebApi(self, name):
        if name not in self.apis:
            raise NoSuchName(name=name, mesg='API name not registered.')

        self.apis.pop(name, None)

        funclist = self._api_ingests.pop(name, [])
        for action_name, ingest_func, gest_glue in funclist:
            self.off(name, gest_glue)
            self.core.off(action_name, ingest_func)

        self.fire('hypnos:register:api:del', api=name)

    def getNyxApi(self, name):
        '''
        Get the Nyx object corresponding to a given API name.

        :param name: Name of the API to get the object for.
        :return: A Nyx object.
        '''
        nyx = self.apis.get(name)
        return nyx

    @staticmethod
    def _webFlattenHttpResponse(resp):
        '''Flatten the Tornado HTTPResponse object to a dictionary.'''
        resp_dict = {
            'request': {'url': resp.request.url,
                        'headers': dict(resp.request.headers)}
        }
        error = resp.error
        if error and not isinstance(error, t_http.HTTPError):
            return resp_dict
        resp_dict.update({'code': resp.code,
                          'raw_body': resp.body,
                          'headers': dict(resp.headers),
                          'effective_url': resp.effective_url, })
        if not resp.body:
            return resp_dict
        ct = resp.headers.get('Content-Type', 'text/plain')
        ct_type, ct_params = cgi.parse_header(ct)
        charset = ct_params.get('charset', 'utf-8').lower()
        try:
            resp_dict['data'] = resp_dict.get('raw_body').decode(charset)
        except Exception as e:
            logger.exception('Failed to decode a raw body in a response object.')
            return resp_dict
        # Handle known content types and put them in the 'data' key
        # we can add support for additional data types as needed.
        if ct_type.lower() == 'application/json':
            resp_dict['data'] = json.loads(resp_dict.get('data'))
        return resp_dict

    def _webRespFailWrapper(self, f):
        '''Decorator for wrapping callback functions to check for exception information.'''

        def check_job_fail(*fargs, **fkwargs):
            _excinfo = fkwargs.get('excinfo')
            if _excinfo:
                _jid = fkwargs.get('jid')
                self.boss.err(_jid, **_excinfo)
            else:
                f(*fargs, **fkwargs)

        return check_job_fail

    def fireWebApi(self, name, *args, **kwargs):
        '''
        Fire a request to a registered API.

        The API response is serviced by a thread in the Hypnos thread pool,
        which will fire either an event on the Hypnos service bus or a caller
        provided callback function.  The default action is to fire an event
        on the service bus with the same name as the API itself.

        A flattened version of the response, error information and the Boss
        job id will be stamped into the kwargs passed along to the the
        callbacks.

        The flattened response is a dictionary, accessed from kwargs using
        the 'resp' key. It contains the following information:

            * request: A dictionary containing the requested URL and headers.
              This is guaranteed to exist.  It has the following values:
                - url: URL requested by the remote server.
                - headers: Headers passed to the remote server.
            * code: HTTP Response code.  This will only be present on a
              successfull request or if a HTTPError is encountered.
            * raw_body: The raw bytes of the reponse.  This will only be
              present on a successful request or if a HTTPError is
              encountered.
            * effective_url: The effective url returned by the server.
              By default, Tornado will follow redirects, so this URL may
              differ from the request URL.  It will only be present on a
              successful request or if a HTTPError is encountered.
            * headers: The response headers.  It will only be present on a
              successful request or if a HTTPError is encountered.
            * data: If we have a raw response body, we will attempt to decode
              the data.  If we are able to decode the content-type header,
              this key will contain a str.  In addition, if we have support
              for the specific content type to decode the data, such a JSON,
              we'll also decode it as well. This will be present given the
              above conditions.


        The flattened error is a dictionary, accessed from kwargs using the
        'errinfo' key.  It mimics the synapse excinfo output, but without
        investigating a stack trace for performance reasons.  It contains
        the following information:
 
            * err: The Exception class raised during the request.
            * errmsg: The str() representation of the exception.
            * errfile: Empty string.
            * errline: Empty string.

        The Hypnos boss job id is a str which can be accessed from kwargs
        using the 'jid' key.

        The following items may be used via kwargs to set request parameters:

            * api_args: This should be a dictionary containing any required
              or optional arguments the API rquires.

        The following items may be passed via kwargs to change the job
        execution parameters:

            * callback: A function which will be called by the servicing
              thread.  By default, this will be wrapped to fire boss.err()
              if excinfo is present in the callback's kwargs.
            * ondone: A function to be executed by the job:fini handler
              when the job has been completed.
            * job_timeout: A timeout on how long the job can run from the
              perspective of the boss.  This isn't related to the request
              or connect timeouts.
            * fail_fast: Boolean value, if set to false, the wrapper which
              calls boss.err() on the executing job will not be applied to
              the callback.  It is then the responsibility for any event
              handlers or callback functions to handle errors.

        :param name: Name of the API to send a request for.
        :param args: Additional args passed to the callback functions.
        :param kwargs: Additional args passed to the callback functions or for
                       changing the job execution.
        :return: Job id value which can be referenced against the Hypnos boss
                 object.
        :raises: NoSuchName if the API name does not exist.
        '''
        # First, make sure the name is good
        nyx = self.getNyxApi(name)
        # Fail fast on a bad name before creating a reference in the self.boss
        # for the job.
        if nyx is None:
            raise NoSuchName(name=name, mesg='Invalid API name')

        # Grab things out of kwargs
        callback = kwargs.pop('callback', None)
        ondone = kwargs.pop('ondone', None)
        job_timeout = kwargs.pop('job_timeout', None)
        fail_fast = kwargs.pop('fail_fast', True)
        api_args = kwargs.get('api_args', {})

        if not callback:
            # Setup the default callback
            def default_callback(*cbargs, **cbkwargs):
                self.fire(name, **{'args': cbargs, 'kwargs': cbkwargs})

            callback = default_callback
        # Wrap the callback so that it will fail fast in the case of a request error.
        if fail_fast:
            callback = self._webRespFailWrapper(callback)

        # Construct the job tufo
        jid = s_async.jobid()
        t = s_async.newtask(callback, *args, **kwargs)
        job = self.boss.initJob(jid, task=t, ondone=ondone, timeout=job_timeout)

        # Create our Async callback function - it enjoys the locals().
        def response_nommer(resp):
            job_kwargs = job[1]['task'][2]
            job_kwargs['jid'] = job[0]
            if resp.error:
                _e = resp.error
                _execinfo = {
                    'err': _e.__class__.__name__,
                    'errmsg': str(_e),
                    'errfile': '',
                    'errline': '',
                }
                job_kwargs['excinfo'] = _execinfo
            resp_dict = self._webFlattenHttpResponse(resp)
            job_kwargs['resp'] = resp_dict
            self.pool.call(self.boss._runJob, job)

        # Construct the request object
        req = nyx.buildHttpRequest(api_args)

        self.client.fetch(req, callback=response_nommer)

        return jid
