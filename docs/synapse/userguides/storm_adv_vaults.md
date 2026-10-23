```mdstorm-setup
```

<a id="storm-adv-vaults"></a>


# Storm Reference - Advanced - Vaults

A [vault](../glossary.md#gloss-vault) is protected storage for the secret values (such as API keys and passwords) and the configuration settings that a Storm package or user needs to talk to something else. This section describes what a vault holds, who may use it, how Storm finds the right one, and how to use one safely from a [privileged module](../devguides/power-ups.md#privileged-modules).

<a id="storm-vaults-overview"></a>


## Overview

A vault is stored in the Cortex and has these fields:

| Field | Description |
|-------|-------------|
| `iden` | The unique identifier of the vault. |
| `name` | A name that is unique across all vaults, 1 to 128 characters. |
| `type` | A string that says what the vault is for, such as `acme-intel`. A vault type may declare a schema for the vault `configs` and `secrets`. |
| `scope` | `global`, `role`, `user`, or none (an unscoped vault). See [Scopes](#storm-vaults-scopes). |
| `owner` | The iden of the user or role the vault belongs to. It is not set for a `global` vault. |
| `permissions` | The users and roles that can use the vault, and at what level. See [Permissions](#storm-vaults-perms). |
| `secrets` | A dictionary of sensitive values. |
| `configs` | A dictionary of non-sensitive settings. |

Keep anything that must not be disclosed, such as an API key or a proxy password, in `secrets`, and everything else, such as a URL, a proxy user name, or a flag, in `configs`. The two are protected differently: a user who may only read a vault can see its `configs` but not its `secrets`.

Use a vault, rather than `$lib.globals`, to store a credential. A vault can be shared with specific users and roles, can hold more than one credential per service, and can be validated against a schema.

Storm packages that talk to an external service typically keep their settings (the "configuration" of a Power-Up) in a vault whose type is the name of the package. The configuration commands of such a package create and update the vault on your behalf.

<a id="storm-vaults-scopes"></a>


## Scopes

The scope of a vault says who it is for, and so that vaults Storm considers when it is asked for the vault of a given type.

| Scope | Owner | Granted when created | Selected automatically |
|-------|-------|----------------------|------------------------|
| `user` | The user the vault belongs to. | The owner has `admin`. | Yes, for the owner. |
| `role` | The role the vault belongs to. | Members of the role have `read`. Nobody has `admin`, so a Cortex admin must manage the vault or grant someone else access. | Yes, for members of the role who can read it. |
| `global` | None. | The `all` role has `read`, so every user may use it. | Yes, for everyone who can read it. |
| none (unscoped) | The user that owns the vault. | The owner has `admin`. | No. It must be requested by name. |

A new vault has only the access shown in the table above. Any permissions passed when it is created are ignored, and everyone else has the default level of `deny` until they are given access.

The scope decides which vaults Storm selects for a user. It does not hide a vault from the admins of the Cortex. An admin of the Cortex may list, read, change, and delete every vault, including the `secrets` of a `user` vault that belongs to someone else. Do not store a credential in a Cortex if its admins should not be able to see it.

A vault is identified by its type, scope, and owner. Only one vault may exist for each combination, so a user may have one `user` vault of a type, and a role may have one `role` vault of a type. An unscoped vault is exempt from this rule, which is what allows several vaults of one type to exist at once, such as separate credentials for different teams. Since nothing selects an unscoped vault automatically, it is always requested by its name.

Only an admin may create a `global` or `role` vault. A user may create a `user` vault only for themselves.

```mdstorm --hide
$lib.auth.users.add(visi)
$lib.auth.roles.add(analysts)
```

```mdstorm
$lib.vault.add(acme-global, acme-intel, global, (null), ({"apikey": "global-key"}), ({"url": "https://acme.example.com"}))
$lib.vault.add(acme-visi, acme-intel, user, $lib.auth.users.byname(visi).iden, ({"apikey": "visi-key"}), ({"url": "https://acme.example.com"}))

for $vault in $lib.vault.list() {
    $lib.print(`{$vault.name}: type={$vault.type} scope={$vault.scope}`)
}
```

<a id="storm-vaults-design"></a>


## Designing Vaults for a Power-Up

Use one vault **type** for each Power-Up, such as `mailer` for the credentials of an external mail service. Put the values that must stay hidden, such as API keys, tokens, and passwords, in the `secrets`, and the values that need not, such as hosts, ports, and user names, in the `configs`. A user, role, or the whole Cortex then has a vault of that type holding the credentials to use, and the code that uses it needs only the type.

The **type** and **scope** together decide how many vaults may exist, so a type is not shared between Power-Ups. A user may have only one `user` vault of a type, so a single type shared by two Power-Ups could hold the credentials for only one of them. A mail service and a chat service each get their own type, such as `mailer` and `chat`, and a user who works with both has one vault of each type.

Users who each have their own credentials for a Power-Up each create a `user` vault of its type. Their code does not need to know which vault is theirs. [`$lib.vault.bytype(mailer)`](../stormtypes_libs.md#stormlibs-lib-vault-bytype) returns the vault of the user running it, so the same macro, command, or query works for every user. Because each user has their own credentials, the remote service can tell the users apart. Synapse does not track which credentials a user uses, so keep a separate set per user when the service should know who made a request.

The **name** of a vault is unique across all vaults, whatever their type, scope, or owner. Two users can not both create a vault named `mailer-key`, even though each would be the only owner of a `user` vault of that type. Give each vault a name that identifies its owner, such as `mailer-visi`, and look vaults up by type rather than by name.

```mdstorm --hide
$lib.auth.users.add(ron)
$lib.vault.add(mailer-visi, mailer, user, $lib.auth.users.byname(visi).iden, ({"apikey": "visi-key"}), ({}))
```

```mdstorm --fail
$lib.vault.add(mailer-visi, mailer, user, $lib.auth.users.byname(ron).iden, ({"apikey": "ron-key"}), ({}))
```

```mdstorm
$lib.vault.add(mailer-ron, mailer, user, $lib.auth.users.byname(ron).iden, ({"apikey": "ron-key"}), ({}))

for $vault in $lib.vault.list() {
    if ($vault.type = "mailer") {
        $lib.print(`{$vault.name}: owner={$lib.auth.users.get($vault.owner).name}`)
    }
}
```

To share one set of credentials, create a `role` or `global` vault of the type instead. A user's own `user` vault takes precedence over them when the code looks the vault up by type. A vault that should be used only when asked for, such as one of several sets of credentials, is created unscoped. Code selects it by name, usually from a `--config <name>` option on a command.

<a id="storm-vaults-resolve"></a>


## Finding a Vault

Storm can find a vault by its iden ([`$lib.vault.get()`](../stormtypes_libs.md#stormlibs-lib-vault-get)), by its name ([`$lib.vault.byname()`](../stormtypes_libs.md#stormlibs-lib-vault-byname)), or by its type ([`$lib.vault.bytype()`](../stormtypes_libs.md#stormlibs-lib-vault-bytype)). Each requires that the calling user may read the vault.

[`$lib.vault.bytype()`](../stormtypes_libs.md#stormlibs-lib-vault-bytype) is how code finds the vault that applies to the user running it. It considers the vaults of the type in this order, and returns the first one it finds:

1. The `user` vault of the calling user.
2. The `role` vault of any role the user is a member of. A role vault that the user may not read is skipped. If several of the user's roles have a vault of the type, the roles are checked in the order they are listed for the user, and the first vault the user may read is used.
3. The `global` vault.

A user may override a shared configuration by creating a `user` vault of the same type, and a `role` vault overrides the `global` one for that role's members. If the vault that is found is one the user is not allowed to read, the call fails with an authorization error rather than moving on to the next scope. Pass the `scope` argument to look only in one scope.

An unscoped vault is never returned by [`$lib.vault.bytype()`](../stormtypes_libs.md#stormlibs-lib-vault-bytype); use [`$lib.vault.byname()`](../stormtypes_libs.md#stormlibs-lib-vault-byname) or [`$lib.vault.get()`](../stormtypes_libs.md#stormlibs-lib-vault-get) for it.

```mdstorm
$vault = $lib.vault.bytype(acme-intel)
$lib.print(`{$vault.name} {$vault.scope}`)

$vault = $lib.vault.bytype(acme-intel, scope=global)
$lib.print(`{$vault.name} {$vault.scope}`)
```

[`$lib.vault.list()`](../stormtypes_libs.md#stormlibs-lib-vault-list) yields only the vaults that the calling user may read.

<a id="storm-vaults-perms"></a>


## Permissions

Access to a vault is controlled with four permission levels, which are available in Storm as [`$lib.auth.easyperm.level`](../stormtypes_libs.md#stormlibs-lib-auth-easyperm):

| Level | Value | Allows |
|-------|-------|--------|
| `deny` | 0 | Nothing. A `deny` on a user is final, whatever their roles allow. |
| `read` | 1 | Reading the vault `configs`, and using the vault. |
| `edit` | 2 | Everything in `read`, plus reading and changing the vault `secrets`, changing the `configs`, and renaming the vault. |
| `admin` | 3 | Everything in `edit`, plus changing the vault permissions and deleting it. |

A user is granted a level if their own level, or the level of any of their roles, is high enough. A user who is an admin of the Cortex may do everything to every vault, whatever its scope or permissions, and a `deny` does not apply to them. This is separate from the `admin` level on a vault, which only allows managing that vault. There is no separate permission that grants access to vaults in general; access is set on each vault.

> [!NOTE]
> A user who has only `read` on a vault cannot read its `secrets`. The `secrets` of such a vault are `(null)`, and the vault is left without its `secrets` when it is converted to a dictionary or returned from a query. A vault that has been shared with `read` is therefore useful on its own for the `configs`, and for secrets only through a privileged module (see [Using Vaults in Privileged Modules](#storm-vaults-privsep)).

Permissions are set on a vault with `vault.set.perm` or [`$vault.setPerm()`](../stormtypes_prims.md#stormprims-vault-setPerm), and require `admin` on the vault.

```mdstorm --hide
$lib.vault.add(acme-unscoped, acme-intel, (null), $lib.auth.users.byname(root).iden, ({"apikey": "unscoped-key"}), ({}))
```

```mdstorm
vault.set.perm acme-unscoped --user visi --level read
```

```mdstorm
vault.set.perm acme-unscoped --role analysts --level edit
```

```mdstorm
vault.set.perm acme-unscoped --role analysts --revoke
```

```mdstorm
$vault = $lib.vault.byname(acme-unscoped)
for ($iden, $level) in $vault.permissions.users {
    $lib.print(`{$lib.auth.users.get($iden).name}: {$level}`)
}
```

<a id="storm-vaults-manage"></a>


## Managing Vaults

The `vault.*` [commands](storm_ref_cmd.md#storm-vault) create and manage vaults from the command line. The same operations are available from Storm through [`$lib.vault`](../stormtypes_libs.md#stormlibs-lib-vault), and through the properties of the vault object that it returns.

```mdstorm --hide-output
vault.add acme-role acme-intel ({"apikey": "role-key"}) ({"url": "https://acme.example.com"}) --role analysts
```

```mdstorm
vault.set.configs acme-role url --value https://other.example.com
```

```mdstorm
vault.set.secrets acme-role apikey --value rotated-key
```

```mdstorm
vault.set.configs acme-role url --delete
```

The same changes can be made from Storm with the properties of the vault:

```mdstorm
$vault = $lib.vault.byname(acme-role)

$vault.name = acme-analysts
$vault.secrets.apikey = another-key
$vault.configs.url = https://acme.example.com

$lib.print($vault.configs)
$lib.print($vault.secrets.apikey)

$vault.configs.url = $lib.undef
$lib.print($vault.configs)
```

Assigning [`$lib.undef`](../stormtypes_libs.md#stormlibs-lib-undef) to a key removes it. [`$lib.vault.print()`](../stormtypes_libs.md#stormlibs-lib-vault-print) prints the details of a vault, and omits the `secrets` unless `showsecrets` is set and the user has `edit` on the vault. To replace several settings at once, change a dictionary from [`$vault.vdef()`](../stormtypes_prims.md#stormprims-vault-vdef) and pass it to [`$lib.vault.update()`](../stormtypes_libs.md#stormlibs-lib-vault-update), which requires `edit` on the vault, or `admin` if the permissions are changed.

A vault is deleted with `vault.del` or [`$vault.delete()`](../stormtypes_prims.md#stormprims-vault-delete), which require `admin`.

<a id="storm-vaults-use"></a>


## Using the Values in a Vault

Storing values in a vault does nothing until Storm reads them. Find the vault, then read its `configs` and `secrets` like the keys of a dictionary, and use them to do the work, such as connecting to a server or calling an API. A vault that holds the host and the credentials for a service is used like this:

```storm
$vault = $lib.vault.bytype(mailer)

$url = `https://{$vault.configs.host}/api/v1/messages`
$headers = ({"Authorization": `Bearer {$vault.secrets.apikey}`})

$resp = $lib.inet.http.get($url, headers=$headers)
```

Reading the `configs` needs `read` on the vault, but reading the `secrets` needs `edit`. A user who has only `read` gets `(null)` for [`$vault.secrets`](../stormtypes_prims.md#stormprims-vault-secrets), so a query that uses a secret only works for a user who has `edit` on the vault, or when a [privileged module](#storm-vaults-privsep) uses the secret for them. The owner of a `user` vault has `admin`, so a query like the one above works for them without a privileged module.

Which vault type to use depends on what the vault is for:

* **A Power-Up or query you are writing.** Define a vault type for it, as described in [Vault Types](#storm-vaults-types), and create a vault of that type with the values it needs. The code you write finds the vault and reads whichever of its values it needs, as above.
* **A feature that has its own vault types.** Some Storm libraries and packages register vault types of their own and create the vaults for you with their own commands or functions. Do not define a type for them. Use the commands or functions of the feature to store the values, which are validated against the type it provides, and let it read them. [`$lib.vault.type.list()`](../stormtypes_libs.md#stormlibs-lib-vault-type-list) shows the types that are registered in the Cortex.

In both cases the vault is the same kind of object, with the same scopes and permissions. The difference is who decides which `configs` and `secrets` it holds and who reads them.

<a id="storm-vaults-privsep"></a>


## Using Vaults in Privileged Modules

A vault that is shared with `read` lets a user use a credential without being able to see it. This works because of how a [privileged module](../devguides/power-ups.md#privileged-modules) is checked: the permissions on a vault are checked against whatever is **reading** it at the time. A privileged module runs with the permissions of an admin, so it may read the `secrets` of a vault that the user running it could not.

That makes the module the place where the secret is protected or leaked, and there is a pattern that keeps a credential safe. Let the **caller** find the vault, and pass it to the privileged module, which uses the `secrets` and returns only the result.

An `acme-intel` module that is privileged because of `asroot:perms` is written to accept a vault:

```storm
// acme.intel.privsep

function lookup(fqdn, vault) {

    // This is read as the module, so the caller needs only read permission.
    $headers = ({"X-API-KEY": $vault.secrets.apikey})
    $url = `{$vault.configs.url}/api/v1/fqdn/{$fqdn}`

    $resp = $lib.inet.http.get($url, headers=$headers)
    if ($resp.code != 200) {
        $lib.warn(`lookup of {$fqdn} returned HTTP code: {$resp.code}`)
        return()
    }

    // Return the response, but not the API key.
    return($resp.json())
}
```

The non-privileged code that calls it finds the vault. Because this runs with the permissions of the calling user, the user must be allowed to read the vault, and the `user`, `role`, `global` order applies:

```storm
function lookup(fqdn, config=(null)) {

    if ($config = null) {
        $vault = $lib.vault.bytype(acme-intel)
    } else {
        $vault = $lib.vault.byname($config)
    }

    return($lib.import(acme.intel.privsep).lookup($fqdn, $vault))
}
```

This gives each of the people who use the module the vault that they are allowed to use, and a way to choose another one by name when they need to. It is the same approach taken by the configuration commands of a Power-Up, which accept a `--config` option naming a vault.

Follow these rules in a privileged module:

* **Let the caller find the vault.** Do not look up a vault by a name taken from the caller inside the module. The module reads it with elevated permissions, so the permissions of the caller are never checked, and the caller could name any vault, such as one belonging to another user.
* **Never return a secret.** Return the result of using it. A `secrets` value that is turned into a string, or a dictionary from [`$vault.vdef()`](../stormtypes_prims.md#stormprims-vault-vdef) that includes the `secrets`, is an ordinary value that is given to the caller. Returning the `secrets` object itself fails for a caller who may not read it, but that is no protection for a value that has already been copied out of it.
* **Keep the code that reads a secret small and private.** Put it in a function whose name starts with `__`, which cannot be called from outside the module.
* **Do not disclose a secret by accident.** Do not print it, include it in a warning, an error, or a log message, or pass it to a function that was given by the caller. If a URL that includes a key is logged, replace the key first.
* **Send it only where it belongs.** Write the address the secret is sent to in the module, or take it from the `configs` of a vault that the caller may not change, so that a caller can not have it sent to a server of its choosing.
* **Write to a vault carefully.** A privileged module may also change a vault. Only do so for a value that the module generated, such as a token that was refreshed, and not for one chosen by the caller.

The following is a mistake made often enough to call out:

```storm
function get_secrets() {
    return($lib.vault.byname("my_vault").secrets.api_key)
}
```

When this function is in a privileged module it hands the API key to anyone who can import the module. The vault is read with the permissions of the module, so it is returned even to a user with no access to the vault, and the secret is returned as a plain string that the caller is free to use or print. If the module needs a credential, pass the vault in as shown above, and return only what the module did with it.

<a id="storm-vaults-types"></a>


## Vault Types

A vault **type** is registered by name and version, and describes the `configs` and `secrets` a vault of that type holds with a [JSON schema](https://json-schema.org/). Vaults of a type are validated against it when they are created or changed, so invalid values are rejected and defaults are applied.

A Storm package registers the types it needs with the `vaults` key of its package definition (see [Vault Types](../devguides/power-ups.md#vault-types)). A type is registered from Storm with [`$lib.vault.type.add()`](../stormtypes_libs.md#stormlibs-lib-vault-type-add), which requires admin. The version of a type must increase each time its schema changes, and a vault of the type that was created with an earlier version is migrated. An optional migration query is given the vault as the `$vault` variable and may change its `configs` and `secrets`. [`$lib.vault.type.get()`](../stormtypes_libs.md#stormlibs-lib-vault-type-get), [`$lib.vault.type.list()`](../stormtypes_libs.md#stormlibs-lib-vault-type-list) and [`$lib.vault.type.versions()`](../stormtypes_libs.md#stormlibs-lib-vault-type-versions) show the registered types, and [`$lib.vault.type.del()`](../stormtypes_libs.md#stormlibs-lib-vault-type-del) removes one that has no vaults.

```mdstorm
$lib.vault.type.add(acme-widgets, 1, ({
    "type": "object",
    "properties": {
        "configs": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
        "secrets": {"type": "object", "properties": {"apikey": {"type": "string", "minLength": 2}}, "required": ["apikey"]},
    },
}))

$lib.vault.add(widgets, acme-widgets, global, (null), ({"apikey": "widgets-key"}), ({"url": "https://acme.example.com"}))
```

> [!TIP]
> Name a vault type after the package that owns it, so the vaults of one package are easy to recognize.
