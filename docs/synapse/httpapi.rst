.. _http-api:

Synapse HTTP/REST API
=====================

Many components within the Synapse ecosystem provide HTTP/REST APIs to
provide a portable interface.  Some of these APIs are RESTful, while other
(streaming data) APIs are technically not.

.. _http-api-conventions:

HTTP/REST API Conventions
-------------------------

All Synapse RESTful APIs use HTTP GET/POST methods to retrieve and modify data.
All POST requests expect a JSON body.  Each RESTful API call will return a
result wrapper dictionary with one of two conventions.

For a successful API call:

::

    {"status": "ok", "result": "some api result here"}

or for an unsuccessful API call:

::

    {"status": "err": "code": "ErrCodeString", "mesg": "A human friendly message."}

Streaming HTTP API endpoints, such as the interface provided to retrieve nodes
from a Synapse Cortex, provide JSON results via HTTP chunked encoding where each
chunk is a single result.

The client example code in these docs is given with the Python "aiohttp" and "requests"
modules. They should be enough to understand the basic operation of the APIs.

For additional examples, see the code examples at `HTTPAPI Examples`_.

.. _http-api-authentication:

Authentication
--------------

Most Synapse HTTP APIs require an authenticated user. HTTP API endpoints requiring
authentication may be accessed using either HTTP Basic authentication via the HTTP
"Authorization" header, using an API Key with the "X-API-KEY" header, or as part of
an authenticated session.

API Key Support
~~~~~~~~~~~~~~~

A Cortex user can create their own API key via Storm. The following is an example
of generating a user API key:

  ::

    storm> ($key, $info)= $lib.auth.users.byname($lib.user.name()).genApiKey('Test Key') $lib.print($key)
    XauBgBIUKgWJEm7VyvkmcuaGZbIl6M2nmueWjRtnYtA=

This API Key can then be used to make HTTP API calls. The following example shows
the use of ``curl`` and ``jq`` to make a Storm call with the API key and then format
the response:

  ::

    $ curl -k -s -H "X-API-KEY: XauBgBIUKgWJEm7VyvkmcuaGZbIl6M2nmueWjRtnYtA=" \
    --data '{"query": "return($lib.user.name())"}' \
    https://localhost:4443/api/v1/storm/call | jq

    {
      "status": "ok",
      "result": "root"
    }


/api/v1/login
~~~~~~~~~~~~~

The login API endpoint may be used to create an authenticated session. To create and use an
authenticated session, the HTTP client library must support cookies. This session may then be
used to call other HTTP API endpoints as the authenticated user. This expects a ``user`` and
``passwd`` provided in the body of a ``POST`` request. The reusable session cookie is returned
in a ``Set-Cookie`` header.

Both of the Python examples use session managers which manage the session cookie automatically.

.. code:: python3
    :name: aiohttp login example

    import aiohttp
    
    async def logInExample(ssl=False):
    
        async with aiohttp.ClientSession() as sess:
    
            info = {'user': 'visi', 'passwd': 'secret'}
            async with sess.post('https://localhost:4443/api/v1/login', json=info, ssl=ssl) as resp:
                item = await resp.json()
                if item.get('status') != 'ok':
                    code = item.get('code')
                    mesg = item.get('mesg')
                    raise Exception(f'Login error ({code}): {mesg}')
            
                # we are now clear to make additional HTTP API calls using sess

.. code:: python3
    :name: requests login example

    import requests

    def logInExample(ssl=False):

        sess = requests.session()

        url = 'https://localhost:4443/api/v1/login'
        info = {'user': 'visi', 'passwd': 'secret'}
        resp = sess.post(url, json=info, verify=ssl)
        item = resp.json()

        if item.get('status') != 'ok':
            code = item.get('code')
            mesg = item.get('mesg')
            raise Exception(f'Login error ({code}): {mesg}')

        # we are now clear to make additional HTTP API calls using sess

/api/v1/logout
~~~~~~~~~~~~~~

The logout API endpoint may be used to end an authenticated session. This invalidates
the session, and any further requests to authenticated endpoints will fail on
authentication failed errors.

Both of the Python examples use session managers which manage the session cookie automatically.

.. code:: python3
    :name: aiohttp logout example

    import aiohttp

    def logoutExample(sess, ssl):
        url = 'https://localhost:4443/api/v1/logout'
        resp = sess.get(url, ssl=ssl)
        item = resp.json()
        if item.get('status') != 'ok':
            code = item.get('code')
            mesg = item.get('mesg')
            raise Exception(f'Logout error ({code}): {mesg}')

