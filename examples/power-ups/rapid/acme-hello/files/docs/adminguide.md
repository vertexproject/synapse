# Acme-Hello Admin Guide

This guide covers the configuration and permissions an admin sets up for Acme-Hello. For day to day
use of its commands, see the [User Guide](userguide.md).

## Configuration

`acme.hello.privsep` calls an external API on the user's behalf and reads its API key from
`$lib.globals`, so the key is set once by an admin rather than by each user:

```stormdoc
storm> $lib.globals."acme:hello:apikey" = mysecretkey
```

The module reads the key back with `$lib.globals."acme:hello:apikey"` and uses it to build a request
header, but never returns it to the caller. Storing it in `$lib.globals` keeps it out of reach of
users who are not permitted to read it directly.

## Granting Access

`acme.hello.privsep` is declared with `asroot:perms`, so a user may only import it once they hold
the `acme.hello.user` permission the package declares:

```stormdoc
storm> auth.user.add visi
```

```stormdoc
storm> auth.user.addrule visi acme.hello.user
Added rule acme.hello.user to user visi.
```

A user without that permission gets an `AuthDeny` error when the module is imported. The other
module, `acme.hello`, is unprivileged and needs no rule.

## Checking the Installed Version

```stormdoc
Name   : acme-hello
Version: 0.0.1
```
