
<a id="stormtypes-libs-header"></a>

# Storm Libraries


Storm Libraries represent powerful tools available inside of the Storm query language.


<a id="stormlibs-lib"></a>

## $lib

The Base Storm Library. This mainly contains utility functionality.


<a id="stormlibs-lib-cast"></a>

### $lib.cast(name, valu)

Normalize a value as a Synapse Data Model Type.

**Args:**

- `name` (`str`): The name of the model type to normalize the value as.
- `valu` (`any`): The value to normalize.


**Returns:**
The normalized value. The return type is `prim`.

<a id="stormlibs-lib-copy"></a>

### $lib.copy(item)

Create and return a deep copy of the given storm object.

Note:
    This is currently limited to msgpack compatible primitives and Node, NodeRef, or Vault objects.

Examples:
    Make a copy of a list or dict::

        $copy = $lib.copy($item)


**Args:**

- `item` (`prim`): The item to make a copy of.


**Returns:**
A deep copy of the object. The return type is `prim`.

<a id="stormlibs-lib-debug"></a>

### $lib.debug

True if the current runtime has debugging enabled.

Note:
    The debug state is inherited by sub-runtimes at instantiation time.  Any
    changes to a runtime's debug state do not percolate automatically.

Examples:
    Check if the runtime is in debug and print a message::

        if $lib.debug {
            $lib.print('Doing stuff!')
        }

    Update the current runtime to enable debugging::

        $lib.debug = (true)

**Returns:**
The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).
When this is used to set the value, it does not have a return type.

<a id="stormlibs-lib-exit"></a>

### $lib.exit(mesg=(null))

Cause a Storm Runtime to stop running.

**Args:**

- `mesg` (`str`): Optional string to warn.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-fire"></a>

### $lib.fire(name, **info)

Fire an event onto the runtime.

Notes:
    This fires events as ``storm:fire`` event types. The name of the event is placed into a ``type`` key,
    and any additional keyword arguments are added to a dictionary under the ``data`` key.

Examples:
    Fire an event called ``demo`` with some data::

        storm> $foo='bar' $lib.fire('demo', foo=$foo, knight='ni')
        ...
        ('storm:fire', {'type': 'demo', 'data': {'foo': 'bar', 'knight': 'ni'}})
        ...


**Args:**

- `name` (`str`): The name of the event to fire.
- `**info` (`any`): Additional keyword arguments containing data to add to the event.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-guid"></a>

### $lib.guid(*args, valu=$lib.undef)

Get a random guid, or generate a guid from the arguments.

**Args:**

- `*args` (`prim`): Arguments which are hashed to create a guid.
- `valu` (`prim`): Create a guid from a single value (no positional arguments can be specified).


**Returns:**
A guid. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-import"></a>

### $lib.import(name, debug=(false), reqvers=(null))

Import a Storm module.

**Args:**

- `name` (`str`): Name of the module to import.
- `debug` (`boolean`): Enable debugging in the module.
- `reqvers` (`str`): Version requirement for the imported module.


**Returns:**
A ``lib`` instance representing the imported package. The return type is `lib`.

<a id="stormlibs-lib-len"></a>

### $lib.len(item)

Get the length of a item.

This could represent the size of a string, or the number of keys in
a dictionary, or the number of elements in an array. It may also be used
to iterate an emitter or yield function and count the total.

**Args:**

- `item` (`prim`): The item to get the length of.


**Returns:**
The length of the item. The return type is `int`.

<a id="stormlibs-lib-max"></a>

### $lib.max(*args)

Get the maximum value in a list of arguments.

**Args:**

- `*args` (`any`): List of arguments to evaluate.


**Returns:**
The largest argument. The return type is `int`.

<a id="stormlibs-lib-min"></a>

### $lib.min(*args)

Get the minimum value in a list of arguments.

**Args:**

- `*args` (`any`): List of arguments to evaluate.


**Returns:**
The smallest argument. The return type is `int`.

<a id="stormlibs-lib-pprint"></a>

### $lib.pprint(item, prefix='', clamp=(null))

The pprint API should not be considered a stable interface.

**Args:**

- `item` (`any`): Item to pprint
- `prefix` (`str`): Line prefix.
- `clamp` (`int`): Line clamping length.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-print"></a>

### $lib.print(mesg)

Print a message to the runtime.

Examples:
    Print a simple string::

        storm> $lib.print("Hello world!")
        Hello world!

    Format and print string based on variables::

        storm> $d=({"key1": (1), "key2": "two"})
             for ($key, $value) in $d { $lib.print(`{$key} => {$value}`) }
        key1 => 1
        key2 => two

    Use values off of a node to format and print string::

        storm> inet:ipv4:asn
             $lib.print(`node: {$node.ndef}, asn: {:asn}`) | spin
        node: ('inet:ipv4', 16909060), asn: 1138

Notes:
    Arbitrary objects can be printed as well. They will have their Python __repr()__ printed.



**Args:**

- `mesg` (`str`): String to print.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-raise"></a>

### $lib.raise(name, mesg, **info)

Raise an exception in the storm runtime.

**Args:**

- `name` (`str`): The name of the error condition to raise.
- `mesg` (`str`): A friendly description of the specific error.
- `**info` (`any`): Additional metadata to include in the exception.


**Returns:**
This function does not return. The return type is `null`.

<a id="stormlibs-lib-range"></a>

### $lib.range(stop, start=(null), step=(null))

Generate a range of integers.

Examples:
    Generate a sequence of integers based on the size of an array::

        storm> $a=(foo,bar,(2)) for $i in $lib.range($lib.len($a)) {$lib.fire('test', indx=$i, valu=$a.$i)}
        Executing query at 2021/03/22 19:25:48.835
        ('storm:fire', {'type': 'test', 'data': {'index': 0, 'valu': 'foo'}})
        ('storm:fire', {'type': 'test', 'data': {'index': 1, 'valu': 'bar'}})
        ('storm:fire', {'type': 'test', 'data': {'index': 2, 'valu': 2}})

Notes:
    The range behavior is the same as the Python3 ``range()`` builtin Sequence type.


**Args:**

- `stop` (`int`): The value to stop at.
- `start` (`int`): The value to start at.
- `step` (`int`): The range step size.


**Yields:**
The sequence of integers. The return type is `int`.

<a id="stormlibs-lib-repr"></a>

### $lib.repr(name, valu)

Attempt to convert a system mode value to a display mode string.

Examples:
    Print the Synapse user name for an iden::

        $lib.print($lib.repr(syn:user, $iden))



**Args:**

- `name` (`str`): The name of the model type.
- `valu` (`any`): The value to convert.


**Returns:**
A display mode representation of the value. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-set"></a>

### $lib.set(*vals)

Get a Storm Set object.

**Args:**

- `*vals` (`any`): Initial values to place in the set.


