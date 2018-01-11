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
import json
import logging
import tempfile
import collections
import urllib.parse
# Third Party Code
import tornado.ioloop as t_ioloop
import tornado.httpclient as t_http
# Custom Code
import synapse.axon as s_axon
import synapse.async as s_async
import synapse.common as s_common
import synapse.cortex as s_cortex

import synapse.glob as s_glob
import synapse.lib.cache as s_cache
import synapse.lib.ingest as s_ingest
import synapse.lib.config as s_config
import synapse.lib.threads as s_threads

logger = logging.getLogger(__name__)

MIN_WORKER_THREADS = 'web:worker:threads:min'
MAX_WORKER_THREADS = 'web:worker:threads:max'
MAX_SPOOL_FILESIZE = 'web:ingest:max_spool_size'
CACHE_ENABLED = 'web:cache:enable'
CACHE_TIMEOUT = 'web:cache:timeout'
MAX_CLIENTS = 'web:tornado:max_clients'
HYPNOS_BASE_DEFS = (
    (MIN_WORKER_THREADS, {'type': 'int', 'doc': 'Minimum number of worker threads to spawn.', 'defval': 8}),
    (MAX_WORKER_THREADS, {'type': 'int', 'doc': 'Maximum number of worker threads to spawn.', 'defval': 64}),
    (MAX_SPOOL_FILESIZE, {'type': 'int',
                          'doc': 'Maximum spoolfile size, in bytes, to use for storing responses associated with '
                                 'APIs that have ingest definitions.',
                          'defval': s_axon.megabyte * 2}),
    (CACHE_ENABLED, {'type': 'bool',
                     'doc': 'Enable caching of job results for a period of time, retrievable by jobid.',
                     'defval': False}),
    (CACHE_TIMEOUT, {'type': 'int',
                     'doc': 'Timeout value, in seconds, that the results will persist in the cache.',
                     'defval': 300}),
    (MAX_CLIENTS, {'type': 'int',
                   'doc': 'Maximum number of concurrent requests which can be made at one time.',
                   'defval': 10}),
)


ioloop = None

def _getIoLoop():
    '''
    Get a RemCycle module local IOLoop.

    Returns:
        t_ioloop.IoLoop: A Tornado IOLoop.
    '''
    global ioloop
    if ioloop is None:
        ioloop = t_ioloop.IOLoop()
        s_threads.worker(ioloop.start)
    return ioloop

def fetch(url, callback, defs=None):
    '''
    Fetch an arbitary URL via Tornado AsyncHTTPClient and execute a callback with the response data.

    Args:
        url (str): URL to request.
        callback (function): Callback function. This must accept two args, the flattened
        HTTPResponse object and a file-like object containing the response body.
        defs (dict): A dictionary containing arguments for the Tornado HTTPRequest
        object constructed by this function.

    Examples:

        Get a webpage and print some information about it:

        def callback(resp, fd):
            print(resp)
            print(fd.read()[:100])
            fd.close()
        url = 'http://www.vertex.link/'

        # Now fetch the URL and execute the callback.
        s_remcycle.fetch(url, callback)

    Notes:
        This API directs HTTP body content to a tempfile.SpooledTemporaryFile.
        This does require smashing in our own ``streaming_callback`` function
        into the kwargs passed along to the HTTPRequest object.  The callback
        streams data into a tempfile.SpooledTemporaryFile object with a maxsize
        of 100 megabytes. ``seek(0)`` is called on this object prior to the
        supplied callback being executed. It is the callbacks responsibility
        to call ``close()`` on the file object when it is done consuming any
        data from it.

    Returns:
        None
    '''
    if defs is None:
        defs = {}

    fd = tempfile.SpooledTemporaryFile(max_size=s_axon.megabyte * 100)

    def write_fd(chunk):
        fd.write(chunk)

    # Stamp in our own streaming callback
    defs['streaming_callback'] = write_fd

    def wrapped_callback(resp):
        fd.seek(0)
        resp = Hypnos._webFlattenHttpResponse(resp)
        s_glob.pool.call(callback, resp, fd)

    req = t_http.HTTPRequest(url, **defs)
    asynchttp = t_http.AsyncHTTPClient(io_loop=_getIoLoop(),
                                       max_body_size=s_axon.terabyte * 1,
                                       )
    ioloop.add_callback(asynchttp.fetch, req, wrapped_callback)


