
<a id="stormtypes-prim-header"></a>

# Storm Types


Storm Objects are used as view objects for manipulating data in the Storm Runtime and in the Cortex itself.


<a id="stormprims-auth-gate-f527"></a>

## auth:gate

Implements the Storm API for an AuthGate.


<a id="stormprims-auth-gate-iden"></a>

### iden

The iden of the AuthGate.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-auth-gate-roles"></a>

### roles

The role idens which are a member of the Authgate.

**Returns:**
The type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-gate-type"></a>

### type

The type of the AuthGate.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-auth-gate-users"></a>

### users

The user idens which are a member of the Authgate.

**Returns:**
The type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-role-f527"></a>

## auth:role

Implements the Storm API for a Role.


<a id="stormprims-auth-role-addRule"></a>

### addRule(rule, gateiden=(null), indx=(null))

Add a rule to the Role

**Args:**

- `rule` (`list`): The rule tuple to added to the Role.
- `gateiden` (`str`): The gate iden used for the rule.
- `indx` (`int`): The position of the rule as a 0 based index.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-role-delRule"></a>

### delRule(rule, gateiden=(null))

Remove a rule from the Role.

**Args:**

- `rule` (`list`): The rule tuple to removed from the Role.
- `gateiden` (`str`): The gate iden used for the rule.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-role-gates"></a>

### gates()

Return a list of auth gates that the role has rules for.

**Returns:**
A list of ``auth:gates`` that the role has rules for. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-role-get"></a>

### get(name)

Get a arbitrary property from the Role definition.

**Args:**

- `name` (`str`): The name of the property to return.


**Returns:**
The requested value. The return type is `prim`.

<a id="stormprims-auth-role-getRules"></a>

### getRules(gateiden=(null))

Get the rules for the role and optional auth gate.

**Args:**

- `gateiden` (`str`): The gate iden used for the rules.


**Returns:**
A list of rules. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-role-iden"></a>

### iden

The Role iden.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-auth-role-name"></a>

### name

A role's name. This can also be used to set the role name.

Example:
        Change a role's name::

            $role=$lib.auth.roles.byname(analyst) $role.name=superheroes


**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-auth-role-popRule"></a>

### popRule(indx, gateiden=(null))

Remove a rule by index from the Role.

**Args:**

- `indx` (`int`): The index of the rule to remove.
- `gateiden` (`str`): The gate iden used for the rule.


**Returns:**
The rule which was removed. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-role-setRules"></a>

### setRules(rules, gateiden=(null))

Replace the rules on the Role with new rules.

**Args:**

- `rules` (`list`): A list of rules to set on the Role.
- `gateiden` (`str`): The gate iden used for the rules.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-f527"></a>

## auth:user

Implements the Storm API for a User.


<a id="stormprims-auth-user-addRule"></a>

### addRule(rule, gateiden=(null), indx=(null))

Add a rule to the User.

**Args:**

- `rule` (`list`): The rule tuple to add to the User.
- `gateiden` (`str`): The gate iden used for the rule.
- `indx` (`int`): The position of the rule as a 0 based index.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-allowed"></a>

### allowed(permname, gateiden=(null), default=(null))

Check if the user has a given permission.

Notes:
    The permission may be specified as either a dotted string (foo.bar.baz) or a list of
    permission parts (foo, bar, baz).

    When no default is specified, the permission's registered default value is used. This is
    the same value used when the permission is enforced, so this API always agrees with
    enforcement.


**Args:**

- `permname`: The permission to check, as either a dotted string or a list of permission parts. The input type may be one of the following: `str`, `list`.
- `gateiden` (`str`): The authgate iden.
- `default` (`boolean`): The value to use when no rule matches. Defaults to the registered default for the permission.


**Returns:**
True if the rule is allowed, False otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-auth-user-delApiKey"></a>

### delApiKey(iden)

Delete an existing API key.

**Args:**

- `iden` (`str`): The iden of the API key.


**Returns:**
True when the key was deleted. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-auth-user-delRule"></a>

### delRule(rule, gateiden=(null))

Remove a rule from the User.

**Args:**

- `rule` (`list`): The rule tuple to removed from the User.
- `gateiden` (`str`): The gate iden used for the rule.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-email"></a>

### email

A user's email. This can also be used to set the user's email.

Example:
        Change a user's email address::

            $user=$lib.auth.users.byname(bob) $user.email="robert@bobcorp.net"


**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-auth-user-gates"></a>

### gates()

Return a list of auth gates that the user has rules for.

**Returns:**
A list of ``auth:gates`` that the user has rules for. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-user-genApiKey"></a>

### genApiKey(name, duration=(null))

Generate a new API key for the user.

        Notes:
            The secret API key returned by this function cannot be accessed again.
        

**Args:**

- `name` (`str`): The name of the API key.
- `duration` (`int`): Duration of time for the API key to be valid, in microseconds.


**Returns:**
A list, containing the secret API key and a dictionary containing metadata about the key. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-user-get"></a>

### get(name)

Get a arbitrary property from the User definition.

**Args:**

- `name` (`str`): The name of the property to return.


**Returns:**
The requested value. The return type is `prim`.

<a id="stormprims-auth-user-getAllowedReason"></a>

### getAllowedReason(permname, gateiden=(null), default=(null))

Return an allowed status and reason for the given perm.

Notes:
    The permission may be specified as either a dotted string (foo.bar.baz) or a list of
    permission parts (foo, bar, baz).

    When no default is specified, the permission's registered default value is used. This is
    the same value used when the permission is enforced, so this API always agrees with
    enforcement.


**Args:**

- `permname`: The permission to check, as either a dotted string or a list of permission parts. The input type may be one of the following: `str`, `list`.
- `gateiden` (`str`): The authgate iden.
- `default` (`boolean`): The value to use when no rule matches. Defaults to the registered default for the permission.


**Returns:**
An (allowed, reason) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-user-getApiKey"></a>

### getApiKey(iden)

Get information about a user's existing API key.

**Args:**

- `iden` (`str`): The iden of the API key.


**Returns:**
A dictionary containing metadata about the key. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-auth-user-getRules"></a>

### getRules(gateiden=(null))

Get the rules for the user and optional auth gate.

**Args:**

- `gateiden` (`str`): The gate iden used for the rules.


**Returns:**
A list of rules. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-user-grant"></a>

### grant(iden, indx=(null))

Grant a Role to the User.

**Args:**

- `iden` (`str`): The iden of the Role.
- `indx` (`int`): The position of the Role as a 0 based index.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-iden"></a>

### iden

The User iden.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-auth-user-listApiKeys"></a>

### listApiKeys()

Get information about all the API keys the user has.

**Returns:**
A list of dictionaries containing metadata about each key. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-user-modApiKey"></a>

### modApiKey(iden, name, valu)

Modify metadata about an existing API key.

**Args:**

- `iden` (`str`): The iden of the API key.
- `name` (`str`): The name of the valu to update.
- `valu` (`any`): The new value of the API key.


**Returns:**
An updated dictionary with metadata about the key. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-auth-user-name"></a>

### name

A user's name. This can also be used to set a user's name.

Example:
        Change a user's name::

            $user=$lib.auth.users.byname(bob) $user.name=robert


**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-auth-user-popRule"></a>

### popRule(indx, gateiden=(null))

Remove a rule by index from the User.

**Args:**

- `indx` (`int`): The index of the rule to remove.
- `gateiden` (`str`): The gate iden used for the rule.


**Returns:**
The rule which was removed. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-user-profile"></a>

### profile

A user profile dictionary. This can be used as an application level key-value store.

Example:
    Set a value::

        $user=$lib.auth.users.byname(bob) $user.profile.somekey="somevalue"

    Get a value::

        $user=$lib.auth.users.byname(bob) $value = $user.profile.somekey