.. code:: python3
    :name: requests logout example

    import requests

    def logoutExample(sess, ssl):
        url = 'https://localhost:4443/api/v1/logout'
        resp = sess.get(url, verify=ssl)
        item = resp.json()
        if item.get('status') != 'ok':
            code = item.get('code')
            mesg = item.get('mesg')
            raise Exception(f'Logout error ({code}): {mesg}')

/api/v1/active
~~~~~~~~~~~~~~

*Method*
    GET

    This is an unauthenticated API that returns the leader status of Cell.

    *Returns*
        A dictionary with the ``active`` key set to True or False.

/api/v1/auth/users
~~~~~~~~~~~~~~~~~~

*Method*
    GET

    *Returns*
        A list of dictionaries, each of which represents a user on the system.

/api/v1/auth/roles
~~~~~~~~~~~~~~~~~~

*Method*
    GET

    *Returns*
        A list of dictionaries, each of which represents a role on the system.

/api/v1/auth/adduser
~~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API endpoint allows the caller to add a user to the system.

    *Input*
        This API expects the following JSON body::

            { "name": "myuser" }

        Any additional "user dictionary" fields (other than "iden") may be specified.

    *Returns*
        The newly created user dictionary.

/api/v1/auth/addrole
~~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API endpoint allows the caller to add a role to the system.

    *Input*
        This API expects the following JSON body::

            { "name": "myrole" }

        Any additional "role dictionary" fields (other than "iden") may be specified.

    *Returns*
        The newly created role dictionary.

/api/v1/auth/delrole
~~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API endpoint allows the caller to delete a role from the system.

    *Input*
        This API expects the following JSON body::

            { "name": "myrole" }

    *Returns*
        null

/api/v1/auth/user/<id>
~~~~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API allows the caller to modify specified elements of a user dictionary.

    *Input*
        This API expects a JSON dictionary containing any updated values for the user.

    *Returns*
        The updated user dictionary.

*Method*
    GET

    This API allows the caller to retrieve a user dictionary.

    *Returns*
        A user dictionary.

/api/v1/auth/password/<id>
~~~~~~~~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API allows the caller to change a user's password. The authenticated user must either be an admin or
    the user whose password is being changed.

    *Input*
        This API expects a JSON dictionary containing the key ``passwd`` with the new password string.

    *Returns*
        The updated user dictionary.


/api/v1/auth/role/<id>
~~~~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API allows the caller to modify specified elements of a role dictionary.

    *Input*
        This API expects a dictionary containing any updated values for the role.

    *Returns*
        The updated role dictionary.

*Method*
    GET

    This API allows the caller to retrieve a role dictionary.

    *Returns*
        A role dictionary.

/api/v1/auth/grant
~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API allows the caller to grant a role to a given user.

    *Input*
        This API expects the following JSON body::

            {
                "user": "<id>",
                "role": "<id>"
            }

    *Returns*
        The updated user dictionary.

/api/v1/auth/revoke
~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API allows the caller to revoke a role which was previously granted to a user.

    *Input*
        This API expects the following JSON body::

            {
                "user": "<id>",
                "role": "<id>"
            }

    *Returns*
        The updated user dictionary.

.. _http-api-cortex:

Cortex
------

A Synapse Cortex implements an HTTP API for interacting with the hypergraph and data model.  Some
of the provided APIs are pure REST APIs for simple data model operations and single/simple node
modification.  However, many of the HTTP APIs provided by the Cortex are streaming APIs which use
HTTP chunked encoding to deliver a stream of results as they become available.

The Cortex also implements the `Axon`_ HTTP API. Permissions are checked within the Cortex, and then
the request is executed on the Axon.

/api/v1/feed
~~~~~~~~~~~~

The Cortex feed API endpoint allows the caller to add nodes in bulk.

*Method*
    POST

    *Input*
        The API expects the following JSON body::

            {
                "items": [ <node>, ... ],
                # and optionally...
                "view": <iden>,
            }

        Each ``<node>`` is expected to be in packed tuple form::

            [ [<formname>, <formvalu>], {...} ]

    *Returns*
        The API returns ``{"status": "ok", "result": null}`` on success and any failures
        are returned using the previously mentioned REST API convention.

/api/v1/storm
~~~~~~~~~~~~~

The Storm API endpoint allows the caller to execute a Storm query on the Cortex and stream
back the messages generated during the Storm runtime execution.  In addition to returning nodes,
these messages include events for node edits, tool console output, etc. This streaming API has back-pressure,
and will handle streaming millions of results as the reader consumes them.
For more information about Storm APIs, including opts behavior, see :ref:`dev_storm_api`.