class Nyx(object):
    '''
    Configuration parser & request generator for a REST service.

    This class is responsible for doing the actual HTTPRequest generation
    in a parametrized fashion for a given input.

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
        * ingest: A dictionary containing a Synapse ingest definition which
          will be used to create an Ingest objects. During registration of a
          Nyx object with Hypnos, these will be registered into the Hypnos
          cortex. This dictionary should contain the key "name" which will be
          used to create a unique name for the ingest events, and the key
          "definition" which must contain the ingest definition. The ingest
          definition must contain a "open" directive which is used with the
          ingest iterdata() function to process the API data prior to ingest.
        * vars: This is a dictionary of items which are stamped into the url
          template during the construction of the Nyx object using format().

    Some API endpoints (typically PUT/POST/PATCH) may require additional
    content which is provided via the HTTP body. The api_arg value "req_body"
    is reserved in order to support passing body data when making the
    HTTPRequest object. A consequence of pulling the body from the api_args
    is that the 'body' argument is not allowed to be present in the "http"
    kv dictionary used when constructing the non-URL portions of the
    HTTPRequest  For use cases where a caller needs to make body requests
    with a default set of content, they are responsible for provided that
    content in the req_body api_args value when calling buildHttpRequest.

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
          "ingest": {
            "definition": {
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
              },
              "open": {
                "format": "json"
              }
            },
            "name": "geolocv4"
          },
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
        self.reserved_api_args = [
            'req_body'
        ]
        self.doc = ''
        self.url_template = ''
        self.url_vars = {}
        self.effective_url = ''
        self.request_defaults = {}
        self.api_args = []
        self.api_kwargs = {}
        self.gest = None
        self.gest_name = None
        self.gest_open = None

        self._parseConfig()

    def description(self):
        '''
        Get a dictionary containing an objects docstring, required api_args
        and optional api args.

        Returns:
            dict: Dictionary containing data.
        '''
        # Make copies of object so the returned mutable dictionary does not
        # affect the Nyx instance.
        d = {'doc': str(self.doc),
             'api_args': list(self.api_args),
             'api_optargs': self.api_kwargs.copy(),
             }
        return d

    def _parseConfig(self):
        for key in self.required_keys:
            if key not in self._raw_config:
                logger.error('Remcycle config is missing a required value %s.', key)
                raise s_common.NoSuchName(name=key, mesg='Missing required key.')
        self.url_template = self._raw_config.get('url')
        self.doc = self._raw_config.get('doc')
        self.url_vars.update(self._raw_config.get('vars', {}))
        self.request_defaults = self._raw_config.get('http', {})
        self._parseGestConfig(self._raw_config.get('ingest'))
        self.api_args.extend(self._raw_config.get('api_args', []))
        for key in self.reserved_api_args:
            if key in self.api_args:
                raise s_common.BadConfValu(name=key,
                                           valu=None,
                                           mesg='Reserved api_arg used.')
        self.api_kwargs.update(self._raw_config.get('api_optargs', {}))

        # Set effective url
        self.effective_url = self.url_template.format(**self.url_vars)

    def _parseGestConfig(self, gest_data=None):  # type: (dict) -> None
        if gest_data is None:
            return
        self.gest_name = gest_data.get('name')
        gestdef = gest_data.get('definition')
        self.gest_open = gestdef.get('open')
        self.gest = gestdef
        # Blow up on missing data early
        if not self.gest_name:
            raise s_common.NoSuchName(name='name', mesg='API Ingest definition is missing its name.')
        if not self.gest_open:
            raise s_common.NoSuchName(name='open', mesg='Ingest definition is missing a open directive.')

    def buildHttpRequest(self,
                         api_args=None):  # type: (dict) -> t_http.HttpRequest
        '''
        Build the HTTPRequest object for a given configuration and arguments.

        Args:
            api_args (dict): Arguments support either required or optional URL
                             values.

        Notes:
            A HTTP body can be provided to the request by passing its contents
            in by adding the "req_body" value to api_args argument.

        Returns:
            tornado.httpclient.HTTPRequest: HTTPRequest object with the
                                            configured url and attributes.

        Raises:
            NoSuchName: If the api_args is missing a required API value.
        '''
        body = None
        t_args = {}
        if api_args:
            body = api_args.pop('req_body', None)
        for argn in self.api_args:
            argv = api_args.get(argn, s_common.novalu)
            if argv is s_common.novalu:
                logger.error('Missing argument: %s', argn)
                raise s_common.NoSuchName(name=argn, mesg='Missing an expected argument')
            t_args[argn] = urllib.parse.quote_plus(str(argv))
        for argn, defval in self.api_kwargs.items():
            t_args[argn] = urllib.parse.quote_plus(str(api_args.get(argn, defval)))
        url = self.effective_url.format(**t_args)
        req = t_http.HTTPRequest(url, body=body, **self.request_defaults)
        return req

class Hypnos(s_config.Config):
    '''
    Object for grabbing a bunch of HTTP(S) data and consuming it via callbacks
    or ingest definitions.  Users can register multiple namespaces, each with
    their own set of API endpoints configured with them.  See the fire_api()
    function for details on retrieving data with Hypnos.

    The Hypnos object inherits from the Config object, and as such has both
    configable parameters and an EventBus available for message passing.

    Notes:
        The following items may be passed via kwargs to change the Hypnos
        object behavior:

        * ioloop: Tornado ioloop used by the IO thread. This would normally
          be left unset, and an ioloop will be created for the io thread.
          This is provided as a helper for testing.
        * content_type_skip: A list of content-type values which will not have
          any attempts to decode data done on them.

        The following values may be passed via configable opts:

        * web:worker:threads:min: Minimum number of worker threads to spawn.
        * web:worker:threads:max:  Maximum number of worker threads to spawn.
        * web:ingest:max_spool_size:  Maximum spoolfile size, in bytes, to use
          for storing responses associated withAPIs that have ingest
          definitions.
        * web:cache:enable: Enable caching of job results for a period
          of time, retrievable by jobid.
        * web:cache:timeout: Timeout value, in seconds, that the
          results will persist in the cache.
        * web:tornado:max_clients: Maximum number of concurrent requests which
          can be made at one time.

    Args:
        core (synapse.cores.common.Cortex): A cortex used to store ingest data. By default a ram cortex is used.
        opts (dict): Optional configuration data for the Config mixin.
    '''

    def __init__(self,
                 core=None,
                 opts=None,
                 *args,
                 **kwargs):
        s_config.Config.__init__(self)
        # Runtime-settable options
        self.onConfOptSet(CACHE_ENABLED, self._onSetWebCache)
        self.onConfOptSet(CACHE_TIMEOUT, self._onSetWebCacheTimeout)

        # Things we need prior to loading in conf values
        self.web_boss = s_async.Boss()
        self.web_cache = s_cache.Cache()
        self.web_cache_enabled = False

        if opts:
            self.setConfOpts(opts)

        self._web_required_keys = ('namespace', 'doc', 'apis')

        self._web_apis = {}
        self._web_namespaces = set([])
        self._web_docs = {}
        self._web_default_http_args = {}  # Global request headers per namespace

        # Check configable options before we spin up any more resources
        max_clients = self.getConfOpt(MAX_CLIENTS)
        pool_min = self.getConfOpt(MIN_WORKER_THREADS)
        pool_max = self.getConfOpt(MAX_WORKER_THREADS)
        if pool_min < 1:
            raise s_common.BadConfValu(name=MIN_WORKER_THREADS,
                                       valu=pool_min,
                                       mesg='web:worker:threads:min must be greater than 1')
        if pool_max < pool_min:
            raise s_common.BadConfValu(name=MAX_WORKER_THREADS,
                                       valu=pool_max,
                                       mesg='web:worker:threads:max must be greater than the web:worker:threads:min')
        if max_clients < 1:
            raise s_common.BadConfValu(name=MAX_CLIENTS,
                                       valu=max_clients,
                                       mesg='web:tornado:max_clients must be greater than 1')
        # Tornado Async
        loop = kwargs.get('ioloop')
        if loop is None:
            loop = t_ioloop.IOLoop()
        self.web_loop = loop
        self.web_client = t_http.AsyncHTTPClient(io_loop=self.web_loop,
                                                 max_clients=max_clients)
        self.web_iothr = self._runIoLoop()

        # Synapse Async and thread pool
        self.web_pool = s_threads.Pool(pool_min, pool_max)

        # Synapse Core and ingest tracking
        if core is None:
            core = s_cortex.openurl('ram://')
            self.onfini(core.fini)
        self.web_core = core
        self._web_api_ingests = collections.defaultdict(list)
        self._web_api_gest_opens = {}

        # Setup Fini handlers
        self.onfini(self._onHypoFini)

        # List of content-type headers to skip automatic decoding
        self._web_content_type_skip = set([])
        self.webContentTypeSkipAdd('application/octet-stream')
        for ct in kwargs.get('content_type_skip', []):
            self.webContentTypeSkipAdd(ct)

    def __repr__(self):
        d = {'name': self.__class__.__name__,
             'loc': hex(id(self)),
             'ns': list(self._web_namespaces),
             'core': self.web_core,
             }
        s = '<{name} at {loc}, namespaces: {ns}, core: {core}>'.format(**d)
        return s

    @s_common.firethread
    def _runIoLoop(self):
        self.web_loop.start()

    def _onHypoFini(self):
        # Stop the IOLoop async thread
        self.web_loop.stop()
        self.web_iothr.join()
        # Stop the boss making jobs
        self.web_boss.fini()
        # Stop the consuming pool
        self.web_pool.fini()
        # Stop the web cache
        self.web_cache.fini()

    @staticmethod
    @s_config.confdef(name='hypnos')
    def _getHyposBaseDefs():
        return HYPNOS_BASE_DEFS

    def _onSetWebCache(self, valu):
        '''
        Enable or disable caching of results from fireWebApi.
        When caching is diabled, all cached data is cleared.

        Args:
            valu (bool): True or False to enable or disable the caching.

        Returns:

        '''
        if valu:
            if self.web_cache_enabled:
                return
            self.web_cache_enabled = True
            self.web_cache.setMaxTime(self.getConfOpt(CACHE_TIMEOUT))
        else:
            if not self.web_cache_enabled:
                return
            self.webCacheClear()
            self.web_cache_enabled = False

    def _onSetWebCacheTimeout(self, valu):
        '''
        Set the cache timeout value.

        Args:
            valu (int):

        Returns:

        '''
        if self.web_cache_enabled:
            self.web_cache.setMaxTime(valu)

    def getWebDescription(self):
        '''
        Get a dictionary containing all namespaces, their docstrings, and
        registered api data.

        Returns:
            dict: Dictionary describing the regsistered namespace API data.
        '''
        d = {}
        for ns in self._web_namespaces:
            nsd = {'doc': self._web_docs[ns]}
            for api_name, api_obj in self._web_apis.items():
                nsd[api_name] = api_obj.description()
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
                    "doc": "api example",
                    "http": {
                      "headers": {
                        "token-goodness": "sekrittoken"
                      }
                    },
                    "ingest": {
                      "definition": {
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
                        },
                        "open": {
                          "format": "json"
                        }
                      },
                      "name": "geolocv4"
                    },
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
                    "doc": "Get the vertex project landingpage.",
                    "http": {
                      "validate_cert": false
                    },
                    "url": "https://vertex.link/"
                  }
                ]
              ],
              "doc": "GrabVertex.linkstuff",
              "http": {
                "user_agent": "Totally Not a Python application."
              },
              "namespace": "vertexproject"
            }

        ::

        The following config keys are required:

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

        The following config keys are optional:

            * http: Global HTTP Request arguments which will be the basis
              for creating HTTPRequest objects. These values should conform to
              the Tornado HTTPRequest constructor.


        An example of a generic configuration for getting arbitrary endpoints is shown below:

        ::

            {
              "apis": [
                [
                  "fqdn",
                  {
                    "api_args": [
                      "fqdn"
                    ],
                    "api_optargs": {
                      "endpoint": ""
                    },
                    "doc": "Get arbitrary domain name.",
                    "http": {
                      "validate_cert": false
                    },
                    "url": "https://{{fqdn}}/{{endpoint}}"
                  }
                ]
              ],
              "doc": "Definition for getting an arbitrary domain.",
              "http": {
                "user_agent": "Some.UserAgent"
              },
              "namespace": "generic"
            }

        Args:
            config (dict): Dictionary containing the configuration information.
            reload_config (bool): If true and the namespace is already registered,
                                  the existing namespace will be removed and the
                                  new config added. Otherwise a NameError will
                                  be thrown.

        Returns:
            None

        Raises:
            Other exceptions are possible, likely as a result of ducktyping.
            NameError: If the existing namespace is registered or a invalid
                       HTTP value is provided.

        '''
        try:
            self._parseWebConf(config, reload_config)
        except Exception as e:
            logger.exception('Failed to process configuration')
            raise e

    def _parseWebConf(self, config, reload_config):

        for key in self._web_required_keys:
            if key not in config:
                logger.error('Remcycle config is missing a required value %s.', key)
                raise s_common.NoSuchName(name=key, mesg='Missing required key.')

        _apis = config.get('apis')
        _namespace = config.get('namespace')
        _doc = config.get('doc')

        if _namespace in self._web_namespaces:
            if reload_config:
                self.delWebConf(_namespace)
            else:
                raise NameError('Namespace is already registered.')

        self._web_docs[_namespace] = _doc
        self._web_default_http_args[_namespace] = {k: v for k, v in config.get('http', {}).items()}

        # Register APIs
        for varn, val in _apis:
            name = ':'.join([_namespace, varn])
            # Stamp api http config ontop of global config, then stamp it into the API config
            _http = self._web_default_http_args[_namespace].copy()
            _http.update(val.get('http', {}))
            val['http'] = _http
            nyx_obj = Nyx(val)
            self._registerWebApi(name, nyx_obj)
        self._web_namespaces.add(_namespace)

        self.fire('hypnos:register:namespace:add', namespace=_namespace)

    def _registerWebApi(self, name, obj):
        '''
        Register a Nyx API with Hypnos.

        Args:
            name (str): API Name
            obj (Nyx): Nyx object contianing spec and gest data.

        Returns:
            None
        '''
        if name in self._web_apis:
            raise NameError('Already registered {}'.format(name))
        self._web_apis[name] = obj
        if obj.gest:
            action_name = ':'.join([name, obj.gest_name])
            # Register the action with the attached cortex
            self.web_core.setGestDef(action_name, obj.gest)

            def gest_glue(event):
                evtname, event_args = event
                kwargs = event_args.get('kwargs')
                resp = kwargs.get('resp')
                data = resp.get('ingdata')
                for _data in data:
                    self.web_core.addGestData(action_name, _data)
                resp['data'].seek(0)

            # Register the action to unpack the async.Boss job results and fire the cortex event
            self.on(name, gest_glue)

            # Store things for later reuse (for deregistartion)
            self._web_api_ingests[name].append((action_name, gest_glue))
            self._web_api_gest_opens[name] = obj.gest_open

        self.fire('hypnos:register:api:add', api=name)

    def delWebConf(self, namespace):
        '''
        Safely remove a namespace.

        Removes a given namespace, APIs and any corresponding event handlers
        which have been snapped into the Hypnos object and its cortex via
        the addWebConfig API.

        Args:
            namespace (str): Namespace to remove.

        Returns:
            None

        Raises:
            NoSuchName: If the namespace requested does not exist.
        '''
        if namespace not in self._web_namespaces:
            raise s_common.NoSuchName('Namespace is not registered.')

        self._web_namespaces.remove(namespace)
        self._web_docs.pop(namespace, None)
        self._web_default_http_args.pop(namespace, None)

        apis_to_remove = []
        for api_name in list(self._web_apis.keys()):
            ns, name = api_name.split(':', 1)
            if ns == namespace:
                apis_to_remove.append(api_name)

        for api_name in apis_to_remove:
            self._delWebApi(api_name)

        self.fire('hypnos:register:namespace:del', namespace=namespace)

    def _delWebApi(self, name):
        if name not in self._web_apis:
            raise s_common.NoSuchName(name=name, mesg='API name not registered.')

        self._web_apis.pop(name, None)
        self._web_api_gest_opens.pop(name, None)

        funclist = self._web_api_ingests.pop(name, [])
        for action_name, gest_glue in funclist:
            self.off(name, gest_glue)

        self.fire('hypnos:register:api:del', api=name)

    def getNyxApi(self, name):
        '''
        Get the Nyx object corresponding to a given API name.

        Args:
            name (str): Name of the API to get the object for.

        Returns:
            Nyx: A Nyx object.
        '''
        nyx = self._web_apis.get(name)
        return nyx

    @staticmethod
    def _webFlattenHttpResponse(resp):
        '''
        Flatten a HTTPResponse into a dictionary.

        This allows the response to be transported across RMI boundaries if
        needed.

        Notes:
            This should be called by the IO thread which actually retrieved
            the web response, as the HTTPResponse object may not be safe to
            pass across threads.

        Args:
            resp (t_http.HTTPResponse): HTTP Response to flatten.

        Returns:
            dict: Dictionary containing the request (url and headers), as well
                  as the code, data, headers and effective url if there was
                  a non-HTTP error.
        '''
        resp_dict = {
            'request': {'url': resp.request.url,
                        'headers': dict(resp.request.headers)}
        }
        if resp.error:
            if not isinstance(resp.error, t_http.HTTPError):
                return resp_dict

            resp_dict['excinfo'] = {
                'err': resp.error.__class__.__name__,
                'errmsg': str(resp.error),
                'errfile': '',
                'errline': '',
            }

        resp_dict.update({'code': resp.code,
                          'data': resp.body,
                          'headers': dict(resp.headers),
                          'effective_url': resp.effective_url, })
        return resp_dict

    def _webProcessResponseFlatten(self, resp_dict):
        '''
        Process a flattened HTTP response to extract as much meaningful data
        out of it as possible.

        Notes:
            This should be called by the IO thread consuming the response
            data, not the thread responsible for actually retrieving the web
            data.

        Args:
            resp_dict (dict) : Dictionary which has been flattened with the
                               _webFlattenHttpResponse function.

        Returns:
            None

        '''

        # Fail fast when we have no data to process
        if not resp_dict.get('data'):
            return
        # Try to do a clean decoding of the provided data if possible.
        ct = resp_dict.get('headers', {}).get('Content-Type', 'text/plain')
        ct_type, ct_params = cgi.parse_header(ct)
        if ct_type.lower() in self._web_content_type_skip:
            return
        charset = ct_params.get('charset', 'utf-8').lower()
        try:
            resp_dict['data'] = resp_dict.get('data').decode(charset)
        except Exception as e:
            logger.exception('Failed to decode a raw body in a response object.')
            return
        # Handle known content types and put them in the 'data' key
        # we can add support for additional data types as needed.
        if ct_type.lower() == 'application/json':
            resp_dict['data'] = json.loads(resp_dict.get('data'))

    def _webProcessResponseGest(self, resp_dict, gest_open):
        '''
        Prepare a web reponse using a ingest open directive.

        Notes:
            This should be called by the IO thread consuming the response
            data, not the thread responsible for actually retrieving the web
            data.

        Args:
            resp_dict (dict): Reponse dictionary. It will have the 'data' field
                              overwritten with a SpooledTemporaryFile and the
                              'ingdata' field added with a generator.
            gest_open (dict): Ingest open directive.

        Returns:
            None
        '''
        # Fail fast, let the ingest go boom later.
        if not resp_dict.get('data'):
            return resp_dict
        # SpooledTemporaryFile will reduce memory burden (as the expanse of disk space)
        # in the event we get a large amount of data back from an endpoint.
        buf = tempfile.SpooledTemporaryFile(max_size=self.getConfOpt(MAX_SPOOL_FILESIZE))
        # TODO Loop in chunks in the event we have a large amount of data.
        buf.write(resp_dict.get('data'))
        buf.seek(0)
        # Build the generator and replace 'data' with the generator.
        ingdata = s_ingest.iterdata(fd=buf, close_fd=False, **gest_open)
        resp_dict['data'] = buf
        resp_dict['ingdata'] = ingdata

    def _webFailRespWrapper(self, func):
        '''
        Decorates a function for wrapping callback functions.

        The decorator performs two functions:

        * Checks for exception information fails the job if the exception
          information is present.
        * Continues to process the resp dictionary to extract and decode
          data, preparing it for a ingest or other consumption.

        Args:
            func: Function to wrap.

        Returns:
            Wrapped function.
        '''

        def check_job_fail(*fargs, **fkwargs):
            _excinfo = fkwargs.get('excinfo')
            if _excinfo:
                _jid = fkwargs.get('jid')
                self.web_boss.err(_jid, **_excinfo)
                return
            _api_name = fkwargs.get('web_api_name')
            _gest_opens = self._web_api_gest_opens.get(_api_name)
            if _gest_opens:
                self._webProcessResponseGest(fkwargs.get('resp'), _gest_opens)
            else:
                self._webProcessResponseFlatten(fkwargs.get('resp'))
            func(*fargs, **fkwargs)

        return check_job_fail

    def _webCacheRespWrapper(self, func):
        '''
        Decorates a function for performing caching of web responses.

        If used, this would be the first function unwrapped by a worker
        thread, as such, the actual data cached by the response has NOT
        been processed so it is the cache user's responsibility to decode
        any data present in the cache.

        Args:
            func: Function to wrap.

        Returns:
            Wrapped function.
        '''

        def cache_job_results(*fargs, **fkwargs):
            jid = fkwargs.get('jid')
            resp = fkwargs.get('resp', {}).copy()
            d = {'web_api_name': fkwargs.get('web_api_name'),
                 'resp': resp,
                 'api_args': fkwargs.get('api_args', {})}
            _excinfo = fkwargs.get('excinfo')
            if _excinfo:
                d['err'] = _excinfo['err']
                d['errmsg'] = _excinfo['errmsg']
                d['errfile'] = _excinfo['errfile']
                d['errline'] = _excinfo['errline']
            # Store the data in the cache
            self.web_cache.put(jid, d)
            # Now call the wrappee
            func(*fargs, **fkwargs)

        return cache_job_results

    def fireWebApi(self, name, *args, **kwargs):
        '''
        Fire a request to a registered API.

        The API response is serviced by a thread in the Hypnos thread pool,
        which will fire either an event on the Hypnos service bus or a caller
        provided callback function.  The default action is to fire an event
        on the service bus with the same name as the API itself.

        A flattened version of the response, error information and the Boss
        job id will be stamped into the kwargs passed along to the the
        callbacks.  If the API name has a ingest associated with it, the
        response data will be pushed into a generator created according to
        the ingest open directive.

        The flattened response is a dictionary, accessed from kwargs using
        the 'resp' key. It contains the following information:

            * request: A dictionary containing the requested URL and headers.
              This is guaranteed to exist.  It has the following values:
                - url: URL requested by the remote server.
                - headers: Headers passed to the remote server.
            * code: HTTP Response code.  This will only be present on a
              successfull request or if a HTTPError is encountered.
            * data: This may be one of three values:

              - A SpooledTemporaryFile containing the raw bytes of the
                response. This will be present if there is a ingest associated
                with the named response. A corresponding generator will be
                created and placed in the "ingdata" field and consumed by the
                ingest. Post-consumption, seek(0) will be called on the
                file-like object. If there are multiple post-ingest consumers
                of the job, each one may want to call seek(0) on the file
                object before consuming it.
              - The decoded data as a string or a decoded json blob. We will
                attempt to parse the data based on the Content-Type header.
                This is a best effort decoding.
              - In the event that the best effort decoding fails, the response
                will be available as raw bytes.

            * effective_url: The effective url returned by the server.
              By default, Tornado will follow redirects, so this URL may
              differ from the request URL.  It will only be present on a
              successful request or if a HTTPError is encountered.
            * headers: The response headers.  It will only be present on a
              successful request or if a HTTPError is encountered.

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

        Notes:

            The following items may be used via kwargs to set request parameters:

                * api_args: This should be a dictionary containing any required
                  or optional arguments the API rquires.

            The following items may be passed via kwargs to change the job
            execution parameters:

                * callback: A function which will be called by the servicing
                  thread.  By default, this will be wrapped to fire boss.err()
                  if excinfo is present in the callback's kwargs.
                * ondone: A function to be executed by the job:fini handler
                  when the job has been completed. If the api we're firing has an
                  ingest associated with it, the response data may not be
                  available to be consumed by the ondone handler.
                * job_timeout: A timeout on how long the job can run from the
                  perspective of the boss.  This isn't related to the request
                  or connect timeouts.
                * wrap_callback: By default, the callback function is wrapped to
                  perform error checking (and fast job failure) in the event of an
                  error encountered during the request, and additional processing
                  of the HTTP response data to perform decoding and content-type
                  processing.  If this value is set to false, the decorator will
                  not be applied to a provided callback function, and the error
                  handling and additional data procesing will be the
                  responsibility of any event handlers or the provided callback
                  function.  The fast failure behavior is handled by boss.err()
                  on the job associated with the API call.

            A HTTP body can be provided to the request by passing its contents
            in by adding the “req_body” value to api_args argument.  See the
            Nyx object documentation for more details.

            If caching is enabled, the caching will be performed as the first
            thing done by the worker thread handling the response data. This
            is done separately from the wrap_callback step mentioned above.

        Args:
            name (str): Name of the API to send a request for.
            *args: Additional args passed to the callback functions.
            **kwargs: Additional args passed to the callback functions or for
                      changing the job execution.

        Returns:
            str: String containing a Job ID which can be used to look up a
                 job against the Hypnos.web_boss object.

        Raises:
            NoSuchName: If the requested API name does not exist.
        '''
        # First, make sure the name is good
        nyx = self.getNyxApi(name)
        # Fail fast on a bad name before creating a reference in the self.boss
        # for the job.
        if nyx is None:
            raise s_common.NoSuchName(name=name, mesg='Invalid API name')

        # Grab things out of kwargs
        callback = kwargs.pop('callback', None)
        ondone = kwargs.pop('ondone', None)
        job_timeout = kwargs.pop('job_timeout', None)
        wrap_callback = kwargs.pop('wrap_callback', True)
        api_args = kwargs.get('api_args', {})

        if not callback:
            # Setup the default callback
            def default_callback(*cbargs, **cbkwargs):
                self.fire(name, **{'args': cbargs, 'kwargs': cbkwargs})

            callback = default_callback
        # Wrap the callback so that it will fail fast in the case of a request error.
        if wrap_callback:
            callback = self._webFailRespWrapper(callback)
        # If the cache is enabled, wrap the callback so we cache the result before
        # The job is executed.
        if self.web_cache_enabled:
            callback = self._webCacheRespWrapper(callback)

        # Construct the job tufo
        jid = s_async.jobid()
        t = s_async.newtask(callback, *args, **kwargs)
        job = self.web_boss.initJob(jid, task=t, ondone=ondone, timeout=job_timeout)

        # Create our Async callback function - it enjoys the locals().
        def response_nommer(resp):
            job_kwargs = job[1]['task'][2]
            # Stamp the job id and the web_api_name into the kwargs dictionary.
            job_kwargs['web_api_name'] = name
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
            self.web_pool.call(self.web_boss._runJob, job)

        # Construct the request object
        req = nyx.buildHttpRequest(api_args)
        self.web_loop.add_callback(self.web_client.fetch, req, response_nommer)

        return jid

    def webJobWait(self, jid, timeout=None):
        '''
        Proxy function for the self.web_boss wait() call, in order to allow
        RMI callers to wait for a job to be completed if they wish.

        Args:
            jid (str): Job id to wait for.
            timeout: Time to wait for.

        Returns:
            bool: async.Boss.wait() result.

        '''
        return self.web_boss.wait(jid, timeout=timeout)

    def webContentTypeSkipAdd(self, content_type):
        '''
        Add a content-type value to be skipped from any sort of decoding
        attempts.

        Args:
            content_type (str): Content-type value to skip.
        '''
        self._web_content_type_skip.add(content_type)

    def webContentTypeSkipDel(self, content_type):
        '''
        Removes a content-type value from the set of values to be skipped
        from any sort of decoding attempts.

        Args:
            content_type (str): Content-type value to remove.
        '''
        if content_type in self._web_content_type_skip:
            self._web_content_type_skip.remove(content_type)

    def webCacheGet(self, jid):
        '''
        Retrieve the cached web response for a given job id.

        Args:
            jid (str): Job ID to retrieve.

        Returns:
            dict: A dictionary containing the job response data. It will have
            the following keys:

            * web_api_name: Name of the API
            * resp: Dictionary containing response data.  The raw data is not
              decoded or processed in any fashion, and is available in the
              'data' key of this dictionary (if present).
            * api_args: Args used when crafting the HTTPRequest with Nyx
            * err (optional): Error type if a error is encountered.
            * errmsg (optional): Error message if a error is encountered.
            * errfile (optional): Empty string if a error is encountered.
            * errline (optional): Empty string if a error is encountered.
        '''
        if not self.web_cache_enabled:
            logger.warning('Cached response requested but cache not enabled.')
        return self.web_cache.get(jid)

    def webCachePop(self, jid):
        '''
        Retrieve the cached web response for a given job id and remove it from the cache.
        Args:
            jid (str): Job ID to retrieve.

        Returns:
            dict: A dictionary containing the job response data. See the docs
            for webCacheGet for the dictionary details.
        '''
        if not self.web_cache_enabled:
            logger.warning('Cache deletion requested but cache not enabled.')
        return self.web_cache.pop(jid)

    def webCacheClear(self):
        '''
        Clear all the contents of the web cache.
        '''
        self.web_cache.clear()