**Returns:**
The new set. The return type is [`set`](stormtypes_prims.md#stormprims-set-f527).

<a id="stormlibs-lib-sorted"></a>

### $lib.sorted(valu, reverse=(false))

Yield sorted values.

**Args:**

- `valu` (`any`): An iterable object to sort.
- `reverse` (`boolean`): Reverse the sort order.


**Yields:**
Yields the sorted output. The return type is `any`.

<a id="stormlibs-lib-trycast"></a>

### $lib.trycast(name, valu)

Attempt to normalize a value and return status and the normalized value.

Examples:
    Do something if the value is a valid IPV4::

        ($ok, $ipv4) = $lib.trycast(inet:ipv4, 1.2.3.4)
        if $ok { $dostuff($ipv4) }


**Args:**

- `name` (`str`): The name of the model type to normalize the value as.
- `valu` (`any`): The value to normalize.


**Returns:**
A list of (<boolean>, <prim>) for status and normalized value. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-undef"></a>

### $lib.undef

This constant can be used to unset variables and derefs.

Examples:
    Unset the variable $foo::

        $foo = $lib.undef

    Remove a dictionary key bar::

        $foo.bar = $lib.undef

    Remove a list index of 0::

        $foo.0 = $lib.undef


**Returns:**
The type is `undef`.

<a id="stormlibs-lib-warn"></a>

### $lib.warn(mesg)

Print a warning message to the runtime.

Notes:
    Arbitrary objects can be warned as well. They will have their Python __repr()__ printed.


**Args:**

- `mesg` (`str`): String to warn.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-aha"></a>

## $lib.aha

A Storm Library for interacting with AHA.


<a id="stormlibs-lib-aha-callPeerApi"></a>

### $lib.aha.callPeerApi(svcname, todo, timeout=(null), skiprun=(null))

Call an API on all peers (leader and mirrors) of an AHA service and yield the responses from each.

        Examples:
            Call getCellInfo on an AHA service::

                $todo = $lib.utils.todo('getCellInfo')
                for $info in $lib.aha.callPeerApi(cortex..., $todo) {
                    $lib.print($info)
                }

            Call getCellInfo on an AHA service, skipping the invoking service::

                $todo = $lib.utils.todo('getCellInfo')
                for $info in $lib.aha.callPeerApi(cortex..., $todo, skiprun=$lib.cell.getCellInfo().cell.run) {
                    $lib.print($info)
                }

            Call method with arguments::

                $todo = $lib.utils.todo(('method', ([1, 2]), ({'foo': 'bar'})))
                for $info in $lib.aha.callPeerApi(cortex..., $todo) {
                    $lib.print($info)
                }

        

**Args:**

- `svcname` (`str`): The name of the AHA service to call. It is easiest to use the relative name of a service, ending with "...".
- `todo` (`list`): The todo tuple (name, args, kwargs).
- `timeout` (`int`): Optional timeout in seconds.
- `skiprun` (`str`): Optional run ID argument that allows skipping results from a specific service run ID.
                                  This is most often used to omit the invoking service from the results, ensuring that only responses from other services are included.
                        


**Yields:**
Yields the results of the API calls as tuples of (svcname, (ok, info)). The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-aha-callPeerGenr"></a>

### $lib.aha.callPeerGenr(svcname, todo, timeout=(null), skiprun=(null))

Call a generator API on all peers (leader and mirrors) of an AHA service and yield the responses from each.

        Examples:
            Call getNexusChanges on an AHA service::

                $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                for $info in $lib.aha.callPeerGenr(cortex..., $todo) {
                    $lib.print($info)
                }

            Call getNexusChanges on an AHA service, skipping the invoking service::

                $todo = $lib.utils.todo('getNexusChanges', (0), wait=(false))
                for $info in $lib.aha.callPeerGenr(cortex..., $todo, skiprun=$lib.cell.getCellInfo().cell.run) {
                    $lib.print($info)
                }

        

**Args:**

- `svcname` (`str`): The name of the AHA service to call. It is easiest to use the relative name of a service, ending with "...".
- `todo` (`list`): The todo tuple (name, args, kwargs).
- `timeout` (`int`): Optional timeout in seconds.
- `skiprun` (`str`): Optional run ID argument that allows skipping results from a specific service run ID.
                                  This is most often used to omit the invoking service from the results, ensuring that only responses from other services are included.
                       


**Yields:**
Yields the results of the API calls as tuples containing (svcname, (ok, info)). The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-aha-del"></a>

### $lib.aha.del(svcname)

Delete a service from AHA.

        Examples:
            Deleting a service with its relative name::

                $lib.aha.del(00.mysvc...)

            Deleting a service with its full name::

                $lib.aha.del(00.mysvc.loop.vertex.link)
        

**Args:**

- `svcname` (`str`): The name of the service to delete. It is easiest to use the relative name of a service, ending with "...".


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-aha-get"></a>

### $lib.aha.get(svcname, filters=(null))

Get information about an AHA service.

        Examples:
            Getting service information with a relative name::

                $lib.aha.get(000.cortex...)

            Getting service information with its full name::

                $lib.aha.get(000.cortex.loop.vertex.link)
        

**Args:**

- `svcname` (`str`): The name of the AHA service to look up. It is easiest to use the relative name of a service, ending with "...".
- `filters` (`dict`): An optional dictionary of filters to use when resolving the AHA service.


**Returns:**
The AHA service information dictionary, or ``(null))``. The return type may be one of the following: `null`, [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-aha-list"></a>

### $lib.aha.list()

Enumerate all of the AHA services.

**Yields:**
The AHA service dictionaries. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-auth"></a>

## $lib.auth

A Storm Library for interacting with Auth in the Cortex.


<a id="stormlibs-lib-auth-getPermDef"></a>

### $lib.auth.getPermDef(perm)

Return a single permission definition.

**Args:**

- `perm` (`list`): A permission tuple.


**Returns:**
A permission definition or null. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-auth-getPermDefs"></a>

### $lib.auth.getPermDefs()

Return a list of permission definitions.

**Returns:**
The list of permission definitions. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-auth-ruleFromText"></a>

### $lib.auth.ruleFromText(text)

Get a rule tuple from a text string.

**Args:**

- `text` (`str`): The string to process.


**Returns:**
A tuple containing a boolean and a list of permission parts. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-auth-textFromRule"></a>

### $lib.auth.textFromRule(rule)

Return a text string from a rule tuple.

**Args:**

- `rule` (`list`): A rule tuple.


**Returns:**
The rule text. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-auth-easyperm"></a>

## $lib.auth.easyperm

A Storm Library for interacting with easy perm dictionaries.


<a id="stormlibs-lib-auth-easyperm-allowed"></a>

### $lib.auth.easyperm.allowed(edef, level)

Check if the current user has a permission level in an easy perm dictionary.

**Args:**

- `edef` (`dict`): The easy perm dictionary to check.
- `level` (`int`): The required permission level number.


**Returns:**
True if the user meets the requirement, false otherwise. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-auth-easyperm-confirm"></a>

### $lib.auth.easyperm.confirm(edef, level, mesg=(null))

Require that the current user has a permission level in an easy perm dictionary.

**Args:**

- `edef` (`dict`): The easy perm dictionary to check.
- `level` (`int`): The required permission level number.
- `mesg` (`str`): Optional error message to present if user does not have required permission level.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-auth-easyperm-init"></a>

### $lib.auth.easyperm.init(edef=(null), default=(1))

Add the easy perm structure to a new or existing dictionary.

Note:
    The current user will be given admin permission in the new
    easy perm structure.


**Args:**

- `edef` (`dict`): A dictionary to add easy perms to.
- `default` (`int`): Specify the default permission level for this item.


**Returns:**
Dictionary with the easy perm structure. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-auth-easyperm-level-admin"></a>

### $lib.auth.easyperm.level.admin

Constant for admin permission.

**Returns:**
The type is `int`.

<a id="stormlibs-lib-auth-easyperm-level-deny"></a>

### $lib.auth.easyperm.level.deny

Constant for deny permission.

**Returns:**
The type is `int`.

<a id="stormlibs-lib-auth-easyperm-level-edit"></a>

### $lib.auth.easyperm.level.edit

Constant for edit permission.

**Returns:**
The type is `int`.

<a id="stormlibs-lib-auth-easyperm-level-read"></a>

### $lib.auth.easyperm.level.read

Constant for read permission.

**Returns:**
The type is `int`.

<a id="stormlibs-lib-auth-easyperm-set"></a>

### $lib.auth.easyperm.set(edef, scope, iden, level)

Set the permission level for a user or role in an easy perm dictionary.

**Args:**

- `edef` (`dict`): The easy perm dictionary to modify.
- `scope` (`str`): The scope, either "users" or "roles".
- `iden` (`str`): The user/role iden depending on scope.
- `level` (`int`): The permission level number, or None to remove the permission.


**Returns:**
Dictionary with the updated easy perm structure. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-auth-gates"></a>

## $lib.auth.gates

A Storm Library for interacting with Auth Gates in the Cortex.


<a id="stormlibs-lib-auth-gates-get"></a>

### $lib.auth.gates.get(iden)

Get a specific Gate by iden.

**Args:**

- `iden` (`str`): The iden of the gate to retrieve.


**Returns:**
The ``auth:gate`` if it exists, otherwise null. The return type may be one of the following: `null`, [`auth:gate`](stormtypes_prims.md#stormprims-auth-gate-f527).

<a id="stormlibs-lib-auth-gates-list"></a>

### $lib.auth.gates.list()

Get a list of Gates in the Cortex.

**Returns:**
A list of ``auth:gate`` objects. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-auth-roles"></a>

## $lib.auth.roles

A Storm Library for interacting with Auth Roles in the Cortex.


<a id="stormlibs-lib-auth-roles-add"></a>

### $lib.auth.roles.add(name, iden=(null))

Add a Role to the Cortex.

**Args:**

- `name` (`str`): The name of the role.
- `iden` (`str`): The iden to assign to the new role.


**Returns:**
The new role object. The return type is [`auth:role`](stormtypes_prims.md#stormprims-auth-role-f527).

<a id="stormlibs-lib-auth-roles-byname"></a>

### $lib.auth.roles.byname(name)

Get a specific Role by name.

**Args:**

- `name` (`str`): The name of the role to retrieve.


**Returns:**
The role by name, or null if it does not exist. The return type may be one of the following: `null`, [`auth:role`](stormtypes_prims.md#stormprims-auth-role-f527).

<a id="stormlibs-lib-auth-roles-del"></a>

### $lib.auth.roles.del(iden)

Delete a Role from the Cortex.

**Args:**

- `iden` (`str`): The iden of the role to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-auth-roles-get"></a>

### $lib.auth.roles.get(iden)

Get a specific Role by iden.

**Args:**

- `iden` (`str`): The iden of the role to retrieve.


**Returns:**
The ``auth:role`` object; or null if the role does not exist. The return type may be one of the following: `null`, [`auth:role`](stormtypes_prims.md#stormprims-auth-role-f527).

<a id="stormlibs-lib-auth-roles-list"></a>

### $lib.auth.roles.list()

Get a list of Roles in the Cortex.

**Returns:**
A list of ``auth:role`` objects. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-auth-users"></a>

## $lib.auth.users

A Storm Library for interacting with Auth Users in the Cortex.


<a id="stormlibs-lib-auth-users-add"></a>

### $lib.auth.users.add(name, passwd=(null), email=(null), iden=(null))

Add a User to the Cortex.

**Args:**

- `name` (`str`): The name of the user.
- `passwd` (`str`): The user's password.
- `email` (`str`): The user's email address.
- `iden` (`str`): The iden to use to create the user.


**Returns:**
The ``auth:user`` object for the new user. The return type is [`auth:user`](stormtypes_prims.md#stormprims-auth-user-f527).

<a id="stormlibs-lib-auth-users-byemail"></a>

### $lib.auth.users.byemail(email)

Get a specific user by email address.

**Args:**

- `email` (`str`): The email of the user to retrieve.


**Returns:**
The ``auth:user`` object, or null if the user does not exist. The return type may be one of the following: `null`, [`auth:user`](stormtypes_prims.md#stormprims-auth-user-f527).

<a id="stormlibs-lib-auth-users-byname"></a>

### $lib.auth.users.byname(name)

Get a specific user by name.

**Args:**

- `name` (`str`): The name of the user to retrieve.


**Returns:**
The ``auth:user`` object, or null if the user does not exist. The return type may be one of the following: `null`, [`auth:user`](stormtypes_prims.md#stormprims-auth-user-f527).

<a id="stormlibs-lib-auth-users-del"></a>

### $lib.auth.users.del(iden)

Delete a User from the Cortex.

**Args:**

- `iden` (`str`): The iden of the user to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-auth-users-get"></a>

### $lib.auth.users.get(iden=(null))

Get a specific User by iden.

**Args:**

- `iden` (`str`): The iden of the user to retrieve. Returns the current user if not specified.


**Returns:**
The ``auth:user`` object, or null if the user does not exist. The return type may be one of the following: `null`, [`auth:user`](stormtypes_prims.md#stormprims-auth-user-f527).

<a id="stormlibs-lib-auth-users-list"></a>

### $lib.auth.users.list()

Get a list of Users in the Cortex.

**Returns:**
A list of ``auth:user`` objects. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-axon"></a>

## $lib.axon

A Storm library for interacting with the Cortex's Axon.

For APIs that accept an ssl argument, the dictionary may contain the following values::

    ({
        'verify': <bool> - Perform SSL/TLS verification. Default is True.
        'client_cert': <str> - PEM encoded full chain certificate for use in mTLS.
        'client_key': <str> - PEM encoded key for use in mTLS. Alternatively, can be included in client_cert.
    })

For APIs that accept a proxy argument, the following values are supported::

    ``(true)``: Use the proxy defined by the http:proxy configuration option if set.
    ``(false)``: Do not use the proxy defined by the http:proxy configuration option if set.
    <str>: A proxy URL string.


<a id="stormlibs-lib-axon-csvrows"></a>

### $lib.axon.csvrows(sha256, dialect='excel', errors='ignore', **fmtparams)

Yields CSV rows from a CSV file stored in the Axon.

Notes:
    The dialect and fmtparams expose the Python csv.reader() parameters.

Example:
    Get the rows from a given csv file::

        for $row in $lib.axon.csvrows($sha256) {
            $dostuff($row)
        }

    Get the rows from a given tab separated file::

        for $row in $lib.axon.csvrows($sha256, delimiter="\t") {
            $dostuff($row)
        }


**Args:**

- `sha256` (`str`): The SHA256 hash of the file.
- `dialect` (`str`): The default CSV dialect to use.
- `errors` (`str`): Specify how encoding errors should handled.
- `**fmtparams` (`any`): Format arguments.


**Yields:**
A list of strings from the CSV file. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-axon-del"></a>

### $lib.axon.del(sha256)

Remove the bytes from the Cortex's Axon by sha256.

Example:
    Delete files from the axon based on a tag::

        file:bytes#foo +:sha256 $lib.axon.del(:sha256)


**Args:**

- `sha256` (`str`): The sha256 of the bytes to remove from the Axon.


**Returns:**
True if the bytes were found and removed. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-axon-dels"></a>

### $lib.axon.dels(sha256s)

Remove multiple byte blobs from the Cortex's Axon by a list of sha256 hashes.

Example:
    Delete a list of files (by hash) from the Axon::

        $list = ($hash0, $hash1, $hash2)
        $lib.axon.dels($list)


**Args:**

- `sha256s` (`list`): A list of sha256 hashes to remove from the Axon.


**Returns:**
A list of boolean values that are True if the bytes were found. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-axon-has"></a>

### $lib.axon.has(sha256)

Check if the Axon the Cortex is configured to use has a given sha256 value.

Examples:
    Check if the Axon has a given file::

        # This example assumes the Axon does have the bytes
        storm> if $lib.axon.has(9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08) {
                $lib.print("Has bytes")
            } else {
                $lib.print("Does not have bytes")
            }

        Has bytes


**Args:**

- `sha256` (`str`): The sha256 value to check.


**Returns:**
True if the Axon has the file, false if it does not. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-axon-hashset"></a>

### $lib.axon.hashset(sha256)

Return additional hashes of the bytes stored in the Axon for the given sha256.

Examples:
    Get the md5 hash for a file given a variable named ``$sha256``::

        $hashset = $lib.axon.hashset($sha256)
        $md5 = $hashset.md5


**Args:**

- `sha256` (`str`): The sha256 value to calculate hashes for.


**Returns:**
A dictionary of additional hashes. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-axon-jsonlines"></a>

### $lib.axon.jsonlines(sha256, errors='ignore')

Yields JSON objects from a JSON-lines file stored in the Axon.

Example:
    Get the JSON objects from a given JSONL file::

        for $item in $lib.axon.jsonlines($sha256) {
            $dostuff($item)
        }


**Args:**

- `sha256` (`str`): The SHA256 hash of the file.
- `errors` (`str`): Specify how encoding errors should handled.


**Yields:**
A JSON object parsed from a line of text. The return type is `any`.

<a id="stormlibs-lib-axon-list"></a>

### $lib.axon.list(offs=(0), wait=(false), timeout=(null))

List (offset, sha256, size) tuples for files in the Axon in added order.

Example:
    List files::

        for ($offs, $sha256, $size) in $lib.axon.list() {
            $lib.print($sha256)
        }

    Start list from offset 10::

        for ($offs, $sha256, $size) in $lib.axon.list(10) {
            $lib.print($sha256)
        }


**Args:**

- `offs` (`int`): The offset to start from.
- `wait` (`boolean`): Wait for new results and yield them in realtime.
- `timeout` (`int`): The maximum time to wait for a new result before returning.


**Yields:**
Tuple of (offset, sha256, size) in added order. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-axon-metrics"></a>

### $lib.axon.metrics()

Get runtime metrics of the Axon.

Example:
    Print the total number of files stored in the Axon::

        $data = $lib.axon.metrics()
        $lib.print(`The Axon has {$data."file:count"} files`)


**Returns:**
A dictionary containing runtime data about the Axon. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-axon-put"></a>

### $lib.axon.put(byts)

Save the given bytes variable to the Axon the Cortex is configured to use.

Examples:
    Save a base64 encoded buffer to the Axon::

        storm> $s='dGVzdA==' $buf=$lib.base64.decode($s) ($size, $sha256)=$lib.axon.put($buf)
             $lib.print(`size={$size} sha256={$sha256}`)

        size=4 sha256=9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08

**Args:**

- `byts` (`bytes`): The bytes to save.


**Returns:**
A tuple of the file size and sha256 value. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-axon-read"></a>

### $lib.axon.read(sha256, offs=(0), size=(1048576))

Read bytes from a file stored in the Axon by its SHA256 hash.

Examples:
    Read 100 bytes starting at offset 0::

        $byts = $lib.axon.read($sha256, size=100)

    Read 50 bytes starting at offset 200::

        $byts = $lib.axon.read($sha256, offs=200, size=50)


**Args:**

- `sha256` (`str`): The SHA256 hash of the file to read.
- `offs` (`int`): The offset to start reading from.
- `size` (`int`): The number of bytes to read. Max is 1 MiB.


**Returns:**
The requested bytes from the file. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-axon-readlines"></a>

### $lib.axon.readlines(sha256, errors='ignore')

Yields lines of text from a plain-text file stored in the Axon.

Examples::

    // Get the lines for a given file.
    for $line in $lib.axon.readlines($sha256) {
        $dostuff($line)
    }


**Args:**

- `sha256` (`str`): The SHA256 hash of the file.
- `errors` (`str`): Specify how encoding errors should handled.


**Yields:**
A line of text from the file. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-axon-size"></a>

### $lib.axon.size(sha256)

Return the size of the bytes stored in the Axon for the given sha256.

Examples:
    Get the size for a file given a variable named ``$sha256``::

        $size = $lib.axon.size($sha256)


**Args:**

- `sha256` (`str`): The sha256 value to check.


**Returns:**
The size of the file or ``null`` if the file is not found. The return type may be one of the following: `int`, `null`.

<a id="stormlibs-lib-axon-unpack"></a>

### $lib.axon.unpack(sha256, fmt, offs=(0))

Unpack bytes from a file stored in the Axon into a struct using the specified format.

Examples:
    Unpack two 32-bit integers from the start of a file::

        $nums = $lib.axon.unpack($sha256, '<II')

    Unpack a 64-bit float starting at offset 100::

        $float = $lib.axon.unpack($sha256, '<d', offs=100)


**Args:**

- `sha256` (`str`): The SHA256 hash of the file to read.
- `fmt` (`str`): The struct format string.
- `offs` (`int`): The offset to start reading from.


**Returns:**
The unpacked values as a tuple. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-axon-upload"></a>

### $lib.axon.upload(genr)

Upload a stream of bytes to the Axon as a file.

Examples:
    Upload bytes from a generator::

        ($size, $sha256) = $lib.axon.upload($getBytesChunks())


**Args:**

- `genr` (`generator`): A generator which yields bytes.


**Returns:**
A tuple of the file size and sha256 value. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-axon-urlfile"></a>

### $lib.axon.urlfile(*args, **kwargs)

Retrieve the target URL using the wget() function and construct an inet:urlfile node from the response.

Notes:
    This accepts the same arguments as ``$lib.axon.wget()``.
    

**Args:**

- `*args` (`any`): Args from ``$lib.axon.wget()``.
- `**kwargs` (`any`): Args from ``$lib.axon.wget()``.


**Returns:**
The ``inet:urlfile`` node on success,  ``null`` on error. The return type may be one of the following: [`node`](stormtypes_prims.md#stormprims-node-f527), `null`.

<a id="stormlibs-lib-axon-wget"></a>

### $lib.axon.wget(url, headers=(null), params=(null), method='GET', json=(null), body=(null), ssl=(null), timeout=(null), proxy=(true))

A method to download an HTTP(S) resource into the Cortex's Axon.

Notes:
    The response body will be stored regardless of the status code. See the ``Axon.wget()`` API
    documentation to see the complete structure of the response dictionary.

Example:
    Get the Vertex Project website::

        $headers = ({})
        $headers."User-Agent" = Foo/Bar

        $resp = $lib.axon.wget("http://vertex.link", method=GET, headers=$headers)
        if $resp.ok { $lib.print(`Downloaded: {$resp.size} bytes`) }


**Args:**

- `url` (`str`): The URL to download
- `headers` (`dict`): An optional dictionary of HTTP headers to send.
- `params` (`dict`): An optional dictionary of URL parameters to add.
- `method` (`str`): The HTTP method to use.
- `json` (`dict`): A JSON object to send as the body.
- `body` (`bytes`): Bytes to send as the body.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.axon help for additional details.
- `timeout` (`int`): Timeout for the download operation.
- `proxy`: Configure proxy usage. See $lib.axon help for additional details. The input type may be one of the following: `boolean`, `str`.


**Returns:**
A status dictionary of metadata. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-axon-wput"></a>

### $lib.axon.wput(sha256, url, headers=(null), params=(null), method='PUT', ssl=(null), timeout=(null), proxy=(true))

A method to upload a blob from the axon to an HTTP(S) endpoint.


**Args:**

- `sha256` (`str`): The sha256 of the file blob to upload.
- `url` (`str`): The URL to upload the file to.
- `headers` (`dict`): An optional dictionary of HTTP headers to send.
- `params` (`dict`): An optional dictionary of URL parameters to add.
- `method` (`str`): The HTTP method to use.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.axon help for additional details.
- `timeout` (`int`): Timeout for the download operation.
- `proxy`: Configure proxy usage. See $lib.axon help for additional details. The input type may be one of the following: `boolean`, `str`.


**Returns:**
A status dictionary of metadata. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-base64"></a>

## $lib.base64

A Storm Library for encoding and decoding base64 data.


<a id="stormlibs-lib-base64-decode"></a>

### $lib.base64.decode(valu, urlsafe=(true))

Decode a base64 string into a bytes object.

**Args:**

- `valu` (`str`): The string to decode.
- `urlsafe` (`boolean`): Perform the decoding in a urlsafe manner if true.


**Returns:**
A bytes object for the decoded data. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-base64-encode"></a>

### $lib.base64.encode(valu, urlsafe=(true))

Encode a bytes object to a base64 encoded string.

**Args:**

- `valu` (`bytes`): The object to encode.
- `urlsafe` (`boolean`): Perform the encoding in a urlsafe manner if true.


**Returns:**
A base64 encoded string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-basex"></a>

## $lib.basex

A Storm library which implements helpers for encoding and decoding strings using an arbitrary charset.


<a id="stormlibs-lib-basex-decode"></a>

### $lib.basex.decode(text, charset)

Decode a baseX string into bytes.

**Args:**

- `text` (`str`): The hex string to be decoded into bytes.
- `charset` (`str`): The charset used to decode the string.


**Returns:**
The decoded bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-basex-encode"></a>

### $lib.basex.encode(byts, charset)

Encode bytes into a baseX string.

**Args:**

- `byts` (`bytes`): The bytes to be encoded into a string.
- `charset` (`str`): The charset used to encode the bytes.


**Returns:**
The encoded string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-bytes"></a>

## $lib.bytes

A Storm Library for interacting with bytes.


<a id="stormlibs-lib-bytes-fromints"></a>

### $lib.bytes.fromints(ints)

Convert an iterable source of integers into bytes.

Note:
    The integer values must be in the range 0 to 255. Values outside of this range will raise a
    BadArg.

Examples:
    Convert a list of integers into bytes::

        $ints = ([0x56, 0x49, 0x53, 0x49])
        $byts = $lib.bytes.fromints($ints)



**Args:**

- `ints` (`generator`): An iterable source of integers.


**Returns:**
The bytes from processing the integers. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-cache"></a>

## $lib.cache

A Storm Library for interacting with Cache Objects.


<a id="stormlibs-lib-cache-fixed"></a>

### $lib.cache.fixed(callback, size=(10000))

Get a new Fixed Cache object.

On a cache-miss when calling .get(), the callback Storm query is executed in a sub-runtime
in the current execution context. A special variable, $cache_key, will be set
to the key argument provided to .get().

The callback Storm query must contain a return statement, and if it does not return a value
when executed with the input, ``(null)`` will be set as the value.

The fixed cache uses FIFO to evict items once the maximum size is reached.

Examples::

    // Use a callback query with a function that modifies the outer runtime,
    // since it will run in the scope where it was defined.
    $test = foo

    function callback(key) {
        $test = $key // this will modify $test in the outer runtime
        return(`{$key}-val`)
    }

    $cache = $lib.cache.fixed(${ return($callback($cache_key)) })
    $value = $cache.get(bar)
    $lib.print($test) // this will equal "bar"

    // Use a callback query that will not modify the outer runtime,
    // except for variables accessible as references.
    $test = foo
    $tests = ([])

    $cache = $lib.cache.fixed(${
        $test = $cache_key        // this will *not* modify $test in the outer runtime
        $tests.append($cache_key) // this will modify $tests in the outer runtime
        return(`{$cache_key}-val`)
    })

    $value = $cache.get(bar)
    $lib.print($test)  // this will equal "foo"
    $lib.print($tests) // this will equal (foo,)


**Args:**

- `callback`: A Storm query that will return a value for $cache_key on a cache miss. The input type may be one of the following: `str`, `storm:query`.
- `size` (`int`): The maximum size of the cache.


**Returns:**
A new ``cache:fixed`` object. The return type is [`cache:fixed`](stormtypes_prims.md#stormprims-cache-fixed-f527).

<a id="stormlibs-lib-cell"></a>

## $lib.cell

A Storm Library for interacting with the Cortex.


<a id="stormlibs-lib-cell-getCellInfo"></a>

### $lib.cell.getCellInfo()

Return metadata specific for the Cortex.

**Returns:**
A dictionary containing metadata. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-cell-getHealthCheck"></a>

### $lib.cell.getHealthCheck()

Get healthcheck information about the Cortex.

**Returns:**
A dictionary containing healthcheck information. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-cell-getMirrorUrls"></a>

### $lib.cell.getMirrorUrls(name=(null))

Get mirror Telepath URLs for an AHA configured service.

**Args:**

- `name` (`str`): The name, or iden, of the service to get mirror URLs for (defaults to the Cortex if not provided).


**Returns:**
A list of Telepath URLs. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-cell-getSystemInfo"></a>

### $lib.cell.getSystemInfo()

Get info about the system in which the Cortex is running.

**Returns:**
A dictionary containing system information. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-cell-iden"></a>

### $lib.cell.iden

The Cortex service identifier.

**Returns:**
The Cortex service identifier. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-cell-trimNexsLog"></a>

### $lib.cell.trimNexsLog(consumers=(null), timeout=(30))

Rotate and cull the Nexus log (and any consumers) at the current offset.

If the consumers argument is provided they will first be checked
if online before rotating and raise otherwise.
After rotation, all consumers provided must catch-up to the offset to cull at
within the specified timeout before executing the cull, and will raise otherwise.


**Args:**

- `consumers` (`list`): List of Telepath URLs for consumers of the Nexus log.
- `timeout` (`int`): Time (in seconds) to wait for consumers to catch-up before culling.


**Returns:**
The offset that was culled (up to and including). The return type is `int`.

<a id="stormlibs-lib-cell-uptime"></a>

### $lib.cell.uptime(name=(null))

Get update data for the Cortex or a connected Service.

**Args:**

- `name` (`str`): The name, or iden, of the service to get uptime data for (defaults to the Cortex if not provided).


**Returns:**
A dictionary containing uptime data. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-compression-bzip2"></a>

## $lib.compression.bzip2

A Storm library which implements helpers for bzip2 compression.


<a id="stormlibs-lib-compression-bzip2-en"></a>

### $lib.compression.bzip2.en(valu)

Compress bytes using bzip2 and return them.

Example:
    Compress bytes with bzip2::

        $foo = $lib.compression.bzip2.en($mybytez)

**Args:**

- `valu` (`bytes`): The bytes to be compressed.


**Returns:**
The bzip2 compressed bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-compression-bzip2-un"></a>

### $lib.compression.bzip2.un(valu)

Decompress bytes using bzip2 and return them.

Example:
    Decompress bytes with bzip2::

    $foo = $lib.compression.bzip2.un($mybytez)

**Args:**

- `valu` (`bytes`): The bytes to be decompressed.


**Returns:**
Decompressed bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-compression-gzip"></a>

## $lib.compression.gzip

A Storm library which implements helpers for gzip compression.


<a id="stormlibs-lib-compression-gzip-en"></a>

### $lib.compression.gzip.en(valu)

Compress bytes using gzip and return them.

Example:
    Compress bytes with gzip::

        $foo = $lib.compression.gzip.en($mybytez)

**Args:**

- `valu` (`bytes`): The bytes to be compressed.


**Returns:**
The gzip compressed bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-compression-gzip-un"></a>

### $lib.compression.gzip.un(valu)

Decompress bytes using gzip and return them.

Example:
    Decompress bytes with gzip::

    $foo = $lib.compression.gzip.un($mybytez)

**Args:**

- `valu` (`bytes`): The bytes to be decompressed.


**Returns:**
Decompressed bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-compression-zlib"></a>

## $lib.compression.zlib

A Storm library which implements helpers for zlib compression.


<a id="stormlibs-lib-compression-zlib-en"></a>

### $lib.compression.zlib.en(valu)

Compress bytes using zlib and return them.

Example:
    Compress bytes with zlib::

        $foo = $lib.compression.zlib.en($mybytez)

**Args:**

- `valu` (`bytes`): The bytes to be compressed.


**Returns:**
The zlib compressed bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-compression-zlib-un"></a>

### $lib.compression.zlib.un(valu)

Decompress bytes using zlib and return them.

Example:
    Decompress bytes with zlib::

    $foo = $lib.compression.zlib.un($mybytez)

**Args:**

- `valu` (`bytes`): The bytes to be decompressed.


**Returns:**
Decompressed bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-cortex"></a>

## $lib.cortex

Library for interacting with the Cortex API.


<a id="stormlibs-lib-cortex-getNdefByNid"></a>

### $lib.cortex.getNdefByNid(nid)

Get the ndef tuple for a node by its node id in this Cortex.

**Args:**

- `nid` (`int`): The node id of the node.


**Returns:**
The ndef of the node or None if the node id is not found. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-cortex-getNidByNdef"></a>

### $lib.cortex.getNidByNdef(ndef)

Get the node id for an ndef in this Cortex.

**Args:**

- `ndef` (`list`): The ndef tuple (form, valu) of the node.


**Returns:**
The node id or None if the ndef is not found. The return type is `int`.

<a id="stormlibs-lib-cortex-getNodeByNid"></a>

### $lib.cortex.getNodeByNid(nid)

Get a node from the current View by its node id in this Cortex.

**Args:**

- `nid` (`int`): The node id of the node.


**Returns:**
The node in the current View if it exists. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-cortex-httpapi"></a>

## $lib.cortex.httpapi

Library for interacting with the Extended HTTP API.


<a id="stormlibs-lib-cortex-httpapi-add"></a>

### $lib.cortex.httpapi.add(path, name='', desc='', runas='owner', authenticated=(true), readonly=(false), iden=(null))

Add an Extended HTTP API endpoint to the Cortex.

This can be used to add an API endpoint which will be resolved under
the API path "/api/ext/". New API endpoint objects are appended to
a list of APIs to resolve in order.

Notes:
    The Cortex does not make any attempt to do any inspection of path values which may conflict between one
    another. This is because the paths for a given endpoint may be changed, they can contain regular
    expressions, and they may have their resolution order changed. Cortex administrators are responsible for
    configuring their Extended HTTP API endpoints with correct paths and order to meet their use cases.

Example:
    Add a simple API handler::

        // Create an endpoint for /api/ext/foo/bar
        $api = $lib.cortex.httpapi.add('foo/bar')

        // Define a GET response handler via storm that makes a simple reply.
        $api.methods.get = ${ $request.reply(200, body=({"some": "data}) }

    Add a wildcard handler::

        // Create a wildcard endpoint for /api/ext/some/thing([a-zA-Z0-9]*)/([a-zA-Z0-9]*)
        $api = $lib.cortex.httpapi.add('some/thing([a-zA-Z0-9]*)/([a-zA-Z0-9]*)')

        // The capture groups are exposed as request arguments.
        // Echo them back to the caller.
        $api.methods.get = ${
            $request.reply(200, body=({"args": $request.args})
        }


**Args:**

- `path` (`str`): The extended HTTP API path.
- `name` (`str`): Friendly name for the Extended HTTP API.
- `desc` (`str`): Description for the Extended HTTP API.
- `runas` (`str`): Run the storm query as the API "owner" or as the authenticated "user".
- `authenticated` (`boolean`): Require the API endpoint to be authenticated.
- `readonly` (`boolean`): Run the Extended HTTP Storm methods in readonly mode.
- `iden` (`str`): An iden for the new Extended HTTP API.


**Returns:**
A new ``http:api`` object. The return type is [`http:api`](stormtypes_prims.md#stormprims-http-api-f527).

<a id="stormlibs-lib-cortex-httpapi-del"></a>

### $lib.cortex.httpapi.del(iden)

Delete an Extended HTTP API endpoint.

**Args:**

- `iden` (`str`): The iden of the API to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-cortex-httpapi-get"></a>

### $lib.cortex.httpapi.get(iden)

Get an Extended ``http:api`` object.

**Args:**

- `iden` (`str`): The iden of the API to retrieve.


**Returns:**
The ``http:api`` object. The return type is [`http:api`](stormtypes_prims.md#stormprims-http-api-f527).

<a id="stormlibs-lib-cortex-httpapi-getByPath"></a>

### $lib.cortex.httpapi.getByPath(path)

Get an Extended ``http:api`` object by path.

Notes:
    The path argument is evaluated as a regular expression input, and will be
    used to get the first HTTP API handler whose path value has a match.


**Args:**

- `path` (`str`): Path to use to retrieve an object.


**Returns:**
The ``http:api`` object or ``(null)`` if there is no match. The return type may be one of the following: [`http:api`](stormtypes_prims.md#stormprims-http-api-f527), `null`.

<a id="stormlibs-lib-cortex-httpapi-index"></a>

### $lib.cortex.httpapi.index(iden, index=(0))

Set the index for a given Extended HTTP API.

**Args:**

- `iden` (`str`): The iden of the API to modify.
- `index` (`int`): The new index of the API. Uses zero based indexing.


**Returns:**
The new index location of the API. The return type is `int`.

<a id="stormlibs-lib-cortex-httpapi-list"></a>

### $lib.cortex.httpapi.list()

Get all the Extended HTTP APIs on the Cortex

**Returns:**
A list of ``http:api`` objects The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-cortex-httpapi-response"></a>

### $lib.cortex.httpapi.response(requestinfo)

Make a response object. Used by API handlers automatically.

**Args:**

- `requestinfo` (`dict`): Request info dictionary. This is an opaque data structure which may change.


**Returns:**
The return type is [`http:api:request`](stormtypes_prims.md#stormprims-http-api-request-f527).

<a id="stormlibs-lib-cron"></a>

## $lib.cron

A Storm Library for interacting with Cron Jobs in the Cortex.


<a id="stormlibs-lib-cron-add"></a>

### $lib.cron.add(period, query, **kwargs)

Add a recurring Cron Job to the Cortex.

**Args:**

- `period` (`str`): The recurrence period for the Cron Job
- `query` (`str`): Query for the Cron Job to execute.
- `**kwargs` (`any`): Key-value parameters used to add the cron job.


**Returns:**
The new Cron Job. The return type is [`cronjob`](stormtypes_prims.md#stormprims-cronjob-f527).

<a id="stormlibs-lib-cron-at"></a>

### $lib.cron.at(query, **kwargs)

Add a non-recurring Cron Job to the Cortex.

**Args:**

- `query` (`str`): Query for the Cron Job to execute.
- `**kwargs` (`any`): Key-value parameters used to add the cron job.


**Returns:**
The new Cron Job. The return type is [`cronjob`](stormtypes_prims.md#stormprims-cronjob-f527).

<a id="stormlibs-lib-cron-del"></a>

### $lib.cron.del(prefix)

Delete a CronJob from the Cortex.

**Args:**

- `prefix` (`str`): A prefix to match in order to identify a cron job to delete. Only a single matching prefix will be deleted.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-cron-get"></a>

### $lib.cron.get(prefix)

Get a CronJob in the Cortex.

**Args:**

- `prefix` (`str`): A prefix to match in order to identify a cron job to get. Only a single matching prefix will be retrieved.


**Returns:**
The requested cron job. The return type is [`cronjob`](stormtypes_prims.md#stormprims-cronjob-f527).

<a id="stormlibs-lib-cron-list"></a>

### $lib.cron.list()

List CronJobs in the Cortex.

**Returns:**
A list of ``cronjob`` objects. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-cron-mod"></a>

### $lib.cron.mod(prefix, edits)

Modify a CronJob in the Cortex.

**Args:**

- `prefix` (`str`): A prefix to match in order to identify a cron job to modify. Only a single matching prefix will be modified.
- `edits` (`dict`): A dictionary of properties and their values to update on the Cron Job.


**Returns:**
The iden of the CronJob which was modified. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-crypto-coin-ethereum"></a>

## $lib.crypto.coin.ethereum

A Storm library which implements helpers for Ethereum.


<a id="stormlibs-lib-crypto-coin-ethereum-eip55"></a>

### $lib.crypto.coin.ethereum.eip55(addr)

Convert an Ethereum address to a checksummed address.

**Args:**

- `addr` (`str`): The Ethereum address to be converted.


**Returns:**
A list of (<boolean>, <addr>) for status and checksummed address. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-crypto-ecc"></a>

## $lib.crypto.ecc

A Storm library for generating and loading ECC keys.


<a id="stormlibs-lib-crypto-ecc-generate"></a>

### $lib.crypto.ecc.generate(curve='P-256')

Generate a new ECC private key.

Examples:
    Generate a key and sign a message::

        $key = $lib.crypto.ecc.generate()
        $sig = $key.sign($mesg.encode())


**Args:**

- `curve` (`str`): The named curve to use (P-256, P-384, or P-521).


**Returns:**
A new ``crypto:ecc:key`` containing the generated private key. The return type is [`crypto:ecc:key`](stormtypes_prims.md#stormprims-crypto-ecc-key-f527).

<a id="stormlibs-lib-crypto-ecc-load"></a>

### $lib.crypto.ecc.load(key)

Load an ECC public or private key.

The encoding (DER or PEM) and whether the key is a public or private key are
detected automatically. The key must contain a single key.

Examples:
    Load a PEM encoded private key::

        $key = $lib.crypto.ecc.load($pem)


**Args:**

- `key`: A DER or PEM encoded ECC public or private key. May be a str (PEM) or bytes. The input type may be one of the following: `str`, `bytes`.


**Returns:**
A new ``crypto:ecc:key`` containing the loaded key. The return type is [`crypto:ecc:key`](stormtypes_prims.md#stormprims-crypto-ecc-key-f527).

<a id="stormlibs-lib-crypto-hashes"></a>

## $lib.crypto.hashes

A Storm Library for hashing bytes


<a id="stormlibs-lib-crypto-hashes-md5"></a>

### $lib.crypto.hashes.md5(byts)

Retrieve an MD5 hash of a byte string.

**Args:**

- `byts` (`bytes`): The bytes to hash.


**Returns:**
The hex digest of the MD5 hash of the input bytes. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-crypto-hashes-sha1"></a>

### $lib.crypto.hashes.sha1(byts)

Retrieve a SHA1 hash of a byte string.

**Args:**

- `byts` (`bytes`): The bytes to hash.


**Returns:**
The hex digest of the SHA1 hash of the input bytes. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-crypto-hashes-sha256"></a>

### $lib.crypto.hashes.sha256(byts)

Retrieve a SHA256 hash of a byte string.

**Args:**

- `byts` (`bytes`): The bytes to hash.


**Returns:**
The hex digest of the SHA256 hash of the input bytes. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-crypto-hashes-sha512"></a>

### $lib.crypto.hashes.sha512(byts)

Retrieve a SHA512 hash of a byte string.

**Args:**

- `byts` (`bytes`): The bytes to hash.


**Returns:**
The hex digest of the SHA512 hash of the input bytes. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-crypto-hmac"></a>

## $lib.crypto.hmac

A Storm library for computing RFC2104 HMAC values.


<a id="stormlibs-lib-crypto-hmac-digest"></a>

### $lib.crypto.hmac.digest(key, mesg, alg='sha256')

Compute the digest value of a message using RFC2104 HMAC.

Examples:
    Compute the HMAC-SHA256 digest for a message with a secret key::

        $digest = $lib.crypto.hmac.digest(key=$secretKey.encode(), mesg=$mesg.encode())


**Args:**

- `key` (`bytes`): The key to use for the HMAC calculation.
- `mesg` (`bytes`): The message to use for the HMAC calculation.
- `alg` (`str`): The digest algorithm to use.


**Returns:**
The binary digest of the HMAC value. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-crypto-jwt"></a>

## $lib.crypto.jwt

A Storm library for constructing, signing, and verifying JSON Web Tokens (JWTs).


<a id="stormlibs-lib-crypto-jwt-algorithms"></a>

### $lib.crypto.jwt.algorithms

The list of JWS algorithms supported by the JWT functionality.

**Returns:**
A list of the supported JWS algorithm names. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-crypto-jwt-generate"></a>

### $lib.crypto.jwt.generate(payload=(null))

Construct a new unsigned ``crypto:jwt`` object.

Examples:
    Construct a token, set a claim, and sign it::

        $key = $lib.crypto.rsa.generate()
        $token = $lib.crypto.jwt.generate()
        $token.payload.sub = "1234567890"
        $jwtstr = $token.sign($key, "RS256")


**Args:**

- `payload` (`dict`): An optional dictionary to use as the initial claims payload.


**Returns:**
The newly constructed crypto:jwt object. The return type is [`crypto:jwt`](stormtypes_prims.md#stormprims-crypto-jwt-f527).

<a id="stormlibs-lib-crypto-jwt-parse"></a>

### $lib.crypto.jwt.parse(token)

Structurally parse a token without a key, reporting whether it is a JWS or a JWE and decoding only
its protected header. This performs no signature verification and no decryption.


**Args:**

- `token` (`str`): The compact or JSON serialized token.


**Returns:**
A dictionary with ``typ`` ("JWS" or "JWE") and the decoded ``header``. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-crypto-jwt-verify"></a>

### $lib.crypto.jwt.verify(token, key, algorithms, audience=(null), issuer=(null), subject=(null), leeway=(0), typ=(null), requiredclaims=(null), options=(null), jwks_uri=(null), ssl_opts=(null), proxy=(true), allowinternal=(false))

Verify a JWT and return a ``crypto:jwt`` object.

The ``algorithms`` list is a required allowlist. The algorithm named in the token header must be
present in the allowlist or verification fails. This is the primary mitigation against JWT algorithm
confusion attacks. The ``none`` algorithm is never supported. Both the compact and the flattened
JWS JSON serializations are accepted.

The ``exp``, ``nbf``, and ``iat`` claims are validated automatically whenever they are present. The
``audience``, ``issuer``, and ``subject`` claims are validated when a corresponding expected value
is provided. Each of these checks may be disabled via the ``options`` dictionary.

The ``key`` may be a PEM key, an HMAC secret, a crypto:rsa:key / crypto:ecc:key object, or a JWK /
JWKS dictionary (a JWKS is selected by the token ``kid``). If ``key`` is null and a ``jwks_uri`` is
provided, the key set is fetched over HTTPS (respecting ``ssl_opts`` and ``proxy``) and cached. The
token header ``jku`` / ``x5u`` / ``jwk`` are never followed.

Examples:
    Verify a token and use the returned object::

        ($ok, $valu) = $lib.crypto.jwt.verify($jwtstr, $key.pubkey(), ("RS256",), audience="myapp")
        if $ok { $lib.print($valu.payload.sub) }


**Args:**

- `token` (`str`): The JWT string to verify.
- `key`: The verification key: a PEM public key (or crypto:rsa:key / crypto:ecc:key) for RS* / PS* / ES*, an HMAC secret for HS*, a JWK / JWKS dictionary, or null to resolve the key via jwks_uri. The input type may be one of the following: `str`, `bytes`, `dict`, `crypto:rsa:key`, `crypto:ecc:key`.
- `algorithms` (`list`): The required allowlist of acceptable JWS algorithms.
- `audience`: The expected audience. The token aud claim must contain at least one match. The input type may be one of the following: `str`, `list`.
- `issuer`: The expected issuer. A str is an exact match; a list is a membership test. The input type may be one of the following: `str`, `list`.
- `subject` (`str`): The expected subject, compared for exact equality with the sub claim.
- `leeway` (`int`): Seconds of clock-skew leeway applied to the exp and nbf checks.
- `typ` (`str`): An expected header typ value to require (e.g. "JWT" or "at+jwt").
- `requiredclaims` (`list`): Claim names that must be present in the payload (presence only, not value).
- `options` (`dict`): Toggles for verify_exp, verify_nbf, verify_iat, verify_aud, verify_iss, and verify_sub. Each defaults to true.
- `jwks_uri` (`str`): An https URL to fetch the JWKS from when key is null. The result is cached.
- `ssl_opts` (`dict`): SSL options for the jwks_uri fetch (same shape as $lib.inet.http).
- `proxy`: Proxy configuration for the jwks_uri fetch (same as $lib.inet.http). The input type may be one of the following: `boolean`, `str`.
- `allowinternal` (`boolean`): Allow a jwks_uri that resolves to a loopback / private / link-local address.


**Returns:**
An ($ok, $valu) tuple. On success $valu is a verified crypto:jwt object; on failure $valu is a dictionary of error information. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-crypto-rsa"></a>

## $lib.crypto.rsa

A Storm library for generating and loading RSA keys.


<a id="stormlibs-lib-crypto-rsa-generate"></a>

### $lib.crypto.rsa.generate(bits=(2048))

Generate a new RSA private key.

Examples:
    Generate a key and sign a message::

        $key = $lib.crypto.rsa.generate()
        $sig = $key.sign($mesg.encode())


**Args:**

- `bits` (`int`): The size of the RSA key to generate in bits (1024 to 8192).


**Returns:**
A new ``crypto:rsa:key`` containing the generated private key. The return type is [`crypto:rsa:key`](stormtypes_prims.md#stormprims-crypto-rsa-key-f527).

<a id="stormlibs-lib-crypto-rsa-load"></a>

### $lib.crypto.rsa.load(key)

Load an RSA public or private key.

The encoding (DER or PEM) and whether the key is a public or private key are
detected automatically. The key must contain a single key.

Examples:
    Load a PEM encoded private key::

        $key = $lib.crypto.rsa.load($pem)


**Args:**

- `key`: A DER or PEM encoded RSA public or private key. May be a str (PEM) or bytes. The input type may be one of the following: `str`, `bytes`.


**Returns:**
A new ``crypto:rsa:key`` containing the loaded key. The return type is [`crypto:rsa:key`](stormtypes_prims.md#stormprims-crypto-rsa-key-f527).

<a id="stormlibs-lib-csv"></a>

## $lib.csv

A Storm Library for interacting with csvtool.


<a id="stormlibs-lib-csv-emit"></a>

### $lib.csv.emit(*args, table=(null))

Emit a ``csv:row`` event to the Storm runtime for the given args.

**Args:**

- `*args` (`any`): Items which are emitted as a ``csv:row`` event.
- `table` (`str`): The name of the table to emit data too. Optional.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-dict"></a>

## $lib.dict

A Storm Library for interacting with dictionaries.


<a id="stormlibs-lib-dict-fromlist"></a>

### $lib.dict.fromlist(valu)

Construct a dictionary from a list of key/value tuples.

**Args:**

- `valu` (`list`): The list of key/value tuples.


**Returns:**
The new dictionary. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-dict-has"></a>

### $lib.dict.has(valu, key)

Check a dictionary has a specific key.

**Args:**

- `valu` (`dict`): The dictionary being checked.
- `key` (`any`): The key to check.


**Returns:**
True if the key is present, false if the key is not present. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-dict-keys"></a>

### $lib.dict.keys(valu)

Retrieve a list of keys in the specified dictionary.

**Args:**

- `valu` (`dict`): The dictionary to operate on.


**Returns:**
List of keys in the specified dictionary. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-dict-pop"></a>

### $lib.dict.pop(valu, key, default=$lib.undef)

Remove specified key and return the corresponding value.

**Args:**

- `valu` (`dict`): The dictionary to operate on.
- `key` (`any`): The key to pop.
- `default` (`any`): Optional default value to return if the key does not exist in the dictionary.


**Returns:**
The popped value. The return type is `any`.

<a id="stormlibs-lib-dict-update"></a>

### $lib.dict.update(valu, other)

Update the specified dictionary with keys/values from another dictionary.

**Args:**

- `valu` (`dict`): The target dictionary (update to).
- `other` (`dict`): The source dictionary (update from).


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-dict-values"></a>

### $lib.dict.values(valu)

Retrieve a list of values in the specified dictionary.

**Args:**

- `valu` (`dict`): The dictionary to operate on.


**Returns:**
List of values in the specified dictionary. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-dmon"></a>

## $lib.dmon

A Storm Library for interacting with StormDmons.


<a id="stormlibs-lib-dmon-add"></a>

### $lib.dmon.add(text, name='noname', ddef=(null))

Add a Storm Dmon to the Cortex.

Examples:
    Add a dmon that executes a query::

        $lib.dmon.add(${ myquery }, name='example dmon')
        

**Args:**

- `text`: The Storm query to execute in the Dmon loop. The input type may be one of the following: `str`, `storm:query`.
- `name` (`str`): The name of the Dmon.
- `ddef` (`dict`): Additional daemon definition fields. 


**Returns:**
A Storm Dmon definition dict. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-dmon-bump"></a>

### $lib.dmon.bump(iden)

Restart the Dmon.

**Args:**

- `iden` (`str`): The GUID of the dmon to restart.


**Returns:**
True if the Dmon is restarted; False if the iden does not exist. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-dmon-del"></a>

### $lib.dmon.del(iden)

Delete a Storm Dmon by iden.

**Args:**

- `iden` (`str`): The iden of the Storm Dmon to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-dmon-get"></a>

### $lib.dmon.get(iden)

Get a Storm Dmon definition by iden.

**Args:**

- `iden` (`str`): The iden of the Storm Dmon to get.


**Returns:**
A Storm Dmon definition dict. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-dmon-list"></a>

### $lib.dmon.list()

Get a list of Storm Dmons.

**Returns:**
A list of Storm Dmon definitions. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-dmon-log"></a>

### $lib.dmon.log(iden)

Get the messages from a Storm Dmon.

**Args:**

- `iden` (`str`): The iden of the Storm Dmon to get logs for.


**Returns:**
A list of messages from the StormDmon. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-dmon-start"></a>

### $lib.dmon.start(iden)

Start a storm dmon.

**Args:**

- `iden` (`str`): The GUID of the dmon to start.


**Returns:**
``(true)`` unless the dmon does not exist or was already started. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-dmon-stop"></a>

### $lib.dmon.stop(iden)

Stop a Storm Dmon.

**Args:**

- `iden` (`str`): The GUID of the Dmon to stop.


**Returns:**
``(true)`` unless the dmon does not exist or was already stopped. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-export"></a>

## $lib.export

A Storm Library for exporting data.


<a id="stormlibs-lib-export-toaxon"></a>

### $lib.export.toaxon(query, opts=(null))

Run a query as an export (fully resolving relationships between nodes in the output set)
and save the resulting stream of packed nodes to the axon.


**Args:**

- `query` (`str`): A query to run as an export.
- `opts` (`dict`): Storm runtime query option params.


**Returns:**
Returns a tuple of (size, sha256). The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-feed"></a>

## $lib.feed

A Storm Library for feeding bulk nodes into a Cortex.


<a id="stormlibs-lib-feed-fromAxon"></a>

### $lib.feed.fromAxon(sha256)

Load a syn.nodes formatted export from axon.

**Args:**

- `sha256` (`str`): The sha256 of the file stored in the axon.


**Returns:**
The number of nodes loaded. The return type is `int`.

<a id="stormlibs-lib-feed-genr"></a>

### $lib.feed.genr(data, reqmeta=(false))

Yield nodes being added to the graph by adding data in nodes format.

Notes:
    This is using the Runtimes's View to call addNodes().
    If the generator is not entirely consumed there is no guarantee
    that all of the nodes which should be made by the feed function
    will be made.


**Args:**

- `data` (`prim`): Nodes data to ingest
- `reqmeta` (`boolean`): Require a meta record.


**Yields:**
Yields Nodes as they are created. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-feed-ingest"></a>

### $lib.feed.ingest(data, reqmeta=(false))

Add nodes to the graph.

Notes:
    This API will cause errors during node creation and property setting
    to produce warning messages, instead of causing the Storm Runtime
    to be torn down.

**Args:**

- `data` (`prim`): Data to send to the ingest function.
- `reqmeta` (`boolean`): Require a meta record.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-file"></a>

## $lib.file

A Storm Library with various file functions.


<a id="stormlibs-lib-file-frombytes"></a>

### $lib.file.frombytes(valu)

Upload supplied data to the configured Axon and create a corresponding file:bytes node.


**Args:**

- `valu` (`bytes`): The file data.


**Returns:**
The file:bytes node representing the supplied data. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-file-fromhex"></a>

### $lib.file.fromhex(valu)

Decode a hex string and upload resulting bytes to the configured Axon and create a corresponding file:bytes node.


**Args:**

- `valu` (`str`): The file data.


**Returns:**
The file:bytes node representing the supplied data. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-gen"></a>

## $lib.gen

A Storm Library for secondary property based deconfliction.


<a id="stormlibs-lib-gis"></a>

## $lib.gis

A Storm library which implements helpers for earth based geospatial calculations.


<a id="stormlibs-lib-gis-bbox"></a>

### $lib.gis.bbox(lon, lat, dist)

Calculate a min/max bounding box for the specified circle.

**Args:**

- `lon` (`float`): The longitude in degrees.
- `lat` (`float`): The latitude in degrees.
- `dist` (`int`): A distance in phys:distance base units (mm).


**Returns:**
A tuple of (lonmin, lonmax, latmin, latmax). The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-graph"></a>

## $lib.graph

A Storm Library for interacting with graph projections in the Cortex.


<a id="stormlibs-lib-graph-activate"></a>

### $lib.graph.activate(iden)

Set the graph projection to use for the top level Storm Runtime.

**Args:**

- `iden` (`str`): The iden of the graph projection to use.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-graph-add"></a>

### $lib.graph.add(gdef)

Add a graph projection to the Cortex.

Example:
    Add a graph projection named "Test Projection"::

        $rules = ({
            "name": "Test Projection",
            "desc": "My test projection",
            "degrees": 2,
            "pivots": [" <(seen)- meta:source "],
            "filters": ["-#nope"],
            "forms": {
                "inet:fqdn": {
                    "pivots": ["<- *", "-> *"],
                    "filters": ["-inet:fqdn:issuffix=1"]
                },
                "*": {
                    "pivots": ["-> #"],
                }
            }
        })
        $lib.graph.add($rules)


**Args:**

- `gdef` (`dict`): A graph projection definition.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-graph-del"></a>

### $lib.graph.del(iden)

Delete a graph projection from the Cortex.

**Args:**

- `iden` (`str`): The iden of the graph projection to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-graph-get"></a>

### $lib.graph.get(iden=(null))

Get a graph projection definition from the Cortex.

**Args:**

- `iden` (`str`): The iden of the graph projection to get. If not specified, returns the current graph projection.


**Returns:**
A graph projection definition, or None if no iden was specified and there is currently no graph projection set. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-graph-grant"></a>

### $lib.graph.grant(gden, scope, iden, level)

Modify permissions granted to users/roles on a graph projection.

**Args:**

- `gden` (`str`): Iden of the graph projection to modify.
- `scope` (`str`): The scope, either "users" or "roles".
- `iden` (`str`): The user/role iden depending on scope.
- `level` (`int`): The permission level number.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-graph-list"></a>

### $lib.graph.list()

List the graph projections available in the Cortex.

**Returns:**
A list of graph projection definitions. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-graph-mod"></a>

### $lib.graph.mod(iden, info)

Modify user editable properties of a graph projection.

**Args:**

- `iden` (`str`): The iden of the graph projection to modify.
- `info` (`dict`): A dictionary of the properties to edit.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-graph-revoke"></a>

### $lib.graph.revoke(gden, scope, iden)

Revoke permissions granted to users/roles on a graph projection.

**Args:**

- `gden` (`str`): Iden of the graph projection to modify.
- `scope` (`str`): The scope, either "users" or "roles".
- `iden` (`str`): The user/role iden depending on scope.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-hex"></a>

## $lib.hex

A Storm library which implements helpers for hexadecimal encoded strings.


<a id="stormlibs-lib-hex-decode"></a>

### $lib.hex.decode(valu)

Decode a hexadecimal string into bytes.

**Args:**

- `valu` (`str`): The hex string to be decoded into bytes.


**Returns:**
The decoded bytes. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-hex-encode"></a>

### $lib.hex.encode(valu)

Encode bytes into a hexadecimal string.

**Args:**

- `valu` (`bytes`): The bytes to be encoded into a hex string.


**Returns:**
The hex encoded string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-hex-fromint"></a>

### $lib.hex.fromint(valu, length, signed=(false))

Convert an integer to a big endian hexadecimal string.

**Args:**

- `valu` (`int`): The integer to be converted.
- `length` (`int`): The number of bytes to use to represent the integer.
- `signed` (`boolean`): If true, convert as a signed value.


**Returns:**
The resulting hex string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-hex-signext"></a>

### $lib.hex.signext(valu, length)

Sign extension pad a hexadecimal encoded signed integer.

**Args:**

- `valu` (`str`): The hex string to pad.
- `length` (`int`): The number of characters to pad the string to.


**Returns:**
The sign extended hex string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-hex-toint"></a>

### $lib.hex.toint(valu, signed=(false))

Convert a big endian hexadecimal string to an integer.

**Args:**

- `valu` (`str`): The hex string to be converted.
- `signed` (`boolean`): If true, convert to a signed integer.


**Returns:**
The resulting integer. The return type is `int`.

<a id="stormlibs-lib-hex-trimext"></a>

### $lib.hex.trimext(valu)

Trim sign extension bytes from a hexadecimal encoded signed integer.

**Args:**

- `valu` (`str`): The hex string to trim.


**Returns:**
The trimmed hex string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-inet-http"></a>

## $lib.inet.http

A Storm Library exposing an HTTP client API.

For APIs that accept an ssl argument, the dictionary may contain the following values::

    ({
        'verify': <bool> - Perform SSL/TLS verification. Default is True.
        'client_cert': <str> - PEM encoded full chain certificate for use in mTLS.
        'client_key': <str> - PEM encoded key for use in mTLS. Alternatively, can be included in client_cert.
        'ca_cert': <str> - A PEM encoded full chain CA certificate for use when verifying the request.
    })

For APIs that accept a proxy argument, the following values are supported::

    (true): Use the proxy defined by the http:proxy configuration option if set.
    (false): Do not use the proxy defined by the http:proxy configuration option if set.
    <str>: A proxy URL string.


<a id="stormlibs-lib-inet-http-codereason"></a>

### $lib.inet.http.codereason(code)

Get the reason phrase for an HTTP status code.

Examples:
    Get the reason for a 404 status code::

        $str=$lib.inet.http.codereason(404)


**Args:**

- `code` (`int`): The HTTP status code.


**Returns:**
The reason phrase for the status code. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-inet-http-connect"></a>

### $lib.inet.http.connect(url, headers=(null), timeout=(300), params=(null), proxy=(true), ssl=(null))

Connect a web socket to tx/rx JSON messages.

**Args:**

- `url` (`str`): The URL to retrieve.
- `headers` (`dict`): HTTP headers to send with the request.
- `timeout` (`int`): Total timeout for the request in seconds.
- `params` (`dict`): Optional parameters which may be passed to the connection request.
- `proxy`: Configure proxy usage. See $lib.inet.http help for additional details. The input type may be one of the following: `boolean`, `str`.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.inet.http help for additional details.


**Returns:**
A websocket object. The return type is [`inet:http:socket`](stormtypes_prims.md#stormprims-inet-http-socket-f527).

<a id="stormlibs-lib-inet-http-get"></a>

### $lib.inet.http.get(url, headers=(null), params=(null), timeout=(300), allow_redirects=(true), proxy=(true), ssl=(null))

Get the contents of a given URL.

**Args:**

- `url` (`str`): The URL to retrieve.
- `headers` (`dict`): HTTP headers to send with the request.
- `params` (`dict`): Optional parameters which may be passed to the request.
- `timeout` (`int`): Total timeout for the request in seconds.
- `allow_redirects` (`boolean`): If set to false, do not follow redirects.
- `proxy`: Configure proxy usage. See $lib.inet.http help for additional details. The input type may be one of the following: `boolean`, `str`.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.inet.http help for additional details.


**Returns:**
The response object. The return type is [`inet:http:resp`](stormtypes_prims.md#stormprims-inet-http-resp-f527).

<a id="stormlibs-lib-inet-http-head"></a>

### $lib.inet.http.head(url, headers=(null), params=(null), timeout=(300), allow_redirects=(false), proxy=(true), ssl=(null))

Get the HEAD response for a URL.

**Args:**

- `url` (`str`): The URL to retrieve.
- `headers` (`dict`): HTTP headers to send with the request.
- `params` (`dict`): Optional parameters which may be passed to the request.
- `timeout` (`int`): Total timeout for the request in seconds.
- `allow_redirects` (`boolean`): If set to true, follow redirects.
- `proxy`: Configure proxy usage. See $lib.inet.http help for additional details. The input type may be one of the following: `boolean`, `str`.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.inet.http help for additional details.


**Returns:**
The response object. The return type is [`inet:http:resp`](stormtypes_prims.md#stormprims-inet-http-resp-f527).

<a id="stormlibs-lib-inet-http-post"></a>

### $lib.inet.http.post(url, headers=(null), json=(null), body=(null), params=(null), timeout=(300), allow_redirects=(true), fields=(null), proxy=(true), ssl=(null))

Post data to a given URL.

**Args:**

- `url` (`str`): The URL to post to.
- `headers` (`dict`): HTTP headers to send with the request.
- `json` (`prim`): The data to post, as JSON object.
- `body` (`bytes`): The data to post, as binary object.
- `params` (`dict`): Optional parameters which may be passed to the request.
- `timeout` (`int`): Total timeout for the request in seconds.
- `allow_redirects` (`boolean`): If set to false, do not follow redirects.
- `fields` (`list`): A list of info dictionaries containing the name, value or sha256, and additional parameters for fields to post, as multipart/form-data. If a sha256 is specified, the request will be sent from the axon and the corresponding file will be uploaded as the value for the field.
- `proxy`: Configure proxy usage. See $lib.inet.http help for additional details. The input type may be one of the following: `boolean`, `str`.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.inet.http help for additional details.


**Returns:**
The response object. The return type is [`inet:http:resp`](stormtypes_prims.md#stormprims-inet-http-resp-f527).

<a id="stormlibs-lib-inet-http-request"></a>

### $lib.inet.http.request(meth, url, headers=(null), json=(null), body=(null), params=(null), timeout=(300), allow_redirects=(true), fields=(null), proxy=(true), ssl=(null))

Make an HTTP request using the given HTTP method to the url.

**Args:**

- `meth` (`str`): The HTTP method. (ex. PUT)
- `url` (`str`): The URL to send the request to.
- `headers` (`dict`): HTTP headers to send with the request.
- `json` (`prim`): The data to include in the body, as JSON object.
- `body` (`bytes`): The data to include in the body, as binary object.
- `params` (`dict`): Optional parameters which may be passed to the request.
- `timeout` (`int`): Total timeout for the request in seconds.
- `allow_redirects` (`boolean`): If set to false, do not follow redirects.
- `fields` (`list`): A list of info dictionaries containing the name, value or sha256, and additional parameters for fields to post, as multipart/form-data. If a sha256 is specified, the request will be sent from the axon and the corresponding file will be uploaded as the value for the field.
- `proxy`: Configure proxy usage. See $lib.inet.http help for additional details. The input type may be one of the following: `boolean`, `str`.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.inet.http help for additional details.


**Returns:**
The response object. The return type is [`inet:http:resp`](stormtypes_prims.md#stormprims-inet-http-resp-f527).

<a id="stormlibs-lib-inet-http-urldecode"></a>

### $lib.inet.http.urldecode(text)

Urldecode a text string.

This will replace %xx escape characters with the special characters they represent
and replace plus signs with spaces.

Examples:
    Urlencode a string::

        $str=$lib.inet.http.urldecode("http%3A%2F%2Fgo+ogle.com")


**Args:**

- `text` (`str`): The text string.


**Returns:**
The urldecoded string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-inet-http-urlencode"></a>

### $lib.inet.http.urlencode(text)

Urlencode a text string.

This will replace special characters in a string using the %xx escape and
replace spaces with plus signs.

Examples:
    Urlencode a string::

        $str=$lib.inet.http.urlencode("http://google.com")


**Args:**

- `text` (`str`): The text string.


**Returns:**
The urlencoded string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-inet-http-oauth-v1"></a>

## $lib.inet.http.oauth.v1

A Storm library to handle OAuth v1 authentication.


<a id="stormlibs-lib-inet-http-oauth-v1-client"></a>

### $lib.inet.http.oauth.v1.client(ckey, csecret, atoken, asecret, sigtype='QUERY')

Initialize an OAuthV1 Client to use for signing/authentication.


**Args:**

- `ckey` (`str`): The OAuthV1 Consumer Key to store and use for signing requests.
- `csecret` (`str`): The OAuthV1 Consumer Secret used to sign requests.
- `atoken` (`str`): The OAuthV1 Access Token (or resource owner key) to use to sign requests.)
- `asecret` (`str`): The OAuthV1 Access Token Secret (or resource owner secret) to use to sign requests.
- `sigtype` (`str`): Where to populate the signature (in the HTTP body, in the query parameters, or in the header)


**Returns:**
An OAuthV1 client to be used to sign requests. The return type is [`inet:http:oauth:v1:client`](stormtypes_prims.md#stormprims-inet-http-oauth-v1-client-f527).

<a id="stormlibs-lib-inet-http-oauth-v2"></a>

## $lib.inet.http.oauth.v2

A Storm library for managing OAuth V2 clients.


<a id="stormlibs-lib-inet-http-oauth-v2-addProvider"></a>

### $lib.inet.http.oauth.v2.addProvider(conf)

Add a new provider configuration.

Example:
    Add a new provider which uses the authorization code flow::

        $iden = $lib.guid(example, provider, oauth)
        $conf = ({
            "iden": $iden,
            "name": "example_provider",
            "client_id": "yourclientid",
            "client_secret": "yourclientsecret",
            "scope": "first_scope second_scope",
            "auth_uri": "https://provider.com/auth",
            "token_uri": "https://provider.com/token",
            "redirect_uri": "https://local.redirect.com/oauth",
        })

        // Optionally enable PKCE
        $conf.extensions = ({"pkce": true})

        // Optionally disable SSL verification
        $conf.ssl = ({"verify": false})

        // Optionally provide additional key-val parameters
        // to include when calling the auth URI
        $conf.extra_auth_params = ({"customparam": "foo"})

        $lib.inet.http.oauth.v2.addProvider($conf)

    Add a new provider which uses the Microsoft Azure Federated Workflow Identify token credentials.
    This resolves the client_assertion from the AZURE_FEDERATED_TOKEN_FILE environment variable::

        $iden = $lib.guid(azureexample, provider, oauth)
        $authority_id = '4b70ee6f-d47b-3262-baa1-41cd7faed71b'
        $conf = ({
            "iden": $iden,
            "name": "example_provider",
            "auth_scheme": "client_assertion",
            "client_id": "yourclientid",
            "client_assertion": {
                "msft:azure:workloadidentity": {
                    "token": true,
                },
            },
            "scope": "first_scope second_scope",
            "auth_uri": `https://login.microsoftonline.com/{$authority_id}/oauth2/v2.0/authorize`,
            "token_uri": `https://login.microsoftonline.com/{$authority_id}/oauth2/v2.0/token`,
            "redirect_uri": "https://local.redirect.com/oauth",
        })

        // Optionally enable PKCE
        $conf.extensions = ({"pkce": true})

        // Optionally disable SSL verification
        $conf.ssl = ({"verify": false})

        // Optionally provide additional key-val parameters
        // to include when calling the auth URI
        $conf.extra_auth_params = ({"customparam": "foo"})

        $lib.inet.http.oauth.v2.addProvider($conf)

    If the ``client_id`` value should come from the AZURE_CLIENT_ID environment variable, use the
    following configuration::

        $conf = ({
            "iden": $iden,
            "name": "example_provider",
            "auth_scheme": "client_assertion",
            "client_assertion": {
                "msft:azure:workloadidentity": {
                    "token": true,
                    "client_id": true,
                },
            },
            "scope": "first_scope second_scope",
            "auth_uri": `https://login.microsoftonline.com/{$authority_id}/oauth2/v2.0/authorize`,
            "token_uri": `https://login.microsoftonline.com/{$authority_id}/oauth2/v2.0/token`,
            "redirect_uri": "https://local.redirect.com/oauth",
        })

    Add a new provider which uses a custom Storm callback to obtain the client_assertion data. These
    callbacks are executed as the user who is performing the authorization_code workflow. The Storm
    callback must return data in a tuple of ``boolean`` and a dictionary containing the assertion in the
    key ``token``. Error messages should be in the key ``error``::

        $iden = $lib.guid(callstormexample, provider, oauth)

        // Example callback
        $callbackQuery = ${
            $url = `{$baseurl}/api/oauth/getAssertion`
            $resp = $lib.inet.http.get($url, ssl=$ssl)
            if ($resp.code = 200) {
                $resp = ([true, {'token': $resp.json().assertion}])
            } else {
                $resp = ([false, {"error": `Failed to get assertion from {$url}`}])
            }
            return ( $resp )
        }

        // Specify any variables that need to be provided to $callbackQuery
        $myCallbackVars = ({
            'baseurl': 'https://local.assertion.provider.corp',
            'ssl': ({"verify": true}),
        })

        // Specify the view the callback is run in.
        $view = $lib.view.get().iden

        $conf = ({
            "iden": $iden,
            "name": "example_provider",
            "auth_scheme": "client_assertion",
            "client_id": "yourclientid",
            "client_assertion": {
                "cortex:callstorm": {
                    "query": $callbackQuery,
                    "view": $view,
                    "vars": $myCallbackVars,
                },
            },
            "scope": "first_scope second_scope",
            "auth_uri": "https://provider.com/auth",
            "token_uri": "https://provider.com/token",
            "redirect_uri": "https://local.redirect.com/oauth",
        })

        // Optionally enable PKCE
        $conf.extensions = ({"pkce": true})

        $lib.inet.http.oauth.v2.addProvider($conf)


**Args:**

- `conf` (`dict`): A provider configuration.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-inet-http-oauth-v2-clearUserAccessToken"></a>

### $lib.inet.http.oauth.v2.clearUserAccessToken(iden)

Clear the stored refresh data for the current user's provider access token.

**Args:**

- `iden` (`str`): The provider iden.


**Returns:**
The existing token state data or None if it did not exist. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-inet-http-oauth-v2-delProvider"></a>

### $lib.inet.http.oauth.v2.delProvider(iden)

Delete a provider configuration.

**Args:**

- `iden` (`str`): The provider iden.


**Returns:**
The deleted provider configuration or None if it does not exist. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-inet-http-oauth-v2-getProvider"></a>

### $lib.inet.http.oauth.v2.getProvider(iden)

Get a provider configuration

**Args:**

- `iden` (`str`): The provider iden.


**Returns:**
The provider configuration or None if it does not exist. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-inet-http-oauth-v2-getUserAccessToken"></a>

### $lib.inet.http.oauth.v2.getUserAccessToken(iden)

Get the provider access token for the current user.

Example:

    Retrieve the token and handle needing an auth code::

        $provideriden = $lib.globals.get("oauth:myprovider")

        ($ok, $data) = $lib.inet.http.oauth.v2.getUserAccessToken($provideriden)

        if $ok {
            // $data is the token to be used in a request
        else {
            // $data is a message stating why the token is not available
            // caller should now handle retrieving a new auth code for the user
        }


**Args:**

- `iden` (`str`): The provider iden.


**Returns:**
List of (<boolean>, <token/mesg>) for status and data. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-inet-http-oauth-v2-listProviders"></a>

### $lib.inet.http.oauth.v2.listProviders()

List provider configurations

**Returns:**
List of (iden, conf) tuples. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-inet-http-oauth-v2-setUserAuthCode"></a>

### $lib.inet.http.oauth.v2.setUserAuthCode(iden, authcode, code_verifier=(null))

Set the auth code for the current user.

**Args:**

- `iden` (`str`): The provider iden.
- `authcode` (`str`): The auth code for the user.
- `code_verifier` (`str`): Optional PKCE code verifier.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-inet-imap"></a>

## $lib.inet.imap

A Storm library to connect to an IMAP server.

For APIs that accept an ssl argument, the dictionary may contain the following values::

    ({
        'verify': <bool> - Perform SSL/TLS verification. Default is True.
        'client_cert': <str> - PEM encoded full chain certificate for use in mTLS.
        'client_key': <str> - PEM encoded key for use in mTLS. Alternatively, can be included in client_cert.
        'ca_cert': <str> - A PEM encoded full chain CA certificate for use when verifying the request.
    })


<a id="stormlibs-lib-inet-imap-connect"></a>

### $lib.inet.imap.connect(host, port=(993), timeout=(30), ssl=(null))

Open a connection to an IMAP server.

If the port is 993, SSL/TLS is enabled by default with verification.

This method will wait for a "hello" response from the server
before returning the ``inet:imap:server`` instance.


**Args:**

- `host` (`str`): The IMAP hostname.
- `port` (`int`): The IMAP server port.
- `timeout` (`int`): The time to wait for all commands on the server to execute.
- `ssl` (`dict`): Optional SSL/TLS options. See $lib.inet.imap help for additional details.


**Returns:**
A new ``inet:imap:server`` instance. The return type is [`inet:imap:server`](stormtypes_prims.md#stormprims-inet-imap-server-f527).

<a id="stormlibs-lib-inet-ipv6"></a>

## $lib.inet.ipv6

A Storm Library for providing ipv6 helpers.


<a id="stormlibs-lib-inet-ipv6-expand"></a>

### $lib.inet.ipv6.expand(valu)

Convert a IPv6 address to its expanded form.'

Notes:
   The expanded form is also sometimes called the "long form" address.

Examples:
   Expand a ipv6 address to its long form::

       $expandedvalu = $lib.inet.ipv6.expand('2001:4860:4860::8888')


**Args:**

- `valu` (`str`): IPv6 Address to expand


**Returns:**
The expanded form. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-inet-smtp"></a>

## $lib.inet.smtp

A Storm Library for sending email messages via SMTP.


<a id="stormlibs-lib-inet-smtp-message"></a>

### $lib.inet.smtp.message()

Construct a new email message.

**Returns:**
The newly constructed inet:smtp:message. The return type is [`inet:smtp:message`](stormtypes_prims.md#stormprims-inet-smtp-message-f527).

<a id="stormlibs-lib-infosec-cvss"></a>

## $lib.infosec.cvss

A Storm library which implements CVSS score calculations.


<a id="stormlibs-lib-infosec-cvss-vectToScore"></a>

### $lib.infosec.cvss.vectToScore(vect, vers=(null))

Compute CVSS scores from a vector string.

Takes a CVSS vector string, attempts to automatically detect the version
(defaults to CVSS3.1 if it cannot), and calculates the base, temporal,
and environmental scores.

Raises:
    - BadArg: An invalid `vers` string is provided
    - BadDataValu: The vector string is invalid in some way.
      Possible reasons are malformed string, duplicated
      metrics, missing mandatory metrics, and invalid metric
      values.

**Args:**

- `vect` (`str`): 
                            A valid CVSS vector string.

                            The following examples are valid formats:

                                - CVSS 2 with version: `CVSS2#AV:L/AC:L/Au:M/C:P/I:C/A:N`
                                - CVSS 2 with parentheses: `(AV:L/AC:L/Au:M/C:P/I:C/A:N)`
                                - CVSS 2 without parentheses: `AV:L/AC:L/Au:M/C:P/I:C/A:N`
                                - CVSS 3.0 with version: `CVSS:3.0/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L`
                                - CVSS 3.1 with version: `CVSS:3.1/AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L`
                                - CVSS 3.0/3.1 with parentheses: `(AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L)`
                                - CVSS 3.0/3.1 without parentheses: `AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L`
- `vers` (`str`): 
                            A valid version string or None to autodetect the
                            version from the vector string. Accepted values
                            are: 2, 3.0, 3.1, None.


**Returns:**

                                A dictionary with the detected version, base score, temporal score,
                                environmental score, overall score, and normalized vector string.
                                The normalized vector string will have metrics ordered in
                                specification order and metrics with undefined values will be
                                removed. Example::

                                    {
                                        'version': '3.1',
                                        'score': 4.3,
                                        'base': 5.0,
                                        'temporal': 4.4,
                                        'environmental': 4.3,
                                        'normalized': 'AV:N/AC:H/PR:L/UI:R/S:U/C:L/I:L/A:L'
                                    }

                               The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-infosec-mitre-attack-flow"></a>

## $lib.infosec.mitre.attack.flow

A Storm library which implements modeling MITRE ATT&CK Flow diagrams.


<a id="stormlibs-lib-infosec-mitre-attack-flow-ingest"></a>

### $lib.infosec.mitre.attack.flow.ingest(flow)

Ingest a MITRE ATT&CK Flow diagram in JSON format.

**Args:**

- `flow` (`any`): The JSON data to ingest.


**Returns:**
The it:mitre:attack:flow node representing the ingested attack flow diagram. The return type may be one of the following: [`node`](stormtypes_prims.md#stormprims-node-f527), `null`.

<a id="stormlibs-lib-infosec-mitre-attack-flow-norm"></a>

### $lib.infosec.mitre.attack.flow.norm(flow)

Normalize a MITRE ATT&CK Flow diagram in JSON format.

**Args:**

- `flow` (`dict`): The MITRE ATT&CK Flow diagram in JSON format to normalize (flatten and sort).


**Returns:**
The normalized MITRE ATT&CK Flow diagram. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-iters"></a>

## $lib.iters

A Storm library for providing iterator helpers.


<a id="stormlibs-lib-iters-enum"></a>

### $lib.iters.enum(genr)

Yield (<indx>, <item>) tuples from an iterable or generator.

**Args:**

- `genr` (`list`): An iterable or generator.


**Yields:**
Yields (<indx>, <item>) tuples. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-iters-zip"></a>

### $lib.iters.zip(*args)

Yield tuples created by iterating multiple iterables in parallel.

**Args:**

- `*args` (`list`): Iterables or generators.


**Yields:**
Yields tuples with an item from each iterable or generator. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-json"></a>

## $lib.json

A Storm Library for interacting with Json data.


<a id="stormlibs-lib-json-load"></a>

### $lib.json.load(text)

Parse a JSON string and return the deserialized data.

**Args:**

- `text` (`str`): The string to be deserialized.


**Returns:**
The JSON deserialized object. The return type is `prim`.

<a id="stormlibs-lib-json-save"></a>

### $lib.json.save(item, indent=(false))

Save an object as a JSON string.

**Args:**

- `item` (`any`): The item to be serialized as a JSON string.
- `indent` (`boolean`): Indent serialized data with two spaces.


**Returns:**
The JSON serialized object. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-json-schema"></a>

### $lib.json.schema(schema, use_default=(true))

Get a JS schema validation object.

**Args:**

- `schema` (`dict`): The JsonSchema to use.
- `use_default` (`boolean`): Whether to insert default schema values into the validated data structure.


**Returns:**
A validation object that can be used to validate data structures. The return type is [`json:schema`](stormtypes_prims.md#stormprims-json-schema-f527).

<a id="stormlibs-lib-jsonstor"></a>

## $lib.jsonstor

Implements cortex JSON storage.


<a id="stormlibs-lib-jsonstor-cachedel"></a>

### $lib.jsonstor.cachedel(path, key)

Remove cached data set with cacheset.

**Args:**

- `path`: The base path to use for the cache key. The input type may be one of the following: `str`, `list`.
- `key` (`prim`): The value to use for the GUID cache key.


**Returns:**
True if the del operation was successful. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-jsonstor-cacheget"></a>

### $lib.jsonstor.cacheget(path, key, asof='now', envl=(false))

Retrieve data stored with cacheset() if it was stored more recently than the asof argument.

**Args:**

- `path`: The base path to use for the cache key. The input type may be one of the following: `str`, `list`.
- `key` (`prim`): The value to use for the GUID cache key.
- `asof` (`time`): The max cache age.
- `envl` (`boolean`): Return the full cache envelope.


**Returns:**
The cached value (or envelope) or null. The return type is `prim`.

<a id="stormlibs-lib-jsonstor-cacheset"></a>

### $lib.jsonstor.cacheset(path, key, valu)

Set cache data with an envelope that tracks time for cacheget() use.

**Args:**

- `path`: The base path to use for the cache key. The input type may be one of the following: `str`, `list`.
- `key` (`prim`): The value to use for the GUID cache key.
- `valu` (`prim`): The data to store.


**Returns:**
The cached asof time and path. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-jsonstor-del"></a>

### $lib.jsonstor.del(path, prop=(null))

Delete a stored JSON object or object.

**Args:**

- `path`: A path string or list of path parts. The input type may be one of the following: `str`, `list`.
- `prop`: A property name or list of name parts. The input type may be one of the following: `str`, `list`.


**Returns:**
True if the del operation was successful. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-jsonstor-get"></a>

### $lib.jsonstor.get(path, prop=(null))

Return a stored JSON object or object property.

**Args:**

- `path`: A path string or list of path parts. The input type may be one of the following: `str`, `list`.
- `prop`: A property name or list of name parts. The input type may be one of the following: `str`, `list`.


**Returns:**
The previously stored value or ``(null)``. The return type is `prim`.

<a id="stormlibs-lib-jsonstor-iter"></a>

### $lib.jsonstor.iter(path=(null))

Yield (<path>, <valu>) tuples for the JSON objects.

**Args:**

- `path`: A path string or list of path parts. The input type may be one of the following: `str`, `list`.


**Yields:**
(<path>, <item>) tuples. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-jsonstor-set"></a>

### $lib.jsonstor.set(path, valu, prop=(null))

Set a JSON object or object property.

**Args:**

- `path`: A path string or list of path elements. The input type may be one of the following: `str`, `list`.
- `valu` (`prim`): The value to set as the JSON object or object property.
- `prop`: A property name or list of name parts. The input type may be one of the following: `str`, `list`.


**Returns:**
True if the set operation was successful. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-layer"></a>

## $lib.layer

A Storm Library for interacting with Layers in the Cortex.


<a id="stormlibs-lib-layer-add"></a>

### $lib.layer.add(ldef=(null))

Add a layer to the Cortex.

**Args:**

- `ldef` (`dict`): The layer definition dictionary.


**Returns:**
A ``layer`` object representing the new layer. The return type is [`layer`](stormtypes_prims.md#stormprims-layer-f527).

<a id="stormlibs-lib-layer-del"></a>

### $lib.layer.del(iden)

Delete a layer from the Cortex.

**Args:**

- `iden` (`str`): The iden of the layer to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-layer-get"></a>

### $lib.layer.get(iden=(null))

Get a Layer from the Cortex. Raises ``NoSuchIden`` if no such layer exists or the user cannot read it.

**Args:**

- `iden` (`str`): The iden of the layer to get. If not set, this defaults to the top layer of the current View.


**Returns:**
The storm layer object. The return type is [`layer`](stormtypes_prims.md#stormprims-layer-f527).

<a id="stormlibs-lib-layer-list"></a>

### $lib.layer.list()

List the layers in a Cortex.

**Returns:**
List of ``layer`` objects. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-lift"></a>

## $lib.lift

A Storm Library for interacting with lift helpers.


<a id="stormlibs-lib-lift-byNodeData"></a>

### $lib.lift.byNodeData(name)

Lift nodes which have a given nodedata name set on them.

**Args:**

- `name` (`str`): The name of the nodedata key to lift by.


**Yields:**
Yields nodes with the given nodedata name. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-lift-byPropAlts"></a>

### $lib.lift.byPropAlts(name, valu, cmpr='=')

Lift nodes by a property value, including alternate property values.

**Args:**

- `name` (`str`): The name of the property to lift by.
- `valu` (`prim`): The value for the property.
- `cmpr` (`str`): The comparison operation to use on the value.


**Yields:**
Yields nodes. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-lift-byPropRefs"></a>

### $lib.lift.byPropRefs(props, valu=(null), cmpr='=')

Lift nodes which are referenced by properties of other nodes.

**Args:**

- `props`: The name of the props to check for references. The input type may be one of the following: `str`, `list`.
- `valu` (`prim`): The value for the property.
- `cmpr` (`str`): The comparison operation to use on the value.


**Yields:**
Yields nodes. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-lift-byPropsDict"></a>

### $lib.lift.byPropsDict(form, props, errok=(false))

Lift all nodes of a form which have a set of properties with specific values.

**Args:**

- `form` (`str`): The name of the form to lift.
- `props` (`dict`): A dictionary of properties and values.
- `errok` (`boolean`): If set, norming failures will not raise an exception.


**Yields:**
Yields nodes. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-lift-byTypeValue"></a>

### $lib.lift.byTypeValue(name, valu, cmpr='=')

Lift nodes which have a property with a specific type and value.

**Args:**

- `name` (`str`): The name of the type to lift.
- `valu` (`prim`): The value for the type.
- `cmpr` (`str`): The comparison operation to use on the value.


**Yields:**
Yields nodes. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-lift-tagsByPref"></a>

### $lib.lift.tagsByPref(prefix, depth=(0))

Lift syn:tag nodes by prefix.

Notes:
    By default this will only return tags at the depth specified in the prefix.
    The depth argument may be provided to indicate the number of additional levels
    in the tag hierarchy to include.


**Args:**

- `prefix` (`str`): The prefix to search for.
- `depth` (`int`): The number of additional levels in the tag hierarchy to include.


**Yields:**
Yields syn:tag nodes with the given prefix. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-log"></a>

## $lib.log

A Storm library which implements server side logging. These messages are logged to the
``synapse.storm.log`` logger.


<a id="stormlibs-lib-log-debug"></a>

### $lib.log.debug(mesg, extra=(null))

Log a message to the Cortex at the debug log level.

Notes:
    This requires the ``log.debug`` permission to use.

Examples:
    Log a debug message::

        $lib.log.debug('I am a debug message!')

    Log a debug message with extra information::

        $lib.log.debug('Extra information included here.', extra=({"key": $valu}))

**Args:**

- `mesg` (`str`): The message to log.
- `extra` (`dict`): Extra key / value pairs to include when structured logging is enabled on the Cortex.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-log-error"></a>

### $lib.log.error(mesg, extra=(null))

Log a message to the Cortex at the error log level.

Notes:
    This requires the ``log.error`` permission to use.

Examples:
    Log an error message::

        $lib.log.error('I am a error message!')

    Log an error message with extra information::

        $lib.log.error('Extra information included here.', extra=({"key": $valu}))

**Args:**

- `mesg` (`str`): The message to log.
- `extra` (`dict`): Extra key / value pairs to include when structured logging is enabled on the Cortex.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-log-info"></a>

### $lib.log.info(mesg, extra=(null))

Log a message to the Cortex at the info log level.

Notes:
    This requires the ``log.info`` permission to use.

Examples:
    Log an info message::

        $lib.log.info('I am a info message!')

    Log an info message with extra information::

        $lib.log.info('Extra information included here.', extra=({"key": $valu}))

**Args:**

- `mesg` (`str`): The message to log.
- `extra` (`dict`): Extra key / value pairs to include when structured logging is enabled on the Cortex.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-log-warning"></a>

### $lib.log.warning(mesg, extra=(null))

Log a message to the Cortex at the warning log level.

Notes:
    This requires the ``log.warning`` permission to use.

Examples:
    Log a warning message::

        $lib.log.warning('I am a warning message!')

    Log a warning message with extra information::

        $lib.log.warning('Extra information included here.', extra=({"key": $valu}))

**Args:**

- `mesg` (`str`): The message to log.
- `extra` (`dict`): Extra key / value pairs to include when structured logging is enabled on the Cortex.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-macro"></a>

## $lib.macro

A Storm Library for interacting with the Storm Macros in the Cortex.


<a id="stormlibs-lib-macro-del"></a>

### $lib.macro.del(name)

Delete a Storm Macro by name from the Cortex.

**Args:**

- `name` (`str`): The name of the macro to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-macro-get"></a>

### $lib.macro.get(name)

Get a Storm Macro definition by name from the Cortex.

**Args:**

- `name` (`str`): The name of the macro to get.


**Returns:**
A macro definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-macro-grant"></a>

### $lib.macro.grant(name, scope, iden, level)

Modify permissions granted to users/roles on a Storm Macro.

**Args:**

- `name` (`str`): Name of the Storm Macro to modify.
- `scope` (`str`): The scope, either "users" or "roles".
- `iden` (`str`): The user/role iden depending on scope.
- `level` (`int`): The permission level number.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-macro-list"></a>

### $lib.macro.list()

Get a list of Storm Macros in the Cortex.

**Returns:**
A list of ``dict`` objects containing Macro definitions. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-macro-mod"></a>

### $lib.macro.mod(name, info)

Modify user editable properties of a Storm Macro.

**Args:**

- `name` (`str`): Name of the Storm Macro to modify.
- `info` (`dict`): A dictionary of the properties to edit.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-macro-set"></a>

### $lib.macro.set(name, storm)

Add or modify an existing Storm Macro in the Cortex.

**Args:**

- `name` (`str`): Name of the Storm Macro to add or modify.
- `storm`: The Storm query to add to the macro. The input type may be one of the following: `str`, `storm:query`.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-math"></a>

## $lib.math

A Storm library for performing math operations.


<a id="stormlibs-lib-math-number"></a>

### $lib.math.number(value)

Convert a value to a Storm Number object.

Storm Numbers are high precision fixed point decimals corresponding to
the hugenum storage type.

This is not to be used for converting a string to an integer.


**Args:**

- `value` (`any`): Value to convert.


**Returns:**
A Number object. The return type is [`number`](stormtypes_prims.md#stormprims-number-f527).

<a id="stormlibs-lib-mime-html"></a>

## $lib.mime.html

A Storm library for manipulating HTML text.


<a id="stormlibs-lib-mime-html-totext"></a>

### $lib.mime.html.totext(html, separator="\n", strip=(true))

Return inner text from all tags within an HTML document.

**Args:**

- `html` (`str`): The HTML text to be parsed.
- `separator` (`str`): The string used to join text.
- `strip` (`boolean`): Strip whitespace from the beginning and end of tag text.


**Returns:**
The separator-joined inner HTML text. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-model"></a>

## $lib.model

A Storm Library for interacting with the Data Model in the Cortex.


<a id="stormlibs-lib-model-edge"></a>

### $lib.model.edge(n1form, verb, n2form)

Get an edge object by name.

**Args:**

- `n1form` (`str`): The form of the n1 node of the edge to retrieve.
- `verb` (`str`): The verb of the edge to retrieve.
- `n2form` (`str`): The form of the n2 node of the edge to retrieve.


**Returns:**
The ``model:edge`` instance of the edge if present or null. The return type may be one of the following: [`model:edge`](stormtypes_prims.md#stormprims-model-edge-f527), `null`.

<a id="stormlibs-lib-model-form"></a>

### $lib.model.form(name)

Get a form object by name.

**Args:**

- `name` (`str`): The name of the form to retrieve.


**Returns:**
The ``model:form`` instance if the form is present or null. The return type may be one of the following: [`model:form`](stormtypes_prims.md#stormprims-model-form-f527), `null`.

<a id="stormlibs-lib-model-prop"></a>

### $lib.model.prop(name)

Get a prop object by name.

**Args:**

- `name` (`str`): The name of the prop to retrieve.


**Returns:**
The ``model:property`` instance if the type if present or null. The return type may be one of the following: [`model:property`](stormtypes_prims.md#stormprims-model-property-f527), `null`.

<a id="stormlibs-lib-model-tagprop"></a>

### $lib.model.tagprop(name)

Get a tag property object by name.

**Args:**

- `name` (`str`): The name of the tag prop to retrieve.


**Returns:**
The ``model:tagprop`` instance of the tag prop if present or null. The return type may be one of the following: [`model:tagprop`](stormtypes_prims.md#stormprims-model-tagprop-f527), `null`.

<a id="stormlibs-lib-model-type"></a>

### $lib.model.type(name)

Get a type object by name.

**Args:**

- `name` (`str`): The name of the type to retrieve.


**Returns:**
The ``model:type`` instance if the type if present on the form or null. The return type may be one of the following: [`model:type`](stormtypes_prims.md#stormprims-model-type-f527), `null`.

<a id="stormlibs-lib-model-deprecated"></a>

## $lib.model.deprecated

A storm library for interacting with the model deprecation mechanism.


<a id="stormlibs-lib-model-deprecated-lock"></a>

### $lib.model.deprecated.lock(name, locked)

Set the locked property for a deprecated model element.

**Args:**

- `name` (`str`): The full path of the model element to lock.
- `locked` (`boolean`): The lock status.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-deprecated-locks"></a>

### $lib.model.deprecated.locks()

Get a dictionary of the data model elements which are deprecated and their lock status in the Cortex.

**Returns:**
A dictionary of named elements to their boolean lock values. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-model-ext"></a>

## $lib.model.ext

A Storm library for manipulating extended model elements.


<a id="stormlibs-lib-model-ext-addEdge"></a>

### $lib.model.ext.addEdge(n1form, verb, n2form, edgeinfo)

Add an extended edge definition to the data model.

**Args:**

- `n1form` (`str`): The form of the n1 node. May be "*" or null to specify "any".
- `verb` (`str`): The edge verb, which must begin with "_".
- `n2form` (`str`): The form of the n2 node. May be "*" or null to specify "any".
- `edgeinfo` (`dict`): A Synapse edge info dictionary.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-addExtModel"></a>

### $lib.model.ext.addExtModel(model)

Add extended model elements to the Cortex from getExtModel().

**Args:**

- `model` (`dict`): A model dictionary from getExtModel().


**Returns:**
The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-model-ext-addForm"></a>

### $lib.model.ext.addForm(formname, basetype, typeopts, typeinfo)

Add an extended form definition to the data model.

**Args:**

- `formname` (`str`): The name of the form to add.
- `basetype` (`str`): The base type the form is derived from.
- `typeopts` (`dict`): A Synapse type opts dictionary.
- `typeinfo` (`dict`): A Synapse form info dictionary.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-addFormProp"></a>

### $lib.model.ext.addFormProp(formname, propname, typedef, propinfo)

Add an extended property definition to the data model.

**Args:**

- `formname` (`str`): The name of the form to add the property to.
- `propname` (`str`): The name of the extended property.
- `typedef` (`list`): A Synapse type definition tuple.
- `propinfo` (`dict`): A Synapse property definition dictionary.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-addTagProp"></a>

### $lib.model.ext.addTagProp(propname, typedef, propinfo)

Add an extended tag property definition to the data model.

**Args:**

- `propname` (`str`): The name of the tag property.
- `typedef` (`list`): A Synapse type definition tuple.
- `propinfo` (`dict`): A Synapse property definition dictionary.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-addType"></a>

### $lib.model.ext.addType(typename, basetype, typeopts, typeinfo)

Add an extended type definition to the data model.

**Args:**

- `typename` (`str`): The name of the type to add.
- `basetype` (`str`): The base type the type is derived from.
- `typeopts` (`dict`): A Synapse type opts dictionary.
- `typeinfo` (`dict`): A Synapse type info dictionary.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-delEdge"></a>

### $lib.model.ext.delEdge(n1form, verb, n2form)

Remove an extended edge definition from the data model.

**Args:**

- `n1form` (`str`): The form of the n1 node. May be "*" or null to specify "any".
- `verb` (`str`): The edge verb, which must begin with "_".
- `n2form` (`str`): The form of the n2 node. May be "*" or null to specify "any".


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-delForm"></a>

### $lib.model.ext.delForm(formname)

Remove an extended form definition from the model.

**Args:**

- `formname` (`str`): The extended form to remove.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-delFormProp"></a>

### $lib.model.ext.delFormProp(formname, propname, force=(false))

Remove an extended property definition from the model.

**Args:**

- `formname` (`str`): The form with the extended property.
- `propname` (`str`): The extended property to remove.
- `force` (`boolean`): Delete the property from all nodes before removing the definition.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-delTagProp"></a>

### $lib.model.ext.delTagProp(propname, force=(false))

Remove an extended tag property definition from the model.

**Args:**

- `propname` (`str`): Name of the tag property to remove.
- `force` (`boolean`): Delete the tag property from all nodes before removing the definition.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-delType"></a>

### $lib.model.ext.delType(typename)

Remove an extended type definition from the model.

**Args:**

- `typename` (`str`): The extended type to remove.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-ext-getExtModel"></a>

### $lib.model.ext.getExtModel()

Get all extended model elements.

**Returns:**
The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-model-migration"></a>

## $lib.model.migration

A Storm library containing migration tools.


<a id="stormlibs-lib-model-migration-copyData"></a>

### $lib.model.migration.copyData(src, dst, overwrite=(false))

Copy node data from the src node to the dst node.

**Args:**

- `src` (`node`): The node to copy data from.
- `dst` (`node`): The node to copy data to.
- `overwrite` (`boolean`): Copy data even if the key exists on the destination node.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-migration-copyEdges"></a>

### $lib.model.migration.copyEdges(src, dst)

Copy edges from the src node to the dst node.

**Args:**

- `src` (`node`): The node to copy edges from.
- `dst` (`node`): The node to copy edges to.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-migration-copyExtProps"></a>

### $lib.model.migration.copyExtProps(src, dst)

Copy extended properties from the src node to the dst node.

**Args:**

- `src` (`node`): The node to copy extended props from.
- `dst` (`node`): The node to copy extended props to.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-migration-copyTags"></a>

### $lib.model.migration.copyTags(src, dst, overwrite=(false))

Copy tags, tag timestamps, and tag props from the src node to the dst node.

**Args:**

- `src` (`node`): The node to copy tags from.
- `dst` (`node`): The node to copy tags to.
- `overwrite` (`boolean`): Copy tag property value even if the property exists on the destination node.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-migration-s"></a>

## $lib.model.migration.s

A Storm library for selectively migrating nodes in the current view.


<a id="stormlibs-lib-model-tags"></a>

## $lib.model.tags

A Storm Library for interacting with tag specifications in the Cortex Data Model.


<a id="stormlibs-lib-model-tags-del"></a>

### $lib.model.tags.del(tagname)

Delete a tag model specification.

Examples:
    Delete the tag model specification for ``cno.threat``::

        $lib.model.tags.del(cno.threat)

**Args:**

- `tagname` (`str`): The name of the tag.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-model-tags-get"></a>

### $lib.model.tags.get(tagname)

Retrieve a tag model specification.

Examples:
    Get the tag model specification for ``cno.threat``::

        $dict = $lib.model.tags.get(cno.threat)

**Args:**

- `tagname` (`str`): The name of the tag.


**Returns:**
The tag model definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-model-tags-list"></a>

### $lib.model.tags.list()

List all tag model specifications.

Examples:
    Iterate over the tag model specifications in the Cortex::

        for ($name, $info) in $lib.model.tags.list() {
            ...
        }

**Returns:**
List of tuples containing the tag name and model definition The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-model-tags-pop"></a>

### $lib.model.tags.pop(tagname, propname)

Pop and return a tag model property.

Examples:
    Remove the regex list from the ``cno.threat`` tag model::

        $regxlist = $lib.model.tags.pop(cno.threat, regex)

**Args:**

- `tagname` (`str`): The name of the tag.
- `propname` (`str`): The name of the tag model property.


**Returns:**
The value of the property. The return type is `prim`.

<a id="stormlibs-lib-model-tags-set"></a>

### $lib.model.tags.set(tagname, propname, propvalu)

Set a tag model property for a tag.

Examples:
    Create a tag model for the ``cno.cve`` tag::

        $regx = ([(null), (null), "[0-9]{4}", "[0-9]{5}"])
        $lib.model.tags.set(cno.cve, regex, $regx)

**Args:**

- `tagname` (`str`): The name of the tag.
- `propname` (`str`): The name of the tag model property.
- `propvalu` (`prim`): The value to set.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-pack"></a>

## $lib.pack

Packing / unpacking structured bytes.


<a id="stormlibs-lib-pack-en"></a>

### $lib.pack.en(fmt, items)

Pack a sequence of items into an array of bytes.

**Args:**

- `fmt` (`str`): A python struct.pack() format string.
- `items` (`list`): A list of values to be packed.


**Returns:**
The packed byte structure. The return type is [`bytes`](stormtypes_prims.md#stormprims-bytes-f527).

<a id="stormlibs-lib-pack-un"></a>

### $lib.pack.un(fmt, byts, offs=(0))

Unpack a sequence of items from an array of bytes.

**Args:**

- `fmt` (`str`): A python struct.unpack() format string.
- `byts` (`bytes`): Bytes to be unpacked
- `offs` (`int`): The offset to begin unpacking from.


**Returns:**
The unpacked items. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-pipe"></a>

## $lib.pipe

A Storm library for interacting with non-persistent queues.


<a id="stormlibs-lib-pipe-gen"></a>

### $lib.pipe.gen(filler, size=(10000))

Generate and return a Storm Pipe.

Notes:
    The filler query is run in parallel with $pipe.

Examples:
    Fill a pipe with a query and consume it with another::

        $pipe = $lib.pipe.gen(${ $pipe.puts((1, 2, 3)) })

        for $items in $pipe.slices(size=2) {
            $dostuff($items)
        }


**Args:**

- `filler`: A Storm query to fill the Pipe. The input type may be one of the following: `str`, `storm:query`.
- `size` (`int`): Maximum size of the pipe.


**Returns:**
The pipe containing query results. The return type is [`pipe`](stormtypes_prims.md#stormprims-pipe-f527).

<a id="stormlibs-lib-pkg"></a>

## $lib.pkg

A Storm Library for interacting with Storm Packages.


<a id="stormlibs-lib-pkg-add"></a>

### $lib.pkg.add(pkgdef, verify=(false))

Add a Storm Package to the Cortex.

**Args:**

- `pkgdef` (`dict`): A Storm Package definition.
- `verify` (`boolean`): Verify storm package signature.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-pkg-del"></a>

### $lib.pkg.del(name)

Delete a Storm Package from the Cortex.

**Args:**

- `name` (`str`): The name of the package to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-pkg-deps"></a>

### $lib.pkg.deps(pkgdef)

Verify the dependencies for a Storm Package.

**Args:**

- `pkgdef` (`dict`): A Storm Package definition.


**Returns:**
A dictionary listing dependencies and if they are met. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-pkg-get"></a>

### $lib.pkg.get(name)

Get a Storm Package from the Cortex.

**Args:**

- `name` (`str`): A Storm Package name.


**Returns:**
The Storm package definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-pkg-has"></a>

### $lib.pkg.has(name)

Check if a Storm Package is available in the Cortex.

**Args:**

- `name` (`str`): A Storm Package name to check for the existence of.


**Returns:**
True if the package exists in the Cortex, False if it does not. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-pkg-list"></a>

### $lib.pkg.list()

Get a list of Storm Packages loaded in the Cortex.

**Returns:**
A list of Storm Package definitions. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-pkg-queues"></a>

### $lib.pkg.queues(name)

Access namespaced Queues for a package.

**Args:**

- `name` (`str`): A Storm Package name to access Queues for.


**Returns:**
An object for accessing the package Queues. The return type is [`pkg:queues`](stormtypes_prims.md#stormprims-pkg-queues-f527).

<a id="stormlibs-lib-pkg-state"></a>

### $lib.pkg.state(name)

Get a read-only dictionary representing the package's persistent state.

**Args:**

- `name` (`str`): A Storm Package name to get state for.


**Returns:**
A read-only dictionary representing the package state. The return type is [`pkg:state`](stormtypes_prims.md#stormprims-pkg-state-f527).

<a id="stormlibs-lib-pkg-vars"></a>

### $lib.pkg.vars(name)

Get a dictionary representing the package's persistent variables.

**Args:**

- `name` (`str`): A Storm Package name to get vars for.


**Returns:**
A dictionary representing the package variables. The return type is [`pkg:vars`](stormtypes_prims.md#stormprims-pkg-vars-f527).

<a id="stormlibs-lib-queue"></a>

## $lib.queue

A Storm Library for interacting with persistent Queues in the Cortex.


<a id="stormlibs-lib-queue-add"></a>

### $lib.queue.add(name, iden=(null))

Add a Queue to the Cortex with a given name.

**Args:**

- `name` (`str`): The name of the Queue to add.
- `iden` (`str`): The iden to assign to the Queue.


**Returns:**
The return type is [`queue`](stormtypes_prims.md#stormprims-queue-f527).

<a id="stormlibs-lib-queue-byname"></a>

### $lib.queue.byname(name)

Get an existing Queue object by name.

**Args:**

- `name` (`str`): The name of the Queue to get.


**Returns:**
A ``queue`` object. The return type is [`queue`](stormtypes_prims.md#stormprims-queue-f527).

<a id="stormlibs-lib-queue-del"></a>

### $lib.queue.del(iden)

Delete a given Queue.

**Args:**

- `iden` (`str`): The iden of the Queue to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-queue-gen"></a>

### $lib.queue.gen(name)

Add or get a Queue in a single operation.

**Args:**

- `name` (`str`): The name of the Queue to add or get.


**Returns:**
The return type is [`queue`](stormtypes_prims.md#stormprims-queue-f527).

<a id="stormlibs-lib-queue-get"></a>

### $lib.queue.get(iden)

Get an existing Queue object by iden.

**Args:**

- `iden` (`str`): The iden of the Queue to get.


**Returns:**
A ``queue`` object. The return type is [`queue`](stormtypes_prims.md#stormprims-queue-f527).

<a id="stormlibs-lib-queue-list"></a>

### $lib.queue.list()

Get a list of the Queues in the Cortex.

**Returns:**
A list of Queue definitions the current user is allowed to interact with. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-quorum-merge"></a>

## $lib.quorum.merge

A Storm library for accessing quorum merge requests.


<a id="stormlibs-lib-quorum-merge-list"></a>

### $lib.quorum.merge.list(todo=(false))

List pending merge requests.

**Args:**

- `todo` (`bool`): Only emit merge requests which require input from the current user.


**Yields:**
A tuple of the view and merge summary. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-random"></a>

## $lib.random

A Storm library for generating random values.


<a id="stormlibs-lib-random-generator"></a>

### $lib.random.generator(seed=(null))

Make a random generator with a given seed.

**Args:**

- `seed` (`str`): The seed value used for the random generator.


**Returns:**
The random generator object. The return type is [`random`](stormtypes_prims.md#stormprims-random-f527).

<a id="stormlibs-lib-random-int"></a>

### $lib.random.int(maxval, minval=(0))

Generate a random integer.

**Args:**

- `maxval` (`int`): The maximum random value.
- `minval` (`int`): The minimum random value.


**Returns:**
A random integer in the range min-max inclusive. The return type is `int`.

<a id="stormlibs-lib-regex"></a>

## $lib.regex

A Storm library for searching/matching with regular expressions.


<a id="stormlibs-lib-regex-escape"></a>

### $lib.regex.escape(text)

Escape arbitrary strings for use in a regular expression pattern.

Example:

    Escape node values for use in a regex pattern::

        for $match in $lib.regex.findall($lib.regex.escape($node.repr()), $mydocument) {
            // do something with $match
        }

    Escape node values for use in regular expression filters::

        it:dev:str~=$lib.regex.escape($node.repr())
        

**Args:**

- `text` (`str`): The text to escape.


**Returns:**
Input string with special characters escaped. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-regex-findall"></a>

### $lib.regex.findall(pattern, text, flags=(0))

Search the given text for the patterns and return a list of matching strings.

Note:
    If multiple matching groups are specified, the return value is a
    list of lists of strings.

Example:

    Extract the matching strings from a piece of text::

        for $x in $lib.regex.findall("G[0-9]{4}", "G0006 and G0001") {
            $dostuff($x)
        }
        

**Args:**

- `pattern` (`str`): The regular expression pattern.
- `text` (`str`): The text to match.
- `flags` (`int`): Regex flags to control the match behavior.


**Returns:**
A list of lists of strings for the matching groups in the pattern. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-regex-flags-i"></a>

### $lib.regex.flags.i

Regex flag to indicate that case insensitive matches are allowed.

**Returns:**
The type is `int`.

<a id="stormlibs-lib-regex-flags-m"></a>

### $lib.regex.flags.m

Regex flag to indicate that multiline matches are allowed.

**Returns:**
The type is `int`.

<a id="stormlibs-lib-regex-matches"></a>

### $lib.regex.matches(pattern, text, flags=(0))

Check if text matches a pattern.

Notes:
    This API requires the pattern to match at the start of the string.

Example:
    Check if the variable matches a expression::

        if $lib.regex.matches("^[0-9]+.[0-9]+.[0-9]+$", $text) {
            $lib.print("It's semver! ...probably")
        }


**Args:**

- `pattern` (`str`): The regular expression pattern.
- `text` (`str`): The text to match.
- `flags` (`int`): Regex flags to control the match behavior.


**Returns:**
True if there is a match, False otherwise. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-regex-replace"></a>

### $lib.regex.replace(pattern, replace, text, flags=(0))

Replace any substrings that match the given regular expression with the specified replacement.

Example:
    Replace a portion of a string with a new part based on a regex::

        $norm = $lib.regex.replace("\sAND\s", " & ", "Ham and eggs!", $lib.regex.flags.i)


**Args:**

- `pattern` (`str`): The regular expression pattern.
- `replace` (`str`): The text to replace matching sub strings.
- `text` (`str`): The input text to search/replace.
- `flags` (`int`): Regex flags to control the match behavior.


**Returns:**
The new string with matches replaced. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-regex-search"></a>

### $lib.regex.search(pattern, text, flags=(0))

Search the given text for the pattern and return the matching groups.

Note:
    In order to get the matching groups, patterns must use parentheses
    to indicate the start and stop of the regex to return portions of.
    If groups are not used, a successful match will return a empty list
    and a unsuccessful match will return ``(null)``.

Example:
    Extract the matching groups from a piece of text::

        $m = $lib.regex.search("^([0-9])+.([0-9])+.([0-9])+$", $text)
        if $m {
            ($maj, $min, $pat) = $m
        }

**Args:**

- `pattern` (`str`): The regular expression pattern.
- `text` (`str`): The text to match.
- `flags` (`int`): Regex flags to control the match behavior.


**Returns:**
A list of strings for the matching groups in the pattern. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-scrape"></a>

## $lib.scrape

A Storm Library for providing helpers for scraping nodes from text.


<a id="stormlibs-lib-scrape-context"></a>

### $lib.scrape.context(text)

Attempt to scrape information from a blob of text, getting the context information about the values found.

Notes:
    This does call the ``scrape`` Storm interface if that behavior is enabled on the Cortex.

Examples:
    Scrape some text and make nodes out of it::

        for ($form, $valu, $info) in $lib.scrape.context($text) {
            [ ( *$form ?= $valu ) ]
        }


**Args:**

- `text` (`str`): The text to scrape


**Yields:**
A dictionary of scraped values, rule types, and offsets scraped from the text. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-scrape-genMatches"></a>

### $lib.scrape.genMatches(text, pattern, fangs=(null), flags=(2))

genMatches is a generic helper function for constructing scrape interfaces using pure Storm.

It accepts the text, a regex pattern, and produce results that can easily be used to create
nodes.

Notes:
    The pattern must have a named regular expression match for the key ``valu`` using the
    named group syntax. For example ``(somekey\s)(?P<valu>[a-z0-9]+)\s``.

Examples:
    A scrape implementation with a regex that matches name keys in text::

        $re="(Name\:\s)(?P<valu>[a-z0-9]+)\s"
        $form="entity:name"

        function scrape(text, form) {
                $ret = ()
                for ($valu, $info) in $lib.scrape.genMatches($text, $re) {
                    $ret.append(($form, $valu, $info))
                }
                return ( $ret )
            }


**Args:**

- `text` (`str`): The text to scrape
- `pattern` (`str`): The regular expression pattern to match against.
- `fangs` (`list`): A list of (src, dst) pairs to refang from text. The src must be equal or larger than the dst in length.
- `flags` (`int`): Regex flags to use (defaults to IGNORECASE).


**Yields:**
Yields a list of (value, info) tuples scraped from the text. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-scrape-ndefs"></a>

### $lib.scrape.ndefs(text)

Attempt to scrape node form, value tuples from a blob of text.

Examples:
    Scrape some text and attempt to make nodes out of it::

        for ($form, $valu) in $lib.scrape($text) {
            [ ( *$form ?= $valu ) ]
        }

**Args:**

- `text` (`str`): The text to scrape


**Yields:**
A list of (form, value) tuples scraped from the text. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-service"></a>

## $lib.service

A Storm Library for interacting with Storm Services.


<a id="stormlibs-lib-service-add"></a>

### $lib.service.add(name, url)

Add a Storm Service to the Cortex.

**Args:**

- `name` (`str`): The cell type name of the Storm Service to add.
- `url` (`str`): The Telepath URL to the Storm Service.


**Returns:**
The Storm Service definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-service-del"></a>

### $lib.service.del(name)

Remove a Storm Service from the Cortex.

**Args:**

- `name` (`str`): The cell type name of the service to remove.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-service-get"></a>

### $lib.service.get(name)

Get a Storm Service definition.

**Args:**

- `name` (`str`): The cell type name of the service to get the definition for.


**Returns:**
A Storm Service definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-service-has"></a>

### $lib.service.has(name)

Check if a Storm Service is available in the Cortex.

**Args:**

- `name` (`str`): The cell type name of the service to check for the existence of.


**Returns:**
True if the service exists in the Cortex, False if it does not. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-service-list"></a>

### $lib.service.list()

List the Storm Service definitions for the Cortex.

Notes:
    The definition dictionaries have an additional ``ready`` key added to them to
    indicate if the Cortex is currently connected to the Storm Service or not.


**Returns:**
A list of Storm Service definitions. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-service-wait"></a>

### $lib.service.wait(name, timeout=(null))

Wait for a given service to be ready.

Notes:
    If a timeout value is not specified, this will block a Storm query until the service is available.


**Args:**

- `name` (`str`): The name, or iden, of the service to wait for.
- `timeout` (`int`): Number of seconds to wait for the service.


**Returns:**
Returns true if the service is available, false on a timeout waiting for the service to be ready. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-spooled"></a>

## $lib.spooled

A Storm Library for interacting with Spooled Objects.


<a id="stormlibs-lib-spooled-set"></a>

### $lib.spooled.set(*vals)

Get a Spooled Storm Set object.

A Spooled Storm Set object is memory-safe to grow to extraordinarily large sizes,
as it will fallback to file backed storage, with two restrictions. First
is that all items in the set can be serialized to a file if the set grows too large,
so all items added must be a serializable Storm primitive. Second is that when an
item is added to the Set, because it could be immediately written disk,
do not hold any references to it outside of the Set itself, as the two objects could
differ.


**Args:**

- `*vals` (`any`): Initial values to place in the set.


**Returns:**
The new set. The return type is [`set`](stormtypes_prims.md#stormprims-set-f527).

<a id="stormlibs-lib-stats"></a>

## $lib.stats

A Storm Library for statistics related functionality.


<a id="stormlibs-lib-stats-tally"></a>

### $lib.stats.tally()

Get a Tally object.

**Returns:**
A new tally object. The return type is [`stat:tally`](stormtypes_prims.md#stormprims-stat-tally-f527).

<a id="stormlibs-lib-stix"></a>

## $lib.stix

A Storm Library for interacting with Stix Version 2.1 CS02.


<a id="stormlibs-lib-stix-lift"></a>

### $lib.stix.lift(bundle)

Lift nodes from a STIX Bundle made by Synapse.

Notes:
    This lifts nodes using the Node definitions embedded into the bundle when created by Synapse using
    custom extension properties.

Examples:
    Lifting nodes from a STIX bundle::

        yield $lib.stix($bundle)


**Args:**

- `bundle` (`dict`): The STIX bundle to lift nodes from.


**Yields:**
Yields nodes. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-stix-validate"></a>

### $lib.stix.validate(bundle)

Validate a STIX Bundle.

Notes:
    This returns a dictionary containing the following values::

        {
            'ok': <boolean> - False if bundle is invalid, True otherwise.
            'mesg': <str> - An error message if there was an error when validating the bundle.
            'results': The results of validating the bundle.
        }


**Args:**

- `bundle` (`dict`): The stix bundle to validate.


**Returns:**
Results dictionary. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-stix-export"></a>

## $lib.stix.export

A Storm Library for exporting to STIX version 2.1 CS02.


<a id="stormlibs-lib-stix-export-bundle"></a>

### $lib.stix.export.bundle(config=(null))

Return a new empty STIX bundle.

The config argument maps synapse forms to stix types and allows you to specify
how to resolve STIX properties and relationships.  The config expects to following format::

    {
        "maxsize": 10000,

        "forms": {
            <formname>: {
                "default": <stixtype0>,
                "stix": {
                    <stixtype0>: {
                        "props": {
                            <stix_prop_name>: <storm_with_return>,
                            ...
                        },
                        "rels": (
                            ( <relname>, <target_stixtype>, <storm> ),
                            ...
                        ),
                        "revs": (
                            ( <revname>, <source_stixtype>, <storm> ),
                            ...
                        )
                    },
                    <stixtype1>: ...
                },
            },
        },
    },

For example, the default config includes the following entry to map entity:campaign nodes to stix campaigns::

    { "forms": {
        "entity:campaign": {
            "default": "campaign",
            "stix": {
                "campaign": {
                    "props": {
                        "name": "{+:name return(:name)} return($node.repr())",
                        "description": "+:desc return(:desc)",
                        "objective": "-(supported)> entity:goal +:name return(:name)",
                        "created": "return($lib.stix.export.timestamp(.created))",
                        "modified": "return($lib.stix.export.timestamp(.updated))",
                    },
                    "rels": (
                        ("attributed-to", "threat-actor", ":actor -> risk:threat"),
                        ("attributed-to", "threat-actor", ":actor -> ou:org"),
                        ("originates-from", "location", ":actor -> ou:org -> geo:place"),
                        ("targets", "identity", "-> risk:attack:activity -(targeted)> ou:org"),
                        ("targets", "identity", "-> risk:attack:activity -(targeted)> ps:person"),
                    ),
                },
            },
    }},

You may also specify pivots on a per form+stixtype basis to automate pivoting to additional nodes
to include in the bundle::

    {"forms": {
        "inet:fqdn":
            ...
            "domain-name": {
                ...
                "pivots": [
                    {"storm": "-> inet:dns:a -> inet:ip", "stixtype": "ipv4-addr"}
                ]
            {
        }
    }

Note:
    The default config is an evolving set of mappings.  If you need to guarantee stable output please
    specify a config.


**Args:**

- `config` (`dict`): The STIX bundle export config to use.


**Returns:**
A new ``stix:bundle`` instance. The return type is [`stix:bundle`](stormtypes_prims.md#stormprims-stix-bundle-f527).

<a id="stormlibs-lib-stix-export-config"></a>

### $lib.stix.export.config()

Construct a default STIX bundle export config.

**Returns:**
A default STIX bundle export config. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-stix-export-timestamp"></a>

### $lib.stix.export.timestamp(tick)

Format an epoch microseconds timestamp for use in STIX output.

**Args:**

- `tick` (`time`): The epoch microseconds timestamp.


**Returns:**
A STIX formatted timestamp string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-stix-import"></a>

## $lib.stix.import

A Storm Library for importing Stix Version 2.1 data.

The default ingest config maps reporter-specific STIX Domain Objects (SDOs) to
reporter-scoped Synapse forms (risk:threat, it:software, entity:campaign,
risk:mitigation, meta:technique). Each SDO uses the bundle id as a gutor $salt so
that the same bundle can be ingested multiple times idempotently (same bundle ID +
name produces the same GUID on every ingest). Entities with the same name that
appear across different bundles will share a node via the gutor property-based
deconfliction fallback; an analyst can separate them using the :resolved property
when needed.

STIX Cyber Observables (SCOs: inet:ip, inet:fqdn, inet:url, file:bytes, geo:place)
are globally deconflicted without a salt, since they represent shared infrastructure
facts rather than reporter-specific assessments.

The optional config["reporter"] key provides a reporter name string that is applied
to each reporter-scoped node via :reporter:name when supplied. To recover the
pre-3.x globally-deconflicted behavior, pass a fully customized config dict.


<a id="stormlibs-lib-stix-import-config"></a>

### $lib.stix.import.config()

Return an editable copy of the default STIX ingest config.

The returned dict may be modified and passed back to ``ingest()`` to override
individual object handlers or add a ``reporter`` name. The ``reporter`` key,
when set to a non-null string, is threaded into every Storm snippet as
``$reporter`` and applied to reporter-scoped nodes via ``:reporter:name ?=``.


**Returns:**
A copy of the default STIX ingest configuration. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-stix-import-ingest"></a>

### $lib.stix.import.ingest(bundle, config=(null))

Import nodes from a STIX bundle.

Each STIX Domain Object is mapped to a reporter-scoped Synapse form and
deconflicted per-bundle via a gutor $salt derived from the bundle id. The
optional ``config`` dict may override individual handler Storm snippets or
supply a ``reporter`` string to populate ``:reporter:name`` on created nodes.


**Args:**

- `bundle` (`dict`): The STIX bundle to ingest.
- `config` (`dict`): An optional STIX ingest configuration. Supports an optional "reporter" key (string) whose value is applied as :reporter:name on all reporter-scoped nodes.


**Yields:**
Yields nodes. The return type is [`node`](stormtypes_prims.md#stormprims-node-f527).

<a id="stormlibs-lib-storm"></a>

## $lib.storm

A Storm library for evaluating dynamic storm expressions.


<a id="stormlibs-lib-storm-eval"></a>

### $lib.storm.eval(text, cast=(null))

Evaluate a Storm runtime value and optionally cast/coerce it.

Note:
    If Storm logging is enabled, the expression being evaluated will be logged
    separately.


**Args:**

- `text` (`str`): A storm expression string.
- `cast` (`str`): A type to cast the result to.


**Returns:**
The value of the expression and optional cast. The return type is `any`.

<a id="stormlibs-lib-storm-run"></a>

### $lib.storm.run(query, opts=(null))

Run a Storm query and yield the messages output by the Storm interpreter.

Note:
    If Storm logging is enabled, the query being run will be logged separately.


**Args:**

- `query` (`str`): A Storm query string.
- `opts` (`dict`): Storm options dictionary.


**Yields:**
The output messages from the Storm runtime. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-tabular"></a>

## $lib.tabular

A Storm Library for creating printable tables.


<a id="stormlibs-lib-tabular-printer"></a>

### $lib.tabular.printer(conf)

Construct a new printer.

Examples:
    Create a simple table using the default separators::

        $conf = ({
            "columns": [
                {"name": "Year", "width": 4},
                {"name": "Author", "width": 20},
                {"name": "Title", "width": 12},
            ]
        })

        $printer = $lib.tabular.printer($conf)

        $lib.print($printer.header())

        for ($year, $author, $title, $publisher) in $data {
            $lib.print($printer.row(($year, $author, $title))
        }

    Create a configuration with custom separators and column options::

        $conf = ({
            "separators": {
                "row:outline": true,
                "column:outline": true,
                "header:row": "#",
                "data:row": "*",
                "column": "+",
            },
            "columns": [
                {"name": "Year", "width": 4, "justify": "right"},
                {"name": "Author", "width": 20, "justify": "center"},
                {"name": "Title", "width": 12, "overflow": "wrap"},
            ]
        })

        $printer = $lib.tabular.printer($conf)


**Args:**

- `conf` (`dict`): The table configuration dictionary.


**Returns:**
The newly constructed tabular:printer. The return type is [`tabular:printer`](stormtypes_prims.md#stormprims-tabular-printer-f527).

<a id="stormlibs-lib-tabular-schema"></a>

### $lib.tabular.schema()

Get a copy of the table configuration schema.

Examples:
    Print a human-readable version of the schema::

        $schema = $lib.tabular.schema()
        $lib.print($lib.yaml.save($schema))


**Returns:**
The table configuration schema. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-tags"></a>

## $lib.tags

Storm utility functions for tags.


<a id="stormlibs-lib-tags-prefix"></a>

### $lib.tags.prefix(names, prefix, ispart=(false))

Normalize and prefix a list of syn:tag:part values so they can be applied.

Examples:
    Add tag prefixes and then use them to tag nodes::

        $tags = $lib.tags.prefix($result.tags, vtx.visi)
        { for $tag in $tags { [ +#$tag ] } }



**Args:**

- `names` (`list`): A list of syn:tag:part values to normalize and prefix. If ``(null)``, this is a no-op and an empty list is returned.
- `prefix` (`str`): The string prefix to add to the syn:tag:part values.
- `ispart` (`boolean`): Whether the names have already been normalized. Normalization will be skipped if set to true.


**Returns:**
A list of normalized and prefixed syn:tag values. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-task"></a>

## $lib.task

A Storm Library for interacting with tasks on a Cortex and its mirrors.


<a id="stormlibs-lib-task-kill"></a>

### $lib.task.kill(prefix)

Stop a running task on the Cortex or a mirror.

**Args:**

- `prefix` (`str`): The prefix of the task to stop. Tasks will only be stopped if there is a single prefix match.


**Returns:**
True if the task was cancelled, False otherwise. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-task-list"></a>

### $lib.task.list()

List tasks the current user can access on the Cortex and its mirrors.

**Yields:**
Task definitions. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-telepath"></a>

## $lib.telepath

A Storm Library for making Telepath connections to remote services.


<a id="stormlibs-lib-telepath-open"></a>

### $lib.telepath.open(url)

Open and return a Telepath RPC proxy.

**Args:**

- `url` (`str`): The Telepath URL to connect to.


**Returns:**
A object representing a Telepath Proxy. The return type is [`telepath:proxy`](stormtypes_prims.md#stormprims-telepath-proxy-f527).

<a id="stormlibs-lib-time"></a>

## $lib.time

A Storm Library for interacting with timestamps.


<a id="stormlibs-lib-time-day"></a>

### $lib.time.day(tick)

Returns the day part of a time value.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The day part of the time expression. The return type is `int`.

<a id="stormlibs-lib-time-dayofmonth"></a>

### $lib.time.dayofmonth(tick)

Returns the index (beginning with 0) of the day within the month.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The index of the day within month. The return type is `int`.

<a id="stormlibs-lib-time-dayofweek"></a>

### $lib.time.dayofweek(tick)

Returns the index (beginning with monday as 0) of the day within the week.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The index of the day within week. The return type is `int`.

<a id="stormlibs-lib-time-dayofyear"></a>

### $lib.time.dayofyear(tick)

Returns the index (beginning with 0) of the day within the year.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The index of the day within year. The return type is `int`.

<a id="stormlibs-lib-time-format"></a>

### $lib.time.format(valu, format)

Format a Synapse timestamp into a string value using ``datetime.strftime()``.

Examples:
    Format a timestamp into a string::

        storm> $now=$lib.time.now() $str=$lib.time.format($now, '%A %d, %B %Y') $lib.print($str)

        Tuesday 14, July 2020

    Format a timestamp into a string using included format string::

        storm> $now=$lib.time.now() $str=$lib.time.format($now, $lib.time.formats.iso8601) $lib.print($str)

        2025-10-02T09:34:00Z

**Args:**

- `valu` (`int`): A timestamp in epoch microseconds.
- `format` (`str`): The strftime format string.


**Returns:**
The formatted time string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-time-formats-iso8601"></a>

### $lib.time.formats.iso8601

ISO8601 time format string in UTC timezone (Z).

**Returns:**
The type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-time-formats-iso8601us"></a>

### $lib.time.formats.iso8601us

ISO8601 time format string (with microseconds) in UTC timezone (Z).

**Returns:**
The type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-time-formats-legacy"></a>

### $lib.time.formats.legacy

Legacy time format string.

**Returns:**
The type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-time-formats-rfc2822"></a>

### $lib.time.formats.rfc2822

RFC 2822 time format string in UTC timezone (Z).

**Returns:**
The type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-time-fromunix"></a>

### $lib.time.fromunix(secs)

Normalize a timestamp from a unix epoch time in seconds to microseconds.

Examples:
    Convert a timestamp from seconds to micros and format it::

        storm> $seconds=1594684800 $micros=$lib.time.fromunix($seconds)
             $str=$lib.time.format($micros, '%A %d, %B %Y') $lib.print($str)

        Tuesday 14, July 2020

**Args:**

- `secs` (`int`): Unix epoch time in seconds.


**Returns:**
The normalized time in microseconds. The return type is `int`.

<a id="stormlibs-lib-time-hour"></a>

### $lib.time.hour(tick)

Returns the hour part of a time value.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The hour part of the time expression. The return type is `int`.

<a id="stormlibs-lib-time-minute"></a>

### $lib.time.minute(tick)

Returns the minute part of a time value.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The minute part of the time expression. The return type is `int`.

<a id="stormlibs-lib-time-month"></a>

### $lib.time.month(tick)

Returns the month part of a time value.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The month part of the time expression. The return type is `int`.

<a id="stormlibs-lib-time-monthofyear"></a>

### $lib.time.monthofyear(tick)

Returns the index (beginning with 0) of the month within the year.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The index of the month within year. The return type is `int`.

<a id="stormlibs-lib-time-now"></a>

### $lib.time.now()

Get the current epoch time in microseconds.

**Returns:**
Epoch time in microseconds. The return type is `int`.

<a id="stormlibs-lib-time-parse"></a>

### $lib.time.parse(valu, format, errok=(false))

Parse a timestamp string using ``datetime.strptime()`` into an epoch timestamp.

Examples:
    Parse a string as for its month/day/year value into a timestamp::

        storm> $s='06/01/2020' $ts=$lib.time.parse($s, '%m/%d/%Y') $lib.print($ts)

        1590969600000000

**Args:**

- `valu` (`str`): The timestamp string to parse.
- `format` (`str`): The format string to use for parsing.
- `errok` (`boolean`): If set, parsing errors will return ``(null)`` instead of raising an exception.


**Returns:**
The epoch timestamp for the string. The return type is `int`.

<a id="stormlibs-lib-time-second"></a>

### $lib.time.second(tick)

Returns the second part of a time value.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The second part of the time expression. The return type is `int`.

<a id="stormlibs-lib-time-sleep"></a>

### $lib.time.sleep(valu)

Pause the processing of data in the storm query.


**Args:**

- `valu` (`int`): The number of seconds to pause for.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-time-ticker"></a>

### $lib.time.ticker(tick, count=(null))

Periodically pause the processing of data in the storm query.


**Args:**

- `tick` (`int`): The amount of time to wait between each tick, in seconds.
- `count` (`int`): The number of times to pause the query before exiting the loop. This defaults to None and will yield forever if not set.


**Yields:**
This yields the current tick count after each time it wakes up. The return type is `int`.

<a id="stormlibs-lib-time-toUTC"></a>

### $lib.time.toUTC(tick, timezone)

Adjust an epoch microseconds timestamp to UTC from the given timezone.


**Args:**

- `tick` (`time`): A time value.
- `timezone` (`str`): A timezone name. See python pytz docs for options.


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-time-year"></a>

### $lib.time.year(tick)

Returns the year part of a time value.


**Args:**

- `tick` (`time`): A time value.


**Returns:**
The year part of the time expression. The return type is `int`.

<a id="stormlibs-lib-trigger"></a>

## $lib.trigger

A Storm Library for interacting with Triggers in the Cortex.


<a id="stormlibs-lib-trigger-add"></a>

### $lib.trigger.add(tdef)

Add a Trigger to the Cortex.

**Args:**

- `tdef` (`dict`): A Trigger definition.


**Returns:**
The new trigger. The return type is [`trigger`](stormtypes_prims.md#stormprims-trigger-f527).

<a id="stormlibs-lib-trigger-del"></a>

### $lib.trigger.del(prefix)

Delete a Trigger from the Cortex.

**Args:**

- `prefix` (`str`): A prefix to match in order to identify a trigger to delete. Only a single matching prefix will be deleted.


**Returns:**
The iden of the deleted trigger which matched the prefix. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-trigger-get"></a>

### $lib.trigger.get(iden)

Get a Trigger in the Cortex.

**Args:**

- `iden` (`str`): The iden of the Trigger to get.


**Returns:**
The requested ``trigger`` object. The return type is [`trigger`](stormtypes_prims.md#stormprims-trigger-f527).

<a id="stormlibs-lib-trigger-list"></a>

### $lib.trigger.list(all=(false))

Get a list of Triggers in the current view or every view.

**Args:**

- `all` (`boolean`): Get a list of all the readable Triggers in every readable View.


**Returns:**
A list of ``trigger`` objects the user is allowed to access. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-trigger-mod"></a>

### $lib.trigger.mod(prefix, edits)

Modify an existing Trigger in the Cortex.

**Args:**

- `prefix` (`str`): A prefix to match in order to identify a trigger to modify. Only a single matching prefix will be modified.
- `edits` (`dict`): A dictionary of properties and their values to update on the Trigger.


**Returns:**
The iden of the modified Trigger The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-utils"></a>

## $lib.utils

A Storm Library with various utility functions.


<a id="stormlibs-lib-utils-todo"></a>

### $lib.utils.todo(_todoname, *args, **kwargs)

Create a todo tuple of (name, args, kwargs).


**Args:**

- `_todoname` (`str`): The todo name.
- `*args` (`any`): Positional arguments for the todo.
- `**kwargs` (`any`): Keyword arguments for the todo.


**Returns:**
A todo tuple of (name, args, kwargs). The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-utils-type"></a>

### $lib.utils.type(valu)

Get the type of the argument value.

**Args:**

- `valu` (`any`): Value to inspect.


**Returns:**
The type of the argument. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-vault"></a>

## $lib.vault

A Storm Library for interacting with vaults.


<a id="stormlibs-lib-vault-add"></a>

### $lib.vault.add(name, vtype, scope, owner, secrets, configs)

Create a new vault.

**Args:**

- `name` (`str`): The name of the new vault.
- `vtype` (`str`): The type of this vault.
- `scope` (`str`): Scope for this vault. One of "user", "role", "global", or ``(null)`` for unscoped vaults.
- `owner` (`str`): User/role iden for this vault if scope is "user" or "role". None for "global" scope vaults.
- `secrets` (`dict`): The initial secret data to store in this vault.
- `configs` (`dict`): The initial config data to store in this vault.


**Returns:**
Iden of the newly created vault. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-vault-byname"></a>

### $lib.vault.byname(name)

Get a vault by name.

**Args:**

- `name` (`str`): 
                            The name of the vault to retrieve.  If user only has
                            PERM_READ, the secrets data will not be returned.  If the
                            user has PERM_EDIT or higher, secrets data will be included
                            in the vault.
                       


**Returns:**
The requested vault. The return type is [`vault`](stormtypes_prims.md#stormprims-vault-f527).

<a id="stormlibs-lib-vault-bytype"></a>

### $lib.vault.bytype(vtype, scope=(null))

Get a vault for a specified vault type.

**Args:**

- `vtype` (`str`): The vault type to retrieved.
- `scope` (`str`): The scope for the specified type. If ``(null)``, then getByType will search.


**Returns:**
Vault or ``(null)`` if the vault could not be retrieved. The return type is [`vault`](stormtypes_prims.md#stormprims-vault-f527).

<a id="stormlibs-lib-vault-get"></a>

### $lib.vault.get(iden)

Get a vault by iden.

**Args:**

- `iden` (`str`): 
                            The iden of the vault to retrieve.  If user only has
                            PERM_READ, the secrets data will not be returned.  If the
                            user has PERM_EDIT or higher, secrets data will be included
                            in the vault.
                       


**Returns:**
The requested vault. The return type is [`vault`](stormtypes_prims.md#stormprims-vault-f527).

<a id="stormlibs-lib-vault-list"></a>

### $lib.vault.list()

List vaults accessible to the current user.

**Yields:**
Yields vaults. The return type is [`vault`](stormtypes_prims.md#stormprims-vault-f527).

<a id="stormlibs-lib-vault-print"></a>

### $lib.vault.print(vault)

Print the details of the specified vault.

**Args:**

- `vault` (`dict`): The vault to print.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-vault-update"></a>

### $lib.vault.update(vdef)

Atomically replace a vault with the given definition.

Notes:
    Requires edit permission on the vault, or admin to change its
    permissions.


**Args:**

- `vdef` (`dict`): The full vault definition to write.


**Returns:**
The updated vault definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-vault-type"></a>

## $lib.vault.type

A Storm Library for managing vault types.


<a id="stormlibs-lib-vault-type-add"></a>

### $lib.vault.type.add(name, version, schema=(null), migration=(null))

Register (or version bump) a vault type and its data JSON schema.

Notes:
    Vaults of this type are validated against the provided schema,
    which is applied to the whole vault definition (its configs,
    secrets, name, and so on). The version must increment on each
    change; a version bump migrates existing vaults via the optional
    migration callback, which is a Storm query that mutates the
    $configs and $secrets variables in place. Requires admin.


**Args:**

- `name` (`str`): The vault type name.
- `version` (`int`): The vault type version.
- `schema` (`dict`): JSON schema for the vault definition, or null.
- `migration` (`str`): Storm migration callback, or null.


**Returns:**
The registered vault type. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-vault-type-del"></a>

### $lib.vault.type.del(name)

Remove a registered vault type. Requires admin.

**Args:**

- `name` (`str`): The vault type name.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-vault-type-get"></a>

### $lib.vault.type.get(name, version=(null))

Get a registered vault type definition.

**Args:**

- `name` (`str`): The vault type name.
- `version` (`int`): A specific version to get. Defaults to the latest version.


**Returns:**
The vault type definition, or null. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-vault-type-list"></a>

### $lib.vault.type.list()

List all registered vault type definitions (latest version of each).

**Returns:**
A list of vault type definitions. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-vault-type-versions"></a>

### $lib.vault.type.versions(name)

List all registered versions of a vault type, oldest first.

**Args:**

- `name` (`str`): The vault type name.


**Returns:**
A list of vault type definitions, oldest version first. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-version"></a>

## $lib.version

A Storm Library for interacting with version information.


<a id="stormlibs-lib-version-commit"></a>

### $lib.version.commit

The synapse commit hash for the local Cortex.

**Returns:**
The commit hash. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-version-matches"></a>

### $lib.version.matches(vertup, reqstr)

Check if the given version string or triple meets the requirements string.

Examples:
    Check if the synapse version is in a range::

        $synver = $lib.version.synapse
        if $lib.version.matches($synver, ">=2.9.0") {
            $dostuff()
        }


**Args:**

- `vertup`: A version string or list of version integers. The input type may be one of the following: `str`, `list`.
- `reqstr` (`str`): The version string to compare against.


**Returns:**
True if the version meets the requirements, False otherwise. The return type is [`boolean`](stormtypes_prims.md#stormprims-boolean-f527).

<a id="stormlibs-lib-version-synapse"></a>

### $lib.version.synapse

The synapse version string for the local Cortex.

**Returns:**
The type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-vertex"></a>

## $lib.vertex

A Storm Library for interacting with the Vertex Hub.


<a id="stormlibs-lib-vertex-deployment"></a>

### $lib.vertex.deployment

This deployment's Vertex Hub registration info.

Requires admin privileges.

**Returns:**
A dict with the deployment ``iden`` and ``pubkey``, or null if not registered. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-vertex-register"></a>

### $lib.vertex.register(email, name=(null), reset=(false))

Register this deployment with the Vertex Hub.

Each registration generates and stores a fresh RSA keypair as this
deployment's cryptographic identity. The returned deployment iden is
used to authenticate subsequent Vertex Hub requests. The email address
must belong to an existing Vertex Hub account.

If this deployment is already registered, this raises unless ``reset``
is set. Passing ``reset`` creates a NEW deployment which may have
different available power-ups.

**Args:**

- `email` (`str`): The email address of the Vertex Hub account to register under.
- `name` (`str`): An optional name for the deployment. The Vertex Hub generates a default if not provided.
- `reset` (`boolean`): Re-register even if already registered, creating a new deployment.


**Returns:**
The new deployment iden, or null if no Vertex Hub account exists for the email. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).

<a id="stormlibs-lib-vertex-packages"></a>

## $lib.vertex.packages

A Storm Library for retrieving packages from the Vertex Hub.


<a id="stormlibs-lib-vertex-packages-get"></a>

### $lib.vertex.packages.get(name, version=(null))

Retrieve a package definition from the Vertex Hub without installing it.

**Args:**

- `name` (`str`): The name of the package.
- `version` (`str`): The version to retrieve. Defaults to the latest version.


**Returns:**
The package definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-vertex-packages-install"></a>

### $lib.vertex.packages.install(name, version=(null))

Install a package from the Vertex Hub.

Any files the package declares are downloaded into the Cortex Axon before the
package is added, so a package is never installed without its files.

**Args:**

- `name` (`str`): The name of the package to install.
- `version` (`str`): The version to install. Defaults to the latest version.


**Returns:**
The installed package definition. The return type is [`dict`](stormtypes_prims.md#stormprims-dict-f527).

<a id="stormlibs-lib-vertex-packages-list"></a>

### $lib.vertex.packages.list()

List the packages available to this deployment.

**Returns:**
A list of available package info dictionaries. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-vertex-packages-versions"></a>

### $lib.vertex.packages.versions(name, match=(null))

List the available versions of a package.

**Args:**

- `name` (`str`): The name of the package.
- `match` (`str`): An optional version prefix used to filter the results.


**Returns:**
A list of available version strings. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-view"></a>

## $lib.view

A Storm Library for interacting with Views in the Cortex.


<a id="stormlibs-lib-view-add"></a>

### $lib.view.add(layers, name=(null))

Add a View to the Cortex.

**Args:**

- `layers` (`list`): A list of layer idens which make up the view.
- `name` (`str`): The name of the view.


**Returns:**
A ``view`` object representing the new View. The return type is [`view`](stormtypes_prims.md#stormprims-view-f527).

<a id="stormlibs-lib-view-del"></a>

### $lib.view.del(iden)

Delete a View from the Cortex.

**Args:**

- `iden` (`str`): The iden of the View to delete.


**Returns:**
The return type is `null`.

<a id="stormlibs-lib-view-get"></a>

### $lib.view.get(iden=(null))

Get a View from the Cortex. Raises ``NoSuchView`` if no such view exists or the user cannot read it.

**Args:**

- `iden` (`str`): The iden of the View to get. If not specified, returns the current View.


**Returns:**
The storm view object. The return type is [`view`](stormtypes_prims.md#stormprims-view-f527).

<a id="stormlibs-lib-view-list"></a>

### $lib.view.list(deporder=(false))

List the Views in the Cortex.

**Args:**

- `deporder` (`boolean`): Return the lists in bottom-up dependency order.


**Returns:**
List of ``view`` objects. The return type is [`list`](stormtypes_prims.md#stormprims-list-f527).

<a id="stormlibs-lib-xml"></a>

## $lib.xml

A Storm library for parsing XML.


<a id="stormlibs-lib-xml-parse"></a>

### $lib.xml.parse(valu)

Parse an XML string into an xml:element tree.

**Args:**

- `valu` (`str`): The XML string to parse into an xml:element tree.


**Returns:**
An xml:element for the root node of the XML tree. The return type is [`xml:element`](stormtypes_prims.md#stormprims-xml-element-f527).

<a id="stormlibs-lib-yaml"></a>

## $lib.yaml

A Storm Library for saving/loading YAML data.


<a id="stormlibs-lib-yaml-load"></a>

### $lib.yaml.load(valu)

Decode a YAML string/bytes into an object.

**Args:**

- `valu` (`str`): The string to decode.


**Returns:**
The decoded primitive object. The return type is `prim`.

<a id="stormlibs-lib-yaml-save"></a>

### $lib.yaml.save(valu, sort_keys=(true))

Encode data as a YAML string.

**Args:**

- `valu` (`prim`): The object to encode.
- `sort_keys` (`boolean`): Sort object keys.


**Returns:**
A YAML string. The return type is [`str`](stormtypes_prims.md#stormprims-str-f527).