*Method*
    GET

    *Input*
        The API expects the following JSON body::

            {
                "query": "a storm query here",

                # optional
                "opts": {
                   ...
                }

                # optional 
                "stream": "jsonlines"
            }

    *Returns*
        The API returns a series of messages generated by the Storm runtime.  Each message is
        returned as an HTTP chunk, allowing readers to consume the resulting messages as a stream.

        The ``stream`` argument to the body modifies how the results are streamed back. Currently this
        optional argument can be set to ``jsonlines`` to get newline separated JSON data.


    *Examples*
        The following two examples show querying the ``api/v1/storm`` endpoint and receiving multiple message types.

        aiohttp example:

        .. code:: python3
            :name: aiohttp api/v1/storm example

            import json
            import pprint

            # Assumes sess is an aiohttp client session that has previously logged in

            query = '.created $lib.print($node.repr(".created")) | limit 3'
            data = {'query': query, 'opts': {'repr': True}}
            url = 'https://localhost:4443/api/v1/storm'

            async with sess.get(url, json=data) as resp:
                async for byts, x in resp.content.iter_chunks():

                    if not byts:
                        break

                    mesg = json.loads(byts)
                    pprint.pprint(mesg)

        requests example:

        .. code:: python3
            :name: requests api/v1/storm example

            import json
            import pprint
            # Assumes sess is an requests client session that has previously logged in

            query = '.created $lib.print($node.repr(".created")) | limit 3'
            data = {'query': query, 'opts': {'repr': True}}
            url = 'https://localhost:4443/api/v1/storm'

            resp = sess.get(url, json=data, stream=True)
            for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                mesg = json.loads(chunk)
                pprint.pprint(mesg)

        When working with these APIs across proxies, we have experienced issues with NGINX interfering with the
        chunked encoding. This may require more careful message reconstruction. The following shows using aiohttp
        to do that message reconstruction.

        .. code:: python3
            :name: chunked encoding reconstruction

            import json
            import pprint
            # Assumes sess is an requests client session that has previously logged in

            query = '.created $lib.print($node.repr(".created")) | limit 3'
            data = {'query': query, 'opts': {'repr': True}}
            url = 'https://localhost:4443/api/v1/storm'

            async with sess.get(url, json=data) as resp:

                buf = b""

                async for byts, chunkend in resp.content.iter_chunks():

                    if not byts:
                        break

                    buf += byts
                    if not chunkend:
                        continue

                    mesg = json.loads(buf)
                    buf = b""

                    pprint.pprint(buf)

/api/v1/storm/call
~~~~~~~~~~~~~~~~~~

The Storm Call API endpoint allows the caller to execute a Storm query on the Cortex and get a single return
value back from the runtime. This is analogous to using the ``callStorm()`` Telepath API. This expects to return a
value from the Storm query using the Storm ``return( )`` syntax.
For more information about Storm APIs, including opts behavior, see :ref:`dev_storm_api`.

*Method*
    GET

    *Input*
        The API expects the following JSON body::

            {
                "query": "a storm query here",

                # optional
                "opts": {
                    ...
                }
            }

    *Returns*
        The API returns ``{"status": "ok", "result": return_value}`` on success and any failures
        are returned using the previously mentioned REST API convention.

    *Examples*
        The following two examples show querying the ``api/v1/storm/call`` endpoint and receiving a return value.

        aiohttp example:

        .. code:: python3
            :name: aiohttp api/v1/storm/call example

            import pprint

            # Assumes sess is an aiohttp client session that has previously logged in

            query = '$foo = $lib.str.format("hello {valu}", valu="world") return ($foo)'
            data = {'query': query}
            url = 'https://localhost:4443/api/v1/storm/call'

            async with sess.get(url, json=data) as resp:
                info = await resp.json()
                pprint.pprint(info)

        requests example:

        .. code:: python3
            :name: requests api/v1/storm/call example

            import pprint
            # Assumes sess is an requests client session that has previously logged in

            query = '$foo = $lib.str.format("hello {valu}", valu="world") return ($foo)'
            data = {'query': query}
            url = 'https://localhost:4443/api/v1/storm/call'

            resp = sess.get(url, json=data)
            info = resp.json()
            pprint.pprint(info)


/api/v1/storm/nodes
~~~~~~~~~~~~~~~~~~~

.. warning::

    This API is deprecated in Synapse ``v2.110.0`` and will be removed in a future version.

