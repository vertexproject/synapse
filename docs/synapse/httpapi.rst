Synapse HTTP/REST API Documentation
===================================

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

/login
~~~~~~

The /login API endpoint may be used to create an authenticated session.  This
session may then be used to call other HTTP API endpoints as the authenticated user.

.. code-block:: python

    import aiohttp

    async def logInExample():

        async with aiohttp.ClientSession() as sess:

            info = {'name': 'visi', 'passwd': 'secret'}
            async with sess.post(f'https://localhost:56443/login', json=info) as resp:
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

.. _index:              ../index.html