**Returns:**
The return type is [`auth:user:profile`](#stormprims-auth-user-profile-f527).

<a id="stormprims-auth-user-revoke"></a>

### revoke(iden)

Remove a Role from the User

**Args:**

- `iden` (`str`): The iden of the Role.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-roles"></a>

### roles

Get the Roles for the User.

**Returns:**
A list of ``auth:roles`` which the user is a member of. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-auth-user-setAdmin"></a>

### setAdmin(admin, gateiden=(null))

Set the Admin flag for the user.

**Args:**

- `admin` (`boolean`): True to make the User an admin, false to remove their admin status.
- `gateiden` (`str`): The gate iden used for the operation.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-setArchived"></a>

### setArchived(archived)

Set the archived status for a user.

Notes:
    Setting a user as "archived" will also lock the user.
    Removing a users "archived" status will not unlock the user.


**Args:**

- `archived` (`boolean`): True to archive the user, false to unarchive them.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-setEmail"></a>

### setEmail(email)

Set the email address of the User.

**Args:**

- `email` (`str`): The email address to set for the User.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-setLocked"></a>

### setLocked(locked)

Set the locked status for a user.

**Args:**

- `locked` (`boolean`): True to lock the user, false to unlock them.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-setPasswd"></a>

### setPasswd(passwd)

Set the Users password.

**Args:**

- `passwd` (`str`): The new password for the user. This is best passed into the runtime as a variable.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-setRoles"></a>

### setRoles(idens)

Replace all the Roles of the User with a new list of roles.

Notes:
    The roleiden for the "all" role must be present in the new list of roles. This replaces all existing roles
    that the user has with the new roles.


**Args:**

- `idens` (`list`): The idens of the Roles to set on the User.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-setRules"></a>

### setRules(rules, gateiden=(null))

Replace the rules on the User with new rules.

**Args:**

- `rules` (`list`): A list of rule tuples.
- `gateiden` (`str`): The gate iden used for the rules.


**Returns:**
The return type is `null`.

<a id="stormprims-auth-user-vars"></a>

### vars

Get a dictionary representing the user's persistent variables.

**Returns:**
The return type is [`auth:user:vars`](#stormprims-auth-user-vars-f527).

<a id="stormprims-auth-user-json-f527"></a>

## auth:user:json

Implements the Storm deref/setitem/iter convention on top of per-user JSON storage.


<a id="stormprims-auth-user-profile-f527"></a>

## auth:user:profile

The Storm deref/setitem/iter convention on top of User profile information.


<a id="stormprims-auth-user-vars-f527"></a>

## auth:user:vars

The Storm deref/setitem/iter convention on top of User vars information.


<a id="stormprims-boolean-f527"></a>

## boolean

Implements the Storm API for a boolean instance.


<a id="stormprims-bytes-f527"></a>

## bytes

Implements the Storm API for a Bytes object.


<a id="stormprims-bytes-bunzip"></a>

### bunzip()

Decompress the bytes using bzip2.

Example:
    Decompress bytes with bzip2::

        $foo = $mybytez.bunzip()

**Returns:**
Decompressed bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-bytes-bzip"></a>

### bzip()

Compress the bytes using bzip2 and return them.

Example:
    Compress bytes with bzip::

        $foo = $mybytez.bzip()

**Returns:**
The bzip2 compressed bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-bytes-decode"></a>

### decode(encoding='utf8', strict=(false))

Decode bytes to a string.

**Args:**

- `encoding` (`str`): The encoding to use.
- `strict` (`str`): If True, raise an exception on invalid values rather than replacing the character.


**Returns:**
The decoded string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-bytes-gunzip"></a>

### gunzip()

Decompress the bytes using gzip and return them.

Example:
    Decompress bytes with bzip2::

    $foo = $mybytez.gunzip()

**Returns:**
Decompressed bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-bytes-gzip"></a>

### gzip()

Compress the bytes using gzip and return them.

Example:
    Compress bytes with gzip::

        $foo = $mybytez.gzip()

**Returns:**
The gzip compressed bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-bytes-json"></a>

### json(encoding=(null), strict=(false))

Load JSON data from bytes.

Notes:
    The bytes must be UTF8, UTF16 or UTF32 encoded.

Example:
    Load bytes to a object::

        $foo = $mybytez.json()

**Args:**

- `encoding` (`str`): Specify an encoding to use.
- `strict` (`str`): If True, raise an exception on invalid string encoding rather than replacing the character.


**Returns:**
The deserialized object. The return type is `prim`.

<a id="stormprims-bytes-slice"></a>

### slice(start, end=(null))

Slice a subset of bytes from an existing bytes.

Examples:
    Slice from index to 1 to 5::

        $subbyts = $byts.slice(1,5)

    Slice from index 3 to the end of the bytes::

        $subbyts = $byts.slice(3)


**Args:**

- `start` (`int`): The starting byte index.
- `end` (`int`): The ending byte index. If not specified, slice to the end.


**Returns:**
The slice of bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-bytes-unpack"></a>

### unpack(fmt, offset=(0))

Unpack structures from bytes using python struct.unpack syntax.

Examples:
    Unpack 3 unsigned 16 bit integers in little endian format::

        ($x, $y, $z) = $byts.unpack("<HHH")


**Args:**

- `fmt` (`str`): A python struck.pack format string.
- `offset` (`int`): An offset to begin unpacking from.


**Returns:**
The unpacked primitive values. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-bytes-xor"></a>

### xor(key)

Perform an "exclusive or" bitwise operation on the bytes and another set of bytes.

Notes:
    The key bytes provided as an argument will be repeated as needed until all bytes have been
    xor'd.

    If a string is provided as the key argument, it will be utf8 encoded before being xor'd.

Examples:
    Perform an xor operation on the bytes in $encoded using the bytes in $key::

        $decoded = $encoded.xor($key)

**Args:**

- `key`: The key bytes to perform the xor operation with. The input type may be one of the following: `str`, `bytes`.


**Returns:**
The xor'd bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-cache-fixed-f527"></a>

## cache:fixed

A StormLib API instance of a Storm Fixed Cache.


<a id="stormprims-cache-fixed-clear"></a>

### clear()

Clear all items from the cache.

**Returns:**
The return type is `null`.

<a id="stormprims-cache-fixed-get"></a>

### get(key)

Get an item from the cache by key.

**Args:**

- `key` (`any`): The key to lookup.


**Returns:**
The value from the cache, or the callback query if it does not exist The return type is `any`.

<a id="stormprims-cache-fixed-pop"></a>

### pop(key)

Pop an item from the cache.

**Args:**

- `key` (`any`): The key to pop.


**Returns:**
The value from the cache, or ``(null)`` if it does not exist The return type is `any`.

<a id="stormprims-cache-fixed-put"></a>

### put(key, value)

Put an item into the cache.

**Args:**

- `key` (`any`): The key put in the cache.
- `value` (`any`): The value to assign to the key.


**Returns:**
The return type is `null`.

<a id="stormprims-cache-fixed-query"></a>

### query

Get the callback Storm query as string.

**Returns:**
The callback Storm query text. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-cmdopts-f527"></a>

## cmdopts

A dictionary like object that holds a reference to a command options namespace.
( This allows late-evaluation of command arguments rather than forcing capture )


<a id="stormprims-cronjob-f527"></a>

## cronjob

Implements the Storm api for a cronjob instance.


<a id="stormprims-cronjob-completed"></a>

### completed

True if a non-recurring Cron Job has completed.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-cronjob-created"></a>

### created

The timestamp when the Cron Job was created.

**Returns:**
The type is `int`.

<a id="stormprims-cronjob-creator"></a>

### creator

The iden of the user that created the Cron Job.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-cronjob-doc"></a>

### doc

The description of the Cron Job.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-cronjob-enabled"></a>

### enabled

Whether the Cron Job is enabled.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-cronjob-iden"></a>

### iden

The iden of the Cron Job.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-cronjob-kill"></a>

### kill()

If the job is currently running, terminate the task.

**Returns:**
A boolean value which is true if the task was terminated. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-cronjob-name"></a>

### name

The name of the Cron Job.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-cronjob-pprint"></a>

### pprint()

Get a dictionary containing user friendly strings for printing the CronJob.

**Returns:**
A dictionary containing structured data about a cronjob for display purposes. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-cronjob-storm"></a>

### storm

The Storm query the Cron Job runs.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-cronjob-user"></a>

### user

The iden of the user the Cron Job runs as.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-cronjob-view"></a>

### view

The iden of the view the Cron Job runs in.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-crypto-ecc-key-f527"></a>

## crypto:ecc:key

A Storm object representing an ECC public or private key.


<a id="stormprims-crypto-ecc-key-encode"></a>

### encode(fmt='pem')

Encode the key as PEM or DER.

**Args:**

- `fmt` (`str`): The encoding format: "pem" (returns a str) or "der" (returns bytes).


**Returns:**
The PEM encoded string or the DER encoded bytes. The return type may be one of the following: [`str`](#stormprims-str-f527), [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-crypto-ecc-key-isPrivate"></a>

### isPrivate

True if the object contains a private key and can sign, otherwise False.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-crypto-ecc-key-pubkey"></a>

### pubkey()

Return a new ``crypto:ecc:key`` containing only the public key.

This raises if the key is already a public-only key.


**Returns:**
A new ``crypto:ecc:key`` containing only the public key. The return type is [`crypto:ecc:key`](#stormprims-crypto-ecc-key-f527).

<a id="stormprims-crypto-ecc-key-sign"></a>

### sign(byts, hashalgo='sha256')

Compute the ECDSA signature for the given bytes.

This raises if the key does not contain a private key.


**Args:**

- `byts` (`bytes`): The bytes to sign.
- `hashalgo` (`str`): The hash algorithm to use (sha256, sha384, or sha512).


**Returns:**
The DER encoded ECDSA signature bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-crypto-ecc-key-verify"></a>

### verify(byts, signature, hashalgo='sha256')

Verify the ECDSA signature for the given bytes.

**Args:**

- `byts` (`bytes`): The bytes to verify.
- `signature` (`bytes`): The DER encoded signature bytes to verify.
- `hashalgo` (`str`): The hash algorithm to use (sha256, sha384, or sha512).


**Returns:**
True if the signature is valid, otherwise False. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-crypto-jwt-f527"></a>

## crypto:jwt

A JSON Web Token (JWT) to construct, sign, and verify.


<a id="stormprims-crypto-jwt-header"></a>

### header

The JOSE header of the JWT.

Header parameters (e.g. ``kid``, ``cty``) may be set while the token is being constructed. The
``alg`` and ``typ`` parameters are set by ``sign()``; a caller-set ``alg`` is always overridden by
the ``sign()`` algorithm argument. Once the token has been signed or loaded the header becomes
immutable.


**Returns:**
The JWT JOSE header. The return type is [`crypto:jwt:dict`](#stormprims-crypto-jwt-dict-f527).

<a id="stormprims-crypto-jwt-payload"></a>

### payload

The claims payload of the JWT.

While the token is being constructed, individual claims may be set (e.g. ``$token.payload.sub = "foo"``).
Once the token has been signed or loaded via ``$lib.crypto.jwt.verify()``, the payload becomes immutable.


**Returns:**
The JWT claims payload. The return type is [`crypto:jwt:dict`](#stormprims-crypto-jwt-dict-f527).

<a id="stormprims-crypto-jwt-sign"></a>

### sign(key, alg, fmt='compact')

Sign the current payload and return a JWT string.

The JOSE header is populated with the algorithm and type and the signature bytes are set. The
payload becomes immutable once the token is signed.


**Args:**

- `key`: The signing key. A PEM encoded private key (or a crypto:rsa:key / crypto:ecc:key object) for RS* / PS* / ES* algorithms, or the secret for HS* algorithms. May be a str or bytes. The input type may be one of the following: `str`, `bytes`, `crypto:rsa:key`, `crypto:ecc:key`.
- `alg` (`str`): The JWS algorithm (HS256/384/512, RS256/384/512, PS256/384/512, or ES256/384/512).
- `fmt` (`str`): The serialization: "compact" (default) or "json" (flattened JWS JSON serialization).


**Returns:**
The signed JWT string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-crypto-jwt-signature"></a>

### signature

The raw signature bytes of the token, or ``$lib.null`` if it has not been signed or verified.

**Returns:**
The type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-crypto-jwt-dict-f527"></a>

## crypto:jwt:dict

A dictionary view of JWT payload or header data which becomes immutable once the token is signed or loaded.


<a id="stormprims-crypto-rsa-key-f527"></a>

## crypto:rsa:key

A Storm object representing an RSA public or private key.


<a id="stormprims-crypto-rsa-key-encode"></a>

### encode(fmt='pem')

Encode the key as PEM or DER.

**Args:**

- `fmt` (`str`): The encoding format: "pem" (returns a str) or "der" (returns bytes).


**Returns:**
The PEM encoded string or the DER encoded bytes. The return type may be one of the following: [`str`](#stormprims-str-f527), [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-crypto-rsa-key-isPrivate"></a>

### isPrivate

True if the object contains a private key and can sign, otherwise False.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-crypto-rsa-key-pubkey"></a>

### pubkey()

Return a new ``crypto:rsa:key`` containing only the public key.

This raises if the key is already a public-only key.


**Returns:**
A new ``crypto:rsa:key`` containing only the public key. The return type is [`crypto:rsa:key`](#stormprims-crypto-rsa-key-f527).

<a id="stormprims-crypto-rsa-key-sign"></a>

### sign(byts, padding='pss', hashalgo='sha256')

Compute the RSA signature for the given bytes.

This raises if the key does not contain a private key.


**Args:**

- `byts` (`bytes`): The bytes to sign.
- `padding` (`str`): The padding scheme to use (pss or pkcs1v15).
- `hashalgo` (`str`): The hash algorithm to use (sha256, sha384, or sha512).


**Returns:**
The RSA signature bytes. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-crypto-rsa-key-verify"></a>

### verify(byts, signature, padding='pss', hashalgo='sha256')

Verify the RSA signature for the given bytes.

**Args:**

- `byts` (`bytes`): The bytes to verify.
- `signature` (`bytes`): The signature bytes to verify.
- `padding` (`str`): The padding scheme to use (pss or pkcs1v15).
- `hashalgo` (`str`): The hash algorithm to use (sha256, sha384, or sha512).


**Returns:**
True if the signature is valid, otherwise False. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-dict-f527"></a>

## dict

Implements the Storm API for a Dictionary object.


<a id="stormprims-environment-vars-f527"></a>

## environment:vars

The Storm deref/iter convention on top of environment vars information.


<a id="stormprims-global-vars-f527"></a>

## global:vars

The Storm deref/setitem/iter convention on top of global vars information.


<a id="stormprims-http-api-f527"></a>

## http:api

Extended HTTP API object.

This object represents an extended HTTP API that has been configured on the Cortex.


<a id="stormprims-http-api-authenticated"></a>

### authenticated

Boolean value indicating if the Extended HTTP API requires an authenticated user or session.

**Returns:**
The return type is [`boolean`](#stormprims-boolean-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-created"></a>

### created

The time the Extended HTTP API was created.

**Returns:**
The type is `int`.

<a id="stormprims-http-api-creator"></a>

### creator

The user that created the Extended HTTP API.

**Returns:**
The return type is [`auth:user`](#stormprims-auth-user-f527).

<a id="stormprims-http-api-desc"></a>

### desc

The description of the API instance.

**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-iden"></a>

### iden

The iden of the Extended HTTP API.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-http-api-methods"></a>

### methods

The dictionary containing the Storm code used to implement the HTTP methods.

**Returns:**
The return type is [`http:api:methods`](#stormprims-http-api-methods-f527).

<a id="stormprims-http-api-name"></a>

### name

The name of the API instance.

**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-owner"></a>

### owner

The user that runs the endpoint query logic when runas="owner".

**Returns:**
The return type is [`auth:user`](#stormprims-auth-user-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-path"></a>

### path

The path of the API instance.

This path may contain regular expression capture groups, which are used to populate
request arguments.

Note:
    The Cortex does not inspect paths in order to identify duplicates or overlapping paths.
    It is the responsibility of the Cortex administrator to configure their Extended HTTP API
    paths so that they are correct for their use cases.

Example:
    Update an API path to contain a single wildcard argument::

        $api.path = 'foo/bar/(.*)/baz'

    Update an API path to contain a two wildcard arguments with restricted character sets::

        $api.path = 'hehe/([a-z]*)/([0-9]{1-4})'


**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-perms"></a>

### perms

The permissions an authenticated user must have in order to access the HTTP API.

**Returns:**
The return type is [`http:api:perms`](#stormprims-http-api-perms-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-readonly"></a>

### readonly

Boolean value indicating if the Storm methods are executed in a readonly Storm runtime.

**Returns:**
The return type is [`boolean`](#stormprims-boolean-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-runas"></a>

### runas

String indicating whether the requests run as the owner or the authenticated user.

**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-updated"></a>

### updated

The time the Extended HTTP API was last modified.

**Returns:**
The return type is `int`.

<a id="stormprims-http-api-vars"></a>

### vars

The Storm runtime variables specific for the API instance.

**Returns:**
The return type is [`http:api:vars`](#stormprims-http-api-vars-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-view"></a>

### view

The View of the API instance. This is the view that Storm methods are executed in.

**Returns:**
The return type is [`view`](#stormprims-view-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-methods-f527"></a>

## http:api:methods

Accessor dictionary for getting and setting Extended HTTP API methods.

Notes:
    The Storm code used to run these methods will have a $request object
    injected into them. This allows the method to send data back to the
    caller when it is run.

Examples:
    Setting a simple GET method::

        $api.methods.get = ${
            $data = ({"someKey": "someValue})
            $headers = ({"someHeader": "someOtherValue"})
            $request.reply(200, headers=$headers, body=$data)
        }

    Removing a PUT method::

        $api.methods.put = $lib.undef

    Crafting a custom text response::

        $api.methods.get = ${
            // Create the body
            $data = 'some value'
            // Encode the response as bytes
            $data = $data.encode()
            // Set the headers
            $headers = ({"Content-Type": "text/plain", "Content-Length": $lib.len($data})
            $request.reply(200, headers=$headers, body=$data)
        }

    Streaming multiple chunks of data as JSON lines. This sends the code, headers and body separately::

        $api.methods.get = ${
            $request.sendcode(200)
            $request.sendheaders(({"Content-Type": "text/plain; charset=utf8"}))
            $values = ((1), (2), (3))
            for $i in $values {
                $body=`{$lib.json.save(({"value": $i}))}\n`
                $request.sendbody($body.encode())
            }
        }



<a id="stormprims-http-api-methods-delete"></a>

### delete

The DELETE request Storm code.

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-methods-get"></a>

### get

The GET request Storm code.

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-methods-head"></a>

### head

The HEAD request Storm code

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-methods-options"></a>

### options

The OPTIONS request Storm code.

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-methods-patch"></a>

### patch

The PATCH request Storm code.

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-methods-post"></a>

### post

The POST request Storm code.

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-methods-put"></a>

### put

The PUT request Storm code.

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-http-api-perms-f527"></a>

## http:api:perms

Accessor list for getting and setting http:api permissions.


<a id="stormprims-http-api-perms-append"></a>

### append(valu)

Append a permission to the list.

**Args:**

- `valu` (`any`): The permission to append to the list.


**Returns:**
The return type is `null`.

<a id="stormprims-http-api-perms-extend"></a>

### extend(valu)

Extend a list using another iterable.

**Args:**

- `valu` (`list`): A list or other iterable.


**Returns:**
The return type is `null`.

<a id="stormprims-http-api-perms-has"></a>

### has(valu)

Check it a permission is in the list.

**Args:**

- `valu` (`any`): The permission to check.


**Returns:**
True if the permission is in the list, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-http-api-perms-index"></a>

### index(valu)

Return a single permission from the list by index.

**Args:**

- `valu` (`int`): The list index value.


**Returns:**
The permission present in the list at the index position. The return type is `any`.

<a id="stormprims-http-api-perms-pop"></a>

### pop()

Pop and return the last permission in the list.

**Returns:**
The last permission from the list. The return type is `any`.

<a id="stormprims-http-api-perms-reverse"></a>

### reverse()

Reverse the order of the list in place

**Returns:**
The return type is `null`.

<a id="stormprims-http-api-perms-size"></a>

### size()

Return the length of the list.

**Returns:**
The size of the list. The return type is `int`.

<a id="stormprims-http-api-perms-slice"></a>

### slice(start, end=(null))

Get a slice of the list.

**Args:**

- `start` (`int`): The starting index.
- `end` (`int`): The ending index. If not specified, slice to the end of the list.


**Returns:**
The slice of the list. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-http-api-request-f527"></a>

## http:api:request

Extended HTTP API Request object.


<a id="stormprims-http-api-request-api"></a>

### api

The http:api object for the request.

**Returns:**
The return type is [`http:api`](#stormprims-http-api-f527).

<a id="stormprims-http-api-request-args"></a>

### args

A list of path arguments made as part of the HTTP API request.
These are the results of any capture groups defined in the Extended HTTP API path regular expression.

**Returns:**
The type is [`list`](#stormprims-list-f527).

<a id="stormprims-http-api-request-body"></a>

### body

The raw request body.

**Returns:**
The type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-http-api-request-client"></a>

### client

The remote IP of the requester.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-http-api-request-headers"></a>

### headers

The request headers.

**Returns:**
The return type is [`http:api:request:headers`](#stormprims-http-api-request-headers-f527).

<a id="stormprims-http-api-request-json"></a>

### json

The request body as json.

**Returns:**
The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-http-api-request-method"></a>

### method

The request method

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-http-api-request-params"></a>

### params

Request parameters.

**Returns:**
The type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-http-api-request-path"></a>

### path

The path which was matched against the Extended HTTPAPI endpoint.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-http-api-request-reply"></a>

### reply(code, headers=(null), body=$lib.undef)

Convenience method to send the response code, headers and body together.

Notes:
    This can only be called once.

    If the response body is not bytes, this method will serialize the body as JSON
    and set the ``Content-Type`` and ``Content-Length`` response headers.


**Args:**

- `code` (`int`): The response code.
- `headers` (`dict`): The response headers.
- `body` (`any`): The response body.


**Returns:**
The return type is `null`.

<a id="stormprims-http-api-request-sendbody"></a>

### sendbody(body)

Send the HTTP response body.

**Args:**

- `body` (`bytes`): The response body.


**Returns:**
The return type is `null`.

<a id="stormprims-http-api-request-sendcode"></a>

### sendcode(code)

Send the HTTP response code.

**Args:**

- `code` (`int`): The response code.


**Returns:**
The return type is `null`.

<a id="stormprims-http-api-request-sendheaders"></a>

### sendheaders(headers)

Send the HTTP response headers.

**Args:**

- `headers` (`dict`): The response headers.


**Returns:**
The return type is `null`.

<a id="stormprims-http-api-request-uri"></a>

### uri

The full request URI.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-http-api-request-user"></a>

### user

The user iden who made the HTTP API request.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-http-api-request-headers-f527"></a>

## http:api:request:headers

Immutable lowercase key access dictionary for HTTP request headers.

Example:
    Request headers can be accessed in a case insensitive manner::

        $valu = $request.headers.Cookie
        // or the lower case value
        $valu = $request.headers.cookie


<a id="stormprims-http-api-vars-f527"></a>

## http:api:vars

Accessor dictionary for getting and setting Extended HTTP API variables.

This can be used to set, unset or iterate over the runtime variables that are
set for an Extended HTTP API endpoint. These variables are set in the Storm
runtime for all of the HTTP methods configured to be executed by the endpoint.

Example:
    Set a few variables on a given API::

        $api.vars.foo = 'the foo string'
        $api.vars.bar = (1234)

    Remove a variable::

        $api.vars.foo = $lib.undef

    Iterate over the variables set for the endpoint::

        for ($key, $valu) in $api.vars {
            $lib.print(`{$key) -> {$valu}`)
        }

    Overwrite all of the variables for a given API with a new dictionary::

        $api.vars = ({"foo": "a new string", "bar": (137)})


<a id="stormprims-inet-http-oauth-v1-client-f527"></a>

## inet:http:oauth:v1:client

A client for doing OAuth V1 Authentication from Storm.


<a id="stormprims-inet-http-oauth-v1-client-sign"></a>

### sign(baseurl, method='GET', headers=(null), params=(null), body=(null))

Sign an OAuth request to a particular URL.


**Args:**

- `baseurl` (`str`): The base url to sign and query.
- `method` (`dict`): The HTTP Method to use as part of signing.
- `headers` (`dict`): Optional headers used for signing. Can override the "Content-Type" header if the signature type is set to SIG_BODY
- `params` (`dict`): Optional query parameters to pass to url construction and/or signing.
- `body` (`bytes`): Optional HTTP body to pass to request signing.


**Returns:**
A 3-element tuple of ($url, $headers, $body). The OAuth signature elements will be embedded in the element specified when constructing the client. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-http-resp-f527"></a>

## inet:http:resp

Implements the Storm API for a HTTP response.


<a id="stormprims-inet-http-resp-body"></a>

### body

The raw HTTP response body as bytes.

**Returns:**
The type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-inet-http-resp-code"></a>

### code

The HTTP status code. It is -1 if an exception occurred.

**Returns:**
The type is `int`.

<a id="stormprims-inet-http-resp-err"></a>

### err

Tuple of the error type and information if an exception occurred.

**Returns:**
The type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-http-resp-getRawHeaders"></a>

### getRawHeaders()

Get a dictionary mapping header names to lists of all their values.

**Returns:**
A dictionary mapping each header name to a list of values. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-inet-http-resp-headers"></a>

### headers

The HTTP Response headers.

**Returns:**
The type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-inet-http-resp-history"></a>

### history

A list of response objects representing the history of the response. This is populated when responses are redirected.

**Returns:**
A list of ``inet:http:resp`` objects. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-http-resp-json"></a>

### json(encoding=(null), strict=(false))

Get the JSON deserialized response.

**Args:**

- `encoding` (`str`): Specify an encoding to use.
- `strict` (`boolean`): If True, raise an exception on invalid string encoding rather than replacing the character.


**Returns:**
The return type is `prim`.

<a id="stormprims-inet-http-resp-msgpack"></a>

### msgpack(strict=(false))

Yield the msgpack deserialized objects.

**Args:**

- `strict` (`boolean`): If True, raise an exception on invalid string encoding rather than replacing the character.


**Yields:**
Unpacked values. The return type is `prim`.

<a id="stormprims-inet-http-resp-reason"></a>

### reason

The reason phrase for the HTTP status code.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-inet-http-resp-request_headers"></a>

### request_headers

The HTTP Request headers.

**Returns:**
The type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-inet-http-resp-url"></a>

### url

The response URL. If the request was redirected, this would be the final URL in the redirection chain. If the status code is -1, then this is the request URL.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-inet-http-socket-f527"></a>

## inet:http:socket

Implements the Storm API for a Websocket.


<a id="stormprims-inet-http-socket-rx"></a>

### rx(timeout=(null))

Receive a message from the web socket.

**Args:**

- `timeout` (`int`): The timeout to wait for


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-http-socket-tx"></a>

### tx(mesg)

Transmit a message over the web socket.

**Args:**

- `mesg` (`dict`): A JSON compatible message.


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-imap-server-f527"></a>

## inet:imap:server

An IMAP server for retrieving email messages.


<a id="stormprims-inet-imap-server-delete"></a>

### delete(uid_set)

Mark an RFC2060 UID message as deleted and expunge the mailbox.

The command uses the +FLAGS.SILENT command and applies the \Deleted flag.
The actual behavior of these commands are mailbox configuration dependent.

Examples:
    Mark a single message as deleted and expunge::

        ($ok, $valu) = $server.delete("8182")

    Mark ranges of messages as deleted and expunge::

        ($ok, $valu) = $server.delete("1:3,6:9")


**Args:**

- `uid_set` (`str`): The UID message set to apply the flag to.


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-imap-server-fetch"></a>

### fetch(uid)

Fetch a message by UID in RFC822 format.

The message is saved to the Axon, and a ``file:bytes`` node is returned.

Examples:
    Fetch a message, save to the Axon, and yield ``file:bytes`` node::

        yield $server.fetch("8182")


**Args:**

- `uid` (`str`): The single message UID.


**Returns:**
The file:bytes node representing the message. The return type is [`node`](#stormprims-node-f527).

<a id="stormprims-inet-imap-server-list"></a>

### list(reference_name='""', pattern='*')

List mailbox names.

By default this method uses a reference_name and pattern to return
all mailboxes from the root.


**Args:**

- `reference_name` (`str`): The mailbox reference name.
- `pattern` (`str`): The pattern to filter by.


**Returns:**
An ($ok, $valu) tuple where $valu is a list of names if $ok=True. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-imap-server-login"></a>

### login(user, passwd)

Login to the IMAP server.

**Args:**

- `user` (`str`): The username to login with.
- `passwd` (`str`): The password to login with.


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-imap-server-markSeen"></a>

### markSeen(uid_set)

Mark messages as seen by an RFC2060 UID message set.

The command uses the +FLAGS.SILENT command and applies the \Seen flag.

Examples:
    Mark a single messsage as seen::

        ($ok, $valu) = $server.markSeen("8182")

    Mark ranges of messages as seen::

        ($ok, $valu) = $server.markSeen("1:3,6:9")


**Args:**

- `uid_set` (`str`): The UID message set to apply the flag to.


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-imap-server-search"></a>

### search(*args, charset='utf-8')

Search for messages using RFC2060 syntax.

Examples:
    Retrieve all messages::

        ($ok, $uids) = $server.search("ALL")

    Search by FROM and SINCE::

        ($ok, $uids) = $server.search("FROM", "visi@vertex.link", "SINCE", "01-Oct-2021")

    Search by a subject substring::

        ($ok, $uids) = $search.search("HEADER", "Subject", "An email subject")


**Args:**

- `*args` (`str`): A set of search criteria to use.
- `charset`: The CHARSET used for the search. May be set to ``(null)`` to disable CHARSET. The input type may be one of the following: `str`, `null`.


**Returns:**
An ($ok, $valu) tuple, where $valu is a list of UIDs if $ok=True. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-imap-server-select"></a>

### select(mailbox='INBOX')

Select a mailbox to use in subsequent commands.

**Args:**

- `mailbox` (`str`): The mailbox name to select.


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-smtp-message-f527"></a>

## inet:smtp:message

An SMTP message to compose and send.


<a id="stormprims-inet-smtp-message-headers"></a>

### headers

A dictionary of email header values.

**Returns:**
The type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-inet-smtp-message-html"></a>

### html

The HTML body of the email message. This can also be used to set an HTML body in the message.

**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-inet-smtp-message-recipients"></a>

### recipients

An array of RCPT TO email addresses.

**Returns:**
The type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-smtp-message-send"></a>

### send(host, port=(25), user=(null), passwd=(null), usetls=(false), starttls=(false), timeout=(60), ssl=(null))

Transmit a message over the web socket.

**Args:**

- `host` (`str`): The hostname or IP address of the SMTP server.
- `port` (`int`): The port that the SMTP server is listening on.
- `user` (`str`): The user name to use authenticating to the SMTP server.
- `passwd` (`str`): The password to use authenticating to the SMTP server.
- `usetls` (`boolean`): Initiate a TLS connection to the SMTP server.
- `starttls` (`boolean`): Use the STARTTLS directive with the SMTP server.
- `timeout` (`int`): The timeout (in seconds) to wait for message delivery.
- `ssl` (`dict`): SSL/TLS options.


**Returns:**
An ($ok, $valu) tuple. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-inet-smtp-message-sender"></a>

### sender

The inet:email to use in the MAIL FROM request. This can also be used to set the sender for the message.

**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-inet-smtp-message-text"></a>

### text

The text body of the email message. This can also be used to set the body of the message.

**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-json-schema-f527"></a>

## json:schema

A JsonSchema validation object for use in validating data structures in Storm.


<a id="stormprims-json-schema-schema"></a>

### schema()

The schema belonging to this object.

**Returns:**
A copy of the schema used for this object. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-json-schema-validate"></a>

### validate(item)

Validate a structure against the Json Schema

**Args:**

- `item` (`prim`): A JSON structure to validate (dict, list, etc...)


**Returns:**
An ($ok, $valu) tuple. If $ok is True, then $valu should be used as the validated data structure. If $ok is False, $valu is a dictionary with a "mesg" key. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-f527"></a>

## layer

Implements the Storm api for a layer instance.


<a id="stormprims-layer-addPull"></a>

### addPull(url, offs=(0), queue_size=(10000), chunk_size=(1000))

Configure the layer to pull edits from a remote layer/feed.

**Args:**

- `url` (`str`): The telepath URL to a layer/feed.
- `offs` (`int`): The offset to begin from.
- `queue_size` (`int`): The queue size of the puller.
- `chunk_size` (`int`): The chunk size of the puller when consuming edits.


**Returns:**
Dictionary containing the pull definition. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-layer-addPush"></a>

### addPush(url, offs=(0), queue_size=(10000), chunk_size=(1000))

Configure the layer to push edits to a remote layer/feed.

**Args:**

- `url` (`str`): A telepath URL of the target layer/feed.
- `offs` (`int`): The local layer offset to begin pushing from
- `queue_size` (`int`): The queue size of the pusher.
- `chunk_size` (`int`): The chunk size of the pusher when pushing edits.


**Returns:**
Dictionary containing the push definition. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-layer-delEdge"></a>

### delEdge(n1nid, verb, n2nid)

Delete edges from a node in this layer.

**Args:**

- `n1nid`: The N1 node id. The input type may be one of the following: `int`, `str`, `bytes`.
- `verb` (`str`): The edge verb to delete.
- `n2nid`: The N2 node id. The input type may be one of the following: `int`, `str`, `bytes`.


**Returns:**
Returns true if edits were made. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-layer-delNodeData"></a>

### delNodeData(nid, name=(null))

Delete node data from a node in this layer.

**Args:**

- `nid`: The node id. The input type may be one of the following: `int`, `str`, `bytes`.
- `name` (`str`): The node data key to delete.


**Returns:**
Returns true if edits were made. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-layer-delPull"></a>

### delPull(iden)

Remove a pull config from the layer.

**Args:**

- `iden` (`str`): The iden of the push config to remove.


**Returns:**
The return type is `null`.

<a id="stormprims-layer-delPush"></a>

### delPush(iden)

Remove a push config from the layer.

**Args:**

- `iden` (`str`): The iden of the push config to remove.


**Returns:**
The return type is `null`.

<a id="stormprims-layer-delStorNode"></a>

### delStorNode(nid)

Delete a storage node, node data, and associated edges from a node in this layer.

**Args:**

- `nid`: The node id. The input type may be one of the following: `int`, `str`, `bytes`.


**Returns:**
Returns true if edits were made. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-layer-delStorNodeProp"></a>

### delStorNodeProp(nid, prop)

Delete a property from a node in this layer.

**Args:**

- `nid`: The node id. The input type may be one of the following: `int`, `str`, `bytes`.
- `prop` (`str`): The property name to delete.


**Returns:**
Returns true if edits were made. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-layer-delTombstone"></a>

### delTombstone(nid, tombtype, tombinfo)

Delete a tombstone stored in the layer.

May only be called on the write layer of the current view. Removing a
tombstone makes the value it masks visible again, so it requires the "add"
permission for that value (``node.add``, ``node.prop.set``, ``node.tag.add``,
``node.data.set``, or ``node.edge.add``) rather than the "del" permission.


**Args:**

- `nid`: The node id of the node. The input type may be one of the following: `int`, `str`, `bytes`.
- `tombtype` (`int`): The tombstone type.
- `tombinfo` (`list`): The tombstone info to delete.


**Returns:**
True if the tombstone was deleted, False if not. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-layer-edited"></a>

### edited()

Return the last time the layer was edited or null if no edits are present.

**Returns:**
The last time the layer was edited. The return type is `time`.

<a id="stormprims-layer-get"></a>

### get(name, defv=(null))

Get a arbitrary value in the Layer definition.

**Args:**

- `name` (`str`): Name of the value to get.
- `defv` (`prim`): The default value returned if the name is not set in the Layer.


**Returns:**
The value requested or the default value. The return type is `prim`.

<a id="stormprims-layer-getEdgeTombstones"></a>

### getEdgeTombstones(verb=(null))

Get (n1nid, verb, n2nid) tuples representing edge tombstones stored in the layer.


**Args:**

- `verb` (`str`): The optional verb to lift edge tombstones for.


**Yields:**
Tuple of n1nid, verb, n2nid. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getEdges"></a>

### getEdges()

Yield (n1nid, verb, n2nid, istombstone) tuples for any light edges in the layer.

Example:
    Iterate the light edges in ``$layer``::

        for ($n1nid, $verb, $n2nid, $tomb) in $layer.getEdges() {
            if $tomb {
                $lib.print(`{$n1nid} -({$verb})> {$n2nid}`)
            } else {
                $lib.print(`{$n1nid} +({$verb})> {$n2nid}`)
            }
        }



**Yields:**
Yields (<n1nid>, <verb>, <n2nid>) tuples The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getEdgesByN1"></a>

### getEdgesByN1(nid, verb=(null))

Yield (verb, n2nid, istombstone) tuples for any light edges in the layer for the source node id.

Example:
    Iterate the N1 edges for ``$node``::

        for ($verb, $n2nid, $tomb) in $layer.getEdgesByN1($node) {
            if $tomb {
                $lib.print(`-({$verb})> {$n2nid}`)
            } else {
                $lib.print(`+({$verb})> {$n2nid}`)
            }
        }



**Args:**

- `nid`: The node id of the node. The input type may be one of the following: `int`, `str`, `bytes`.
- `verb` (`str`): An optional edge verb to filter by.


**Yields:**
Yields (<verb>, <n2nid>, <istombstone>) tuples The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getEdgesByN2"></a>

### getEdgesByN2(nid, verb=(null))

Yield (verb, n1nid, istombstone) tuples for any light edges in the layer for the target node id.

Example:
    Iterate the N2 edges for ``$node``::

        for ($verb, $n1nid) in $layer.getEdgesByN2($node) {
            if $tomb {
                $lib.print(`-({$verb})> {$n1nid}`)
            } else {
                $lib.print(`+({$verb})> {$n1nid}`)
            }
        }


**Args:**

- `nid`: The node id of the node. The input type may be one of the following: `int`, `str`, `bytes`.
- `verb` (`str`): An optional edge verb to filter by.


**Yields:**
Yields (<verb>, <n1nid>, <istombstone>) tuples The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getFormCounts"></a>

### getFormCounts()

Get the formcounts for the Layer.

Example:
    Get the formcounts for the current Layer::

        $counts = $lib.layer.get().getFormCounts()

**Returns:**
Dictionary containing form names and the count of the nodes in the Layer. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-layer-getNodeData"></a>

### getNodeData(nid)

Yield (name, valu, istombstone) tuples for any node data in the layer for the target node nid.

Example:
    Iterate the node data for ``$node``::

        for ($name, $valu, $tomb) in $layer.getNodeData($node.nid) {
            if $tomb {
                $lib.print(`{$name} DELETED`)
            } else {
                $lib.print(`{$name} = {$valu}`)
            }
        }


**Args:**

- `nid`: The node id of the node. The input type may be one of the following: `int`, `str`, `bytes`.


**Yields:**
Yields (<name>, <valu>, <istombstone>>) tuples The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getPropArrayCount"></a>

### getPropArrayCount(propname, valu=$lib.undef)

Get the number of individual value rows in the layer for the given array property name.

**Args:**

- `propname` (`str`): The property name to look up.
- `valu` (`any`): A specific value in the array property to look up.


**Returns:**
The count of rows. The return type is `int`.

<a id="stormprims-layer-getPropCount"></a>

### getPropCount(propname, valu=$lib.undef)

Get the number of property rows in the layer for the given full form or property name.

**Args:**

- `propname` (`str`): The property or form name to look up.
- `valu` (`any`): A specific value of the property to look up.


**Returns:**
The count of rows. The return type is `int`.

<a id="stormprims-layer-getPropValues"></a>

### getPropValues(propname)

Yield unique property values in the layer for the given form or property name.

**Args:**

- `propname` (`str`): The property or form name to look up.


**Yields:**
Unique property values. The return type is `any`.

<a id="stormprims-layer-getStorNode"></a>

### getStorNode(nid)

Retrieve the raw storage node for the specified node id.


**Args:**

- `nid`: The node id of the node. The input type may be one of the following: `int`, `str`, `bytes`.


**Returns:**
The storage node dictionary. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-layer-getStorNodes"></a>

### getStorNodes()

Get nid, sode tuples representing the data stored in the layer.

Notes:
    The storage nodes represent **only** the data stored in the layer
    and may not represent whole nodes.


**Yields:**
Tuple of nid, sode values. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getStorNodesByForm"></a>

### getStorNodesByForm(form)

Get nid, sode tuples representing the data stored in the layer for a given form.

Notes:
    The storage nodes represent **only** the data stored in the layer
    and may not represent whole nodes.


**Args:**

- `form` (`str`): The name of the form to get storage nodes for.


**Yields:**
Tuple of nid, sode values. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getStorNodesByProp"></a>

### getStorNodesByProp(propname, propvalu=(null), propcmpr='=')

Get nid, sode tuples representing the data stored in the layer for a given property.

Notes:

    The storage nodes represent **only** the data stored in the layer
    and may not represent whole nodes.


**Args:**

- `propname` (`str`): The full property name to lift by.
- `propvalu` (`prim`): The value for the property.
- `propcmpr` (`str`): The comparison operation to use on the value.


**Yields:**
Tuple of nid, sode values. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-getTagCount"></a>

### getTagCount(tagname, formname=(null))

Return the number of tag rows in the layer for the given tag and optional form.

Examples:
    Get the number of ``inet:ipv4`` nodes with the ``$foo.bar`` tag::

        $count = $lib.layer.get().getTagCount(foo.bar, formname=inet:ipv4)

**Args:**

- `tagname` (`str`): The name of the tag to look up.
- `formname` (`str`): The form to constrain the look up by.


**Returns:**
The count of tag rows. The return type is `int`.

<a id="stormprims-layer-getTagPropCount"></a>

### getTagPropCount(tag, propname, form=(null), valu=$lib.undef)

Get the number of rows in the layer for the given tag property.

**Args:**

- `tag` (`str`): The tag to look up.
- `propname` (`str`): The property name to look up.
- `form` (`str`): The optional form to look up.
- `valu` (`any`): A specific value of the property to look up.


**Returns:**
The count of rows. The return type is `int`.

<a id="stormprims-layer-getTombstones"></a>

### getTombstones()

Get (nid, tombtype, info) tuples representing tombstones stored in the layer.


**Yields:**
Tuple of node id, tombstone type, and type specific info. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-layer-hasEdge"></a>

### hasEdge(n1nid, verb, n2nid)

Check if a light edge between two nodes exists in the layer.

**Args:**

- `n1nid`: The N1 node id. The input type may be one of the following: `int`, `str`, `bytes`.
- `verb` (`str`): The edge verb.
- `n2nid`: The N2 node id. The input type may be one of the following: `int`, `str`, `bytes`.


**Returns:**
True if the edge exists in the layer, False if it is a tombstone, or None if not present. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-layer-iden"></a>

### iden

The iden of the Layer.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-layer-liftByNodeData"></a>

### liftByNodeData(name)

Lift and yield nodes with the given node data key set within the layer.

Example:
    Yield all nodes with the data key zootsuit set in the top layer::

        yield $lib.layer.get().liftByNodeData(zootsuit)



**Args:**

- `name` (`str`): The node data name to lift by.


**Yields:**
Yields nodes. The return type is [`node`](#stormprims-node-f527).

<a id="stormprims-layer-liftByProp"></a>

### liftByProp(propname, propvalu=(null), propcmpr='=')

Lift and yield nodes with the property and optional value set within the layer.

Example:
    Yield all nodes with the property ``ou:org:name`` set in the top layer::

        yield $lib.layer.get().liftByProp(ou:org:name)

    Yield all nodes with the property ``ou:org:name=woot`` in the top layer::

        yield $lib.layer.get().liftByProp(ou:org:name, woot)

    Yield all nodes with the property ``ou:org:name^=woot`` in the top layer::

        yield $lib.layer.get().liftByProp(ou:org:name, woot, "^=")



**Args:**

- `propname` (`str`): The full property name to lift by.
- `propvalu` (`any`): The value for the property.
- `propcmpr` (`str`): The comparison operation to use on the value.


**Yields:**
Yields nodes. The return type is [`node`](#stormprims-node-f527).

<a id="stormprims-layer-liftByTag"></a>

### liftByTag(tagname, formname=(null))

Lift and yield nodes with the tag set within the layer.

Example:
    Yield all nodes with the tag #foo set in the layer::

        yield $lib.layer.get().liftByTag(foo)

    Yield all inet:fqdn with the tag #foo set in the layer::

        yield $lib.layer.get().liftByTag(foo, inet:fqdn)



**Args:**

- `tagname` (`str`): The tag name to lift by.
- `formname` (`str`): The optional form to lift.


**Yields:**
Yields nodes. The return type is [`node`](#stormprims-node-f527).

<a id="stormprims-layer-name"></a>

### name

The name of the Layer.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-layer-repr"></a>

### repr()

Get a string representation of the Layer.

**Returns:**
A string that can be printed, representing a Layer. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-layer-set"></a>

### set(name, valu)

Set an arbitrary value in the Layer definition.

**Args:**

- `name` (`str`): The name to set.
- `valu` (`any`): The value to set.


**Returns:**
The return type is `null`.

<a id="stormprims-layer-setStorNodeProp"></a>

### setStorNodeProp(nid, prop, valu)

Set a property on a node in this layer.

**Args:**

- `nid`: The node id. The input type may be one of the following: `int`, `str`, `bytes`.
- `prop` (`str`): The property name to set.
- `valu` (`any`): The value to set.


**Returns:**
Returns true if edits were made. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-layer-verify"></a>

### verify(config=(null))

Verify consistency between the node storage and indexes in the given layer.

Example:
    Get all messages about consistency issues in the default layer::

        for $mesg in $lib.layer.get().verify() {
            $lib.print($mesg)
        }

Notes:
    The config format argument and message format yielded by this API is considered BETA
    and may be subject to change! The formats will be documented when the convention stabilizes.


**Args:**

- `config` (`dict`): The scan config to use (default all enabled).


**Yields:**
Yields messages describing any index inconsistencies. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-list-f527"></a>

## list

Implements the Storm API for a List instance.


<a id="stormprims-list-append"></a>

### append(valu)

Append a value to the list.

**Args:**

- `valu` (`any`): The item to append to the list.


**Returns:**
The return type is `null`.

<a id="stormprims-list-extend"></a>

### extend(valu)

Extend a list using another iterable. If ``(null)`` is provided, this is a no-op.

Examples:
    Populate a list by extending it with other lists::

        $list = ()

        $foo = (f, o, o)
        $bar = (b, a, r)

        $list.extend($foo)
        $list.extend($bar)

        // $list is now (f, o, o, b, a, r)

    Safely extend a list with a value that may be null::

        $list = ()

        $list.extend($attrs.foo.bar.baz)


**Args:**

- `valu` (`list`): A list or other iterable. If ``(null)``, this is a no-op.


**Returns:**
The return type is `null`.

<a id="stormprims-list-has"></a>

### has(valu)

Check if a value is in the list.

**Args:**

- `valu` (`any`): The value to check.


**Returns:**
True if the item is in the list, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-list-index"></a>

### index(valu)

Return a single field from the list by index.

**Args:**

- `valu` (`int`): The list index value.


**Returns:**
The item present in the list at the index position. The return type is `any`.

<a id="stormprims-list-pop"></a>

### pop(index=(-1))

Pop and return the entry at the specified index in the list. If no index is specified, pop the last entry.

**Args:**

- `index` (`int`): Index of entry to pop.


**Returns:**
The entry at the specified index in the list. The return type is `any`.

<a id="stormprims-list-rem"></a>

### rem(item, all=(false))

Remove a specific item from anywhere in the list.

**Args:**

- `item` (`any`): An item in the list.
- `all` (`boolean`): Remove all instances of item from the list.


**Returns:**
Boolean indicating if the item was removed from the list. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-list-reverse"></a>

### reverse()

Reverse the order of the list in place

**Returns:**
The return type is `null`.

<a id="stormprims-list-size"></a>

### size()

Return the length of the list.

**Returns:**
The size of the list. The return type is `int`.

<a id="stormprims-list-slice"></a>

### slice(start, end=(null))

Get a slice of the list.

Examples:
    Slice from index to 1 to 5::

        $x=(f, o, o, b, a, r)
        $y=$x.slice(1,5)  // (o, o, b, a)

    Slice from index 3 to the end of the list::

        $y=$x.slice(3)  // (b, a, r)


**Args:**

- `start` (`int`): The starting index.
- `end` (`int`): The ending index. If not specified, slice to the end of the list.


**Returns:**
The slice of the list. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-list-sort"></a>

### sort(reverse=(false))

Sort the list in place.

**Args:**

- `reverse` (`boolean`): Sort the list in reverse order.


**Returns:**
The return type is `null`.

<a id="stormprims-list-unique"></a>

### unique()

Get a copy of the list containing unique items.

**Returns:**
The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-model-edge-f527"></a>

## model:edge

Implements the Storm API for an Edge.


<a id="stormprims-model-edge-n1form"></a>

### n1form

The form of the n1 node. May be null to specify "any".

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-edge-n2form"></a>

### n2form

The form of the n2 node. May be null to specify "any".

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-edge-verb"></a>

### verb

The edge verb.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-form-f527"></a>

## model:form

Implements the Storm API for a Form.


<a id="stormprims-model-form-name"></a>

### name

The name of the Form.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-form-prop"></a>

### prop(name)

Get a Property on the Form.

**Args:**

- `name` (`str`): The property to retrieve.


**Returns:**
The ``model:property`` instance if the property if present on the form or null. The return type may be one of the following: [`model:property`](#stormprims-model-property-f527), `null`.

<a id="stormprims-model-form-props"></a>

### props

Get a dictionary of Properties on the Form.

**Returns:**
The return type is [`model:form:props`](#stormprims-model-form-props-f527).

<a id="stormprims-model-form-type"></a>

### type

Get the Type for the form.

**Returns:**
The return type is [`model:type`](#stormprims-model-type-f527).

<a id="stormprims-model-form-props-f527"></a>

## model:form:props

A Storm Primitive representing the properties on a Form.


<a id="stormprims-model-property-f527"></a>

## model:property

Implements the Storm API for a Property.


<a id="stormprims-model-property-computed"></a>

### computed

True if the Property has been computed from another.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-model-property-form"></a>

### form

Get the Form for the Property.

**Returns:**
The return type may be one of the following: [`model:form`](#stormprims-model-form-f527), `null`.

<a id="stormprims-model-property-full"></a>

### full

The full name of the Property.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-property-name"></a>

### name

The short name of the Property.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-property-types"></a>

### types

Get the types allowed for the property.

**Returns:**
A list of ``model:type`` objects for the types allowed in the property. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-model-tagprop-f527"></a>

## model:tagprop

Implements the Storm API for a Tag Property.


<a id="stormprims-model-tagprop-name"></a>

### name

The name of the Tag Property.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-tagprop-type"></a>

### type

Get the Type for the Tag Property.

**Returns:**
The return type is [`model:type`](#stormprims-model-type-f527).

<a id="stormprims-model-type-f527"></a>

## model:type

A Storm types wrapper around a lib.types.Type


<a id="stormprims-model-type-mutable"></a>

### mutable

True if the type is mutable.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-model-type-name"></a>

### name

The name of the Type.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-type-norm"></a>

### norm(valu)

Get the norm and info for the Type.

**Args:**

- `valu` (`any`): The value to norm.


**Returns:**
A tuple of the normed value and its information dictionary. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-model-type-opts"></a>

### opts

The options for the Type.

**Returns:**
The type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-model-type-repr"></a>

### repr(valu)

Get the repr of a value for the Type.

**Args:**

- `valu` (`any`): The value to get the repr of.


**Returns:**
The string form of the value as represented by the type. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-model-type-stortype"></a>

### stortype

The stortype of the Type.

**Returns:**
The type is `int`.

<a id="stormprims-node-f527"></a>

## node

Implements the Storm api for a node instance.


<a id="stormprims-node-addEdge"></a>

### addEdge(verb, dest)

Add a light-weight edge.

**Args:**

- `verb` (`str`): The edge verb to add.
- `dest`: The destination node id. The input type may be one of the following: `int`, `str`, `bytes`.


**Returns:**
The return type is `null`.

<a id="stormprims-node-delEdge"></a>

### delEdge(verb, dest)

Remove a light-weight edge.

**Args:**

- `verb` (`str`): The edge verb to remove.
- `dest`: The destination node id to remove. The input type may be one of the following: `int`, `str`, `bytes`.


**Returns:**
The return type is `null`.

<a id="stormprims-node-difftags"></a>

### difftags(tags, prefix=(null), apply=(false), norm=(false))

Get and optionally apply the difference between the current set of tags and another set.

**Args:**

- `tags` (`list`): The set to compare against.
- `prefix` (`str`): An optional prefix to match tags under.
- `apply` (`boolean`): If true, apply the diff.
- `norm` (`boolean`): Optionally norm the list of tags. If a prefix is provided, it will not be normed.


**Returns:**
The tags which have been added/deleted in the new set. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-node-edges"></a>

### edges(verb=(null), reverse=(false))

Yields the (verb, nid) tuples for this nodes edges.

**Args:**

- `verb` (`str`): If provided, only return edges with this verb.
- `reverse` (`boolean`): If true, yield edges with this node as the dest rather than source.


**Yields:**
A tuple of (verb, nid) values for this nodes edges. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-form"></a>

### form

Get the form of the Node.

**Returns:**
The form of the Node. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-node-getByLayer"></a>

### getByLayer()

Return a dict you can use to lookup which props/tags came from which layers.

**Returns:**
property / tag lookup dictionary. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-node-getStorNodes"></a>

### getStorNodes()

Return a list of "storage nodes" which were fused from the layers to make this node.

**Returns:**
List of storage node objects. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-globtags"></a>

### globtags(glob)

Get a list of the tag components from a Node which match a tag glob expression.

**Args:**

- `glob` (`str`): The glob expression to match.


**Returns:**
The components of tags which match the wildcard component of a glob expression. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-is"></a>

### is(name)

Check if a Node is a given form or implements a given interface.

**Args:**

- `name`: The form(s) or interface(s) to compare the Node against. The input type may be one of the following: `str`, `list`.


**Returns:**
True if the node is at least one of the forms or implements at least one of the interfaces specified, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-node-ndef"></a>

### ndef

Get the form and primary property of the Node.

**Returns:**
A tuple of the form and primary property. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-nid"></a>

### nid

Get the node id of the Node.

**Returns:**
The integer node id, or null if the node has no nid. The return type may be one of the following: `int`, `null`.

<a id="stormprims-node-pack"></a>

### pack(dorepr=(false))

Return the serializable/packed version of the Node.

**Args:**

- `dorepr` (`boolean`): Include repr information for human readable versions of properties.


**Returns:**
A tuple containing the ndef and property bag of the node. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-repr"></a>

### repr(name=(null), defv=(null))

Get the repr for the primary property or secondary property of a Node.

**Args:**

- `name` (`str`): The name of the secondary property to get the repr for.
- `defv` (`str`): The default value to return if the secondary property does not exist


**Returns:**
The string representation of the requested value. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-node-setValue"></a>

### setValue(valu)

Set the primary property value for a Node with special deconfliction rules.

**Args:**

- `valu` (`any`): The new value.


**Returns:**
The return type is `null`.

<a id="stormprims-node-tags"></a>

### tags(glob=(null), leaf=(false))

Get a list of the tags on the Node.

Notes:
   When providing a glob argument, the following rules are used. A single asterisk(*) will replace exactly
   one dot-delimited component of a tag. A double asterisk(**) will replace one or more of any character.


**Args:**

- `glob` (`str`): A tag glob expression. If this is provided, only tags which match the expression are returned.
- `leaf` (`boolean`): If true, only leaf tags are included in the returned tags.


**Returns:**
A list of tags on the node. If a glob match is provided, only matching tags are returned. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-value"></a>

### value

Get the value of the primary property of the Node.

**Returns:**
The primary property. The return type is `prim`.

<a id="stormprims-node-data-f527"></a>

## node:data

A Storm Primitive representing the NodeData stored for a Node.


<a id="stormprims-node-data-cacheget"></a>

### cacheget(name, asof='now')

Retrieve data stored with cacheset() if it was stored more recently than the asof argument.

**Args:**

- `name` (`str`): The name of the data to load.
- `asof` (`time`): The max cache age.


**Returns:**
The cached value or null. The return type is `prim`.

<a id="stormprims-node-data-cacheset"></a>

### cacheset(name, valu)

Set a node data value with an envelope that tracks time for cache use.

**Args:**

- `name` (`str`): The name of the data to set.
- `valu` (`prim`): The data to store.


**Returns:**
The return type is `null`.

<a id="stormprims-node-data-get"></a>

### get(name)

Get the Node data for a given name for the Node.

**Args:**

- `name` (`str`): Name of the data to get.


**Returns:**
The stored node data. The return type is `prim`.

<a id="stormprims-node-data-has"></a>

### has(name)

Check if the Node data has the given key set on it

**Args:**

- `name` (`str`): Name of the data to check for.


**Returns:**
True if the key is found, otherwise false. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-node-data-list"></a>

### list()

Get a list of the Node data on the Node as (name, value) tuples.

**Returns:**
List of (name, value) tuples stored on the node. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-data-load"></a>

### load(name)

Load the Node data onto the Node so that the Node data is packed and returned by the runtime.

**Args:**

- `name` (`str`): The name of the data to load.


**Returns:**
The return type is `null`.

<a id="stormprims-node-data-pop"></a>

### pop(name)

Pop (remove) a the Node data from the Node.

**Args:**

- `name` (`str`): The name of the data to remove from the node.


**Returns:**
The data removed. The return type is `prim`.

<a id="stormprims-node-data-set"></a>

### set(name, valu)

Set the Node data for a given name on the Node.

**Args:**

- `name` (`str`): The name of the data.
- `valu` (`prim`): The data to store.


**Returns:**
The return type is `null`.

<a id="stormprims-node-path-f527"></a>

## node:path

Implements the Storm API for the Path object.


<a id="stormprims-node-path-links"></a>

### links()

The list of links which this Path has been forked from during pivot operations.

**Returns:**
A list of (node id, link info) tuples. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-path-listvars"></a>

### listvars()

List variables available in the path of a storm query.

**Returns:**
List of tuples containing the name and value of path variables. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-node-path-meta"></a>

### meta

The PathMeta object for the Path.

**Returns:**
The type is [`node:path:meta`](#stormprims-node-path-meta-f527).

<a id="stormprims-node-path-vars"></a>

### vars

The PathVars object for the Path.

**Returns:**
The type is [`node:path:vars`](#stormprims-node-path-vars-f527).

<a id="stormprims-node-path-meta-f527"></a>

## node:path:meta

Put the storm deref/setitem/iter convention on top of path meta information.


<a id="stormprims-node-path-vars-f527"></a>

## node:path:vars

Put the storm deref/setitem/iter convention on top of path variables.


<a id="stormprims-node-props-f527"></a>

## node:props

A Storm Primitive representing the properties on a Node.


<a id="stormprims-noderef-f527"></a>

## noderef

A type and value tuple representing a node.

This is the form-valued specialization of Valu.


<a id="stormprims-noderef-is"></a>

### is(name)

Check if the type in the tuple is a given type.

**Args:**

- `name`: The type or types to compare the type in the tuple against. The input type may be one of the following: `str`, `list`.


**Returns:**
True if the type is at least one of the types specified, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-noderef-type"></a>

### type

Get the type of the tuple.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-noderef-value"></a>

### value

Get the valu of the tuple.

**Returns:**
The type is `any`.

<a id="stormprims-number-f527"></a>

## number

Implements the Storm API for a Number instance.

Storm Numbers are high precision fixed point decimals corresponding to the
the hugenum storage type.


<a id="stormprims-number-scaleb"></a>

### scaleb(other)

Return the number multiplied by 10**other.

Example:
    Multiply the value by 10**-18::

        $baz.scaleb(-18)

**Args:**

- `other` (`int`): The amount to adjust the exponent.


**Returns:**
The exponent adjusted number. The return type is [`number`](#stormprims-number-f527).

<a id="stormprims-number-tofloat"></a>

### tofloat()

Return the number as a float.

**Returns:**
The number as a float. The return type is `float`.

<a id="stormprims-number-toint"></a>

### toint(rounding=(null))

Return the number as an integer.

By default, decimal places will be truncated. Optionally, rounding rules
can be specified by providing the name of a Python decimal rounding mode
to the 'rounding' argument.

Example:
    Round the value stored in $baz up instead of truncating::

        $baz.toint(rounding=ROUND_UP)

**Args:**

- `rounding` (`str`): An optional rounding mode to use.


**Returns:**
The number as an integer. The return type is `int`.

<a id="stormprims-number-tostr"></a>

### tostr()

Return the number as a string.

**Returns:**
The number as a string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-pipe-f527"></a>

## pipe

A Storm Pipe provides fast ephemeral queues.


<a id="stormprims-pipe-put"></a>

### put(item)

Add a single item to the Pipe.

**Args:**

- `item` (`any`): An object to add to the Pipe.


**Returns:**
The return type is `null`.

<a id="stormprims-pipe-puts"></a>

### puts(items)

Add a list of items to the Pipe.

**Args:**

- `items` (`list`): A list of items to add.


**Returns:**
The return type is `null`.

<a id="stormprims-pipe-size"></a>

### size()

Retrieve the number of items in the Pipe.

**Returns:**
The number of items in the Pipe. The return type is `int`.

<a id="stormprims-pipe-slice"></a>

### slice(size=(1000))

Return a list of up to size items from the Pipe.

**Args:**

- `size` (`int`): The max number of items to return.


**Returns:**
A list of at least 1 item from the Pipe. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-pipe-slices"></a>

### slices(size=(1000))

Yield lists of up to size items from the Pipe.

Notes:
    The loop will exit when the Pipe is closed and empty.

Examples:
    Operation on slices from a pipe one at a time::

        for $slice in $pipe.slices(1000) {
            for $item in $slice { $dostuff($item) }
        }

    Operate on slices from a pipe in bulk::

        for $slice in $pipe.slices(1000) {
            $dostuff_batch($slice)
        }

**Args:**

- `size` (`int`): The max number of items to yield per slice.


**Yields:**
Yields objects from the Pipe. The return type is `any`.

<a id="stormprims-pkg-queue-f527"></a>

## pkg:queue

A StormLib API instance for a package Queue.


<a id="stormprims-pkg-queue-cull"></a>

### cull(offs)

Remove items from the Queue up to, and including, the offset.

**Args:**

- `offs` (`int`): The offset which to cull records from the Queue.


**Returns:**
The return type is `null`.

<a id="stormprims-pkg-queue-get"></a>

### get(offs=(0), wait=(true))

Get a particular item from the Queue.

**Args:**

- `offs` (`int`): The offset to retrieve an item from.
- `wait` (`boolean`): Wait for the offset to be available before returning the item.


**Returns:**
A tuple of the offset and the item from the Queue. If wait is false and the offset is not present, null is returned. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-pkg-queue-gets"></a>

### gets(offs=(0), wait=(true), size=(null))

Get multiple items from the Queue as a iterator.

**Args:**

- `offs` (`int`): The offset to retrieve an items from.
- `wait` (`boolean`): Wait for the offset to be available before returning the item.
- `size` (`int`): The maximum number of items to yield


**Yields:**
Yields tuples of the offset and item. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-pkg-queue-name"></a>

### name

The name of the Queue.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-pkg-queue-pkgname"></a>

### pkgname

The name of the package the Queue belongs to.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-pkg-queue-pop"></a>

### pop(offs=(null), wait=(false))

Pop an item from the Queue at a specific offset.

**Args:**

- `offs` (`int`): Offset to pop the item from. If not specified, the first item in the Queue will be popped.
- `wait` (`boolean`): Wait for an item to be available to pop.


**Returns:**
The offset and item popped from the Queue. If there is no item at the offset or the Queue is empty and wait is false, it returns null. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-pkg-queue-put"></a>

### put(item)

Put an item into the Queue.

**Args:**

- `item` (`prim`): The item being put into the Queue.


**Returns:**
The Queue offset of the item. The return type is `int`.

<a id="stormprims-pkg-queue-puts"></a>

### puts(items)

Put multiple items into the Queue.

**Args:**

- `items` (`list`): The items to put into the Queue.


**Returns:**
The Queue offset of the first item. The return type is `int`.

<a id="stormprims-pkg-queue-size"></a>

### size()

Get the number of items in the Queue.

**Returns:**
The number of items in the Queue. The return type is `int`.

<a id="stormprims-pkg-queues-f527"></a>

## pkg:queues

A StormLib API instance for interacting with persistent Queues for a package in the Cortex.


<a id="stormprims-pkg-queues-add"></a>

### add(name)

Add a Queue for the package with a given name.

**Args:**

- `name` (`str`): The name of the Queue to add.


**Returns:**
The return type is [`pkg:queue`](#stormprims-pkg-queue-f527).

<a id="stormprims-pkg-queues-del"></a>

### del(name)

Delete a given Queue.

**Args:**

- `name` (`str`): The name of the Queue to delete.


**Returns:**
The return type is `null`.

<a id="stormprims-pkg-queues-gen"></a>

### gen(name)

Add or get a Queue in a single operation.

**Args:**

- `name` (`str`): The name of the Queue to add or get.


**Returns:**
The return type is [`pkg:queue`](#stormprims-pkg-queue-f527).

<a id="stormprims-pkg-queues-get"></a>

### get(name)

Get an existing Queue.

**Args:**

- `name` (`str`): The name of the Queue to get.


**Returns:**
A ``pkg:queue`` object. The return type is [`pkg:queue`](#stormprims-pkg-queue-f527).

<a id="stormprims-pkg-queues-list"></a>

### list()

Get a list of the Queues for the package in the Cortex.

**Yields:**
Queue definitions for the package. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-pkg-state-f527"></a>

## pkg:state

A read-only Storm interface for accessing package state information.


<a id="stormprims-pkg-vars-f527"></a>

## pkg:vars

The Storm deref/setitem/iter convention on top of pkg vars information.


<a id="stormprims-queue-f527"></a>

## queue

A StormLib API instance of a named channel in the Cortex MultiQueue.


<a id="stormprims-queue-cull"></a>

### cull(offs)

Remove items from the Queue up to, and including, the offset.

**Args:**

- `offs` (`int`): The offset which to cull records from the Queue.


**Returns:**
The return type is `null`.

<a id="stormprims-queue-get"></a>

### get(offs=(0), cull=(true), wait=(true))

Get a particular item from the Queue.

**Args:**

- `offs` (`int`): The offset to retrieve an item from.
- `cull` (`boolean`): Culls items up to, but not including, the specified offset.
- `wait` (`boolean`): Wait for the offset to be available before returning the item.


**Returns:**
A tuple of the offset and the item from the Queue. If wait is false and the offset is not present, null is returned. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-queue-gets"></a>

### gets(offs=(0), wait=(true), cull=(false), size=(null))

Get multiple items from the Queue as a iterator.

**Args:**

- `offs` (`int`): The offset to retrieve items from.
- `wait` (`boolean`): Wait for the offset to be available before returning the item.
- `cull` (`boolean`): Culls items up to, but not including, the specified offset.
- `size` (`int`): The maximum number of items to yield.


**Yields:**
Yields tuples of the offset and item. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-queue-iden"></a>

### iden

The iden of the Queue.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-queue-name"></a>

### name

The name of the Queue.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-queue-pop"></a>

### pop(offs=(null), wait=(false))

Pop an item from the Queue at a specific offset.

**Args:**

- `offs` (`int`): Offset to pop the item from. If not specified, the first item in the Queue will be popped.
- `wait` (`boolean`): Wait for an item to be available to pop.


**Returns:**
The offset and item popped from the Queue. If there is no item at the offset or the Queue is empty and wait is false, it returns null. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-queue-put"></a>

### put(item)

Put an item into the Queue.

**Args:**

- `item` (`prim`): The item being put into the Queue.


**Returns:**
The Queue offset of the item. The return type is `int`.

<a id="stormprims-queue-puts"></a>

### puts(items)

Put multiple items into the Queue.

**Args:**

- `items` (`list`): The items to put into the Queue.


**Returns:**
The Queue offset of the first item. The return type is `int`.

<a id="stormprims-queue-size"></a>

### size()

Get the number of items in the Queue.

**Returns:**
The number of items in the Queue. The return type is `int`.

<a id="stormprims-random-f527"></a>

## random

A random number generator.


<a id="stormprims-random-int"></a>

### int(maxval, minval=(0))

Generate a random integer.

**Args:**

- `maxval` (`int`): The maximum random value.
- `minval` (`int`): The minimum random value.


**Returns:**
A random integer in the range min-max inclusive. The return type is `int`.

<a id="stormprims-random-seed"></a>

### seed

The seed used for the generator. Setting this value resets the generator state.

**Returns:**
The return type may be one of the following: [`str`](#stormprims-str-f527), `null`.
When this is used to set the value, it does not have a return type.

<a id="stormprims-runtime-vars-f527"></a>

## runtime:vars

The Storm deref/setitem/iter convention on top of runtime vars information.


<a id="stormprims-set-f527"></a>

## set

Implements the Storm API for a Set object.


<a id="stormprims-set-add"></a>

### add(*items)

Add a item to the set. Each argument is added to the set.

**Args:**

- `*items` (`any`): The items to add to the set.


**Returns:**
The return type is `null`.

<a id="stormprims-set-adds"></a>

### adds(*items)

Add the contents of a iterable items to the set.

**Args:**

- `*items` (`any`): Iterables items to add to the set.


**Returns:**
The return type is `null`.

<a id="stormprims-set-has"></a>

### has(item)

Check if a item is a member of the set.

**Args:**

- `item` (`any`): The item to check the set for membership.


**Returns:**
True if the item is in the set, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-set-list"></a>

### list()

Get a list of the current members of the set.

**Returns:**
A list containing the members of the set. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-set-rem"></a>

### rem(*items)

Remove an item from the set.

**Args:**

- `*items` (`any`): Items to be removed from the set.


**Returns:**
The return type is `null`.

<a id="stormprims-set-rems"></a>

### rems(*items)

Remove the contents of a iterable object from the set.

**Args:**

- `*items` (`any`): Iterables items to remove from the set.


**Returns:**
The return type is `null`.

<a id="stormprims-set-size"></a>

### size()

Get the size of the set.

**Returns:**
The size of the set. The return type is `int`.

<a id="stormprims-spooled-set-f527"></a>

## spooled:set

A StormLib API instance of a Storm Set object that can fallback to lmdb.


<a id="stormprims-spooled-set-add"></a>

### add(*items)

Add a item to the set. Each argument is added to the set.

**Args:**

- `*items` (`any`): The items to add to the set.


**Returns:**
The return type is `null`.

<a id="stormprims-spooled-set-adds"></a>

### adds(*items)

Add the contents of a iterable items to the set.

**Args:**

- `*items` (`any`): Iterables items to add to the set.


**Returns:**
The return type is `null`.

<a id="stormprims-spooled-set-has"></a>

### has(item)

Check if a item is a member of the set.

**Args:**

- `item` (`any`): The item to check the set for membership.


**Returns:**
True if the item is in the set, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-spooled-set-list"></a>

### list()

Get a list of the current members of the set.

**Returns:**
A list containing the members of the set. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-spooled-set-rem"></a>

### rem(*items)

Remove an item from the set.

**Args:**

- `*items` (`any`): Items to be removed from the set.


**Returns:**
The return type is `null`.

<a id="stormprims-spooled-set-rems"></a>

### rems(*items)

Remove the contents of a iterable object from the set.

**Args:**

- `*items` (`any`): Iterables items to remove from the set.


**Returns:**
The return type is `null`.

<a id="stormprims-spooled-set-size"></a>

### size()

Get the size of the set.

**Returns:**
The size of the set. The return type is `int`.

<a id="stormprims-stat-tally-f527"></a>

## stat:tally

A tally object.

An example of using it::

    $tally = $lib.stats.tally()

    $tally.inc(foo)

    for $name, $total in $tally {
        $doStuff($name, $total)
    }



<a id="stormprims-stat-tally-get"></a>

### get(name)

Get the value of a given counter.

**Args:**

- `name` (`str`): The name of the counter to get.


**Returns:**
The value of the counter, or 0 if the counter does not exist. The return type is `int`.

<a id="stormprims-stat-tally-inc"></a>

### inc(name, valu=(1))

Increment a given counter.

**Args:**

- `name` (`str`): The name of the counter to increment.
- `valu` (`int`): The value to increment the counter by.


**Returns:**
The return type is `null`.

<a id="stormprims-stat-tally-sorted"></a>

### sorted(byname=(false), reverse=(false))

Get a list of (counter, value) tuples in sorted order.

**Args:**

- `byname` (`boolean`): Sort by counter name instead of value.
- `reverse` (`boolean`): Sort in descending order instead of ascending order.


**Returns:**
List of (counter, value) tuples in sorted order. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-stix-bundle-f527"></a>

## stix:bundle

Implements the Storm API for creating and packing a STIX bundle for v2.1


<a id="stormprims-stix-bundle-add"></a>

### add(node, stixtype=(null))

Make one or more STIX objects from a node, and add it to the bundle.

Examples:
    Example Storm which would be called remotely via the ``callStorm()`` API::

        init { $bundle = $lib.stix.bundle() }
        #aka.feye.thr.apt1
        $bundle.add($node)
        fini { return($bundle) }
    

**Args:**

- `node` (`node`): The node to make a STIX object from.
- `stixtype` (`str`): The explicit name of the STIX type to map the node to. This will override the default mapping.


**Returns:**
The stable STIX id of the added object. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-stix-bundle-size"></a>

### size()

Return the number of STIX objects currently in the bundle.

**Returns:**
The return type is `int`.

<a id="stormprims-storm-query-f527"></a>

## storm:query

A storm primitive representing an embedded query.


<a id="stormprims-storm-query-exec"></a>

### exec()

Execute the Query in a sub-runtime.

Notes:
    The ``.exec()`` method can return a value if the Storm query
    contains a ``return( ... )`` statement in it.

**Returns:**
A value specified with a return statement, or none. The return type may be one of the following: `null`, `any`.

<a id="stormprims-storm-query-size"></a>

### size(limit=(1000))

Execute the Query in a sub-runtime and return the number of nodes yielded.

**Args:**

- `limit` (`int`): Limit the maximum number of nodes produced by the query.


**Returns:**
The number of nodes yielded by the query. The return type is `int`.

<a id="stormprims-str-f527"></a>

## str

Implements the Storm API for a String object.


<a id="stormprims-str-encode"></a>

### encode(encoding='utf8')

Encoding a string value to bytes.

**Args:**

- `encoding` (`str`): Encoding to use. Defaults to utf8.


**Returns:**
The encoded string. The return type is [`bytes`](#stormprims-bytes-f527).

<a id="stormprims-str-endswith"></a>

### endswith(text)

Check if a string ends with text.

**Args:**

- `text` (`str`): The text to check.


**Returns:**
True if the text ends with the string, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-str-find"></a>

### find(valu)

Find the offset of a given string within another.

Examples:
    Find values in the string ``asdf``::

        $x = asdf
        $x.find(d) // returns 2
        $x.find(v) // returns null



**Args:**

- `valu` (`str`): The substring to find.


**Returns:**
The first offset of substring or null. The return type is `int`.

<a id="stormprims-str-format"></a>

### format(**kwargs)

Format a text string from an existing string.

Examples:
    Format a string with a fixed argument and a variable::

        $template='Hello {name}, list is {list}!' $list=(1,2,3,4) $new=$template.format(name='Reader', list=$list)

        

**Args:**

- `**kwargs` (`any`): Keyword values which are substituted into the string.


**Returns:**
The new string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-join"></a>

### join(items)

Join items into a string using the current string as a separator.

Examples:
    Join together a list of strings with a dot separator::

        storm> $sepr='.' $foo=$sepr.join(('rep', 'vtx', 'tag')) $lib.print($foo)

        rep.vtx.tag

    Join values inline together with a dot separator::

        storm> $foo=('.').join(('rep', 'vtx', 'tag')) $lib.print($foo)

        rep.vtx.tag

**Args:**

- `items` (`list`): A list of items to join together.


**Returns:**
The joined string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-json"></a>

### json()

Parse a JSON string and return the deserialized data.

**Returns:**
The JSON deserialized object. The return type is `prim`.

<a id="stormprims-str-ljust"></a>

### ljust(size, fillchar=' ')

Left justify the string.

**Args:**

- `size` (`int`): The length of character to left justify.
- `fillchar` (`str`): The character to use for padding.


**Returns:**
The left justified string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-lower"></a>

### lower()

Get a lowercased copy of the string.

Examples:
    Printing a lowercased string::

        $foo="Duck"
        $lib.print($foo.lower())

**Returns:**
The lowercased string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-lstrip"></a>

### lstrip(chars=(null))

Remove leading characters from a string.

Examples:
    Removing whitespace and specific characters::

        $strippedFoo = $foo.lstrip()
        $strippedBar = $bar.lstrip(w)

**Args:**

- `chars` (`str`): A list of characters to remove. If not specified, whitespace is stripped.


**Returns:**
The stripped string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-replace"></a>

### replace(oldv, newv, maxv=(null))

Replace occurrences of a string with a new string, optionally restricting the number of replacements.

Example:
    Replace instances of the string "bar" with the string "baz"::

        $foo.replace('bar', 'baz')

**Args:**

- `oldv` (`str`): The value to replace.
- `newv` (`str`): The value to add into the string.
- `maxv` (`int`): The maximum number of occurrences to replace.


**Returns:**
The new string with replaced instances. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-reverse"></a>

### reverse()

Get a reversed copy of the string.

Examples:
    Printing a reversed string::

        $foo="foobar"
        $lib.print($foo.reverse())

**Returns:**
The reversed string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-rjust"></a>

### rjust(size, fillchar=' ')

Right justify the string.

**Args:**

- `size` (`int`): The length of character to right justify.
- `fillchar` (`str`): The character to use for padding.


**Returns:**
The right justified string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-rsplit"></a>

### rsplit(text, maxsplit=(-1))

Split the string into multiple parts, from the right, based on a separator.

Example:
    Split a string on the colon character::

        ($foo, $bar) = $baz.rsplit(":", maxsplit=1)

**Args:**

- `text` (`str`): The text to split the string up with.
- `maxsplit` (`int`): The max number of splits.


**Returns:**
A list of parts representing the split string. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-str-rstrip"></a>

### rstrip(chars=(null))

Remove trailing characters from a string.

Examples:
    Removing whitespace and specific characters::

        $strippedFoo = $foo.rstrip()
        $strippedBar = $bar.rstrip(asdf)
    

**Args:**

- `chars` (`str`): A list of characters to remove. If not specified, whitespace is stripped.


**Returns:**
The stripped string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-size"></a>

### size()

Return the length of the string.

**Returns:**
The size of the string. The return type is `int`.

<a id="stormprims-str-slice"></a>

### slice(start, end=(null))

Get a substring slice of the string.

Examples:
    Slice from index to 1 to 5::

        $x="foobar"
        $y=$x.slice(1,5)  // "ooba"

    Slice from index 3 to the end of the string::

        $y=$x.slice(3)  // "bar"


**Args:**

- `start` (`int`): The starting character index.
- `end` (`int`): The ending character index. If not specified, slice to the end of the string


**Returns:**
The slice substring. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-split"></a>

### split(text, maxsplit=(-1))

Split the string into multiple parts based on a separator.

Example:
    Split a string on the colon character::

        ($foo, $bar) = $baz.split(":")

**Args:**

- `text` (`str`): The text to split the string up with.
- `maxsplit` (`int`): The max number of splits.


**Returns:**
A list of parts representing the split string. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-str-startswith"></a>

### startswith(text)

Check if a string starts with text.

**Args:**

- `text` (`str`): The text to check.


**Returns:**
True if the text starts with the string, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-str-strip"></a>

### strip(chars=(null))

Remove leading and trailing characters from a string.

Examples:
    Removing whitespace and specific characters::

        $strippedFoo = $foo.strip()
        $strippedBar = $bar.strip(asdf)

**Args:**

- `chars` (`str`): A list of characters to remove. If not specified, whitespace is stripped.


**Returns:**
The stripped string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-title"></a>

### title()

Get a title cased copy of the string.

Examples:
    Printing a title cased string::

        $foo="Hello world."
        $lib.print($foo.title())

**Returns:**
The title cased string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-str-upper"></a>

### upper()

Get a uppercased copy of the string.

Examples:
    Printing a uppercased string::

        $foo="Duck"
        $lib.print($foo.upper())

**Returns:**
The uppercased string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-tabular-printer-f527"></a>

## tabular:printer

A Storm object for printing tabular data using a defined configuration.


<a id="stormprims-tabular-printer-header"></a>

### header()

Create a header row string.

**Returns:**
The header row string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-tabular-printer-row"></a>

### row(data)

Create a new row string from a data list.

**Args:**

- `data` (`list`): The data to create the row from; length must match the number of configured columns.


**Returns:**
The row string. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-telepath-proxy-f527"></a>

## telepath:proxy

Implements the Storm API for a Telepath proxy.

These can be created via ``$lib.telepath.open()``. Storm Service objects
are also Telepath proxy objects.

Methods called off of these objects are executed like regular Telepath RMI
calls.

An example of calling a method which returns data::

    $prox = $lib.telepath.open($url)
    $result = $prox.doWork($data)
    return ( $result )

An example of calling a method which is a generator::

    $prox = $lib.telepath.open($url)
    for $item in $prox.genrStuff($data) {
        $doStuff($item)
    }



<a id="stormprims-telepath-proxy-genrmethod-f527"></a>

## telepath:proxy:genrmethod

Implements the generator methods for the telepath:proxy.

An example of calling a method which is a generator::

    $prox = $lib.telepath.open($url)
    for $item in $prox.genrStuff($data) {
        $doStuff($item)
    }


<a id="stormprims-telepath-proxy-method-f527"></a>

## telepath:proxy:method

Implements the call methods for the telepath:proxy.

An example of calling a method which returns data::

    $prox = $lib.telepath.open($url)
    $result = $prox.doWork($data)
    $doStuff($result)


<a id="stormprims-trigger-f527"></a>

## trigger

Implements the Storm API for a Trigger.


<a id="stormprims-trigger-async"></a>

### async

Whether the Trigger runs asynchronously.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-trigger-cond"></a>

### cond

The edit type which causes the Trigger to fire.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-created"></a>

### created

The timestamp when the Trigger was created.

**Returns:**
The type is `int`.

<a id="stormprims-trigger-creator"></a>

### creator

The iden of the user that created the Trigger.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-doc"></a>

### doc

The description of the Trigger.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-enabled"></a>

### enabled

Whether the Trigger is enabled.

**Returns:**
The type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-trigger-form"></a>

### form

The form which causes the Trigger to fire.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-iden"></a>

### iden

The Trigger iden.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-n2form"></a>

### n2form

The N2 form which causes the Trigger to fire.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-name"></a>

### name

The name of the Trigger.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-prop"></a>

### prop

The prop which causes the Trigger to fire.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-storm"></a>

### storm

The Storm query that the Trigger runs.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-tag"></a>

### tag

The tag which causes the Trigger to fire.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-user"></a>

### user

The iden of the user the Trigger runs as.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-verb"></a>

### verb

The edge verb which causes the Trigger to fire.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-trigger-view"></a>

### view

The iden of the view the Trigger runs in.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-valu-f527"></a>

## valu

A generic type and value tuple representing a typed Storm value.

The first element of the tuple is a data model type name and the second is
the normalized value. All type-driven behavior (comparison, deref, repr) is
dispatched through the model Type resolved from that type name.


<a id="stormprims-valu-is"></a>

### is(name)

Check if the type in the tuple is a given type.

**Args:**

- `name`: The type or types to compare the type in the tuple against. The input type may be one of the following: `str`, `list`.


**Returns:**
True if the type is at least one of the types specified, false otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-valu-type"></a>

### type

Get the type of the tuple.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-valu-value"></a>

### value

Get the valu of the tuple.

**Returns:**
The type is `any`.

<a id="stormprims-vault-f527"></a>

## vault

Implements the Storm API for a Vault.

Callers (instantiation) of this class must have already checked that the user has at least
PERM_READ to the vault.

Permissions are checked against the runtime in scope, which is the one reading the vault
rather than the one which resolved it, so that a privsep module using asroot:perms may read
secrets on behalf of a caller who only holds PERM_READ. The runtime captured at construction
is used only when no runtime is in scope, which happens when callStorm converts a vault
object it is returning after the runtime has exited.


<a id="stormprims-vault-configs"></a>

### configs

The Vault configs data.

**Returns:**
The return type is [`vault:data`](#stormprims-vault-data-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-vault-delete"></a>

### delete()

Delete the Vault.

**Returns:**
``(true)`` if the vault was deleted, ``(false)`` otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-vault-iden"></a>

### iden

The Vault iden.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-vault-name"></a>

### name

The Vault name.

**Returns:**
The return type is [`str`](#stormprims-str-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-vault-owner"></a>

### owner

The Vault owner (user or role iden).

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-vault-permissions"></a>

### permissions

The Vault permissions.

**Returns:**
The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-vault-scope"></a>

### scope

The Vault scope.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-vault-secrets"></a>

### secrets

The Vault secrets data.

**Returns:**
The return type is [`vault:data`](#stormprims-vault-data-f527).
When this is used to set the value, it does not have a return type.

<a id="stormprims-vault-setPerm"></a>

### setPerm(iden, level)

Set easy permissions on the Vault.

**Args:**

- `iden` (`str`): The user or role to modify.
- `level` (`str`): The easyperm level for the iden. ``(null)`` to remove an existing permission.


**Returns:**
``(true)`` if the permission was set, ``(false)`` otherwise. The return type is [`boolean`](#stormprims-boolean-f527).

<a id="stormprims-vault-type"></a>

### type

The Vault type.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-vault-vdef"></a>

### vdef()

Get the full vault definition dict. Secrets are omitted without edit permission.

**Returns:**
The vault definition. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-vault-data-f527"></a>

## vault:data

Implements the Storm API for Vault data. This is used for both vault configs and vault secrets.


<a id="stormprims-view-f527"></a>

## view

Implements the Storm api for a View instance.


<a id="stormprims-view-addNode"></a>

### addNode(form, valu, props=(null))

Transactionally add a single node and all it's properties. If any validation fails, no changes are made.

**Args:**

- `form` (`str`): The form name.
- `valu` (`prim`): The primary property value.
- `props` (`dict`): An optional dictionary of props.


**Returns:**
The node if the view is the current view, otherwise null. The return type is [`node`](#stormprims-node-f527).

<a id="stormprims-view-addNodeEdits"></a>

### addNodeEdits(edits)

Add NodeEdits to the view.

**Args:**

- `edits` (`list`): A list of nodeedits.


**Returns:**
The return type is `null`.

<a id="stormprims-view-children"></a>

### children()

Yield Views which are children of this View.

**Yields:**
Child Views. The return type is [`view`](#stormprims-view-f527).

<a id="stormprims-view-delMergeRequest"></a>

### delMergeRequest()

Remove the existing merge request.

**Returns:**
The deleted merge request. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-delMergeVote"></a>

### delMergeVote(useriden=(null))

Remove a previously created merge vote.

Notes:
    The default use case removes a vote cast by the current user. Specifying the useriden
    parameter allows you to remove a vote cast by another user but requires global admin
    permissions.


**Args:**

- `useriden` (`str`): Delete a merge vote by a different user.


**Returns:**
The vote record that was removed. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-detach"></a>

### detach()

Detach the view from its parent. WARNING: This cannot be reversed.

**Returns:**
The return type is `null`.

<a id="stormprims-view-fork"></a>

### fork(name=(null))

Fork a View in the Cortex.

**Args:**

- `name` (`str`): The name of the new view.


**Returns:**
The ``view`` object for the new View. The return type is [`view`](#stormprims-view-f527).

<a id="stormprims-view-get"></a>

### get(name, defv=(null))

Get a view configuration option.

**Args:**

- `name` (`str`): Name of the value to get.
- `defv` (`prim`): The default value returned if the name is not set in the View.


**Returns:**
The value requested or the default value. The return type is `prim`.

<a id="stormprims-view-getEdgeVerbs"></a>

### getEdgeVerbs()

Get the Edge verbs which exist in the View.

**Yields:**
Yields the edge verbs used by Layers which make up the View. The return type is [`str`](#stormprims-str-f527).

<a id="stormprims-view-getEdges"></a>

### getEdges(verb=(null))

Get node information for Edges in the View.

**Args:**

- `verb` (`str`): The name of the Edges verb to iterate over.


**Yields:**
Yields tuples containing the source nid, verb, and destination nid. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-view-getFormCounts"></a>

### getFormCounts()

Get the formcounts for the View.

Example:
    Get the formcounts for the current View::

        $counts = $lib.view.get().getFormCounts()

**Returns:**
Dictionary containing form names and the count of the nodes in the View's Layers. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-getMergeRequest"></a>

### getMergeRequest()

Return the existing merge request or null.

**Returns:**
The merge request. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-getMergeRequestSummary"></a>

### getMergeRequestSummary()

Return the merge request, votes, parent quorum definition, and current layer offset.

**Returns:**
The summary info. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-getMerges"></a>

### getMerges()

Yields previously successful merges into the view.

**Yields:**
Yields previously successful merges into the view. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-getMergingViews"></a>

### getMergingViews()

Get a list of idens of Views that have open merge requests to this View.

**Idens:**
The list of View idens that have an open merge request into this View. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-view-getPropArrayCount"></a>

### getPropArrayCount(propname, valu=$lib.undef)

Get the number of individual array property values in the View for the given array property name.

Notes:
   This is a fast approximate count calculated by summing the number of
   array property values in each layer of the view. Property values
   which are overwritten by different values in higher layers will
   still be included in the count.


**Args:**

- `propname` (`str`): The property name to look up.
- `valu` (`any`): The value in the array property to look up.


**Returns:**
The count of nodes. The return type is `int`.

<a id="stormprims-view-getPropCount"></a>

### getPropCount(propname, valu=$lib.undef, cmpr='=', type=$lib.undef)

Get the number of nodes in the View with a specific property and optional value.

Notes:
   This is a fast approximate count calculated by summing the number of
   nodes with the property value in each layer of the view. Property values
   which are overwritten by different values in higher layers will still
   be included in the count. When ``valu`` is provided, only the ``=`` (exact)
   and ``^=`` (prefix) comparators are supported.


**Args:**

- `propname` (`str`): The property name to look up.
- `valu` (`any`): The value of the property to look up.
- `cmpr` (`str`): The comparator to use with valu. Only = and ^= are supported.
- `type` (`str`): For a polymorphic property, count only values of this member type (cannot be combined with valu).


**Returns:**
The count of nodes. The return type is `int`.

<a id="stormprims-view-getPropValues"></a>

### getPropValues(propname, valu=$lib.undef, cmpr='=', limit=$lib.undef, type=$lib.undef)

Yield unique property values in the view for the given form or property name.

Notes:
    When ``valu`` is provided, only the ``=`` (exact) and ``^=`` (prefix) comparators are
    supported. For a polymorphic property, ``type`` restricts the results to a single
    member type.


**Args:**

- `propname` (`str`): The property or form name to look up.
- `valu` (`any`): An optional value to filter results using the specified comparator.
- `cmpr` (`str`): The comparator to use with valu. Only = and ^= are supported.
- `limit` (`int`): An optional maximum number of values to yield.
- `type` (`str`): For a polymorphic property, restrict results to this member type name.


**Yields:**
Unique property values. The return type is `any`.

<a id="stormprims-view-getTagPropCount"></a>

### getTagPropCount(tag, propname, form=(null), valu=$lib.undef)

Get the number of nodes in the View with the given tag property and optional value.

Notes:
   This is a fast approximate count calculated by summing the number of
   nodes with the tag property value in each layer of the view.
   Values which are overwritten by different values in higher layers
   will still be included in the count.


**Args:**

- `tag` (`str`): The tag to look up.
- `propname` (`str`): The property name to look up.
- `form` (`str`): The optional form to look up.
- `valu` (`any`): The value of the property to look up.


**Returns:**
The count of nodes. The return type is `int`.

<a id="stormprims-view-iden"></a>

### iden

The iden of the View.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-view-insertParentFork"></a>

### insertParentFork(name=(null))

Insert a new View between a forked View and its parent.

**Args:**

- `name` (`str`): The name of the new View.


**Returns:**
The ``view`` object for the new View. The return type is [`view`](#stormprims-view-f527).

<a id="stormprims-view-layers"></a>

### layers

The ``layer`` objects associated with the ``view``.

**Returns:**
The type is [`list`](#stormprims-list-f527).

<a id="stormprims-view-merge"></a>

### merge(force=(false))

Schedule a merge of a forked View back into its parent View.

The forking layer is flipped to read-only and the merge runs as
a background task that resumes automatically across Cortex
restarts. The call returns immediately with the merge info; the
forked View and its top layer are removed once the merge
completes.

**Args:**

- `force` (`boolean`): Force the view to merge if possible.


**Returns:**
The newly created merge info. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-parent"></a>

### parent

The parent View. Will be ``(null)`` if the view is not a fork.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-view-repr"></a>

### repr()

Get a string representation of the View.

**Returns:**
A list of lines that can be printed, representing a View. The return type is [`list`](#stormprims-list-f527).

<a id="stormprims-view-set"></a>

### set(name, valu)

Set a view configuration option.

Current runtime updatable view options include:

    name (str)
        A terse name for the View.

    desc (str)
        A description of the View.

    parent (str)
        The parent View iden.

    protected (bool)
        Setting to ``(true)`` will prevent the layer from being merged or deleted.

    layers (list(str))
        Set the list of layer idens for a non-forked view. Layers are specified
        in precedence order with the first layer in the list being the write layer.

    quorum (dict)
        A dictionary of the quorum settings which require users to vote on merges.

        ::

            {
                "count": <int>,
                "roles": [ <roleid>, ... ]
            }

        Once quorum is enabled for a view, any forks must use the setMergeRequest()
        API to request that the child view is merged. The $view.addMergeVote() API
        is used for users to add their votes if they have been granted one of the
        roles listed. Once the number of approvals are met and there are no vetoes, a
        background process will kick off which merges the nodes and ultimately deletes
        the view and top layer.

To maintain consistency with the view.fork() semantics, setting the "parent"
option on a view has a few limitations:

    * The view must not already have a parent
    * The view must not have more than 1 layer


**Args:**

- `name` (`str`): The name of the value to set.
- `valu` (`prim`): The value to set.


**Returns:**
The return type is `null`.

<a id="stormprims-view-setMergeComment"></a>

### setMergeComment(comment)

Set the main comment/description of a merge request.

**Args:**

- `comment` (`str`): The text comment to set for the merge request


**Returns:**
The updated merge request. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-setMergeRequest"></a>

### setMergeRequest(comment=(null))

Setup a merge request for the view in the current state.

**Args:**

- `comment` (`str`): A text comment to include in the merge request.


**Returns:**
The newly created merge request. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-setMergeVote"></a>

### setMergeVote(approved=(true), comment=(null))

Register a vote for or against the current merge request.

**Args:**

- `approved` (`boolean`): Set to (true) to approve the merge or (false) to veto it.
- `comment` (`str`): A comment attached to the vote.


**Returns:**
The vote record that was created. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-setMergeVoteComment"></a>

### setMergeVoteComment(comment)

Set the comment associated with your vote on a merge request.

**Args:**

- `comment` (`str`): The text comment to set for the merge vote


**Returns:**
The fully updated vote record. The return type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-view-swapLayer"></a>

### swapLayer()

Swaps the top layer for a fresh one and deletes the old layer.

**Returns:**
The return type is `null`.

<a id="stormprims-view-triggers"></a>

### triggers

The ``trigger`` objects associated with the ``view``.

**Returns:**
The type is [`list`](#stormprims-list-f527).

<a id="stormprims-view-wipeLayer"></a>

### wipeLayer()

Delete all nodes and nodedata from the write layer. Triggers will be run.

**Returns:**
The return type is `null`.

<a id="stormprims-xml-element-f527"></a>

## xml:element

A Storm object for dealing with elements in an XML tree.


<a id="stormprims-xml-element-attrs"></a>

### attrs

The element attributes list.

**Returns:**
The type is [`dict`](#stormprims-dict-f527).

<a id="stormprims-xml-element-find"></a>

### find(name, nested=(true))

Find all nested elements with the specified tag name.

**Args:**

- `name` (`str`): The name of the XML tag.
- `nested` (`boolean`): Set to ``(false)`` to only find direct children.


**Returns:**
A generator which yields xml:elements. The return type is `generator`.

<a id="stormprims-xml-element-get"></a>

### get(name)

Get a single child element by XML tag name.

**Args:**

- `name` (`str`): The name of the child XML element tag.


**Returns:**
The child XML element or ``(null)``. The return type is [`xml:element`](#stormprims-xml-element-f527).

<a id="stormprims-xml-element-name"></a>

### name

The element tag name.

**Returns:**
The type is [`str`](#stormprims-str-f527).

<a id="stormprims-xml-element-text"></a>

### text

The element text body.

**Returns:**
The type is [`str`](#stormprims-str-f527).
