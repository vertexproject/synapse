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
for immeadiate consumption.

These requests are handled by Hypnos objects, which can have a single or
multiple definitions snapped into them in order to grab data on demand.
Hypnos grabs these requests with a single IO thread, and offloads the
consumption of the data to multiple worker threads.
'''
# Stdlib
import cgi
import inspect
import logging
import argparse
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
import synapse.lib.output as s_output
import synapse.lib.threads as s_threads

from synapse.common import *

log = logging.getLogger(__name__)


def valid_http_values():
    '''
    Generate a set of valid HTTPRequest arguments we will recognize in Remcycle.
    '''
    # TODO Replace try/except when Python2.7 support is dropped.
    try:
        spec = inspect.getfullargspec(func=t_http.HTTPRequest)
    except AttributeError:
        try:
            spec = inspect.getargspec(func=t_http.HTTPRequest.__init__)
        except:
            raise
    args = set(spec.args)
    if 'self' in args:
        args.remove('self')
    # We don't want url's coming through an HTTP configuration option
    if 'url' in args:
        args.remove('url')
    return args


VALID_TORNADO_HTTP_ARGS = valid_http_values()


def validate_http_values(vard):
    '''
    Ensure that the values in a dictionary are valid HTTPRequest arguments.

    :param vard: Dictionary to examine.
    :return: True, otherwise raises an Exception.
    :raises: Exception if the input isn't a dictionary or if a key in the
             input isn't in VALID_TORNADO_HTTP_ARGS.
    '''
    if not isinstance(vard, dict):
        raise Exception('bad type')
    for varn, varv in vard.items():
        if varn not in VALID_TORNADO_HTTP_ARGS:
            log.error('Bad varn encountered: %s', varn)
            raise Exception('Varn is not a valid tornado arg')
    return True


# TODO Lots of string constants used here which should be defined.
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
          values set by the api configuration method noted below should
          be enclosed with double curly brackets.

    The following configuration values are optional.

        * api: This is a list of two objects, one listing required API values
          and the second listing default API values.
            - The first object should be a list of required values.  These
              must be provided by the user when they call build_http_request.
            - The second object should be a dictionary of optional values and
              their defaults.  A user may provide alternative values when
              calling build_http_request, but sensible defaults should be
              provided here.
        * http: A dictionary of key/value items which can provide per-api
          specific arguements for the creation of HTTPRequest objects.
        * ingests: A dictionary of Synapse ingest definitions which will be
          used to create Ingest objects.  During registration of a Nyx object
          with Hypnos, these will be registered into the Hypnos cortex.
          Multiple named ingests may be made available for a single API.
        * vars: This is a list of 2 value items which are stamped into the url
          value during the construction of the Nyx object.

    See a complete example below:

    ::

        {
          "api": [
            [
              "someplace"
            ],
            {
              "domore": 0
            }
          ],
          "doc": "api example",
          "http": {
            "headers": {
              "token-goodness": "sekrit token"
            }
          },
          "ingests": {
            "ingest_definition": {
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
          },
          "url": "http://vertex.link/api/v4/geoloc/{{someplace}}/info?domore={{domore}}&apikey={APIKEY}",
          "vars": [
            ["APIKEY", "8675309"]
          ]
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
           calling build_http_request.  The caller may provide the "domore"
           value if they want to override the default value of "0".
        4. An Ingest will be created for parsing the data from the API and
           made available to the Hypnos object.

    :param api_config: API Endpoint configuration outlined above.
    :param namespace_http_config: Default HTTPRequent configuration values.
    '''

    def __init__(self, api_config, namespace_http_config=None):
        if namespace_http_config:
            self.namespace_http_config = namespace_http_config.copy()
        else:
            self.namespace_http_config = {}
        validate_http_values(self.namespace_http_config)
        self._raw_config = dict(api_config)
        self.required_keys = ['url',
                              'doc'
                              ]
        self.optional_keys = ['vars',
                              'http',
                              'api',
                              'ingests'
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
        self._default_client_config = self._build_default_req_dict()

    def _parse_config(self):
        for key in self.required_keys:
            if key not in self._raw_config:
                log.error('Remcycle config is missing a required value %s.', key)
                raise NoSuchName('Missing required key.')
            value = self._raw_config.get(key)
            if key == 'url':
                if not s_compat.isstr(value):
                    raise Exception('bad type')
                self.url_template = value
            if key == 'doc':
                if not s_compat.isstr(value):
                    raise Exception('bad type')
                self.doc = value
        for key in self.optional_keys:
            value = self._raw_config.get(key)
            if value is None:
                continue
            if key == 'vars':
                if not isinstance(value, (tuple, list)):
                    raise Exception('bad type')
                for varn, varv in value:
                    self.url_vars[varn] = varv
            if key == 'http':
                validate_http_values(vard=value)
                for varn, varv in value.items():
                    self.request_defaults[varn] = varv
            if key == 'api':
                if not isinstance(value, (tuple, list)):
                    raise Exception('bad type')
                api_args, api_kwargs = value
                if not isinstance(api_args, (tuple, list)):
                    raise Exception('bad type')
                if not isinstance(api_kwargs, dict):
                    raise Exception('bad type')
                for argn in api_args:
                    if not s_compat.isstr(argn):
                        raise Exception('bad type')
                    self.api_args.append(argn)
                for argn, defval in api_kwargs.items():
                    if not s_compat.isstr(argn):
                        raise Exception('bad type')
                    self.api_kwargs[argn] = defval
            if key == 'ingests':
                if not isinstance(value, dict):
                    raise Exception('bad type')
                for varn, var in value.items():
                    gest = s_ingest.Ingest(var)
                    self.gests[varn] = gest
        # Set effective url
        self.effective_url = self.url_template.format(**self.url_vars)

    def _build_default_req_dict(self):
        ret = self.namespace_http_config.copy()
        ret.update(self.request_defaults)
        return ret

    def build_http_request(self,
                           api_args=None,
                           request_args=None):
        '''
        Build the HTTPRequest object for a given configuration.

        :param api_args: Arguments support either required or optional URL
                         values.
        :param request_args: Arguments which will override or add to the
                             HTTPRequest object arguments. Strings will be
                             url quoted so that they may be safely requested.
        :return: tornado.httpclient.HTTPRequest object with the configured
                 url and attributes.
        :raises: NoSuchName if the api_args is missing a required API value.
        '''
        t_args = {}
        for argn in self.api_args:
            if argn not in api_args:
                log.error('Missing arguement: %s', argn)
                raise NoSuchName('Missing an expected argument')
            t_args[argn] = s_compat.url_quote_plus(str(api_args.get(argn)))
        for argn, defval in self.api_kwargs.items():
            t_args[argn] = s_compat.url_quote_plus(str(api_args.get(argn, defval)))
        url = self.effective_url.format(**t_args)
        args = self._default_client_config.copy()
        if request_args:
            validate_http_values(vard=request_args)
            args.update(request_args)
        req = t_http.HTTPRequest(url, **args)
        return req


class Hypnos(s_config.Config):
    '''
    Object for grabbing a bunch of HTTP(S) data and consuming it via callbacks
    or ingest definitions.  Users can register multiple namespaces, each with
    their own set of API endpoints configured with them.  See the fire_api()
    function for details on retrieving data with Hypnos.

    :param core: Cortex used to store ingest data.  By default, a ram cortex
                 is used.
    :param ioloop: Tornado ioloop used by the IO thread. This would normally
                   be left unset, and an ioloop will be created for the io
                   thread. This is provided as a helper for testing.
    '''

    def __init__(self,
                 core=None,
                 ioloop=None):
        s_config.Config.__init__(self)

        self.required_keys = ('namespace',
                              'doc',
                              'apis')
        self.optional_keys = ['http',
                              ]

        self.apis = {}
        self.namespaces = set([])
        self.docs = {}
        self.global_request_headers = {}  # Global request headers per namespace

        # Tornado Async
        if ioloop:
            self.loop = ioloop
        else:
            self.loop = t_ioloop.IOLoop()
        self.client = t_http.AsyncHTTPClient(io_loop=self.loop)
        self.iothr = self._runIoLoop()

        # Synapse Async
        self.boss = s_async.Boss()
        # FIXME options
        self.pool = s_threads.Pool(8, maxsize=64)

        # Synapse Core and ingest tracking
        if core:
            self.core = core
            self.core_provided = True
        else:
            self.core = s_cortex.openurl('ram://')
            self.core_provided = False
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
        # Stop the cortex if we created the cortex ourselves.
        if not self.core_provided:
            self.core.fini()

    def register_config(self, config, reload_config=False):
        '''
        Register a configuration into a Hypnos object.

        The Hypnos object can accept a configuration object shaped like the following:

        ::

            {
              "apis": {
                "geoloc": {
                  "api": [
                    [
                      "someplace"
                    ],
                    {
                      "domore": 0
                    }
                  ],
                  "doc": "api example",
                  "http": {
                    "headers": {
                      "token-goodness": "sekrit token"
                    }
                  },
                  "ingests": {
                    "ingest_definition": {
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
                  },
                  "url": "http://vertex.link/api/v4/geoloc/{{someplace}}/info?domore={{domore}}&apikey={APIKEY}",
                  "vars": [
                    ["APIKEY", "8675309"]
                  ]
                },
                "https": {
                  "doc": "Get the vertex project landing page.",
                  "http": {
                    "validate_cert": false
                  },
                  "url": "https://vertex.link/"
                }
              },
              "doc": "Grab Vertex.link stuff",
              "http": {
                "user_agent": "Totally Not a Python application."
              },
              "namespace": "vertexproject"
            }

        ::

        The following keys are required:

            * namespace: String identifier for all APIs present in the
              configuration.  Must be locally unique.
            * doc: Simple string describing the overall namespace.
            * apis: Dictionary containing configuration values for API
              endpoints. See Nyx object for details of how this data should be
              shaped.  The keys of this dictionary, when joined with the
              namespace of the configuration, form the name of the APIs for
              later use.  Given the example above, the following APIs would
              be registered:
                - vertexproject:geoloc
                - vertexproject:https

        The following keys are optional:

            * http: Global HTTP Request arguments which will be the basis
              for creating HTTPRequest objects.


        :param config: Dictionary containing the configuration information.
        :param reload_config: If true and the namespace is already registered,
                              the existing namespace will be removed and the new
                              config added.
        :return: None
        :raises: NameError if the existing namespace is registered.
        :raises: Exception if the configuration isn't shaped properly.
        '''
        _apis = {}
        _namespace = ''
        _doc = ''
        for key in self.required_keys:
            if key not in config:
                log.error('Remcycle config is missing a required value %s.', key)
                raise NoSuchName('Missing required key.')
            value = config.get(key)
            if not value:
                raise Exception('Value must be present.')
            if key == 'namespace':
                if not s_compat.isstr(value):
                    raise Exception('bad type')
                _namespace = value
            if key == 'apis':
                if not isinstance(value, dict):
                    raise Exception('Bad type')
                _apis = value
            if key == 'doc':
                if not s_compat.isstr(value):
                    raise Exception('bad type')
                _doc = value
        if _namespace in self.namespaces:
            if reload_config:
                self.deregister_config(namespace=_namespace)
            else:
                raise NameError('Namespace is already registered.')
        self.docs[_namespace] = _doc
        for key in self.optional_keys:
            value = config.get(key)
            if value is None:
                continue
            if key == 'http':
                validate_http_values(vard=value)
                gd = {varn: varv for varn, varv in value.items()}
                self.global_request_headers[_namespace] = gd
        # Register APIs
        for varn, val in _apis.items():
            name = ':'.join([_namespace, varn])
            nyx_obj = Nyx(api_config=val,
                          namespace_http_config=self.global_request_headers.get(_namespace)
                          )
            self._register_api(name=name, obj=nyx_obj)
        self.namespaces.add(_namespace)

    def _register_api(self, name, obj):
        '''
        Register a Nyx object and any corresponding ingest definitions to the
        cortex.
        '''
        if name in self.apis:
            raise Exception('Already registered {}'.format(name))
        self.apis[name] = obj
        for gest_name, gest in obj.gests.items():
            action_name = ':'.join([name, gest_name])
            # Register the action with the attached cortex
            ingest_func = s_ingest.register_ingest(core=self.core,
                                                   gest=gest,
                                                   evtname=action_name,
                                                   ret_func=True
                                                   )

            def gest_glue(event):
                evtname, event_args = event
                kwargs = event_args.get('kwargs')
                resp = kwargs.get('resp')
                data = resp.get('data')
                self.core.fire(action_name, data=data)

            # Register the action to unpack the async.Boss job results and fire the cortex event
            self.on(name=name, func=gest_glue)

            # Store things for later reuse (for deregistartion)
            self._api_ingests[name].append((action_name, ingest_func, gest_glue))

    def deregister_config(self, namespace):
        '''
        Remove a given namespace, APIs and any corresponding event handlers
        which have been snapped into the Hypnos object and its cortex via
        the register_config API .

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
            self._deregister_api(name=api_name)

    def _deregister_api(self, name):
        if name not in self.apis:
            raise NoSuchName('API name not registered.')

        self.apis.pop(name, None)

        funclist = self._api_ingests.pop(name, [])
        for action_name, ingest_func, gest_glue in funclist:
            self.off(name, gest_glue)
            self.core.off(action_name, ingest_func)

    def get_api(self, name):
        '''
        Get the Nyx object corresponding to a given API name.

        :param name: Name of the API to get the object for.
        :return: A Nyx object.
        :raises: A NoSuchName error if the requested name does not exist.
        '''
        nyx = self.apis.get(name)
        if not nyx:
            log.error('No name registered with')
            raise NoSuchName
        return nyx

    @staticmethod
    def _flatten_response(resp):
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
            log.exception('Failed to decode a raw body in a response object.')
            return resp_dict
        # Handle known content types and put them in the 'data' key
        # we can add support for additional data types as needed.
        if ct_type.lower() == 'application/json':
            resp_dict['data'] = json.loads(resp_dict.get('data'))
        return resp_dict

    def _resp_fail_wrapper(self, f):
        '''Decorator for wrapping callback functions to check for exception information.'''

        def check_job_fail(*fargs, **fkwargs):
            _excinfo = fkwargs.get('excinfo')
            if _excinfo:
                _jid = fkwargs.get('jid')
                self.boss.err(jid=_jid, **_excinfo)
            else:
                f(*fargs, **fkwargs)

        return check_job_fail

    def fire_api(self, name, *args, **kwargs):
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
            * errmsg: The str() represnetation of the exception.
            * errfile: Empty string.
            * errline: Empty string.

        The Hypnos boss job id is a str which can be accessed from kwargs
        using the 'jid' key.

        The following items may be used via kwargs to set request parameters:

            * api_args: This should be a dictionary containing any required
              or optional arguments the API rquires.
            * request_args: This should be a dictionary containing values
              used to override any namespace or api default values when
              creating the Tornado HTTPRequest object.

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
        nyx = self.get_api(name=name)

        # Grab things out of kwargs
        callback = kwargs.pop('callback', None)
        ondone = kwargs.pop('ondone', None)
        job_timeout = kwargs.pop('job_timeout', None)
        fail_fast = kwargs.pop('fail_fast', True)
        api_args = kwargs.get('api_args', {})
        request_args = kwargs.get('request_args', {})

        if not callback:
            # Setup the default callback
            def default_callback(*args, **kwargs):
                self.fire(evtname=name, **{'args': args, 'kwargs': kwargs})

            callback = default_callback
        # Wrap the callback so that it will fail fast in the case of a request error.
        if fail_fast:
            callback = self._resp_fail_wrapper(callback)

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
            resp_dict = self._flatten_response(resp=resp)
            job_kwargs['resp'] = resp_dict
            self.pool.call(self.boss._runJob, job)

        # Construct the request object
        req = nyx.build_http_request(api_args=api_args, request_args=request_args)

        self.client.fetch(req, callback=response_nommer)

        return jid


def main(argv, outp=None):  # pragma: no cover
    '''
    Example usage of remcycle.Hypnos
    '''
    if outp is None:  # pragma: no cover
        outp = s_output.OutPut()

    p = makeargpaser()
    options = p.parse_args(argv)

    if not options.verbose:
        logging.disable(logging.DEBUG)

    gconfig = {
        'apis': {
            'fqdn': {
                'doc': 'Get arbitrary domain name.',
                'http': {
                    'validate_cert': False
                },
                'url': 'https://{{fqdn}}/',
                'api': [
                    ['fqdn'],
                    {}
                ]
            }
        },
        'doc': 'Definition for getting an arbitrary domain.',
        'http': {
            'user_agent': 'SynapseTest.RemCycle'
        },
        'namespace': 'generic',
    }

    fqdns = ['www.google.com',
             'www.cnn.com',
             'www.vertex.link',
             'www.reddit.com',
             'www.foxnews.com',
             'www.msnbc.com',
             'www.bbc.co.uk',
             'www.amazon.com',
             'www.paypal.com',
             ]

    h = Hypnos()
    h.register_config(gconfig)

    def func(event_tufo):
        event_name, argdata = event_tufo
        kwargs = argdata.get('kwargs')
        resp = kwargs.get('resp')
        msg = 'Asked for [{}], got [{}] with code {}'.format(resp.get('request').get('url'),
                                                             resp.get('effective_url'),
                                                             resp.get('code')
                                                             )
        outp.printf(msg)

    h.on('generic:fqdn', func=func)

    job_ids = [h.fire_api('generic:fqdn', api_args={'fqdn': fqdn}) for fqdn in fqdns]
    for jid in job_ids:
        h.boss.wait(jid)

    h.fini()

    return 0


def makeargpaser():  # pragma: no cover
    '''Make argument parser.'''
    parser = argparse.ArgumentParser(description="Execute a simple remcycle.Hypnos example.")
    parser.add_argument('-v', '--verbose', dest='verbose', default=False, action='store_true',
                        help='Enable verbose output')
    return parser


def _main():  # pragma: no cover
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(funcName)s]')
    return main(sys.argv[1:])


if __name__ == '__main__':  # pragma: no cover
    sys.exit(_main())