The Storm nodes API endpoint allows the caller to execute a Storm query on the Cortex and stream
back the resulting nodes.  This streaming API has back-pressure, and will handle streaming millions
of results as the reader consumes them.

*Method*
    GET

    *Input*
        See /api/v1/storm for expected JSON body input.

    *Returns*
        The API returns the resulting nodes from the input Storm query.  Each node is returned
        as an HTTP chunk, allowing readers to consume the resulting nodes as a stream.

        Each serialized node will have the following structure::

            [
                [<form>, <valu>],       # The [ typename, typevalue ] definition of the node.
                {
                    "iden": <hash>,     # A stable identifier for the node.
                    "tags": {},         # The tags on the node.
                    "props": {},        # The node's secondary properties.

                    # optionally (if query opts included {"repr": True}
                    "reprs": {}         # Presentation values for props which need it.
                }
            ]

        The ``stream`` argument, documented in the /api/v1/storm endpoint, modifies how the nodes
        are streamed back. Currently this optional argument can be set to ``jsonlines`` to get newline
        separated JSON data.

/api/v1/storm/export
~~~~~~~~~~~~~~~~~~~~

The Storm export API endpoint allows the caller to execute a Storm query on the Cortex and export the resulting nodes
in msgpack format such that they can be directly ingested with the ``syn.nodes`` feed function.

*Method*
    GET

    *Input*
        See /api/v1/storm for expected JSON body input.

    *Returns*
        The API returns the resulting nodes from the input Storm query. This API yields nodes after an initial complete
        lift in order to limit exported edges.

        Each exported node will be in msgpack format.

        There is no Content-Length header returned, since the API cannot predict the volume of data a given query
        may produce.

/api/v1/model
~~~~~~~~~~~~~

*Method*
    GET

    This API allows the caller to retrieve the current Cortex data model.

    *Input*
        The API takes no input.

    *Returns*
        The API returns the model in a dictionary, including the types, forms and tagprops.  Secondary
        property information is also included for each form::

            {
                "types": {
                    ...  # dictionary of type definitions
                },
                "forms": {
                    ...  # dictionary of form definitions, including secondary properties
                },
                "tagprops": {
                    ...  # dictionary of tag property definitions
                }
            }


/api/v1/model/norm
~~~~~~~~~~~~~~~~~~

*Method*
    GET, POST

    This API allows the caller to normalize a value based on the Cortex data model.  This may be called via a GET or
    POST requests.

    *Input*
        The API expects the following JSON body::

            {
                "prop": "prop:name:here",
                "value": <value>,
            }

    *Returns*
        The API returns the normalized value as well as any parsed subfields or type specific info::

            {
                "norm": <value>,
                "info": {
                    "subs": {},
                    ...
                }
            }

/api/v1/storm/vars/get
~~~~~~~~~~~~~~~~~~~~~~

*Method*
    GET
    
    This API allows the caller to retrieve a storm global variable.
    
    *Input*
        The API expects the following JSON body::
        
            {
                "name": "varnamehere",
                "default": null,
            }
            
    *Returns*
        The API returns the global variable value or the specified default using the REST API convention described earlier.

/api/v1/storm/vars/set
~~~~~~~~~~~~~~~~~~~~~~

*Method*
    POST
    
    This API allows the caller to set a storm global variable.
    
    *Input*
        The API expects the following JSON body::
        
            {
                "name": "varnamehere",
                "value": <value>,
            }
            
    *Returns*
        The API returns `true` using the REST API convention described earlier.
        
/api/v1/storm/vars/pop
~~~~~~~~~~~~~~~~~~~~~~

*Method*
    POST
    
    This API allows the caller to pop/delete a storm global variable.
    
    *Input*
        The API expects the following JSON body::
        
            {
                "name": "varnamehere",
                "default": <value>,
            }
            
    *Returns*
        The API returns the current value of the variable or default using the REST API convention described earlier.


/api/v1/core/info
~~~~~~~~~~~~~~~~~

*Method*
    GET

    This API allows the caller to retrieve the current Cortex version, data model definitions, and Storm information.

    *Input*
        The API takes no input.

    *Returns*
        The API returns the model in a dictionary, including the types, forms and tagprops.  Secondary
        property information is also included for each form::

            {
                "version": [ <major>, <minor>, <patch> ], # Version tuple 
                "modeldict": {
                    ...  # dictionary of model definitions
                },
                "stormdocs": {
                    "libraries": [
                        ... # list of information about Storm libraries.
                    ],
                    "types": [
                        ... # list of information about Storm types.
                    ]
                }
            }

