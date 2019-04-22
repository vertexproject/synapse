
.. _http-api:

Synapse HTTP/REST API
=====================

Many components within the Synapse ecosystem provide HTTP/REST APIs to
provide a portable interface.  Some of these APIs are RESTful, while other
(streaming data) APIs are technically not.

HTTP/REST API Conventions
-------------------------

All Synapse RESTful APIs use HTTP GET/POST methods to retrieve and modify data.
All POST requests expect a JSON body.  Each RESTful API call will return a
result wrapper dictionary with one of two conventions.

For a successful API call::

    {"status": "ok", "result": "some api result here"}

or for an unsuccessful API call::

    {"status": "err": "code": "ErrCodeString", "mesg": "A humon friendly message."}

Streaming HTTP API endpoints, such as the interface provided to retrieve nodes
from a Synapse Cortex, provide JSON results via HTTP chunked encoding where each
chunk is a single result.

Client example code in these docs uses the python "aiohttp" module and assumes
familiarity with python asynchronous code conventions.  However, they should be
enough to understand the APIs basic operation.

Authentication
--------------

While not in "insecure" mode, most Synapse HTTP APIs require an authenticated user.
HTTP API endpoints requiring authentication may be accessed using either HTTP Basic
authentication via the HTTP "Authorization" header or as part of an authenticated
session.  For more information on configuring users/roles see TODO.

To create and use an authenticated session, the HTTP client library must support
cookies.

/api/v1/login
~~~~~~~~~~~~~

The login API endpoint may be used to create an authenticated session.  This
session may then be used to call other HTTP API endpoints as the authenticated user.

.. code-block:: python

    import aiohttp

    async def logInExample():

        async with aiohttp.ClientSession() as sess:

            info = {'user': 'visi', 'passwd': 'secret'}
            async with sess.post(f'https://localhost:56443/api/v1/login', json=info) as resp:
                item = await resp.json()
                if item.get('status') != 'ok':
                    code = item.get('code')
                    mesg = item.get('mesg')
                    raise Exception(f'Login error ({code}): {mesg}')

            # we are now clear to make additional HTTP API calls using sess

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
        The newly created role dictionary.

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

    This API allows the caller to retrieve a user dictionary.

    *Returns*
        A user dictionary.

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

Cortex
------

A Synapse Cortex implements an HTTP API for interacting with the hypergraph and data model.  Some
of the provided APIs are pure REST APIs for simple data model operations and single/simple node
modification.  However, many of the HTTP APIs provided by the Cortex are streaming APIs which use
HTTP chunked encoding to deliver a stream of results as they become available.

/api/v1/storm
~~~~~~~~~~~~~

The Storm API endpoint allows the caller to execute a Storm query on the Cortex and stream
back the messages generated during the Storm runtime execution.  In addition to returning nodes,
these messsages include events for node edits, tool console output, etc.

*Method*
    GET

    *Input*
        The API expects the following JSON body::

            {
                "query": "a storm query here",

                # optionally...

                "opts": {
                    "repr": <bool>,         # Add optional "reprs" field to returned nodes.
                    "limit": <int>,         # Limit the total number of nodes to be returned.
                    "vars": {
                        <name>: <value>,    # Variables to map into the Storm query runtime.
                    },
                    "ndefs": []             # A list of [form, valu] tuples to use as initial input.
                    "idens": []             # A list of node iden hashes to use as initial input.
                }
            }

    *Returns*
        The API returns a series of messages generated by the Storm runtime.  Each message is
        returned as an HTTP chunk, alling readers to consume the resulting nodes as a stream.

        Each message has the following basic structure::

            [ "type", { ..type specific info... } ]

/api/v1/storm/nodes
~~~~~~~~~~~~~~~~~~~

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

.. _index:              ../index.html