/api/ext/*
~~~~~~~~~~

This API endpoint is used as the Base URL for Extended HTTP API endpoints which are user defined. See
:ref:`devops-svc-cortex-ext-http` for additional information about this endpoint.


Aha
---

A Synapse Aha service implements an HTTP API for assisting with devops.

/api/v1/aha/provision/service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*Method*
    POST

    This API allows the caller to generate an AHA provisioning URL.
    
    *Input*
        The API expects the following JSON body::
        
            {
                "name": " ... name of the service being provisioned",
                "provinfo": {
                    "dmon:port": # optional integer, default Telepath listening port.
                    "https:port": # optional integer, default HTTPS listening port.
                    "mirror": # optional string, service to Mirror.
                    "conf": {
                        ... # optional, default service configuration values.
                    }
                }
            }
    
    *Returns*
        The API returns the following provisioning information.  The data is returned using the REST API convention described earlier::
        
            {
                "url": "< the AHA provisioning URL >",
            }


/api/v1/aha/services
~~~~~~~~~~~~~~~~~~~~

*Method*
    GET

    This API allows the caller to get a list of all the registered services.

    *Input*
        The API accepts the following  **optional** JSON body::

            {
                "network": " ... name of the aha network to list",
            }

    *Returns*
        The API returns the following provisioning information.  The data is returned using the REST API
        convention described earlier::

            [
                {
                    "name": "< the full service name >",
                    "svcname": "< service name part >",
                    "svcnetw": "< service network part >",
                    "svcinfo": {
                        "run": "< runtime service identifier >",
                        "iden": "< persistent service identifier >",
                        "leader": "< service leader name >",
                        "urlinfo": {
                            "scheme": "< listening scheme >",
                            "port": listening port,
                            "path": "< listening path >",
                            "host": "< listening IP address >"
                        },
                        "ready": < boolean indicating the service is either an active leader or in the realtime change event window >,
                        "online": < runtime aha identifier if the service is connected >
                    }
                },
                ...
            ]

Axon
----

A Synapse Axon implements an HTTP API for uploading and downloading files.
The HTTP APIs use HTTP chunked encoding for handling large files.

/api/v1/axon/files/del
~~~~~~~~~~~~~~~~~~~~~~

This API allows the caller to delete multiple files from the Axon by the SHA-256.

*Method*
    POST
    
    *Input*
        The API expects the following JSON body::
        
            {
                "sha256s": [<sha256>, ...],
            }
            
    *Returns*
        The API returns an array of SHA-256 and boolean values representing whether each was found in the Axon and deleted. The array is returned using the REST API convention described earlier.
        

/api/v1/axon/files/put
~~~~~~~~~~~~~~~~~~~~~~

This API allows the caller to upload and save a file to the Axon.  This may be called via a PUT or POST request.

*Method*
    PUT, POST

    *Input*
        The API expects a stream of byte chunks.

    *Returns*
        On successful upload, or if the file already existed, the API returns information about the file::
        
            {
              "md5": "<the md5sum value of the uploaded bytes>",
              "sha1": "<the sha1 value of the uploaded bytes>",
              "sha256": "<the sha256 value of the uploaded bytes>",
              "sha512": "<the sha512 value of the uploaded bytes>",
              "size": <the size of the uploaded bytes>
            }


/api/v1/axon/files/has/sha256/<SHA-256>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This API allows the caller to check if a file exists in the Axon as identified by the SHA-256.

*Method*
    GET
    
    *Returns*
        True if the file exists; False if the file does not exist.


/api/v1/axon/files/by/sha256/<SHA-256>
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This API allows the caller to retrieve or remove a file from the Axon as identified by the SHA-256.  If the file does
not exist a 404 will be returned.

*Method*
    GET
    
    *Returns*
        If the file exists a stream of byte chunks will be returned to the caller. A ``Range`` header with a single
        ``bytes`` value can be provided to get a subset of a file.

*Method*
     HEAD
     
     *Returns*
        If the file exists, the ``Content-Length`` header will be set for the size of the file. If a ``Range`` header
        with a single ``bytes`` value is provided, the ``Content-Length`` header will describe the size of the range,
        and the ``Content-Range`` header will also be set to describe the range of the requested bytes.

*Method*
    DELETE
    
    *Returns*
        Boolean via the REST API convention described earlier.  If the file is not found an error is returned.
        


.. _HTTPAPI Examples: https://github.com/vertexproject/synapse/tree/master/examples/httpapi
